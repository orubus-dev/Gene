"""The learning loop — simulation, trial, error, mastery.

The user's spec, implemented literally:

  * data comes in as tasks (inputs + a checker — the environment's physics,
    NOT answers handed to the learner);
  * the organism hypothesizes a procedure (pipeline of innate primitives);
  * it runs the hypothesis in simulation and checks ONLY pass/fail;
  * if wrong it mutates/repairs and tries again — as long as its hormones
    allow;
  * when it is right it moves on, and the procedure is consolidated as a
    skill (a gene), a possible reflex, and causal confidence in the
    predictor.

Nothing about the answer is ever written into the organism. What it keeps
is what IT built.
"""
import json
import os
import random

from . import dsl, genome, hdc
from .reflex import stimulus_key


# ============================== task worlds ==================================
def gen_number_task(rng, tier=1):
    a, b = rng.randint(0, 9 * tier), rng.randint(0, 9 * tier)
    kind = rng.choice(["add", "sub", "mul"] if tier > 1 else ["add", "sub"])
    if kind == "add":
        inp, out = [a, b], a + b
    elif kind == "sub":
        if b > a:
            a, b = b, a
        inp, out = [a, b], a - b
    else:
        a, b = rng.randint(0, 9), rng.randint(0, 9)
        inp, out = [a, b], a * b
    return {"domain": "number", "input": inp, "expected": out,
            "prompt": "compute %s %s %s" % (a, {"add": "+", "sub": "-", "mul": "x"}[kind], b)}


def gen_string_task(rng, tier=1):
    words = ["gene", "helix", "mind", "code", "life", "cell", "axion", "delta"]
    s = rng.choice(words)
    if tier > 1:
        s = s + "-" + rng.choice(words)
    kind = rng.choice(["reverse", "upper", "wrap", "first_word", "shout"] if tier > 1
                      else ["reverse", "upper", "shout"])
    if kind == "reverse":
        inp, out = s, s[::-1]
    elif kind == "upper":
        inp, out = s, s.upper()
    elif kind == "shout":
        inp, out = s, s.upper() + "!"
    elif kind == "first_word":
        inp, out = s, s.split("-")[0]
    else:
        inp, out = s, "[%s]" % s
    return {"domain": "string", "input": s, "expected": out, "prompt": kind}


def gen_list_task(rng, tier=1):
    n = rng.randint(2, 3 + tier)
    xs = [rng.randint(0, 20) for _ in range(n)]
    kind = rng.choice(["sum", "max", "min", "sort", "reverse", "unique", "length"]
                      if tier > 1 else ["sum", "max", "reverse"])
    fn = {"sum": sum, "max": max, "min": min, "length": len,
          "sort": sorted, "reverse": lambda v: v[::-1],
          "unique": lambda v: sorted(set(v))}[kind]
    return {"domain": "list", "input": xs, "expected": fn(list(xs)), "prompt": kind}


def gen_sequence_task(rng, tier=1):
    a, d = rng.randint(0, 5), rng.randint(2, 6 + 3 * tier)
    seq = [a + d * i for i in range(5)]
    return {"domain": "sequence", "input": seq, "expected": a + d * 5, "prompt": "next in sequence"}


def gen_code_task(rng, tier=1):
    """Program synthesis: infer the hidden function from I/O behavior.

    The hidden function is the *environment*. The organism never sees it —
    only example behavior, then it must write (synthesize) its own pipeline
    that reproduces the behavior. What it synthesizes is real code it built.
    Hidden family is restricted to behaviors expressible by the innate motor
    cortex — the physics is fair, not impossible.
    """
    hidden = rng.choice(["double", "negate", "incr", "decr", "halfeven"])
    def double(x): return x * 2
    def negate(x): return -x
    def incr(x): return x + 1
    def decr(x): return x - 1
    def halfeven(x): return x // 2
    fn = {"double": double, "negate": negate, "incr": incr,
          "decr": decr, "halfeven": halfeven}[hidden]
    if hidden == "halfeven":
        xs = [rng.randrange(-8, 10, 2) for _ in range(3)]
    else:
        xs = [rng.randint(-9, 9) for _ in range(3)]
    examples = [{"in": x, "out": fn(x)} for x in xs]
    return {"domain": "code", "input": xs[0], "expected": examples[0]["out"],
            "examples": examples, "prompt": "synthesize function from examples",
            "hidden": hidden}


GENERATORS = {
    "number": gen_number_task,
    "string": gen_string_task,
    "list": gen_list_task,
    "sequence": gen_sequence_task,
    "code": gen_code_task,
}


# ============================== hypothesis engines ===========================
def number_pipeline_candidates(rng, task, known_genes):
    """Candidate pipelines for a number task [a, b] -> result.

    The trick that keeps this honest: a number task is executed as
    map-over-input with one arithmetic op — but WHICH op and WHICH order
    must be discovered by trial. We generate candidates from innate ops,
    never from the expected value.
    """
    cands = []
    # core hypotheses for two-number input: combine-all, first-minus-last, all-product
    cands.append([{"op": "sumv", "args": {}}])
    cands.append([{"op": "diff", "args": {}}])
    cands.append([{"op": "prod", "args": {}}])
    for opname in ("add", "sub", "mul", "fdiv"):
        cands.append([{"op": "sumv", "args": {}}, {"op": opname, "args": {}}])
    cands.append([{"op": "maxv", "args": {}}])
    cands.append([{"op": "minv", "args": {}}])
    for g in known_genes:
        cands.append(g["steps"])
    for _ in range(4):
        cands.append(genome.random_gene(rng, "number")["steps"])
    return cands


def sequence_pipeline_candidates(rng, task, known_genes):
    """Next-in-sequence: last + delta. Must discover 'last' then 'add d'."""
    cands = []
    for n in range(-2, 13):
        cands.append([{"op": "last", "args": {}}, {"op": "add", "args": {"n": n}}])
    for n in range(1, 7):
        cands.append([{"op": "last", "args": {}}, {"op": "sub", "args": {"n": n}}])
    cands.append([{"op": "first", "args": {}}, {"op": "add", "args": {"n": 0}}])
    for g in known_genes:
        cands.append(g["steps"])
    for _ in range(3):
        cands.append(genome.random_gene(rng, "sequence")["steps"])
    return cands


def string_pipeline_candidates(rng, task, known_genes):
    s = task["input"]
    cands = []
    for steps in (
        [{"op": "reverse", "args": {}}],
        [{"op": "upper", "args": {}}],
        [{"op": "lower", "args": {}}],
        [{"op": "wrap", "args": {"pre": "[", "suf": "]"}}],
        [{"op": "upper", "args": {}}, {"op": "concat", "args": {"with": "!"}}],
        [{"op": "split", "args": {"sep": "-"}}, {"op": "first", "args": {}}],
        [{"op": "words", "args": {}}, {"op": "first", "args": {}}],
        [{"op": "sort", "args": {}}, {"op": "join", "args": {"sep": ""}}],
    ):
        cands.append(steps)
    for g in known_genes:
        cands.append(g["steps"])
    for _ in range(5):
        cands.append(genome.random_gene(rng, "string")["steps"])
    return cands


def list_pipeline_candidates(rng, task, known_genes):
    cands = []
    for steps in (
        [{"op": "sumv", "args": {}}],
        [{"op": "maxv", "args": {}}],
        [{"op": "minv", "args": {}}],
        [{"op": "sort", "args": {}}],
        [{"op": "rsort", "args": {}}],
        [{"op": "unique", "args": {}}],
        [{"op": "length", "args": {}}],
        [{"op": "count", "args": {}}],
        [{"op": "reverse", "args": {}}],
        [{"op": "first", "args": {}}],
        [{"op": "last", "args": {}}],
    ):
        cands.append(steps)
    for g in known_genes:
        cands.append(g["steps"])
    for _ in range(4):
        cands.append(genome.random_gene(rng, "list")["steps"])
    return cands


def code_pipeline_candidates(rng, task, known_genes):
    """Search over single unary numeric ops checked against examples."""
    cands = []
    base = []
    for op1 in ("add", "sub", "mul", "fdiv"):
        for n in (-2, -1, 0, 1, 2, 3, 4, 5):
            base.append([{"op": op1, "args": {"n": n}}])
    base.append([{"op": "identity", "args": {}}])
    base.append([{"op": "sqr", "args": {}}])
    cands.extend(base)
    for g in known_genes:
        cands.append(g["steps"])
    return cands


CANDIDATE_FN = {
    "number": number_pipeline_candidates,
    "sequence": sequence_pipeline_candidates,
    "string": string_pipeline_candidates,
    "list": list_pipeline_candidates,
    "code": code_pipeline_candidates,
}


def run_pipeline_on(domain, task, steps):
    """Execute a hypothesis. Code domain checks ALL examples (behavioral test)."""
    if domain == "number":
        wrapped = [{"op": "map", "args": {"pipeline": steps}}]
        # map over [a,b] with the numeric steps, then the task is arity-2:
        # sum-style handling: organism pipelines operate on the list directly.
        return dsl.execute_pipeline(steps, task["input"])
    return dsl.execute_pipeline(steps, task["input"])


def check(domain, task, result):
    exp = task["expected"]
    try:
        if isinstance(exp, float) or isinstance(result, float):
            return abs(float(result) - float(exp)) < 1e-9
        return result == exp
    except Exception:
        return False


# ============================== the loop =====================================
def train_task(task, genome_genes, reflexes, predictor, endocrine, rng,
               max_retries=14, now=0.0):
    """One task. Trial until right (or budget gone). ONLY pass/fail feedback.

    Returns dict(attempt log, learned gene or None).
    """
    domain = task["domain"]
    payload_key = stimulus_key(domain, task["input"])
    attempts = []
    candidates = []

    # reflex first (System 1)
    arc = reflexes.consult(domain, task["input"])
    if arc:
        candidates.append(("reflex", arc))
    # fit genes first (exploitation)
    for g in sorted(genome_genes, key=lambda g: -g["fitness"]):
        candidates.append(("gene:" + g["id"], g["steps"]))
        if len(candidates) > 24:
            break
    # hypothesis space (exploration; hormones widen it)
    budget = endocrine.search_budget(max_retries)
    generated = CANDIDATE_FN[domain](rng, task, [])
    # dedupe
    seen = set()
    for tag, steps in candidates:
        seen.add(json.dumps(steps, sort_keys=True))
    for steps in generated:
        k = json.dumps(steps, sort_keys=True)
        if k not in seen:
            seen.add(k)
            candidates.append(("hypothesis", steps))

    tried = 0
    winner = None
    for tag, steps in candidates:
        if tried >= budget:
            break
        tried += 1
        predicted = predictor.predict(domain, steps)
        try:
            if domain == "code":
                # behavioral test: the candidate must reproduce ALL example behavior
                ok = True
                for ex in task["examples"]:
                    r2 = dsl.execute_pipeline(steps, ex["in"])
                    if not check(domain, {"expected": ex["out"]}, r2):
                        ok = False
                        break
                result = "behavior-ok" if ok else None
            else:
                result = run_pipeline_on(domain, task, steps)
                ok = check(domain, task, result)
        except Exception:
            result, ok = None, False
        surprise = predictor.reconcile(domain, steps, ok)
        endocrine.surprise(min(1.0, surprise))
        attempts.append({"tag": tag, "ok": ok, "pred": round(predicted, 2),
                         "steps": dsl.pipeline_to_python(steps)})
        if ok:
            winner = steps
            break
        endocrine.effort(0.5)

    if winner:
        endocrine.success(1.0)
        reflexes.reinforce(domain, task["input"], winner)
        gene = genome.new_gene(winner, fitness=1.0, uses=1, born=now)
        return {"solved": True, "attempts": attempts, "gene": gene,
                "domain": domain, "coactive": [domain, "skill", "success"]}
    endocrine.load(1.0)
    return {"solved": False, "attempts": attempts, "gene": None,
            "domain": domain, "coactive": [domain, "failure"]}


def dedupe_genes(genes, cap=600):
    seen, out = set(), []
    for g in sorted(genes, key=lambda g: -g["fitness"]):
        k = json.dumps(g["steps"], sort_keys=True)
        if k in seen:
            continue
        seen.add(k)
        out.append(g)
        if len(out) >= cap:
            break
    return out
