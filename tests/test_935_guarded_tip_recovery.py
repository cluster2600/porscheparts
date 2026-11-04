import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'twins/935-horizontal-cooling-system-f0/source'))
try:
    import numpy as np
    import recover_tip_sections
    from guarded_tip_recovery import guarded_contours, prepare
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


@unittest.skipUnless(AVAILABLE, 'Requires numpy and scipy')
class GuardedTipTests(unittest.TestCase):
    def setUp(self):
        angle = np.arange(24) * (2 * np.pi / 24)
        points = np.column_stack((np.cos(angle), np.sin(angle), np.zeros(24)))
        self.segments = np.stack((points, np.roll(points, -1, axis=0)), axis=1)

    def test_complete_cut_is_accepted(self):
        self.assertEqual(len(guarded_contours(self.segments, 0)), 1)

    def test_closed_cut_with_unrelated_open_arc_is_rejected(self):
        arc = np.array([[[3, 0, 0], [4, 0, 0]]])
        with self.assertRaisesRegex(ValueError, 'omits'):
            guarded_contours(np.concatenate((self.segments, arc)), 0)

    def test_explicit_gap_repair_is_allowed(self):
        contours = guarded_contours(self.segments[:-1], .3)
        self.assertEqual(len(contours[0][1]), 1)

    def test_original_function_restored_after_failure(self):
        original = recover_tip_sections.ordered_contours
        with patch.object(recover_tip_sections, 'prepare', side_effect=ValueError('fail')):
            with self.assertRaisesRegex(ValueError, 'fail'):
                prepare(Path('case'), Path('output'))
        self.assertIs(recover_tip_sections.ordered_contours, original)


if __name__ == '__main__':
    unittest.main()
