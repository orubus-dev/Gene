"""The concept graph — semantic memory.

Concepts are nodes with a kind, attributes, word bindings and an HDC
vector (stored as its seed string — vectors are recomputed, never saved).
Links carry strength; co-activation strengthens them (Hebb), disuse
weakens them (apoptosis). Nothing here knows any facts — this is pure
structure that knowledge flows through.
"""
import time

from . import hdc

KINDS = ("entity", "action", "property", "relation", "word", "domain", "meta")


class ConceptGraph:

    def __init__(self):
        self.nodes = {}        # id -> node dict
        self.by_word = {}      # lowercase word -> id

    # ---- construction ------------------------------------------------------
    def ensure(self, cid, kind="entity", attrs=None, words=()):
        node = self.nodes.get(cid)
        if node is None:
            node = {
                "id": cid,
                "kind": kind if kind in KINDS else "entity",
                "attrs": {},
                "words": [],
                "vec": cid,                     # seed string; vector recomputed
                "links": {},                    # target_id -> strength
                "created": time.time(),
                "touched": time.time(),
            }
            self.nodes[cid] = node
        if attrs:
            for k, v in attrs.items():
                node["attrs"][k] = v
        for w in words or ():
            self.bind_word(node, w)
        return node

    def bind_word(self, node, word):
        w = str(word).lower().strip()
        if w and w not in node["words"]:
            node["words"].append(w)
        self.by_word[w] = node["id"]

    def relate(self, a, b, rel="assoc", strength=0.5):
        if a == b:
            return
        self.ensure(a); self.ensure(b)
        key = "%s>%s" % (rel, b)
        old = self.nodes[a]["links"].get(key, 0.0)
        self.nodes[a]["links"][key] = min(1.0, old + strength)
        self.nodes[b]["touched"] = time.time()

    def unlink(self, a, rel, b):
        self.nodes.get(a, {}).get("links", {}).pop("%s>%s" % (rel, b), None)

    # ---- retrieval ----------------------------------------------------------
    def get(self, cid):
        return self.nodes.get(cid)

    def by_similarity(self, seed, topn=5):
        q = hdc.vec(seed)
        scored = [(n["id"], hdc.sim(q, hdc.vec(n["vec"]))) for n in self.nodes.values()]
        scored.sort(key=lambda t: -t[1])
        return scored[:topn]

    def lookup_word(self, word):
        cid = self.by_word.get(str(word).lower().strip())
        return self.nodes.get(cid) if cid else None

    def neighbors(self, cid, rel=None):
        out = []
        for key, strength in self.nodes.get(cid, {}).get("links", {}).items():
            r, target = key.split(">", 1)
            if rel is None or r == rel:
                out.append((r, target, strength))
        out.sort(key=lambda t: -t[2])
        return out

    def activate(self, seeds, topn=8):
        """Spreading activation: bundle the seed vectors, find nearest concepts."""
        if isinstance(seeds, str):
            seeds = [seeds]
        q = hdc.bundle([hdc.vec(s) for s in seeds]) if len(seeds) > 1 else hdc.vec(seeds[0])
        return self.by_similarity_seedvec(q, topn)

    def by_similarity_seedvec(self, q, topn=5):
        scored = [(n["id"], hdc.sim(q, hdc.vec(n["vec"]))) for n in self.nodes.values()]
        scored.sort(key=lambda t: -t[1])
        return scored[:topn]

    # ---- plasticity ----------------------------------------------------------
    def hebbian(self, ids, amount=0.1):
        """Fire together, wire together."""
        uniq = [i for i in dict.fromkeys(ids) if i in self.nodes]
        for i in range(len(uniq)):
            for j in range(i + 1, len(uniq)):
                self.relate(uniq[i], uniq[j], rel="assoc", strength=amount)
                self.relate(uniq[j], uniq[i], rel="assoc", strength=amount)
        for cid in uniq:
            self.nodes[cid]["touched"] = time.time()

    def decay(self, rate=0.01):
        for n in self.nodes.values():
            for k in list(n["links"].keys()):
                n["links"][k] -= rate
                if n["links"][k] <= 0.0:
                    del n["links"][k]

    def apoptosis(self, min_strength=0.05, max_nodes=4000):
        """Prune: weak, isolated, long-untouched concepts die off."""
        now = time.time()
        doomed = []
        for n in self.nodes.values():
            if n["kind"] == "meta":
                continue  # core self-concepts persist
            strong = [s for _, _, s in self.neighbors(n["id"])]
            if not strong and (now - n["touched"]) > 3600:
                doomed.append(n["id"])
            elif sum(strong) < min_strength and (now - n["touched"]) > 86400:
                doomed.append(n["id"])
        if len(self.nodes) > max_nodes:  # overpopulation: cut the weakest
            ranked = sorted(
                (n for n in self.nodes.values() if n["kind"] != "meta"),
                key=lambda n: sum(s for _, _, s in self.neighbors(n["id"])),
            )
            doomed += [n["id"] for n in ranked[: len(self.nodes) - max_nodes]]
        for cid in doomed:
            self.nodes.pop(cid, None)
        self.by_word = {w: i for w, i in self.by_word.items() if i in self.nodes}
        return len(doomed)

    # ---- persistence ----------------------------------------------------------
    def to_dict(self):
        return {"nodes": self.nodes}

    @classmethod
    def from_dict(cls, d):
        g = cls()
        g.nodes = d.get("nodes", {})
        g.by_word = {}
        for n in g.nodes.values():
            for w in n.get("words", []):
                g.by_word[w.lower()] = n["id"]
        return g
