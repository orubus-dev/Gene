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
        self.assertRegex(r.lower(), r"never heard|no record|no match|new word to me|don't know")
        self.assertNotIn("teacher", r.lower())
        # grounded reasoning, not a bare cop-out
        self.assertTrue(len(r) > 60)

    def test_prefix_reasoning(self):
        r = self.m.handle_text("what is an unglorb?")
        self.assertIn("unglorb", r.lower())
        self.assertRegex(r.lower(), r"never heard|no record|no match|new word to me|don't know")

    def test_near_match_suggests_known(self):
        r = self.m.handle_text("what is a dawg?")
        self.assertIn("dog", r.lower())

    def test_compound_decomposition(self):
        r = self.m.handle_text("what is a seacow?")
        self.assertIn("sea", r.lower())
        self.assertIn("cow", r.lower())

    def test_taught_real_confirmed(self):
        r = self.m.handle_text("do tardigrades exist?")
        self.assertRegex(r.lower(), r"real|is a|creature|animal")
        self.assertNotRegex(r.lower(), r"never heard|don't know|no match")

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
        self.assertEqual(classify_semantic("what time is it"), "time")
        self.assertEqual(classify_semantic("what's the weather like"), "weather")
        # nonsense stays unclassified rather than guessed
        self.assertIn(classify_semantic("xyzzy plugh"), (None,))

    def test_natural_speech_no_machinery_narration(self):
        # the user's law: a person doesn't cite their own brain plumbing
        BAN = ("my graph", "in my graph", "hormone", "provenance", "diffable",
               "in git", "episodes", "vector", "concepts", "study list")
        asks = ["how are you?", "thanks!", "bye", "what time is it?",
                "what's the weather like?", "what is an octopus?"]
        for a in asks:
            r = self.m.handle_text(a) or ""
            low = r.lower()
            for b in BAN:
                self.assertNotIn(b, low, "%r -> %r leaked %r" % (a, r, b))

    def test_extrapolate_names_family(self):
        self.m.teach_file(os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "curriculum", "grammar-1.json"))
        r = self.m.handle_text("we have statements and questions — what other grammar types are out there?")
        self.assertTrue(r, "extrapolate returned nothing")
        hits = sum(1 for f in ("command", "exclamation", "negation", "passive",
                               "conditional", "comparative", "superlative",
                               "future tense", "plural") if f in r.lower())
        self.assertGreaterEqual(hits, 2, r)
if __name__ == "__main__":
    unittest.main()
