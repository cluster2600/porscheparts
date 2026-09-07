import importlib.util
import json
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "parts/993-eng-intercooler-bracket-ti-f0-0001/source/intercooler_bracket.py"
RECORD = ROOT / "catalog/parts/993-eng-intercooler-bracket-ti-f0-0001.json"
REPORT = ROOT / "parts/993-eng-intercooler-bracket-ti-f0-0001/evidence/engineering-screen.json"
FVD_SOURCE = ROOT / "catalog/sources/src-fvd-993-intercooler-bracket-dimensions.json"
PET_SOURCE = ROOT / "catalog/sources/src-porschefanatics-993-turbo-pet.json"
SPEC = importlib.util.spec_from_file_location("intercooler_bracket", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class IntercoolerBracketTiF0Tests(unittest.TestCase):
    def test_published_values_are_separated_from_hypotheses(self) -> None:
        report = MODULE.engineering_screen()
        self.assertEqual(
            report["geometry_authority"]["published"],
            [
                "commercial product envelope 255 x 80 x 23 mm",
                "commercial product mass 200 g",
            ],
        )
        self.assertGreaterEqual(len(report["geometry_authority"]["hypotheses"]), 4)
        self.assertFalse(report["release_authorized"])

    def test_beam_bearing_thermal_and_mass_equations_are_recomputed(self) -> None:
        force = 400.0
        results = MODULE.engineering_screen(force)["results"]
        area = 2.0 * 8.0 * 6.0
        second_moment = 2.0 * 8.0 * 6.0**3 / 12.0
        moment = force * 220.0 / 4.0
        bending = moment * 3.0 / second_moment
        shear = 1.5 * force / area

        self.assertAlmostEqual(results["analytic_volume_mm3"], MODULE.analytic_volume_mm3())
        self.assertAlmostEqual(results["effective_rail_area_mm2"], area)
        self.assertAlmostEqual(results["effective_second_moment_mm4"], second_moment)
        self.assertAlmostEqual(results["nominal_bending_stress_mpa"], bending)
        self.assertAlmostEqual(results["maximum_transverse_shear_mpa"], shear)
        self.assertAlmostEqual(
            results["von_mises_screen_mpa"],
            math.sqrt(bending**2 + 3.0 * shear**2),
        )
        self.assertAlmostEqual(
            results["linear_elastic_center_deflection_mm"],
            force * 220.0**3 / (48.0 * 110_000.0 * second_moment),
        )
        self.assertAlmostEqual(
            results["thermal_growth_over_screen_span_mm"],
            9.0e-6 * 220.0 * 120.0,
        )
        self.assertLess(results["screening_mass_g"], 200.0)

    def test_elastic_results_scale_linearly_with_force(self) -> None:
        low = MODULE.engineering_screen(100.0)["results"]
        high = MODULE.engineering_screen(400.0)["results"]
        for key in (
            "nominal_bending_stress_mpa",
            "maximum_transverse_shear_mpa",
            "linear_elastic_center_deflection_mm",
            "pedestal_average_bearing_mpa",
        ):
            self.assertAlmostEqual(high[key], 4.0 * low[key])

    def test_committed_artifacts_keep_titanium_release_blocked(self) -> None:
        record = json.loads(RECORD.read_text(encoding="utf-8"))
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        fvd = json.loads(FVD_SOURCE.read_text(encoding="utf-8"))
        pet = json.loads(PET_SOURCE.read_text(encoding="utf-8"))

        self.assertEqual(record["validation"]["status"], "concept")
        self.assertTrue(record["titanium"]["applicable"])
        self.assertIn("LPBF", record["manufacturing"]["candidate_processes"])
        self.assertEqual(report["step_roundtrip"]["status"], "passed")
        self.assertEqual(report["step_roundtrip"]["solid_count"], 1)
        self.assertEqual(report["step_roundtrip"]["envelope_mm"], [255.0, 80.0, 23.0])
        self.assertGreaterEqual(len(report["release_blockers"]), 9)
        self.assertEqual(fvd["quality"]["dimensional_accuracy"], "declared")
        self.assertEqual(pet["quality"]["dimensional_accuracy"], "unknown")
        self.assertFalse(report["release_authorized"])


if __name__ == "__main__":
    unittest.main()
