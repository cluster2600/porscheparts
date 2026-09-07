import importlib.util
import json
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "parts/993-eng-three-runner-intake-alsi10mg-f0-0001/source/three_runner_intake.py"
RECORD = ROOT / "catalog/parts/993-eng-three-runner-intake-alsi10mg-f0-0001.json"
REPORT = ROOT / "parts/993-eng-three-runner-intake-alsi10mg-f0-0001/evidence/engineering-screen.json"
PATRICK_SOURCE = ROOT / "catalog/sources/src-patrick-pmo-964-993-46mm-intake-manifold.json"
PF_SOURCE = ROOT / "catalog/sources/src-porschefanatics-pmo-964-993-46mm-intake-manifold.json"
SPEC = importlib.util.spec_from_file_location("three_runner_intake", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ThreeRunnerIntakeAlSi10MgF0Tests(unittest.TestCase):
    def test_published_string_and_interpretation_are_separate(self) -> None:
        report = MODULE.engineering_screen()
        authority = report["geometry_authority"]
        self.assertEqual(
            authority["published"],
            [
                "commercial title string 46 mm x 42 mm x 100 mm",
                "three-bolt manifold set with two pieces",
                "raw aluminium finish, alloy not disclosed",
            ],
        )
        self.assertEqual(
            authority["catalogue_identity"],
            ["FUE PMO 9150", "PM-O915-0", "PMO9150"],
        )
        self.assertGreaterEqual(len(authority["hypotheses"]), 7)
        self.assertIn("No PMO or Porsche surface", authority["not_claimed"])
        self.assertFalse(report["engine_operation_authorized"])
        self.assertFalse(report["release_authorized"])

    def test_flow_and_pressure_equations_are_recomputed(self) -> None:
        results = MODULE.engineering_screen()["results"]
        total_q = 3.6 / 1000.0 * 6800.0 / (2.0 * 60.0) * 0.95
        runner_q = total_q / 6.0
        top_area = math.pi * (0.046 / 2.0) ** 2
        bottom_area = math.pi * (0.042 / 2.0) ** 2
        top_u = runner_q / top_area
        bottom_u = runner_q / bottom_area
        speed_of_sound = math.sqrt(1.4 * 287.0 * 320.0)
        loss = 0.05 * 0.5 * 1.16 * bottom_u**2

        self.assertAlmostEqual(results["total_cold_volume_flow_m3_s"], total_q)
        self.assertAlmostEqual(results["runner_volume_flow_m3_s"], runner_q)
        self.assertAlmostEqual(results["top_velocity_m_s"], top_u)
        self.assertAlmostEqual(results["bottom_velocity_m_s"], bottom_u)
        self.assertAlmostEqual(results["bottom_mach"], bottom_u / speed_of_sound)
        self.assertAlmostEqual(results["screening_contraction_loss_pa"], loss)
        self.assertGreater(results["bottom_reynolds"], 4000.0)

    def test_acoustic_thermal_and_shell_screens_are_recomputed(self) -> None:
        results = MODULE.engineering_screen()["results"]
        speed_of_sound = math.sqrt(1.4 * 287.0 * 320.0)
        firing_hz = 6800.0 / 60.0 * 6.0 / 2.0

        self.assertAlmostEqual(results["engine_firing_frequency_hz"], firing_hz)
        self.assertAlmostEqual(
            results["runner_quarter_wave_hz"], speed_of_sound / (4.0 * 0.1)
        )
        self.assertAlmostEqual(
            results["first_order_quarter_wave_length_mm"],
            speed_of_sound / (4.0 * firing_hz) * 1000.0,
        )
        self.assertAlmostEqual(results["thin_wall_hoop_stress_mpa"], 0.11)
        self.assertAlmostEqual(
            results["free_thermal_expansion_mm"], 21.0e-6 * 100.0 * 100.0
        )
        self.assertAlmostEqual(
            results["fully_constrained_elastic_thermal_stress_mpa"], 147.0
        )

    def test_committed_step_and_catalogue_stay_fail_closed(self) -> None:
        record = json.loads(RECORD.read_text(encoding="utf-8"))
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        patrick = json.loads(PATRICK_SOURCE.read_text(encoding="utf-8"))
        porschefanatics = json.loads(PF_SOURCE.read_text(encoding="utf-8"))

        self.assertEqual(record["manufacturing"]["preferred_process"], "undecided")
        self.assertIn("casting", record["manufacturing"]["candidate_processes"])
        self.assertIn("LPBF", record["manufacturing"]["candidate_processes"])
        self.assertEqual(record["validation"]["status"], "concept")
        self.assertEqual(report["step_roundtrip"]["status"], "passed")
        self.assertEqual(report["step_roundtrip"]["solid_count"], 1)
        self.assertEqual(report["step_roundtrip"]["envelope_mm"], [180.0, 70.0, 100.0])
        self.assertAlmostEqual(
            report["results"]["cad_volume_mm3"],
            report["step_roundtrip"]["volume_mm3"],
        )
        self.assertAlmostEqual(
            report["results"]["screening_mass_each_bank_g"], 461.0341661070729
        )
        self.assertEqual(patrick["quality"]["dimensional_accuracy"], "declared")
        self.assertEqual(porschefanatics["quality"]["evidence_level"], "C")
        self.assertGreaterEqual(len(report["release_blockers"]), 9)
        self.assertFalse(report["manufacturing_authorized"])
        self.assertFalse(report["engine_operation_authorized"])
        self.assertFalse(report["release_authorized"])


if __name__ == "__main__":
    unittest.main()
