#!/usr/bin/env python3
"""Tests fail-closed de la comparaison d'orientation F42.3."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SLICE_SOURCE = ROOT / "twins/reference-917-engine/source/run_f42_2_full_build_slicing.py"
EVIDENCE = ROOT / "twins/reference-917-engine/evidence/f42-3-orientation-comparison"
REPORT = EVIDENCE / "917-head-f42-3-orientation-comparison-report.json"
IMAGE = EVIDENCE / "917-head-f42-3-orientation-comparison.png"
MANIFEST = EVIDENCE / "917-head-f42-3-publication-manifest.json"


def load_source(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot_load:{name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class F423OrientationComparisonTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.slicer = load_source(SLICE_SOURCE, "f42_2_slicer_for_f42_3")
        cls.report = json.loads(REPORT.read_text(encoding="utf-8"))

    def test_minus_y_transform_is_opposite_build_direction(self) -> None:
        vertices = np.asarray([[-2.0, -10.0, -3.0], [4.0, 12.0, 5.0]])
        plus_y = self.slicer.orientation_transform(vertices, "scan_y_down")
        minus_y = self.slicer.orientation_transform(vertices, "scan_y_up")
        np.testing.assert_allclose(plus_y[:, 2], [0.0, 22.0])
        np.testing.assert_allclose(minus_y[:, 2], [22.0, 0.0])
        np.testing.assert_allclose(plus_y[:, 1], [3.0, -5.0])
        np.testing.assert_allclose(minus_y[:, 1], [-3.0, 5.0])
        with self.assertRaisesRegex(self.slicer.F422Error, "unsupported_orientation"):
            self.slicer.orientation_transform(vertices, "invented")

    def test_both_orientations_are_actual_complete_slices(self) -> None:
        report = self.report
        self.assertEqual(report["phase"], "F42.3")
        self.assertEqual(report["common_method"]["actual_midplane_slices_per_orientation"], 4122)
        self.assertEqual(report["common_method"]["layer_thickness_mm"], 0.05)
        for result in report["orientations"].values():
            self.assertEqual(result["layer_count"], 4122)
            self.assertEqual(result["empty_layer_count"], 0)
        self.assertTrue(report["gates"]["both_actual_4122_layer_slices_completed"])
        self.assertTrue(report["gates"]["both_nominal_machine_envelopes_fit"])

    def test_complete_stack_overrules_surface_proxy(self) -> None:
        report = self.report
        reference = report["orientations"]["reference_scan_y_down_plus_y"]
        candidate = report["orientations"]["candidate_scan_y_up_minus_y"]
        self.assertLess(candidate["new_island_count_total"], reference["new_island_count_total"])
        self.assertLess(
            candidate["unsupported_area_layer_integral_mm2_layers"],
            reference["unsupported_area_layer_integral_mm2_layers"],
        )
        self.assertGreater(candidate["support_volume_cm3"], reference["support_volume_cm3"])
        self.assertGreater(
            candidate["support_vertical_side_surface_mm2"],
            reference["support_vertical_side_surface_mm2"],
        )
        self.assertAlmostEqual(
            report["comparison_percent_candidate_minus_reference"]["support_volume_cm3"],
            21.3179951274,
            places=6,
        )
        self.assertFalse(
            report["decision"]["candidate_numerically_better_on_all_required_geometric_metrics"]
        )
        self.assertEqual(report["decision"]["selected_orientation"], "scan_y_down (+Y) retained")

    def test_interfaces_recoater_and_release_stay_closed(self) -> None:
        report = self.report
        interface = report["functional_interface_and_build_plate"]
        self.assertTrue(interface["build_plate_facing_side_reversed"])
        self.assertFalse(interface["functional_interface_semantic_labels_available"])
        self.assertFalse(interface["functional_interface_contact_with_plate_ruled_out"])
        self.assertFalse(report["recoater"]["candidate_collision_clearance_verified"])
        self.assertFalse(report["decision"]["orientation_change_authorized"])
        self.assertFalse(report["gates"]["manufacturing_release"])
        self.assertFalse(report["verdict"]["part_authorized_for_print"])

    def test_public_report_is_sanitized(self) -> None:
        serialized = REPORT.read_text(encoding="utf-8").lower()
        for forbidden in (
            "/workspace/",
            "/tmp/",
            "private-f42-head",
            "wkb_hex",
            ".stl",
            ".step",
            "vertex_coordinates",
        ):
            self.assertNotIn(forbidden, serialized)
        self.assertFalse(self.report["publication"]["contains_private_geometry"])
        self.assertFalse(self.report["publication"]["contains_coordinates_or_contours"])
        self.assertRegex(self.report["private_input"]["sha256"], r"^[0-9a-f]{64}$")

    def test_image_manifest_binds_public_artifacts(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertGreater(IMAGE.stat().st_size, 50_000)
        self.assertEqual(manifest["artifacts"]["report"]["sha256"], sha256(REPORT))
        self.assertEqual(manifest["artifacts"]["image"]["sha256"], sha256(IMAGE))
        self.assertFalse(manifest["gates"]["contains_private_geometry"])
        self.assertFalse(manifest["gates"]["orientation_change_authorized"])
        self.assertFalse(manifest["gates"]["manufacturing_release"])


if __name__ == "__main__":
    unittest.main()
