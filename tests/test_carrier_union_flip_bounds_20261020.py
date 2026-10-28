"""Analytic controls for the diagonal-flip surface certificate."""
from fractions import Fraction as F
import importlib.util
from pathlib import Path
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/design-20261016/resume-20261020/certified_union_flip_quality.py'
SPEC=importlib.util.spec_from_file_location('carrier_union_flip_bounds',SOURCE)
M=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M)


class UnionFlipBoundTests(unittest.TestCase):
    def test_convex_planar_quad_has_exactly_zero_surface_change(self):
        bound,proof=M.flip_bound([(0,0,0),(1,1,0),(0,1,0),(1,0,0)])
        self.assertEqual(bound,0);self.assertEqual(proof['projection_dropped_axis'],2)

    def test_nonplanar_quad_has_exact_lift_bound(self):
        bound,_=M.flip_bound([(0,0,0),(1,1,0),(0,1,0),(1,0,.125)])
        self.assertEqual(bound,F(1,8))

    def test_projection_uses_an_axis_with_nonzero_plane_normal(self):
        bound,proof=M.flip_bound([(0,0,0),(0,1,1),(0,0,1),(.125,1,0)])
        self.assertEqual(bound,F(1,8));self.assertEqual(proof['projection_dropped_axis'],0)

    def test_nonconvex_projection_is_refused(self):
        with self.assertRaises(ValueError):M.flip_bound([(0,0,0),(1,1,0),(0,1,0),(-1,0,0)])

    def test_degenerate_source_plane_is_refused(self):
        with self.assertRaises(ValueError):M.flip_bound([(0,0,0),(1,1,1),(2,2,2),(0,1,0)])

    def test_exact_squared_quality_of_right_isosceles_triangle(self):
        self.assertEqual(M.quality_squared([(0,0,0),(1,0,0),(0,1,0)]),F(1,4))
