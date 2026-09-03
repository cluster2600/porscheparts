#!/usr/bin/env python3
"""Test autonome des preuves publiées du paquet distribution F38."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "twins/reference-917-engine/evidence/f38-valvetrain-package"
REPORT_PATH = EVIDENCE / "f38-valvetrain-package-report.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class F38ValvetrainPackageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))

    def test_status_is_explicitly_fail_closed(self) -> None:
        self.assertEqual(self.report["phase"], "F38")
        self.assertIn("release_blocked", self.report["status"])
        self.assertIn("not_fitted_or_dynamically_validated", self.report["classification"])

    def test_architecture_counts(self) -> None:
        architecture = self.report["architecture"]
        expected = {
            "valves": 4,
            "guides": 4,
            "seats": 4,
            "springs": 8,
            "rocker_shafts": 2,
            "rockers": 4,
            "lower_spring_cups": 4,
            "upper_spring_retainers": 4,
            "total_separate_solids": 35,
        }
        for key, value in expected.items():
            self.assertEqual(architecture[key], value, key)
        self.assertTrue(architecture["separate_step_files"])
        self.assertFalse(architecture["published_monolithic_assembly"])

    def test_ten_separate_step_groups_are_hash_bound(self) -> None:
        artifacts = self.report["artifacts"]
        self.assertEqual(len(artifacts), 10)
        self.assertEqual(sum(item["component_count"] for item in artifacts), 35)
        for item in artifacts:
            step = item["step"]
            path = EVIDENCE / step["path"]
            self.assertTrue(path.is_file(), item["id"])
            self.assertEqual(path.stat().st_size, step["bytes"], item["id"])
            self.assertEqual(sha256(path), step["sha256"], item["id"])
            self.assertTrue(path.read_bytes().startswith(b"ISO-10303-21;\n"), item["id"])
            reopened = item["independent_reimport"]
            self.assertEqual(reopened["solid_count"], item["component_count"], item["id"])
            self.assertTrue(reopened["valid"], item["id"])
            self.assertTrue(reopened["manifold"], item["id"])
            self.assertTrue(reopened["all_solids_closed"], item["id"])

    def test_no_scan_or_monolithic_assembly_is_published(self) -> None:
        names = {path.name for path in EVIDENCE.rglob("*") if path.is_file()}
        self.assertNotIn("f38-four-valve-rocker-assembly.step", names)
        self.assertFalse(any(name.lower().endswith((".stl", ".obj", ".ply")) for name in names))
        self.assertFalse(any("scan" in name.lower() for name in names))

    def test_image_is_hash_bound_and_scan_free(self) -> None:
        image = self.report["image"]
        path = EVIDENCE / image["path"]
        self.assertEqual(path.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(path.stat().st_size, image["bytes"])
        self.assertEqual(sha256(path), image["sha256"])
        self.assertFalse(image["contains_scan_geometry"])

    def test_versioned_sources_are_hash_bound(self) -> None:
        for key in ("spec", "builder", "publisher", "renderer"):
            entry = self.report["inputs"][key]
            path = ROOT / entry["path"]
            self.assertTrue(path.is_file(), key)
            self.assertEqual(sha256(path), entry["sha256"], key)

    def test_structural_claim_is_not_inferred(self) -> None:
        status = self.report["structural_status"]
        self.assertTrue(status["f38_calculix_three_grid_screen_present"])
        self.assertEqual(status["mesh_sizes_mm"], [2.0, 1.5, 1.25])
        self.assertTrue(status["p99_grid_change_below_10_percent"])
        self.assertFalse(status["raw_maximum_grid_change_below_10_percent"])
        self.assertFalse(status["actual_resultant_direction_complete"])
        self.assertFalse(status["nonlinear_contact_complete"])
        self.assertFalse(status["qualified_material_card"])
        self.assertFalse(status["fatigue_and_thermal_cycle_complete"])
        self.assertFalse(status["f37_parent_linear_screen_transfer_allowed"])
        self.assertFalse(status["structural_proof"])

    def test_release_gates_remain_closed(self) -> None:
        gates = self.report["release_gates"]
        self.assertTrue(gates["all_published_step_roundtrips_valid_closed"])
        self.assertTrue(gates["component_counts_verified"])
        blocked = (
            "absolute_scale_confirmed",
            "porsche_917_mating_interfaces_confirmed",
            "cam_profile_measured",
            "kinematic_clearances_validated",
            "dynamic_valvetrain_correlated",
            "nonlinear_contacts_validated",
            "spring_surge_and_coil_bind_validated",
            "fatigue_and_thermal_cycles_validated",
            "qualified_material_cards",
            "structural_proof",
            "metal_print_authorized",
            "engine_start_authorized",
        )
        for gate in blocked:
            self.assertFalse(gates[gate], gate)


if __name__ == "__main__":
    unittest.main()
