"""Check exact edge subdivision, including an IEEE midpoint failure fixture."""
import importlib.util
import sys
import unittest
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))


@unittest.skipUnless(importlib.util.find_spec('numpy'), 'NumPy runtime required')
class ExactEdgeSubdivisionTests(unittest.TestCase):
    def setUp(self):
        import numpy as np
        import calculix_exact_edge_subdivision as kernel
        self.np, self.kernel = np, kernel
        self.vertices = np.array([[0., 0., -1.], [0., 0., 1.], [1., 0., 0.],
                                  [0., 1., 0.], [-1., 0., 0.], [0., -1., 0.]])
        self.cells = np.array([[0, 1, 2, 3], [0, 1, 3, 4],
                               [0, 1, 4, 5], [0, 1, 5, 2]], dtype=np.int64)

    def tilted(self):
        points = self.vertices.copy()
        points[:, 0] += 1.
        points[0, 2], points[1, 2] = 0., 3.
        points[1, 0] = 1. + 3 * self.np.spacing(1.)
        return points

    def test_default_closed_star_preserves_inputs_and_boundary(self):
        before = self.vertices.tobytes(), self.cells.tobytes()
        point, children, proof = self.kernel.propose(self.vertices, self.cells, (0, 1), 6)
        self.np.testing.assert_array_equal(point, [0., 0., 0.])
        self.assertEqual(children.shape, (8, 4))
        self.assertEqual(self.kernel.boundary(children), self.kernel.boundary(self.cells))
        self.assertTrue(proof['exact_per_parent_partition_preserved'])
        self.assertEqual(before, (self.vertices.tobytes(), self.cells.tobytes()))

    def test_exact_thirds_recover_a_rounded_midpoint(self):
        vertices = self.tilted()
        with self.assertRaisesRegex(AssertionError, 'Rounded edge point'):
            self.kernel.propose(vertices, self.cells, (0, 1), 6)
        for t, ulps, height in [(Fraction(1, 3), 1, 1.), (Fraction(2, 3), 2, 2.)]:
            point, children, _ = self.kernel.propose(vertices, self.cells, (0, 1), 6, fraction=t)
            self.assertEqual(point[0], 1. + ulps * self.np.spacing(1.))
            self.assertEqual(point[2], height)
            points = self.np.vstack([vertices, point])
            for i, parent in enumerate(self.cells):
                volume = self.kernel.volume(vertices[parent])
                self.assertEqual(self.kernel.volume(points[children[2*i]]), t * volume)
                self.assertEqual(self.kernel.volume(points[children[2*i+1]]), (1-t) * volume)

    def test_unrepresentable_third_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'Rounded edge point'):
            self.kernel.propose(self.vertices, self.cells, (0, 1), 6, fraction=Fraction(1, 3))

    def test_endpoints_and_float_fraction_are_rejected(self):
        for t in [Fraction(0), Fraction(1), Fraction(-1, 3), .5]:
            with self.subTest(fraction=t), self.assertRaisesRegex(AssertionError, 'Exact interior rational'):
                self.kernel.propose(self.vertices, self.cells, (0, 1), 6, fraction=t)

    def test_open_link_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'open or nonmanifold'):
            self.kernel.propose(self.vertices, self.cells[:3], (0, 1), 6)

    def test_inverted_parent_and_volume_cap_are_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'Nonpositive parent'):
            self.kernel.propose(self.vertices, self.cells[:, [1, 0, 2, 3]], (0, 1), 6)
        with self.assertRaisesRegex(AssertionError, 'Candidate volume'):
            self.kernel.propose(self.vertices, self.cells, (0, 1), 6, volume_cap=Fraction(1, 100))


if __name__ == '__main__':
    unittest.main()
