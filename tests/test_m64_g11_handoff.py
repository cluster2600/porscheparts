"""The prepared assembly and GPU job cannot be mistaken for a released result."""
import json
import hashlib
from pathlib import Path
import subprocess
import unittest


class G11HandoffChecks(unittest.TestCase):
    def test_delivery_incident_preserves_unknown_outcomes_and_evidence(self):
        evidence = Path(__file__).resolve().parents[1] / 'twins/m64-cylinder-head/evidence/g11-support-stiffness-20260926'
        incident = json.loads((evidence / 'delivery-incident.json').read_text())
        for name in ('collection_archive_retrieved', 'complete_solver_fields_retained',
                     'finest_mesh_acceptance_demonstrated', 'target_0p040_mm_demonstrated',
                     'manufacturing_authorized', 'engine_start_authorized'):
            self.assertIs(incident[name], False)
        self.assertEqual(incident['final_compute_status'], 'unknown')
        self.assertIsNone(incident['actual_cost_USD'])
        self.assertIsNone(incident['provider_observation']['actual_deletion_time_and_cause'])
        self.assertIsNone(incident['additional_stdout_observations']['one_mm_final_outcomes'])
        for item in incident['retained_evidence']:
            self.assertEqual(hashlib.sha256((evidence / item['path']).read_bytes()).hexdigest(), item['sha256'])

    def test_published_cad_checks_do_not_release_the_part(self):
        root = Path(__file__).resolve().parents[1]
        source = root / 'twins/m64-cylinder-head/source/fourvalve/g11_cad.py'
        evidence = root / 'twins/m64-cylinder-head/evidence/g11-support-stiffness-20260926'
        cad = json.loads((evidence / 'cad.json').read_text())
        self.assertEqual(cad['source_sha256'], hashlib.sha256(source.read_bytes()).hexdigest())
        self.assertTrue(cad['complete'])
        self.assertFalse(cad['manufacturing_authorized'])
        self.assertFalse(cad['engine_start_authorized'])
        self.assertEqual(cad['crank_samples_deg'], list(range(0, 720, 5)))
        self.assertEqual(len(cad['variants']), 12)
        for variant in cad['variants']:
            self.assertTrue(variant['cad_accepted'])
            self.assertEqual(variant['motion_samples_checked'], 144)
            self.assertEqual(variant['rejections'], [])
            self.assertEqual(variant['sampled_motion_interferences'], [])
        comparison = json.loads((evidence / 'baseline-brep-comparison.json').read_text())
        for row in comparison['results']:
            self.assertEqual(row['old_minus_new_mm3'], 0)
            self.assertEqual(row['new_minus_old_mm3'], 0)
            self.assertTrue(row['bounds_identical'])

    def test_preparation_preserves_unqualified_inputs_and_shell_syntax(self):
        source = Path(__file__).resolve().parents[1] / 'twins/m64-cylinder-head/source/fourvalve'
        subprocess.run(['bash', '-n', str(source / 'g11_gpu_job.sh')], check=True)
        record = json.loads((source / 'g11_assembly_inputs.json').read_text())
        self.assertEqual(record['classification'], 'assembly_calculation_preparation_not_a_solved_assembly')
        for gate in ('assembled_stiffness_qualified', 'hot_material_qualified',
                     'manufacturing_authorized', 'engine_start_authorized'):
            self.assertIs(record[gate], False)
        self.assertIs(record['omniverse_handoff']['structural_validation'], False)
        self.assertTrue({'head', 'central_diaphragm', 'carrier_base_p', 'carrier_base_m',
                         'cam_caps', 'rocker_shafts', 'camshafts', 'carrier_fasteners',
                         'head_fasteners'} <= set(record['required_components']))
        missing = ' '.join(record['required_inputs_not_qualified']).lower()
        for essential in ('restraints', 'preload', 'engagement', 'retention', '0.040 mm',
                          'friction', 'temperature', 'load cycle'):
            self.assertIn(essential, missing)
        self.assertIn('no automatic promotion when none passes', record['selection'])
        self.assertIn('Never bridge the nominal shaft gap', record['optimistic_linked_case_policy'])
        self.assertTrue({'translation_relative_to_head_mm', 'axis_rotation_relative_to_head_rad',
                         'force_and_moment_balance', 'mesh_sensitivity', 'input_provenance'}
                        <= set(record['outputs_required']))


if __name__ == '__main__':
    unittest.main()
