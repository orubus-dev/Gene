"""Knowledge acquisition — the five ways of knowing.

The core law: NO factual knowledge is hard-coded in this codebase. The
organism only owns *mechanisms* for gaining knowledge, the way a child
owns senses and questions:

    1. observe    — accept a fact seen in the environment
    2. experiment — act, watch the result, remember the outcome
    3. infer      — derive what follows from what is already linked
    4. inquire    — ask the teacher, queue the question if absent
    5. inherit    — specialize/generalize from related concepts

Teaching (the channel Orubus/any operator uses) is structured *data*
under curriculum/ — lessons the organism digests through these same
mechanisms. Remove the curriculum and it starts empty but still learns.
"""
import json
import os
import time


class KnowledgeSystem:

    def __init__(self, graph, episodes, questions_path):
        self.graph = graph
        self.episodes = episodes
        self.questions_path = questions_path

    # ---- 1. observe ----------------------------------------------------------
    def observe(self, subject, attrs=None, words=(), relations=(), coactive=None):
        node = self.graph.ensure(subject, attrs=attrs or {}, words=words)
        for r in relations or ():
            self.graph.relate(subject, r.get("to"), rel=r.get("rel", "assoc"),
                              strength=float(r.get("strength", 0.5)))
        self.episodes.record("observe", {
            "subject": subject, "coactive": coactive or [subject] + [r.get("to") for r in relations or ()],
        })
        return node

    # ---- 2. experiment ---------------------------------------------------------
    def experiment(self, domain, payload, runner):
        """Run an action in a world, record the outcome as experience."""
        try:
            result, ok = runner(payload)
        except Exception as e:
            result, ok = None, False
        self.episodes.record("experiment", {"domain": domain, "payload": payload,
                                            "ok": ok, "coactive": [domain, "experiment"]})
        return result, ok

    # ---- 3. infer ---------------------------------------------------------------
    def infer(self, cid):
        """Derive what follows from links: is-a inheritance, causes chaining."""
        node = self.graph.get(cid)
        if not node:
            return None
        gained = {}
        for rel, target, strength in self.graph.neighbors(cid):
            t = self.graph.get(target)
            if not t:
                continue
            if rel == "is-a":
                gained.setdefault("is-a", []).append(target)
                for k, v in t["attrs"].items():
                    if k not in node["attrs"]:
                        gained[k] = v
                        node["attrs"]["%s (inherited from %s)" % (k, target)] = v
            if rel == "causes":
                gained.setdefault("causes", []).append(target)
        if gained:
            self.episodes.record("infer", {"subject": cid, "gained": list(gained.keys()),
                                           "coactive": [cid] + [t for _, t, _ in self.graph.neighbors(cid)]})
        return gained

    # ---- 4. inquire ---------------------------------------------------------------
    def inquire(self, question):
        """Ask the teacher. If the teacher isn't here, queue the question —
        a real mechanism: mind/questions.json is the organism raising its hand."""
        q = {"t": time.time(), "q": question}
        os.makedirs(os.path.dirname(self.questions_path), exist_ok=True)
        asked = []
        if os.path.exists(self.questions_path):
            try:
                with open(self.questions_path) as f:
                    asked = json.load(f)
            except Exception:
                asked = []
        asked.append(q)
        with open(self.questions_path, "w") as f:
            json.dump(asked[-200:], f, indent=1)
        self.episodes.record("inquire", {"q": question, "coactive": ["teacher", "question"]})
        return q

    # ---- 5. inherit ------------------------------------------------------------------
    def inherit(self, parent_cid, child_cid, drop=()):
        """Specialize: child is-a parent, minus overridden traits."""
        parent = self.graph.get(parent_cid)
        if not parent:
            return None
        attrs = {k: v for k, v in parent["attrs"].items() if k not in drop}
        child = self.graph.ensure(child_cid, attrs=attrs)
        self.graph.relate(child_cid, parent_cid, rel="is-a", strength=0.9)
        self.episodes.record("inherit", {"parent": parent_cid, "child": child_cid,
                                         "coactive": [parent_cid, child_cid]})
        return child

    # ---- teaching channel ---------------------------------------------------------------
    def teach(self, pack):
        """Digest a lesson pack (structured data). Returns a report.

        Pack schema:
        {
          "concepts": [{"id","kind","words","attrs","relations":[{"to","rel"}]}],
          "examples": [{"domain","input","expected"}]      # experience, not answers:
        }
        Examples become *tasks the organism must solve* in its learning loop —
        the teacher shows the goal, never the procedure.
        """
        report = {"concepts": 0, "examples": 0}
        for c in pack.get("concepts", []):
            node = self.observe(c["id"], attrs=c.get("attrs"), words=c.get("words"),
                                relations=c.get("relations"))
            if c.get("kind"):
                node["kind"] = c["kind"]
            report["concepts"] += 1
        report["examples"] = len(pack.get("examples", []))
        return report

    def teach_file(self, path):
        with open(path, "r", encoding="utf-8") as f:
            pack = json.load(f)
        return self.teach(pack)

    # ---- provenance -----------------------------------------------------------------------
    def provenance(self, cid):
        """How do we know what we know? Trace the sources of each attribute."""
        node = self.graph.get(cid)
        if not node:
            return None
        return {
            "id": cid,
            "kind": node["kind"],
            "attrs": node["attrs"],
            "relations": [{"rel": r, "to": t, "strength": round(s, 3)}
                          for r, t, s in self.graph.neighbors(cid)],
            "words": node["words"],
            "age_hours": round((time.time() - node["created"]) / 3600.0, 2),
        }
