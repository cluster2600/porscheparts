"""Circuit d'huile de turbo : instruit, et maintenu ecarte.

Le triage a fait remonter `oil pipe` comme meilleur candidat additif du
catalogue d'usine. L'instruction conclut non, deux fois. Ces tests empechent la
conclusion de se relacher : le mode de rupture reste l'incendie, la piece reste
interdite, et le titane reste exclu par la grille du depot sur le filetage
repete — meme si quelqu'un, plus tard, trouvait la geometrie elegante.
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
SAFETY = ROOT / "SAFETY.md"

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
        self.assertIn("attribution reste à faire", limits)

    def test_the_fire_failure_mode_is_the_stated_reason(self) -> None:
        doc = DOC.read_text(encoding="utf-8")
        self.assertIn("incendie", doc)
        # Le depot definit lui-meme safety_critical par l'incendie.
        self.assertIn("incendie", SAFETY.read_text(encoding="utf-8"))

    def test_titanium_is_excluded_by_the_repository_own_grid(self) -> None:
        grid = GRID.read_text(encoding="utf-8")
        self.assertIn("grippage", grid)
        limits = " ".join(load(PART)["validation"]["known_limits"])
        self.assertIn("grippage", limits)

    def test_the_consolidation_case_is_recorded_not_denied(self) -> None:
        limits = " ".join(load(PART)["validation"]["known_limits"])
        self.assertIn("onze pièces", limits)


if __name__ == "__main__":
    unittest.main()
