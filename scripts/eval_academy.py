#!/usr/bin/env python3
"""Academy evaluation battery — boolean-only, run until green x3.

Sections:
  A. maths     — eval/solve/rearrange/fuse on taught equations + held-out probes
  B. chemistry — symbols, reactions, formulas via memory routes and live chat
  C. science   — biology / physics / geography knowledge through the graph
  D. memory    — long-term recall, autobiography, prospective fire, working
  E. brain     — status, feelings, chemical levels, species merge
  F. regression— chat, taxonomy, arithmetic, English transforms

Usage: python3 scripts/eval_academy.py [--verbose]
"""
import json
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gene.mind import Mind          # noqa: E402
from gene import maths as M         # noqa: E402
from gene import dsl                # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERBOSE = "--verbose" in sys.argv
results = []


def check(section, name, cond, detail=""):
    results.append((section, name, bool(cond), detail))
    if not cond or VERBOSE:
        print("%s %-38s %s %s" % ("PASS" if cond else "FAIL", name,
                                  "" if cond else "|", detail if not cond else ""))


mind = Mind()
rng = random.Random(2027)

# ============================ A. maths =========================================
n_pass = 0
n_try = 0
fuse_n = 0
for trial in range(90):
    tier = rng.choice([1, 2, 3, 4])
    task = M.gen_maths_task(rng, tier)
    if task is None:
        continue
    n_try += 1
    try:
        got = dsl.execute_pipeline([{"op": "maths_task", "args": {}}], task["input"])
    except Exception:
        got = None
    if isinstance(task["expected"], float):
        hit = got is not None and isinstance(got, (int, float)) and \
            abs(float(got) - task["expected"]) < 1e-6
    else:
        hit = got == task["expected"]
    if hit:
        n_pass += 1
    if task["kind"] == "fuse" and hit:
        fuse_n += 1
check("A-maths", "taught routes %d/%d" % (n_pass, n_try), n_try >= 50 and n_pass >= 0.92 * n_try,
      "%d/%d" % (n_pass, n_try))
check("A-maths", "fusions solved", fuse_n >= 5, "%d fuse hits" % fuse_n)
# live chat maths
for text, pat in [("compute 42+8", r"50"), ("what is 9x7", r"63")]:
    r = mind.handle_text(text) or ""
    check("A-maths", "live %r" % text, re.search(pat, r), r[:60])

# ============================ B. chemistry =====================================
for text, must in [("symbol of oxygen", ["O", "oxygen"]),
                   ("symbol of gold", ["Au"]),
                   ("what is the formula of water", ["h2o", "H2O"]),
                   ("react hydrogen and oxygen", ["water"]),
                   ("mix sodium and chlorine", ["salt"]),
                   ("react carbon and oxygen", ["carbon dioxide"])]:
    r = mind.handle_text(text) or ""
    low = r.lower()
    check("B-chem", text, any(m.lower() in low for m in must), r[:70])

# ============================ C. science =======================================
SCI = [
    ("what is a mitochondria", ["energy", "cell"]),
    ("what is dna", ["instructions", "helix", "life", "genes"]),
    ("what is photosynthesis", ["sunlight", "food", "process"]),
    ("what is gravity", ["pull", "toward", "force", "gravity"]),
    ("what is mount everest", ["mountain", "8849", "roof", "himalayas"]),
    ("what is the nile", ["river", "6650", "longest", "egypt"]),
    ("what is japan", ["tokyo", "country", "asia", "japanese"]),
    ("what is the pacific ocean", ["largest", "ocean", "asia"]),
    ("what is a neuron", ["signal", "cell", "brain", "carrying"]),
    ("what is rust", ["iron", "oxygen", "eats", "flaky"]),
    ("is gold a metal", ["yes", "gold"]),
    ("what is lightning", ["static", "discharge", "electric", "sky"]),
    ("what is africa", ["continent", "sahara", "humankind", "nile"]),
    ("what is the sahara", ["desert", "largest", "hot", "africa"]),
    ("what is an enzyme", ["protein", "speeds", "chemistry"]),
]
hits = 0
for text, must in SCI:
    r = mind.handle_text(text) or ""
    low = r.lower()
    hit = any(m.lower() in low for m in must)
    hits += hit
    check("C-science", text, hit, r[:80])
check("C-science", "science battery", hits >= 13, "%d/%d" % (hits, len(SCI)))
# members of a science category
r = mind.handle_text("name some elements") or ""
check("C-science", "name some elements",
      any(w in r.lower() for w in ("hydrogen", "oxygen", "gold", "iron")), r[:80])

# ============================ D. memory ========================================
mems = mind.mem_lt._all()
check("D-memory", "long-term memories exist", len(mems) >= 20, str(len(mems)))
r = mind.handle_text("what happened last cycle") or ""
check("D-memory", "last cycle narrative", bool(re.search(r"\d", r)) and
      any(w in r.lower() for w in ("cycle", "cracked", "task")), r[:90])
r = mind.handle_text("tell me about your day") or ""
check("D-memory", "autobiography", len(r) > 30 and any(
    w in r.lower() for w in ("cycle", "cracked", "standout", "felt")), r[:90])
r = mind.handle_text("what was your hardest failure") or ""
check("D-memory", "hardest failure", any(w in r.lower() for w in ("sting", "failed", "wall", "memory")), r[:90])
# when did you learn X — pick a real memory topic
if mems:
    topic = (mems[0].get("attrs") or {}).get("words", "")
    r = mind.handle_text("when did you learn about %s" % topic) or ""
    check("D-memory", "when learned %r" % topic,
          bool(re.search(r"\d", r)) and any(w in r.lower() for w in ("cycle", "found", "learned", "memory")), r[:90])
# prospective: add an intention, then walk the topic past
it = mind.intents.add("when volcanoes come up, mention the magma chamber", topic="volcanoes")
r = mind.handle_text("let us talk about volcanoes") or ""
check("D-memory", "prospective fires", "magma" in r.lower() or "side note" in r.lower(), r[:110])
# working memory: topic tracked
check("D-memory", "working topic tracked", mind.working.d["topic"] in ("volcanoes", "talk"), str(mind.working.d["topic"]))
r = mind.handle_text("what do you remember") or ""
check("D-memory", "memory inventory", bool(re.search(r"\d", r)), r[:90])

# ============================ E. brain =========================================
r = mind.handle_text("how is your brain") or ""
check("E-brain", "brain status", any(w in r.lower() for w in ("brain", "tick", "region"))
      and bool(re.search(r"\d", r)), r[:90])
r = mind.handle_text("what are you feeling right now") or ""
check("E-brain", "feeling", any(w in r.lower() for w in ("feel", "like", "calm", "baseline",
                                                         "chemistry", "steady", "running"))
      and bool(re.search(r"\d", r)), r[:90])
r = mind.handle_text("what are your dopamine levels") or ""
check("E-brain", "dopamine level", "dopamine" in r.lower() and bool(re.search(r"\d", r)), r[:90])
r = mind.handle_text("show me a brain scan") or ""
check("E-brain", "scan merged", "merged" in r.lower() and "human" in r.lower(), r[:60])
check("E-brain", "species scans merged", len(mind.brain.species) >= 4, str(mind.brain.species))
check("E-brain", "field non-empty", mind.brain.field_sum > 0, str(round(mind.brain.field_sum, 1)))
emo = mind.brain.emotion_word()
check("E-brain", "emotion classified", emo is not None, str(emo))

# ============================ F. regression ====================================
for text, must in [("who are you", ["gene"]),
                   ("hello", ["hello", "hey", "hi"]),
                   ("what is a dog", ["mammal", "canid", "animal", "pet"]),
                   ("turn she walks into a question", ["does she walk"]),
                   ("past tense of go", ["went"]),
                   ("is a whale a fish", ["no", "not", "mammal"]),
                   ("make a sentence with dog and swim", [".", "dog", "swim"]),
                   ("guess the animal: barks, loyal pet, wags tail", ["dog"])]:
    r = mind.handle_text(text) or ""
    low = r.lower()
    check("F-regress", text, any(m.lower() in low for m in must), r[:70])

# ============================ report ===========================================
print()
fails = [(s, n, d) for s, n, ok, d in results if not ok]
tot = len(results)
print("ACADEMY EVAL: %d/%d passed" % (tot - len(fails), tot))
if fails:
    for s, n, d in fails:
        print("  FAIL [%s] %s %s" % (s, n, d))
    sys.exit(1)
print("ALL SECTIONS GREEN")
