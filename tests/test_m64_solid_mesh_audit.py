from _deps import require_modules
require_modules("numpy")

import importlib.util
from pathlib import Path
import unittest

import numpy as np


SOURCE = Path(__file__).resolve().parents[1] / "twins/m64-cylinder-head/audit_solid_mesh.py"
SPEC = importlib.util.spec_from_file_location("m64_solid_mesh", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SolidMeshAuditTests(unittest.TestCase):
    def setUp(self):
        self.points = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.], [0., 0., 1.]])
        self.cells = np.array([[0, 1, 2, 3]])
        self.surface = np.array([[0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3]])

    def test_analytic_tetra_volume(self):
        self.assertAlmostEqual(MODULE.signed_tetra_volumes(self.points, self.cells)[0], 1 / 6)

    def test_inversion_not_hidden_by_absolute_value(self):
        self.assertLess(MODULE.signed_tetra_volumes(self.points, np.array([[0, 2, 1, 3]]))[0], 0)

    def test_degenerate_tetra_is_zero(self):
        points = self.points.copy()
        points[3] = points[0]
        self.assertEqual(MODULE.signed_tetra_volumes(points, self.cells)[0], 0)

    def test_nonfinite_points_rejected(self):
        self.points[0, 0] = np.nan
        with self.assertRaisesRegex(ValueError, "finite_3d"):
            MODULE.signed_tetra_volumes(self.points, self.cells)

    def test_out_of_range_connectivity_rejected(self):
        with self.assertRaisesRegex(ValueError, "connectivity"):
            MODULE.signed_tetra_volumes(self.points, np.array([[0, 1, 2, 9]]))

    def test_complete_surface_matches(self):
        report = MODULE.boundary_summary(self.cells, self.surface)
        self.assertTrue(report["boundary_connectivity_matches_stored_surface"])
        self.assertEqual(report["tetra_boundary_triangles"], 4)

    def test_missing_triangle_rejected(self):
        report = MODULE.boundary_summary(self.cells, self.surface[:-1])
        self.assertFalse(report["boundary_connectivity_matches_stored_surface"])
        self.assertEqual(report["tetra_boundary_triangles_missing_from_surface"], 1)

    def test_duplicate_surface_rejected(self):
        report = MODULE.boundary_summary(self.cells, np.concatenate([self.surface, self.surface[:1]]))
        self.assertEqual(report["duplicate_stored_triangles"], 1)
        self.assertFalse(report["boundary_connectivity_matches_stored_surface"])

    def test_internal_face_is_not_boundary(self):
        cells = np.array([[0, 1, 2, 3], [0, 2, 1, 4]])
        surface = np.array([[0, 1, 3], [0, 2, 3], [1, 2, 3], [0, 1, 4], [0, 2, 4], [1, 2, 4]])
        report = MODULE.boundary_summary(cells, surface)
        self.assertEqual(report["internal_triangle_faces"], 1)
        self.assertTrue(report["boundary_connectivity_matches_stored_surface"])

    def test_nonmanifold_face_rejected(self):
        cells = np.array([[0, 1, 2, 3], [0, 1, 2, 4], [0, 1, 2, 5]])
        report = MODULE.boundary_summary(cells, self.surface)
        self.assertEqual(report["nonmanifold_triangle_faces"], 1)
        self.assertFalse(report["boundary_connectivity_matches_stored_surface"])

    def test_project_threshold_is_not_positivity_only(self):
        report = MODULE.quality_summary(np.array([.8, .00001]))
        self.assertEqual(report["count_le_zero"], 0)
        self.assertEqual(report["count_lt_0p1"], 1)
        self.assertFalse(report["project_quality_gate_passed"])

    def test_nonfinite_quality_rejected(self):
        with self.assertRaisesRegex(ValueError, "finite_nonempty"):
            MODULE.quality_summary(np.array([np.nan]))


if __name__ == "__main__":
    unittest.main()
