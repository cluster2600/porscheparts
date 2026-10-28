"""Guide exports contain only declared files and safely embed their description."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'scripts/build_part_workflow_guide.py'
spec = importlib.util.spec_from_file_location('workflow_guide', SOURCE)
guide = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guide)


class WorkshopGuideTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.asset = self.root / 'part.step'
        self.asset.write_text('authored test geometry')
        self.data = {'title': '</script><img src=x onerror=alert(1)>',
                     'inputs': [{'title': 'Plan', 'description': 'Known scale'}],
                     'stages': [{'files': [{'source': 'part.step', 'label': 'STEP'}]} for _ in range(6)]}
        self.description = self.root / 'description.json'

    def save(self):
        self.description.write_text(json.dumps(self.data))

    def test_export_binds_assets_and_escapes_script_terminators(self):
        self.save()
        def pdf(data, output):
            (output / 'guide-atelier.pdf').write_bytes(b'%PDF-fixture')
        with patch.object(guide, 'ROOT', self.root), patch.object(guide, 'make_pdf', pdf):
            manifest = guide.build(self.description, self.root / 'export')
        document = (self.root / 'export/index.html').read_text()
        self.assertNotIn(self.data['title'], document)
        self.assertIn('\\u003c/script\\u003e', document)
        copied = manifest['sources']['part.step']
        self.assertEqual(guide.digest(self.root / 'export' / copied['file']), guide.digest(self.asset))
        self.assertEqual(set(manifest['outputs_sha256']), {'index.html', 'guide-atelier.pdf'})

    def test_asset_path_cannot_escape_repository(self):
        self.data['stages'][0]['files'][0]['source'] = '../private.step'
        self.save()
        with patch.object(guide, 'ROOT', self.root), self.assertRaises(ValueError):
            guide.build(self.description, self.root / 'rejected')


if __name__ == '__main__':
    unittest.main()
