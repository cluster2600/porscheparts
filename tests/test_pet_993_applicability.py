import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "generate_pet_993_applicability.py"
SPEC = importlib.util.spec_from_file_location("generate_pet_993_applicability", MODULE_PATH)
generator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(generator)


class Pet993ApplicabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(generator.OUTPUT.read_text(encoding="utf-8"))

    def test_source_is_the_classic_kat517_text_and_not_copied(self) -> None:
        source = self.contract["source_boundary"]
        self.assertEqual(source["pet_source_id"], "pet-classic-993")
        self.assertEqual(source["pet_text_expected_path"], "/tmp/kat517-993.txt")
        self.assertRegex(source["pet_text_sha256"], r"^[0-9a-f]{64}$")
        self.assertFalse(source["raw_pet_text_copied"])
        self.assertFalse(source["raw_pet_pdf_copied"])

    def test_direct_model_columns_produce_fail_closed_candidates(self) -> None:
        scope = self.contract["scope"]
        self.assertEqual(scope["source_listed_occurrences"], 6624)
        self.assertEqual(scope["annotated_occurrence_records"], 1002)
        self.assertEqual(scope["machine_bom_candidate_occurrences"], 173)
        self.assertEqual(scope["machine_bom_candidate_vehicle_links"], 178)
        self.assertEqual(scope["candidate_vehicle_counts"]["993-turbo"], 108)
        self.assertEqual(scope["human_reviewed_occurrences"], 0)
        self.assertEqual(scope["complete_variant_boms"], 0)

    def test_turbo_brake_disc_is_a_direct_quantity_one_candidate(self) -> None:
        record = next(
            item
            for item in self.contract["records"]
            if item["oem_reference"] == "993 351 046 10"
            and item["pet_illustration"] == "602-00"
        )
        self.assertTrue(record["machine_bom_candidate"])
        self.assertEqual(record["directly_resolved_vehicle_ids"], ["993-turbo"])
        self.assertEqual(record["candidate_quantity_per_car"], 1)
        self.assertEqual(record["annotations"][0]["token"], "TURBO")
        self.assertTrue(record["annotations"][0]["logical_text_line_numbers"])
        self.assertFalse(record["claims"]["human_reviewed"])

    def test_shared_wiring_harness_keeps_both_direct_annotations(self) -> None:
        record = next(
            item
            for item in self.contract["records"]
            if item["oem_reference"] == "993 612 038 01"
            and item["pet_illustration"] == "902-10"
        )
        self.assertEqual(
            record["directly_resolved_vehicle_ids"],
            ["993-carrera-4", "993-turbo"],
        )
        self.assertEqual(
            {annotation["token"] for annotation in record["annotations"]},
            {"CARRERA 4", "TURBO"},
        )
        self.assertTrue(record["machine_bom_candidate"])

    def test_indirect_codes_are_never_machine_bom_candidates(self) -> None:
        indirect = [
            record
            for record in self.contract["records"]
            if any(annotation["kind"] != "direct_variant" for annotation in record["annotations"])
        ]
        self.assertTrue(indirect)
        self.assertTrue(all(not record["machine_bom_candidate"] for record in indirect))

    def test_z64_is_front_axle_drive_not_gearbox(self) -> None:
        z64 = [
            annotation
            for record in self.contract["records"]
            for annotation in record["annotations"]
            if annotation["token"] == "Z64.20"
        ]
        self.assertEqual(len(z64), 3)
        self.assertEqual({annotation["kind"] for annotation in z64}, {"front_axle_drive_code"})

    def test_tracked_contract_validates(self) -> None:
        generator.validate_contract(self.contract)


if __name__ == "__main__":
    unittest.main()
