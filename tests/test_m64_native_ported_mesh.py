"""Pure witnesses for signed volume and native ported-head mesh connectivity."""
import importlib.util
from pathlib import Path
import unittest


SOURCE = Path(__file__).resolve().parents[1] / "twins/m64-cylinder-head/source/mesh_native_ported_head.py"
SPEC = importlib.util.spec_from_file_location("m64_native_ported_mesh", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class NativePortedMeshTests(unittest.TestCase):
    def setUp(self):
        self.points = {
            11: (0., 0., 0.),
            23: (1., 0., 0.),
            47: (0., 1., 0.),
            89: (0., 0., 1.),
        }
        self.tetrahedra = [(11, 23, 47, 89)]
        self.triangles = [
            (47, 23, 11), (11, 23, 89), (89, 47, 11), (23, 47, 89),
        ]

    def test_quality_count_and_volume_fractions_are_distinct(self):
        report = MODULE.quality_distribution([.01, .5], [6., 54.])
        self.assertEqual(report['bad_tetrahedron_count_fraction'], .5)
        self.assertEqual(report['bad_tetrahedron_absolute_volume_fraction'], .1)
        self.assertEqual(report['minSICN_below_0p1'], 1)
        self.assertEqual(report['nonpositive_Jacobians'], 0)
        for quality, determinants in (([], []), ([.5], []), ([float('nan')], [1.])):
            with self.assertRaises(ValueError):
                MODULE.quality_distribution(quality, determinants)

    def test_positive_tetra_with_noncontiguous_tags_and_complete_boundary(self):
        volume = MODULE.signed_tetra_volume(*(self.points[tag] for tag in self.tetrahedra[0]))
        self.assertAlmostEqual(volume, 1 / 6)
        report = MODULE.connectivity_metrics(self.points, self.tetrahedra, self.triangles)
        self.assertAlmostEqual(report["signed_volume_sum"], 1 / 6)
        self.assertAlmostEqual(report["absolute_volume_sum"], 1 / 6)
        for key in ("count_negative", "count_zero", "repeated_node_tetrahedra",
                    "boundary_missing_triangles", "stored_triangles_not_on_boundary",
                    "duplicate_stored_triangles", "nonmanifold_faces"):
            with self.subTest(metric=key):
                self.assertEqual(report[key], 0)
        self.assertEqual(report["tetra_connected_components"], 1)
        self.assertTrue(report["boundary_matches"])

    def test_inversion_and_missing_boundary_triangle_are_both_reported(self):
        report = MODULE.connectivity_metrics(
            self.points, [(11, 47, 23, 89)], self.triangles[:-1])
        self.assertAlmostEqual(report["signed_volume_sum"], -1 / 6)
        self.assertAlmostEqual(report["absolute_volume_sum"], 1 / 6)
        self.assertEqual(report["count_negative"], 1)
        self.assertEqual(report["count_zero"], 0)
        self.assertEqual(report["boundary_missing_triangles"], 1)
        self.assertEqual(report["stored_triangles_not_on_boundary"], 0)
        self.assertEqual(report["nonmanifold_faces"], 0)
        self.assertFalse(report["boundary_matches"])

    def test_two_separate_tetrahedra_have_two_components(self):
        points = dict(self.points)
        points.update({
            101: (3., 0., 0.), 205: (4., 0., 0.),
            307: (3., 1., 0.), 401: (3., 0., 1.),
        })
        triangles = self.triangles + [
            (101, 205, 307), (101, 205, 401),
            (101, 307, 401), (205, 307, 401),
        ]
        report = MODULE.connectivity_metrics(
            points, self.tetrahedra + [(101, 205, 307, 401)], triangles)
        self.assertEqual(report["tetra_connected_components"], 2)
        self.assertAlmostEqual(report["signed_volume_sum"], 1 / 3)
        self.assertEqual(report["count_negative"], 0)
        self.assertEqual(report["boundary_missing_triangles"], 0)
        self.assertEqual(report["nonmanifold_faces"], 0)
        self.assertTrue(report["boundary_matches"])

    def test_three_tetrahedra_sharing_one_face_are_nonmanifold(self):
        points = dict(self.points)
        points.update({107: (0., 0., -1.), 223: (0., 0., 2.)})
        tetrahedra = [(11, 23, 47, 89), (11, 47, 23, 107), (11, 23, 47, 223)]
        # All nine singly incident faces are present; the shared face has
        # three incident tetrahedra and must independently reject the boundary.
        triangles = [
            (11, 23, 89), (11, 47, 89), (23, 47, 89),
            (11, 23, 107), (11, 47, 107), (23, 47, 107),
            (11, 23, 223), (11, 47, 223), (23, 47, 223),
        ]
        report = MODULE.connectivity_metrics(points, tetrahedra, triangles)
        self.assertEqual(report["nonmanifold_faces"], 1)
        self.assertEqual(report["boundary_missing_triangles"], 0)
        self.assertEqual(report["stored_triangles_not_on_boundary"], 0)
        self.assertEqual(report["count_negative"], 0)
        self.assertFalse(report["boundary_matches"])


if __name__ == "__main__":
    unittest.main()
