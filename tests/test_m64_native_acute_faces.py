import importlib.util
from pathlib import Path
import unittest


@unittest.skipUnless(importlib.util.find_spec('numpy'),'optional numerical dependencies')
class NativeAngleTest(unittest.TestCase):
    def test_tangent_angle_and_invalid_vectors(self):
        path=Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/wholebody/audit_native_acute_faces.py'
        spec=importlib.util.spec_from_file_location('native_angles',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.assertAlmostEqual(module.angle_degrees([1,0,0],[0,2,0]),90.)
        self.assertAlmostEqual(module.angle_degrees([1,0,0],[2,0,0]),0.)
        for value in ([0,0,0],[1,0],[float('nan'),0,0]):
            with self.assertRaises(ValueError):module.angle_degrees(value,[1,0,0])
