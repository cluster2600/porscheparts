#!/usr/bin/env python3
"""Independent analytic mesh fixture and false-admission regressions, no solvers."""
import copy,json,tempfile,unittest
from pathlib import Path
import numpy as np
from assembly_interface_gate import evaluate
from diagnose_d2_establishment import poly_mesh,completed_log
from prepare_d3_relaxation_pair import changed_system
ROOT=Path(__file__).resolve().parents[1]


class IndependentChecks(unittest.TestCase):
    def test_two_unit_tetrahedra_have_known_volumes_and_centroids(self):
        with tempfile.TemporaryDirectory() as tmp:
            case=Path(tmp);mesh=case/'constant/polyMesh';mesh.mkdir(parents=True)
            def write(name,rows):(mesh/name).write_text(str(len(rows))+'\n(\n'+'\n'.join(rows)+'\n)\n')
            write('points',['(0 0 0)','(1 0 0)','(0 1 0)','(0 0 1)','(0 0 -1)'])
            write('faces',['3(0 2 1)','3(0 1 3)','3(1 2 3)','3(2 0 3)','3(0 4 1)','3(1 4 2)','3(2 4 0)'])
            write('owner',['0','0','0','0','1','1','1']);write('neighbour',['1'])
            *_,volume,centers=poly_mesh(case)
            np.testing.assert_allclose(volume,[1/6,1/6],rtol=1e-14,atol=0)
            np.testing.assert_allclose(centers,[[.25,.25,.25],[.25,.25,-.25]],rtol=1e-14,atol=0)

    def test_incomplete_native_tail_is_never_a_completed_iteration(self):
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'log';file.write_text('Time = 1020\nGAMG: Solving for p, Initial residual = 0.1, Final residual = 0.001, No Iterations 4\nExecutionTime = 2 s  ClockTime = 3 s\nTime = 1021\nGAMG: Solving for p, Initial residual = 0.09, Final residual = 0.0009, No Iterations 4\n')
            self.assertEqual([x['iteration'] for x in completed_log(file)],[1020])

    def test_valid_geometry_and_visual_materials_cannot_close_interfaces(self):
        contract=json.loads((ROOT/'parameters/assembly-interface-contract.json').read_text())
        result=evaluate(contract,{'brep_valid':True,'metal_shader':True})
        self.assertFalse(result['functional_completion_allowed']);self.assertEqual(len(result['missing_evidence']),55)
        for claim in ['functional_interfaces_verified','manufacturing_authorized','physical_validation_established','functional_completion_allowed']:
            with self.assertRaises(ValueError):evaluate(contract,{claim:True})

    def test_model_generated_inspection_is_rejected_as_physical_evidence(self):
        contract=json.loads((ROOT/'parameters/assembly-interface-contract.json').read_text())
        contract['physical_measurements']['rotor_output_shaft.axis']={'origin':'model_generated','value':[0,0,1],**{k:'self-generated' for k in contract['measurement_requirements']}}
        self.assertIn('rotor_output_shaft.axis',evaluate(contract,{})['missing_evidence'])

    def test_equal_work_pair_changes_only_pressure_relaxation(self):
        control=(ROOT/'parameters/D2-restart1000-controlDict').read_text()
        solution=(ROOT/'parameters/D2-executed-configurations/system/fvSolution').read_text()
        a,u=changed_system(control,solution,.15);b,v=changed_system(control,solution,.05)
        self.assertEqual(a,b);self.assertEqual(u.replace('p 0.15','p 0.05'),v)
        self.assertIn('startTime 1020;',a);self.assertIn('endTime 1040;',a)
        for bad in [control.replace('endTime 1020;','endTime 1080;'),control.replace('startTime 1000;','startTime 0;')]:
            with self.assertRaises(ValueError):changed_system(bad,solution,.15)
        with self.assertRaises(ValueError):changed_system(control,solution,.25)


if __name__=='__main__':unittest.main()
