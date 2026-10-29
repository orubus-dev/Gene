#!/usr/bin/env python3
"""Bench: how fast does Gene answer, and how much RAM does she use."""
import time, sys, os, resource
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gene.mind import Mind

t0 = time.time()
m = Mind(root="mind")
load_s = time.time() - t0
print(f"LOAD: {load_s:.2f}s to restore full trained mind from disk")

QUESTIONS = [
    ("identity",   "who are you"),
    ("science",    "what does the mitochondria do"),
    ("chem",       "what is the symbol of gold"),
    ("chem-mix",   "react hydrogen and oxygen"),
    ("maths",      "solve eq_ke for v with e=50 m=1"),
    ("memory",     "what do you remember"),
    ("brain",      "how do you feel right now"),
    ("smalltalk",  "hello there"),
]

print(f"\n{'kind':<10} {'latency':>10}  answer head")
print("-" * 70)
for kind, q in QUESTIONS:
    t = time.time()
    r = m.handle_text(q)
    dt = (time.time() - t) * 1000
    reply = r if isinstance(r, str) else (r.get("reply") or r.get("text") or str(r))
    ans = reply[:52].replace("\n", " ")
    print(f"{kind:<10} {dt:>8.1f}ms  {ans}")

rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
print(f"\nRAM: {rss_mb:.0f} MB peak for the whole trained mind")
try:
    n = len(m.graph._nodes)
except AttributeError:
    n = -1
print(f"graph concepts: {n}")
