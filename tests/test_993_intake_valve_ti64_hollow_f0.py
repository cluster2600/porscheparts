import importlib.util
import json
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "parts/993-eng-intake-valve-ti64-hollow-f0-0001/source/intake_valve.py"
RECORD = ROOT / "catalog/parts/993-eng-intake-valve-ti64-hollow-f0-0001.json"
REPORT = ROOT / "parts/993-eng-intake-valve-ti64-hollow-f0-0001/evidence/engineering-screen.json"
PF_SOURCE = ROOT / "catalog/sources/src-porschefanatics-993-titanium-valve-context.json"
FVD_SOURCE = ROOT / "catalog/sources/src-fvd-993-inlet-valve-dimensions.json"
EOS_SOURCE = ROOT / "catalog/sources/src-eos-ti64-grade5.json"
SPEC = importlib.util.spec_from_file_location("intake_valve", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class IntakeValveTi64HollowF0Tests(unittest.TestCase):
    def test_published_facts_hypotheses_and_gates_are_separate(self) -> None:
        screen = MODULE.engineering_screen()
        published = screen["geometry_authority"]["published"]

        self.assertEqual(published["porsche_part_number"], "99310540902")
        self.assertEqual(published["head_diameter_mm"], 49.0)
        self.assertEqual(published["stem_diameter_mm"], 8.0)
        self.assertEqual(published["product_envelope_mm"], [50.0, 110.0, 50.0])
        self.assertEqual(published["product_mass_g"], 120.0)
        self.assertGreaterEqual(len(screen["geometry_authority"]["hypotheses"]), 5)
        self.assertIn("No Porsche", screen["geometry_authority"]["not_claimed"])
        self.assertFalse(screen["manufacturing_authorized"])
        self.assertFalse(screen["engine_operation_authorized"])
        self.assertFalse(screen["release_authorized"])

    def test_simple_harmonic_dynamics_are_recomputed(self) -> None:
        results = MODULE.engineering_screen()["results"]
        engine_omega = 2.0 * math.pi * 6720.0 / 60.0
        cam_omega = engine_omega / 2.0
        duration = math.radians(240.0 / 2.0) / cam_omega
        peak_velocity = math.pi * 0.012 / duration
        peak_acceleration = 2.0 * math.pi**2 * 0.012 / duration**2

        self.assertAlmostEqual(results["engine_angular_speed_rad_s"], engine_omega)
        self.assertAlmostEqual(results["cam_angular_speed_rad_s"], cam_omega)
        self.assertAlmostEqual(results["simple_harmonic_event_duration_s"], duration)
        self.assertAlmostEqual(results["simple_harmonic_peak_velocity_m_s"], peak_velocity)
        self.assertAlmostEqual(results["simple_harmonic_peak_acceleration_m_s2"], peak_acceleration)
        self.assertAlmostEqual(results["synthetic_peak_inertia_force_n"], 0.060 * peak_acceleration)
        self.assertAlmostEqual(results["maximum_spring_force_n"], 520.0 + 40.0 * 12.0)

    def test_axial_plate_and_buckling_equations_are_recomputed(self) -> None:
        results = MODULE.engineering_screen()["results"]
        stem_area = math.pi / 4.0 * (8.0**2 - 5.0**2)
        head_area = math.pi * 49.0**2 / 4.0
        pressure_force = 0.20 * head_area
        expected_force = 1000.0 + 0.060 * results["simple_harmonic_peak_acceleration_m_s2"] + pressure_force
        second_moment = math.pi / 64.0 * (8.0**4 - 5.0**4)
        euler = math.pi**2 * 110_000.0 * second_moment / 95.0**2
        plate_stress = ((3.0 + 0.34) / 8.0) * 0.20 * 19.0**2 / 2.2**2

        self.assertAlmostEqual(results["hollow_stem_area_mm2"], stem_area)
        self.assertAlmostEqual(results["differential_pressure_force_n"], pressure_force)
        self.assertAlmostEqual(results["conservative_axial_force_n"], expected_force)
        self.assertAlmostEqual(results["nominal_hollow_stem_axial_stress_mpa"], expected_force / stem_area)
        self.assertAlmostEqual(results["hollow_stem_second_moment_mm4"], second_moment)
        self.assertAlmostEqual(results["euler_buckling_load_n"], euler)
        self.assertAlmostEqual(results["head_plate_bending_stress_screen_mpa"], plate_stress)

    def test_modal_thermal_and_cycle_equations_are_recomputed(self) -> None:
        results = MODULE.engineering_screen()["results"]
        area_m2 = math.pi / 4.0 * (8.0**2 - 5.0**2) / 1_000_000.0
        conduction = 6.7 * area_m2 * 400.0 / 0.060

        self.assertAlmostEqual(results["valve_event_frequency_hz"], 6720.0 / 120.0)
        self.assertAlmostEqual(results["valve_events_at_duty"], 6720.0 / 120.0 * 100.0 * 3600.0)
        self.assertAlmostEqual(results["free_total_length_growth_mm"], 9.0e-6 * 109.0 * 400.0)
        self.assertAlmostEqual(results["fully_constrained_elastic_thermal_stress_mpa"], 110_000.0 * 9.0e-6 * 400.0)
        self.assertAlmostEqual(results["one_dimensional_stem_conduction_w"], conduction)
        self.assertGreater(results["first_bending_frequency_screen_hz"], results["valve_event_frequency_hz"])
        self.assertGreater(results["spring_energy_over_lift_j"], results["peak_kinetic_energy_j"])

    def test_committed_step_sources_and_catalogue_stay_fail_closed(self) -> None:
        record = json.loads(RECORD.read_text(encoding="utf-8"))
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        porschefanatics = json.loads(PF_SOURCE.read_text(encoding="utf-8"))
        fvd = json.loads(FVD_SOURCE.read_text(encoding="utf-8"))
        eos = json.loads(EOS_SOURCE.read_text(encoding="utf-8"))

        self.assertEqual(record["classification"]["safety_class"], "prohibited_pending_engineering")
        self.assertEqual(record["manufacturing"]["preferred_process"], "LPBF")
        self.assertTrue(record["titanium"]["applicable"])
        self.assertEqual(record["validation"]["status"], "concept")
        self.assertEqual(report["step_roundtrip"]["status"], "passed")
        self.assertEqual(report["step_roundtrip"]["solid_count"], 1)
        self.assertEqual(report["step_roundtrip"]["open_powder_port_count"], 1)
        self.assertEqual(report["step_roundtrip"]["internal_radial_web_count"], 4)
        for actual, expected in zip(report["step_roundtrip"]["envelope_mm"], [49.0, 49.0, 109.0]):
            self.assertAlmostEqual(actual, expected, places=5)
        self.assertAlmostEqual(report["results"]["cad_mass_g"], 55.45271788925315)
        self.assertAlmostEqual(report["results"]["f0_mass_reduction_ratio_vs_same_outer_solid"], 0.2338416952290313)
        self.assertEqual(porschefanatics["quality"]["evidence_level"], "C")
        self.assertEqual(fvd["quality"]["evidence_level"], "C")
        self.assertEqual(eos["quality"]["evidence_level"], "B")
        self.assertGreaterEqual(len(report["release_blockers"]), 14)
        self.assertFalse(report["manufacturing_authorized"])
        self.assertFalse(report["engine_operation_authorized"])
        self.assertFalse(report["release_authorized"])


if __name__ == "__main__":
    unittest.main()
