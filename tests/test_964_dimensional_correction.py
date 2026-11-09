import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("dimensional_audit", ROOT /
    "twins/964-chassis/dimensional-correction-20261106/audit.py")
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class DimensionalCorrectionTests(unittest.TestCase):
    def observation(self):
        return {"observation_id": "synthetic-span", "part_identity": "dimensioned fixture contact pair",
                "comparison_kind": "direct_distance", "source_scalar_mm": 100,
                "source_tolerance_mm": 1, "unit": "mm"}

    def binding(self):
        return {"feature_ids": ["a", "b"], "part_identity": "dimensioned fixture contact pair",
                "identity_status": "independently_qualified", "same_frame_admitted": True}

    def test_wrong_actual_mapped_distance_fails(self):
        model = {"units": "mm", "source_features_mm": {"a": [0, 0, 0], "b": [110, 0, 0]}}
        result = AUDIT.compare_distance(self.observation(), model, self.binding())
        self.assertEqual(result["model_value_mm"], 110)
        self.assertEqual(result["delta_mm"], 10)
        self.assertFalse(result["within_source_tolerance"])
        model["source_features_mm"]["b"] = [100, 0, 0]
        correct = AUDIT.compare_distance(self.observation(), model, self.binding())
        self.assertEqual(correct["model_value_mm"], 100)
        self.assertEqual(correct["delta_mm"], 0)
        self.assertTrue(correct["within_source_tolerance"])
        wrong_units = dict(self.observation(), unit="inch")
        self.assertIsNone(AUDIT.compare_distance(wrong_units, model, self.binding())["delta_mm"])

    def test_citations_nominal_wheelbase_and_flat_landmark_do_not_bind_contacts(self):
        model = {"units": "mm", "wheelbase_mm": 2272, "floor_z": 0,
                 "measurement_ids": ["synthetic-span"]}
        rows, summary = AUDIT.coverage([self.observation()], model, {"synthetic-span": self.binding()})
        self.assertEqual(summary["implemented_comparisons"], 0)
        self.assertFalse(summary["reconstruction_admitted"])
        self.assertIsNone(rows[0]["model_value_mm"])
        self.assertIsNone(rows[0]["delta_mm"])

    def test_unregistered_or_wrong_physical_feature_keeps_delta_null(self):
        model = {"units": "mm", "source_features_mm": {"a": [0, 0, 0], "b": [100, 0, 0]}}
        binding = self.binding()
        binding["same_frame_admitted"] = False
        self.assertIsNone(AUDIT.compare_distance(self.observation(), model, binding)["delta_mm"])
        binding["same_frame_admitted"] = True
        binding["part_identity"] = "different bolt or floor skin"
        self.assertIsNone(AUDIT.compare_distance(self.observation(), model, binding)["delta_mm"])

    def test_actual_frozen_f2_has_no_source_contact_comparison(self):
        model = json.loads((ROOT /
            "twins/964-chassis/sculpted-cell-f2-20261106/canonical-model.json").read_text())
        rows, summary = AUDIT.coverage([self.observation()], model, {})
        self.assertEqual(summary["implemented_comparisons"], 0)
        self.assertFalse(summary["reconstruction_admitted"])
        self.assertFalse(summary["inventory_is_required_geometry_contract"])
        self.assertIsNone(rows[0]["model_value_mm"])
        self.assertIsNone(rows[0]["delta_mm"])

    def test_effective_b_width_overlay_preserves_catalogue_and_no_model_delta(self):
        path = ROOT / "catalog/measurements/MEAS-OWNER-964-FRAME-20261105.json"
        before = path.read_bytes()
        rows = AUDIT.rows_from_registry(path, AUDIT.REGISTRIES["MEAS-OWNER-964-FRAME-20261105"])
        effective = AUDIT.apply_mi_b_overlay(rows, ROOT)
        bolt = next(r for r in effective if r["observation_id"] == "MNL-FD964-MI-B-BOLT")
        original = next(r for r in json.loads(before)["declared_values"] if r["value_id"] == bolt["observation_id"])
        self.assertEqual(json.loads(bolt["source_values"]), original["numeric_values"])
        self.assertIsNone(json.loads(bolt["endpoint_or_state_definition"])["components"]["half_width"])
        self.assertEqual(bolt["effective_half_width_mm"], 306)
        self.assertEqual(json.loads(bolt["effective_source_values"])["combined_equal_opposed_span"], 612)
        self.assertEqual(bolt["source_amendment_sha256"], AUDIT.sha(ROOT / AUDIT.MI_B_AMENDMENT))
        checked, summary = AUDIT.coverage(effective, {"units": "mm"}, {})
        self.assertEqual(summary["implemented_comparisons"], 0)
        self.assertTrue(all(r["model_value_mm"] is None and r["delta_mm"] is None for r in checked))
        self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
