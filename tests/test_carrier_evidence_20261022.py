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

    def test_quadratic_displacement_image_is_bound_to_the_accepted_complete_field(self):
        media=ROOT/'docs/media/carrier-convergence-20261022/P2-quality-remesh'
        figure=json.loads((media/'displacement-figure-provenance.json').read_text())
        accepted=REPORT/'evidence/mesh-quality-20261025/mac-remeshed-P2-assessment-001/assessment.json'
        self.assertIn(hashlib.sha256(accepted.read_bytes()).hexdigest(),figure['source_sha256'].values())
        self.assertEqual(figure['figure_sha256'],hashlib.sha256((media/'carrier-quadratic-displacement.png').read_bytes()).hexdigest())
        self.assertEqual(figure['deformation_scale'],10)
        self.assertEqual(figure['display_triangles'],4*figure['complete_boundary_faces'])
        self.assertTrue(figure['all_quadratic_boundary_nodes_included'])
        self.assertFalse(figure['spatial_convergence_demonstrated'])
        self.assertAlmostEqual(figure['displacement_max_mm'],json.loads(accepted.read_text())['displacement_max_mm'])

    def test_new_gpu_core_screen_keeps_fixed_limits_and_conditional_mass_scope(self):
        base=REPORT/'evidence/mesh-quality-20261025'
        reports=[json.loads((base/f'remeshed-cellular-collected-010/results/{device}/report.json').read_text())for device in ['cpu','cuda']]
        for report in reports:
            self.assertEqual(report['status'],'passed')
            self.assertEqual(report['queries'],381564)
            self.assertEqual(report['fixed_absolute_error_limit_mm'],.0001)
            self.assertLessEqual(report['maximum_absolute_error_mm'],.0001)
        self.assertEqual(reports[0]['source_sha256'],reports[1]['source_sha256'])
        self.assertTrue(reports[1]['gpu_validated'])
        self.assertEqual(reports[1]['actual_device'],'cuda:0')
        screen=json.loads((base/'remeshed-cellular-budget-001/assessment.json').read_text())
        self.assertEqual(screen['parameters']['skin_mm'],1.5)
        self.assertEqual(screen['parameters']['bore_keepout_mm'],10)
        self.assertEqual(screen['selected_cells'],44)
        self.assertFalse(screen['reference_geometry_changed'])
        self.assertFalse(screen['cellular_geometry_generated'])
        self.assertFalse(screen['cellular_strength_validated'])

    def test_replacement_fine_timeout_keeps_no_field_and_confirmed_teardown(self):
        base=REPORT/'evidence/mesh-quality-20261025'
        receipt=json.loads((base/'linux-010-recursive-fine-P2-001/actual-terminal.json').read_text())
        self.assertEqual(receipt['actual_returncode'],124)
        self.assertTrue(receipt['outer_timeout'])
        self.assertTrue(receipt['process_reaped'])
        self.assertTrue(receipt['inputs_unchanged'])
        self.assertEqual(receipt['output_sha256']['job.dat'],hashlib.sha256(b'').hexdigest())
        refusal=json.loads((base/'linux-010-fine-refusal-001.json').read_text())
        self.assertFalse(refusal['field_assessment_published'])
        self.assertFalse(refusal['convergence_demonstrated'])
        absent=json.loads((base/'vast-lease-010/supervisor-absence-verified.json').read_text())
        self.assertTrue(absent['verified_absent'])

    def test_actual_cuda_and_cpu_pass_the_same_unchanged_oracle_limit(self):
        reports=[json.loads((REPORT/f'evidence/warp/results/carrier-{device}/report.json').read_text())for device in ['cpu','cuda']]
        for row in reports:
            self.assertEqual(row['status'],'passed');self.assertEqual(row['fixed_absolute_error_limit_mm'],.0001);self.assertEqual(row['queries'],65536);self.assertLessEqual(row['maximum_absolute_error_mm'],.0001)
        self.assertTrue(reports[1]['gpu_validated']);self.assertEqual(reports[1]['actual_device'],'cuda:0');self.assertEqual(reports[0]['source_sha256'],reports[1]['source_sha256'])

    def test_cross_host_normal_exit_does_not_override_failed_complete_reference(self):
        base=REPORT/'evidence/mesh-quality-20261025'
        receipt=json.loads((base/'linux-013-recursive-coarse-P2-001/actual-terminal.json').read_text())
        self.assertEqual(receipt['actual_returncode'],0)
        self.assertTrue(receipt['solver_finished_marker'])
        field=json.loads((base/'linux-013-coarse-P2-assessment-001/assessment.json').read_text())
        self.assertEqual(field['status'],'quadratic_equilibrium_or_energy_refused')
        self.assertEqual(field['result_rows']['stresses'],4*field['C3D10_elements'])
        self.assertGreater(field['relative_energy_residual'],field['fixed_energy_relative_limit'])
        self.assertFalse(field['stress_convergence_demonstrated'])
        guard=json.loads((base/'vast-lease-013/guard-terminal-live.json').read_text())
        self.assertEqual(guard['consecutive_absent_confirmations'],3)

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
