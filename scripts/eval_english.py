#!/usr/bin/env python3
"""Part-3 evaluation battery — full English, the things Orubus ordered:

  A. SENTENCE TRANSFORMS — the gap admitted in v1.2, now closed:
     "she walks" -> "does she walk?" live, across every construction
     (question, negative, past, continuous, future, statement, command),
     with HELD-OUT regular verbs that were never in any lesson pack.
  B. WORD GRAMMAR REGRESSION — word forms still hold.
  C. ENTITY DATABASE — is-a classification, member listing, clue guessing,
     natural descriptions: the taxonomy graph answering through speech.
  D. VOCABULARY BREADTH — random taught entities described correctly;
     unknown things stay honest (no confident invention).
  E. PIECING SENTENCES TOGETHER — compose novel sentences from taught words.
  F. REGRESSION — chat battery still clean.

Exit code 0 iff all gates pass.
"""
import json
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gene.mind import Mind  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
m = Mind()
PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append((name, detail))
    print("%s %-58s %s" % ("PASS" if cond else "FAIL", name, detail[:66]))


def warm():
    m.train(budget=300, tier=2, domains=["sentence", "grammar"])
    m.train(budget=300, tier=3, domains=["taxonomy"])
    m.train(budget=250, tier=4, domains=["sentence", "grammar"])
    m.train(budget=200, tier=3)
    m.train_chat(budget=220, start_tier=2)
    m.sleep()


# ------------------------------------------------------------------ helpers --
def norm(s):
    return " ".join(str(s or "").lower().strip().split())


def has_sentence_form(reply, expect_words):
    r = norm(reply)
    return all(w in r for w in expect_words) and r.endswith(("?", ".", "!")) \
        and len(r.split()) >= 3


# ------------------------------------------------------------------- warm ----
print("warming: 820 boolean tasks through the normal channel...")
warm()
print("=" * 78)
print("A. SENTENCE TRANSFORMS — the v1.2 gap, closed live")
print("=" * 78)
SENT_CASES = [
    # (ask, must-contain words, kind of ending)
    ("turn she walks into a question", ["does", "she", "walk"], "?"),
    ("question form of the dog barks", ["does", "the dog", "bark"], "?"),
    ("make a question: the dogs bark", ["do", "the dogs", "bark"], "?"),
    ("she walks in past tense", ["she", "walked"], "."),
    ("past tense of the cat sleeps", ["the cat", "slept"], "."),
    ("turn the birds sing into past tense", ["the birds", "sang"], "."),
    ("negative of she walks", ["she", "doesn't", "walk"], "."),
    ("make a negative: the dog barks", ["the dog", "doesn't", "bark"], "."),
    ("she walks in future tense", ["she", "will", "walk"], "."),
    ("future of the dogs swim", ["the dogs", "will", "swim"], "."),
    ("continuous of she walks", ["she", "is", "walking"], "."),
    ("turn the dogs bark into present continuous", ["the dogs", "are", "barking"], "."),
    ("does she walk? as a statement", ["she", "walks"], "."),
    ("is she happy? as a statement", ["she", "is", "happy"], "."),
    ("do the dogs bark? as a statement", ["the dogs", "bark"], "."),
    ("imperative of you walk", ["walk"], "!"),
]
for ask, words, end in SENT_CASES:
    r = m.handle_text(ask) or ""
    ok = all(w in r.lower() for w in words) and r.rstrip().endswith(end)
    check(ask[:56], ok, r[:60])

print()
print("-- held-out regular verbs (never in any lesson pack) --")
HELD = ["climb", "march", "glow", "sail", "jog", "greet", "paint",
        "warn", "type", "bolt", "sip", "hum", "stir", "trot", "peck"]
rng = random.Random(42)
held_ok = 0
held_n = 0
for v in HELD:
    for kind, ask, words, end in (
            ("ynq", "question form of the %s %ss" % ("dog", v), ["does", "the dog", v], "?"),
            ("past", "past tense of she %ss" % v, ["she", v + "ed"], "."),
            ("fut", "future of the cat %ss" % v, ["the cat", "will", v], "."),
            ("cont", "continuous of she %ss" % v, ["she", "is", v + "ing"], ".")):
        held_n += 1
        r = m.handle_text(ask) or ""
        ok = all(w in r.lower() for w in words) and r.rstrip().endswith(end)
        held_ok += ok
        if not ok and held_n - held_ok <= 6:
            print("     miss: %-40r -> %r (want %s)" % (ask, r, words))
check("held-out verbs generalize (%d/%d)" % (held_ok, held_n),
      held_ok >= int(0.9 * held_n), "%d/%d" % (held_ok, held_n))

print()
print("=" * 78)
print("B. WORD GRAMMAR REGRESSION")
print("=" * 78)
WORD_CASES = [("past of walk", "walked"), ("plural of fox", "foxes"),
              ("ing of swim", "swimming"), ("past of go", "went"),
              ("third of have", "has")]
for ask, want in WORD_CASES:
    r = m.handle_text(ask) or ""
    check(ask, want in r.lower(), r[:60])

print()
print("=" * 78)
print("C. ENTITY DATABASE — the taxonomy graph, answering in sentences")
print("=" * 78)
ISA = [("is a dog a mammal?", True), ("is a dog a bird?", False),
       ("is a shark a fish?", True), ("is a rose an animal?", False),
       ("is a whale a mammal?", True), ("is a spider an insect?", False),
       ("is an eagle a bird?", True), ("is bread a food?", True)]
for ask, want_yes in ISA:
    r = m.handle_text(ask) or ""
    low = r.lower()
    ok = (("not" in low or "isn't" in low or "no —" in low or low.startswith("no"))
          != want_yes) or (want_yes and re.search(r"\b(yep|yes|right)\b", low))
    # want_yes -> affirmatives pass; want_no -> a denial must appear
    if want_yes:
        ok = bool(re.search(r"\b(yep|yes|right|correct)\b", low)) and \
            not re.search(r"\bnot quite\b|\bisn't\b", low)
    else:
        ok = bool(re.search(r"\bnot\b|isn't|\bno\b|actually", low))
    check(ask, ok, r[:60])

r = m.handle_text("name some mammals") or ""
# the member list is long; the head of the list is depth-ranked, so require
# a real roster (count + several known mammals anywhere in the reply)
listed = [w for w in ("dog", "cat", "fox", "lion", "whale", "bat", "mouse",
                      "rat", "otter", "beaver", "manatee", "elephant", "deer",
                      "moose", "raccoon", "seal", "walrus") if w in r.lower()]
n_shown = r.count(",")
check("name some mammals", ("in all" in r.lower() and n_shown >= 4 and len(listed) >= 2)
      or len(listed) >= 4, "shown=%d listed=%s" % (n_shown + 1, listed[:4]))

CLUES = [("guess the animal: barks, a loyal pet", "dog"),
         ("guess the animal: purrs and whiskers", "cat"),
         ("name the creature: howls at the moon, hunts in packs", "wolf"),
         ("name the word: shading and warming the head", "hat"),
         ("name the word: an iron lattice over paris", "eiffel")]
for ask, want in CLUES:
    r = m.handle_text(ask) or ""
    check(ask[:52], want in r.lower(), r[:60])

r = m.handle_text("what is a dog?") or ""
check("what is a dog? (natural description)",
      "dog" in r.lower() and ("mammal" in r.lower() or "canid" in r.lower()
                              or "barks" in r.lower()), r[:70])

print()
print("-- vocabulary breadth: 30 random taught entities, described from graph --")
cdir = os.path.join(ROOT, "curriculum")
ents = []
for fn in ("taxonomy-1.json", "taxonomy-2.json"):
    with open(os.path.join(cdir, fn)) as f:
        for c in json.load(f)["concepts"]:
            if c.get("kind") == "entity" and c.get("attrs"):
                ents.append(c["id"])
rng = random.Random(7)
sample = rng.sample(sorted(set(ents)), 30)
desc_ok = 0
misses = []
for cid in sample:
    r = m.handle_text("what is a %s?" % cid.replace("_", " ")) or ""
    low = r.lower()
    grounded = cid.replace("_", " ") in low or any(
        str(v).lower() in low for v in
        (json.load(open(os.path.join(cdir, "taxonomy-1.json"))) and {}))
    # grounded = names the thing or one of its taught attrs/parents
    node = m.graph.get(cid) or {}
    attrs = node.get("attrs", {}) or {}
    grounded = (cid.replace("_", " ") in low) or \
        any(str(v).lower()[:12] in low for v in attrs.values() if isinstance(v, str)) or \
        any(p.replace("_", " ") in low for p in [t for _, t, _ in m.graph.neighbors(cid)][:1])
    desc_ok += bool(grounded and len(r) > 10)
    if not (grounded and len(r) > 10):
        misses.append((cid, r[:50]))
check("describes 30 random entities (%d/30)" % desc_ok, desc_ok >= 27,
      "%d/30 %s" % (desc_ok, misses[:2]))

r = m.handle_text("what is a zorpus?") or ""
check("unknown stays honest (zorpus)", re.search(
    r"don't|do not|haven't|new to me|no record|teach me|not sure|never heard",
    r.lower()) is not None, r[:60])

print()
print("=" * 78)
print("E. PIECING SENTENCES TOGETHER — composition from taught words")
print("=" * 78)
COMP = [("make a sentence with dog and swim", ["dog", "swim"]),
        ("use moon and wolf in a sentence", ["moon", "wolf"]),
        ("sentence with the words rain and sing", ["rain", "sing"]),
        ("make a sentence with cat and purr", ["cat", "purr"])]
for ask, words in COMP:
    r = m.handle_text(ask) or ""
    ok = all(w in r.lower() for w in words) and \
        r.rstrip().endswith((".", "!", "?")) and len(r.split()) >= 3 and \
        r[0].isupper()
    check(ask[:54], ok, r[:60])
r = m.handle_text("make a sentence with flurg and swim") or ""
check("compose with unknown word stays honest", re.search(
    r"don't have|new word|teach me", r.lower()) is not None, r[:60])

print()
print("=" * 78)
print("F. REGRESSION — chat battery spot checks")
print("=" * 78)
CHAT = [("who are you?", ["gene", "1.0"]), ("what time is it?", None),
        ("do dragons exist?", None), ("tell me something new", None)]
for ask, _ in CHAT:
    r = m.handle_text(ask) or ""
    low = r.lower()
    if ask == "who are you?":
        ok = "gene" in low and "1.0" in low
    elif ask == "what time is it?":
        ok = re.search(r"no clock|don't|can't|not sure", low) is not None
    elif ask == "do dragons exist?":
        ok = re.search(r"myth|legend|stor|fiction|not real|isn't real|never",
                       low) is not None
    else:
        ok = len(r) > 24 and not re.search(r"as an ai|i cannot", low)
    check("chat: " + ask, ok, r[:60])

print()
print("=" * 78)
total = len(PASS) + len(FAIL)
print("RESULT: %d/%d passed" % (len(PASS), total))
if FAIL:
    print("failed:")
    for name, detail in FAIL:
        print("  -", name, "|", detail)
sys.exit(0 if not FAIL else 1)
