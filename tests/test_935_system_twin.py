import copy
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / 'twins/935-horizontal-cooling-system-f0'
sys.path.insert(0, str(STUDY / 'source'))
from build_system_twin import (build, calculate, logical_usda, MissingData,
                               operating_point, thermal_step)
from compare_holdout import compare


class CoolingSystemTwinTests(unittest.TestCase):
    def setUp(self):
        self.case = json.loads((STUDY / 'synthetic-case.json').read_text())

    def test_real_template_does_not_manufacture_values(self):
        result = calculate(json.loads((STUDY / 'operating-case.template.json').read_text()))
        self.assertTrue(all(m['values'] is None for m in result['models'].values()))
        self.assertFalse(result['digital_twin_validated'])

    def test_speed_ratio_convention_and_slip(self):
        self.case['parameters']['belt_slip_fraction']['value'] = 0.1
        result = calculate(self.case)
        self.assertEqual(result['models']['speeds']['values'], {'input_rpm': 1800, 'rotor_rpm': 900})
        self.assertIsNone(result['models']['airflow']['values'])

    def test_analytic_operating_point_and_parallel_conservation(self):
        result = calculate(self.case)['models']['airflow']['values']
        q = math.sqrt(5) - 1
        self.assertAlmostEqual(result['volume_flow_m3_s'], q, places=12)
        self.assertAlmostEqual(result['total_pressure_rise_pa'], 50 * q * q, places=10)
        self.assertAlmostEqual(sum(result['branch_volume_flow_m3_s']), q, places=12)
        self.assertAlmostEqual(result['parallel_pressure_loss_pa'] + result['series_pressure_loss_pa'], result['total_pressure_rise_pa'], places=10)

    def test_branch_resistance_changes_flow_split(self):
        r = operating_point([[0, 200, 0.5], [2, 0, 0.5]], 5, [180, 720])
        self.assertAlmostEqual(r['branch_volume_flow_m3_s'][0] / r['branch_volume_flow_m3_s'][1], 2)

    def test_power_and_torque_energy_budget(self):
        result = calculate(self.case)['models']
        fan = result['airflow']['values']['fan_shaft_power_w']
        drive = result['steady_drive_budget']['values']
        self.assertAlmostEqual(drive['steady_drive_input_power_w'] * 0.8, fan)
        self.assertAlmostEqual(drive['steady_drive_loss_w'] + fan, drive['steady_drive_input_power_w'])
        self.assertAlmostEqual(drive['steady_fan_torque_nm'] * 2 * math.pi * 1000 / 60, fan)
        self.assertAlmostEqual(drive['belt_tension_difference_n'] * 0.05, drive['steady_drive_input_torque_nm'])

    def test_inertia_is_reflected_with_square_speed_ratio(self):
        result = calculate(self.case)['models']['inertia_and_unbalance']['values']
        self.assertAlmostEqual(result['rotor_inertia_reflected_to_input_kg_m2'], 0.0025)
        self.assertAlmostEqual(result['rotor_acceleration_torque_nm'], 0.1)

    def test_thermal_zero_load_decays_without_overshoot(self):
        r = thermal_step(1, 1, 1000, 10, 1000, 0, 20, 100, 1)
        self.assertEqual(r['steady_solid_temperature_deg_c'], 20)
        self.assertTrue(20 < r['solid_temperature_after_step_deg_c'] < 100)
        self.assertTrue(20 < r['air_outlet_temperature_after_step_deg_c'] < r['solid_temperature_after_step_deg_c'])

    def test_thermal_high_ua_limit_matches_air_capacity(self):
        r = thermal_step(1, 1, 1000, 1e8, 1000, 1000, 20, 21, 10)
        self.assertAlmostEqual(r['steady_solid_temperature_deg_c'], 21)
        self.assertAlmostEqual(r['solid_temperature_after_step_deg_c'], 21)
        self.assertAlmostEqual(r['transient_heat_to_air_w'], 1000)

    def test_no_extrapolation_or_nonmonotone_map(self):
        with self.assertRaises(MissingData):
            operating_point([[1, 1, 0.5], [2, 0, 0.5]], 100, [100])
        with self.assertRaises(ValueError):
            operating_point([[0, 0, 0.5], [1, 100, 0.5]], 1, [1])
        with self.assertRaises(ValueError):
            operating_point([[0, 100, 0.5], [1, 0, 0.5]], 1, [0])

    def test_pressure_basis_density_and_topology_are_gated(self):
        self.case['pressure_basis'] = 'static_to_static'
        with self.assertRaises(ValueError): calculate(self.case)
        self.case['pressure_basis'] = 'total_to_total'
        self.case['parameters']['map_air_density']['value'] = 1.1
        self.assertIsNone(calculate(self.case)['models']['airflow']['values'])
        self.case['parameters']['map_air_density']['value'] = 1
        self.case['air_topology_confirmed'] = False
        self.assertIsNone(calculate(self.case)['models']['airflow']['values'])

    def test_bad_units_uncertainty_and_numbers_rejected(self):
        for key, value in [('unit', 'rad/s'), ('value', float('nan')), ('value', True), ('uncertainty', -1)]:
            case = copy.deepcopy(self.case)
            case['parameters']['engine_rpm'][key] = value
            with self.assertRaises(ValueError): calculate(case)

    def test_synthetic_evidence_cannot_become_specimen_data(self):
        self.case['purpose'] = 'specimen_model'
        self.case['specimen_id'] = 'not_independently_verified'
        with self.assertRaises(ValueError): calculate(self.case)

    def test_partial_model_can_calculate_speed_without_airflow(self):
        self.case['parameters']['fan_map']['value'] = None
        result = calculate(self.case)
        self.assertIsNotNone(result['models']['speeds']['values'])
        self.assertIsNone(result['models']['airflow']['values'])
        self.assertIsNone(result['models']['thermal']['values'])

    def test_logical_stage_has_no_geometry_poses_or_physics(self):
        definition = json.loads((STUDY / 'system-definition.json').read_text())
        contract = json.loads((STUDY / 'interface-contract.json').read_text())
        text = logical_usda(definition, contract)
        self.assertEqual(text.count('rel twin:sides'), 17)
        for forbidden in ('def Mesh', 'def Xform', 'PhysicsRigidBodyAPI', 'physics:mass', 'xformOp:'):
            self.assertNotIn(forbidden, text)
        self.assertIn('twin:scanScaleVerified = false', text)

    def test_outputs_are_private_and_nonoverwriting(self):
        with tempfile.TemporaryDirectory() as t:
            out = Path(t) / 'new'
            result = build(STUDY / 'operating-case.template.json', out)
            self.assertEqual(result['interfaces'], 17)
            self.assertFalse(result['source_scan_geometry_loaded'])
            self.assertTrue((out / 'system-logical.usda').exists())
            with self.assertRaises(ValueError): build(STUDY / 'synthetic-case.json', out)
        with self.assertRaises(ValueError): build(STUDY / 'synthetic-case.json', STUDY / 'unsafe-new-output')

    def holdout(self):
        result = calculate(self.case)
        result['case_sha256'] = 'a' * 64
        row = {'sample_id': 'synthetic', 'dataset_role': 'holdout', 'quantity_path': 'speeds.rotor_rpm',
               'unit': 'rpm', 'observed': '1000', 'observed_standard_uncertainty': '0', 'prediction_standard_uncertainty': '0',
               'acceptance_absolute_error': '0', 'model_case_sha256': 'a' * 64,
               'measurement_sha256': 'b' * 64, 'predeclared_tolerance_sha256': 'c' * 64}
        return result, row

    def test_holdout_does_not_promote_a_physical_twin(self):
        data, row = self.holdout()
        result = compare(data, [row])
        self.assertTrue(result['all_declared_tolerances_met'])
        self.assertFalse(result['digital_twin_validated'])
        row['observed'] = '1100'
        self.assertFalse(compare(data, [row])['all_declared_tolerances_met'])

    def test_empty_calibration_reused_or_mismatched_holdout_rejected(self):
        data, row = self.holdout()
        self.assertFalse(compare(data, [])['all_declared_tolerances_met'])
        for key, value in [('dataset_role', 'calibration'), ('model_case_sha256', 'd' * 64), ('observed', 'NaN'), ('unit', 'rad/s')]:
            bad = dict(row, **{key: value})
            with self.assertRaises(ValueError): compare(data, [bad])
        data['input_evidence_sha256'] = ['b' * 64]
        with self.assertRaises(ValueError): compare(data, [row])


if __name__ == '__main__':
    unittest.main()
