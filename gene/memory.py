"""Episodic memory + the sleep cycle.

Episodes are the raw experience log (jsonl). Sleep replays them:
co-active concepts wire together (hippocampal -> cortical consolidation),
unused links decay, weak concepts die (apoptosis). The episode file
rotates so the brain never bloats the repo.
"""
import json
import os
import time

MAX_EPISODES = 1500


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


def sleep_cycle(graph, episodes, decay=0.01, replay_k=200):
    """One night's work: replay, consolidate, decay, prune.

    Returns a report dict.
    """
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
