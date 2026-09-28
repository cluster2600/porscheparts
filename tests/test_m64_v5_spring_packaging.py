"""Nominal spring-stack arithmetic and fail-closed clearance verdicts, no private CAD."""
import importlib.util
import math
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parents[1] / 'twins/m64-cylinder-head/source/wholebody'
sys.path.insert(0, str(HERE))
SPEC = importlib.util.spec_from_file_location('v5_spring_packaging', HERE / 'spring_packaging.py')
packaging = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(packaging)


class SpringPackagingTests(unittest.TestCase):
    def test_stack_and_unsupported_inputs(self):
        for lift, compressed, bind, guide in ((11.5, 28.9, 6.2, 10.5), (9.6, 30.8, 8.1, 12.4)):
            result = packaging.stack(40.4, 22.7, lift)
            self.assertAlmostEqual(result['seat_axial'], 36.6)
            self.assertAlmostEqual(result['compressed_height'], compressed)
            self.assertAlmostEqual(result['bind_reserve'], bind)
            self.assertAlmostEqual(result['retainer_to_guide_at_full_lift'], guide)
        # A changed keeper allowance must actually change the package and its margin.
        self.assertAlmostEqual(packaging.stack(40.4, 22.7, 11.5, tip_allowance=7.)['retainer_to_guide_at_full_lift'], 8.5)
        for value in (0., -1., math.nan, math.inf, True, 50.):
            with self.subTest(value=value), self.assertRaises(ValueError):
                packaging.stack(40.4, 22.7, 11.5, tip_allowance=value)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'section.svg'
            packaging.diagram(path, [], 7.)
            self.assertIn('7 mm supposé', path.read_text())
            ET.parse(path)

    def test_contact_and_intersection_are_not_clearance(self):
        self.assertFalse(packaging.envelope_clear(100., 0.))
        self.assertFalse(packaging.envelope_clear(0., 0.))
        self.assertFalse(packaging.envelope_clear(0., math.nan))
        self.assertFalse(packaging.envelope_clear(-1., .1))
        self.assertFalse(packaging.envelope_clear(0., math.inf))
        self.assertTrue(packaging.envelope_clear(0., .1))


if __name__ == '__main__':
    unittest.main()
