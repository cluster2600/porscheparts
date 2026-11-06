"""Preserve exhaustive geometry-candidate choice with fewer qualification calls."""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from calculix_candidate_order import choose


class CandidateOrderTests(unittest.TestCase):
    def test_matches_independent_exhaustive_choice(self):
        rng = random.Random(993008)
        for _ in range(1000):
            n = rng.randrange(1, 24)
            rows = [(rng.randrange(4) / 3., 1. + rng.randrange(4), k)
                    for k in range(n)]
            valid = {k for k in range(n) if rng.randrange(3)}
            eligible = [row for row in rows if row[2] in valid]
            expected = max(eligible, key=lambda row: (row[0], row[1], -row[2])) if eligible else None
            calls = []

            def evaluate(key):
                calls.append(key)
                return {'qualified_key': key} if key in valid else None

            actual = choose(rows, evaluate)
            self.assertEqual(None if actual is None else actual[0], expected)
            if expected is not None:
                self.assertEqual(actual[1], {'qualified_key': expected[2]})
            self.assertLessEqual(len(calls), n)
            self.assertEqual(len(calls), len(set(calls)))

    def test_refused_top_candidate_and_stable_ties(self):
        calls = []

        def evaluate(key):
            calls.append(key)
            return None if key == 0 else {'valid': True}

        actual = choose([(2., 1., 0), (1., 2., 2), (1., 2., 1), (0., 9., 3)], evaluate)
        self.assertEqual(actual[0], (1., 2., 1))
        self.assertEqual(calls, [0, 1])

    def test_empty_and_no_valid_candidate(self):
        self.assertIsNone(choose([], lambda key: self.fail('Unexpected evaluation')))
        calls = []
        self.assertIsNone(choose([(0., 1., 1), (0., 2., 2)], lambda key: calls.append(key)))
        self.assertEqual(calls, [2, 1])

    def test_invalid_ranking_refused_before_qualification(self):
        bad = [[(float('nan'), 1., 0)], [(float('inf'), 1., 0)],
               [(-1., 1., 0)], [(1., 0., 0)], [(1., float('nan'), 0)],
               [(1., 1., -1)], [(1., 1., 1.5)],
               [(1., 1., 0), (2., 1., 0)]]
        for rows in bad:
            with self.subTest(rows=rows), self.assertRaises(AssertionError):
                choose(rows, lambda key: self.fail('Invalid input reached qualification'))


if __name__ == '__main__':
    unittest.main()
