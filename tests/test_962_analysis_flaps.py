"""Exact zero-thickness fin recognition; no approximate or feature deletion."""
from pathlib import Path
import sys
import unittest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "twins/962-cylinder-head-f0/source"))
from cancel_analysis_flaps import cancel_exact_fins


class ExactFinTests(unittest.TestCase):
    def setUp(self):
        self.points = np.array([[0., 0, 0], [1., 0, 0], [0., 1, 0], [0., 0, 1], [.5, -.5, 0]])
        self.tetra = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]])

    def test_exact_opposite_fin_maps_without_welding(self):
        faces = np.vstack([self.tetra, [0, 1, 4], [1, 0, 4]])
        q, g, rows, vm, fm = cancel_exact_fins(self.points, faces)
        self.assertTrue(np.array_equal(q, self.points[:4]))
        self.assertTrue(np.array_equal(g, self.tetra))
        self.assertEqual(vm.tolist(), [0, 1, 2, 3, -1])
        self.assertEqual(fm.tolist(), [0, 1, 2, 3, -1, -1])
        self.assertEqual(rows[0]["attachment_edge"], [0, 1])

    def test_same_orientation_duplicate_rejected(self):
        faces = np.vstack([self.tetra, [0, 1, 4], [0, 1, 4]])
        with self.assertRaisesRegex(ValueError, "opposite"):
            cancel_exact_fins(self.points, faces)

    def test_isolated_two_face_sheet_cannot_be_deleted(self):
        with self.assertRaisesRegex(ValueError, "exactly one tip"):
            cancel_exact_fins(self.points, np.array([[0, 1, 4], [1, 0, 4]]))

    def test_valid_geometry_is_not_repaired(self):
        with self.assertRaisesRegex(ValueError, "not applicable"):
            cancel_exact_fins(self.points[:4], self.tetra)


if __name__ == "__main__":
    unittest.main()
