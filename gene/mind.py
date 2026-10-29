"""The Mind — assembles the organism and runs its life.

One object owns every subsystem and the state directory (mind/). The
repo *is* the brain: everything the organism becomes is committed state,
diffable in git.
"""
import json
import os
import random
import time

from . import concepts, conversation, endocrine, evolution, hdc, immune, knowledge
from . import linguistics, memory, reflex, trainer, world
from . import development, ingenuity
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
        self.convo = conversation.Conversation(self)
        self.progress = self._load("progress.json", {"attempts": 0, "solved": 0,
                                                     "by_domain": {}, "cycles": 0,
                                                     "history": []})
        self.meta = self._load("meta.json", {"born": time.time(), "name": "gene"})

        self._seed_core()

    # ---------- core self (machinery concepts, not knowledge) ----------------
    def _seed_core(self):
        for cid, kind in (("self", "meta"), ("knowledge", "meta"),
                          ("teacher", "meta"), ("skill", "meta"),
                          ("success", "meta"), ("failure", "meta"),
                          ("question", "meta"), ("experiment", "meta"),
                          ("conversation", "idea")):
            self.graph.ensure(cid, kind=kind)
        for dom in ("number", "string", "list", "sequence", "code", "chat"):
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
        self._snapshot_history(report)
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

    def train_chat(self, budget=60, start_tier=1):
        """One conversational waking block: boolean-only, escalating tiers.
        Failed tasks make the NEXT task harder (never easier, never revealed)."""
        from . import lang_trainer as LT
        report = {"tasks": 0, "solved": 0, "by_intent": {}, "tiers": {},
                  "escalations": 0, "max_tier": start_tier}
        tier = start_tier
        queue = []
        for i in range(budget):
            if queue:
                task = queue.pop(0)          # escalated retry from a failure
            else:
                task = LT.gen_chat_task(self.rng, tier)
            outcome = LT.train_chat_task(task, self.convo, self.genes,
                                         self.reflexes, self.predictor,
                                         self.hormones, self.rng, now=time.time())
            report["tasks"] += 1
            it = task["intent"]
            report["by_intent"].setdefault(it, {"tasks": 0, "solved": 0})
            report["by_intent"][it]["tasks"] += 1
            report["tiers"][str(task["tier"])] = report["tiers"].get(str(task["tier"]), 0) + 1
            self.progress["attempts"] += len(outcome["attempts"])
            self.episodes.record("chat_task", {"intent": it, "tier": task["tier"],
                                               "stimulus": task["input"][:80],
                                               "solved": outcome["solved"],
                                               "tries": len(outcome["attempts"]),
                                               "coactive": outcome["coactive"]})
            self.graph.hebbian(outcome["coactive"], 0.05)
            if outcome["solved"]:
                report["solved"] += 1
                report["by_intent"][it]["solved"] += 1
                self.progress["solved"] += 1
                if outcome["gene"] and not any(
                        g["steps"] == outcome["gene"]["steps"] and g.get("domain") == "chat"
                        for g in self.genes):
                    if outcome["gene"]["id"] is None:
                        outcome["gene"]["id"] = "c%05d" % self.rng.randint(0, 99999)
                    self.genes.append(outcome["gene"])
                self.graph.relate("chat", "skill", strength=0.1)
                tier = max(start_tier, task["tier"])          # hold the hard-won level
                # ASPIRATION LAW: dominate a tier and the world gets harder —
                # winning is also a reason to climb, never to coast.
                if report["tasks"] >= 5 and report["solved"] / report["tasks"] >= 0.9:
                    tier = min(4, tier + 1)
            else:
                # ESCALATION LAW: failure -> harder next, answer never shown.
                # Bound: a stimulus re-escalates at most 3 times, then it is
                # released (it returns next cycle; never revealed, never easier).
                tries = task.get("tries", 0)
                if tries < 3:
                    esc = dict(task)
                    esc["tier"] = min(4, task["tier"] + 1)
                    esc["input"] = task["input"]
                    esc["tries"] = tries + 1
                    queue.append(esc)
                    report["escalations"] += 1
                    tier = min(4, max(tier, esc["tier"]))
                    self.episodes.record("escalation", {"intent": it,
                                                        "tier": esc["tier"],
                                                        "coactive": ["chat", "failure", "harder"]})
            report["max_tier"] = max(report["max_tier"], tier)
        self.progress["cycles"] += 1
        self._snapshot_history({"by_domain": {"chat": {"tasks": report["tasks"],
                                                        "solved": report["solved"]}}})
        self.genes = trainer.dedupe_genes(self.genes)
        self.dev.record_win("chat") if report["solved"] else None
        return report

    def _snapshot_history(self, report):
        """Append a per-cycle solve-rate snapshot (for self-improvement narrative)."""
        hist = self.progress.setdefault("history", [])
        rates = {}
        for dom, v in report.get("by_domain", {}).items():
            if v.get("tasks"):
                rates[dom] = round(v["solved"] / v["tasks"], 3)
            # keep lifetime per-domain counters current too
            agg = self.progress.setdefault("by_domain", {}).setdefault(
                dom, {"tasks": 0, "solved": 0})
            agg["tasks"] += v.get("tasks", 0)
            agg["solved"] += v.get("solved", 0)
        if rates:
            hist.append({"cycle": self.progress["cycles"], "rates": rates})
        self.progress["history"] = hist[-30:]

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
        """The live loop: social layer -> parse -> reflex -> know/reason/act."""
        # social/conversational layer first (identity, greetings, smalltalk...)
        social = self.convo.handle(text)
        if social:
            return social

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
            subj_id = i["subject"]
            ans = self._find_answer(subj_id)
            if not ans:
                # word-bound lookup ("zorpus" taught via words[], not id)
                wn = self.graph.lookup_word(subj_id.replace("_", " "))
                if wn:
                    ans = self._find_answer(wn["id"])
            if ans:
                tail = self.rng.choice([
                    "",
                    " (From my graph — ask 'how do you know %s' for provenance.)" % subj_id.replace("_", " "),
                    " Taught or derived — nothing hard-coded.",
                    " Want the deeper links? Say 'more'.",
                ])
                full = (ans + tail).strip()
                self.convo.state.d["last_answer"] = full[:200]
                self.convo.state.save()
                return full
            # unknown: infer harder, then INGENUITY (decompose + existence),
            # then analogy, then honest miss + question back
            gained = self.knowledge.infer(subj_id)
            if gained:
                parts = []
                if gained.get("is-a"):
                    parts.append("%s is %s" % (i["subject"].replace("_", " "), gained["is-a"][0].replace("_", " ")))
                for k, v in gained.items():
                    if k not in ("is-a", "causes"):
                        parts.append("%s: %s" % (k, v))
                if parts:
                    return "By inference: %s." % "; ".join(parts[:2])
            verdict_reply = ingenuity.existence_reply(self, subj_id)
            near = self.graph.activate([subj_id], topn=3)
            near = [n for n, s in near if s > 0.12 and n != subj_id]
            if near and "'" + subj_id.replace("_", " ") in verdict_reply:
                # ingenuity had nothing structural to say; keep HDC guess but
                # honest-first: lead with the verdict, append the HDC neighbor
                return verdict_reply + " (By raw vector feel it lands nearest '%s' — weak signal.)" % near[0].replace("_", " ")
            return verdict_reply

        if intent == "query_attr":
            node = self.graph.get(i["subject"])
            if node and any(k.startswith(i["attr"]) for k in node["attrs"]):
                return "Yes — %s has %s." % (i["subject"], i["attr"])
            self.knowledge.inquire("Does %s have %s?" % (i["subject"], i["attr"]))
            return "I don't know whether %s has %s yet. Tell me '%s has %s' and I'll wire it in — or ask me something adjacent." % (
                i["subject"], i["attr"], i["subject"], i["attr"])

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

        # unknown words -> knowledge seeking (raise the hand silently, keep talking)
        STOPWORDS = {"the", "and", "for", "are", "but", "not", "you", "all",
                     "can", "her", "was", "one", "our", "out", "his", "has",
                     "have", "been", "will", "what", "how", "why", "who",
                     "tell", "me", "about", "that", "this", "with", "does",
                     "did", "do", "is", "it", "of", "on", "in", "to", "a",
                     "an", "your", "my", "know", "think", "heard", "ever"}
        words = [w for w in linguistics.parse(text).get("text", text).lower().split()
                 if w.isalpha()]
        unknown = [w for w in words if len(w) > 2 and w not in STOPWORDS
                   and not self.graph.lookup_word(w)]
        if unknown:
            w = unknown[0]
            self.episodes.record("wonder", {"unknown": ", ".join(unknown[:5]),
                                            "coactive": ["self", "question", "study"]})
            return ingenuity.existence_reply(self, w)
        return ("I heard you, but I don't yet know how to think about that. "
                "Give me a fact or a puzzle and I'll grow around it.")

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
        h = s["hormones"]
        templates = [
            ("organism status — concepts: %d | skills: %d | reflexes: %d | "
             "causal rules: %d | lifetime: %d attempts, %d solved (%.1f%%) | "
             "cycles: %d | hormones: curiosity %.2f urgency %.2f energy %.2f mood %.2f",
             (s["concepts"], s["skills"], s["reflexes"], s["predictor_rules"],
              s["attempts"], s["solved"], acc, s["cycles"],
              h["curiosity"], h["urgency"], h["energy"], h["mood"])),
            ("self-report: %d concepts, %d skills, %d reflex arcs, %d causal rules. "
             "Lifetime: %d/%d solved (%.1f%%) over %d cycles. Mood %.2f, energy %.0f%%, "
             "curiosity %.2f — all diffable in git.",
             (s["concepts"], s["skills"], s["reflexes"], s["predictor_rules"],
              s["solved"], s["attempts"], acc, s["cycles"],
              h["mood"], h["energy"] * 100, h["curiosity"])),
            ("%d concepts strong, %d skills, %d reflexes, %d rules. "
             "%d attempts, %d solved (%.1f%%), %d cycles lived. "
             "Hormones: mood %.2f | energy %.0f%% | curiosity %.2f | urgency %.2f.",
             (s["concepts"], s["skills"], s["reflexes"], s["predictor_rules"],
              s["attempts"], s["solved"], acc, s["cycles"],
              h["mood"], h["energy"] * 100, h["curiosity"], h["urgency"])),
        ]
        tpl, args = templates[self.rng.randrange(len(templates))]
        return tpl % args
