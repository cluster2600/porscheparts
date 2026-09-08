import importlib.util
import json
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "parts/993-eng-oil-filter-console-alsi10mg-f0-0001/source/oil_filter_console.py"
RECORD = ROOT / "catalog/parts/993-eng-oil-filter-console-alsi10mg-f0-0001.json"
REPORT = ROOT / "parts/993-eng-oil-filter-console-alsi10mg-f0-0001/evidence/engineering-screen.json"
PF_SOURCE = ROOT / "catalog/sources/src-porschefanatics-993-oil-filter-console-candidate.json"
MASS_SOURCE = ROOT / "catalog/sources/src-oemvwshop-993-oil-filter-console-mass.json"
FILTER_SOURCE = ROOT / "catalog/sources/src-mahleretail-oc229-993-filter-interface.json"
ARCHITECTURE_SOURCE = ROOT / "catalog/sources/src-islandworks-integrated-oil-console-6061.json"
EOS_SOURCE = ROOT / "catalog/sources/src-eos-alsi10mg-current-page.json"
SPEC = importlib.util.spec_from_file_location("oil_filter_console", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class OilFilterConsoleAlSi10MgF0Tests(unittest.TestCase):
    def test_published_filter_and_mass_do_not_define_console_geometry(self) -> None:
        screen = MODULE.engineering_screen()
        published = screen["geometry_authority"]["published"]

        self.assertEqual(published["console_part_numbers"], ["99310705700", "99310705701"])
        self.assertEqual(published["console_commercial_mass_kg"], 0.78)
        self.assertEqual(published["filter_thread"], "M20x1.5")
        self.assertEqual(published["filter_diameter_mm"], 76.0)
        self.assertEqual(published["filter_height_mm"], 101.0)
        self.assertEqual(published["oil_pressure_bar_ocr_unverified"], 6.5)
        self.assertGreaterEqual(len(screen["geometry_authority"]["hypotheses"]), 6)
        self.assertIn("neither defines", screen["geometry_authority"]["not_claimed"])

    def test_hot_and_cold_hydraulics_are_recomputed_and_fail_closed(self) -> None:
        screen = MODULE.engineering_screen()
        results = screen["results"]
        hot = results["hot_hydraulic"]
        cold = results["cold_hydraulic"]

        self.assertAlmostEqual(hot["flow_m3_s"], 0.0005)
        self.assertEqual(len(hot["segments"]), 3)
        self.assertAlmostEqual(hot["total_pressure_loss_pa"], 28824.592158200452)
        self.assertAlmostEqual(cold["total_pressure_loss_pa"], 44650.11767181784)
        self.assertAlmostEqual(results["pressure_loss_limit_pa"], 32500.0)
        self.assertGreater(results["hot_pressure_loss_allowance_ratio"], 1.0)
        self.assertLess(results["cold_pressure_loss_allowance_ratio"], 1.0)
        self.assertTrue(results["hot_hydraulic_pass"])
        self.assertFalse(results["cold_hydraulic_pass"])
        self.assertFalse(results["preliminary_screen_pass"])

    def test_pressure_filter_and_thermal_screens_are_recomputed(self) -> None:
        results = MODULE.engineering_screen()["results"]
        wall_stress_mpa = 1.2e6 * 0.016 / (2.0 * 0.004) / 1.0e6
        preload_n = 20.0 / (0.20 * 0.020)
        seal_area_mm2 = math.pi / 4.0 * (72.0**2 - 62.0**2)
        thread_area_mm2 = math.pi * 20.0 * 12.0 * 0.5
        thermal_stress_mpa = 70.0e9 * 21.0e-6 * 130.0 / 1.0e6

        self.assertAlmostEqual(results["channel_wall_stress_mpa_at_proof"], wall_stress_mpa)
        self.assertAlmostEqual(results["filter_preload_n_from_published_torque"], preload_n)
        self.assertAlmostEqual(results["synthetic_filter_seal_area_mm2"], seal_area_mm2)
        self.assertAlmostEqual(results["thread_shear_area_mm2"], thread_area_mm2)
        self.assertGreater(results["ambient_yield_to_channel_wall_ratio"], 1.5)
        self.assertGreater(results["ambient_yield_to_thread_von_mises_ratio"], 1.5)
        self.assertTrue(results["filter_interface_pass"])
        self.assertAlmostEqual(results["fully_constrained_thermal_stress_mpa"], thermal_stress_mpa)
        self.assertLess(results["ambient_yield_to_constrained_thermal_ratio"], 1.5)
        self.assertFalse(results["thermal_screen_pass"])
        self.assertIn("not_computable", results["fatigue_seal_and_cleanliness_status"])

    def test_dfam_value_and_release_gates_are_explicit(self) -> None:
        screen = MODULE.engineering_screen()
        dfam = screen["dfam_screen"]

        self.assertEqual(dfam["integrated_gallery_count"], 2)
        self.assertEqual(dfam["gallery_opening_count"], 4)
        self.assertFalse(dfam["trapped_powder_volume"])
        self.assertFalse(dfam["powder_removal_validated"])
        self.assertTrue(dfam["filter_spigot_is_unthreaded_machining_stock"])
        self.assertAlmostEqual(dfam["wall_to_process_minimum_ratio"], 10.0)
        self.assertGreaterEqual(len(screen["release_blockers"]), 16)
        self.assertFalse(screen["manufacturing_authorized"])
        self.assertFalse(screen["engine_operation_authorized"])
        self.assertFalse(screen["release_authorized"])

    def test_committed_step_catalogue_and_sources_are_consistent(self) -> None:
        record = json.loads(RECORD.read_text(encoding="utf-8"))
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        porschefanatics = json.loads(PF_SOURCE.read_text(encoding="utf-8"))
        mass_source = json.loads(MASS_SOURCE.read_text(encoding="utf-8"))
        filter_source = json.loads(FILTER_SOURCE.read_text(encoding="utf-8"))
        architecture = json.loads(ARCHITECTURE_SOURCE.read_text(encoding="utf-8"))
        eos = json.loads(EOS_SOURCE.read_text(encoding="utf-8"))

        self.assertEqual(record["classification"]["safety_class"], "prohibited_pending_engineering")
        self.assertEqual(record["manufacturing"]["preferred_process"], "undecided")
        self.assertEqual(record["validation"]["status"], "concept")
        self.assertFalse(record["titanium"]["applicable"])
        self.assertEqual(report["step_roundtrip"]["status"], "passed")
        self.assertEqual(report["step_roundtrip"]["solid_count"], 1)
        self.assertEqual(report["step_roundtrip"]["integrated_gallery_count"], 2)
        self.assertEqual(report["step_roundtrip"]["mount_bore_count"], 4)
        for actual, expected in zip(report["step_roundtrip"]["envelope_mm"], [144.0, 90.0, 50.0]):
            self.assertAlmostEqual(actual, expected, places=4)
        self.assertAlmostEqual(report["results"]["cad_mass_g"], 840.3435078269009)
        self.assertEqual(porschefanatics["quality"]["evidence_level"], "C")
        self.assertEqual(mass_source["quality"]["evidence_level"], "C")
        self.assertEqual(filter_source["quality"]["evidence_level"], "C")
        self.assertEqual(architecture["quality"]["evidence_level"], "C")
        self.assertEqual(eos["quality"]["evidence_level"], "B")


if __name__ == "__main__":
    unittest.main()
