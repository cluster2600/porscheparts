"""Carter de chaine : bon candidat additif, mauvais candidat titane.

Ces tests gardent les deux moitiés du verdict. La consolidation est reconnue,
pour qu'on ne perde pas le fait que la piece merite l'additif. Et le refus du
titane est verrouille sur ses trois motifs de grille, pour qu'une relecture
distraite ne le rouvre pas.

Le dernier test est le plus important : il verifie que les cinq
contre-indications de TITANIUM.md sont bien traitees comme des refus, et non
comme des malus. C'est l'infidelite que cette piece a fait apparaitre.
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

# Conditions a lever, pas refus absolus : la grille dit « contact glissant
# **non traite** » et « couple galvanique **non maitrise** », et SAFETY.md
# inscrit leur prevention parmi les exigences minimales du metal.
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
        """Le grippage et le couple galvanique ont des parades declarees, donc
        ils ne refusent plus : ils sont portes comme exigences. Restent les deux
        motifs qu'aucune parade ne leve — la dilatation differentielle contre un
        carter aluminium, et le fait que le titane n'ameliore pas la fonte
        d'aluminium d'origine."""
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
        self.assertIn("en aluminium", doc)
        self.assertIn("aluminium", load(PART)["manufacturing"]["material"]["family"])

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
        self.assertIn("non traité", GRID.read_text(encoding="utf-8"))

    def test_a_declared_mitigation_becomes_a_carried_requirement(self) -> None:
        entry = next(
            item for item in load(SCREEN)["ranking"] if item["part_id"] == PART_ID
        )
        carried = {item["condition"] for item in entry["carried_requirements"]}
        self.assertIn("galling_or_repeated_threads", carried)
        self.assertIn("uncontrolled_galvanic_couple", carried)
        # La dilatation, elle, reste sans parade : c'est ce qui bloque.
        self.assertNotIn("differential_expansion_with_alloy_mate", carried)

    def test_the_screen_states_that_it_does_not_cover_the_car(self) -> None:
        screen = load(SCREEN)
        self.assertIn("pas sur la voiture", screen["scope_warning"])
        self.assertIn("6 259", screen["scope_warning"])


if __name__ == "__main__":
    unittest.main()
