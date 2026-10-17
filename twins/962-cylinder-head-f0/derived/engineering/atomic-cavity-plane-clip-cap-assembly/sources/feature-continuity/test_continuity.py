"""Four tiny literal continuity tests, prepared unrun; no head inputs/native query."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
import numpy as np
from patch_helpers import patch_topology

PREP = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('held_stage_continuity', PREP/'audit_continuity.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
module.np = np; module.patch_topology = patch_topology
FIXTURES = json.loads((PREP/'literal-fixtures.json').read_text())


class ContinuityTests(unittest.TestCase):
    def compare(self, row):
        return module.compare_region(np.asarray(row['points_before'], dtype='<f8'),
            np.asarray(row['faces_before'], dtype='<u8'), np.asarray(row['points_after'], dtype='<f8'),
            np.asarray(row['faces_after'], dtype='<u8'), row['region_ids'],
            np.asarray(row['coordinate_origins'], dtype='<u8'),
            np.asarray(row['face_sources'], dtype='<u8'), row['fixed_faces'])

    def test_new_interior_point_disk_and_fixed_exterior(self):
        row = FIXTURES['square_refinement_with_fixed_exterior']; result = self.compare(row)
        self.assertEqual(result['before'], row['expected_before'])
        self.assertEqual(result['after'], row['expected_after'])
        self.assertEqual(result['fixed_candidate_cap_face_ids'], [4])
        self.assertEqual(result['new_local_coordinate_points'], 1)
        self.assertEqual(result['exterior_faces'], 1)
        self.assertFalse(result['new_MAX_points_used_as_original_indices'])

    def test_annulus_preserves_two_loops_without_disk_assumption(self):
        row = FIXTURES['annulus_refinement']; result = self.compare(row)
        self.assertEqual(result['before'], row['expected_before'])
        self.assertEqual(result['after'], row['expected_after'])
        self.assertEqual(result['before']['boundary_loops'], 2)
        self.assertEqual(result['after']['euler_characteristic'], 0)

    def test_retained_coordinate_and_MAX_boundary_refuse(self):
        row = copy.deepcopy(FIXTURES['square_refinement_with_fixed_exterior'])
        row['points_after'][0][0] = .25
        with self.assertRaisesRegex(ValueError, 'coordinate bytes'):
            self.compare(row)
        row = copy.deepcopy(FIXTURES['square_refinement_with_fixed_exterior'])
        row['coordinate_origins'][0] = module.MAX
        with self.assertRaisesRegex(ValueError, 'MAX point'):
            self.compare(row)

    def test_exterior_winding_or_source_multiplicity_refuse(self):
        row = copy.deepcopy(FIXTURES['square_refinement_with_fixed_exterior'])
        row['faces_after'][-1] = [1, 2, 4]
        with self.assertRaisesRegex(ValueError, 'oriented exterior'):
            self.compare(row)
        row = copy.deepcopy(FIXTURES['annulus_refinement'])
        row['face_sources'][-1] = row['face_sources'][-2]
        with self.assertRaisesRegex(ValueError, 'unique and in range'):
            self.compare(row)


if __name__ == '__main__':
    unittest.main()
