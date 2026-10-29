import os
import shutil
import tempfile
import unittest

from gene.endocrine import Endocrine
from gene.mind import Mind


class TestKnowledge(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.m = Mind(root=os.path.join(self.tmp, "mind"))

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_teach_then_know(self):
        r = self.m.knowledge.teach({"concepts": [
            {"id": "zorp", "kind": "entity", "words": ["zorp"],
             "attrs": {"description": "a creature from fiction"}}]})
        self.assertEqual(r["concepts"], 1)
        ans = self.m.handle_text("what is zorp")
        self.assertIn("creature", ans)

    def test_fact_then_query(self):
        self.m.handle_text("a flink is a machine")
        ans = self.m.handle_text("what is flink")
        self.assertIn("machine", ans)

    def test_infer_is_a(self):
        self.m.handle_text("a wug is a animal")
        self.m.handle_text("a zib is a wug")
        # zib is-a wug is-a animal: inference walks one hop up from zib
        gained = self.m.knowledge.infer("zib")
        self.assertIn("is-a", gained or {})

    def test_inquire_queues_question(self):
        self.m.handle_text("what is quasimodo")
        qs = self.m._load("questions.json", [])
        self.assertTrue(any("quasimodo" in q["q"] for q in qs))

    def test_provenance(self):
        self.m.handle_text("a dax is a tool")
        p = self.m.knowledge.provenance("dax")
        self.assertIsNotNone(p)
        self.assertEqual(p["kind"], "entity")


class TestLiveLoop(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.m = Mind(root=os.path.join(self.tmp, "mind"))

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_compute_learned_live(self):
        ans = self.m.handle_text("compute 7 plus 5")
        self.assertIn("12", ans)

    def test_sequence_next(self):
        ans = self.m.handle_text("next in 2 4 6 8 10")
        self.assertIn("12", ans)

    def test_string_op(self):
        ans = self.m.handle_text("reverse helix")
        self.assertIn("xileh", ans)

    def test_list_op(self):
        ans = self.m.handle_text("sum 3 9 4")
        self.assertIn("16", ans)

    def test_unknown_word_seeks_knowledge(self):
        ans = self.m.handle_text("tell me about blorptastic")
        self.assertIn("blorptastic", ans)
        self.assertIn("study list", ans)
        self.assertNotIn("teacher", ans.lower())

    def test_status(self):
        ans = self.m.handle_text("status")
        self.assertIn("concepts", ans)


class TestEndocrine(unittest.TestCase):
    def test_surprise_raises_curiosity(self):
        e = Endocrine()
        before = e.h["curiosity"]
        e.surprise(1.0)
        self.assertGreater(e.h["curiosity"], before)

    def test_budget_modulated(self):
        e = Endocrine()
        e.h["urgency"] = 1.0
        self.assertGreater(e.search_budget(10), 10)


if __name__ == "__main__":
    unittest.main()
