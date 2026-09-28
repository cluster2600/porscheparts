import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "generate_pet_993_heat_shield_surrogate.py"
SPEC = importlib.util.spec_from_file_location(
    "generate_pet_993_heat_shield_surrogate", MODULE_PATH
)
generator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(generator)


class Pet993HeatShieldSurrogateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = generator.derive()
        self.scad = generator.render_scad()
        self.usd = generator.render_usd()
        self.report = generator.build_report(self.data, self.scad, self.usd)
        generator.validate(self.data, self.scad, self.usd, self.report)

    def test_exact_oem_reference_links_one_pet_master(self) -> None:
        subject = self.report["subject"]
        self.assertEqual(subject["oem_reference"], "99312311351")
        self.assertEqual(
            subject["pet_part_master_twin_id"],
            "TWIN-PET-993-PART-B6629ABCA63D241CEDCC",
        )
        self.assertEqual(subject["pet_illustration"], "202-16")
        self.assertEqual(subject["pet_position"], 7)

    def test_envelope_mass_arithmetic_is_not_material_density(self) -> None:
        inputs = self.report["documentary_inputs"]
        self.assertEqual(inputs["supplier_declared_bounding_box_mm"], [160.0, 110.0, 105.0])
        self.assertEqual(inputs["supplier_declared_mass_kg"], 0.23)
        self.assertAlmostEqual(inputs["bounding_box_volume_m3"], 0.001848)
        self.assertIn("not_material_density", inputs["quotient_semantics"])
        self.assertIsNone(inputs["material_label"])

    def test_thermal_contract_has_no_evaluated_point_or_material_selection(self) -> None:
        self.assertEqual(len(self.report["thermal_model"]["equations"]), 7)
        self.assertFalse(self.report["thermal_model"]["operating_point_available"])
        self.assertFalse(self.report["thermal_model"]["reference_solver_credit"])
        self.assertEqual(len(self.report["load_cases"]), 4)
        self.assertTrue(all(case["status"] == "blocked" for case in self.report["load_cases"]))
        self.assertEqual(
            self.report["material_and_manufacturing_route"]["selected_material_count"],
            0,
        )
        self.assertTrue(
            all(item["status"] == "unsourced_unselected" for item in self.report["material_and_manufacturing_route"]["candidate_matrix"])
        )

    def test_physicsnemo_and_omniverse_remain_fail_closed(self) -> None:
        discovery = self.report["physicsnemo_discovery"]
        self.assertEqual(
            discovery["commit"],
            "4fbfcfd62bf050b48ceec6b438da409b9f4644b3",
        )
        self.assertEqual(
            {item["model"] for item in discovery["model_menu"]},
            {"DoMINO", "GeoTransolver", "Transolver", "MeshGraphNet"},
        )
        self.assertEqual(
            {item["datapipe"] for item in discovery["datapipe_menu"]},
            {"DoMINODataPipe", "TransolverDataPipe"},
        )
        self.assertFalse(discovery["execution_enabled"])
        handoff = self.report["omniverse_handoff"]
        self.assertEqual(handoff["preflight_status"], "blocked")
        self.assertFalse(handoff["guide_composed_into_vehicle"])
        self.assertFalse(handoff["simready_validated"])

    def test_openusd_is_one_guide_and_checked_in_outputs_are_current(self) -> None:
        self.assertEqual(self.usd.count('kind = "component"'), 1)
        self.assertEqual(self.usd.count('purpose = "guide"'), 1)
        self.assertFalse(any(self.report["claim_boundary"].values()))
        self.assertEqual(generator.main(["--check"]), 0)


if __name__ == "__main__":
    unittest.main()
