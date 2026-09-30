"""Offline checks for the bounded PicoGK code evaluation boundary."""
import importlib.util
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
