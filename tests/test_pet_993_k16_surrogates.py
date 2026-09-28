import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "generate_pet_993_k16_surrogates.py"
SPEC = importlib.util.spec_from_file_location("generate_pet_993_k16_surrogates", MODULE_PATH)
generator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(generator)


class Pet993K16SurrogateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = generator.derive()
        self.scad = generator.render_scad(self.data)
        self.usd = generator.render_usd(self.data)
        self.report = generator.build_report(self.data, self.scad, self.usd)
        generator.validate(self.data, self.scad, self.usd, self.report)

    def test_two_sides_link_all_four_pet_masters_without_mirroring_dimensions(self) -> None:
        by_side = {item["side"]: item for item in self.report["variants"]}
        self.assertEqual(set(by_side), {"left", "right"})
        self.assertEqual(
            by_side["left"]["oem_references"],
            ["99312301351", "99312301352"],
        )
        self.assertEqual(
            by_side["right"]["oem_references"],
            ["99312301451", "99312301452"],
        )
        self.assertEqual(
            len(
                {
                    master
                    for item in by_side.values()
                    for master in item["pet_part_master_twin_ids"]
                }
            ),
            4,
        )
        self.assertIsNone(by_side["left"]["wheel_diameter_guides_mm"])
        self.assertEqual(
            by_side["left"]["wheel_diameter_evidence"],
            "not_available_and_not_mirrored_from_right",
        )
        self.assertEqual(len(by_side["right"]["wheel_diameter_guides_mm"]), 4)

    def test_mass_and_dimension_checks_are_arithmetic_only(self) -> None:
        checks = self.report["mass_and_dimension_consistency"]
        self.assertEqual(
            checks["status"],
            "passed_arithmetic_only_not_geometry_or_material_validation",
        )
        self.assertAlmostEqual(checks["complete_unit_envelope_volume_m3"], 0.011172)
        self.assertAlmostEqual(
            checks["combined_mass_per_combined_envelope_volume_kg_m3"],
            508.413891873,
            places=9,
        )
        self.assertIn("prevents_density_inference", checks["interpretation"])

    def test_zero_d_equations_exist_but_no_operating_point_is_evaluated(self) -> None:
        model = self.report["zeroD_model"]
        self.assertEqual(len(model["equations"]), 6)
        self.assertFalse(model["map_available"])
        self.assertFalse(model["operating_point_available"])
        self.assertFalse(model["shaft_balance_evaluated"])
        self.assertFalse(model["reference_solver_credit"])
        self.assertEqual(self.report["summary"]["evaluated_zeroD_operating_points"], 0)
        self.assertEqual(
            self.report["cold_side_solver_harness"]["status"],
            "toolchain_smoke_not_K16_reference_CFD",
        )

    def test_physicsnemo_menu_is_live_discovered_but_disabled(self) -> None:
        discovery = self.report["physicsnemo_discovery"]
        self.assertEqual(
            discovery["commit"],
            "4fbfcfd62bf050b48ceec6b438da409b9f4644b3",
        )
        self.assertEqual(
            {item["model"] for item in discovery["model_menu"]},
            {"DoMINO", "GeoTransolver", "Transolver", "MeshGraphNet"},
        )
        self.assertFalse(discovery["execution_enabled"])
        self.assertTrue(all(item["selected"] is False for item in discovery["model_menu"]))

    def test_openusd_and_material_routes_remain_guides_only(self) -> None:
        self.assertEqual(self.usd.count('kind = "component"'), 2)
        self.assertEqual(self.usd.count('purpose = "guide"'), 6)
        for prohibited in (
            "UsdPhysics",
            "RigidBodyAPI",
            "CollisionAPI",
            "MassAPI",
            "MaterialBindingAPI",
        ):
            self.assertNotIn(prohibited, self.usd)
        route = self.report["material_and_manufacturing_route"]
        self.assertEqual(route["selected_material_count"], 0)
        self.assertEqual(route["selected_functional_manufacturing_route_count"], 0)
        self.assertFalse(any(self.report["claim_boundary"].values()))

    def test_checked_in_outputs_are_current(self) -> None:
        self.assertEqual(generator.main(["--check"]), 0)


if __name__ == "__main__":
    unittest.main()
