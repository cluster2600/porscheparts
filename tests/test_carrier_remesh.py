"""Keep planar patch selection away from folds and reject malformed mesh inputs."""
import importlib.util
import json
import struct
import sys
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'parts/993-eng-carrier-0001/source/remesh-20261016'


class RemeshEvidenceTests(unittest.TestCase):
    def test_failed_design_and_old_mesh_comparison_are_not_promoted(self):
        result = json.loads((SOURCE / 'results.json').read_text())
        trial = result['last_design_trial']
        self.assertFalse(trial['selected_as_final_part'])
        self.assertEqual(trial['uniform_1p5_mm_wall_screen_status'], 'rejected')
        self.assertEqual(trial['old_coarse_STL_equivalence_status'], 'rejected')
        self.assertTrue(trial['exact_CAD_to_mesh']['passed'])
        self.assertTrue(trial['mesh_to_exact_CAD']['candidate_sampled_chord_screen_pass'])
        self.assertEqual(trial['native_topology']['needle_triangles'], 0)
        self.assertGreater(trial['strict_wall_metrics']['thin_wall_area_fraction'], 0)



class GeometryRuntimeSetupTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('geometry_setup', SOURCE / 'setup_runtime.py')
        self.setup = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.setup)

    def test_incompatible_CAD_versions_are_refused(self):
        versions = dict(self.setup.CAD_VERSIONS, numpy='99.0')
        with self.assertRaisesRegex(ValueError, 'pinned'):
            self.setup.require_versions({'versions': versions})

    def test_unknown_existing_directory_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            marker = Path(folder) / 'user-file'
            marker.write_text('keep')
            with self.assertRaisesRegex(ValueError, 'fresh path'):
                self.setup.setup(Path('/missing/cad-python'), Path(folder))
            self.assertEqual(marker.read_text(), 'keep')



class GeometryIdentityTests(unittest.TestCase):
    def test_identity_receipt_accepts_only_the_geometry_STEP_hash(self):
        spec = importlib.util.spec_from_file_location('gmsh_identity', SOURCE / 'gmsh_remesh.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'geometry.json'
            path.write_text(json.dumps({'geometry_sha256': {'carrier.step': 'a' * 64}}))
            self.assertEqual(module.identity_step_sha256(path), 'a' * 64)
            for invalid in ({}, {'geometry_sha256': {'carrier.step': 'invalid'}}):
                path.write_text(json.dumps(invalid))
                with self.assertRaisesRegex(ValueError, 'geometry_sha256'):
                    module.identity_step_sha256(path)



@unittest.skipUnless(importlib.util.find_spec('numpy'), 'Optional NumPy mesh runtime required')
class CarrierRemeshTests(unittest.TestCase):
    def setUp(self):
        import numpy as np
        self.np = np
        spec = importlib.util.spec_from_file_location('carrier_remesh', SOURCE / 'remesh.py')
        self.worker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.worker)
        self.criteria = json.loads((SOURCE / 'criteria.json').read_text())
        self.vertices = np.array([[0., 0., 0.], [100., 0., 0.], [50., .01, 0.], [50., -1., 0.]])
        self.faces = np.array([[0, 1, 2], [1, 0, 3]])

    def test_connected_plane_is_selected_without_moving_coordinates(self):
        before = self.vertices.copy()
        patches = self.worker.planar_patches(self.vertices, self.faces, self.criteria)
        self.assertEqual(patches, [[0, 1]])
        self.assertTrue(self.np.array_equal(before, self.vertices))

    def test_patch_does_not_grow_across_a_fold(self):
        self.vertices[3, 2] = .1
        patches = self.worker.planar_patches(self.vertices, self.faces, self.criteria)
        self.assertEqual(patches, [[0]])

    def test_stl_roundtrip_and_malformed_input(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'part.stl'
            self.worker.write_stl(path, self.vertices, self.faces)
            vertices, faces = self.worker.read_stl(path)
            self.assertEqual(len(faces), 2)
            self.assertTrue(self.np.allclose(vertices[faces], self.vertices[self.faces], atol=1e-6))
            path.write_bytes(path.read_bytes()[:-1])
            with self.assertRaisesRegex(ValueError, 'exact-length'):
                self.worker.read_stl(path)

    def test_thickness_dump_length_and_flat_cap_classification(self):
        spec = importlib.util.spec_from_file_location('thickness_analysis', SOURCE / 'analyze_thickness.py')
        analysis = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(analysis)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'thickness.bin'
            row = self.np.array([[0, 0, 22, 1, 0, 22, 0, 1, 22, 1.5]], dtype='<f4')
            path.write_bytes(struct.pack('<i', 1) + row.tobytes())
            triangles, thickness = analysis.read_dump(path)
            _, area, labels = analysis.regions(triangles)
            self.assertEqual(thickness.tolist(), [1.5])
            self.assertEqual(area.tolist(), [.5])
            self.assertEqual(labels.tolist(), ['plane_caps'])
            result = analysis.analyse(path, Path(folder) / 'result')
            self.assertEqual(result['total_area_below_mm2']['1.5'], 0)
            self.assertEqual(result['original_wall_screen_status'], 'passed')
            path.write_bytes(path.read_bytes()[:-1])
            with self.assertRaisesRegex(ValueError, 'count/length'):
                analysis.read_dump(path)


@unittest.skipUnless(importlib.util.find_spec('igl'), 'Optional native libigl runtime required')
class NativeAuditMathTests(unittest.TestCase):
    def test_known_point_distance_and_crossing_triangles(self):
        import igl
        import igl.predicates
        import numpy as np
        vertices = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]])
        squared, _, _ = igl.point_mesh_squared_distance(np.array([[.25, .25, 2.]]), vertices, np.array([[0, 1, 2]]))
        self.assertAlmostEqual(squared[0], 4.)
        crossing = np.vstack((vertices, [[.2, .2, -1.], [.2, .2, 1.], [.8, .2, 0.]]))
        found, pairs, _ = igl.predicates.find_self_intersections(crossing, np.array([[0, 1, 2], [3, 4, 5]]), False)
        self.assertTrue(found)
        self.assertEqual(len(pairs), 1)

    def test_CAD_samples_identity_and_closed_tetrahedron(self):
        import numpy as np
        import trimesh
        sys.path.insert(0, str(SOURCE))
        try:
            spec = importlib.util.spec_from_file_location('cad_mesh_checker', SOURCE / 'cad_mesh_audit.py')
            checker = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(checker)
        finally:
            sys.path.pop(0)
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            vertices = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.], [0., 0., 1.]])
            mesh = trimesh.Trimesh(vertices, [[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]], process=False)
            stl = folder / 'tetra.stl'; mesh.export(stl)
            samples = folder / 'samples.npz'; np.savez(samples, points_mm=vertices)
            receipt = {'results': {'candidate_STL': {'sha256': checker.sha(stl)}},
                       'exact_CAD_surface_samples_sha256': checker.sha(samples), 'exact_CAD_surface_samples': 4,
                       'STEP_sha256': 'a' * 64, 'CAD_sampling': 'Known tetrahedron vertices',
                       'exact_CAD_volume_mm3': 1 / 6, 'exact_CAD_bounds_mm': [[0, 0, 0], [1, 1, 1]],
                       'candidate_sampled_chord_screen_pass': True}
            path = folder / 'brep.json'; path.write_text(json.dumps(receipt))
            result = checker.run(stl, path, samples, folder / 'result')
            self.assertEqual(result['exact_CAD_to_mesh']['maximum_mm'], 0)
            self.assertEqual(result['topology']['boundary_edges'], 0)
            self.assertAlmostEqual(result['topology']['volume_mm3'], 1 / 6)
            self.assertEqual(result['self_intersection_pairs'], 0)
            self.assertFalse(result['historical_receipt_missing_volume_or_bounds'])
            self.assertEqual(set(result['failures']), {'mesh_bore_dimension', 'mesh_seating_plane'})
            samples.write_bytes(samples.read_bytes() + b'changed')
            with self.assertRaisesRegex(ValueError, 'archive hash'):
                checker.run(stl, path, samples, folder / 'refused')
            self.assertFalse((folder / 'refused').exists())


if __name__ == '__main__':
    unittest.main()
