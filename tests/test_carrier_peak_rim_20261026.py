"""Patch-rim diagnostics preserve internal seams and exact segment distances."""
import importlib.util
from pathlib import Path
import sys
import unittest
import numpy as np
S=Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/design-20261016/convergence-20261022';sys.path.insert(0,str(S));spec=importlib.util.spec_from_file_location('carrier_peak_rim',S/'diagnose_boundary_peak.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class RimTests(unittest.TestCase):
    def test_segment_projection_uses_interior_and_clamps_endpoints(self):
        segments=np.array([[[0.,0,0],[2,0,0]]]);self.assertAlmostEqual(m.distance(np.array([1.,3,0]),segments)['distance_mm'],3);self.assertAlmostEqual(m.distance(np.array([3.,0,0]),segments)['distance_mm'],1)

    def test_one_quadratic_face_has_six_rim_segments_not_internal_diagonals(self):
        v=np.array([[0.,0,0],[2,0,0],[0,2,0],[1,0,0],[1,1,0],[0,1,0]]);segments,count=m.rim(v,np.array([[0,1,2,3,4,5]]),np.arange(6));self.assertEqual(count,1);self.assertEqual(len(segments),6);self.assertAlmostEqual(m.distance(np.array([.5,.5,1]),segments)['distance_mm'],np.sqrt(1.25))

    def test_degenerate_segment_and_incomplete_patch_are_refused(self):
        with self.assertRaises(ValueError):m.distance(np.zeros(3),np.zeros((1,2,3)))
        with self.assertRaises(ValueError):m.rim(np.zeros((6,3)),np.array([[0,1,2,3,4,5]]),np.array([0,1,2]))


if __name__=='__main__':unittest.main()
