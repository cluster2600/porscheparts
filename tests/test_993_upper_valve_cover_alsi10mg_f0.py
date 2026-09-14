import importlib.util
import json
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "parts/993-eng-upper-valve-cover-alsi10mg-f0-0001/source/upper_valve_cover.py"
RECORD = ROOT / "catalog/parts/993-eng-upper-valve-cover-alsi10mg-f0-0001.json"
REPORT = ROOT / "parts/993-eng-upper-valve-cover-alsi10mg-f0-0001/evidence/engineering-screen.json"
FVD_SOURCE = ROOT / "catalog/sources/src-fvd-993-billet-valve-cover-set.json"
PROTOMOTIVE_SOURCE = ROOT / "catalog/sources/src-protomotive-993-upper-valve-cover-6061.json"
PF_SOURCE = ROOT / "catalog/sources/src-porschefanatics-993-valve-cover-candidate.json"
EOS_SOURCE = ROOT / "catalog/sources/src-eos-alsi10mg-current-page.json"
SPEC = importlib.util.spec_from_file_location("upper_valve_cover", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class UpperValveCoverAlSi10MgF0Tests(unittest.TestCase):
    def test_published_kit_is_not_promoted_to_individual_geometry(self) -> None:
        screen = MODULE.engineering_screen()
        published = screen["geometry_authority"]["published"]

        self.assertEqual(published["fvd_complete_kit_envelope_mm"], [400.0, 150.0, 200.0])
        self.assertEqual(published["fvd_complete_kit_mass_kg"], 3.32)
        self.assertEqual(published["protomotive_alternative_material"], "6061-T6_billet_aluminium")
        self.assertEqual(published["torque_nm_ocr_unverified"], 9.7)
        self.assertGreaterEqual(len(screen["geometry_authority"]["hypotheses"]), 5)
        self.assertIn("complete commercial kit", screen["geometry_authority"]["not_claimed"])

    def test_pressure_and_clamp_screens_are_recomputed(self) -> None:
        results = MODULE.engineering_screen()["results"]
        plate_stress = 0.75 * 0.02 * 45.0**2 / 3.0**2
        preload = 9.7 / (0.20 * 0.006)
        gasket_area = 220.0 * 95.0 - 208.0 * 83.0
        gasket_pressure = preload * 10.0 / gasket_area
        local_i = 30.0 * 6.0**3 / 12.0
        local_stress = (preload * 6.0 / 2.0) * 3.0 / local_i

        self.assertAlmostEqual(results["roof_plate_stress_mpa"], plate_stress)
        self.assertAlmostEqual(results["per_bolt_preload_n_from_unverified_torque"], preload)
        self.assertAlmostEqual(results["average_gasket_pressure_mpa"], gasket_pressure)
        self.assertAlmostEqual(results["local_flange_stress_mpa"], local_stress)
        self.assertGreater(results["ambient_yield_to_roof_pressure_ratio"], 1.5)
        self.assertGreater(results["ambient_yield_to_local_flange_stress_ratio"], 1.5)
        self.assertTrue(results["pressure_screen_pass"])
        self.assertTrue(results["clamp_screen_pass"])

    def test_three_thermal_screens_fail_closed(self) -> None:
        results = MODULE.engineering_screen()["results"]
        thermal_stress = 70.0e9 * 21.0e-6 * 180.0
        curvature = 21.0e-6 * 50.0 / 0.003
        bow_mm = curvature * 0.220**2 / 8.0 * 1000.0

        self.assertAlmostEqual(results["fully_constrained_thermal_stress_mpa"], thermal_stress / 1.0e6)
        self.assertAlmostEqual(results["thermal_gradient_curvature_per_m"], curvature)
        self.assertAlmostEqual(results["thermal_bow_mm"], bow_mm)
        self.assertLess(results["ambient_yield_to_constrained_thermal_ratio"], 1.5)
        self.assertLess(results["seal_bow_allowance_to_prediction_ratio"], 1.0)
        self.assertLess(results["convection_capacity_to_target_ratio"], 1.0)
        self.assertFalse(results["thermal_screen_pass"])
        self.assertFalse(results["preliminary_screen_pass"])
        self.assertIn("not_computable", results["fatigue_and_seal_life_status"])

    def test_dfam_value_and_release_gates_are_explicit(self) -> None:
        screen = MODULE.engineering_screen()
        dfam = screen["dfam_screen"]

        self.assertTrue(dfam["open_oil_side"])
        self.assertFalse(dfam["trapped_powder_volume"])
        self.assertEqual(dfam["integrated_cop_tower_count"], 3)
        self.assertEqual(dfam["integrated_fin_count"], 6)
        self.assertAlmostEqual(dfam["roof_to_process_minimum_ratio"], 7.5)
        self.assertGreaterEqual(len(screen["release_blockers"]), 15)
        self.assertFalse(screen["manufacturing_authorized"])
        self.assertFalse(screen["engine_operation_authorized"])
        self.assertFalse(screen["release_authorized"])

    def test_committed_step_catalogue_and_sources_are_consistent(self) -> None:
        record = json.loads(RECORD.read_text(encoding="utf-8"))
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        fvd = json.loads(FVD_SOURCE.read_text(encoding="utf-8"))
        protomotive = json.loads(PROTOMOTIVE_SOURCE.read_text(encoding="utf-8"))
        porschefanatics = json.loads(PF_SOURCE.read_text(encoding="utf-8"))
        eos = json.loads(EOS_SOURCE.read_text(encoding="utf-8"))

        self.assertEqual(record["classification"]["safety_class"], "prohibited_pending_engineering")
        self.assertEqual(record["manufacturing"]["preferred_process"], "undecided")
        self.assertEqual(record["validation"]["status"], "concept")
        self.assertEqual(record["vehicle"]["porsche_part_numbers"], [])
        self.assertFalse(record["titanium"]["applicable"])
        self.assertEqual(report["step_roundtrip"]["status"], "passed")
        self.assertEqual(report["step_roundtrip"]["solid_count"], 1)
        self.assertEqual(report["step_roundtrip"]["bolt_bore_count"], 10)
        self.assertEqual(report["step_roundtrip"]["cop_tower_count"], 3)
        self.assertEqual(report["step_roundtrip"]["external_fin_count"], 6)
        for actual, expected in zip(report["step_roundtrip"]["envelope_mm"], [220.0, 95.0, 45.0]):
            self.assertAlmostEqual(actual, expected, places=5)
        self.assertAlmostEqual(report["results"]["cad_mass_g"], 483.6529492283003)
        self.assertEqual(fvd["quality"]["evidence_level"], "C")
        self.assertEqual(protomotive["quality"]["evidence_level"], "C")
        self.assertEqual(porschefanatics["quality"]["evidence_level"], "C")
        self.assertEqual(eos["quality"]["evidence_level"], "B")


if __name__ == "__main__":
    unittest.main()
