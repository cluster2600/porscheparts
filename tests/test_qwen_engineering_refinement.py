"""One check of graph identity, SI reference values and the strict qualification gate."""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RefinementTests(unittest.TestCase):
    def test_curriculum_and_qualification(self):
        spec = importlib.util.spec_from_file_location('refinement', ROOT/'training/qwen-engineering-refinement/refine.py')
        refine = importlib.util.module_from_spec(spec); spec.loader.exec_module(refine)
        sys.path.insert(0, str(ROOT/'training/qwen-engineering-20261002'))
        try:
            import curriculum
            registered = refine.module('qwen_registered_runner', ROOT/'training/qwen-engineering-20261002/run.py')
            choose, DOMAINS = registered.choose, registered.DOMAINS
        finally: sys.path.pop(0)
        formulas = {row[0]: row for row in refine.FORMULAS}
        _, expression, values, _ = formulas['goodman_inverse_factor']
        expected = {'values': values, 'expression': expression}
        self.assertTrue(refine.parameterized('result = '+expression, expected, curriculum.calculate))
        self.assertFalse(refine.parameterized('result = 0.45', expected, curriculum.calculate))
        for name, expected in [('axial_stress', 6000000), ('bearing_stress', 15000000), ('cantilever_root_moment', 10),
                               ('conduction_rate', 2720), ('convection_rate', 12.8), ('goodman_inverse_factor', 0.45), ('empirical_bolt_preload', 9375)]:
            _, expression, values, _ = formulas[name]
            self.assertAlmostEqual(curriculum.calculate('result = '+expression, values), expected)
        class Empty:
            @staticmethod
            def candidates(**kwargs): return []
            @staticmethod
            def variant_selection_candidates(): return []
        class Pico:
            SYSTEM = 'synthetic'
            @staticmethod
            def code(beams): return repr(beams)
        rows = refine.additions(Empty, Pico, Empty)
        graphs = [r for r in rows if r['domain'] == 'picogk']
        self.assertEqual(len(graphs), 512)
        def signature(beams):
            return sorted(tuple(sorted((tuple(b[:4]), tuple(b[4:8]))))+tuple(b[8:]) for b in beams)
        for a, b in zip(graphs[::2], graphs[1::2]): self.assertEqual(signature(a['expected']), signature(b['expected']))
        self.assertEqual({s: sum(r['domain'] == 'python' and r['split'] == s for r in rows) for s in ('train', 'valid', 'test')}, {'train': 96, 'valid': 24, 'test': 24})
        before = [{'id': d+str(i), 'domain': d, 'passed': i == 0} for d in DOMAINS for i in range(8)]
        after = [{**r, 'passed': True} for r in before]
        self.assertTrue(refine.qualified(before, after, choose)['near_perfect_bounded_validation'])
        after[-1]['passed'] = False
        self.assertFalse(refine.qualified(before, after, choose)['near_perfect_bounded_validation'])


if __name__ == '__main__': unittest.main()
