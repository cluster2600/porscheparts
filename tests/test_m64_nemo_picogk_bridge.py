import importlib.util
from pathlib import Path
import sys
import unittest

HERE=Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/wholebody'
sys.path.insert(0,str(HERE))
SPEC=importlib.util.spec_from_file_location('nemo_bridge',HERE/'audit_nemo_picogk_bridge.py')
bridge=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(bridge)


class BridgeTests(unittest.TestCase):
    def test_optimizer_never_trades_new_inversions_or_worse_minimum_for_count(self):
        from optimize_nemo_interior import improves
        before={'nonpositive_Jacobians':0,'minSICN_below_0p1':160,'minimum_minSICN':.017,
                'bad_tetrahedron_absolute_volume_fraction':.0003}
        better={**before,'minSICN_below_0p1':150}
        self.assertTrue(improves(before,better))
        self.assertFalse(improves(before,before))
        for key,value in [('nonpositive_Jacobians',1),('minimum_minSICN',.016),
                          ('bad_tetrahedron_absolute_volume_fraction',.0004)]:
            self.assertFalse(improves(before,{**better,key:value}))

    def test_oriented_tetra_reference_and_boundary(self):
        import numpy as np
        p=np.array([[0.,0.,0.],[1.,0.,0.],[.5,np.sqrt(3)/2,0.],[.5,np.sqrt(3)/6,np.sqrt(2/3)]])
        c=np.array([[0,1,2,3]],dtype=np.int64)
        ref=bridge.tetra_reference(p,c)
        self.assertAlmostEqual(ref['volumes'][0],np.sqrt(2)/12)
        self.assertAlmostEqual(ref['aspect_ratio'][0],1)
        self.assertAlmostEqual(ref['edge_length_ratio'][0],1)
        f=bridge.boundary_faces(c); xyz=p[f]; center=p.mean(0)
        self.assertTrue((np.einsum('ij,ij->i',np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0]),xyz.mean(1)-center)>0).all())
        with self.assertRaises(ValueError): bridge.tetra_reference(p,c[:,[0,2,1,3]])
        with self.assertRaises(ValueError): bridge.tetra_reference(p.astype(np.float32),c)
        with self.assertRaises(ValueError): bridge.boundary_faces(np.repeat(c,3,axis=0))


if __name__=='__main__': unittest.main()
