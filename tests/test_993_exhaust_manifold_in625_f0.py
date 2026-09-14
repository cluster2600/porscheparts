import importlib.util
import json
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "parts/993-eng-exhaust-manifold-in625-f0-0001/source/exhaust_manifold.py"
RECORD = ROOT / "catalog/parts/993-eng-exhaust-manifold-in625-f0-0001.json"
REPORT = ROOT / "parts/993-eng-exhaust-manifold-in625-f0-0001/evidence/engineering-screen.json"
KLINE_SOURCE = ROOT / "catalog/sources/src-kline-993-turbo-in625-manifolds.json"
PF_SOURCE = ROOT / "catalog/sources/src-porschefanatics-993-turbo-in625-manifolds.json"
PET_SOURCE = ROOT / "catalog/sources/src-porsche-pet-993-turbo-heat-exchanger-202-10.json"
SPEC = importlib.util.spec_from_file_location("exhaust_manifold", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ExhaustManifoldIn625F0Tests(unittest.TestCase):
    def test_published_facts_and_hypotheses_are_separate(self) -> None:
        report = MODULE.engineering_screen()
        authority = report["geometry_authority"]

        self.assertEqual(authority["published"][0], "993 Turbo manifold offering in Inconel 625")
        self.assertIn("2.9 kg per side", authority["published"][1])
        self.assertGreaterEqual(len(authority["hypotheses"]), 6)
        self.assertIn("No Porsche or Kline surface", authority["not_claimed"])
        self.assertFalse(report["manufacturing_authorized"])
        self.assertFalse(report["engine_operation_authorized"])
        self.assertFalse(report["release_authorized"])

    def test_flow_equations_are_recomputed(self) -> None:
        results = MODULE.engineering_screen()["results"]
        primary_area = math.pi * (0.034 / 2.0) ** 2
        collector_area = math.pi * (0.056 / 2.0) ** 2
        cold_total = 3.6 / 1000.0 * 5750.0 / (2.0 * 60.0) * 0.95
        hot_bank = cold_total / 2.0 * 900.0 / 300.0
        hot_density = 1.18 * 300.0 / 900.0
        primary_velocity = hot_bank / 3.0 / primary_area
        collector_velocity = hot_bank / collector_area
        speed_of_sound = math.sqrt(1.33 * 287.0 * 900.0)
        loss = 0.2 * 0.5 * hot_density * collector_velocity**2

        self.assertAlmostEqual(results["primary_flow_area_each_m2"], primary_area)
        self.assertAlmostEqual(results["collector_flow_area_m2"], collector_area)
        self.assertAlmostEqual(results["cold_volume_flow_total_m3_s"], cold_total)
        self.assertAlmostEqual(results["hot_volume_flow_bank_m3_s"], hot_bank)
        self.assertAlmostEqual(results["primary_velocity_m_s"], primary_velocity)
        self.assertAlmostEqual(results["collector_velocity_m_s"], collector_velocity)
        self.assertAlmostEqual(results["collector_mach"], collector_velocity / speed_of_sound)
        self.assertAlmostEqual(results["screening_junction_pressure_loss_pa"], loss)
        self.assertGreater(results["primary_reynolds"], 4000.0)
        self.assertGreater(results["collector_reynolds"], results["primary_reynolds"])

    def test_pressure_thermal_radiation_and_acoustic_equations_are_recomputed(self) -> None:
        results = MODULE.engineering_screen()["results"]
        collector_area = math.pi * (0.056 / 2.0) ** 2
        speed_of_sound = math.sqrt(1.33 * 287.0 * 900.0)
        bank_frequency = 5750.0 / 60.0 * 3.0 / 2.0

        self.assertAlmostEqual(results["thin_wall_hoop_stress_mpa"], 50_000.0 * 0.028 / 0.0012 / 1e6)
        self.assertAlmostEqual(results["collector_pressure_force_n"], 50_000.0 * collector_area)
        self.assertAlmostEqual(results["free_thermal_expansion_mm"], 13.7e-6 * 215.0 * (900.0 - 293.0))
        self.assertAlmostEqual(results["fully_constrained_elastic_thermal_stress_mpa"], 204_000.0 * 13.7e-6 * (900.0 - 293.0))
        self.assertAlmostEqual(results["bank_pulse_frequency_hz"], bank_frequency)
        self.assertAlmostEqual(results["path_quarter_wave_hz"], speed_of_sound / (4.0 * results["acoustic_path_mm"] / 1000.0))
        self.assertGreater(results["radiative_power_approx_w"], 0.0)
        self.assertGreater(results["fully_constrained_elastic_thermal_stress_mpa"], 640.0)

    def test_committed_step_sources_and_catalogue_stay_fail_closed(self) -> None:
        record = json.loads(RECORD.read_text(encoding="utf-8"))
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        kline = json.loads(KLINE_SOURCE.read_text(encoding="utf-8"))
        porschefanatics = json.loads(PF_SOURCE.read_text(encoding="utf-8"))
        pet = json.loads(PET_SOURCE.read_text(encoding="utf-8"))

        self.assertEqual(record["classification"]["safety_class"], "prohibited_pending_engineering")
        self.assertEqual(record["manufacturing"]["preferred_process"], "undecided")
        self.assertEqual(record["validation"]["status"], "concept")
        self.assertEqual(report["step_roundtrip"]["status"], "passed")
        self.assertEqual(report["step_roundtrip"]["solid_count"], 1)
        self.assertEqual(report["step_roundtrip"]["connected_flow_volume_count"], 1)
        envelope = report["step_roundtrip"]["envelope_mm"]
        for actual, expected in zip(envelope, [146.4, 66.4, 215.0]):
            self.assertAlmostEqual(actual, expected, places=5)
        self.assertAlmostEqual(report["results"]["screening_mass_flow_core_g"], 509.97159952215463)
        self.assertEqual(kline["quality"]["dimensional_accuracy"], "unknown")
        self.assertEqual(porschefanatics["quality"]["evidence_level"], "C")
        self.assertIn("993 211 039 55", pet["notes"])
        self.assertGreaterEqual(len(report["release_blockers"]), 10)
        self.assertFalse(report["manufacturing_authorized"])
        self.assertFalse(report["engine_operation_authorized"])
        self.assertFalse(report["release_authorized"])


if __name__ == "__main__":
    unittest.main()
