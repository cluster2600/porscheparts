import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import build_carrier_workshop_guide_v2 as public_base

original_builder = public_base.build
spec = importlib.util.spec_from_file_location('carrier_workshop_v3', ROOT/'scripts/build_carrier_workshop_guide_v3.py')
guide = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guide)


class WorkshopGuideV3(unittest.TestCase):
    def descriptor(self):
        data = json.loads((ROOT/'manufacturing/workflows/993-carrier-guide.json').read_text())
        data['stages'][5]['commands'] = [
            'python3 scripts/run_part_workflow.py run '+guide.OLD_RECIPE+' --runtime work/part-workflow/runtime-v2.json --output work/NEW',
            'python3 scripts/assemble_carrier_workflow.py verify work/ACTUAL']
        return data

    def test_presentation_uses_v3_without_changing_frozen_admission_or_other_commands(self):
        data = self.descriptor()
        before = copy.deepcopy(data)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'description.json'
            path.write_text(json.dumps(data))
            with patch.object(guide, 'build', return_value={'rendered':True}) as renderer:
                self.assertEqual(guide.render(path, Path(directory)/'guide'), {'rendered':True})
            rendered = json.loads(path.read_text())
            renderer.assert_called_once_with(path, Path(directory)/'guide')
        self.assertIs(public_base.build, original_builder)
        self.assertIsNot(guide._base, public_base)
        self.assertEqual(rendered['stages'][:3], before['stages'][:3])
        self.assertEqual(rendered['stages'][4], before['stages'][4])
        self.assertEqual(rendered['stages'][5]['commands'][1], before['stages'][5]['commands'][1])
        self.assertIn(guide.NEW_RECIPE, rendered['stages'][5]['commands'][0].split())
        self.assertIn('interfaces de contact', rendered['stages'][3]['purpose'])
        self.assertEqual(rendered['workshop_adapter']['sha256'],
                         hashlib.sha256((ROOT/'scripts/build_carrier_workshop_guide_v3.py').read_bytes()).hexdigest())

    def test_unknown_layout_or_reproduction_command_cannot_be_rewritten(self):
        cases = []
        for command in ['unexpected command', 'python3 '+guide.OLD_RECIPE+'.other']:
            data = self.descriptor()
            data['stages'][5]['commands'][0] = command
            cases.append(data)
        data = self.descriptor()
        data['stages'][3]['id'] = 'unexpected'
        cases.append(data)
        for data in cases:
            with self.subTest(data=data), tempfile.TemporaryDirectory() as directory:
                path = Path(directory)/'description.json'
                path.write_text(json.dumps(data))
                before = path.read_bytes()
                with self.assertRaises(ValueError), patch.object(guide, 'build') as renderer:
                    guide.render(path, Path(directory)/'guide')
                renderer.assert_not_called()
                self.assertEqual(path.read_bytes(), before)

    def test_changed_frozen_source_is_rejected_before_package_call(self):
        with patch.object(guide, 'BASE_SHA256', '0'*64), patch.object(guide._base, 'package') as package:
            with self.assertRaisesRegex(ValueError, 'sources changed'):
                guide.package(Path('work/UNUSED'))
            package.assert_not_called()
