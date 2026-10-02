import importlib.util
import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/wholebody'))


@unittest.skipUnless(importlib.util.find_spec('numpy') and importlib.util.find_spec('scipy'), 'optional numpy/scipy runtime')
class ProjectedSurfaceTopologyTests(unittest.TestCase):
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
