#!/usr/bin/env python3
"""Tests autonomes F42.1, sans STEP prive."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "twins/reference-917-engine/source/repair_topology_f42_1.py"
EVIDENCE = ROOT / "twins/reference-917-engine/evidence/f42-1-topology-repair"
SUMMARY = EVIDENCE / "917-head-f42-1-repair-summary.json"
FACE_MAP = EVIDENCE / "917-head-f42-1-face-map.json"
IMAGE = EVIDENCE / "917-head-f42-1-face-map.png"


def load_module():
    sys.path.insert(0, str(SOURCE.parent))
    spec = importlib.util.spec_from_file_location("repair_topology_f42_1", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable_to_load_F42_1_repair")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class F421TopologyRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repair = load_module()
        cls.summary_text = SUMMARY.read_text(encoding="utf-8")
        cls.summary = json.loads(cls.summary_text)
        cls.face_map_text = FACE_MAP.read_text(encoding="utf-8")
        cls.face_map = json.loads(cls.face_map_text)

    def test_synthetic_same_parameter_copy_shares_all_3d_geometry(self) -> None:
        original = BRepPrimAPI_MakeBox(20.0, 30.0, 10.0).Shape()
        candidate = self.repair.same_parameter_candidate(original, 1.0e-4)
        geometry = self.repair.shared_geometry_audit(original, candidate)
        delta = self.repair.property_delta(
            self.repair.shape_properties(original),
            self.repair.shape_properties(candidate),
        )
        self.assertTrue(geometry["all_3D_surfaces_identical"])
        self.assertTrue(geometry["all_3D_curves_identical_or_both_null"])
        self.assertEqual(delta["maximum_bbox_coordinate_delta_scan_units"], 0.0)
        self.assertAlmostEqual(delta["volume_delta_scan_units_cubed"], 0.0, places=9)
        self.assertAlmostEqual(delta["surface_area_delta_scan_units_squared"], 0.0, places=9)
        self.assertEqual(self.repair.pcurve_faults(candidate)["fault_count"], 0)

    def test_source_contains_no_surface_deformation_operation(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("BRepLib.SameParameter_s", source)
        self.assertIn("BRepBuilderAPI_Copy(original, False, False)", source)
        for forbidden in ("ShapeFix_Shape", "BRepOffset", "Sewing", "makeThickSolid"):
            self.assertNotIn(forbidden, source)

    def test_published_verdict_rejects_roundtrip_candidate(self) -> None:
        self.assertEqual(self.summary["verdict"], "REPAIR_REJECTED_FAIL_CLOSED")
        self.assertTrue(self.summary["gates"]["sampled_skin_distance_at_most_0_02"])
        self.assertFalse(self.summary["gates"]["zero_BOPAlgo_faults"])
        self.assertFalse(self.summary["gates"]["private_candidate_accepted_as_clean_repair"])
        self.assertFalse(self.summary["publication"]["source_STEP_published"])
        self.assertFalse(self.summary["publication"]["candidate_STEP_published"])
        self.assertFalse(
            self.summary["publication"]["scan_derived_face_or_sample_coordinates_published"]
        )
        self.assertNotIn("bbox_scan_units", self.face_map_text)
        self.assertNotIn("center_of_mass_scan_units", self.face_map_text)

    def test_face_map_and_image_are_bound_and_fail_closed(self) -> None:
        self.assertEqual(len(self.face_map["faces"]), 25)
        self.assertTrue(
            all(face["surface_type"] == "GeomAbs_BSplineSurface" for face in self.face_map["faces"])
        )
        self.assertEqual(
            sum(bool(face["BOP_self_intersect"]) for face in self.face_map["faces"]), 8
        )
        self.assertEqual(
            sum(bool(face["BOP_invalid_curve_on_surface"]) for face in self.face_map["faces"]), 23
        )
        self.assertFalse(self.face_map["gmsh"]["three_dimensional_mesh_completed"])
        self.assertEqual(IMAGE.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(
            hashlib.sha256(IMAGE.read_bytes()).hexdigest(), self.summary["image"]["sha256"]
        )
        self.assertEqual(
            hashlib.sha256(FACE_MAP.read_bytes()).hexdigest(),
            self.summary["face_reconstruction_map"]["sha256"],
        )


if __name__ == "__main__":
    unittest.main()
