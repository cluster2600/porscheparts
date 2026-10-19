"""A recipe preserves sources, keeps failed logs and detects changed artifacts."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'scripts/run_part_workflow.py'
spec = importlib.util.spec_from_file_location('part_workflow', SOURCE)
workflow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workflow)


class PartWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        previous = workflow.ROOT
        workflow.ROOT = self.root
        self.addCleanup(setattr, workflow, 'ROOT', previous)
        folder = self.root / 'manufacturing/workflows'
        folder.mkdir(parents=True)
        self.recipe = folder / 'fixture.json'
        self.runtime = self.root / 'runtime.json'
        self.runtime.write_text(json.dumps({'python': sys.executable}))
        (self.root / 'source.txt').write_text('unchanged input')
        self.script = self.root / 'stage.py'
        self.script.write_text('from pathlib import Path\nimport sys\nPath(sys.argv[1]).write_text("known output")\n')
        self.plan = {'schema': 'porscheparts.part-workflow@1', 'part_id': 'FIXTURE',
                     'source': {'kind': 'measurements', 'units': 'mm'},
                     'inputs_sha256': {p.name: workflow.sha(p) for p in (self.script, self.root / 'source.txt')},
                     'stages': [{'id': 'geometry', 'argv': ['{python}', '{repo}/stage.py', '{run}/part.txt'],
                                 'timeout_seconds': 10, 'outputs': ['part.txt']}]}
        self.save()

    def save(self):
        self.recipe.write_text(json.dumps(self.plan))

    def test_success_is_execution_not_engineering_acceptance_and_detects_changed_output(self):
        output = self.root / 'run'
        result = workflow.execute(self.recipe, self.runtime, output)
        self.assertEqual(result['status'], 'executed')
        self.assertNotIn('manufacturing_authorized', result)
        with self.assertRaises(FileExistsError):
            workflow.execute(self.recipe, self.runtime, output)
        (output / 'part.txt').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'Output changed'):
            workflow.verify(output)

    def test_input_and_output_path_guards_precede_execution(self):
        for change in ('source', 'escape'):
            with self.subTest(change=change):
                plan = json.loads(self.recipe.read_text())
                if change == 'source':
                    plan['inputs_sha256']['source.txt'] = '0' * 64
                else:
                    plan['stages'][0]['outputs'] = ['../outside.txt']
                self.recipe.write_text(json.dumps(plan))
                output = self.root / ('run-' + change)
                with self.assertRaises(ValueError):
                    workflow.execute(self.recipe, self.runtime, output)
                self.assertFalse(output.exists())
                self.save()

    def test_failed_stage_retains_logs_and_stops_the_chain(self):
        self.script.write_text('import sys\nprint("diagnostic")\nsys.exit(3)\n')
        self.plan['inputs_sha256']['stage.py'] = workflow.sha(self.script)
        self.plan['stages'].append({**self.plan['stages'][0], 'id': 'later'})
        self.save()
        output = self.root / 'failed'
        with self.assertRaisesRegex(ValueError, 'Stage command failed'):
            workflow.execute(self.recipe, self.runtime, output)
        result = json.loads((output / 'workflow.json').read_text())
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(len(result['stages']), 1)
        self.assertIn('diagnostic', (output / 'logs/geometry.stdout.log').read_text())
        self.assertEqual(workflow.verify(output)['status'], 'failed')
        (output / 'logs/geometry.stdout.log').write_text('overwritten diagnostic')
        with self.assertRaisesRegex(ValueError, 'Output changed'):
            workflow.verify(output)

    def test_missing_runtime_is_refused_without_partial_output(self):
        self.runtime.write_text('{}')
        output = self.root / 'missing-runtime'
        with self.assertRaises(KeyError):
            workflow.execute(self.recipe, self.runtime, output)
        self.assertFalse(output.exists())

    def test_directory_outputs_detect_changed_packaged_files(self):
        self.script.write_text('from pathlib import Path\nimport sys\np=Path(sys.argv[1]);p.mkdir();(p/"layer.npz").write_bytes(b"known vectors")\n')
        self.plan['inputs_sha256']['stage.py'] = workflow.sha(self.script)
        self.plan['stages'][0]['argv'][-1] = '{run}/layers'
        self.plan['stages'][0]['outputs'] = ['layers']
        self.save()
        output = self.root / 'directory-output'
        result = workflow.execute(self.recipe, self.runtime, output)
        self.assertEqual(result['stages'][0]['output_types']['layers'], 'directory')
        (output / 'layers/layer.npz').write_bytes(b'changed vectors')
        with self.assertRaisesRegex(ValueError, 'Output changed'):
            workflow.verify(output)

    def test_deadline_allows_the_owned_stage_to_clean_up(self):
        self.script.write_text('import signal,time,sys\nfrom pathlib import Path\ndef cancel(signum,frame): raise InterruptedError("cancelled")\nsignal.signal(signal.SIGTERM,cancel)\ntry: time.sleep(20)\nfinally: Path(sys.argv[1]).write_text("owned resources removed")\n')
        self.plan['inputs_sha256']['stage.py'] = workflow.sha(self.script)
        self.plan['stages'][0]['timeout_seconds'] = 1
        self.save()
        output = self.root / 'deadline'
        with self.assertRaises(TimeoutError):
            workflow.execute(self.recipe, self.runtime, output)
        self.assertEqual((output / 'part.txt').read_text(), 'owned resources removed')
        self.assertEqual(json.loads((output / 'workflow.json').read_text())['status'], 'failed')


if __name__ == '__main__':
    unittest.main()
