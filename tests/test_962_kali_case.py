import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'twins/962-cylinder-head-f0/source/coolant_flow'
spec=importlib.util.spec_from_file_location('kali_water_case',SOURCE/'prepare_kali_case.py')
case=importlib.util.module_from_spec(spec);spec.loader.exec_module(case)


class KaliWaterCaseTests(unittest.TestCase):
    def test_operating_point_units_and_wall_rename(self):
        files,v,k,omega=case.dictionaries(.0008,965,400)
        self.assertAlmostEqual(v,2)
        self.assertAlmostEqual(k,.015)
        self.assertTrue(math.isfinite(omega) and omega>0)
        self.assertIn('volumetricFlowRate constant 0.0008',files['0/U'])
        self.assertIn('dimensions [0 2 -2 0 0 0 0]',files['0/p'])
        self.assertIn('patch inlet;',files['system/controlDict'])
        self.assertIn('name waterWallTyped;',files['system/wallTypeStage1'])
        self.assertIn('patches (waterWallTyped)',files['system/wallTypeStage2'])
        self.assertIn('type wall;',files['system/wallTypeStage2'])

    def test_invalid_parameters_and_failed_mesh_do_not_create_outputs(self):
        for q,rho,area in ((0,965,400),(.001,float('nan'),400),(.001,965,-1)):
            with self.subTest(q=q,rho=rho,area=area),self.assertRaises(ValueError):case.dictionaries(q,rho,area)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);mesh=root/'mesh';mesh.mkdir()
            (mesh/'saved-readback.json').write_text(json.dumps(dict(independent_volume_quality_passed=False,below_sicn_01=1)))
            with self.assertRaises(ValueError):case.prepare(mesh,root/'surface',root/'budget.json',root/'out')
            self.assertFalse((root/'out').exists())

    def test_solver_is_after_the_existing_strict_mesh_guard(self):
        script=(SOURCE/'run_kali_case.sh').read_text()
        self.assertLess(script.index('checkMesh -case'),script.index('accept_mesh.py'))
        self.assertLess(script.index('accept_mesh.py'),script.index('timeout 1800 mpirun'))
        self.assertIn('set -euo pipefail',script)

    def test_serial_recipe_checks_inputs_and_mesh_before_solver(self):
        script=(SOURCE/'run_kali_serial.sh').read_text()
        self.assertLess(script.index("record['case_hashes']"),script.index('gmshToFoam -case'))
        self.assertLess(script.index('checkMesh -case'),script.index('accept_mesh.py'))
        self.assertLess(script.index('accept_mesh.py'),script.index('1800 foamRun'))
        self.assertIn('set -euo pipefail',script)
        self.assertNotIn('mpirun ',script)


if __name__=='__main__':unittest.main()
