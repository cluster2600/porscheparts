import importlib.util
import math
from pathlib import Path
import sys
import unittest


SOURCE = Path(__file__).resolve().parents[1] / 'twins/935-horizontal-cooling-system-f0/source'
sys.path.insert(0, str(SOURCE))
try:
    import numpy  # noqa: F401
except ImportError:
    NUMPY = False
else:
    NUMPY = True
if NUMPY:
    from review_rotor_sweep import between_sample_motion, moving_fixture


@unittest.skipUnless(NUMPY, 'NumPy unavailable')
class RotorSweepTests(unittest.TestCase):
    def test_nearest_phase_motion_bound_and_invalid_inputs(self):
        self.assertAlmostEqual(between_sample_motion(2., 4), 4 * math.sin(math.pi / 8))
        self.assertGreater(between_sample_motion(143.740748109341, 240), 1.88)
        for radius, count in ((0, 4), (float('nan'), 4), (1, 2), (1, True)):
            with self.assertRaises(ValueError):
                between_sample_motion(radius, count)

    @unittest.skipUnless(importlib.util.find_spec('fcl'), 'Optional native FCL unavailable')
    def test_fcl_transform_moves_and_restores_surface(self):
        moving_fixture()
