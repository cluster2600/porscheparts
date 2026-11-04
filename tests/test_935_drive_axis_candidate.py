"""Small geometry controls for the provisional drive scan selection."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

import numpy as np

SOURCE = (Path(__file__).resolve().parents[1] /
          'twins/935-horizontal-cooling-system-f0/source/fragment-frames-20261104' /
          'fit_drive_axis_candidate.py')
spec = importlib.util.spec_from_file_location('drive_axis_candidate', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DriveAxisSelectionTests(unittest.TestCase):
    def test_window_and_normal_filter(self):
        # The first triangle is near radius 7 and has a radial-facing normal.
        triangles = np.array([[[7., 0, -10], [7., 1, -10], [7., 0, -9]],
                              [[20., 0, -10], [20., 1, -10], [20., 0, -9]],
                              [[7., 0, -10], [8., 0, -10], [7., 1, -10]],
                              [[7., 0, -10], [7., 0, -10], [7., 0, -10]]])
        centres, normals, keep = module.select(triangles)
        self.assertEqual(keep.tolist(), [True, False, False, False])
        self.assertAlmostEqual(float(np.linalg.norm(normals[0])), 1.)
        self.assertEqual(centres.shape, (4, 3))

    def test_rejects_unpinned_input(self):
        with tempfile.TemporaryDirectory(dir='work') as directory:
            scan = Path(directory) / 'wrong.stl'
            scan.write_bytes(b'not a scan')
            out = Path(directory) / 'new-output'
            with self.assertRaisesRegex(ValueError, 'Pinned'):
                module.run(scan, out)
            self.assertFalse(out.exists())
