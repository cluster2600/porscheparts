"""Independent synthetic controls for the local analytic study components."""
import unittest

try:
    import numpy as np
    import scipy
    from scripts.scan_feature_study import (
        axis_frame, cavity_variance, fit_cylinder, fit_plane, inspect_circle, inspect_cylinder, split_source_ids,
    )
except ImportError:
    np = None


@unittest.skipIf(np is None, "scan feature controls require NumPy/SciPy")
class ScanFeatureStudyTests(unittest.TestCase):
    def cylinder(self, angle=360., span=8., radius=5., tilt=.12):
        theta = np.linspace(0, np.radians(angle), 90, endpoint=False)
        z = np.linspace(-span / 2, span / 2, 16)
        theta, z = np.meshgrid(theta, z)
        points = np.c_[radius * np.cos(theta.ravel()), radius * np.sin(theta.ravel()), z.ravel()]
        rotation = np.array([[np.cos(tilt), 0, np.sin(tilt)], [0, 1, 0], [-np.sin(tilt), 0, np.cos(tilt)]])
        return points @ rotation.T + [12, -18, 25], rotation

    def test_noisy_tilted_cylinder_recovers_known_geometry_on_disjoint_points(self):
        points, rotation = self.cylinder()
        points += np.random.default_rng(19).normal(0, .01, points.shape)
        train, evaluation = split_source_ids(np.arange(len(points)))
        model = fit_cylinder(points[train], [0, 0, 1])
        report = inspect_cylinder(model, points[evaluation], [0, 0, 1])
        self.assertTrue(report["retained_as_scan_fit_candidate"])
        self.assertAlmostEqual(model["radius_mm"], 5., delta=.01)
        self.assertGreater(abs(np.array(model["axis_direction"]) @ rotation[:, 2]), .9999)
        self.assertLess(report["p95_mm"], .03)

    def test_partial_arc_and_short_support_are_refused(self):
        for angle, span, reason in [(180., 8., "angular"), (360., .4, "axial_span")]:
            points, _ = self.cylinder(angle=angle, span=span, tilt=0.)
            train, evaluation = split_source_ids(np.arange(len(points)))
            result = inspect_cylinder(fit_cylinder(points[train], [0, 0, 1]), points[evaluation], [0, 0, 1])
            self.assertFalse(result["retained_as_scan_fit_candidate"])
            self.assertTrue(any(reason in r for r in result["rejection_reasons"]))

    def test_non_cylindrical_heldout_geometry_does_not_pass(self):
        points, _ = self.cylinder(tilt=0.)
        train, evaluation = split_source_ids(np.arange(len(points)))
        model = fit_cylinder(points[train], [0, 0, 1])
        distorted = points[evaluation].copy()
        distorted[:, 0] += 1.5 * np.sign(distorted[:, 0] - 12)
        report = inspect_cylinder(model, distorted, [0, 0, 1])
        self.assertIn("evaluation_residual_exceeds_limit", report["rejection_reasons"])

    def test_plane_rank_and_prediction(self):
        x, y = np.meshgrid(np.linspace(-2, 2, 9), np.linspace(-3, 3, 9))
        points = np.c_[x.ravel(), y.ravel(), (2 + .2 * x - .3 * y).ravel()]
        model = fit_plane(points[::2])
        self.assertLess(abs(points[1::2] @ model["normal"] - model["offset_mm"]).max(), 1e-10)
        with self.assertRaisesRegex(ValueError, "collinear"):
            fit_plane(np.c_[np.arange(10), np.zeros((10, 2))])

    def test_cavity_statistic_rejects_boss_and_planar_patch(self):
        theta = np.linspace(0, 2 * np.pi, 180, endpoint=False)
        points = np.c_[5 * np.cos(theta), 5 * np.sin(theta), np.zeros(len(theta))]
        radial = points / 5
        hole = cavity_variance(points, -radial, np.ones(len(points)))
        boss = cavity_variance(points, radial, np.ones(len(points)))
        plane = cavity_variance(points, np.tile([0, 0, 1], (len(points), 1)), np.ones(len(points)))
        self.assertTrue(hole["hollow_candidate"])
        self.assertFalse(boss["hollow_candidate"])
        self.assertFalse(plane["hollow_candidate"])
        self.assertEqual(hole["through_or_blind"], "unresolved_by_this_statistic")

    def test_cavity_statistic_invariant_to_translation_rotation_and_face_splitting(self):
        points, _ = self.cylinder(tilt=0.)
        rotation, _ = np.linalg.qr(np.random.default_rng(37).normal(size=(3, 3)))
        normals = points - [12, -18, 25]
        normals[:, 2] = 0
        normals /= np.linalg.norm(normals, axis=1)[:, None]
        first = cavity_variance(points, -normals, np.ones(len(points)))
        moved = cavity_variance(points @ rotation.T + [30, 20, -50], -normals @ rotation.T, np.ones(len(points)))
        split = cavity_variance(np.repeat(points, 2, axis=0), np.repeat(-normals, 2, axis=0), np.ones(2 * len(points)) / 2)
        for name in ["variance_plus_mm2", "variance_minus_mm2"]:
            self.assertAlmostEqual(first[name], moved[name], places=9)
            self.assertAlmostEqual(first[name], split[name], places=9)

    def test_rim_fit_does_not_claim_functional_identity(self):
        theta = np.linspace(0, 2 * np.pi, 360, endpoint=False)
        points = np.c_[7 * np.cos(theta), 7 * np.sin(theta), np.ones(len(theta))]
        rim = inspect_circle(points)
        self.assertTrue(rim["circular_rim_candidate"])
        self.assertAlmostEqual(rim["diameter_mm"], 14)
        self.assertFalse(rim["functional_hole_identity_accepted"])
        points[:, 0] *= 2
        self.assertFalse(inspect_circle(points)["circular_rim_candidate"])

    def test_invalid_inputs_and_source_id_partition(self):
        for ids in [[0, 0], [-1, 2], [1., 2.]]:
            with self.assertRaises(ValueError):
                split_source_ids(np.array(ids))
        train, held = split_source_ids(np.arange(100))
        self.assertFalse(set(train) & set(held))
        self.assertEqual(sorted(np.r_[train, held]), list(range(100)))
        for axis in [[0, 0, 0], [np.nan, 0, 1]]:
            with self.assertRaises(ValueError):
                axis_frame(axis)
        with self.assertRaises(ValueError):
            cavity_variance(np.zeros((4, 3)), np.zeros((4, 3)), np.ones(4))

    def test_independent_checker_rejects_score_or_acceptance_promotion(self):
        from scripts.validate_scan_feature_study import verify_evaluation
        points, _ = self.cylinder(tilt=0.)
        model = {"kind": "cylinder", "axis_direction": [0., 0., 1.],
                 "axis_origin_mm": [12., -18., 25.], "radius_mm": 5.}
        record = inspect_cylinder(model, points, [0, 0, 1])
        record["id"] = "synthetic"
        limits = {"p95_limit_mm": .4, "minimum_span_mm": 3., "minimum_coverage_degrees": 300.,
                  "maximum_tilt_degrees": 15.}
        self.assertTrue(verify_evaluation(model, points, record, limits, [0, 0, 1])["passed"])
        for field, value in [("p95_mm", .2), ("retained_as_scan_fit_candidate", False),
                             ("physical_dimension_accepted", True), ("coverage_by_axial_third_degrees", [360., 360., 360.])]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                verify_evaluation(model, points, {**record, field: value}, limits, [0, 0, 1])

    def test_independent_checker_rejects_partition_loss_and_leakage(self):
        from scripts.validate_scan_feature_study import verify_partition
        selected = np.arange(30)
        train, held = split_source_ids(selected)
        verify_partition(selected, train, held)
        for bad_train, bad_held in [(train[1:], held), (np.r_[train, held[:1]], held), (train, held[1:])]:
            with self.assertRaises(ValueError):
                verify_partition(selected, bad_train, bad_held)


if __name__ == "__main__":
    unittest.main()
