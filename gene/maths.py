"""Maths — equations as first-class things the organism thinks with.

Orubus's spec: "give it the foundational formulary and it should be able
to build the structure for everything above it — create new equations,
fuse them."

The split, same law as everywhere else in this codebase:
  * ABILITY (this module, like the motor cortex): parse an expression,
    evaluate it, isolate a symbol, render canonically, fuse two formulas
    by substituting a shared symbol. Pure manipulation — no facts.
  * MEMORY (the organism's graph): WHICH formulas exist, what each
    symbol means. The organism only answers from formulas it was taught
    or that appear in the stimulus itself.

The environment (task world below) owns the lesson truth and grades
pass/fail only. Equations live in the graph as nodes (kind "equation")
with a "formula" attr, so deleting the graph deletes every formula.
"""
import json
import math
import os
import re

from . import dsl, genome

# ============================ expression physics ==============================
# AST: ("num", v) | ("var", name) | ("+", a, b) | ("-", a, b) | ("*", a, b)
#      | ("/", a, b) | ("^", a, b) | ("neg", a) | ("sqrt", a)

_TOKEN_RE = re.compile(r"\s*(\d+\.\d+|\d+|[a-z]+|=|\*\*|[-+*/^()])")


def tokenize(text):
    out = []
    i = 0
    s = text.strip()
    while i < len(s):
        m = _TOKEN_RE.match(s, i)
        if not m:
            if s[i].isspace():
                i += 1
                continue
            raise ValueError("bad token at %d in %r" % (i, s))
        out.append(m.group(1))
        i = m.end()
    return out


class _Parser:
    """Recursive descent: expr -> term -> factor -> power -> atom."""

    def __init__(self, toks):
        self.toks = toks
        self.i = 0

    def peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else None

    def eat(self, t=None):
        got = self.peek()
        if got is None or (t is not None and got != t):
            raise ValueError("expected %r got %r" % (t, got))
        self.i += 1
        return got

    def parse(self):
        n = self.expr()
        if self.peek() is not None:
            raise ValueError("trailing tokens")
        return n

    def expr(self):
        n = self.term()
        while self.peek() in ("+", "-"):
            op = self.eat()
            n = (op, n, self.term())
        return n

    def term(self):
        n = self.factor()
        while self.peek() in ("*", "/"):
            op = self.eat()
            n = (op, n, self.factor())
        return n

    def factor(self):
        if self.peek() == "-":
            self.eat()
            return ("neg", self.factor())
        if self.peek() == "+":
            self.eat()
            return self.factor()
        return self.power()

    def power(self):
        n = self.atom()
        if self.peek() == "^":
            self.eat()
            n = ("^", n, self.factor())
        return n

    def atom(self):
        t = self.peek()
        if t == "(":
            self.eat()
            n = self.expr()
            self.eat(")")
            return n
        if t == "**":                      # python-ish exponent alias
            self.eat()
            return ("^", self.atom(), self.factor())
        if t is None:
            raise ValueError("unexpected end")
        if re.match(r"^\d", t):
            self.eat()
            return ("num", float(t))
        if re.match(r"^[a-z]+$", t):
            self.eat()
            if t == "sqrt" and self.peek() == "(":
                self.eat("(")
                inner = self.expr()
                self.eat(")")
                return ("sqrt", inner)
            if t == "pi":
                return ("num", math.pi)
            return ("var", t)
        raise ValueError("bad atom %r" % t)


def parse_expr(text):
    """'v = u + a*t' -> AST of the RHS (LHS handled by formula())."""
    toks = tokenize(str(text))
    eq = None
    if "=" in toks:
        eq = toks.index("=")
        toks = toks[eq + 1:]
    return _Parser(toks).parse()


def parse_side(text):
    """Parse an expression that may contain '='; returns (lhs_ast, rhs_ast)."""
    toks = tokenize(str(text))
    if "=" in toks:
        i = toks.index("=")
        return _Parser(toks[:i]).parse(), _Parser(toks[i + 1:]).parse()
    raise ValueError("not an equation: %r" % text)


def ast_vars(n):
    if n[0] == "num":
        return set()
    if n[0] == "var":
        return {n[1]}
    if n[0] in ("neg", "sqrt"):
        return ast_vars(n[1])
    return ast_vars(n[1]) | ast_vars(n[2])


def eval_ast(n, env):
    k = n[0]
    if k == "num":
        return n[1]
    if k == "var":
        if n[1] not in env:
            raise KeyError("no value for %r" % n[1])
        return float(env[n[1]])
    if k == "neg":
        return -eval_ast(n[1], env)
    if k == "sqrt":
        v = eval_ast(n[1], env)
        if v < 0:
            raise ValueError("sqrt of negative")
        return math.sqrt(v)
    a = eval_ast(n[1], env)
    b = eval_ast(n[2], env)
    if k == "+":
        return a + b
    if k == "-":
        return a - b
    if k == "*":
        return a * b
    if k == "/":
        return a / b
    if k == "^":
        return a ** b
    raise ValueError("bad node %r" % (n,))


def _num_str(v):
    if abs(v - round(v)) < 1e-9 and abs(v) < 1e15:
        return str(int(round(v)))
    return "%.12g" % v


def render(n, prec=0):
    """Canonical string: no spaces, explicit '*', minimal parens.
    Parens when a child's own precedence is weaker than its parent:
    +- (1) under */^, */ (2) under ^ or inside /, ^ (3) nowhere."""
    k = n[0]
    if k == "num":
        return _num_str(n[1])
    if k == "var":
        return n[1]
    if k == "neg":
        s = "-" + render(n[1], 1)
        return "(%s)" % s if prec > 1 else s
    if k == "sqrt":
        return "sqrt(%s)" % render(n[1], 0)
    if k in ("+", "-"):
        a, b = render(n[1], 1), render(n[2], 1)
        s = "%s%s%s" % (a, k, b)
        return "(%s)" % s if prec > 1 else s
    if k == "*":
        a, b = render(n[1], 2), render(n[2], 2)
        s = "%s*%s" % (a, b)
        return "(%s)" % s if prec > 2 else s
    if k == "/":
        a, b = render(n[1], 2), render(n[2], 3)   # denominator: compound children parenthesize
        s = "%s/%s" % (a, b)
        return "(%s)" % s if prec >= 2 else s
    if k == "^":
        a, b = render(n[1], 3), render(n[2], 1)
        s = "%s^%s" % (a, b)
        return "(%s)" % s if prec >= 3 else s   # only left-nested ^ needs parens
    raise ValueError("bad node %r" % (n,))


def contains(n, target):
    return target in ast_vars(n)


def _occurrences(n, target):
    if n[0] == "var":
        return 1 if n[1] == target else 0
    if n[0] == "num":
        return 0
    if n[0] in ("neg", "sqrt"):
        return _occurrences(n[1], target)
    return _occurrences(n[1], target) + _occurrences(n[2], target)


def solve_eq(lhs, rhs, target):
    """Isolate target in lhs = rhs. Linear-in-target chains and target^2 /
    target-in-sqrt forms. Raises when the target is tangled (that is an
    honest failure the trial loop can eat)."""
    if _occurrences(lhs, target) + _occurrences(rhs, target) != 1:
        raise ValueError("target %r not isolable" % target)
    return _isolate(lhs, rhs, target)


def _isolate(lhs, rhs, target):
    if lhs[0] == "var" and lhs[1] == target:
        return rhs
    k = lhs[0]
    if k == "num":
        raise ValueError("no target in lhs")
    if k in ("neg",):
        return _isolate(lhs[1], ("neg", rhs), target)
    if k == "sqrt":
        # sqrt(x) = rhs  ->  x = rhs^2
        return _isolate(lhs[1], ("^", rhs, ("num", 2.0)), target)
    if k == "^":
        # lhs = base ^ exp. target in base, exp == 2  ->  base = sqrt(rhs)
        base, expo = lhs[1], lhs[2]
        if contains(base, target) and expo[0] == "num" and abs(expo[1] - 2.0) < 1e-9:
            return _isolate(base, ("sqrt", rhs), target)
        raise ValueError("cannot isolate through ^")
    a, b = lhs[1], lhs[2]
    if k == "+":
        if contains(a, target):
            return _isolate(a, ("-", rhs, b), target)
        return _isolate(b, ("-", rhs, a), target)
    if k == "-":
        if contains(a, target):
            return _isolate(a, ("+", rhs, b), target)
        return _isolate(b, ("-", a, rhs), target)   # b = a - rhs
    if k == "*":
        if contains(a, target):
            return _isolate(a, ("/", rhs, b), target)
        return _isolate(b, ("/", rhs, a), target)
    if k == "/":
        if contains(a, target):
            return _isolate(a, ("*", rhs, b), target)
        return _isolate(b, ("/", a, rhs), target)   # b = a / rhs
    raise ValueError("bad lhs node")


def formula(text):
    """Taught formula string -> (subject, power, rhs_ast). Accepts plain
    subjects (v=...) and squared subjects (c^2=..., power 2)."""
    lhs, rhs = parse_side(text)
    if lhs[0] == "var":
        return lhs[1], 1, rhs
    if (lhs[0] == "^" and lhs[1][0] == "var" and lhs[2][0] == "num"
            and abs(lhs[2][1] - 2.0) < 1e-9):
        return lhs[1][1], 2, rhs
    raise ValueError("formula subject must be a single symbol")


def substitute(node, var, repl):
    if node[0] == "var":
        return repl if node[1] == var else node
    if node[0] in ("num",):
        return node
    if node[0] in ("neg", "sqrt"):
        return (node[0], substitute(node[1], var, repl))
    return (node[0], substitute(node[1], var, repl), substitute(node[2], var, repl))


def fuse_formulas(f1, f2):
    """Equation synthesis: substitute f2's subject (rhs) for its symbol
    inside f1. 'v=u+a*t' + 'a=f/m'  ->  'v=u+(f/m)*t'. Returns the fused
    formula string, or raises when nothing composes."""
    s1, _, r1 = formula(f1)
    s2, _, r2 = formula(f2)
    if s2 not in ast_vars(r1):
        raise ValueError("no shared symbol %r" % s2)
    merged = substitute(r1, s2, r2)
    return "%s=%s" % (s1, render(merged))


def evaluate_formula(f, env):
    _, _, rhs = formula(f)
    v = eval_ast(rhs, env)
    return round(v, 6)


def solve_formula(f, target, env):
    s, spow, rhs = formula(f)
    env = dict(env)
    if target == s:
        v = eval_ast(rhs, env)
        return round(math.sqrt(v), 6) if spow == 2 else round(v, 6)
    lhs_full = ("^", ("var", s), ("num", 2.0)) if spow == 2 else ("var", s)
    sol = solve_eq(rhs, lhs_full, target)
    return round(eval_ast(sol, env), 6)


def rearrange_formula(f, target):
    s, spow, rhs = formula(f)
    if target == s:
        return "%s=%s" % (target, ("sqrt(%s)" % render(rhs)) if spow == 2
                          else render(rhs))
    lhs_full = ("^", ("var", s), ("num", 2.0)) if spow == 2 else ("var", s)
    sol = solve_eq(rhs, lhs_full, target)
    return "%s=%s" % (target, render(sol))


# ============================== the task world ================================
# PUBLIC lesson data: curriculum/maths-1.json (kind "equation", attr
# "formula"). PROBES: held-out formulas the lesson never mentions — the
# stimulus itself carries the formula, so generalizing is an ability test.

_LESSON = None
PROBE_FORMULAS = [
    "p=2*l+2*w", "c=pi*d", "t=d/s", "r=d/2", "a=b*h", "n=a+b+c",
    "y=x-3", "m=2*n+1", "s=4*pi*r*r", "v=a*t", "f=m/a", "d=t*v",
]


def _lesson():
    global _LESSON
    if _LESSON is not None:
        return _LESSON
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "curriculum", "maths-1.json")
    eqs = []
    try:
        with open(path) as fh:
            pack = json.load(fh)
        for c in pack.get("concepts", []):
            if c.get("kind") == "equation" and c.get("attrs", {}).get("formula"):
                eqs.append({"id": c["id"], "formula": c["attrs"]["formula"],
                            "words": c.get("words", [])})
    except Exception:
        pass
    _LESSON = eqs
    return eqs


def _values(rng, variables, tier):
    hi = 12 if tier < 3 else 40
    out = {}
    for v in sorted(variables):
        out[v] = rng.randint(1, hi) if tier < 3 else round(rng.uniform(0.5, hi), 1)
    return out


def gen_maths_task(rng, tier=1):
    """Four physics shapes: eval, solve, rearrange, fuse. Tier gates:
    t1 eval, t2 eval+solve, t3 solve+rearrange(+held-out probes),
    t4 rearrange+fuse (equation synthesis)."""
    eqs = _lesson()
    kinds = ["eval"] if tier < 2 else (["eval", "solve"] if tier < 3 else
                                       (["solve", "rearrange"] if tier < 4 else
                                        ["rearrange", "fuse"]))
    kind = rng.choice(kinds)

    if kind == "fuse":
        for _ in range(30):
            f1, f2 = rng.choice(eqs), rng.choice(eqs)
            if f1["id"] == f2["id"]:
                continue
            try:
                truth = fuse_formulas(f1["formula"], f2["formula"])
            except Exception:
                continue
            if len(truth) > 60:
                continue
            return {"domain": "maths", "kind": "fuse",
                    "input": "fuse %s and %s" % (f1["id"], f2["id"]),
                    "expected": truth, "prompt": "fuse %s + %s" % (f1["id"], f2["id"])}
        return None

    use_probe = tier >= 3 and rng.random() < 0.3
    if use_probe:
        f = rng.choice(PROBE_FORMULAS)
        try:
            subj, _spow, rhs = formula(f)
            vs = sorted(ast_vars(rhs))
            if not vs:
                return None
            vals = _values(rng, vs, tier)
            if kind == "rearrange":
                tgt = rng.choice(vs)
                truth = rearrange_formula(f, tgt)
            elif kind == "solve":
                tgt = rng.choice(vs)
                vals = dict(vals)
                truth = solve_formula(f, tgt, vals)
            else:
                truth = evaluate_formula(f, vals)
        except Exception:
            return None
        pairs = " ".join("%s=%s" % (k, _num_str(v)) for k, v in sorted(vals.items()))
        base = "%s %s" % (f, pairs)
        tail = ""
        if kind in ("solve", "rearrange"):
            tail = "for %s " % tgt
            if kind == "solve":
                tail += "with "
        return {"domain": "maths", "kind": kind,
                "input": "%s %s %s" % (kind, base, tail),
                "expected": truth, "prompt": "%s %s" % (kind, f)}
    if not eqs:
        return None
    for _ in range(8):                     # skip tangled targets honestly
        e = rng.choice(eqs)
        subj, _spow, rhs = formula(e["formula"])
        vs = sorted(ast_vars(rhs))
        if not vs:
            continue
        if kind == "rearrange":
            tgt = rng.choice(vs)
            try:
                truth = rearrange_formula(e["formula"], tgt)
            except Exception:
                continue
            return {"domain": "maths", "kind": "rearrange",
                    "input": "rearrange %s for %s" % (e["id"], tgt),
                    "expected": truth, "prompt": "rearrange %s" % e["id"]}
        vals = _values(rng, vs, tier)
        tgt = rng.choice(vs)
        try:
            truth = solve_formula(e["formula"], tgt, vals) if kind == "solve" \
                else evaluate_formula(e["formula"], vals)
        except Exception:
            continue
        pairs = " ".join("%s=%s" % (k, _num_str(v)) for k, v in sorted(vals.items()))
        body = "%s %s" % (e["id"], pairs)
        if kind == "solve":
            body = "%s for %s %s" % (e["id"], tgt, pairs)
        return {"domain": "maths", "kind": kind, "input": "%s %s" % (kind, body),
                "expected": truth, "prompt": "%s %s" % (kind, e["id"])}
    return None


# ======================= the organism's memory routes =========================
# These ops read ONLY the organism's own graph (dsl._GRAPH) plus the
# stimulus text. No lesson file is ever opened here.

def _eq_formula_from_graph(name):
    g = dsl._GRAPH
    if g is None:
        raise LookupError("no graph wired")
    node = g.get("eq_%s" % name) or g.get(name)
    if not node:
        node = g.lookup_word(name)
    if not node:
        raise LookupError("no equation %r taught" % name)
    f = (node.get("attrs") or {}).get("formula")
    if not f:
        raise LookupError("no formula on %r" % name)
    return f


def _parse_task(text):
    """Split a maths stimulus: kind, eq-or-formula, target, values."""
    toks = str(text).strip().rstrip("?!. ").split()
    if not toks:
        raise ValueError("empty")
    kind = toks[0].lower()
    rest = toks[1:]
    target = None
    vals = {}
    body = []
    i = 0
    while i < len(rest):
        t = rest[i]
        if t.lower() == "for" and i + 1 < len(rest):
            target = rest[i + 1].lower()
            i += 2
            continue
        if t.lower() == "with":
            i += 1
            continue
        if "=" in t:
            k, v = t.split("=", 1)
            try:
                vals[k.strip().lower()] = float(v)
                i += 1
                continue
            except ValueError:
                body.append(t)               # an inline formula, not a pair
                i += 1
                continue
        body.append(t)
        i += 1
    f = None
    name = None
    if body and "=" in body[0]:
        f = body[0]
    elif body:
        name = body[0].lower()
    if kind == "fuse" and len(body) >= 3:
        name = body[0].lower()
        name2 = body[2].lower()
        return kind, name, name2, target, vals, f
    return kind, name, None, target, vals, f


def _resolve(kind, name, name2, target, vals, inline):
    """Route the task using the organism's memory (graph formulas) or the
    formula printed in the stimulus itself."""
    if kind == "fuse":
        f1 = _eq_formula_from_graph(name)
        f2 = _eq_formula_from_graph(name2)
        return fuse_formulas(f1, f2)
    f = inline
    if f is None:
        f = _eq_formula_from_graph(name)
    if kind == "eval":
        return evaluate_formula(f, vals)
    if kind == "solve":
        if not target:
            raise ValueError("no target symbol")
        return solve_formula(f, target, vals)
    if kind == "rearrange":
        if not target:
            raise ValueError("no target symbol")
        return rearrange_formula(f, target)
    raise ValueError("unknown maths kind %r" % kind)


@dsl.op("maths_task")
def _maths_task(x, args):
    """The organism's whole maths route: parse the ask, pull the formulas
    from ITS OWN memory (or the stimulus), run the algebra, answer."""
    kind, name, name2, target, vals, inline = _parse_task(x)
    return _resolve(kind, name, name2, target, vals, inline)


@dsl.op("eq_lookup")
def _eq_lookup(x, args):
    """Memory route: the taught formula for a named equation."""
    toks = str(x).split()
    name = toks[1] if len(toks) > 1 else toks[0]
    return _eq_formula_from_graph(name.lower())


def _num_out(v):
    if isinstance(v, float) and abs(v - round(v)) < 1e-9:
        return int(round(v))
    return v


@dsl.op("maths_eval")
def _maths_eval(x, args):
    kind, name, name2, target, vals, inline = _parse_task(x)
    r = _resolve("eval", name, name2, target, vals, inline)
    return _num_out(r)


@dsl.op("maths_solve")
def _maths_solve(x, args):
    kind, name, name2, target, vals, inline = _parse_task(x)
    r = _resolve("solve", name, name2, target, vals, inline)
    return _num_out(r)


@dsl.op("maths_rearrange")
def _maths_rearrange(x, args):
    kind, name, name2, target, vals, inline = _parse_task(x)
    return _resolve("rearrange", name, name2, target, vals, inline)


@dsl.op("maths_fuse")
def _maths_fuse(x, args):
    kind, name, name2, target, vals, inline = _parse_task(x)
    return _resolve("fuse", name, name2, target, vals, inline)


def maths_pipeline_candidates(rng, task, known_genes):
    """Hypotheses: the matching memory route first, then the general route,
    then decoys (identity/lower must fail on numbers), then genes."""
    kind = task.get("kind", "eval")
    routes = {"eval": ["maths_eval", "maths_task"],
              "solve": ["maths_solve", "maths_task"],
              "rearrange": ["maths_rearrange", "maths_task"],
              "fuse": ["maths_fuse", "maths_task"]}
    cands = [[{"op": op, "args": {}}] for op in routes.get(kind, ["maths_task"])]
    cands.append([{"op": "identity", "args": {}}])
    cands.append([{"op": "lower", "args": {}}])
    for g in known_genes:
        if g.get("domain") == "maths" and g.get("steps"):
            cands.append(g["steps"])
    for _ in range(3):
        cands.append(genome.random_gene(rng, "maths")["steps"])
    seen, out = set(), []
    for s in cands:
        k = json.dumps(s, sort_keys=True)
        if k not in seen:
            seen.add(k)
            out.append(s)
    return out
