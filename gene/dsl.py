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

@op("quotv")
def _quotv(x, args):
    """first ÷ last of a pair. An innate ability: 'share one by the other'.
    True division — 5 shared by 4 gives 1.25, not a dodge."""
    xs = _scalar_list(x)
    if len(xs) < 2:
        raise ValueError("quot needs two elements")
    n = _num(xs[-1])
    if n == 0:
        raise ZeroDivisionError
    return _num(xs[0]) / n

@op("neg")
def _neg(x, args):
    """Unary negation — 'below zero'. An ability, like stepping backwards."""
    return -_num(x)

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


# ---- grammar memory (ability, not knowledge) --------------------------------
# The resolver is wired to the organism's OWN concept graph at startup. The
# op can only ever read what the organism was taught or derived — delete the
# graph and it raises like any other failed attempt.
_WORD_RESOLVER = None


def set_word_resolver(fn):
    """Wire the grammar-memory lookup to the organism's concept graph."""
    global _WORD_RESOLVER
    _WORD_RESOLVER = fn


@op("grammar_lookup")
def _grammar_lookup(x, args):
    """Look up a taught word-form: x='go', args={'form':'past'} -> 'went'.
    Reads ONLY the organism's memory. Un-taught forms fail (a real miss)."""
    if _WORD_RESOLVER is None:
        raise TypeError("no grammar memory wired")
    form = args.get("form")
    attrs = _WORD_RESOLVER(str(x))
    if not attrs or form not in attrs:
        raise LookupError("form %r of %r not in memory" % (form, x))
    return attrs[form]


# ---- sentence motor cortex ---------------------------------------------------
# A speaker's hands: split a sentence into words, move words around, put a
# word in a slot. Pure manipulation — WHERE a word goes and WHAT word it is
# must be discovered or remembered, never coded here.
# The organism's graph is wired in (set_word_graph) so memory ops can read
# the tables it was taught: verb forms, aux agreement, contractions.

_GRAPH = None
_FORM_IDX = None          # lazy reverse index: inflected -> base, per form
_DETERMINERS = ("a", "an", "the")


def set_word_graph(graph):
    """Wire sentence memory ops to the organism's concept graph."""
    global _GRAPH, _FORM_IDX
    _GRAPH = graph
    _FORM_IDX = None


def _is_vowel(c):
    return c in "aeiou"


def _cvc(w):
    """consonant-vowel-consonant tail (no doubling op uses this — kept for
    future orthography work; doubling is stress-dependent and stays a
    memory matter, the way children learn 'stopped' by correction)."""
    if len(w) < 3:
        return False
    a, b, c = w[-3], w[-2], w[-1]
    return (not _is_vowel(a)) and _is_vowel(b) and (not _is_vowel(c)) and c not in "wxy"


def reg_past(w):
    """Regular English past-tense orthography (an ability, like pronunciation).
    Covers +ed, e->d, consonant+y->ied. Irregulars live in memory only."""
    if w.endswith("e"):
        return w + "d"
    if len(w) >= 3 and w.endswith("y") and not _is_vowel(w[-2]):
        return w[:-1] + "ied"
    return w + "ed"


def reg_ing(w):
    if w.endswith("ie"):
        return w[:-2] + "ying"
    if w.endswith("ee"):
        return w + "ing"
    if w.endswith("e"):
        return w[:-1] + "ing"
    return w + "ing"


def reg_third(w):
    if w.endswith(("s", "x", "z", "ch", "sh")):
        return w + "es"
    if len(w) >= 3 and w.endswith("y") and not _is_vowel(w[-2]):
        return w[:-1] + "ies"
    return w + "s"


def reg_base(w):
    """Best-effort de-inflection of a regular form (walks->walk, flies->fly,
    cities->city, wolves->wolf, types->type). Tries memory first; falls back
    to orthography. Returns the likeliest base."""
    cands = []
    if w.endswith("ies") and len(w) > 3:
        cands.append(w[:-3] + "y")
    if w.endswith("oes") and len(w) > 3:
        cands.append(w[:-2])
    if w.endswith(("ches", "shes", "xes", "zes", "sses")):
        cands.append(w[:-2])
    if w.endswith("ves") and len(w) > 3:
        cands.append(w[:-3] + "f")
    if w.endswith("s") and not w.endswith("ss") and len(w) > 2:
        cands.append(w[:-1])
    if w.endswith("es") and len(w) > 2:
        cands.append(w[:-2])
    cands.append(w)
    if _WORD_RESOLVER:
        for c in cands:
            if _WORD_RESOLVER(c):
                return c
    return cands[0]


def _form_index():
    """Reverse index over the organism's taught forms: walked->walk, goes->go.
    Built lazily from the graph; rebuilt if the graph is re-wired."""
    global _FORM_IDX
    if _FORM_IDX is not None:
        return _FORM_IDX
    idx = {}
    for f in ("past", "ing", "third", "plural"):
        idx[f] = {}
    if _GRAPH is not None:
        for n in _GRAPH.nodes.values():
            a = n.get("attrs", {})
            words = n.get("words") or []
            base = words[0] if words else n["id"].replace("_", " ")
            for f in ("past", "ing", "third", "plural"):
                v = a.get(f)
                if isinstance(v, str) and v and v != base:
                    idx[f][v.lower()] = base
    _FORM_IDX = idx
    return _FORM_IDX


def _verb_form(w, form):
    """The organism's morphological competence: memory first (taught forms,
    including ALL irregulars), regular orthography otherwise. A native
    speaker's regular-rule productivity: never heard 'walk'? You can still
    say 'walked'. Irregular 'went' must have been learned."""
    w = str(w).lower().strip()
    if not w:
        raise ValueError("empty word")
    attrs = _WORD_RESOLVER(w) if _WORD_RESOLVER else None
    if isinstance(attrs, dict) and attrs.get(form):
        return attrs[form]
    idx = _form_index()
    base = None
    for f in ("third", "past", "ing", "plural"):
        if w in idx[f]:
            base = idx[f][w]
            break
    if base is None:
        if attrs:            # bound word that IS a base form
            base = w
        else:
            base = reg_base(w) if w.endswith("s") else w
    if form == "base":
        return base
    battrs = _WORD_RESOLVER(base) if _WORD_RESOLVER else None
    if isinstance(battrs, dict) and battrs.get(form):
        return battrs[form]
    return {"past": reg_past, "ing": reg_ing,
            "third": reg_third, "base": lambda x: x}[form](base)


def _as_word_list(x):
    ws = list(_seq(x))
    if not ws:
        raise ValueError("empty sentence")
    return [str(w) for w in ws]


@op("verb_last_to")
def _verb_last_to(x, args):
    """Replace the last word with its `form` (base/past/ing/third) — memory
    first, regular rule otherwise. Operates on a word list."""
    ws = _as_word_list(x)
    ws[-1] = _verb_form(ws[-1], args.get("form", "past"))
    return ws


@op("reg_past")
def _reg_past(x, args):
    ws = _as_word_list(x)
    ws[-1] = reg_past(ws[-1])
    return ws


@op("reg_ing")
def _reg_ing(x, args):
    ws = _as_word_list(x)
    ws[-1] = reg_ing(ws[-1])
    return ws


@op("reg_third")
def _reg_third(x, args):
    ws = _as_word_list(x)
    ws[-1] = reg_third(ws[-1])
    return ws


@op("aux_insert")
def _aux_insert(x, args):
    """Insert the agreeing auxiliary for the sentence's subject at `pos`.
    Reads the taught aux tables (aux_do/aux_be/aux_will) from memory.
    Subject lookup: pronouns direct; noun heads via determiner skip and the
    plural-marker rule — all taught data, never coded facts."""
    fam = args.get("family", "do")
    pos = int(args.get("pos", 0))
    ws = _as_word_list(x)
    node = _GRAPH.get("aux_%s" % fam) if _GRAPH else None
    if not node:
        raise LookupError("aux table %r not taught" % fam)
    a = node.get("attrs", {})
    head = ""
    for w in ws:
        lw = w.lower().strip("'\".,?!")
        if lw in _DETERMINERS:
            continue
        head = lw
        break
    if head in a:
        aux = a[head]
    else:
        key = "plural" if head.endswith("s") and not head.endswith("ss") else "singular"
        aux = a.get(key)
    if not aux:
        raise LookupError("no agreement for subject %r in %s" % (head, fam))
    ws.insert(pos, aux)
    return ws


@op("verb_agree")
def _verb_agree(x, args):
    """Give the final verb the form that AGREES with the subject, read from
    the taught aux_do table (he->does -> third form; they/do -> base form).
    The same agreement physics aux_insert uses — no facts, just the table."""
    ws = _as_word_list(x)
    head = ""
    for w in ws:
        lw = w.lower().strip("'\".,?!")
        if lw in _DETERMINERS:
            continue
        head = lw
        break
    node = _GRAPH.get("aux_do") if _GRAPH else None
    a = node.get("attrs", {}) if node else {}
    aux = a.get(head)
    if not aux:
        key = "plural" if head.endswith("s") and not head.endswith("ss") \
            else "singular"
        aux = a.get(key)
    form = "base" if aux in ("do", "did", "will") else "third"
    ws[-1] = _verb_form(ws[-1], form)
    return ws


@op("contract_not")
def _contract_not(x, args):
    """Merge an adjacent AUX + 'not' using the taught contraction table
    (do not -> don't). Un-taught merges fail honestly."""
    ws = _as_word_list(x)
    node = _GRAPH.get("contractions") if _GRAPH else None
    if not node:
        raise LookupError("contraction table not taught")
    table = node.get("attrs", {})
    out = []
    i = 0
    while i < len(ws):
        if i + 1 < len(ws):
            key = "%s %s" % (ws[i].lower(), ws[i + 1].lower())
            if key in table:
                out.append(table[key])
                i += 2
                continue
        out.append(ws[i])
        i += 1
    return out


@op("swap_first_two")
def _swap_first_two(x, args):
    """Swap the first two words — the movement a speaker does for inversion."""
    ws = _as_word_list(x)
    if len(ws) < 2:
        raise ValueError("swap needs two words")
    ws[0], ws[1] = ws[1], ws[0]
    return ws


@op("drop_first")
def _drop_first(x, args):
    ws = _as_word_list(x)
    ws.pop(0)
    return ws


@op("insert_at")
def _insert_at(x, args):
    """Put a literal word at a position — the hands, not the words."""
    ws = _as_word_list(x)
    ws.insert(int(args.get("pos", 0)), str(args.get("with", "")))
    return ws


@op("strip_punct")
def _strip_punct(x, args):
    if not isinstance(x, str):
        raise TypeError("strip_punct needs a string")
    return x.strip().rstrip("?!.,;:'\"")


@op("join_words")
def _join_words(x, args):
    return " ".join(str(i) for i in _scalar_list(x))


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
