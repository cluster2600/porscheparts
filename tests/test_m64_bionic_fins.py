import importlib.util
import math
from pathlib import Path
import sys
import unittest

SOURCE = Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/bionic-fins/study.py'
SPEC = importlib.util.spec_from_file_location('bionic_fin_study', SOURCE)
study = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(study)
sys.path.insert(0, str(SOURCE.parent))
try:
    import countercheck
except ImportError:
    countercheck = None


class FinStudyTests(unittest.TestCase):
    def test_constant_fin_matches_independent_convective_tip_formula(self):
        d = next(study.designs())
        for k, h in ((12, 40), (80, 100), (160, 200)):
            area, perimeter, length = .06*.003, 2*(.06+.003), .028
            m = math.sqrt(h*perimeter/(k*area))
            c = k*area*m
            terminal = h*area
            exact = c*(math.sinh(m*length)+terminal/c*math.cosh(m*length))/(math.cosh(m*length)+terminal/c*math.sinh(m*length))
            self.assertAlmostEqual(study.conductance(d, k, h), exact, places=12)
        self.assertEqual(study.conductance(d, 80, 0), 0)

    def test_parallel_roots_sum_and_taper_refines(self):
        d = next(study.designs())
        parallel = dict(d, edges=[study.edge((0, 0), (-2, 28), 3, 3), study.edge((0, 0), (2, 28), 3, 3)])
        one = dict(d, edges=parallel['edges'][:1])
        self.assertAlmostEqual(study.conductance(parallel, 80, 100), 2*study.conductance(one, 80, 100), places=12)
        tapered = list(study.designs())[1]
        ref = study.conductance(tapered, 12, 200, 1024)
        errors = [abs(study.conductance(tapered, 12, 200, n)-ref) for n in (16, 32, 64)]
        self.assertGreater(errors[0], errors[1])
        self.assertGreater(errors[1], errors[2])

    def test_volume_equality_and_fail_closed_dimensions(self):
        base = next(study.designs())
        for d in study.designs():
            self.assertAlmostEqual(study.nominal_volume(d), study.nominal_volume(base), places=8)
        for k, h, n in ((0, 100, 64), (80, -1, 64), (math.nan, 100, 64), (80, math.inf, 64), (80, 100, True)):
            with self.assertRaises(ValueError):
                study.conductance(base, k, h, n)
        for bad in (dict(base, depth_mm=math.nan), dict(base, edges=[]), dict(base, surprise=1),
                    dict(base, edges=[study.edge((1, 0), (0, 28), 3, 3)]),
                    dict(base, edges=[study.edge((0, 0), (0, 28), 3, 1)])):
            with self.assertRaises(ValueError):
                study.validate(bad)

    def test_bionic_ranking_does_not_assert_head_or_material_validation(self):
        result = study.run()
        self.assertTrue(result['best_bionic_id'].startswith('leaf-'))
        self.assertFalse(result['real_head_optimized'])
        self.assertFalse(result['manufacturing_authorized'])
        self.assertIsNone(result['actual_alloy'])
        self.assertIsNone(result['air_pressure_loss_Pa'])
        self.assertTrue(result['rejected'])
        self.assertLess(max(r['max_relative_128_vs_256'] for r in result['refinement']), 1e-4)

@unittest.skipIf(countercheck is None, 'Working NumPy/SciPy required for finite volumes')
class FinCountercheckTests(unittest.TestCase):
    def test_fused_area_excludes_overlap_then_normalizes(self):
        d = next(d for d in study.designs() if d['id'] == 'leaf-0.7-2.0-2.2-0.75')
        self.assertLess(countercheck.union_area(d)*d['depth_mm'], study.nominal_volume(d))
        corrected = countercheck.normalize(d)
        self.assertAlmostEqual(countercheck.union_area(corrected), 84, places=8)
        self.assertGreater(corrected['edges'][0]['t0_mm'], d['edges'][0]['t0_mm'])

    def test_rectangular_fin_heat_balance_area_and_analytic_limit(self):
        d = next(study.designs())
        result = countercheck.solve(d, 160, 40, .1)
        self.assertLess(result['relative_heat_imbalance'], 1e-8)
        self.assertLess(abs(result['conductance_W_K']/study.conductance(d, 160, 40)-1), .001)
        self.assertAlmostEqual(result['raster_volume_mm3'], 5040)
        self.assertAlmostEqual(result['convection_area_mm2'], 60*(2*28+3)+2*84, places=7)
        self.assertEqual(countercheck.normalize(d), d)
        for step in (.2, .1, .05):
            self.assertAlmostEqual(countercheck.mask(d, step).sum()*step**2*60, 5040)

    def test_sloped_boundary_area_converges_to_euclidean_polygon(self):
        d = countercheck.normalize(next(d for d in study.designs() if d['id'] == 'leaf-0.7-2.0-2.2-0.75'))
        actual = 60*sum(math.dist(a,b) for a,b in countercheck.exterior_segments(d))+2*84
        result = countercheck.solve(d, 80, 100, .1)
        self.assertLess(abs(result['convection_area_mm2']/actual-1), .01)
        self.assertLess(result['relative_heat_imbalance'], 1e-8)
        for bad in (math.nan, .001, 1):
            with self.assertRaises(ValueError):
                countercheck.mask(d, bad)


if __name__ == '__main__':
    unittest.main()
