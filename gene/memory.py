"""Memory — the full palace.

Orubus asked for "long term, episodic, and many more other memory
classes". Gene has no LLM context window — memory is structural and
persisted. This module now owns the whole estate:

  1. EpisodicMemory     the raw tape of lived moments (jsonl) — was already here
  2. LongTermEpisodic   sleep promotes high-salience episodes into
                        memory-nodes wired INTO the concept graph; near-
                        duplicates merge; trivia fades. She can recall
                        when she learned something, her hardest failure,
                        what happened last cycle.
  3. EmotionalMemory    endocrine state bonded to episodes: what felt
                        good/bad/scary, per domain and per skill, biasing
                        practice and coloring recall.
  4. WorkingMemory      the honest replacement for a "context window": a
                        bounded live thread — current topic, active
                        entities, the last few turns, current goal.
  5. ProspectiveMemory  intentions: "when I next see X, bring up Y" —
                        open questions become triggers that fire when the
                        topic walks past.
  6. NarrativeMemory    sleep writes a running autobiography she can
                        actually tell you.

Zero facts live here. Only machinery for keeping what she lived.
"""
import json
import os
import re
import time

MAX_EPISODES = 1500
SALIENCE_KEYS = ("task", "chat_task", "escalation", "development",
                 "hypothesis_confirmed", "immune", "wonder")


class EpisodicMemory:

    def __init__(self, path):
        self.path = path
        self.archive = path + ".archive.jsonl"
        self._n = self._count()

    def _count(self):
        if not os.path.exists(self.path):
            return 0
        with open(self.path, "rb") as f:
            return sum(1 for _ in f)

    def record(self, kind, data):
        ep = {"t": round(time.time(), 3), "kind": kind, "data": data}
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(ep, ensure_ascii=False) + "\n")
        self._n += 1
        if self._n > MAX_EPISODES:
            self._rotate()
        return ep

    def _rotate(self):
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            with open(self.archive, "a", encoding="utf-8") as g:
                g.writelines(lines[: len(lines) // 2])
            with open(self.path, "w", encoding="utf-8") as f:
                f.writelines(lines[len(lines) // 2:])
            self._n = len(lines) - len(lines) // 2

    def tail(self, k=100):
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r", encoding="utf-8") as f:
            lines = f.readlines()[-k:]
        out = []
        for ln in lines:
            try:
                out.append(json.loads(ln))
            except Exception:
                pass
        return out

    def replay(self, k=200):
        """Return recent episodes for consolidation."""
        return self.tail(k)

    def since(self, ts):
        out = []
        for ep in self.tail(1500):
            if ep.get("t", 0) >= ts:
                out.append(ep)
        return out


def base_sleep(graph, episodes, decay=0.01, replay_k=200):
    """One night's classic work: replay, consolidate, decay, prune."""
    eps = episodes.replay(replay_k)
    consolidated = 0
    for ep in eps:
        data = ep.get("data") or {}
        ids = data.get("coactive") or []
        if len(ids) >= 2:
            graph.hebbian(ids, amount=0.05)
            consolidated += 1
    graph.decay(rate=decay)
    pruned = graph.apoptosis()
    return {"replayed": len(eps), "consolidated": consolidated, "pruned": pruned,
            "concepts": len(graph.nodes)}


# ======================= 2. long-term episodic memory =========================
STOP = {"the", "a", "an", "of", "to", "in", "and", "is", "was", "for", "on",
        "with", "at", "by", "it", "this", "that", "i", "you", "me", "my"}


def _topic_words(text, k=3):
    ws = [w for w in re.findall(r"[a-z]+", str(text).lower()) if len(w) > 2]
    return [w for w in ws if w not in STOP][:k]


def _salience(ep):
    d = ep.get("data") or {}
    kind = ep.get("kind")
    if kind in ("task", "chat_task"):
        tries = d.get("tries", 1)
        if d.get("solved"):
            return 0.3 + 0.12 * tries          # hard-won wins glow
        return 0.25 + 0.15 * tries            # hard failures glow more
    if kind == "escalation":
        return 0.55
    if kind in ("development", "hypothesis_confirmed", "immune"):
        return 0.9
    if kind == "wonder":
        return 0.2
    return 0.1


class LongTermEpisodic:
    """Sleep-time promotion of lived episodes into graph memory-nodes."""

    _KIND_WORDS = {"q2s": "statement", "ynq": "question", "neg": "negative",
                   "cont": "continuous", "fut": "future", "imp": "command",
                   "excl": "exclamation", "plural": "plural"}

    @classmethod
    def _sane(cls, text):
        """Memory content is spoken content — internal kind ids become words."""
        s = str(text)
        for k, w in cls._KIND_WORDS.items():
            s = re.sub(r"\b%s:\s*" % k, "%s: " % w, s)
            s = re.sub(r"^%s\b" % k, w, s)
        return s

    def __init__(self, graph):
        self.g = graph

    def _mem_id(self, topic):
        return "mem_%s" % re.sub(r"[^a-z0-9]+", "_", "_".join(topic))[:48]

    def promote(self, episodes, cycle, k=24, now=0.0):
        """Pick the salient episodes since the last sleep, wire them in as
        kind-'memory' nodes (is-a memory + assoc to topic concepts).
        Same topic+outcome merges (count up, strength up) instead of
        duplicating. Returns the created/merged node ids."""
        eps = [e for e in episodes.replay(400) if e.get("kind") in SALIENCE_KEYS]
        eps.sort(key=_salience, reverse=True)
        made = []
        for ep in eps[:k]:
            d = ep.get("data") or {}
            kind = ep.get("kind")
            if kind in ("task", "chat_task"):
                what = d.get("prompt") or d.get("stimulus") or ""
                outcome = "win" if d.get("solved") else "loss"
                topic = _topic_words(what) or [kind]
                felt = "proud" if outcome == "win" and d.get("tries", 1) > 1 else \
                       ("stung" if outcome == "loss" else "fine")
            elif kind == "escalation":
                what = "kept failing, world got harder"
                outcome = "loss"
                topic = _topic_words(d.get("intent") or "challenge")
                felt = "stung"
            else:
                what = kind
                outcome = "note"
                topic = _topic_words(str(d) or kind)
                felt = "marked"
            if not topic:
                continue
            mid = self._mem_id(topic)
            node = self.g.nodes.get(mid)
            if node and (node.get("attrs") or {}).get("outcome") == outcome:
                a = node["attrs"]
                a["count"] = int(a.get("count", 1)) + 1
                a["salience"] = round(min(1.0, float(a.get("salience", 0.3)) + 0.08), 3)
                a["last_cycle"] = cycle
                node["touched"] = now or time.time()
                made.append(mid)
                continue
            valence = 0.6 if outcome == "win" else (-0.6 if outcome == "loss" else 0.2)
            node = self.g.ensure(mid, kind="memory", attrs={
                "what": self._sane(str(what))[:120], "outcome": outcome,
                "when_cycle": cycle, "salience": round(_salience(ep), 3),
                "count": 1, "felt": felt, "valence": valence,
                "words": " ".join(topic),
            }, words=topic)
            self.g.relate(mid, "memory", rel="is-a", strength=0.9)
            self.g.ensure("memory", kind="category",
                          attrs={"def": "a lived moment kept for good"})
            for t in topic:
                if self.g.get(t):
                    self.g.relate(mid, t, rel="assoc", strength=0.3)
            made.append(mid)
        return made

    # ---- recall routes (facts only from the graph) --------------------------
    def _all(self):
        return [n for n in self.g.nodes.values() if n.get("kind") == "memory"]

    def recall_topic(self, topic):
        key = str(topic).lower().strip()
        hits = []
        for n in self._all():
            hay = str((n.get("attrs") or {}).get("words", "")) + " " + \
                str((n.get("attrs") or {}).get("what", ""))
            if key in hay.lower():
                hits.append(n)
        hits.sort(key=lambda n: -float((n.get("attrs") or {}).get("salience", 0)))
        return hits[:3]

    def learned_when(self, topic):
        hits = self.recall_topic(topic)
        if not hits:
            return None
        n = hits[0]
        a = n.get("attrs") or {}
        return {"when_cycle": a.get("when_cycle"), "what": a.get("what"),
                "count": a.get("count", 1)}

    def hardest(self):
        losses = [n for n in self._all()
                  if (n.get("attrs") or {}).get("outcome") == "loss"]
        if not losses:
            return None
        return max(losses, key=lambda n: float((n.get("attrs") or {}).get("salience", 0)))

    def last(self, cycle, k=4):
        cyc = [n for n in self._all()
               if (n.get("attrs") or {}).get("when_cycle") == cycle]
        cyc.sort(key=lambda n: -float((n.get("attrs") or {}).get("salience", 0)))
        return cyc[:k]

    def proudest(self):
        wins = [n for n in self._all()
                if (n.get("attrs") or {}).get("outcome") == "win"]
        if not wins:
            return None
        return max(wins, key=lambda n: float((n.get("attrs") or {}).get("salience", 0)))


# ========================= 3. emotional memory =================================
class EmotionalMemory:
    """Valence bonds: how each domain and each skill tag has FELT, plus a
    short flash list of vivid emotional moments. Bias in, color out."""

    def __init__(self, path):
        self.path = path
        self.d = {"domains": {}, "skills": {}, "flashes": []}
        if path and os.path.exists(path):
            try:
                with open(path) as f:
                    self.d.update(json.load(f))
            except Exception:
                pass

    def save(self):
        if self.path:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w") as f:
                json.dump(self.d, f, indent=1)

    def feel(self, outcome, domain, tag=None, valence=None):
        v = valence if valence is not None else (0.6 if outcome == "win" else -0.5)
        for book, key in ((self.d["domains"], domain), (self.d["skills"], tag)):
            if not key:
                continue
            old = float(book.get(key, 0.0))
            book[key] = round(old * 0.9 + v * 0.1, 3)
        self.d["domains"] = dict(list(sorted(self.d["domains"].items(),
                                             key=lambda kv: -abs(kv[1])))[:40])
        self.d["skills"] = dict(list(sorted(self.d["skills"].items(),
                                            key=lambda kv: -abs(kv[1])))[:60])

    def flash(self, text, valence):
        self.d["flashes"] = (self.d["flashes"] +
                             [{"t": round(time.time(), 1), "what": str(text)[:80],
                               "v": round(valence, 2)}])[-24:]

    def bias(self, domain):
        """Practice bias: domains that felt bad get pulled TOWARD (face the
        sting); domains that felt great rest on their laurels a little."""
        v = float(self.d["domains"].get(domain, 0.0))
        return max(0.4, 1.0 + (0.5 - v) * 0.3)

    def mood_word(self):
        if not self.d["domains"]:
            return None
        v = sum(self.d["domains"].values()) / max(1, len(self.d["domains"]))
        if v > 0.25:
            return "good"
        if v < -0.2:
            return "sore"
        return "steady"


# =========================== 4. working memory =================================
class WorkingMemory:
    """The bounded live thread — what a context window pretends to be.
    Current topic, active entities, the last handful of turns, one goal."""

    def __init__(self, path):
        self.path = path
        self.d = {"topic": None, "entities": [], "turns": [], "goal": None}
        if path and os.path.exists(path):
            try:
                with open(path) as f:
                    self.d.update(json.load(f))
            except Exception:
                pass

    def save(self):
        if self.path:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w") as f:
                json.dump(self.d, f, indent=1)

    def observe(self, text, intent, entities=(), reply=None):
        t = str(text)
        for e in entities:
            if e not in self.d["entities"]:
                self.d["entities"] = (self.d["entities"] + [e])[-8:]
        self.d["topic"] = entities[-1] if entities else self.d["topic"]
        self.d["turns"] = (self.d["turns"] +
                           [{"t": round(time.time(), 1), "text": t[:70],
                             "intent": intent, "reply": (reply or "")[:70]}])[-6:]

    def set_goal(self, goal):
        self.d["goal"] = goal

    def summary(self):
        bits = []
        if self.d["topic"]:
            bits.append("on %s" % str(self.d["topic"]).replace("_", " "))
        if self.d["goal"]:
            bits.append("aiming to %s" % self.d["goal"])
        if self.d["entities"]:
            bits.append("holding: " + ", ".join(
                str(e).replace("_", " ") for e in self.d["entities"][-4:]))
        return "; ".join(bits) if bits else "a clear desk"


# ========================= 5. prospective memory ===============================
class ProspectiveMemory:
    """Open intentions: 'when I next see X, check/mention Y'. Seeded from
    the question ledger; fires when the trigger topic walks past."""

    def __init__(self, path, knowledge=None):
        self.path = path
        self.knowledge = knowledge
        self.d = {"items": []}
        if path and os.path.exists(path):
            try:
                with open(path) as f:
                    self.d.update(json.load(f))
            except Exception:
                pass
        self._import_questions()

    def _import_questions(self):
        if not self.knowledge:
            return
        try:
            with open(self.knowledge.questions_path) as f:
                qs = json.load(f)
        except Exception:
            return
        have = {i.get("topic") for i in self.d["items"]}
        for q in qs[-30:]:
            topic = _topic_words(q.get("q", ""), 2)
            if not topic:
                continue
            key = topic[0]
            if key in have:
                continue
            self.add("when %s comes up, look into what I asked: %s" % (key, q.get("q", "")[:80]),
                     topic[0])

    def save(self):
        if self.path:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w") as f:
                json.dump(self.d, f, indent=1)

    def add(self, text, topic=None, cycle=None):
        topic = topic or (_topic_words(text, 1) or ["something"])[0]
        item = {"id": "int_%d" % (int(time.time() * 1000) % 100000000),
                "text": str(text)[:140], "topic": topic,
                "created_cycle": cycle, "status": "open",
                "created": round(time.time(), 1)}
        self.d["items"] = (self.d["items"] + [item])[-40:]
        return item

    def check(self, text):
        """Fire any open intention whose topic just walked past. Fired items
        are marked done (a mention, not a nag)."""
        low = str(text).lower()
        fired = []
        for it in self.d["items"]:
            if it.get("status") != "open":
                continue
            if it.get("topic") and re.search(r"\b%s\b" % re.escape(it["topic"]), low):
                it["status"] = "done"
                it["fired"] = round(time.time(), 1)
                fired.append(it)
        if len(self.d["items"]) > 60:
            self.d["items"] = [i for i in self.d["items"] if i.get("status") == "open"][-40:]
        return fired

    def open_count(self):
        return sum(1 for i in self.d["items"] if i.get("status") == "open")


# ========================== 6. narrative memory ================================
MAX_AUTO = 400


class Narrative:
    """The running autobiography — one entry per sleep, told in sentences."""

    def __init__(self, path):
        self.path = path

    def append(self, entry):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self.rotate()

    def rotate(self):
        if not os.path.exists(self.path):
            return
        with open(self.path, "rb") as f:
            n = sum(1 for _ in f)
        if n > MAX_AUTO:
            with open(self.path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            with open(self.path, "w", encoding="utf-8") as f:
                f.writelines(lines[len(lines) // 2:])

    def last(self, k=3):
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r", encoding="utf-8") as f:
            lines = f.readlines()[-k:]
        out = []
        for ln in lines:
            try:
                out.append(json.loads(ln))
            except Exception:
                pass
        return out

    def render_day(self, k=1):
        """Turn recent autobiography entries into spoken sentences."""
        entries = self.last(k)
        if not entries:
            return None
        e = entries[-1]
        bits = []
        day = e.get("day") or "recently"
        bits.append("%s I lived through %s" % (day, e.get("headline", "a quiet cycle")))
        if e.get("wins"):
            bits.append("%d problems cracked" % e["wins"])
        if e.get("top"):
            bits.append("the standout was %s" % e["top"])
        if e.get("felt"):
            bits.append("it felt %s" % e["felt"])
        if e.get("kept"):
            bits.append("I kept %s as long-term memories" % e["kept"])
        return ". ".join(bits) + "."


def sleep_cycle(graph, episodes, mind=None, decay=0.01, replay_k=200):
    """One night's work: classic consolidation, then the new memory estate:
    long-term promotion, narrative entry, brain rest. Extended report."""
    report = base_sleep(graph, episodes, decay=decay, replay_k=replay_k)
    if mind is None:
        return report
    cycle = mind.progress.get("cycles", 0)
    lt = mind.mem_lt
    made = lt.promote(episodes, cycle)
    report["memories_kept"] = len(made)
    wins = sum(1 for e in episodes.tail(300)
               if e.get("kind") in ("task", "chat_task") and (e.get("data") or {}).get("solved"))
    tasks = sum(1 for e in episodes.tail(300) if e.get("kind") in ("task", "chat_task"))
    mood_word = mind.valence.mood_word() or "steady"
    top = ""
    proudest = lt.proudest()
    if proudest:
        a = proudest.get("attrs") or {}
        top = str(a.get("what", ""))[:60]
    headline = "%d tasks, %d cracked" % (tasks, wins) if tasks else "a quiet cycle"
    doms = getattr(mind, "_last_domains", None) or []
    mind.diary.append({
        "t": round(time.time(), 1), "cycle": cycle,
        "day": "Cycle %d" % cycle,
        "headline": headline, "wins": wins, "tasks": tasks,
        "top": top, "felt": mood_word, "kept": len(made),
        "domains": doms, "emotion": mind.brain.emotion_word(),
    })
    mind.brain.rest()
    report["brain"] = mind.brain.status_line()
    return report
