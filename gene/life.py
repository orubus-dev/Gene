"""CLI — the organism's life cycles.

    python -m gene awaken            # first breath: create/confirm state
    python -m gene teach CURRICULUM  # digest a lesson pack
    python -m gene train --budget N  # a waking session of trial-and-error
    python -m gene sleep             # replay, consolidate, prune
    python -m gene evolve --gens N   # select over the gene pool
    python -m gene live              # chat with the organism (stdin)
    python -m gene demo              # scripted demonstration
    python -m gene status            # state of the organism
"""
import argparse
import json
import os
import sys

from .mind import Mind


def cmd_awaken(mind):
    mind.persist()
    return "awake. concepts=%d skills=%d — nothing known, everything possible." % (
        len(mind.graph.nodes), len(mind.genes))


def cmd_teach(mind, path):
    r = mind.teach_file(path)
    mind.persist()
    return "taught: %d concepts, %d examples queued as experience." % (
        r["concepts"], r["examples"])


def cmd_train(mind, budget, tier):
    r = mind.train(budget=budget, tier=tier)
    mind.persist()
    return ("train cycle %d — %d tasks, %d solved, %d new skills, pool=%d. by domain: %s"
            % (r["tasks"] and mind.progress["cycles"], r["tasks"], r["solved"],
               r["new_genes"], r["pool"],
               ", ".join("%s %d/%d" % (d, v["solved"], v["tasks"])
                         for d, v in sorted(r["by_domain"].items()))))


def cmd_train_chat(mind, budget, tier):
    r = mind.train_chat(budget=budget, start_tier=tier)
    mind.persist()
    return ("chat cycle — %d tasks, %d solved, escalations %d, max tier %d. by intent: %s"
            % (r["tasks"], r["solved"], r["escalations"], r["max_tier"],
               ", ".join("%s %d/%d" % (k, v["solved"], v["tasks"])
                         for k, v in sorted(r["by_intent"].items()))))


def cmd_sleep(mind):
    r = mind.sleep()
    mind.persist()
    return "sleep — replayed %d episodes, consolidated %d, pruned %d, concepts now %d." % (
        r["replayed"], r["consolidated"], r["pruned"], r["concepts"])


def cmd_evolve(mind, gens):
    r = mind.evolve(gens=gens)
    mind.persist()
    return "evolve — %d generations, pool now %d genes." % (r["generations"], r["pool"])


def cmd_status(mind):
    return mind.status_text()


def cmd_demo(mind):
    lines = []

    def say(who, text):
        lines.append("%s: %s" % (who, text))

    say("you", "what is gene")
    say("gene", mind.handle_text("what is gene"))
    say("you", "gene is an organism that learns")
    say("gene", mind.handle_text("gene is an organism that learns"))
    say("you", "what is gene")
    say("gene", mind.handle_text("what is gene"))
    say("you", "compute 7 plus 5")
    say("gene", mind.handle_text("compute 7 plus 5"))
    say("you", "next in 2 4 6 8 10")
    say("gene", mind.handle_text("next in 2 4 6 8 10"))
    say("you", "sum 3 9 4")
    say("gene", mind.handle_text("sum 3 9 4"))
    say("you", "reverse helix")
    say("gene", mind.handle_text("reverse helix"))
    say("you", "what is a zorp")
    say("gene", mind.handle_text("what is a zorp"))
    say("you", "how do you know gene")
    say("gene", mind.handle_text("how do you know gene"))
    say("you", "status")
    say("gene", mind.handle_text("status"))
    mind.persist()
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="gene", description="the gene organism")
    ap.add_argument("command", choices=["awaken", "teach", "train", "trainchat",
                                        "sleep", "evolve", "live", "demo", "status"])
    ap.add_argument("path", nargs="?", help="curriculum file for teach")
    ap.add_argument("--budget", type=int, default=40)
    ap.add_argument("--tier", type=int, default=1)
    ap.add_argument("--gens", type=int, default=2)
    a = ap.parse_args(argv)

    mind = Mind()
    if a.command == "awaken":
        print(cmd_awaken(mind))
    elif a.command == "teach":
        if not a.path:
            sys.exit("teach needs a curriculum file")
        print(cmd_teach(mind, a.path))
    elif a.command == "train":
        print(cmd_train(mind, a.budget, a.tier))
    elif a.command == "trainchat":
        print(cmd_train_chat(mind, a.budget, a.tier))
    elif a.command == "sleep":
        print(cmd_sleep(mind))
    elif a.command == "evolve":
        print(cmd_evolve(mind, a.gens))
    elif a.command == "status":
        print(cmd_status(mind))
    elif a.command == "demo":
        print(cmd_demo(mind))
    elif a.command == "live":
        print("gene organism live. talk; ctrl-C to rest.")
        while True:
            try:
                text = input("you> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\ngene: resting. state saved.")
                mind.persist()
                break
            if not text:
                continue
            print("gene> " + mind.handle_text(text))
            mind.persist()


if __name__ == "__main__":
    main()
