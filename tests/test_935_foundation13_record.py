import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / 'docs/research/935-horizontal-cooling/foundation13-rotor-pilot-20261022.json'


class Foundation13RecordTests(unittest.TestCase):
    def test_record_retains_source_hashes_and_synthetic_scope(self):
        record = json.loads(RECORD.read_text())
        for name, expected in record['source_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), expected)
        self.assertEqual(record['synthetic_Couette_control']['status'], 'MRF_Couette_control_passed')
        self.assertFalse(record['synthetic_Couette_control']['rotor_935_CFD_accepted'])
        self.assertTrue(all(value is False for value in record['scope'].values()))
        self.assertEqual(record['SI_surface_audit']['complete_SI_surface']['self_intersection_pairs'], 0)
        self.assertEqual(record['SI_surface_audit']['crossing_cube_control_detected_pairs'], 15)

    def test_failed_rotor_criteria_are_not_upgraded_by_conservation_or_backup(self):
        record = json.loads(RECORD.read_text())
        probe = record['rotor_probe']
        self.assertEqual(probe['native_execution']['exit'], 0)
        self.assertTrue(probe['native_execution']['input_files_unchanged'])
        self.assertLess(probe['maximum_final_window_mass_imbalance_relative'], .001)
        self.assertFalse(probe['single_mesh_pilot_pass'])
        self.assertFalse(probe['extended_geometry_mesh_check_pass'])
        for key in ('total_pressure_rise_Pa', 'resisting_torque_z_Nm'):
            self.assertGreater(probe['metrics'][key]['peak_to_peak_relative'], .01)
            self.assertFalse(probe['metrics'][key]['stationarity_pass'])
        self.assertFalse(probe['compressibility_assessed'])
        self.assertEqual(record['private_delivery']['payload_files'], 593)
        self.assertTrue(record['private_delivery']['GitHub_all_asset_digests_verified'])
        self.assertFalse(record['private_delivery']['manufacturing_authorized'])


if __name__ == '__main__':
    unittest.main()
