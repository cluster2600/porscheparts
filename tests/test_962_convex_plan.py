import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'twins/962-cylinder-head-f0/source/coolant_flow'
sys.path.insert(0,str(SOURCE))
spec=importlib.util.spec_from_file_location('convex_plan',SOURCE/'apply_convex_plan.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class ConvexPlanTests(unittest.TestCase):
    def test_changed_mesh_cannot_create_an_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);case=root/'case';mesh=case/'constant/polyMesh';mesh.mkdir(parents=True)
            selection=root/'selection';selection.mkdir()
            (mesh/'points').write_text('changed')
            (selection/'selection-plan.json').write_text(json.dumps({'mesh_hashes':{'points':'wrong'}}))
            with self.assertRaises(ValueError):module.apply(case,selection,root/'out')
            self.assertFalse((root/'out').exists())


if __name__=='__main__':unittest.main()
