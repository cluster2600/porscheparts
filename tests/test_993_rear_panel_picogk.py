"""Catch stale PicoGK concept exports without requiring a native CAD runtime."""
import hashlib
import json
from pathlib import Path
import struct
import unittest


CAD = Path(__file__).resolve().parents[1] / 'docs/projects/993-programmable-rear-panel/cad'


class RearPanelConceptTests(unittest.TestCase):
    def test_sources_and_exports_match_inspected_revision(self):
        report = json.loads((CAD / 'preview/checks.json').read_text())
        for folder, key in ((CAD, 'source_hashes'), (CAD / 'preview', 'exports')):
            for name, expected in report[key].items():
                with self.subTest(file=name):
                    self.assertEqual(hashlib.sha256((folder / name).read_bytes()).hexdigest(), expected)
        self.assertEqual(report['parameters'], json.loads((CAD / 'concept.json').read_text()))
        self.assertEqual(report['status'], 'visual_concept_not_oem_not_for_manufacturing')
        for key in ('physical_fit_checked', 'fastening_design_complete',
                    'optical_performance_checked', 'thermal_checked', 'manufacturing_authorized'):
            self.assertIs(report[key], False)

    def test_glb_contains_four_separate_concept_parts(self):
        data = (CAD / 'preview/rear-panel-concept.glb').read_bytes()
        magic, version, length = struct.unpack_from('<4sII', data)
        self.assertEqual((magic, version, length), (b'glTF', 2, len(data)))
        size, kind = struct.unpack_from('<I4s', data, 12)
        self.assertEqual(kind, b'JSON')
        scene = json.loads(data[20:20 + size])
        self.assertEqual({mesh['name'] for mesh in scene['meshes']},
                         {'lens', 'housing', 'rear-cover', 'display-envelope'})
        self.assertEqual(len([node for node in scene['nodes'] if 'mesh' in node]), 4)


if __name__ == '__main__':
    unittest.main()
