"""Chemistry task world — reactions and symbols as memory routes.

The taught lesson (curriculum/science-chem.json) carries elements with
symbols and reactions with reactants->product. The environment grades
pass/fail; the organism answers from ITS OWN graph: element nodes carry
a "symbol" attr, reaction nodes carry "reactants" and "product".
Nothing here opens the lesson file on the organism's behalf.
"""
import json
import os
import re

from . import dsl, genome

_LESSON = None


def _lesson():
    global _LESSON
    if _LESSON is not None:
        return _LESSON
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "curriculum", "science-chem.json")
    els, rxns, comps = [], [], []
    try:
        with open(path) as fh:
            pack = json.load(fh)
        for c in pack.get("concepts", []):
            a = c.get("attrs") or {}
            if c.get("kind") == "element" and a.get("symbol"):
                els.append({"id": c["id"], "symbol": a["symbol"], "attrs": a,
                            "words": c.get("words", []) or [c["id"]]})
            elif c.get("kind") == "reaction" and a.get("reactants") and a.get("product"):
                rxns.append({"id": c["id"], "reactants": a["reactants"],
                             "product": a["product"], "attrs": a,
                             "words": c.get("words", []) or [c["id"]]})
            elif c.get("id") and a.get("formula"):
                comps.append({"id": c["id"], "formula": a["formula"], "attrs": a,
                              "words": c.get("words", []) or [c["id"]]})
    except Exception:
        pass
    _LESSON = (els, rxns, comps)
    return _LESSON


def gen_chem_task(rng, tier=1):
    """Three shapes: symbol of an element, product of a reaction, formula
    of a compound. Tier 3+ mixes in the harder recall routes."""
    els, rxns, comps = _lesson()
    kinds = ["symbol", "react"] if tier < 3 else ["symbol", "react", "formula"]
    kind = rng.choice(kinds)
    if kind == "symbol" and els:
        e = rng.choice(els)
        return {"domain": "chem", "kind": "symbol", "input": "symbol %s" % e["id"],
                "expected": e["symbol"], "prompt": "symbol of %s" % e["id"]}
    if kind == "react" and rxns:
        r = rng.choice(rxns)
        terms = [t.strip() for t in r["reactants"].split("+")]
        return {"domain": "chem", "kind": "react",
                "input": "react %s" % " and ".join(terms),
                "expected": r["product"], "prompt": "%s -> ?" % r["reactants"]}
    if kind == "formula" and comps:
        c = rng.choice(comps)
        return {"domain": "chem", "kind": "formula",
                "input": "formula %s" % (c["words"][0] if c["words"] else c["id"]),
                "expected": c["formula"], "prompt": "formula of %s" % c["id"]}
    return None


# ---------------- the organism's ops (memory routes) --------------------------
def _node_for(word):
    g = dsl._GRAPH
    if g is None:
        raise LookupError("no graph wired")
    key = str(word).lower().strip().replace(" ", "_")
    node = g.get(key) or g.lookup_word(str(word).lower().strip())
    if not node:
        raise LookupError("not taught: %r" % word)
    return node


@dsl.op("chem_symbol")
def _chem_symbol(x, args):
    """x = 'symbol oxygen' -> 'O', read from the organism's own memory."""
    toks = str(x).split()
    if len(toks) < 2:
        raise ValueError("no element named")
    node = _node_for(toks[1])
    sym = (node.get("attrs") or {}).get("symbol")
    if not sym:
        raise LookupError("no taught symbol for %r" % toks[1])
    return sym


@dsl.op("chem_react")
def _chem_react(x, args):
    """x = 'react hydrogen and oxygen' -> scan the organism's taught
    reactions for one whose reactants cover the named terms; answer its
    product. Reaction knowledge lives only in the graph."""
    body = re.sub(r"^react\s+", "", str(x).strip().lower())
    terms = [t for t in re.split(r"\s+and\s+|\+", body) if t.strip()]
    want = set(t.strip().replace(" ", "_") for t in terms)
    g = dsl._GRAPH
    best, best_n = None, 0
    for n in g.nodes.values():
        a = n.get("attrs") or {}
        if not a.get("reactants") or not a.get("product"):
            continue
        have = set(t.strip().replace(" ", "_")
                   for t in a["reactants"].lower().split("+"))
        if want and want.issubset(have) and len(have) > best_n:
            best, best_n = a["product"], len(have)
    if not best:
        raise LookupError("no taught reaction for %s" % " + ".join(terms))
    return best


@dsl.op("chem_formula")
def _chem_formula(x, args):
    """x = 'formula water' -> the taught formula attr."""
    toks = str(x).split()
    if len(toks) < 2:
        raise ValueError("no compound named")
    node = _node_for(toks[1])
    f = (node.get("attrs") or {}).get("formula")
    if not f:
        raise LookupError("no taught formula for %r" % toks[1])
    return f


def chem_pipeline_candidates(rng, task, known_genes):
    kind = task.get("kind", "symbol")
    routes = {"symbol": ["chem_symbol", "chem_formula"],
              "react": ["chem_react"],
              "formula": ["chem_formula", "chem_symbol"]}
    cands = [[{"op": op, "args": {}}] for op in routes.get(kind, [])]
    cands.append([{"op": "identity", "args": {}}])
    for g in known_genes:
        if g.get("domain") == "chem" and g.get("steps"):
            cands.append(g["steps"])
    for _ in range(2):
        cands.append(genome.random_gene(rng, "chem")["steps"])
    seen, out = set(), []
    for s in cands:
        k = json.dumps(s, sort_keys=True)
        if k not in seen:
            seen.add(k)
            out.append(s)
    return out
