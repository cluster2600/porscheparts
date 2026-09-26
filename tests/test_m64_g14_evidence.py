"""Public G14 evidence cannot turn numerical consistency into target acceptance."""
import hashlib
import json
import math
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT/'twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926'


class G14Evidence(unittest.TestCase):
    def test_current_cad_views_and_prepared_linux_recipe_are_pinned(self):
        pins = {
            ROOT/'docs/assets/m64-g14/outer-intake-web.png': 'cdc90b63efb8a65b945d1702a77a8d1b2b85cf8fcedc2d7272aefbddea5ffc3a',
            ROOT/'docs/assets/m64-g14/outer-intake-web-section.png': '3ae91ca5ff4e456bb1c6fbaaad31298adabedcb292b0ef633003caf3240787c7',
            EVIDENCE/'native-replay/linux512/linux_job.py': 'cbfc999a6627991b71d0e139aa6403203c5fea5494053ccf685928915771f08e',
            EVIDENCE/'native-replay/linux512/test_linux_job.py': 'ca425da7543b4e264ad5d94facfc2fc2e08f51a22de73263355dafbc55827f2f',
            EVIDENCE/'native-replay/linux512/inputs.json': '3e8dcfa8c3e41dc289d64099263de68e61475aa7e896260df7a07ab437d3849d',
        }
        for path, expected in pins.items():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected)
        inputs = json.loads((EVIDENCE/'native-replay/linux512/inputs.json').read_text())
        for key in ('build_executed', 'qualification_executed', 'fine_solve_executed'):
            self.assertFalse(inputs[key])
        section = json.loads((EVIDENCE/'section-intake-web-xminus30.json').read_text())
        self.assertEqual(section['source_sha256'], hashlib.sha256(
            (EVIDENCE/'native-replay/section_intake_web.py').read_bytes()).hexdigest())
        self.assertTrue(section['input_unchanged'])
        self.assertTrue(section['section_valid_nonempty'])
        self.assertEqual(section['section_plane_x_mm'], -30)
        for key in ('geometry_redesigned', 'FEA_executed', 'manufacturing_authorized', 'engine_start_authorized'):
            self.assertFalse(section[key])
        for name in ('section-xminus30.png', 'section-xminus30-isometric.png'):
            png = ROOT/'docs/assets/m64-g14'/('outer-intake-web-'+name)
            self.assertEqual(hashlib.sha256(png.read_bytes()).hexdigest(), section['views_sha256'][name])

    def test_native_sources_and_coarse_results(self):
        for receipt, source in (('cad-v1.json', 'g14_cad_private.py'),
                                ('cad-lower-v1.json', 'g14_lower_cheeks_private.py'),
                                ('cad-central-v2.json', 'g14_central_followup_private.py'),
                                ('cad-central-root-v1.json', 'g14_central_root_private.py'),
                                ('cad-extended-v1.json', 'g14_extended_haunch_private.py'),
                                ('cad-central-caps-v1.json', 'g14_central_caps_private.py'),
                                ('cad-outer-root-v1.json', 'g14_outer_root_private.py'),
                                ('cad-outer-upper-caps-v1.json', 'g14_outer_upper_caps_private.py'),
                                ('cad-outer-inner-bands-v1.json', 'g14_outer_inner_bands_private.py'),
                                ('cad-outer-intake-web-v1.json', 'g14_outer_intake_web_private.py'),
                                ('combined-candidate-clearance-v1.json', 'check_combined_candidates.py'),
                                ('combined-caps-extended-clearance-v1.json', 'check_caps_extended_candidates.py'),
                                ('combined-caps-outer-root-clearance-v1.json', 'check_caps_outer_root_candidates.py'),
                                ('combined-caps-outer-upper-clearance-v1.json', 'check_caps_outer_upper_candidates.py'),
                                ('combined-caps-outer-inner-bands-clearance-v1.json', 'check_caps_outer_inner_bands_candidates.py'),
                                ('combined-caps-outer-intake-web-clearance-v1.json', 'check_caps_outer_intake_web_candidates.py')):
            data = json.loads((EVIDENCE/receipt).read_text())
            digest = hashlib.sha256((EVIDENCE/'native-replay'/source).read_bytes()).hexdigest()
            self.assertEqual(data['source_sha256'], digest)
            if not receipt.startswith('combined-'):
                self.assertTrue(data['complete'])
                self.assertIsNone(data['error'])
            else:
                self.assertEqual(len(data['pairs']), 3)
                self.assertTrue(all(p['intersection_volume_mm3'] == 0 for p in data['pairs']))
            self.assertFalse(data['manufacturing_authorized'])
            self.assertFalse(data['engine_start_authorized'])
        for name in ('central68-coarse.json', 'central-local-coarse.json', 'central40-coarse.json',
                     'central-root2-coarse.json', 'outer-extended-coarse.json',
                     'central-caps-coarse.json', 'outer-root2-coarse.json',
                     'outer-upper-caps-coarse.json', 'outer-inner-bands-coarse.json',
                     'outer-intake-web-coarse.json'):
            result = json.loads((EVIDENCE/name).read_text())
            self.assertEqual(result['status'], 'completed')
            self.assertTrue(result['numerically_qualified'])
            self.assertEqual({r['direction'] for r in result['cases']}, {'x', 'minus_z'})
            norms = []
            for row in result['cases']:
                self.assertTrue(row['mechanics']['equilibrium_passed'])
                self.assertEqual(row['solver']['info'], 0)
                self.assertLessEqual(row['residual'], 1e-8)
                self.assertLessEqual(row['agreement']['max_nodal_difference_over_max_reference_U'], 1e-4)
                for vector in row['mechanics']['journal_weighted_displacement_mm'].values():
                    self.assertEqual(len(vector), 3)
                    self.assertTrue(all(math.isfinite(v) for v in vector))
                    norms.append(math.hypot(*vector))
            self.assertAlmostEqual(max(norms), result['maximum_journal_motion_mm'], places=14)
            passed = name in ('central-caps-coarse.json', 'outer-intake-web-coarse.json')
            self.assertEqual(max(norms) <= .040, passed)
            self.assertEqual(result['below_0_040mm_coarse_screen'], passed)
            self.assertFalse(result['mesh_convergence_qualified'])

    def test_retry_preserves_original_failed_execution(self):
        failed = json.loads((EVIDENCE/'outer-combined-cg-timeout.json').read_text())
        retry = json.loads((EVIDENCE/'outer-combined-cg-retry.json').read_text())
        self.assertEqual(failed['status'], 'failed')
        self.assertFalse(failed['numerically_qualified'])
        self.assertEqual(retry['original_failed_summary_sha256'], failed['summary_sha256'])
        self.assertTrue(retry['original_failed_execution_unchanged'])
        self.assertTrue(retry['numerically_qualified'])
        self.assertFalse(retry['CCX_rerun'])
        self.assertGreater(retry['maximum_journal_motion_mm'], .040)
        self.assertFalse(retry['below_0_040mm_coarse_screen'])
        self.assertFalse(retry['mesh_convergence_qualified'])

    def test_medium_result_and_plug_nonaggravation_are_not_final_acceptance(self):
        medium = json.loads((EVIDENCE/'central-caps-medium-hashfix.json').read_text())
        coarse = json.loads((EVIDENCE/'central-caps-coarse.json').read_text())
        self.assertEqual(medium['status'], 'completed')
        self.assertTrue(medium['numerically_qualified'])
        self.assertTrue(medium['artifact_hashes_match'])
        self.assertEqual(medium['verified_artifact_count'], 37)
        self.assertEqual(medium['mesh']['size_mm'], 1.5)
        comparison = medium['coarse_to_medium']
        self.assertEqual(comparison['coarse_case_sha256'], coarse['case_sha256'])
        norms = []
        for row in medium['cases']:
            self.assertEqual(row['solver']['info'], 0)
            self.assertTrue(row['mechanics']['equilibrium_passed'])
            self.assertLessEqual(row['residual'], 1e-8)
            self.assertLessEqual(row['agreement']['max_nodal_difference_over_max_reference_U'], 1e-4)
            old = next(r for r in coarse['cases'] if r['direction'] == row['direction'])
            a, b = old['mechanics'], row['mechanics']
            change = next(r for r in comparison['comparisons'] if r['direction'] == row['direction'])
            raw_change = max(math.dist(a['journal_weighted_displacement_mm'][s],
                                      b['journal_weighted_displacement_mm'][s]) /
                             math.hypot(*b['journal_weighted_displacement_mm'][s])
                             for s in ('intake', 'exhaust'))
            stress_change = abs(a['von_Mises_p95_MPa'] - b['von_Mises_p95_MPa']) / b['von_Mises_p95_MPa']
            self.assertAlmostEqual(raw_change, change['journal_vector_relative_change'])
            self.assertAlmostEqual(stress_change, change['stress_p95_relative_change'])
            self.assertLessEqual(raw_change, .01)
            self.assertLessEqual(stress_change, .05)
            norms.extend(math.hypot(*v) for v in b['journal_weighted_displacement_mm'].values())
        self.assertAlmostEqual(max(norms), medium['maximum_journal_motion_mm'])
        self.assertLessEqual(max(norms), .040)
        for key in ('mesh_convergence_qualified', 'assembled_stiffness_qualified',
                    'hot_material_qualified', 'manufacturing_authorized', 'engine_start_authorized'):
            self.assertFalse(medium[key])
        cad = json.loads((EVIDENCE/'cad-outer-intake-web-v1.json').read_text())
        for row in cad['variants']:
            self.assertTrue(row['cad_accepted'])
            self.assertFalse(row['service_removal_qualified'])
            self.assertEqual(set(row['plug_removal_checks']), {'1', '2'})
            checks = row['plug_removal_checks'].values()
            self.assertTrue(all(v['new_material_overlap_mm3'] == 0 for v in checks))
            self.assertGreater(max(v['baseline_overlap_mm3'] for v in checks), 1756)

    def test_mesh_preflight_and_preconditioner_are_not_acceptance(self):
        for name, source in (
                ('central-caps-mesh-1p5.json', 'caps_mesh_preflight.py'),
                ('central-caps-mesh-1.json', 'caps_mesh_preflight.py'),
                ('amg-benchmark.json', 'amg_benchmark.py')):
            data = json.loads((EVIDENCE/name).read_text())
            self.assertEqual(data['source_sha256'], hashlib.sha256(
                (EVIDENCE/'native-replay/fea'/source).read_bytes()).hexdigest())
            self.assertTrue(data['complete'])
            self.assertIsNone(data['error'])
            self.assertFalse(data['mesh_convergence_qualified'])
            self.assertFalse(data['manufacturing_authorized'])
            self.assertFalse(data['engine_start_authorized'])
            if name.startswith('central-'):
                self.assertFalse(data['FEA_executed'])
                self.assertFalse(data['CCX_executed'])
                self.assertGreater(data['mesh']['minimum_Gauss4_Jacobian_mm3'], 0)
            else:
                self.assertFalse(data['production_recipe_promoted'])
                self.assertFalse(data['CUDA_executed'])
                self.assertEqual({(r['direction'], r['method']) for r in data['cases']},
                                 {(d, m) for d in ('x', 'minus_z') for m in ('jacobi', 'amg')})
                self.assertTrue(all(r['passed'] and r['relative_residual'] <= 1e-8
                                    for r in data['cases']))

    def test_failed_medium_solve_is_not_a_target_or_resource_failure(self):
        failed = json.loads((EVIDENCE/'central-caps-medium-failure.json').read_text())
        crash = json.loads((EVIDENCE/'central-caps-medium-crash-diagnostic.json').read_text())
        for key, filename in (('source_sha256', 'caps_medium_candidate.py'),
                              ('test_sha256', 'test_caps_medium_candidate.py')):
            self.assertEqual(failed[key], hashlib.sha256(
                (EVIDENCE/'native-replay/fea'/filename).read_bytes()).hexdigest())
        self.assertEqual(crash['attempt_summary_sha256'], failed['summary_sha256'])
        self.assertEqual(crash['attempt_case_sha256'], failed['case_sha256'])
        self.assertEqual(crash['termination_signal_number'], 11)
        self.assertEqual(crash['faulting_frames'][0]['symbol'], 'I2Ohash_insert')
        self.assertIsNone(failed['native_CCX_returncode'])
        self.assertEqual(failed['x_DAT_bytes'], 0)
        self.assertFalse(failed['resource_guard_triggered'])
        for key in ('complete', 'numerically_qualified', 'minus_z_executed',
                    'matrix_export_executed', 'CG_executed', 'mesh_convergence_qualified',
                    'manufacturing_authorized', 'engine_start_authorized'):
            self.assertFalse(failed[key])
        witness = json.loads((EVIDENCE/'spooles-hash-unit-qualification.json').read_text())
        self.assertTrue(witness['unit_fix_qualified'])
        self.assertFalse(witness['primary_original_passed_flag'])
        self.assertFalse(witness['FEA_executed'])
        for key, filename in (('reproducer_sha256', 'spooles-hash-reproducer.c'),
                              ('three_line_patch_sha256', 'spooles-hash-three-line.patch')):
            self.assertEqual(witness[key], hashlib.sha256(
                (EVIDENCE/'native-replay'/filename).read_bytes()).hexdigest())

    def test_retained_energy_diagnostic_is_balanced_not_a_new_solve(self):
        for name, source in (
                ('outer-extended-minus-z-energy-v2.json', 'outer_energy_diagnostic.py'),
                ('outer-root2-minus-z-energy-v1.json', 'outer_root_energy_diagnostic.py'),
                ('outer-upper-caps-minus-z-energy-v2.json', 'outer_upper_caps_energy_diagnostic.py')):
            data = json.loads((EVIDENCE/name).read_text())
            self.assertEqual(data['source_sha256'], hashlib.sha256(
                (EVIDENCE/'native-replay/fea'/source).read_bytes()).hexdigest())
            self.assertEqual(data['input_hashes_before'], data['input_hashes_after'])
            self.assertFalse(data['new_solve_executed'])
            self.assertFalse(data['manufacturing_authorized'])
            self.assertTrue(data['balance']['passed'])
            self.assertLessEqual(data['balance']['relative_difference'], 1e-4)
            self.assertAlmostEqual(sum(r['energy_fraction'] for r in data['regions']), 1.)

    def test_rebuilt_reference_is_two_load_numerical_proof_not_medium_acceptance(self):
        data = json.loads((EVIDENCE/'hashfixed-reference.json').read_text())
        self.assertEqual(data['proof']['source_sha256'], hashlib.sha256(
            (EVIDENCE/'native-replay/fea/hashfix_reference.py').read_bytes()).hexdigest())
        self.assertTrue(data['complete'])
        self.assertTrue(data['all_numerical_checks_passed'])
        self.assertIsNone(data['error'])
        self.assertTrue(data['runtime_verified_after'])
        self.assertFalse(data['matrix_reexported'])
        self.assertTrue(data['fresh_CPU_CG'])
        self.assertFalse(data['manufacturing_authorized'])
        self.assertFalse(data['engine_start_authorized'])
        self.assertEqual({r['direction'] for r in data['rows']}, {'x', 'minus_z'})
        for row in data['rows']:
            self.assertTrue(row['passed'])
            self.assertEqual(row['direct']['native_returncode'], 0)
            self.assertTrue(row['mechanics']['equilibrium_passed'])
            self.assertLessEqual(row['relative_residual'], 1e-8)
            self.assertLessEqual(row['agreement']['max_nodal_difference_over_max_reference_U'], 1e-4)

    def test_prepared_fine_decks_are_not_fine_solve_evidence(self):
        receipt_path = EVIDENCE/'central-fine-decks-prepared.json'
        data = json.loads(receipt_path.read_text())
        controller = json.loads((EVIDENCE/'central-fine-decks-controller.json').read_text())
        self.assertEqual(controller['receipt_sha256'], hashlib.sha256(receipt_path.read_bytes()).hexdigest())
        self.assertEqual(data['proof'], controller['proof'])
        for key, name in (('source_sha256', 'fine_deck_prepare.py'),
                          ('test_sha256', 'test_fine_deck_prepare.py')):
            self.assertEqual(data['proof'][key], hashlib.sha256((EVIDENCE/'native-replay/fea'/name).read_bytes()).hexdigest())
        for value in (data, controller):
            self.assertTrue(value['complete'])
            self.assertIsNone(value['error'])
            for key in ('FEA_executed', 'CCX_executed', 'CG_executed', 'CUDA_executed',
                        'mesh_convergence_qualified', 'remote_Linux_job_operational',
                        'manufacturing_authorized', 'engine_start_authorized'):
                self.assertFalse(value[key])
        mesh = data['mesh']
        self.assertEqual(mesh['size_mm'], 1.)
        self.assertEqual(mesh['nominal_journal_width_mm'], 11)
        self.assertGreater(mesh['minimum_Gauss4_Jacobian_mm3'], 0)
        self.assertEqual(data['kinematic_free_dofs'], 3*(mesh['nodes']-mesh['fixed_nodes']))
        self.assertEqual({r['direction'] for r in data['deck_checks']['cases']}, {'x', 'minus_z'})
        for row in data['deck_checks']['cases']:
            self.assertTrue(row['full_bottom_land_fixed_XYZ'])
            self.assertTrue(row['load_sign_and_axis_passed'])
            for side, force in row['journal_force_magnitudes_N'].items():
                self.assertAlmostEqual(force, row['expected_journal_forces_N'][side], places=8)


if __name__ == '__main__':
    unittest.main()
