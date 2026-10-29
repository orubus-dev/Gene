import os
import random
import shutil
import tempfile
import unittest

from gene import trainer
from gene.endocrine import Endocrine
from gene.reflex import Reflexes
from gene.world import Predictor


class TestTrainer(unittest.TestCase):
    def setUp(self):
        self.rng = random.Random(42)
        self.refl = Reflexes()
        self.pred = Predictor()
        self.endo = Endocrine()
        self.genes = []

    def test_number_tasks_learned(self):
        solved = 0
        for _ in range(12):
            t = trainer.gen_number_task(self.rng, tier=1)
            out = trainer.train_task(t, self.genes, self.refl, self.pred,
                                     self.endo, self.rng)
            solved += out["solved"]
            if out["gene"]:
                self.genes.append(out["gene"])
        self.assertGreaterEqual(solved, 10)

    def test_reflex_forms_on_repeat(self):
        t = trainer.gen_string_task(self.rng, tier=1)
        for _ in range(3):
            out = trainer.train_task(t, self.genes, self.refl, self.pred,
                                     self.endo, self.rng)
            if out["gene"]:
                self.genes.append(out["gene"])
        arc = self.refl.consult(t["domain"], t["input"])
        self.assertIsNotNone(arc)

    def test_code_synthesis_solves_examples(self):
        solved = 0
        for _ in range(10):
            t = trainer.gen_code_task(self.rng, tier=1)
            out = trainer.train_task(t, self.genes, self.refl, self.pred,
                                     self.endo, self.rng)
            solved += out["solved"]
        self.assertGreaterEqual(solved, 8)

    def test_boolean_feedback_only(self):
        """The learner never sees the expected answer — attempts only carry ok flags."""
        t = trainer.gen_number_task(self.rng, tier=1)
        out = trainer.train_task(t, self.genes, self.refl, self.pred,
                                 self.endo, self.rng)
        for a in out["attempts"]:
            self.assertNotIn("expected", a)
            self.assertIn("ok", a)


class TestEndToEndCycle(unittest.TestCase):
    def test_train_sleep_evolve_improves_or_stays(self):
        from gene.mind import Mind
        tmp = tempfile.mkdtemp()
        try:
            m = Mind(root=os.path.join(tmp, "mind"))
            before = len(m.genes)
            m.train(budget=30)
            m.sleep()
            m.evolve(gens=1)
            self.assertGreaterEqual(len(m.genes), 1)
            self.assertGreaterEqual(m.progress["solved"], 5)
        finally:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
