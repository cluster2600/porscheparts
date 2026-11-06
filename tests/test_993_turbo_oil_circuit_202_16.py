"""Turbo oil circuit: investigated, and kept out.

Triage surfaced `oil pipe` as the best additive candidate in the factory
catalogue. The investigation concludes no, twice. These tests stop that
conclusion from loosening: the failure mode remains fire, the part remains
prohibited, and titanium remains excluded by the repository grid on repeated
threading — even if someone later finds the geometry elegant.
"""
from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PART = ROOT / "catalog/parts/993-eng-turbo-oil-return-line-in625-f0-0001.json"
SOURCE = ROOT / "catalog/sources/src-pet-993-202-16-turbo-oil-circuit.json"
DOC = ROOT / "docs/993/993_CIRCUIT_HUILE_TURBO_202-16.md"
GRID = ROOT / "docs/TITANIUM.md"
SAFETY = ROOT / "docs" / "SAFETY.md"

CIRCUIT_REFERENCES = (
    "993 107 125 53",
    "993 107 126 53",
    "993 107 338 53",
    "993 107 339 53",
)


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class TurboOilCircuitTests(unittest.TestCase):
    def test_the_identity_is_established_and_recorded(self) -> None:
        part = load(PART)
        for reference in CIRCUIT_REFERENCES:
            self.assertIn(reference, part["vehicle"]["porsche_part_numbers"])
        self.assertTrue(SOURCE.exists())
        self.assertEqual(load(SOURCE)["quality"]["evidence_level"], "A")

    def test_the_part_stays_prohibited(self) -> None:
        part = load(PART)
        self.assertEqual(
            part["classification"]["safety_class"], "prohibited_pending_engineering"
        )

    def test_the_feed_return_attribution_is_declared_unestablished(self) -> None:
        limits = " ".join(load(PART)["validation"]["known_limits"])
        self.assertIn("attribution remains to be done", limits)

    def test_the_fire_failure_mode_is_the_stated_reason(self) -> None:
        doc = DOC.read_text(encoding="utf-8")
        self.assertIn("fire", doc)
        # Le depot definit lui-meme safety_critical par l'incendie.
        self.assertRegex(SAFETY.read_text(encoding="utf-8"), r"\bfire\b")

    def test_titanium_is_excluded_by_the_repository_own_grid(self) -> None:
        grid = GRID.read_text(encoding="utf-8")
        self.assertIn("galling", grid)
        limits = " ".join(load(PART)["validation"]["known_limits"])
        self.assertIn("galling", limits)

    def test_the_consolidation_case_is_recorded_not_denied(self) -> None:
        limits = " ".join(load(PART)["validation"]["known_limits"])
        self.assertIn("eleven fluid or retention parts", limits)


if __name__ == "__main__":
    unittest.main()
