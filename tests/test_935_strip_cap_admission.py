"""Bounded source-owner admission and provenance tests using synthetic geometry."""
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'docs/research/935-strip-cap-admission-20261106/source'


def module(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


admission = module(SOURCE/'admit_strip_caps.py')
inspection = module(SOURCE/'verify_strip_cap_admission.py')
assembly = module(SOURCE/'assemble_strip_cap_candidate.py')
polygon = module(ROOT/'docs/research/935-acquisition-gap-trials-20261106/source/inspect_acquisition_patches.py')


class StripCapAdmission(unittest.TestCase):
    def setUp(self):
        self.job = dict(limits=dict(min_edges=3, max_edges=128, max_diagonal_nominal_mm=3.,
                                   max_plane_residual_nominal_mm=.25, minimum_adjacent_normal_absolute_p10=.8),
                        minimum_acquired_signed_normal_dot=0., minimum_acquired_signed_normal_p10=.8)
        self.points = np.array([[0., 0., 0.], [0., 1., 0.], [1., 1., 0.], [1., 0., 0.]])
        self.normals = np.tile([0., 0., 1.], (4, 1))

    def test_literal_controls_cover_signed_source_and_orientation_refusals(self):
        self.assertEqual(inspection.controls(self.job, polygon.simple_projection), 6)

    def test_absolute_alignment_does_not_authorize_an_opposed_source_layer(self):
        self.assertTrue(np.all(np.abs((-self.normals)@np.array([0., 0., 1.])) == 1))
        reasons, _, _ = inspection.independent_screen(self.points, -self.normals, self.job, polygon.simple_projection)
        self.assertIn('opposed_or_tangent_acquired_owner', reasons)
        self.assertIn('acquired_signed_normal_cone', reasons)

    def test_clockwise_source_boundary_requires_forward_fill_normal(self):
        reasons, _, _ = inspection.independent_screen(self.points, self.normals, self.job, polygon.simple_projection)
        self.assertFalse(reasons)
        reasons, _, _ = inspection.independent_screen(self.points[::-1], self.normals, self.job, polygon.simple_projection)
        self.assertIn('opposed_or_tangent_acquired_owner', reasons)

    def test_independent_inspection_is_translation_invariant(self):
        before = inspection.independent_screen(self.points, self.normals, self.job, polygon.simple_projection)
        after = inspection.independent_screen(self.points+[1000000., -1000000., 30000.], self.normals, self.job, polygon.simple_projection)
        self.assertEqual(before, after)

    def test_strip_owner_recovers_both_acquired_owners_and_excludes_other_origins(self):
        mesh = dict(inferred_surface_kind=np.array([0, 4, 0]), original_face_ids=np.array([5, -1, 6]), source_frontier_pair_ids=np.array([-1, 0, -1]))
        boundary = dict(owners=np.arange(3), edge_origin_kind=np.array([1, 6, 3]))
        previous = dict(inferred_surface_kind=np.array([0, 0]), original_face_ids=np.array([8, 9]))
        old_boundary = dict(boundary_face_rows=np.array([0, 1])); census = dict(selected_pair_edge_ids=np.array([[0, 1]]))
        offsets, rows = admission.acquired_references(mesh, boundary, previous, old_boundary, census)
        self.assertEqual(offsets.tolist(), [0, 1, 3, 3]); self.assertEqual(rows.tolist(), [5, 8, 9])
        previous['inferred_surface_kind'][1] = 3
        with self.assertRaises(AssertionError):
            admission.acquired_references(mesh, boundary, previous, old_boundary, census)

    def test_tangent_source_owner_is_refused_even_with_other_aligned_owners(self):
        normal = np.tile([0., 0., 1.], (20, 1)); normal[0] = [1., 0., 0.]
        reasons, _, p10 = inspection.independent_screen(self.points, normal, self.job, polygon.simple_projection)
        self.assertGreaterEqual(p10, .8); self.assertIn('opposed_or_tangent_acquired_owner', reasons)

    def test_parent_coordinates_faces_and_all_earlier_ancestry_remain_exact(self):
        base = dict(points=self.points.copy(), triangles=np.array([[0, 1, 2]]), global_node_ids=np.arange(4),
                    inferred_surface_kind=np.array([4]), source_patch_curve_ids=np.array([30000042]),
                    original_face_ids=np.array([-1]), source_frontier_pair_ids=np.array([42]), omission_ancestor=np.array([19]))
        result = assembly.compose(base, {7:np.array([[2, 1, 3]])})
        np.testing.assert_array_equal(result['points'], base['points'])
        np.testing.assert_array_equal(result['triangles'][:1], base['triangles'])
        for key in ('inferred_surface_kind', 'source_patch_curve_ids', 'original_face_ids', 'source_frontier_pair_ids', 'omission_ancestor'):
            np.testing.assert_array_equal(result[key][:1], base[key])
        self.assertEqual(result['source_strip_cap_curve_ids'].tolist(), [-1, 7])
        self.assertEqual(result['source_patch_curve_ids'].tolist(), [30000042, 40000007])
        self.assertEqual(result['source_frontier_pair_ids'].tolist(), [42, -1])
        self.assertEqual(result['inferred_surface_kind'].tolist(), [4, 5])

    def test_empty_composition_does_not_invent_faces(self):
        base = dict(points=self.points, triangles=np.array([[0, 1, 2]]), global_node_ids=np.arange(4), original_face_ids=np.array([17]))
        result = assembly.compose(base, {})
        np.testing.assert_array_equal(result['triangles'], base['triangles'])
        self.assertEqual(result['source_strip_cap_curve_ids'].tolist(), [-1])

    def test_invalid_provenance_shape_and_out_of_bounds_patch_fail_closed(self):
        base = dict(points=self.points, triangles=np.array([[0, 1, 2]]), global_node_ids=np.arange(4), original_face_ids=np.array([17]))
        with self.assertRaises(AssertionError):
            assembly.compose(base, {3:np.array([[1, 2, 9]])})
        with self.assertRaises(AssertionError):
            assembly.compose(base, {-1:np.array([[1, 2, 3]])})
        base['original_face_ids'] = np.array([17, 18])
        with self.assertRaises(AssertionError):
            assembly.compose(base, {})

    def test_executed_sources_and_helpers_are_bound(self):
        result = json.loads((SOURCE.parent/'results.json').read_text())
        for row in result['executed_sources']:
            self.assertEqual(hashlib.sha256((SOURCE/row['name']).read_bytes()).hexdigest(), row['sha256'])
        for row in result['reused_helpers']:
            self.assertEqual(hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest(), row['sha256'])
        for row in result['public_artifacts']:
            self.assertEqual(hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest(), row['sha256'])
        self.assertNotIn('/Users/', json.dumps(result))

    def test_complete_scope_and_independent_admission_denominators(self):
        result = json.loads((SOURCE.parent/'results.json').read_text())
        self.assertEqual(result['admission']['complete_walk_denominator'], 1489)
        self.assertEqual(result['admission']['new_strip_border_walks'], 993)
        self.assertEqual(result['admission']['admitted_trials'], 304)
        self.assertEqual(result['admission']['unchanged_acquired_walks_not_retried'], 462)
        self.assertEqual(result['admission']['other_origin_walks_not_retried'], 34)
        self.assertTrue(result['independent_admission']['admission_independently_verified'])
        self.assertEqual(result['local_inspection']['local_patches_accepted'], 304)

    def test_surface_acceptance_never_grants_physical_or_manufacturing_release(self):
        result = json.loads((SOURCE.parent/'results.json').read_text())
        final = result['final_audit']
        self.assertTrue(final['surface_study_checks_passed'])
        self.assertGreater(final['remaining_boundary_edges'], 90000)
        self.assertFalse(final['closed_volume'])
        self.assertFalse(final['physical_acceptance'])
        self.assertFalse(result['goal_complete'])
        self.assertFalse(result['manufacturing_authorized'])


if __name__ == '__main__':
    unittest.main()
