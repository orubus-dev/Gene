#!/usr/bin/env python3
"""Part-3 full-English massive training run — the real pipeline at scale.

Orubus's directive: full linguistics (entire English foundation), the
entity-database graph wired in, part-1 + part-2 pipelines, absorption in
the hundreds of thousands, no early stopping. This driver runs the SAME
life cycle as every other phase — teach happened through the normal
channel; here it is wake (boolean tasks, fail->harder), chat (boolean,
escalating tiers), sleep (consolidate), evolve (part-2 selection) — at
scale, checkpointed after every step so any number of invocations sum
into one continuous run.

Usage:
  python3 scripts/full_english.py wake <b>   # one waking block (10k tasks)
  python3 scripts/full_english.py chat <b>   # one conversational round
  python3 scripts/full_english.py summary    # totals so far

Zero facts here. The environment worlds (sent_world, taxonomy, chat,
grammar, arithmetic...) own the physics; the organism owns its own graph.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gene.mind import Mind  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "mind", "full_english_run.jsonl")

WAKE_TASKS = int(os.environ.get("GENE_WAKE_TASKS", "10000"))
CHAT_TURNS = int(os.environ.get("GENE_CHAT_TURNS", "1800"))
EVOLVE_EVERY = 5
DOM_ROTATION = [
    ["sentence", "grammar"],
    ["taxonomy", "sentence"],
    ["sentence", "taxonomy", "grammar"],
    ["number", "string", "list", "sequence", "code"],
    ["sentence", "taxonomy"],
]


def log(rec):
    rec["t"] = round(time.time(), 1)
    with open(LOG, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def read_tier():
    path = os.path.join(ROOT, "mind", "full_english_state.json")
    try:
        with open(path) as f:
            return json.load(f).get("tier", 2)
    except Exception:
        return 2


def save_tier(tier):
    path = os.path.join(ROOT, "mind", "full_english_state.json")
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
    mind.persist()
    log(cr)
    save_tier(tier)
    print("wake %d: %d/%d (%.2f) tier=%d genes=%d %.1fs"
          % (b, r["solved"], r["tasks"], rate, tier, len(mind.genes),
             time.time() - t0))


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
