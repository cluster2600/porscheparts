"""Analytic cell scale and native backend evidence retain their distinct scope."""
import hashlib
import json
import math
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'docs/reports/carrier-convergence-20261022/evidence/mesh-quality-20261025'


class CellScaleTests(unittest.TestCase):
    def test_scale_bounds_match_the_constructed_level_pair(self):
        r=json.loads((BASE/'gyroid-scale-bounds-001/assessment.json').read_text())
        a=r['threshold'];u=.5*math.asin(2*a/3)
        self.assertAlmostEqual(3*math.sin(u)*math.cos(u),a)
        for row in r['rows']:
            p=row['pitch_mm'];lo=a*p/(2*math.pi*math.sqrt(3));hi=math.sqrt(3)*math.asin(2*a/3)*p/(2*math.pi)
            self.assertAlmostEqual(row['minimum_opposite_level_gap_lower_mm'],lo)
            self.assertAlmostEqual(row['minimum_opposite_level_gap_upper_mm'],hi)
            self.assertLessEqual(lo,hi)
            self.assertAlmostEqual(row['nominal_pad_core_periods']*p,r['nominal_pad_core_depth_mm'])
        self.assertFalse(r['part_geometry_changed']);self.assertFalse(r['printability_qualified'])
        image=ROOT/'docs/media/carrier-convergence-20261022/gyroid-scale-bounds-001/gyroid-length-scale.png'
        self.assertEqual(hashlib.sha256(image.read_bytes()).hexdigest(),r['figure_sha256'])

    def test_actual_pardiso_two_full_repeats_keep_original_component_limits(self):
        r=json.loads((BASE/'vast-lease-020/pardiso-reference-terminal.json').read_text())
        self.assertEqual(r['status'],'actual_PARDISO_two_complete_reference_repeats_passed')
        self.assertEqual(len(r['repeats']),2)
        for row in r['repeats']:
            self.assertTrue(row['within_all_limits'])
            for name,limit in [('displacement',1e-5),('stress',.01),('reactions',.01)]:
                self.assertLessEqual(row['maximum_component_differences'][name],limit)

    def test_shared_operator_preserves_negative_control_and_all_six_gold_fields(self):
        p=BASE/'unitcellengine-factor-reuse-001/collected-controls'
        bad=json.loads((p/'upstream-soft/assessment.json').read_text())
        self.assertGreater(min(bad['relative_energy_residuals']),.01)
        for name in ['adapted-soft','adapted-solid','adapted-n16']:
            r=json.loads((p/name/'assessment.json').read_text())
            self.assertEqual(r['status'],'independent_operator_energy_checks_passed')
            self.assertLessEqual(max(r['relative_energy_residuals']),1e-4)
            self.assertEqual(len(r['solve_calls']),1)
            self.assertEqual(r['solve_calls'][0]['rhs_shape'][1],6)
            self.assertFalse(r['carrier_convergence_demonstrated'])
        cross=json.loads((p/'n16-crosscheck.json').read_text())
        self.assertEqual(cross['status'],'six_complete_CCX_field_crosschecks_passed')
        self.assertEqual(len(cross['cases']),6)
        for row in cross['cases']:
            self.assertEqual(row['physical_node_count'],4913)
            self.assertEqual(row['stress_integration_points'],32768)
            self.assertLessEqual(row['U_max_component_difference_mm'],1e-5)
            self.assertLessEqual(row['S_max_component_difference_MPa'],.01)
            self.assertLessEqual(row['RF_max_component_difference_N'],.01)
