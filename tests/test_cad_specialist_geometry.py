"""Focused deterministic input/safety/metric tests; not a native CAD certificate."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import subprocess

SOURCE = Path(__file__).resolve().parents[1] / 'twins/m64-cylinder-head/source'


def module(name):
    spec = importlib.util.spec_from_file_location(name, SOURCE / f'{name}.py')
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


worker = module('cad_specialist_sandbox_worker')
controller = module('run_cad_specialist_sandbox')


class SpecialistGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global np, prepare, compare
        try:
            import numpy as np
            from scipy.spatial import cKDTree  # noqa: F401: validate optional native runtime
        except ImportError as error:
            raise unittest.SkipTest(f'working NumPy/SciPy QA runtime required: {error}')
        prepare = module('prepare_cad_specialist_scan_input')
        compare = module('compare_cad_specialist_geometry')

    def test_normalization_inverse(self):
        values = np.array([[10., 2, 6], [12, 6, 16], [11, 3, 7]])
        normalized, center, scale = prepare.normalize(values)
        self.assertTrue(np.allclose(normalized * scale + center, values))
        self.assertAlmostEqual(np.ptp(normalized, axis=0).max(), 2)

    def test_degenerate_normalization_rejected(self):
        with self.assertRaises(ValueError):
            prepare.normalize(np.ones((3, 3)))

    def test_sampling_reproducible_and_inside(self):
        triangles = np.array([[[0., 0, 0], [1, 0, 0], [0, 1, 0]]])
        a, ids, weights = prepare.sample_surface(triangles, 256, 12)
        b, _, _ = prepare.sample_surface(triangles, 256, 12)
        self.assertTrue(np.array_equal(a, b))
        self.assertTrue(np.all(a >= 0))
        self.assertTrue(np.all(a.sum(axis=1) <= 1))
        self.assertTrue(np.allclose(weights.sum(axis=1), 1))
        self.assertEqual(ids.shape, (256,))

    def test_empty_area_rejected(self):
        with self.assertRaises(ValueError):
            prepare.sample_surface(np.zeros((1, 3, 3)), 256, 12)

    def test_stl_roundtrip_and_bad_size(self):
        triangles = np.array([[[0., 0, 0], [1, 0, 0], [0, 1, 0]]])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'triangle.stl'
            prepare.write_stl(path, triangles)
            self.assertTrue(np.array_equal(compare.read_stl(path), triangles))
            path.write_bytes(path.read_bytes() + b'x')
            with self.assertRaises(ValueError):
                compare.read_stl(path)

    def test_identical_point_comparison(self):
        reference = np.array([[0., 0, 0], [1, 0, 0], [0, 1, 0]])
        result = compare.compare(reference, reference.copy(), reference.copy())
        for row in result.values():
            self.assertEqual(row['rms'], 0)

    def test_FPS_starts_at_zero_and_selects_farthest(self):
        fps = module('prepare_cad_specialist_fps_input')
        points = np.array([[0., 0, 0], [1, 0, 0], [4, 0, 0], [2, 0, 0]])
        self.assertEqual(fps.farthest_indices(points, 4).tolist(), [0, 2, 3, 1])

    def test_FPS_rejects_duplicate_short_pool(self):
        fps = module('prepare_cad_specialist_fps_input')
        with self.assertRaises(ValueError):
            fps.farthest_indices(np.zeros((5, 3)), 2)

    def test_reference_hash_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'reference.npy'
            np.save(path, np.zeros((4, 3)))
            with self.assertRaises(ValueError):
                compare.verified_points(path, '0' * 64, count=4)

    def test_reference_shape_and_finiteness_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'reference.npy'
            for values in [np.zeros((4, 2)), np.full((4, 3), np.nan)]:
                np.save(path, values)
                with self.assertRaises(ValueError):
                    compare.verified_points(path, prepare.sha(path), count=4)

    def test_reference_verified_load(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'reference.npy'
            values = np.arange(12, dtype=float).reshape(4, 3)
            np.save(path, values)
            self.assertTrue(np.array_equal(compare.verified_points(path, prepare.sha(path), count=4), values))


class SpecialistASTTests(unittest.TestCase):
    def test_expected_CadQuery_screen(self):
        worker.screen("import cadquery as cq\nr = cq.Workplane('XY').box(1, 2, 3)\n")

    def test_unsafe_generated_syntax_rejected(self):
        for source in ['import os', "open('/etc/passwd')", 'while True: pass',
                       'x.__class__', "getattr(x, 'x')", 'def f(): pass']:
            with self.subTest(source=source), self.assertRaises(ValueError):
                worker.screen(source)


class SpecialistCleanupTests(unittest.TestCase):
    def test_inspect_timeout_still_removes_and_proves_absence(self):
        with patch.object(controller.subprocess, 'run', side_effect=[
            subprocess.TimeoutExpired('inspect', 15),
            subprocess.CompletedProcess([], 0, '', ''),
            subprocess.CompletedProcess([], 0, '', ''),
        ]) as calls:
            result = controller.cleanup_container('exact-name')
        self.assertTrue(result['removed_verified'])
        self.assertEqual(calls.call_args_list[1].args[0], ['docker', 'rm', '-f', 'exact-name'])
        self.assertIn('name=^/exact-name$', calls.call_args_list[2].args[0])

    def test_daemon_failure_never_means_absence(self):
        with patch.object(controller.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, '', 'daemon unavailable')):
            result = controller.cleanup_container('exact-name')
        self.assertFalse(result['removed_verified'])
        self.assertEqual(result['absence_probe_return_code'], 1)

    def test_remaining_container_is_not_removed(self):
        with patch.object(controller.subprocess, 'run', side_effect=[
            subprocess.CompletedProcess([], 0, '{}', ''),
            subprocess.CompletedProcess([], 1, '', ''),
            subprocess.CompletedProcess([], 0, 'exact-name\n', ''),
        ]):
            result = controller.cleanup_container('exact-name')
        self.assertFalse(result['removed_verified'])

    def test_remove_timeout_still_probes_absence(self):
        with patch.object(controller.subprocess, 'run', side_effect=[
            subprocess.CompletedProcess([], 0, '{}', ''),
            subprocess.TimeoutExpired('remove', 20),
            subprocess.TimeoutExpired('probe', 10),
        ]) as calls:
            result = controller.cleanup_container('exact-name')
        self.assertEqual(calls.call_count, 3)
        self.assertFalse(result['removed_verified'])


if __name__ == '__main__':
    unittest.main()
