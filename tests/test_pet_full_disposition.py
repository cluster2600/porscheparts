"""Disposition de tout le catalogue d'usine : plus une seule perte silencieuse.

Les criblages publiaient ce qu'ils retenaient, et 956 designations sur 1 026
tombaient sans motif. C'est ainsi que `oil pipe` puis `pulley` se sont perdus,
et c'est ce que ces tests interdisent desormais.

Le dernier test garde l'aveu qui compte : une designation generique nomme une
forme, pas une fonction, et ne peut pas etre jugee a ce niveau. Le rapport doit
continuer a le dire et a compter ce qu'il laisse ouvert.
"""
from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SELECTION = ROOT / "twins/993-exhaust-tip-ti-f0/evidence/selection"
DISPOSITION = SELECTION / "pet-full-disposition.json"
VERDICT = SELECTION / "pet-candidate-verdict.json"
JUDGEMENTS = ROOT / "catalog/manufacturing/pet-candidate-judgements.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class PetFullDispositionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.report = load(DISPOSITION)

    def test_every_designation_is_disposed_of(self) -> None:
        counted = sum(
            bucket["designations"] for bucket in self.report["counts"].values()
        )
        self.assertEqual(counted, self.report["designations_total"])
        self.assertEqual(self.report["silently_dropped"], 0)

    def test_nothing_is_left_without_a_call(self) -> None:
        remaining = self.report["counts"].get("needs_a_human_call", {"designations": 0})
        self.assertEqual(remaining["designations"], 0)
        self.assertEqual(self.report["remaining_to_judge"], [])

    def test_every_category_has_a_written_definition(self) -> None:
        for category in self.report["counts"]:
            with self.subTest(category=category):
                self.assertIn(category, self.report["categories"])
                self.assertTrue(self.report["categories"][category].strip())

    def test_every_row_carries_a_category(self) -> None:
        for row in self.report["rows"]:
            with self.subTest(designation=row["description"]):
                self.assertIn(row["category"], self.report["categories"])

    def test_the_generic_gap_is_measured_and_declared(self) -> None:
        """Ce que le depot ne sait pas faire doit rester compte, pas masque."""
        generic = self.report["counts"].get("generic_designation")
        self.assertIsNotNone(generic)
        self.assertGreater(generic["designations"], 0)
        self.assertIn("reference par reference", self.report["what_this_does_not_do"])
        self.assertEqual(
            len(self.report["generic_designations"]), generic["designations"]
        )

    def test_the_verdict_reaches_designations_the_vocabulary_had_missed(self) -> None:
        """`muffler` n'etait pas dans les 70 du triage lexical. Une fois juge a
        la main, il doit remonter dans le gisement."""
        backlog = {row["description"] for row in load(VERDICT)["backlog"]}
        self.assertIn("muffler", backlog)
        self.assertIn("tail pipe", backlog)

    def test_the_judgement_layer_covers_what_the_disposition_says_it_covers(self) -> None:
        judged_rows = {
            row["description"]
            for row in self.report["rows"]
            if row["category"] == "judged"
        }
        judgements = set(load(JUDGEMENTS)["parts"])
        self.assertEqual(judged_rows - judgements, set())


if __name__ == "__main__":
    unittest.main()
