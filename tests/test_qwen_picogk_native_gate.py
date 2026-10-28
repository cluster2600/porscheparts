"""Check the plan trust boundary and the recorded witnesses without requiring the private native runtime."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT/'training/qwen-picogk-native-gate'
RESULTS = json.loads((HERE/'results.json').read_text())


class PicoGKNativeGateTest(unittest.TestCase):
    def test_boundary(self):
        script = HERE/'gate.py'
        result = subprocess.run([sys.executable, str(script), '--self-check'],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_results_bind_the_committed_sources(self):
        for name, digest in RESULTS['source_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(), digest, name)

    def test_summary_follows_the_recorded_witnesses(self):
        fixtures, summary = RESULTS['fixtures'], RESULTS['summary']
        for key, flag in (('native', 'native_pass'), ('vdb', 'vdb_pass'), ('raw_mesh', 'raw_mesh_pass')):
            self.assertEqual(summary[key], {'passed': sum(f[flag] for f in fixtures), 'total': len(fixtures)}, key)
        for f in fixtures:
            mesh = f['raw_mesh']
            # The auditor's rule, recomputed from the recorded topology rather than trusted from its flag.
            strict = mesh['watertight'] and mesh['winding_consistent'] and mesh['exact_zero_area_faces'] == 0 and mesh['signed_triangle_volume'] > 0
            self.assertEqual(mesh['strict_raw_mesh_screen_pass'], strict, f['plan'])
            self.assertEqual(f['raw_mesh_pass'], strict, f['plan'])
            self.assertEqual(f['status'] == 'accepted_synthetic_geometry', f['native_pass'] and f['vdb_pass'] and f['raw_mesh_pass'], f['plan'])
            self.assertFalse(f['vdb']['reconstructed_from_stl']); self.assertIn(f['voxel_mm'], (0.5, 1.0))
        self.assertFalse(RESULTS['manufacturing_qualified']); self.assertFalse(RESULTS['mesh_repairs_applied'])
        self.assertFalse(RESULTS['model_usage']['native']['manufacturing_qualified'])

    def test_negative_inputs_never_reach_geometry(self):
        cases = RESULTS['negative_checks']['cases']
        self.assertEqual(len(cases), RESULTS['summary']['negative_inputs_rejected_before_execution'])
        self.assertTrue(all(c['status'] == 'rejected' and c['geometry_executed'] is False for c in cases))

    def test_qualified_command_receipt_is_refused(self):
        # The qualified command from PR 257 records a plan without raw_response/structure_passed; this gate fails closed on it.
        # A separate interpreter keeps pilot's sibling imports away from modules other tests already loaded.
        probe = ("import runpy, sys; gate = runpy.run_path(sys.argv[1])\n"
                 "pipe = {'recipe': 'pipe', 'parameters_mm': [18, 7, 3], 'missing': []}\n"
                 "receipt = {'plan': pipe, 'model_called': True, 'semantic_intent_verified': True, 'geometry_executed': False, 'manufacturing_qualified': False}\n"
                 "try: gate['checked_plan'](receipt, pipe)\n"
                 "except ValueError as error: print(error)\n"
                 "else: sys.exit('accepted')\n")
        result = subprocess.run([sys.executable, '-c', probe, str(HERE/'gate.py')], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('complete raw response', result.stdout)
