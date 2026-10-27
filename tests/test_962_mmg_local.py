import importlib.util
from pathlib import Path
import sys
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'twins/962-cylinder-head-f0/source/coolant_flow'
sys.path.insert(0,str(SOURCE))
spec=importlib.util.spec_from_file_location('local_mmg',SOURCE/'prepare_mmg_local.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class LocalMmgTests(unittest.TestCase):
    def test_two_vertex_rings_do_not_unlock_an_unrelated_region(self):
        import numpy as np
        t=np.array([[0,1,2,3],[1,2,3,4],[3,4,5,6],[7,8,9,10]])
        np.testing.assert_array_equal(module.patch(t,[0]),[True,True,True,False])


if __name__=='__main__':unittest.main()
