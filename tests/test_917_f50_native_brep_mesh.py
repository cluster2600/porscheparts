#!/usr/bin/env python3
"""Tests fail-closed des preuves publiques F50 B-Rep/maillage."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = (
    ROOT
    / "twins/reference-917-engine/evidence/f50-native-brep/native-brep-mesh-f50.json"
)
SOURCE_DIR = ROOT / "twins/reference-917-engine/source"


class NativeBrepMeshF50Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    def test_evidence_is_public_metrics_only(self) -> None:
        self.assertEqual(
            self.report["schema"],
            "porsche-917-f50-native-brep-mesh-public-evidence/v1",
        )
        self.assertEqual(self.report["phase"], "F50")
        self.assertFalse(self.report["geometry_policy"]["private_geometry_committed"])
        for suffix in ("*.step", "*.brep", "*.stl", "*.msh", "*.node", "*.ele"):
            self.assertEqual(list(EVIDENCE.parent.glob(suffix)), [])

    def test_no_global_oval_or_skin_deformation(self) -> None:
        policy = self.report["geometry_policy"]
        self.assertTrue(policy["pcurve_reprojection_only"])
        self.assertTrue(policy["all_3D_surfaces_shared_with_input"])
        self.assertTrue(policy["all_3D_curves_shared_with_input"])
        self.assertFalse(policy["surface_or_curve_deformation_used"])
        self.assertFalse(policy["anisotropic_scale_used"])
        self.assertFalse(policy["global_ellipse_used"])
        self.assertFalse(policy["global_oval_used"])
        self.assertFalse(policy["global_box_used"])
        self.assertFalse(self.report["authority"]["outer_skin"]["deformed_by_F50"])

    def test_two_native_masters_pass_exact_roundtrip(self) -> None:
        masters = self.report["native_OCCT_masters"]
        self.assertEqual(set(masters), {"2V", "4V"})
        for variant in masters.values():
            result = variant["roundtrip"]
            self.assertEqual(result["BOP_fault_count"], 0)
            self.assertTrue(result["exact_BRepCheck_valid"])
            self.assertEqual(result["solid_count"], 1)
            self.assertEqual(result["shell_count"], 1)
            self.assertEqual(result["free_edge_count"], 0)
            self.assertEqual(result["nonmanifold_edge_count"], 0)
            self.assertEqual(result["bbox_maximum_coordinate_delta_scan_units"], 0.0)
            self.assertLess(result["volume_relative_delta"], 1.0e-8)
            self.assertTrue(variant["accepted_as_private_same_kernel_CAD_CAE_master"])
            self.assertEqual(len(variant["private_native_BREP_sha256"]), 64)

    def test_step_interoperability_remains_rejected(self) -> None:
        gate = self.report["STEP_interoperability"]
        self.assertFalse(gate["accepted"])
        self.assertEqual(len(gate["2V_profiles"]), 3)
        for profile in gate["2V_profiles"]:
            self.assertEqual(profile["BOP_InvalidCurveOnSurface_count"], 8)
            self.assertEqual(profile["unique_face_count"], 5)
            self.assertEqual(profile["unique_edge_count"], 8)

    def test_rejected_strategies_are_not_promoted(self) -> None:
        strategies = self.report["rejected_repair_strategies"]
        self.assertGreaterEqual(len(strategies), 5)
        self.assertTrue(all(item["accepted"] is False for item in strategies))
        faceted = next(item for item in strategies if "faceting" in item["id"])
        self.assertEqual(faceted["2V_roundtrip_BOP_fault_count"], 22)

    def test_gmsh_profiles_fail_strict_quality_gate(self) -> None:
        gmsh = self.report["Gmsh"]
        self.assertFalse(gmsh["strict_mesh_accepted"])
        generated = [
            profile
            for group in (gmsh["2V_profiles"], gmsh["4V_profiles"])
            for profile in group
            if "tetrahedra" in profile
        ]
        self.assertGreaterEqual(len(generated), 5)
        for profile in generated:
            self.assertFalse(profile["accepted"])
            self.assertGreater(profile["count_lt_0p1"], 0)
        self.assertGreater(
            gmsh["2V_profiles"][-1]["p01_minSICN"],
            gmsh["2V_profiles"][-2]["p01_minSICN"],
        )

    def test_tessellations_are_closed_and_volume_bounded(self) -> None:
        for variant in self.report["independent_tessellation"].values():
            self.assertTrue(variant["all_edge_incidence_equals_2"])
            self.assertEqual(
                variant["TetGen_self_intersection_check"],
                "PASS_NO_FACES_INTERSECTING",
            )
            self.assertLess(variant["absolute_volume_relative_delta_from_BREP"], 5.0e-4)

    def test_tetgen_is_independent_but_not_strictly_accepted(self) -> None:
        tetgen = self.report["TetGen"]
        self.assertFalse(tetgen["strict_mesh_accepted"])
        self.assertIn("not_equivalent", tetgen["metric_note"])
        self.assertGreaterEqual(len(tetgen["2V_profiles"]), 2)
        self.assertGreaterEqual(len(tetgen["4V_profiles"]), 1)
        for profiles in (tetgen["2V_profiles"], tetgen["4V_profiles"]):
            for profile in profiles:
                self.assertEqual(profile["count_le_0"], 0)
                self.assertGreater(profile["count_lt_0p1"], 0)
                self.assertFalse(profile["accepted"])

    def test_all_release_gates_remain_closed(self) -> None:
        gates = self.report["gates"]
        self.assertTrue(gates["native_same_kernel_CAD_CAE_master_accepted"])
        for key, value in gates.items():
            if key == "native_same_kernel_CAD_CAE_master_accepted":
                continue
            self.assertFalse(value, key)

    def test_reproducible_sources_are_present(self) -> None:
        for filename in (
            "build_native_brep_pcurve_master_f50.py",
            "export_native_brep_step_variants_f50.py",
            "mesh_native_brep_matrix_f50.py",
            "probe_native_brep_pcurves_f50.py",
            "probe_step_profiles_pcurves_f50.py",
            "tessellate_native_brep_surface_f50.py",
        ):
            self.assertTrue((SOURCE_DIR / filename).is_file(), filename)


if __name__ == "__main__":
    unittest.main()
