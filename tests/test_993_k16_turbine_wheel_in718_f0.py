import importlib.util
import json
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "parts/993-eng-k16-turbine-wheel-in718-f0-0001/source/turbine_wheel.py"
RECORD = ROOT / "catalog/parts/993-eng-k16-turbine-wheel-in718-f0-0001.json"
REPORT = ROOT / "parts/993-eng-k16-turbine-wheel-in718-f0-0001/evidence/engineering-screen.json"
EOS_SOURCE = ROOT / "catalog/sources/src-eos-in718-api-m290-40um.json"
KINUGAWA_SOURCE = ROOT / "catalog/sources/src-kinugawa-k16-turbine-wheel-53161205000.json"
PF_SOURCE = ROOT / "catalog/sources/src-porschefanatics-993-k16-compressor-wheel-candidate.json"
TURBOMASTER_SOURCE = ROOT / "catalog/sources/src-turbomaster-993-k16-6735-parts.json"
SPEC = importlib.util.spec_from_file_location("turbine_wheel", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class K16TurbineWheelIN718F0Tests(unittest.TestCase):
    def test_published_identity_is_separated_from_f0_hypotheses(self) -> None:
        screen = MODULE.engineering_screen()
        published = screen["geometry_authority"]["published"]

        self.assertEqual(published["turbine_wheel_reference"], "5316-120-5000")
        self.assertEqual(published["right_turbo_reference"], "5316-988-6735")
        self.assertEqual(published["inducer_diameter_mm"], 54.96)
        self.assertEqual(published["exducer_diameter_mm"], 48.97)
        self.assertEqual(published["blade_count"], 12)
        self.assertEqual(published["tip_height_mm"], 9.4)
        self.assertEqual(published["shaft_diameter_mm"], 8.42)
        self.assertGreaterEqual(len(screen["geometry_authority"]["hypotheses"]), 5)
        self.assertIn("No Porsche", screen["geometry_authority"]["not_claimed"])

    def test_blade_and_disk_formulas_are_recomputed(self) -> None:
        screen = MODULE.engineering_screen()
        results = screen["results"]
        omega = results["derived_shaft_speed_rpm"] * 2.0 * math.pi / 60.0
        ro = 54.96 / 2000.0
        ri = 9.5 / 1000.0
        length = ro - ri
        root = 2.4 / 1000.0
        tip = 0.8 / 1000.0
        height = 9.4 / 1000.0
        area = length * (root + tip) / 2.0
        moment = length * (
            root * (ri + length / 2.0)
            + (tip - root) * (ri / 2.0 + length / 3.0)
        )
        mean_radius = moment / area
        mass = 8150.0 * area * height
        force = mass * omega**2 * mean_radius
        nominal_stress = 2.5 * force / (root * height)
        overspeed_stress = nominal_stress * 1.2**2
        disk_stress = (3.0 + 0.29) / 8.0 * 8150.0 * omega**2 * ro**2 * 1.2**2

        self.assertAlmostEqual(results["blade"]["mass_g"], mass * 1000.0)
        self.assertAlmostEqual(results["blade"]["centrifugal_force_n"], force)
        self.assertAlmostEqual(results["blade"]["overspeed_root_stress_mpa"], overspeed_stress / 1.0e6)
        self.assertAlmostEqual(results["overspeed_rotating_disk_stress_mpa"], disk_stress / 1.0e6)

    def test_hot_side_power_balance_and_failure_are_explicit(self) -> None:
        screen = MODULE.engineering_screen()
        results = screen["results"]

        self.assertAlmostEqual(results["derived_shaft_speed_rpm"], 103463.76445545294)
        self.assertAlmostEqual(results["turbine_power_required_w"], 13805.02025727882)
        self.assertAlmostEqual(results["turbine_expansion_ratio_required"], 1.4187168666161456)
        self.assertLess(results["ambient_yield_to_overspeed_blade_root_stress_ratio"], 1.5)
        self.assertGreater(results["ambient_yield_to_overspeed_disk_stress_ratio"], 1.5)
        self.assertLess(results["ambient_yield_to_constrained_gradient_ratio"], 1.5)
        self.assertFalse(results["temperature_envelope_pass"])
        self.assertFalse(results["ambient_mechanical_screen_pass"])
        self.assertFalse(results["preliminary_screen_pass"])
        self.assertIn("not_computable", results["creep_screen_status"])
        self.assertIn("not_computable", results["hcf_lcf_screen_status"])

    def test_material_scope_and_release_gates_are_fail_closed(self) -> None:
        screen = MODULE.engineering_screen()
        material = screen["material_screen"]

        self.assertEqual(material["process_trl"], 9)
        self.assertEqual(material["density_kg_m3"], 8150.0)
        self.assertEqual(material["ambient_vertical_yield_strength_pa"], 865.0e6)
        self.assertEqual(material["average_defect_fraction"], 0.0003)
        self.assertEqual(material["published_use_temperature_limit_c"], 700.0)
        self.assertIn("no K16 hot HCF", material["scope"])
        self.assertGreaterEqual(len(screen["release_blockers"]), 16)
        self.assertFalse(screen["manufacturing_authorized"])
        self.assertFalse(screen["turbo_operation_authorized"])
        self.assertFalse(screen["engine_operation_authorized"])
        self.assertFalse(screen["release_authorized"])

    def test_committed_step_catalogue_and_sources_are_consistent(self) -> None:
        record = json.loads(RECORD.read_text(encoding="utf-8"))
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        eos = json.loads(EOS_SOURCE.read_text(encoding="utf-8"))
        kinugawa = json.loads(KINUGAWA_SOURCE.read_text(encoding="utf-8"))
        porschefanatics = json.loads(PF_SOURCE.read_text(encoding="utf-8"))
        turbomaster = json.loads(TURBOMASTER_SOURCE.read_text(encoding="utf-8"))

        self.assertEqual(record["classification"]["safety_class"], "prohibited_pending_engineering")
        self.assertEqual(record["manufacturing"]["preferred_process"], "undecided")
        self.assertEqual(record["validation"]["status"], "concept")
        self.assertEqual(record["vehicle"]["porsche_part_numbers"], [])
        self.assertFalse(record["titanium"]["applicable"])
        self.assertEqual(report["step_roundtrip"]["status"], "passed")
        self.assertEqual(report["step_roundtrip"]["solid_count"], 1)
        self.assertEqual(report["step_roundtrip"]["blade_count"], 12)
        self.assertEqual(report["step_roundtrip"]["cad_taper_segment_count_per_blade"], 4)
        self.assertFalse(report["step_roundtrip"]["full_shaft_included"])
        for actual, expected in zip(report["step_roundtrip"]["envelope_mm"], [54.96, 54.96, 20.0]):
            self.assertAlmostEqual(actual, expected, places=5)
        self.assertEqual(eos["quality"]["evidence_level"], "B")
        self.assertEqual(kinugawa["quality"]["evidence_level"], "C")
        self.assertEqual(porschefanatics["quality"]["evidence_level"], "C")
        self.assertEqual(turbomaster["quality"]["evidence_level"], "C")


if __name__ == "__main__":
    unittest.main()
