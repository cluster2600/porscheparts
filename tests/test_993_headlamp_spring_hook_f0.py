import importlib.util
import json
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "parts/993-elec-headlamp-spring-hook-f0-0001/source/headlamp_spring_hook.py"
RECORD = ROOT / "catalog/parts/993-elec-headlamp-spring-hook-f0-0001.json"
SPEC = importlib.util.spec_from_file_location("headlamp_spring_hook", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class HeadlampSpringHookF0Tests(unittest.TestCase):
    def test_beam_equations_are_recomputed(self) -> None:
        report = MODULE.engineering_screen(30.0)
        results = report["results"]
        self.assertEqual(report["status"], "f0_clean_sheet_math_screen_only")
        self.assertAlmostEqual(results["analytic_volume_mm3"], 881.0)
        self.assertAlmostEqual(results["minimum_socket_wall_mm"], 1.5)
        self.assertAlmostEqual(results["arm_second_moment_mm4"], 18.0)
        self.assertAlmostEqual(results["bending_stress_mpa"], 15.0)
        self.assertAlmostEqual(results["maximum_transverse_shear_mpa"], 1.875)
        self.assertAlmostEqual(
            results["von_mises_screen_mpa"], math.sqrt(15.0**2 + 3 * 1.875**2)
        )

    def test_force_scaling_is_linear_in_elastic_screen(self) -> None:
        low = MODULE.engineering_screen(10.0)["results"]
        high = MODULE.engineering_screen(30.0)["results"]
        self.assertAlmostEqual(high["bending_stress_mpa"], 3 * low["bending_stress_mpa"])
        self.assertAlmostEqual(high["tip_deflection_mm"], 3 * low["tip_deflection_mm"])
        self.assertAlmostEqual(high["bond_average_shear_mpa"], 3 * low["bond_average_shear_mpa"])

    def test_record_and_report_refuse_fitment_claims(self) -> None:
        record = json.loads(RECORD.read_text(encoding="utf-8"))
        report = MODULE.engineering_screen()
        self.assertEqual(record["geometry"]["source_type"], "estimated")
        self.assertEqual(record["validation"]["status"], "concept")
        self.assertFalse(report["release_authorized"])
        self.assertIn("AlSi10Mg_FlexM291 2.01", record["manufacturing"]["material"]["grade"])
        self.assertEqual(report["material_screen"]["published_vertical_yield_strength_mpa"], 233.0)
        self.assertFalse(report["material_screen"]["design_allowable"])
        self.assertGreaterEqual(len(report["release_blockers"]), 6)
        self.assertIn("No published dimensions", report["release_blockers"][0])


if __name__ == "__main__":
    unittest.main()
