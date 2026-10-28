import unittest

from gene import hdc


class TestHDC(unittest.TestCase):
    def test_deterministic(self):
        self.assertEqual(hdc.vec("gene"), hdc.vec("gene"))

    def test_self_similarity(self):
        a = hdc.vec("alpha")
        self.assertAlmostEqual(hdc.sim(a, a), 1.0)

    def test_distinct_low_similarity(self):
        a, b = hdc.vec("alpha"), hdc.vec("beta")
        self.assertLess(abs(hdc.sim(a, b)), 0.06)

    def test_bind_commutative_and_dissimilar(self):
        a, b = hdc.vec("alpha"), hdc.vec("beta")
        ab, ba = hdc.bind(a, b), hdc.bind(b, a)
        self.assertEqual(ab, ba)
        self.assertLess(abs(hdc.sim(ab, a)), 0.06)
        self.assertLess(abs(hdc.sim(ab, b)), 0.06)

    def test_bundle_prototype(self):
        a, b, c = hdc.vec("a"), hdc.vec("b"), hdc.vec("c")
        s = hdc.bundle([a, b, c])
        self.assertGreater(hdc.sim(s, a), 0.4)
        self.assertGreater(hdc.sim(s, b), 0.4)

    def test_permute_preserves_similarity(self):
        a = hdc.vec("seq")
        self.assertAlmostEqual(hdc.sim(a, hdc.permute(a, 0)), 1.0)

    def test_sequence_encoding(self):
        s1 = hdc.encode_sequence([hdc.vec("x"), hdc.vec("y")])
        s2 = hdc.encode_sequence([hdc.vec("x"), hdc.vec("y")])
        s3 = hdc.encode_sequence([hdc.vec("y"), hdc.vec("x")])
        self.assertAlmostEqual(hdc.sim(s1, s2), 1.0)
        self.assertLess(hdc.sim(s1, s3), 0.8)


if __name__ == "__main__":
    unittest.main()
