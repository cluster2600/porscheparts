import importlib.util
from pathlib import Path
import sys
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'twins/962-cylinder-head-f0/source/coolant_flow'
sys.path.insert(0,str(SOURCE))
spec=importlib.util.spec_from_file_location('convex_completion',SOURCE/'complete_convex_selection.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class ConvexCompletionTests(unittest.TestCase):
    def test_three_cells_form_a_convex_bipyramid_while_two_are_concave(self):
        import numpy as np
        p=np.array([[0,0,0],[1,0,0],[0,1,0],[.3,.3,1],[.3,.3,-1]])
        cells=[p[[3,4,i,j]] for i,j in ((0,1),(1,2),(2,0))]
        self.assertTrue(module.convex_union(cells))
        self.assertFalse(module.convex_union(cells[:2]))


if __name__=='__main__':unittest.main()
