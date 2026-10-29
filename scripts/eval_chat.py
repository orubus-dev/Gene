#!/usr/bin/env python3
"""Gene 1.1 evaluation battery.

Verifies the four things Orubus demanded:
  A. PARAPHRASE — same ask in different grammar never yields the same canned
     line and never breaks (the 'someone else chats it' test).
  B. INGENUITY — never-seen words get honest verdicts + grounded hypotheses;
     near-words map to known concepts; taught-real vs taught-mythical vs
     unknown are three different answers.
  C. CREATIVITY — piecing together: novel statements from stored facts,
     different every run.
  D. IMPROVEMENT — self-improvement narrated with real numbers.

Exit code 0 iff all gates pass.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gene.mind import Mind  # noqa: E402

m = Mind()
PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append((name, detail))
    print("%s %-52s %s" % ("PASS" if cond else "FAIL", name, detail[:80]))


print("=" * 76)
print("A. PARAPHRASE BATTERY — grammar invariance + reply adaptation")
print("=" * 76)
IDENTITY_FORMS = ["who are you?", "what's your name?", "introduce yourself",
                  "what do people call you?", "who am I speaking with?",
                  "describe yourself in a line", "what should I call you?"]
replies = []
for f in IDENTITY_FORMS:
    m.rng.seed(hash(f) % 10000)
    r = m.handle_text(f) or ""
    replies.append(r)
    named = re.search(r"\bgene\b", r, re.I)
    vers = bool(re.search(r"\d", r))
    check("identity forms: %r" % f[:34], bool(named and vers and len(r) > 10),
          r[:60])
distinct = len(set(replies)) == len(replies)
check("identity: all %d replies DISTINCT (no canned echo)" % len(replies), distinct,
      "%d distinct" % len(set(replies)))

GREET_FORMS = ["hi", "hello there", "hey you!", "greetings, machine", "yo yo",
               "good morning", "hiya!!"]
greplies = [m.handle_text(f) or "" for f in GREET_FORMS]
check("greeting: 7 forms all answered", all(len(r) >= 10 for r in greplies))
check("greeting: all distinct", len(set(greplies)) == len(greplies))

print()
print("=" * 76)
print("B. INGENUITY BATTERY — the zorpus test")
print("=" * 76)
UNKNOWN = ["what is a zorpus?", "does a zorpus exist?", "have you heard of a flurg?",
           "is there such a thing as a blorp?", "what is a zorp?"]
for u in UNKNOWN:
    r = m.handle_text(u) or ""
    honest = re.search(r"never heard|no match|don't know|new word to me|no record|honest answer: unknown", r, re.I)
    grounded = re.search(r"creature|latin|teach me|world|closest", r, re.I)
    check("unknown: %r" % u[:42], bool(honest and grounded and "teacher" not in r.lower()),
          r[:64])

NEAR = [("what is a dawg?", "dog"), ("what is a kitty?", "cat"),
        ("what is a doggo?", "dog")]
for q, target in NEAR:
    r = m.handle_text(q) or ""
    check("near-match: %r -> %s" % (q[:30], target), target in r.lower(), r[:64])

r = m.handle_text("what is a seacow?") or ""
check("compound: seacow decomposed", ("sea" in r.lower() and "cow" in r.lower()
                                      and ("theory" in r.lower() or "apart" in r.lower()
                                           or "inference" in r.lower())), r[:64])

REAL = ["have you heard of quokkas?", "what is a platypus?", "do tardigrades exist?",
        "have you heard of the magnapinna squid?", "do you know about octopuses?"]
for q in REAL:
    r = m.handle_text(q) or ""
    confirms = re.search(r"real|is a|is an|creature|animal|mammal", r, re.I)
    denies = re.search(r"never heard|don't know|no match|no record", r, re.I)
    check("taught-real: %r confirmed" % q[:38], bool(confirms and not denies), r[:64])

MYTH = ["do dragons exist?", "have you heard of unicorns?", "what is a phoenix?"]
for q in MYTH:
    r = m.handle_text(q) or ""
    classified = re.search(r"mythical|stories|legend|not in nature", r, re.I)
    check("taught-mythical: %r classified" % q[:38], bool(classified), r[:64])

print()
print("=" * 76)
print("C. CREATIVITY BATTERY — piecing things together")
print("=" * 76)
GROUNDING = set()
import json
for fn in os.listdir(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "curriculum")):
    if fn.endswith(".json"):
        for c in json.load(open(os.path.join(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__))), "curriculum", fn))).get("concepts", []):
            GROUNDING.add(c["id"].replace("_", " ").lower())
            GROUNDING.update(w.lower() for w in c.get("words", []))

PROMPTS = ["tell me something new you figured out",
           "make me a connection between two things you know",
           "what have you derived on your own lately?",
           "surprise me", "what connections do you see in your graph?"]
all_creative = []
for p in PROMPTS:
    r1 = m.handle_text(p) or ""
    m.rng.seed(1234)
    r2 = m.handle_text(p) or ""
    grounded = sum(1 for g in GROUNDING if g in r1.lower()) >= 1
    connective = re.search(r"both|share|like|connect|link|blend|between|infer|conclude|derive|hypothes|theory|nearest|junction", r1, re.I)
    check("creativity: %r" % p[:44], bool(r1 and connective and grounded and len(r1) > 40),
          r1[:64])
    all_creative.append((p, r1, r2))
varied = all(r1 != r2 for _, r1, r2 in all_creative)
check("creativity: repeat ask yields DIFFERENT composition", varied)

print()
print("=" * 76)
print("D. IMPROVEMENT BATTERY — self-improvement narrative")
print("=" * 76)
for q in ["are you getting better at numbers?", "how much have you improved?",
          "quantify your growth for me", "what did you used to fail at that you solve now?"]:
    r = m.handle_text(q) or ""
    ok = (re.search(r"\d", r) and re.search(r"better|improv|climbing|growth|steady|curve|ledger|receipts|quantified", r, re.I)) \
        or re.search(r"too early|just started", r, re.I)
    check("improvement: %r" % q[:46], bool(ok), r[:64])

print()
print("=" * 76)
print("E. STRESS — 120 turns, cop-out and echo detection")
print("=" * 76)
import random
rng = random.Random(42)
POOL = (IDENTITY_FORMS + GREET_FORMS +
        ["how are you?", "what can you do?", "thanks!", "ok cool", "you're smart",
         "are you chatgpt?", "what do you wonder about?", "are you getting better?",
         "do blimps exist?", "what is a zorp?", "tell me about whales",
         "compute 3 plus 4", "next in 2 4 6 8", "status"])
cop_outs = 0
broken = 0
repeats = 0
seen_reply = {}
for i in range(120):
    t = rng.choice(POOL)
    r = m.handle_text(t) or ""
    if not r or len(r) < 6:
        broken += 1
    if re.search(r"my teacher|question queued|i'll ask|waiting for my", r, re.I):
        cop_outs += 1
    h = hash(r.strip().lower())
    seen_reply[h] = seen_reply.get(h, 0) + 1
repeats = sum(1 for c in seen_reply.values() if c > 6)
check("stress: 120 turns, %d broken, %d cop-outs" % (broken, cop_outs),
      broken == 0 and cop_outs == 0)
check("stress: no reply overused (>6 of 120)", repeats == 0,
      "%d distinct replies" % len(seen_reply))

print()
print("=" * 76)
print("RESULT: %d passed, %d failed" % (len(PASS), len(FAIL)))
print("=" * 76)
sys.exit(1 if FAIL else 0)
