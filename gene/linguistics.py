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
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}


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


def parse(text):
    """Parse to an intent dict. Returns {"intent": ..., ...} — the caller
    (mind.py) decides how to act. This is parsing to *meaning*, not tokens."""
    t = text.strip()
    low = t.lower().rstrip("?!.")

    if low in ("status",):
        return {"intent": "status"}
    if low.startswith("what do you know"):
        return {"intent": "self_report"}

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
