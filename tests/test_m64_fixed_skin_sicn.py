import importlib.util
from pathlib import Path
import unittest


@unittest.skipUnless(importlib.util.find_spec('numpy'),'optional numerical dependencies')
class FixedSkinTest(unittest.TestCase):
    def test_metric_orientation_and_monotone_gate(self):
        import numpy as np
        path=Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/wholebody/optimize_fixed_skin_sicn.py'
        spec=importlib.util.spec_from_file_location('fixed_skin',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        p=np.vstack([np.zeros(3),module.IDEAL.T])[None]
        q,v=module.metric(p);self.assertAlmostEqual(q[0],1.)
        qn,vn=module.metric(p[:,[0,2,1,3]])
        self.assertAlmostEqual(qn[0],-1.);self.assertAlmostEqual(vn[0],-v[0])
        old=np.array([.05,.2]);vol=np.ones(2)
        self.assertTrue(module.admissible(old,vol,np.array([.11,.15]),vol))
        for bad in (np.array([.04,.3]),np.array([.07,.08]),np.array([float('nan'),.2])):
            self.assertFalse(module.admissible(old,vol,bad,vol))

    def test_cavity_flip_keeps_oriented_boundary_and_rejects_regression(self):
        import numpy as np
        import sys
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/wholebody'))
        from flip_fixed_skin_tetrahedra import admit_cavity,metric,oriented_skin,candidates
        points=np.array([[0,0,0],[1,0,0],[.5,.8660254,0],
            [-.3194267563,.2060662632,.201511346], [.67679964,.3679390464,-.0397858143]])
        old=np.array([[0,1,2,3],[0,2,1,4]])
        new=np.array([[3,4,0,1],[3,4,1,2],[3,4,2,0]])
        admitted=admit_cavity(points,old,new)
        self.assertIsNotNone(admitted)
        self.assertEqual(oriented_skin(old),oriented_skin(admitted))
        self.assertTrue((metric(points[admitted])[0]>=.1).all())
        self.assertIsNone(admit_cavity(points,admitted,old))
        self.assertIsNone(admit_cavity(points,old,np.vstack([new,new[0]])))
        self.assertIsNone(admit_cavity(points,old,[[0,1,2,2]]))
        self.assertTrue(any(len(ids)==2 and len(c)==3 for ids,c in candidates(old,[1])))
        octa=np.array([[0,1,2,3],[0,1,3,4],[0,1,4,5],[0,1,5,2]])
        alternatives=[c for ids,c in candidates(octa,[0]) if len(ids)==len(c)==4]
        self.assertEqual(len(alternatives),2)
        self.assertTrue(all(len({tuple(sorted(t)) for t in c})==4 for c in alternatives))
