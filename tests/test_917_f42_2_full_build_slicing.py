#!/usr/bin/env python3
"""Tests fail-closed du tranchage pleine pile F42.2."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "twins/reference-917-engine/source/run_f42_2_full_build_slicing.py"
EVIDENCE = ROOT / "twins/reference-917-engine/evidence/f42-2-full-build"
REPORT = EVIDENCE / "917-head-f42-2-full-build-report.json"
METRICS = EVIDENCE / "917-head-f42-2-layer-metrics.csv"
IMAGE = EVIDENCE / "917-head-f42-2-full-build.png"
VIDEO = EVIDENCE / "917-head-f42-2-build-progress.mp4"
MANIFEST = EVIDENCE / "917-head-f42-2-publication-manifest.json"


def load_source():
    spec = importlib.util.spec_from_file_location("f42_2_slicing", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot_load_f42_2_source")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class F422FullBuildSlicingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_source()
        cls.report = json.loads(REPORT.read_text(encoding="utf-8"))
        with METRICS.open("r", encoding="utf-8", newline="") as stream:
            cls.rows = list(csv.DictReader(stream))

    def test_layer_math_is_fail_closed(self) -> None:
        self.assertEqual(self.module.required_layer_count(206.093643, 0.05), 4122)
        with self.assertRaisesRegex(self.module.F422Error, "invalid_build_height"):
            self.module.required_layer_count(float("nan"), 0.05)
        with self.assertRaisesRegex(self.module.F422Error, "invalid_layer_thickness"):
            self.module.required_layer_count(206.0, 0.0)

    def test_locked_transform_is_scan_y_down_and_grounded(self) -> None:
        vertices = np.asarray([[-2.0, -10.0, -3.0], [4.0, 12.0, 5.0]])
        transformed = self.module.locked_transform(vertices)
        np.testing.assert_allclose(transformed[:, 0], [-2.0, 4.0])
        np.testing.assert_allclose(transformed[:, 1], [3.0, -5.0])
        np.testing.assert_allclose(transformed[:, 2], [0.0, 22.0])

    def test_all_4122_midplane_slices_are_contiguous_and_finite(self) -> None:
        self.assertEqual(len(self.rows), 4122)
        expected_fields = {
            "layer_index",
            "z_mm",
            "part_area_mm2",
            "part_perimeter_mm",
            "part_component_count",
            "new_island_count",
            "unsupported_area_mm2",
            "unsupported_component_count",
            "support_cross_section_area_mm2",
            "support_cross_section_perimeter_mm",
        }
        self.assertEqual(set(self.rows[0]), expected_fields)
        for index, row in enumerate(self.rows):
            self.assertEqual(int(row["layer_index"]), index)
            self.assertAlmostEqual(float(row["z_mm"]), (index + 0.5) * 0.05, places=7)
            for key, value in row.items():
                if key == "layer_index":
                    continue
                numeric = float(value)
                self.assertTrue(math.isfinite(numeric), (index, key))
                self.assertGreaterEqual(numeric, 0.0, (index, key))

    def test_report_proves_geometric_slice_but_not_thermal_or_recoater(self) -> None:
        report = self.report
        self.assertEqual(report["phase"], "F42.2")
        self.assertTrue(report["geometric_slicing"]["executed"])
        self.assertEqual(report["geometric_slicing"]["required_layer_count"], 4122)
        self.assertEqual(report["geometric_slicing"]["layer_thickness_mm"], 0.05)
        self.assertTrue(report["support_proxy"]["private_layer_resolved_geometry_generated"])
        self.assertFalse(report["support_proxy"]["published"])
        self.assertFalse(report["thermal_process"]["additivefoam_executed_in_this_phase"])
        self.assertFalse(report["recoater"]["collision_clearance_verified"])
        self.assertFalse(report["gates"]["supplier_slicer_project_reviewed"])
        self.assertFalse(report["gates"]["machine_file_generated_and_signed"])
        self.assertFalse(report["gates"]["manufacturing_release"])
        self.assertFalse(report["verdict"]["part_authorized_for_print"])

    def test_public_evidence_has_no_private_geometry_or_path(self) -> None:
        serialized = (REPORT.read_text(encoding="utf-8") + METRICS.read_text(encoding="utf-8")).lower()
        for forbidden in (
            "/workspace/",
            "private-f42-head",
            "wkb_hex",
            "vertex",
            "triangle_coordinates",
            ".stl",
            ".step",
            ".3mf",
        ):
            self.assertNotIn(forbidden, serialized)
        self.assertFalse(self.report["publication"]["contains_private_geometry"])
        self.assertFalse(self.report["publication"]["contains_coordinates_or_contours"])
        self.assertRegex(self.report["private_input"]["sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(self.report["publication"]["public_layer_metrics_sha256"], digest(METRICS))

    def test_public_renders_and_manifest_are_bound_by_hash(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertGreater(IMAGE.stat().st_size, 50_000)
        self.assertGreater(VIDEO.stat().st_size, 100_000)
        for name, path in {
            "report": REPORT,
            "metrics": METRICS,
            "image": IMAGE,
            "video": VIDEO,
        }.items():
            self.assertEqual(manifest["artifacts"][name]["sha256"], digest(path))
        self.assertFalse(manifest["gates"]["contains_private_geometry"])
        self.assertFalse(manifest["gates"]["recoater_clearance_verified"])
        self.assertFalse(manifest["gates"]["print_authorized"])


if __name__ == "__main__":
    unittest.main()
