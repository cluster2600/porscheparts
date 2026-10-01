"""Check Qwen's graph contract and the retained digital concept's provenance."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'parts/993-eng-carrier-0001/source/qwen-concept-f1'
DERIVED = ROOT / 'parts/993-eng-carrier-0001/derived/qwen-concept-f1'
spec = importlib.util.spec_from_file_location('carrier_interfaces', SOURCE / 'interfaces.py')
interfaces = importlib.util.module_from_spec(spec)
spec.loader.exec_module(interfaces)


class CarrierQwenTests(unittest.TestCase):
    def test_closed_mesh_cannot_hide_missing_engine_attachment(self):
        result = interfaces.carrier_preflight()
        self.assertEqual(result['decision'], 'blocked')
        self.assertEqual(result['missing_interfaces'], ['engine_bracket'])
        self.assertEqual(result['unverified_interfaces'], sorted(interfaces.ROLES))
        self.assertIsNone(result['material_grade'])
        self.assertIs(result['manufacturing_authorized'], False)
        with self.assertRaisesRegex(ValueError, 'blocked'):
            interfaces.require_preflight()
        self.assertEqual(interfaces.require_preflight(shape_study=True), result)
        contract = json.loads((SOURCE / 'interface-contract.json').read_text())
        del contract['requirements']['engine_bracket']
        with patch.object(interfaces.json, 'loads', return_value=contract):
            with self.assertRaisesRegex(ValueError, 'missing required interface'):
                interfaces.carrier_preflight()
        # A model's boolean or total opening count cannot replace attachment inspection.
        for actual in (True, 4):
            result = interfaces.assess({'bracket': {'attachment_sites': 4, 'reference': 'pet_only'}},
                {'bracket': {'attachment_sites': actual, 'inspection': 'model_says_complete'}})
            self.assertEqual(result['decision'], 'blocked')

    def test_generation_and_export_block_before_loading_native_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'must-not-exist'
            for name in ('infer.py', 'export_checked.py'):
                completed = subprocess.run([sys.executable, str(SOURCE / name), '/missing-input', str(output)],
                    capture_output=True, text=True)
                self.assertNotEqual(completed.returncode, 0)
                self.assertIn('Carrier generation/export blocked', completed.stderr)
                self.assertFalse(output.exists())

    def test_training_families_are_disjoint_and_incident_is_not_trained(self):
        # Load the curriculum without the optional MLX runtime or cached model.
        with patch.dict(sys.modules, {'interfaces': interfaces}):
            spec = importlib.util.spec_from_file_location('carrier_training', SOURCE / 'train_interfaces.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            rows = module.cases()
        self.assertEqual(len(rows), 89)
        self.assertEqual(len({r['messages'][1]['content'] for r in rows}), len(rows))
        families = {s: {r['family'] for r in rows if r['split'] == s} for s in ('train', 'valid', 'test', 'incident')}
        for a, left in families.items():
            for b, right in families.items():
                if a != b:
                    self.assertFalse(left & right)
        for row in rows:
            self.assertIs(row['expected']['manufacturing_authorized'], False)
            if row['split'] != 'incident':
                self.assertEqual(row['expected']['decision'], 'engineering_review_required' if row['scenario'] == 6 else 'blocked')
                self.assertEqual(row['expected'], interfaces.assess(row['requirements'], row['observations']))
        self.assertEqual(rows[-1]['id'], 'incident-99311502153')
        self.assertEqual(rows[-1]['split'], 'incident')
        with patch.dict(sys.modules, {'interfaces': interfaces, 'train_interfaces': module}):
            spec = importlib.util.spec_from_file_location('carrier_training_v2', SOURCE / 'train_interfaces_v2.py')
            continuation = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(continuation)
            extended = continuation.cases()
        self.assertEqual({s: sum(r['split'] == s for r in extended) for s in ('train', 'valid', 'test', 'regression')},
                         {'train': 210, 'valid': 70, 'test': 81, 'regression': 25})
        self.assertEqual(len({r['messages'][1]['content'] for r in extended}), len(extended))
        old_tests = {r['id'] for r in rows if r['split'] in ('test', 'incident')}
        self.assertEqual({r['id'] for r in extended if r['split'] == 'regression'}, old_tests)
        self.assertFalse(old_tests & {r['id'] for r in extended if r['split'] == 'train'})
        joint = next(r for r in extended if r.get('states') == ('absent', 'unknown', 'unknown'))
        self.assertEqual(len(joint['expected']['missing_interfaces']), 1)
        self.assertEqual(len(joint['expected']['unverified_interfaces']), 3)
        groups = {s: {r['family'] for r in extended if r['split'] == s} for s in ('train', 'valid', 'test', 'regression')}
        for a, left in groups.items():
            for b, right in groups.items():
                if a != b:
                    self.assertFalse(left & right)

    def test_model_edges_and_export_closure(self):
        receipt = json.loads((SOURCE / 'inference.json').read_text())
        self.assertEqual(receipt['adapter_sha256'], 'a1014c6f71b46d879c09462c4a57d17d00df8f11b8178dd53bf6d5f2ac2f778a')
        rejected, accepted = receipt['attempts']
        self.assertTrue(all(not r['semantic_passed'] for r in rejected['records']))
        code = []
        for row in accepted['records']:
            self.assertTrue(row['semantic_passed'])
            lines = row['parsed_code'].splitlines()
            self.assertEqual(len(lines), 4)
            for line, (a, b) in zip(lines, row['edges']):
                numbers = [float(v) for v in re.findall(r'(-?\d+(?:\.\d+)?)[fF]\b', line)]
                self.assertEqual(numbers, row['vertices'][a] + [0.6] + row['vertices'][b] + [0.6])
                self.assertTrue(line.endswith('true);'))
            code.extend(lines)
        source = (SOURCE / 'Program.cs').read_text()
        block = source.split('// BEGIN QWEN:', 1)[1].split('\n', 1)[1].split('// END QWEN')[0].strip()
        self.assertEqual(block, '\n'.join(code))

        report = json.loads((DERIVED / 'checks.json').read_text())
        for name in ('Program.cs', 'inference.json', 'export.py'):
            self.assertEqual(hashlib.sha256((SOURCE / name).read_bytes()).hexdigest(), report['inputs'][name])
        for name, expected in report['outputs'].items():
            self.assertEqual(hashlib.sha256((DERIVED / name).read_bytes()).hexdigest(), expected)
        stl = (DERIVED / 'carrier-concept.stl').read_bytes()
        triangles = struct.unpack_from('<I', stl, 80)[0]
        self.assertEqual(len(stl), 84 + triangles * 50)
        self.assertEqual(triangles, report['mesh']['triangles'])
        self.assertTrue(report['mesh']['watertight'])
        self.assertEqual(report['mesh']['connected_components'], 1)
        self.assertEqual(report['mesh']['euler_characteristic'], -6)
        self.assertTrue(report['usd']['reopened'] and report['usd']['mesh_arrays_match'])
        for flag in ('physical_part_access_confirmed', 'is_fitment_validated', 'is_material_qualified', 'is_manufacturing_release'):
            self.assertIs(report[flag], False)


if __name__ == '__main__':
    unittest.main()
