"""Result reuse preserves a failed parent status and rejects mixed or altered inputs."""
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location('carrier_assembly', SCRIPTS / 'assemble_carrier_workflow.py')
assembly = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assembly)


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


class CarrierWorkflowAssemblyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        for module in (assembly, assembly.workflow):
            previous = module.ROOT
            module.ROOT = self.root
            self.addCleanup(setattr, module, 'ROOT', previous)
        script = self.root / 'stage.py'
        script.write_text('from pathlib import Path\nimport sys\np=Path(sys.argv[1]);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b"known data")\n')
        runtime = self.root / 'runtime.json'
        write(runtime, {'python': sys.executable})
        recipe = self.root / 'manufacturing/workflows/fixture.json'
        stages = []
        for stage in assembly.PREFIX:
            name = 'surface/carrier-remeshed.stl' if stage == 'surface' else stage + '/result.txt'
            stages.append({'id': stage, 'argv': ['{python}', '{repo}/stage.py', '{run}/' + name],
                           'timeout_seconds': 5, 'outputs': [name]})
        stages.append({'id': 'process', 'argv': ['{python}', '-c', 'raise SystemExit(3)'],
                       'timeout_seconds': 5, 'outputs': []})
        write(recipe, {'schema': 'porscheparts.part-workflow@1', 'part_id': '993-ENG-CARRIER-0001',
                       'source': {'kind': 'editable_cad', 'units': 'mm'},
                       'inputs_sha256': {'stage.py': assembly.workflow.sha(script)}, 'stages': stages})
        self.source = self.root / 'work/source'
        with self.assertRaisesRegex(ValueError, 'Stage command failed'):
            assembly.workflow.execute(recipe, runtime, self.source)
        self.process, self.audit = self.root / 'work/process', self.root / 'work/audit'
        self.process.mkdir()
        admission = {}
        for key in assembly.guide.ADMISSION_KEYS:
            path = self.process / (key + '.json')
            write(path, {'status': 'passed', 'fixture': key})
            admission[key] = {'status': 'passed', 'receipt': path.name,
                              'receipt_sha256': assembly.workflow.sha(path)}
        self.report = {'status': 'open_build_preparation_completed', 'source_and_runtime_unchanged_at_completion': True,
                       'input_sha256': assembly.workflow.sha(self.source / 'surface/carrier-remeshed.stl'),
                       'n_layers': 2, 'admission': admission, 'manufacturing_preparation_admitted': True,
                       'outputs_sha256': assembly.files(self.process)}
        write(self.process / 'support-stage.json', self.report)
        write(self.process / 'report.json', self.report)
        self.assessment = {'status': 'passed', 'complete_build_audited': True, 'layers_audited': 2,
                           'input_receipt_sha256': assembly.workflow.sha(self.process / 'report.json')}
        write(self.audit / 'assessment.json', self.assessment)
        self.output = self.root / 'work/assembled'

    def assemble(self):
        return assembly.assemble(self.source, self.process, self.audit, self.output)

    def test_failed_later_stage_stays_failed_and_only_verified_prefix_is_imported(self):
        receipt = self.assemble()
        self.assertEqual(receipt['status'], 'artifacts_assembled')
        self.assertEqual(receipt['source_workflow']['status'], 'failed')
        self.assertFalse(receipt['source_workflow']['later_source_stages_imported'])
        self.assertFalse((self.output / 'logs/process.stderr.log').exists())
        self.assertNotIn('stages', receipt)
        self.assertFalse((self.output / 'workflow.json').exists())
        shutil.rmtree(self.source)
        self.assertEqual(assembly.verify(self.output), receipt)

    def test_changed_prefix_file_is_refused_before_output_creation(self):
        (self.source / 'mechanics/result.txt').write_text('altered')
        with self.assertRaisesRegex(ValueError, 'Output changed'):
            self.assemble()
        self.assertFalse(self.output.exists())

    def test_unsuccessful_prefix_is_not_reused(self):
        path = self.source / 'workflow.json'
        receipt = json.loads(path.read_text())
        receipt['stages'][4]['status'] = 'failed'
        write(path, receipt)
        with self.assertRaisesRegex(ValueError, 'twelve declared'):
            self.assemble()
        self.assertFalse(self.output.exists())

    def test_process_for_another_surface_is_refused(self):
        self.report['input_sha256'] = '0' * 64
        write(self.process / 'report.json', self.report)
        with self.assertRaisesRegex(ValueError, 'exact imported surface'):
            self.assemble()
        self.assertFalse(self.output.exists())

    def test_partial_audit_and_unaudited_receipt_are_refused(self):
        for alteration in ({'complete_build_audited': False}, {'input_receipt_sha256': '0' * 64}):
            with self.subTest(alteration=alteration):
                write(self.audit / 'assessment.json', {**self.assessment, **alteration})
                with self.assertRaisesRegex(ValueError, 'audit of every layer'):
                    self.assemble()
                self.assertFalse(self.output.exists())

    def test_symbolic_source_file_is_refused_even_when_contents_match(self):
        path = self.source / 'cad/result.txt'
        twin = self.source / 'identical.txt'
        shutil.copyfile(path, twin)
        path.unlink()
        path.symlink_to(twin)
        with self.assertRaisesRegex(ValueError, 'symbolic links'):
            self.assemble()
        self.assertFalse(self.output.exists())

    def test_altered_copy_is_detected_without_recalculating(self):
        self.assemble()
        (self.output / 'mechanics/result.txt').write_text('tampered')
        with self.assertRaisesRegex(ValueError, 'Assembly output identity'):
            assembly.verify(self.output)


if __name__ == '__main__':
    unittest.main()
