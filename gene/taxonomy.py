"""The entity database — a taxonomy wired into the concept graph.

Orubus's spec: "another graph — it breaks stuff down to entity, animal,
mammal, ... and so on, and then uses the clues you have given it to
actually form meaningful words."

This module owns ZERO facts. It is the machinery that reads the is-a
spine the organism was taught (entity -> living -> organism -> animal ->
vertebrate -> mammal -> ... -> dog) and:

  1. ancestors   — the full chain from a thing up to entity
  2. describe    — render a thing as natural sentences (chain + taught attrs)
  3. clue_search — match clue words ("barks", "a loyal pet") against the
                   taught entities; rank and return the best with evidence
  4. is_a        — boolean classification along the taught spine
  5. members     — everything under a category (the shelf view)

Delete the graph and every function here returns empty/None — no facts
live in code.
"""
import json
import math
import re

from . import dsl

EXCLUDED_KINDS = {"domain", "meta", "grammar_type", "verb_form", "noun_form",
                  "adj_form", "category", "idea"}
_ENTS_CACHE = {}
_DF_CACHE = {}
# attr keys whose values render as a natural sentence via FRAMES
FRAMES = {
    "sound": "It %s.",
    "diet": "It eats %s.",
    "habitat": "It lives in %s.",
    "feature": "It's known for %s.",
    "trait": "It's %s.",
    "used_for": "You use it for %s.",
    "made_of": "It's made of %s.",
    "taste": "It tastes %s.",
    "role": "It's %s.",
    "size": "It's %s.",
    "part": "You'll find it on %s.",
    "color": "It's %s.",
    "shape": "Its shape is %s.",
    "speed": "It moves %s.",
    "young": "Its young: %s.",
    "def": None,          # category definitions render in the chain sentence
}


def _name(graph_or_id, cid=None):
    """A thing, said the way it was taught: category fish_cat speaks as
    'fish' (its taught word), never as its internal id. The id's own word
    always wins — whale is 'whale', never the plural 'whales'."""
    if cid is None:
        cid = graph_or_id
        graph = None
    else:
        graph = graph_or_id
    key = str(cid).lower().replace(" ", "_")
    if graph is not None:
        node = graph.get(key)
        ws = [(node or {}).get("words")] or []
        if ws:
            ws = list(ws[0] or [])
        if key in [w.lower().replace(" ", "_") for w in ws]:
            return key.replace("_", " ")
        if ws:
            return str(ws[0])
    return str(cid).replace("_", " ")


def ancestors(graph, cid, max_depth=10):
    """Chain from cid upward along is-a links (strongest first): dog ->
    canid -> mammal -> animal -> organism -> living -> entity."""
    chain = []
    cur = cid
    node = graph.get(cur)
    if node is None:
        node = graph.lookup_word(str(cid).replace("_", " "))
        cur = node["id"] if node else None
    for _ in range(max_depth):
        if not cur:
            break
        node = graph.get(cur)
        if not node:
            break
        parents = [t for rel, t, _ in graph.neighbors(cur) if rel == "is-a"]
        if not parents:
            break
        cur = parents[0]
        if cur in chain:
            break
        chain.append(cur)
    return chain


def spine_set(graph):
    """The taught backbone: every category node (entity, living, organism,
    animal, mammal, canid, ...). Categories carry kind 'category' because
    that is how the teacher taught them — this is a lookup, not a walk, and
    concrete things (dog, sofa) are never in it."""
    return {nid for nid, n in graph.nodes.items() if n.get("kind") == "category"}


def entity_nodes(graph, spine=None):
    """Concrete taught entities: have an is-a chain into the spine, carry
    attrs, and aren't categories/machinery themselves. Memoized per graph
    snapshot (nodes only change through teaching)."""
    key = (id(graph), len(graph.nodes))
    if key in _ENTS_CACHE:
        return _ENTS_CACHE[key]
    if spine is None:
        spine = spine_set(graph)
    out = {}
    for nid, n in graph.nodes.items():
        if n.get("kind") in EXCLUDED_KINDS or nid in spine:
            continue
        a = n.get("attrs", {})
        if not a:
            continue
        chain = ancestors(graph, nid)
        if chain and any(c in spine for c in chain):
            out[nid] = n
    _ENTS_CACHE[key] = out
    return out


def is_a(graph, child, parent):
    ch = ancestors(graph, child)
    p = str(parent).lower().strip().replace(" ", "_")
    ids = [c.lower() for c in ch]
    if p in ids:
        return True
    # taught words count too: "is a shark a fish" hits fish_cat via words
    for c in ch:
        node = graph.get(c)
        if node:
            ws = [str(w).lower().replace(" ", "_") for w in (node.get("words") or [])]
            if p in ws:
                return True
    return False


def describe(graph, cid, rng=None, max_sents=3):
    """A thing, said in sentences. Content 100% from the graph: the is-a
    chain gives the class sentence; taught attrs give the detail sentences.
    Returns None when the organism holds nothing describable."""
    node = graph.get(cid) or graph.lookup_word(str(cid).replace("_", " "))
    if not node:
        return None
    nid = node["id"]
    chain = ancestors(graph, nid)
    if not chain:
        return None
    name = _name(graph, nid)
    sents = []
    # class sentence: "A dog is a canid — a mammal." (chain depth <= 3)
    parts = []
    for c in chain[:3]:
        cn = graph.get(c)
        if cn and cn.get("attrs", {}).get("def"):
            parts.append("%s (%s)" % (_name(graph, c), cn["attrs"]["def"]))
            break
        parts.append(_name(graph, c))
    if len(parts) == 1:
        sents.append("A %s is a %s." % (name, parts[0]))
    else:
        sents.append("A %s is a %s." % (name, " — a ".join(parts[:2])))
    # detail sentences from taught attrs, stable order, up to max_sents
    a = node.get("attrs", {})
    for k in sorted(a.keys()):
        if len(sents) >= max_sents:
            break
        frame = FRAMES.get(k)
        v = a[k]
        if not frame or not isinstance(v, str) or not v.strip():
            continue
        if k == "def":
            continue
        s = frame % v.strip()
        if not s.endswith(("!", "?")):
            s = s.rstrip(".") + "."
        sents.append(s)
    return " ".join(sents) if sents else None


def members(graph, cat, max_n=40):
    """Everything taught under a category (mammal -> dogs, cats, whales...).
    Deeper (more specific) things come first."""
    spine = spine_set(graph)
    cat_id = str(cat).lower().strip().replace(" ", "_")
    node = graph.get(cat_id) or graph.lookup_word(str(cat))
    if not node:
        return []
    out = []
    for nid in entity_nodes(graph, spine):
        chain = ancestors(graph, nid)
        if node["id"] in chain:
            out.append((nid, len(chain)))
    out.sort(key=lambda t: -t[1])
    return [nid for nid, _ in out[:max_n]]


def _tokens(s):
    return [w for w in re.findall(r"[a-z']+", str(s).lower()) if len(w) > 1]


def clue_search(graph, clues, topn=3):
    """Match clue phrases against taught entities. A clue hits when its
    tokens overlap the entity's words, attr values, or chain names. Hits are
    weighted by rarity (how few entities carry the token) — 'barks' says
    more than 'the' — and more specific matches (deeper chain) win ties."""
    clue_toks = set()
    for part in re.split(r"[,;]|\band\b", str(clues)):
        clue_toks |= set(_tokens(part))
    if not clue_toks:
        return []
    ents = entity_nodes(graph)
    # rarity: in how many entities does each token appear? (cached per snapshot)
    ckey = (id(graph), len(graph.nodes))
    df, n_total, hays = _DF_CACHE.get(ckey, ({}, max(1, len(ents)), {}))
    if not hays:
        for nid, n in ents.items():
            hay = _entity_hay(graph, nid, n)
            hays[nid] = hay
            for t in set(hay):
                df[t] = df.get(t, 0) + 1
        _DF_CACHE[ckey] = (df, n_total, hays)
    scored = []
    for nid, n in ents.items():
        hits = clue_toks & hays[nid]
        if not hits:
            continue
        depth = len(ancestors(graph, nid))
        w = sum(1.0 + math.log(1.0 + n_total / max(1, df.get(t, 1)))
                for t in hits)
        scored.append((nid, round(w, 3), len(hits), depth))
    scored.sort(key=lambda t: (-t[1], -t[2], -t[3], t[0]))
    return [(nid, hits, depth) for nid, _, hits, depth in scored[:topn]]


def _entity_hay(graph, nid, n):
    """Everything a clue can match against for one entity: words, attrs,
    and the names along its is-a chain."""
    hay = set(_tokens(nid))
    hay |= set(n.get("words") or [])
    for k, v in n.get("attrs", {}).items():
        if k == "status":
            continue
        hay |= set(_tokens(v))
    chain = ancestors(graph, nid)
    for c in chain[:4]:
        hay |= set(_tokens(c))
    return hay


# =============== the taxonomy task world (environment physics) ================
# The environment owns the taught lesson data (public curriculum files) and
# grades parent-questions and clue-guesses pass/fail. The organism answers
# from its own graph through the ops below — never sees the pack.

_TAX_CACHE = None
_ALL_TOKENS = None
CLUE_KEYS = ("sound", "diet", "habitat", "feature", "trait", "role",
             "used_for", "made_of", "taste", "size", "speed")


def _taxonomy_lesson():
    """PUBLIC lesson data: entities, attrs, declared parent — from
    curriculum/taxonomy-*.json + facts_animals.json."""
    global _TAX_CACHE
    if _TAX_CACHE is not None:
        return _TAX_CACHE
    import json
    import os
    ents = []
    cdir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "curriculum")
    for fn in ("taxonomy-1.json", "taxonomy-2.json", "facts_animals.json"):
        try:
            with open(os.path.join(cdir, fn)) as f:
                pack = json.load(f)
        except Exception:
            continue
        for c in pack.get("concepts", []):
            if not c.get("id") or c.get("kind") in ("domain", "meta"):
                continue
            parent = None
            for r in c.get("relations", []) or ():
                if r.get("rel") == "is-a":
                    parent = r.get("to")
                    break
            ents.append({"id": c["id"], "words": c.get("words", []) or [c["id"]],
                         "attrs": c.get("attrs", {}) or {}, "parent": parent})
    _TAX_CACHE = ents
    return ents


def _all_attr_tokens(ents):
    """Union of every entity's attr tokens, computed ONCE. The distinctive
    test per entity becomes: its value tokens minus this set minus its own
    (an entity's own words never make another entity's clue distinctive)."""
    global _ALL_TOKENS
    if _ALL_TOKENS is None:
        toks = set()
        for e in ents:
            for v in e["attrs"].values():
                toks |= set(re.findall(r"[a-z']+", str(v)))
        _ALL_TOKENS = toks
    return _ALL_TOKENS


def gen_taxonomy_task(rng, tier=1):
    """Environment: either 'parent' (what is a X?) or 'clues' (guess the
    entity from taught clues). Expected comes from the lesson pack — the
    organism only ever sees the stimulus and pass/fail."""
    ents = _taxonomy_lesson()
    if not ents:
        return None
    use_clues = tier >= 2 and (rng.random() < 0.55 or tier >= 3)
    if not use_clues:
        e = rng.choice(ents)
        if not e["parent"]:
            return gen_taxonomy_task(rng, tier)
        return {"domain": "taxonomy", "kind": "parent", "input": e["id"],
                "expected": e["parent"].replace("_", " "),
                "prompt": "parent of %s" % e["id"]}
    # clue task: 1 distinctive clue + shared ones, so the answer is unique
    all_toks = _all_attr_tokens(ents)
    for _ in range(20):
        e = rng.choice(ents)
        vals = [str(e["attrs"][k]) for k in CLUE_KEYS if e["attrs"].get(k)]
        own = set(re.findall(r"[a-z']+", e["id"]))
        for v in vals:
            own |= set(re.findall(r"[a-z']+", v))
        others = all_toks - own          # everyone else's attr tokens, O(1)
        distinctive = None
        for v in vals:
            vt = set(re.findall(r"[a-z']+", v))
            if vt and vt - others:
                distinctive = v
                break
        if not vals:
            continue
        clues = []
        if tier >= 3 and distinctive:
            clues.append(distinctive)
        clues.extend(vals[: 2 if tier >= 3 else 3])
        if tier < 3:
            clues.append(e["parent"].replace("_", " ") if e["parent"] else e["id"])
        elif distinctive is None:
            clues.append(e["id"])
        if not clues:
            continue
        return {"domain": "taxonomy", "kind": "clues",
                "input": ", ".join(clues[:4]), "expected": e["id"],
                "prompt": "clues: %s" % ", ".join(clues[:2])}
    return None


# ---------------- the organism's ops (memory routes) --------------------------
@dsl.op("parent_of")
def _parent_of(x, args):
    """The organism's memory: strongest taught is-a parent of a thing."""
    g = dsl._GRAPH
    if g is None:
        raise TypeError("no graph wired")
    key = str(x).lower().strip().replace(" ", "_")
    node = g.get(key) or g.lookup_word(str(x).lower().strip())
    if not node:
        raise LookupError("not taught: %r" % x)
    parents = [t for rel, t, _ in g.neighbors(node["id"]) if rel == "is-a"]
    if not parents:
        raise LookupError("no taught parent for %r" % x)
    return parents[0].replace("_", " ")


@dsl.op("clue_match")
def _clue_match(x, args):
    """The organism's memory: best entity for a clue phrase."""
    g = dsl._GRAPH
    if g is None:
        raise TypeError("no graph wired")
    res = clue_search(g, x, topn=1)
    if not res:
        raise LookupError("no entity matches those clues")
    return res[0][0].replace("_", " ")


def taxonomy_pipeline_candidates(rng, task, known_genes):
    """Hypotheses: the memory route first, decoys and genes after. Which
    route answers which kind is consolidated by trial like everywhere else."""
    kind = task.get("kind", "parent")
    cands = []
    if kind == "parent":
        cands.append([{"op": "parent_of", "args": {}}])
        cands.append([{"op": "lower", "args": {}}])
    else:
        cands.append([{"op": "clue_match", "args": {}}])
        cands.append([{"op": "identity", "args": {}}])
    for g in known_genes:
        if g.get("domain") == "taxonomy" and g.get("steps"):
            cands.append(g["steps"])
    seen, out = set(), []
    for s in cands:
        k = json.dumps(s, sort_keys=True)
        if k not in seen:
            seen.add(k)
            out.append(s)
    return out
