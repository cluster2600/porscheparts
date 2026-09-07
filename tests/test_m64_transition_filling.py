import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / 'twins/m64-cylinder-head/trial_transition_filling.py'
spec = importlib.util.spec_from_file_location('transition_filling', PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TransitionFillingTests(unittest.TestCase):
    def test_same_algorithm_pairs(self):
        old = [{'probe_private':i, 'status':'resolved', 'ray_scan_units':1.} for i in range(3)]
        new = [{**r, 'ray_scan_units':v} for r,v in zip(old, (1.,2.,.5))]
        self.assertEqual(module.compare_fixed_rays(old,new),
                         {'unchanged_within_tolerance':1,'increased':1,'decreased':1})

    def test_resolution_is_not_gain(self):
        old = [{'probe_private':1,'status':'unresolved'}]
        new = [{'probe_private':1,'status':'resolved','ray_scan_units':2.}]
        self.assertEqual(module.compare_fixed_rays(old,new), {'not_paired_resolved':1})

    def test_identity_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            module.compare_fixed_rays([{'probe_private':1}], [{'probe_private':2}])

    def test_non_finite_or_invalid_resolved_length_rejected(self):
        old = [{'probe_private':1, 'status':'resolved', 'ray_scan_units':1.}]
        for length in (float('nan'), float('inf'), -1., 0., True, None):
            with self.subTest(length=length), self.assertRaises(ValueError):
                module.compare_fixed_rays(old, [{**old[0], 'ray_scan_units':length}])

    def test_invalid_tolerance_rejected(self):
        for tolerance in (float('nan'), float('inf'), -1., 0., True):
            with self.subTest(tolerance=tolerance), self.assertRaises(ValueError):
                module.compare_fixed_rays([], [], tolerance=tolerance)

    def test_unknown_status_rejected(self):
        with self.assertRaises(ValueError):
            module.compare_fixed_rays([{'probe_private':1,'status':'failed'}], [])


if __name__ == '__main__':
    unittest.main()
