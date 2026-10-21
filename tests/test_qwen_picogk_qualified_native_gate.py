"""Check the typed receipt boundary without private models or native runtime."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT/'training/qwen-picogk-native-gate/qualified_gate.py'
SETUP = '''
import copy, json, runpy, sys
gate = runpy.run_path(sys.argv[1])
plan = {'recipe': 'pipe', 'parameters_mm': [18, 7, 3], 'missing': []}
request = {'recipe': 'pipe', 'language': 'en', 'interface_status': 'synthetic', 'fields': {
    'length': {'value': 18, 'unit': 'mm', 'quantity': 'length'},
    'outer': {'value': 14, 'unit': 'mm', 'quantity': 'diameter'},
    'inner': {'value': 6, 'unit': 'mm', 'quantity': 'diameter'}}}
manifest = {'qualified_profile_sha256': 'profile', 'adapter_sha256': 'adapter'}
receipt = {'plan': plan, 'semantic_intent_verified': True, 'model_called': True,
           'geometry_executed': False, 'manufacturing_qualified': False,
           'profile_sha256': 'profile', 'adapter_sha256': 'adapter', 'request_sha256': 'request'}
def check(value=receipt, expected=plan, query=request):
    return gate['checked_plan'](value, expected, query, 'request', manifest)
def reject(value=receipt, expected=plan, query=request):
    try: check(value, expected, query)
    except (ValueError, TypeError): pass
    else: raise AssertionError('Invalid typed receipt accepted')
'''


class QualifiedNativeGateTests(unittest.TestCase):
    def probe(self, body):
        result = subprocess.run([sys.executable, '-c', SETUP + body, str(SCRIPT)],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_qualified_typed_plan_does_not_invent_model_text(self):
        self.probe("assert 'raw_response' not in receipt; assert check() == plan")

    def test_receipt_identity_is_bound(self):
        self.probe("\nfor key in ('profile_sha256', 'adapter_sha256', 'request_sha256'):\n reject(dict(receipt, **{key: 'changed'}))")

    def test_receipt_flags_require_exact_booleans(self):
        self.probe("\nfor key in ('semantic_intent_verified', 'model_called', 'geometry_executed', 'manufacturing_qualified'):\n reject(dict(receipt, **{key: 'false'}))")

    def test_request_and_independent_expected_both_match(self):
        self.probe("changed = copy.deepcopy(request); changed['fields']['length']['value'] = 19\nreject(query=changed)\nreject(expected=dict(plan, parameters_mm=[19, 7, 3]))")

    def test_unverified_interfaces_never_reach_geometry(self):
        self.probe("reject(query=dict(request, interface_status='unverified'))")

    def test_nonfinite_boolean_and_extra_plan_fields_fail(self):
        self.probe("\nfor values in ([18, True, 3], [18, float('nan'), 3]):\n reject(dict(receipt, plan=dict(plan, parameters_mm=values)))\nreject(dict(receipt, plan=dict(plan, extra='untrusted')))\nreject(dict(receipt, plan=None))")

    def test_recorded_sources_and_geometry_decisions(self):
        report = json.loads((SCRIPT.parent/'results-qualified-20261022.json').read_text())
        for name, digest in report['source_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(), digest, name)
        for key, block, flag in (('native', 'native', 'geometry_screen_passed'),
                                  ('vdb', 'vdb', 'passed'), ('raw_mesh', 'raw_mesh', 'strict_raw_mesh_screen_pass')):
            self.assertEqual(report['summary'][key],
                             {'passed': sum(f[block][flag] for f in report['fixtures']), 'total': len(report['fixtures'])})
        for fixture in report['fixtures']:
            mesh = fixture['raw_mesh']
            strict = (mesh['watertight'] and mesh['winding_consistent']
                      and mesh['exact_zero_area_faces'] == 0 and mesh['signed_triangle_volume'] > 0)
            self.assertEqual(mesh['strict_raw_mesh_screen_pass'], strict)
            self.assertEqual(fixture['status'] == 'accepted_synthetic_geometry',
                             fixture['native']['geometry_screen_passed'] and fixture['vdb']['passed'] and strict)
            self.assertFalse(fixture['manufacturing_qualified'])
        self.assertEqual(len(report['negative_checks']), 8)
        self.assertTrue(all(x['status'] == 'rejected' and x['geometry_executed'] is False
                            for x in report['negative_checks']))
        self.assertTrue(report['existing_output_overwrite_rejected'])
        self.assertEqual(report['model_smoke']['status'], 'accepted_synthetic_geometry')
        self.assertFalse(report['model_smoke']['original_model_text_recorded'])
        for flag in ('manufacturing_qualified', 'model_weights_updated', 'serving_defaults_changed',
                     'mesh_repairs_applied', 'historical_training_reproduced'):
            self.assertFalse(report[flag], flag)
