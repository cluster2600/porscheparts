import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "generate_993_configuration_axes.py"
SPEC = importlib.util.spec_from_file_location("generate_993_configuration_axes", MODULE_PATH)
generator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(generator)


class ConfigurationAxisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(generator.OUTPUT.read_text(encoding="utf-8"))
        cls.by_value = {item["value"]: item for item in cls.contract["axis_contracts"]}

    def test_four_axes_exist_without_complete_vehicle_claim(self) -> None:
        scope = self.contract["scope"]
        self.assertEqual(scope["axis_contract_count"], 4)
        self.assertEqual(scope["complete_vehicle_configuration_count"], 0)
        self.assertEqual(scope["promoted_vehicle_bom_candidate_count"], 0)
        self.assertFalse(self.contract["combination_policy"]["cartesian_product_allowed"])

    def test_body_axes_are_separate_candidates(self) -> None:
        self.assertEqual(self.by_value["Cabriolet"]["candidate_occurrence_count"], 73)
        self.assertEqual(self.by_value["Targa"]["candidate_occurrence_count"], 50)
        for value in ("Cabriolet", "Targa"):
            contract = self.by_value[value]
            self.assertFalse(contract["complete_vehicle_bom"])
            self.assertFalse(contract["combined_with_model_variant"])
            self.assertEqual(
                contract["candidate_occurrences_with_single_quantity"],
                contract["candidate_occurrence_count"],
            )

    def test_transmission_summary_proves_only_code_family_interpretation(self) -> None:
        evidence = self.contract["transmission_summary_evidence"]
        self.assertIn("A50.04", evidence["tiptronic_4_speed_code_examples"])
        self.assertIn("A50.05", evidence["tiptronic_4_speed_code_examples"])
        self.assertIn("G50.20", evidence["manual_6_speed_code_examples"])
        self.assertIn("G64.51", evidence["manual_6_speed_code_examples"])
        self.assertEqual(set(evidence["claims"].values()), {False})

    def test_transmission_axis_candidates_remain_unpromoted(self) -> None:
        manual = self.by_value["manual_6_speed_candidate"]
        tiptronic = self.by_value["tiptronic_4_speed_candidate"]
        self.assertEqual(manual["candidate_occurrence_count"], 89)
        self.assertEqual(tiptronic["candidate_occurrence_count"], 2)
        for contract in (manual, tiptronic):
            self.assertTrue(contract["candidate_occurrences"])
            self.assertTrue(
                all(
                    candidate["promoted_to_vehicle_bom"] is False
                    for candidate in contract["candidate_occurrences"]
                )
            )

    def test_tracked_contract_validates(self) -> None:
        generator.validate_contract(self.contract)


if __name__ == "__main__":
    unittest.main()
