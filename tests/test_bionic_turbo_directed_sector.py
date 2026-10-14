import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'twins/bionic-turbo-f1/cfd'))
from directed_sector_witness import hex_topology
from internal_face_facets import balance
from star_cell_partition import partition

class DirectedSectorTests(unittest.TestCase):
    def test_shared_hex_faces_and_partition_conserve_volume(self):
        grid=np.array([[[[r,a,k] for a in range(3)] for r in range(3)] for k in range(2)],float)
        f,o,n,z=hex_topology(grid);p=grid.reshape(-1,3);self.assertEqual(len(n),4);self.assertEqual(len(o),20)
        before,_=balance(p,f,o,n,2,z);self.assertLess(before['max_area_closure_m2'],1e-14);self.assertEqual(before['cells'],4)
        q,ff,oo,nn,zz,parents=partition(p,f,o,n,z);r,_=balance(q,ff,oo,nn,2,zz)
        self.assertEqual(r['cells'],24);self.assertAlmostEqual(r['minimum_oriented_cell_volume_m3'],1/6);self.assertLess(r['max_rotating_cell_flux_m3_s'],1e-14)
        self.assertEqual(ff[len(nn):],f[len(n):]);np.testing.assert_array_equal(q[:len(p)],p)

    def test_directed_refinement_preserves_anchors_walls_and_frame_tangency(self):
        from directed_sector_witness import sector_grid
        from uniform_interface_projection import metrics
        from audit_frame_interface import face_geometry
        sectors=128;nodes=np.array([[6,29],[6.1,28.95]]);width=.4;points=[]
        for z,r in ((.006,.029),(.00605,.028975),(.0061,.02895)):
            for layer,offset in enumerate(np.linspace(-.0004,.0004,5)):
                for a in range(2*sectors):
                    theta=a*np.pi/sectors;chord=1 if layer==2 or a%2==0 else np.cos(np.pi/sectors)
                    points.append([(r+offset)*chord*np.cos(theta),(r+offset)*chord*np.sin(theta),z])
        base,one=sector_grid(np.array(points),nodes,width,sectors,1);fine,eight=sector_grid(np.array(points),nodes,width,sectors,8)
        np.testing.assert_array_equal(base,fine[:,:,::8]);self.assertLess(eight['max_wall_plane_error_m'],1e-12)
        volumes=[]
        for grid in (base,fine):
            p=grid.reshape(-1,3);f,o,n,z=hex_topology(grid);flags=np.isin(np.arange(max(o)+1),z);selected=np.flatnonzero(flags[o[:len(n)]]^flags[n]);m=metrics(p,[f[i] for i in selected],10000)
            self.assertLess(m['max_normal_frame_speed_m_s'],1e-8)
            volumes.append(sum(np.dot(*face_geometry(p[face]))/3 for face in f[len(n):]))
        self.assertAlmostEqual(volumes[0]/volumes[1],1,places=12)
        with self.assertRaises(ValueError):sector_grid(np.array(points)[:-1],nodes,width,sectors,8)
