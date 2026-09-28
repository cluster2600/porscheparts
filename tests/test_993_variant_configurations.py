import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "generate_993_variant_configurations.py"
SPEC = importlib.util.spec_from_file_location("generate_993_variant_configurations", MODULE_PATH)
generator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(generator)


class VariantConfigurationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(generator.OUTPUT.read_text(encoding="utf-8"))

    def test_all_documented_variants_have_separate_contracts(self) -> None:
        self.assertEqual(self.contract["scope"]["variant_configuration_count"], 8)
        self.assertEqual(
            {item["vehicle_id"] for item in self.contract["configurations"]},
            {
                "993-carrera",
                "993-carrera-4",
                "993-carrera-4s",
                "993-carrera-s",
                "993-gt2",
                "993-rs",
                "993-turbo",
                "993-turbo-s",
            },
        )
        self.assertFalse(self.contract["strategy"]["universal_993_bom_allowed"])
        self.assertEqual(self.contract["strategy"]["first_integration_target"], "993-turbo")
        self.assertFalse(self.contract["scope"]["complete_configuration_universe"])
        self.assertEqual(self.contract["scope"]["provisional_configuration_axis_contracts"], 4)
        self.assertEqual(self.contract["scope"]["pet_summary_type_records"], 69)
        self.assertEqual(self.contract["scope"]["pet_summary_configuration_candidates"], 149)
        self.assertEqual(self.contract["scope"]["pet_summary_configuration_gaps"], 2)
        self.assertEqual(self.contract["scope"]["single_dimension_part_constraint_occurrences"], 694)
        self.assertEqual(
            self.contract["scope"]["resolved_configuration_part_constraint_occurrences"], 682
        )
        self.assertEqual(self.contract["scope"]["configuration_part_candidate_links"], 24063)
        self.assertEqual(self.contract["scope"]["configuration_exception_contracts"], 4)
        self.assertEqual(
            self.contract["scope"]["mapped_configuration_exception_occurrences"], 12
        )
        self.assertEqual(self.contract["scope"]["fully_resolved_configuration_exceptions"], 0)

    def test_pet_exposes_unmodeled_cabriolet_targa_and_powertrain_dimensions(self) -> None:
        universe = self.contract["catalogue_configuration_universe"]
        self.assertEqual(universe["source_vehicle_body_styles"], ["Coupé"])
        self.assertEqual(set(universe["missing_body_style_contracts"]), {"CABRIO", "TARGA"})
        self.assertEqual(universe["observed_body_style_tokens"]["CABRIO"], 62)
        self.assertEqual(universe["observed_body_style_tokens"]["TARGA"], 33)
        self.assertIn("M64.60", universe["observed_engine_code_tokens"])
        self.assertIn("G64.51", universe["observed_transmission_code_tokens"])
        self.assertIn("M491", universe["observed_option_code_tokens"])
        axes = {item["value"]: item for item in universe["provisional_axis_contracts"]}
        self.assertEqual(axes["Cabriolet"]["candidate_occurrence_count"], 73)
        self.assertEqual(axes["Targa"]["candidate_occurrence_count"], 50)
        self.assertEqual(axes["manual_6_speed_candidate"]["candidate_occurrence_count"], 89)
        self.assertEqual(axes["tiptronic_4_speed_candidate"]["candidate_occurrence_count"], 2)
        self.assertTrue(all(item["complete_vehicle_bom"] is False for item in axes.values()))
        roster = universe["pet_summary_roster"]
        self.assertEqual(roster["review_queue_entry_count"], 151)
        self.assertEqual(roster["promoted_vehicle_configurations"], 0)
        linkage = universe["configuration_part_linkage"]
        self.assertEqual(linkage["unresolved_constraint_occurrences"], 12)
        self.assertEqual(linkage["promoted_vehicle_bom_entries"], 0)
        exceptions = universe["configuration_exceptions"]
        self.assertEqual(exceptions["unmapped_exception_occurrences"], 0)
        self.assertEqual(exceptions["fully_resolved_configuration_exceptions"], 0)
        self.assertEqual(len(exceptions["contract_ids"]), 4)

    def test_only_context_read_fitments_enter_variant_boms(self) -> None:
        scope = self.contract["scope"]
        self.assertEqual(scope["human_read_pet_part_count"], 15)
        self.assertEqual(scope["human_read_parts_with_variant_proof"], 13)
        self.assertEqual(scope["human_read_parts_without_variant_proof"], 2)
        self.assertEqual(scope["variant_assignment_links"], 28)
        self.assertEqual(scope["machine_resolved_bom_candidate_occurrences"], 173)
        self.assertEqual(scope["machine_resolved_bom_candidate_links"], 178)
        self.assertEqual(scope["unresolved_listed_pet_occurrences"], 12864)
        self.assertEqual(scope["listed_occurrences_without_direct_model_candidate"], 12691)

    def test_turbo_is_first_target_but_not_a_complete_bom(self) -> None:
        turbo = next(item for item in self.contract["configurations"] if item["vehicle_id"] == "993-turbo")
        self.assertEqual(turbo["readiness"]["verified_bom_entry_count"], 10)
        self.assertEqual(turbo["readiness"]["configured_pet_occurrence_count"], 10)
        self.assertEqual(turbo["readiness"]["machine_resolved_bom_candidate_count"], 108)
        self.assertEqual(turbo["readiness"]["machine_candidate_instance_quantity"], 143)
        self.assertFalse(turbo["readiness"]["complete_variant_bom"])
        self.assertEqual(turbo["readiness"]["editable_geometry_entries"], 0)
        self.assertEqual(turbo["readiness"]["physicsnemo_results"], 0)
        self.assertFalse(turbo["readiness"]["functional_vehicle_claim"])

    def test_gt2_remains_empty_and_turbo_s_has_one_unpromoted_candidate(self) -> None:
        empty_ids = {
            item["vehicle_id"]
            for item in self.contract["configurations"]
            if not item["verified_bom_entries"] and not item["machine_resolved_bom_candidates"]
        }
        self.assertEqual(empty_ids, {"993-gt2"})
        turbo_s = next(
            item for item in self.contract["configurations"] if item["vehicle_id"] == "993-turbo-s"
        )
        self.assertEqual(len(turbo_s["machine_resolved_bom_candidates"]), 1)
        candidate = turbo_s["machine_resolved_bom_candidates"][0]
        self.assertEqual(candidate["oem_reference"], "993 361 980 00")
        self.assertFalse(candidate["promoted_to_verified_bom"])

    def test_all_entries_keep_engineering_fields_empty(self) -> None:
        for configuration in self.contract["configurations"]:
            for entry in configuration["verified_bom_entries"]:
                self.assertIsNone(entry["mounted_transform"])
                self.assertIsNone(entry["geometry_revision"])
                self.assertIsNone(entry["selected_material"])
                self.assertIsNone(entry["manufacturing_route"])
                self.assertEqual(
                    entry["part_master_twin_id"],
                    generator.part_master_twin_id(entry["oem_reference"]),
                )
            for candidate in configuration["machine_resolved_bom_candidates"]:
                self.assertIsNone(candidate["mounted_transform"])
                self.assertIsNone(candidate["geometry_revision"])
                self.assertIsNone(candidate["selected_material"])
                self.assertIsNone(candidate["manufacturing_route"])
                self.assertFalse(candidate["promoted_to_verified_bom"])

    def test_tracked_contract_validates(self) -> None:
        generator.validate_contract(self.contract)


if __name__ == "__main__":
    unittest.main()
