import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'twins/bionic-turbo-f1/cfd'))
from rotor_shell_inventory import inventory

class RotorShellTests(unittest.TestCase):
    def test_closed_shell_and_vertex_touching_open_patch_are_distinct(self):
        p=np.array([[0,0,0],[1,0,0],[0,1,0],[0,0,1],[-1,0,0],[0,-1,0]],dtype=float)
        r=inventory(p,[[0,2,1],[0,1,3],[1,2,3],[2,0,3],[0,4,5]])
        self.assertEqual(len(r),2);self.assertEqual([(x['closed'],x['euler_characteristic']) for x in r],[(True,2),(False,1)])
        self.assertEqual(r[1]['boundary_edges'],3)

    def test_nonmanifold_and_invalid_faces_rejected(self):
        p=np.array([[0,0,0],[1,0,0],[0,1,0],[0,-1,0],[0,0,1]])
        for faces in ([[0,1,2],[1,0,3],[0,1,4]],[[0,0,1]],[[0,1,9]],[]):
            with self.assertRaises(ValueError):inventory(p,faces)

    def test_quad_grid_is_one_open_component_without_triangulation(self):
        p=np.array([[x,y,0] for y in range(2) for x in range(3)])
        r=inventory(p,[[0,1,4,3],[1,2,5,4]])
        self.assertEqual(len(r),1);self.assertEqual(r[0]['boundary_edges'],6);self.assertEqual(r[0]['euler_characteristic'],1)

class CastellationControlTests(unittest.TestCase):
    def test_only_snap_changes_and_unexpected_stage_configuration_is_rejected(self):
        from prepare_castellated_control import disable_snap
        text='header\ncastellatedMesh true; snap true; addLayers false;\ngeometry {}'
        result=disable_snap(text)
        self.assertEqual(result.replace('snap false;','snap true;'),text)
        for bad in ('',text+text,result):
            with self.assertRaises(ValueError):disable_snap(bad)
