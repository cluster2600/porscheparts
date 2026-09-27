"""Pure hash and array-size guards; no private geometry or optional CAD imports."""
import importlib.util
from pathlib import Path
import sys
import unittest

HERE=Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/wholebody'
sys.path.insert(0,str(HERE))
SPEC=importlib.util.spec_from_file_location('native_export',HERE/'export_native_body.py')
export=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(export)


class NativeExportTests(unittest.TestCase):
    def test_requires_an_exact_sha256(self):
        self.assertEqual(export.expected_digest('ab'*32),'ab'*32)
        for value in ('a'*63,'AB'*32,'a'*65,'x'*64,True,None):
            with self.subTest(value=value),self.assertRaises(ValueError):export.expected_digest(value)

    def test_mesh_bounds_and_finiteness(self):
        self.assertTrue(export.mesh_limits(3,1,0,2,True))
        for args in [(3,1,-1,2,True),(3,1,0,3,True),(3,1,0,2,False),(3,0,0,2,True),
                     (3,2000001,0,2,True),(True,1,0,2,True),(6000001,1,0,2,True)]:
            with self.subTest(args=args):self.assertFalse(export.mesh_limits(*args))


if __name__=='__main__':unittest.main()
