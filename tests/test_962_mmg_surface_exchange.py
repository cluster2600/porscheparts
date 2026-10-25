import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'twins/962-cylinder-head-f0/source/coolant_flow'
sys.path.insert(0,str(SOURCE))
spec=importlib.util.spec_from_file_location('mmg_surface_exchange',SOURCE/'mmg_surface_exchange.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class MmgSurfaceExchangeTests(unittest.TestCase):
    def test_master_tampering_cannot_create_an_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);native=root/'native.stl';native.write_text('changed')
            with self.assertRaises(ValueError):module.exchange(root,root/'raw.mesh','unused',native,'wrong',root/'out')
            self.assertFalse((root/'out').exists())


if __name__=='__main__':unittest.main()
