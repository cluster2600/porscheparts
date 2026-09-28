import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TWIN = ROOT / "twins" / "vehicle-911-917"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class Vehicle911917930TailF3Tests(unittest.TestCase):
    def test_tail_and_extension_remain_fail_closed_visual_requirements(self) -> None:
        f2 = load_json(TWIN / "designer-render-930-tail-f2.json")
        f3 = load_json(TWIN / "designer-render-930-tail-stretched-f3.json")

        self.assertEqual(f2["design_requirement"]["spoiler_type"], "fixed_930_turbo_inspired_whale_tail")
        self.assertEqual(f2["design_requirement"]["heat_exchanger_type"], "horizontal_twin_turbo_charge_air_heat_exchanger")
        self.assertEqual(f3["design_requirement"]["wheelbase_extension_mm"], 450.0)
        self.assertEqual(f3["design_requirement"]["rear_overhang_extension_mm"], 0.0)
        self.assertFalse(any(f2["release_gates"].values()))
        self.assertFalse(any(f3["release_gates"].values()))

    def test_wide_f4_keeps_aero_and_traction_claims_closed(self) -> None:
        f4 = load_json(TWIN / "designer-render-930-tail-wide-f4.json")

        self.assertEqual(f4["design_requirement"]["span_intent"], "full_rear_fender_width_with_small_outer_projection")
        self.assertIsNone(f4["design_requirement"]["span_mm"])
        self.assertIsNone(f4["design_requirement"]["incidence_deg"])
        self.assertIsNone(f4["design_requirement"]["downforce_n"])
        self.assertEqual(f4["user_reference"]["rights_status"], "unknown_do_not_publish_or_redistribute")
        self.assertFalse(any(f4["release_gates"].values()))

    def test_f5_intakes_and_firewall_are_not_claimed_as_engineered(self) -> None:
        f5 = load_json(TWIN / "designer-render-intakes-firewall-f5.json")

        self.assertEqual(f5["design_requirement"]["rear_quarter_glass"], "deleted_both_sides")
        self.assertIn("full_height", f5["design_requirement"]["firewall_intent"])
        self.assertIsNone(f5["design_requirement"]["intake_area_mm2_each"])
        self.assertIsNone(f5["design_requirement"]["fire_resistance_rating"])
        self.assertFalse(any(f5["release_gates"].values()))

    def test_f6_closes_rear_cabin_without_opening_firewall_gates(self) -> None:
        f6 = load_json(TWIN / "designer-render-cabin-closed-f6.json")

        self.assertEqual(f6["design_requirement"]["seat_count"], 2)
        self.assertEqual(f6["design_requirement"]["seat_location"], "ahead_of_full_height_firewall")
        self.assertEqual(
            f6["design_requirement"]["rear_compartment_visibility_in_three_quarter_view"],
            "fully_blocked_by_opaque_firewall",
        )
        self.assertFalse(f6["intermediate_asset"]["retained_in_workspace"])
        self.assertFalse(any(f6["release_gates"].values()))

    def test_f7_straightens_firewall_without_claiming_engineering_validation(self) -> None:
        f7 = load_json(TWIN / "designer-render-straight-firewall-f7.json")

        self.assertEqual(f7["design_requirement"]["seat_count"], 2)
        self.assertEqual(
            f7["design_requirement"]["firewall_visual_plane"],
            "single_straight_vertical_plane_perpendicular_to_floor",
        )
        self.assertEqual(f7["design_requirement"]["firewall_visual_thickness"], "uniform_double_skin")
        self.assertIsNone(f7["design_requirement"]["firewall_longitudinal_position_mm"])
        self.assertIsNone(f7["design_requirement"]["firewall_thickness_mm"])
        self.assertFalse(any(f7["release_gates"].values()))

    def test_f8_freezes_artistic_roof_without_dimension_claims(self) -> None:
        f8 = load_json(TWIN / "designer-render-roof-profile-f8.json")

        self.assertEqual(f8["design_requirement"]["view"], "lower_true_side_cutaway")
        self.assertEqual(
            f8["design_requirement"]["firewall_visual_plane"],
            "preserved_straight_vertical_plane",
        )
        self.assertIsNone(f8["design_requirement"]["roof_profile_dimensions"])
        self.assertIsNone(f8["design_requirement"]["windshield_angle_deg"])
        self.assertFalse(any(f8["release_gates"].values()))

    def test_local_images_match_recorded_hashes_when_available(self) -> None:
        for contract_name in (
            "designer-render-930-tail-f2.json",
            "designer-render-930-tail-stretched-f3.json",
            "designer-render-930-tail-wide-f4.json",
            "designer-render-intakes-firewall-f5.json",
            "designer-render-cabin-closed-f6.json",
            "designer-render-straight-firewall-f7.json",
            "designer-render-roof-profile-f8.json",
        ):
            contract = load_json(TWIN / contract_name)
            for field in ("edit_target", "output_asset"):
                asset = contract[field]
                path = ROOT / asset["path"]
                if not path.exists():
                    self.skipTest("rendus locaux volontairement absents de Git")
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), asset["sha256"])


if __name__ == "__main__":
    unittest.main()
