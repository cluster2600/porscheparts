#!/usr/bin/env python3
"""Tests autonomes des preuves publiques F47; aucun STEP prive n'est requis."""

from __future__ import annotations

import ast
import hashlib
import json
import math
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "twins/reference-917-engine/internal-brep-contract-f47.json"
BUILDER_PATH = ROOT / "twins/reference-917-engine/source/build_internal_brep_variants_f47.py"
RENDERER_PATH = ROOT / "twins/reference-917-engine/source/render_internal_brep_variants_f47.py"
EVIDENCE = ROOT / "twins/reference-917-engine/evidence/f47-internal-brep"
REPORT_PATH = EVIDENCE / "f47-internal-brep-public-report.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def nominal_minimum_ligament(variant: dict, bore_radius: float) -> float:
    circles: list[tuple[str, float, float, float]] = []
    for valve in variant["valves"]:
        x, y = valve["centre_xy_mm"]
        circles.append((valve["id"], x, y, 0.5 * valve["seat_envelope_diameter_mm"]))
    px, py = variant["spark_plug"]["centre_xy_mm"]
    circles.append(("spark_plug", px, py, 0.5 * variant["spark_plug"]["diameter_mm"]))
    clearances = [bore_radius - math.hypot(x, y) - radius for _, x, y, radius in circles]
    for index, (_, x1, y1, r1) in enumerate(circles):
        for _, x2, y2, r2 in circles[index + 1 :]:
            clearances.append(math.hypot(x2 - x1, y2 - y1) - r1 - r2)
    return min(clearances)


class F47InternalBRepEvidenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        cls.report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))

    def test_authority_and_same_locked_outer_skin(self) -> None:
        self.assertEqual(self.contract["phase"], "F47")
        outer = self.contract["authority"]["outer_skin_f43_private"]
        self.assertEqual(
            outer["sha256"],
            self.report["authority"]["outer_skin_F43_private"]["sha256"],
        )
        self.assertTrue(outer["same_exact_bytes_required_for_2v_and_4v"])
        self.assertFalse(outer["absolute_scale_certified"])
        self.assertTrue(self.report["construction"]["same_private_outer_STEP_bytes_loaded_for_2V_and_4V"])
        self.assertEqual(
            self.report["common_outer_envelope_OCCT"]["bbox_coordinate_maximum_difference_2V_vs_4V_scan_units"],
            0.0,
        )

    def test_builder_has_no_forbidden_global_primitive_call(self) -> None:
        tree = ast.parse(BUILDER_PATH.read_text(encoding="utf-8"))
        called_attributes = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertTrue({"addCylinder", "cut", "fuse"}.issubset(called_attributes))
        self.assertTrue(
            called_attributes.isdisjoint(
                {"addEllipse", "addDisk", "addBox", "addCone", "addTorus", "addWedge"}
            )
        )
        source = BUILDER_PATH.read_text(encoding="utf-8").lower()
        for forbidden_identifier in ("ellipse_volume", "global_ellipse", "global_oval", "global_box"):
            self.assertNotIn(forbidden_identifier + "(", source)
        policy = self.contract["geometry_policy"]
        self.assertFalse(policy["global_ellipse_allowed"])
        self.assertFalse(policy["global_oval_allowed"])
        self.assertFalse(policy["global_box_allowed"])

    def test_component_counts_and_separate_domains(self) -> None:
        for name, count in (("2V", 2), ("4V", 4)):
            variant = self.report["variants"][name]
            self.assertEqual(variant["separate_components"]["seat_count"], count)
            self.assertEqual(variant["separate_components"]["guide_count"], count)
            self.assertEqual(variant["separate_components"]["valve_count"], count)
            self.assertEqual(variant["separate_components"]["solid_count"], 3 * count)
            self.assertEqual(variant["gas_core"]["solid_count"], 1)
            self.assertEqual(variant["oil_core"]["solid_count"], 1)
            self.assertEqual(variant["gas_oil_separation"]["intersection_volume_scan_units_cubed"], 0.0)
            self.assertGreater(variant["gas_oil_separation"]["minimum_distance_scan_units"], 1.5)

    def test_nominal_ligaments_are_recomputed_but_not_called_wall_proof(self) -> None:
        bore_radius = 0.5 * self.contract["common_candidate_geometry"]["bore"]["diameter_mm"]
        for contract_name, report_name in (("2v", "2V"), ("4v", "4V")):
            expected = nominal_minimum_ligament(self.contract["variants"][contract_name], bore_radius)
            recorded = self.report["variants"][report_name]["analytic_functional_packaging_screen"]
            self.assertAlmostEqual(recorded["minimum_nominal_ligament_scan_units"], expected, places=9)
            self.assertFalse(recorded["global_wall_thickness_verified"])
        self.assertFalse(self.report["wall_thickness"]["gate_pass"])

    def test_fail_closed_when_BOP_Gmsh_and_thickness_fail(self) -> None:
        gates = self.report["release_gates"]
        for gate in (
            "two_valve_BOPAlgo_clean",
            "four_valve_BOPAlgo_clean",
            "two_valve_Gmsh_3D",
            "four_valve_Gmsh_3D",
            "gas_core_BOPAlgo_clean_both_variants",
            "minimum_wall_1_5_mm_verified",
            "no_trapped_powder_verified",
            "metal_print_authorized",
            "engine_start_authorized",
        ):
            self.assertFalse(gates[gate], gate)
        self.assertTrue(self.report["verdict"].startswith("FAIL_CLOSED"))

    def test_public_hashes_and_no_private_geometry(self) -> None:
        self.assertEqual(sha256(CONTRACT_PATH), self.report["authority"]["contract"]["sha256"])
        self.assertEqual(sha256(BUILDER_PATH), self.report["construction"]["builder"]["sha256"])
        self.assertEqual(sha256(RENDERER_PATH), self.report["images"]["renderer"]["sha256"])
        for key in ("four_views", "sections"):
            entry = self.report["images"][key]
            self.assertEqual(sha256(ROOT / entry["path"]), entry["sha256"])
        forbidden = {".step", ".stp", ".stl", ".obj", ".msh", ".brep"}
        leaked = [path for path in EVIDENCE.rglob("*") if path.is_file() and path.suffix.lower() in forbidden]
        self.assertEqual(leaked, [])
        self.assertFalse(self.report["repository_policy"]["raw_scan_committed"])
        self.assertFalse(self.report["repository_policy"]["private_SCAN_derived_STEP_STL_MSH_committed"])


if __name__ == "__main__":
    unittest.main()
