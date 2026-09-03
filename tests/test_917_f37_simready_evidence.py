"""Contrôle hors ``work/`` des preuves Omniverse / SimReady F37."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "twins/reference-917-engine/evidence/f37-simready"
PUBLICATION = EVIDENCE / "publication.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name: str) -> dict:
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


class F37SimReadyEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.publication = load("publication.json")

    def test_manifest_hashes_every_published_evidence_file(self):
        declared = self.publication["files"]
        actual = {
            path.name
            for path in EVIDENCE.iterdir()
            if path.is_file() and path.name not in {"publication.json", "README.md"}
        }
        self.assertEqual(set(declared), actual)
        for name, digest in declared.items():
            self.assertEqual(sha256(EVIDENCE / name), digest, name)

    def test_no_full_head_geometry_is_published(self):
        forbidden = {".obj", ".ply", ".stl", ".3mf", ".usd", ".usda", ".usdc"}
        self.assertFalse([path.name for path in EVIDENCE.iterdir() if path.suffix.lower() in forbidden])
        self.assertFalse(self.publication["inputs"]["local_head_stl_committed"])
        self.assertFalse(self.publication["inputs"]["converted_usdc_committed"])

    def test_minimum_validation_and_render_really_passed(self):
        self.assertTrue(load("preflight.json")["status"] == "ready")
        self.assertTrue(load("minimum.json")["passed"])
        render = load("ovrtx-render.json")
        self.assertTrue(render["passed"])
        self.assertFalse(render["pixel_inspection"]["uniform"])
        self.assertEqual(render["triangle_count"], 857330)

    def test_nvidia_warning_is_preserved_and_blocks_consensus(self):
        for report_name in ("asset-validator.json", "geometry.json"):
            report = load(report_name)
            self.assertEqual(report["issue_counts"]["WARNING"], 1)
            self.assertEqual(report["issues"][0]["requirement"], "com.nvidia.usd.VG.007@1.0.0")
            self.assertEqual(report["issues"][0]["message"], "8047 vertices are non-manifold.")
        self.assertFalse(self.publication["release_gates"]["validator_consensus"])

    def test_no_visual_or_schema_step_opens_release_gates(self):
        self.assertFalse(self.publication["results"]["content_agents_completed"])
        self.assertFalse(self.publication["results"]["physics_solver_run_by_omniverse"])
        self.assertTrue(all(value is False for value in self.publication["release_gates"].values()))


if __name__ == "__main__":
    unittest.main()
