import contextlib
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch
import zipfile

import numpy as np
import importlib.util
import os

SOURCE = Path(__file__).resolve().parents[1] / 'twins/m64-cylinder-head/source/physicsnemo-mesh/benchmark_mesh.py'
SPEC = importlib.util.spec_from_file_location('m64_physicsnemo_benchmark', SOURCE)
b = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(b)


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.points = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]])
        self.cells = np.array([[0, 1, 2]], dtype=np.int64)

    def test_valid_triangle(self):
        b.validate(self.points, self.cells)

    def test_wrong_dtypes(self):
        for points, cells in [(self.points.astype('f4'), self.cells), (self.points, self.cells.astype('i4'))]:
            with self.assertRaises(b.Refusal):
                b.validate(points, cells)

    def test_wrong_shapes_empty_and_indices(self):
        for points, cells in [(self.points[:, :2], self.cells), (self.points[:0], self.cells),
                              (self.points, self.cells + 1), (self.points, self.cells - 1)]:
            with self.assertRaises(b.Refusal):
                b.validate(points, cells)

    def test_nonfinite(self):
        for value in [np.inf, np.nan]:
            self.points[0, 0] = value
            with self.assertRaises(b.Refusal):
                b.validate(self.points, self.cells)

    def test_repeated_vertex(self):
        with self.assertRaises(b.Refusal):
            b.validate(self.points, np.array([[0, 0, 2]], dtype=np.int64))

    def test_order_and_signed_zero_hashes(self):
        self.assertNotEqual(b.array_sha(self.cells), b.array_sha(self.cells[:, ::-1]))
        before = b.array_sha(self.points)
        self.points[0, 0] = -0.
        self.assertNotEqual(before, b.array_sha(self.points))

    def test_hash_shape_and_copy(self):
        self.assertEqual(b.array_sha(self.points), b.array_sha(self.points.copy()))
        self.assertNotEqual(b.array_sha(self.points), b.array_sha(self.points.reshape(-1)))

    def test_comparison_true_false_nonfinite(self):
        self.assertTrue(b.compare(self.points, self.points.copy())['passed'])
        self.assertFalse(b.compare(self.points, self.points + 0.01)['passed'])
        self.points[0, 0] = np.nan
        self.assertEqual(b.compare(self.points, self.points)['nonfinite_values'], 1)
        self.assertFalse(b.compare(self.points, self.points)['passed'])

    def test_positive_tiny_area_is_not_masked_by_absolute_floor(self):
        result = b.compare(np.array([0.]), np.array([2. ** -60]), atol=0)
        self.assertFalse(result['passed'])
        self.assertEqual(result['positive_reference_but_zero_area'], 1)
        self.assertEqual(result['max_relative_area_error'], 1.)

    def test_failed_normal_components_are_counted_as_one_cell(self):
        actual = np.array([[0., 0., 1.], [0., 0., 1.]])
        reference = np.array([[1., 0., 0.], [0., 0., 1.]])
        result = b.compare(actual, reference)
        self.assertEqual(result['failed_values'], 2)
        self.assertEqual(result['failed_cells'], 1)

    def test_warmup_is_separate_and_five_repetitions(self):
        calls, syncs = [], []
        result, report = b.repeated(lambda: calls.append(len(calls)) or len(calls), lambda: syncs.append(1))
        self.assertEqual(result, 6)
        self.assertEqual(len(calls), 6)
        self.assertEqual(len(syncs), 12)
        self.assertEqual(len(report['repetitions_seconds']), 5)
        self.assertGreaterEqual(report['warmup_seconds'], 0)

    def test_new_mesh_per_call_and_quality_keys(self):
        created = []
        class Mesh:
            def __init__(self, points, cells):
                created.append(self)
                self.cell_areas = np.array([0.5])
                self.cell_normals = np.array([[0., 0., 1.]])
                self.quality_metrics = {key: np.array([1.]) for key in b.QUALITY_KEYS}
        outputs, _ = b.repeated(lambda: b.compute(Mesh, self.points, self.cells), lambda: None)
        self.assertEqual(len({id(mesh) for mesh in created}), 6)
        self.assertEqual(set(outputs), {'areas', 'unit_normals', *b.QUALITY_KEYS})
        with self.assertRaises(b.Refusal):
            b.compute(lambda **kw: Mock(cell_areas=1, cell_normals=1, quality_metrics={}), self.points, self.cells)

    def test_known_positive_gram_and_normalization_counterexamples(self):
        s = 2. ** -30
        e1, e2 = np.array([1., 0., 0.]), np.array([1., s, 0.])
        gram = np.dot(e1, e1) * np.dot(e2, e2) - np.dot(e1, e2) ** 2
        self.assertEqual(gram, 0.)
        self.assertEqual(np.linalg.norm(np.cross(e1, e2)) / 2., s / 2.)
        cross_length = s * s
        self.assertGreater(cross_length, 0.)
        self.assertLess(cross_length / max(cross_length, 1e-12), 1.)

    def test_wheel_exact_sources(self):
        if 'M64_PHYSICSNEMO_WHEEL' not in os.environ:
            self.skipTest('Optional offline wheel audit: set M64_PHYSICSNEMO_WHEEL; no download in tests')
        wheel = Path(os.environ['M64_PHYSICSNEMO_WHEEL'])
        self.assertEqual(hashlib.sha256(wheel.read_bytes()).hexdigest(), b.WHEEL_SHA)
        with zipfile.ZipFile(wheel) as archive:
            for name, expected in b.SOURCE_PINS.items():
                self.assertEqual(hashlib.sha256(archive.read('physicsnemo/' + name)).hexdigest(), expected)

    def supervise(self, first_wait):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'new'
            argv = ['benchmark_mesh.py', '--mesh', 'mesh', '--reference', 'ref',
                    '--reference-report', 'receipt', '--output', str(output)]
            proc = Mock(pid=123, wait=Mock(side_effect=[first_wait, 0]))
            with patch.object(b.sys, 'argv', argv), patch.object(b.subprocess, 'Popen', return_value=proc) as popen, \
                    patch.object(b.os, 'killpg') as kill, contextlib.redirect_stdout(io.StringIO()) as stdout:
                code = b.main()
            self.assertFalse(popen.call_args.kwargs['shell'])
            self.assertTrue(popen.call_args.kwargs['start_new_session'])
            kill.assert_called_once_with(123, b.signal.SIGKILL)
            self.assertEqual(proc.wait.call_args_list[0].kwargs, {'timeout': 290})
            self.assertEqual(proc.wait.call_args_list[1].kwargs, {'timeout': 5})
            self.assertLess(len(stdout.getvalue()), 4096)
            summary = json.loads((output / 'supervisor-report.json').read_text())
            self.assertTrue(summary['process_group_kill_and_wait_completed'])
            return code

    def test_supervisor_success(self):
        self.assertEqual(self.supervise(0), 0)

    def test_supervisor_timeout(self):
        self.assertEqual(self.supervise(subprocess.TimeoutExpired('private-argv', 290)), 124)

    def test_supervisor_interruption(self):
        self.assertEqual(self.supervise(KeyboardInterrupt()), 130)

    def test_existing_output_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / 'existing').touch()
            with patch.object(b.sys, 'argv', ['b', '--mesh', 'm', '--reference', 'r', '--reference-report', 'p', '--output', temp]), \
                    patch.object(b.subprocess, 'Popen') as popen, self.assertRaises(b.Refusal):
                b.main()
            popen.assert_not_called()


if __name__ == '__main__':
    unittest.main()
