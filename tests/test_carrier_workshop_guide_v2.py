"""A generated file is insufficient when support admission or the complete path audit is absent."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location('carrier_guide_v2', SCRIPTS / 'build_carrier_workshop_guide_v2.py')
guide = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guide)


class CarrierWorkshopGuideV2Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.run = Path(self.temp.name).resolve()
        self.process_dir = self.run / 'process'
        self.process_dir.mkdir()
        self.admission = {}
        for key in guide.ADMISSION_KEYS:
            path = self.process_dir / (key + '.json')
            path.write_text(json.dumps({'status': 'passed', 'witness': key}))
            self.admission[key] = {'status': 'passed', 'receipt': path.name, 'receipt_sha256': guide.sha(path)}
        self.process = {'input_sha256': 'a' * 64, 'n_layers': 2, 'admission': self.admission,
                        'manufacturing_preparation_admitted': True}
        self.write_process()

    def write_process(self):
        (self.process_dir / 'support-stage.json').write_text(json.dumps(self.process))
        (self.process_dir / 'report.json').write_text(json.dumps(self.process))

    def write_scan_audit(self, complete=True):
        path = self.run / 'scanpath-audit'
        path.mkdir(exist_ok=True)
        self.audit = {'status': 'passed', 'complete_build_audited': complete, 'layers_audited': 2,
                      'input_receipt_sha256': guide.sha(self.process_dir / 'report.json')}
        (path / 'assessment.json').write_text(json.dumps(self.audit))

    def test_six_matching_hashed_admissions_are_required(self):
        self.assertEqual(guide.admitted_process(self.process_dir, self.process), self.admission)
        self.process['admission']['collisions']['status'] = 'not_run'
        self.write_process()
        with self.assertRaisesRegex(ValueError, 'Unpassed support admission'):
            guide.admitted_process(self.process_dir, self.process)

    def test_old_generation_without_admission_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'admission criteria'):
            guide.admitted_process(self.process_dir, {'status': 'open_build_preparation_completed'})

    def test_changed_receipt_is_refused(self):
        (self.process_dir / 'contacts.json').write_text('changed after checking')
        with self.assertRaisesRegex(ValueError, 'receipt identity mismatch'):
            guide.admitted_process(self.process_dir, self.process)

    def test_receipt_cannot_escape_the_process_directory(self):
        outside = self.run / 'outside.json'
        outside.write_text('{"status":"passed"}')
        self.admission['skins'].update(receipt='../outside.json', receipt_sha256=guide.sha(outside))
        self.write_process()
        with self.assertRaisesRegex(ValueError, 'receipt identity mismatch'):
            guide.admitted_process(self.process_dir, self.process)

    def test_partial_path_audit_is_refused(self):
        self.write_scan_audit(complete=False)
        with self.assertRaisesRegex(ValueError, 'Complete scanpath audit'):
            guide.admitted_scanpaths(self.run, self.process)

    def test_audit_of_another_process_revision_is_refused(self):
        self.write_scan_audit()
        self.assertEqual(guide.admitted_scanpaths(self.run, self.process), self.audit)
        (self.process_dir / 'report.json').write_text('another build revision')
        with self.assertRaisesRegex(ValueError, 'Complete scanpath audit'):
            guide.admitted_scanpaths(self.run, self.process)

    def support_audit(self, **changes):
        data = {'status': 'passed', 'complete_build_audited': True, 'layers_audited': 2,
                'input_receipt_sha256': guide.sha(self.process_dir / 'report.json'),
                'support_scanpaths_audited': True, 'geometric_confinement_passed': True,
                'exposure_connectivity_passed': True, 'every_material_group_exposed': True}
        folder = self.run / 'support-scanpath-audit'
        folder.mkdir(exist_ok=True)
        (folder / 'scanpaths').mkdir(exist_ok=True)
        for name, field in (('scanpaths/assessment.json', 'scanpath_audit_receipt_sha256'),
                            ('group-exposure-coverage.json', 'group_coverage_receipt_sha256')):
            (folder / name).write_text(json.dumps(data))
            data[field] = guide.sha(folder / name)
        data.update(changes)
        (folder / 'assessment.json').write_text(json.dumps(data))
        return data

    def test_all_support_paths_and_exposure_contacts_are_required(self):
        data = self.support_audit()
        self.assertEqual(guide.admitted_support_scanpaths(self.run, self.process), data)
        for key in ('complete_build_audited', 'geometric_confinement_passed', 'exposure_connectivity_passed',
                    'every_material_group_exposed'):
            self.support_audit(**{key: False})
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'Complete support path'):
                guide.admitted_support_scanpaths(self.run, self.process)

    def test_support_audit_of_another_receipt_is_refused(self):
        self.support_audit(input_receipt_sha256='0' * 64)
        with self.assertRaisesRegex(ValueError, 'Complete support path'):
            guide.admitted_support_scanpaths(self.run, self.process)

    def test_changed_group_or_scanpath_subreceipt_is_refused(self):
        for name in ('scanpaths/assessment.json', 'group-exposure-coverage.json'):
            self.support_audit()
            (self.run / 'support-scanpath-audit' / name).write_text('{"status":"passed"}')
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'receipt identity'):
                guide.admitted_support_scanpaths(self.run, self.process)


if __name__ == '__main__':
    unittest.main()
