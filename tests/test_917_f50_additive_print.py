#!/usr/bin/env python3
"""Tests fail-closed de la qualification d'impression additive F50."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "twins/reference-917-engine"
EVIDENCE = BASE / "evidence/f50-additive-print"
CONTRACT = BASE / "additive-print-qualification-f50.json"
MANIFEST = EVIDENCE / "manifest.json"
LOCK = BASE / "f50-private-master-hash-lock.json"
MASTER_HASHES = {
    "2v": "1574eb58b7af09bcadab6c9cfcdd9a56940d479a5aa1b1eb807d31d41d4f7c36",
    "4v": "10ff1a2af8f2dbca78cf6ac2f72a9e1f2842e171f1e1e76080f07eacd4162131",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class F50AdditivePrintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = load(CONTRACT)
        cls.manifest = load(MANIFEST)
        cls.lock = load(LOCK)
        cls.geometry = {
            variant: load(EVIDENCE / f"geometry-{variant}/917-head-f50-{variant}-lpbf-geometry-report.json")
            for variant in ("2v", "4v")
        }
        cls.coupons = load(EVIDENCE / "additivefoam-coupons/917-head-f50-additivefoam-report.json")

    def test_private_native_masters_are_hash_locked_without_public_geometry(self) -> None:
        self.assertEqual(self.lock["master_hashes"], MASTER_HASHES)
        self.assertFalse(self.lock["contains_private_geometry"])
        self.assertFalse(self.lock["absolute_scale_certified"])
        self.assertEqual(self.contract["private_master_hash_lock"]["master_hashes"], MASTER_HASHES)
        self.assertFalse(self.contract["geometry_policy"]["private_geometry_published"])

    def test_no_oval_proxy_skin_change_or_anisotropic_scale(self) -> None:
        policy = self.contract["geometry_policy"]
        self.assertFalse(policy["scan_skin_modified"])
        self.assertFalse(policy["envelope_proxy_used"])
        self.assertFalse(policy["global_oval_or_ellipse_used"])
        self.assertFalse(policy["anisotropic_scaling_used"])
        self.assertEqual(policy["analysis_transforms"], "rigid rotations and translations only")
        for report in self.geometry.values():
            invariants = report["geometry_invariants"]
            self.assertFalse(invariants["scan_skin_modified"])
            self.assertFalse(invariants["envelope_proxy_used"])
            self.assertFalse(invariants["elliptic_or_oval_exterior_used"])
            self.assertFalse(invariants["anisotropic_scaling_used"])
            self.assertEqual(invariants["analysis_transform"], "rigid rotation and translation only")

    def test_full_piece_actual_slicing_has_all_50um_layers(self) -> None:
        for variant, report in self.geometry.items():
            slicing = report["full_build_slicing"]
            self.assertEqual(report["master"]["sha256"], MASTER_HASHES[variant])
            self.assertEqual(slicing["layer_thickness_mm"], 0.05)
            self.assertEqual(slicing["layer_count"], math.ceil(slicing["build_height_mm"] / 0.05))
            self.assertEqual(slicing["layer_count"], 4111)
            self.assertTrue(slicing["rigid_transform_only"])
            self.assertTrue(slicing["bare_part_nominal_fit"])
            self.assertGreater(slicing["layers_with_unsupported_area"], 0)
            csv_path = EVIDENCE / f"geometry-{variant}/917-head-f50-{variant}-layer-metrics.csv"
            with csv_path.open(encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), slicing["layer_count"])
            self.assertEqual([int(row["layer_index"]) for row in rows], list(range(slicing["layer_count"])))
            self.assertTrue(all(math.isfinite(float(row["z_mm"])) for row in rows))

    def test_machine_and_geometry_screens_are_explicitly_limited(self) -> None:
        machine = self.contract["machine_candidate"]
        self.assertEqual(machine["manufacturer"], "Velo3D")
        self.assertEqual(machine["model"], "Sapphire standard")
        self.assertEqual(machine["build_cylinder_diameter_mm"], 315.0)
        self.assertEqual(machine["build_height_mm"], 400.0)
        for report in self.geometry.values():
            self.assertGreater(report["thickness_screen"]["sample_fraction_below_1p5_mm"], 0.0)
            self.assertFalse(report["gates"]["minimum_wall_1p5mm_everywhere"])
            self.assertFalse(report["recoater_screen"]["pass"])
            self.assertFalse(report["closed_volume_gate"]["final_pass"])
            self.assertFalse(report["machining_and_support_gate"]["pass"])

    def test_additivefoam_campaign_is_local_hash_linked_and_not_full_head(self) -> None:
        self.assertEqual(self.coupons["master_hashes"], MASTER_HASHES)
        self.assertEqual(self.coupons["software"]["additivefoam_revision"], "9c05c5eb54db03faa342b14b0806efe740de8c44")
        self.assertEqual(len(self.coupons["cases"]), 4)
        self.assertTrue(self.coupons["two_variant_process_binding"]["shared_local_witness"])
        self.assertTrue(self.coupons["gates"]["four_hash_linked_solver_runs_completed"])
        self.assertFalse(self.coupons["gates"]["all_numerical_case_gates_passed"])
        self.assertFalse(self.coupons["representativity"]["full_head_distortion_simulated"])
        self.assertFalse(self.coupons["material_model"]["target_CP1_card_used"])
        for case in self.coupons["cases"].values():
            self.assertTrue(case["completed"])
            self.assertTrue(case["finite"])
            self.assertEqual(case["layer_thickness_mm"], 0.05)
            self.assertEqual(case["vtk_state_count"], 6)
            self.assertEqual(case["temperature_cap_hit"], case["temperature_max_k"] >= 3299.0)
            self.assertEqual(
                case["numerical_case_pass"],
                case["completed"] and case["finite"] and case["maximum_courant_number"] <= 0.5 and not case["temperature_cap_hit"],
            )

    def test_public_manifest_hashes_and_formats(self) -> None:
        self.assertFalse(self.manifest["private_geometry_published"])
        for entry in self.manifest["entries"]:
            path = ROOT / entry["path"]
            self.assertTrue(path.is_file(), entry["path"])
            self.assertEqual(sha256(path), entry["sha256"])
            self.assertEqual(path.stat().st_size, entry["bytes"])
        image = EVIDENCE / "media/917-head-f50-lpbf-process-dashboard.png"
        video = EVIDENCE / "media/917-head-f50-lpbf-process.mp4"
        self.assertEqual(image.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(video.read_bytes()[4:8], b"ftyp")
        self.assertGreater(video.stat().st_size, 100_000)

    def test_no_private_paths_or_geometry_in_public_evidence(self) -> None:
        forbidden_suffixes = {".brep", ".step", ".stp", ".stl", ".obj", ".msh", ".inp", ".frd", ".vtk", ".vtp"}
        leaked = [path for path in EVIDENCE.rglob("*") if path.is_file() and path.suffix.lower() in forbidden_suffixes]
        self.assertEqual(leaked, [])
        for path in EVIDENCE.rglob("*"):
            if path.suffix.lower() not in {".json", ".csv", ".md"} or not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("/tmp/", text, str(path))
            self.assertNotIn("/workspace/", text, str(path))
            self.assertNotIn('"case_path"', text, str(path))

        audit_source = (BASE / "source/run_f50_lpbf_geometry_audit.py").read_text(encoding="utf-8")
        self.assertNotIn("EXPECTED_BOUNDS", audit_source)
        self.assertIn('parser.add_argument("--expected-bounds-lock"', audit_source)
        self.assertIn("private_bounds_lock_identity_mismatch", audit_source)

    def test_every_physical_release_gate_remains_red(self) -> None:
        gates = self.contract["release_gates"]
        for name in (
            "minimum_wall_1p5mm_everywhere",
            "supplier_support_topology_validated",
            "support_removal_access_validated",
            "recoater_collision_with_distorted_part_validated",
            "powder_removal_physically_validated",
            "target_CP1_hot_material_card_used",
            "full_piece_thermomechanical_distortion_converged",
            "supplier_machine_file_signed",
            "physical_coupon_qualified",
            "ct_or_endoscopy_completed",
            "metal_print_authorized",
            "engine_start_authorized",
        ):
            self.assertFalse(gates[name], name)


if __name__ == "__main__":
    unittest.main()
