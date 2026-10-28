"""Manufactured constant-stress cells check the refined cellular screen's integrals."""
import importlib.util
from pathlib import Path
import sys
import unittest
import numpy as np

SOURCE=Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/design-20261016/convergence-20261022'
sys.path.insert(0,str(SOURCE))
spec=importlib.util.spec_from_file_location('carrier_linear_core',SOURCE/'prepare_linear_cellular_screen.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class LinearCoreTests(unittest.TestCase):
    def test_all_elastic_energy_modes_integrate_over_actual_cell_volume(self):
        vertices=np.array([[0.,0,0],[2,0,0],[0,3,0],[0,0,4]]);cells=np.array([[0,1,2,3]])
        for state,density in [([1,0,0,0,0,0],1/200),([1,1,1,0,0,0],3*.4/200),([0,0,0,1,0,0],1.3/100)]:
            with self.subTest(state=state):
                centres,radii,volumes,energy=module.cell_fields(vertices,cells,np.array([state]),100,.3)
                np.testing.assert_allclose(centres,[[.5,.75,1]])
                self.assertAlmostEqual(volumes[0],4)
                self.assertAlmostEqual(energy[0],4*density)
                self.assertTrue(np.all(np.linalg.norm(vertices-centres[0],axis=1)<=radii[0]))

    def test_inverted_nonfinite_incomplete_and_wrapped_rosters_are_refused(self):
        v=np.eye(4,3,k=-1);c=np.array([[0,1,2,3]]);stress=np.zeros((1,6))
        for vertices,cells,field in [(v,c[:,[1,0,2,3]],stress),(v,c,np.full((1,6),np.nan)),(v,c,np.zeros((0,6))),(v,np.array([[-1,1,2,3]]),stress)]:
            with self.subTest(cells=cells.tolist()):
                with self.assertRaises(ValueError):module.cell_fields(vertices,cells,field,100,.3)

if __name__=='__main__':unittest.main()
