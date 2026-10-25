"""Geometric conservation and exterior-face identity on a complete red split."""
from collections import Counter
from fractions import Fraction as Q
import importlib.util
from pathlib import Path
import unittest
import numpy as np

SOURCE=Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/design-20261016/convergence-20261022/refine_matched_tetrahedra.py'
spec=importlib.util.spec_from_file_location('_nested_carrier',SOURCE);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def determinant(t):
    a,b,c=[tuple(Q(float(x))-Q(float(y))for x,y in zip(row,t[0]))for row in t[1:]]
    return a[0]*(b[1]*c[2]-b[2]*c[1])-a[1]*(b[0]*c[2]-b[2]*c[0])+a[2]*(b[0]*c[1]-b[1]*c[0])


class NestedRefinementTests(unittest.TestCase):
    def setUp(self):
        corners=np.array([[0.,0,0],[1.,0,0],[0,1.,0],[0,0,1.]])
        self.vertices=np.vstack([corners,[(corners[i]+corners[j])/2 for i,j in [(0,1),(1,2),(0,2),(0,3),(1,3),(2,3)]]]);self.cells=module.subdivide(np.arange(10)[None,:],np)

    def test_all_children_have_exact_one_eighth_parent_volume(self):
        values=[abs(determinant(self.vertices[cell]))for cell in self.cells];self.assertEqual(values,[Q(1,8)]*8);self.assertEqual(sum(values),Q(1))

    def test_complete_boundary_matches_four_refined_parent_faces(self):
        counts=Counter(tuple(sorted(face))for c in self.cells for face in [c[[0,1,2]],c[[0,1,3]],c[[0,2,3]],c[[1,2,3]]]);self.assertEqual(set(counts.values()),{1,2})
        parent_faces=np.array([[0,2,1,6,5,4],[0,1,3,4,8,7],[0,3,2,7,9,6],[1,2,3,5,9,8]]);expected={tuple(sorted(f))for f in module.subdivide_faces(parent_faces,np)};self.assertEqual({f for f,n in counts.items()if n==1},expected);self.assertEqual(len(expected),16)

    def test_consistent_refined_surface_force_preserves_affine_virtual_work(self):
        v=self.vertices;parent=np.array([[0,1,2,4,5,6]]);children=module.subdivide_faces(parent,np);force=np.zeros((len(v),3));traction=np.array([2.,-3.,5.])
        for face in children:
            t=v[face];area=np.linalg.norm(np.cross(t[1]-t[0],t[2]-t[0]))/2
            for node in face:force[node]+=area*traction/3
        np.testing.assert_allclose(force.sum(0),traction/2,atol=1e-15);np.testing.assert_allclose(np.cross(v,force).sum(0),np.cross(np.array([1/3,1/3,0]),traction/2),atol=1e-15)
        displacement=v@np.array([[1,2,3],[4,-1,2],[0,3,1]])+np.array([1.,2.,3.]);expected=.5*np.dot(traction,displacement[[0,1,2]].mean(0));self.assertAlmostEqual(float((force*displacement).sum()),expected,places=13)


if __name__=='__main__':unittest.main()
