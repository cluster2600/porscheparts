import importlib.util
import json
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "parts/993-eng-piston-cp1-gallery-f0-0001/source/piston.py"
RECORD = ROOT / "catalog/parts/993-eng-piston-cp1-gallery-f0-0001.json"
REPORT = ROOT / "parts/993-eng-piston-cp1-gallery-f0-0001/evidence/engineering-screen.json"
PF_SOURCE = ROOT / "catalog/sources/src-porschefanatics-993-additive-piston-precedent.json"
PORSCHE_SOURCE = ROOT / "catalog/sources/src-porsche-additive-piston-validation.json"
VELO_SOURCE = ROOT / "catalog/sources/src-velo3d-cp1-material-datasheet.json"
SPEC = importlib.util.spec_from_file_location("piston", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class PistonCp1GalleryF0Tests(unittest.TestCase):
    def test_published_facts_and_hypotheses_are_separate(self) -> None:
        report = MODULE.engineering_screen()
        published = report["geometry_authority"]["published"]

        self.assertEqual(published["m64_60_engine_bore_mm"], 100.0)
        self.assertEqual(published["m64_60_engine_stroke_mm"], 76.4)
        self.assertEqual(published["porsche_additive_piston_endurance_hours"], 200.0)
        self.assertIn("not Porsche 993", published["porsche_additive_scope"])
        self.assertGreaterEqual(len(report["geometry_authority"]["hypotheses"]), 6)
        self.assertIn("No Porsche", report["geometry_authority"]["not_claimed"])
        self.assertFalse(report["manufacturing_authorized"])
        self.assertFalse(report["engine_operation_authorized"])
        self.assertFalse(report["release_authorized"])

    def test_gas_inertia_and_pin_equations_are_recomputed(self) -> None:
        results = MODULE.engineering_screen()["results"]
        piston_area_mm2 = math.pi * 100.0**2 / 4.0
        omega = 2.0 * math.pi * 6720.0 / 60.0
        acceleration = 0.0764 / 2.0 * omega**2 * (1.0 + (0.0764 / 2.0) / 0.127)
        inertia_n = (500.0 + 140.0) / 1000.0 * acceleration
        gas_n = 12.0 * piston_area_mm2

        self.assertAlmostEqual(results["piston_area_mm2"], piston_area_mm2)
        self.assertAlmostEqual(results["synthetic_peak_gas_force_n"], gas_n)
        self.assertAlmostEqual(results["angular_speed_rad_s"], omega)
        self.assertAlmostEqual(results["synthetic_tdc_acceleration_m_s2"], acceleration)
        self.assertAlmostEqual(results["synthetic_tdc_acceleration_g"], acceleration / 9.80665)
        self.assertAlmostEqual(results["mean_piston_speed_m_s"], 2.0 * 0.0764 * 6720.0 / 60.0)
        self.assertAlmostEqual(results["rod_to_crank_ratio"], 0.127 / (0.0764 / 2.0))
        self.assertAlmostEqual(results["crank_to_rod_ratio"], (0.0764 / 2.0) / 0.127)
        self.assertAlmostEqual(results["documentary_displacement_per_cylinder_cm3"], piston_area_mm2 * 76.4 / 1000.0)
        self.assertAlmostEqual(results["documentary_six_cylinder_displacement_cm3"], 6.0 * piston_area_mm2 * 76.4 / 1000.0)
        self.assertAlmostEqual(results["synthetic_tensile_inertia_force_n"], inertia_n)
        self.assertAlmostEqual(results["conservative_pin_force_n"], gas_n + inertia_n)
        self.assertAlmostEqual(results["pin_projected_pressure_screen_mpa"], (gas_n + inertia_n) / (23.0 * 40.0))

    def test_crown_plate_equations_are_recomputed(self) -> None:
        results = MODULE.engineering_screen()["results"]
        factor = (3.0 + 0.33) / 8.0
        stress = factor * 12.0 * 41.0**2 / 5.5**2
        rigidity = 70_000.0 * 5.5**3 / (12.0 * (1.0 - 0.33**2))
        deflection = 12.0 * 41.0**4 / (64.0 * rigidity)

        self.assertAlmostEqual(results["crown_plate_factor"], factor)
        self.assertAlmostEqual(results["crown_bending_stress_screen_mpa"], stress)
        self.assertAlmostEqual(results["crown_plate_rigidity_n_mm"], rigidity)
        self.assertAlmostEqual(results["crown_center_deflection_screen_mm"], deflection)
        self.assertLess(results["ambient_yield_to_crown_stress_ratio"], 1.1)

    def test_gallery_flow_and_thermal_equations_are_recomputed(self) -> None:
        results = MODULE.engineering_screen()["results"]
        diameter_m = 0.007
        area_m2 = math.pi * (diameter_m / 2.0) ** 2
        length_m = 2.0 * math.pi * 0.034
        flow_m3_s = 2.0 / 1000.0 / 60.0
        velocity = flow_m3_s / area_m2
        reynolds = 850.0 * velocity * diameter_m / 0.010
        friction = 64.0 / reynolds
        loss = friction * length_m / diameter_m * 850.0 * velocity**2 / 2.0

        self.assertAlmostEqual(results["gallery_flow_area_m2"], area_m2)
        self.assertAlmostEqual(results["gallery_path_length_m"], length_m)
        self.assertAlmostEqual(results["oil_velocity_m_s"], velocity)
        self.assertAlmostEqual(results["oil_reynolds"], reynolds)
        self.assertAlmostEqual(results["darcy_friction_factor"], friction)
        self.assertAlmostEqual(results["gallery_pressure_loss_pa"], loss)
        self.assertAlmostEqual(results["oil_temperature_rise_for_5kw_k"], 5000.0 / ((flow_m3_s * 850.0) * 2000.0))
        self.assertAlmostEqual(results["free_outer_diameter_growth_mm"], 23.0e-6 * 99.0 * 200.0)
        self.assertAlmostEqual(results["load_cycles_at_duty"], 6720.0 / 60.0 * 100.0 * 3600.0)
        self.assertAlmostEqual(results["shaft_revolutions_at_duty"], 40_320_000.0)
        self.assertAlmostEqual(results["combustion_events_per_cylinder_at_duty"], 20_160_000.0)
        self.assertAlmostEqual(results["porsche_200h_max_speed_equivalent_revolutions"], 80_640_000.0)
        self.assertAlmostEqual(results["porsche_200h_max_speed_equivalent_combustion_events_per_cylinder"], 40_320_000.0)

    def test_committed_step_sources_and_catalogue_stay_fail_closed(self) -> None:
        record = json.loads(RECORD.read_text(encoding="utf-8"))
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        porschefanatics = json.loads(PF_SOURCE.read_text(encoding="utf-8"))
        porsche = json.loads(PORSCHE_SOURCE.read_text(encoding="utf-8"))
        velo = json.loads(VELO_SOURCE.read_text(encoding="utf-8"))

        self.assertEqual(record["classification"]["safety_class"], "prohibited_pending_engineering")
        self.assertEqual(record["manufacturing"]["preferred_process"], "LPBF")
        self.assertFalse(record["titanium"]["applicable"])
        self.assertEqual(record["validation"]["status"], "concept")
        self.assertEqual(report["step_roundtrip"]["status"], "passed")
        self.assertEqual(report["step_roundtrip"]["solid_count"], 1)
        self.assertEqual(report["step_roundtrip"]["powder_port_count"], 2)
        for actual, expected in zip(report["step_roundtrip"]["envelope_mm"], [99.0, 99.0, 70.0]):
            self.assertAlmostEqual(actual, expected, places=5)
        self.assertAlmostEqual(report["results"]["cad_mass_g"], 681.3184433418205)
        self.assertEqual(porschefanatics["quality"]["evidence_level"], "C")
        self.assertEqual(porsche["quality"]["evidence_level"], "A")
        self.assertEqual(velo["quality"]["evidence_level"], "B")
        self.assertGreaterEqual(len(report["release_blockers"]), 12)
        self.assertFalse(report["manufacturing_authorized"])
        self.assertFalse(report["engine_operation_authorized"])
        self.assertFalse(report["release_authorized"])


if __name__ == "__main__":
    unittest.main()
