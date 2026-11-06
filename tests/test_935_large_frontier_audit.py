"""Large unequal-sampling source diagnostics and independently checked ancestry."""
import importlib.util
from pathlib import Path
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT/path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class LargeFrontierDiagnosticTests(unittest.TestCase):
    def setUp(self):
        folder = 'docs/research/935-large-frontier-audit-20261106/source/'
        self.producer = module(folder+'audit_large_frontier.py', 'large_diagnostic_producer')
        self.checker = module(folder+'verify_large_frontier.py', 'large_diagnostic_checker')
        self.legacy = module('docs/research/935-end-wall-admission-20261106/source/admit_end_walls.py', 'frozen_large_signed_screen')
        self.scalar = module('docs/research/935-end-wall-admission-20261106/source/verify_end_wall_admission.py', 'frozen_large_signed_scalar')
        self.limits = dict(min_edges=3, max_edges=128, max_diagonal_nominal_mm=3.,
                           max_plane_residual_nominal_mm=.25, min_distinct_acquired_owners=2,
                           minimum_acquired_binormal_signed_p10=.8)
        upper = np.c_[np.linspace(0., 30., 81), np.full(81, .1), np.zeros(81)]
        lower = np.c_[np.linspace(30., 0., 53), np.full(53, -.1), np.zeros(53)]
        self.points = np.r_[upper, lower]
        tangent = np.roll(self.points, -1, axis=0)-self.points
        self.normals = np.cross(tangent, [0., 0., -1.])
        self.normals /= np.linalg.norm(self.normals, axis=1)[:, None]

    def describe(self, points=None, normals=None):
        points = self.points if points is None else points
        normals = self.normals if normals is None else normals
        def no_projection(_points):
            raise AssertionError('A large contour must not be passed off as an old compact domain')
        positions = np.arange(len(points))
        result = self.producer.describe(points, positions, normals, positions, self.limits, self.legacy, no_projection)
        peer = self.checker.scalar_diagnostics(points, positions, normals, positions, self.limits, self.scalar)
        return result, peer

    def test_unequal_long_chains_are_diagnostic_only(self):
        row, peer = self.describe()
        self.assertEqual(set(row['legacy_scope_refusals']), {'edge_count', 'diagonal'})
        self.assertTrue(row['fixed_planar_acquired_binormal_diagnostic_compatible'])
        self.assertTrue(peer['compatible'])
        self.assertTrue(row['principal_second_span_at_most_0_5'])
        self.assertFalse(row['projection_contact_or_native_construction_admitted'])
        self.assertTrue(np.allclose(row['principal_squared_singular_values'], peer['squared_singular_values'], atol=1e-9))
        self.assertTrue(np.allclose(row['principal_spans_nominal_mm'], [30., .2, 0.], atol=1e-9))
        self.assertAlmostEqual(row['acquired_binormal_signed_p10'], 1.)

    def test_void_side_normals_refuse_planar_compatibility(self):
        row, peer = self.describe(normals=-self.normals)
        self.assertFalse(row['fixed_planar_acquired_binormal_diagnostic_compatible'])
        self.assertFalse(peer['compatible'])
        self.assertLess(row['acquired_binormal_signed_p10'], 0.)

    def test_annular_inner_rim_and_global_reversal_do_not_gain_disk_admission(self):
        points = self.points[::-1].copy()
        normals = -np.roll(self.normals[::-1], -1, axis=0)
        row, peer = self.describe(points, normals)
        self.assertFalse(row['fixed_planar_acquired_binormal_diagnostic_compatible'])
        self.assertFalse(peer['compatible'])

    def test_rank_one_frame_is_not_accepted_as_a_plane(self):
        points = self.points.copy(); points[:, 1:] = 0
        # Keep distinct endpoints for this diagnostic by using a monotone line.
        points[:, 0] = np.arange(len(points), dtype=float)
        row, peer = self.describe(points)
        self.assertFalse(row['principal_plane_unique'])
        self.assertFalse(peer['plane_unique'])
        self.assertFalse(row['fixed_planar_acquired_binormal_diagnostic_compatible'])


class LargeFrontierAncestryTests(unittest.TestCase):
    def setUp(self):
        folder = 'docs/research/935-large-frontier-audit-20261106/source/'
        self.producer = module(folder+'audit_large_frontier.py', 'large_ancestry_producer')
        self.checker = module(folder+'verify_large_frontier.py', 'large_ancestry_checker')
        self.refs = np.array([[7, 0, 1], [3, 2, 3]])
        self.census = dict(source_edge_keys=self.refs, selected_pair_edge_ids=np.array([[0, 1]]), selected_pair_classes=np.array([1]))
        self.registry = dict(global_pair_ids=np.array([0]), birth_census_sha256=np.array(['a'*64]),
            birth_census_proof_sha256=np.array(['b'*64]), birth_local_pair_ids=np.array([0]),
            birth_rounds=np.array([3]), raw_pair_keys=np.array([[3, 2, 3, 7, 0, 1]]), geometry_classes=np.array([1]))
        self.sources = {'a'*64: dict(census=self.census, proof_hash='b'*64, birth_round=3, class_policy='two_classes')}

    def test_registry_recovers_ordered_supports_without_reordering(self):
        result = self.producer.birth_references(self.registry, self.sources)
        self.assertTrue(np.array_equal(result[0], self.refs))

    def test_wrong_birth_hash_round_or_class_refused(self):
        for change in ({'birth_census_proof_sha256': np.array(['c'*64])},
                       {'birth_rounds': np.array([99])}, {'geometry_classes': np.array([0])}):
            with self.assertRaises(AssertionError):
                self.producer.birth_references(dict(self.registry, **change), self.sources)

    def test_missing_class_table_needs_explicit_opposed_policy(self):
        census = {k: v for k, v in self.census.items() if k != 'selected_pair_classes'}
        sources = {'a'*64: dict(self.sources['a'*64], census=census)}
        with self.assertRaises(AssertionError):
            self.producer.birth_references(self.registry, sources)
        sources['a'*64]['class_policy'] = 'opposed_only'
        self.assertTrue(np.array_equal(self.producer.birth_references(self.registry, sources)[0], self.refs))

    def test_inferred_quad_requires_oriented_cross_edge_and_exact_source(self):
        points = np.array([[0., 0., .1], [.2, 0., .1], [.2, 0., -.1], [0., 0., -.1]])
        raw = dict(vertices=points)
        for face in ([1, 0, 3], [0, 3, 1], [3, 1, 0]):
            mesh = dict(points=points.copy(), triangles=np.array([face]), inferred_surface_kind=np.array([9]), original_face_ids=np.array([-1]))
            signature = self.checker.inferred_signature(mesh, 0, [0, 3], raw, self.refs, 9, 21)
            self.assertEqual(signature, [9, 21, 7, 3, -1, 0, 3])
        with self.assertRaises(AssertionError):
            self.checker.inferred_signature(mesh, 0, [1, 3], raw, self.refs, 9, 21)
        bad = dict(mesh, triangles=np.array([[3, 0, 1]]))
        with self.assertRaises(AssertionError):
            self.checker.inferred_signature(bad, 0, [0, 3], raw, self.refs, 9, 21)
        bad = dict(mesh, points=points.copy()); bad['points'][0, 0] += .001
        with self.assertRaises(AssertionError):
            self.checker.inferred_signature(bad, 0, [0, 3], raw, self.refs, 9, 21)


if __name__ == '__main__':
    unittest.main()
