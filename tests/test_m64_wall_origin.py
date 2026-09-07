import importlib.util
from pathlib import Path
import unittest


SOURCE = Path(__file__).resolve().parents[1] / 'twins/m64-cylinder-head/trace_wall_origin.py'
spec = importlib.util.spec_from_file_location('wall_origin', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class WallOriginTests(unittest.TestCase):
    def test_inherited_interval(self):
        result = module.classify_origin((0., .75), [(-4., -2.), (0., .75)])
        self.assertEqual(result['origin'], 'inherited_envelope')
        self.assertTrue(result['entry_inherited'])
        self.assertTrue(result['exit_inherited'])

    def test_cut_created_end(self):
        result = module.classify_origin((0., .75), [(0., 4.)])
        self.assertEqual(result['origin'], 'candidate_cut_boundary')
        self.assertTrue(result['entry_inherited'])
        self.assertFalse(result['exit_inherited'])

    def test_internal_fragment(self):
        result = module.classify_origin((1., 2.), [(0., 4.)])
        self.assertEqual(result['origin'], 'candidate_cut_boundary')
        self.assertFalse(result['entry_inherited'])
        self.assertFalse(result['exit_inherited'])

    def test_unresolved_is_not_inherited(self):
        for intervals in ([], [(0., .3)], [(0., 2.), (0., 3.)]):
            self.assertEqual(module.classify_origin((0., 1.), intervals)['origin'],
                             'unresolved_envelope_containment')

    def test_bad_interval_rejected(self):
        for pair in ((1., 0.), (1., 1.), (float('nan'), 1.), (0., float('inf'))):
            with self.assertRaises(ValueError):
                module.classify_origin(pair, [(0., 2.)])
        with self.assertRaises(ValueError):
            module.classify_origin((0., 1.), [(0., 2.)], -1)


if __name__ == '__main__':
    unittest.main()
