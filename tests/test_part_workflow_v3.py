"""Keep the runner2 contracts; extend only the maximum timeout per stage.

The inherited timeout cleanup is unchanged. These tests do not claim the
stronger process-group closure guarantees of the separate diagnostic runner.
"""
import importlib.util
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT/'scripts/run_part_workflow_v2.py'
SOURCE = ROOT/'scripts/run_part_workflow_v3.py'
spec = importlib.util.spec_from_file_location('part_workflow_v3_contract', SOURCE)
workflow = importlib.util.module_from_spec(spec); spec.loader.exec_module(workflow)
fixture_spec = importlib.util.spec_from_file_location('part_workflow_v3_fixtures',
    Path(__file__).with_name('test_part_workflow_v2.py'))
fixtures = importlib.util.module_from_spec(fixture_spec); fixture_spec.loader.exec_module(fixtures)


class PartWorkflowV3Tests(fixtures.baseline.PartWorkflowTests):
    def setUp(self):
        scoped = patch.object(fixtures.baseline, 'workflow', workflow)
        scoped.start(); self.addCleanup(scoped.stop)
        super().setUp()

    def test_source_is_only_the_two_duration_substitutions(self):
        original = ORIGINAL.read_bytes()
        self.assertEqual(workflow.sha(ORIGINAL),
            'caeee30d5768926bc924b5ce253b0fac5a06caa6b552828bcf33a57dd07d3bba')
        self.assertEqual(original.count(b'14400'), 2)
        self.assertEqual(SOURCE.read_bytes(), original.replace(b'14400', b'86400'))

    def test_duration_boundaries_and_types_preserve_v2_bool_behavior(self):
        for value in (1,3600,14400,14401,86399,86400,True):
            with self.subTest(accepted=value):
                self.plan['stages'][0]['timeout_seconds'] = value
                workflow.validate(self.plan)
        for value in (0,-1,86401,False,None,'86400',86400.,[],{}):
            with self.subTest(refused=value):
                self.plan['stages'][0]['timeout_seconds'] = value
                with self.assertRaisesRegex(ValueError,'1..86400 seconds'):
                    workflow.validate(self.plan)
        for value in (True,False):
            self.assertEqual(isinstance(value,int) and 1<=value<=86400,
                             isinstance(value,int) and 1<=value<=14400)

    def test_small_real_stage_records_this_v3_runner_sha(self):
        self.plan['stages'][0]['timeout_seconds'] = 14401
        self.save()
        result = workflow.execute(self.recipe,self.runtime,self.root/'duration-v3')
        self.assertEqual(result['runner_sha256'],workflow.sha(SOURCE))
        self.assertNotEqual(result['runner_sha256'],workflow.sha(ORIGINAL))
        self.assertEqual(result['status'],'executed')
        self.assertEqual(result['stages'][0]['returncode'],0)
