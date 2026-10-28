import os
import random
import shutil
import tempfile
import unittest

from gene import concepts, memory
from gene.reflex import Reflexes
from gene.world import Predictor


class TestConceptGraph(unittest.TestCase):
    def setUp(self):
        self.g = concepts.ConceptGraph()

    def test_ensure_idempotent(self):
        a = self.g.ensure("fire", attrs={"hot": "yes"})
        b = self.g.ensure("fire", attrs={"hot": "yes"})
        self.assertIs(a, b)
        self.assertEqual(len(self.g.nodes), 1)

    def test_hebbian_strengthens(self):
        self.g.ensure("x"); self.g.ensure("y")
        self.g.hebbian(["x", "y"], amount=0.3)
        links = dict((r + ">" + t, s) for r, t, s in self.g.neighbors("x"))
        self.assertGreater(links.get("assoc>y", 0), 0.2)

    def test_decay_and_apoptosis(self):
        self.g.ensure("ephemeral")
        self.g.decay(rate=0.5)
        pruned = self.g.apoptosis(min_strength=100.0)
        self.assertIn("ephemeral", self.g.nodes)  # too young, but decayed links gone
        self.g.nodes["ephemeral"]["touched"] = 0
        self.g.apoptosis()
        self.assertNotIn("ephemeral", self.g.nodes)

    def test_word_lookup(self):
        self.g.ensure("fire", words=["fire"])
        self.assertEqual(self.g.lookup_word("FIRE")["id"], "fire")


class TestMemoryAndSleep(unittest.TestCase):
    def test_episodes_record_and_replay(self):
        tmp = tempfile.mkdtemp()
        try:
            eps = memory.EpisodicMemory(os.path.join(tmp, "ep.jsonl"))
            eps.record("a", {"coactive": ["x", "y"]})
            eps.record("b", {"coactive": ["y", "z"]})
            self.assertEqual(len(eps.replay()), 2)
        finally:
            shutil.rmtree(tmp)

    def test_sleep_consolidates(self):
        tmp = tempfile.mkdtemp()
        try:
            g = concepts.ConceptGraph()
            g.ensure("x"); g.ensure("y")
            eps = memory.EpisodicMemory(os.path.join(tmp, "ep.jsonl"))
            eps.record("a", {"coactive": ["x", "y"]})
            r = memory.sleep_cycle(g, eps)
            self.assertEqual(r["replayed"], 1)
            self.assertGreaterEqual(r["consolidated"], 1)
        finally:
            shutil.rmtree(tmp)


class TestReflexAndPredictor(unittest.TestCase):
    def test_reflex_forms_after_repeats(self):
        r = Reflexes()
        self.assertIsNone(r.consult("number", [2, 3]))
        r.reinforce("number", [2, 3], [{"op": "sumv", "args": {}}])
        self.assertIsNone(r.consult("number", [2, 3]))  # not strong yet
        r.reinforce("number", [2, 3], [{"op": "sumv", "args": {}}])
        self.assertIsNotNone(r.consult("number", [2, 3]))

    def test_predictor_reconciles(self):
        p = Predictor()
        steps = [{"op": "sumv", "args": {}}]
        p0 = p.predict("number", steps)
        for ok in (True, True, True, True):
            p.reconcile("number", steps, ok)
        self.assertGreater(p.predict("number", steps), p0)
        self.assertTrue(p.confident("number", steps))


if __name__ == "__main__":
    unittest.main()
