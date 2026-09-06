import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'twins/reference-917-engine/source/thicken_scan_fins_f54.py'
spec = importlib.util.spec_from_file_location('fin_thickening_f54', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FinThickeningTests(unittest.TestCase):
    def profiles(self):
        return [{'z': z, 'kind': kind, 'points_xy': [[0, 0], [2, 0], [1, 1]]}
                for z, kind in [(0, 'core'), (2, 'fin_lower'),
                                (3.5, 'fin_upper'), (6, 'core')]]

    def test_only_paired_heights_change_without_mutating_input(self):
        source = self.profiles()
        result, count = module.thicken(source, 2.)
        self.assertEqual(count, 1)
        self.assertEqual([p['z'] for p in result], [0, 1.75, 3.75, 6])
        self.assertEqual(source, self.profiles())
        self.assertEqual([p['points_xy'] for p in result], [p['points_xy'] for p in source])

    def test_nonfinite_reduction_and_overlap_are_rejected(self):
        for target in (float('nan'), float('inf'), 1.5, 1., 20.):
            with self.subTest(target=target), self.assertRaises(ValueError):
                module.thicken(self.profiles(), target)

    def test_incomplete_pair_and_unexpected_spacing_are_rejected(self):
        for profiles in (self.profiles()[:2], self.profiles()):
            if len(profiles) == 4:
                profiles[2]['z'] = 3.6
            with self.assertRaises(ValueError):
                module.thicken(profiles, 2.)


if __name__ == '__main__':
    unittest.main()
