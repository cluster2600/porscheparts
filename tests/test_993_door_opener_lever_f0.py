import importlib.util
import json
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "parts/993-int-door-opener-lever-f0-0001/source/door_opener_lever.py"
RECORD = ROOT / "catalog/parts/993-int-door-opener-lever-f0-0001.json"
REPORT = ROOT / "parts/993-int-door-opener-lever-f0-0001/evidence/engineering-screen.json"
SOURCE = ROOT / "catalog/sources/src-porschefanatics-993-door-opener-pet.json"
SPEC = importlib.util.spec_from_file_location("door_opener_lever", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class DoorOpenerLeverF0Tests(unittest.TestCase):
    def test_published_values_are_separated_from_hypotheses(self) -> None:
        report = MODULE.engineering_screen()
        self.assertEqual(
            report["status"],
            "f0_published_envelope_clean_sheet_math_screen_only",
        )
        self.assertEqual(
            report["geometry_authority"]["published"],
            [
                "commercial product envelope 108 x 45 x 27 mm",
                "commercial pair mass 180 g",
            ],
        )
        self.assertGreaterEqual(len(report["geometry_authority"]["hypotheses"]), 4)
        self.assertFalse(report["release_authorized"])

    def test_beam_pivot_and_mass_equations_are_recomputed(self) -> None:
        force = 150.0
        report = MODULE.engineering_screen(force)
        results = report["results"]
        span = 92.0 - 35.0
        area = 45.0 * 5.0
        second_moment = 45.0 * 5.0**3 / 12.0
        bending = force * span * 2.5 / second_moment
        shear = 1.5 * force / area

        self.assertAlmostEqual(results["analytic_volume_mm3"], MODULE.analytic_volume_mm3())
        self.assertAlmostEqual(results["lever_span_mm"], span)
        self.assertAlmostEqual(results["lever_section_area_mm2"], area)
        self.assertAlmostEqual(results["lever_second_moment_mm4"], second_moment)
        self.assertAlmostEqual(results["bending_stress_mpa"], bending)
        self.assertAlmostEqual(results["maximum_transverse_shear_mpa"], shear)
        self.assertAlmostEqual(
            results["von_mises_screen_mpa"],
            math.sqrt(bending**2 + 3.0 * shear**2),
        )
        self.assertAlmostEqual(
            results["pivot_average_bearing_stress_mpa"],
            force / (2.0 * 6.0 * 4.0),
        )
        self.assertAlmostEqual(
            results["candidate_pin_double_shear_mpa"],
            force / (2.0 * math.pi * 6.0**2 / 4.0),
        )
        self.assertLess(results["screening_pair_mass_g"], 180.0)

    def test_elastic_results_scale_linearly_with_force(self) -> None:
        low = MODULE.engineering_screen(50.0)["results"]
        high = MODULE.engineering_screen(150.0)["results"]
        for key in (
            "bending_stress_mpa",
            "maximum_transverse_shear_mpa",
            "linear_elastic_tip_deflection_mm",
            "pivot_average_bearing_stress_mpa",
            "candidate_pin_double_shear_mpa",
            "clevis_net_tension_mpa",
        ):
            self.assertAlmostEqual(high[key], 3.0 * low[key])

    def test_committed_report_and_catalogue_keep_release_blocked(self) -> None:
        record = json.loads(RECORD.read_text(encoding="utf-8"))
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        source = json.loads(SOURCE.read_text(encoding="utf-8"))

        self.assertEqual(record["geometry"]["source_type"], "mixed")
        self.assertEqual(record["validation"]["status"], "concept")
        self.assertEqual(
            record["vehicle"]["porsche_part_numbers"],
            ["99355585100", "99355585200"],
        )
        self.assertFalse(report["release_authorized"])
        self.assertGreaterEqual(len(report["release_blockers"]), 7)
        self.assertEqual(report["step_roundtrip"]["status"], "passed")
        self.assertEqual(report["step_roundtrip"]["solid_count"], 1)
        self.assertEqual(source["quality"]["dimensional_accuracy"], "unknown")
        self.assertIn(
            "4192f9699f1176bcfe8b8ec7cbcc7c05dc7ee296",
            source["quality"]["verified_against"][0],
        )


if __name__ == "__main__":
    unittest.main()
