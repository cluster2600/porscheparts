"""Literal geometry and source-integrity controls for the new necessary test."""
import importlib.util
from pathlib import Path
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def module(name):
    path = ROOT/'docs/research/935-nonplanar-boundary-admission-20261106/source'/(name+'.py')
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class NonplanarBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.producer = module('audit_nonplanar_boundary')
        cls.checker = module('verify_nonplanar_boundary')

    def replay(self, points, owners):
        a, rim = self.producer.allowed_triangles(points, owners)
        b, other = self.checker.triangle_replay(points, owners)
        np.testing.assert_array_equal(a, b)
        np.testing.assert_array_equal(rim, other)
        count = self.producer.disk_count(len(points), a)
        self.assertEqual(count, self.checker.recursive_count(len(points), b))
        return a, rim, count

    def bowed(self):
        p = np.array([[0, 0, 0], [1.5, 0, 0], [1.5, 1.5, 1.5], [0, 1.5, 0.]])
        # Literal expected cap uses diagonal 0--2. Acquired owners lie outside it.
        third = [2, 0, 0, 2]
        owners = np.asarray([[p[i], p[(i+1) % 4], p[i]+p[(i+1) % 4]-p[k]]
                             for i, k in enumerate(third)])
        return p, owners

    def constant_owners(self, n):
        return np.tile(np.array([[0., 0, 0], [0, 1, 0], [1, 0, 0]]), (n, 1, 1))

    def test_bowed_literal_disk_passes_without_a_planar_shortcut(self):
        p, owners = self.bowed()
        centred = p-p.mean(axis=0)
        _, _, axes = np.linalg.svd(centred)
        self.assertGreater(np.abs(centred@axes[-1]).max(), .25)
        legal, rim, count = self.replay(p, owners)
        self.assertEqual(count, 1)
        self.assertIn((0, 1, 2), set(map(tuple, legal)))
        self.assertIn((0, 2, 3), set(map(tuple, legal)))
        self.assertTrue(rim.any(axis=1).all())

    def test_complete_convex_pentagon_and_hexagon_counts(self):
        for n, expected in [(3, 1), (4, 2), (5, 5), (6, 14)]:
            angle = np.arange(n)*2*np.pi/n
            points = np.column_stack((np.cos(angle), np.sin(angle), np.zeros(n)))
            legal, rim, count = self.replay(points, self.constant_owners(n))
            self.assertEqual(len(legal), n*(n-1)*(n-2)//6)
            self.assertEqual(int(rim.sum()), n*(n-2))
            self.assertEqual(count, expected)

    def test_reversing_acquired_material_side_refuses_the_disk(self):
        p, owners = self.bowed()
        _, rim, count = self.replay(p, owners[:, [0, 2, 1]])
        self.assertEqual(count, 0)
        self.assertFalse(rim.any())

    def test_flat_reversed_contour_refuses_fixed_owner_normals(self):
        points = np.array([[0., 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]])
        self.assertEqual(self.replay(points, self.constant_owners(4))[2], 2)
        self.assertEqual(self.replay(points[::-1], self.constant_owners(4))[2], 0)

    def test_zero_area_source_corner_triangle_is_not_available(self):
        points = np.array([[0., 0, 0], [1, 0, 0], [2, 0, 0]])
        legal, rim, count = self.replay(points, self.constant_owners(3))
        self.assertEqual(len(legal), 0)
        self.assertFalse(rim.any())
        self.assertEqual(count, 0)

    def test_exact_power_of_two_scale_and_translation(self):
        points, owners = self.bowed()
        baseline = self.replay(points, owners)
        shifted = self.replay(points*8+[32., -16, 4], owners*8+[32., -16, 4])
        np.testing.assert_array_equal(baseline[0], shifted[0])
        np.testing.assert_array_equal(baseline[1], shifted[1])
        self.assertEqual(baseline[2], shifted[2])

    def test_missing_combination_cannot_be_replaced_by_a_local_edge_flag(self):
        legal = np.array([[0, 1, 3], [0, 2, 3]])
        self.assertEqual(self.producer.disk_count(4, legal), 0)
        self.assertEqual(self.checker.recursive_count(4, legal), 0)

    def test_source_face_identity_and_winding_are_not_self_attested(self):
        points, owner_points = self.bowed()
        all_points, inverse = np.unique(owner_points.reshape(-1, 3), axis=0, return_inverse=True)
        triangles = inverse.reshape(-1, 3)
        rim_nodes = [int(np.flatnonzero(np.all(all_points == p, axis=1))[0]) for p in points]
        mesh = dict(points=all_points, triangles=triangles, original_face_ids=np.arange(4),
                    inferred_surface_kind=np.zeros(4, dtype=np.int64))
        border = dict(boundary=np.column_stack((rim_nodes, np.roll(rim_nodes, -1))),
                      owners=np.arange(4), edge_origin_kind=np.ones(4, dtype=np.int64))
        raw = dict(vertices=all_points, triangles=triangles)
        for fn in (self.producer.raw_owners, self.checker.recover_owners):
            actual, keys = fn(mesh, border, raw, range(4))
            np.testing.assert_array_equal(actual, owner_points)
            self.assertEqual(keys.shape, (4, 3))
            bad = {**mesh, 'original_face_ids': np.array([1, 1, 2, 3])}
            with self.assertRaises((AssertionError, KeyError)):
                fn(bad, border, raw, range(4))
            bad = {**mesh, 'triangles': triangles[:, [0, 2, 1]]}
            with self.assertRaises(AssertionError):
                fn(bad, border, raw, range(4))

    def test_complete_boundary_and_owner_corruptions(self):
        mesh = dict(points=np.array([[0., 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]]),
                    triangles=np.array([[0, 1, 2], [0, 2, 3]]))
        border = dict(boundary=np.array([[0, 1], [1, 2], [2, 3], [3, 0]]), owners=np.array([0, 0, 1, 1]))
        self.assertEqual(self.checker.inspect_complete_boundary(mesh, border), 4)
        with self.assertRaises(AssertionError):
            self.checker.inspect_complete_boundary(mesh, {**border, 'owners': np.array([1, 0, 1, 1])})
        with self.assertRaises(AssertionError):
            self.checker.inspect_complete_boundary(mesh, {**border, 'boundary': border['boundary'][::-1, ::-1]})

    def test_scope_separates_bowed_planar_rank_and_inferred_sources(self):
        bowed, _ = self.bowed()
        planar = bowed.copy()
        planar[:, 2] = 0
        line = np.array([[0., 0, 0], [.5, 0, 0], [1, 0, 0]])
        walks = [bowed, planar, line, bowed]
        points = np.concatenate(walks)
        offsets = np.r_[0, np.cumsum([len(p) for p in walks])]
        edges = np.concatenate([np.column_stack((np.arange(a, b), np.roll(np.arange(a, b), -1)))
                                for a, b in zip(offsets[:-1], offsets[1:])])
        origins = np.ones(len(edges), dtype=np.int64)
        origins[-1] = 6
        border = dict(boundary=edges, offsets=offsets, cycle_edges=np.arange(len(edges)), edge_origin_kind=origins)
        a, first = self.producer.select_walks(dict(points=points), border)
        b, second = self.checker.independent_scope(dict(points=points), border)
        self.assertEqual(first, second)
        self.assertEqual([x[0] for x in a], [0])
        self.assertEqual([x[0] for x in b], [0])
        self.assertEqual(first['rank_below_two'], 1)
        self.assertEqual(first['compact_planar_outside_new_scope'], 1)
        self.assertEqual(first['mixed_or_nonacquired'], 1)


if __name__ == '__main__':
    unittest.main()
