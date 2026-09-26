"""Public G14 evidence cannot turn numerical consistency into target acceptance."""
import hashlib
import json
import math
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT/'twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926'


class G14Evidence(unittest.TestCase):
    def test_native_sources_and_coarse_results(self):
        for receipt, source in (('cad-v1.json', 'g14_cad_private.py'),
                                ('cad-lower-v1.json', 'g14_lower_cheeks_private.py'),
                                ('cad-central-v2.json', 'g14_central_followup_private.py'),
                                ('cad-central-root-v1.json', 'g14_central_root_private.py'),
                                ('cad-extended-v1.json', 'g14_extended_haunch_private.py'),
                                ('cad-central-caps-v1.json', 'g14_central_caps_private.py'),
                                ('cad-outer-root-v1.json', 'g14_outer_root_private.py'),
                                ('combined-candidate-clearance-v1.json', 'check_combined_candidates.py'),
                                ('combined-caps-extended-clearance-v1.json', 'check_caps_extended_candidates.py'),
                                ('combined-caps-outer-root-clearance-v1.json', 'check_caps_outer_root_candidates.py')):
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
                     'central-caps-coarse.json', 'outer-root2-coarse.json'):
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
            passed = name == 'central-caps-coarse.json'
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


if __name__ == '__main__':
    unittest.main()
