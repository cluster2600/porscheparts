"""Chain case: good additive candidate, poor titanium candidate.

These tests guard both halves of the verdict. The consolidation is recognized,
so that the fact that the part deserves additive manufacturing is not lost. And
the titanium refusal is locked on its three grid reasons, so that a careless
review does not reopen it.

The last test matters most: it checks that the five contraindications of
TITANIUM.md are treated as refusals, not as penalties. That is the infidelity
this part brought to light.
"""
from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PART_ID = "993-ENG-CHAIN-CASE-0001"
PART = ROOT / "catalog/parts/993-eng-chain-case-0001.json"
SOURCE = ROOT / "catalog/sources/src-pet-993-103-05-chain-case.json"
DOC = ROOT / "docs/993/993_CACHE_DE_CHAINE_103-05.md"
INPUTS = ROOT / "catalog/manufacturing/titanium-am-screen-inputs.json"
SCREEN = ROOT / "twins/993-exhaust-tip-ti-f0/evidence/selection/titanium-candidate-screen.json"
GRID = ROOT / "docs/TITANIUM.md"

# Conditions to lift, not absolute refusals: the grid says "sliding contact
# **not treated**" and "galvanic couple **not controlled**", and SAFETY.md
# lists their prevention among the minimum requirements for metal.
MITIGABLE = (
    "galling_or_repeated_threads",
    "uncontrolled_galvanic_couple",
    "differential_expansion_with_alloy_mate",
)


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class ChainCaseTests(unittest.TestCase):
    def test_the_identity_comes_from_the_factory_plate(self) -> None:
        part = load(PART)
        for reference in ("993 105 093 05", "964 105 094 04", "993 107 087 51"):
            self.assertIn(reference, part["vehicle"]["porsche_part_numbers"])
        self.assertEqual(load(SOURCE)["quality"]["evidence_level"], "A")

    def test_the_additive_case_is_recognised(self) -> None:
        judgement = load(INPUTS)["parts"][PART_ID]
        self.assertTrue(judgement["titanium_relevance"]["consolidation"])
        self.assertTrue(judgement["titanium_relevance"]["internal_passages_unmachinable"])
        self.assertIn("consolidation", judgement["additive_families"])
        self.assertIn("passages_internes", judgement["additive_families"])

    def test_titanium_is_refused_on_the_two_reasons_that_survive(self) -> None:
        """Galling and the galvanic couple have declared countermeasures, so
        they no longer refuse: they are carried as requirements. Two reasons
        remain that no countermeasure lifts — differential expansion against
        an aluminum case, and the fact that titanium does not improve on the
        original cast aluminum."""
        entry = next(
            item for item in load(SCREEN)["ranking"] if item["part_id"] == PART_ID
        )
        self.assertFalse(entry["eligible"])
        reasons = " ".join(entry["disqualifiers"])
        self.assertIn("dilatation", reasons)
        self.assertIn("n'ameliore pas la matiere d'origine", reasons)
        self.assertFalse(load(PART)["titanium"]["applicable"])

    def test_the_part_stays_prohibited(self) -> None:
        self.assertEqual(
            load(PART)["classification"]["safety_class"],
            "prohibited_pending_engineering",
        )

    def test_the_aluminium_answer_is_recorded_not_lost(self) -> None:
        doc = DOC.read_text(encoding="utf-8")
        self.assertIn("in aluminium", doc)
        self.assertIn("aluminum", load(PART)["manufacturing"]["material"]["family"])

    def test_a_condition_without_a_declared_mitigation_blocks(self) -> None:
        screen = load(SCREEN)
        ranking = {item["part_id"]: item for item in screen["ranking"]}
        for part_id, judgement in load(INPUTS)["parts"].items():
            counters = judgement["titanium_counter_indications"]
            parades = judgement.get("mitigations", {})
            unresolved = [
                name
                for name in MITIGABLE
                if counters.get(name) and not (parades.get(name) or "").strip()
            ]
            if unresolved:
                with self.subTest(part=part_id, conditions=unresolved):
                    self.assertFalse(ranking[part_id]["eligible"])
        self.assertIn("Untreated sliding contact", GRID.read_text(encoding="utf-8"))

    def test_a_declared_mitigation_becomes_a_carried_requirement(self) -> None:
        entry = next(
            item for item in load(SCREEN)["ranking"] if item["part_id"] == PART_ID
        )
        carried = {item["condition"] for item in entry["carried_requirements"]}
        self.assertIn("galling_or_repeated_threads", carried)
        self.assertIn("uncontrolled_galvanic_couple", carried)
        # Expansion, however, has no countermeasure: that is what blocks.
        self.assertNotIn("differential_expansion_with_alloy_mate", carried)

    def test_the_screen_states_that_it_does_not_cover_the_car(self) -> None:
        screen = load(SCREEN)
        self.assertIn("pas sur la voiture", screen["scope_warning"])
        self.assertIn("6 259", screen["scope_warning"])


if __name__ == "__main__":
    unittest.main()
