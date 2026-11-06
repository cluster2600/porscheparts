"""Strict native result intake: complete fields and independently damaged rows."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

try:
    import numpy as np
except ImportError:
    np = None

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipIf(np is None, 'NumPy is required')
class CalculixC3D4FieldReaderTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location(
            'c3d4_reader', ROOT / 'scripts/calculix_c3d4_field_reader.py')
        self.reader = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.reader)
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.field = (
            'displacements (vx,vy,vz) for set ALLN\n'
            '1 1.234567E-7 -2.5 0\n2 0 0 0\n3 0 0 0\n4 0 0 0\n'
            'forces (fx,fy,fz) for set FIXED\n1 0 0 2\n4 0 0 -2\n'
            'stresses (elem,int.pnt.,sxx,syy,szz,sxy,sxz,syz) for set BODY\n'
            '1 1 11 22 33 44 55 66\n'
            'internal energy density (elem,int.pnt.,energy) for set BODY\n'
            '1 1 0.25\n')

    def read(self, text):
        path = self.root / 'job.dat'
        path.write_text(text)
        output = self.root / 'fields'
        output.mkdir()
        return self.reader.parse_dat(path, output, 4, 1, np.array([0, 3]))

    def test_complete_native_fields_and_decimal_bits(self):
        arrays, counts = self.read(self.field)
        self.assertEqual(counts, {'u': 4, 'rf': 2, 's': 1, 'ener': 1})
        expected = np.array([float('1.234567E-7'), -2.5, 0.])
        np.testing.assert_array_equal(arrays['u'][0].view(np.uint64),
                                      expected.view(np.uint64))
        np.testing.assert_array_equal(arrays['rf'], [[0, 0, 2], [0, 0, -2]])
        np.testing.assert_array_equal(arrays['s'], [[11, 22, 33, 44, 55, 66]])
        self.assertEqual(arrays['ener'][0], .25)

    def test_missing_energy_rejected(self):
        with self.assertRaises(AssertionError):
            self.read(self.field.rsplit('1 1 0.25\n', 1)[0])

    def test_duplicate_displacement_rejected(self):
        with self.assertRaises(AssertionError):
            self.read(self.field.replace('2 0 0 0', '1 0 0 0'))

    def test_reordered_reaction_roster_rejected(self):
        with self.assertRaises(AssertionError):
            self.read(self.field.replace('4 0 0 -2', '3 0 0 -2'))

    def test_wrong_integration_point_rejected(self):
        with self.assertRaises(AssertionError):
            self.read(self.field.replace('1 1 11', '1 2 11'))

    def test_nonfinite_value_rejected(self):
        with self.assertRaises(AssertionError):
            self.read(self.field.replace('1 1 0.25', '1 1 nan'))

    def test_trailing_numeric_junk_rejected(self):
        with self.assertRaises((AssertionError, ValueError, Warning)):
            self.read(self.field.replace('1 1 0.25', '1 1 0.25junk'))

    def test_compensating_row_width_errors_rejected(self):
        with self.assertRaises(AssertionError):
            self.read(self.field.replace('2 0 0 0\n3 0 0 0',
                                         '2 0 0\n3 0 0 0 0'))

    def test_repeated_section_rejected(self):
        with self.assertRaises(AssertionError):
            self.read(self.field + 'displacements (vx,vy,vz)\n')

    def test_decimal_node_identifier_rejected(self):
        with self.assertRaises(AssertionError):
            self.read(self.field.replace('2 0 0 0', '2.0 0 0 0'))

    def test_extra_result_row_rejected(self):
        with self.assertRaises(AssertionError):
            self.read(self.field + '2 1 0.25\n')


if __name__ == '__main__':
    unittest.main()
