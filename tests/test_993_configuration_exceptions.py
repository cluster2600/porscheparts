import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "generate_993_configuration_exceptions.py"
SPEC = importlib.util.spec_from_file_location("generate_993_configuration_exceptions", MODULE_PATH)
generator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(generator)


class ConfigurationExceptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(generator.OUTPUT.read_text(encoding="utf-8"))
        cls.by_id = {
            item["contract_id"]: item for item in cls.contract["exception_contracts"]
        }

    def test_all_twelve_unresolved_constraints_are_tracked(self) -> None:
        scope = self.contract["scope"]
        self.assertEqual(scope["exception_contract_count"], 4)
        self.assertEqual(scope["input_unresolved_constraint_occurrences"], 12)
        self.assertEqual(scope["mapped_exception_occurrences"], 12)
        self.assertEqual(scope["unmapped_exception_occurrences"], 0)

    def test_variant_exception_counts_close(self) -> None:
        coverage = self.contract["coverage"]["mapped_occurrences_by_contract"]
        self.assertEqual(coverage["CONFIG-EXCEPTION-993-CARRERA-S"], 8)
        self.assertEqual(coverage["CONFIG-EXCEPTION-993-CARRERA-4S"], 2)
        self.assertEqual(coverage["CONFIG-EXCEPTION-993-TURBO-S"], 1)
        self.assertEqual(coverage["CONFIG-EXCEPTION-993-A50-07"], 1)

    def test_carrera_s_and_4s_keep_order_information_evidence(self) -> None:
        carrera_s = self.by_id["CONFIG-EXCEPTION-993-CARRERA-S"]
        carrera_4s = self.by_id["CONFIG-EXCEPTION-993-CARRERA-4S"]
        self.assertEqual(carrera_s["catalogue_vehicle_metadata"]["yearStart"], 1997)
        self.assertEqual(carrera_4s["catalogue_vehicle_metadata"]["yearStart"], 1996)
        self.assertEqual(carrera_s["pet_presence_evidence"]["kind"], "pet_order_information")
        self.assertEqual(carrera_4s["pet_presence_evidence"]["kind"], "pet_order_information")

    def test_turbo_s_engine_code_remains_explicitly_unverified(self) -> None:
        turbo_s = self.by_id["CONFIG-EXCEPTION-993-TURBO-S"]
        self.assertEqual(turbo_s["pet_presence_evidence"]["kind"], "pet_option_legend")
        self.assertEqual(
            turbo_s["engine_code_status"], "explicitly_unverified_in_source_vehicle_note"
        )
        self.assertIn("unverified", turbo_s["catalogue_vehicle_metadata"]["notes"])

    def test_a50_07_is_not_equated_with_a50_05_or_a5007(self) -> None:
        a50 = self.by_id["CONFIG-EXCEPTION-993-A50-07"]
        relation = a50["pet_summary_relation_hypothesis"]
        self.assertEqual(relation["summary_transmission_type_code"], "A50.05")
        self.assertEqual(relation["summary_transmission_number_prefix"], "A5007")
        self.assertEqual(relation["summary_model_years"], [1997, 1998])
        self.assertFalse(relation["equivalence_claim"])
        self.assertIn("unresolved_do_not_equate", relation["relation_status"])

    def test_no_exception_is_promoted_or_complete(self) -> None:
        scope = self.contract["scope"]
        self.assertEqual(scope["fully_resolved_configuration_exceptions"], 0)
        self.assertEqual(scope["promoted_vehicle_configurations"], 0)
        self.assertEqual(scope["promoted_vehicle_bom_entries"], 0)
        self.assertEqual(scope["complete_vehicle_boms"], 0)
        for item in self.contract["exception_contracts"]:
            self.assertFalse(item["human_reviewed"])
            self.assertFalse(item["promoted_to_vehicle_configuration"])
            self.assertFalse(item["complete_vehicle_bom"])

    def test_tracked_contract_validates(self) -> None:
        generator.validate_contract(self.contract)


if __name__ == "__main__":
    unittest.main()
