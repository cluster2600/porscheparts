import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT
    / "parts"
    / "993-eng-carrier-0001"
    / "source"
    / "build_mass_constrained_surrogate.py"
)
SPEC = importlib.util.spec_from_file_location(
    "build_mass_constrained_surrogate", MODULE_PATH
)
generator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(generator)


class EngineCarrierMassConstrainedSurrogateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.values = generator.derive()
        self.scad = generator.render_scad(self.values)
        self.usd = generator.render_usd(self.values)
        self.report = generator.build_report(self.values, self.scad, self.usd)
        generator.validate(self.values, self.scad, self.usd, self.report)

    def test_declared_envelope_and_mass_close_the_equivalent_section(self) -> None:
        self.assertEqual(
            self.report["input_constraints"]["declared_envelope_mm"],
            [600.0, 50.0, 50.0],
        )
        self.assertEqual(self.report["input_constraints"]["declared_mass_kg"], 1.96)
        section = self.report["derived_section"]
        self.assertAlmostEqual(section["equivalent_wall_mm"], 2.175319724, places=9)
        self.assertAlmostEqual(section["fill_fraction"], 0.166454352, places=9)
        self.assertEqual(section["reconstructed_mass_kg"], 1.96)
        self.assertEqual(section["mass_error_kg"], 0.0)
        self.assertTrue(section["mass_constraint_closed"])

    def test_analytic_bookends_are_reproducible_but_not_component_results(self) -> None:
        bookends = self.report["analytic_bookends"]
        self.assertEqual(bookends["documentary_force_upper_N"], 1912.29675)
        self.assertAlmostEqual(
            bookends["simply_supported_central_point_load"][
                "max_bending_stress_MPa"
            ],
            45.112916149,
            places=9,
        )
        self.assertAlmostEqual(
            bookends["cantilever_tip_load"]["max_deflection_mm"],
            4.124609476,
            places=9,
        )
        self.assertIsNone(bookends["strength_or_life_conclusion"])
        self.assertFalse(bookends["acceptance_criteria_present"])

    def test_interface_domains_are_bounded_without_selecting_coordinates(self) -> None:
        domains = self.report["interface_search_domains"]
        self.assertEqual(len(domains), 2)
        for domain in domains:
            self.assertEqual(domain["x_mm"], [-300.0, 300.0])
            self.assertEqual(domain["y_mm"], [-25.0, 25.0])
            self.assertEqual(domain["z_mm"], [0.0, 50.0])
            self.assertEqual(domain["selected_point_count"], 0)

    def test_openusd_is_a_four_wall_guide_without_physics_or_material(self) -> None:
        self.assertEqual(self.usd.count('def Cube "Guide"'), 4)
        self.assertIn("metersPerUnit = 0.001", self.usd)
        self.assertIn("bool componentCredit = false", self.usd)
        for prohibited in (
            "UsdPhysics",
            "RigidBodyAPI",
            "CollisionAPI",
            "MassAPI",
            "MaterialBindingAPI",
        ):
            self.assertNotIn(prohibited, self.usd)

    def test_all_engineering_and_release_claims_fail_closed(self) -> None:
        self.assertFalse(
            self.report["input_constraints"]["material_properties_qualified"]
        )
        self.assertEqual(
            self.report["model_roles"]["physicsnemo"],
            "ineligible_no_reference_CAE_dataset",
        )
        self.assertTrue(
            all(value is False for value in self.report["claim_boundary"].values())
        )

    def test_checked_in_outputs_are_current(self) -> None:
        self.assertEqual(generator.main(["--check-index"]), 0)
        self.assertEqual(generator.main(["--check"]), 0)
        self.assertEqual(
            json.loads(generator.REPORT.read_text(encoding="utf-8")), self.report
        )


if __name__ == "__main__":
    unittest.main()
