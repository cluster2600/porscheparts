import importlib.util
import json
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "parts/993-eng-intercooler-end-tank-alsi10mg-f0-0001/source/end_tank.py"
RECORD = ROOT / "catalog/parts/993-eng-intercooler-end-tank-alsi10mg-f0-0001.json"
REPORT = ROOT / "parts/993-eng-intercooler-end-tank-alsi10mg-f0-0001/evidence/engineering-screen.json"
TA_SOURCE = ROOT / "catalog/sources/src-ta-technix-993-intercooler-dimensions.json"
ALBERT_SOURCE = ROOT / "catalog/sources/src-albert-motorsport-993-aluminum-intercooler.json"
PF_SOURCE = ROOT / "catalog/sources/src-porschefanatics-993-intercooler-end-tank-candidate.json"
SPEC = importlib.util.spec_from_file_location("end_tank", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class IntercoolerEndTankAlSi10MgF0Tests(unittest.TestCase):
    def test_published_facts_and_hypotheses_are_separate(self) -> None:
        report = MODULE.engineering_screen()
        published = report["geometry_authority"]["published"]

        self.assertEqual(published["two_core_dimensions_mm"], [260.0, 260.0, 100.0])
        self.assertEqual(published["outer_connection_diameter_mm"], 66.0)
        self.assertEqual(published["inner_connection_diameter_mm"], 68.0)
        self.assertIn("exact alloy not disclosed", published["assembly_material"])
        self.assertGreaterEqual(len(report["geometry_authority"]["hypotheses"]), 5)
        self.assertIn("No TA Technix", report["geometry_authority"]["not_claimed"])
        self.assertFalse(report["manufacturing_authorized"])
        self.assertFalse(report["engine_operation_authorized"])
        self.assertFalse(report["release_authorized"])

    def test_flow_equations_are_recomputed(self) -> None:
        results = MODULE.engineering_screen()["results"]
        port_diameter_m = 0.0616
        port_area_m2 = math.pi * (port_diameter_m / 2.0) ** 2
        core_open_area_m2 = 0.260 * 0.100 * 0.65
        total_flow = 3.6 / 1000.0 * 5750.0 / (2.0 * 60.0) * 0.95
        bank_flow = total_flow / 2.0
        density = 180_000.0 / (287.0 * 330.0)
        port_velocity = bank_flow / port_area_m2
        core_velocity = bank_flow / core_open_area_m2
        reynolds = density * port_velocity * port_diameter_m / 1.9e-5
        area_ratio = core_open_area_m2 / port_area_m2
        loss_coefficient = (1.0 - 1.0 / area_ratio) ** 2
        loss = loss_coefficient * 0.5 * density * port_velocity**2

        self.assertAlmostEqual(results["port_flow_area_m2"], port_area_m2)
        self.assertAlmostEqual(results["core_open_area_m2"], core_open_area_m2)
        self.assertAlmostEqual(results["bank_volume_flow_m3_s"], bank_flow)
        self.assertAlmostEqual(results["air_density_kg_m3"], density)
        self.assertAlmostEqual(results["port_velocity_m_s"], port_velocity)
        self.assertAlmostEqual(results["core_face_velocity_m_s"], core_velocity)
        self.assertAlmostEqual(results["port_reynolds"], reynolds)
        self.assertAlmostEqual(results["effective_area_ratio"], area_ratio)
        self.assertAlmostEqual(results["screening_expansion_pressure_loss_pa"], loss)
        self.assertAlmostEqual(results["screening_flow_power_loss_w"], loss * bank_flow)

    def test_pressure_thermal_and_cycle_equations_are_recomputed(self) -> None:
        results = MODULE.engineering_screen()["results"]

        self.assertAlmostEqual(results["port_thin_wall_hoop_stress_mpa"], 0.08 * 33.0 / 2.2)
        self.assertAlmostEqual(results["unsupported_panel_bay_mm"], 100.0 / 4.0)
        self.assertAlmostEqual(results["guided_panel_bending_stress_screen_mpa"], 0.308 * 0.08 * (25.0 / 2.2) ** 2)
        self.assertAlmostEqual(results["core_face_pressure_force_n"], 80_000.0 * 0.260 * 0.100)
        self.assertAlmostEqual(results["free_flange_width_growth_mm"], 21.0e-6 * 274.0 * 100.0)
        self.assertAlmostEqual(results["fully_constrained_elastic_thermal_stress_mpa"], 70_000.0 * 21.0e-6 * 100.0)
        self.assertAlmostEqual(results["bank_pulse_frequency_hz"], 5750.0 / 60.0 * 3.0 / 2.0)
        self.assertAlmostEqual(results["pressure_pulses_at_duty"], 5750.0 / 60.0 * 3.0 / 2.0 * 100.0 * 3600.0)

    def test_committed_step_sources_and_catalogue_stay_fail_closed(self) -> None:
        record = json.loads(RECORD.read_text(encoding="utf-8"))
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        ta = json.loads(TA_SOURCE.read_text(encoding="utf-8"))
        albert = json.loads(ALBERT_SOURCE.read_text(encoding="utf-8"))
        porschefanatics = json.loads(PF_SOURCE.read_text(encoding="utf-8"))

        self.assertEqual(record["classification"]["safety_class"], "prohibited_pending_engineering")
        self.assertEqual(record["manufacturing"]["preferred_process"], "LPBF")
        self.assertFalse(record["titanium"]["applicable"])
        self.assertEqual(record["validation"]["status"], "concept")
        self.assertEqual(report["step_roundtrip"]["status"], "passed")
        self.assertEqual(report["step_roundtrip"]["solid_count"], 1)
        self.assertEqual(report["step_roundtrip"]["connected_flow_volume_count"], 1)
        self.assertEqual(report["step_roundtrip"]["flow_guide_count"], 3)
        for actual, expected in zip(report["step_roundtrip"]["envelope_mm"], [134.0, 274.0, 114.0]):
            self.assertAlmostEqual(actual, expected, places=5)
        self.assertAlmostEqual(report["results"]["cad_mass_g"], 605.9203380614059)
        self.assertEqual(ta["quality"]["dimensional_accuracy"], "declared")
        self.assertEqual(albert["quality"]["evidence_level"], "C")
        self.assertEqual(porschefanatics["quality"]["dimensional_accuracy"], "unknown")
        self.assertGreaterEqual(len(report["release_blockers"]), 12)
        self.assertFalse(report["manufacturing_authorized"])
        self.assertFalse(report["engine_operation_authorized"])
        self.assertFalse(report["release_authorized"])


if __name__ == "__main__":
    unittest.main()
