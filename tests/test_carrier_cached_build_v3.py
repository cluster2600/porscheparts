import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

if importlib.util.find_spec('pyslm') is None:
    raise unittest.SkipTest('Optional coverage runtime required')
from pyslm.support import support as native_support
if not hasattr(native_support, '_triangulate_exact_projected_domain'):
    raise unittest.SkipTest('Pinned coverage runtime required')

SOURCE = Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/process-skins-20261016'
sys.path.insert(0, str(SOURCE))
import build_cached as public_base
import admissions_v3 as public_admission

original_seal, original_prepared = public_base.seal, public_base.PreparedRegions
original_construction = public_admission._construction
spec = importlib.util.spec_from_file_location('carrier_cached_v3', SOURCE/'build_cached_v3.py')
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)


class CachedBuildV3(unittest.TestCase):
    def stage(self, directory):
        directory.mkdir()
        checkpoint = dict(input_sha256='a'*64, manufacturing_preparation_admitted=True,
                          admission={}, outputs_sha256={}, admission_runtime_hooks=driver.RUNTIME_HOOKS)
        for key in driver.KEYS:
            receipt = dict(passed=True, status='passed', input_sha256=checkpoint['input_sha256'],
                admission_schema=driver.SCHEMA,
                admission_source_sha256=driver.POLICY_SHA256[driver.POLICY_FILES[1]],
                admission_runtime_hooks=driver.RUNTIME_HOOKS)
            name = f'admission-{key}.json'
            (directory/name).write_text(json.dumps(receipt))
            checkpoint['admission'][key] = dict(status='passed', receipt=name, receipt_sha256=driver.sha(directory/name))
        self.save_checkpoint(directory, checkpoint)
        return checkpoint

    def save_checkpoint(self, directory, checkpoint):
        (directory/'support-stage.json').write_text(json.dumps(checkpoint))

    def change_receipt(self, directory, checkpoint, key, **values):
        item = checkpoint['admission'][key]
        path = directory/item['receipt']
        data = json.loads(path.read_text())
        data.update(values)
        path.write_text(json.dumps(data))
        item['receipt_sha256'] = driver.sha(path)
        self.save_checkpoint(directory, checkpoint)

    def test_only_private_modules_receive_v3_policy_and_all_sources_are_pinned(self):
        self.assertIs(public_base.seal, original_seal)
        self.assertIs(public_base.PreparedRegions, original_prepared)
        self.assertIs(public_admission._construction, original_construction)
        self.assertIs(driver._base.seal, driver.seal)
        self.assertIs(driver.admissions_v3._construction, driver._index)
        self.assertEqual(driver.POLICY_SHA256[driver.POLICY_FILES[2]], driver.INDEX_SHA256)
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory)/'manifest.json'
            original.write_text('{}')
            prepared = SimpleNamespace(files={original:driver.sha(original)})
            checked = []
            def verify():
                checked.append(True)
                self.assertTrue(all(driver.sha(p)==s for p,s in prepared.files.items()))
            prepared.verify = verify
            with patch.object(driver, '_prepared_regions', return_value=prepared):
                self.assertIs(driver.prepared_regions('manifest', [0]), prepared)
            self.assertEqual(checked, [True])
            self.assertEqual(prepared.files, {original:driver.sha(original), **driver.POLICY_SHA256})

    def test_passed_v2_or_another_v3_source_cannot_start_reuse(self):
        for update in [dict(admission_schema='support-geometry-v2-continuous-intervals'),
                       dict(admission_source_sha256='b'*64), dict(admission_runtime_hooks={})]:
            with self.subTest(update=update), tempfile.TemporaryDirectory() as directory:
                stage = Path(directory)/'stage'
                checkpoint = self.stage(stage)
                self.change_receipt(stage, checkpoint, 'grids', **update)
                with patch.object(driver._base, 'build') as build, self.assertRaisesRegex(ValueError, 'exact v3 policy'):
                    driver.build('input', Path(directory)/'output', 'store', 'cache', reuse_support_stage=stage)
                build.assert_not_called()
                self.assertFalse((Path(directory)/'output').exists())

    def test_changed_receipt_missing_gate_and_path_escape_are_refused(self):
        for kind in ['changed', 'missing', 'escape']:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                stage = Path(directory)/'stage'
                checkpoint = self.stage(stage)
                if kind == 'changed':
                    with (stage/'admission-grids.json').open('a') as stream:
                        stream.write(' ')
                elif kind == 'missing':
                    checkpoint['admission'].pop('grids')
                    self.save_checkpoint(stage, checkpoint)
                else:
                    checkpoint['admission']['grids']['receipt'] = '../outside.json'
                    self.save_checkpoint(stage, checkpoint)
                with self.assertRaises(ValueError):
                    driver.verify_v3_stage(stage)

    def test_changed_policy_source_prevents_delegation(self):
        with patch.dict(driver.POLICY_SHA256, {driver.POLICY_FILES[0]:'0'*64}), patch.object(driver._base, 'build') as build:
            with self.assertRaisesRegex(ValueError, 'policy changed'):
                driver.build('input', 'output', 'store', 'cache')
            build.assert_not_called()

    def test_seal_binds_hook_to_every_receipt_and_rehashes_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'output'
            checkpoint = self.stage(output)
            checkpoint.pop('admission_runtime_hooks')
            for key in driver.KEYS:
                self.change_receipt(output, checkpoint, key, admission_runtime_hooks=None)
            before = {key:item['receipt_sha256'] for key,item in checkpoint['admission'].items()}
            with patch.object(driver.admissions_v3, 'seal', return_value=(checkpoint['admission'], True)):
                admission, admitted = driver.seal(output, checkpoint, object())
            self.assertTrue(admitted)
            self.assertEqual(set(admission), set(driver.KEYS))
            for key,item in admission.items():
                self.assertNotEqual(before[key], item['receipt_sha256'])
                self.assertEqual(item['receipt_sha256'], driver.sha(output/item['receipt']))
            driver.verify_v3_stage(output)
            checkpoint.pop('admission_runtime_hooks')
            self.save_checkpoint(output, checkpoint)
            with self.assertRaisesRegex(ValueError, 'runtime hook'):
                driver.verify_v3_stage(output)

    def test_new_checkpoint_retains_raw_receipts_and_records_adapter_source(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'output'
            saved = {}
            def build(*args):
                checkpoint = self.stage(output)
                saved.update({p.name:p.read_bytes() for p in output.glob('admission-*.json')})
                return copy.deepcopy(checkpoint)
            with patch.object(driver._base, 'build', side_effect=build):
                result = driver.build('input', output, 'store', 'cache', supports_only=True)
            self.assertEqual(result['support_strategy'], driver.STRATEGY)
            self.assertEqual(result['runner_adapter_source_sha256'], driver.sha(driver.POLICY_FILES[0]))
            self.assertEqual(json.loads((output/'support-stage.json').read_text()), result)
            self.assertEqual({p.name:p.read_bytes() for p in output.glob('admission-*.json')}, saved)
            self.assertEqual(driver.verify_v3_stage(output)['input_sha256'], 'a'*64)

    def test_full_build_restores_hook_and_report_checkpoint_hash_after_core_reuse(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'output'
            def build(*args):
                checkpoint = self.stage(output)
                checkpoint.pop('admission_runtime_hooks')
                self.save_checkpoint(output, checkpoint)
                return dict(outputs_sha256={'support-stage.json':driver.sha(output/'support-stage.json')})
            with patch.object(driver._base, 'build', side_effect=build):
                result = driver.build('input', output, 'store', 'cache')
            self.assertEqual(result['outputs_sha256']['support-stage.json'], driver.sha(output/'support-stage.json'))
            driver.verify_v3_stage(output)
