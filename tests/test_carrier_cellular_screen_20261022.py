"""Whole-cell buffers must protect interfaces and reject unsafe centroid-only cores."""
import importlib.util
from pathlib import Path
import sys
import unittest
import numpy as np

SOURCE=Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/design-20261016/convergence-20261022'


def load(name):
    sys.path.insert(0,str(SOURCE))
    try:
        spec=importlib.util.spec_from_file_location('_'+name,SOURCE/(name+'.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
    finally:sys.path.pop(0)


class CellularScreenTests(unittest.TestCase):
    def test_clear_centroid_does_not_admit_a_cell_that_reaches_the_skin(self):
        module=load('select_cellular_budget');result=module.eligible_core(np.array([3.,3.,1.70005]),np.array([.2,2.9,.2]),np.zeros(3),0.,np.ones(3,dtype=bool),1.5)
        np.testing.assert_array_equal(result,[True,False,False])

    def test_keepout_applies_to_the_whole_cell_and_loaded_bores(self):
        module=load('prepare_cellular_screen');geometry={'central_bolt_centres_xy_mm':[[50,20]],'central_bore_radius_mm':5.5,'secondary_centres_xy_mm':[],'secondary_radius_mm':2.};parameters={'end_inboard_limit_abs_X_mm':260.,'bore_keepout_mm':10.};points=np.array([[0.,0,0],[250,0,0],[50,20,0],[35,20,0]])
        result=module.protected_cells(points,np.array([1.,20.,1.,1.]),geometry,parameters);np.testing.assert_array_equal(result,[True,False,False,False])


if __name__=='__main__':unittest.main()
