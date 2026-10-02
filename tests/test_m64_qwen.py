"""Offline checks for the synthetic corpus and model promotion boundary."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

DIRECTORY = Path(__file__).resolve().parents[1] / 'training/m64-qwen'
spec = importlib.util.spec_from_file_location('m64_qwen_dataset', DIRECTORY / 'dataset.py')
dataset = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dataset)
# run.py uses a sibling import, without making MLX a repository test dependency.
spec = importlib.util.spec_from_file_location('m64_qwen_run', DIRECTORY / 'run.py')
runner = importlib.util.module_from_spec(spec)
previous = sys.modules.get('dataset')
sys.modules['dataset'] = dataset
try:
    spec.loader.exec_module(runner)
finally:
    if previous is None:
        del sys.modules['dataset']
    else:
        sys.modules['dataset'] = previous


class M64QwenTests(unittest.TestCase):
    def test_dataset_is_complete_disjoint_and_reproducible(self):
        rows = dataset.examples()
        self.assertEqual(dataset.validate(rows), {'train': 40, 'valid': 10, 'test': 20})
        self.assertEqual(rows, dataset.examples())
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'data'
            manifest = dataset.write_dataset(target)
            for name, expected in manifest['data_hashes'].items():
                self.assertEqual(dataset.digest(target / name), expected)
            with self.assertRaises(FileExistsError):
                dataset.write_dataset(target)
        duplicate = copy.deepcopy(rows)
        duplicate[1] = duplicate[0]
        with self.assertRaises(ValueError):
            dataset.validate(duplicate)
        leakage = copy.deepcopy(rows)
        leakage[-1]['family'] = 'duct'
        with self.assertRaises(ValueError):
            dataset.validate(leakage)
        altered = copy.deepcopy(rows)
        altered[0]['expected']['host'] = 'vast'
        with self.assertRaises(ValueError):
            dataset.validate(altered)

    def test_strict_json_and_promotion(self):
        self.assertFalse(runner.exact_match('{"allowed":0}', {'allowed': False}))
        self.assertFalse(runner.exact_match('{"x":true,"x":false}', {'x': False}))
        self.assertFalse(runner.exact_match('```json\n{}\n```', {}))
        self.assertFalse(runner.exact_match('{"x":NaN}', {'x': None}))
        self.assertTrue(runner.exact_match('{"x":null}', {'x': None}))
        cases = [{'id': str(i), 'task': 'material' if i == 0 else 'route', 'passed': i < 15, 'content_match_ignoring_fence': i < 15}
                 for i in range(20)]
        base = {'cases': cases, 'passed': 15, 'mean_seconds': 1}
        adapter = copy.deepcopy(base)
        self.assertEqual(runner.comparison(base, adapter, 1, .5)['decision'], 'keep_base')
        adapter['cases'][15]['passed'] = True
        adapter['cases'][15]['content_match_ignoring_fence'] = True
        adapter['passed'] = 16
        self.assertEqual(runner.comparison(base, adapter, 1, .5)['decision'], 'candidate_adapter')
        adapter['cases'][0]['passed'] = False
        adapter['cases'][0]['content_match_ignoring_fence'] = False
        self.assertEqual(runner.comparison(base, adapter, 1, .5)['decision'], 'keep_base')
        adapter['cases'][0]['passed'] = True
        adapter['cases'][0]['content_match_ignoring_fence'] = True
        adapter['cases'][1]['content_match_ignoring_fence'] = False
        self.assertEqual(runner.comparison(base, adapter, 1, .5)['decision'], 'keep_base')
        adapter['cases'][1]['content_match_ignoring_fence'] = True
        adapter['mean_seconds'] = 3
        self.assertEqual(runner.comparison(base, adapter, 1, .5)['decision'], 'keep_base')
        adapter['mean_seconds'] = 1
        self.assertEqual(runner.comparison(base, adapter, 1, 2)['decision'], 'keep_base')
        with self.assertRaises(ValueError):
            runner.comparison(base, {'cases': []}, 1, .5)

    def test_chat_end_token_is_registered(self):
        class Tokenizer:
            def __init__(self):
                self.tokens = []
            def add_eos_token(self, token):
                self.tokens.append(token)
        tokenizer = Tokenizer()
        runner.configure_tokenizer(tokenizer)
        self.assertEqual(tokenizer.tokens, ['<|im_end|>'])

    def test_sources_and_model_pin(self):
        config = json.loads((DIRECTORY / 'model.json').read_text())
        self.assertRegex(config['revision'], r'^[a-f0-9]{40}$')
        self.assertRegex(config['weights_sha256'], r'^[a-f0-9]{64}$')
        for name in dataset.SOURCES:
            self.assertTrue((dataset.ROOT / name).is_file(), name)


if __name__ == '__main__':
    unittest.main()
