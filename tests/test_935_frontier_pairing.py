"""Adversarial pairing and omission tests; public fixtures never replace scan evidence."""
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'docs/research/935-frontier-pairing-20261106/source'


def module(name):
    spec = importlib.util.spec_from_file_location(name, SOURCE/(name+'.py'))
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


census = module('census_frontier_pairs')
inspection = module('verify_frontier_pairs_v2')
construction = module('build_frontier_strips')
filtering = module('filter_frontier_strips')


class FrontierPairing(unittest.TestCase):
    def setUp(self):
        self.limits = dict(maximum_cross_endpoint_distance_nominal_mm=.5, maximum_tangent_dot=-.8,
                           minimum_owner_normal_dot=.8, minimum_signed_bridge_triangle_normal_dot=.8)

    def test_positive_and_negative_literal_geometric_controls(self):
        self.assertEqual(inspection.controls(self.limits), 10)

    def test_exhaustive_search_includes_exact_radius_and_excludes_other_walks(self):
        points = np.array([[0., 0., 0.], [.5, 0., 0.], [np.nextafter(.5, 1), 0., 0.], [.1, 0., 0.]])
        pairs = inspection.exhaustive_pairs(points, np.array([0, 0, 0, 1]), np.arange(4), .5, 1, 10)
        self.assertEqual(pairs.tolist(), [[0, 1], [1, 2]])

    def test_search_resource_envelope_fails_closed(self):
        with self.assertRaises(AssertionError):
            inspection.exhaustive_pairs(np.zeros((4, 3)), np.zeros(4), np.arange(4), .5, 2, 2)

    def test_all_edges_of_a_nearest_tie_are_refused(self):
        pairs = np.array([[0, 1], [0, 2], [1, 3]])
        scores = np.array([.1, .1, .3])
        selected, best, ambiguous = inspection.reciprocal_unique(pairs, scores, 1e-12)
        actual, _, mask = census.mutual_unique(pairs, scores, 4, 1e-12)
        self.assertEqual(selected.tolist(), [])
        self.assertEqual(actual.tolist(), [])
        self.assertEqual(ambiguous.tolist(), [0])
        self.assertEqual(np.flatnonzero(mask).tolist(), [0])

    def test_sub_tolerance_score_difference_is_ambiguous(self):
        selected, _, ambiguous = inspection.reciprocal_unique(np.array([[0, 1], [0, 2]]), np.array([.1, .1+5e-13]), 1e-12)
        self.assertFalse(len(selected)); self.assertEqual(ambiguous.tolist(), [0])

    def test_pairing_never_uses_a_nonreciprocal_best_neighbor(self):
        pairs = np.array([[0, 1], [1, 2]])
        selected, _, _ = inspection.reciprocal_unique(pairs, np.array([.3, .1]), 1e-12)
        self.assertEqual(pairs[selected].tolist(), [[1, 2]])

    def test_third_incident_face_is_refused_before_construction(self):
        patch = np.array([[1, 0, 3], [1, 3, 2]])
        nv = 4; codes = np.array([1, 6]); counts = np.array([2, 1]); directions = np.array([[0, 1], [2, 1]])
        boundary = {'edge_origin_kind': np.array([1, 1])}
        self.assertIsNone(construction.incidence_changes(patch, nv, codes, counts, directions,
                                                        codes, np.arange(2), boundary, np.zeros(2), 0))

    def test_complete_rejection_removes_both_triangles_only(self):
        parent = np.array([[0, 1, 2], [0, 2, 3]])
        data = dict(points=np.arange(12).reshape(4, 3), global_node_ids=np.arange(4),
                    triangles=np.r_[parent, [[3, 2, 1], [3, 1, 0], [0, 3, 2], [0, 2, 1]]],
                    source_frontier_pair_ids=np.array([-1, -1, 4, 4, 9, 9]), provenance=np.arange(6))
        result = filtering.compose(data, {4})
        np.testing.assert_array_equal(result['triangles'][:2], parent)
        np.testing.assert_array_equal(result['points'], data['points'])
        self.assertEqual(result['source_frontier_pair_ids'].tolist(), [-1, -1, 9, 9])
        self.assertEqual(result['provenance'].tolist(), [0, 1, 4, 5])
        with self.assertRaises(AssertionError):
            filtering.compose(data, {7})

    def test_executed_sources_and_reused_helpers_match_the_receipt(self):
        result = json.loads((SOURCE.parent/'results.json').read_text())
        for row in result['executed_sources']:
            self.assertEqual(hashlib.sha256((SOURCE/row['name']).read_bytes()).hexdigest(), row['sha256'])
        for row in result['reused_helpers']:
            self.assertEqual(hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest(), row['sha256'])
        self.assertNotIn('/Users/', json.dumps(result))

    def test_whole_mesh_refusals_and_remaining_openings_are_reported(self):
        result = json.loads((SOURCE.parent/'results.json').read_text())
        self.assertEqual(result['construction']['proposed_pairs'], 1315)
        self.assertEqual(result['construction']['accepted_pairs'], 1101)
        self.assertEqual(result['initial_inspection']['whole_mesh_intersection_pairs'], 41)
        self.assertEqual(result['filtering']['removed_whole_pairs'], 37)
        final = result['final_inspection']
        self.assertEqual(final['added_strip_pairs'], 1064)
        self.assertEqual(final['added_triangles'], 2128)
        self.assertTrue(final['surface_study_checks_passed'])
        self.assertGreater(final['remaining_boundary_edges'], 90000)
        self.assertFalse(final['closed_volume'])
        self.assertFalse(final['manufacturing_authorized'])


if __name__ == '__main__':
    unittest.main()
