#!/usr/bin/env python3
"""Vérifie la vidéo F39 sans la transformer en preuve physique."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "twins/reference-917-engine/evidence/f39-functional-video"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class F39FunctionalVideoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads((EVIDENCE / "publication.json").read_text(encoding="utf-8"))

    def test_video_is_bound_to_its_binary(self) -> None:
        video = self.report["video"]
        path = EVIDENCE / video["path"]
        self.assertEqual(path.stat().st_size, video["bytes"])
        self.assertEqual(digest(path), video["sha256"])

    def test_delivery_shape_is_exact(self) -> None:
        video = self.report["video"]
        self.assertEqual((video["width"], video["height"]), (1920, 1080))
        self.assertEqual(video["duration_s"], 26.0)
        self.assertEqual(video["fps"], 30)
        self.assertEqual(video["frames"], 780)
        self.assertFalse(video["audio"])

    def test_supporting_images_are_bound(self) -> None:
        for name, artifact in self.report["artifacts"].items():
            self.assertEqual(digest(EVIDENCE / name), artifact["sha256"])

    def test_animation_explains_four_valves_and_two_cooling_paths(self) -> None:
        mechanism = self.report["shown_mechanism"]
        self.assertEqual(mechanism["valves"], 4)
        self.assertEqual(mechanism["intake_valves"], 2)
        self.assertEqual(mechanism["exhaust_valves"], 2)
        self.assertEqual(len(mechanism["cooling_paths"]), 2)

    def test_video_does_not_open_release_gates(self) -> None:
        self.assertEqual(
            self.report["classification"],
            "explanatory_animation_not_solver_or_engine_test_evidence",
        )
        for name, value in self.report["release_gates"].items():
            self.assertFalse(value, name)


if __name__ == "__main__":
    unittest.main()
