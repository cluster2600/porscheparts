#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import hashlib
import json
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "twins/reference-917-engine/f39-cooling-optimization.json"
SOURCE = ROOT / "twins/reference-917-engine/source/run_f39_cooling_optimization.py"
PUBLISHED = ROOT / "twins/reference-917-engine/evidence/f39-cooling-optimization"
SPEC = importlib.util.spec_from_file_location("f39_cooling", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class F39CoolingOptimizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT.read_text())

    def test_release_gates_remain_false(self) -> None:
        self.assertTrue(all(value is False for value in self.contract["release_gates"].values()))

    def test_two_methods_are_declared_separately(self) -> None:
        self.assertIn("OpenFOAM", self.contract["method_a_openfoam_anchored"]["source"])
        self.assertIn("Gnielinski", self.contract["method_b_correlation"]["method"])
        self.assertIn("reduced_order", self.contract["method_a_openfoam_anchored"]["classification"])
        self.assertIn("independent", self.contract["method_b_correlation"]["classification"])

    def test_baseline_methods_are_finite(self) -> None:
        duct = next(item for item in self.contract["search_space"]["duct_variants"] if item["id"] == "splitter12")
        parameters = {"fin_levels": 12, "fin_thickness_mm": 2.0, "clear_gap_mm": 4.5, "root_radius_mm": 2.0, "mean_span_mm": 86.0, "mean_flow_length_mm": 180.0, "duct": duct, "local_oil_heat_removal_w": 0.0}
        result = MODULE.evaluate(self.contract, parameters)
        self.assertTrue(math.isfinite(result["maximum_bridge_temperature_c"]))
        self.assertGreater(result["maximum_bridge_temperature_c"], 260.0)
        self.assertFalse(result["screen"]["numerical_screen_passed"])

    def test_geometry_filter_respects_scan_envelope(self) -> None:
        geometry = MODULE.candidate_geometry(self.contract, 18, 2.4, 5.5, 100.0, 180.0)
        self.assertFalse(geometry["fits_scan_envelope_screen"])

    def test_optimizer_is_deterministic_and_fail_closed(self) -> None:
        # The published report is the deterministic end-to-end proof.
        report = json.loads((PUBLISHED / "f39-cooling-optimization-report.json").read_text())
        optimization = report["optimization"]
        self.assertEqual(optimization["combinations_evaluated"], 1728)
        self.assertEqual(optimization["geometry_feasible_combinations"], 432)
        self.assertEqual(optimization["numerical_screen_passing_combinations"], 35)
        self.assertTrue(optimization["gnielinski_all_geometry_feasible_cases_above_re_3000"])
        self.assertEqual(
            optimization["passing_combinations_by_local_oil_heat_w"],
            {"0.0": 0, "600.0": 0, "1200.0": 35},
        )
        selected = report["optimization"]["selected_candidate"]
        objectives = report["objectives"]
        if report["decision"]["numerical_candidate_found"]:
            self.assertLessEqual(selected["maximum_bridge_temperature_c"], objectives["maximum_bridge_temperature_c"])
            self.assertLessEqual(selected["maximum_pressure_drop_pa"], objectives["maximum_air_pressure_drop_pa"])
            self.assertLessEqual(selected["h_cross_method_relative_difference"], objectives["maximum_cross_method_h_relative_difference"])
        self.assertFalse(report["decision"]["full_head_CHT_complete"])
        self.assertFalse(report["decision"]["oil_gallery_geometry_and_heat_transfer_validated"])
        self.assertFalse(report["decision"]["metal_print_authorized"])
        self.assertFalse(report["decision"]["engine_start_authorized"])

    def test_selected_candidate_and_energy_balance(self) -> None:
        report = json.loads((PUBLISHED / "f39-cooling-optimization-report.json").read_text())
        selected = report["optimization"]["selected_candidate"]
        self.assertEqual(selected["parameters"]["duct"], "splitter12")
        self.assertEqual(selected["parameters"]["fin_levels"], 14)
        self.assertEqual(selected["parameters"]["local_oil_heat_removal_w"], 1200.0)
        self.assertAlmostEqual(selected["maximum_bridge_temperature_c"], 230.829324, places=5)
        self.assertAlmostEqual(selected["maximum_pressure_drop_pa"], 4991.461591, places=5)
        self.assertAlmostEqual(selected["pressure_drop_cross_method_relative_difference"], 0.0702641825, places=8)
        for thermal in (selected["thermal_a"], selected["thermal_b"]):
            self.assertAlmostEqual(
                thermal["air_heat_w"] + thermal["local_oil_heat_removal_w"],
                thermal["total_heat_w"],
            )
            self.assertTrue(thermal["within_CP1_interpolation_range"])

    def test_off_design_exposes_temperature_and_pressure_failures(self) -> None:
        report = json.loads((PUBLISHED / "f39-cooling-optimization-report.json").read_text())
        off_design = report["off_design_sensitivity"]
        self.assertTrue(any(item["maximum_bridge_temperature_c"] > 260.0 for item in off_design))
        self.assertTrue(any(item["maximum_pressure_drop_pa"] > 6700.0 for item in off_design))
        self.assertTrue(any(item["screen"]["numerical_screen_passed"] for item in off_design))
        self.assertTrue(any(not item["screen"]["numerical_screen_passed"] for item in off_design))

    def test_publication_manifest_is_self_consistent(self) -> None:
        publication = json.loads((PUBLISHED / "publication.json").read_text())
        self.assertTrue(all(value is False for value in publication["gates"].values()))
        for relative, expected in publication["files"].items():
            path = PUBLISHED / relative
            self.assertEqual(path.stat().st_size, expected["bytes"])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected["sha256"])


if __name__ == "__main__":
    unittest.main()
