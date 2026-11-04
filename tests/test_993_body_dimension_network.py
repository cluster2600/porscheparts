"""Guard projection conventions and unknown geometry in the 993 source audit."""
import copy
import importlib.util
import json
import math
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "twins/964-chassis/993-body-network-20261104"
SPEC = importlib.util.spec_from_file_location("body_993_network", HERE / "build.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class BodyDimensionNetworkTests(unittest.TestCase):
    def test_signed_height_and_absolute_position_do_not_follow_from_lengths(self):
        result = MODULE.implied_height(5, 0, 3, 0)
        self.assertEqual(result["nominal_abs_delta_z_mm"], 4)
        self.assertEqual(result["worst_case_feasible_interval_mm"], [4, 4])
        self.assertIsNone(result["height_sign"])
        self.assertIsNone(result["absolute_z_mm"])
        self.assertIsNone(result["accepted_coordinate_uncertainty_mm"])

    def test_overlapping_length_bands_admit_zero_height(self):
        result = MODULE.implied_height(5, 1, 4, 1)
        self.assertEqual(result["worst_case_feasible_interval_mm"][0], 0)
        self.assertAlmostEqual(result["worst_case_feasible_interval_mm"][1], math.sqrt(27))
        self.assertIsNone(MODULE.implied_height(5, None, 4, 1)["worst_case_feasible_interval_mm"])

    def test_impossible_or_nonfinite_lengths_are_rejected(self):
        for args in [(3, 0, 5, 0), (float("nan"), 0, 3, 0), (True, 0, 0, 0), (5, -1, 3, 0)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                MODULE.implied_height(*args)

    def test_projection_basis_and_generation_cannot_be_changed_silently(self):
        original = json.loads(MODULE.FLOOR.read_text())
        for mutation in ("basis", "generation", "admission"):
            record = copy.deepcopy(original)
            row = next(v for v in record["declared_values"] if v["value_id"] == "MNL-993FC-S-HORIZONTAL")
            if mutation == "basis":
                row["details"]["measurement_basis"] = "direct_distance"
            elif mutation == "generation":
                row["details"]["endpoint_ids"][0] = "964:P13"
            else:
                row["details"]["functional_geometry_admitted"] = True
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                MODULE.dimensions(record)

    def test_missing_tolerance_is_not_filled_and_no_xyz_is_published(self):
        result = MODULE.build()
        self.assertIsNone(result["drawing_stations"]["993:P3"]["worst_case_half_interval_mm"])
        self.assertNotIn("993:P4", result["drawing_stations"])
        for point in result["drawing_stations"].values():
            self.assertIsNone(point["vehicle_xyz_mm"])
            self.assertIsNone(point["axis"])
            self.assertIsNone(point["mating_face"])
        self.assertFalse(any(result["release_flags"].values()))
        self.assertIsNone(result["unresolved"]["993:P7_span_mm"])
        self.assertIsNone(result["unresolved"]["993:P23_identity"])

    def test_published_analysis_is_reproducible_and_has_full_coverage(self):
        result = MODULE.build()
        self.assertEqual(json.loads((HERE / "analysis.json").read_text()), result)
        self.assertEqual(result["counts"]["combined_scalar_observations"], 40)
        self.assertEqual(result["counts"]["point_identities_with_pair_spans"], 18)
        self.assertEqual(result["counts"]["matching_964_candidate_pairs"], 13)
        closure = result["rear_subframe_projection_check"]
        self.assertTrue(closure["intervals_overlap"])
        self.assertLess(abs(closure["nominal_residual_mm"]), 0.02)
        self.assertGreater(closure["misinterpretation_example"]["difference_from_published_longitudinal_mm"], 38)


if __name__ == "__main__":
    unittest.main()
