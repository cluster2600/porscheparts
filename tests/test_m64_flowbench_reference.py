import importlib.util
import json
import math
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'twins/m64-cylinder-head/targets'
SPEC = importlib.util.spec_from_file_location('flowbench_reference', FOLDER / 'flowbench_reference.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FlowbenchReferenceTests(unittest.TestCase):
    def test_no_pressure_drop(self):
        self.assertEqual(MODULE.ideal_mass_flux(100000, 300, 100000), (0.0, 0.0, False))

    def test_low_pressure_drop_matches_bernoulli_limit(self):
        flux, _, _ = MODULE.ideal_mass_flux(100000, 300, 99999.99)
        self.assertAlmostEqual(flux / math.sqrt(2 * 100000 / (287.05 * 300) * .01), 1.0, places=6)

    def test_choked_limit_independent_formula_and_plateau(self):
        flux, mach, choked = MODULE.ideal_mass_flux(100000, 300, 20000)
        expected = 100000 * math.sqrt(1.4 / (287.05 * 300)) * (2 / 2.4) ** 3
        self.assertAlmostEqual(flux, expected, places=10)
        self.assertAlmostEqual(mach, 1, places=12)
        self.assertTrue(choked)
        self.assertEqual(MODULE.ideal_mass_flux(100000, 300, 10000), (flux, mach, choked))

    def test_bad_inputs_rejected(self):
        for args in [(0, 300, 100), (100000, 0, 90000), (100000, 300, -1),
                     (100000, 300, 100001), (float('nan'), 300, 90000),
                     (100000, 300, 90000, 287.05, 1)]:
            with self.assertRaises(ValueError):
                MODULE.ideal_mass_flux(*args)

    def test_declared_pilot_is_not_a_head_result(self):
        policy = json.loads((FOLDER / 'intake-flowbench-pilot.json').read_text())
        report = MODULE.reference_report(policy)
        self.assertAlmostEqual(report['pressure_drop_Pa'], 6974.48948)
        self.assertAlmostEqual(report['outlet_static_pressure_Pa'], 94350.51052)
        self.assertGreater(report['ideal_reference_Mach'], .3)
        self.assertFalse(report['ideal_reference_choked'])
        self.assertIsNone(report['head_mass_flow_kg_s'])
        self.assertIsNone(report['head_discharge_coefficient'])
        self.assertFalse(report['CFD_executed'])
        self.assertFalse(report['manufacturing_authorized'])
        self.assertEqual(policy['preregistered_exploratory_checks']['minimum_spatial_levels_before_comparison'], 3)


if __name__ == '__main__':
    unittest.main()
