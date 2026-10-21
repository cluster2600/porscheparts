"""3MF decimal coordinates must encode the actual source binary value."""
from fractions import Fraction
import importlib.util
import math
from pathlib import Path
import tempfile
import unittest
import zipfile

SOURCE=Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/design-20261016/resume-20261020/canonical_component_3mf.py'
SPEC=importlib.util.spec_from_file_location('exact_carrier_3mf_coordinates',SOURCE)
CORE=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(CORE)


class ExactCoordinateTests(unittest.TestCase):
    def test_decimal_is_exact_rational_value_of_binary_input(self):
        for value in [.1,-296.000030517578125,2.**-100,math.nextafter(1.,2.)]:
            with self.subTest(value=value):
                self.assertEqual(Fraction(CORE.exact_decimal(value)),Fraction.from_float(value))

    def test_nonfinite_coordinate_is_rejected(self):
        for value in [float('nan'),float('inf'),float('-inf')]:
            with self.subTest(value=value),self.assertRaises(ValueError):CORE.exact_decimal(value)

    def test_default_and_explicit_identity_are_identical(self):
        self.assertTrue(CORE.identity_transform(None))
        self.assertTrue(CORE.identity_transform('1 0 0 0 1 0 0 0 1 0 0 0'))

    def test_small_translation_is_not_silently_tolerated(self):
        self.assertFalse(CORE.identity_transform('1 0 0 0 1 0 0 0 1 0.000000000001 0 0'))

    def test_required_extension_prefix_survives_coordinate_canonicalization(self):
        xml=f'''<model xmlns="{CORE.CORE}" xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p" unit="millimeter"><resources><object id="1" p:UUID="preserved"><mesh><vertices><vertex x="0.1" y="0" z="0"/></vertices></mesh></object><object id="2"><components><component objectid="1"/></components></object></resources><build><item objectid="2"/></build></model>'''
        with tempfile.TemporaryDirectory() as folder:
            raw=Path(folder)/'raw.3mf';target=Path(folder)/'exact.3mf'
            with zipfile.ZipFile(raw,'w') as archive:archive.writestr('3D/3dmodel.model',xml)
            CORE.canonicalize(raw,target,{1:[[.1,0.,0.]]})
            with zipfile.ZipFile(target) as archive:result=archive.read('3D/3dmodel.model').decode()
        self.assertIn('xmlns:p=',result)
        self.assertIn('requiredextensions="p"',result)


if __name__=='__main__':unittest.main()
