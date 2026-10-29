"""The predictor — the world-model loop.

Before the organism acts it *predicts*; after acting it *reconciles*.
Prediction error = surprise = belief revision. This is the smallest honest
version of a world model: causal confidence per (domain, action signature),
updated only by lived outcomes — never handed down from code.
"""
import json
import os


class Predictor:

    def __init__(self, path=None):
        self.path = path
        self.rules = {}   # sig -> {"n": int, "ok": int, "p": float}
        if path and os.path.exists(path):
            try:
                with open(path) as f:
                    self.rules.update(json.load(f))
            except Exception:
                self.rules = {}

    def signature(self, domain, steps):
        return domain + ":" + "|".join(
            "%s(%s)" % (s.get("op"), ",".join("%s=%s" % (k, v) for k, v in sorted((s.get("args") or {}).items())))
            for s in steps
        )

    def predict(self, domain, steps):
        """Probability this action does what it looks like it does."""
        r = self.rules.get(self.signature(domain, steps))
        return r["p"] if r else 0.35  # born naive

    def reconcile(self, domain, steps, outcome_ok):
        """Belief revision on observation. Returns surprise in [0,1]."""
        sig = self.signature(domain, steps)
        r = self.rules.setdefault(sig, {"n": 0, "ok": 0, "p": 0.35})
        prev = r["p"]
        r["n"] += 1
        r["ok"] += 1 if outcome_ok else 0
        # incremental mean with gentle prior decay
        r["p"] = (r["ok"] + 1.0) / (r["n"] + 2.0)
        return abs(prev - r["p"]) + (0.0 if outcome_ok == (prev >= 0.5) else 0.4)

    def confident(self, domain, steps, threshold=0.7, n=3):
        r = self.rules.get(self.signature(domain, steps))
        return bool(r and r["n"] >= n and r["p"] >= threshold)

    def save(self):
        if self.path:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w") as f:
                json.dump(self.rules, f)
