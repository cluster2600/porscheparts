"""Route tournage 6063 de la bague de commodo.

Le depot a conclu que cette piece doit etre tournee et non frittee. Ce test
verifie que la carte publiee reste honnete sur ce que ce choix ne resout pas :
la cote d'ajustement n'est toujours pas tolerancee, les arêtes ne sont toujours
pas definies, et aucun montage n'est autorise. Il verifie aussi que la nuance
est choisie sur le critere qui gouverne la piece, et non sur la matiere la mieux
documentee du depot — c'est l'erreur que la decision 0005 a corrigee.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PART_ID = "993-INT-SWITCH-TRIM-RING-F1-0001"
PART = ROOT / "catalog/parts/993-int-switch-trim-ring-f1-0001.json"
MASTER = ROOT / "parts/993-int-switch-trim-ring-f1-0001/derived/switch_trim_ring_f1.step"
EVIDENCE = ROOT / "twins/993-switch-trim-ring-f1/evidence/turning-f1"
CARD = EVIDENCE / "993-int-switch-trim-ring-f1-0001-turning-route-card.json"
RFQ = EVIDENCE / "993-int-switch-trim-ring-f1-0001-turning-rfq.md"
PROCESS = ROOT / "catalog/manufacturing/processes/cnc-turning-6063-t6-bright-anodised.json"
DECISION = ROOT / "docs/decisions/0005-alsi10mg-nest-pas-un-choix.md"

STILL_OPEN_QUESTIONS = {
    "thin_wall_workholding_reviewed",
    "edge_break_specified",
    "fit_dimension_toleranced",
    "anodising_growth_subtracted_from_fit",
    "material_certificate_contracted",
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class SwitchTrimRingTurningF1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.card = load(CARD)
        self.gates = {entry["gate"]: entry for entry in self.card["gates"]}

    def test_the_card_names_the_part_and_the_turning_family(self) -> None:
        self.assertEqual(self.card["part_id"], PART_ID)
        self.assertEqual(self.card["route_family"], "cnc_turning")
        self.assertEqual(self.card["safety_class"], "non_critical")

    def test_no_vehicle_fitment_is_authorised(self) -> None:
        self.assertFalse(self.card["vehicle_fitment_authorized"])
        self.assertEqual(self.card["status"], "blocked_missing_input")

    def test_changing_process_did_not_close_the_questions_it_cannot_answer(self) -> None:
        for name in STILL_OPEN_QUESTIONS:
            with self.subTest(gate=name):
                self.assertIn(name, self.gates)
                self.assertFalse(self.gates[name]["pass"])
                self.assertTrue(self.gates[name]["blocker"].strip())

    def test_the_alloy_is_chosen_on_appearance_not_on_repository_convenience(self) -> None:
        process = load(PROCESS)
        self.assertEqual(
            process["selection_rationale"]["governing_requirement"], "appearance"
        )
        self.assertIn("AlSi10Mg LPBF", process["selection_rationale"]["rejected_alternatives"])
        self.assertTrue(self.gates["alloy_selected_against_governing_requirement"]["pass"])
        self.assertTrue(DECISION.exists())

    def test_the_catalogue_record_follows_the_decision(self) -> None:
        manufacturing = load(PART)["manufacturing"]
        self.assertEqual(manufacturing["preferred_process"], "CNC")
        self.assertIn("6063", manufacturing["material"]["grade"])

    def test_the_fit_strategy_does_not_pretend_to_replace_a_measurement(self) -> None:
        fit = self.card["fit_strategy"]
        self.assertEqual(len(fit["candidate_outer_diameters_mm"]), 3)
        self.assertIn("pas ce qui la remplace", fit["why_not_simply_measure"])

    def test_the_quote_request_carries_the_master_fingerprint(self) -> None:
        digest = hashlib.sha256(MASTER.read_bytes()).hexdigest()
        text = RFQ.read_text(encoding="utf-8")
        self.assertIn(digest, text)
        self.assertIn("6061", text)


if __name__ == "__main__":
    unittest.main()
