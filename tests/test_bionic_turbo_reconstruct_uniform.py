import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'twins/bionic-turbo-f1/cfd'))
from reconstruct_uniform_witness import reconstruct

class ReconstructUniformTests(unittest.TestCase):
    def test_complete_grid_preserves_faceted_walls_and_rejects_missing_nodes(self):
        sectors=4;p=[]
        for z in (0,.0005,.001):
            for offset in np.linspace(-.001,.001,5):
                for k in range(8):
                    radius=(.03+z/2+offset)*(np.cos(np.pi/sectors) if k%2 else 1)
                    p.append([radius*np.cos(k*np.pi/sectors),radius*np.sin(k*np.pi/sectors),z])
        p=np.array(p);q,r=reconstruct(p,[[0,30],[1,30.5]],1,sectors)
        self.assertTrue(r['logical_grid_complete']);self.assertTrue(r['source_macro_vertices_unchanged']);self.assertLess(r['max_lateral_surface_distance_m'],1e-12)
        np.testing.assert_allclose(q[:8],p[:8],atol=1e-15)
        self.assertAlmostEqual(np.linalg.norm(q[2*8+1,:2]),.03)
        with self.assertRaises(ValueError):reconstruct(p[:-1],[[0,30],[1,30.5]],1,sectors)
        bad=p.copy();bad[-1]=bad[0]
        with self.assertRaises(ValueError):reconstruct(bad,[[0,30],[1,30.5]],1,sectors)
