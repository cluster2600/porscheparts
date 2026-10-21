"""Tiny pure-stdlib complex tests; no head arrays or scientific module import."""
import importlib.util
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('patch_census_test_kernels',HERE/'patch_kernels.py')
M = importlib.util.module_from_spec(spec)
old = sys.dont_write_bytecode; sys.dont_write_bytecode = True
try:
    spec.loader.exec_module(M)
finally:
    sys.dont_write_bytecode = old


class PatchKernels(unittest.TestCase):
    def test_two_triangle_disk_oriented_boundary(self):
        faces = {10:(0,1,2),20:(0,2,3)}
        t = M.topology(faces)
        self.assertEqual((t['vertices'],t['edges'],t['faces'],t['Euler']),(4,5,2,1))
        self.assertEqual(t['oriented_boundary_cycles'],[[0,1,2,3]])
        self.assertTrue(t['is_abstract_disk'])
        self.assertEqual(M.face_groups(faces),[[10,20]])

    def test_annulus_two_rims_is_not_disk(self):
        rows=[]
        for i in range(4):
            j=(i+1)%4
            rows.extend([(i,j,j+4),(i,j+4,i+4)])
        t=M.topology(dict(enumerate(rows)))
        self.assertEqual((t['Euler'],len(t['oriented_boundary_cycles'])),(0,2))
        self.assertTrue(t['local_oriented_manifold_with_boundary'])
        self.assertFalse(t['is_abstract_disk'])

    def test_vertex_touch_is_two_edge_components_with_bad_link(self):
        faces={3:(0,1,2),9:(0,3,4)}
        self.assertEqual(M.face_groups(faces),[[3],[9]])
        self.assertEqual(M.vertex_contacts([[3],[9]],faces),{'0':[0,1]})
        t=M.topology(faces)
        self.assertIn(0,t['vertex_link_failures'])
        self.assertFalse(t['boundary_is_disjoint_oriented_cycles'])

    def test_reversed_internal_edge_orientation_is_reported(self):
        t=M.topology({0:(0,1,2),1:(0,3,2)})
        self.assertEqual(t['inconsistent_internal_orientations'],[[0,2]])
        self.assertFalse(t['local_oriented_manifold_with_boundary'])

    def test_nonmanifold_three_face_edge_is_reported(self):
        t=M.topology({0:(0,1,2),1:(1,0,3),2:(0,1,4)})
        self.assertEqual(t['nonmanifold_edges'],[[0,1]])
        self.assertFalse(t['is_abstract_disk'])

    def test_closed_tetrahedron_has_cycles_and_no_disk_boundary(self):
        t=M.topology(dict(enumerate([(0,2,1),(0,1,3),(1,2,3),(2,0,3)])))
        self.assertEqual(t['Euler'],2)
        self.assertEqual(t['oriented_boundary_cycles'],[])
        self.assertEqual(t['vertex_link_failures'],[])
        self.assertTrue(t['local_oriented_manifold_with_boundary'])
        self.assertFalse(t['is_abstract_disk'])


if __name__=='__main__':
    unittest.main()
