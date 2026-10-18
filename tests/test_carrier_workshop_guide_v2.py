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

    def test_visual_workflow_snapshot_survives_the_runner_final_update(self):
        source, destination = self.run / 'workflow.json', self.run / 'snapshot.json'
        source.write_text('{"status":"running","stages":["verified prefix"]}')
        expected = guide.sha(source)
        guide.snapshot_workflow(source, destination, expected)
        source.write_text('{"status":"completed","stages":["verified prefix","guide"]}')
        self.assertEqual(guide.sha(destination), expected)
        self.assertNotEqual(guide.sha(source), expected)
        with self.assertRaises(FileExistsError):
            guide.snapshot_workflow(destination, destination, expected)

    def test_changed_visual_workflow_cannot_be_copied_under_the_old_identity(self):
        source, destination = self.run / 'workflow.json', self.run / 'snapshot.json'
        source.write_text('{"stages":["verified prefix"]}')
        expected = guide.sha(source)
        source.write_text('{"stages":["different prefix"]}')
        with self.assertRaisesRegex(ValueError, 'Visual workflow changed'):
            guide.snapshot_workflow(source, destination, expected)
        self.assertFalse(destination.exists())

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
                'exposure_connectivity_passed': True, 'every_material_group_exposed': True,
                'rational_part_contact_intersections': True, 'hybrid_envelope_store_verified': True}
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

    def test_legacy_contact_or_store_pass_is_refused_at_both_receipt_levels(self):
        for field in ('rational_part_contact_intersections', 'hybrid_envelope_store_verified'):
            for target in ('assessment.json', 'scanpaths/assessment.json'):
                for value in (None, False):
                    self.support_audit()
                    folder = self.run / 'support-scanpath-audit'
                    path = folder / target
                    data = json.loads(path.read_text())
                    data.pop(field)
                    if value is not None:
                        data[field] = value
                    path.write_text(json.dumps(data))
                    if target.startswith('scanpaths/'):
                        summary = json.loads((folder / 'assessment.json').read_text())
                        summary['scanpath_audit_receipt_sha256'] = guide.sha(path)
                        (folder / 'assessment.json').write_text(json.dumps(summary))
                    with self.subTest(field=field, target=target, value=value), self.assertRaisesRegex(ValueError, 'Complete support path'):
                        guide.admitted_support_scanpaths(self.run, self.process)

    def test_changed_group_or_scanpath_subreceipt_is_refused(self):
        for name in ('scanpaths/assessment.json', 'group-exposure-coverage.json'):
            self.support_audit()
            (self.run / 'support-scanpath-audit' / name).write_text('{"status":"passed"}')
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'receipt identity'):
                guide.admitted_support_scanpaths(self.run, self.process)

    def visual_fixture(self):
        def write(name, contents):
            path = self.run / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(contents)
            return path
        write('cad/study.json', '{"geometry":"known study"}')
        for name in ('mesh.inp', 'mesh.npz', 'combined-rigid-static.inp',
                     'combined-rigid-static.npz', 'combined-rigid-static.json'):
            write('cad/mesh-7/' + name, 'known retained ' + name)
        drawing = {'STL_sha256': 'a' * 64, 'study_sha256': guide.sha(self.run / 'cad/study.json')}
        write('dimensions/drawing.json', json.dumps(drawing))
        fields = {'case': 'combined-rigid-static'}
        for key, name in (('mesh_sha256', 'mesh.inp'), ('mesh_npz_sha256', 'mesh.npz'),
                          ('solver_deck_sha256', 'combined-rigid-static.inp'),
                          ('result_npz_sha256', 'combined-rigid-static.npz'),
                          ('result_record_sha256', 'combined-rigid-static.json')):
            fields[key] = guide.sha(self.run / 'cad/mesh-7' / name)
        write('fields/combined.json', json.dumps(fields))
        stages = []
        for identity, names in (
                ('dimensions', ('dimensions/carrier-dimensions.png', 'dimensions/drawing.json')),
                ('surface-figure', ('surface-figure/carrier-remesh-comparison.png',)),
                ('fields', ('fields/combined.png', 'fields/combined.json'))):
            for name in names:
                if name.endswith('.png'):
                    write(name, 'known rendered pixels ' + name)
            stages.append({'id': identity, 'status': 'executed', 'returncode': 0,
                           'outputs_sha256': {name: guide.sha(self.run / name) for name in names}})
        write('workflow.json', json.dumps({'stages': stages}))
        write('process/support-000.npz', 'known complete support')
        write('process/layers/layer-00001.npz', 'known audited layer')
        write('process/layers.csv', 'layer,part_area_mm2\n0,0\n1,4\n')
        self.process.update(supports=[{'index': 0}], outputs_sha256={
            'layers/layer-00001.npz': guide.sha(self.run / 'process/layers/layer-00001.npz')})
        self.write_process()
        images = {}
        for name in ('build-supports.png', 'support-teeth.png', 'layer-contours-hatches.png'):
            images[name] = guide.sha(write('process/' + name, 'known final image ' + name))
        self.figures = {'partial_witness': False, 'input_receipt_sha256': guide.sha(self.process_dir / 'report.json'),
                        'render_source_sha256': guide.sha(guide.PROCESS_RENDERER), 'images_sha256': images,
                        'layer_index': 1}
        self.write_figures()

    def write_figures(self):
        (self.process_dir / 'figures.json').write_text(json.dumps(self.figures))

    def test_all_visuals_bind_to_recorded_prefix_and_complete_audited_process(self):
        self.visual_fixture()
        result = guide.admitted_visuals(self.run, self.process, 'a' * 64)
        self.assertEqual(result['layer_index'], 1)
        self.assertEqual(len(result['images_sha256']), 6)

    def test_old_or_partial_support_figures_are_refused(self):
        self.visual_fixture()
        old_renderer = guide.ROOT / 'parts/993-eng-carrier-0001/source/process-coverage-20261016/render_pyslm.py'
        for key, value in [('input_receipt_sha256', '0' * 64), ('partial_witness', True),
                           ('render_source_sha256', guide.sha(old_renderer))]:
            original = self.figures[key]
            self.figures[key] = value
            self.write_figures()
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'same-process'):
                guide.admitted_visuals(self.run, self.process, 'a' * 64)
            self.figures[key] = original

    def test_replaced_support_image_is_refused_even_with_matching_report(self):
        self.visual_fixture()
        (self.process_dir / 'build-supports.png').write_text('old rejected support image')
        with self.assertRaisesRegex(ValueError, 'differs from its same-process'):
            guide.admitted_visuals(self.run, self.process, 'a' * 64)

    def test_mechanical_figure_cannot_borrow_another_result(self):
        self.visual_fixture()
        (self.run / 'cad/mesh-7/combined-rigid-static.npz').write_text('another mechanical result')
        with self.assertRaisesRegex(ValueError, 'another retained result'):
            guide.admitted_visuals(self.run, self.process, 'a' * 64)

    def test_unreported_surface_cannot_appear_in_the_support_scene(self):
        self.visual_fixture()
        (self.process_dir / 'support-999.npz').write_text('unreported stale support')
        with self.assertRaisesRegex(ValueError, 'unreported support surfaces'):
            guide.admitted_visuals(self.run, self.process, 'a' * 64)

    def test_layer_image_must_use_a_retained_nonempty_audited_layer(self):
        self.visual_fixture()
        self.figures['layer_index'] = self.process['n_layers']
        self.write_figures()
        with self.assertRaisesRegex(ValueError, 'actual audited layer'):
            guide.admitted_visuals(self.run, self.process, 'a' * 64)

    def test_assembled_visuals_require_the_recorded_source_workflow_identity(self):
        self.visual_fixture()
        provenance = self.run / 'provenance'
        provenance.mkdir()
        (provenance / 'source-workflow.json').write_bytes((self.run / 'workflow.json').read_bytes())
        (self.run / 'assembly.json').write_text(json.dumps({'source_workflow': {'sha256': '0' * 64}}))
        with self.assertRaisesRegex(ValueError, 'verified assembly'):
            guide.admitted_visuals(self.run, self.process, 'a' * 64)


if __name__ == '__main__':
    unittest.main()
