import importlib.util
import json
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "parts/993-eng-k16-compressor-wheel-alsi10mg-f0-0001/source/compressor_wheel.py"
RECORD = ROOT / "catalog/parts/993-eng-k16-compressor-wheel-alsi10mg-f0-0001.json"
REPORT = ROOT / "parts/993-eng-k16-compressor-wheel-alsi10mg-f0-0001/evidence/engineering-screen.json"
PF_SOURCE = ROOT / "catalog/sources/src-porschefanatics-993-k16-compressor-wheel-candidate.json"
K16_SOURCE = ROOT / "catalog/sources/src-invasionautoproducts-993-k16-internal-data.json"
EOS_SOURCE = ROOT / "catalog/sources/src-eos-alsi10mg-current-page.json"
SPEC = importlib.util.spec_from_file_location("compressor_wheel", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class K16CompressorWheelAlSi10MgF0Tests(unittest.TestCase):
    def test_published_facts_hypotheses_and_gates_are_separate(self) -> None:
        screen = MODULE.engineering_screen()
        published = screen["geometry_authority"]["published"]

        self.assertEqual(published["compressor_wheel_reference"], "53241232006")
        self.assertEqual(published["right_turbo_reference"], "53169886735")
        self.assertEqual(published["inducer_diameter_mm"], 40.6)
        self.assertEqual(published["exducer_diameter_mm"], 60.5)
        self.assertEqual(published["main_blade_count"], 6)
        self.assertEqual(published["splitter_blade_count"], 6)
        self.assertGreaterEqual(len(screen["geometry_authority"]["hypotheses"]), 6)
        self.assertIn("No BorgWarner", screen["geometry_authority"]["not_claimed"])
        self.assertFalse(screen["manufacturing_authorized"])
        self.assertFalse(screen["turbo_operation_authorized"])
        self.assertFalse(screen["engine_operation_authorized"])
        self.assertFalse(screen["release_authorized"])

    def test_speed_flow_and_reynolds_are_recomputed(self) -> None:
        results = MODULE.engineering_screen()["results"]
        sound_speed = math.sqrt(1.4 * 287.05 * 330.0)
        tip_speed = 0.9 * sound_speed
        radius = 60.5 / 2000.0
        omega = tip_speed / radius
        rpm = omega * 60.0 / (2.0 * math.pi)
        bank_flow = 3.6 / 1000.0 * 5750.0 / 120.0 * 0.95 / 2.0
        area = math.pi / 4.0 * (0.0406**2 - 0.012**2)
        velocity = bank_flow / area
        density = 180_000.0 / (287.05 * 330.0)

        self.assertAlmostEqual(results["sound_speed_m_s"], sound_speed)
        self.assertAlmostEqual(results["tip_speed_m_s"], tip_speed)
        self.assertAlmostEqual(results["derived_shaft_speed_rpm"], rpm)
        self.assertAlmostEqual(results["bank_volume_flow_m3_s"], bank_flow)
        self.assertAlmostEqual(results["inducer_annulus_area_m2"], area)
        self.assertAlmostEqual(results["inducer_axial_velocity_m_s"], velocity)
        self.assertAlmostEqual(results["inducer_axial_mach"], velocity / sound_speed)
        self.assertAlmostEqual(results["inducer_reynolds"], density * velocity * 0.0406 / 1.9e-5)

    def test_compressor_thermodynamics_are_recomputed(self) -> None:
        results = MODULE.engineering_screen()["results"]
        t2s = 330.0 * 1.8 ** ((1.4 - 1.0) / 1.4)
        t2 = 330.0 + (t2s - 330.0) / 0.72
        work = 1005.0 * (t2 - 330.0)
        mass_flow = results["air_density_kg_m3"] * results["bank_volume_flow_m3_s"]
        power = mass_flow * work

        self.assertAlmostEqual(results["isentropic_outlet_temperature_k"], t2s)
        self.assertAlmostEqual(results["efficiency_adjusted_outlet_temperature_k"], t2)
        self.assertAlmostEqual(results["specific_compressor_work_j_kg"], work)
        self.assertAlmostEqual(results["screening_compressor_power_w"], power)
        self.assertAlmostEqual(results["screening_compressor_torque_nm"], power / (results["tip_speed_m_s"] / 0.03025))

    def test_rotating_disk_blade_thermal_and_unbalance_screens_are_recomputed(self) -> None:
        results = MODULE.engineering_screen()["results"]
        omega = results["tip_speed_m_s"] / 0.03025
        disk_stress_pa = (3.0 + 0.33) / 8.0 * 2670.0 * omega**2 * 0.03025**2
        main_mass_kg = 306.9 / 1.0e9 * 2670.0
        main_force = main_mass_kg * omega**2 * ((7.0 + 30.25) / 2000.0)
        main_stress_mpa = 2.0 * main_force / (1.2 * 11.0)

        self.assertAlmostEqual(results["rotating_disk_stress_mpa"], disk_stress_pa / 1.0e6)
        self.assertAlmostEqual(results["overspeed_rotating_disk_stress_mpa"], disk_stress_pa / 1.0e6 * 1.2**2)
        self.assertAlmostEqual(results["main_blade_centrifugal_force_n"], main_force)
        self.assertAlmostEqual(results["main_blade_root_stress_mpa"], main_stress_mpa)
        self.assertAlmostEqual(results["overspeed_governing_blade_root_stress_mpa"], main_stress_mpa * 1.2**2)
        self.assertLess(results["ambient_yield_to_overspeed_blade_root_stress_ratio"], 1.0)
        self.assertAlmostEqual(results["free_thermal_radius_growth_mm"], 21.0e-6 * 30.25 * 150.0)
        self.assertAlmostEqual(results["fully_constrained_thermal_stress_mpa"], 70.0e9 * 21.0e-6 * 150.0 / 1.0e6)
        self.assertAlmostEqual(results["residual_unbalance_force_n"], 10.0e-9 * omega**2)

    def test_committed_step_sources_and_catalogue_preserve_failed_screen(self) -> None:
        record = json.loads(RECORD.read_text(encoding="utf-8"))
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        porschefanatics = json.loads(PF_SOURCE.read_text(encoding="utf-8"))
        k16 = json.loads(K16_SOURCE.read_text(encoding="utf-8"))
        eos = json.loads(EOS_SOURCE.read_text(encoding="utf-8"))

        self.assertEqual(record["classification"]["safety_class"], "prohibited_pending_engineering")
        self.assertEqual(record["manufacturing"]["preferred_process"], "LPBF")
        self.assertFalse(record["titanium"]["applicable"])
        self.assertEqual(record["validation"]["status"], "concept")
        self.assertEqual(report["step_roundtrip"]["status"], "passed")
        self.assertEqual(report["step_roundtrip"]["solid_count"], 1)
        self.assertEqual(report["step_roundtrip"]["main_blade_count"], 6)
        self.assertEqual(report["step_roundtrip"]["splitter_blade_count"], 6)
        for actual, expected in zip(report["step_roundtrip"]["envelope_mm"], [60.5, 60.5, 18.0]):
            self.assertAlmostEqual(actual, expected, places=5)
        self.assertAlmostEqual(report["results"]["cad_mass_g"], 32.70298560930258)
        self.assertLess(report["results"]["ambient_yield_to_overspeed_blade_root_stress_ratio"], 1.0)
        self.assertEqual(porschefanatics["quality"]["evidence_level"], "C")
        self.assertEqual(k16["quality"]["evidence_level"], "C")
        self.assertEqual(eos["quality"]["evidence_level"], "B")
        self.assertGreaterEqual(len(report["release_blockers"]), 14)
        self.assertFalse(report["manufacturing_authorized"])
        self.assertFalse(report["turbo_operation_authorized"])
        self.assertFalse(report["engine_operation_authorized"])
        self.assertFalse(report["release_authorized"])


if __name__ == "__main__":
    unittest.main()
