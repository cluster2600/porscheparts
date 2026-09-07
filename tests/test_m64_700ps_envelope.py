import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'twins/m64-cylinder-head/targets'
SCRIPT = DIRECTORY / '700ps_envelope.py'
TARGET = DIRECTORY / '700ps-biturbo.json'
spec = importlib.util.spec_from_file_location('m64_700ps', SCRIPT)
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)


class M64SevenHundredPSTests(unittest.TestCase):
    def setUp(self):
        self.target = json.loads(TARGET.read_text())
        self.base = self.target['balance_model']['base_case']

    def test_ps_is_not_mechanical_hp(self):
        result = model.balance(**self.base)
        self.assertEqual(result['power_kw_target'], 514.849125)
        self.assertAlmostEqual(result['power_mechanical_hp_target'], 690.4240494336717)

    def test_four_stroke_work_identity_independent_torque_formula(self):
        result = model.balance(**self.base)
        torque = result['torque_nm_required_at_this_rpm']
        bmep_pa = result['bmep_bar_required'] * 1e5
        self.assertAlmostEqual(bmep_pa * .0036, torque * 4 * math.pi, places=10)
        self.assertAlmostEqual(torque, 756.3764602180348)
        self.assertAlmostEqual(result['bmep_bar_required'], 26.40251923076923)

    def test_ideal_gas_and_four_stroke_mass_closure(self):
        result = model.balance(**self.base)
        rho = result['manifold_absolute_bar_required'] * 1e5 / (287.05 * 333.15)
        fresh_mass_per_cycle = rho * .0036 * .95
        self.assertAlmostEqual(fresh_mass_per_cycle * 6500 / 120, result['air_kg_per_s'])

    def test_garrett_400_mechanical_hp_example_in_si(self):
        case = dict(self.base,
                    power_ps=400 * model.MECHANICAL_HP_W / model.PS_W,
                    bsfc_kg_per_kwh=.55 * model.KG_PER_LB / (model.MECHANICAL_HP_W / 1000),
                    lambda_ratio=12 / 14.7)
        self.assertAlmostEqual(model.balance(**case)['air_lb_per_min'], 44.0)

    def test_air_fuel_and_energy_balance_do_not_assign_head_heat(self):
        result = model.balance(**self.base)
        self.assertAlmostEqual(result['fuel_kg_per_h'], 175.0487025)
        self.assertAlmostEqual(result['air_kg_per_s'], 175.0487025 * .82 * 14.7 / 3600)
        self.assertAlmostEqual(result['fuel_lower_heating_power_kw'],
                               result['power_kw_target'] + result['fuel_power_minus_brake_kw_NOT_head_heat'])
        self.assertNotIn('head_heat_kw', result)
        self.assertNotIn('cylinder_peak_pressure_pa', result)

    def test_parallel_turbos_split_mass_not_pressure_ratio(self):
        one = model.balance(**dict(self.base, turbochargers=1))
        two = model.balance(**self.base)
        self.assertAlmostEqual(one['air_per_turbo_kg_per_s'], 2 * two['air_per_turbo_kg_per_s'])
        self.assertEqual(one['compressor_pressure_ratio_required'], two['compressor_pressure_ratio_required'])

    def test_altitude_increases_pr_not_required_manifold_density(self):
        sea = model.balance(**self.base)
        altitude = model.balance(**dict(self.base, ambient_pressure_pa=85000))
        self.assertEqual(sea['manifold_absolute_bar_required'], altitude['manifold_absolute_bar_required'])
        self.assertGreater(altitude['compressor_pressure_ratio_required'], sea['compressor_pressure_ratio_required'])
        self.assertGreater(altitude['corrected_air_per_turbo_lb_per_min_reporting_reference'],
                           sea['corrected_air_per_turbo_lb_per_min_reporting_reference'])

    def test_pressure_losses_use_absolute_pressures(self):
        result = model.balance(**self.base)
        self.assertAlmostEqual(result['compressor_pressure_ratio_required'],
                               (result['manifold_absolute_bar_required'] + .15) / .98325)
        self.assertAlmostEqual(result['manifold_gauge_bar_relative_to_local_ambient'],
                               result['manifold_absolute_bar_required'] - 1.01325)

    def test_increasing_rpm_reduces_torque_bmep_and_map_at_fixed_target(self):
        low = model.balance(**dict(self.base, rpm=6000))
        high = model.balance(**dict(self.base, rpm=7500))
        self.assertEqual(low['air_kg_per_s'], high['air_kg_per_s'])
        for key in ('torque_nm_required_at_this_rpm', 'bmep_bar_required', 'manifold_absolute_bar_required'):
            self.assertAlmostEqual(low[key] / high[key], 1.25)

    def test_invalid_and_nonfinite_inputs_rejected(self):
        for key in self.base:
            for bad in (float('nan'), float('inf'), -1, True):
                with self.subTest(key=key, value=bad), self.assertRaises(ValueError):
                    model.balance(**dict(self.base, **{key: bad}))
        for changes in ({'compressor_isentropic_efficiency': 1.1},
                        {'inlet_pressure_loss_pa': 101325}, {'turbochargers': 1.5},
                        {'bsfc_kg_per_kwh': .001}, {'power_ps': 0}):
            with self.assertRaises(ValueError):
                model.balance(**dict(self.base, **changes))

    def test_target_conflicts_fail_closed(self):
        target = copy.deepcopy(self.target)
        for field, bad in (('unit', 'hp'), ('location', 'wheels'), ('value', 1000)):
            modified = copy.deepcopy(target)
            modified['user_target']['power'][field] = bad
            with self.assertRaises(ValueError):
                model.report(modified)

    def test_all_endpoint_combinations_and_provenance(self):
        report = model.report(self.target)
        self.assertEqual(report['corner_count'], 128)
        self.assertEqual(len(report['one_factor_at_a_time']), 20)
        self.assertFalse(report['performance_validated'])
        self.assertFalse(report['manufacturing_authorized'])
        self.assertFalse(report['maximum_cylinder_pressure_predicted'])
        self.assertFalse(report['head_heat_flux_predicted'])
        self.assertFalse(any(self.target['qualification'].values()))
        for case in report['corners']:
            self.assertEqual(model.balance(**dict(self.base, **case['inputs'])), case['result'])

    def test_stored_report_matches_current_inputs_and_code(self):
        saved = json.loads((DIRECTORY / '700ps-balance-20260907.json').read_text())
        self.assertEqual(saved.pop('target_sha256'), hashlib.sha256(TARGET.read_bytes()).hexdigest())
        self.assertEqual(saved.pop('script_sha256'), hashlib.sha256(SCRIPT.read_bytes()).hexdigest())
        self.assertEqual(saved, model.report(self.target))

    def test_cli_refuses_to_overwrite_an_existing_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'receipt.json'
            command = [sys.executable, str(SCRIPT), '--output', str(output)]
            subprocess.run(command, check=True, capture_output=True)
            before = output.read_bytes()
            retry = subprocess.run(command, capture_output=True)
            self.assertNotEqual(retry.returncode, 0)
            self.assertEqual(output.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
