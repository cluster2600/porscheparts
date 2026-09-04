#!/usr/bin/env python3
"""Tests autonomes du paquet F49; aucune geometrie privee n'est requise."""

from __future__ import annotations

import hashlib
import json
import struct
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "twins/reference-917-engine"
CONTRACT = BASE / "internal-solid-repair-f49.json"
PUBLISHER = BASE / "source/publish_internal_solid_repair_f49.py"
RENDERER = BASE / "source/render_internal_solid_repair_f49.py"
EVIDENCE = BASE / "evidence/f49-solid"
REPORT = EVIDENCE / "f49-solid-public-report.json"
PUBLICATION = EVIDENCE / "publication.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class F49InternalSolidRepairTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = load(CONTRACT)
        cls.report = load(REPORT)
        cls.publication = load(PUBLICATION)

    def test_publication_is_reproducible(self) -> None:
        result = subprocess.run(
            [sys.executable, str(PUBLISHER), "--project-root", str(ROOT), "--check"],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("OK (fail-closed)", result.stdout)

    def test_authority_and_outer_skin_are_locked(self) -> None:
        self.assertEqual(self.contract["phase"], "F49")
        outer = self.contract["authority"]["outer_skin_F43_private"]
        self.assertEqual(outer["sha256"], "38f8ed3071005e5f64156d8670b5a755c98599d8702ef030ff132b7a034f0f24")
        lock = self.contract["geometry_lock"]
        self.assertFalse(lock["outer_skin_surface_edit_allowed"])
        self.assertFalse(lock["global_healing_or_sewing_allowed"])
        self.assertFalse(lock["anisotropic_scale_allowed"])
        self.assertFalse(lock["ellipse_or_oval_primitive_allowed"])
        self.assertFalse(lock["global_proxy_allowed"])
        self.assertEqual(lock["maximum_outer_skin_displacement_scan_units"], 0.0)
        observed = self.report["locked_outer_skin"]
        self.assertTrue(observed["same_exact_F43_source_bytes_loaded"])
        self.assertFalse(observed["surface_edit_operation_used"])
        self.assertFalse(observed["anisotropic_scale_used"])
        self.assertFalse(observed["ellipse_or_oval_primitive_used"])
        self.assertFalse(observed["global_proxy_used"])
        self.assertFalse(observed["external_face_signature_equal_outside_openings"])

    def test_anti_ellipse_and_no_geometry_generation(self) -> None:
        renderer = RENDERER.read_text(encoding="utf-8").lower()
        publisher = PUBLISHER.read_text(encoding="utf-8").lower()
        for forbidden_call in (
            "ellipse_volume(",
            "makeellipse(",
            "global_ellipse(",
            "global_box(",
            "anisotropic_scale(",
            "importshapes(",
            "write_step(",
        ):
            self.assertNotIn(forbidden_call, renderer)
            self.assertNotIn(forbidden_call, publisher)
        self.assertNotIn("import cadquery", renderer)
        self.assertNotIn("import gmsh", renderer)
        self.assertNotIn("import occ", renderer)
        self.assertEqual(
            self.report["images"]["classification"],
            "annotated_F47_scan_derived_visual_evidence_of_rejected_candidates_not_new_F49_geometry",
        )

    def test_roundtrip_failures_are_not_promoted(self) -> None:
        attempts = self.report["repair_attempts"]
        self.assertEqual(attempts["2V"]["baseline_F47"]["BOPAlgo_fault_count"], 8)
        self.assertEqual(attempts["4V"]["baseline_F47"]["BOPAlgo_fault_count"], 32)
        self.assertEqual(attempts["2V"]["individual_boolean_rebuild"]["faulty_face_count_private"], 5)
        self.assertEqual(attempts["2V"]["individual_boolean_rebuild"]["faulty_edge_count_private"], 8)
        repair = attempts["2V"]["bounded_pcurve_reprojection_surfacecurve_mode_1"]
        self.assertEqual(repair["pre_export_BOPAlgo_fault_count"], 0)
        self.assertEqual(repair["roundtrip_BOPAlgo_fault_count"], 8)
        self.assertFalse(repair["roundtrip_Gmsh_3D_attempted"])
        mode0 = attempts["2V"]["surfacecurve_mode_0"]
        self.assertEqual(mode0["roundtrip_BOPAlgo_fault_count"], 131)
        repair_4v = attempts["4V"]["bounded_pcurve_reprojection_surfacecurve_mode_1"]
        self.assertEqual(repair_4v["pre_export_BOPAlgo_fault_count"], 0)
        self.assertEqual(repair_4v["roundtrip_BOPAlgo_fault_count"], 32)
        self.assertFalse(repair_4v["roundtrip_Gmsh_3D_attempted"])
        self.assertFalse(attempts["2V"]["accepted"])
        self.assertFalse(attempts["4V"]["accepted"])
        self.assertFalse(self.report["Gmsh_policy"]["new_F49_head_mesh_created"])

    def test_oil_stays_separate_and_not_a_coolant_jacket(self) -> None:
        oil = self.report["oil_core"]
        self.assertTrue(oil["unchanged_from_F47"])
        self.assertTrue(oil["separate_from_gas"])
        self.assertFalse(oil["liquid_coolant_jacket"])
        self.assertEqual(oil["2V"]["BOPAlgo_fault_count"], 0)
        self.assertEqual(oil["4V"]["BOPAlgo_fault_count"], 0)
        self.assertFalse(oil["pressure_and_drainback_validated"])

    def test_wall_and_release_gates_remain_closed(self) -> None:
        wall = self.report["wall_and_ligament_audit"]
        self.assertEqual(wall["target_mm_if_one_scan_unit_equals_one_mm"], 1.5)
        self.assertEqual(wall["2V_minimum_nominal_ligament_scan_units"], 1.5)
        self.assertGreater(wall["4V_minimum_nominal_ligament_scan_units"], 3.15)
        self.assertFalse(wall["full_skin_to_void_map_completed"])
        self.assertFalse(wall["minimum_wall_1_5_mm_verified"])
        gates = self.report["release_gates"]
        for name in (
            "complete_outer_face_identity_proved",
            "2V_BOPAlgo_zero",
            "4V_BOPAlgo_zero",
            "2V_Gmsh_3D",
            "4V_Gmsh_3D",
            "minimum_wall_1_5_mm_verified",
            "no_trapped_powder_verified",
            "fitment_OEM_certified",
            "thermal_validated",
            "structural_validated",
            "fatigue_validated",
            "metal_print_authorized",
            "engine_start_authorized",
        ):
            self.assertFalse(gates[name], name)
        self.assertIn("FAIL_CLOSED", self.report["verdict"])
        self.assertIn("NOT_PRINTABLE", self.report["verdict"])

    def test_publication_hashes_and_images(self) -> None:
        for artifact in self.publication["artifacts"]:
            path = ROOT / artifact["path"]
            self.assertTrue(path.is_file(), artifact["path"])
            self.assertEqual(sha256(path), artifact["sha256"])
        self.assertFalse(self.publication["private_geometry_published"])
        expected = {
            "917-head-f49-scan-derived-exterior-four-views.png": (2560, 2060),
            "917-head-f49-2v-4v-sections.png": (2560, 1740),
        }
        for name, dimensions in expected.items():
            data = (EVIDENCE / name).read_bytes()
            self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(struct.unpack(">II", data[16:24]), dimensions)

    def test_no_private_geometry_or_coordinates_are_published(self) -> None:
        forbidden_suffixes = {".step", ".stp", ".stl", ".brep", ".obj", ".msh"}
        leaked = [p for p in EVIDENCE.rglob("*") if p.is_file() and p.suffix.lower() in forbidden_suffixes]
        self.assertEqual(leaked, [])
        policy = self.report["repository_policy"]
        self.assertFalse(policy["raw_scan_committed"])
        self.assertFalse(policy["private_STEP_STL_BREP_MSH_OBJ_committed"])
        self.assertFalse(policy["private_fault_indices_or_coordinates_committed"])
        public_text = REPORT.read_text(encoding="utf-8")
        self.assertNotIn("face_indices_private", public_text)
        self.assertNotIn("edge_indices_private", public_text)


if __name__ == "__main__":
    unittest.main()
