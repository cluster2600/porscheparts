#!/usr/bin/env python3
"""Contrôles fail-closed du porte-axes et de l'assemblage F38."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "twins/reference-917-engine/f38-rocker-carrier-redesign.json"
WORK = ROOT / "work/917-rocker-carrier-f38"
CAD = WORK / "cad/f38-rocker-carrier-cad-report.json"
SEQUENCE = WORK / "sequence/f38-valvetrain-sequence-report.json"
RENDER = WORK / "renders/f38-scan-assembly-render-report.json"
FEA = WORK / "calculix/f38-carrier-calculix-report.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@unittest.skipUnless(
    CAD.is_file() and SEQUENCE.is_file() and RENDER.is_file(),
    "artefacts locaux F38 porte-axes non générés",
)
class F38RockerCarrierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.spec = load(SPEC)
        cls.cad = load(CAD)
        cls.sequence = load(SEQUENCE)
        cls.render = load(RENDER)

    def test_contract_is_derived_and_release_remains_closed(self) -> None:
        self.assertEqual(self.spec["phase"], "F38")
        self.assertEqual(self.spec["parent_evidence"]["f37_calculix_report"]["finest_raw_maximum_mpa"], 208.73422210552775)
        self.assertTrue(all(value is False for value in self.spec["release_gates"].values()))
        self.assertFalse(self.spec["fea_screen"]["qualified_material_card"])
        self.assertFalse(self.spec["fea_screen"]["nonlinear_contact_complete"])

    def test_separate_step_components_and_counts(self) -> None:
        artifacts = {item["id"]: item for item in self.cad["artifacts"]}
        expected = {
            "rocker-carrier-f38-rounded-reinforced": 1,
            "four-rockers-f38": 4,
            "two-rocker-shafts-f38": 2,
            "two-intake-valves-f38": 2,
            "two-exhaust-valves-f38": 2,
            "four-valve-guides-f38": 4,
            "four-valve-seats-f38": 4,
            "eight-valve-springs-f38": 8,
            "four-lower-spring-cups-f38": 4,
            "four-upper-spring-retainers-f38": 4,
            "f38-four-valve-rocker-assembly": 35,
        }
        self.assertEqual(set(artifacts), set(expected))
        for identifier, count in expected.items():
            self.assertEqual(artifacts[identifier]["created"]["solid_count"], count)
            step = WORK / "cad" / artifacts[identifier]["step"]["path"]
            self.assertTrue(step.is_file(), identifier)
            self.assertEqual(sha256(step), artifacts[identifier]["step"]["sha256"])

    def test_bounded_roundtrip_limits_are_not_hidden(self) -> None:
        checks = self.cad["checks"]
        self.assertTrue(checks["assembly_step_delivered"])
        self.assertFalse(checks["assembly_step_roundtrip_verified"])
        self.assertFalse(checks["spring_step_roundtrip_verified"])
        self.assertFalse(checks["all_step_roundtrips_valid_closed"])

    def test_scan_conforming_skin_is_used_by_both_views(self) -> None:
        self.assertEqual(self.render["phase"], "F38")
        self.assertEqual(self.render["head"]["sha256"], "3c7159d47be2cd4632ae823a272f73514c784b0659207c002e34c9dc7e49fbbb")
        self.assertEqual(len(self.render["views"]), 2)
        self.assertTrue(all(not view["missing_components"] for view in self.render["views"]))
        self.assertTrue(all(value is False for value in self.render["gates"].values()))

    def test_conditional_sequence_has_36_frames_and_three_key_states(self) -> None:
        self.assertEqual(self.sequence["frame_count"], 36)
        self.assertEqual(set(self.sequence["key_states"]), {"closed", "mid_lift", "open"})
        self.assertIn("not_dynamic_simulation", self.sequence["classification"])
        self.assertTrue(all(value is False for value in self.sequence["gates"].values()))
        for item in self.sequence["frames"]:
            path = WORK / "sequence" / item["path"]
            self.assertEqual(sha256(path), item["sha256"])

    def test_calculix_three_grid_report_when_present(self) -> None:
        if not FEA.is_file():
            self.skipTest("F38 CalculiX report not generated in bounded run")
        report = load(FEA)
        self.assertEqual(report["phase"], "F38")
        self.assertEqual(len(report["cases"]), 3)
        self.assertEqual([item["mesh"]["mesh_size_mm"] for item in report["cases"]], [2.0, 1.5, 1.25])
        self.assertFalse(report["gates"]["qualified_material_card"])
        self.assertFalse(report["gates"]["nonlinear_contact_complete"])
        self.assertFalse(report["gates"]["metal_print_authorized"])
        self.assertFalse(report["gates"]["engine_start_authorized"])


if __name__ == "__main__":
    unittest.main()
