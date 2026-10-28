"""Procedure genes — the organism's DNA for skills.

A gene is a pipeline of innate primitives plus fitness metadata. Skills
are *expressed* genes. Mutation edits steps/args; crossover splices two
genes. Fitness is behavioral: did it work, how fast. Genes that never
fire decay (apoptosis in memory.py).
"""
import itertools
import random

from . import dsl

_gid = itertools.count(1)


def new_gene(steps, name=None, fitness=0.0, uses=0, born=0):
    g = {
        "id": "g%05d" % next(_gid),
        "name": name or dsl.pipeline_to_python(steps),
        "steps": steps,
        "fitness": fitness,
        "uses": uses,
        "born": born,
    }
    return g


def gene_kind(gene, sample_input):
    """Probe which domain a gene handles without exploding."""
    try:
        dsl.execute_pipeline(gene["steps"], sample_input)
        return True
    except Exception:
        return False


# ---- random gene generation (the zygote's noise) ---------------------------
STRING_OPS = ["reverse", "upper", "lower", "words", "first", "last",
              "slice", "concat", "prepend", "wrap", "item", "sort", "join"]
LIST_OPS = ["sumv", "maxv", "minv", "sort", "rsort", "unique", "length",
            "count", "reverse", "first", "last"]
NUM_OPS = ["add", "sub", "mul", "fdiv", "diff", "prod", "sqr"]


def random_gene(rng, domain, length=None):
    length = length or rng.randint(1, 3)
    steps = []
    for _ in range(length):
        steps.append(_random_step(rng, domain))
    return new_gene(steps, born=rng.random())


def _random_step(rng, domain):
    if domain == "string":
        name = rng.choice(STRING_OPS)
    elif domain in ("list", "sequence"):
        name = rng.choice(LIST_OPS)
    elif domain == "number":
        name = rng.choice(NUM_OPS)
    else:
        name = rng.choice(STRING_OPS + LIST_OPS + NUM_OPS)
    return {"op": name, "args": _random_args(rng, name)}


def _random_args(rng, opname):
    if opname in ("add", "sub"):
        return {"n": rng.randint(-9, 9)}
    if opname == "mul":
        return {"n": rng.choice([-3, -2, -1, 0, 1, 2, 3, 10])}
    if opname == "fdiv":
        return {"n": rng.choice([1, 2, 3, 4, 5])}
    if opname == "slice":
        return {"a": rng.randint(0, 3), "b": rng.randint(3, 8)}
    if opname in ("concat", "prepend", "wrap"):
        w = rng.choice(["[", "]", "(", ")", "-", "_", "*", ">"])
        if opname == "wrap":
            return {"pre": w, "suf": w}
        return {"with": w}
    if opname == "repeat":
        return {"n": rng.randint(1, 3)}
    if opname == "item":
        return {"i": rng.randint(0, 4)}
    return {}


# ---- genetics ---------------------------------------------------------------
def mutate_gene(gene, rng, domain):
    steps = [dict(s) for s in gene["steps"]]
    if not steps:
        steps = [_random_step(rng, domain)]
    else:
        choice = rng.random()
        i = rng.randrange(len(steps))
        if choice < 0.35:                      # tweak args
            opname = steps[i]["op"]
            steps[i]["args"] = _random_args(rng, opname)
        elif choice < 0.55:                    # replace a step
            steps[i] = _random_step(rng, domain)
        elif choice < 0.75:                    # insert a step
            steps.insert(i, _random_step(rng, domain))
        elif choice < 0.9 or len(steps) < 2:   # swap two steps
            j = rng.randrange(len(steps))
            steps[i], steps[j] = steps[j], steps[i]
        else:                                  # delete a step
            del steps[i]
    return new_gene(steps, born=rng.random())


def crossover(a, b, rng):
    if not a["steps"]:
        return new_gene([dict(s) for s in b["steps"]])
    if not b["steps"]:
        return new_gene([dict(s) for s in a["steps"]])
    i = rng.randrange(len(a["steps"]) + 1)
    j = rng.randrange(len(b["steps"]) + 1)
    child_steps = [dict(s) for s in (a["steps"][:i] + b["steps"][j:])]
    if not child_steps:
        child_steps = [dict(s) for s in a["steps"]]
    return new_gene(child_steps, born=rng.random())


# ---- serialization ----------------------------------------------------------
def genome_to_dict(genes):
    return {"genes": genes}


def genome_from_dict(d):
    return d.get("genes", [])


def dedupe_genes(genes, cap=600):
    """Canonical gene-pool dedupe: identical DNA is one individual."""
    import json as _json
    seen, out = set(), []
    for g in sorted(genes, key=lambda g: -g.get("fitness", 0.0)):
        k = _json.dumps(g["steps"], sort_keys=True)
        if k in seen:
            continue
        seen.add(k)
        out.append(g)
        if len(out) >= cap:
            break
    return out
