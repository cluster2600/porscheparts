import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'twins/bionic-turbo-f1/cfd'))
from uniform_interface_projection import project

class UniformProjectionTests(unittest.TestCase):
    def test_uniform_chord_subdivision_recovers_analytic_trapezoids(self):
        angles=[0,.1,.2];points=[]
        for z,r in ((0,.03),(.001,.0305)):
            endpoints=[np.array([r,0,z]),np.array([r*np.cos(.2),r*np.sin(.2),z])]
            points.extend([endpoints[0],(endpoints[0]+endpoints[1])/2,endpoints[1]])
        faces=[(0,1,4,3),(1,2,5,4)];p=np.array(points);q,report=project(p,faces,[[0,30],[1,30.5]],10000)
        self.assertGreater(report['before']['max_normal_frame_speed_m_s'],1)
        self.assertLess(report['after']['max_normal_frame_speed_m_s'],1e-8)
        np.testing.assert_allclose(np.linalg.norm(q[:3,:2],axis=1),.03,atol=1e-15)
        np.testing.assert_array_equal(q[:,2],p[:,2])
        with self.assertRaises(ValueError):project(p,[[0,1,2,5,3]],[[0,30],[1,30.5]],10000)
        with self.assertRaises(ValueError):project(p,faces,[[0,30],[.5,30.1],[1,30.5]],10000)
        distorted=p.copy();distorted[4,2]+=.0001
        with self.assertRaises(ValueError):project(distorted,faces,[[0,30],[1,30.5]],10000)

    def test_native_area_weighted_face_centre_requires_axial_grid_reconstruction(self):
        from uniform_interface_projection_v2 import project as grid_project
        p=np.array([[.0289278606841216,0,.006],[.02887942096945005,0,.00605],[.02886205477226627,.000708523675891451,.006049972044848866],[.02891043824657925,.0007097114235187,.006]])
        nodes=[[6,28.9278606841216],[6.1,28.8309812547785]];faces=[(0,1,2,3)]
        with self.assertRaises(ValueError):project(p,faces,nodes,10471.975511966)
        q,r=grid_project(p,faces,nodes,10471.975511966)
        self.assertLess(r['after']['max_plane_distance_m'],1e-12);self.assertLess(r['after']['max_normal_frame_speed_m_s'],1e-8)
        self.assertAlmostEqual(q[2,2],.00605);self.assertGreater(r['max_axial_displacement_m'],2e-8)
        ambiguous=p.copy();ambiguous[2,2]=.006025
        with self.assertRaises(ValueError):grid_project(ambiguous,faces,nodes,10471.975511966)
