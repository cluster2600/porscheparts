"""Public numerical claims remain bound to executed receipts and fixed limits."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'docs/reports/carrier-convergence-20261022'


class EvidenceTests(unittest.TestCase):
    def test_every_published_exact_copy_keeps_its_recorded_digest(self):
        manifest=json.loads((REPORT/'evidence-copy-manifest.json').read_text())
        self.assertGreater(len(manifest['exact_copies']),50)
        for row in manifest['exact_copies']:
            with self.subTest(path=row['path']):self.assertEqual(hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest(),row['sha256'])

    def test_actual_cuda_and_cpu_pass_the_same_unchanged_oracle_limit(self):
        reports=[json.loads((REPORT/f'evidence/warp/results/carrier-{device}/report.json').read_text())for device in ['cpu','cuda']]
        for row in reports:
            self.assertEqual(row['status'],'passed');self.assertEqual(row['fixed_absolute_error_limit_mm'],.0001);self.assertEqual(row['queries'],65536);self.assertLessEqual(row['maximum_absolute_error_mm'],.0001)
        self.assertTrue(reports[1]['gpu_validated']);self.assertEqual(reports[1]['actual_device'],'cuda:0');self.assertEqual(reports[0]['source_sha256'],reports[1]['source_sha256'])

    def test_refused_and_incomplete_solves_never_become_convergence(self):
        bad=json.loads((REPORT/'evidence/h0-P1-native-001-energy-diagnostic-001/assessment.json').read_text());self.assertGreater(bad['relative_energy_residual'],bad['fixed_relative_limit'])
        timeout=json.loads((REPORT/'evidence/refused-fine-and-tetgen-collected-001/h1-P2-native-001/actual-terminal.json').read_text());self.assertEqual(timeout['actual_returncode'],124);self.assertTrue(timeout['outer_timeout']);self.assertTrue(timeout['process_reaped']);self.assertFalse(timeout['solver_finished_marker'])
        comparison=json.loads((REPORT/'evidence/P1-comparison.json').read_text());self.assertFalse(comparison['convergence_demonstrated'])

    def test_quadratic_comparison_stays_open_despite_stable_global_stiffness(self):
        row=json.loads((REPORT/'evidence/P2-comparison-001.json').read_text())
        self.assertFalse(row['convergence_demonstrated'])
        changes=row['comparisons'][0]['relative_change_using_finer_denominator']
        self.assertLess(changes['displacement_max_mm'],.02)
        self.assertGreater(changes['central_peak_VM_MPa'],.05)
        timeout=json.loads((REPORT/'evidence/serial-followup-mechanics-collected-001/h1-P2-serial-all-002/actual-terminal.json').read_text())
        self.assertEqual(timeout['actual_returncode'],124);self.assertTrue(timeout['process_reaped'])

    def test_cellular_screen_does_not_become_a_changed_part_or_resistance_claim(self):
        screen=json.loads((REPORT/'evidence/cellular-budget-001/assessment.json').read_text())
        self.assertFalse(screen['reference_geometry_changed']);self.assertFalse(screen['cellular_geometry_generated']);self.assertFalse(screen['cellular_strength_validated'])
        self.assertGreater(screen['conditional_mass_reduction_kg'],0)
        self.assertLess(screen['conditional_mass_reduction_kg'],.002)
        for device in ['cpu','cuda']:
            row=json.loads((REPORT/f'evidence/cellular-screen-collected-001/results/cellular-{device}/report.json').read_text())
            self.assertEqual(row['queries'],screen['analysis_cells']);self.assertEqual(row['status'],'passed');self.assertEqual(row['fixed_absolute_error_limit_mm'],.0001)
        self.assertTrue(row['gpu_validated'])

    def test_compiler_case_keeps_the_failed_control_and_fixed_comparison_limits(self):
        row=json.loads((REPORT/'evidence/compiler-regression-comparison-001.json').read_text())
        self.assertFalse(row['cases']['static']['fixed_limits_pass']);self.assertTrue(row['cases']['recursive']['fixed_limits_pass'])
        self.assertEqual(row['contract']['stress_component_difference_limit_MPa'],.01)
        rejected=json.loads((REPORT/'evidence/serial-followup-mechanics-collected-001/compiler-recursive-P2-001/actual-terminal.json').read_text())
        self.assertNotEqual(rejected['actual_returncode'],0);self.assertTrue(rejected['process_reaped'])


if __name__=='__main__':unittest.main()
