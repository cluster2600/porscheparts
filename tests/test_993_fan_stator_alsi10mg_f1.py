import functools
import importlib.util
import json
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PART = ROOT / "parts/993-eng-fan-stator-alsi10mg-f1-0001"
SCRIPT = PART / "source/fan_stator_f1.py"
RECORD = ROOT / "catalog/parts/993-eng-fan-stator-alsi10mg-f1-0001.json"
REPORT = PART / "evidence/engineering-screen.json"
ROTOR_REPORT = ROOT / "parts/993-eng-cooling-impeller-we43-f1-0001/evidence/engineering-screen.json"
SPEC = importlib.util.spec_from_file_location("fan_stator_f1", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


@functools.lru_cache(maxsize=None)
def cached_screen(cad_volume_mm3=None):
    return MODULE.engineering_screen(cad_volume_mm3)


class FanStatorAlSi10MgF1Tests(unittest.TestCase):
    def test_vanes_remove_the_rotor_swirl_without_stall(self) -> None:
        screen = cached_screen()
        for vane, exit_flow in zip(screen["vane_design"], screen["rotor_exit_flow"]):
            self.assertAlmostEqual(vane["inlet_metal_deg"], exit_flow["swirl_angle_deg"])
            self.assertAlmostEqual(vane["radius_mm"], exit_flow["radius_mm"])
        for row in screen["vane_off_design_rows"]:
            self.assertLess(abs(row["residual_exit_swirl_deg"]), 0.5)
            self.assertFalse(row["stalled"])

    def test_the_stator_adds_flow_at_lower_shaft_power(self) -> None:
        screen = cached_screen()
        points = screen["operating_points"]
        rotor_only = points["F1_rotor_only_sharp_inlet"]
        stator = points["F1_rotor_plus_designed_stator_sharp_inlet"]
        both = points["F1_rotor_plus_designed_stator_and_bellmouth"]

        self.assertGreater(stator["flow_m3_s"], rotor_only["flow_m3_s"])
        self.assertGreater(both["flow_m3_s"], stator["flow_m3_s"])
        self.assertLess(stator["shaft_power_w"], rotor_only["shaft_power_w"])
        self.assertGreater(stator["efficiency"], rotor_only["efficiency"])
        self.assertEqual(stator["exit_swirl_loss_pa"] < 1.0, True)

    def test_rotor_only_point_matches_the_committed_rotor_evidence(self) -> None:
        rotor = json.loads(ROTOR_REPORT.read_text(encoding="utf-8"))
        point = cached_screen()["operating_points"]["F1_rotor_only_sharp_inlet"]
        self.assertAlmostEqual(point["flow_m3_s"], rotor["operating_points"]["F1_rotor_in_F0_housing"]["flow_m3_s"])

    def test_tone_screen_picks_the_fewest_vanes_that_cut_off_blade_pass(self) -> None:
        results = cached_screen()["results"]
        tip_mach = cached_screen()["synthetic_cases"]["overspeed_tip_mach"]

        self.assertEqual(results["vane_count"], 17)
        self.assertEqual(math.gcd(17, 11), 1)
        for v in range(12, 17):
            screen = MODULE.tone_screen(v, 11, tip_mach)
            self.assertFalse(screen["coprime_with_blades"] and screen["bpf_interaction_cut_off"])
        self.assertEqual(MODULE.tone_screen(17, 11, tip_mach)["cut_on_modes"], [{"harmonic": 2, "k": 1, "mode": 5}])

    def test_modal_bounds_clear_blade_pass_and_are_recomputed(self) -> None:
        structure = cached_screen()["structure"]
        self.assertAlmostEqual(
            structure["first_mode_clamped_hz"] / structure["first_mode_pinned_hz"],
            4.730040744862704**2 / math.pi**2,
        )
        for mode in (structure["first_mode_pinned_hz"], structure["first_mode_clamped_hz"]):
            for f in (1833.3333333333333, 2200.0, 3666.6666666666665, 4400.0):
                self.assertGreaterEqual(abs(mode - f) / f, 0.20)

    def test_committed_step_and_catalogue_are_fail_closed(self) -> None:
        record = json.loads(RECORD.read_text(encoding="utf-8"))
        report = json.loads(REPORT.read_text(encoding="utf-8"))

        self.assertEqual(record["classification"]["safety_class"], "prohibited_pending_engineering")
        self.assertEqual(record["validation"]["status"], "concept")
        self.assertEqual(report["step_roundtrip"]["status"], "passed")
        self.assertEqual(report["step_roundtrip"]["solid_count"], 1)
        self.assertEqual(report["step_roundtrip"]["vane_count"], 17)
        for actual, expected in zip(report["step_roundtrip"]["envelope_mm"], [248.0, 248.0, 39.0]):
            self.assertAlmostEqual(actual, expected, places=3)
        self.assertEqual(report["results"], cached_screen(report["results"]["cad_volume_mm3"])["results"])
        self.assertFalse(report["manufacturing_authorized"])
        self.assertFalse(report["engine_operation_authorized"])
        self.assertFalse(report["release_authorized"])


if __name__ == "__main__":
    unittest.main()
