import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'twins/962-cylinder-head-f0/source/coolant_flow'
sys.path.insert(0,str(SOURCE))
spec=importlib.util.spec_from_file_location('water_mmg_import',SOURCE/'import_mmg.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class MmgImportTests(unittest.TestCase):
    def test_references_cannot_silently_assign_wrong_patches(self):
        names=module.physical_names([103,101,102],[1])
        self.assertEqual(names,((2,101,'inlet'),(2,102,'outlet'),(2,103,'walls'),(3,1,'coolant')))
        for surfaces,volumes in (([101,102],[1]),([101,102,104],[1]),([101,102,103],[2])):
            with self.subTest(surfaces=surfaces,volumes=volumes),self.assertRaises(ValueError):
                module.physical_names(surfaces,volumes)

    def test_parent_tampering_prevents_output_before_loading_native_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);parent=root/'parent';parent.mkdir()
            (parent/'mesh-report.json').write_text('{"mesh_sha256":"wrong"}')
            (parent/'saved-readback.json').write_text('{"mesh_sha256":"wrong"}')
            (parent/'coolant.msh').write_text('changed')
            with self.assertRaises(ValueError):module.convert(parent,root/'raw.mesh','unused',root/'out')
            self.assertFalse((root/'out').exists())


if __name__=='__main__':unittest.main()
