import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "generate_pet_993_charge_air_surrogates.py"
SPEC = importlib.util.spec_from_file_location(
    "generate_pet_993_charge_air_surrogates", MODULE_PATH
)
generator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(generator)


class Pet993ChargeAirSurrogateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = generator.derive()
        self.scad = generator.render_scad(self.data)
        self.usd = generator.render_usd(self.data)
        self.report = generator.build_report(self.data, self.scad, self.usd)
        generator.validate(self.data, self.scad, self.usd, self.report)

    def test_five_exact_oem_references_link_to_five_pet_masters(self) -> None:
        self.assertEqual(
            {item["oem_reference"] for item in self.report["components"]},
            {
                "99311033053",
                "99311034054",
                "99311063256",
                "99311063356",
                "99360611400",
            },
        )
        self.assertEqual(
            len(
                {
                    item["pet_part_master_twin_id"]
                    for item in self.report["components"]
                }
            ),
            5,
        )
        self.assertTrue(
            all(item["interface_coordinate_count"] == 0 for item in self.report["components"])
        )

    def test_aftermarket_diameters_stay_unpositioned_and_ta_data_is_quarantined(self) -> None:
        guide = self.report["aftermarket_dimensional_guides"]
        self.assertEqual(guide["diameter_pair_mm"], [43.0, 57.0])
        self.assertEqual(guide["assigned_side_count"], 0)
        self.assertEqual(guide["assigned_endpoint_count"], 0)
        self.assertEqual(guide["promoted_OEM_interface_dimension_count"], 0)
        quarantined = self.report["quarantined_evidence"]
        self.assertEqual(len(quarantined), 1)
        self.assertGreater(
            quarantined[0]["inner_diameter_mm"],
            quarantined[0]["outer_diameter_mm"],
        )
        self.assertFalse(quarantined[0]["promoted_to_geometry_or_flow_area"])

    def test_eight_zero_d_equations_exist_without_an_evaluated_point(self) -> None:
        model = self.report["zeroD_model"]
        self.assertEqual(len(model["equations"]), 8)
        self.assertFalse(model["operating_point_available"])
        self.assertFalse(model["reference_solver_credit"])
        self.assertFalse(model["network_solution_credit"])
        self.assertEqual(self.report["summary"]["evaluated_zeroD_operating_points"], 0)

    def test_physicsnemo_and_omniverse_are_discovered_but_not_executed(self) -> None:
        discovery = self.report["physicsnemo_discovery"]
        self.assertEqual(
            discovery["commit"],
            "4fbfcfd62bf050b48ceec6b438da409b9f4644b3",
        )
        self.assertEqual(
            {item["model"] for item in discovery["model_menu"]},
            {"GeoTransolver", "Transolver", "MeshGraphNet", "DoMINO"},
        )
        self.assertFalse(discovery["execution_enabled"])
        self.assertTrue(all(item["selected"] is False for item in discovery["model_menu"]))
        handoff = self.report["omniverse_handoff"]
        self.assertEqual(handoff["preflight_status"], "blocked")
        self.assertFalse(handoff["guide_composed_into_vehicle"])
        self.assertFalse(handoff["vehicle_transform_known"])
        self.assertFalse(handoff["simready_validated"])

    def test_openusd_stage_is_guides_only_and_report_is_current(self) -> None:
        self.assertEqual(self.usd.count('kind = "component"'), 5)
        self.assertEqual(self.usd.count('purpose = "guide"'), 7)
        self.assertFalse(any(self.report["claim_boundary"].values()))
        self.assertEqual(generator.main(["--check"]), 0)


if __name__ == "__main__":
    unittest.main()
