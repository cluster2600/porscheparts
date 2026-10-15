"""Analytical witnesses for conservative all-angle mesh separation bounds."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from _deps import require_modules
require_modules("numpy", "scipy", "trimesh")
import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "twins/bionic-turbo-f1/compare_geometry.py"
SPEC = importlib.util.spec_from_file_location("bionic_f1_compare", SCRIPT)
COMPARE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COMPARE)


class BionicF1GeometryTests(unittest.TestCase):
    def test_regularization_and_other_nonstudy_parameters_must_match(self):
        baseline = {"parameters": {"voxel_mm": .5, "regularization_mm": .625,
                     "volute_law": "radius_linear", "chamber_profile": "conical"},
                    "regularization": {"distance_mm": .625}, "kernel": "test"}
        candidate = json.loads(json.dumps(baseline))
        candidate["parameters"].update(volute_law="area_affine", chamber_profile="wheel_shroud")
        COMPARE.require_matched_conditions(baseline, candidate)
        candidate["parameters"]["regularization_mm"] = .5
        with self.assertRaisesRegex(ValueError, "paired_parameters_differ"):
            COMPARE.require_matched_conditions(baseline, candidate)
        candidate["parameters"]["regularization_mm"] = .625
        candidate["regularization"]["distance_mm"] = .5
        with self.assertRaisesRegex(ValueError, "paired_regularization_mismatch"):
            COMPARE.require_matched_conditions(baseline, candidate)
        candidate["regularization"]["distance_mm"] = .625
        candidate["grid_phase_mm"] = [.173, .119, .071]
        with self.assertRaisesRegex(ValueError, "paired_grid_phase_mismatch"):
            COMPARE.require_matched_conditions(baseline, candidate)
        baseline["grid_phase_mm"] = [.173, .119, .071]
        COMPARE.require_matched_conditions(baseline, candidate)

    def test_triangle_interior_reaches_axis_despite_remote_vertices(self):
        triangle = np.array([[[-2, -1, 0], [2, -1, 0], [0, 3, 1]]], dtype=float)
        self.assertGreater(np.linalg.norm(triangle[0, :, :2], axis=1).min(), 2)
        self.assertEqual(COMPARE.projected_min_radius(triangle)[0], 0)
        self.assertEqual(COMPARE.projected_min_radius(triangle[:, ::-1])[0], 0)

    def test_edge_minimum_and_degenerate_projection(self):
        triangles = np.array([[[2, -5, 0], [2, 5, 0], [4, 0, 0]],
                              [[2, -5, 0], [2, 5, 0], [2, -5, 3]],
                              [[-2, 0, 0], [2, 0, 1], [3, 0, 2]],
                              [[2, 3, 0], [2, 3, 1], [2, 3, 2]]], dtype=float)
        np.testing.assert_allclose(COMPARE.projected_min_radius(triangles),
                                   [2, 2, 0, np.sqrt(13)], atol=2e-8, rtol=0)

    def test_regular_cylinder_in_annular_shell_matches_apothem_bound(self):
        sections = 32
        rotor = trimesh.creation.cylinder(radius=1, height=2, sections=sections)
        housing = trimesh.creation.annulus(r_min=3, r_max=4, height=4, sections=sections)
        profile = COMPARE.radial_profile(rotor.triangles, housing.triangles)
        expected = 3 * np.cos(np.pi / sections) - 1
        self.assertEqual(profile["gate"], "positive")
        self.assertAlmostEqual(profile["minimum_radial_gap_lower_mm"], expected, places=7)
        self.assertTrue(profile["axis_outside_material"])
        self.assertEqual(len(profile["bands"]), 20)

    def test_solid_housing_containment_never_passes_radial_bound_alone(self):
        rotor = trimesh.creation.cylinder(radius=1, height=2, sections=32)
        filled_housing = trimesh.creation.cylinder(radius=3, height=4, sections=32)
        profile = COMPARE.radial_profile(rotor.triangles, filled_housing.triangles)
        self.assertTrue(profile["all_radial_bounds_positive"])
        self.assertFalse(profile["axis_outside_material"])
        self.assertEqual(profile["gate"], "indeterminate")

    def test_closed_band_takes_whole_overlapping_triangle_extrema(self):
        rotor = np.array([[[1, 0, -.01], [5, 0, .19], [1, 1, .19]]])
        housing = trimesh.creation.annulus(r_min=8, r_max=9, height=2, sections=32)
        profile = COMPARE.radial_profile(rotor, housing.triangles)
        self.assertGreaterEqual(profile["bands"][0]["rotor_max_radius_upper_mm"], 5)
        self.assertGreaterEqual(profile["bands"][1]["rotor_max_radius_upper_mm"], 5)

    def test_obstacle_through_axis_fails_conservative_gate(self):
        rotor = trimesh.creation.cylinder(radius=1, height=2, sections=32)
        housing = trimesh.creation.annulus(r_min=3, r_max=4, height=4, sections=32)
        obstacle = np.array([[[-4, -2, -.5], [4, -2, .5], [0, 5, .5]]])
        profile = COMPARE.radial_profile(rotor.triangles, np.concatenate((housing.triangles, obstacle)))
        self.assertEqual(profile["gate"], "indeterminate")
        self.assertLess(profile["minimum_radial_gap_lower_mm"], 0)

    def test_nonfinite_empty_and_unbounded_inputs_rejected(self):
        for triangles in (np.empty((0, 3, 3)), np.full((1, 3, 3), np.nan), np.full((1, 3, 3), 1e9)):
            with self.assertRaises(ValueError):
                COMPARE.projected_min_radius(triangles)

    def test_rejected_prior_inspection_cannot_produce_positive_comparison(self):
        rotor = trimesh.creation.cylinder(radius=1, height=2, sections=16)
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            wheel = directory / "compressor-wheel.stl"
            rotor.export(wheel)
            manifest = directory / "wheel-report.json"
            manifest.write_text(json.dumps({"units": "mm", "status": "concept_assembly_generated", "files": [
                {"file": wheel.name, "triangles": len(rotor.faces), "sha256": COMPARE.sha256(wheel)}]}))
            (directory / "inspection.json").write_text(json.dumps({"status": "failed", "geometry_passed": False}))
            report = COMPARE.compare(directory, directory, wheel, manifest, COMPARE.sha256(manifest))
            self.assertEqual(report["gate"], "indeterminate")
            self.assertIn("baseline: prior_inspection_not_passed", report["errors"])
            self.assertFalse(report["profiles"])
            mismatch = COMPARE.compare(directory, directory, wheel, manifest, "0" * 64)
            self.assertIn("wheel_report_sha256_mismatch", mismatch["errors"])


if __name__ == "__main__":
    unittest.main()
