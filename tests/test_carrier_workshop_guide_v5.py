"""The v5 wrapper changes only its command and adapter provenance."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import build_carrier_workshop_guide_v4 as public_v4

ORIGINAL_BUILD, ORIGINAL_PACKAGE = public_v4.build, public_v4.package
spec = importlib.util.spec_from_file_location('carrier_workshop_v5', ROOT/'scripts/build_carrier_workshop_guide_v5.py')
guide = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guide)


class WorkshopGuideV5(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.description = self.root/'guide-description.json'
        self.data = dict(stages=[dict(id=name, checks=[], files=[]) for name in
            ('reference', 'dimensions', 'mechanics', 'supports', 'layers', 'delivery')],
            constitutive_reference=dict(frames_verified=16, ENER_all_frames_pass=False,
                independent_Piola_all_frames_pass=True, STEP_equivalence_claimed=False),
            workshop_adapter=dict(source='scripts/build_carrier_workshop_guide_v4.py', sha256=guide.BASE_SHA256))
        self.data['stages'][2]['checks'] = [dict(label='Grade 23 ELI'), dict(label='900 MPa'), dict(label='ENER REFUSÉ')]
        self.data['stages'][2]['files'] = [dict(source='constitutive-reference/'+str(i)) for i in range(7)]
        self.data['stages'][5]['commands'] = ['python3 scripts/run_part_workflow.py run '+guide.OLD_RECIPE+
            ' --runtime work/runtime-v2.json --output work/fresh',
            'python3 scripts/assemble_carrier_workflow.py verify work/fresh']
        self.save()

    def save(self):
        self.description.write_text(json.dumps(self.data, ensure_ascii=False))

    def test_private_v4_hook_and_reference_policy_leave_public_module_intact(self):
        self.assertIs(public_v4.build, ORIGINAL_BUILD)
        self.assertIs(public_v4.package, ORIGINAL_PACKAGE)
        self.assertIsNot(guide._base, public_v4)
        self.assertIs(guide._base.build, guide.render)
        self.assertEqual(guide._base.REFERENCE_FILES, public_v4.REFERENCE_FILES)
        self.assertEqual(guide._base.CASE_ID, public_v4.CASE_ID)
        self.assertEqual(guide.digest(guide.BASE), guide.BASE_SHA256)

    def test_only_recipe_token_and_adapter_provenance_change(self):
        expected = copy.deepcopy(self.data)
        expected['stages'][5]['commands'][0] = expected['stages'][5]['commands'][0].replace(guide.OLD_RECIPE, guide.NEW_RECIPE)
        expected['workshop_adapter'] = dict(source='scripts/build_carrier_workshop_guide_v5.py',
            sha256=guide.SOURCE_SHA256, base_sha256=guide.BASE_SHA256,
            retained_adapter=self.data['workshop_adapter'])
        with patch.object(guide, 'build', return_value={'software_fixture': True}) as render:
            result = guide.render(self.description, self.root/'guide')
        self.assertEqual(json.loads(self.description.read_text()), expected)
        self.assertEqual(result, {'software_fixture': True})
        render.assert_called_once_with(self.description, self.root/'guide')
        self.assertFalse((self.root/'guide').exists())

    def test_unknown_or_duplicate_command_and_wrong_layout_refuse_before_writing(self):
        for mode in ('missing', 'duplicate', 'layout'):
            with self.subTest(mode=mode):
                original = copy.deepcopy(self.data)
                if mode == 'missing':self.data['stages'][5]['commands'][0] = 'unexpected command'
                elif mode == 'duplicate':self.data['stages'][5]['commands'][0] += ' '+guide.OLD_RECIPE
                else:self.data['stages'][5]['id'] = 'unexpected'
                self.save();before = self.description.read_bytes()
                with patch.object(guide, 'build') as render, self.assertRaises(ValueError):
                    guide.render(self.description, self.root/'guide')
                render.assert_not_called()
                self.assertEqual(self.description.read_bytes(), before)
                self.data = original

    def test_changed_source_or_base_pin_refuses_before_delegation(self):
        for field in ('SOURCE_SHA256', 'BASE_SHA256'):
            with self.subTest(field=field), patch.object(guide, field, '0'*64), patch.object(guide._base, 'package') as base:
                with self.assertRaisesRegex(ValueError, 'sources changed'):guide.package(self.root)
                base.assert_not_called()

    def test_package_delegates_without_changing_v4_arguments(self):
        with patch.object(guide._base, 'package', return_value={'delegated': True}) as base:
            self.assertEqual(guide.package(self.root), {'delegated': True})
        base.assert_called_once_with(self.root)

    def test_post_delegate_source_guard_is_preserved(self):
        def altered(run):
            guide.SOURCE_SHA256 = '0'*64
            return {'delegated': True}
        with patch.object(guide, 'SOURCE_SHA256', guide.SOURCE_SHA256), patch.object(guide._base, 'package', side_effect=altered) as base:
            with self.assertRaisesRegex(ValueError, 'sources changed'):guide.package(self.root)
        base.assert_called_once_with(self.root)


if __name__ == '__main__':
    unittest.main()
