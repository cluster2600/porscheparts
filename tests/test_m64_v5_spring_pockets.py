"""Pure bounds and stack checks; these do not execute or qualify private CAD."""
import importlib.util
import math
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parents[1] / 'twins/m64-cylinder-head/source/wholebody'
sys.path.insert(0, str(HERE))
SPEC = importlib.util.spec_from_file_location('v5_spring_pockets', HERE / 'build_spring_pockets.py')
pockets = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pockets)


class SpringPocketTests(unittest.TestCase):
    def test_fixed_design_stack(self):
        for lift, bind in ((11.5, 6.2), (9.6, 8.1)):
            result = pockets.design_stack(lift)
            self.assertAlmostEqual(result['seat_axial'], 59.6)
            self.assertAlmostEqual(result['retainer_closed_axial'], 100.)
            self.assertAlmostEqual(result['stem_tip_axial_hypothesis'], 105.)
            self.assertAlmostEqual(result['stem_extension_from_V2'], 23.)
            self.assertAlmostEqual(result['bind_reserve'], bind)
            self.assertGreater(pockets.TOP, result['retainer_closed_axial'])
        self.assertEqual((pockets.OUTER_DIAMETER, pockets.INNER_DIAMETER), (32., 14.))

    def test_port_gate_requires_every_geometric_criterion(self):
        self.assertTrue(pockets.port_gate(0, 0., 3.))
        for values in ((1, 0., 4.), (0, 1., 4.), (0, 0., 2.999), (0, -1., 4.),
                       (0, math.nan, 4.), (0, math.inf, 4.), (0, 0., math.inf),
                       (0, 0., math.nan), (False, 0., 4.), (0, False, 4.), (0, 0., True)):
            with self.subTest(values=values):
                self.assertFalse(pockets.port_gate(*values))

    def test_zero_common_never_accepts_a_solid(self):
        self.assertTrue(pockets.zero_common(0, 0.))
        self.assertFalse(pockets.zero_common(1, 1e-10))
        self.assertFalse(pockets.zero_common(0, 1.1e-7))


if __name__ == '__main__':
    unittest.main()
