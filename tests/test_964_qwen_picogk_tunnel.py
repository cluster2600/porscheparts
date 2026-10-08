from pathlib import Path
import hashlib
import json
import math
import runpy
import unittest

MODULE = runpy.run_path(str(Path(__file__).resolve().parents[1] /
                           'twins/964-chassis/source/qwen-picogk-tunnel/prepare.py'))


class QwenTunnelTests(unittest.TestCase):
    def test_kali_execution_keeps_runtime_failure_and_physical_limits(self):
        root = Path(__file__).resolve().parents[1]
        report = json.loads((root/'twins/964-chassis/derived/kali-compute-20261002.json').read_text())
        self.assertFalse(report['boolean_regression']['stock']['stock_passed'])
        self.assertTrue(report['boolean_regression']['candidate']['stock_passed'])
        self.assertTrue(report['calculix_comparison']['passed'])
        self.assertFalse(report['truss']['new_tunnel_openings_represented'])
        self.assertFalse(report['manufacturing_authorized'])
        self.assertFalse(report['road_or_track_release'])
        self.assertFalse(report['runtime']['shared_runtime_modified'])
        self.assertFalse(report['verification']['global_check_passed'])
        for run in report['native_runs']:
            self.assertTrue(run['nose_passage_probe'] and run['service_opening_probe'] and run['side_wall_probes'])
            self.assertFalse(run['structural_simulation_performed'])
            self.assertEqual(run['residual_same_grid_collision_mm3'], 0)
        for path, sha in report['artifacts'].items():
            if path.startswith('twins/'):
                self.assertEqual(hashlib.sha256((root/path).read_bytes()).hexdigest(), sha)

    def test_published_run_binds_source_and_keeps_release_closed(self):
        root = Path(__file__).resolve().parents[1]
        report = json.loads((root/'twins/964-chassis/derived/qwen-picogk-tunnel-20261002.json').read_text())
        self.assertFalse(report['manufacturing_authorized'])
        self.assertFalse(report['raw_scan_used'])
        self.assertFalse(report['paid_compute_used'])
        self.assertEqual(len(report['inference']['records']), 3)
        self.assertTrue(all(row['semantic_passed'] for row in report['inference']['records']))
        for path, sha in report['artifacts'].items():
            self.assertEqual(len(sha), 64)
            if path.startswith('twins/'):
                self.assertEqual(hashlib.sha256((root/path).read_bytes()).hexdigest(), sha)
        self.assertEqual([run['voxel_size_mm'] for run in report['native_runs']], [4, 2])
        for run in report['native_runs']:
            self.assertFalse(run['manufacturing_authorized'])
            self.assertFalse(run['vehicle_fit_verified'])
            self.assertFalse(run['structural_simulation_performed'])
            self.assertFalse(run['dynamic_clearance_verified'])
            self.assertEqual(run['residual_same_grid_collision_mm3'], 0)
            self.assertEqual(sum(c['baseline_collision_mm3'] > 0 for c in run['collisions']), 3)

    def test_transcription_must_preserve_radii_coordinates_caps_and_edge_count(self):
        expected = [710, 0, 335, 21, 2010, 0, 335, 21, False]
        scaled = [14.2, 0, 6.7, .42, 40.2, 0, 6.7, .42, False]
        check = MODULE['checked_response']
        # Test this module's semantic gate, not a reimplementation of the pinned parser.
        signature = lambda beams: beams
        self.assertEqual(check('parsed by pinned helper', expected, lambda _: ('', [scaled]), signature), expected)
        invalid = [[], [scaled, scaled], [scaled[:3]+[.84]+scaled[4:]],
                   [scaled[:8]+[True]], [[14.3]+scaled[1:]]]
        for beams in invalid:
            with self.subTest(beams=beams), self.assertRaises(ValueError):
                check('rejected', expected, lambda _: ('', beams), signature)

    def test_existing_concept_omits_longitudinal_and_cover_intersections(self):
        design = {'screening_geometry_mm': {'floor_z': 180}, 'vehicle_packaging_mm': {
            'common_cell': {'tunnel_start_x': 430, 'tunnel_end_x': 1980, 'tunnel_outer_width': 330,
                            'tunnel_outer_height': 275, 'service_cover_thickness': 18},
            'c2_package': {'external_shift_rod_start_x': 710, 'external_shift_rod_end_x': 2010,
                           'external_shift_rod_center_y': 0, 'external_shift_rod_center_z': 335,
                           'external_shift_rod_diameter': 42, 'shifter_tower_center_xyz': [980, 0, 430],
                           'shifter_tower_envelope_xyz': [220, 250, 180]},
            'c4_package': {'central_tube_start_x': -170, 'central_tube_end_x': 1980,
                           'central_tube_center_z': 310, 'central_tube_outer_diameter': 150,
                           'shift_guide_center_y': 92, 'shift_guide_diameter': 32}}}
        result = MODULE['specification'](design)
        self.assertEqual(result['scale'], 50)
        self.assertEqual(len(result['boxes_mm']), 5)
        self.assertEqual(result['expected_beams_mm']['c4_shift_guide'], [-40, 92, 392, 16, 1850, 92, 392, 16, False])
        collision = result['analytic_collision_mm3']
        self.assertEqual(collision['c2_shift_rod'], 0)
        self.assertAlmostEqual(collision['c4_central_tube'], 38*math.pi*75**2)
        self.assertAlmostEqual(collision['c4_shift_guide'], 38*math.pi*16**2)
        self.assertEqual(collision['c2_shifter_tower'], 990000)


if __name__ == '__main__':
    unittest.main()
