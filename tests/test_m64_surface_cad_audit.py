import importlib.util
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/flowbench-intake'))
import audit_surface_cad as audit


class TriangleTests(unittest.TestCase):
    def test_degenerate_triangle_has_no_invented_normal(self):
        r=audit.triangle_geometry([(0,0,0),(1,0,0),(2,0,0)])
        self.assertTrue(r['degenerate']);self.assertIsNone(r['normal_private'])

    def test_deterministic_partial_selection_is_bounded_unique_and_spread(self):
        indices=audit.sample_indices(2000,96)
        self.assertEqual(indices,audit.sample_indices(2000,96))
        self.assertEqual(len(set(indices)),96)
        self.assertEqual((indices[0],indices[-1]),(0,1999))
        self.assertEqual(audit.sample_indices(7,0),list(range(7)))
        self.assertEqual(audit.sample_indices(7,1),[3])
        with self.assertRaises(ValueError):audit.sample_indices(0,2)
        with self.assertRaises(ValueError):audit.sample_indices(7,-1)


@unittest.skipUnless(importlib.util.find_spec('OCP'),'native OCP runtime required')
class NativeFaceTests(unittest.TestCase):
    def face(self):
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
        from OCP.gp import gp_Pln,gp_Pnt,gp_Dir
        return BRepBuilderAPI_MakeFace(gp_Pln(gp_Pnt(0,0,0),gp_Dir(0,0,1)),0,1,0,1).Face()

    def test_oriented_plane_distinguishes_inverted_triangle(self):
        face=audit.FaceAudit(self.face());points=[(.1,.1,0),(.8,.1,0),(.1,.8,0)]
        first=face.triangle(points);second=face.triangle(list(reversed(points)))
        self.assertTrue(all(p['triangle_dot_CAD_normal']==1. for p in first['samples']))
        self.assertTrue(all(p['triangle_dot_CAD_normal']==-1. for p in second['samples']))

    def test_outside_trim_does_not_become_zero_distance_to_unbounded_plane(self):
        result=audit.FaceAudit(self.face()).point((2,.5,0))
        self.assertAlmostEqual(result['trimmed_face_distance_numeric'],1.)
        self.assertFalse(result['source_point_within_face_tolerance'])
        self.assertTrue(result['valid_trim_projection'])
        self.assertEqual(result['closest_support_kind'],'TopAbs_EDGE')
        self.assertEqual(result['selected_projection']['uv_private'],[1.,.5])

    def test_cylinder_edge_normal_is_bound_to_closest_support_not_remote_corner(self):
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
        from OCP.gp import gp_Cylinder,gp_Ax3,gp_Pnt,gp_Dir
        from unittest.mock import patch
        face=BRepBuilderAPI_MakeFace(gp_Cylinder(gp_Ax3(gp_Pnt(0,0,0),gp_Dir(0,0,1)),10.),0,math.pi,0,.01).Face()
        angle=2.4
        # Off the trimmed cylinder in z: nearest point is on a circular edge.
        # A fallback corner at angle0 would yield an opposite radial normal.
        xyz=(9.99*math.cos(angle),9.99*math.sin(angle),-.0001)
        with patch('OCP.GeomAPI.GeomAPI_ProjectPointOnSurf',side_effect=AssertionError('unrelated_projection_forbidden')):
            r=audit.FaceAudit(face).point(xyz)
        self.assertTrue(r['valid_trim_projection'])
        self.assertEqual(r['closest_support_kind'],'TopAbs_EDGE')
        self.assertLess(r['closest_support_surface_binding_error'],1e-12)
        self.assertAlmostEqual(r['selected_projection']['uv_private'][0],angle)
        self.assertAlmostEqual(r['selected_projection']['distance'],r['trimmed_face_distance_numeric'])
        self.assertGreater(audit.dot(r['normal_private'],(math.cos(angle),math.sin(angle),0)),.999999)

    def test_nonzero_offset_is_measured_and_not_called_conformity_proof(self):
        r=audit.FaceAudit(self.face()).triangle([(.1,.1,.02),(.8,.1,.02),(.1,.8,.02)])
        self.assertAlmostEqual(r['samples'][0]['trimmed_face_distance_numeric'],.02)
        self.assertTrue(r['samples_do_not_bound_entire_triangle'])

    def test_straight_ribbon_reports_real_width_and_no_invented_curvature(self):
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
        from OCP.gp import gp_Pln,gp_Pnt,gp_Dir
        face=BRepBuilderAPI_MakeFace(gp_Pln(gp_Pnt(0,0,0),gp_Dir(0,0,1)),0,100,0,1).Face()
        r=audit.sampled_border_resolution(face)
        self.assertAlmostEqual(r['sampled_interior_width_min'],1.)
        self.assertEqual(r['sampled_curvature_max'],0.)
        self.assertIsNone(r['refinement_hypothesis']['suggested_maximum_edge_length_from_samples'])
        self.assertFalse(r['global_width_minimum_or_curvature_maximum_proven'])

    def test_circular_ribbon_sagitta_hypothesis_is_numerical_not_acceptance(self):
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
        from OCP.gp import gp_Cylinder,gp_Ax3,gp_Pnt,gp_Dir
        face=BRepBuilderAPI_MakeFace(gp_Cylinder(gp_Ax3(gp_Pnt(0,0,0),gp_Dir(0,0,1)),10.),0,math.pi,0,1).Face()
        r=audit.sampled_border_resolution(face)
        self.assertAlmostEqual(r['sampled_interior_width_min'],1.)
        self.assertAlmostEqual(r['sampled_curvature_max'],.1)
        self.assertAlmostEqual(r['refinement_hypothesis']['suggested_maximum_edge_length_from_samples'],math.sqrt(20.))
        self.assertFalse(r['refinement_hypothesis']['admissibility_or_physical_precision_claim'])


if __name__=='__main__':unittest.main()
