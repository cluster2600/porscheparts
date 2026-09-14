import contextlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import importlib.util

SOURCE_DIR = Path(__file__).resolve().parents[1] / 'twins/m64-cylinder-head/source/physicsnemo-mesh'
SPEC = importlib.util.spec_from_file_location('m64_physicsnemo_cross_adapter', SOURCE_DIR / 'benchmark_cross_adapter.py')
adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter)

LIBRARY = SOURCE_DIR / 'benchmark_mesh.py'


class FakeMesh:
    constructions = 0

    def __init__(self, points, cells):
        self.points, self.cells = points, cells
        FakeMesh.constructions += 1


TORCH = SimpleNamespace(linalg=SimpleNamespace(
    cross=lambda a, b, dim: np.cross(a, b, axis=dim),
    vector_norm=lambda a, dim: np.linalg.norm(a, axis=dim)))


class CrossTests(unittest.TestCase):
    def setUp(self):
        self.b = adapter.load(LIBRARY)
        self.points = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]])
        self.cells = np.array([[0, 1, 2]], dtype=np.int64)

    def test_area_and_oriented_unit_normal(self):
        values = adapter.compute(TORCH, FakeMesh, self.points, self.cells)
        np.testing.assert_array_equal(values['areas'], [0.5])
        np.testing.assert_array_equal(values['unit_normals'], [[0., 0., 1.]])
        reversed_values = adapter.compute(TORCH, FakeMesh, self.points, self.cells[:, ::-1])
        np.testing.assert_array_equal(reversed_values['areas'], [0.5])
        np.testing.assert_array_equal(reversed_values['unit_normals'], [[0., 0., -1.]])

    def test_skinny_gram_counterexample_stays_positive(self):
        s = 2. ** -30
        self.points[2] = [1., s, 0.]
        values = adapter.compute(TORCH, FakeMesh, self.points, self.cells)
        np.testing.assert_array_equal(values['areas'], [s / 2])
        np.testing.assert_array_equal(values['unit_normals'], [[0., 0., 1.]])

    def test_small_nonzero_triangle_has_unit_normal_without_epsilon(self):
        s = 2. ** -30
        values = adapter.compute(TORCH, FakeMesh, self.points * s, self.cells)
        np.testing.assert_array_equal(values['areas'], [s * s / 2])
        np.testing.assert_array_equal(values['unit_normals'], [[0., 0., 1.]])

    def test_degenerate_normal_not_falsely_claimed_unit(self):
        self.points[2] = [2., 0., 0.]
        with np.errstate(invalid='ignore'):
            values = adapter.compute(TORCH, FakeMesh, self.points, self.cells)
        self.assertEqual(values['areas'][0], 0.)
        self.assertTrue(np.isnan(values['unit_normals']).all())
        self.assertFalse(self.b.compare(values['unit_normals'], np.array([[0., 0., 1.]]))['passed'])

    def test_inputs_and_connectivity_unchanged(self):
        before = [self.b.array_sha(a) for a in (self.points, self.cells)]
        adapter.compute(TORCH, FakeMesh, self.points, self.cells)
        self.assertEqual(before, [self.b.array_sha(a) for a in (self.points, self.cells)])

    def test_warmup_plus_five_uncached_calls(self):
        FakeMesh.constructions = 0
        syncs = []
        _, timing = self.b.repeated(lambda: adapter.compute(TORCH, FakeMesh, self.points, self.cells), lambda: syncs.append(1))
        self.assertEqual(FakeMesh.constructions, 6)
        self.assertEqual(len(timing['repetitions_seconds']), 5)
        self.assertEqual(len(syncs), 12)

    def test_modified_library_rejected_before_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'changed.py'
            path.write_text('raise RuntimeError("must_not_execute")')
            with self.assertRaisesRegex(ValueError, 'library_pin_mismatch'):
                adapter.load(path)

    def test_main_failure_private_summary_and_alarm_cleanup(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'output'
            argv = ['adapter', '--library', str(LIBRARY), '--mesh', 'm', '--reference', 'r', '--reference-report', 'j', '--output', str(output)]
            with patch('sys.argv', argv), patch.object(adapter, 'run', side_effect=RuntimeError('private coordinates not for stdout')), \
                    patch.object(adapter.signal, 'signal', return_value='previous') as handler, patch.object(adapter.signal, 'alarm') as alarm, \
                    contextlib.redirect_stdout(io.StringIO()) as captured:
                result = adapter.main()
            self.assertEqual(result, 2)
            self.assertNotIn('private', captured.getvalue())
            self.assertLess(len(captured.getvalue()), 4096)
            self.assertEqual([call.args[0] for call in alarm.call_args_list], [300, 0])
            self.assertEqual(handler.call_args.args, (adapter.signal.SIGALRM, 'previous'))
            report = json.loads((output / 'report.json').read_text())
            self.assertFalse(report['process_completed'])
            self.assertFalse(report['CFD_authorized'])
            self.assertFalse(report['manufacturing_authorized'])
            self.assertEqual(report['error_type'], 'RuntimeError')

    def test_expiration(self):
        with self.assertRaisesRegex(TimeoutError, 'benchmark_300s_limit'):
            adapter.expired(None, None)


if __name__ == '__main__':
    unittest.main()
