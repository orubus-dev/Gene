"""The linguistic interface — words to concepts and back.

There is NO tokenizer here: no vocabulary tables, no embeddings, no
neural text machinery. Words are discrete keys; meaning lives in the
concept graph they point into. Unknown words are not errors — they are
knowledge-seeking triggers ("I don't know this word yet").

Recognized intents (grown over time, keep minimal and honest):
  fact        "an X is a Y" / "X is Y" / "X has Y"
  query       "what is X" / "what are X" / "does X have Y" / "how do you know X"
  compute     "compute A + B" / "add A and B" / "multiply A and B" ...
  transform   "reverse X" / "sort 3,1,2" / "sum 1 2 3" / "next in 2 4 6 8 10"
  teach       "remember X is Y"
  status      "status" / "what do you know"
"""
import re

NUMWORDS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
            "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
            "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
            "nineteen": 19, "twenty": 20}


def _num(tok):
    tok = tok.lower().strip()
    if tok in NUMWORDS:
        return NUMWORDS[tok]
    try:
        return int(tok)
    except ValueError:
        try:
            return float(tok)
        except ValueError:
            return None


def _numbers(text):
    toks = re.findall(r"-?\d+\.?\d*|" + "|".join(NUMWORDS), text.lower())
    out = []
    for t in toks:
        v = _num(t)
        if v is not None:
            out.append(v)
    return out


def _strip_article(s):
    return re.sub(r"^(a|an|the)\s+", "", s.strip())


# ---- arithmetic expressions: bare, prefixed, or number-worded ----------------
_NUM = r"(?:-?\d+(?:\.\d+)?|%s)" % "|".join(NUMWORDS)
_ARITH_RE = re.compile(r"^(%s)\s*([+\-*/xX\u00f7])\s*(%s)$" % (_NUM, _NUM))
_ARITH_WORDS_RE = re.compile(
    r"^(%s)\s+(plus|minus|times|multiplied by|divided by|over)\s+(%s)$"
    % (_NUM, _NUM))
_PREFIX_WORDS = r"^(?:what(?:'s| is)|whats|compute|calculate|whats)\s+(.+)$"


def _val(tok):
    v = _num(tok)
    return v


def _arith(text):
    """Match an arithmetic expression (bare, word-op, or prefixed). Returns
    a compute intent dict or None. Handles 125+6, 3*8, 5/4, 1-3, five plus
    seven, what is 97+38, divide 5 by 4."""
    t = text.strip().rstrip("?!. ")
    m = re.match(_PREFIX_WORDS, t)
    if m:
        t = m.group(1).strip()
    m = re.match(r"^(?:divide|dividing)\s+(%s)\s+by\s+(%s)$" % (_NUM, _NUM), t)
    if m:
        return {"intent": "compute", "op": "div", "args": [_val(m.group(1)), _val(m.group(2))]}
    m = re.match(r"^(%s)\s+divided by\s+(%s)$" % (_NUM, _NUM), t)
    if m:
        return {"intent": "compute", "op": "div", "args": [_val(m.group(1)), _val(m.group(2))]}
    m = _ARITH_RE.match(t)
    if m:
        a, opb = _val(m.group(1)), _val(m.group(3))
        sym = m.group(2).lower()
        op = {"+": "add", "-": "sub", "*": "mul", "x": "mul",
              "\u00f7": "div", "/": "div"}[sym]
        return {"intent": "compute", "op": op, "args": [a, opb]}
    m = _ARITH_WORDS_RE.match(t)
    if m:
        a, opb = _val(m.group(1)), _val(m.group(3))
        op = {"plus": "add", "minus": "sub", "times": "mul",
              "multiplied by": "mul", "divided by": "div", "over": "div"}[m.group(2)]
        return {"intent": "compute", "op": op, "args": [a, opb]}
    return None


# ---- grammar transforms: learned forms of taught words -----------------------
_GRAMMAR_FORMS = {
    "past": r"(?:past(?:\s+tense)?|simple past)",
    "plural": r"(?:plural|pluralized?)",
    "ing": r"(?:ing|ing form|continuous)",
    "third": r"(?:third(?:\s+person|\s+form)?|third-person)",
}


def _grammar(text):
    """Match a grammar-transform ask: 'past tense of walk', 'plural of cat',
    'what is the past tense of go', 'turn walk into past'. Returns intent
    dict or None."""
    t = text.strip().rstrip("?!. ")
    t = re.sub(r"^(?:what(?:'s| is)|whats|tell me)\s+(?:the\s+)?", "", t, flags=re.I)
    for form, pat in _GRAMMAR_FORMS.items():
        m = re.match(r"^(?:turn|make|put)?\s*(?:the\s+)?(%s)\s+(?:of|for)\s+([a-z][a-z-]*)$"
                     % pat, t, re.I)
        if m:
            return {"intent": "grammar", "form": form, "word": m.group(2).lower()}
        m = re.match(r"^([a-z][a-z-]*)\s+(?:in|to|into)\s+(?:the\s+)?(%s)$" % pat, t, re.I)
        if m:
            return {"intent": "grammar", "form": form, "word": m.group(1).lower()}
        m = re.match(r"^(?:turn|make)\s+([a-z][a-z-]*)\s+(?:in ?to|to)\s+(?:the\s+)?(?:%s)(?:\s+tense)?$"
                     % pat, t, re.I)
        if m:
            return {"intent": "grammar", "form": form, "word": m.group(1).lower()}
    return None


# ---- sentence transforms: whole-sentence grammar asks ------------------------
_SENT_KINDS = (
    r"question|interrogative|negative|past(?:\s+tense)?|simple past|"
    r"future(?:\s+tense)?|continuous|present\s+continuous|progressive|"
    r"ing(?:\s+form)?|imperative|command|exclamation|exclamatory|"
    r"statement|declarative|plural"
)


def _norm_kind(k):
    k = (k or "").strip().lower()
    if k.startswith("past"):
        return "past"
    if k.startswith("fut"):
        return "fut"
    if k in ("continuous", "present continuous", "progressive") or k.startswith("ing"):
        return "cont"
    if k in ("imperative", "command"):
        return "imp"
    if k in ("exclamation", "exclamatory"):
        return "excl"
    if k in ("statement", "declarative"):
        return "q2s"
    if k in ("question", "interrogative"):
        return "ynq"
    if k == "negative":
        return "neg"
    if k == "plural":
        return "plural"
    return None


def _sent_grammar(text):
    """Match a whole-sentence transform ask: 'turn she walks into a
    question', 'question form of does she walk?', 'she walks in past
    tense', 'make a negative: the dog barks'. Multi-word sentences only —
    single words belong to the word-form grammar above. Returns intent
    dict or None."""
    t = text.strip()
    body = t
    kind = None
    m = re.match(r"^(?:make|turn|change|put|convert|rewrite|say)\s+['\"“”]?(.+?)['\"“”]?\s+"
                 r"(?:in ?to|into|to|as)\s+(?:an?\s+|the\s+)?(%s)[?.!]*\s*$"
                 % _SENT_KINDS, t, re.I)
    if m:
        body, kind = m.group(1), m.group(2)
    else:
        m = re.match(r"^(?:make|say|form|give me)\s+(?:an?\s+)?(%s)\s*[:\-—]\s*['\"“”]?(.+?)['\"“”]?[?.!]*\s*$"
                     % _SENT_KINDS, t, re.I)
        if m:
            kind, body = m.group(1), m.group(2)
        else:
            m = re.match(r"^(?:what(?:'s| is)\s+)?(?:the\s+)?(%s)\s+(?:form|version)\s+of\s+"
                         r"['\"“”]?(.+?)['\"“”]?[?.!]*\s*$" % _SENT_KINDS, t, re.I)
            if m:
                kind, body = m.group(1), m.group(2)
            else:
                m = re.match(r"^['\"“”]?(.+?)['\"“”]?\s+(?:in|to)\s+(?:the\s+)?(%s)[?.!]*\s*$"
                             % _SENT_KINDS, t, re.I)
                if m:
                    body, kind = m.group(1), m.group(2)

            if kind is None:
                # 'negative of she walks', 'past tense of the cat sleeps'
                m = re.match(r"^(?:the\s+)?(%s)\s+of\s+['\"\u201c\u201d]?(.+?)['\"\u201c\u201d]?[?.!]*\s*$"
                             % _SENT_KINDS, t, re.I)
                if m:
                    kind, body = m.group(1), m.group(2)
            if kind is None:
                # 'does she walk? as a statement', 'she walks as a question'
                m = re.match(r"^['\"\u201c\u201d]?(.+?)['\"\u201c\u201d]?\s+as\s+(?:a|an|the)?\s*"
                             r"(%s)[?.!]*\s*$" % _SENT_KINDS, t, re.I)
                if m:
                    body, kind = m.group(1), m.group(2)
    if kind is None:
        return None
    k = _norm_kind(kind)
    if not k:
        return None
    sent = body.strip().strip("'\"“”?.! ").strip()
    if not sent or len(sent.split()) < 2:
        return None                      # single words -> word grammar
    if k == "plural":
        return None                      # sentence plural not a task here
    return {"intent": "sentence", "kind": k, "sentence": sent.lower()}


def _compose(text):
    """Match a sentence-composition ask: 'make a sentence with dog and
    swim', 'use moon and wolf in a sentence', 'sentence with the words
    rain and sing'. The words must be taught; the piecing-together is the
    organism's own grammar at work."""
    t = text.strip()
    m = re.match(r"^(?:make|build|write|form|give me|say)\s+(?:me\s+)?"
                 r"(?:a|an|one|another)?\s*(?:new\s+|full\s+)?sentence\s+(?:with|using|from)\s+"
                 r"['\"“”]?(.+?)['\"“”]?[?.!]*\s*$", t, re.I)
    if not m:
        m = re.match(r"^(?:use|put)\s+['\"“”]?(.+?)['\"“”]?\s+in\s+(?:a|one|another)\s+"
                     r"sentence[?.!]*\s*$", t, re.I)
    if not m:
        m = re.match(r"^sentence\s+with\s+(?:the\s+words\s+)?['\"“”]?(.+?)['\"“”]?[?.!]*\s*$",
                     t, re.I)
    if not m:
        return None
    body = m.group(1)
    parts = [p.strip(" '\"") for p in re.split(r",|\band\b", body) if p.strip(" '\"")]
    words = []
    for p in parts:
        w = p.lower().strip()
        w = re.sub(r"^(?:the|a|an)\s+", "", w)
        if w and len(w.split()) == 1:
            words.append(w)
    if not words:
        return None
    return {"intent": "compose", "words": words[:3]}


def _chem(text):
    """Match a chemistry ask: 'symbol of gold', 'what is the formula of
    water', 'react hydrogen and oxygen', 'what does sodium and chlorine
    make'. Returns intent dict or None."""
    t = text.strip().rstrip("?!. ")
    m = re.match(r"^(?:what(?:'s| is)\s+)?(?:the\s+)?symbol\s+(?:of\s+)?([a-z][a-z ]*)$", t, re.I)
    if m:
        return {"intent": "chem", "kind": "symbol", "name": m.group(1).strip().lower()}
    m = re.match(r"^(?:what(?:'s| is)\s+)?(?:the\s+)?(?:chemical\s+)?formula\s+(?:of|for)\s+([a-z][a-z ]*)$", t, re.I)
    if m:
        return {"intent": "chem", "kind": "formula", "name": m.group(1).strip().lower()}
    m = re.match(r"^(?:react|mix|combine)\s+(.+)$", t, re.I)
    if m:
        return {"intent": "chem", "kind": "react", "terms": m.group(1).strip().lower()}
    m = re.match(r"^(?:what do you get (?:if|when) you (?:mix|react|combine|burn)|"
                 r"what does ([a-z]+ and [a-z]+) make)\b", t, re.I)
    if m:
        return {"intent": "chem", "kind": "react",
                "terms": m.group(1).strip().lower() if m.group(1) else t}
    return None


def _maths_ask(text):
    """Match a live maths ask: 'solve f=ma for a with f=10 m=2',
    'solve speed for t v=20 u=2 a=3', 'rearrange v=u+a*t for a',
    'evaluate eq_ke m=1 v=10', 'fuse eq_speed and eq_accel'. Returns an
    intent dict in the task-world shape, or None."""
    t = text.strip().rstrip("?!. ")
    m = re.match(r"^(?:solve|rearrange|evaluate|eval|fuse)\s+(.+)$", t, re.I)
    if not m:
        return None
    kind = t.split()[0].lower()
    kind = {"evaluate": "eval", "eval": "eval"}.get(kind, kind)
    body = m.group(1).strip()
    # split off k=v pairs and the 'for X' / 'with' scaffolding
    toks = body.split()
    target = None
    vals = []
    head = []
    i = 0
    while i < len(toks):
        w = toks[i]
        if w.lower() == "for" and i + 1 < len(toks):
            target = toks[i + 1].lower()
            i += 2
            continue
        if w.lower() == "with":
            i += 1
            continue
        if "=" in w:
            k, v = w.split("=", 1)
            try:
                float(v)
                vals.append(w)
                i += 1
                continue
            except ValueError:
                pass
        head.append(w)
        i += 1
    if kind == "fuse":
        if len(head) >= 3:
            return {"intent": "maths", "kind": "fuse",
                    "input": "fuse %s and %s" % (head[0], head[2])}
        return None
    if not head:
        return None
    eq = head[0]
    if kind == "eval":
        return {"intent": "maths", "kind": "eval",
                "input": "eval %s %s" % (eq, " ".join(vals))}
    if target:
        if kind == "solve":
            return {"intent": "maths", "kind": "solve",
                    "input": "solve %s for %s %s" % (eq, target, " ".join(vals))}
        return {"intent": "maths", "kind": "rearrange",
                "input": "rearrange %s for %s" % (eq, target)}
    return None


def parse(text):
    """Parse to an intent dict. Returns {"intent": ..., ...} — the caller
    (mind.py) decides how to act. This is parsing to *meaning*, not tokens."""
    t = text.strip()
    low = t.lower().rstrip("?!.")

    if low in ("status",):
        return {"intent": "status"}
    if low.startswith("what do you know"):
        return {"intent": "self_report"}

    # arithmetic and grammar before everything — expression-shaped input
    # must never be mistaken for a query about a subject
    a = _arith(t)
    if a:
        return a
    sg = _sent_grammar(t)
    if sg:
        return sg
    cp = _compose(t)
    if cp:
        return cp
    g = _grammar(t)
    if g:
        return g
    ch = _chem(low)
    if ch:
        return ch
    ma = _maths_ask(t)
    if ma:
        return ma

    m = re.match(r"^is\s+(?:a|an|the)\s+(.+?)\s+(?:a|an)\s+(.+?)\??$", low)
    if m:
        return {"intent": "query_isa",
                "x": m.group(1).strip().replace(" ", "_"),
                "y": m.group(2).strip().rstrip("?").replace(" ", "_")}

    m = re.match(r"^is\s+([a-z][a-z _-]*?)\s+(?:a|an)\s+([a-z][a-z _-]*?)\??$", low)
    if m and m.group(1).split()[0] not in ("there", "it", "that", "this",
                                           "he", "she") \
            and "such" not in m.group(1):
        return {"intent": "query_isa",
                "x": m.group(1).strip().replace(" ", "_"),
                "y": m.group(2).strip().rstrip("?").replace(" ", "_")}

    m = re.match(r"^(?:name|list|give me|tell me)\s+(?:me\s+)?(?:some |all |a few )?"
                 r"([a-z]+?)s\b[?.!]*$", low)
    if m:
        return {"intent": "query_members", "cat": m.group(1)}
    m = re.match(r"^what\s+([a-z]+?)s\s+do\s+you\s+know\??$", low)
    if m:
        return {"intent": "query_members", "cat": m.group(1)}

    m = re.match(r"^(?:guess|name)(?:\s+the)?\s+(?:animal|creature|thing|entity|word)"
                 r"\s*[:\-—]\s*(.+)$", low)
    if m:
        return {"intent": "clue_guess", "clues": m.group(1)}
    m = re.match(r"^(.+?)\s*[:\-—]\s*what\s+(?:is|am)\s+(?:it|i)\??$", low)
    if m:
        return {"intent": "clue_guess", "clues": m.group(1)}

    m = re.match(r"^how do you know (?:about )?(.+)$", low)
    if m:
        return {"intent": "provenance", "subject": m.group(1).replace(" ", "_")}

    m = re.match(r"^tell me about (.+)$", low)
    if m:
        return {"intent": "query", "subject": _strip_article(m.group(1)).replace(" ", "_")}

    m = re.match(r"^(?:what is|what are|whats|what'?s|who is|who'?s)\s+(.+)$", low)
    if m:
        return {"intent": "query", "subject": _strip_article(m.group(1)).replace(" ", "_")}

    m = re.match(r"^does\s+(.+?)\s+have\s+(.+)$", low)
    if m:
        return {"intent": "query_attr", "subject": m.group(1).replace(" ", "_"),
                "attr": m.group(2).strip()}

    m = re.match(r"^(?:remember that\s+)?(.+?)\s+has\s+(.+)$", low)
    if m and " is " not in low:
        return {"intent": "fact_attr", "subject": m.group(1).replace(" ", "_"),
                "attr": m.group(2).strip()}

    m = re.match(r"^(?:an?\s+)?(.+?)\s+is\s+(?:an?\s+)?(.+)$", low)
    if m:
        return {"intent": "fact", "subject": _strip_article(m.group(1)).replace(" ", "_"),
                "object": _strip_article(m.group(2)).replace(" ", "_")}

    m = re.match(r"^(?:compute|calculate)\s+(.+)$", low)
    if m:
        nums = _numbers(m.group(1))
        if len(nums) >= 2:
            if any(x in m.group(1) for x in ("+", "plus", "add")):
                return {"intent": "compute", "op": "add", "args": nums[:2]}
            if any(x in m.group(1) for x in ("-", "minus", "subtract")):
                return {"intent": "compute", "op": "sub", "args": nums[:2]}
            if any(x in m.group(1) for x in ("x", "times", "multiply", "multiplied")):
                return {"intent": "compute", "op": "mul", "args": nums[:2]}
            return {"intent": "compute", "op": "add", "args": nums[:2]}

    m = re.match(r"^(?:add|plus)\s+(.+?)\s+(?:and|to)\s+(.+)$", low)
    if m:
        a, b = _num(m.group(1)), _num(m.group(2))
        if a is not None and b is not None:
            return {"intent": "compute", "op": "add", "args": [a, b]}

    m = re.match(r"^(?:multiply|times)\s+(.+?)\s+(?:and|by)\s+(.+)$", low)
    if m:
        a, b = _num(m.group(1)), _num(m.group(2))
        if a is not None and b is not None:
            return {"intent": "compute", "op": "mul", "args": [a, b]}

    m = re.match(r"^next in\s+(.+)$", low) or re.match(r"^(?:continue)\s+(.+)$", low)
    if m:
        nums = _numbers(m.group(1))
        if len(nums) >= 2:
            return {"intent": "sequence", "args": nums}

    m = re.match(r"^(sum|max|min|sort|rsort|unique|reverse|length)\s+(.+)$", low)
    if m:
        op, rest = m.group(1), m.group(2).strip()
        nums = _numbers(rest)
        if op == "reverse" and not nums:
            return {"intent": "strop", "op": "reverse", "arg": rest}
        seq = nums if nums else [w.strip(",") for w in rest.split()]
        return {"intent": "listop", "op": op, "args": seq}

    m = re.match(r"^(reverse|upper|lower|shout)\s+(.+)$", low)
    if m:
        return {"intent": "strop", "op": m.group(1), "arg": m.group(2)}

    return {"intent": "unknown", "text": t}


def is_question(i):
    return i.get("intent") in ("query", "query_attr", "provenance", "self_report")
