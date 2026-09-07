import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest

SOURCE = (Path(__file__).resolve().parents[1] /
          'twins/m64-cylinder-head/source/picogk-local-junction/audit_surface_topology.py')


@unittest.skipUnless(importlib.util.find_spec('numpy'), 'numpy QA runtime required')
class SurfaceTopologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import numpy as np
        cls.np = np
        spec = importlib.util.spec_from_file_location('surface_topology_audit', SOURCE)
        cls.audit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.audit)

    def tetrahedron(self):
        return (self.np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.], [0., 0., 1.]]),
                self.np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]]))

    def test_closed_tetrahedron_keeps_all_faces_and_checks_vertex_circles(self):
        vertices, faces = self.tetrahedron()
        result = self.audit.audit_arrays(vertices, faces)
        self.assertEqual(result['faces_original_and_retained'], 4)
        self.assertEqual(result['vertex_link_classification'], {'circle': 4})
        self.assertEqual(result['components'][0]['euler_V_minus_E_plus_F'], 2)
        self.assertAlmostEqual(result['signed_triangle_volume_scan_units_cubed'], 1/6)
        self.assertTrue(result['closed_oriented_combinatorial_surface_screen_pass'])
        self.assertEqual(result['geometric_self_or_inter_component_intersections'], 'untested')

    def test_stl_repeated_coordinates_only_are_indexed_together(self):
        vertices, faces = self.tetrahedron()
        repeated = vertices[faces].reshape(-1, 3)
        ids = self.np.arange(12).reshape(-1, 3)
        result = self.audit.audit_arrays(repeated, ids)
        self.assertEqual(result['exact_unique_vertices'], 4)
        self.assertTrue(result['closed_oriented_combinatorial_surface_screen_pass'])
        # A one-ULP perturbation is not merged or repaired.
        repeated[0, 0] = self.np.nextafter(repeated[0, 0], 1.)
        perturbed = self.audit.audit_arrays(repeated, ids)
        self.assertEqual(perturbed['exact_unique_vertices'], 5)
        self.assertFalse(perturbed['closed_oriented_combinatorial_surface_screen_pass'])

    def test_null_duplicate_and_oppositely_oriented_faces_are_not_removed(self):
        vertices, faces = self.tetrahedron()
        for extra in ([0, 0, 1], faces[0], faces[0][::-1]):
            with self.subTest(extra=list(extra)):
                result = self.audit.audit_arrays(vertices, self.np.vstack([faces, extra]))
                self.assertEqual(result['faces_original_and_retained'], 5)
                self.assertEqual(result['faces_removed'], 0)
                self.assertFalse(result['closed_oriented_combinatorial_surface_screen_pass'])
                self.assertEqual(result['edge_connected_face_components'], 1)
        degenerate = self.audit.audit_arrays(vertices, self.np.vstack([faces, [0, 0, 1]]))
        self.assertEqual(degenerate['exact_zero_area_faces'], 1)
        self.assertEqual(degenerate['components'][0]['self_loop_edges'], 1)
        self.assertGreater(degenerate['components'][0]['edge_incidence_histogram'][4], 0)
        twice = self.audit.audit_arrays(vertices, self.np.vstack([faces, [0, 0, 1], [0, 0, 1]]))
        self.assertEqual(twice['components'][0]['self_loop_edges'], 1)
        self.assertEqual(twice['components'][0]['two_incidence_nonloop_orientation_conflicts'], 0)

    def test_pinched_vertex_fails_even_with_every_edge_twice(self):
        vertices, faces = self.tetrahedron()
        # Outward tetrahedra share only their origin, not an edge or face.
        result = self.audit.audit_arrays(self.np.vstack([vertices, -vertices]),
                                        self.np.vstack([faces, faces[:, ::-1] + 4]))
        self.assertEqual(result['edge_connected_face_components'], 2)
        self.assertEqual(result['vertex_connected_face_components'], 1)
        self.assertEqual(result['vertex_link_classification'], {'circle': 6, 'invalid': 1})
        self.assertFalse(result['closed_oriented_combinatorial_surface_screen_pass'])
        for component in result['components']:
            self.assertEqual(component['edge_incidence_histogram'], {2: 6})
            self.assertEqual(component['two_incidence_nonloop_orientation_conflicts'], 0)

    def test_boundary_links_are_paths_not_accepted_as_closed(self):
        vertices, faces = self.tetrahedron()
        result = self.audit.audit_arrays(vertices, faces[:1])
        self.assertEqual(result['vertex_link_classification'], {'isolated': 1, 'path': 3})
        self.assertEqual(result['unused_exact_unique_vertices_retained'], 1)
        self.assertEqual(result['components'][0]['edge_incidence_histogram'], {1: 3})
        self.assertFalse(result['closed_oriented_combinatorial_surface_screen_pass'])

    def test_small_negative_component_is_retained_without_cavity_inference(self):
        vertices, faces = self.tetrahedron()
        inner = vertices * .01 + .1
        result = self.audit.audit_arrays(self.np.vstack([vertices, inner]),
                                        self.np.vstack([faces, faces[:, ::-1] + 4]))
        self.assertEqual(result['edge_connected_face_components'], 2)
        self.assertEqual([row['volume_sign'] for row in result['components']], ['positive', 'negative'])
        self.assertEqual([row['faces'] for row in result['components']], [4, 4])
        self.assertTrue(result['closed_oriented_combinatorial_surface_screen_pass'])
        self.assertEqual(result['shell_nesting_and_cavity_classification'], 'untested')
        self.assertAlmostEqual(result['component_sum_minus_whole_integration'], 0)

    def test_local_orientation_conflict_is_rejected(self):
        vertices, faces = self.tetrahedron()
        faces[0] = faces[0][::-1]
        result = self.audit.audit_arrays(vertices, faces)
        self.assertEqual(result['components'][0]['two_incidence_nonloop_orientation_conflicts'], 3)
        self.assertFalse(result['closed_oriented_combinatorial_surface_screen_pass'])

    def test_exact_collinearity_does_not_treat_rounded_cross_zero_as_exact(self):
        points = self.np.array([[1e16, 1e16, 0], [1e16+2, 1e16+2, 0], [1, 0, 0.]])
        faces = self.np.array([[0, 1, 2]])
        self.assertTrue((self.np.cross(points[1]-points[0], points[2]-points[0]) == 0).all())
        self.assertFalse(self.audit.exact_zero_area_mask(points, faces)[0])
        collinear = self.np.array([[0., 0., 0.], [.125, .25, .5], [.25, .5, 1.]])
        self.assertTrue(self.audit.exact_zero_area_mask(collinear, faces)[0])

    def test_invalid_arrays_and_face_count_bounds_fail_closed(self):
        vertices, faces = self.tetrahedron()
        for broken_vertices, broken_faces in (
                (vertices * self.np.nan, faces), (vertices, faces - 1),
                (vertices, faces.astype(float)), (vertices, faces[:0])):
            with self.assertRaises(ValueError):
                self.audit.audit_arrays(broken_vertices, broken_faces)
        original_limit = self.audit.MAX_FACES
        try:
            self.audit.MAX_FACES = 3
            with self.assertRaises(ValueError):
                self.audit.audit_arrays(vertices, faces)
        finally:
            self.audit.MAX_FACES = original_limit

    def write_stl(self, path, vertices, faces):
        chunks = [bytes(80), struct.pack('<I', len(faces))]
        for triangle in vertices[faces]:
            chunks.append(struct.pack('<12fH', 0., 0., 0., *triangle.flatten(), 0))
        path.write_bytes(b''.join(chunks))

    def fixture_receipts(self, directory):
        vertices, faces = self.tetrahedron()
        exports = {}
        for name in ('before', 'after', 'added'):
            path = directory / (name + '.stl')
            self.write_stl(path, vertices, faces)
            exports[name] = {'sha256': self.audit.sha(path), 'triangles': len(faces)}
        native = {'schema': 'm64-picogk-local-junction-witness/v1', 'voxel_scan_units': .2,
                  'private_head_processed': False, 'exports': exports,
                  'status': 'occupancy_guards_passed_mesh_audit_pending'}
        native_path = directory / 'run-report.json'
        native_path.write_text(json.dumps(native))
        raw_path = directory / 'raw.json'
        raw_path.write_text(json.dumps({'native_report_sha256': self.audit.sha(native_path),
                                        'meshes': exports, 'status': 'rejected_raw_mesh_screen'}))
        return raw_path

    def test_hash_bound_read_only_receipt_never_promotes_original_rejection(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            raw = self.fixture_receipts(directory)
            files = list(directory.iterdir())
            hashes = {path: self.audit.sha(path) for path in files}
            output = directory / 'new-report.json'
            self.assertEqual(self.audit.run(directory, raw, output), 0)
            report = json.loads(output.read_text())
            self.assertEqual(report['status'], 'diagnostic_completed_no_qualification_decision')
            self.assertEqual(report['original_raw_audit_status_retained'], 'rejected_raw_mesh_screen')
            self.assertFalse(report['manufacturing_authorized'])
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            self.assertEqual(hashes, {path: self.audit.sha(path) for path in files})
            with self.assertRaises(FileExistsError):
                self.audit.run(directory, raw, output)

    def test_stl_hash_change_and_wrong_resolution_refuse_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            raw = self.fixture_receipts(directory)
            path = directory / 'after.stl'
            original = path.read_bytes()
            path.write_bytes(b'changed' + original[7:])
            output = directory / 'never.json'
            with self.assertRaises(ValueError):
                self.audit.run(directory, raw, output)
            self.assertFalse(output.exists())
            path.write_bytes(original)
            native_path = directory / 'run-report.json'
            native = json.loads(native_path.read_text())
            native['voxel_scan_units'] = .1
            native_path.write_text(json.dumps(native))
            record = json.loads(raw.read_text())
            record['native_report_sha256'] = self.audit.sha(native_path)
            raw.write_text(json.dumps(record))
            with self.assertRaises(ValueError):
                self.audit.run(directory, raw, output)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
