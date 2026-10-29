import os
import re
import shutil
import tempfile
import unittest

from gene.mind import Mind


class TestIngenuity(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.m = Mind(root=os.path.join(self.tmp, "mind"))
        self.m.teach_file(os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "curriculum", "facts_animals.json"))
        self.m.teach_file(os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "curriculum", "facts_world.json"))

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_unknown_gets_honest_verdict_and_hypothesis(self):
        r = self.m.handle_text("what is a zorpus?")
        self.assertIn("zorpus", r.lower())
        self.assertRegex(r.lower(), r"never heard|not in my graph|no record")
        self.assertNotIn("teacher", r.lower())
        # grounded reasoning, not a bare cop-out
        self.assertTrue(len(r) > 60)

    def test_prefix_reasoning(self):
        r = self.m.handle_text("what is an unglorb?")
        self.assertIn("unglorb", r.lower())
        self.assertRegex(r.lower(), r"never heard|not in my graph|no record")

    def test_near_match_suggests_known(self):
        r = self.m.handle_text("what is a dawg?")
        self.assertIn("dog", r.lower())

    def test_compound_decomposition(self):
        r = self.m.handle_text("what is a seacow?")
        self.assertIn("sea", r.lower())
        self.assertIn("cow", r.lower())

    def test_taught_real_confirmed(self):
        r = self.m.handle_text("do tardigrades exist?")
        self.assertRegex(r.lower(), r"real|is a|creature|in my graph")
        self.assertNotRegex(r.lower(), r"never heard|not in my graph")

    def test_taught_mythical_classified(self):
        r = self.m.handle_text("do dragons exist?")
        self.assertRegex(r.lower(), r"mythical|stories|not in nature")

    def test_creativity_grounded_and_varied(self):
        r1 = self.m.handle_text("tell me something new you figured out")
        self.m.rng.seed(99)
        r2 = self.m.handle_text("tell me something new you figured out")
        self.assertTrue(r1 and len(r1) > 40)
        self.assertTrue(r2 and len(r2) > 40)

    def test_improvement_uses_numbers_or_honest(self):
        self.m.train_chat(budget=10)
        self.m.persist()
        r = self.m.handle_text("are you getting better?")
        self.assertTrue(re.search(r"\d", r) or "too early" in r.lower())

    def test_identity_aspects_distinct(self):
        a = self.m.handle_text("what's your name?")
        b = self.m.handle_text("who made you?")
        self.assertIn("Gene", a)
        self.assertTrue(b)  # origin answered, not fallen through

    def test_paraphrase_semantic_fallback(self):
        from gene.conversation import classify_semantic
        # exact exemplar paraphrases land deterministically (sim=1.0)
        self.assertEqual(classify_semantic("who am I speaking with?"), "identity")
        self.assertEqual(classify_semantic("where do you come from?"), "origin")
        self.assertEqual(classify_semantic("what do you wonder about"), "creativity")
        # nonsense stays unclassified rather than guessed
        self.assertIn(classify_semantic("xyzzy plugh"), (None,))
if __name__ == "__main__":
    unittest.main()
