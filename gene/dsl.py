"""Innate motor primitives and the pipeline executor.

This is the organism's *motor cortex* — innate machinery, NOT knowledge.
A child is born able to grasp and babble; it is not born knowing that
2+2=4. Every op here is an ability to act on data, not a fact about the
world. All knowledge lives in memory/curriculum, never in code.

A pipeline is a list of steps: [{"op": "reverse"}, {"op": "upper"}].
Execution applies steps left to right. A type error is a failed attempt,
not a crash — that is what trial-and-error eats.
"""

OPS = {}


def op(name):
    def deco(fn):
        OPS[name] = fn
        return fn
    return deco


def _num(x):
    if isinstance(x, bool):
        raise TypeError("bool is not a number here")
    if isinstance(x, (int, float)):
        return x
    raise TypeError("expected number, got %r" % (x,))


def _seq(x):
    if isinstance(x, (list, tuple)):
        return list(x)
    if isinstance(x, str):
        return x
    raise TypeError("expected sequence, got %r" % (x,))


def _scalar_list(x):
    """Allow both a scalar (treated as 1-list) and a list."""
    if isinstance(x, (list, tuple)):
        return list(x)
    return [x]


# ---- string/list structure primitives -------------------------------------
@op("identity")
def _identity(x, args):
    return x

@op("reverse")
def _reverse(x, args):
    s = _seq(x)
    return s[::-1]

@op("upper")
def _upper(x, args):
    if not isinstance(x, str):
        raise TypeError("upper needs a string")
    return x.upper()

@op("lower")
def _lower(x, args):
    if not isinstance(x, str):
        raise TypeError("lower needs a string")
    return x.lower()

@op("sort")
def _sort(x, args):
    return sorted(_scalar_list(x))

@op("rsort")
def _rsort(x, args):
    return sorted(_scalar_list(x), reverse=True)

@op("unique")
def _unique(x, args):
    seen, out = set(), []
    for i in _scalar_list(x):
        k = (i.__class__.__name__, i)
        if k not in seen:
            seen.add(k)
            out.append(i)
    return out

@op("length")
def _length(x, args):
    s = _seq(x)
    return len(s)

@op("first")
def _first(x, args):
    s = _seq(x)
    if not s:
        raise ValueError("first of empty")
    return s[0]

@op("last")
def _last(x, args):
    s = _seq(x)
    if not s:
        raise ValueError("last of empty")
    return s[-1]

@op("sumv")
def _sumv(x, args):
    return sum(_num(i) for i in _scalar_list(x))

@op("subv")
def _subv(x, args):
    """first − last of a pair. An innate ability: 'take one away from the other'."""
    s = _scalar_list(x)
    return _num(s[0]) - _num(s[-1])

@op("maxv")
def _maxv(x, args):
    return max(_num(i) for i in _scalar_list(x))

@op("minv")
def _minv(x, args):
    return min(_num(i) for i in _scalar_list(x))

@op("count")
def _count(x, args):
    return len(_scalar_list(x))


@op("sqr")
def _sqr(x, args):
    v = _num(x)
    return v * v

@op("diff")
def _diff(x, args):
    xs = _scalar_list(x)
    if len(xs) < 2:
        raise ValueError("diff needs two elements")
    return _num(xs[0]) - _num(xs[-1])

@op("prod")
def _prod(x, args):
    p = 1
    for i in _scalar_list(x):
        p *= _num(i)
    return p


# ---- parameterized primitives ---------------------------------------------
@op("add")
def _add(x, args):
    return _num(x) + _num(args.get("n", 0))

@op("sub")
def _sub(x, args):
    return _num(x) - _num(args.get("n", 0))

@op("mul")
def _mul(x, args):
    return _num(x) * _num(args.get("n", 1))

@op("fdiv")
def _fdiv(x, args):
    n = _num(args.get("n", 1))
    if n == 0:
        raise ZeroDivisionError
    return _num(x) / n

@op("slice")
def _slice(x, args):
    s = _seq(x)
    return s[args.get("a", 0):args.get("b")]

@op("concat")
def _concat(x, args):
    return "%s%s" % (x, args.get("with", ""))

@op("prepend")
def _prepend(x, args):
    return "%s%s" % (args.get("with", ""), x)

@op("wrap")
def _wrap(x, args):
    return "%s%s%s" % (args.get("pre", ""), x, args.get("suf", ""))

@op("repeat")
def _repeat(x, args):
    n = int(args.get("n", 1))
    if n < 0 or n > 999:
        raise ValueError("bad repeat")
    return _seq(x) * n

@op("item")
def _item(x, args):
    s = _seq(x)
    i = int(args.get("i", 0))
    return s[i]

@op("split")
def _split(x, args):
    if not isinstance(x, str):
        raise TypeError("split needs a string")
    return x.split(args.get("sep", None) or None)

@op("join")
def _join(x, args):
    return (args.get("sep", "") or "").join(str(i) for i in _scalar_list(x))

@op("words")
def _words(x, args):
    if not isinstance(x, str):
        raise TypeError("words needs a string")
    return x.split()


# ---- higher-order primitives (list transforms) -----------------------------
@op("map")
def _map(x, args):
    """Apply a nested pipeline to each element."""
    sub = args.get("pipeline") or []
    return [execute_pipeline(sub, i) for i in _scalar_list(x)]

@op("filterop")
def _filterop(x, args):
    """Keep elements where nested pipeline result == args['val']."""
    sub = args.get("pipeline") or []
    val = args.get("val")
    return [i for i in _scalar_list(x) if execute_pipeline(sub, i) == val]


def execute_pipeline(steps, x):
    """Run a pipeline. Any failure raises — the caller treats it as a wrong answer."""
    cur = x
    for step in steps:
        name = step.get("op")
        if name not in OPS:
            raise KeyError("unknown op %r" % name)
        cur = OPS[name](cur, step.get("args") or {})
    return cur


def pipeline_to_python(steps):
    """Render a learned pipeline as equivalent Python-ish code (for the code domain)."""
    parts = []
    for s in steps:
        a = s.get("args") or {}
        argstr = ", ".join("%s=%r" % (k, v) for k, v in a.items())
        parts.append(s["op"] + ("(%s)" % argstr if argstr else ""))
    return " | ".join(parts)
