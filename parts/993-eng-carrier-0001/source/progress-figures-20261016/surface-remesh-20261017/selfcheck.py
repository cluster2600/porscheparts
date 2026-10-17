"""Stdlib boundary checks; no rendering or scientific import."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import struct

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('figure',HERE/'figure.py');figure=importlib.util.module_from_spec(spec);spec.loader.exec_module(figure)
class Checks(unittest.TestCase):
    def test_truncated_and_empty_STL_rejected_before_scientific_import(self):
        with tempfile.TemporaryDirectory()as folder:
            path=Path(folder)/'bad.stl'
            for data in [b'',bytes(80),bytes(80)+struct.pack('<I',0),bytes(80)+struct.pack('<I',1)+bytes(49)]:
                path.write_bytes(data)
                with self.assertRaises(ValueError):figure.read_binary(path)
        import sys
        self.assertNotIn('numpy',sys.modules)
    def test_sha_bytes(self):
        with tempfile.TemporaryDirectory()as folder:
            path=Path(folder)/'empty';path.write_bytes(b'')
            self.assertEqual(figure.sha(path),'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')
if __name__=='__main__':unittest.main()
