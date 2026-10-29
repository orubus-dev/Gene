#!/usr/bin/env python3
"""Dev probe (teacher-side): teach the real packs into an in-memory graph,
wire it like Mind does, then check EVERY generated sentence/taxonomy task
has at least one candidate pipeline that reproduces the expected output.
Build-time sanity gate — catches env/ops/lesson drift before training."""
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gene import concepts as CX, dsl, sent_world, taxonomy  # noqa: E402


def teach_into(graph, packs):
    """Same digestion as Knowledge.teach: ensure + explicit kind + relations."""
    for pack in packs:
        for c in pack.get("concepts", []):
            node = graph.ensure(c["id"], attrs=c.get("attrs") or {},
                                words=c.get("words") or ())
            if c.get("kind"):
                node["kind"] = c["kind"]
            for r in c.get("relations") or ():
                graph.relate(c["id"], r.get("to"), rel=r.get("rel", "assoc"),
                             strength=float(r.get("strength", 0.5)))


def build_graph():
    g = CX.ConceptGraph()
    cdir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "curriculum")
    packs = []
    for fn in ("sent-grammar.json", "vocab-verbs.json", "vocab-nouns.json",
               "vocab-adj.json", "grammar-1.json"):
        with open(os.path.join(cdir, fn)) as f:
            packs.append(json.load(f))
    teach_into(g, packs)
    return g


def main():
    rng = random.Random(11)
    g = build_graph()
    dsl.set_word_graph(g)
    dsl.set_word_resolver(lambda w: (g.lookup_word(w) or {}).get("attrs", {}))

    n_task, n_route, n_fail = 0, 0, 0
    fails = {}
    for tier in (1, 2, 3, 4):
        for _ in range(220):
            task = sent_world.gen_sentence_task(rng, tier)
            exp = task["expected"]
            got, hit = None, False
            for steps in sent_world.sentence_pipeline_candidates(rng, task, []):
                try:
                    got = " ".join(str(dsl.execute_pipeline(steps, task["input"])).split())
                except Exception:
                    continue
                if got == exp:
                    hit = True
                    break
            n_task += 1
            if hit:
                n_route += 1
            else:
                n_fail += 1
                key = (task["kind"], task["input"])
                fails.setdefault(task["kind"], []).append((task["input"], exp, got))
    print("sentence tasks: %d, some-route: %d, no-route: %d"
          % (n_task, n_route, n_fail))
    for kind, lst in fails.items():
        for inp, exp, got in lst[:4]:
            print("  MISS %-5s %-22r env=%-24r cand=%r" % (kind, inp, exp, got))

    # taxonomy tasks: parent + clues graded against the taught graph itself
    tg = CX.ConceptGraph()
    cdir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "curriculum")
    packs = []
    for fn in ("taxonomy-1.json", "taxonomy-2.json", "facts_animals.json"):
        try:
            with open(os.path.join(cdir, fn)) as f:
                packs.append(json.load(f))
        except Exception:
            continue
    teach_into(tg, packs)
    dsl.set_word_graph(tg)          # parent_of reads the organism's wired graph
    dsl.set_word_resolver(lambda w: (tg.lookup_word(w) or {}).get("attrs", {}))
    t_ok, t_n = 0, 0
    for _ in range(300):
        task = taxonomy.gen_taxonomy_task(rng, rng.choice([1, 2, 3]))
        if task is None:
            continue
        t_n += 1
        if task["kind"] == "parent":
            try:
                out = dsl.execute_pipeline([{"op": "parent_of", "args": {}}],
                                           task["input"])
                if out == task["expected"]:
                    t_ok += 1
            except Exception:
                pass
        else:
            res = taxonomy.clue_search(tg, task["input"], topn=1)
            if res and res[0][0] == task["expected"]:
                t_ok += 1
    print("taxonomy tasks: %d, correct: %d (%.1f%%)"
          % (t_n, t_ok, 100.0 * t_ok / max(1, t_n)))
    return 0 if (n_fail == 0 and t_ok >= int(0.9 * t_n)) else 1


if __name__ == "__main__":
    sys.exit(main())
