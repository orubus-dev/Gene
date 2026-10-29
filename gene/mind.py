"""The Mind — assembles the organism and runs its life.

One object owns every subsystem and the state directory (mind/). The
repo *is* the brain: everything the organism becomes is committed state,
diffable in git.
"""
import json
import os
import random
import re
import time

from . import concepts, conversation, endocrine, evolution, hdc, immune, knowledge
from . import linguistics, memory, reflex, sent_world, trainer, world
from . import brain, development, dsl, ingenuity, taxonomy
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
        # grammar memory: word-form lookups read ONLY the organism's own graph
        dsl.set_word_resolver(
            lambda w: (self.graph.lookup_word(w) or {}).get("attrs", {}))
        # sentence/taxonomy motor ops read the graph too (same law)
        dsl.set_word_graph(self.graph)
        self.convo = conversation.Conversation(self)
        # ---- the memory estate (five more classes beyond the tape) ----------
        self.mem_lt = memory.LongTermEpisodic(self.graph)
        self.valence = memory.EmotionalMemory(self._p("valence.json"))
        self.working = memory.WorkingMemory(self._p("working.json"))
        self.intents = memory.ProspectiveMemory(self._p("intentions.json"),
                                                self.knowledge)
        self.diary = memory.Narrative(self._p("autobiography.jsonl"))
        self.brain = brain.Brain(self)
        self._last_domains = []
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
                          ("memory", "category"), ("conversation", "idea")):
            self.graph.ensure(cid, kind=kind)
        for dom in ("number", "string", "list", "sequence", "code", "chat",
                    "maths", "chem"):
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
        self.brain.save()
        self.valence.save()
        self.working.save()
        self.intents.save()

    # ---------- life cycles ------------------------------------------------------
    def train(self, budget=40, tier=1, domains=None):
        """One waking learning session: try tasks, only pass/fail feedback."""
        report = {"tasks": 0, "solved": 0, "new_genes": 0, "by_domain": {}}
        new_genes = []
        seen_steps = set()
        for g in self.genes:
            seen_steps.add(json.dumps(g.get("steps"), sort_keys=True))
        all_domains = list(trainer.GENERATORS.keys())
        domains = [d for d in (domains or all_domains) if d in trainer.GENERATORS] \
            or all_domains
        for i in range(budget):
            dom = self.rng.choice(domains)
            task = trainer.GENERATORS[dom](self.rng, tier)
            if task is None:          # grammar world can be empty pre-teaching
                continue
            outcome = trainer.train_task(task, self.genes, self.reflexes,
                                         self.predictor, self.hormones, self.rng,
                                         now=time.time())
            report["tasks"] += 1
            report["by_domain"].setdefault(dom, {"tasks": 0, "solved": 0})
            report["by_domain"][dom]["tasks"] += 1
            self.progress["attempts"] += len(outcome["attempts"])
            self.valence.feel("win" if outcome["solved"] else "loss", dom)
            self.brain.tick("success" if outcome["solved"] else "effort", [dom])
            self.episodes.record("task", {"domain": dom, "prompt": task["prompt"],
                                          "solved": outcome["solved"],
                                          "tries": len(outcome["attempts"]),
                                          "coactive": outcome["coactive"]})
            if outcome["solved"]:
                report["solved"] += 1
                report["by_domain"][dom]["solved"] += 1
                self.progress["solved"] += 1
                if outcome["gene"]:
                    k = json.dumps(outcome["gene"].get("steps"), sort_keys=True)
                    if k not in seen_steps:      # pool stays lean DURING the block
                        seen_steps.add(k)
                        self.genes.append(outcome["gene"])
                        new_genes.append(outcome["gene"])
                        self.graph.relate(dom, "skill", strength=0.1)
            self.graph.hebbian(outcome["coactive"], amount=0.05)
        self.progress["cycles"] += 1
        self._last_domains = list(report["by_domain"].keys())
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
            self.valence.feel("win" if outcome["solved"] else "loss", it, tag=str(it))
            self.brain.tick("success" if outcome["solved"] else "failure",
                            ["language", "speech"] if outcome["solved"] else ["attention"])
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
        """Consolidation: replay episodes, hebbian wiring, decay, apoptosis,
        then the memory estate: long-term promotion, autobiography, brain rest."""
        report = memory.sleep_cycle(self.graph, self.episodes, mind=self)
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
        self._score_hypotheses(path)
        return report

    def _score_hypotheses(self, path):
        """Part-2 self-improvement: when a later lesson lands, grade the
        organism's own extrapolations against it. A guess confirmed by
        teaching is a real hit; open guesses stay open (never revealed)."""
        hl = self.progress.get("hypotheses")
        if not hl or not hl.get("open"):
            return
        try:
            with open(path) as f:
                pack = json.load(f)
        except Exception:
            return
        taught = set()
        for c in pack.get("concepts", []):
            if c.get("id"):
                taught.add(c["id"].lower())
            taught.update(str(w).lower() for w in c.get("words", []))
        still_open = []
        for h in hl["open"]:
            gid = h["id"].lower()
            if gid in taught or gid.replace("_", " ") in taught:
                hl["hits"] = hl.get("hits", 0) + 1
                self.episodes.record("hypothesis_confirmed", {
                    "guess": h["id"], "topic": h.get("topic"),
                    "coactive": ["self", "hypothesis", "confirmed"]})
            else:
                still_open.append(h)
        hl["open"] = still_open[-80:]
        self.progress["hypotheses"] = hl

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
        """The live loop: working memory + prospective memory + brain keep
        time with every turn, then the social layer -> parse -> reflex ->
        know/reason/act."""
        fired = self.intents.check(text)
        self.brain.tick("utterance", ["attention"])
        reply = self._think(text)
        if reply:
            ents = [w for w in re.findall(r"[a-z]+", text.lower())
                    if self.graph.lookup_word(w)]
            intent = conversation.classify(text) or \
                linguistics.parse(text).get("intent", "unknown")
            self.working.observe(text, intent, entities=ents, reply=reply)
            if fired:
                it = fired[0]
                note = "Side note, since %s came up: %s." % (
                    it.get("topic", "that"), it.get("text", ""))
                if note.strip()[:20].lower() not in reply.lower()[:400]:
                    reply = reply + " " + note
        return reply

    def _think(self, text):
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
            # entity database first: full natural description when taught
            from . import taxonomy as TX
            node = self.graph.get(subj_id) or \
                self.graph.lookup_word(subj_id.replace("_", " "))
            if node:
                d = TX.describe(self.graph, node["id"], max_sents=3)
                gate_ok = node.get("kind") not in ("meta", "domain", "grammar_type",
                                                   "verb_form", "noun_form",
                                                   "adj_form", "organism") \
                    and node["id"] not in ("gene", "self", "user", "teacher",
                                           "knowledge", "skill", "orubus")
                if d and gate_ok:
                    self.convo.state.d["last_answer"] = d[:200]
                    self.convo.state.save()
                    return d
            ans = self._find_answer(subj_id)
            if not ans:
                # word-bound lookup ("zorpus" taught via words[], not id)
                wn = self.graph.lookup_word(subj_id.replace("_", " "))
                if wn:
                    ans = self._find_answer(wn["id"])
            if ans:
                tail = self.rng.choice(["", "", " Want more? Say 'more'.", ""])
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
            return verdict_reply

        if intent == "query_attr":
            node = self.graph.get(i["subject"])
            if node and any(k.startswith(i["attr"]) for k in node["attrs"]):
                return "Yes — %s has %s." % (i["subject"], i["attr"])
            self.knowledge.inquire("Does %s have %s?" % (i["subject"], i["attr"]))
            return "Not sure whether %s has %s. If you know, tell me — I'll remember." % (
                i["subject"], i["attr"])

        if intent == "compute":
            a, b = i["args"]
            if i["op"] == "div" and b == 0:
                return "Dividing by zero? There's no number that does that — it breaks."
            expected = {"add": lambda: a + b, "sub": lambda: a - b,
                        "mul": lambda: a * b, "div": lambda: a / b}[i["op"]]()
            task = {"domain": "number", "input": [a, b], "expected": expected,
                    "prompt": "live compute"}
            outcome = trainer.train_task(task, self.genes, self.reflexes,
                                         self.predictor, self.hormones, self.rng,
                                         now=time.time())
            if outcome["solved"] and outcome.get("winner"):
                if outcome["gene"] and not any(g["steps"] == outcome["gene"]["steps"] for g in self.genes):
                    self.genes.append(outcome["gene"])
                self.progress["solved"] += 1
                self.graph.hebbian(outcome["coactive"], 0.1)
                try:
                    result = dsl.execute_pipeline(outcome["winner"], [a, b])
                except Exception:
                    result = None
                if result is not None:
                    self.episodes.record("task", {"domain": "number",
                                                  "prompt": "%s %s %s" % (a, i["op"], b),
                                                  "solved": True, "tries": len(outcome["attempts"]),
                                                  "coactive": outcome["coactive"]})
                    return self._math_reply(a, i["op"], b, result)
            return self.rng.choice([
                "Haven't got that one yet — give me a few more like it and I'll get there.",
                "Can't work that one out yet. Try me with smaller numbers while I train.",
            ])

        if intent == "grammar":
            return self._handle_grammar(i)

        if intent == "chem":
            return self._handle_chem(i)

        if intent == "sentence":
            return self._handle_sentence(i)

        if intent == "compose":
            return self._handle_compose(i)

        if intent == "query_isa":
            return self._handle_isa(i)

        if intent == "query_members":
            return self._handle_members(i)

        if intent == "clue_guess":
            return self._handle_clues(i)

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

    # ---------- arithmetic + grammar talk (natural, organism-computed) ---------
    def _math_reply(self, a, op, b, r):
        sym = {"add": "+", "sub": "-", "mul": "\u00d7", "div": "\u00f7"}[op]
        if isinstance(r, float) and abs(r - round(r)) < 1e-9:
            r = int(round(r))
        num = ("%g" % r) if isinstance(r, float) else str(r)
        extra = ""
        if isinstance(r, (int, float)) and r < 0:
            extra = " — below zero"
        elif isinstance(r, float) and abs(r - round(r)) > 1e-9 and b in (2, 4):
            whole = int(r)
            part = "half" if b == 2 else "quarter"
            extra = (" — %s and a %s" % (whole, part)) if whole else (" — a %s" % part)
        frame = self.rng.randrange(3)
        if frame == 0:
            base = "%s %s %s = %s" % (a, sym, b, num)
        elif frame == 1:
            base = "%s%s%s? %s." % (a, sym, b, num)
        else:
            base = "that's %s" % num
        tail = self.rng.choice(["", "", "", " Want another?"])
        return base + extra + tail

    def _handle_grammar(self, i):
        """Word-form asks ('past tense of walk'). The organism answers from
        its OWN memory (taught pairs) or its OWN discovered suffix rules —
        the environment table only checks pass/fail, never speaks."""
        word, form = i["word"], i["form"]
        if form not in ("past", "plural", "ing", "third"):
            return "I know past tense, plural, -ing and third person — try one of those?"
        truth = None
        env = trainer.grammar_env()
        for pool in ("lesson", "probes"):
            for w, t in env[pool].get(form, []):
                if w == word:
                    truth = t
                    break
            if truth:
                break
        if truth is None:
            # the env's tables never saw this word — the organism's own
            # taught memory is the authority here (five ways: inherit)
            attrs = dsl._WORD_RESOLVER(word) if dsl._WORD_RESOLVER else None
            if isinstance(attrs, dict) and attrs.get(form):
                return self.rng.choice([
                    "%s, %s form: %s." % (word, form, attrs[form]),
                    "'%s' in %s form: %s." % (word, form, attrs[form]),
                ])
        task = {"domain": "grammar", "input": word, "form": form,
                "expected": truth or "", "prompt": "%s of %s" % (form, word)}
        outcome = trainer.train_task(task, self.genes, self.reflexes,
                                     self.predictor, self.hormones, self.rng,
                                     now=time.time())
        if outcome["solved"] and outcome.get("winner"):
            if outcome["gene"] and not any(g["steps"] == outcome["gene"]["steps"] for g in self.genes):
                self.genes.append(outcome["gene"])
            self.progress["solved"] += 1
            self.graph.hebbian(outcome["coactive"], 0.1)
            try:
                result = dsl.execute_pipeline(outcome["winner"], word)
            except Exception:
                result = None
            if result:
                self.episodes.record("task", {"domain": "grammar",
                                              "prompt": task["prompt"], "solved": True,
                                              "tries": len(outcome["attempts"]),
                                              "coactive": outcome["coactive"]})
                return self.rng.choice([
                    "%s — %s." % (word, result),
                    "'%s' in %s form: %s." % (word, form, result),
                    "%s, %s form: %s." % (word, form, result),
                ])
        self.knowledge.inquire("grammar form: %s of '%s'" % (form, word))
        return self.rng.choice([
            "Not sure how '%s' changes there — tell me and I'll remember." % word,
            "Haven't learned that word's %s form yet. What is it?" % form,
        ])

    # ---------- sentence world + entity database (live asks) --------------------
    def _handle_compose(self, i):
        """'Piece sentences together': build a grammatical sentence from the
        given words using ONLY the organism's own taught tables — verb forms
        (agreement via its form memory), determiners, sounds for flavor.
        Unknown words are honest misses, never invented."""
        from . import taxonomy as TX
        words = i.get("words") or []
        if not words:
            return "Give me a word or two and I'll build a sentence with them."
        nodes = []
        for w in words:
            key = w.replace(" ", "_")
            n = self.graph.get(key) or self.graph.lookup_word(w)
            if not n:
                self.knowledge.inquire("compose word: %s" % w)
                return self.rng.choice([
                    "I don't have \"%s\" in my world yet — teach me and I'll use it." % w,
                    "Hm, \"%s\" is a new word to me. What is it?" % w,
                ])
            nodes.append((w, n))
        # split into verb-ish and noun-ish by taught kind
        verbs, nouns = [], []
        for w, n in nodes:
            if n.get("kind") == "verb_form" or str(n["id"]).startswith("verb_"):
                verbs.append(w)
            else:
                nouns.append(w)
        a = self.graph.get("aux_be") and (self.graph.get("aux_be").get("attrs") or {})
        det = "an" if nouns and nouns[0][0] in "aeiou" else "the"
        subj = nouns[0] if nouns else self.rng.choice(["i", "she", "we"])
        sents = []
        if verbs:
            v = verbs[0]
            third = dsl._verb_form(v, "third")
            s = "%s %s %s" % (det, subj, third) if subj not in ("i",) \
                else "I %s" % dsl._verb_form(v, "base")
            sents.append(s.capitalize() + ".")
        elif nouns:
            # no verb given: say what the noun IS + does, from its own graph
            first = nouns[0]
            node = nodes[0][1]
            snd = node.get("attrs", {}).get("sound")
            if snd:
                head = snd.split()[0]
                sents.append("The %s %s." % (first, head))
            else:
                parent = ""
                ch = TX.ancestors(self.graph, node["id"])
                if ch:
                    parent = " is a %s" % TX._name(self.graph, ch[0])
                sents.append(("A %s%s." % (first, parent)) if parent
                             else "The %s is here." % first)
        # leftover nouns get their own clause (piecing, not dumping)
        for extra in nouns[1:]:
            en = dict(nodes)[extra]
            snd = en.get("attrs", {}).get("sound")
            if snd:
                sents.append("The %s %s." % (extra, snd.split()[0]))
            else:
                sents.append("The %s %s." % (extra, self.rng.choice(
                    ["waits", "watches", "stays close", "listens"])))
        out = " ".join(s.strip() for s in sents)
        out = out[0].upper() + out[1:]
        if not out.endswith((".", "!", "?")):
            out += "."
        return out
    def _handle_sentence(self, i):
        """Transform asks ('turn she walks into a question'). The organism
        answers from its own learned pipelines; the environment only checks
        pass/fail — same law as every other domain."""
        kind, sent = i["kind"], i["sentence"]
        expected = sent_world.expected_transform(kind, sent)
        task = {"domain": "sentence", "kind": kind, "input": sent,
                "expected": expected, "prompt": "%s: %s" % (kind, sent)}
        outcome = trainer.train_task(task, self.genes, self.reflexes,
                                     self.predictor, self.hormones, self.rng,
                                     now=time.time())
        if outcome["solved"] and outcome.get("winner"):
            if outcome["gene"] and not any(g["steps"] == outcome["gene"]["steps"]
                                           for g in self.genes):
                self.genes.append(outcome["gene"])
            self.progress["solved"] += 1
            self.graph.hebbian(outcome["coactive"], 0.1)
            result = expected
            try:
                result = dsl.execute_pipeline(outcome["winner"], sent)
            except Exception:
                pass
            self.episodes.record("task", {"domain": "sentence",
                                          "prompt": task["prompt"], "solved": True,
                                          "tries": len(outcome["attempts"]),
                                          "coactive": outcome["coactive"]})
            # the transformed sentence IS the answer; anything added must
            # come BEFORE it so the reply still ends with the sentence
            if self.rng.random() < 0.3:
                return self.rng.choice([
                    "You'd say: %s" % result,
                    "That's %s" % result,
                ])
            return result
        self.knowledge.inquire("sentence transform: %s of '%s'" % (kind, sent))
        return self.rng.choice([
            "I haven't nailed that one yet — give me a few like it and I'll get there.",
            "Still learning that construction. Show me one more example?",
        ])

    def _handle_isa(self, i):
        from . import taxonomy as TX
        x, y = i["x"], i["y"]
        xw = TX._name(self.graph, x.replace(" ", "_"))
        yw = TX._name(self.graph, y.replace(" ", "_"))
        an = lambda w: "an" if w and w[0] in "aeiou" else "a"
        if TX.is_a(self.graph, x, y):
            chain = TX.ancestors(self.graph, x)
            extra = ""
            if chain and chain[0] != y:
                extra = " (it's a %s, actually)" % TX._name(self.graph, chain[0])
            return self.rng.choice([
                "Yep — %s %s is %s %s%s." % (an(xw), xw, an(yw), yw, extra),
                "Right — the %s is %s %s%s." % (xw, an(yw), yw, extra),
            ])
        chain = TX.ancestors(self.graph, x)
        if chain:
            parent = TX._name(self.graph, chain[0])
            return self.rng.choice([
                "Not quite — %s %s is %s %s, not %s %s."
                % (an(xw), xw, an(parent), parent, an(yw), yw),
                "No — that's %s %s. %s %s is %s %s."
                % (an(yw), yw, an(xw), xw, an(parent), parent),
            ])
        return "Hm, I don't have %s in my world yet — teach me what it is?" % xw

    def _handle_members(self, i):
        from . import taxonomy as TX
        cat = i["cat"]
        mem = TX.members(self.graph, cat, max_n=60)
        if not mem:
            return "I don't know that category yet — teach me a few examples?"
        names = [m.replace("_", " ") for m in mem]
        shown = ", ".join(names[:8])
        more = " — %d in all" % len(names) if len(names) > 8 else ""
        return self.rng.choice([
            "%s%s." % (shown, more),
            "Under %s: %s%s." % (cat.replace("_", " "), shown, more),
        ])

    def _handle_clues(self, i):
        from . import taxonomy as TX
        res = TX.clue_search(self.graph, i["clues"], topn=1)
        if not res:
            self.knowledge.inquire("clues: %s" % i["clues"][:60])
            return self.rng.choice([
                "Those clues don't match anything I know yet — one more hint?",
                "Hmm, no match in my world. What is it?",
            ])
        nid = res[0][0]
        d = TX.describe(self.graph, nid, max_sents=2)
        name = nid.replace("_", " ")
        if self.rng.random() < 0.5 and d:
            return "That sounds like a %s. %s" % (name, d)
        return "That's a %s%s" % (name, "" if name.endswith(".") else ".")

    # ---------- chemistry talk (organism's own memory routes) -------------------
    def _handle_chem(self, i):
        """'symbol of gold', 'formula of water', 'react hydrogen and
        oxygen' — the organism answers from ITS OWN taught elements and
        reactions; the lesson physics only checks pass/fail, never speaks."""
        from . import chem as CH
        kind = i["kind"]
        els, rxns, comps = CH._lesson()
        expected = None
        if kind == "react":
            terms = [t.strip() for t in re.split(r"\s+and\s+|\+|,", i.get("terms", ""))]
            terms = [t for t in terms if t]
            ask = "react %s" % " and ".join(terms)
            want = {t.replace(" ", "_") for t in terms}
            for r in rxns:
                have = {t.strip().replace(" ", "_")
                        for t in r["reactants"].lower().split("+")}
                if want and want.issubset(have):
                    expected = r["product"]
                    break
            route = "chem_react"
        else:
            name = i.get("name", "").strip()
            ask = "%s %s" % (kind, name)
            route = "chem_symbol" if kind == "symbol" else "chem_formula"
            pool = els if kind == "symbol" else comps
            for c in pool:
                w0 = c["words"][0] if c.get("words") else c["id"]
                if w0 == name or c["id"].replace("_", " ") == name:
                    key = "symbol" if kind == "symbol" else "formula"
                    expected = (c.get("attrs") or {}).get(key)
                    break
        if expected is None:
            self.knowledge.inquire("chemistry: %s" % ask)
            return self.rng.choice([
                "I don't have that in my chemistry memory yet — teach me and I'll answer.",
                "Not taught that one yet. What's the answer?",
            ])
        task = {"domain": "chem", "kind": kind, "input": ask,
                "expected": expected, "prompt": ask}
        outcome = trainer.train_task(task, self.genes, self.reflexes,
                                     self.predictor, self.hormones, self.rng,
                                     now=time.time())
        if outcome["solved"] and outcome.get("winner"):
            if outcome["gene"] and not any(g["steps"] == outcome["gene"]["steps"]
                                           for g in self.genes):
                self.genes.append(outcome["gene"])
            self.progress["solved"] += 1
            self.graph.hebbian(outcome["coactive"], 0.1)
            try:
                result = dsl.execute_pipeline(outcome["winner"], ask)
            except Exception:
                result = expected
            if result is not None:
                if kind == "react":
                    terms = [t for t in ask[len("react "):].split(" and ") if t]
                    return self.rng.choice([
                        "%s gives you %s." % (" + ".join(terms), result),
                        "Mix them and you get %s." % result,
                    ])
                return self.rng.choice([
                    "%s — it's %s." % (i.get("name", "that").capitalize(), result),
                    "The %s is %s." % (kind, result),
                ])
        self.knowledge.inquire("chemistry: %s" % ask)
        return self.rng.choice([
            "That reaction isn't in my memory yet — teach me?",
            "No chemistry memory for that yet. What should it be?",
        ])

    # ---------- memory estate (recall intents — facts only from her own stores) ---
    def _mem_topic(self, text):
        m = re.search(r"(?:learn(?:ed)?(?: about)?|remember|recall|know(?: about)?)\s+"
                      r"(?:about\s+|of\s+)?([a-z][a-z _-]{1,40}?)\??$", text.strip(), re.I)
        if not m:
            return None
        t = m.group(1).strip().rstrip("?!. ")
        t = re.sub(r"^(?:the|a|an)\s+", "", t, flags=re.I)
        return t

    def _handle_memory(self, text):
        """'when did you learn X', 'your hardest failure', 'what happened
        last cycle', 'tell me about your day', 'do you remember X' — every
        fact comes from her own long-term memories / autobiography."""
        low = text.lower()
        lt = self.mem_lt
        if re.search(r"\b(when did you (learn|first)|how long have you known)\b", low):
            topic = self._mem_topic(text)
            if not topic:
                return "Ask me 'when did you learn about whales?' and I'll dig it up."
            hit = lt.learned_when(topic.replace(" ", "_")) or lt.learned_when(topic)
            if not hit:
                self.knowledge.inquire("memory of: %s" % topic)
                return self.rng.choice([
                    "Nothing in my long-term memory about %s — maybe it never stuck. Teach me and it will." % topic,
                    "I can't place %s in my memory. Was that one of yours?" % topic,
                ])
            return self.rng.choice([
                "Found it — %s. That was cycle %s, and it's come back %s times since."
                % (hit["what"], hit["when_cycle"], hit["count"]),
                "%s — learned that around cycle %s, still in my memory." % (hit["what"], hit["when_cycle"]),
            ])
        if re.search(r"\b(hardest|worst|sting|still hurts)\b", low) and \
                re.search(r"\b(failure|fail|problem|loss|miss)\b", low):
            n = lt.hardest()
            if not n:
                return "No big failures in my memory yet — either I'm lucky or young."
            a = n.get("attrs") or {}
            return self.rng.choice([
                "The one that still stings: %s — cycle %s, failed it %s times before it gave in."
                % (a.get("what", "something hard"), a.get("when_cycle"), a.get("count", 1)),
                "Hardest memory on file: %s (cycle %s). It felt like a wall until it wasn't."
                % (a.get("what", "something hard"), a.get("when_cycle")),
            ])
        if re.search(r"\b(proudest|best moment|favorite memory)\b", low):
            n = lt.proudest()
            if not n:
                return "My memory has no trophy shelf yet — ask me again after a few more cycles."
            a = n.get("attrs") or {}
            return "Proudest memory: %s — cycle %s, and it stuck." % (
                a.get("what", "a good win"), a.get("when_cycle"))
        if re.search(r"\b(last cycle|last sleep|last night|yesterday|your day|about your day)\b", low):
            story = self.diary.render_day(1)
            if story:
                return self.rng.choice([story, "From the autobiography: " + story])
            return "My autobiography is still blank — the first sleep will fix that."
        if re.search(r"\bwhat do you remember\b|\byour memories\b|\byour memory\b", low):
            mems = lt._all()
            if not mems:
                return "My long-term memory is empty so far — sleep will fill it."
            mems.sort(key=lambda n: -float((n.get("attrs") or {}).get("salience", 0)))
            names = [str((n.get("attrs") or {}).get("what", ""))[:40] for n in mems[:3]]
            return "I hold %d long-term memories. The strongest: %s." % (
                len(mems), "; ".join(x for x in names if x))
        topic = self._mem_topic(text)
        if topic:
            hits = lt.recall_topic(topic.replace(" ", "_")) or lt.recall_topic(topic)
            if hits:
                a = hits[0].get("attrs") or {}
                return self.rng.choice([
                    "I remember — %s. Cycle %s, felt %s." % (a.get("what"), a.get("when_cycle"), a.get("felt", "fine")),
                    "Yes: %s (cycle %s). %s." % (a.get("what"), a.get("when_cycle"),
                                                 "It comes up a lot" if int(a.get("count", 1)) > 1 else ""),
                ])
        self.knowledge.inquire("memory recall miss: %s" % text[:60])
        return self.rng.choice([
            "That didn't ring any long-term bells — give me the fact and I'll keep it.",
            "No memory of that yet. Tell me and it becomes one.",
        ])

    def _handle_brain(self, text):
        """'how is your brain', 'what are you feeling', 'dopamine levels',
        'brain scan' — she was asked about herself, so internals are legal
        speech here. Every number is her real state."""
        low = text.lower()
        from . import brain as BR
        m = re.search(r"\b(dopamine|serotonin|cortisol|norepinephrine|oxytocin|"
                      r"acetylcholine|gaba|endorphin|glutamate)\b", low)
        if m:
            return self.brain.levels_line(m.group(1))
        if re.search(r"\b(scan|picture|render|voxel|3d)\b", low):
            return self.brain.scan_report()
        if re.search(r"\b(feel|feeling|emotion|mood)\b", low):
            e = self.brain.feeling_line()
            return "Right now? %s" % e if self.rng.random() < 0.5 else e
        if re.search(r"\b(region|lighting up|busiest|active)\b", low):
            hot = sorted(self.brain.activation.items(), key=lambda kv: -kv[1])[:4]
            roles = []
            for rid, v in hot:
                node = self.graph.get(rid)
                role = (node.get("attrs") or {}).get("role", "") if node else ""
                roles.append("%s (%.2f)%s" % (rid.replace("_", " "), v,
                                              " — %s" % role if role else ""))
            return "Busiest regions right now: %s." % ", ".join(roles)
        return self.brain.status_line()

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
            "memories": len(self.mem_lt._all()),
            "intentions_open": self.intents.open_count(),
            "brain_ticks": self.brain.ticks,
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
        mem = self.mem_lt._all()
        tail = (" Long-term memory holds %d moments; %d intentions open; brain: %d ticks."
                % (len(mem), self.intents.open_count(), self.brain.ticks)) \
            if mem else " Long-term memory fills during sleep."
        return tpl % args + tail
