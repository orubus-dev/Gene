"""Reflex arc — the fast path.

When the same stimulus keeps mapping to the same successful response,
the cortex-grade loop is skipped entirely: stimulus -> cached response.
This is System 1. Learning it is automatic; forgetting is via decay.
"""
import hashlib
import json
import os

MAX_ARCS = 30000          # the body keeps its strongest arcs, prunes the rest


def stimulus_key(domain, payload):
    raw = json.dumps([domain, payload], sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


class Reflexes:

    def __init__(self, path=None):
        self.path = path
        self.arcs = {}   # key -> {"steps":..., "hits": int, "strength": float}
        if path and os.path.exists(path):
            try:
                with open(path) as f:
                    self.arcs.update(json.load(f))
            except Exception:
                self.arcs = {}

    def consult(self, domain, payload):
        arc = self.arcs.get(stimulus_key(domain, payload))
        if arc and arc["strength"] >= 0.6:
            return arc["steps"]
        return None

    def reinforce(self, domain, payload, steps, amount=0.4):
        k = stimulus_key(domain, payload)
        arc = self.arcs.get(k)
        if arc and arc["steps"] == steps:
            arc["hits"] += 1
            arc["strength"] = min(1.0, arc["strength"] + amount)
        elif arc is None:
            self.arcs[k] = {"steps": steps, "hits": 1, "strength": amount}
        else:
            # conflicting response: overwrite and reset — the body rewires
            self.arcs[k] = {"steps": steps, "hits": 1, "strength": amount}
        if len(self.arcs) > MAX_ARCS:
            keep = sorted(self.arcs.items(),
                          key=lambda kv: -kv[1]["strength"])[:MAX_ARCS]
            self.arcs = dict(keep)

    def decay(self, rate=0.05):
        for k in list(self.arcs.keys()):
            self.arcs[k]["strength"] -= rate
            if self.arcs[k]["strength"] <= 0.0:
                del self.arcs[k]

    def save(self):
        if self.path:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w") as f:
                json.dump(self.arcs, f)
