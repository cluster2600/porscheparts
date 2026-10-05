"""Offline checks for the bounded PicoGK code evaluation boundary."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1] / 'training' / 'm64-qwen'
# Isolate sibling imports: other repository suites also import modules named run.
def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


dataset = load('picogk_test_dataset', 'dataset.py')
with patch.dict(sys.modules, {'dataset': dataset}):
    runner = load('picogk_test_runner', 'run.py')
    with patch.dict(sys.modules, {'run': runner}):
        picogk = load('m64_picogk', 'picogk.py')
with patch.dict(sys.modules, {'dataset':dataset,'run':runner,'picogk':picogk}):
    improve=load('m64_improve','improve.py')


class PicoGKTrainingTests(unittest.TestCase):
    def test_corpus_and_execution_boundary(self):
        rows = picogk.corpus()
        self.assertEqual(len(rows), 88)
        self.assertEqual(sum(r['split'] == 'test' for r in rows), 16)
        train_shapes = {r['shape'] for r in rows if r['split'] == 'train'}
        for row in rows:
            expected = row['expected']
            text = picogk.code(expected)
            self.assertEqual(picogk.signature(picogk.parse(text)[1]), picogk.signature(expected))
            if row['group'] == 'composition_holdout':
                self.assertNotIn(row['shape'], train_shapes)
        text = picogk.code(rows[0]['expected'])
        for attack in ('System.IO.File.Delete("x");', text + '\nwhile(true) {}',
                       text.replace('1f,', '1000f,'), text.replace('-5f', 'float.NaN'),
                       text + '\n#error injected', text * 7):
            with self.assertRaises(ValueError):
                picogk.parse(attack)
        altered = [list(b) for b in rows[0]['expected']]
        altered[0][3] *= 2
        self.assertNotEqual(picogk.signature(altered), picogk.signature(rows[0]['expected']))
        b = rows[0]['expected'][0]
        reversed_beam = b[4:8] + b[:4] + [b[8]]
        self.assertEqual(picogk.signature([b]), picogk.signature([reversed_beam]))

    def test_expanded_graph_instances(self):
        rows=picogk.expanded_corpus()
        self.assertEqual(rows,picogk.expanded_corpus())
        self.assertEqual([sum(r['split']==s for r in rows) for s in ('train','valid','test')],[128,16,16])
        all_rows=rows+picogk.corpus()
        self.assertEqual(len({r['messages'][1]['content'] for r in all_rows}),len(all_rows))
        for r in rows:
            self.assertEqual(picogk.signature(picogk.parse(r['messages'][-1]['content'])[1]),picogk.signature(r['expected']))

    def test_validation_selection(self):
        def result(usd,pico):
            return {'usd':[{'id':'u','passed':usd}],'picogk':[{'id':'p','passed':pico}]}
        before=result(False,True)
        self.assertIsNone(improve.select(before,{400:result(True,False),800:before}))
        self.assertEqual(improve.select(before,{400:result(True,True),800:result(True,True)}),400)
        with self.assertRaises(ValueError):improve.select(before,{400:{'usd':[],'picogk':before['picogk']}})
        self.assertEqual(improve.select(result(True,False),{800:result(True,True)},True),800)
        self.assertIsNone(improve.select(result(True,False),{800:result(False,True)},True))

    def test_focused_curriculum_is_disjoint(self):
        fresh=picogk.expanded_corpus(3)
        self.assertEqual([sum(r['split']==s for r in fresh) for s in ('train','valid','test')],[512,16,24])
        rows=picogk.corpus()+picogk.expanded_corpus()+fresh
        self.assertEqual(len({r['messages'][1]['content'] for r in rows}),len(rows))
        for row in fresh:
            self.assertEqual(picogk.signature(picogk.parse(row['messages'][-1]['content'])[1]),picogk.signature(row['expected']))

    def test_replay_changes_training_only(self):
        usd=[{'id':'usd-'+s,'split':s} for s in ('train','valid','test')]
        pico=[{'id':'train-original','split':'train'},{'id':'pico3-train-000','split':'train'},
              {'id':'valid-original','split':'valid'},{'id':'test-original','split':'test'}]
        rows=improve.split_rows(usd,pico,'train',2,4)
        self.assertEqual([r['id'] for r in rows].count('usd-train'),4)
        self.assertEqual([r['id'] for r in rows].count('train-original'),2)
        self.assertEqual([r['id'] for r in rows].count('pico3-train-000'),1)
        self.assertTrue(all(r['split']=='train' for r in rows))
        for split in ('valid','test'):
            self.assertEqual(improve.split_rows(usd,pico,split,16,16),
                             [r for r in usd+pico if r['split']==split])

    def test_retention_report_keeps_experiment_identity_and_case_counts(self):
        latest=json.loads((HERE/'retention-results.json').read_text())
        for report,name,step,counts in ((latest,'coding-006',800,(19,7)),
                (latest['previous_attempt'],'coding-005',600,(16,25))):
            self.assertEqual(report['experiment'],'m64-qwen-'+name)
            self.assertEqual(report['candidate_adapter_path'],f'work/m64-qwen/{name}/checkpoint-{step}')
            self.assertIsNone(report['selected_step'])
            self.assertFalse(report['final_tests_evaluated'])
            for domain,expected in zip(('usd','picogk'),counts):
                rows=report['validation_cases'][domain];score=report['validation_summary'][domain]
                self.assertEqual(score['total'],len({r['id'] for r in rows}))
                self.assertEqual(score['after_passed'],expected)
                self.assertEqual(score['after_passed'],sum(r['after_passed'] for r in rows))
                self.assertEqual(score['regressions'],[r['id'] for r in rows if r['before_passed'] and not r['after_passed']])
