"""Etape 04 du pipeline AM pour le levier interieur de porte F0.

Le test ne dit pas que le levier est fabricable. Il verifie que la carte de
route publiee reste fermee, liee au maitre par empreinte, que les portes de
coherence passent et que celles qui demandent un fournisseur restent closes.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PART_ID = "993-INT-DOOR-OPENER-LEVER-F0-0001"
MASTER = ROOT / "parts/993-int-door-opener-lever-f0-0001/derived/door_opener_lever_f0.step"
EVIDENCE = ROOT / "twins/993-door-opener-lever-alsi10mg-f0/evidence/route-f0"
CARD = EVIDENCE / "993-int-door-opener-lever-f0-0001-process-route-card.json"
RFQ = EVIDENCE / "993-int-door-opener-lever-f0-0001-supplier-rfq.md"
POLICY = ROOT / "catalog/manufacturing/am-validation-policy.json"

CONSISTENT = {
    "machine_identity_consistent",
    "material_identity_consistent",
    "layer_thickness_consistent",
    "screened_wall_above_process_minimum",
    "bare_part_fits_machine_envelope",
}
CLOSED = {
    "orientation_engineering_reviewed",
    "temperature_dependent_constitutive_card_available",
    "heat_treatment_route_defined",
    "machining_stock_defined",
    "part_allowables_derived_from_coupons",
    "powder_lot_traceability_contracted",
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class DoorOpenerLeverRouteF0Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.card = load(CARD)
        self.gates = {entry["gate"]: entry for entry in self.card["gates"]}

    def test_card_names_part_and_stage_without_authorizing_print(self) -> None:
        self.assertEqual(self.card["part_id"], PART_ID)
        self.assertEqual(self.card["stage_id"], "04_material_machine_process_card")
        self.assertFalse(self.card["metal_print_authorized"])
        self.assertEqual(self.card["status"], "blocked_missing_input")
        self.assertEqual(self.card["blocking_gate_count"], len(CLOSED))

    def test_consistency_gates_pass_and_supplier_gates_stay_closed(self) -> None:
        for name in CONSISTENT:
            with self.subTest(gate=name):
                self.assertTrue(self.gates[name]["pass"])
        for name in CLOSED:
            with self.subTest(gate=name):
                self.assertFalse(self.gates[name]["pass"])
                self.assertTrue(self.gates[name]["blocker"].strip())

    def test_quote_request_carries_master_fingerprint(self) -> None:
        text = RFQ.read_text(encoding="utf-8")
        self.assertIn(hashlib.sha256(MASTER.read_bytes()).hexdigest(), text)
        for name in CLOSED:
            self.assertIn(name, text)

    def test_policy_records_stage_as_blocked_with_card(self) -> None:
        stage = load(POLICY)["part_overrides"][PART_ID]["stages"]["04_material_machine_process_card"]
        self.assertEqual(stage["status"], "blocked_missing_input")
        self.assertIn(str(CARD.relative_to(ROOT)), stage["evidence"])


if __name__ == "__main__":
    unittest.main()
