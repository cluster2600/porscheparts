"""Analytic exact-distance controls, including nonvertex support witnesses."""
import importlib.util
from pathlib import Path
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT/'docs/research/935-nonplanar-boundary-admission-20261106/source/verify_disk_support.py'


class NonplanarDiskSupportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('independent_disk_support', PATH)
        cls.checker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.checker)

    def test_plane_interior_exact_radius_and_next_binary64_value(self):
        tri = np.array([[0., 0, 0], [1, 0, 0], [0, 1, 0]])
        self.assertTrue(self.checker.within([.25, .25, .25], tri))
        self.assertFalse(self.checker.within([.25, .25, np.nextafter(.25, np.inf)], tri))

    def test_edge_and_vertex_clamping(self):
        tri = np.array([[0., 0, 0], [1, 0, 0], [0, 1, 0]])
        self.assertTrue(self.checker.within([.5, -.25, 0], tri))
        self.assertFalse(self.checker.within([.5, np.nextafter(-.25, -np.inf), 0], tri))
        self.assertTrue(self.checker.within([-.25, 0, 0], tri))
        self.assertFalse(self.checker.within([-.25, -.25, 0], tri))

    def test_large_triangle_can_support_a_point_far_from_every_vertex(self):
        tri = np.array([[-10., -10, 0], [10, -10, 0], [0, 10, 0]])
        q = np.array([0., 0, .25])
        self.assertTrue(np.all(np.linalg.norm(tri-q, axis=1) > .25))
        self.assertTrue(self.checker.within(q, tri))

    def test_degenerate_original_triangles_have_closed_edge_support(self):
        for tri in [np.array([[0., 0, 0], [1, 0, 0], [2, 0, 0]]), np.zeros((3, 3))]:
            self.assertTrue(self.checker.within([0., 0, .125], tri))
            self.assertFalse(self.checker.within([0., 0, .5], tri))

    def test_exact_dyadic_scale_and_translation_preserve_the_comparison(self):
        tri = np.array([[0., 0, 0], [1, 0, 0], [0, 1, 0]])
        for q in [np.array([.25, .25, .25]), np.array([.25, .25, .5])]:
            expected = self.checker.within(q, tri)
            self.assertEqual(self.checker.within(q*8+[32., -8, 4], tri*8+[32., -8, 4], radius=2), expected)

    def test_support_filtered_triangulation_counts_whole_disks(self):
        full = np.array([[0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3]])
        self.assertEqual(self.checker.count_disks(4, full), 2)
        self.assertEqual(self.checker.count_disks(4, np.array([[0, 1, 2], [0, 2, 3]])), 1)
        self.assertEqual(self.checker.count_disks(4, np.array([[0, 1, 2]])), 0)


if __name__ == '__main__':
    unittest.main()
