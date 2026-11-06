"""The 993 dashboard F0 interface contracts refuse unsupported values (#567)."""

import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "check_993_dashboard_interface_contracts_567", ROOT / "scripts/check_993_dashboard_interface_contracts.py"
)
checker = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(checker)


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


CONTRACT = load(checker.CONTRACTS)
ASSEMBLY = load(checker.ASSEMBLY)
IDENTITY = load(checker.IDENTITY)


def interface(contract, interface_id):
    return next(i for i in contract["interfaces"] if i["interface_id"] == interface_id)


class RepositoryState(unittest.TestCase):
    def test_contracts_are_consistent(self):
        self.assertEqual(checker.check_contract(CONTRACT, ASSEMBLY, IDENTITY), [])

    def test_every_value_is_null_and_nothing_is_admitted(self):
        self.assertEqual(CONTRACT["evidence_layers"]["admitted_physical_evidence"], [])
        for _, item in checker._measurands(CONTRACT):
            self.assertIsNone(item["value"], item["id"])
            self.assertIsNone(item["uncertainty"], item["id"])
        self.assertIsNone(CONTRACT["vehicle_frame"]["origin"])
        for i in CONTRACT["interfaces"]:
            self.assertIsNone(i["tolerances"]["value"], i["interface_id"])
            self.assertIsNone(i["attachments"]["hole_pattern"], i["interface_id"])
            self.assertIsNone(i["attachments"]["axes"], i["interface_id"])

    def test_m564_target_carries_no_trim_or_strip_identity(self):
        for name in ("IF_TRIM_TO_BODY_PANEL", "IF_KNEE_STRIP_TO_ORIGINAL_MOUNTS"):
            self.assertIsNone(interface(CONTRACT, name)["catalogue_identity"]["M564-LHD"]["items"])

    def test_safety_interfaces_are_marked(self):
        safety = {i["interface_id"] for i in CONTRACT["interfaces"] if i["safety_relevant"]}
        self.assertTrue(checker.REQUIRED_SAFETY_INTERFACES <= safety)


class Refused(unittest.TestCase):
    def assertRefused(self, contract, fragment):
        errors = checker.check_contract(contract, ASSEMBLY, IDENTITY)
        self.assertTrue(any(fragment in e for e in errors), errors)

    def test_missing_interface(self):
        bad = copy.deepcopy(CONTRACT)
        bad["interfaces"] = [i for i in bad["interfaces"] if i["interface_id"] != "IF_COLUMN_CLEARANCE"]
        self.assertRefused(bad, "missing ['IF_COLUMN_CLEARANCE']")

    def test_duplicate_interface_cannot_be_hidden_by_dictionary_lookup(self):
        bad = copy.deepcopy(CONTRACT)
        bad["interfaces"].append(copy.deepcopy(interface(bad, "IF_COLUMN_CLEARANCE")))
        self.assertRefused(bad, "duplicate interface_id")

    def test_value_without_admitted_reading(self):
        bad = copy.deepcopy(CONTRACT)
        interface(bad, "IF_TRIM_TO_BODY_PANEL")["part_datums"][0]["value"] = [12.0, 4.0, 0.0]
        self.assertRefused(bad, "value without an admitted reading")

    def test_value_from_the_picogk_concept(self):
        bad = copy.deepcopy(CONTRACT)
        item = interface(bad, "IF_TRIM_TO_BODY_PANEL")["host_datums"][0]
        item.update(value=[0.0, 0.0, 0.0], uncertainty=0.5,
                    evidence="twins/993-dashboard-f0/dashboard-trim-f0-visual.stl")
        self.assertRefused(bad, "evidence cites a model or the F0 concept")

    def test_arbitrary_existing_file_cannot_admit_a_numeric_host_datum(self):
        bad = copy.deepcopy(CONTRACT)
        bad["evidence_layers"]["admitted_physical_evidence"] = ["README.md"]
        bad["vehicle_frame"]["host_datum_features"][0].update(
            value=[1.0, 2.0, 3.0], uncertainty=0.1, evidence="README.md"
        )
        self.assertRefused(bad, "F0 must remain empty")
        self.assertRefused(bad, "F0 datum value, uncertainty and evidence must remain null")

    def test_frame_and_attachment_geometry_remain_unset(self):
        bad = copy.deepcopy(CONTRACT)
        bad["vehicle_frame"]["origin"] = [0.0, 0.0, 0.0]
        interface(bad, "IF_BODY_PANEL_TO_SHELL")["attachments"]["hole_pattern"] = [[0.0, 0.0]]
        self.assertRefused(bad, "F0 origin and axes must remain null")
        self.assertRefused(bad, "F0 physical attachment fields must remain null")
        bad = copy.deepcopy(CONTRACT)
        interface(bad, "IF_TRIM_TO_BODY_PANEL")["attachments"]["fastener_identity"] = "M6 bolt"
        self.assertRefused(bad, "F0 fastener assignment must remain unknown")

    def test_status_and_tolerance_cannot_be_promoted_in_f0(self):
        bad = copy.deepcopy(CONTRACT)
        bad["status"] = "accepted"
        item = interface(bad, "IF_TRIM_TO_BODY_PANEL")
        item["status"] = "accepted"
        item["tolerances"]["value"] = 1.5
        bad["reviewer_roles"][2]["assigned_to"] = "Reviewer A"
        self.assertRefused(bad, "F0 contract must remain proposed")
        self.assertRefused(bad, "F0 interface status must remain missing_data")
        self.assertRefused(bad, "F0 tolerance value must remain null")

    def test_m564_target_cannot_be_removed(self):
        bad = copy.deepcopy(CONTRACT)
        bad["candidate_variants"] = [v for v in bad["candidate_variants"] if v["row_id"] != "M564-LHD"]
        for item in bad["interfaces"]:
            item["catalogue_identity"].pop("M564-LHD")
        self.assertRefused(bad, "F0 target and documented alternatives")

    def test_unmapped_dashboard_identity_cannot_gain_an_invented_part_number(self):
        bad = copy.deepcopy(CONTRACT)
        interface(bad, "IF_TRIM_TO_BODY_PANEL")["catalogue_identity"]["M564-LHD"]["items"] = [{
            "part_number": "999 999 999 99", "source_id": "SRC-PORSCHE-PET-993",
            "plate": "809-02", "pdf_page": 511, "position": "1",
        }]
        self.assertRefused(bad, "unmapped dashboard target cannot gain part numbers")
        interface(bad, "IF_TRIM_TO_BODY_PANEL")["catalogue_identity"]["M564-LHD"]["status"] = "plate_heading"
        self.assertRefused(bad, "F0 status must remain unmapped_in_kat017")

    def test_steering_inventory_cannot_be_relabelled_as_a_dashboard_identity(self):
        bad = copy.deepcopy(CONTRACT)
        items = interface(bad, "IF_COLUMN_CLEARANCE")["catalogue_identity"]["M564-LHD"]["items"]
        items[0]["part_number"] = "999 999 999 99"
        self.assertRefused(bad, "steering items must match the reviewed PET inventory")

    def test_source_pointers_must_match_the_checked_contract_inputs(self):
        bad = copy.deepcopy(CONTRACT)
        bad["assembly"] = "twins/993-dashboard-f0/dashboard-trim-f0-visual.stl"
        self.assertRefused(bad, "must cite the checked F0 assembly")

    def test_repetition_requirement_cannot_be_lowered(self):
        bad = copy.deepcopy(CONTRACT)
        bad["vehicle_frame"]["host_datum_features"][0]["repetitions_min"] = 1
        self.assertRefused(bad, "at least three independent repetitions required")

    def test_host_reading_derived_from_the_part(self):
        bad = copy.deepcopy(CONTRACT)
        interface(bad, "IF_PILLARS_AND_WINDSHIELD")["host_datums"][0]["methods"].append("derived")
        self.assertRefused(bad, "host reading by a forbidden method")

    def test_interface_without_host_datum(self):
        bad = copy.deepcopy(CONTRACT)
        interface(bad, "IF_HOOD_TO_TRIM")["host_datums"] = []
        self.assertRefused(bad, "no independent host datum")

    def test_m564_borrowing_rs_trim_number(self):
        bad = copy.deepcopy(CONTRACT)
        block = interface(bad, "IF_TRIM_TO_BODY_PANEL")["catalogue_identity"]
        block["M564-LHD"] = copy.deepcopy(block["M002-LHD"])
        self.assertRefused(bad, "belongs to another variant")

    def test_catalogue_item_without_page(self):
        bad = copy.deepcopy(CONTRACT)
        interface(bad, "IF_VENTS_TO_TRIM_DUCTS")["catalogue_identity"]["M002-LHD"]["items"][0]["pdf_page"] = None
        self.assertRefused(bad, "plate, page and position required")

    def test_tolerance_without_reviewer(self):
        bad = copy.deepcopy(CONTRACT)
        interface(bad, "IF_CONSOLE_TO_DASH")["tolerances"]["value"] = 1.5
        self.assertRefused(bad, "tolerance set without an assigned interface reviewer")

    def test_model_or_double_role_reviewer(self):
        bad = copy.deepcopy(CONTRACT)
        bad["reviewer_roles"][1]["assigned_to"] = "Claude Code agent"
        self.assertRefused(bad, "a model or generator cannot hold a role")
        bad = copy.deepcopy(CONTRACT)
        bad["reviewer_roles"][1]["assigned_to"] = "Reviewer A"
        bad["reviewer_roles"][2]["assigned_to"] = "Reviewer A"
        self.assertRefused(bad, "one person holds two roles")

    def test_safety_interface_without_engineering_role(self):
        bad = copy.deepcopy(CONTRACT)
        bad["reviewer_roles"] = [r for r in bad["reviewer_roles"] if r["role"] != "professional_engineering_reviewer"]
        self.assertRefused(bad, "without a professional engineering reviewer")

    def test_trim_attachment_cannot_be_demoted(self):
        bad = copy.deepcopy(CONTRACT)
        interface(bad, "IF_TRIM_TO_BODY_PANEL")["safety_relevant"] = False
        self.assertRefused(bad, "required safety interface must be marked safety_relevant")

    def test_unknown_load_path(self):
        bad = copy.deepcopy(CONTRACT)
        interface(bad, "IF_HOOD_TO_TRIM")["load_paths"].append("LP_INVENTED")
        self.assertRefused(bad, "unknown LP_INVENTED")


class Contradictions(unittest.TestCase):
    def test_non_overlapping_readings_contradict(self):
        readings = [
            {"measurand": "TB-H03", "specimen_id": "SPEC-993-DASH-0001", "value": 1.20, "uncertainty": 0.05},
            {"measurand": "TB-H03", "specimen_id": "SPEC-993-DASH-0001", "value": 1.40, "uncertainty": 0.05},
            {"measurand": "TB-H03", "specimen_id": "SPEC-993-DASH-0002", "value": 2.00, "uncertainty": 0.05},
        ]
        self.assertEqual(len(checker.find_contradictions(readings)), 1)

    def test_overlapping_readings_do_not(self):
        readings = [
            {"measurand": "TB-H03", "specimen_id": "SPEC-993-DASH-0001", "value": 1.20, "uncertainty": 0.10},
            {"measurand": "TB-H03", "specimen_id": "SPEC-993-DASH-0001", "value": 1.35, "uncertainty": 0.10},
        ]
        self.assertEqual(checker.find_contradictions(readings), [])


if __name__ == "__main__":
    unittest.main()
