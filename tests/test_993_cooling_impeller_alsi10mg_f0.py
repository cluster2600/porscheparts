import importlib.util
import json
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "parts/993-eng-cooling-impeller-alsi10mg-f0-0001/source/cooling_impeller.py"
RECORD = ROOT / "catalog/parts/993-eng-cooling-impeller-alsi10mg-f0-0001.json"
REPORT = ROOT / "parts/993-eng-cooling-impeller-alsi10mg-f0-0001/evidence/engineering-screen.json"
HOUSING_REPORT = ROOT / "parts/993-eng-fan-housing-alsi10mg-f0-0001/evidence/engineering-screen.json"
SOURCE_PATHS = (
    ROOT / "catalog/sources/src-porschefanatics-993-engine-cooling-impeller-candidate.json",
    ROOT / "catalog/sources/src-fvd-964-993-fan-wheel-dimensions.json",
    ROOT / "catalog/sources/src-porsche-poitiers-964-993-fan-wheel-mass.json",
    ROOT / "catalog/sources/src-partworks-964-993-fan-wheel-aluminium.json",
    ROOT / "catalog/sources/src-eos-alsi10mg-current-page.json",
)
SPEC = importlib.util.spec_from_file_location("cooling_impeller", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class CoolingImpellerAlSi10MgF0Tests(unittest.TestCase):
    def test_published_product_data_are_not_promoted_to_geometry(self) -> None:
        screen = MODULE.engineering_screen()
        published = screen["geometry_authority"]["published"]

        self.assertEqual(published["part_number"], "96410601531")
        self.assertEqual(published["fvd_commercial_envelope_mm"], [300.0, 300.0, 150.0])
        self.assertEqual(published["fvd_commercial_mass_kg"], 0.94)
        self.assertEqual(published["porsche_poitiers_commercial_mass_kg"], 0.948)
        self.assertGreaterEqual(len(screen["geometry_authority"]["hypotheses"]), 5)
        self.assertIn("commercial product envelope", screen["geometry_authority"]["not_claimed"])

    def test_previous_housing_f0_integration_fails_without_silent_adjustment(self) -> None:
        screen = MODULE.engineering_screen()
        housing = json.loads(HOUSING_REPORT.read_text(encoding="utf-8"))
        integration = screen["upstream_f0_integration"]
        results = screen["results"]

        self.assertEqual(integration["housing_part_id"], housing["part_id"])
        self.assertEqual(integration["housing_synthetic_throat_mm"], 252.0)
        self.assertEqual(integration["impeller_synthetic_outer_diameter_mm"], 280.0)
        self.assertAlmostEqual(results["housing_diametral_clearance_mm"], -28.0)
        self.assertAlmostEqual(results["housing_radial_clearance_mm"], -14.0)
        self.assertFalse(results["housing_fit_screen_pass"])
        self.assertFalse(results["preliminary_screen_pass"])

    def test_overspeed_blade_and_modal_algebra_are_recomputed(self) -> None:
        results = MODULE.engineering_screen()["results"]
        omega = 12_000.0 * 2.0 * math.pi / 60.0
        tip_speed = omega * 0.140
        hoop_stress_mpa = 2670.0 * tip_speed**2 / 1.0e6
        blade_mass = 0.102 * 0.007 * 0.020 * 2670.0
        blade_force = blade_mass * omega**2 * 0.0885

        self.assertAlmostEqual(results["overspeed_rpm"], 12_000.0)
        self.assertAlmostEqual(results["overspeed_tip_speed_m_s"], tip_speed)
        self.assertAlmostEqual(results["overspeed_rim_hoop_stress_mpa"], hoop_stress_mpa)
        self.assertAlmostEqual(results["single_blade_overspeed_centrifugal_force_n"], blade_force)
        self.assertAlmostEqual(results["blade_root_direct_stress_mpa"], blade_force / 140.0)
        self.assertTrue(results["overspeed_screen_pass"])
        self.assertTrue(results["blade_root_screen_pass"])
        self.assertTrue(results["modal_screen_pass"])
        self.assertGreater(results["overspeed_kinetic_energy_j"], 6000.0)

    def test_flow_target_and_thermal_failure_are_explicit(self) -> None:
        results = MODULE.engineering_screen()["results"]
        area = math.pi / 4.0 * (0.280**2 - 0.080**2)
        thermal_stress = 70.0e9 * 21.0e-6 * 130.0

        self.assertAlmostEqual(results["annular_flow_area_m2"], area)
        self.assertAlmostEqual(results["mean_axial_velocity_m_s"], 1.01 / area)
        self.assertAlmostEqual(results["synthetic_air_power_w"], 808.0)
        self.assertAlmostEqual(results["fully_constrained_thermal_stress_mpa"], thermal_stress / 1.0e6)
        self.assertLess(results["ambient_yield_to_constrained_thermal_ratio"], 1.5)
        self.assertFalse(results["thermal_screen_pass"])
        self.assertIn("not_computable", results["hcf_balance_aeroacoustics_and_containment_status"])

    def test_step_catalogue_sources_and_release_gates_are_consistent(self) -> None:
        record = json.loads(RECORD.read_text(encoding="utf-8"))
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        sources = [json.loads(path.read_text(encoding="utf-8")) for path in SOURCE_PATHS]

        self.assertEqual(record["classification"]["safety_class"], "prohibited_pending_engineering")
        self.assertEqual(record["manufacturing"]["preferred_process"], "undecided")
        self.assertEqual(record["validation"]["status"], "concept")
        self.assertFalse(record["titanium"]["applicable"])
        self.assertEqual(report["step_roundtrip"]["status"], "passed")
        self.assertEqual(report["step_roundtrip"]["solid_count"], 1)
        self.assertEqual(report["step_roundtrip"]["synthetic_blade_count"], 12)
        self.assertEqual(report["step_roundtrip"]["hub_bore_count"], 1)
        for actual, expected in zip(report["step_roundtrip"]["envelope_mm"], [280.0, 280.0, 30.0]):
            self.assertAlmostEqual(actual, expected, places=5)
        self.assertAlmostEqual(report["results"]["cad_mass_g"], 990.3868690132803)
        self.assertEqual([source["quality"]["evidence_level"] for source in sources], ["C", "C", "C", "C", "B"])
        self.assertGreaterEqual(len(report["release_blockers"]), 18)
        self.assertFalse(report["manufacturing_authorized"])
        self.assertFalse(report["engine_operation_authorized"])
        self.assertFalse(report["release_authorized"])


if __name__ == "__main__":
    unittest.main()
