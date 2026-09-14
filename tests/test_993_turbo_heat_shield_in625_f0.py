import importlib.util
import json
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "parts/993-eng-turbo-heat-shield-in625-f0-0001/source/turbo_heat_shield.py"
RECORD = ROOT / "catalog/parts/993-eng-turbo-heat-shield-in625-f0-0001.json"
REPORT = ROOT / "parts/993-eng-turbo-heat-shield-in625-f0-0001/evidence/engineering-screen.json"
FVD_SOURCE = ROOT / "catalog/sources/src-fvd-993-turbo-heat-shield-dimensions.json"
EOS_SOURCE = ROOT / "catalog/sources/src-eos-in625-material-data.json"
SPEC = importlib.util.spec_from_file_location("turbo_heat_shield", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class TurboHeatShieldIn625F0Tests(unittest.TestCase):
    def test_published_envelope_and_hypotheses_are_separate(self) -> None:
        report = MODULE.engineering_screen()
        self.assertEqual(report["geometry_authority"]["catalogue_identity"], ["99312311351"])
        self.assertEqual(
            report["geometry_authority"]["published"],
            [
                "commercial product envelope 160 x 110 x 105 mm",
                "commercial product mass 230 g",
            ],
        )
        self.assertGreaterEqual(len(report["geometry_authority"]["hypotheses"]), 4)
        self.assertFalse(report["release_authorized"])

    def test_mechanical_and_thermal_equations_are_recomputed(self) -> None:
        force = 50.0
        results = MODULE.engineering_screen(force)["results"]
        inertia = 40.0 * 0.8**3 / 12.0
        stress = (force * 60.0 / 4.0) * 0.4 / inertia

        self.assertAlmostEqual(results["analytic_volume_mm3"], MODULE.analytic_volume_mm3())
        self.assertAlmostEqual(results["strip_second_moment_mm4"], inertia)
        self.assertAlmostEqual(results["nominal_bending_stress_mpa"], stress)
        self.assertAlmostEqual(
            results["linear_elastic_center_deflection_mm"],
            force * 60.0**3 / (48.0 * 204_000.0 * inertia),
        )
        self.assertAlmostEqual(
            results["free_thermal_expansion_mm"],
            13.7e-6 * 160.0 * (650.0 - 293.0),
        )
        expected_flux = 0.8 * MODULE.STEFAN_BOLTZMANN * (900.0**4 - 650.0**4)
        self.assertAlmostEqual(results["incident_radiative_flux_w_m2"], expected_flux)
        self.assertGreater(results["fully_constrained_elastic_thermal_stress_mpa"], 640.0)
        self.assertGreater(results["screening_mass_g"], 230.0)

    def test_elastic_results_scale_linearly_with_force(self) -> None:
        low = MODULE.engineering_screen(10.0)["results"]
        high = MODULE.engineering_screen(50.0)["results"]
        for key in (
            "maximum_bending_moment_n_mm",
            "nominal_bending_stress_mpa",
            "linear_elastic_center_deflection_mm",
            "mount_average_bearing_mpa",
        ):
            self.assertAlmostEqual(high[key], 5.0 * low[key])

    def test_committed_artifacts_keep_route_and_release_open(self) -> None:
        record = json.loads(RECORD.read_text(encoding="utf-8"))
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        fvd = json.loads(FVD_SOURCE.read_text(encoding="utf-8"))
        eos = json.loads(EOS_SOURCE.read_text(encoding="utf-8"))

        self.assertEqual(record["manufacturing"]["preferred_process"], "undecided")
        self.assertIn("sheet_metal", record["manufacturing"]["candidate_processes"])
        self.assertIn("LPBF", record["manufacturing"]["candidate_processes"])
        self.assertEqual(record["validation"]["status"], "concept")
        self.assertEqual(report["step_roundtrip"]["status"], "passed")
        self.assertEqual(report["step_roundtrip"]["solid_count"], 1)
        self.assertEqual(report["step_roundtrip"]["envelope_mm"], [160.0, 110.0, 105.0])
        self.assertEqual(fvd["quality"]["dimensional_accuracy"], "declared")
        self.assertEqual(eos["quality"]["evidence_level"], "B")
        self.assertGreaterEqual(len(report["release_blockers"]), 9)
        self.assertFalse(report["release_authorized"])


if __name__ == "__main__":
    unittest.main()
