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

    def test_complete_N64_fields_do_not_turn_a_failed_refinement_into_convergence(self):
        r=json.loads((BASE/'shared-N64-refinement-020/assessment.json').read_text())
        self.assertTrue(r['all_twelve_actual_N64_strain_fields_collected'])
        self.assertEqual(r['relative_refinement_limit'],.02)
        self.assertEqual(r['required_successive_refinement_comparisons'],2)
        self.assertGreater(r['rows'][-1]['relative_tensor_resolution_change'],.02)
        self.assertFalse(r['rows'][-1]['resolution_change_passed'])
        self.assertTrue(r['rows'][-1]['void_floor_test_passed'])
        self.assertFalse(r['unitcell_stiffness_converged']);self.assertFalse(r['carrier_convergence_demonstrated'])
        source=ROOT/'parts/993-eng-carrier-0001/source/design-20261016/convergence-20261022/unitcellengine-study/compare_shared_cells.py'
        self.assertIn(hashlib.sha256(source.read_bytes()).hexdigest(),r['source_sha256'].values())
        for name in ['bounded900-n64-floor1e-4','bounded900-n64-floor1e-6']:
            audit=json.loads((BASE/'unitcellengine-collected-020'/name/'saved-field-audit.json').read_text())
            self.assertEqual(audit['stress_points_per_case'],2097152)
            self.assertEqual(audit['actual_cases'],6)
            self.assertLessEqual(max(x['relative_work_error']for x in audit['cases']),1e-4)

    def test_big_native_crosscheck_keeps_only_its_four_completed_strain_cases(self):
        r=json.loads((BASE/'unitcellengine-factor-reuse-001/n64-native-four-field-crosscheck.json').read_text())
        self.assertEqual(len(r['cases']),4);self.assertFalse(r['native_N64_tensor_complete'])
        self.assertEqual(r['missing_native_strain_modes'],[4,5])
        source=ROOT/'parts/993-eng-carrier-0001/source/design-20261016/convergence-20261022/unitcellengine-study/compare_native_N64_partial.py'
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),r['source_sha256'])
        for row in r['cases']:
            self.assertEqual(row['counts']['stresses'],2097152)
            self.assertLessEqual(row['maximum_component_differences']['displacements'],1e-5)
            self.assertLessEqual(row['maximum_component_differences']['stresses'],.01)
            self.assertLessEqual(row['maximum_component_differences']['forces'],.01)

    def test_paid_runtime_is_absent_after_complete_collection(self):
        p=BASE/'vast-lease-020';guard=json.loads((p/'guard-terminal-live.json').read_text());destroy=json.loads((p/'research-custodian-destroy.stdout').read_text());inventory=json.loads((p/'post-collection-inventory.json').read_text());collection=json.loads((p/'research-collection-complete.json').read_text())
        self.assertEqual(guard['status'],'owned_instance_verified_absent')
        self.assertEqual(guard['consecutive_absent_confirmations'],3)
        self.assertTrue(destroy['destroyed']);self.assertTrue(destroy['verified_absent'])
        self.assertFalse(inventory['owned_instance_present']);self.assertEqual(inventory['account_instance_count'],0)
        self.assertLess(collection['epoch'],guard['observed_epoch'])
