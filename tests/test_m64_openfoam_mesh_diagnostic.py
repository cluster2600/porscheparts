import importlib.util
from pathlib import Path
import sys
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/flowbench-intake'
sys.path.insert(0,str(SOURCE))
spec=importlib.util.spec_from_file_location('mesh_diagnostic',SOURCE/'check_openfoam_mesh.py')
diagnostic=importlib.util.module_from_spec(spec);spec.loader.exec_module(diagnostic)


class MeshDiagnosticTests(unittest.TestCase):
    def test_conversion_authority_does_not_authorize_solver(self):
        manifest={'purpose':'head_pilot','mesh_sha256':'a'*64}
        review={'schema':'m64-intake-pilot-review/v1','approved_for_mesh_diagnostic':True,
                'approved_for_diagnostic_cfd':False,'boundary_assignment_accepted':True,
                'mesh_sha256':'a'*64,'native_domain_sha256':'b'*64}
        diagnostic.validate_review(manifest,review)
        with self.assertRaises(ValueError):diagnostic.pilot.require_head_review(manifest,review)
        for change in ({'approved_for_mesh_diagnostic':False},{'mesh_sha256':'c'*64},
                       {'native_domain_sha256':''},{'boundary_assignment_accepted':False}):
            with self.assertRaises(ValueError):diagnostic.validate_review(manifest,{**review,**change})

    def test_explicit_single_scale_and_no_solver_command(self):
        commands=diagnostic.commands()
        self.assertEqual([name for name,cmd in commands],['gmshToFoam','transformPoints','createPatch','checkMesh'])
        self.assertEqual(commands[1][1],['transformPoints','scale=(0.001 0.001 0.001)'])
        self.assertEqual(commands[-1][1],['checkMesh','-allTopology','-allGeometry'])


if __name__=='__main__':unittest.main()
