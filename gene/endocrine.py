"""The endocrine system — global hormonal modulators.

A handful of scalars bias the whole mind at once, the way cortisol or
dopamine biases an entire brain. No learning here, just regulation:

    curiosity  -> drives exploration when the world surprises us
    urgency    -> widens search budgets under load
    energy     -> depletes with effort, restores during sleep
    mood       -> running average of how well things are going
"""
import json
import os

DEFAULTS = {"curiosity": 0.5, "urgency": 0.3, "energy": 1.0, "mood": 0.5}


class Endocrine:

    def __init__(self, path=None):
        self.path = path
        self.h = dict(DEFAULTS)
        if path and os.path.exists(path):
            try:
                with open(path) as f:
                    self.h.update(json.load(f))
            except Exception:
                pass
        self._clamp()

    def _clamp(self):
        for k in self.h:
            self.h[k] = max(0.0, min(1.0, float(self.h[k])))

    # ---- event-driven secretion ---------------------------------------------
    def surprise(self, amount):
        """Prediction error: the world didn't do what we thought."""
        self.h["curiosity"] = min(1.0, self.h["curiosity"] + 0.6 * amount)
        self.h["mood"] = max(0.0, self.h["mood"] - 0.3 * amount)

    def success(self, amount=1.0):
        """A hypothesis worked: calm down, feel good."""
        self.h["curiosity"] = max(0.0, self.h["curiosity"] - 0.4 * amount)
        self.h["mood"] = min(1.0, self.h["mood"] + 0.2 * amount)

    def load(self, amount=1.0):
        self.h["urgency"] = min(1.0, self.h["urgency"] + 0.3 * amount)

    def effort(self, amount=1.0):
        self.h["energy"] = max(0.0, self.h["energy"] - 0.02 * amount)

    def rested(self, amount=1.0):
        self.h["energy"] = min(1.0, self.h["energy"] + amount)
        self.h["urgency"] = max(0.0, self.h["urgency"] - 0.4 * amount)

    # ---- hormonal effects on cognition ---------------------------------------
    def search_budget(self, base):
        """Urgency + curiosity widen the trial budget."""
        mult = 1.0 + 1.5 * self.h["urgency"] + 1.0 * self.h["curiosity"]
        return max(2, int(round(base * mult)))

    def exploration_rate(self):
        """Curiosity favors novel/random hypotheses over exploitation."""
        return self.h["curiosity"]

    def save(self):
        if self.path:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w") as f:
                json.dump(self.h, f, indent=1)
