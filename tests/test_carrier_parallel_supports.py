"""Ordered support workers must retain exact cuts, identities and cleanup."""
import sys
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'parts/993-eng-carrier-0001/source/process-support-slicing-20261016'
sys.path.insert(0, str(SOURCE))
try:
    import numpy as np
    from parallel_support_sections import ParallelSupportSections, support_section
except ImportError:
    np = None


@unittest.skipIf(np is None, 'NumPy support-slicing runtime unavailable')
class ParallelSupportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.paths, self.surfaces, self.bounds = [], [], []
        for x in (0., 1.):
            vertices = np.array([[x, 0., 0.], [x, 2., 0.], [x, 0., 2.]])
            faces = np.array([[0, 1, 2]], dtype=np.int64)
            path = Path(self.temp.name) / f'support-{int(x):03d}.npz'
            np.savez(path, vertices=vertices, faces=faces)
            self.paths.append(path)
            self.surfaces.append(SimpleNamespace(vertices=vertices, faces=faces))
            self.bounds.append(np.array([[0., 2.]]))
        self.heights = [.25, .5, 1., 1.75]

    def test_all_regions_and_layers_equal_serial_and_workers_close(self):
        calculate = ParallelSupportSections(self.paths, self.heights, workers=2)
        expected = [[support_section(s, z, b) for s, b in zip(self.surfaces, self.bounds)] for z in self.heights]
        with calculate:
            for i, z in enumerate(self.heights):
                for j, (surface, bounds) in enumerate(zip(self.surfaces, self.bounds)):
                    self.assertTrue(np.array_equal(calculate(surface, z, bounds), expected[i][j]))
        self.assertTrue(calculate.receipt()['worker_group_closed'])
        self.assertEqual(calculate.receipt()['completed_layers'], 4)
        self.assertEqual(calculate.receipt()['completed_surfaces_in_current_layer'], 0)

    def test_wrong_surface_identity_refused_and_workers_still_close(self):
        calculate = ParallelSupportSections(self.paths, self.heights, workers=2)
        with self.assertRaisesRegex(ValueError, 'surface or bounds'), calculate:
            calculate(self.surfaces[1], self.heights[0], self.bounds[1])
        self.assertTrue(calculate.receipt()['worker_group_closed'])

    def test_skipped_midplane_refused_and_workers_still_close(self):
        calculate = ParallelSupportSections(self.paths, self.heights, workers=2)
        with self.assertRaisesRegex(ValueError, 'ordered midplanes'), calculate:
            calculate(self.surfaces[0], self.heights[1], self.bounds[0])
        self.assertTrue(calculate.receipt()['worker_group_closed'])

    def test_submission_failure_closes_the_new_worker_group(self):
        calculate = ParallelSupportSections(self.paths, self.heights, workers=2)
        with patch.object(calculate, '_submit', side_effect=RuntimeError('injected startup refusal')):
            with self.assertRaisesRegex(RuntimeError, 'startup refusal'):
                calculate.__enter__()
        self.assertTrue(calculate.receipt()['worker_group_closed'])


if __name__ == '__main__':
    unittest.main()
