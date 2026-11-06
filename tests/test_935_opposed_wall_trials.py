"""Independent incident-mask, ancestry and exploratory-wall refusal contracts."""
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'docs/research/935-opposed-wall-trials-20261106/source'


def module(name):
    spec = importlib.util.spec_from_file_location(name, SOURCE/(name+'.py'))
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


admission = module('admit_opposed_walls')
inspection = module('verify_wall_inputs')
constructor = module('build_opposed_walls_v2')
filtering = module('filter_opposed_walls')


class OpposedWallTrials(unittest.TestCase):
    def test_complete_incident_masks_match_independent_boolean_membership(self):
        rng = np.random.default_rng(935)
        faces = rng.integers(0, 90, size=(250, 3))
        corners = np.array([[0, 3, 19, 89], [4, 27, 33, 65], [9, 10, 61, 80]])
        offsets, masks = admission.incident_masks(faces, corners)
        self.assertEqual(len(offsets), len(corners)+1)
        for index, selected in enumerate(corners):
            rows = masks[offsets[index]:offsets[index+1]]
            self.assertTrue(inspection.mask_matches(faces, selected, rows))
            self.assertEqual(rows.tolist(), sorted(set(rows)))

    def test_mask_refuses_missing_duplicate_or_unrelated_rows(self):
        faces = np.array([[0,1,4], [2,3,5], [4,5,6]])
        self.assertTrue(inspection.mask_matches(faces, [0,1,2,3], np.array([0,1])))
        for wrong in ([0], [0,1,1], [0,1,2], [1,0]):
            self.assertFalse(inspection.mask_matches(faces, [0,1,2,3], np.array(wrong)))

    def test_new_incident_face_invalidates_previously_complete_mask(self):
        faces = np.array([[0,1,4], [2,3,5]])
        self.assertTrue(inspection.mask_matches(faces, [0,1,2,3], np.array([0,1])))
        self.assertFalse(inspection.mask_matches(np.r_[faces, [[1,6,7]]], [0,1,2,3], np.array([0,1])))

    def test_whole_wall_filter_preserves_older_matching_numeric_id(self):
        data = dict(points=np.zeros((4,3)), global_node_ids=np.arange(4),
                    triangles=np.array([[0,1,2],[0,2,3],[1,0,3],[1,3,2]]),
                    source_opposed_wall_pair_ids=np.array([-1,-1,7,7]),
                    source_untried_pair_ids=np.array([7,7,-1,-1]),
                    inferred_surface_kind=np.array([0,6,7,7]),
                    opposed_wall_immediate_parent_face_rows=np.array([0,1,-1,-1]))
        result = filtering.compose(data, {7})
        self.assertTrue(np.array_equal(result['triangles'], data['triangles'][:2]))
        self.assertEqual(result['source_untried_pair_ids'].tolist(), [7,7])
        self.assertEqual(result['inferred_surface_kind'].tolist(), [0,6])
        self.assertEqual(result['opposed_wall_immediate_parent_face_rows'].tolist(), [0,1])
        self.assertTrue(np.array_equal(result['points'], data['points']))

    def test_filter_refuses_unrecognised_wall_id(self):
        with self.assertRaises(AssertionError):
            filtering.compose({'source_opposed_wall_pair_ids': np.array([-1,2,2])}, {3})

    def incidence_fixture(self):
        # Independent literal parent edge codes and directed edges for two skins.
        edges = np.array([[0,1],[1,4],[4,0],[2,3],[3,5],[5,2]])
        codes = edges.min(axis=1)*7+edges.max(axis=1)
        order = np.argsort(codes); codes = codes[order]; edges = edges[order]
        boundary = {'edge_origin_kind': np.ones(6, dtype=int)}
        def admit(patch, uses=np.ones(6, dtype=int), origins=boundary):
            return constructor.incidence_changes(np.array(patch), 7, codes, uses, edges,
                codes, np.arange(6), origins, np.zeros(6, dtype=int), 0)
        return codes, admit

    def test_literal_wall_reverses_both_acquired_border_uses(self):
        _, admit = self.incidence_fixture()
        self.assertIsNotNone(admit([[1,0,3],[1,3,2]]))
        self.assertIsNone(admit([[3,0,1],[2,3,1]]))

    def test_interior_edge_duplicate_patch_and_inferred_border_are_refused(self):
        codes, admit = self.incidence_fixture(); patch = [[1,0,3],[1,3,2]]
        counts = np.ones(6, dtype=int); counts[np.flatnonzero(codes == 1)] = 2
        self.assertIsNone(admit(patch, uses=counts))
        self.assertIsNone(admit(patch+patch))
        origins = np.ones(6, dtype=int); origins[np.flatnonzero(codes == 1)] = 8
        self.assertIsNone(admit(patch, origins={'edge_origin_kind': origins}))

    def test_executed_sources_and_unchanged_helpers_remain_hash_bound(self):
        result = json.loads((SOURCE.parent/'results.json').read_text())
        for row in result['executed_sources']:
            self.assertEqual(hashlib.sha256((SOURCE/row['name']).read_bytes()).hexdigest(), row['sha256'])
        for row in result['reused_helpers']:
            self.assertEqual(hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest(), row['sha256'])
        self.assertNotIn('/Users/', json.dumps(result))

    def test_kind_collision_is_preserved_and_versioned_correction_is_only_one_line(self):
        old = (SOURCE/'build_opposed_walls.py').read_text()
        corrected = (SOURCE/'build_opposed_walls_v2.py').read_text()
        self.assertEqual(corrected, old.replace('new[:] = 6\n', 'new[:] = 7\n', 1))
        result = json.loads((SOURCE.parent/'results.json').read_text())
        self.assertFalse(result['initial_provenance_stop']['first_output_physically_or_geometrically_admitted'])
        self.assertTrue(result['initial_provenance_stop']['first_output_preserved'])

    def test_exploratory_geometry_does_not_release_the_head(self):
        result = json.loads((SOURCE.parent/'results.json').read_text())
        self.assertTrue(result['final_audit']['surface_study_checks_passed'])
        self.assertFalse(result['goal_complete'])
        self.assertFalse(result['physical_acceptance'])
        self.assertFalse(result['manufacturing_authorized'])
        self.assertFalse(result['final_audit']['closed_volume'])
        self.assertEqual(result['provenance_namespace']['new_surface_kind'], 7)
        self.assertEqual(result['provenance_namespace']['new_boundary_origin'], 8)


if __name__ == '__main__':
    unittest.main()
