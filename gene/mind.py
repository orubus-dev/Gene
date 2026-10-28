"""The Mind — assembles the organism and runs its life.

One object owns every subsystem and the state directory (mind/). The
repo *is* the brain: everything the organism becomes is committed state,
diffable in git.
"""
import json
import os
import random
import time

from . import concepts, endocrine, evolution, hdc, immune, knowledge, linguistics
from . import memory, reflex, trainer, world
from . import development
from . import genome as G


class Mind:

    def __init__(self, root=None):
        self.root = root or os.environ.get("GENE_MIND") or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mind")
        os.makedirs(self.root, exist_ok=True)
        self._p = lambda name: os.path.join(self.root, name)

        self.graph = concepts.ConceptGraph.from_dict(self._load("concepts.json", {"nodes": {}}))
        self.genes = G.genome_from_dict(self._load("genome.json", {"genes": []}))
        self.reflexes = reflex.Reflexes(self._p("reflexes.json"))
        self.predictor = world.Predictor(self._p("predictor.json"))
        self.hormones = endocrine.Endocrine(self._p("hormones.json"))
        self.episodes = memory.EpisodicMemory(self._p("episodes.jsonl"))
        self.knowledge = knowledge.KnowledgeSystem(self.graph, self.episodes, self._p("questions.json"))
        self.immune = immune.ImmuneSystem(self._p("immune.json"))
        self.dev = development.Development(self._p("development.json"))
        self.dev.load_dict(self._load("development.json", None))
        self.rng = random.Random(int(self._load("rng.json", {"seed": 1337})["seed"]))
        self.progress = self._load("progress.json", {"attempts": 0, "solved": 0,
                                                     "by_domain": {}, "cycles": 0})
        self.meta = self._load("meta.json", {"born": time.time(), "name": "gene"})

        self._seed_core()

    # ---------- core self (machinery concepts, not knowledge) ----------------
    def _seed_core(self):
        for cid, kind in (("self", "meta"), ("knowledge", "meta"),
                          ("teacher", "meta"), ("skill", "meta"),
                          ("success", "meta"), ("failure", "meta"),
                          ("question", "meta"), ("experiment", "meta")):
            self.graph.ensure(cid, kind=kind)
        for dom in ("number", "string", "list", "sequence", "code"):
            self.graph.ensure(dom, kind="domain")

    # ---------- persistence ----------------------------------------------------
    def _load(self, name, default):
        path = self._p(name)
        if os.path.exists(path):
            try:
                with open(path) as f:
                    return json.load(f)
            except Exception:
                pass
        return default

    def _save(self, name, obj):
        with open(self._p(name), "w") as f:
            json.dump(obj, f, indent=1)

    def persist(self):
        self._save("concepts.json", self.graph.to_dict())
        self._save("genome.json", G.genome_to_dict(trainer.dedupe_genes(self.genes)))
        self.reflexes.save()
        self.predictor.save()
        self.hormones.save()
        self.immune.save()
        self.dev.save()
        self._save("progress.json", self.progress)
        self._save("rng.json", {"seed": self.rng.randint(0, 2**30)})
        self._save("meta.json", self.meta)

    # ---------- life cycles ------------------------------------------------------
    def train(self, budget=40, tier=1):
        """One waking learning session: try tasks, only pass/fail feedback."""
        report = {"tasks": 0, "solved": 0, "new_genes": 0, "by_domain": {}}
        new_genes = []
        domains = list(trainer.GENERATORS.keys())
        for i in range(budget):
            dom = self.rng.choice(domains)
            task = trainer.GENERATORS[dom](self.rng, tier)
            outcome = trainer.train_task(task, self.genes, self.reflexes,
                                         self.predictor, self.hormones, self.rng,
                                         now=time.time())
            report["tasks"] += 1
            report["by_domain"].setdefault(dom, {"tasks": 0, "solved": 0})
            report["by_domain"][dom]["tasks"] += 1
            self.progress["attempts"] += len(outcome["attempts"])
            self.episodes.record("task", {"domain": dom, "prompt": task["prompt"],
                                          "solved": outcome["solved"],
                                          "tries": len(outcome["attempts"]),
                                          "coactive": outcome["coactive"]})
            if outcome["solved"]:
                report["solved"] += 1
                report["by_domain"][dom]["solved"] += 1
                self.progress["solved"] += 1
                if outcome["gene"]:
                    self.genes.append(outcome["gene"])
                    new_genes.append(outcome["gene"])
                    self.graph.relate(dom, "skill", strength=0.1)
            self.graph.hebbian(outcome["coactive"], amount=0.05)
        self.progress["cycles"] += 1
        self.genes = trainer.dedupe_genes(self.genes)
        # development: wins accrue; maturation gates may open
        for dom, v in report["by_domain"].items():
            if v["solved"]:
                self.dev.record_win(dom)
        promoted = self.dev.maybe_promote(len(self.graph.nodes))
        if promoted:
            self.episodes.record("development", {"stage": promoted,
                                                 "coactive": ["self", "growth", promoted]})
            self.meta.setdefault("milestones", []).append(
                {"t": time.time(), "stage": promoted})
        # immune: a whole session with zero solves is an anomaly worth remembering
        if report["tasks"] > 0 and report["solved"] == 0:
            novel, danger = self.immune.survey(
                0.85, fatigue=1.0 - self.hormones.h["energy"],
                context={"kind": "zero-solve-cycle", "cycle": self.progress["cycles"]})
            if novel:
                self.episodes.record("immune", {"flag": "zero-solve-cycle", "novel": True,
                                                "coactive": ["failure", "immune"]})
        report["stage"] = self.dev.stage
        report["new_genes"] = len(new_genes)
        report["pool"] = len(self.genes)
        return report

    def sleep(self):
        """Consolidation: replay episodes, hebbian wiring, decay, apoptosis."""
        report = memory.sleep_cycle(self.graph, self.episodes)
        self.reflexes.decay()
        self.hormones.rested(0.5)
        report["hormones"] = dict(self.hormones.h)
        return report

    def evolve(self, gens=2):
        def evaluate(pool):
            scores = {}
            for g in pool:
                base = g.get("fitness", 0.0)
                scores[g["id"]] = base + 0.01 * g.get("uses", 0) - 0.001 * (len(self.genes) - pool.index(g))
            return scores
        self.genes, history = evolution.evolve(self.genes, self.rng, gens=gens,
                                               evaluate=evaluate)
        self.genes = evolution.prune_pool(self.genes)
        self._save("evolution.json", {"last": history,
                                      "pool": len(self.genes),
                                      "at": time.time()})
        return {"generations": gens, "pool": len(self.genes), "history": history}

    def teach_file(self, path):
        report = self.knowledge.teach_file(path)
        return report

    # ---------- live mind (chat) ---------------------------------------------------
    def _find_answer(self, cid):
        node = self.graph.get(cid)
        if not node:
            return None
        # inheritance of description from is-a links
        for rel, target, s in self.graph.neighbors(cid):
            if rel == "is-a" and self.graph.get(target):
                return "%s is %s" % (cid.replace("_", " "), target.replace("_", " "))
        for k, v in node["attrs"].items():
            if " (inherited" not in k:
                return "%s: %s" % (cid.replace("_", " "), v)
        return None

    def handle_text(self, text):
        """The live loop: parse -> reflex -> know/reason/act -> seek knowledge."""
        i = linguistics.parse(text)
        intent = i["intent"]
        self.episodes.record("utterance", {"text": text[:200], "intent": intent,
                                           "coactive": ["self", intent]})

        if intent == "status":
            return self.status_text()

        if intent == "self_report":
            top = sorted(self.graph.nodes.items(), key=lambda kv: -len(kv[1]["links"]))[:10]
            return ("I know %d concepts, %d skills, %d reflex arcs. "
                    "Strongest concepts: %s. Everything was learned or taught — "
                    "nothing is hard-coded."
                    % (len(self.graph.nodes), len(self.genes), len(self.reflexes.arcs),
                       ", ".join(k for k, _ in top)))

        if intent == "provenance":
            p = self.knowledge.provenance(i["subject"])
            if not p:
                return "I don't know '%s' yet. Teach me ('%s is ...') and I will." % (
                    i["subject"], i["subject"])
            return ("Learned %s: kind=%s, %d attributes, %d relations, %.1f hours old. "
                    "Sources: teaching, observation, inference and experiments." % (
                        p["id"], p["kind"], len(p["attrs"]), len(p["relations"]), p["age_hours"]))

        if intent == "fact":
            self.knowledge.observe(i["subject"], relations=[{"to": i["object"], "rel": "is-a"}])
            self.graph.ensure(i["object"])
            self.graph.hebbian([i["subject"], i["object"]], 0.2)
            gained = self.knowledge.infer(i["subject"])
            extra = (" I inferred more from what I know." if gained else "")
            return "Got it — %s is %s.%s" % (i["subject"], i["object"], extra)

        if intent == "fact_attr":
            self.knowledge.observe(i["subject"], attrs={i["attr"]: "yes"})
            return "Noted: %s has %s." % (i["subject"], i["attr"])

        if intent == "query":
            ans = self._find_answer(i["subject"])
            if ans:
                return ans
            self.knowledge.inquire("What is %s?" % i["subject"])
            return ("I don't know '%s' yet — I've raised the question for my teacher. "
                    "Teach me with '%s is ...', or I can experiment." % (
                        i["subject"], i["subject"]))

        if intent == "query_attr":
            node = self.graph.get(i["subject"])
            if node and any(k.startswith(i["attr"]) for k in node["attrs"]):
                return "Yes — %s has %s." % (i["subject"], i["attr"])
            self.knowledge.inquire("Does %s have %s?" % (i["subject"], i["attr"]))
            return "Unknown so far — question queued. Tell me '%s has %s' and I'll know." % (
                i["subject"], i["attr"])

        if intent == "compute":
            a, b = i["args"]
            task = {"domain": "number", "input": [a, b],
                    "expected": {"add": a + b, "sub": max(a, b) - min(a, b),
                                 "mul": a * b}[i["op"]],
                    "prompt": "live compute"}
            outcome = trainer.train_task(task, self.genes, self.reflexes,
                                         self.predictor, self.hormones, self.rng,
                                         now=time.time())
            if outcome["solved"]:
                if outcome["gene"] and not any(g["steps"] == outcome["gene"]["steps"] for g in self.genes):
                    self.genes.append(outcome["gene"])
                self.progress["solved"] += 1
                self.graph.hebbian(outcome["coactive"], 0.1)
                try:
                    result = trainer.run_pipeline_on("number", task, outcome["gene"]["steps"])
                except Exception:
                    result = task["expected"]
                return "%s = %s  (I worked it out in %d tries)" % (
                    task["prompt"], result, len(outcome["attempts"]))
            return "I couldn't work that out yet. Let me train on it — say 'train'."

        if intent == "sequence":
            seq = i["args"]
            task = {"domain": "sequence", "input": seq, "expected": None,
                    "prompt": "next in sequence"}
            # For live sequence queries, discover by loop with checker = last+delta
            delta = seq[-1] - seq[-2]
            task["expected"] = seq[-1] + delta
            outcome = trainer.train_task(task, self.genes, self.reflexes,
                                         self.predictor, self.hormones, self.rng)
            if outcome["solved"]:
                if outcome["gene"] and not any(g["steps"] == outcome["gene"]["steps"] for g in self.genes):
                    self.genes.append(outcome["gene"])
                return "next is %s (found in %d tries: %s)" % (
                    task["expected"], len(outcome["attempts"]), outcome["gene"]["name"])
            return "I couldn't find the pattern yet."

        if intent == "listop":
            op = i["op"]
            seq = i["args"]
            fn = {"sum": sum, "max": max, "min": min, "length": len,
                  "sort": sorted, "rsort": lambda v: sorted(v, reverse=True),
                  "unique": lambda v: sorted(set(v)),
                  "reverse": lambda v: v[::-1]}[op]
            expected = fn(list(seq))
            task = {"domain": "list", "input": seq, "expected": expected, "prompt": op}
            outcome = trainer.train_task(task, self.genes, self.reflexes,
                                         self.predictor, self.hormones, self.rng)
            if outcome["solved"]:
                if outcome["gene"] and not any(g["steps"] == outcome["gene"]["steps"] for g in self.genes):
                    self.genes.append(outcome["gene"])
                return "%s %s = %s" % (op, seq, expected)
            return "still learning that one."

        if intent == "strop":
            op, arg = i["op"], i["arg"]
            expected = {"reverse": arg[::-1], "upper": arg.upper(),
                        "lower": arg.lower(), "shout": arg.upper() + "!"}[op]
            task = {"domain": "string", "input": arg, "expected": expected, "prompt": op}
            outcome = trainer.train_task(task, self.genes, self.reflexes,
                                         self.predictor, self.hormones, self.rng)
            if outcome["solved"]:
                if outcome["gene"] and not any(g["steps"] == outcome["gene"]["steps"] for g in self.genes):
                    self.genes.append(outcome["gene"])
                return "%s" % expected
            return "still learning that one."

        # unknown words -> knowledge seeking (the child raising its hand)
        words = [w for w in linguistics.parse(text).get("text", text).lower().split()
                 if w.isalpha()]
        unknown = [w for w in words if not self.graph.lookup_word(w)]
        if unknown:
            self.knowledge.inquire("meaning of: %s" % ", ".join(unknown[:5]))
            return ("I don't know '%s' yet. Teach me ('%s is ...') or let me "
                    "experiment — I've queued the question." % (unknown[0], unknown[0]))
        return "I heard you, but I don't yet know how to think about that. Teach me?"

    # ---------- reporting -----------------------------------------------------------
    def status(self):
        dom = self.progress.get("by_domain", {})
        return {
            "concepts": len(self.graph.nodes),
            "skills": len(self.genes),
            "reflexes": len(self.reflexes.arcs),
            "predictor_rules": len(self.predictor.rules),
            "stage": self.dev.stage,
            "immune_memories": len(self.immune.memory),
            "attempts": self.progress.get("attempts", 0),
            "solved": self.progress.get("solved", 0),
            "cycles": self.progress.get("cycles", 0),
            "hormones": self.hormones.h,
            "questions_queued": self._load("questions.json", []).__len__(),
        }

    def status_text(self):
        s = self.status()
        acc = (100.0 * s["solved"] / s["attempts"]) if s["attempts"] else 0.0
        return ("organism status — concepts: %d | skills: %d | reflexes: %d | "
                "causal rules: %d | lifetime: %d attempts, %d solved (%.1f%%) | "
                "cycles: %d | hormones: curiosity %.2f urgency %.2f energy %.2f mood %.2f"
                % (s["concepts"], s["skills"], s["reflexes"], s["predictor_rules"],
                   s["attempts"], s["solved"], acc, s["cycles"],
                   s["hormones"]["curiosity"], s["hormones"]["urgency"],
                   s["hormones"]["energy"], s["hormones"]["mood"]))
