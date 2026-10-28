"""The immune system — novelty detection and habituation.

A body must notice "this is NOT like anything I've seen" and also stop
reacting to what turns out harmless. Prediction error raises the alarm;
a fingerprint of the alarming pattern is remembered so the same shock
habitulates — immune memory. Nothing here knows facts; it knows danger
and novelty, which is what an immune system actually knows.
"""
import hashlib
import json
import os


class ImmuneSystem:

    def __init__(self, path=None, threshold=0.45):
        self.path = path
        self.threshold = threshold
        self.memory = {}   # fingerprint -> {"hits": int, "last": ts}
        if path and os.path.exists(path):
            try:
                with open(path) as f:
                    d = json.load(f)
                self.threshold = d.get("threshold", threshold)
                self.memory = d.get("memory", {})
            except Exception:
                pass

    def fingerprint(self, context):
        raw = json.dumps(context, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha1(raw.encode()).hexdigest()[:16]

    def survey(self, prediction_error, fatigue=0.0, context=None):
        """Returns (is_novel, is_danger). Fatigue raises the reaction threshold
        (a tired body ignores more). Habituation dampens repeat shocks."""
        thr = self.threshold * (1.0 + 0.35 * fatigue)
        danger = prediction_error >= thr
        if not danger:
            return (False, False)
        fp = self.fingerprint(context or prediction_error)
        rec = self.memory.get(fp)
        if rec is None:
            self.memory[fp] = {"hits": 1, "last": 0.0}
            return (True, True)          # first contact: novel AND alarming
        rec["hits"] += 1
        # habituation: the shock fades with exposure
        return (False, prediction_error >= thr * (1.0 + 0.5 * min(3, rec["hits"])))

    def tolerant(self, context):
        """Have we seen this pattern enough to stop panicking?"""
        rec = self.memory.get(self.fingerprint(context))
        return bool(rec and rec["hits"] >= 3)

    def save(self):
        if self.path:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w") as f:
                json.dump({"threshold": self.threshold, "memory": self.memory}, f)
