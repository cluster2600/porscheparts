"""Exact cancellation must not remove a merely close or reversed triangle."""
import importlib.util
from pathlib import Path
import sys
import unittest

import numpy as np

SOURCE = Path(__file__).resolve().parents[1]/"twins/962-cylinder-head-f0/source"
sys.path.insert(0, str(SOURCE))
SPEC = importlib.util.spec_from_file_location("quality_distance", SOURCE/"audit_quality_distance.py")
MODULE = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(MODULE)


class ExactDistanceReduction(unittest.TestCase):
    def test_exact_cancellation_and_complete_target_are_required(self):
        p = np.array([[0., 0, 0], [1., 0, 0], [0, 1., 0]])
        f = np.array([[0, 1, 2]])
        q = p.copy(); q[0, 0] = -0.
        self.assertTrue(MODULE.shared_faces(p, f, q, f[:, [1, 2, 0]])[0].all())
        self.assertFalse(MODULE.shared_faces(p, f, q, f[:, [0, 2, 1]])[0].any())
        q[1, 0] = np.nextafter(1., 2.)
        self.assertFalse(MODULE.shared_faces(p, f, q, f)[0].any())
        target_p = np.concatenate([p, p+[0, 0, 1.]])
        target_f = np.array([[0, 1, 2], [3, 4, 5]])
        calls = []
        def native(a, fa, b, fb, tolerance, factor, normalize):
            calls.append((fa.copy(), fb.copy(), normalize))
            return 0., 0., 1., 0., 0.
        result = MODULE.directed(p, f, target_p, target_f, query=native)
        self.assertEqual(result["target_faces"], 2)
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(calls[0][1]), 2)
        self.assertIs(calls[0][2], False)
        empty = MODULE.directed(p, np.empty((0, 3), dtype=int), target_p, target_f, query=native)
        self.assertEqual((empty["lower"], empty["upper"]), (0., 0.))
        self.assertIs(empty["native_called"], False)
        self.assertEqual(len(calls), 1)
        for tolerance in (True, 0., float("nan")):
            with self.subTest(tolerance=tolerance), self.assertRaises(ValueError):
                MODULE.directed(p, f, target_p, target_f, tolerance, query=native)


if __name__ == "__main__":
    unittest.main()
