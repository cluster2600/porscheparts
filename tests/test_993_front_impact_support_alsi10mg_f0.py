import importlib.util
import json
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "parts/993-body-front-impact-support-alsi10mg-f0-0001/source/front_impact_support.py"
RECORD = ROOT / "catalog/parts/993-body-front-impact-support-alsi10mg-f0-0001.json"
REPORT = ROOT / "parts/993-body-front-impact-support-alsi10mg-f0-0001/evidence/engineering-screen.json"
FVD_SOURCE = ROOT / "catalog/sources/src-fvd-993-front-impact-tube-dimensions.json"
PF_SOURCE = ROOT / "catalog/sources/src-porschefanatics-993-lightweight-bumper-support.json"
SPEC = importlib.util.spec_from_file_location("front_impact_support", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class FrontImpactSupportAlSi10MgF0Tests(unittest.TestCase):
    def test_published_data_and_clean_sheet_hypotheses_are_separate(self) -> None:
        report = MODULE.engineering_screen()
        authority = report["geometry_authority"]
        self.assertEqual(
            authority["published"],
            [
                "commercial product envelope 139 x 100 x 53 mm",
                "commercial product mass 145 g",
                "commercial material family aluminium, alloy not disclosed",
            ],
        )
        self.assertEqual(authority["catalogue_identity"], ["FVD50501700"])
        self.assertGreaterEqual(len(authority["hypotheses"]), 6)
        self.assertIn("No Porsche or FVD surface", authority["not_claimed"])
        self.assertFalse(report["manufacturing_authorized"])
        self.assertFalse(report["release_authorized"])

    def test_mass_section_and_nominal_strength_are_recomputed(self) -> None:
        results = MODULE.engineering_screen()["results"]
        shell_area = math.pi * (30.0 * 19.0 - 28.8 * 17.8)
        front_core_area = 57.6 * 0.8 + 35.6 * 0.8 - 0.8**2
        minimum_area = shell_area + front_core_area

        self.assertAlmostEqual(results["shell_annulus_area_mm2"], shell_area)
        self.assertAlmostEqual(results["front_core_area_mm2"], front_core_area)
        self.assertAlmostEqual(results["minimum_section_area_mm2"], minimum_area)
        self.assertAlmostEqual(
            results["nominal_axial_stress_mpa"], 15_000.0 / minimum_area
        )
        self.assertAlmostEqual(
            results["yield_force_upper_bound_n"], minimum_area * 245.0
        )
        self.assertGreater(results["ambient_yield_ratio"], 1.0)

    def test_energy_buckling_modal_and_thermal_screens_are_recomputed(self) -> None:
        results = MODULE.engineering_screen()["results"]
        energy_each = 15_000.0 * 80.0 / 1000.0
        equivalent_speed = math.sqrt(2.0 * 2.0 * energy_each / 1450.0) * 3.6

        self.assertAlmostEqual(results["synthetic_energy_each_j"], energy_each)
        self.assertAlmostEqual(
            results["synthetic_equivalent_vehicle_speed_km_h"], equivalent_speed
        )
        self.assertLess(
            results["front_web_flat_plate_buckling_stress_mpa"], 245.0
        )
        self.assertGreater(results["global_euler_force_n"], 15_000.0)
        self.assertGreater(results["cantilever_shell_first_bending_mode_hz"], 0.0)
        self.assertAlmostEqual(
            results["free_thermal_expansion_mm"], 21.0e-6 * 139.0 * 100.0
        )

    def test_committed_step_and_catalogue_stay_fail_closed(self) -> None:
        record = json.loads(RECORD.read_text(encoding="utf-8"))
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        fvd = json.loads(FVD_SOURCE.read_text(encoding="utf-8"))
        porschefanatics = json.loads(PF_SOURCE.read_text(encoding="utf-8"))

        self.assertEqual(
            record["classification"]["safety_class"],
            "prohibited_pending_engineering",
        )
        self.assertEqual(record["manufacturing"]["preferred_process"], "undecided")
        self.assertIn("sheet_metal", record["manufacturing"]["candidate_processes"])
        self.assertIn("LPBF", record["manufacturing"]["candidate_processes"])
        self.assertEqual(record["validation"]["status"], "concept")
        self.assertEqual(report["step_roundtrip"]["status"], "passed")
        self.assertEqual(report["step_roundtrip"]["solid_count"], 1)
        self.assertEqual(report["step_roundtrip"]["envelope_mm"], [139.0, 100.0, 53.0])
        self.assertAlmostEqual(
            report["results"]["cad_volume_mm3"],
            report["step_roundtrip"]["volume_mm3"],
        )
        self.assertAlmostEqual(report["results"]["screening_mass_g"], 144.65230527565333)
        self.assertEqual(fvd["quality"]["dimensional_accuracy"], "declared")
        self.assertEqual(porschefanatics["quality"]["evidence_level"], "C")
        self.assertGreaterEqual(len(report["release_blockers"]), 11)
        self.assertFalse(report["manufacturing_authorized"])
        self.assertFalse(report["release_authorized"])


if __name__ == "__main__":
    unittest.main()
