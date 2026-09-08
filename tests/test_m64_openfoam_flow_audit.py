import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('flow_audit', ROOT / 'twins/m64-cylinder-head/source/flowbench-intake/audit_openfoam_flow.py')
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)
CRITERIA = json.loads((ROOT / 'twins/m64-cylinder-head/targets/intake-flowbench-pilot.json').read_text())['preregistered_exploratory_checks']


def histories(n=200):
    return {p: [[i, 0.1, value if i else 0.] for i in range(n+1)]
            for p, value in (('inlet', -0.1), ('receiver_outlet', 0.1), ('walls', 0.))}


class FlowAuditTests(unittest.TestCase):
    def test_native_table_and_nonfinite_or_restarted_history(self):
        cols = ['Time', 'Area', 'orientedSum(phi)']
        text = '# Time\tArea\torientedSum(phi)\n0 0.1 0\n1 0.1 -0.1\n'
        self.assertEqual(MOD.table(text, cols)[-1][-1], -0.1)
        for changed in (text + '1 0.1 -0.2\n', text.replace('-0.1', 'nan'),
                        text.replace('Area', 'Other'), text.replace('1 0.1 -0.1', '1 0.1')):
            with self.assertRaises(ValueError):
                MOD.table(changed, cols)

    def test_twenty_iterations_do_not_satisfy_preregistered_window(self):
        report = MOD.mass_checks(histories(20), 100, CRITERIA)
        self.assertEqual(report['completed_iterations_in_tables'], 20)
        self.assertFalse(report['sufficient_history'])
        self.assertFalse(report['mass_checks_passed'])

    def test_exact_mass_checks_are_not_convergence_or_validation(self):
        report = MOD.mass_checks(histories(), 100, CRITERIA)
        self.assertTrue(report['mass_checks_passed'])
        self.assertFalse(report['convergence_demonstrated'])

    def test_walls_leakage_is_not_omitted(self):
        series = histories()
        series['walls'][-1][2] = .001
        self.assertFalse(MOD.mass_checks(series, 100, CRITERIA)['mass_checks_passed'])

    def test_balanced_but_drifting_flow_fails(self):
        series = histories()
        for p in ('inlet', 'receiver_outlet'):
            for row in series[p][-100:]:
                row[2] *= 1.1
        self.assertFalse(MOD.mass_checks(series, 100, CRITERIA)['mass_checks_passed'])

    def test_balanced_leak_through_impermeable_walls_still_fails(self):
        series = histories()
        for i in range(1, 201):
            series['walls'][i][2] = .001
            series['receiver_outlet'][i][2] = .099
        report = MOD.mass_checks(series, 100, CRITERIA)
        self.assertLess(report['maximum_relative_mass_imbalance_last_window'], 1e-12)
        self.assertFalse(report['prescribed_stationary_no_slip_wall_flux_zero'])
        self.assertFalse(report['mass_checks_passed'])

    def test_missing_times_or_different_patch_times_rejected(self):
        series = histories()
        series['inlet'].pop(1)
        with self.assertRaises(ValueError):
            MOD.mass_checks(series, 100, CRITERIA)
        series = histories()
        for rows in series.values():
            rows.pop(1)
        with self.assertRaises(ValueError):
            MOD.mass_checks(series, 100, CRITERIA)

    def test_equal_oscillating_means_do_not_prove_stationarity(self):
        series = histories()
        for i in range(1, 201):
            series['receiver_outlet'][i][2] = .1 + (-1)**i * .02
            series['inlet'][i][2] = -series['receiver_outlet'][i][2]
        report = MOD.mass_checks(series, 100, CRITERIA)
        self.assertTrue(report['mass_checks_passed'])
        self.assertGreater(report['relative_outlet_peak_to_peak_last_window'], .39)
        self.assertTrue(report['stationarity_not_proven_by_equal_window_means'])
        self.assertFalse(report['convergence_demonstrated'])

    def test_reversed_or_zero_flow_not_accepted(self):
        for value in (0., -.1):
            series = histories()
            for row in series['receiver_outlet'][1:]:
                row[2] = value
            self.assertFalse(MOD.mass_checks(series, 100, CRITERIA)['mass_checks_passed'])

    def test_moving_area_not_accepted_as_stationary(self):
        series = copy.deepcopy(histories())
        series['walls'][-1][1] *= 2
        with self.assertRaises(ValueError):
            MOD.mass_checks(series, 100, CRITERIA)


if __name__ == '__main__':
    unittest.main()
