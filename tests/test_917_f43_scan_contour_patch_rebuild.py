#!/usr/bin/env python3
"""Tests autonomes du paquet public F43, sans ouvrir la géométrie privée."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "twins/reference-917-engine/source/build_scan_contour_patch_reconstruction_f43.py"
AUDIT_SOURCE = ROOT / "twins/reference-917-engine/source/audit_scan_contour_patch_reconstruction_f43.py"
RENDER_SOURCE = ROOT / "twins/reference-917-engine/source/render_scan_contour_patch_reconstruction_f43.py"
EVIDENCE = ROOT / "twins/reference-917-engine/evidence/f43-scan-contour-patch"
REPORT = EVIDENCE / "f43-scan-contour-patch-report.json"
README = EVIDENCE / "README.md"
FOUR_VIEWS = EVIDENCE / "917-head-f43-scan-contour-4views.png"
SECTION = EVIDENCE / "917-head-f43-scan-contour-section.png"


class F43ScanContourPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(REPORT.read_text(encoding="utf-8"))
        cls.source_text = SOURCE.read_text(encoding="utf-8")

    def test_builder_has_no_global_envelope_primitive(self) -> None:
        tree = ast.parse(self.source_text)
        called_attributes = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        forbidden_calls = {"addEllipse", "addDisk", "addBox", "addCylinder", "addCone"}
        self.assertTrue(forbidden_calls.isdisjoint(called_attributes))
        self.assertNotIn("ellipse" + "_volume", self.source_text)
        construction = self.report["construction"]
        self.assertTrue(construction["body_and_fins_follow_irregular_scan_contours"])
        self.assertFalse(construction["forbidden_primitive_gate"]["global_ellipse_used"])
        self.assertFalse(construction["forbidden_primitive_gate"]["global_box_used"])
        self.assertEqual(construction["source_contour_count"], 44)
        self.assertEqual(construction["retained_contour_count"], 41)

    def test_publication_contains_no_private_geometry(self) -> None:
        forbidden_suffixes = {".step", ".stp", ".stl", ".msh", ".obj", ".ply"}
        self.assertTrue(forbidden_suffixes.isdisjoint(path.suffix.lower() for path in EVIDENCE.iterdir()))
        binding = self.report["private_geometry_binding"]
        self.assertIn("private_local_only", binding["repository_policy"])
        self.assertFalse(binding["STEP"]["published"])
        self.assertFalse(binding["surface_STL"]["published"])
        self.assertFalse(self.report["provenance"]["raw_scan_or_profiles_published"])

    def test_exact_brep_passes_but_quality_and_scope_fail_closed(self) -> None:
        roundtrip = self.report["roundtrip_OCCT"]
        self.assertTrue(roundtrip["BRepCheck_exact"]["shape_valid"])
        self.assertEqual(roundtrip["topology"]["solid_count"], 1)
        self.assertEqual(roundtrip["topology"]["shell_count"], 1)
        self.assertEqual(roundtrip["topology"]["free_edge_count"], 0)
        self.assertEqual(roundtrip["topology"]["nonmanifold_edge_count"], 0)
        self.assertEqual(roundtrip["pcurve_fault_count"], 0)
        self.assertFalse(roundtrip["BOPAlgo"]["has_faulty"])

        mesh = self.report["Gmsh_3D"]["refined_Delaunay_Relocate3D"]
        self.assertEqual(mesh["count_minSICN_le_0"], 0)
        self.assertEqual(mesh["count_minSICN_lt_0_1"], 378)
        self.assertFalse(mesh["strict_gate_passed"])
        self.assertFalse(self.report["scan_deviation_screen"]["lateral_skin"]["passed"])
        self.assertEqual(self.report["verdict"], "EXTERNAL_BREP_BASELINE_ONLY_FAIL_CLOSED")
        self.assertFalse(self.report["scope"]["CAE_ready"])
        self.assertFalse(self.report["scope"]["manufacturing_authorized"])
        self.assertFalse(self.report["scope"]["functional_internal_geometry_present"])

    def test_two_and_four_valve_variants_must_share_external_skin(self) -> None:
        self.assertTrue(self.report["scope"]["same_external_skin_for_future_2V_and_4V_variants"])
        unresolved = self.report["unresolved_gates"]
        self.assertFalse(unresolved["functional_2V_geometry"])
        self.assertFalse(unresolved["functional_4V_geometry"])
        self.assertFalse(unresolved["minimum_wall_thickness_at_least_1_5"])
        self.assertFalse(unresolved["trapped_void_audit"])

    def test_images_are_bound_to_report(self) -> None:
        for path, key in ((FOUR_VIEWS, "four_views"), (SECTION, "section")):
            self.assertEqual(path.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
            metadata = self.report["published_images"][key]
            self.assertEqual(path.stat().st_size, metadata["bytes"])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), metadata["sha256"])
        self.assertIn("base B-Rep externe uniquement", README.read_text(encoding="utf-8"))

    def test_all_reproduction_sources_exist(self) -> None:
        self.assertTrue(SOURCE.is_file())
        self.assertTrue(AUDIT_SOURCE.is_file())
        self.assertTrue(RENDER_SOURCE.is_file())


if __name__ == "__main__":
    unittest.main()
