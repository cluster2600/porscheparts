"""Etape 04 du pipeline AM pour la bague de commodo F1.

Ce test ne dit pas que la bague est fabricable. Il verifie que la carte de route
publiee reste **fermee** : qu'elle est liee au master par empreinte, qu'elle
n'ouvre aucune porte de fabrication, et surtout qu'elle continue de signaler
l'incoherence qui l'a motivee — un tranchage a 50 um confronte a la seule route
AlSi10Mg publiee sur cette machine, qui est a 30 um. Une carte qui deviendrait
verte sans coupon, sans traitement thermique et sans lot de poudre serait un
faux, et c'est cela que le test cherche.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PART_ID = "993-INT-SWITCH-TRIM-RING-F1-0001"
MASTER = ROOT / "parts/993-int-switch-trim-ring-f1-0001/derived/switch_trim_ring_f1.step"
EVIDENCE = ROOT / "twins/993-switch-trim-ring-alsi10mg-f1/evidence/route-f1"
CARD = EVIDENCE / "993-int-switch-trim-ring-f1-0001-process-route-card.json"
RFQ = EVIDENCE / "993-int-switch-trim-ring-f1-0001-supplier-rfq.md"
PROCESS = ROOT / "catalog/manufacturing/processes/eos-m290-alsi10mg-30um.json"
GEOMETRY = (
    ROOT
    / "twins/993-switch-trim-ring-alsi10mg-f1/evidence/lpbf-f1"
    / "993-int-switch-trim-ring-f1-0001-lpbf-geometry-report.json"
)
POLICY = ROOT / "catalog/manufacturing/am-validation-policy.json"

MANDATORY_CLOSED_GATES = {
    "orientation_engineering_reviewed",
    "temperature_dependent_constitutive_card_available",
    "heat_treatment_route_defined",
    "machining_stock_defined",
    "part_allowables_derived_from_coupons",
    "powder_lot_traceability_contracted",
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class SwitchTrimRingRouteF1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.card = load(CARD)
        self.gates = {entry["gate"]: entry for entry in self.card["gates"]}

    def test_the_card_names_the_part_and_the_pipeline_stage(self) -> None:
        self.assertEqual(self.card["part_id"], PART_ID)
        self.assertEqual(self.card["stage_id"], "04_material_machine_process_card")
        self.assertEqual(self.card["safety_class"], "non_critical")

    def test_no_manufacturing_gate_is_opened(self) -> None:
        self.assertFalse(self.card["metal_print_authorized"])
        self.assertEqual(self.card["status"], "blocked_missing_input")
        self.assertGreater(self.card["blocking_gate_count"], 0)

    def test_the_gates_that_need_a_supplier_stay_closed(self) -> None:
        for name in MANDATORY_CLOSED_GATES:
            with self.subTest(gate=name):
                self.assertIn(name, self.gates)
                self.assertFalse(self.gates[name]["pass"])
                self.assertTrue(self.gates[name]["blocker"].strip())

    def test_the_layer_thickness_incoherence_is_reported_not_smoothed(self) -> None:
        screened = load(GEOMETRY)["full_build_slicing"]["layer_thickness_mm"]
        qualified = load(PROCESS)["process_reference"]["layer_thickness_um"] / 1000.0
        self.assertNotAlmostEqual(screened, qualified)
        self.assertFalse(self.gates["layer_thickness_consistent"]["pass"])
        self.assertEqual(self.card["derived"]["screened_layer_thickness_mm"], screened)
        self.assertEqual(self.card["derived"]["qualified_layer_thickness_mm"], qualified)

    def test_the_quote_request_carries_the_master_fingerprint(self) -> None:
        digest = hashlib.sha256(MASTER.read_bytes()).hexdigest()
        text = RFQ.read_text(encoding="utf-8")
        self.assertIn(digest, text)
        self.assertIn("pas un ordre de", text)
        for name in MANDATORY_CLOSED_GATES:
            self.assertIn(name, text)

    def test_the_policy_records_the_stage_as_blocked(self) -> None:
        stage = load(POLICY)["part_overrides"][PART_ID]["stages"][
            "04_material_machine_process_card"
        ]
        self.assertEqual(stage["status"], "blocked_missing_input")
        self.assertIn(
            "twins/993-switch-trim-ring-alsi10mg-f1/evidence/route-f1/"
            "993-int-switch-trim-ring-f1-0001-process-route-card.json",
            stage["evidence"],
        )


if __name__ == "__main__":
    unittest.main()
