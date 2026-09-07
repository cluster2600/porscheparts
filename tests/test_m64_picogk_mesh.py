import importlib.util
from pathlib import Path
import struct
import sys
import tempfile
from types import SimpleNamespace
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'twins/m64-cylinder-head/source/picogk'
sys.path.insert(0, str(SOURCE))
import export_master


class PicoGKMeshTests(unittest.TestCase):
    def test_settings_are_absolute_and_bounded(self):
        export_master.validate_settings(.05, .15)
        for value in (0., -.1, .051, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                export_master.validate_settings(value, .15)

    def test_binary_stl_size_and_nonfinite_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bad.stl'
            path.write_bytes(bytes(80) + struct.pack('<I', 2))
            with self.assertRaises(ValueError):
                export_master.load_binary_stl(path)
            path.write_bytes(bytes(80) + struct.pack('<I', 1)
                             + struct.pack('<12fH', *([0.] * 3 + [float('nan')] + [0.] * 8), 0))
            with self.assertRaises(ValueError):
                export_master.load_binary_stl(path)

    def test_tetrahedron_topology_and_volume(self):
        import numpy as np
        vertices = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.], [0., 0., 1.]])
        triangles = vertices[[[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]]]
        report = export_master.mesh_summary(triangles)
        self.assertTrue(report['edge_manifold_closed'])
        self.assertTrue(report['winding_consistent_on_two_face_edges'])
        self.assertEqual(report['connected_vertex_components'], 1)
        self.assertEqual(report['euler_characteristic'], 2)
        self.assertAlmostEqual(report['signed_volume_scan_units_cubed'], 1 / 6)
        opened = export_master.mesh_summary(triangles[:3])
        self.assertEqual(opened['boundary_edges'], 3)
        self.assertFalse(opened['edge_manifold_closed'])

    def test_flipped_face_and_disconnected_shell_detected(self):
        import numpy as np
        vertices = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.], [0., 0., 1.]])
        triangles = vertices[[[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]]]
        flipped = triangles.copy(); flipped[0] = flipped[0][::-1]
        self.assertFalse(export_master.mesh_summary(flipped)['winding_consistent_on_two_face_edges'])
        both = np.concatenate([triangles, triangles + 3.])
        self.assertEqual(export_master.mesh_summary(both)['connected_vertex_components'], 2)

    @unittest.skipUnless(importlib.util.find_spec('trimesh') and importlib.util.find_spec('rtree'), 'optional mesh QA runtime')
    def test_normal_chord_box_and_triangle_proximity(self):
        import trimesh
        from compare_meshes import normal_chord_screen, surface_distances
        cube = trimesh.creation.box(extents=[2., 2., 2.])
        screen = normal_chord_screen(cube, 128, 11)
        self.assertEqual(screen['resolved_exit_chords'], 128)
        self.assertAlmostEqual(screen['chord_scan_units']['minimum'], 2.)
        self.assertEqual(screen['below_threshold_samples'], 0)
        self.assertFalse(screen['minimum_wall_thickness_proved'])
        distances = surface_distances(cube, cube, 128, 11)
        self.assertLess(distances['distance_scan_units']['maximum'], 1e-12)

    def test_no_reconstruction_or_fabrication_claims_in_source(self):
        source = (SOURCE / 'compare_meshes.py').read_text()
        self.assertIn("'manufacturing_authorized': False", source)
        self.assertIn("'functional_interface_preservation_certified': False", source)
        self.assertIn("'continuous_Hausdorff_bound': False", source)

    @unittest.skipUnless(importlib.util.find_spec('trimesh') and importlib.util.find_spec('rtree'), 'optional mesh QA runtime')
    def test_three_resolution_pipeline_on_explicit_synthetic_fixture(self):
        import json
        import trimesh
        import compare_meshes
        with tempfile.TemporaryDirectory(prefix='synthetic-picogk-software-test-') as directory:
            root = Path(directory)
            master = root / 'synthetic-cube.stl'
            cube = trimesh.creation.box(extents=[2., 2., 2.])
            cube.export(master)
            receipt = root / 'synthetic-export.json'
            receipt.write_text(json.dumps({'mesh_sha256': export_master.sha256(master),
                                           'voxel_input_topology_gate_passed': True,
                                           'source_STEP_sha256': 'synthetic_unit_test_no_actual_STEP'}))
            candidates = []
            for resolution, offset in ((.8, .08), (.4, .04), (.2, .02)):
                run_directory = root / f'synthetic-{resolution}'
                run_directory.mkdir()
                path = run_directory / 'head-roundtrip.stl'
                copy = cube.copy(); copy.apply_translation([offset, 0., 0.]); copy.export(path)
                (run_directory / 'run-report.json').write_text(json.dumps({
                    'input_sha256': export_master.sha256(master), 'input_unchanged': True,
                    'transform': 'identity', 'voxel_mm': resolution,
                    'scope': 'synthetic_software_test_not_actual_PicoGK_run',
                    'roundtrip': {'sha256': export_master.sha256(path), 'filename': path.name,
                                  'triangles': len(copy.faces)}}))
                candidates.append((str(resolution), str(path)))
            args = SimpleNamespace(master=master, master_report=receipt, candidate=candidates,
                                   output=root / 'report', samples=64, chord_samples=64, seed=17, render=False)
            self.assertEqual(compare_meshes.run(args), 0)
            report = json.loads((args.output / 'mesh-comparison-report.json').read_text())
            self.assertEqual(len(report['runs']), 3)
            self.assertTrue(report['master_unchanged_after_audit'])
            self.assertTrue(report['convergence_screen']['sampled_maximum_distance_monotone_nonincreasing'])
            self.assertFalse(report['manufacturing_authorized'])
            bad_receipt = Path(candidates[0][1]).parent / 'run-report.json'
            wrong = json.loads(bad_receipt.read_text()); wrong['input_sha256'] = 'wrong_master'
            bad_receipt.write_text(json.dumps(wrong))
            args.output = root / 'rejected-report'
            with self.assertRaisesRegex(ValueError, 'candidate_run_receipt_provenance'):
                compare_meshes.run(args)
            self.assertFalse((args.output / 'mesh-comparison-report.json').exists())


if __name__ == '__main__':
    unittest.main()
