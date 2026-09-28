import importlib.util
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/wholebody'))


@unittest.skipUnless(importlib.util.find_spec('OCP') and importlib.util.find_spec('numpy'), 'optional CAD runtime')
class ConstrainedPatchTests(unittest.TestCase):
    def test_two_adjacent_rectangles_keep_their_boundary_area_and_source(self):
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
        from OCP.BRepCheck import BRepCheck_Analyzer
        from OCP.BRepGProp import BRepGProp
        from OCP.GProp import GProp_GProps
        from OCP.TopAbs import TopAbs_FACE
        from OCP.gp import gp_Pnt
        from trial_constrained_patch import exterior_edges, filling, interior_points, sampled_distance
        from trial_bounded_tip_cut import encode, indexed
        def rectangle(x):
            wire = BRepBuilderAPI_MakePolygon()
            for a, b in ((x, 0), (x+1, 0), (x+1, 1), (x, 1)): wire.Add(gp_Pnt(a, b, 0))
            wire.Close()
            return BRepBuilderAPI_MakeFace(wire.Wire()).Face()
        source = BRepAlgoAPI_Fuse(rectangle(0), rectangle(1)).Shape()
        before = encode(source); faces = indexed(source, TopAbs_FACE)
        self.assertEqual(len(exterior_edges(faces)), 6)
        result, report = filling(faces, 5)
        self.assertTrue(BRepCheck_Analyzer(result, True, False, True).IsValid())
        self.assertEqual(encode(source), before)
        self.assertEqual(report['interior_constraints'], 50)
        self.assertLess(report['reported_G0_error'], 1e-12)
        props = GProp_GProps(); BRepGProp.SurfaceProperties_s(result, props)
        self.assertAlmostEqual(props.Mass(), 2., places=10)
        self.assertLess(sampled_distance(interior_points(result, 9), source)['maximum'], 1e-10)
        from trial_trimmed_support import unify_local
        self.assertEqual(len(indexed(unify_local(source, []), TopAbs_FACE)), 1)
        self.assertEqual(len(indexed(unify_local(source, faces), TopAbs_FACE)), 2)
        with self.assertRaises(ValueError): exterior_edges([])
        with self.assertRaises(ValueError): interior_points(faces[0], 42)
        with self.assertRaises(ValueError): sampled_distance([], result)

    def test_native_support_tool_uses_fixed_surface_and_bounded_extrusion(self):
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon
        from OCP.BRepCheck import BRepCheck_Analyzer
        from OCP.BRepGProp import BRepGProp
        from OCP.GProp import GProp_GProps
        from OCP.Geom import Geom_BezierSurface
        from OCP.TColgp import TColgp_Array2OfPnt
        from OCP.gp import gp_Pnt
        from trial_trimmed_support import support_tool, encode
        poles = TColgp_Array2OfPnt(1, 2, 1, 2)
        for i in (1, 2):
            for j in (1, 2): poles.SetValue(i, j, gp_Pnt(2*i-3, 2*j-3, 0))
        surface = Geom_BezierSurface(poles)
        support = BRepBuilderAPI_MakeFace(surface, 1e-7).Face()
        wire = BRepBuilderAPI_MakePolygon()
        for x, y in ((-.5, -.5), (.5, -.5), (.5, .5), (-.5, .5)): wire.Add(gp_Pnt(x, y, .02))
        wire.Close(); lip = BRepBuilderAPI_MakeFace(wire.Wire()).Face(); before = encode(support)
        tool, report = support_tool(support, [lip], [0., 0., 1.])
        self.assertEqual(before, encode(support))
        self.assertTrue(BRepCheck_Analyzer(tool, True, False, True).IsValid())
        self.assertAlmostEqual(report['maximum_sampled_projection_gap'], .02, places=12)
        props = GProp_GProps(); BRepGProp.VolumeProperties_s(tool, props)
        self.assertAlmostEqual(props.Mass(), 1.04**2*.1, places=12)
        with self.assertRaises(ValueError): support_tool(support, [lip], [0., 0., 2.])

    def test_surface_audit_does_not_hide_a_hole_or_duplicate(self):
        import numpy as np
        from trial_compound_junction_mesh import surface_edges
        tetra = np.array([[1, 2, 3], [0, 3, 2], [0, 1, 3], [0, 2, 1]])
        self.assertEqual(surface_edges(tetra)['not_incident_twice'], 0)
        self.assertEqual(surface_edges(tetra[:-1])['not_incident_twice'], 3)
        self.assertEqual(surface_edges(np.vstack([tetra, tetra[:1]]))['duplicate_triangles'], 1)
        with self.assertRaises(ValueError): surface_edges(np.array([[0, 0, 1]]))

    def test_faceted_volume_matches_translated_analytic_box(self):
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
        from OCP.gp import gp_Pnt
        from audit_reconstruction_lip import faceted_volume
        box = BRepPrimAPI_MakeBox(gp_Pnt(100, -70, 50), 2., 3., 4.).Shape()
        result = faceted_volume(box, .001)
        self.assertAlmostEqual(result['volume'], 24., places=10)
        with self.assertRaises(ValueError): faceted_volume(box, float('nan'))

    @unittest.skipUnless(importlib.util.find_spec('vtk'), 'optional VTK distance runtime')
    def test_native_samples_measure_distance_to_triangle_not_only_vertices(self):
        import numpy as np
        from OCP.gp import gp_Pnt
        from audit_compound_shape import points_to_triangles
        p = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]])
        f = np.array([[0, 1, 2]])
        result = points_to_triangles([gp_Pnt(.2, .3, .02)], p, f)
        self.assertAlmostEqual(result['maximum'], .02, places=12)
        with self.assertRaises(ValueError): points_to_triangles([], p, f)


if __name__ == '__main__': unittest.main()
