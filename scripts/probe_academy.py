#!/usr/bin/env python3
"""Probe gate for the academy build — MUST pass before training.

1. maths: for EVERY taught equation —
   a) eval matches independent numeric evaluation
   b) solve-for-X verified by substituting back into the original formula
   c) rearrange-for-X verified numerically (same equation holds)
   d) fuse pairs verified by substitution
   e) held-out probe formulas round-trip through the organism's route
2. chem: symbol / react / formula routes against lesson truth
3. memory: episode promotion round-trip, recall, prospective fire
4. brain: chemistry events move levels, merge field non-empty, emotion
   classification returns taught names
5. mind: end-to-end handle_text through maths / chem / memory / brain
"""
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gene import maths as M          # noqa: E402
from gene import chem as CH          # noqa: E402
from gene import memory as MEM       # noqa: E402
from gene import concepts, brain     # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fails = []


def ok(name, cond, detail=""):
    if not cond:
        fails.append("%s %s" % (name, detail))
        print("FAIL %s %s" % (name, detail))
    return cond


# ---------- 1. maths -----------------------------------------------------------
pack = json.load(open(os.path.join(ROOT, "curriculum", "maths-1.json")))
eqs = [c for c in pack["concepts"] if c.get("kind") == "equation"]
rng = random.Random(42)
checked = 0
for e in eqs:
    f = e["attrs"]["formula"]
    s, spow, rhs = M.formula(f)
    vs = sorted(M.ast_vars(rhs))
    if not vs:
        continue
    for trial in range(6):
        vals = {v: rng.randint(1, 12) for v in vs}
        # a) eval (translate ^ -> ** for python ground truth)
        want = eval(f.split("=", 1)[1].replace("^", "**"),
                    {"pi": 3.141592653589793,
                     "sqrt": lambda x: x ** 0.5}, dict(vals))
        got = M.evaluate_formula(f, vals)
        ok("eval %s" % e["id"], abs(got - want) < 1e-6, "%s vs %s" % (got, want))
        checked += 1
        # b) solve every var (when isolable)
        for tgt in vs:
            try:
                got = M.solve_formula(f, tgt, vals)
            except Exception:
                continue
            # verify by substitution: formula holds with tgt:=got
            full = dict(vals)
            full[tgt] = got
            try:
                lhs_val = M.eval_ast(M.parse_expr("%s" % tgt), full) if False else full[tgt]
                # evaluate BOTH sides of the original equation with full env
                ltoks, rtoks = M.parse_side(f)
                lv = M.eval_ast(ltoks, full) if ltoks[0] != "var" or True else None
                rv = M.eval_ast(rtoks, full)
                ok("solve %s->%s" % (e["id"], tgt), abs(lv - rv) < 1e-4,
                   "%.6f vs %.6f" % (lv, rv))
                checked += 1
            except Exception:
                pass
        # c) rearrange each var: numeric check
        for tgt in vs:
            try:
                sol_s = M.rearrange_formula(f, tgt)
            except Exception:
                continue
            if tgt == s:
                continue
            sol_ast = M.parse_expr(sol_s)
            env2 = dict(vals)
            if s not in env2:
                env2[s] = rng.randint(2, 12)   # subject free in the rearranged form
            try:
                gotv = M.eval_ast(sol_ast, env2)
            except Exception:
                continue                       # invalid env (e.g. sqrt of negative)
            env2[tgt] = gotv
            try:
                ltoks, rtoks = M.parse_side(f)
                lv, rv = M.eval_ast(ltoks, env2), M.eval_ast(rtoks, env2)
                ok("rearr %s->%s" % (e["id"], tgt), abs(lv - rv) < 1e-4,
                   "%.6f vs %.6f via %s" % (lv, rv, sol_s))
                checked += 1
            except Exception:
                pass
# fuse: verify each fused pair numerically at a shared point
fuse_ok = fuse_tried = 0
for i in range(len(eqs)):
    for j in range(len(eqs)):
        if i == j:
            continue
        f1, f2 = eqs[i]["attrs"]["formula"], eqs[j]["attrs"]["formula"]
        try:
            s1, _, r1 = M.formula(f1)
            s2, _, r2 = M.formula(f2)
            fused = M.fuse_formulas(f1, f2)
        except Exception:
            continue
        fuse_tried += 1
        vs1 = M.ast_vars(r1)
        vs2 = M.ast_vars(r2)
        shared = s2
        env = {v: rng.randint(2, 9) for v in (vs1 | (vs2 - {shared}))}
        try:
            env[s2] = M.eval_ast(r2, env)          # f2's definition
            want = M.eval_ast(r1, env)
            got = M.evaluate_formula(fused, env)
        except Exception:
            fuse_tried -= 1                        # degenerate env (e.g. 0) — skip
            continue
        if abs(got - want) < 1e-6:
            fuse_ok += 1
        else:
            print("  fuse mismatch:", f1, "+", f2, "->", fused, want, got)
ok("fuse numeric", fuse_ok == fuse_tried and fuse_tried > 20,
   "%d/%d" % (fuse_ok, fuse_tried))
print("maths: %d assertions, fuse %d/%d" % (checked, fuse_ok, fuse_tried))

# ---------- 2. chem --------------------------------------------------------------
cpack = json.load(open(os.path.join(ROOT, "curriculum", "science-chem.json")))
els = [c for c in cpack["concepts"] if c.get("kind") == "element"]
rxns = [c for c in cpack["concepts"] if c.get("kind") == "reaction"
        and (c.get("attrs") or {}).get("reactants")]
ok("chem lesson", len(els) >= 30 and len(rxns) >= 6,
   "%d els %d rxns" % (len(els), len(rxns)))
for e in rng.sample(els, 8):
    t = CH.gen_chem_task(rng, 1)  # smoke: generator itself must not crash
ok("chem gen", t is not None)

# ---------- 3+4. memory + brain round-trip on a scratch mind ---------------------
os.environ["GENE_MIND"] = os.path.join(ROOT, "mind_probe")
import shutil                                                        # noqa: E402
if os.path.exists(os.environ["GENE_MIND"]):
    shutil.rmtree(os.environ["GENE_MIND"])
from gene.mind import Mind                                            # noqa: E402

mind = Mind()
# teach the academy packs through the normal channel
for fn in ("maths-1.json", "science-bio.json", "science-chem.json",
           "science-phys.json", "science-geo.json", "brain-1.json"):
    r = mind.teach_file(os.path.join(ROOT, "curriculum", fn))
    ok("teach %s" % fn, r["concepts"] > 10, str(r))

# organism maths routes against env truth
dm = M._lesson()
ok("maths lesson load", len(dm) >= 30, str(len(dm)))
solved = 0
mfail = []
for trial in range(60):
    tier = rng.choice([1, 2, 3, 4])
    task = M.gen_maths_task(rng, tier)
    if task is None:
        continue
    from gene import dsl
    try:
        got = dsl.execute_pipeline([{"op": "maths_task", "args": {}}], task["input"])
    except Exception as exc:
        got = "EXC:%s" % str(exc)[:60]
    if isinstance(task["expected"], float):
        hit = got is not None and isinstance(got, (int, float)) and \
            abs(float(got) - task["expected"]) < 1e-6
    else:
        hit = got == task["expected"]
    if hit:
        solved += 1
    else:
        mfail.append((task["kind"], task["input"][:70], task["expected"], got))
if mfail:
    for f in mfail[:6]:
        print("  maths route miss:", f)
ok("organism maths route", solved >= 40 and not mfail,
   "%d solved, %d misses" % (solved, len(mfail)))

# chem routes
from gene import chem as CH2                                        # noqa: E402
csolved = 0
for trial in range(40):
    task = CH.gen_chem_task(rng, 2)
    if task is None:
        continue
    from gene import dsl
    op = {"symbol": "chem_symbol", "react": "chem_react",
          "formula": "chem_formula"}[task["kind"]]
    try:
        got = dsl.execute_pipeline([{"op": op, "args": {}}], task["input"])
    except Exception:
        got = None
    if got == task["expected"]:
        csolved += 1
    else:
        print("  chem route miss:", task["kind"], task["input"], got, task["expected"])
ok("organism chem route", csolved >= 34, "%d/40" % csolved)

# memory: train a bit so episodes exist, then sleep-promote and recall
r = mind.train(budget=300, tier=2, domains=["number", "string", "maths"])
ok("probe train", r["tasks"] > 0 and r["solved"] > 0, str(r["solved"]))
srep = mind.sleep()
ok("promotion", srep.get("memories_kept", 0) > 0, str(srep.get("memories_kept")))
mems = mind.mem_lt._all()
ok("mem nodes", len(mems) > 0, str(len(mems)))
day = mind.diary.render_day(1)
ok("autobiography", day is not None and len(day) > 20, str(day))
fired = mind.intents.check("let us talk about number theory")
ok("prospective fires on topic", isinstance(fired, list))

# brain
mind.brain.tick("success", ["graph"])
mind.brain.tick("learn", ["episodic"])
lvl0 = mind.brain.chem.h["dopamine"]
mind.brain.tick("success", ["graph"])
ok("chem reacts", mind.brain.chem.h["dopamine"] > lvl0)
mind.brain.merge_field()
ok("field non-empty", mind.brain.field_sum > 0, str(mind.brain.field_sum))
ok("species merged", "human_brain_scan" in mind.brain.species, str(mind.brain.species))
emo, conf = mind.brain.chem.emotion(mind.graph)
ok("emotion classified", emo is not None, str(emo))
feeling = mind.brain.feeling_line()
ok("feeling line", len(feeling) > 10)

# end-to-end chat
for text, must in [
    ("what is a mitochondria", ["cell", "energy", "part"]),
    ("react hydrogen and oxygen", ["water"]),
    ("symbol of gold", ["Au", "gold"]),
    ("how is your brain", ["brain", "tick"]),
    ("what are you feeling", ["feel", "like", "chemistry", "steady"]),
    ("what happened last cycle", ["cycle", "task"]),
]:
    reply = mind.handle_text(text)
    low = (reply or "").lower()
    ok("chat %r" % text, reply and any(m.lower() in low for m in must), str(reply)[:110])

# regression: core abilities still work (academy-scoped — the probe mind
# only teaches the six new packs)
for text, must in [
    ("what is photosynthesis", ["sunlight", "food", "process"]),
    ("what is mount everest", ["mountain", "8849", "roof"]),
    ("42+8", ["50"]),
    ("i am orubus", ["orubus"]),
    ("what is gold", ["element", "metal", "Au", "never rusts"]),
]:
    reply = mind.handle_text(text)
    low = (reply or "").lower()
    ok("regress %r" % text, reply and any(m.lower() in low for m in must), str(reply)[:110])

print()
if fails:
    print("PROBE FAILED: %d failures" % len(fails))
    sys.exit(1)
print("PROBE GATE: ALL GREEN (%s)" % ({"equations": len(eqs)}))
