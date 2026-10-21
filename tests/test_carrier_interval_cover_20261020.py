"""Rational adversarial checks of the outward-rounded continuous cover proof."""
from fractions import Fraction as Q
import importlib.util
from pathlib import Path
import random
import unittest
import numpy as np

SOURCE=Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/design-20261016/resume-20261020/interval_surface_cover.py'
spec=importlib.util.spec_from_file_location('_interval_surface_math',SOURCE);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class IntervalCoverTests(unittest.TestCase):
    def test_binary_interval_bound_contains_exact_rational_witness_distances(self):
        rng=random.Random(20261020);n=32
        targets=np.array([[[rng.uniform(-400,400)for _ in range(3)]for _ in range(3)]for _ in range(n)])
        source=np.array([[[rng.uniform(-400,400)for _ in range(3)]for _ in range(3)]for _ in range(n)])
        weights=np.empty((n,3,3),dtype=np.uint32)
        for i in range(n):
            for j in range(3):
                a=rng.randrange(module.DEN+1);b=rng.randrange(module.DEN-a+1);weights[i,j]=[a,b,module.DEN-a-b]
        targets[0]=[[300.,-300.,4.],[300.+2**-30,-300.,4.],[300.,-300.+2**-30,4.]]
        source[0]=targets[0];weights[0]=np.eye(3,dtype=np.uint32)*module.DEN
        lo=np.nextafter(source,-np.inf);hi=np.nextafter(source,np.inf);upper=module.witness_bound_squared(lo,hi,targets,weights,np)
        for i in range(n):
            exact=Q(0)
            for j in range(3):
                value=Q(0)
                for axis in range(3):
                    q=sum(Q(int(weights[i,j,k]))*Q(float(targets[i,k,axis]))for k in range(3))/module.DEN
                    value+=max((Q(float(lo[i,j,axis]))-q)**2,(Q(float(hi[i,j,axis]))-q)**2)
                exact=max(exact,value)
            self.assertGreaterEqual(Q(float(upper[i])),exact)
        proposed=module.convex_weights(source[:,0],targets,np)
        self.assertTrue(np.all(proposed.sum(axis=1,dtype=np.uint64)==module.DEN))

    def test_every_recursive_child_interval_contains_the_exact_dyadic_child(self):
        points=[tuple(map(Q,p))for p in [(.1,-.2,300.),(.3,.7,-299.),(-.4,.9,4.)]]
        lo=np.array([[list(map(float,p))for p in points]]);hi=lo.copy()
        for _ in range(6):
            child_lo,child_hi=module.children(lo,hi,np)
            ab=tuple((points[0][k]+points[1][k])/2 for k in range(3));bc=tuple((points[1][k]+points[2][k])/2 for k in range(3));ac=tuple((points[0][k]+points[2][k])/2 for k in range(3))
            expected=[(points[0],ab,ac),(ab,points[1],bc),(ac,bc,points[2]),(ab,bc,ac)]
            for child in range(4):
                for vertex in range(3):
                    for axis in range(3):
                        self.assertLessEqual(Q(float(child_lo[child,vertex,axis])),expected[child][vertex][axis]);self.assertGreaterEqual(Q(float(child_hi[child,vertex,axis])),expected[child][vertex][axis])
            points=list(expected[3]);lo=child_lo[3:4].copy();hi=child_hi[3:4].copy()

    def test_quadtree_partition_refuses_gaps_overlaps_and_missing_source_faces(self):
        def checked(faces,paths,depths,count=1):return module.coverage(np.array(faces,dtype=np.uint32),np.array(paths,dtype=np.uint64),np.array(depths,dtype=np.uint8),count,4,np)
        self.assertTrue(checked([0],[0],[0]))
        self.assertTrue(checked([0]*4,list(range(4)),[1]*4))
        self.assertFalse(checked([0]*3,[0,1,2],[1]*3))
        self.assertFalse(checked([0]*4,[0,1,2,2],[1]*4))
        self.assertFalse(checked([1],[0],[0],2))


if __name__=='__main__':unittest.main()
