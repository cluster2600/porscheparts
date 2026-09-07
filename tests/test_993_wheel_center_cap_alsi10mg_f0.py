import importlib.util
import json
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "parts/993-whl-center-cap-alsi10mg-f0-0001/source/wheel_center_cap.py"
RECORD = ROOT / "catalog/parts/993-whl-center-cap-alsi10mg-f0-0001.json"
REPORT = ROOT / "parts/993-whl-center-cap-alsi10mg-f0-0001/evidence/engineering-screen.json"
PF_SOURCE = ROOT / "catalog/sources/src-porschefanatics-993-wheel-center-cap-status.json"
SPEC = importlib.util.spec_from_file_location("wheel_center_cap", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class WheelCenterCapAlSi10MgF0Tests(unittest.TestCase):
    def test_published_geometry_and_clean_sheet_interfaces_are_separate(self) -> None:
        report = MODULE.engineering_screen()
        self.assertEqual(report["geometry_authority"]["catalogue_identity"], ["99336130307"])
        self.assertEqual(
            report["geometry_authority"]["published"],
            [
                "commercial outer diameter 76 mm",
                "commercial inner diameter 60 mm",
                "commercial overall height 46 mm",
                "commercial original material plastic",
            ],
        )
        self.assertGreaterEqual(len(report["geometry_authority"]["hypotheses"]), 4)
        self.assertFalse(report["release_authorized"])

    def test_retention_rotation_and_thermal_equations_are_recomputed(self) -> None:
        delta = 0.4
        results = MODULE.engineering_screen(delta)["results"]
        inertia = 8.0 * 2.0**3 / 12.0
        tab_force = 3.0 * 70_000.0 * inertia * delta / 30.0**3
        mass_g = MODULE.analytic_volume_mm3() / 1000.0 * 2.67

        self.assertAlmostEqual(results["analytic_volume_mm3"], MODULE.analytic_volume_mm3())
        self.assertAlmostEqual(results["screening_mass_each_g"], mass_g)
        self.assertAlmostEqual(results["insertion_force_each_tab_n"], tab_force)
        self.assertAlmostEqual(results["insertion_root_stress_mpa"], tab_force * 30.0 / inertia)
        self.assertAlmostEqual(results["friction_retention_capacity_n"], 4.0 * 0.30 * tab_force)
        omega = (250.0 / 3.6) / 0.315
        self.assertAlmostEqual(results["wheel_angular_speed_rad_s"], omega)
        self.assertAlmostEqual(
            results["aluminium_minus_steel_diametral_growth_mm"],
            (21.0e-6 - 12.0e-6) * 60.0 * 120.0,
        )
        self.assertGreater(results["friction_retention_ratio"], 1.0)

    def test_insertion_results_scale_linearly_with_deflection(self) -> None:
        low = MODULE.engineering_screen(0.1)["results"]
        high = MODULE.engineering_screen(0.4)["results"]
        for key in (
            "insertion_force_each_tab_n",
            "insertion_root_stress_mpa",
            "friction_retention_capacity_n",
            "friction_retention_ratio",
        ):
            self.assertAlmostEqual(high[key], 4.0 * low[key])

    def test_committed_artifacts_keep_process_and_release_undecided(self) -> None:
        record = json.loads(RECORD.read_text(encoding="utf-8"))
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        source = json.loads(PF_SOURCE.read_text(encoding="utf-8"))

        self.assertEqual(record["manufacturing"]["preferred_process"], "undecided")
        self.assertIn("LPBF", record["manufacturing"]["candidate_processes"])
        self.assertIn("MJF", record["manufacturing"]["candidate_processes"])
        self.assertEqual(record["validation"]["status"], "concept")
        self.assertNotIn("Porsche crest", record["description"])
        self.assertEqual(report["step_roundtrip"]["status"], "passed")
        self.assertEqual(report["step_roundtrip"]["solid_count"], 1)
        self.assertEqual(report["step_roundtrip"]["envelope_mm"], [76.0, 76.0, 46.0])
        self.assertEqual(source["quality"]["dimensional_accuracy"], "unknown")
        self.assertGreaterEqual(len(report["release_blockers"]), 9)
        self.assertFalse(report["release_authorized"])


if __name__ == "__main__":
    unittest.main()
