import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'twins/bionic-turbo-f1/cfd'))
from internal_face_facets import facet_internal,balance

class InternalFacetsTests(unittest.TestCase):
    def test_warped_cube_balance_and_protected_faces(self):
        p=np.array([[x,y,z] for z in (0,1) for y in (0,1) for x in (0,1)],float)+[3,4,5];p[7]+=[.17,-.13,.31]
        f=[[0,2,3,1],[4,5,7,6],[0,1,5,4],[2,6,7,3],[0,4,6,2],[1,3,7,5]];o=np.zeros(6,int);n=np.ones(6,int)
        before,_=balance(p,f,o,np.array([],int),2,[0]);self.assertGreater(before['max_rotating_cell_flux_m3_s'],1e-8)
        new,own,nei,parents,r=facet_internal(p,f,o,n,[])
        after,_=balance(p,new,own,np.array([],int),2,[0]);self.assertLess(after['max_rotating_cell_flux_m3_s'],1e-12)
        self.assertTrue(np.all(own==0) and np.all(nei==1));self.assertLess(after['max_area_closure_m2'],1e-12)
        untouched,*_=facet_internal(p,f,o,n,range(6));self.assertEqual(untouched,f)
        walls,*_=facet_internal(p,f,o,np.array([],int),[]);self.assertEqual(walls,f)
        with self.assertRaises(ValueError):facet_internal(p,f,o,n,[6])

    def test_batch_geometry_matches_individual_pinned_formula(self):
        from frame_balance_batches import geometry
        from audit_frame_interface import face_geometry
        rng=np.random.default_rng(41)
        for n in range(3,10):
            angle=np.arange(n)*2*np.pi/n
            polygons=np.tile(np.array([np.cos(angle),np.sin(angle),angle*0]).T,(7,1,1));polygons+=rng.normal(0,.02,polygons.shape)
            c,s,w=geometry(polygons)
            for i,p in enumerate(polygons):
                cc,ss=face_geometry(p);np.testing.assert_allclose(c[i],cc,rtol=1e-14,atol=1e-15);np.testing.assert_allclose(s[i],ss,rtol=1e-14,atol=1e-15)
        with self.assertRaises(ValueError):geometry(np.zeros((1,4,3)))

    def test_star_partition_retains_faces_and_volume(self):
        from star_cell_partition import partition
        p=np.array([[x,y,z] for z in (0,1) for y in (0,1) for x in (0,1)],float)
        faces=[[0,2,3,1],[4,5,7,6],[0,1,5,4],[2,6,7,3],[0,4,6,2],[1,3,7,5]]
        q,f,o,n,z,parent=partition(p,faces,np.zeros(6,int),np.array([],int),[0])
        self.assertEqual(len(parent),6);self.assertEqual(len(z),6);self.assertEqual(f[len(n):],faces);np.testing.assert_array_equal(q[:len(p)],p)
        r,_=balance(q,f,o,n,2,z);self.assertAlmostEqual(r['minimum_oriented_cell_volume_m3'],1/6);self.assertLess(r['max_area_closure_m2'],1e-14);self.assertLess(r['max_rotating_cell_flux_m3_s'],1e-14)
        p[7]+=[.17,-.13,.31]
        with self.assertRaises(ValueError):partition(p,faces,np.zeros(6,int),np.array([],int),[0])
