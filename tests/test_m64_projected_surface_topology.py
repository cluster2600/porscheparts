import importlib.util
import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/wholebody'))


@unittest.skipUnless(importlib.util.find_spec('numpy') and importlib.util.find_spec('scipy'), 'optional numpy/scipy runtime')
class ProjectedSurfaceTopologyTests(unittest.TestCase):
    def test_rejected_cells_boundary_face_contacts_are_not_only_vertex_contacts(self):
        import numpy as np
        from audit_faceted_volume_failures import boundary_contacts
        cells=np.array([[0,1,2,3],[0,4,5,6],[4,5,6,7]])
        faces=np.array([[0,1,2],[0,1,3],[0,2,3],[1,2,3]])
        result=boundary_contacts(cells,faces)
        self.assertEqual(result['boundary_vertex_count_histogram'],[1,1,0,0,1])
        self.assertEqual(result['boundary_face_count_histogram'],[2,0,0,0,1])
        self.assertEqual(boundary_contacts(cells[:0],faces)['boundary_face_count_histogram'],[0]*5)
        with self.assertRaises(ValueError): boundary_contacts(cells.astype(float),faces)

    @unittest.skipUnless(importlib.util.find_spec('gmsh'), 'optional Gmsh runtime')
    def test_optimisation_refreshes_element_cache_after_topology_changes(self):
        import numpy as np
        import gmsh
        from trial_audited_discrete_volume import optimize_volume
        if gmsh.__version__ != '4.15.2': self.skipTest('qualified Gmsh 4.15.2 required')
        gmsh.initialize(['cache-test','-nopopup'],readConfigFiles=False,run=False)
        gmsh.option.setNumber('General.Terminal',0)
        try:
            gmsh.model.occ.addBox(0,0,0,1,1,1); gmsh.model.occ.synchronize()
            for key,value in {'Mesh.MeshSizeMin':.3,'Mesh.MeshSizeMax':.3,
                    'Mesh.Optimize':0,'Mesh.Renumber':0,'General.NumThreads':1}.items():
                gmsh.option.setNumber(key,value)
            gmsh.model.mesh.generate(3)
            tags=gmsh.model.mesh.getElements(3)[1][0]
            gmsh.model.mesh.getElementQualities(tags,'minSICN')  # Populate the old cache.
            optimize_volume(gmsh,'default')
            current=gmsh.model.mesh.getElements(3)[1][0]
            self.assertGreater(len(np.setdiff1d(current,tags)),0)
            qualities=gmsh.model.mesh.getElementQualities(current,'minSICN')
            self.assertEqual(len(qualities),len(current)); self.assertTrue(np.isfinite(qualities).all())
        finally: gmsh.finalize()

    @unittest.skipUnless(importlib.util.find_spec('gmsh'), 'optional Gmsh runtime')
    def test_discrete_volume_keeps_boundary_and_rejects_winding_or_coordinate_change(self):
        import numpy as np
        import gmsh
        from trial_audited_discrete_volume import generate, check_boundary, OPTIMIZERS
        if gmsh.__version__ != '4.15.2': self.skipTest('qualified Gmsh 4.15.2 required')
        p = np.array([[0.,0.,0.], [1.,0.,0.], [0.,1.,0.], [0.,0.,1.]])
        f = np.array([[0,2,1],[0,1,3],[0,3,2],[1,2,3]])
        gmsh.initialize(['discrete-test','-nopopup'],readConfigFiles=False,run=False)
        gmsh.option.setNumber('General.Terminal',0)
        try:
            generate(gmsh,p,f)
            self.assertTrue(check_boundary(gmsh,p,f[:,[1,2,0]][::-1]))
            types, elements, _ = gmsh.model.mesh.getElements(3)
            self.assertEqual(list(types),[4]); self.assertGreater(len(elements[0]),0)
            self.assertTrue((gmsh.model.mesh.getElementQualities(elements[0],'minDetJac')>0).all())
            with self.assertRaisesRegex(ValueError,'oriented_boundary'):
                check_boundary(gmsh,p,f[:,::-1])
            altered=p.copy(); altered[0,0]=1e-12
            with self.assertRaisesRegex(ValueError,'exact_boundary_nodes'):
                check_boundary(gmsh,altered,f)
            gmsh.clear(); generate(gmsh,p,f,extend_size=False)
            self.assertTrue(check_boundary(gmsh,p,f))
            for method in OPTIMIZERS.values():
                gmsh.model.mesh.optimize(method,force=True)
                self.assertTrue(check_boundary(gmsh,p,f))
        finally: gmsh.finalize()

    def test_curve_subdivision_preserves_direction_and_requires_unique_parent(self):
        import numpy as np
        from trial_project_compound_surface import split_curve_lines, update_stored_curves
        old = np.array([[2, 1], [2, 3]], dtype=np.uint64)
        new, used = split_curve_lines(old, {(1, 2): 4})
        np.testing.assert_array_equal(new, [[2, 4], [4, 1], [2, 3]])
        np.testing.assert_array_equal(old, [[2, 1], [2, 3]])
        self.assertEqual(used, {(1, 2)})
        for lines, split in ((old, {(1, 2): 1}), (old.astype(float), {}),
                             (np.array([[1, 2], [2, 1]]), {}),
                             (np.array([[1, 2], [1, 4]]), {(1, 2): 4})):
            with self.assertRaises(ValueError): split_curve_lines(lines, split)
        class Mesh:
            def getElements(self, dim, tag): return [1], [[1, 2]], [old.ravel()]
            def removeElements(self, *args): raise AssertionError('must validate before mutation')
        class Model:
            mesh = Mesh()
            def getEntities(self, dim): return [(1, 7)]
        class API: model = Model()
        with self.assertRaisesRegex(ValueError, 'every_split_requires_stored_curve_parent'):
            update_stored_curves(API(), {(8, 9): 10})
        from reconcile_projected_curves import recover_bisections
        children = np.array([[4, 1], [2, 4], [5, 2], [3, 5]])
        self.assertEqual(recover_bisections(old, children), {(1, 2):4, (2, 3):5})
        for bad in (children[:-1], children[[0,0,2,3]], np.array([[1,4],[2,4],[2,4],[3,4]]),
                    np.array([[1,3],[3,2],[2,5],[5,3]])):
            with self.assertRaises(ValueError): recover_bisections(old, bad)
        from reconcile_projected_curves import curve_parameters
        class Curve:
            def getClosestPoint(self,*args): return [0,0,0, 1,0,0], [999,999]
            def getParametrization(self,*args): return [0,1]
            def getParametrizationBounds(self,*args): return [0],[1]
            def getValue(self,*args): return [0,0,0, 1,0,0]
        api=API(); api.model=Curve()
        parameters,distance,residual=curve_parameters(api,7,np.array([[0,0,0],[1,0,0]]))
        np.testing.assert_array_equal(parameters,[0,1]); self.assertEqual(residual,0)
        api.model.getValue=lambda *args: [0,0,0, 2,0,0]
        _,distance,_=curve_parameters(api,7,np.array([[0,0,0],[1,0,0]]))
        self.assertGreater(distance[1],1e-6)
        api.model.getValue=lambda *args: [0,0,0, float('nan'),0,0]
        with self.assertRaisesRegex(ValueError,'parameter_roundtrip_failed'):
            curve_parameters(api,7,np.array([[0,0,0],[1,0,0]]))

    @unittest.skipUnless(importlib.util.find_spec('gmsh'), 'optional Gmsh runtime')
    def test_real_gmsh_curve_bisection_does_not_change_surface_or_coordinates(self):
        import numpy as np
        import gmsh
        from trial_project_compound_surface import update_stored_curves
        if gmsh.__version__ != '4.15.2': self.skipTest('qualified Gmsh 4.15.2 required for removeElements')
        gmsh.initialize(['curve-test','-nopopup'],readConfigFiles=False,run=False)
        gmsh.option.setNumber('General.Terminal',0)
        try:
            gmsh.model.add('fixture'); gmsh.model.addDiscreteEntity(1,7); gmsh.model.addDiscreteEntity(2,8,[7])
            gmsh.model.mesh.addNodes(2,8,[1,2,3,4],[0,0,0, 2,0,0, 0,1,0, 1,0,0])
            gmsh.model.mesh.addElementsByType(7,1,[1],[2,1])
            gmsh.model.mesh.addElementsByType(8,2,[2,3],[1,4,3, 4,2,3])
            before=gmsh.model.mesh.getNodes(); triangles=gmsh.model.mesh.getElements(2)
            result=update_stored_curves(gmsh,{(1,2):4})
            self.assertEqual(result,dict(rebuilt_curves=1,subdivided_stored_lines=1))
            np.testing.assert_array_equal(gmsh.model.mesh.getElements(1)[2][0],[2,4,4,1])
            for a,b in zip(before,gmsh.model.mesh.getNodes()): np.testing.assert_array_equal(a,b)
            np.testing.assert_array_equal(gmsh.model.mesh.getElements(2)[2][0],triangles[2][0])
            self.assertEqual(update_stored_curves(gmsh,{}),dict(rebuilt_curves=0,subdivided_stored_lines=0))
        finally: gmsh.finalize()

    @unittest.skipUnless(os.environ.get('M64_CGAL_INTERSECTIONS'), 'optional compiled CGAL auditor')
    def test_intersection_selection_keeps_arrays_and_detects_crossing_and_coplanar_overlap(self):
        import numpy as np
        from audit_surface_intersections import intersection_pairs
        def selected_intersections(p, f):
            report = intersection_pairs(p, f, Path(os.environ['M64_CGAL_INTERSECTIONS']))
            self.assertTrue(report['complete'])
            return np.unique(report['pairs_private']).astype(int)
        p = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.],
                      [.2, .2, -1.], [.2, .2, 1.], [.6, .2, 0.]])
        f = np.array([[0, 1, 2], [3, 4, 5]])
        original_p, original_f = p.copy(), f.copy()
        np.testing.assert_array_equal(selected_intersections(p, f), [0, 1])
        np.testing.assert_array_equal(p, original_p); np.testing.assert_array_equal(f, original_f)
        p[3:] = [[.1, .1, 0.], [.5, .1, 0.], [.1, .5, 0.]]
        np.testing.assert_array_equal(selected_intersections(p, f), [0, 1])
        p[3:, 2] = .01
        self.assertEqual(len(selected_intersections(p, f)), 0)
        # Two triangles meeting only at their common edge are not an intersection.
        square = np.array([[0., 0., 0.], [1., 0., 0.], [1., 1., 0.], [0., 1., 0.]])
        self.assertEqual(len(selected_intersections(square, np.array([[0, 1, 2], [0, 2, 3]]))), 0)
        np.testing.assert_array_equal(selected_intersections(
            np.array([[0., 0., 0.], [1., 0., 0.], [2., 0., 0.]]), np.array([[0, 1, 2]])), [0])
        with self.assertRaises(ValueError): selected_intersections(square.astype(np.float32), f)

    def test_indexed_vertex_links_winding_and_curve_mismatch_without_welding(self):
        import numpy as np
        from audit_projected_surface import indexed_topology, stored_curve_edges, orient_entities
        p = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.], [0., 0., 1.]])
        f = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]])
        original_p, original_f = p.copy(), f.copy()
        good = indexed_topology(p, f)
        self.assertTrue(good['indexed_closed_oriented_manifold_screen_passed'])
        self.assertEqual(good['vertex_link_classification'], {'circle': 4})
        pinched = np.vstack([f, np.where(f[:, ::-1] == 0, 0, f[:, ::-1]+3)])
        result = indexed_topology(np.vstack([p, -p[1:]]), pinched)
        self.assertEqual(result['not_incident_twice'], 0)
        self.assertEqual(result['vertex_link_classification'], {'invalid': 1, 'circle': 6})
        self.assertFalse(result['indexed_closed_oriented_manifold_screen_passed'])
        reversed_face = f.copy(); reversed_face[0] = reversed_face[0, ::-1]
        self.assertEqual(indexed_topology(p, reversed_face)['two_incidence_orientation_conflicts'], 3)
        restored, orientation = orient_entities(p, reversed_face, np.arange(1, 5))
        self.assertTrue(indexed_topology(p, restored)['indexed_closed_oriented_manifold_screen_passed'])
        self.assertEqual(orientation['reversed_triangles'], 1)
        np.testing.assert_array_equal(np.sort(restored, axis=1), np.sort(f, axis=1))
        with self.assertRaisesRegex(ValueError, 'inconsistent_entity_orientation'):
            orient_entities(p, reversed_face, np.ones(4, dtype=int))
        with self.assertRaisesRegex(ValueError, 'single_connected_entity_shell'):
            orient_entities(np.vstack([p, p+3]), np.vstack([f, f+4]), np.arange(1, 9))
        with self.assertRaisesRegex(ValueError, 'single_connected_entity_shell'):
            orient_entities(np.vstack([p, p+3]), np.vstack([f, f+4]), np.tile(np.arange(1, 5), 2))
        self.assertFalse(indexed_topology(p, f[:-1])['indexed_closed_oriented_manifold_screen_passed'])
        self.assertFalse(indexed_topology(p, np.vstack([f, f[:1]]))['indexed_closed_oriented_manifold_screen_passed'])
        doubled = indexed_topology(np.vstack([p, p]), np.vstack([f, f+4]))
        self.assertEqual(doubled['exact_duplicate_used_coordinates'], 4)
        self.assertFalse(doubled['coordinates_merged'])
        self.assertFalse(doubled['indexed_closed_oriented_manifold_screen_passed'])
        curves = stored_curve_edges(np.array([[0, 3, 2], [3, 1, 2]]), np.array([[0, 1], [1, 2], [3, 0]]))
        self.assertEqual(curves['missing_line_indices_private'], [0])
        with self.assertRaises(ValueError): indexed_topology(p, f.astype(float))
        with self.assertRaises(ValueError): stored_curve_edges(f, np.array([[0., 1.]]))
        np.testing.assert_array_equal(p, original_p); np.testing.assert_array_equal(f, original_f)


if __name__ == '__main__': unittest.main()
