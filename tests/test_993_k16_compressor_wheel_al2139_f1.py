import importlib.util
import json
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "parts/993-eng-k16-compressor-wheel-al2139-f1-0001/source/compressor_wheel_f1.py"
RECORD = ROOT / "catalog/parts/993-eng-k16-compressor-wheel-al2139-f1-0001.json"
REPORT = ROOT / "parts/993-eng-k16-compressor-wheel-al2139-f1-0001/evidence/engineering-screen.json"
F0_REPORT = ROOT / "parts/993-eng-k16-compressor-wheel-alsi10mg-f0-0001/evidence/engineering-screen.json"
EOS_SOURCE = ROOT / "catalog/sources/src-eos-al2139-am-m290-60um.json"
PF_SOURCE = ROOT / "catalog/sources/src-porschefanatics-993-k16-compressor-wheel-candidate.json"
SPEC = importlib.util.spec_from_file_location("compressor_wheel_f1", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class K16CompressorWheelAl2139F1Tests(unittest.TestCase):
    def test_iteration_recomputes_failed_f0_and_passes_only_ambient_screen(self) -> None:
        screen = MODULE.engineering_screen()
        results = screen["results"]

        self.assertEqual(screen["predecessor"]["part_id"], "993-ENG-K16-COMPRESSOR-WHEEL-ALSI10MG-F0-0001")
        self.assertAlmostEqual(screen["predecessor"]["f0_screen_ratio"], 0.6267715989202132)
        self.assertLess(results["f0_ambient_yield_to_overspeed_root_stress_ratio_recomputed"], 1.0)
        self.assertGreaterEqual(results["f1_ambient_yield_to_overspeed_root_stress_ratio"], 1.5)
        self.assertGreaterEqual(results["f1_ambient_yield_to_overspeed_disk_stress_ratio"], 1.5)
        self.assertGreaterEqual(results["f1_ambient_yield_to_constrained_thermal_ratio"], 1.5)
        self.assertTrue(results["ambient_analytical_screen_pass"])
        self.assertFalse(screen["manufacturing_authorized"])
        self.assertFalse(screen["turbo_operation_authorized"])
        self.assertFalse(screen["engine_operation_authorized"])
        self.assertFalse(screen["release_authorized"])

    def test_linear_taper_integrals_are_recomputed(self) -> None:
        omega = 0.9 * math.sqrt(1.4 * 287.05 * 330.0) / 0.03025
        main = MODULE.tapered_blade_screen(7.0, 11.0, 3.0, 0.8, 2840.0, omega)
        length_m = 0.03025 - 0.007
        root_m = 0.003
        tip_m = 0.0008
        plan_area = length_m * (root_m + tip_m) / 2.0
        volume_m3 = plan_area * 0.011
        radial_moment = length_m * (
            root_m * (0.007 + length_m / 2.0)
            + (tip_m - root_m) * (0.007 / 2.0 + length_m / 3.0)
        )
        mean_radius = radial_moment / plan_area
        mass = 2840.0 * volume_m3
        force = mass * omega**2 * mean_radius
        stress_mpa = 2.0 * force / (0.003 * 0.011) / 1.0e6

        self.assertAlmostEqual(main["volume_mm3"], volume_m3 * 1.0e9)
        self.assertAlmostEqual(main["mass_g"], mass * 1000.0)
        self.assertAlmostEqual(main["mean_radius_mm"], mean_radius * 1000.0)
        self.assertAlmostEqual(main["centrifugal_force_n"], force)
        self.assertAlmostEqual(main["root_stress_mpa"], stress_mpa)
        self.assertAlmostEqual(main["overspeed_root_stress_mpa"], stress_mpa * 1.2**2)

    def test_material_and_process_scope_is_explicit(self) -> None:
        material = MODULE.engineering_screen()["material_screen"]

        self.assertEqual(material["process_trl"], 3)
        self.assertEqual(material["density_kg_m3"], 2840.0)
        self.assertEqual(material["comparison_yield_strength_pa"], 460.0e6)
        self.assertEqual(material["comparison_ultimate_strength_pa"], 520.0e6)
        self.assertEqual(material["comparison_elongation_ratio"], 0.04)
        self.assertEqual(material["published_average_defect_fraction_range"], [0.002, 0.003])
        self.assertEqual(material["published_minimum_wall_mm"], 0.4)
        self.assertIn("no hot HCF", material["scope"])

    def test_flow_and_thermodynamics_preserve_f0_regression_point(self) -> None:
        results = MODULE.engineering_screen()["results"]
        sound_speed = math.sqrt(1.4 * 287.05 * 330.0)
        tip_speed = 0.9 * sound_speed
        bank_flow = 3.6 / 1000.0 * 5750.0 / 120.0 * 0.95 / 2.0
        area = math.pi / 4.0 * (0.0406**2 - 0.012**2)
        t2s = 330.0 * 1.8 ** ((1.4 - 1.0) / 1.4)
        t2 = 330.0 + (t2s - 330.0) / 0.72

        self.assertAlmostEqual(results["tip_speed_m_s"], tip_speed)
        self.assertAlmostEqual(results["bank_volume_flow_m3_s"], bank_flow)
        self.assertAlmostEqual(results["inducer_axial_velocity_m_s"], bank_flow / area)
        self.assertAlmostEqual(results["efficiency_adjusted_outlet_temperature_k"], t2)
        self.assertAlmostEqual(results["specific_compressor_work_j_kg"], 1005.0 * (t2 - 330.0))

    def test_committed_step_sources_and_catalogue_are_fail_closed(self) -> None:
        record = json.loads(RECORD.read_text(encoding="utf-8"))
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        f0 = json.loads(F0_REPORT.read_text(encoding="utf-8"))
        eos = json.loads(EOS_SOURCE.read_text(encoding="utf-8"))
        porschefanatics = json.loads(PF_SOURCE.read_text(encoding="utf-8"))

        self.assertEqual(record["classification"]["safety_class"], "prohibited_pending_engineering")
        self.assertEqual(record["manufacturing"]["preferred_process"], "LPBF")
        self.assertEqual(record["validation"]["status"], "concept")
        self.assertFalse(record["titanium"]["applicable"])
        self.assertEqual(report["step_roundtrip"]["status"], "passed")
        self.assertEqual(report["step_roundtrip"]["solid_count"], 1)
        self.assertEqual(report["step_roundtrip"]["cad_taper_segment_count_per_blade"], 4)
        self.assertEqual(report["step_roundtrip"]["main_blade_count"], 6)
        self.assertEqual(report["step_roundtrip"]["splitter_blade_count"], 6)
        for actual, expected in zip(report["step_roundtrip"]["envelope_mm"], [60.5, 60.5, 18.0]):
            self.assertAlmostEqual(actual, expected, places=5)
        self.assertAlmostEqual(report["results"]["cad_mass_g"], 38.49471833965529)
        self.assertAlmostEqual(f0["results"]["ambient_yield_to_overspeed_blade_root_stress_ratio"], 0.6267715989202134)
        self.assertEqual(eos["quality"]["evidence_level"], "B")
        self.assertEqual(porschefanatics["quality"]["evidence_level"], "C")
        self.assertGreaterEqual(len(report["release_blockers"]), 14)
        self.assertFalse(report["manufacturing_authorized"])
        self.assertFalse(report["turbo_operation_authorized"])
        self.assertFalse(report["engine_operation_authorized"])
        self.assertFalse(report["release_authorized"])


if __name__ == "__main__":
    unittest.main()
