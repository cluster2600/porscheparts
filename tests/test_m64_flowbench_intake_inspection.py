import importlib.util
import math
from pathlib import Path
import unittest


PATH = Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/flowbench-intake/inspect_pilot.py'
spec = importlib.util.spec_from_file_location('m64_flowbench_inspection', PATH)
inspection = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inspection)


class PilotInspectionTests(unittest.TestCase):
    def test_nominal_overlap_not_entire_fluid_domain(self):
        value = inspection.axial_probe(17.8,5.99,6.)
        self.assertAlmostEqual(value['length'],.01)
        self.assertAlmostEqual(value['cylinder_volume'],math.pi*17.8**2*.01)

    def test_lift_is_along_inclined_valve_axis(self):
        vector = inspection.lift_translation(-8.,6.)
        self.assertGreater(vector[0],0.)
        self.assertLess(vector[2],0.)
        self.assertAlmostEqual(math.sqrt(sum(x*x for x in vector)),6.)
        self.assertEqual(inspection.lift_translation(0.,0.),[0.,0.,0.])

    def test_reject_gap_or_invalid_probe(self):
        for values in [(17.8,6.,6.),(17.8,6.1,6.),(-1.,5.99,6.),(math.nan,0.,1.)]:
            with self.assertRaises(ValueError):
                inspection.axial_probe(*values)
        for angle,lift in [(8.,-1.),(math.nan,6.),(8.,math.inf)]:
            with self.assertRaises(ValueError):
                inspection.lift_translation(angle,lift)


if __name__ == '__main__':
    unittest.main()
