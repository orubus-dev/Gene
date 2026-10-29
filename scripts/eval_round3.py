#!/usr/bin/env python3
"""Gene round-3 evaluation battery — the four things Orubus ordered:

  A. ARITHMETIC GENERALIZATION — knows 5+7 => must do 125+6, 3*8, 5/4, 1-3
     (never-taught operands, true signed subtraction, true division).
  B. NATURALNESS — a person doesn't narrate their brain plumbing: everyday
     asks must be answered plainly, with zero machinery vocabulary.
  C. GRAMMAR (part 1) — taught forms answered from memory; UNSEEN regular
     words answered by the discovered rule (real generalization).
  D. EXTRAPOLATION (part 2) — given a fragment of a family, reach the rest
     of the family (the 'evolution pipeline'), labeled as inference.
  E. REGRESSION — core chat battery + stress, plus escalation law intact.

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
    print("%s %-56s %s" % ("PASS" if cond else "FAIL", name, detail[:72]))


# ---------------------------------------------------------------- warm-up ----
# a short honest warm-up: the organism solves real tasks (pass/fail only)
# so the eval measures a trained state, not a blank one.
m.teach_file(os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "curriculum", "math-1.json"))
m.teach_file(os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "curriculum", "grammar-1.json"))
m.train(budget=140, tier=2)
m.train(budget=120, tier=3)
m.train_chat(budget=180, start_tier=2)
m.sleep()

print("=" * 78)
print("A. ARITHMETIC GENERALIZATION — knows 5+7, so: 125+6, 3*8, 5/4, 1-3")
print("=" * 78)
ARITH = [
    ("125+6", "131"), ("3*8", "24"), ("5/4", "1.25"), ("1-3", "-2"),
    ("what is 97+38?", "135"), ("what's 12*12?", "144"),
    ("compute 259 + 164", "423"), ("what is 18-25?", "-7"),
    ("divide 9 by 3", "3"), ("34-7", "27"),
]
for expr, want in ARITH:
    r = m.handle_text(expr) or ""
    ok = want in r and "couldn" not in r.lower() and "haven't" not in r.lower()
    check("%s -> %s" % (expr, want), ok, r[:60])

print()
print("=" * 78)
print("B. NATURALNESS — no machinery narration in everyday speech")
print("=" * 78)
BAN = ("my graph", "in my graph", "hormone", "provenance", "diffable", "in git",
       "episodes", "vector", "hebbian", "causal", "reflex", "my concepts",
       "concept graph", "study list", "curriculum", "tokenizer", "neural",
       "my training", "weights")
EVERYDAY = [
    "how are you?", "thanks a lot!", "goodbye", "what time is it?",
    "what's the weather like?", "ok cool", "you're smart", "what do you do?",
]
for q in EVERYDAY:
    r = m.handle_text(q) or ""
    leaked = [b for b in BAN if b in r.lower()]
    check("natural: %r" % q[:38], bool(r) and not leaked and len(r) < 400,
          (r[:52] + " LEAK:" + ",".join(leaked)) if leaked else r[:52])

# the zorpus test, natural edition: verdict-first, no plumbing talk
for u in ["what is a zorpus?", "does a blimp exist?"]:
    r = m.handle_text(u) or ""
    honest = re.search(r"never heard|no match|don't know|new word to me|no record", r, re.I)
    clean = not any(b in r.lower() for b in BAN)
    check("natural verdict: %r" % u[:38], bool(honest and clean), r[:60])

print()
print("=" * 78)
print("C. GRAMMAR (part 1) — taught forms from memory, UNSEEN words by rule")
print("=" * 78)
TAUGHT = [("past tense of walk", "walked"), ("past tense of go", "went"),
          ("past tense of think", "thought"), ("plural of cat", "cats"),
          ("plural of box", "boxes"), ("past tense of dance", "danced")]
for q, want in TAUGHT:
    r = m.handle_text(q) or ""
    check("grammar taught: %s -> %s" % (q, want), want in r, r[:56])
UNSEEN = [("past tense of climb", "climbed"), ("past tense of float", "floated"),
          ("past tense of smile", "smiled"), ("plural of river", "rivers"),
          ("plural of shadow", "shadows"), ("past tense of reach", "reached")]
for q, want in UNSEEN:
    r = m.handle_text(q) or ""
    check("grammar UNSEEN: %s -> %s" % (q, want), want in r, r[:56])

print()
print("=" * 78)
print("D. EXTRAPOLATION (part 2) — from a fragment, reach the family")
print("=" * 78)
FAMILY = ["statement", "question", "command", "exclamation", "negation", "active",
          "passive", "conditional", "comparative", "superlative", "relative clause",
          "past tense", "present tense", "future tense", "plural", "singular"]
SEED_ASKS = [
    "we have statements and questions — what other grammar types are out there?",
    "grammar has past and present tense — what else belongs in the family?",
    "here are two sentence types: statement, command. complete the family.",
    "extrapolate grammar: given statement, question — derive what else must exist",
]
reached = set()
for q in SEED_ASKS:
    r = m.handle_text(q) or ""
    named = {f for f in FAMILY if f in r.lower()}
    reached |= named
    infer = re.search(r"bet|think|guess|probably|likely|pattern|family|missing|"
                      r"figure|inference|should|shape", r, re.I)
    check("extrapolate: %d new from %r" % (len(named), q[:36]),
          bool(len(named) >= 2 and infer), r[:60])
cov = len(reached) / len(FAMILY)
check("family coverage: %d/%d grammar types reached (%.0f%%)"
      % (len(reached), len(FAMILY), cov * 100), cov >= 0.7,
      "reached: " + ", ".join(sorted(reached)))

# the self-scoring ledger must now hold open guesses
hl = m.progress.get("hypotheses") or {}
check("hypothesis ledger: %d open guesses recorded" % len(hl.get("open", [])),
      len(hl.get("open", [])) >= 5, str(hl.get("hits", 0)) + " hits so far")

print()
print("=" * 78)
print("E. REGRESSION — chat battery + stress + escalation law")
print("=" * 78)
IDENT = ["who are you?", "what's your name?", "introduce yourself",
         "who am I speaking with?", "what should I call you?"]
reps = [m.handle_text(f) or "" for f in IDENT]
check("identity: 5 forms answered, all distinct",
      all(re.search(r"gene", r, re.I) and re.search(r"\d", r) for r in reps)
      and len(set(reps)) == len(reps))
GREET = ["hi", "hello there", "hey you!", "greetings, machine", "yo yo"]
gr = [m.handle_text(f) or "" for f in GREET]
check("greeting: 5 forms all answered distinct",
      all(len(r) >= 10 for r in gr) and len(set(gr)) == len(gr))
NEAR = [("what is a dawg?", "dog"), ("what is a kitty?", "cat")]
for q, target in NEAR:
    r = m.handle_text(q) or ""
    check("near-match: %r -> %s" % (q, target), target in r.lower(), r[:56])
r = m.handle_text("tell me something new you figured out") or ""
check("creativity still grounded", len(r) > 40 and
      re.search(r"both|share|like|connect|link|blend|between|probably", r, re.I), r[:56])
r = m.handle_text("are you getting better?") or ""
check("improvement still quantified", bool(re.search(r"\d", r)) or "too early" in r.lower(), r[:56])

import random
rng = random.Random(7)
POOL = (IDENT + GREET + EVERYDAY + ["how are you?", "thanks!", "what is a zorp?",
        "do octopuses exist?", "125+6", "past tense of jump", "status",
        "what other grammar types are out there?"])
broken = cop = rep_over = 0
seen = {}
sample = {}
for i in range(120):
    t = rng.choice(POOL)
    r = m.handle_text(t) or ""
    if not r or len(r) < 5:
        broken += 1
    if re.search(r"my teacher|question queued|waiting for my|queued for study", r, re.I):
        cop += 1
    h = hash(r.strip().lower())
    seen[h] = seen.get(h, 0) + 1
    sample.setdefault(h, (t, r))
rep_over = sum(1 for c in seen.values() if c > 8)
worst = sorted(seen.items(), key=lambda kv: -kv[1])[:2]
detail = "%d distinct | top: %s" % (len(seen),
        " || ".join("%dx[%s -> %s]" % (c, sample[h][0][:20], sample[h][1][:40])
                    for h, c in worst))
check("stress: 120 turns, %d broken, %d cop-outs" % (broken, cop), broken == 0 and cop == 0)
check("stress: no reply overused (>8/120)", rep_over == 0, detail)

print()
print("=" * 78)
print("RESULT: %d passed, %d failed" % (len(PASS), len(FAIL)))
print("=" * 78)
sys.exit(1 if FAIL else 0)
