import importlib.util
import json
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "parts/993-eng-turbo-oil-return-line-in625-f0-0001/source/turbo_oil_return_line.py"
RECORD = ROOT / "catalog/parts/993-eng-turbo-oil-return-line-in625-f0-0001.json"
REPORT = ROOT / "parts/993-eng-turbo-oil-return-line-in625-f0-0001/evidence/engineering-screen.json"
PATRICK_SOURCE = ROOT / "catalog/sources/src-patrickmotorsports-993-turbo-oil-return-pipes.json"
PF_SOURCE = ROOT / "catalog/sources/src-porschefanatics-993-turbo-oil-return-candidate.json"
EOS_SOURCE = ROOT / "catalog/sources/src-eos-in625-material-data.json"
SPEC = importlib.util.spec_from_file_location("turbo_oil_return_line", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class TurboOilReturnLineIN625F0Tests(unittest.TestCase):
    def test_catalogue_identity_is_separated_from_synthetic_geometry(self) -> None:
        screen = MODULE.engineering_screen()
        published = screen["geometry_authority"]["published"]

        self.assertEqual(published["product_reference"], "TUR 993 107 338 53 PMS")
        self.assertEqual(published["model_years"], [1996, 1997])
        self.assertEqual(published["set_content"], "left_and_right")
        self.assertIn("adjust", published["installation_note"])
        self.assertGreaterEqual(len(screen["geometry_authority"]["hypotheses"]), 5)
        self.assertIn("No Porsche", screen["geometry_authority"]["not_claimed"])

    def test_laminar_hydraulic_equations_are_recomputed(self) -> None:
        hydraulic = MODULE.hydraulic_screen()
        diameter = 0.0103
        flow = 2.0e-3 / 60.0
        area = math.pi * diameter**2 / 4.0
        velocity = flow / area
        reynolds = 850.0 * velocity * diameter / 0.015
        friction = 64.0 / reynolds
        dynamic_pressure = 850.0 * velocity**2 / 2.0
        total = (
            friction * 0.175 / diameter * dynamic_pressure
            + 4.0 * dynamic_pressure
            + 850.0 * 9.80665 * 0.09
        )

        self.assertEqual(hydraulic["flow_regime"], "laminar")
        self.assertAlmostEqual(hydraulic["mean_velocity_m_s"], velocity)
        self.assertAlmostEqual(hydraulic["reynolds"], reynolds)
        self.assertAlmostEqual(hydraulic["darcy_friction_factor"], friction)
        self.assertAlmostEqual(hydraulic["total_pressure_drop_pa"], total)
        self.assertGreater(hydraulic["pressure_drop_screen_ratio"], 1.5)

    def test_pressure_passes_but_full_thermal_restraint_fails(self) -> None:
        screen = MODULE.engineering_screen()
        results = screen["results"]
        hoop = 300000.0 * 0.0103 / (2.0 * 0.0012)
        axial = 300000.0 * 0.0103 / (4.0 * 0.0012)
        von_mises = math.sqrt(hoop**2 + axial**2 - hoop * axial)
        thermal = 204.0e9 * 13.7e-6 * 580.0

        self.assertAlmostEqual(results["pressure_von_mises_mpa"], von_mises / 1.0e6)
        self.assertAlmostEqual(results["fully_constrained_thermal_stress_mpa"], thermal / 1.0e6)
        self.assertGreater(results["ambient_yield_to_pressure_ratio"], 1.5)
        self.assertGreater(results["ambient_yield_to_combined_ratio"], 1.5)
        self.assertLess(results["ambient_yield_to_constrained_thermal_ratio"], 1.5)
        self.assertAlmostEqual(results["free_thermal_expansion_mm"], 1.39055)
        self.assertLess(results["maximum_restraint_fraction_for_1p5_margin"], 0.27)
        self.assertTrue(results["hydraulic_screen_pass"])
        self.assertTrue(results["pressure_mechanical_screen_pass"])
        self.assertFalse(results["thermal_constraint_screen_pass"])
        self.assertFalse(results["preliminary_screen_pass"])

    def test_dfam_conflict_and_release_gates_are_closed(self) -> None:
        screen = MODULE.engineering_screen()
        dfam = screen["dfam_screen"]

        self.assertTrue(dfam["open_internal_channel"])
        self.assertFalse(dfam["trapped_powder_volume"])
        self.assertFalse(dfam["internal_supports_allowed"])
        self.assertAlmostEqual(dfam["wall_to_process_minimum_ratio"], 3.0)
        self.assertIn("rigid LPBF", dfam["installation_adjustability_conflict"])
        self.assertGreaterEqual(len(screen["release_blockers"]), 15)
        self.assertFalse(screen["manufacturing_authorized"])
        self.assertFalse(screen["turbo_operation_authorized"])
        self.assertFalse(screen["engine_operation_authorized"])
        self.assertFalse(screen["release_authorized"])

    def test_committed_step_catalogue_and_sources_are_consistent(self) -> None:
        record = json.loads(RECORD.read_text(encoding="utf-8"))
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        patrick = json.loads(PATRICK_SOURCE.read_text(encoding="utf-8"))
        porschefanatics = json.loads(PF_SOURCE.read_text(encoding="utf-8"))
        eos = json.loads(EOS_SOURCE.read_text(encoding="utf-8"))

        self.assertEqual(record["classification"]["safety_class"], "prohibited_pending_engineering")
        self.assertEqual(record["manufacturing"]["preferred_process"], "undecided")
        self.assertEqual(record["validation"]["status"], "concept")
        self.assertEqual(record["vehicle"]["porsche_part_numbers"], [])
        self.assertFalse(record["titanium"]["applicable"])
        self.assertEqual(report["step_roundtrip"]["status"], "passed")
        self.assertEqual(report["step_roundtrip"]["solid_count"], 1)
        self.assertEqual(report["step_roundtrip"]["flange_count"], 2)
        self.assertEqual(report["step_roundtrip"]["bolt_bore_count"], 4)
        self.assertEqual(report["step_roundtrip"]["continuous_internal_passage_count"], 1)
        for actual, expected in zip(report["step_roundtrip"]["envelope_mm"], [140.0, 60.0, 94.0]):
            self.assertAlmostEqual(actual, expected, places=4)
        self.assertAlmostEqual(report["results"]["cad_mass_g"], 101.16068411230884)
        self.assertEqual(patrick["quality"]["evidence_level"], "C")
        self.assertEqual(porschefanatics["quality"]["evidence_level"], "C")
        self.assertEqual(eos["quality"]["evidence_level"], "B")


if __name__ == "__main__":
    unittest.main()
