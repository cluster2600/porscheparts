import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'twins/bionic-turbo-f1/cfd'))
from periodic_sector_boundary import paired_cuts


class PeriodicSectorTest(unittest.TestCase):
    def test_pair_rotation_and_refuse_displaced_vertex(self):
        angle=.1;c,s=np.cos(angle),np.sin(angle);r=np.array([[c,-s,0],[s,c,0],[0,0,1]])
        a=np.array([[1.,0,0],[2,0,0],[2,0,1],[1,0,1]])
        p=np.vstack((a,a@r.T));faces=[[0,1,2],[0,1,2,3],[7,6,5,4]]
        order,report=paired_cuts(p,faces,1,angle)
        self.assertEqual(order.tolist(),[0,1,2]);self.assertEqual(report['paired_faces'],1)
        vector=np.array([.3,-.7,2.]);self.assertTrue(np.allclose(r.T@(r@vector),vector,atol=1e-14))
        self.assertTrue(np.allclose(r@np.cross([0,0,3],a[0]),np.cross([0,0,3],r@a[0]),atol=1e-14))
        p[4,2]+=.01
        with self.assertRaises(ValueError):paired_cuts(p,faces,1,angle)

if __name__=='__main__':unittest.main()
