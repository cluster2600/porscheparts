from pathlib import Path
import sys
import unittest

import numpy as np

SOURCE = Path(__file__).resolve().parents[1] / 'twins/935-horizontal-cooling-system-f0/source'
sys.path.insert(0, str(SOURCE))
import complete_candidate_rotor as rotor


class CandidateRotorTests(unittest.TestCase):
    def case(self):
        return {'purpose': 'hypothesis_screen', 'scale_verified': False,
                'scale_mm_per_source_unit': 1, 'wall_source_units': 2,
                'back_source_units': 2, 'boss_radius_source_units': 5,
                'profile_stride': 4, 'stations_source_units': [9, 10, 12, 14, 15],
                'reference_blade_id': '0', 'tip_radius_source_units': 20,
                'hub_z_source_units': [-2, 2],
                'assumptions': [{'rejection_test': 'Independent inspection'}]}

    def data(self):
        theta = np.linspace(0, 2 * np.pi, 128, endpoint=False)
        profiles = [np.column_stack((np.full(128, x), np.cos(theta), np.sin(theta)))
                    for x in [10, 12, 14]]
        return {'schema': '935-observed-section-loft-v1', 'regions': [
            {'blade_id': str(i), 'phase_radians': i * 2 * np.pi / 3,
             'stations_source_units': [10, 12, 14],
             'profiles': [rotor.world_profile(p, i * 2 * np.pi / 3).tolist() for p in profiles]}
            for i in range(3)]}

    def test_transform_roundtrip(self):
        p = np.arange(24).reshape(8, 3)
        np.testing.assert_allclose(rotor.local_profile(rotor.world_profile(p, .72), .72), p, atol=1e-13)

    def test_acquired_profiles_unchanged_except_explicit_resampling(self):
        data = self.data()
        completed = rotor.completed_sections(data, self.case())
        np.testing.assert_allclose(completed[0]['profiles'][1],np.asarray(data['regions'][0]['profiles'][0])[::4])
        self.assertEqual(completed[0]['provenance'][0]['classification'],'constant_profile_root_or_tip_design')
        self.assertEqual(completed[0]['provenance'][1]['classification'],'registered_acquired_reference_section')

    def test_missing_sector_profile_is_identified(self):
        data = self.data()
        data['regions'].append({**data['regions'][0], 'blade_id': 'missing',
                                'stations_source_units': [12, 14],
                                'profiles': data['regions'][0]['profiles'][1:]})
        completed = rotor.completed_sections(data, self.case())
        self.assertEqual(completed[-1]['provenance'][1]['classification'], 'periodic_reference_reconstruction')

    def test_refuses_promotion_and_invalid_parameters(self):
        for change in ({'purpose': 'specimen_model'}, {'scale_verified': True},
                       {'profile_stride': 3}, {'wall_source_units': float('nan')},
                       {'stations_source_units': [1, 1, 2]}, {'assumptions': []}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                rotor.validate({**self.case(), **change})


if __name__ == '__main__':
    unittest.main()
