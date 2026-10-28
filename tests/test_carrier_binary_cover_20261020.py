"""Exact dyadic geometry and split-history checks for binary surface covers."""
from fractions import Fraction as Q
import importlib.util
from pathlib import Path
import unittest
import numpy as np

SOURCE=Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/design-20261016/resume-20261020/interval_surface_cover_bisect.py'
spec=importlib.util.spec_from_file_location('_binary_cover_math',SOURCE);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class BinaryCoverTests(unittest.TestCase):
    def test_all_three_edge_bisections_enclose_the_exact_half_triangles(self):
        points=[tuple(map(Q,p))for p in [(.1,-.2,300.),(.3,.7,-299.),(-.4,.9,4.)]]
        values=np.array([list(map(float,p))for p in points]);lo=np.repeat(values[None,:,:],3,axis=0);hi=lo.copy()
        child_lo,child_hi=module.split(lo,hi,np.arange(3),np)
        for edge in range(3):
            i=edge;j=(edge+1)%3;k=(edge+2)%3;mid=tuple((points[i][axis]+points[j][axis])/2 for axis in range(3));expected=[(points[i],mid,points[k]),(mid,points[j],points[k])]
            for child in range(2):
                for vertex in range(3):
                    for axis in range(3):
                        self.assertLessEqual(Q(float(child_lo[2*edge+child,vertex,axis])),expected[child][vertex][axis]);self.assertGreaterEqual(Q(float(child_hi[2*edge+child,vertex,axis])),expected[child][vertex][axis])

    def test_partition_requires_consistent_split_edges_as_well_as_complete_addresses(self):
        def check(paths,depths,histories):return module.binary_coverage(np.zeros(len(paths),dtype=np.uint32),np.array(paths,dtype=np.uint64),np.array(depths,dtype=np.uint8),np.array(histories,dtype=np.uint64),1,np)
        self.assertTrue(check([0],[0],[0]))
        self.assertTrue(check([0,1],[1,1],[2,2]))
        # Root edge0; left child retained; right child bisected along edge2.
        self.assertTrue(check([0,2,3],[1,2,2],[0,2,2]))
        self.assertFalse(check([0,2],[1,2],[0,2]))
        self.assertFalse(check([0,2,2],[1,2,2],[0,2,2]))
        self.assertFalse(check([0,2,3],[1,2,2],[0,1,2]))
        self.assertFalse(check([0,2,3],[1,2,2],[0,6,6]))


if __name__=='__main__':unittest.main()
