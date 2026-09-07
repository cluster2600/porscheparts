"""Tests fail-closed du dimensionnement distribution et matière F45."""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path
import struct
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "twins/reference-917-engine/source/build_valvetrain_material_screen_f45.py"
REPORT = ROOT / "twins/reference-917-engine/valvetrain-material-screen-f45.json"
IMAGE = ROOT / "twins/reference-917-engine/evidence/f45-valvetrain/valvetrain-material-screen-f45.png"


def load_module():
    specification = importlib.util.spec_from_file_location("f45_valvetrain_material", SCRIPT)
    if specification is None or specification.loader is None:
        raise RuntimeError("cannot_import_f45_builder")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


class ValvetrainMaterialScreenF45Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.report = json.loads(REPORT.read_text(encoding="utf-8"))

    def test_report_is_reproducible_and_fail_closed(self):
        self.assertEqual(self.report, self.module.build_report(ROOT))
        self.assertEqual(self.report["phase"], "F45")
        self.assertTrue(self.report["release_gates"])
        self.assertTrue(all(value is False for value in self.report["release_gates"].values()))
        self.assertIsNone(self.report["head_material_selection"]["selected"])

    def test_no_global_ovalization_or_synthetic_head_body(self):
        boundary = self.report["authority_boundary"]
        self.assertFalse(boundary["global_ovalization"])
        self.assertFalse(boundary["external_scan_contour_modified"])
        for architecture in self.report["architectures"].values():
            policy = architecture["geometry_policy"]
            self.assertEqual(policy["combustion_bore_shape"], "circle")
            self.assertEqual(policy["combustion_bore_diameter_mm"], 90.0)
            self.assertFalse(policy["global_anisotropic_scale_allowed"])
            self.assertFalse(policy["global_ovalization_allowed"])
            self.assertFalse(policy["body_or_fin_geometry_created"])
            self.assertEqual(architecture["packing"]["bore_shape"], "circle")

    def test_type_912_values_are_never_relabelled_as_917_30(self):
        two = self.report["architectures"]["2v"]
        historical = two["historical_reference"]
        self.assertEqual(historical["variant"], "type_912_4_5_na_not_917_30")
        self.assertEqual(historical["intake_head_diameter_mm"], 47.5)
        self.assertEqual(historical["exhaust_head_diameter_mm"], 40.5)
        self.assertEqual(historical["intake_max_lift_mm"], 12.1)
        self.assertEqual(historical["exhaust_max_lift_mm"], 10.5)
        self.assertFalse(historical["direct_transfer_to_F45"])
        self.assertTrue(self.report["authority_boundary"]["type_912_values_never_relabelled_as_917_30_exact"])

    def test_circular_bore_packing_has_positive_gaps(self):
        for architecture in self.report["architectures"].values():
            packing = architecture["packing"]
            self.assertTrue(packing["screen_pass"])
            self.assertGreaterEqual(packing["minimum_bore_edge_gap_mm"], 1.5)
            self.assertGreaterEqual(packing["minimum_seat_to_seat_gap_mm"], 2.0)
            self.assertGreater(packing["minimum_spring_envelope_gap_mm"], 0.0)
        self.assertGreaterEqual(
            self.report["architectures"]["4v"]["packing"]["minimum_seat_to_plug_gap_mm"],
            3.0,
        )

    def test_curtain_throat_kinematics_and_frequency_are_explicit(self):
        equations = self.report["equations"]
        for name in (
            "curtain_area",
            "throat_area",
            "event_time",
            "half_cosine_peak_velocity",
            "half_cosine_peak_acceleration",
            "system_frequency",
        ):
            self.assertIn(name, equations)
        intake_2v = self.report["architectures"]["2v"]["valves"]["intake"]
        expected_curtain = math.pi * 42.0 * 11.5
        expected_throat = math.pi * (0.86 * 42.0) ** 2 / 4.0
        self.assertAlmostEqual(intake_2v["flow"]["curtain_area_mm2"], expected_curtain, places=5)
        self.assertAlmostEqual(intake_2v["flow"]["throat_area_mm2"], expected_throat, places=5)
        self.assertEqual(intake_2v["flow"]["limiter_at_maximum_lift"], "throat")
        self.assertAlmostEqual(intake_2v["event_time_ms"], 300.0 / (6.0 * 9000.0) * 1000.0, places=5)
        for architecture in self.report["architectures"].values():
            for valve in architecture["valves"].values():
                self.assertGreater(valve["maximum_velocity_m_s"], 0.0)
                self.assertGreater(valve["maximum_acceleration_m_s2"], 0.0)
                self.assertEqual(valve["spring"]["valve_event_frequency_hz"], 75.0)
                self.assertFalse(valve["spring"]["supplier_curve_or_spintron_validated"])

    def test_spring_math_has_wahl_bind_load_and_margin(self):
        for architecture in self.report["architectures"].values():
            for valve in architecture["valves"].values():
                spring = valve["spring"]
                self.assertGreater(spring["combined_rate_n_mm"], 0.0)
                self.assertGreaterEqual(spring["worst_case_coil_bind_margin_mm"], 2.5)
                self.assertGreaterEqual(spring["open_force_to_combined_load_margin"], 1.2)
                self.assertLessEqual(spring["maximum_wahl_corrected_shear_mpa"], 1000.0)
                self.assertGreater(spring["natural_to_event_frequency_ratio"], 1.0)
                self.assertTrue(spring["static_analytical_screen_pass"])
                self.assertFalse(spring["dynamic_screen_pass"])
                self.assertFalse(spring["analytical_screen_pass"])
                self.assertFalse(spring["research_shear_limit_is_supplier_allowable"])
                for coil in (spring["outer"], spring["inner"]):
                    self.assertGreater(coil["spring_index"], 4.0)
                    self.assertGreater(coil["wahl_factor"], 1.0)

    def test_routes_are_purchased_for_valves_springs_seats_and_guides(self):
        for architecture in self.report["architectures"].values():
            routes = architecture["component_routes"]
            self.assertIn("not_printed", routes["valves"])
            self.assertIn("not_printed", routes["springs"])
            self.assertIn("not_printed", routes["seats_and_guides"])
            interfaces = architecture["seat_and_guide_strategy"]
            self.assertFalse(interfaces["interface_dimension_invented"])
            self.assertIsNone(interfaces["seat_angle_contact_width_interference_and_bore"])
            self.assertIsNone(interfaces["guide_length_outer_diameter_interference_clearance_and_finish"])
        for component in self.report["component_material_screen"].values():
            self.assertFalse(component["printed"])
            self.assertIsNone(component["selected_supplier_part"])
        self.assertIsNone(self.report["component_material_screen"]["nimonic_exhaust_alternative"]["source"])

    def test_no_head_material_has_a_complete_hot_card(self):
        matrix = self.report["head_material_matrix"]
        self.assertEqual(len(matrix), 5)
        self.assertTrue(all(item["complete_hot_card"] is False for item in matrix))
        self.assertEqual({item["id"] for item in matrix}, {
            "Aheadd_HT1_heat_treatment_1",
            "Aheadd_HT1_heat_treatment_2",
            "A20X_A205_LPBF_T7",
            "EOS_AlF357_T6_like",
            "EOS_AlSi10Mg_T6",
        })
        ht2 = next(item for item in matrix if item["requested_alias"] == "Aheadd_HT2")
        self.assertIn("traitement #2", ht2["normalization_note"])

    def test_checked_image_is_full_hd_plan_view(self):
        data = IMAGE.read_bytes()
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        width, height = struct.unpack(">II", data[16:24])
        self.assertEqual((width, height), (2560, 1440))
        self.assertGreater(len(data), 100_000)


if __name__ == "__main__":
    unittest.main()
