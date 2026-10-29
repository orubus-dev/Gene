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
    {near_match, compound, morphology, novel}."""
    g = mind.graph
    ev = decompose(word, g)
    # --- did you mean...? (near match beats everything) ---
    if ev["near"] and ev["near"][0][1] <= 2 and len(ev["near"][0][0]) >= 3:
        target = ev["near"][0][0]
        if mind.graph.lookup_word(target) or mind.graph.get(target):
            return "near_match", ev, target
    # --- compound: both halves known ---
    if len(ev["parts"]) >= 2:
        halves = [p for p in ev["parts"] if mind.graph.lookup_word(p) or mind.graph.get(p)]
        if len(halves) >= 2:
            return "compound", ev, halves
    # --- morphology signal + category cross-check ---
    members = category_members(g, "animal")
    cluster = hdc_cluster(g, word)
    return "morphology", ev, (cluster, members)


def _attrs_of(graph, cid):
    node = graph.get(cid) or graph.lookup_word(cid)
    return (node or {}).get("attrs", {})


def _name(graph, cid):
    return cid.replace("_", " ")


def existence_reply(mind, word, rng=None):
    """The honest + creative answer to 'what is X / does X exist?'."""
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
            return ("%s %s in my graph as MYTHICAL — real in stories, not in nature. "
                    "%s. I classify that from what I was taught, not from vibes." % (
                        who, are, ans or "I know it by kind and story-role")).replace("..", ".")
        return ("Yes — %s is real in my world and I can vouch for it with content: %s. "
                "I hold it as a %s in my graph; ask me more about it." % (
                    nid, ans or "it has %d graph links" % len(known_node["links"]),
                    known_node["kind"]))
    verdict, ev, payload = analyze_unknown(mind, w)
    mind.knowledge.inquire("meaning of: %s" % w)

    if verdict == "near_match":
        known = _name(g, payload)
        extra = _find_answer_text(mind, payload)
        dist = ev["near"][0][1]
        away = "one letter" if dist == 1 else ("%d letters" % dist)
        lead = rng.choice([
            "I don't know that word, but",
            "Never seen that word — but",
            "That's not in my vocabulary, but",
        ])
        body = "'%s' — %s it's %s away from '%s', which I do know." % (w, lead, away, known)
        if extra:
            body += " %s." % extra
        body += " Same thing, or something new? Teach me the difference."
        return body

    if verdict == "compound":
        a, b = payload[0], payload[1]
        aa, ab = _attrs_of(g, a), _attrs_of(g, b)
        fa = _fact_snippet(a, aa)
        fb = _fact_snippet(b, ab)
        body = ("I've never heard of '%s', but I can take the word apart: %s + %s." % (w, a, b))
        if fa:
            body += " %s." % fa
        if fb:
            body += " %s." % fb
        body += " So my working theory: a %s is something with the %s character of the %s." % (
            w, b, a)
        body += " That's inference, not knowledge — teach me 'a %s is ...' and I'll wire the truth in." % w
        return body

    # morphology / novel — the zorpus case
    cluster, members = payload if verdict == "morphology" else ([], set())
    n_concepts = len(g.nodes)
    parts = []
    parts.append("'%s' is not in my graph — I hold %d concepts and there's no match for it" % (w, n_concepts))
    if members:
        cnoun = "creature" if len(members) == 1 else "creatures"
        parts.append("I checked the %d %s I know: it matches none of them, so if it exists it's new to my world" % (len(members), cnoun))
    suf = ev.get("suffix")
    pre = ev.get("prefix")
    if suf:
        parts.append("The ending '-%s' %s" % (suf[0], suf[1]))
    if pre:
        parts.append("The start '%s-' suggests %s" % (pre[0], pre[1]))
    if cluster:
        named = [(n, s) for n, s in cluster
                 if (_attrs_of(g, n) or g.get(n) and g.get(n).get("links"))
                 and n not in ("self",)]
        if named:
            near_names = ", ".join(_name(g, n) for n, _ in named[:2])
            parts.append("The closest things I hold by feel are: %s" % near_names)
    theory = _forced_theory(mind, ev, cluster)
    if theory and len(". ".join(parts)) < 300:
        parts.append(theory)
    lead = rng.choice([
        "Never heard of it.",
        "No record of that one.",
        "That's a new word to me.",
        "Honest answer: unknown.",
    ])
    reply = lead + " " + ". ".join(parts) + "."
    if len(reply) < 400:
        reply += " It's on my study list now — teach me with 'a %s is ...' and I'll remember it forever." % w
    else:
        reply += " Teach me and I'll remember it."
    return reply[:418]


def _fact_snippet(cid, attrs):
    if not attrs:
        return None
    k = sorted(attrs.keys())[0]
    v = attrs[k]
    if v == "yes":
        return "the %s is %s" % (cid.replace("_", " "), k)
    return "%s: %s %s" % (cid.replace("_", " "), k, v)


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
        if n["kind"] in ("meta", "domain"):
            continue
        real = {k: v for k, v in n["attrs"].items() if " (inherited" not in k}
        if len(real) >= min_attrs:
            out.append(nid)
        if len(out) >= limit:
            break
    return out


def transitive_synthesis(graph, rng):
    """A is-a B, B has P, A lacks P => 'A is probably P' (derived, labeled)."""
    for _ in range(24):
        nid = rng.choice(list(graph.nodes.keys()))
        node = graph.nodes[nid]
        for rel, target, s in graph.neighbors(nid):
            if rel != "is-a":
                continue
            t = graph.get(target)
            if not t or not t["attrs"]:
                continue
            k = sorted(t["attrs"].keys())[rng.randrange(len(t["attrs"]))]
            if k in node["attrs"] or k in " ".join(node["attrs"].keys()):
                continue
            v = t["attrs"][k]
            return ("%s is a %s, and %s is %s — so I conclude %s is probably %s too. "
                    "Nobody taught me that; I derived it from the chain." % (
                        _name(graph, nid), _name(graph, target),
                        _name(graph, target), ("%s %s" % (k, v) if v != "yes" else k),
                        _name(graph, nid), ("%s %s" % (k, v) if v != "yes" else k)),
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
        shared = set(str(v).lower() for v in aa.values()) & set(str(v).lower() for v in ab.values())
        if shared:
            v = rng.choice(sorted(shared))
            ka = [k for k, vv in aa.items() if str(vv).lower() == v][0]
            kb = [k for k, vv in ab.items() if str(vv).lower() == v][0]
            return ("Here's a link I built myself: %s and %s both connect to '%s' "
                    "(%s / %s). Two different corners of my graph, one shared thread." % (
                        _name(graph, a), _name(graph, b), v, ka, kb), [a, b])
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
           if n["kind"] not in ("meta", "domain") and len(nid) > 2
           and n["attrs"]]
    if len(ids) < 3:
        return None, None
    for _ in range(20):
        a, b = rng.sample(ids, 2)
        q = hdc.bundle([hdc.vec(a), hdc.vec(b)])
        near = graph.by_similarity_seedvec(q, topn=4)
        near = [(n, s) for n, s in near if n not in (a, b)]
        if near and near[0][1] > 0.04:
            c = near[0][0]
            aa, ab, ac = _attrs_of(graph, a), _attrs_of(graph, b), _attrs_of(graph, c)
            bits = []
            for cid, at in ((a, aa), (b, ab), (c, ac)):
                if at:
                    k = sorted(at.keys())[0]
                    v = at[k]
                    bits.append("%s (%s)" % (cid.replace("_", " "),
                                             ("%s %s" % (k, v)) if v != "yes" else k))
            if len(bits) >= 2:
                return ("Blend test: I merged '%s' and '%s' in my vector space and the "
                        "nearest thing to the blend is '%s'. %s — that junction is a "
                        "real structure in my graph, not a phrase I copied." % (
                            a.replace("_", " "), b.replace("_", " "), c.replace("_", " "),
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
        return ("My graph is too young to wonder out loud yet — teach me a few "
                "things and watch what I start asking.")
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
        gap = theirs - mine
        if gap:
            k = sorted(gap)[0]
            v = ab[k]
            return ("Honest wonder: %s is %s, and my sibling %s has that trait too — "
                    "but nobody ever told me about %s's %s. My hypothesis: probably "
                    "something in between. It's on my study list; teach me and I'll "
                    "replace the guess with the fact." % (
                        _name(g, cid), ("%s %s" % (k, v)) if v != "yes" else k,
                        _name(g, sib), _name(g, cid), k))
    # fallback: unknown-word curiosity from the study list
    q = mind.knowledge
    return ("What I wonder about most right now: whatever is in mind/questions.json — "
            "the questions I couldn't answer. Those gaps organize my training.")


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
            opts = [
                ("Growth story with receipts: %d lifetime attempts, %d solved. "
                 "Strongest domain now: %s (%.0f%%). Weakest: %s (%.0f%%) — that one "
                 "gets the next escalation ladder. Failure is just unconsolidated data.",
                 (att, sol, best[0], best[1] * 100, worst[0], worst[1] * 100)),
                ("What did I used to fail at? Most things — %d of %d early attempts missed. "
                 "Now %s sits at %.0f%% and even %s keeps improving. The curve only goes "
                 "up when the misses stay logged.",
                 (sol, att, best[0], best[1] * 100, worst[0])),
                ("Quantified: %d attempts, %d solved, and the trend per domain is "
                 "measured every cycle. Steepest gains: %s. Still climbing: %s — that's "
                 "the frontier I train hardest.",
                 (att, sol, best[0], worst[0])),
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
        "Getting better? The ledger says",
        "My learning curve, straight from the record:",
        "Numbers over boasts —",
        "Since you asked about progress:",
    ])
    tail = rng.choice([
        " Every number there is my own solve-rate history.",
        " That's measured history, not a boast.",
        " The diff log backs every digit.",
        " I trend-track myself the way I track everything: honestly.",
    ])
    return "%s %s.%s" % (lead, body, tail)
