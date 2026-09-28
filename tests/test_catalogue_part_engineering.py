import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "generate_catalogue_part_engineering.py"
SPEC = importlib.util.spec_from_file_location("generate_catalogue_part_engineering", MODULE_PATH)
generator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(generator)


class CataloguePartEngineeringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = generator.build_contract()

    def test_all_eighteen_parts_have_fail_closed_engineering_contracts(self) -> None:
        self.assertEqual(len(self.contract["parts"]), 18)
        self.assertEqual(self.contract["summary"]["ready_for_reference_cae"], 0)
        self.assertEqual(self.contract["summary"]["released_for_functional_manufacture"], 0)
        for part in self.contract["parts"]:
            self.assertTrue(part["engineering_status"].startswith("blocked_"))
            self.assertEqual(part["digital_twin_tests"]["reference_cae"]["claim"], "no_FEA_result")
            self.assertEqual(part["digital_twin_tests"]["manufacturing_release"]["claim"], "not_released")

    def test_wheel_screening_uses_offset_without_claiming_body_clearance(self) -> None:
        wheel = next(part for part in self.contract["parts"] if part["twin_id"] == "TWIN-FUCHS-37024.013")
        self.assertAlmostEqual(wheel["screening_metrics"]["nominal_bead_seat_width_mm"], 177.8)
        self.assertAlmostEqual(wheel["screening_metrics"]["mounting_plane_to_inboard_bead_seat_mm"], 143.9)
        self.assertAlmostEqual(wheel["screening_metrics"]["mounting_plane_to_outboard_bead_seat_mm"], 33.9)
        self.assertIn("clearance are excluded", wheel["screening_metrics"]["interpretation"])

    def test_carrier_screening_is_not_analysis_geometry(self) -> None:
        carrier = next(
            part for part in self.contract["parts"] if part["twin_id"] == "TWIN-993-ENGINE-CARRIER-TURBO"
        )
        self.assertAlmostEqual(carrier["screening_metrics"]["declared_envelope_volume_m3"], 0.0015)
        self.assertAlmostEqual(carrier["screening_metrics"]["apparent_solid_fraction_if_steel"], 0.166454)
        self.assertEqual(carrier["simulation"]["analysis_geometry"], "unavailable")
        self.assertIsNone(carrier["manufacturing"]["selected_functional_route"])
        screening = carrier["virtual_material_screening"]
        self.assertEqual(
            screening["status"],
            "F1_generic_analytic_screening_complete_no_component_credit",
        )
        self.assertAlmostEqual(
            screening["analytic_results"]["same_geometry"]["ti64_deflection_ratio"],
            1.842105263,
        )
        self.assertFalse(screening["component_credit"])
        self.assertIsNone(screening["screening_decision"]["selected_material"])
        self.assertIsNone(
            screening["screening_decision"]["selected_functional_process"]
        )

    def test_physicsnemo_is_a_disabled_surrogate_not_the_reference_solver(self) -> None:
        policy = self.contract["physicsnemo_policy"]
        self.assertFalse(policy["execution_enabled"])
        self.assertIn("surrogate_only_after", policy["role"])
        self.assertIn("GeoTransolver", policy["candidate_architecture"])
        self.assertIn("MeshGraphNet", policy["candidate_architectures"])
        self.assertEqual(self.contract["solver_policy"]["reference_structural_solver"], "CalculiX")
        self.assertIn("PhysicsNeMo_prediction_as_reference_solution", policy["prohibited_claims"])

    def test_dimension_only_parts_keep_material_and_process_unselected(self) -> None:
        turbo = next(
            part
            for part in self.contract["parts"]
            if part["twin_id"] == "TWIN-993-TURBOCHARGER-K16-LEFT"
        )
        self.assertIsNone(turbo["materials"]["selected_material_system"])
        self.assertEqual(
            turbo["materials"]["screening_hypothesis"],
            "multimaterial_high_temperature_turbomachinery_assembly",
        )
        self.assertFalse(turbo["materials"]["single_material_assumption_allowed"])
        self.assertIsNone(turbo["manufacturing"]["selected_functional_route"])
        self.assertEqual(turbo["simulation"]["analysis_geometry"], "unavailable")
        self.assertEqual(
            turbo["simulation"]["domain_ids"],
            ["rotordynamics", "structural", "thermal_fluid"],
        )

    def test_checked_in_output_is_current(self) -> None:
        self.assertEqual(generator.run(write=False), 0)
        payload = json.loads(generator.OUTPUT.read_text(encoding="utf-8"))
        self.assertEqual(payload, self.contract)


if __name__ == "__main__":
    unittest.main()
