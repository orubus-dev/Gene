#!/usr/bin/env python3
"""Part-4 academy massive training run — memory estate + maths + science.

Orubus's directive: all five memory classes, full maths (equations,
derivations, fusions), full science pipelines (biology, chemistry,
physics, geography), the artificial brain in the loop, and the same
absorption pipeline at hundreds-of-thousands scale. Real training only —
the teacher packs went through the normal channel; here it is wake
(boolean tasks, fail->harder), chat (boolean, escalating tiers), sleep
(consolidation + long-term promotion + autobiography + brain rest),
evolve (selection) — checkpointed per invocation.

Usage:
  python3 scripts/full_academy.py wake <b>   # one waking block (10k tasks)
  python3 scripts/full_academy.py chat <b>   # one conversational round
  python3 scripts/full_academy.py summary    # totals so far

Zero facts here. The environment worlds own the physics; the organism
owns its own graph.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gene.mind import Mind  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "mind", "full_academy_run.jsonl")

WAKE_TASKS = int(os.environ.get("GENE_WAKE_TASKS", "10000"))
CHAT_TURNS = int(os.environ.get("GENE_CHAT_TURNS", "1800"))
EVOLVE_EVERY = 5
DOM_ROTATION = [
    ["maths", "taxonomy"],                      # formulary + all sciences
    ["maths", "maths", "taxonomy"],             # maths-heavy
    ["chem", "taxonomy"],                       # reactions + science recall
    ["sentence", "grammar", "maths"],           # language + maths
    ["taxonomy", "chem", "maths"],              # the full academy mix
    ["number", "string", "list", "sequence", "code"],  # part-1 core
    ["maths", "sentence", "taxonomy"],          # blend
    ["chem", "grammar", "maths"],               # symbols + forms
]


def log(rec):
    rec["t"] = round(time.time(), 1)
    with open(LOG, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def read_tier():
    path = os.path.join(ROOT, "mind", "full_academy_state.json")
    try:
        with open(path) as f:
            return json.load(f).get("tier", 4)
    except Exception:
        return 4


def save_tier(tier):
    path = os.path.join(ROOT, "mind", "full_academy_state.json")
    with open(path, "w") as f:
        json.dump({"tier": tier}, f)


def do_wake(b):
    mind = Mind()
    tier = read_tier()
    doms = DOM_ROTATION[(b - 1) % len(DOM_ROTATION)]
    t0 = time.time()
    r = mind.train(budget=WAKE_TASKS, tier=tier, domains=doms)
    rate = r["solved"] / max(1, r["tasks"])
    if rate > 0.9 and tier < 4:
        tier += 1
    cr = {"event": "wake", "block": b, "domains": doms, "tier": tier,
          "tasks": r["tasks"], "solved": r["solved"], "rate": round(rate, 3),
          "genes": len(mind.genes)}
    if b % EVOLVE_EVERY == 0:
        ev = mind.evolve(gens=4)
        cr["evolve_gens"] = ev["generations"]
        cr["pool"] = ev["pool"]
    s = mind.sleep()
    cr["sleep_nodes"] = len(mind.graph.nodes)
    cr["memories_kept"] = s.get("memories_kept", 0)
    cr["memories_total"] = len(mind.mem_lt._all())
    mind.persist()
    log(cr)
    save_tier(tier)
    print("wake %d: %d/%d (%.2f) tier=%d genes=%d mems=%d %.1fs"
          % (b, r["solved"], r["tasks"], rate, tier, len(mind.genes),
             cr["memories_total"], time.time() - t0))


def do_chat(b):
    mind = Mind()
    tier = read_tier()
    t0 = time.time()
    chat = mind.train_chat(budget=CHAT_TURNS, start_tier=tier)
    mind.sleep()
    mind.persist()
    log({"event": "chat", "round": b, "turns": chat["tasks"],
         "solved": chat["solved"],
         "rate": round(chat["solved"] / max(1, chat["tasks"]), 3),
         "max_tier": chat.get("max_tier", "?"),
         "escalations": chat.get("escalations", 0)})
    print("chat %d: %d/%d (%.2f) max_tier=%s esc=%s %.1fs"
          % (b, chat["solved"], chat["tasks"],
             chat["solved"] / max(1, chat["tasks"]), chat.get("max_tier"),
             chat.get("escalations"), time.time() - t0))


def summary():
    tot_w = tot_c = 0
    blocks = chats = 0
    try:
        with open(LOG) as f:
            for ln in f:
                try:
                    rec = json.loads(ln)
                except Exception:
                    continue
                if rec.get("event") == "wake":
                    tot_w += rec["tasks"]
                    blocks += 1
                elif rec.get("event") == "chat":
                    tot_c += rec["turns"]
                    chats += 1
    except FileNotFoundError:
        pass
    print(json.dumps({"wake_blocks": blocks, "wake_tasks": tot_w,
                      "chat_rounds": chats, "chat_turns": tot_c,
                      "absorption_total": tot_w + tot_c}))


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "summary"
    if cmd == "summary":
        summary()
    elif cmd == "wake":
        do_wake(int(sys.argv[2]))
    elif cmd == "chat":
        do_chat(int(sys.argv[2]))


if __name__ == "__main__":
    main()
