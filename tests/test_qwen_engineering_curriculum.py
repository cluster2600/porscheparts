"""Check arithmetic isolation, split provenance and the unchanged retention gate."""
import importlib.util
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parents[1]/'training/qwen-engineering-20261002'
spec = importlib.util.spec_from_file_location('wide_curriculum', HERE/'curriculum.py')
curriculum = importlib.util.module_from_spec(spec); spec.loader.exec_module(curriculum)
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location('wide_runner', HERE/'run.py')
runner = importlib.util.module_from_spec(spec); spec.loader.exec_module(runner)
sys.path.remove(str(HERE))


class EngineeringCurriculumTests(unittest.TestCase):
    def test_units_and_untrusted_code(self):
        self.assertEqual(curriculum.calculate('result = speed * length / viscosity', {'speed': 2, 'length': 0.1, 'viscosity': 1e-5}), 20000)
        self.assertEqual(curriculum.calculate('result = target * cell / speed', {'target': 0.5, 'cell': 0.001, 'speed': 2}), 0.00025)
        for source in ('result = __import__("os").system("true")', 'import os\nresult = 1', 'result = x.real', 'result = [x for x in range(100)]', 'other = 1', 'result = 2**10000'):
            with self.assertRaises(ValueError): curriculum.calculate(source, {'x': 1})

    def test_disjoint_fixture_families(self):
        class Pico:
            SYSTEM = 'literal graph'
            @staticmethod
            def code(beams): return repr(beams)
        class USD: SYSTEM = 'bounded USD'
        rows = curriculum.cases(USD, Pico)
        self.assertEqual(curriculum.validate(rows), {'train': 384, 'valid': 32, 'test': 32})
        families = [set(curriculum.FAMILIES[s]) for s in ('train', 'valid', 'test')]
        self.assertFalse(families[0] & families[1] or families[0] & families[2] or families[1] & families[2])
        rows[-1]['family'] = 'duct'
        with self.assertRaises(ValueError): curriculum.validate(rows)

    def test_more_passes_cannot_hide_a_regression(self):
        before = [{'id': d+str(i), 'domain': d, 'passed': i == 0} for d in runner.DOMAINS for i in range(8)]
        after = [{**r, 'passed': True} for r in before]
        self.assertTrue(runner.choose(before, after)['candidate_eligible_for_fresh_tests'])
        after[0]['passed'] = False
        self.assertFalse(runner.choose(before, after)['candidate_eligible_for_fresh_tests'])


if __name__ == '__main__': unittest.main()
