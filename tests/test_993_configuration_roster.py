import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "generate_993_configuration_roster.py"
SPEC = importlib.util.spec_from_file_location("generate_993_configuration_roster", MODULE_PATH)
generator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(generator)


class ConfigurationRosterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.roster = json.loads(generator.OUTPUT.read_text(encoding="utf-8"))

    def test_pet_summary_tables_close(self) -> None:
        scope = self.roster["scope"]
        self.assertEqual(scope["type_record_count"], 69)
        self.assertEqual(scope["engine_option_count"], 34)
        self.assertEqual(scope["transmission_option_count"], 40)
        self.assertEqual(scope["configuration_candidate_count"], 149)
        self.assertEqual(scope["type_records_with_candidates"], 67)
        self.assertEqual(scope["type_records_without_candidates"], 2)

    def test_body_and_family_coverage_is_explicit(self) -> None:
        coverage = self.roster["coverage"]
        self.assertEqual(
            coverage["type_records_by_body_or_variant_token"],
            {"CABRIO": 22, "COUPE": 35, "RS": 4, "TARGA": 8},
        )
        self.assertEqual(coverage["type_records_by_model_family"]["turbo"], 12)
        self.assertEqual(coverage["type_records_by_model_family"]["carrera_4_family"], 20)

    def test_only_two_1996_rs_transmission_intersections_are_missing(self) -> None:
        type_by_id = {item["type_record_id"]: item for item in self.roster["type_records"]}
        gaps = self.roster["configuration_gaps"]
        self.assertEqual(len(gaps), 2)
        for gap in gaps:
            type_record = type_by_id[gap["type_record_id"]]
            self.assertEqual(type_record["model_family"], "carrera_rs")
            self.assertEqual(type_record["model_year"], 1996)
            self.assertEqual(gap["missing_dimension"], "transmission_option")

    def test_source_anomalies_are_preserved_not_silently_corrected(self) -> None:
        source_anomaly_types = [
            item for item in self.roster["type_records"] if item["source_anomalies"]
        ]
        source_anomaly_transmissions = [
            item for item in self.roster["transmission_options"] if item["source_anomalies"]
        ]
        self.assertEqual(len(source_anomaly_types), 1)
        self.assertEqual(source_anomaly_types[0]["model_year"], 1996)
        self.assertEqual(len(source_anomaly_transmissions), 1)
        self.assertEqual(source_anomaly_transmissions[0]["transmission_code"], "G64.42")
        self.assertEqual(source_anomaly_transmissions[0]["transmission_number_prefix"], "G6452")
        self.assertFalse(source_anomaly_transmissions[0]["code_number_prefix_matches"])

    def test_review_queue_covers_every_candidate_and_gap(self) -> None:
        queue = self.roster["review_queue"]
        scope = self.roster["scope"]
        self.assertEqual(
            queue["entry_count"],
            scope["configuration_candidate_count"] + scope["configuration_gap_count"],
        )
        self.assertEqual(self.roster["coverage"]["review_queue_by_priority"]["P0"], 14)
        self.assertTrue(all(item["review_status"] == "not_started" for item in queue["entries"]))
        self.assertTrue(all(item["promoted"] is False for item in queue["entries"]))

    def test_candidates_make_no_engineering_or_vehicle_claim(self) -> None:
        scope = self.roster["scope"]
        self.assertEqual(scope["human_reviewed_configuration_candidates"], 0)
        self.assertEqual(scope["promoted_vehicle_configurations"], 0)
        self.assertEqual(scope["complete_vehicle_boms"], 0)
        for candidate in self.roster["configuration_candidates"]:
            self.assertFalse(candidate["promoted_to_configured_vehicle"])
            self.assertFalse(candidate["complete_vehicle_bom"])
            self.assertIsNone(candidate["geometry_revision"])
            self.assertIsNone(candidate["selected_material_set"])
            self.assertEqual(candidate["reference_solver_results"], 0)
            self.assertEqual(candidate["physicsnemo_results"], 0)

    def test_tracked_contract_validates(self) -> None:
        generator.validate_contract(self.roster)


if __name__ == "__main__":
    unittest.main()
