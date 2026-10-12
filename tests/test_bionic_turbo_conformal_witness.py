import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'twins/bionic-turbo-f1/cfd'))
from conformal_mrf_witness import mesh_text

class ConformalWitnessTests(unittest.TestCase):
    def test_radial_blocks_preserve_angular_faces_and_closed_wall_count(self):
        text=mesh_text()
        self.assertEqual(text.count('hex ('),64)
        self.assertEqual(text.count('(5 1 20)'),32)
        self.assertEqual(text.count('(10 1 20)'),32)
        self.assertIn('edges ();',text)
        self.assertEqual(text.split('faces (',1)[1].count('('),192)

    def test_radial_interface_rotation_is_tangent_and_blocks_are_right_handed(self):
        import re
        import numpy as np
        text=mesh_text()
        body=text.split('vertices (',1)[1].split(');',1)[0]
        points=np.array([[float(x) for x in row.split()] for row in re.findall(r'\(([^()]*)\)',body)])
        blocks=[[int(x) for x in row.split()] for row in re.findall(r'hex \(([^()]*)\)',text)]
        for v in blocks:
            p=points[v]
            self.assertGreater(np.linalg.det(np.array([p[1]-p[0],p[3]-p[0],p[4]-p[0]])),0)
        for v in blocks[:32]:
            p=points[[v[i] for i in (1,2,6,5)]]
            cf=p.mean(axis=0);sf=np.cross(p[1]-p[0],p[3]-p[0])
            self.assertTrue(np.allclose(p[0]+p[2],p[1]+p[3],rtol=0,atol=1e-15))
            self.assertGreater(np.dot(cf,sf),0)
            self.assertLess(abs(np.dot(np.cross([0,0,10471.975511966],cf),sf)),1e-14)
