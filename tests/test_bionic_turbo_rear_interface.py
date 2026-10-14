import math,sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'twins/bionic-turbo-f1/cfd'))
from audit_rear_interface import planar_annulus,crossing_facets


def ring():
    angles=np.arange(16)*2*math.pi/16
    inner=np.column_stack((np.cos(angles),np.sin(angles),np.full(16,-3.75)))
    outer=inner.copy();outer[:,:2]*=3
    return np.array([face for i in range(16) for face in ((inner[i],outer[(i+1)%16],outer[i]),(inner[i],inner[(i+1)%16],outer[(i+1)%16]))])


class RearInterfaceTests(unittest.TestCase):
    def test_complete_annulus_without_angular_sampling(self):
        r=planar_annulus(ring(),radius=2)
        self.assertTrue(r['complete_angular_coverage']);self.assertEqual(r['boundary_edges'],32)
        self.assertLess(r['annulus_inner_radius_mm'],2);self.assertGreater(r['annulus_outer_radius_mm'],2)

    def test_missing_sector_and_duplicate_face_reject_coverage(self):
        t=ring()
        for changed in (t[2:],np.concatenate((t,t[:1])),t[:,::-1]):
            with self.assertRaises(ValueError):planar_annulus(changed,radius=2)

    def test_nonplanar_defect_cannot_be_rounded_into_a_plane(self):
        t=ring();t[:2,:,2]+=1e-10
        with self.assertRaises(ValueError):planar_annulus(t,radius=2)

    def test_radial_triangle_interior_and_axial_crossings(self):
        t=np.array([[[-3,1,-1],[3,1,1],[0,4,1]],[[10,0,5],[11,0,5],[10,1,5]]],dtype=float)
        np.testing.assert_array_equal(crossing_facets(t,0,0,0,2),[0])
        self.assertEqual(len(crossing_facets(t,2,3,0,20)),0)

    def test_touching_boundary_loops_outside_annulus_do_not_create_a_hole_inside(self):
        extra=np.array([[[10,0,-3.75],[10,1,-3.75],[11,0,-3.75]],[[10,0,-3.75],[10,-1,-3.75],[9,0,-3.75]]])
        result=planar_annulus(np.concatenate((ring(),extra)),radius=2)
        self.assertTrue(result['complete_angular_coverage'])
        self.assertEqual(result['branching_boundary_vertices_outside_annulus'],1)

    def test_bounded_profile_retains_both_variants(self):
        from audit_rear_interface import bounded_profile
        def report():
            return dict(bands=[dict(z_low_mm=(i-38)*.1,z_high_mm=(i-37)*.1,rotor_upper_mm=5.,stator_lower_mm=40.) for i in range(359)],corridor=dict(open_profiles=[dict(band_indices=list(range(3,359)),minimum_radial_separation_bound_mm=1.)]))
        a,b=report(),report();b['bands'][-1]['stator_lower_mm']=30
        result=bounded_profile(a,b)
        self.assertGreaterEqual(result['verified_radial_clearance_mm'],1.)
        self.assertGreater(result['maximum_absolute_slope'],0)
        self.assertEqual(result['nodes_z_radius_mm'][0],[-4.,32.])
        self.assertLessEqual(result['nodes_z_radius_mm'][-1][1],29.)
        b['corridor']['open_profiles'][0]['band_indices']=[3]
        with self.assertRaises(ValueError):bounded_profile(a,b)

    def test_rear_patch_split_preserves_all_faces(self):
        from profile_mrf_witness import mesh_text
        from rear_mrf_witness import split_rear_wall
        text=mesh_text([[-3.75,32],[-3.5,32],[-3,31.8]],.4,128)
        result=split_rear_wall(text,128)
        self.assertIn('boundary (stator {type wall;',result)
        self.assertEqual(result.count('hex ('),text.count('hex ('))
        self.assertEqual(result.count('('),text.count('(')+1)
        with self.assertRaises(ValueError):split_rear_wall(text,64)
