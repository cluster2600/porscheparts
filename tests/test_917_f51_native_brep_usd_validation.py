#!/usr/bin/env python3
"""Tests fail-closed de la conversion privée B-Rep vers USD F51."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "twins/reference-917-engine/evidence/f51-native-usd-validation"
EVIDENCE = EVIDENCE_DIR / "native-brep-usd-f51.json"
F50 = ROOT / "twins/reference-917-engine/evidence/f50-native-brep/native-brep-mesh-f50.json"
SOURCE_DIR = ROOT / "twins/reference-917-engine/source"


class NativeBrepUsdF51Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        cls.f50 = json.loads(F50.read_text(encoding="utf-8"))

    def test_public_evidence_contains_no_private_geometry_or_coordinates(self) -> None:
        self.assertEqual(
            self.report["schema"],
            "porsche-917-f51-native-brep-usd-public-evidence/v1",
        )
        self.assertEqual(self.report["phase"], "F51")
        for suffix in ("*.brep", "*.step", "*.stl", "*.obj", "*.ply", "*.3mf", "*.npz", "*.usd", "*.usda", "*.usdc"):
            self.assertEqual(list(EVIDENCE_DIR.glob(suffix)), [], suffix)
        serialized = EVIDENCE.read_text(encoding="utf-8")
        for forbidden in ("/tmp/", "/f51/", "asset_path", "bbox_scan_units_private"):
            self.assertNotIn(forbidden, serialized)

    def test_workflow_is_validation_only_without_step_or_content_agents(self) -> None:
        workflow = self.report["workflow"]
        self.assertEqual(workflow["classification"], "validation_only")
        self.assertEqual(workflow["property_assignment_intent"], "skip")
        self.assertFalse(workflow["STEP_intermediate_used"])
        self.assertEqual(workflow["output_root"], "private_not_committed")
        self.assertEqual(self.report["NVIDIA_preflight"]["status"], "PASS")
        self.assertEqual(self.report["NVIDIA_preflight"]["content_agents_status"], "skipped")

    def test_no_scale_deformation_proxy_or_oval(self) -> None:
        policy = self.report["geometry_policy"]
        self.assertEqual(policy["scale_transform"], [1.0, 1.0, 1.0])
        for key in (
            "point_displacement_used",
            "surface_deformation_used",
            "anisotropic_scale_used",
            "proxy_used",
            "ellipse_or_oval_used",
            "STEP_intermediate_used",
            "material_assignment_used",
            "physics_authoring_used",
            "private_geometry_committed",
        ):
            self.assertFalse(policy[key], key)

    def test_two_variants_are_hash_linked_to_f50(self) -> None:
        self.assertEqual(set(self.report["variants"]), {"2V", "4V"})
        for name, variant in self.report["variants"].items():
            master = self.f50["native_OCCT_masters"][name]
            self.assertEqual(variant["source_native_BREP_sha256"], master["private_native_BREP_sha256"])
            self.assertTrue(master["accepted_as_private_same_kernel_CAD_CAE_master"])
            for key in ("surface_archive_sha256", "private_USD_sha256"):
                self.assertEqual(len(variant[key]), 64)
                int(variant[key], 16)
            self.assertGreater(variant["private_USD_bytes"], 1_000_000)

    def test_surface_and_usd_roundtrip_are_closed_and_scan_locked(self) -> None:
        for variant in self.report["variants"].values():
            tess = variant["tessellation"]
            usd = variant["USD_roundtrip"]
            self.assertEqual(tess["boundary_edge_count"], 0)
            self.assertEqual(tess["nonmanifold_edge_count"], 0)
            self.assertEqual(tess["winding_conflict_edge_count_after_index_reorientation"], 0)
            self.assertEqual(tess["connected_component_count"], 1)
            self.assertEqual(tess["degenerate_triangle_count"], 0)
            self.assertFalse(tess["reorientation_changed_coordinates"])
            self.assertLessEqual(tess["maximum_bbox_delta_from_native_BREP_scan_units"], 2.0e-6)
            self.assertLessEqual(tess["absolute_volume_relative_delta_from_native_BREP"], 5.0e-4)
            self.assertEqual(usd["component_count"], 1)
            self.assertEqual(usd["mesh_count"], 1)
            self.assertEqual(usd["point_count"], tess["point_count"])
            self.assertEqual(usd["triangle_count"], tess["triangle_count"])
            self.assertEqual(usd["normal_count"], tess["triangle_count"])
            self.assertEqual(usd["meters_per_unit"], 0.001)
            self.assertEqual(usd["up_axis"], "Z")
            self.assertEqual(usd["xform_op_count"], 0)
            self.assertEqual(usd["applied_schema_count"], 0)
            self.assertLessEqual(usd["maximum_bbox_delta_from_F43_scan_units"], 5.0e-6)
            self.assertLessEqual(usd["maximum_float32_coordinate_quantization_scan_units"], 5.0e-6)
            self.assertGreaterEqual(usd["normal_alignment_minimum"], 0.999999)

    def test_four_valve_winding_fix_changes_only_indices(self) -> None:
        four = self.report["variants"]["4V"]["tessellation"]
        self.assertEqual(four["winding_conflict_edge_count_before_index_reorientation"], 23)
        self.assertEqual(four["winding_conflict_edge_count_after_index_reorientation"], 0)
        self.assertEqual(four["triangle_index_records_reoriented"], 43)
        self.assertFalse(four["reorientation_changed_coordinates"])

    def test_nvidia_diagnostics_pass_but_formal_profile_is_blocked(self) -> None:
        for variant in self.report["variants"].values():
            for name, result in variant["validators"].items():
                self.assertTrue(result["passed"], name)
                self.assertEqual(result["status"], "PASS")
                self.assertEqual(result["issue_counts"].get("ERROR", 0), 0)
                self.assertEqual(result["issue_counts"].get("FAILURE", 0), 0)
            profile = variant["formal_SimReady_profile"]
            self.assertEqual(profile["target"], "Prop-Robotics-Neutral@2.1.0")
            self.assertEqual(profile["status"], "BLOCKED_NEEDS_RERUN")
            self.assertFalse(profile["passed"])
            self.assertEqual(profile["available_profile_count_reported_by_runtime"], 0)

    def test_release_gates_stay_closed(self) -> None:
        gates = self.report["gates"]
        for key in (
            "private_native_BREP_authority_accepted",
            "private_surface_tessellation_accepted",
            "private_USD_geometry_roundtrip_accepted",
            "NVIDIA_minimum_and_asset_geometry_diagnostics_accepted",
        ):
            self.assertTrue(gates[key], key)
        for key in (
            "formal_SimReady_profile_accepted",
            "OVRTX_render_validated",
            "manufacturing_authorized",
            "metal_print_authorized",
            "engine_start_authorized",
        ):
            self.assertFalse(gates[key], key)

    def test_reproducible_sources_are_present(self) -> None:
        for filename in (
            "tessellate_native_brep_for_usd_f51.py",
            "author_native_surface_usd_f51.py",
            "consolidate_native_usd_validation_f51.py",
        ):
            self.assertTrue((SOURCE_DIR / filename).is_file(), filename)


if __name__ == "__main__":
    unittest.main()
