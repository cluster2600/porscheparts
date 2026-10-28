"""An isolated mixed-store reader must not weaken the frozen exposure checks."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

if any(importlib.util.find_spec(name) is None for name in ('numpy', 'trimesh', 'shapely')):
    raise unittest.SkipTest('Optional geometry runtime required')

SOURCE = Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/process-scanpath-audit-20261016'
sys.path.insert(0, str(SOURCE))
import audit_support_scanpaths_hybrid as audit
import audit_complete_supports_hybrid as complete


class MixedStoreAudit(unittest.TestCase):
    def fixture(self, root):
        snapshot = root/'source'
        snapshot.mkdir()
        contents = {
            'admitted_regions.py': 'class EnvelopeStore:\n    def __init__(self,*args):\n        raise ValueError("v1 rejects a mixed store")\n',
            'native_prism_case.py': 'def load_case(*args):\n    return "synthetic native case"\n',
            'admitted_regions_v2.py': ('from admitted_regions import EnvelopeStore as HistoricalStore\n'
                'from native_prism_case import load_case\n'
                'class EnvelopeStore(HistoricalStore):\n'
                '    def __init__(self,path,input_sha256,parameters):\n'
                '        self.path,self.checked=path,0\n'
                '    def verify(self):\n        self.checked+=1\n'),
            'interface_sources.py': '# Synthetic dependency\n',
            'interface_sources_prisms.py': '# Synthetic dependency\n',
            'interface_sources_prisms_v2.py': '# Synthetic dependency\n',
        }
        for name, text in contents.items():
            (snapshot/name).write_text(text)
        digests = {name: audit.sha(snapshot/name) for name in contents}
        report = dict(input_sha256='synthetic-part', parameters={'layer_height_mm': .06},
                      outputs_sha256={'source/'+name: value for name, value in digests.items()})
        return snapshot, digests, report

    def setUp(self):
        # These module names belong to each synthetic source snapshot. Real
        # modules from other tests are restored unchanged, never silently reused.
        self.saved = {name: sys.modules.pop(name, None) for name in ('admitted_regions', 'native_prism_case')}

    def tearDown(self):
        for name, value in self.saved.items():
            sys.modules.pop(name, None)
            if value is not None:
                sys.modules[name] = value

    def load(self, injection, snapshot):
        spec = injection.private_importlib().util.spec_from_file_location(
            'support_audit_envelopes', snapshot/'admitted_regions.py')
        module = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(snapshot))
        try:
            spec.loader.exec_module(module)
        finally:
            sys.path.pop(0)
        return module

    def test_old_reader_refuses_mixed_schema_then_private_adapter_uses_v2(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot, digests, report = self.fixture(root)
            original_spec = importlib.util.spec_from_file_location
            old = audit.private_module(snapshot/'admitted_regions.py', digests['admitted_regions.py'], '_synthetic_v1')
            with self.assertRaisesRegex(ValueError, 'v1 rejects'):
                old.EnvelopeStore(snapshot, report['input_sha256'], report['parameters'])
            with mock.patch.object(audit, 'STORE_SOURCES', digests):
                injection = audit.HybridImport(root, report)
                module = self.load(injection, snapshot)
                store = module.EnvelopeStore(snapshot, report['input_sha256'], report['parameters'])
                injection.verify()
            self.assertEqual((injection.loads, injection.stores), (1, 1))
            self.assertGreaterEqual(store.checked, 2)
            self.assertIs(importlib.util.spec_from_file_location, original_spec)
            with self.assertRaisesRegex(ValueError, 'v1 rejects'):
                old.EnvelopeStore(snapshot, report['input_sha256'], report['parameters'])

    def test_other_imports_are_unchanged_and_envelope_path_cannot_be_redirected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot, digests, report = self.fixture(root)
            with mock.patch.object(audit, 'STORE_SOURCES', digests):
                injection = audit.HybridImport(root, report)
                unrelated = injection.spec_from_file_location('unrelated', snapshot/'native_prism_case.py')
                self.assertIsInstance(unrelated.loader, importlib.machinery.SourceFileLoader)
                with self.assertRaisesRegex(ValueError, 'Unexpected'):
                    injection.spec_from_file_location('support_audit_envelopes', root/'admitted_regions.py')
                self.load(injection, snapshot)
                with self.assertRaisesRegex(ValueError, 'repeated'):
                    injection.spec_from_file_location('support_audit_envelopes', snapshot/'admitted_regions.py')

    def test_missing_identity_mutation_and_absent_store_instance_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot, digests, report = self.fixture(root)
            with mock.patch.object(audit, 'STORE_SOURCES', digests):
                for value in (None, 'wrong'):
                    report['outputs_sha256']['source/native_prism_case.py'] = value
                    with self.assertRaisesRegex(ValueError, 'approved mixed-store'):
                        audit.HybridImport(root, report)
                report['outputs_sha256']['source/native_prism_case.py'] = digests['native_prism_case.py']
                injection = audit.HybridImport(root, report)
                with self.assertRaisesRegex(ValueError, 'Exactly one'):
                    injection.verify()
                (snapshot/'native_prism_case.py').write_text('# Changed after binding\n')
                with self.assertRaisesRegex(ValueError, 'snapshot changed'):
                    injection.verify()

    def test_sibling_import_from_another_snapshot_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot, digests, report = self.fixture(root)
            foreign = root/'foreign.py'
            foreign.write_text('class EnvelopeStore:\n    def __init__(self,*args): pass\n')
            sys.modules['admitted_regions'] = audit.private_module(foreign, audit.sha(foreign), 'admitted_regions')
            with mock.patch.object(audit, 'STORE_SOURCES', digests):
                injection = audit.HybridImport(root, report)
                with self.assertRaisesRegex(ValueError, 'another snapshot'):
                    self.load(injection, snapshot)

    def test_constructor_cannot_switch_the_part_or_parameters(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot, digests, report = self.fixture(root)
            with mock.patch.object(audit, 'STORE_SOURCES', digests):
                injection = audit.HybridImport(root, report)
                module = self.load(injection, snapshot)
                for args in ((root, report['input_sha256'], report['parameters']),
                             (snapshot, 'another-part', report['parameters']),
                             (snapshot, report['input_sha256'], {})):
                    with self.assertRaisesRegex(ValueError, 'another input'):
                        module.EnvelopeStore(*args)
                module.EnvelopeStore(snapshot, report['input_sha256'], report['parameters'])
                with self.assertRaisesRegex(ValueError, 'another input'):
                    module.EnvelopeStore(snapshot, report['input_sha256'], report['parameters'])

    def test_isolation_composes_with_frozen_rational_and_every_group_checks(self):
        injection = SimpleNamespace(private_importlib=lambda: 'private import namespace')
        module = audit.isolated_anchor_audit(injection)
        legacy = module.previous.legacy_module()
        self.assertEqual(legacy.importlib, 'private import namespace')
        self.assertIsNot(module, audit.anchors)
        self.assertIsNot(module.previous, audit.anchors.previous)
        frozen = complete.frozen_complete_module().frozen_complete_module()
        self.assertIs(frozen.base, audit)
        self.assertTrue(callable(frozen.group_witness))

    def test_base_adapter_stamps_verification_only_after_the_real_private_load(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            snapshot, digests, report = self.fixture(root)
            (root/'report.json').write_text(json.dumps(report))
            output = root/'audit'

            def isolated(injection):
                def measured(*args):
                    loaded = self.load(injection, snapshot)
                    loaded.EnvelopeStore(snapshot, report['input_sha256'], report['parameters'])
                    (output/'source').mkdir(parents=True)
                    return dict(status='passed', rational_part_contact_intersections=True)
                return SimpleNamespace(audit=measured)

            with mock.patch.object(audit, 'STORE_SOURCES', digests), \
                    mock.patch.object(audit, 'isolated_anchor_audit', side_effect=isolated):
                receipt = audit.audit(root, output, 'synthetic.stl')
            self.assertIs(receipt['hybrid_envelope_store_verified'], True)
            self.assertEqual(receipt['hybrid_store_sources_sha256'], digests)
            for name, digest in digests.items():
                self.assertEqual(audit.sha(output/'source'/name), digest)
            self.assertEqual(json.loads((output/'assessment.json').read_text()), receipt)

    def test_base_adapter_cannot_stamp_hybrid_flag_when_the_store_was_not_loaded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            snapshot, digests, report = self.fixture(root)
            (root/'report.json').write_text(json.dumps(report))
            false_audit = SimpleNamespace(audit=lambda *args: dict(status='passed'))
            with mock.patch.object(audit, 'STORE_SOURCES', digests), \
                    mock.patch.object(audit, 'isolated_anchor_audit', return_value=false_audit):
                with self.assertRaisesRegex(ValueError, 'Exactly one'):
                    audit.audit(root, root/'audit', 'synthetic.stl')

    def test_complete_wrapper_requires_both_flags_and_keeps_child_receipt_hash(self):
        for hybrid, rational in ((None, True), (False, True), (True, None), (True, False), (True, True)):
            with tempfile.TemporaryDirectory() as directory:
                output = Path(directory)/'audit'
                def measured(*args):
                    (output/'scanpaths').mkdir(parents=True)
                    (output/'scanpaths/assessment.json').write_text(json.dumps(dict(
                        hybrid_envelope_store_verified=hybrid, rational_part_contact_intersections=rational,
                        part_contact_intermediate_encoding=False, hybrid_store_sources_sha256={})))
                    return dict(status='passed', scanpath_audit_receipt_sha256=audit.sha(output/'scanpaths/assessment.json'))
                module = SimpleNamespace(__file__=str(SOURCE/'audit_complete_supports_exact_anchors.py'), audit=measured)
                with mock.patch.object(complete, 'frozen_complete_module', return_value=module):
                    if hybrid is True and rational is True:
                        receipt = complete.audit(directory, output, 'synthetic.stl')
                        self.assertIs(receipt['hybrid_envelope_store_verified'], True)
                        self.assertEqual(receipt['scanpath_audit_receipt_sha256'], audit.sha(output/'scanpaths/assessment.json'))
                    else:
                        with self.assertRaisesRegex(ValueError, 'mixed store and rational'):
                            complete.audit(directory, output, 'synthetic.stl')


if __name__ == '__main__':
    unittest.main()
