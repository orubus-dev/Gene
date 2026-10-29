#!/usr/bin/env python3
"""Baseline probe: (1) paraphrase robustness, (2) ingenuity on unknowns,
(3) creativity, (4) self-improvement narrative. Run before/after upgrades."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gene.mind import Mind

m = Mind()
m.rng.seed(7)

print("=" * 72)
print("PROBE 1 — paraphrase robustness (same ask, different grammar)")
print("=" * 72)
forms = [
    "who are you?",
    "what's your name?",
    "introduce yourself",
    "what do people call you?",
    "where are you from?",
    "who made you?",
    "what are you made of?",
    "tell me about yourself",
]
for f in forms:
    r = m.handle_text(f)
    print("you> %-32s" % f)
    print("gene> %s" % ((r or "(fell through to generic)")[:160].replace("\n", " ")))
    print()

print("=" * 72)
print("PROBE 2 — ingenuity on never-seen words")
print("=" * 72)
for f in ["what is a zorpus", "what is a zorp", "do blorps exist?",
          "what is a dawg", "what is a seacow", "have you heard of flurg"]:
    r = m.handle_text(f)
    print("you> %-32s" % f)
    print("gene> %s" % ((r or "(fell through to generic)")[:200].replace("\n", " ")))
    print()

print("=" * 72)
print("PROBE 3 — creativity (piece things together)")
print("=" * 72)
for f in ["tell me something new you figured out",
          "make me a connection between two things you know",
          "what do you wonder about?"]:
    r = m.handle_text(f)
    print("you> %-32s" % f)
    print("gene> %s" % ((r or "(fell through to generic)")[:200].replace("\n", " ")))
    print()

print("=" * 72)
print("PROBE 4 — self-improvement narrative")
print("=" * 72)
for f in ["are you getting better at numbers?", "how much have you improved?"]:
    r = m.handle_text(f)
    print("you> %-40s" % f)
    print("gene> %s" % ((r or "(fell through to generic)")[:200].replace("\n", " ")))
    print()
