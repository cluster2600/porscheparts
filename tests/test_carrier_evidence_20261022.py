"""Public numerical claims remain bound to executed receipts and fixed limits."""
import hashlib
import json
from pathlib import Path
import re
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

    def test_dependency_patch_replay_preserves_its_negative_control_and_actual_figure(self):
        base=REPORT/'evidence/mesh-quality-20261025/spooles-upstream-review-015/mac-race-ab-001'
        terminal=json.loads((base/'terminal.json').read_text());self.assertEqual(terminal['baseline_returncode'],1);self.assertEqual(terminal['fixed_returncode'],0)
        for mode,bad in [('baseline',142),('fixed',0)]:
            text=(base/(mode+'-known-solution-test.stdout')).read_text();match=re.search(r'(\d+)/(\d+) iterations wrong',text)
            self.assertEqual(tuple(map(int,match.groups())),(bad,500))
            receipt=json.loads((base/(mode+'-known-solution-test.json')).read_text());self.assertTrue(receipt['process_reaped']);self.assertEqual(receipt['stdout_sha256'],hashlib.sha256(text.encode()).hexdigest())
        media=ROOT/'docs/media/carrier-convergence-20261022/spooles-patch-replay-015';figure=json.loads((media/'figure-provenance.json').read_text());self.assertEqual([r['wrong']for r in figure['results']],[142,0]);self.assertEqual(figure['figure_sha256'],hashlib.sha256((media/'spooles-known-solution-replay.png').read_bytes()).hexdigest());self.assertFalse(figure['carrier_convergence_demonstrated'])

    def test_n48_pass_and_native_fft_controls_preserve_unaccepted_next_levels(self):
        base=REPORT/'evidence/mesh-quality-20261025';steps=json.loads((base/'periodic-gyroid-study-002/comparison-progress.json').read_text());self.assertEqual(steps[-1]['resolution'],48);self.assertTrue(steps[-1]['resolution_change_passed']);self.assertFalse(steps[-2]['resolution_change_passed']);self.assertLess(steps[-1]['relative_void_floor_tensor_change'],.01)
        refused=json.loads((base/'periodic-gyroid-study-002/n64-floor1e-4/case-0/actual-terminal.json').read_text());self.assertEqual(refused['actual_returncode'],124);self.assertTrue(refused['process_reaped']);self.assertTrue(refused['inputs_unchanged']);self.assertEqual(refused['termination_reason'],'wall_timeout')
        fft=json.loads((base/'fft-feasibility-001/qualification-summary.json').read_text());self.assertFalse(fft['unitcell_stiffness_converged']);self.assertFalse(fft['full_Python_package_qualified']);self.assertNotEqual(fft['high_contrast_actual_returncode'],0)
        for name in ['solid-n5','laminate-n5']:self.assertLess(fft['controls'][name]['relative_control_tensor_error'],1e-5)
        fix=json.loads((base/'fft-feasibility-001/private-rpath-fix-001.json').read_text());self.assertFalse(fix['global_packages_changed'])
        for f in fix['files']:self.assertEqual(len(f['after_rpaths']),len(set(f['after_rpaths'])));self.assertEqual(set(f['before_rpaths']),set(f['after_rpaths']));self.assertEqual(len(f['text_section_sha256_unchanged']),64)
        media=ROOT/'docs/media/carrier-convergence-20261022/periodic-cell-research-002';figure=json.loads((media/'figure-provenance.json').read_text());self.assertEqual(figure['figure_sha256'],hashlib.sha256((media/'periodic-cell-stiffness.png').read_bytes()).hexdigest());self.assertEqual(figure['resolutions'],[16,24,32,48]);self.assertFalse(figure['unitcell_stiffness_converged'])

    def test_skin_design_scenarios_keep_original_selection_and_conditional_scope(self):
        base=REPORT/'evidence/mesh-quality-20261025';r=json.loads((base/'cellular-skin-sweep-001/assessment.json').read_text());self.assertEqual(r['status'],'conditional_skin_sensitivity_screen_completed');self.assertFalse(r['geometry_changed']);self.assertFalse(r['changed_geometry_stiffness_predicted']);self.assertFalse(r['printability_qualified']);self.assertFalse(r['bore_keepout_changed']);rows=r['rows'];self.assertEqual([x['skin_mm']for x in rows],[.75,1.,1.25,1.5,2.,3.]);self.assertTrue(all(a['conditional_saving_kg']>b['conditional_saving_kg']for a,b in zip(rows,rows[1:])))
        original=next(x for x in rows if x['skin_mm']==1.5);budget=json.loads((base/'linear-cellular-budget-015/assessment.json').read_text());self.assertEqual(original['selected_cells'],budget['selected_cells']);self.assertEqual(original['conditional_saving_kg'],budget['conditional_mass_reduction_kg'])
        media=ROOT/'docs/media/carrier-convergence-20261022/cellular-skin-sweep-001';figure=json.loads((media/'figure-provenance.json').read_text());self.assertEqual(figure['figure_sha256'],hashlib.sha256((media/'cellular-skin-sensitivity.png').read_bytes()).hexdigest())

    def test_completed_fine_field_keeps_failed_peak_observables_and_actual_teardown(self):
        base=REPORT/'evidence/mesh-quality-20261025';r=json.loads((base/'fine-P2-015-assessment/assessment.json').read_text());receipt=json.loads((base/'linux-015-fine-P2-001/actual-terminal.json').read_text());self.assertEqual(receipt['actual_returncode'],0);self.assertTrue(receipt['process_reaped']);self.assertTrue(receipt['inputs_unchanged']);self.assertEqual(r['result_rows'],dict(displacements=4884701,stresses=12210048,forces=42930));self.assertLess(r['relative_energy_residual'],1e-4);self.assertFalse(r['strength_qualified'])
        comparison=json.loads((base/'P2-spatial-comparison-015.json').read_text());self.assertEqual(len(comparison['comparisons']),1);self.assertFalse(comparison['convergence_demonstrated']);c=comparison['comparisons'][0];self.assertFalse(c['within_limits']);changes=c['relative_change_using_finer_denominator'];self.assertLess(changes['displacement_max_mm'],.02);self.assertLess(changes['compliance_Nmm'],.02);self.assertGreater(changes['global_peak_VM_MPa'],.05);self.assertGreater(changes['central_peak_VM_MPa'],.05)
        diag=json.loads((base/'fine-P2-peak-diagnostic-015/assessment.json').read_text());self.assertTrue(diag['all_integration_points_retained']);self.assertFalse(diag['stress_observables_excluded']);self.assertFalse(diag['singularity_proved']);self.assertLess(diag['peaks'][0]['fixed_patch_rim']['distance_mm'],.01);self.assertEqual(diag['peaks'][0]['VM_MPa'],r['integration_point_VM_max_MPa'])
        guard=json.loads((base/'vast-lease-015/guard-terminal-live.json').read_text());self.assertEqual(guard['status'],'owned_instance_verified_absent');self.assertEqual(guard['consecutive_absent_confirmations'],3)
        media=ROOT/'docs/media/carrier-convergence-20261022/P2-fine-015';figure=json.loads((media/'displacement-figure-provenance.json').read_text());self.assertEqual(figure['figure_sha256'],hashlib.sha256((media/'carrier-quadratic-displacement.png').read_bytes()).hexdigest());self.assertFalse(figure['stress_field_averaged'])

    def test_frozen_core_t10_energy_and_unselected_mkl_backend_stay_separate(self):
        base=REPORT/'evidence/mesh-quality-20261025';r=json.loads((base/'fine-P2-core-energy-015/assessment.json').read_text());self.assertEqual(r['selected_cells'],7401);self.assertTrue(r['selection_unchanged']);self.assertFalse(r['changed_geometry_stiffness_predicted']);self.assertFalse(r['cellular_geometry_generated']);self.assertLess(r['original_T10_energy_fraction_in_selected_cells'],.005)
        refused=json.loads((base/'mkl-feasibility-015/qualification-refusal.json').read_text());self.assertEqual(refused['status'],'MKL_PARDISO_not_qualified_backend_not_selected');self.assertEqual(refused['actual_coarse_backend'],'SPOOLES');self.assertFalse(refused['second_reference_repeat_completed'])

    def test_periodic_cell_control_and_refinement_do_not_become_carrier_convergence(self):
        base=REPORT/'evidence/mesh-quality-20261025'
        control=json.loads((base/'public-periodic-solid-control-002/assessment.json').read_text());self.assertEqual(control['status'],'periodic_full_solid_six_strain_control_passed');self.assertLess(control['relative_solid_control_tensor_error'],1e-5);self.assertEqual(len(control['cases']),6)
        values=[]
        for n in [16,24,32]:
            report=json.loads((base/f'periodic-gyroid-study-001/n{n}-floor1e-6/assessment.json').read_text());self.assertEqual(report['status'],'periodic_gyroid_six_strain_energy_checks_passed');self.assertFalse(report['cellular_part_generated']);self.assertFalse(report['unitcell_mesh_convergence_demonstrated']);self.assertEqual(len(report['cases']),6);self.assertEqual(report['solid_periodic_components'],1);values.append(report['minimum_tensor_stiffness_ratio'])
            self.assertTrue(all(x['relative_energy_residual']<=1e-4 and x['pbc_max_mm']<=1e-8 for x in report['cases']))
        self.assertTrue(all(.15<x<.18 for x in values))
        media=ROOT/'docs/media/carrier-convergence-20261022/periodic-cell-research-001';figure=json.loads((media/'figure-provenance.json').read_text());self.assertEqual(figure['figure_sha256'],hashlib.sha256((media/'periodic-cell-stiffness.png').read_bytes()).hexdigest());self.assertEqual(figure['resolutions'],[16,24,32]);self.assertTrue(all(x>.02 for x in figure['relative_tensor_changes']));self.assertFalse(figure['unitcell_stiffness_converged'])

    def test_finer_interior_screen_keeps_actual_gpu_checks_and_conditional_geometry_scope(self):
        base=REPORT/'evidence/mesh-quality-20261025';budget=json.loads((base/'linear-cellular-budget-015/assessment.json').read_text())
        self.assertEqual(budget['analysis_cells'],3052512);self.assertEqual(budget['selected_cells'],7401);self.assertFalse(budget['reference_geometry_changed']);self.assertFalse(budget['cellular_geometry_generated']);self.assertFalse(budget['cellular_strength_validated'])
        self.assertAlmostEqual(budget['conditional_mass_reduction_kg'],.6*budget['selected_analysis_volume_mm3']*4.42e-6)
        for device in ['cpu','cuda']:
            report=json.loads((base/f'linear-cellular-collected-015/results/{device}/report.json').read_text());self.assertEqual(report['queries'],3052512);self.assertEqual(report['triangles'],785624);self.assertEqual(report['status'],'passed');self.assertEqual(report['fixed_absolute_error_limit_mm'],.0001)
        self.assertTrue(report['gpu_validated']);self.assertEqual(report['actual_device'],'cuda:0')
        media=ROOT/'docs/media/carrier-convergence-20261022/P1-refined-core-screen-015';figure=json.loads((media/'figure-provenance.json').read_text());self.assertEqual(figure['figure_sha256'],hashlib.sha256((media/'carrier-cellular-budget-screen.png').read_bytes()).hexdigest());self.assertEqual(figure['assessment_sha256'],hashlib.sha256((base/'linear-cellular-budget-015/assessment.json').read_bytes()).hexdigest())

    def test_corrected_linux_runtime_keeps_library_identity_and_two_full_reference_checks(self):
        base=REPORT/'evidence/mesh-quality-20261025';built=json.loads((base/'linux-patched-build-collected-015b/binary-identity.json').read_text());self.assertTrue(built['installed_runtime_libraries_unchanged']);self.assertFalse(built['carrier_runtime_qualified'])
        terminal=json.loads((base/'vast-lease-015/patched-reference-terminal.json').read_text());self.assertEqual(terminal['native_binary_sha256'],built['native_binary_sha256']);self.assertEqual(len(terminal['repeats']),2);self.assertTrue(all(row['within_all_limits']for row in terminal['repeats']));self.assertFalse(terminal['spatial_convergence_demonstrated'])
        fetched=json.loads((base/'patched-repro-sources-002/sources-ready.json').read_text());self.assertEqual(fetched['status'],'all_pinned_public_sources_verified');self.assertEqual(len(fetched['files']),15)

    def test_two_execution_repeats_do_not_admit_a_lucky_multithreaded_run_or_become_spatial_steps(self):
        base=REPORT/'evidence/mesh-quality-20261025';trials=json.loads((base/'vast-lease-015/profile-trials.json').read_text());stock=next(x for x in trials if x['mode']=='stock8')
        self.assertEqual([x['assessor_returncode']for x in stock['repeats']],[0,2]);self.assertTrue(stock['refused'])
        selected=json.loads((base/'vast-lease-015/selected-profile.json').read_text());self.assertEqual(selected['mode'],'stock1');self.assertTrue(selected['two_complete_reference_repeats_passed'])
        corrected=json.loads((base/'spooles-upstream-review-015/mac-full-reference-terminal.json').read_text());self.assertEqual(len(corrected['repeats']),2);self.assertTrue(all(x['within_all_limits']for x in corrected['repeats']));self.assertFalse(corrected['spatial_convergence_demonstrated']);self.assertFalse(corrected['fine_field_produced'])

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
