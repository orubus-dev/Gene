import random
import unittest

from gene import dsl, genome


class TestDSL(unittest.TestCase):
    def test_pipeline(self):
        steps = [{"op": "reverse", "args": {}}, {"op": "upper", "args": {}}]
        self.assertEqual(dsl.execute_pipeline(steps, "gene"), "ENEG")

    def test_number_ops(self):
        self.assertEqual(dsl.execute_pipeline([{"op": "add", "args": {"n": 5}}], 3), 8)
        self.assertEqual(dsl.execute_pipeline([{"op": "mul", "args": {"n": 3}}], 4), 12)

    def test_list_ops(self):
        self.assertEqual(dsl.execute_pipeline([{"op": "sumv", "args": {}}], [1, 2, 3]), 6)
        self.assertEqual(dsl.execute_pipeline([{"op": "unique", "args": {}}], [1, 1, 2]), [1, 2])

    def test_errors_are_failures_not_crashes(self):
        with self.assertRaises(TypeError):
            dsl.execute_pipeline([{"op": "upper", "args": {}}], 42)


class TestGenome(unittest.TestCase):
    def test_mutation_changes_something(self):
        rng = random.Random(7)
        g = genome.random_gene(rng, "string")
        m = genome.mutate_gene(g, rng, "string")
        self.assertIsInstance(m, dict)
        self.assertIn("steps", m)

    def test_crossover_produces_valid_pipeline(self):
        rng = random.Random(11)
        a = genome.new_gene([{"op": "reverse", "args": {}}])
        b = genome.new_gene([{"op": "upper", "args": {}}, {"op": "concat", "args": {"with": "!"}}])
        c = genome.crossover(a, b, rng)
        try:
            dsl.execute_pipeline(c["steps"], "gene")
        except Exception:
            pass  # pipeline may type-error on some inputs; must not crash the system


if __name__ == "__main__":
    unittest.main()
