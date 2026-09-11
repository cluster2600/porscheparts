"""Triage titane du catalogue d'usine : couverture et honnetete du perimetre.

Le criblage des fiches porte sur une trentaine de pieces, le catalogue d'usine
en compte pres de six mille. Ces tests existent pour que le depot ne puisse plus
laisser croire qu'il a regarde « tout le catalogue ».

Le triage de zones tourne sur les seules donnees du depot et est donc verifie
ici. Le triage piece a piece demande un releve de designations tenu hors du
depot : seule sa sortie publiee est controlee, et seulement si elle existe.
"""
from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SELECTION = ROOT / "twins/993-exhaust-tip-ti-f0/evidence/selection"
ZONES = SELECTION / "pet-zone-titanium-triage.json"
PARTS = SELECTION / "pet-part-titanium-triage.json"
TITANIUM = SELECTION / "titanium-candidate-screen.json"
SKELETON = ROOT / "catalog/reference/993-assembly-skeleton.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class PetTitaniumTriageTests(unittest.TestCase):
    def test_the_zone_triage_covers_every_illustration_of_the_skeleton(self) -> None:
        report = load(ZONES)
        skeleton = load(SKELETON)
        illustrations = sum(
            len(system["illustrations"]) for system in skeleton["systems"]
        )
        self.assertEqual(report["zones_screened"], illustrations)
        self.assertEqual(
            report["catalogue_reference_count"], skeleton["reference_count"]
        )

    def test_the_zone_triage_states_its_own_coverage_gap(self) -> None:
        report = load(ZONES)
        self.assertLess(report["part_record_coverage_percent"], 1.0)
        self.assertIn("copie de catalogue", report["why_not_finer"])
        self.assertEqual(report["granularity"], "illustration_group")

    def test_the_zone_triage_never_claims_to_select_a_part(self) -> None:
        report = load(ZONES)
        self.assertIn("not_a_part_selection", report["authority"])
        self.assertIn("n'est pas une piece", report["next_step"])

    def test_the_fiche_screen_is_not_presented_as_covering_the_catalogue(self) -> None:
        fiches = load(TITANIUM)
        zones = load(ZONES)
        self.assertLess(
            fiches["parts_screened"], zones["catalogue_reference_count"] / 100
        )

    def test_the_part_triage_when_published_keeps_the_catalogue_outside(self) -> None:
        if not PARTS.exists():
            self.skipTest("triage piece a piece non publie : releve PET hors depot")
        report = load(PARTS)
        self.assertIn("not_a_part_selection", report["authority"])
        self.assertIn("hors du depot", report["listing_source"])
        # Seule une liste courte est publiee, jamais le releve entier.
        self.assertLess(len(report["shortlist"]), report["distinct_descriptions"] / 4)
        self.assertTrue(report["limits"])

    def test_the_part_triage_reconfirms_the_selected_part(self) -> None:
        if not PARTS.exists():
            self.skipTest("triage piece a piece non publie : releve PET hors depot")
        report = load(PARTS)
        top = [item["description"] for item in report["shortlist"][:6]]
        self.assertIn("tail pipe", top)


if __name__ == "__main__":
    unittest.main()
