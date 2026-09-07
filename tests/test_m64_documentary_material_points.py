import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "twins/m64-cylinder-head/documentary-material-points-20260907.json").read_text())


class DocumentaryMaterialTests(unittest.TestCase):
    def test_sources_have_binary_identity_and_visual_pages(self):
        for source in DATA["sources"].values():
            self.assertEqual(len(source["pdf_sha256"]), 64)
            self.assertTrue(source["visually_reviewed_pdf_pages_1_based"])
            self.assertGreater(source["bytes"], 0)

    def test_cp1_treatment_not_hot_tensile_test(self):
        cp1 = DATA["materials"]["Aheadd_CP1"]
        table = cp1["heat_treatment_comparison"]
        self.assertEqual(table["heat_treatment_temperature_c"], 400)
        self.assertEqual(table["tensile_test_temperature_c"], 25)
        self.assertEqual(cp1["published_hot_tensile_rows"], [])
        self.assertIsNone(table["conductivity_measurement_temperature_c"])

    def test_a20x_only_published_temperature_rows(self):
        table = DATA["materials"]["A20X"]["temperature_dependent_tensile_table"]
        self.assertEqual([row["test_temperature_c"] for row in table["rows"]], [20, 100, 150, 200, 250])
        self.assertFalse(table["automatic_T7_assignment_allowed"])
        self.assertIsNone(table["yield_offset_percent"])
        self.assertIsNone(table["sample_count"])
        self.assertEqual(table["rows"][0]["yield_strength_mpa"], 445)
        self.assertTrue(table["source_discrepancy"])

    def test_documentary_facts_not_solver_card(self):
        boundaries = DATA["use_boundaries"]
        self.assertIsNone(boundaries["selected_material"])
        for key, value in boundaries.items():
            if key != "selected_material":
                self.assertIs(value, False)

    def test_missing_thermal_laws_not_filled_by_another_alloy(self):
        for material in DATA["materials"].values():
            missing = material["not_published_in_reviewed_pages"]
            self.assertIn("specific_heat_vs_temperature", missing)
            self.assertIn("thermal_expansion_vs_temperature", missing)
            self.assertIn("thermal_conductivity_vs_temperature", missing)


if __name__ == "__main__":
    unittest.main()
