import importlib.util
from pathlib import Path
import sys
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'twins/962-cylinder-head-f0/source/coolant_flow'
sys.path.insert(0,str(SOURCE))
spec=importlib.util.spec_from_file_location('stencil_relocation',SOURCE/'relocate_stencil.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class StencilRelocationTests(unittest.TestCase):
    def test_regular_tetrahedron_analytic_determinant_scale_and_rank(self):
        import numpy as np
        tetra=np.array([[[0,0,0],[1,0,0],[.5,np.sqrt(3)/2,0],[.5,np.sqrt(3)/6,np.sqrt(2/3)]]])
        np.testing.assert_allclose(module.determinants(tetra,np.ones((1,4),bool)),[64/27])
        mask=np.array([[False,True,True,True]])
        np.testing.assert_allclose(module.determinants(tetra,mask),[16/27])
        np.testing.assert_allclose(module.determinants(tetra*1000,mask),[16/27])
        self.assertLess(module.determinants(tetra,np.array([[False,False,True,True]]))[0],1e-12)

    def test_interior_star_recovers_all_three_gates_without_mutating_boundary(self):
        import numpy as np
        points=np.array([[0,0,0],[1,0,0],[.5,np.sqrt(3)/2,0],[.5,np.sqrt(3)/6,np.sqrt(2/3)],[.02,.02,.02]])
        before=points.copy();t=np.array([[4,*face] for face in module.PATTERNS])
        mask=np.tile([False,True,True,True],(4,1));pairs=np.array([(i,j) for i in range(4) for j in range(i+1,4)])
        moved,result=module.optimise_node(points,t,mask,pairs,4)
        self.assertTrue(result['accepted'],result);np.testing.assert_array_equal(points,before)
        points[4]=moved;q,v=module.tetra_metrics(points[t])
        self.assertGreaterEqual(q.min(),.1);self.assertGreaterEqual(module.determinants(points[t],mask).min(),.001)
        self.assertGreaterEqual((v[pairs].min(axis=1)/v[pairs].sum(axis=1)).min(),.05)


if __name__=='__main__':unittest.main()
