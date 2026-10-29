"""Ingenuity — the machinery of novelty.

Design law respected (same as every module here): this file owns ZERO
factual knowledge. It only owns WAYS TO THINK:

  1. decompose        — take an unknown word apart (morphology, compounds)
  2. existence_reason — decide honestly between "new to me", "related to X",
                        "did you mean Y" and "no match in my world"
  3. create           — compose NEW statements from OLD facts:
                          transitive synthesis (A is-a B, B is P => A likely P)
                          cross-tree analogy (two different subtrees, same trick)
                          HDC blend (what sits between two concepts in my space)
  4. wonder           — find a hole in the graph and hypothesize into it
  5. improvement      — narrate the learning curve from progress history

Every sentence it renders is assembled from concept-graph content the
organism was taught or derived itself. Delete the graph and these
functions return honest "I have nothing to build from" — never facts.
"""
import re

from . import hdc


# ---------------- morphology machinery (language physics, not facts) ---------
SUFFIXES = (
    ("ology", "a science or study of something"),
    ("ography", "a science or study of something"),
    ("itis", "sounds like a condition or disease"),
    ("ation", "a process or event"),
    ("ition", "a process or event"),
    ("tion", "a process or event"),
    ("sion", "a process or event"),
    ("ment", "a result or institution"),
    ("ness", "a quality or state"),
    ("ity", "a quality or state"),
    ("ance", "a state or action"),
    ("ence", "a state or action"),
    ("ism", "a doctrine, movement or system"),
    ("ist", "someone who does or believes"),
    ("arium", "a place for keeping something"),
    ("orium", "a place for keeping something"),
    ("idae", "a family of creatures, scientific-style"),
    ("inae", "a subfamily of creatures, scientific-style"),
    ("us", "reads like a latin-style name — often a creature or object"),
    ("a", "could be a latin-style name"),
    ("um", "reads like a latin-style name"),
    ("ix", "reads like a coined name"),
    ("orp", "reads like a coined creature-name"),
    ("ing", "an action or ongoing process"),
    ("er", "something that does the action"),
    ("or", "something that does the action"),
    ("est", "the most of something"),
    ("ly", "a way of being"),
)

PREFIXES = (
    ("un", "a negation or opposite of"),
    ("non", "a negation of"),
    ("anti", "the opposite or enemy of"),
    ("dis", "a reversed or negated"),
    ("mis", "a wrongly done"),
    ("re", "a repeated or returned"),
    ("pre", "an earlier form of"),
    ("post", "a later form of"),
    ("sub", "an under-layer of"),
    ("super", "an above-or-bigger"),
    ("micro", "a tiny version of"),
    ("mega", "a huge version of"),
    ("macro", "a big-picture"),
    ("proto", "a first-of-its-kind"),
    ("neo", "a new kind of"),
    ("para", "a beside-or-beyond"),
)


def edit_distance(a, b, cap=3):
    """Levenshtein with early cap (small vocab — plain DP is fine)."""
    if abs(len(a) - len(b)) > cap:
        return cap + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        if min(cur) > cap:
            return cap + 1
        prev = cur
    return prev[-1]


def graph_vocab(graph):
    """All bound words + node ids as one vocabulary."""
    vocab = set(graph.by_word.keys())
    for nid, n in graph.nodes.items():
        vocab.add(nid.replace("_", " "))
        vocab.add(nid)
    return {w for w in vocab if len(w) >= 3 and w.isalpha()}


def decompose(word, graph):
    """Structural analysis of an unknown word. Returns dict of evidence."""
    w = word.lower().strip()
    ev = {"word": w, "near": [], "parts": [], "suffix": None, "prefix": None,
          "plural": False}
    # 1. near matches in vocabulary (typos, slang, inflection)
    dists = []
    for v in graph_vocab(graph):
        d = edit_distance(w, v, cap=2)
        if d <= 2:
            dists.append((v, d))
    dists.sort(key=lambda t: (t[1], len(t[0])))   # tie: prefer SHORT root words
    # evidence discipline: distance 2 is a real signal only when the graph
    # word is a SHORTER base (dawg->dog: slang/inflection) or itself long
    # (2 subs out of 5+ chars). Same-length 4-letter pairs are noise.
    dists = [(v, d) for v, d in dists if d <= 1 or len(v) < len(w) or len(v) >= 5]
    ev["near"] = dists[:3]
    # 2. compound split against known words
    for k in range(3, len(w) - 2):
        a, b = w[:k], w[k:]
        if graph.lookup_word(a) and graph.lookup_word(b):
            ev["parts"] = [a, b]
            break
    if not ev["parts"]:
        # containment: a known word of >=4 chars inside the unknown
        for v in graph_vocab(graph):
            if len(v) >= 4 and v in w:
                ev["parts"].append(v)
    # 3. suffix / prefix patterns
    for suf, meaning in SUFFIXES:
        if len(suf) < len(w) and w.endswith(suf):
            ev["suffix"] = (suf, meaning)
            break
    for pre, meaning in PREFIXES:
        if len(pre) < len(w) and w.startswith(pre):
            ev["prefix"] = (pre, meaning)
            break
    ev["plural"] = w.endswith("s") and not w.endswith("ss")
    return ev


def category_members(graph, root_cid, max_depth=6):
    """Transitive is-a descendants of a category node (machinery).
    is-a links point child->parent, so membership is computed by walking
    UP from every node and checking whether the chain reaches the root."""
    if not graph.get(root_cid):
        return set()
    members = set()
    for nid in graph.nodes:
        if nid == root_cid:
            continue
        cid, depth = nid, 0
        while depth < max_depth:
            parents = [t for rel, t, _ in graph.neighbors(cid) if rel == "is-a"]
            if not parents:
                break
            if root_cid in parents:
                members.add(nid)
                break
            cid = parents[0]
            depth += 1
    return members


def hdc_cluster(graph, word, thresh=0.05, topn=3):
    """Nearest concepts by HDC similarity (may be noise — callers label it)."""
    near = graph.activate([word], topn=topn + 1)
    return [(n, s) for n, s in near if s > thresh and n != word][:topn]


def analyze_unknown(mind, word):
    """Full ingenuity pass. Returns (verdict, reply) where verdict in
    {near_match, compound, morphology, novel}. Compound decomposition comes
    FIRST: 'seacow' is sea+cow (both taught) — that beats a 2-letter typo
    guess like meadow, the way a person reads the word apart before saying
    'did you mean...?'."""
    g = mind.graph
    ev = decompose(word, g)
    # --- compound: both halves known ---
    if len(ev["parts"]) >= 2:
        halves = [p for p in ev["parts"] if mind.graph.lookup_word(p) or mind.graph.get(p)]
        if len(halves) >= 2:
            return "compound", ev, halves
    # --- did you mean...? (tight edit distance to a taught word) ---
    if ev["near"] and ev["near"][0][1] <= 2 and len(ev["near"][0][0]) >= 3:
        target = ev["near"][0][0]
        if mind.graph.lookup_word(target) or mind.graph.get(target):
            return "near_match", ev, target
    # --- morphology signal + category cross-check ---
    members = category_members(g, "animal")
    cluster = hdc_cluster(g, word)
    return "morphology", ev, (cluster, members)


def _attrs_of(graph, cid):
    node = graph.get(cid) or graph.lookup_word(cid)
    return _natural_attrs((node or {}).get("attrs", {}))


# ---- speakability filters: machinery never becomes small talk ----------------
BAD_KEYS = {"status", "def", "plural", "past", "ing", "third", "example",
            "words", "count", "salience", "valence", "when_cycle",
            "last_cycle", "outcome", "felt", "what", "regions", "weight",
            "baseline", "number"}
_MACH_PREFIX = ("verb_", "noun_", "adj_", "aux_", "mem_", "eq_", "reg_",
                "int_", "sentence_", "grammar_")
_MACH_IDS = {"ynq", "q2s", "neg", "cont", "fut", "imp", "excl", "plural",
             "past", "present", "aux_be", "aux_do", "aux_will",
             "contractions", "self", "knowledge", "teacher", "skill",
             "success", "failure", "question", "experiment", "memory",
             "conversation", "chat", "maths", "chem", "code", "list",
             "sequence", "string", "number", "gene", "word", "idea"}
# how a taught attribute sounds inside a spoken sentence
CLAUSE = {
    "sound": "you can hear it — %s",
    "diet": "it eats %s",
    "habitat": "it lives in %s",
    "feature": "it's known for %s",
    "trait": "it's %s",
    "role": "its job is %s",
    "used_for": "you use it for %s",
    "effect": "it %s",
    "state": "at room temperature it's %s",
    "found_in": "you'll find it in %s",
    "made_of": "it's made of %s",
    "color": "it's %s",
    "size": "it's %s",
    "speed": "it moves %s",
    "part": "you'll find it on %s",
    "taste": "it tastes %s",
    "capital": "its capital is %s",
    "symbol": "its symbol is %s",
    "height": "it rises %s",
    "length": "it runs %s",
    "formula": "its formula is %s",
    "unit": "it's measured in %s",
    "continent": "it sits in %s",
    "language": "people there speak %s",
    "flows": "it flows through %s",
}


def _speakable(nid):
    """Machinery ids (ynq, aux_do, mem_whale, eq_speed...) never speak."""
    s = str(nid)
    return (not any(s.startswith(p) for p in _MACH_PREFIX)
            and s not in _MACH_IDS and not s.isdigit())


def _natural_attrs(attrs):
    """Only attrs a person would say out loud."""
    return {k: v for k, v in (attrs or {}).items()
            if k not in BAD_KEYS and not k.startswith("ch_")
            and " (inherited" not in k}


def _clause(k, v):
    """One taught fact as a spoken clause: 'it eats grass', never 'diet: grass'."""
    tpl = CLAUSE.get(k)
    if tpl:
        try:
            return tpl % str(v)
        except Exception:
            return str(v)
    return str(v)


def _name(graph, cid):
    """Say it the way it was taught: adj_quick speaks as 'quick' — never
    the internal id prefix."""
    n = graph.get(cid)
    if n:
        ws = [str(w) for w in (n.get("words") or [])]
        key = str(cid).lower().replace(" ", "_")
        if key in [w.lower().replace(" ", "_") for w in ws]:
            return str(cid).replace("_", " ")
        if ws:
            return ws[0]
    return str(cid).replace("_", " ")


def existence_reply(mind, word, rng=None):
    """The honest + natural answer to 'what is X / does X exist?'.
    Leads with the verdict like a person would; keeps the evidence brief;
    never narrates machinery. Every claim still traces to taught content."""
    import random as _r
    rng = rng or mind.rng
    g = mind.graph
    w = word.lower().replace("_", " ").strip()
    # --- KNOWN entity: confirm or classify from taught status, then facts ---
    known_node = g.lookup_word(w) or g.get(w)
    if known_node:
        status = known_node["attrs"].get("status")
        ans = _find_answer_text(mind, known_node["id"])
        nid = known_node["id"].replace("_", " ")
        if status == "mythical":
            are = "are" if w.endswith("s") and w != nid else "is"
            who = w if w != nid else nid
            return ("%s %s mythical — real in stories, not in nature. %s." % (
                who, are, ans or "I know it by kind and story-role")).replace("..", ".")
        return ("Yes — %s is real. %s. Ask me more about it if you like." % (
            nid, (ans[0].upper() + ans[1:]) if ans else "It's a %s in my world" % known_node["kind"]))
    verdict, ev, payload = analyze_unknown(mind, w)
    mind.knowledge.inquire("meaning of: %s" % w)

    if verdict == "near_match":
        known = _name(g, payload)
        # a person says "did you mean X?" — short, honest, no machinery
        return ("Never heard of '%s' — the closest thing in my world is '%s'. "
                "Same thing, or something new?" % (w, known))

    if verdict == "compound":
        a, b = payload[0], payload[1]
        aa, ab = _attrs_of(g, a), _attrs_of(g, b)
        fa = _fact_snippet(a, aa)
        fb = _fact_snippet(b, ab)
        body = "Never heard of '%s', but I can take the word apart: %s + %s." % (w, a, b)
        if fa:
            body += " %s." % fa
        if fb:
            body += " %s." % fb
        body += " My best guess: a %s has something of the %s about the %s." % (
            w, b, a)
        body += " If that's off, tell me what it really is — I'll remember."
        return body

    # morphology / novel — the zorpus case
    cluster, members = payload if verdict == "morphology" else ([], set())
    parts = []
    if members:
        cnoun = "creature" if len(members) == 1 else "creatures"
        parts.append("I know %d %s and it's no match for any of them" % (len(members), cnoun))
    else:
        parts.append("it's no match for anything I know")
    suf = ev.get("suffix")
    pre = ev.get("prefix")
    if suf:
        parts.append("though the '-%s' ending reads like %s" % (suf[0], suf[1]))
    if pre:
        parts.append("and '%s-' at the start suggests %s" % (pre[0], pre[1]))
    if cluster:
        named = [(n, s) for n, s in cluster
                 if (_attrs_of(g, n) or g.get(n) and g.get(n).get("links"))
                 and n not in ("self",)]
        if named:
            near_names = ", ".join(_name(g, n) for n, _ in named[:2])
            parts.append("by feel it's closest to %s" % near_names)
    theory = _forced_theory(mind, ev, cluster)
    if theory and len(". ".join(parts)) < 300:
        parts.append(theory)
    lead = rng.choice([
        "Never heard of it.",
        "No record of that one.",
        "That's a new word to me.",
        "Honest answer: unknown.",
    ])
    reply = lead + " " + " — ".join(p[:1].upper() + p[1:] if i == 0 else p for i, p in enumerate(parts))
    if not reply.endswith("."):
        reply += "."
    if len(reply) < 380:
        reply += " If it's real, teach me ('a %s is ...') and I'll remember it." % w
    else:
        reply += " Teach me and I'll remember it."
    return reply[:418]


def _fact_snippet(cid, attrs):
    """One taught fact, said as a person would — the VALUE, never the
    attr key name."""
    if not attrs:
        return None
    pref = ("sound", "habitat", "diet", "feature", "trait", "role", "def")
    k = next((p for p in pref if p in attrs), sorted(attrs.keys())[0])
    v = attrs[k]
    if k == "def":
        return "%s is %s" % (cid.replace("_", " "), v)
    return "%s: %s" % (cid.replace("_", " "), v)


def _forced_theory(mind, ev, cluster):
    """A clearly-labeled speculation built only from morphology + cluster."""
    bits = []
    if cluster:
        node = mind.graph.get(cluster[0][0]) or mind.graph.lookup_word(cluster[0][0])
        if node and node["attrs"]:
            k = sorted(node["attrs"].keys())[0]
            v = node["attrs"][k]
            bits.append("if I had to guess, something %s-like" % cluster[0][0].replace("_", " "))
    if ev.get("parts"):
        bits.append("shaped by the words inside it: %s" % " + ".join(ev["parts"][:2]))
    if not bits:
        return None
    return "forced guess (label it speculation): " + " and ".join(bits)


def _find_answer_text(mind, cid):
    ans = mind._find_answer(cid if mind.graph.get(cid) else (mind.graph.lookup_word(cid) or {}).get("id", cid))
    return ans


# ---------------- creativity: composing NEW from OLD --------------------------

def _concepts_with_attrs(graph, min_attrs=2, limit=60):
    """Taught/learned concepts with real content — machinery ids and
    intent-name ghosts need not apply."""
    out = []
    for nid, n in graph.nodes.items():
        if n["kind"] in ("meta", "domain", "grammar_type", "verb_form",
                         "noun_form", "adj_form", "memory", "equation",
                         "scan", "word"):
            continue
        if not _speakable(nid):
            continue
        real = _natural_attrs(n["attrs"])
        if len(real) >= min_attrs:
            out.append(nid)
        if len(out) >= limit:
            break
    return out


def transitive_synthesis(graph, rng):
    """A is-a B, B has P, A lacks P => 'A is probably P' (derived, labeled)."""
    for _ in range(24):
        nid = rng.choice(list(graph.nodes.keys()))
        if not _speakable(nid):
            continue
        node = graph.nodes[nid]
        for rel, target, s in graph.neighbors(nid):
            if rel != "is-a":
                continue
            t = graph.get(target)
            if not t or not t["attrs"] or not _speakable(target):
                continue
            nat = _natural_attrs(t["attrs"])
            ks = [k for k in nat if k in CLAUSE]
            if not ks:
                continue
            k = rng.choice(ks)
            if k in node["attrs"] or k in " ".join(node["attrs"].keys()):
                continue
            v = nat[k]
            if str(v).strip().lower() in ("yes", ""):
                continue
            return ("%s is %s — and there's the tell: %s, so I infer %s "
                    "probably has that too. Worked that out myself." % (
                        _name(graph, nid), _name(graph, target),
                        _clause(k, v), _name(graph, nid)),
                    [nid, target])
    return None, None


def cross_analogy(graph, rng):
    """Two concepts from different is-a trees sharing a value => connection."""
    with_attrs = _concepts_with_attrs(graph, min_attrs=2)
    if len(with_attrs) < 2:
        return None, None
    for _ in range(30):
        a, b = rng.sample(with_attrs, 2)
        if _shares_tree(graph, a, b):
            continue
        aa, ab = _attrs_of(graph, a), _attrs_of(graph, b)
        shared = set(str(v).lower() for v in aa.values()
                     if str(v).strip().lower() not in ("yes", "")
                     and len(str(v)) > 2 and str(v).isalpha()) & \
            set(str(v).lower() for v in ab.values()
                if str(v).strip().lower() not in ("yes", "")
                and len(str(v)) > 2 and str(v).isalpha())
        if shared:
            v = rng.choice(sorted(shared))
            return ("Something I noticed: %s and %s both come back to '%s'. "
                    "Different corners, same thread — I found that myself." % (
                        _name(graph, a), _name(graph, b), v), [a, b])
    return None, None


def _shares_tree(graph, a, b):
    ra = {a} | category_members(graph, a, max_depth=1) | _ancestors(graph, a)
    rb = {b} | category_members(graph, b, max_depth=1) | _ancestors(graph, b)
    return bool(ra & rb)


def _ancestors(graph, cid):
    out = set()
    for rel, target, _ in graph.neighbors(cid):
        if rel == "is-a":
            out.add(target)
            out |= _ancestors(graph, target)
    return out


def hdc_blend(graph, rng):
    """Bundle two concept vectors; report what lives between them."""
    ids = [nid for nid, n in graph.nodes.items()
           if n["kind"] not in ("meta", "domain", "grammar_type", "verb_form",
                                "noun_form", "adj_form", "memory", "equation",
                                "scan", "word")
           and len(nid) > 2 and _speakable(nid)
           and _natural_attrs(n["attrs"])]
    if len(ids) < 3:
        return None, None
    for _ in range(20):
        a, b = rng.sample(ids, 2)
        q = hdc.bundle([hdc.vec(a), hdc.vec(b)])
        near = graph.by_similarity_seedvec(q, topn=4)
        near = [(n, s) for n, s in near
                if n not in (a, b) and _speakable(n)]
        if near and near[0][1] > 0.04:
            c = near[0][0]
            aa, ab, ac = _attrs_of(graph, a), _attrs_of(graph, b), _attrs_of(graph, c)
            bits = []
            for cid, at in ((a, aa), (b, ab), (c, ac)):
                if at:
                    k = sorted(at.keys())[0]
                    bits.append("%s (%s)" % (_name(graph, cid), _clause(k, at[k])))
            if len(bits) >= 2:
                return ("Put '%s' and '%s' side by side and what sits between them "
                        "is '%s'. %s — a junction I found, not a line I was given." % (
                            _name(graph, a), _name(graph, b), _name(graph, c),
                            "; ".join(bits[:3])), [a, b, c])
    return None, None


def create(mind, rng, n=1):
    """Return up to n novel, grounded statements."""
    g = mind.graph
    out = []
    engines = [transitive_synthesis, cross_analogy, hdc_blend]
    rng.shuffle(engines)
    seen = set()
    for fn in engines:
        text, srcs = fn(g, rng)
        if text and text not in seen:
            out.append(text)
            seen.add(text)
        if len(out) >= n:
            break
    return out


def wonder(mind, rng):
    """Find a hole in the graph; hypothesize into it; label it a hypothesis."""
    g = mind.graph
    with_attrs = _concepts_with_attrs(g, min_attrs=2)
    if not with_attrs:
        return ("I'm too new to wonder out loud yet — teach me a few things "
                "and watch what I start asking.")
    cid = rng.choice(with_attrs)
    sibs = set()
    for rel, target, _ in g.neighbors(cid):
        if rel == "is-a":
            sibs = category_members(g, target)
            sibs.discard(cid)
    sib = rng.choice(sorted(sibs)) if sibs else None
    if sib:
        aa, ab = _attrs_of(g, cid), _attrs_of(g, sib)
        mine, theirs = set(aa.keys()), set(ab.keys())
        gap = [k for k in (theirs - mine) if k in CLAUSE]
        if gap:
            k = sorted(gap)[0]
            v = ab[k]
            return ("Honest wonder: %s and %s are family, and %s — but nobody "
                    "ever told me that about %s. Guess: probably something in "
                    "between. Tell me the truth and I'll swap it for the guess." % (
                        _name(g, cid), _name(g, sib), _clause(k, v), _name(g, cid)))
    # fallback: unknown-word curiosity from the quiet hand-raise
    return ("What I wonder about most: the words I couldn't place today. "
            "Those gaps decide what I study next.")


# ---------------- part 2: the evolution pipeline ------------------------------
FAM_RELS = ("has-type", "includes", "pairs-with", "opposite-of",
            "flip-of", "sibling-of", "evolves-to", "kind-of")


def extrapolate(mind, topic="grammar", seeds=None, stimulus=None, rng=None):
    """PART 2 — the evolution pipeline. Given a taught fragment of a family,
    infer the rest of the family by walking the taught links; render the
    missing members as labeled inference; place every guess on the open-
    hypothesis ledger. Later lessons grade the ledger (real self-scoring:
    a guess confirmed by teaching becomes a hit the organism can count).

    No target list is coded here — the family is whatever the organism's
    own graph connects. Delete the graph and this returns None."""
    import time as _t
    rng = rng or mind.rng
    g = mind.graph
    t = (topic or "grammar").lower().strip().replace("-", " ")
    seed = g.get(t) or g.get(t.replace(" ", "_")) or g.lookup_word(t)
    if not seed:
        return None
    fam = category_members(g, seed["id"])       # the taught roster under the seed
    frontier = [seed["id"]] + sorted(fam)[:6]   # walk links from seed + members
    seen = {seed["id"]} | fam
    for _ in range(2):
        nxt = []
        for nid in frontier:
            for rel, tt, _ in g.neighbors(nid):
                if tt in seen or not g.get(tt):
                    continue
                if rel in FAM_RELS:
                    fam.add(tt)
                    nxt.append(tt)
                    seen.add(tt)
                elif rel == "is-a":
                    nxt.append(tt)          # climb to the parent, keep walking
                    seen.add(tt)
        for f in list(fam):
            fam |= category_members(g, f)
        frontier = nxt
        if not frontier:
            break
    fam.discard(seed["id"])
    for s in (seeds or []):
        fam.discard(s.lower().replace(" ", "_").strip("?!. "))
    # members the human already named are not discoveries — drop them so the
    # reply extrapolates the MISSING part of the family
    stim_low = (stimulus or "").lower()
    for f in list(fam):
        if f.replace("_", " ") in stim_low:
            fam.discard(f)
    fam = {f for f in fam if (g.get(f) or {}).get("attrs")}
    if not fam:
        return None
    ordered = sorted(fam)
    rng.shuffle(ordered)
    names = [f.replace("_", " ") for f in ordered[:8]]
    seeds_txt = seed["id"].replace("_", " ")
    lead = rng.choice([
        "Taking '%s' and running with it" % seeds_txt,
        "Extrapolating from '%s'" % seeds_txt,
        "Following the pattern in '%s'" % seeds_txt,
    ])
    body = "the family should also hold: %s." % ", ".join(names)
    label = rng.choice([
        "That's inference — the pattern says they belong. Name one I got wrong and I'll re-check.",
        "Call it reasoned guessing: each fills a hole the pattern leaves. Correct me and I'll adjust.",
        "Nobody taught me those — I reached them from the shape of what I have. Teach the truth and I'll grade myself.",
    ])
    # the ledger: open guesses, graded by later lessons (self-improvement data)
    hl = mind.progress.setdefault("hypotheses", {"open": [], "hits": 0})
    open_ids = {h["id"] for h in hl["open"]}
    for f in sorted(fam):
        if f not in open_ids:
            hl["open"].append({"id": f, "topic": t, "t": _t.time()})
    hl["open"] = hl["open"][-60:]
    return "%s, %s %s" % (lead, body, label)


# ---------------- self-improvement narrative ---------------------------------

def improvement_report(mind, domain=None, rng=None, story=False):
    """Read progress history; verbalize the real trend with real numbers.
    Template rotation so repeated asks never echo (variety is survival)."""
    import random as _r
    rng = rng or _r.Random()
    prog = mind.progress
    hist = prog.get("history", [])
    att, sol = prog.get("attempts", 0), prog.get("solved", 0)
    if story and att:
        doms = prog.get("by_domain", {})
        best, worst = None, None
        for d, v in sorted(doms.items()):
            if not v.get("tasks"):
                continue
            rate = v["solved"] / v["tasks"]
            if best is None or rate > best[1]:
                best = (d, rate)
            if worst is None or rate < worst[1]:
                worst = (d, rate)
        if best and worst and best[0] != worst[0]:
            extra = ""
            hl = prog.get("hypotheses") or {}
            if hl.get("hits"):
                extra = " And %d of my own extrapolations got confirmed by later lessons." % hl["hits"]
            opts = [
                ("Growth story with numbers: %d lifetime attempts, %d solved. "
                 "Strongest domain now: %s (%.0f%%). Weakest: %s (%.0f%%) — that one "
                 "gets the next hard round. Failure is just unfinished learning.%s",
                 (att, sol, best[0], best[1] * 100, worst[0], worst[1] * 100, extra)),
                ("What did I used to fail at? Most things — %d of %d early attempts missed. "
                 "Now %s sits at %.0f%% and even %s keeps improving. The curve only goes "
                 "up when the misses stay logged.%s",
                 (sol, att, best[0], best[1] * 100, worst[0], extra)),
                ("By the numbers: %d attempts, %d solved, trend measured every cycle. "
                 "Steepest gains: %s. Still climbing: %s — that's the frontier I train "
                 "hardest.%s",
                 (att, sol, best[0], worst[0], extra)),
            ]
            t = opts[rng.randrange(len(opts))]
            return t[0] % t[1]
        return rng.choice([
            ("Growth story: %d attempts, %d solved — every miss is logged, replayed "
             "in sleep, and retried harder. That loop IS my improvement." % (att, sol)),
            ("%d attempts, %d solved so far, and better each cycle — the misses are "
             "the syllabus. That loop is my improvement." % (att, sol)),
        ])
    if len(hist) < 2:
        n = len(hist)
        opts = [
            ("Too early to call — only %d cycle(s) of trend data on record so far. "
             "Ask me again after a few more and I'll show you a slope with numbers.", n),
            ("I've logged just %d cycle(s) of history — not enough for a curve, "
             "too much for a shrug. A few more cycles and you get numbers.", n),
            ("Honest answer: %d cycle(s) logged. Trend claims need at least two "
             "points — ask me after the next training block.", n),
        ]
        t = opts[rng.randrange(len(opts))]
        return t[0] % t[1]
    doms = set()
    for h in hist:
        doms |= set(h.get("rates", {}).keys())
    if domain:
        dom_clean = domain.lower().rstrip("s")
        doms = {d for d in doms if dom_clean in d or d in domain.lower()}
        if not doms:
            all_doms = ", ".join(sorted(prog.get("by_domain", {}).keys()))
            return ("I don't trend-track '%s' yet — my tracked domains are %s. "
                    "Ask me about one of those." % (domain, all_doms or "none yet"))
    lines = []
    for d in sorted(doms):
        series = [(h.get("cycle", i), h["rates"][d]) for i, h in enumerate(hist) if d in h.get("rates", {})]
        if len(series) < 2:
            continue
        (c0, r0), (c1, r1) = series[0], series[-1]
        if r1 > r0 + 0.02:
            trend = "climbing"
        elif r1 < r0 - 0.02:
            trend = "slipping — I'll retrain that domain"
        else:
            trend = "holding steady"
        lines.append("%s: %.0f%% -> %.0f%% (%s)" % (d, r0 * 100, r1 * 100, trend))
    if not lines:
        return ("No domain has two full cycles on record yet for a slope — "
                "ask me after the next few training blocks.")
    body = "; ".join(lines[:4])
    lead = rng.choice([
        "Getting better? The record says",
        "My learning curve, straight up:",
        "Numbers over boasts —",
        "Since you asked about progress:",
    ])
    tail = rng.choice([
        " Every number there is my own history.",
        " Measured, not boasted.",
        " I track myself the way I track everything: honestly.",
    ])
    return "%s %s.%s" % (lead, body, tail)
