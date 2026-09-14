import importlib.util
import hashlib
import json
import math
from pathlib import Path
import sys
import unittest


SOURCE = Path(__file__).resolve().parents[1] / 'twins/m64-cylinder-head/source'
sys.path.insert(0, str(SOURCE))
spec = importlib.util.spec_from_file_location('m64_continuous_clearance', SOURCE / 'audit_continuous_valve_clearance.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
sys.path.remove(str(SOURCE))


class ContinuousClearanceTests(unittest.TestCase):
    def test_grid_covers_complete_lift(self):
        grid = module.lift_grid(11.5, 1.)
        self.assertEqual((grid[0], grid[-1], len(grid)), (0., 11.5, 13))
        self.assertLessEqual(module.covering_radius(grid), .5)

    def test_bound_uses_both_independent_translations(self):
        bound = module.clearance_bound(2.2, [0., 1., 2.], [0., .8, 1.6], .01)
        self.assertAlmostEqual(bound, 1.29)

    def test_sparse_grid_can_remain_inconclusive(self):
        self.assertLess(module.clearance_bound(.8, [0., 1.], [0., 1.], 1e-5), 0)

    def test_mid_cell_contact_cannot_be_certified_from_positive_samples(self):
        # A(s)=(s,0), B(t)=(0.5,t-0.5), s,t in [0,1]: all four
        # grid corners are separated, but the two points meet at (0.5,0.5).
        grid = [0., 1.]
        sampled = min(math.hypot(s-.5, t-.5) for s in grid for t in grid)
        self.assertGreater(sampled, 0)
        self.assertLess(module.clearance_bound(sampled, grid, grid, 1e-5), 0)

    def test_refinement_does_not_remove_numerical_reserve(self):
        self.assertAlmostEqual(module.clearance_bound(2., [0., .1], [0., .1], .01), 1.89)

    def test_invalid_parameters_fail(self):
        for lift, step in [(0, 1), (1, 0), (math.nan, 1), (1, .001)]:
            with self.assertRaises(ValueError):
                module.lift_grid(lift, step)
        for grid in ([0], [0, 0], [1, 0], [0, math.inf]):
            with self.assertRaises(ValueError):
                module.covering_radius(grid)
        with self.assertRaises(ValueError):
            module.clearance_bound(1, [0, 1], [0, 1], -.1)

    def test_bound_covers_analytic_independent_point_motion(self):
        # Known analytic distance between points moving on orthogonal axes.
        a = module.lift_grid(2., .4)
        b = module.lift_grid(3., .4)
        sampled = min(math.hypot(4-x, 5-y) for x in a for y in b)
        lower = module.clearance_bound(sampled, a, b, 1e-5)
        for i in range(101):
            for j in range(101):
                self.assertLessEqual(lower, math.hypot(4-2*i/100, 5-3*j/100))

    def test_native_receipt_binds_current_step_and_all_six_pairs(self):
        directory = SOURCE.parent / 'evidence/four-valve-design-v2-20260907'
        report = json.loads((directory / 'continuous-valve-pair-report.json').read_text())
        self.assertEqual(report['STEP_sha256'], hashlib.sha256((directory / 'closed.step').read_bytes()).hexdigest())
        self.assertEqual(report['audit_source_sha256'], hashlib.sha256((SOURCE / 'audit_continuous_valve_clearance.py').read_bytes()).hexdigest())
        self.assertEqual(len(report['pairs']), 6)
        self.assertEqual(sum(len(p['samples']) for p in report['pairs']), 862)
        self.assertAlmostEqual(report['minimum_continuous_lower_bound_mm'], 1.216555553556495)
        self.assertTrue(report['all_pairs_positive_under_numerical_assumption'])
        self.assertTrue(report['numerical_allowance_is_assumed_not_interval_verified'])
        self.assertFalse(report['manufacturing_authorized'])
        self.assertFalse(report['piston_or_fixed_component_clearance_checked'])
        self.assertFalse(report['thermal_or_elastic_deformation_checked'])


if __name__ == '__main__':
    unittest.main()
