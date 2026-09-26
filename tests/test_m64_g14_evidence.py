"""Public G14 evidence cannot turn numerical consistency into target acceptance."""
import hashlib
import json
import math
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT/'twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926'


class G14Evidence(unittest.TestCase):
    def test_native_sources_and_rejected_coarse_result(self):
        for receipt, source in (('cad-v1.json', 'g14_cad_private.py'),
                                ('cad-lower-v1.json', 'g14_lower_cheeks_private.py'),
                                ('cad-central-v2.json', 'g14_central_followup_private.py'),
                                ('cad-central-root-v1.json', 'g14_central_root_private.py'),
                                ('cad-extended-v1.json', 'g14_extended_haunch_private.py'),
                                ('combined-candidate-clearance-v1.json', 'check_combined_candidates.py')):
            data = json.loads((EVIDENCE/receipt).read_text())
            digest = hashlib.sha256((EVIDENCE/'native-replay'/source).read_bytes()).hexdigest()
            self.assertEqual(data['source_sha256'], digest)
            if receipt != 'combined-candidate-clearance-v1.json':
                self.assertTrue(data['complete'])
                self.assertIsNone(data['error'])
            else:
                self.assertEqual(len(data['pairs']), 3)
                self.assertTrue(all(p['intersection_volume_mm3'] == 0 for p in data['pairs']))
            self.assertFalse(data['manufacturing_authorized'])
            self.assertFalse(data['engine_start_authorized'])
        result = json.loads((EVIDENCE/'central68-coarse.json').read_text())
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
        self.assertGreater(max(norms), .040)
        self.assertFalse(result['below_0_040mm_coarse_screen'])
        self.assertFalse(result['mesh_convergence_qualified'])


if __name__ == '__main__':
    unittest.main()
