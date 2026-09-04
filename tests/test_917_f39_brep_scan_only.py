"""Contrat autonome des preuves geometriques F39 scan-only."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "twins/reference-917-engine/f39-brep-scan-only.json"
EVIDENCE = ROOT / "twins/reference-917-engine/evidence/f39-brep-scan-only"
REPORT_PATH = EVIDENCE / "f39-brep-validation-report.json"
BUILD_PATH = EVIDENCE / "f39-brep-build-report.json"
STEP_PATH = EVIDENCE / "f39-brep-scan-only-head.step"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class F39BrepScanOnlyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        cls.report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        cls.build = json.loads(BUILD_PATH.read_text(encoding="utf-8"))

    def test_unit_and_fitment_are_explicitly_uncertified(self) -> None:
        unit = self.contract["unit_convention"]
        self.assertTrue(unit["scan_unit_treated_as_mm"])
        self.assertFalse(unit["metrologically_confirmed"])
        self.assertFalse(unit["oem_fitment_certified"])
        self.assertFalse(unit["additional_dimensions_available"])

    def test_published_step_is_analytic_and_hash_locked(self) -> None:
        master = self.report["geometry_master"]
        self.assertEqual(master["role"], "analytic_OCC_STEP_master_not_scan_mesh")
        self.assertEqual(master["sha256"], sha256(STEP_PATH))
        self.assertEqual(master["sha256"], self.build["files"]["step"]["sha256"])
        self.assertEqual(self.report["contract_sha256"], sha256(CONTRACT_PATH))
        self.assertGreater(STEP_PATH.stat().st_size, 1_000_000)

    def test_step_roundtrip_and_volume_mesh_are_real_but_quality_fails(self) -> None:
        geometry = self.build["geometry"]
        mesh = self.report["step_volume_mesh"]
        self.assertEqual(geometry["step_reimport_volume_count"], 1)
        self.assertTrue(mesh["gmsh_success"])
        self.assertGreater(mesh["nodes"], 80_000)
        self.assertGreater(mesh["volume_elements"], 350_000)
        self.assertEqual(mesh["elements_minSICN_le_0"], 0)
        self.assertEqual(mesh["elements_minSICN_lt_0_1"], 34)
        self.assertGreater(mesh["minimum_minSICN"], 0.0)
        self.assertFalse(mesh["quality_gate_minSICN_above_0_1"])

    def test_no_closed_void_screen_passes_at_three_resolutions(self) -> None:
        topology = self.report["topology_and_open_voids"]
        self.assertEqual(topology["step_boundary_shell_components"], 1)
        self.assertEqual(topology["closed_internal_shells_detected"], 0)
        self.assertTrue(topology["surface_stl_watertight"])
        self.assertEqual(topology["surface_stl_body_count"], 1)
        results = topology["voxel_resolution_study"]
        self.assertEqual([row["pitch_mm_if_unit_convention_holds"] for row in results], [2.0, 1.5, 1.0])
        self.assertTrue(all(row["trapped_void_volume_mm3"] == 0.0 for row in results))
        self.assertTrue(topology["zero_at_all_three_resolutions"])

    def test_minimum_wall_is_fail_closed(self) -> None:
        wall = self.report["minimum_wall"]
        named = wall["named_analytic_features"]
        sampled = wall["independent_sampled_mesh"]
        self.assertGreaterEqual(named["minimum_mm"], 1.5)
        self.assertFalse(named["proves_global_post_boolean_minimum"])
        self.assertEqual(sampled["sample_count"], 2400)
        self.assertLess(sampled["p01_mm_if_scale_is_mm"], 1.5)
        self.assertFalse(sampled["p01_gate_passes"])
        self.assertFalse(wall["global_minimum_1_5_mm_proven"])

    def test_scan_is_not_distributed_and_fit_is_not_claimed(self) -> None:
        policy = self.report["input_policy"]
        self.assertFalse(policy["raw_or_scan_derived_geometry_published"])
        self.assertNotIn("scan.stl", {path.name for path in EVIDENCE.iterdir()})
        conformance = self.report["scan_conformance"]
        self.assertIn("not_exact_Hausdorff", conformance["method"])
        self.assertFalse(conformance["scale_or_fitment_certification"])

    def test_images_exist_and_are_readable_png(self) -> None:
        for name in ("f39-brep-exterior.png", "f39-brep-section.png", "f39-brep-scan-overlay.png"):
            path = EVIDENCE / name
            payload = path.read_bytes()
            self.assertEqual(payload[:8], b"\x89PNG\r\n\x1a\n")
            width, height = struct.unpack(">II", payload[16:24])
            self.assertGreaterEqual(width, 1200)
            self.assertGreaterEqual(height, 700)

    def test_all_release_authorizations_remain_false(self) -> None:
        release = self.report["release_decision"]
        self.assertFalse(release["minimum_wall_gate_passed"])
        self.assertFalse(release["mesh_quality_gate_passed"])
        self.assertFalse(release["oem_fitment_certified"])
        self.assertFalse(release["metal_print_authorized"])
        self.assertFalse(release["engine_start_authorized"])
        self.assertTrue(all(value is False for value in self.report["release_gates"].values()))


if __name__ == "__main__":
    unittest.main()
