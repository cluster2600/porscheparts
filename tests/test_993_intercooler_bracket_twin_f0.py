import hashlib
import importlib.util
import json
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TWIN = ROOT / "catalog/twins/twin-993-intercooler-bracket-ti-f0.json"
PART = ROOT / "catalog/parts/993-eng-intercooler-bracket-ti-f0-0001.json"
STEP = ROOT / "parts/993-eng-intercooler-bracket-ti-f0-0001/derived/intercooler_bracket_ti_f0.step"
ANALYTIC = ROOT / "parts/993-eng-intercooler-bracket-ti-f0-0001/evidence/engineering-screen.json"
FEA = ROOT / "parts/993-eng-intercooler-bracket-ti-f0-0001/evidence/calculix-screen.json"
USD = ROOT / "parts/993-eng-intercooler-bracket-ti-f0-0001/evidence/simready-conversion-summary.json"
RUNNER = ROOT / "twins/993-intercooler-bracket-ti-f0/source/run_calculix_screen.py"
SPEC = importlib.util.spec_from_file_location("intercooler_bracket_calculix", RUNNER)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class IntercoolerBracketTwinF0Tests(unittest.TestCase):
    def test_twin_is_an_envelope_concept_with_open_interfaces(self) -> None:
        twin = load(TWIN)
        self.assertEqual(twin["fidelity"], "F1_envelope")
        self.assertEqual(twin["validation"]["status"], "concept")
        self.assertEqual(
            twin["components"][0]["part_id"],
            "993-ENG-INTERCOOLER-BRACKET-TI-F0-0001",
        )
        self.assertIsNone(twin["components"][0]["accuracy_mm"])
        self.assertTrue(twin["interfaces"])
        self.assertTrue(
            all(item["status"] == "missing_data" for item in twin["interfaces"])
        )
        for relative in twin["validation"]["evidence"]:
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_calculix_screen_uses_three_quadratic_meshes(self) -> None:
        report = load(FEA)
        self.assertEqual(report["solver"]["analysis"], "CalculiX linear static C3D10")
        self.assertEqual(report["solver"]["gmsh_version"], "4.12.1")
        self.assertIn("Version 2.21", report["solver"]["calculix_version_output"])
        self.assertEqual(
            [case["mesh"]["mesh_size_mm"] for case in report["cases"]],
            [5.0, 3.5, 2.5],
        )
        self.assertTrue(
            all(case["mesh"]["quadratic_tetrahedra"] > 0 for case in report["cases"])
        )
        self.assertTrue(report["numerical_gates"]["p95_grid_change_below_10_percent"])
        self.assertTrue(
            report["numerical_gates"]["displacement_grid_change_below_10_percent"]
        )
        self.assertLess(
            report["grid_comparison_fine_vs_previous"]["p95_relative_change"],
            0.10,
        )
        self.assertLess(
            report["grid_comparison_fine_vs_previous"]["displacement_relative_change"],
            0.10,
        )
        finest = report["cases"][-1]
        self.assertGreater(finest["von_mises_mpa"]["maximum"], 300.0)
        self.assertGreater(finest["maximum_displacement_mm"], 1.0)
        self.assertFalse(report["release_authorized"])
        self.assertTrue(all(value is False for value in report["engineering_gates"].values()))

    def test_fea_and_analytic_models_remain_distinct(self) -> None:
        analytic = load(ANALYTIC)["results"]
        finest = load(FEA)["cases"][-1]
        self.assertAlmostEqual(MODULE.von_mises([100.0, 0.0, 0.0, 0.0, 0.0, 0.0]), 100.0)
        self.assertTrue(
            math.isclose(
                finest["von_mises_mpa"]["p95"]
                / analytic["von_mises_screen_mpa"],
                0.31821635938833276,
                rel_tol=1e-9,
            )
        )
        self.assertTrue(
            math.isclose(
                finest["maximum_displacement_mm"]
                / analytic["linear_elastic_center_deflection_mm"],
                0.4321177810334883,
                rel_tol=1e-9,
            )
        )

    def test_dfam_decision_is_conditional_not_a_print_release(self) -> None:
        assessment = load(FEA)["dfam_assessment"]
        self.assertFalse(assessment["lpbf_preferred_for_current_geometry"])
        self.assertFalse(assessment["geometry_redesign_authorized"])
        self.assertIn("requires_CNC_sheet_LPBF", assessment["current_route_decision"])

    def test_usd_summary_proves_only_minimum_conversion(self) -> None:
        summary = load(USD)
        self.assertEqual(summary["status"], "minimum_usd_passed_not_simready")
        self.assertEqual(summary["property_assignment_intent"], "skip")
        self.assertEqual(
            summary["source"]["sha256"], hashlib.sha256(STEP.read_bytes()).hexdigest()
        )
        self.assertTrue(summary["gates"]["step_to_usd_conversion"])
        self.assertTrue(summary["gates"]["minimum_usd"])
        self.assertFalse(summary["gates"]["material_agent_assignment"])
        self.assertFalse(summary["gates"]["physics_agent_assignment"])
        self.assertFalse(summary["gates"]["manufacturing_authorized"])
        self.assertEqual(
            summary["minimum_usd_validation"]["bounds_stage_units_mm"],
            [255.0, 80.0, 23.0],
        )

    def test_public_evidence_has_no_machine_paths(self) -> None:
        text = "\n".join(
            path.read_text(encoding="utf-8") for path in (FEA, USD, TWIN, PART)
        )
        for forbidden in ("/tmp/", "/Users/", "/workspace/", "/run/"):
            self.assertNotIn(forbidden, text)

    def test_part_record_links_new_evidence_and_stays_blocked(self) -> None:
        part = load(PART)
        self.assertEqual(part["validation"]["status"], "concept")
        self.assertIn(FEA.relative_to(ROOT).as_posix(), part["validation"]["evidence"])
        self.assertIn(USD.relative_to(ROOT).as_posix(), part["validation"]["evidence"])
        self.assertEqual(part["manufacturing"]["preferred_process"], "CNC")
        self.assertEqual(part["titanium"]["hip_required"], "to_be_determined")


if __name__ == "__main__":
    unittest.main()
