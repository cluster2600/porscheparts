"""Preserve the original runner contract with only the reviewed duration bound."""
import importlib.util
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT/'scripts/run_part_workflow.py'
SOURCE = ROOT/'scripts/run_part_workflow_v2.py'
spec = importlib.util.spec_from_file_location('part_workflow_v2_contract', SOURCE)
workflow = importlib.util.module_from_spec(spec); spec.loader.exec_module(workflow)
baseline_spec = importlib.util.spec_from_file_location('part_workflow_v2_baseline',
    Path(__file__).with_name('test_part_workflow.py'))
baseline = importlib.util.module_from_spec(baseline_spec); baseline_spec.loader.exec_module(baseline)


class PartWorkflowV2Tests(baseline.PartWorkflowTests):
    def setUp(self):
        scoped = patch.object(baseline, 'workflow', workflow)
        scoped.start(); self.addCleanup(scoped.stop)
        super().setUp()

    def test_source_is_only_the_two_duration_substitutions(self):
        original = ORIGINAL.read_bytes()
        self.assertEqual(workflow.sha(ORIGINAL),
            '80d46feac620f95259cc51e26bcbbbe100a63af45c40e82f5c86a06c6ec713b7')
        self.assertEqual(original.count(b'3600'), 2)
        self.assertEqual(SOURCE.read_bytes(), original.replace(b'3600', b'14400'))

    def test_duration_boundaries_and_types_preserve_v1_bool_behavior(self):
        for value in (1,3600,3601,14400,True):
            with self.subTest(accepted=value):
                self.plan['stages'][0]['timeout_seconds'] = value
                workflow.validate(self.plan)
        for value in (0,-1,14401,False,None,'3600',3600.,[],{}):
            with self.subTest(refused=value):
                self.plan['stages'][0]['timeout_seconds'] = value
                with self.assertRaisesRegex(ValueError,'1..14400 seconds'):
                    workflow.validate(self.plan)
        for value in (True,False):
            # The unchanged isinstance(int) rule intentionally still accepts True.
            self.assertEqual(isinstance(value,int) and 1<=value<=14400,
                             isinstance(value,int) and 1<=value<=3600)

    def test_small_real_stage_records_this_v2_runner_sha(self):
        self.plan['stages'][0]['timeout_seconds'] = 3601
        self.save()
        result = workflow.execute(self.recipe,self.runtime,self.root/'duration-v2')
        self.assertEqual(result['runner_sha256'],workflow.sha(SOURCE))
        self.assertNotEqual(result['runner_sha256'],workflow.sha(ORIGINAL))
        self.assertEqual(result['status'],'executed')
        self.assertEqual(result['stages'][0]['returncode'],0)
