import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "validate_catalogue_part_physicsnemo.py"
SPEC = importlib.util.spec_from_file_location("validate_catalogue_part_physicsnemo", MODULE_PATH)
validator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(validator)


class CataloguePartPhysicsNeMoTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = validator.validate()

    def test_live_discovery_and_runtime_pin_are_separate(self) -> None:
        discovery = self.contract["discovery"]
        self.assertEqual(discovery["current_snapshot"]["version"], "2.3.0a0")
        self.assertEqual(discovery["runtime_snapshot"]["version"], "2.2.0")
        self.assertEqual(discovery["runtime_snapshot"]["tag"], "v2.2.0")

    def test_model_and_datapipe_are_independent_axes(self) -> None:
        models = {entry["model"] for entry in self.contract["model_menu"]}
        point_cloud = next(
            entry
            for entry in self.contract["datapipe_menu"]
            if entry["name"] == "DropTestPointCloudDataset_pattern"
        )
        self.assertEqual(set(point_cloud["model_families"]), {"GeoTransolver", "Transolver", "FIGConvUNet"})
        self.assertTrue(set(point_cloud["model_families"]) < models)

    def test_selected_pilot_stays_disabled_without_reference_data(self) -> None:
        pilot = self.contract["selected_pilot"]
        self.assertEqual(pilot["model"], "GeoTransolver")
        self.assertFalse(pilot["execution_enabled"])
        self.assertTrue(all(value is False for value in self.contract["enablement_gates"].values()))

    def test_dataset_split_is_grouped_and_empty(self) -> None:
        split = self.contract["dataset_contract"]["split_policy"]
        self.assertEqual(split["method"], "grouped_by_geometry_revision_and_load_envelope")
        self.assertTrue(split["random_node_split_prohibited"])
        self.assertEqual(sum(split[key] for key in ("train_samples", "validation_samples", "held_out_test_samples")), 0)


if __name__ == "__main__":
    unittest.main()
