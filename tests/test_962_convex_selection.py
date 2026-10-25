import importlib.util
from pathlib import Path
import sys
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'twins/962-cylinder-head-f0/source/coolant_flow'
sys.path.insert(0,str(SOURCE))
spec=importlib.util.spec_from_file_location('convex_selection',SOURCE/'select_convex_merges.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class ConvexSelectionTests(unittest.TestCase):
    def test_convex_bipyramid_and_concave_union_are_distinguished(self):
        import numpy as np
        base=np.array([[0,0,0],[1,0,0],[0,1,0]])
        a=np.vstack([base,[.25,.25,1]])
        self.assertTrue(module.convex_pair(a,np.vstack([base,[.25,.25,-1]])))
        self.assertFalse(module.convex_pair(a,np.vstack([base,[2,2,-1]])))
        self.assertFalse(module.convex_pair(a,a))


if __name__=='__main__':unittest.main()
