#!/usr/bin/env python3
"""Tests autonomes du controle B-Rep F42 (aucun STEP prive requis)."""

from __future__ import annotations

import importlib.util
import hashlib
import json
from pathlib import Path
import unittest

try:
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
except ModuleNotFoundError:  # Optional heavy CAD runtime; static gates still run.
    BRepPrimAPI_MakeBox = None


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "twins/reference-917-engine/source/audit_brep_f42.py"
PUBLIC_REPORT = (
    ROOT
    / "twins/reference-917-engine/evidence/f42-brep-audit/917-head-f42-brep-audit-summary.json"
)
PUBLIC_IMAGE = PUBLIC_REPORT.with_name("917-head-f42-brep-audit.png")


def load_module():
    spec = importlib.util.spec_from_file_location("audit_brep_f42", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable_to_load_F42_audit")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class F42BrepAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_module() if BRepPrimAPI_MakeBox is not None else None

    @unittest.skipIf(BRepPrimAPI_MakeBox is None, "OCP CAD runtime not installed")
    def test_closed_synthetic_box_is_one_valid_manifold_solid(self) -> None:
        shape = BRepPrimAPI_MakeBox(20.0, 30.0, 10.0).Shape()
        topology = self.audit.topology(shape)
        check = self.audit.brepcheck(shape)
        properties = self.audit.shape_properties(shape)
        self.assertEqual(topology["unique_subshape_counts"]["solid"], 1)
        self.assertEqual(topology["unique_subshape_counts"]["shell"], 1)
        self.assertEqual(topology["edge_classification"]["free_edges"], 0)
        self.assertEqual(topology["edge_classification"]["nonmanifold_edges"], 0)
        self.assertTrue(check["shape_valid"])
        self.assertAlmostEqual(properties["volume_scan_units_cubed"], 6000.0, places=6)

    @unittest.skipIf(BRepPrimAPI_MakeBox is None, "OCP CAD runtime not installed")
    def test_exact_chords_of_box_ignore_sampling_triangulation_seams(self) -> None:
        shape = BRepPrimAPI_MakeBox(20.0, 30.0, 10.0).Shape()
        result = self.audit.exact_normal_chord_thickness(
            shape,
            requested_samples=6,
            seed=42,
            tessellation_deflection=1.0,
            threshold=9.99,
        )
        self.assertEqual(result["resolved_samples"], 6)
        self.assertEqual(result["unresolved_samples"], 0)
        self.assertAlmostEqual(result["minimum_scan_units"], 10.0, places=5)
        self.assertTrue(result["gate_all_sampled_exact_normal_chords_at_or_above_threshold"])
        self.assertFalse(result["gate_global_wall_thickness_proven"])
        self.assertIn("sampling_only", result["tessellation_role"])

    def test_script_is_fail_closed_and_never_writes_a_step(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("FAIL_CLOSED_NOT_PRINTABLE_NOT_FITMENT_CERTIFIED", source)
        self.assertIn("private_local_only_not_copied_to_git", source)
        self.assertIn('"private_F42_STEP_produced": False', source)
        self.assertNotIn("STEPControl_Writer", source)
        self.assertNotIn("ShapeFix_Shape", source)

    def test_public_report_has_no_private_coordinates_or_geometry(self) -> None:
        report_text = PUBLIC_REPORT.read_text(encoding="utf-8")
        report = json.loads(report_text)
        self.assertEqual(report["phase"], "F42")
        self.assertEqual(report["verdict"], "FAIL_CLOSED_NOT_PRINTABLE_NOT_FITMENT_CERTIFIED")
        self.assertFalse(report["publication"]["raw_STEP_published"])
        self.assertFalse(report["publication"]["repaired_STEP_published"])
        self.assertNotIn("point_scan_units", report_text)
        self.assertNotIn("faulty_shape_bboxes", report_text)
        self.assertEqual(len(report["private_evidence_binding"]["input_sha256"]), 64)
        self.assertFalse(report["gates"]["zero_boolean_argument_faults"])
        self.assertFalse(report["gates"]["all_sampled_exact_chords_at_least_threshold"])
        self.assertFalse(report["independent_gmsh_screen"]["three_dimensional_mesh_completed"])
        self.assertEqual(
            len(report["independent_gmsh_screen"]["unique_surfaces_with_invalid_element_warning"]),
            25,
        )
        self.assertEqual(PUBLIC_IMAGE.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(
            hashlib.sha256(PUBLIC_IMAGE.read_bytes()).hexdigest(),
            report["public_image"]["sha256"],
        )


if __name__ == "__main__":
    unittest.main()
