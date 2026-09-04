"""Contrôles du calcul angle-vilebrequin Cantera/Wiebe F46."""

from __future__ import annotations

import gzip
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "twins/reference-917-engine/source/run_cantera_2v_4v_crank_cycle_f46.py"
CONTRACT = ROOT / "twins/reference-917-engine/cantera-2v-4v-crank-cycle-f46.json"
EVIDENCE = ROOT / "twins/reference-917-engine/evidence/f46-cantera-cycle"
REPORT = EVIDENCE / "cycle-report.json"
MANIFEST = EVIDENCE / "manifest.json"
FIGURE = EVIDENCE / "figures/f46-2v-4v-cycle.svg"


def load_module():
    specification = importlib.util.spec_from_file_location("f46_cantera_cycle", SCRIPT)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CanteraCrankCycleF46Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.report = json.loads(REPORT.read_text(encoding="utf-8"))

    def test_contract_is_hashed_comparable_and_fail_closed(self):
        self.assertEqual(self.module.validate_contract(self.contract, ROOT), [])
        geometry = self.contract["geometry"]
        self.assertEqual((geometry["bore_mm"], geometry["stroke_mm"]), (90.0, 70.4))
        self.assertFalse(geometry["external_head_geometry_used"])
        self.assertFalse(geometry["external_scan_contour_modified"])
        self.assertFalse(geometry["oval_or_ellipse_created"])
        self.assertFalse(self.contract["common_operating_point"]["power_target_is_solver_boundary"])
        self.assertTrue(all(value is False for value in self.contract["release_gates"].values()))

    def test_slider_crank_has_exact_dead_centres_and_positive_volume(self):
        geometry = self.module.slider_crank_geometry(self.contract)
        self.assertAlmostEqual(
            self.module.cylinder_volume_m3(0.0, geometry),
            geometry["clearance_volume_m3"],
            places=13,
        )
        self.assertAlmostEqual(
            self.module.cylinder_volume_m3(180.0, geometry),
            geometry["clearance_volume_m3"] + geometry["swept_volume_m3"],
            places=13,
        )
        self.assertGreater(geometry["rod_crank_ratio"], 3.0)

    def test_valve_law_orifice_and_wiebe_equations(self):
        lift = self.module.valve_lift_mm(110.0, -10.0, 230.0, 11.5)
        self.assertAlmostEqual(lift, 11.5, places=10)
        self.assertEqual(self.module.valve_lift_mm(360.0, -10.0, 230.0, 11.5), 0.0)
        area = self.module.valve_effective_area_m2(2, 31.5, 1152.757316, 10.0, 0.72)
        self.assertGreater(area, 0.0)
        choked = self.module.compressible_orifice_mass_flow(300000.0, 325.0, 1.4, 287.0, 100000.0, area)
        unchoked = self.module.compressible_orifice_mass_flow(300000.0, 325.0, 1.4, 287.0, 290000.0, area)
        self.assertGreater(choked, unchoked)
        xb, derivative = self.module.wiebe_fraction_and_derivative(382.5, 350.0, 65.0, 6.908, 2.0)
        self.assertGreater(xb, 0.0)
        self.assertGreater(derivative, 0.0)

    def test_exact_36_case_matrix_three_steps_and_cd_bracket(self):
        cases = self.report["cases"]
        self.assertEqual(len(cases), 36)
        keys = {
            (case["architecture"], case["model"], case["Cd"], case["crank_step_deg"])
            for case in cases
        }
        expected = {
            (architecture, model, cd, step)
            for architecture in ("2v", "4v")
            for model in ("cantera_finite_rate", "wiebe_counter_model")
            for cd in (0.62, 0.72, 0.82)
            for step in (1.0, 0.5, 0.25)
        }
        self.assertEqual(keys, expected)
        self.assertEqual(self.report["runtime"]["cantera_version"], "3.2.0")
        self.assertEqual(
            self.report["runtime"]["mechanism_sha256_actual"],
            self.contract["combustion_models"]["cantera_finite_rate"]["mechanism_sha256"],
        )

    def test_each_case_has_finite_outputs_balances_and_raw_trace(self):
        for case in self.report["cases"]:
            cycle = case["last_cycle"]
            for key in (
                "peak_pressure_pa_abs",
                "peak_temperature_k",
                "peak_heat_release_rate_w",
                "wall_heat_out_j",
                "indicated_work_j_per_cylinder_cycle",
                "imep_pa",
                "volumetric_efficiency_screen",
            ):
                self.assertTrue(math.isfinite(cycle[key]), f"{case['case_id']}:{key}")
            self.assertGreater(cycle["peak_pressure_pa_abs"], 0.0)
            self.assertGreater(cycle["peak_temperature_k"], 0.0)
            self.assertGreaterEqual(case["balances"]["mass_residual_fraction"], 0.0)
            self.assertGreaterEqual(case["balances"]["energy_residual_fraction"], 0.0)
            self.assertFalse(case["validation_claimed"])
            raw = case["raw_timeseries"]
            path = ROOT / raw["path"]
            self.assertTrue(path.is_file())
            self.assertEqual(sha256(path), raw["sha256"])
            self.assertEqual(raw["rows"], int(round(720.0 / case["crank_step_deg"])))
            with gzip.open(path, "rt", encoding="utf-8") as stream:
                self.assertEqual(tuple(stream.readline().strip().split(",")), self.module.RAW_COLUMNS)

    def test_comparisons_cover_step_cd_architecture_and_independent_combustion(self):
        comparisons = self.report["comparisons"]
        self.assertEqual(set(comparisons["step_convergence"]), {"2v", "4v"})
        self.assertEqual(
            set(comparisons["architecture_comparison_at_baseline_Cd_and_finest_step"]),
            {"cantera_finite_rate", "wiebe_counter_model"},
        )
        self.assertEqual(set(comparisons["Cd_bracket_at_finest_step"]), {"2v", "4v"})
        self.assertEqual(
            set(comparisons["cross_combustion_model_at_baseline_Cd_and_finest_step"]),
            {"2v", "4v"},
        )
        finite = next(case for case in self.report["cases"] if case["model"] == "cantera_finite_rate")
        prescribed = next(case for case in self.report["cases"] if case["model"] == "wiebe_counter_model")
        self.assertGreater(finite["last_cycle"]["chemical_heat_release_j"], 0.0)
        self.assertEqual(finite["last_cycle"]["prescribed_combustion_heat_j"], 0.0)
        self.assertEqual(prescribed["last_cycle"]["chemical_heat_release_j"], 0.0)
        self.assertGreater(prescribed["last_cycle"]["prescribed_combustion_heat_j"], 0.0)

    def test_quality_is_numerical_only_and_physical_gates_stay_closed(self):
        quality = self.report["quality_assessment"]
        self.assertTrue(quality["mass_balance"]["all_cases_pass"])
        self.assertTrue(quality["energy_balance"]["all_cases_pass"])
        self.assertTrue(quality["crank_step_convergence"]["all_baseline_metrics_pass"])
        self.assertFalse(quality["physical_validation_completed"])
        self.assertFalse(self.report["conclusion"]["combustion_validation_claimed"])
        self.assertFalse(self.report["conclusion"]["print_or_engine_start_authorized"])
        self.assertFalse(self.report["conclusion"]["external_geometry_created"])
        self.assertFalse(self.report["conclusion"]["oval_or_ellipse_created"])
        self.assertTrue(all(value is False for value in self.report["release_gates"].values()))

    def test_manifest_and_vector_graph_are_bound(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        paths = {item["path"]: item for item in manifest["artifacts"]}
        figure_relative = str(FIGURE.relative_to(ROOT))
        self.assertIn(figure_relative, paths)
        self.assertEqual(sha256(FIGURE), paths[figure_relative]["sha256"])
        svg = FIGURE.read_text(encoding="utf-8")
        self.assertIn('width="1600"', svg)
        self.assertIn('height="1000"', svg)
        self.assertIn("Aucune géométrie ovale", svg)


if __name__ == "__main__":
    unittest.main()
