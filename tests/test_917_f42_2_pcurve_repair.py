#!/usr/bin/env python3
"""Autonomous F42.2 tests; no private STEP is required."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

try:
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
except ImportError:  # OCP is only required for the synthetic CAD test.
    BRepPrimAPI_MakeBox = None


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "twins/reference-917-engine/source/repair_pcurves_f42_2.py"
EVIDENCE = ROOT / "twins/reference-917-engine/evidence/f42-2-pcurve-repair"
SUMMARY = EVIDENCE / "917-head-f42-2-pcurve-repair-summary.json"
IMAGE = EVIDENCE / "917-head-f42-2-pcurve-diagnostic.png"


def load_module():
    sys.path.insert(0, str(SOURCE.parent))
    spec = importlib.util.spec_from_file_location("repair_pcurves_f42_2", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable_to_load_F42_2_repair")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class F422PcurveRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repair = load_module() if BRepPrimAPI_MakeBox is not None else None
        cls.summary_text = SUMMARY.read_text(encoding="utf-8")
        cls.summary = json.loads(cls.summary_text)

    @unittest.skipIf(BRepPrimAPI_MakeBox is None, "OCP is not installed")
    def test_clean_synthetic_box_needs_no_pcurve_repair(self) -> None:
        box = BRepPrimAPI_MakeBox(20.0, 30.0, 10.0).Shape()
        candidate, trial = self.repair.make_trial(box, None, 2.0e-2)
        self.assertEqual(trial["baseline_pcurve_faults"]["result_count"], 0)
        self.assertEqual(trial["repair"]["attempted_pair_count"], 0)
        self.assertEqual(trial["residual_pcurve_faults"]["result_count"], 0)
        self.assertTrue(trial["shared_geometry"]["all_3D_surfaces_identical"])
        self.assertTrue(trial["shared_geometry"]["all_3D_curves_identical_or_both_null"])
        self.assertIsNotNone(candidate)

    def test_source_excludes_surface_and_3d_curve_rebuilds(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("FixAddPCurve", source)
        self.assertIn("builder.UpdateEdge(edge, None, face, tolerance)", source)
        for forbidden in (
            "ShapeFix_Shape",
            "BRepOffset",
            "Sewing",
            "BuildCurves3d",
            "FixAddCurve3d",
            "FixRemoveCurve3d",
        ):
            self.assertNotIn(forbidden, source)

    def test_public_report_is_fail_closed_and_coordinate_free(self) -> None:
        self.assertEqual(self.summary["verdict"], "REPAIR_REJECTED_FAIL_CLOSED")
        self.assertFalse(self.summary["gates"]["roundtrip_zero_BOPAlgo_faults"])
        self.assertFalse(self.summary["gates"]["gmsh_3D_mesh_success"])
        self.assertFalse(self.summary["gates"]["private_candidate_accepted"])
        self.assertFalse(self.summary["publication"]["source_STEP_published"])
        self.assertFalse(self.summary["publication"]["candidate_STEP_published"])
        self.assertNotIn('"bbox_scan_units"', self.summary_text)
        self.assertNotIn('"center_of_mass_scan_units"', self.summary_text)

    def test_numeric_regression_and_image_binding(self) -> None:
        self.assertEqual(self.summary["mapped_25_face_trial"]["target_face_count"], 25)
        self.assertEqual(
            self.summary["diagnostic_expansion"]["pre_export_residual_pcurve_fault_count"],
            4,
        )
        self.assertGreater(
            self.summary["diagnostic_expansion"][
                "maximum_sampled_edge_surface_deviation_scan_units"
            ],
            0.02,
        )
        self.assertEqual(self.summary["pre_export_full_BOPAlgo"]["result_count"], 14)
        self.assertEqual(self.summary["roundtrip"]["full_BOPAlgo"]["result_count"], 246)
        self.assertEqual(IMAGE.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(
            hashlib.sha256(IMAGE.read_bytes()).hexdigest(),
            self.summary["image"]["sha256"],
        )


if __name__ == "__main__":
    unittest.main()
