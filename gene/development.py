"""Development — maturation gates.

A child learns to walk before it learns to talk. Curriculum domains and
capabilities unlock by lived milestones, never by config flags. Stages:

    sensorimotor  -> number/string/list babble, causal experiments
    skills        -> code synthesis from examples, multi-step compositions
    language      -> word-bound reasoning, teaching dialogues (future)

Promotion is earned by wins and concept growth; regression is possible
if the body degrades (apoptosis wiped too much).
"""
import json
import os

STAGES = ("sensorimotor", "skills", "language")
STAGE_RANK = {s: i for i, s in enumerate(STAGES)}

GATES = {
    # stage: (min_wins_total, min_sensorimotor_wins, min_concepts)
    "skills": (3, 3, 8),
    "language": (8, 4, 16),
}


class Development:

    def __init__(self, path=None):
        self.path = path
        self.stage = "sensorimotor"
        self.wins = {}          # domain -> count
        self.total_wins = 0
        self.milestones = []    # [{"t","stage","event"}]

    def record_win(self, domain):
        self.wins[domain] = self.wins.get(domain, 0) + 1
        self.total_wins += 1

    def sensorimotor_wins(self):
        return sum(v for k, v in self.wins.items() if k != "code")

    def maybe_promote(self, concept_count):
        """Check gates; return new stage or None."""
        cur = STAGE_RANK[self.stage]
        for st in STAGES[cur + 1:]:
            w, sm, c = GATES.get(st, (10 ** 9, 0, 0))
            if self.total_wins >= w and self.sensorimotor_wins() >= sm and concept_count >= c:
                self.stage = st
                self.milestones.append({"stage": st, "wins": self.total_wins})
                return st
        return None

    def allows(self, task_stage):
        return STAGE_RANK.get(task_stage, 0) <= STAGE_RANK[self.stage]

    def to_dict(self):
        return {"stage": self.stage, "wins": self.wins,
                "total_wins": self.total_wins, "milestones": self.milestones}

    def save(self):
        if self.path:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w") as f:
                json.dump(self.to_dict(), f, indent=1)

    def load_dict(self, d):
        if not d:
            return
        self.stage = d.get("stage", self.stage)
        self.wins = d.get("wins", {})
        self.total_wins = d.get("total_wins", sum(self.wins.values()))
        self.milestones = d.get("milestones", [])
