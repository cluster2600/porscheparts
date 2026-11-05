"""Native field-width regressions must preserve the geometry's binary values."""

import importlib.util
import math
from pathlib import Path
import struct
import unittest


MODULE = Path(__file__).resolve().parents[1] / "scripts/calculix_coordinate_format.py"
SPEC = importlib.util.spec_from_file_location("calculix_coordinate_format", MODULE)
FORMAT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FORMAT)


class CoordinateFormatTests(unittest.TestCase):
    def test_native_reader_rejected_long_scientific_token_is_losslessly_shortened(self):
        value = -4.0459999581798999e-5
        self.assertGreater(len(format(value, ".17g")), 20)
        token = FORMAT.format_coordinate(value)
        self.assertLessEqual(len(token), 20)
        self.assertEqual(struct.pack("d", float(token)), struct.pack("d", value))

    def test_small_negative_fixed_coordinate_preserves_its_last_bit(self):
        value = -0.048549324755079004
        token = FORMAT.format_coordinate(value)
        self.assertLessEqual(len(token), 20)
        self.assertEqual(struct.pack("d", float(token)), struct.pack("d", value))

    def test_unrepresentable_standard_field_refuses_instead_of_rounding(self):
        with self.assertRaisesRegex(ValueError, "No exact"):
            FORMAT.format_coordinate(0.00023784860968589783)

    def test_signed_zero_is_preserved(self):
        for value in [0.0, -0.0]:
            with self.subTest(value=repr(value)):
                token = FORMAT.format_coordinate(value)
                self.assertEqual(struct.pack("d", float(token)), struct.pack("d", value))

    def test_adjacent_binary_values_are_not_collapsed(self):
        values = [math.nextafter(1.0, 0.0), 1.0, math.nextafter(1.0, math.inf)]
        tokens = [FORMAT.format_coordinate(value) for value in values]
        self.assertEqual(len(set(tokens)), 3)
        self.assertEqual([float(token) for token in tokens], values)

    def test_nonfinite_coordinates_refuse(self):
        for value in [math.nan, math.inf, -math.inf]:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "finite"):
                    FORMAT.format_coordinate(value)


if __name__ == "__main__":
    unittest.main()
