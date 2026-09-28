import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "generate_993_turbo_integration_seed.py"
SPEC = importlib.util.spec_from_file_location(
    "generate_993_turbo_integration_seed", MODULE_PATH
)
generator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(generator)


class TurboIntegrationSeedTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = generator.build()
        generator.validate(self.contract)

    def test_target_is_reversible_1998_row_turbo_hypothesis(self) -> None:
        target = self.contract["integration_target"]
        candidate = target["configuration_candidate"]
        self.assertEqual(
            candidate["configuration_candidate_id"],
            "CONFIG-CANDIDATE-993-32037F10BE2E4BFAEC9A",
        )
        self.assertEqual(candidate["model_family"], "turbo")
        self.assertEqual(candidate["model_year"], 1998)
        self.assertEqual(candidate["market_group"], "rest_of_world_unmarked")
        self.assertEqual(candidate["engine_code"], "M64.60")
        self.assertEqual(candidate["transmission_code"], "G64.51")
        self.assertEqual(candidate["source_anomalies"], [])
        self.assertTrue(target["selection_reversible"])
        self.assertFalse(target["promoted_to_configured_vehicle"])

    def test_seed_covers_all_systems_but_is_not_a_bom(self) -> None:
        scope = self.contract["scope"]
        self.assertEqual(scope["candidate_occurrences"], 325)
        self.assertEqual(scope["candidate_part_masters"], 316)
        self.assertEqual(scope["candidate_instance_quantity_sum"], 580)
        self.assertEqual(scope["human_read_variant_occurrences"], 10)
        self.assertEqual(scope["single_dimension_constraint_occurrences"], 315)
        self.assertEqual(
            scope["direct_turbo_annotation_occurrences_within_constraints"], 108
        )
        self.assertEqual(
            set(self.contract["coverage"]["candidate_occurrences_by_system"]),
            {"0xx", "1xx", "2xx", "3xx", "4xx", "5xx", "6xx", "7xx", "8xx", "9xx"},
        )
        self.assertEqual(scope["configured_vehicle_bom_entries"], 0)
        self.assertFalse(scope["functioning_vehicle_claim"])

    def test_known_engineering_evidence_gaps_are_visible(self) -> None:
        coverage = self.contract["coverage"]
        self.assertEqual(len(coverage["detailed_engineering_master_ids_in_seed"]), 2)
        self.assertEqual(len(coverage["detailed_engineering_master_ids_outside_seed"]), 6)
        self.assertIn(
            "TWIN-PET-993-PART-F77CBF8A0C10743C3178",
            coverage["detailed_engineering_master_ids_in_seed"],
        )
        self.assertIn(
            "TWIN-PET-993-PART-62DA237715E2C0D682AE",
            coverage["detailed_engineering_master_ids_outside_seed"],
        )

    def test_every_candidate_entry_stays_unreleased(self) -> None:
        ids = [
            item["occurrence_twin_id"] for item in self.contract["candidate_entries"]
        ]
        self.assertEqual(len(ids), len(set(ids)))
        for item in self.contract["candidate_entries"]:
            self.assertFalse(item["promoted_to_vehicle_bom"])
            self.assertIsNone(item["mounted_transform"])
            self.assertIsNone(item["geometry_revision"])
            self.assertIsNone(item["selected_material"])
            self.assertIsNone(item["manufacturing_route"])

    def test_checked_in_seed_is_current(self) -> None:
        self.assertEqual(generator.main(["--check"]), 0)
        self.assertEqual(
            json.loads(generator.OUTPUT.read_text(encoding="utf-8")), self.contract
        )


if __name__ == "__main__":
    unittest.main()
