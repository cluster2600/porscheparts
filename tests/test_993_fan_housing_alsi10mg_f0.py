import importlib.util
import json
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "parts/993-eng-fan-housing-alsi10mg-f0-0001/source/fan_housing.py"
RECORD = ROOT / "catalog/parts/993-eng-fan-housing-alsi10mg-f0-0001.json"
REPORT = ROOT / "parts/993-eng-fan-housing-alsi10mg-f0-0001/evidence/engineering-screen.json"
PF_SOURCE = ROOT / "catalog/sources/src-porschefanatics-993-fan-housing-candidate.json"
FVD_SOURCE = ROOT / "catalog/sources/src-fvd-993-fan-housing-dimensions.json"
ROISSY_SOURCE = ROOT / "catalog/sources/src-porsche-roissy-993-fan-housing-mass.json"
MATERIAL_SOURCE = ROOT / "catalog/sources/src-carparts-993-fan-housing-aluminium.json"
EOS_SOURCE = ROOT / "catalog/sources/src-eos-alsi10mg-current-page.json"
SPEC = importlib.util.spec_from_file_location("fan_housing", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class FanHousingAlSi10MgF0Tests(unittest.TestCase):
    def test_published_bounds_are_not_promoted_to_interfaces(self) -> None:
        screen = MODULE.engineering_screen()
        published = screen["geometry_authority"]["published"]

        self.assertEqual(published["part_numbers"], ["99310666703", "99310666701"])
        self.assertEqual(published["fvd_commercial_envelope_mm"], [300.0, 300.0, 170.0])
        self.assertEqual(published["fvd_commercial_mass_kg"], 1.9)
        self.assertEqual(published["porsche_roissy_commercial_mass_kg"], 1.86)
        self.assertGreaterEqual(len(screen["geometry_authority"]["hypotheses"]), 5)
        self.assertIn("commercial envelope", screen["geometry_authority"]["not_claimed"])

    def test_airflow_and_power_screen_are_recomputed(self) -> None:
        results = MODULE.engineering_screen()["results"]
        area = math.pi / 4.0 * (0.252**2 - 0.090**2)
        velocity = 1.25 / area
        dynamic_pressure = 0.5 * 1.05 * velocity**2
        pressure_loss = 0.80 * dynamic_pressure

        self.assertAlmostEqual(results["annular_flow_area_m2"], area)
        self.assertAlmostEqual(results["mean_air_velocity_m_s"], velocity)
        self.assertAlmostEqual(results["synthetic_pressure_loss_pa"], pressure_loss)
        self.assertAlmostEqual(results["air_power_w"], pressure_loss * 1.25)
        self.assertTrue(results["flow_screen_pass"])

    def test_structural_modal_and_thermal_screens_are_fail_closed(self) -> None:
        results = MODULE.engineering_screen()["results"]
        inertia = 12.0 * 12.0**3 / 12.0
        stress = (2000.0 / 6.0) * 81.0 * 6.0 / inertia
        deflection = (2000.0 / 6.0) * 81.0**3 / (3.0 * 70_000.0 * inertia)
        thermal_stress = 70.0e9 * 21.0e-6 * 130.0

        self.assertAlmostEqual(results["spoke_second_moment_mm4"], inertia)
        self.assertAlmostEqual(results["spoke_bending_stress_mpa"], stress)
        self.assertAlmostEqual(results["spoke_tip_deflection_mm"], deflection)
        self.assertTrue(results["static_screen_pass"])
        self.assertTrue(results["modal_screen_pass"])
        self.assertAlmostEqual(results["fully_constrained_thermal_stress_mpa"], thermal_stress / 1.0e6)
        self.assertLess(results["ambient_yield_to_constrained_thermal_ratio"], 1.5)
        self.assertFalse(results["thermal_screen_pass"])
        self.assertFalse(results["preliminary_screen_pass"])
        self.assertIn("not_computable", results["fatigue_containment_and_cooling_status"])

    def test_dfam_and_release_gates_are_explicit(self) -> None:
        screen = MODULE.engineering_screen()
        dfam = screen["dfam_screen"]

        self.assertTrue(dfam["stationary_part"])
        self.assertFalse(dfam["rotating_impeller_included"])
        self.assertTrue(dfam["open_air_path"])
        self.assertFalse(dfam["trapped_powder_volume"])
        self.assertEqual(dfam["integrated_spoke_count"], 6)
        self.assertAlmostEqual(dfam["shell_to_process_minimum_ratio"], 7.5)
        self.assertGreaterEqual(len(screen["release_blockers"]), 16)
        self.assertFalse(screen["manufacturing_authorized"])
        self.assertFalse(screen["engine_operation_authorized"])
        self.assertFalse(screen["release_authorized"])

    def test_step_catalogue_report_and_sources_are_consistent(self) -> None:
        record = json.loads(RECORD.read_text(encoding="utf-8"))
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        sources = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in (PF_SOURCE, FVD_SOURCE, ROISSY_SOURCE, MATERIAL_SOURCE, EOS_SOURCE)
        ]

        self.assertEqual(record["classification"]["safety_class"], "prohibited_pending_engineering")
        self.assertEqual(record["manufacturing"]["preferred_process"], "undecided")
        self.assertEqual(record["validation"]["status"], "concept")
        self.assertFalse(record["titanium"]["applicable"])
        self.assertEqual(report["step_roundtrip"]["status"], "passed")
        self.assertEqual(report["step_roundtrip"]["solid_count"], 1)
        self.assertEqual(report["step_roundtrip"]["stationary_spoke_count"], 6)
        self.assertEqual(report["step_roundtrip"]["mount_bore_count"], 6)
        self.assertEqual(report["step_roundtrip"]["rotating_impeller_count"], 0)
        for actual, expected in zip(report["step_roundtrip"]["envelope_mm"], [300.0, 300.0, 170.0]):
            self.assertAlmostEqual(actual, expected, places=5)
        self.assertAlmostEqual(report["results"]["cad_mass_g"], 1783.5766287255715)
        self.assertEqual([source["quality"]["evidence_level"] for source in sources], ["C", "C", "C", "C", "B"])


if __name__ == "__main__":
    unittest.main()
