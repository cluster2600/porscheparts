#!/usr/bin/env python3
"""Tests du comparateur de reproductibilite AdditiveFOAM F42.2."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "twins/reference-917-engine/source/compare_additivefoam_f42_hosts.py"
SPEC = importlib.util.spec_from_file_location("compare_additivefoam_f42_hosts", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def measurement(index: int) -> dict:
    return {
        "case_id": f"C{index:02d}",
        "resolution": "nominal",
        "completed": True,
        "fatal_error": False,
        "finite": True,
        "temperature_max_k": 2100.0,
        "temperature_p99_k": 1200.0,
        "molten_volume_mm3": 0.08,
        "melt_pool_length_mm": 0.50,
        "melt_pool_width_mm": 0.18,
        "melt_pool_depth_mm": 0.10,
        "maximum_courant_number": 0.30,
    }


class F42LpbfReproducibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.left = [measurement(index) for index in range(33)]
        self.right = [dict(item) for item in self.left]

    def test_identical_33_case_runs_pass_runtime_reproducibility_only(self) -> None:
        report = MODULE.compare(self.left, self.right, "cpu-a", "cpu-b")
        self.assertTrue(report["gates"]["all_33_runs_reproduced_within_tolerance"])
        self.assertFalse(report["gates"]["second_independent_physics_method_completed"])
        self.assertFalse(report["gates"]["metal_print_authorized"])

    def test_missing_case_fails_closed(self) -> None:
        report = MODULE.compare(self.left, self.right[:-1], "cpu-a", "cpu-b")
        self.assertFalse(report["case_set_identical"])
        self.assertFalse(report["gates"]["all_33_runs_reproduced_within_tolerance"])

    def test_large_metric_difference_fails(self) -> None:
        self.right[0]["temperature_p99_k"] = 1300.0
        report = MODULE.compare(self.left, self.right, "cpu-a", "cpu-b")
        self.assertFalse(report["comparisons"][0]["metrics"]["temperature_p99_k"]["passes"])
        self.assertFalse(report["gates"]["all_33_runs_reproduced_within_tolerance"])

    def test_cap_classification_mismatch_fails(self) -> None:
        self.left[0]["temperature_max_k"] = 3298.5
        self.right[0]["temperature_max_k"] = 3299.5
        report = MODULE.compare(self.left, self.right, "cpu-a", "cpu-b")
        self.assertFalse(report["comparisons"][0]["temperature_cap_classification_matches"])
        self.assertFalse(report["gates"]["all_33_runs_reproduced_within_tolerance"])


if __name__ == "__main__":
    unittest.main()
