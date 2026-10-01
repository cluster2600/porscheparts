"""Check Qwen's graph contract and the retained digital concept's provenance."""
import hashlib
import json
from pathlib import Path
import re
import struct
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'parts/993-eng-carrier-0001/source/qwen-concept-f1'
DERIVED = ROOT / 'parts/993-eng-carrier-0001/derived/qwen-concept-f1'


class CarrierQwenTests(unittest.TestCase):
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
