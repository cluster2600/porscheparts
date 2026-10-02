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
        from OCP.TopExp import TopExp
        from OCP.TopoDS import TopoDS
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
        boundary = exterior_edges(faces)
        self.assertEqual(len(boundary), 6)
        self.assertTrue(all(TopExp.LastVertex_s(TopoDS.Edge_s(a), True).IsSame(
            TopExp.FirstVertex_s(TopoDS.Edge_s(b), True))
            for a, b in zip(boundary, boundary[1:]+boundary[:1])))
        with self.assertRaises(ValueError): exterior_edges([rectangle(0), rectangle(3)])
        result, report = filling(faces, 5)
        self.assertTrue(BRepCheck_Analyzer(result, True, False, True).IsValid())
        self.assertEqual(encode(source), before)
        self.assertEqual(report['interior_constraints'], 50)
        self.assertLess(report['reported_G0_error'], 1e-12)
        initialized, initial_report = filling(faces, 5, faces[0])
        self.assertTrue(BRepCheck_Analyzer(initialized, True, False, True).IsValid())
        self.assertTrue(initial_report['native_initial_plane'])
        self.assertLess(initial_report['reported_G0_error'], 1e-12)
        self.assertEqual(encode(source), before)
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

    def test_projection_fixes_only_selected_points_and_rejects_large_shift(self):
        import numpy as np
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
        from OCP.gp import gp_Pln
        from trial_project_compound_surface import project_points
        from trial_bounded_tip_cut import encode
        plane = BRepBuilderAPI_MakeFace(gp_Pln(), -1., 1., -1., 1.).Face()
        before = encode(plane)
        points = np.array([[-.5, -.5, 0.], [.5, -.5, 0.], [.5, .5, 0.], [-.5, .5, 0.], [0., 0., .02]])
        original = points.copy(); mask = np.array([False, False, False, False, True])
        result = project_points(points, plane, mask)
        np.testing.assert_array_equal(result[:4], points[:4])
        np.testing.assert_allclose(result[-1], [0., 0., 0.], atol=1e-12)
        np.testing.assert_array_equal(points, original)
        self.assertEqual(encode(plane), before)
        points[-1, 2] = .2
        with self.assertRaises(ValueError): project_points(points, plane, mask)
        with self.assertRaises(ValueError): project_points(original, plane, mask.astype(int))
        with self.assertRaises(ValueError): project_points(original, plane, np.zeros(5, dtype=bool))

    def test_local_refinement_preserves_boundary_orientation_area_and_source(self):
        import numpy as np
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
        from OCP.gp import gp_Pln
        from trial_project_compound_surface import refine_patch
        plane = BRepBuilderAPI_MakeFace(gp_Pln(), -1., 1., -1., 1.).Face()
        p = np.array([[-.5, -.5, 0.], [.5, -.5, 0.], [.5, .5, 0.], [-.5, .5, 0.], [0., 0., 0.]])
        f = np.array([[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4]])
        q, g, parents = refine_patch(p, f, plane)
        np.testing.assert_array_equal(q[:len(p)], p)
        self.assertEqual((len(q), len(g)), (9, 12))
        self.assertEqual(set(parents), {0, 1, 2, 3})
        cross = np.cross(q[g[:, 1]]-q[g[:, 0]], q[g[:, 2]]-q[g[:, 0]])
        self.assertTrue((cross[:, 2] > 0).all())
        self.assertAlmostEqual(float(cross[:, 2].sum()/2), 1.)
        edges, count = np.unique(np.sort(np.concatenate([g[:, e] for e in ((0, 1), (1, 2), (2, 0))]), axis=1), axis=0, return_counts=True)
        self.assertTrue((count <= 2).all())
        self.assertEqual({tuple(e) for e in edges[count == 1]}, {(0, 1), (1, 2), (2, 3), (0, 3)})
        # A centre triangle plus its three neighbours exercises 0, 1 and 3 splits.
        p2 = np.array([[0., 0., 0.], [.4, 0., 0.], [0., .4, 0.], [.4, -.4, 0.], [.4, .4, 0.], [-.4, .4, 0.], [-.8, -.8, 0.], [-.6, -.8, 0.], [-.8, -.6, 0.]])
        f2 = np.array([[0, 1, 2], [1, 0, 3], [2, 1, 4], [0, 2, 5], [6, 7, 8]])
        q, g, parents = refine_patch(p2, f2, plane)
        self.assertEqual(len(g), 11)
        self.assertTrue((np.cross(q[g[:, 1]]-q[g[:, 0]], q[g[:, 2]]-q[g[:, 0]])[:, 2] > 0).all())
        with self.assertRaises(ValueError): refine_patch(p, np.vstack([f, f[:1]]), plane)

    def test_surface_audit_does_not_hide_a_hole_or_duplicate(self):
        import numpy as np
        from trial_compound_junction_mesh import surface_edges
        tetra = np.array([[1, 2, 3], [0, 3, 2], [0, 1, 3], [0, 2, 1]])
        self.assertEqual(surface_edges(tetra)['not_incident_twice'], 0)
        self.assertEqual(surface_edges(tetra[:-1])['not_incident_twice'], 3)
        self.assertEqual(surface_edges(np.vstack([tetra, tetra[:1]]))['duplicate_triangles'], 1)
        with self.assertRaises(ValueError): surface_edges(np.array([[0, 0, 1]]))

    def test_two_projected_midpoints_choose_an_orientation_preserving_diagonal(self):
        import numpy as np
        from trial_project_compound_surface import split_edges
        # The projected BC midpoint is inside the original triangle: XC folds,
        # but AY triangulates the same five boundary vertices without a fold.
        p = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.], [.5, 0., 0.], [.2, .5, 0.]])
        edges = np.array([[0, 1], [1, 2]])
        for row in ([0, 1, 2], [1, 2, 0], [2, 0, 1], [2, 1, 0]):
            g, parents = split_edges(np.array([row]), edges, 3, p)
            normals = np.cross(p[g[:, 1]]-p[g[:, 0]], p[g[:, 2]]-p[g[:, 0]])
            old = np.cross(p[row[1]]-p[row[0]], p[row[2]]-p[row[0]])
            self.assertTrue((normals@old > 0).all())
            np.testing.assert_allclose(normals.sum(axis=0), .7*old)
            np.testing.assert_array_equal(parents, [0, 0, 0])
            es, count = np.unique(np.sort(np.concatenate([g[:, e] for e in ((0, 1), (1, 2), (2, 0))]), axis=1), axis=0, return_counts=True)
            self.assertEqual({tuple(e) for e in es[count == 1]}, {(0, 3), (1, 3), (1, 4), (2, 4), (0, 2)})
        p[4] = [.2, -.2, 0.]
        g, _ = split_edges(np.array([[0, 1, 2]]), edges, 3, p)
        # Neither diagonal is valid: retain the failure for the caller's gate.
        self.assertTrue((np.cross(p[g[:, 1]]-p[g[:, 0]], p[g[:, 2]]-p[g[:, 0]])[:, 2] <= 0).any())

    @unittest.skipUnless(importlib.util.find_spec('gmsh'), 'optional Gmsh runtime')
    def test_shape_witnesses_select_only_nearby_triangles(self):
        import numpy as np
        from trial_project_compound_surface import witness_region
        p = np.array([[0., 0., 0.], [.2, 0., 0.], [0., .2, 0.], [2., 0., 0.], [2.2, 0., 0.], [2., .2, 0.]])
        f = np.array([[0, 1, 2], [3, 4, 5]])
        np.testing.assert_array_equal(witness_region(p, f, [[0., 0., 0.], [.1, 0., 0.]]), [True, False])
        np.testing.assert_array_equal(witness_region(p, f, [[0., 0., 0.], [.1, 0., 0.], [2., 0., 0.]]), [True, True])
        with self.assertRaises(ValueError): witness_region(p, f, [[0., 0., 0.], [float('nan'), 0., 0.]])
        with self.assertRaises(ValueError): witness_region(p, f, np.zeros((40001, 3)))
        # A shape audit must bind the parent receipt too, not just its mesh.
        import argparse
        import json
        import tempfile
        from trial_project_compound_surface import run, native, BODY_SHA
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            body, mesh, receipt, audit = [root/name for name in ('body.brep', 'mesh.msh', 'receipt.json', 'audit.json')]
            body.write_text('not a real body'); mesh.write_text('not a real mesh')
            receipt.write_text(json.dumps({'necessary_surface_checks_passed': True}))
            data = dict(schema='m64-compound-native-shape-samples/v1', status='completed_diagnostic_only',
                        inputs_unchanged=True, source_hashes={body.name: BODY_SHA, mesh.name: native.sha256(mesh), receipt.name: 'wrong'})
            audit.write_text(json.dumps(data))
            args = argparse.Namespace(body=body, mesh=mesh, receipt=receipt, local_shape_witnesses=audit,
                                      split_interior_edges=True, split_shared_boundaries=False,
                                      all_shape_exceedances=False, output=root/'out')
            with self.assertRaisesRegex(ValueError, 'bound_completed_shape_audit'):
                run(args)
            data['source_hashes'][receipt.name] = native.sha256(receipt)
            audit.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'pinned_classified_parent'):
                run(args)
            args.all_shape_exceedances = True
            data['groups'] = {name: {direction: dict(maximum=.05, exceedance_limit_scan_units=.040,
                exceedance_points_private=[]) for direction in ('mesh_to_native', 'native_to_mesh')}
                for name in ('lower', 'upper')}
            audit.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'complete_bounded_0040'):
                run(args)
            self.assertFalse(args.output.exists())

    def test_three_projected_midpoints_retriangulate_the_same_concave_boundary(self):
        import numpy as np
        from trial_project_compound_surface import split_edges
        p = np.array([[0., 0., 0.], [1., 0., 0.], [1.22, .52, 0.],
                      [.4, -.18, 0.], [.92, .13, 0.], [1.11, .26, 0.]])
        original = p.copy(); edges = np.array([[0, 1], [0, 2], [1, 2]])
        default = np.array([[0, 3, 4], [3, 1, 5], [4, 5, 2], [3, 5, 4]])
        cross = lambda f: np.cross(p[f[:, 1]]-p[f[:, 0]], p[f[:, 2]]-p[f[:, 0]])
        self.assertTrue((cross(default)[:, 2] < 0).any())
        for row in ([0, 1, 2], [1, 2, 0], [2, 1, 0]):
            f, parents = split_edges(np.array([row]), edges, 3, p)
            sign = np.sign(np.cross(p[row[1]]-p[row[0]], p[row[2]]-p[row[0]])[2])
            self.assertEqual(len(f), 4)
            self.assertTrue((cross(f)[:, 2]*sign > 0).all())
            np.testing.assert_allclose(cross(f).sum(axis=0), sign*cross(default).sum(axis=0))
            es, count = np.unique(np.sort(np.concatenate([f[:, e] for e in ((0, 1), (1, 2), (2, 0))]), axis=1), axis=0, return_counts=True)
            self.assertEqual({tuple(e) for e in es[count == 1]}, {(0, 3), (1, 3), (1, 5), (2, 5), (2, 4), (0, 4)})
            self.assertTrue((count <= 2).all())
            np.testing.assert_array_equal(parents, [0, 0, 0, 0])
        np.testing.assert_array_equal(p, original)

    def test_feature_midpoints_follow_shared_native_edge_not_nearest_face(self):
        import numpy as np
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
        from OCP.BRepAdaptor import BRepAdaptor_Surface
        from OCP.TopAbs import TopAbs_FACE
        from OCP.TopoDS import TopoDS
        from trial_constrained_patch import indexed, compound
        from trial_bounded_tip_cut import encode
        from trial_project_compound_surface import feature_midpoints, project_points
        faces = indexed(BRepPrimAPI_MakeBox(1., 1., 1.).Shape(), TopAbs_FACE)
        bottom = next(f for f in faces if abs(BRepAdaptor_Surface(TopoDS.Face_s(f)).Plane().Axis().Direction().Z()) > .9
                      and abs(BRepAdaptor_Surface(TopoDS.Face_s(f)).Plane().Location().Z()) < 1e-12)
        front = next(f for f in faces if abs(BRepAdaptor_Surface(TopoDS.Face_s(f)).Plane().Axis().Direction().Y()) > .9
                     and abs(BRepAdaptor_Surface(TopoDS.Face_s(f)).Plane().Location().Y()) < 1e-12)
        target = compound([bottom, front]); before = encode(target)
        p = np.array([[.4, .04, 0.], [.6, 0., .06], [.7, .02, 0.]])
        original = p.copy(); edges = np.array([[0, 1], [0, 2]])
        near = project_points(p[edges].mean(axis=1), target, np.ones(2, dtype=bool))
        self.assertGreater(float(np.linalg.norm(near[0]-[.5, 0., 0.])), .01)
        np.testing.assert_allclose(feature_midpoints(p, edges, target), [[.5, 0., 0.], [.55, .03, 0.]], atol=1e-12)
        np.testing.assert_array_equal(p, original); self.assertEqual(encode(target), before)
        with self.assertRaisesRegex(ValueError, 'endpoint_on_native_face'):
            feature_midpoints(p+np.array([0., 0., .01]), edges, target)
        with self.assertRaises(ValueError): feature_midpoints(p, np.array([[0, 3]]), target)
        with self.assertRaises(ValueError): feature_midpoints(p, np.tile(edges, (129, 1)), target)
        # Geometrically nearby but topologically disconnected faces cannot claim a seam.
        from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy
        separate = compound([bottom, BRepBuilderAPI_Copy(front, True, False).Shape()])
        with self.assertRaisesRegex(ValueError, 'unique_common_native_feature'):
            feature_midpoints(p, edges[:1], separate)

    def test_shared_curve_refinement_splits_both_faces_without_moving_old_nodes(self):
        import numpy as np
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder, BRepPrimAPI_MakeBox
        from OCP.BRepAdaptor import BRepAdaptor_Surface
        from OCP.GeomAbs import GeomAbs_Cylinder
        from OCP.TopAbs import TopAbs_FACE
        from OCP.TopoDS import TopoDS
        from trial_constrained_patch import indexed
        from trial_bounded_tip_cut import encode
        from trial_project_compound_surface import refine_shared_boundaries
        body = BRepPrimAPI_MakeCylinder(1., 1.).Shape(); before = encode(body)
        faces = indexed(body, TopAbs_FACE)
        side = next(f for f in faces if BRepAdaptor_Surface(TopoDS.Face_s(f)).GetType() == GeomAbs_Cylinder)
        cap = next(f for f in faces if BRepAdaptor_Surface(TopoDS.Face_s(f)).GetType() != GeomAbs_Cylinder
                   and abs(BRepAdaptor_Surface(TopoDS.Face_s(f)).Plane().Location().Z()) < 1e-12)
        p = np.array([[np.cos(.3), -np.sin(.3), 0.], [np.cos(.3), np.sin(.3), 0.],
                      [.5, 0., 0.], [1., 0., .3]])
        f = np.array([[0, 1, 2], [1, 0, 3]]); owners = np.array([11, 12])
        q, g, parents, report = refine_shared_boundaries(p, f, owners, {11: cap, 12: side}, {'cap': [11]})
        np.testing.assert_array_equal(q[:4], p)
        np.testing.assert_allclose(q[4], [1., 0., 0.], atol=1e-12)
        self.assertEqual((len(q), len(g)), (5, 4))
        self.assertEqual(sorted(parents), [0, 0, 1, 1])
        self.assertEqual(report['shared_edges'], 1)
        self.assertEqual(report['neighbour_face_tags_private'], [12])
        self.assertEqual(encode(body), before)
        edges, counts = np.unique(np.sort(np.concatenate([g[:, e] for e in ((0, 1), (1, 2), (2, 0))]), axis=1), axis=0, return_counts=True)
        incidence = {tuple(e): int(n) for e, n in zip(edges, counts)}
        self.assertNotIn((0, 1), incidence)
        self.assertEqual((incidence[(0, 4)], incidence[(1, 4)]), (2, 2))
        normal = lambda xyz: np.cross(xyz[:, 1]-xyz[:, 0], xyz[:, 2]-xyz[:, 0])
        self.assertTrue((np.einsum('ij,ij->i', normal(p[f])[parents], normal(q[g])) > 0).all())
        unrelated = indexed(BRepPrimAPI_MakeBox(1., 1., 1.).Shape(), TopAbs_FACE)[0]
        with self.assertRaises(ValueError): refine_shared_boundaries(p, f, owners, {11: cap, 12: unrelated}, {'cap': [11]})
        with self.assertRaises(ValueError): refine_shared_boundaries(p, np.vstack([f, f[:1]]), np.array([11, 12, 11]), {11: cap, 12: side}, {'cap': [11]})

        # A native straight common edge already matches its chord exactly.
        box_faces = indexed(BRepPrimAPI_MakeBox(1., 1., 1.).Shape(), TopAbs_FACE)
        bottom = next(face for face in box_faces if
            abs(BRepAdaptor_Surface(TopoDS.Face_s(face)).Plane().Axis().Direction().Z()) > .9
            and abs(BRepAdaptor_Surface(TopoDS.Face_s(face)).Plane().Location().Z()) < 1e-12)
        front = next(face for face in box_faces if
            abs(BRepAdaptor_Surface(TopoDS.Face_s(face)).Plane().Axis().Direction().Y()) > .9
            and abs(BRepAdaptor_Surface(TopoDS.Face_s(face)).Plane().Location().Y()) < 1e-12)
        p = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.], [0., 0., 1.]])
        q, g, parents, report = refine_shared_boundaries(p, f, owners, {11: bottom, 12: front}, {'cap': [11]})
        np.testing.assert_array_equal(q, p); np.testing.assert_array_equal(g, f)
        np.testing.assert_array_equal(parents, [0, 1])
        self.assertEqual(report['shared_edges'], 0)
        self.assertEqual(report['skipped_exact_straight_edges'], 1)

    def test_faceted_volume_matches_translated_analytic_box(self):
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
        from OCP.gp import gp_Pnt
        from audit_reconstruction_lip import faceted_volume
        box = BRepPrimAPI_MakeBox(gp_Pnt(100, -70, 50), 2., 3., 4.).Shape()
        result = faceted_volume(box, .001)
        self.assertAlmostEqual(result['volume'], 24., places=10)
        with self.assertRaises(ValueError): faceted_volume(box, float('nan'))

    @unittest.skipUnless(importlib.util.find_spec('gmsh'), 'optional Gmsh runtime')
    def test_patch_sizing_refines_selected_surface_not_separate_control(self):
        import gmsh
        import numpy as np
        from trial_compound_junction_mesh import restrict_patch_size
        gmsh.initialize(['patch-sizing-test', '-nopopup'], readConfigFiles=False, run=False)
        try:
            gmsh.option.setNumber('General.Terminal', 0)
            a = gmsh.model.occ.addRectangle(0, 0, 0, 1, 1)
            b = gmsh.model.occ.addRectangle(4, 0, 0, 1, 1)
            gmsh.model.occ.synchronize()
            for key, value in {'Mesh.MeshSizeFromPoints': 0, 'Mesh.MeshSizeFromCurvature': 0,
                               'Mesh.MeshSizeMin': .01, 'Mesh.MeshSizeMax': .5}.items():
                gmsh.option.setNumber(key, value)
            field = restrict_patch_size(gmsh, [a], .1)
            gmsh.model.mesh.field.setAsBackgroundMesh(field); gmsh.model.mesh.generate(2)
            _, ea, na = gmsh.model.mesh.getElements(2, a)
            _, eb, _ = gmsh.model.mesh.getElements(2, b)
            self.assertGreater(len(ea[0]), 4*len(eb[0]))
            p = np.array([gmsh.model.mesh.getNode(int(i))[0] for i in na[0]]).reshape(-1, 3, 3)
            self.assertLess(np.linalg.norm(p-np.roll(p, 1, axis=1), axis=2).max(), .16)
            with self.assertRaises(ValueError): restrict_patch_size(gmsh, [], .1)
            with self.assertRaises(ValueError): restrict_patch_size(gmsh, [a], float('nan'))
        finally: gmsh.finalize()

    @unittest.skipUnless(importlib.util.find_spec('vtk'), 'optional VTK distance runtime')
    def test_native_samples_measure_distance_to_triangle_not_only_vertices(self):
        import numpy as np
        from OCP.gp import gp_Pnt
        from audit_compound_shape import points_to_triangles
        p = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]])
        f = np.array([[0, 1, 2]])
        result = points_to_triangles([gp_Pnt(.2, .3, .02)], p, f)
        self.assertAlmostEqual(result['maximum'], .02, places=12)
        witness = result['maximum_witness_private']
        self.assertEqual(witness['sample_index'], 0)
        np.testing.assert_allclose(witness['closest'], [.2, .3, 0.], atol=1e-12)
        self.assertEqual(witness['triangle'], p.tolist())
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace
        from trial_constrained_patch import sampled_distance
        wire = BRepBuilderAPI_MakePolygon()
        for row in p: wire.Add(gp_Pnt(*row))
        wire.Close()
        native = sampled_distance([gp_Pnt(.2, .3, .01), gp_Pnt(.2, .3, .02)],
                                  BRepBuilderAPI_MakeFace(wire.Wire()).Face())
        self.assertEqual(native['maximum_witness_private']['sample_index'], 1)
        self.assertAlmostEqual(native['maximum'], .02, places=12)
        np.testing.assert_allclose(native['maximum_witness_private']['closest'], [.2, .3, 0.], atol=1e-12)
        with self.assertRaises(ValueError): points_to_triangles([], p, f)

        samples = [gp_Pnt(.2, .3, z) for z in (.01, .04, .05, .08)]
        plane = BRepBuilderAPI_MakeFace(wire.Wire()).Face()
        for result in (sampled_distance(samples, plane, .04), points_to_triangles(samples, p, f, .04)):
            self.assertEqual(result['samples'], 4)
            self.assertEqual(result['exceedance_limit_scan_units'], .04)
            np.testing.assert_allclose(result['exceedance_points_private'], [[.2, .3, .05], [.2, .3, .08]])
            self.assertAlmostEqual(result['maximum'], .08)
        with self.assertRaises(ValueError): sampled_distance(samples, plane, float('nan'))
        with self.assertRaises(ValueError): points_to_triangles(samples, p, f, 0.)


if __name__ == '__main__': unittest.main()
