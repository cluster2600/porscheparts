import importlib.util
import json
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "parts/993-eng-connecting-rod-ti64-f0-0001/source/connecting_rod.py"
RECORD = ROOT / "catalog/parts/993-eng-connecting-rod-ti64-f0-0001.json"
REPORT = ROOT / "parts/993-eng-connecting-rod-ti64-f0-0001/evidence/engineering-screen.json"
TZR_SOURCE = ROOT / "catalog/sources/src-tzr-pauter-993-connecting-rod-dimensions.json"
PF_SOURCE = ROOT / "catalog/sources/src-porschefanatics-993-titanium-connecting-rods.json"
EOS_SOURCE = ROOT / "catalog/sources/src-eos-ti64-grade5.json"
SPEC = importlib.util.spec_from_file_location("connecting_rod", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ConnectingRodTi64F0Tests(unittest.TestCase):
    def test_published_facts_and_hypotheses_are_separate(self) -> None:
        report = MODULE.engineering_screen()
        published = report["geometry_authority"]["published"]

        self.assertEqual(published["center_distance_mm"], 127.0)
        self.assertEqual(published["big_end_housing_diameter_mm"], 58.01)
        self.assertEqual(published["piston_pin_diameter_mm"], 23.01)
        self.assertEqual(published["steel_mass_g"], 535.0)
        self.assertGreaterEqual(len(report["geometry_authority"]["hypotheses"]), 5)
        self.assertIn("No PAUTER surface", report["geometry_authority"]["not_claimed"])
        self.assertFalse(report["manufacturing_authorized"])
        self.assertFalse(report["engine_operation_authorized"])
        self.assertFalse(report["release_authorized"])

    def test_mass_gas_and_inertia_equations_are_recomputed(self) -> None:
        results = MODULE.engineering_screen()["results"]
        target_mass_g = 535.0 * (1.0 - 0.33)
        area_m2 = math.pi * (0.100 / 2.0) ** 2
        omega = 2.0 * math.pi * 6720.0 / 60.0
        acceleration = 0.0764 / 2.0 * omega**2 * (1.0 + (0.0764 / 2.0) / 0.127)
        reciprocating_mass_kg = (600.0 + target_mass_g / 3.0) / 1000.0
        inertia_n = reciprocating_mass_kg * acceleration
        gas_n = 12.0e6 * area_m2

        self.assertAlmostEqual(results["published_titanium_target_mass_g"], target_mass_g)
        self.assertAlmostEqual(results["piston_area_m2"], area_m2)
        self.assertAlmostEqual(results["angular_speed_rad_s"], omega)
        self.assertAlmostEqual(results["synthetic_tdc_acceleration_m_s2"], acceleration)
        self.assertAlmostEqual(results["synthetic_reciprocating_mass_kg"], reciprocating_mass_kg)
        self.assertAlmostEqual(results["synthetic_tensile_inertia_force_n"], inertia_n)
        self.assertAlmostEqual(results["synthetic_peak_gas_force_n"], gas_n)
        self.assertAlmostEqual(results["conservative_compression_force_n"], gas_n + inertia_n)

    def test_stress_buckling_cycles_and_thermal_equations_are_recomputed(self) -> None:
        results = MODULE.engineering_screen()["results"]
        compression_n = results["conservative_compression_force_n"]
        inertia_n = results["synthetic_tensile_inertia_force_n"]
        area_mm2 = 2.0 * 10.0 * 14.0
        inertia_m4 = 2.0 * 0.010 * 0.014**3 / 12.0
        strut_length_m = math.hypot(110.0 - 25.0, 20.0 + 10.0) / 1000.0
        euler_n = math.pi**2 * 110.0e9 * inertia_m4 / strut_length_m**2

        self.assertAlmostEqual(results["local_compression_screen_mpa"], 1.5 * compression_n / area_mm2)
        self.assertAlmostEqual(results["local_tension_screen_mpa"], 1.5 * inertia_n / area_mm2)
        self.assertAlmostEqual(results["combined_weak_axis_i_m4"], inertia_m4)
        self.assertAlmostEqual(results["euler_buckling_load_n"], euler_n)
        self.assertAlmostEqual(results["euler_to_compression_load_ratio"], euler_n / compression_n)
        self.assertAlmostEqual(results["load_cycles_at_duty"], 6720.0 / 60.0 * 100.0 * 3600.0)
        self.assertAlmostEqual(results["free_center_distance_thermal_expansion_mm"], 9.0e-6 * 127.0 * 100.0)

    def test_committed_step_sources_and_catalogue_stay_fail_closed(self) -> None:
        record = json.loads(RECORD.read_text(encoding="utf-8"))
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        tzr = json.loads(TZR_SOURCE.read_text(encoding="utf-8"))
        porschefanatics = json.loads(PF_SOURCE.read_text(encoding="utf-8"))
        eos = json.loads(EOS_SOURCE.read_text(encoding="utf-8"))

        self.assertEqual(record["classification"]["safety_class"], "prohibited_pending_engineering")
        self.assertEqual(record["manufacturing"]["preferred_process"], "LPBF")
        self.assertTrue(record["titanium"]["applicable"])
        self.assertEqual(record["titanium"]["hip_required"], "to_be_determined")
        self.assertEqual(record["validation"]["status"], "concept")
        self.assertEqual(report["step_roundtrip"]["status"], "passed")
        self.assertEqual(report["step_roundtrip"]["solid_count"], 2)
        for actual, expected in zip(report["step_roundtrip"]["envelope_mm"], [186.0, 84.0, 19.58]):
            self.assertAlmostEqual(actual, expected, places=5)
        self.assertAlmostEqual(report["results"]["cad_mass_g"], 341.0236949267339)
        self.assertEqual(tzr["quality"]["dimensional_accuracy"], "declared")
        self.assertEqual(porschefanatics["quality"]["evidence_level"], "C")
        self.assertEqual(eos["quality"]["evidence_level"], "B")
        self.assertGreaterEqual(len(report["release_blockers"]), 10)
        self.assertFalse(report["manufacturing_authorized"])
        self.assertFalse(report["engine_operation_authorized"])
        self.assertFalse(report["release_authorized"])


if __name__ == "__main__":
    unittest.main()
