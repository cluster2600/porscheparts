#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import hashlib
import json
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "twins/reference-917-engine/f42-cooling-cht-contract.json"
SOURCE = ROOT / "twins/reference-917-engine/source/run_f42_cooling_cht.py"
PUBLISHED = ROOT / "twins/reference-917-engine/evidence/f42-cooling-cht/f42-cooling-cht-cross-check.json"
SPEC = importlib.util.spec_from_file_location("f42_cooling", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class F42CoolingChtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_geometry_is_exact_f41_and_not_modified(self) -> None:
        geometry = self.contract["geometry"]
        self.assertEqual(
            geometry["source_stl_sha256"],
            "2c1af796e851b680f67fd28b780d4b00fb8115efcf7e25a30d99361e6da1ac81",
        )
        self.assertTrue(geometry["watertight"])
        self.assertFalse(geometry["external_shape_modified_by_F42"])
        self.assertFalse(geometry["engine_interfaces_capped_for_CFD"])

    def test_release_gates_are_fail_closed(self) -> None:
        self.assertTrue(all(value is False for value in self.contract["release_gates"].values()))

    def test_analytical_bounds_are_deterministic(self) -> None:
        cases = MODULE.analytical_cases(self.contract)
        self.assertEqual(len(cases), 4)
        selected = next(case for case in cases if case["case_id"] == "p26-capture0.70")
        self.assertAlmostEqual(selected["mean_clear_gap_mm"], 4.096153846153846, places=10)
        self.assertAlmostEqual(selected["effective_h_w_m2k"], 215.764, places=2)
        self.assertAlmostEqual(selected["straight_pressure_drop_pa"], 1090.7, places=0)
        self.assertTrue(selected["correlation_in_reynolds_range"])
        self.assertTrue(selected["pressure_drop_below_6p7kpa"])
        self.assertTrue(any(not item["pressure_drop_below_6p7kpa"] for item in cases))

    def test_bridge_screen_fails_closed_above_material_range(self) -> None:
        selected = next(case for case in MODULE.analytical_cases(self.contract) if case["case_id"] == "p26-capture0.70")
        screen = MODULE.bridge_temperature(
            self.contract,
            selected["effective_h_w_m2k"],
            self.contract["geometry"]["surface_area_mm2_if_scan_unit_is_mm"] * 1.0e-6,
        )
        self.assertTrue(math.isfinite(screen["bridge_temperature_c"]))
        self.assertFalse(screen["maximum_below_260_c"])
        self.assertFalse(screen["within_qualified_interpolation_range_to_300c"])

    def test_published_report_never_claims_full_cht_or_release(self) -> None:
        report = json.loads(PUBLISHED.read_text(encoding="utf-8"))
        decision = report["decision"]
        self.assertFalse(decision["full_head_CHT_complete"])
        self.assertFalse(decision["metal_print_authorized"])
        self.assertFalse(decision["engine_start_authorized"])
        self.assertFalse(decision["absolute_scale_confirmed"])
        self.assertGreaterEqual(len(report["method_a_openfoam"]["cases"]), 2)
        self.assertTrue(any(case["status"] == "failed_or_incomplete" for case in report["method_a_openfoam"]["cases"]))

    def test_publication_manifest_is_self_consistent(self) -> None:
        root = PUBLISHED.parent
        publication = json.loads((root / "publication.json").read_text(encoding="utf-8"))
        self.assertTrue(all(value is False for value in publication["gates"].values()))
        for relative, expected in publication["files"].items():
            path = root / relative
            self.assertEqual(path.stat().st_size, expected["bytes"])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected["sha256"])


if __name__ == "__main__":
    unittest.main()
