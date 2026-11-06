"""The dashboard-trim PET identity matrix refuses unsupported mappings (#566)."""

import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "check_993_dashboard_pet_identity_566", ROOT / "scripts/check_993_dashboard_pet_identity.py"
)
checker = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(checker)

IDENTITY = json.loads(checker.IDENTITY.read_text(encoding="utf-8"))
RECORD = json.loads(checker.RECORD.read_text(encoding="utf-8"))


def row(identity, row_id):
    return next(item for item in identity["matrix"] if item["row_id"] == row_id)


def complete_submission():
    files = [{"path": "e1.jpg", "specimen_id": "SPEC-993-DASH-0001", "sha256": "a" * 64}]
    return {
        "specimen_id": "SPEC-993-DASH-0001",
        "E1-option-label": {"identifiers_visible": False, "m_codes": ["M564"]},
        "E2-passenger-reverse": {
            "region_shown": True, "airbag_module": False, "tear_line": False, "deployment_flap": False,
        },
        "E3-trim-label": {"part_number": None},
        "E4-continuity": {"files": files, "linking_marks": 2},
        "E5-rights": {"licence": "CC-BY-4.0", "personal_data_removed": True},
    }


class RepositoryState(unittest.TestCase):
    def test_identity_and_record_are_consistent(self):
        self.assertEqual(checker.check_identity(IDENTITY), [])
        self.assertEqual(checker.check_record(RECORD, IDENTITY), [])

    def test_m564_target_stays_unmapped(self):
        for hand in ("LHD", "RHD"):
            self.assertEqual(row(IDENTITY, f"M564-{hand}")["mapping_status"], "unmapped_in_kat017")
            self.assertIsNone(row(IDENTITY, f"M564-{hand}")["dashboard_trim"])
        self.assertIsNone(IDENTITY["f0_target"]["dashboard_trim_part_number"])
        self.assertIsNone(IDENTITY["f0_target"]["specimen_id"])

    def test_shared_trim_number_conflict_stays_open(self):
        register = json.loads((ROOT / "catalog/registers/contradictions.json").read_text(encoding="utf-8"))
        entry = next(e for e in register["entries"] if e["contradiction_id"] == "CTR-0019")
        self.assertEqual(entry["status"], "open")
        self.assertEqual({v["location"].split(",")[0] for v in entry["values"]},
                         {"illustration 809-00", "illustration 809-02"})

    def test_gates_are_unchanged(self):
        self.assertEqual(RECORD["validation"]["status"], "concept")
        self.assertEqual(RECORD["classification"]["safety_class"], "functional")


class RefusedMappings(unittest.TestCase):
    def assertRefused(self, identity, fragment):
        errors = checker.check_identity(identity)
        self.assertTrue(any(fragment in e for e in errors), errors)

    def test_m564_borrowing_the_airbag_plate_number(self):
        bad = copy.deepcopy(IDENTITY)
        target = row(bad, "M564-LHD")
        source = row(bad, "M562-LHD")
        target.update(plate="809-00", dashboard_trim=source["dashboard_trim"], mapping_status="title_match_only")
        self.assertRefused(bad, "titled passenger_airbag_present")

    def test_m564_borrowing_the_rs_plate_number(self):
        bad = copy.deepcopy(IDENTITY)
        target = row(bad, "M564-LHD")
        source = row(bad, "M002-LHD")
        target.update(plate="809-02", dashboard_trim=source["dashboard_trim"], mapping_status="mapped_by_option_code")
        self.assertRefused(bad, "carries no line-level M564")

    def test_unmapped_row_cannot_carry_numbers(self):
        bad = copy.deepcopy(IDENTITY)
        row(bad, "M564-LHD")["dashboard_trim"] = row(bad, "M002-LHD")["dashboard_trim"]
        self.assertRefused(bad, "unmapped row keeps this null")

    def test_wrong_handedness_remark(self):
        bad = copy.deepcopy(IDENTITY)
        row(bad, "M002-LHD")["dashboard_trim"][0]["remark"] = "/RL"
        self.assertRefused(bad, "does not state /LL")

    def test_page_outside_its_plate(self):
        bad = copy.deepcopy(IDENTITY)
        row(bad, "M003-RHD")["knee_protection_strip"][0]["pdf_page"] = 501
        self.assertRefused(bad, "is not a page of plate 809-02")

    def test_item_plate_cannot_borrow_opposite_airbag_scope(self):
        bad = copy.deepcopy(IDENTITY)
        row(bad, "M002-LHD")["knee_protection_strip"][0] = copy.deepcopy(
            row(bad, "M562-LHD")["knee_protection_strip"][0]
        )
        self.assertRefused(bad, "plate 809-01 is titled passenger_airbag_present")

    def test_item_plate_needs_its_own_line_level_option_code(self):
        bad = copy.deepcopy(IDENTITY)
        plate = copy.deepcopy(next(p for p in bad["plates"] if p["illustration"] == "809-02"))
        plate["illustration"] = "809-03"
        plate["option_code_on_lines"] = None
        bad["plates"].append(plate)
        row(bad, "M002-LHD")["knee_protection_strip"][0]["plate"] = "809-03"
        self.assertRefused(bad, "plate 809-03 carries no line-level M002")

    def test_missing_row(self):
        bad = copy.deepcopy(IDENTITY)
        bad["matrix"] = [r for r in bad["matrix"] if r["row_id"] != "M561-RHD"]
        self.assertRefused(bad, "missing rows")

    def test_f0_target_number_while_unmapped(self):
        bad = copy.deepcopy(IDENTITY)
        bad["f0_target"]["dashboard_trim_part_number"] = "993 552 055 00"
        self.assertRefused(bad, "must stay null")


class RefusedRecords(unittest.TestCase):
    def test_record_claiming_m564_without_unmapped_label(self):
        bad = copy.deepcopy(RECORD)
        bad["vehicle"]["variants"][0] = "M564 without airbag"
        self.assertTrue(any("must say" in e for e in checker.check_record(bad, IDENTITY)))

    def test_record_with_unknown_trim_number(self):
        bad = copy.deepcopy(RECORD)
        bad["vehicle"]["porsche_part_numbers"].append("993 552 057 00")
        self.assertTrue(any("993 552 057 00" in e for e in checker.check_record(bad, IDENTITY)))

    def test_airbag_only_trim_number_is_not_an_applicable_replacement(self):
        for number in ("993 552 055 01", "993 552 056 01"):
            with self.subTest(number=number):
                bad = copy.deepcopy(RECORD)
                bad["vehicle"]["porsche_part_numbers"].append(number)
                errors = checker.check_record(bad, IDENTITY)
                self.assertTrue(any(number in error and "not an applicable" in error for error in errors), errors)

    def test_record_with_unknown_knee_strip(self):
        bad = copy.deepcopy(RECORD)
        bad["validation"]["known_limits"].append("Strip 964 552 059 00 assumed.")
        self.assertTrue(any("964 552 059 00" in e for e in checker.check_record(bad, IDENTITY)))


class SpecimenAdmission(unittest.TestCase):
    def test_declarative_m564_submission_is_held_pending_independent_review(self):
        verdict, reasons = checker.admit_specimen(complete_submission())
        self.assertEqual(verdict, "held")
        self.assertIn("E1-E5: independent file, continuity and rights verification pending", reasons)

    def test_zero_or_malformed_digest_is_refused(self):
        for digest in ("0" * 64, "not-a-sha256", "A" * 64):
            submission = complete_submission()
            submission["E4-continuity"]["files"][0]["sha256"] = digest
            verdict, reasons = checker.admit_specimen(submission)
            self.assertEqual(verdict, "refused")
            self.assertTrue(any(reason.startswith("E4:") for reason in reasons))

    def test_each_missing_evidence_is_refused(self):
        for key in checker.EVIDENCE_IDS:
            submission = complete_submission()
            del submission[key]
            verdict, reasons = checker.admit_specimen(submission)
            self.assertEqual(verdict, "refused", key)
            self.assertTrue(any(r.startswith(key[:2]) for r in reasons), (key, reasons))

    def test_m562_label_is_refused(self):
        submission = complete_submission()
        submission["E1-option-label"]["m_codes"] = ["M562"]
        self.assertEqual(checker.admit_specimen(submission)[0], "refused")

    def test_flap_seen_overrides_a_clean_label(self):
        submission = complete_submission()
        submission["E2-passenger-reverse"]["tear_line"] = True
        verdict, reasons = checker.admit_specimen(submission)
        self.assertEqual(verdict, "refused")
        self.assertIn("E2: tear_line observed or not ruled out", reasons)

    def test_unknown_reverse_features_are_not_assumed_absent(self):
        submission = complete_submission()
        del submission["E2-passenger-reverse"]["airbag_module"]
        self.assertEqual(checker.admit_specimen(submission)[0], "refused")

    def test_visible_identifier_is_refused(self):
        submission = complete_submission()
        submission["E1-option-label"]["identifiers_visible"] = True
        self.assertEqual(checker.admit_specimen(submission)[0], "refused")

    def test_identifier_derived_specimen_id_is_refused(self):
        submission = complete_submission()
        submission["specimen_id"] = "WP0ZZZ99ZTS000000"
        self.assertEqual(checker.admit_specimen(submission)[0], "refused")

    def test_m561_and_label_conflicts_are_held(self):
        submission = complete_submission()
        submission["E1-option-label"]["m_codes"] = ["M561"]
        self.assertEqual(checker.admit_specimen(submission)[0], "held")
        submission = complete_submission()
        submission["E3-trim-label"] = {"part_number": "993 552 055 00", "matches_matrix_row": False}
        self.assertEqual(checker.admit_specimen(submission)[0], "held")
        submission["E3-trim-label"].pop("matches_matrix_row")
        verdict, reasons = checker.admit_specimen(submission)
        self.assertEqual(verdict, "held")
        self.assertTrue(any(reason.startswith("E3:") for reason in reasons))

    def test_file_from_another_specimen_breaks_continuity(self):
        submission = complete_submission()
        submission["E4-continuity"]["files"][0]["specimen_id"] = "SPEC-993-DASH-0002"
        self.assertEqual(checker.admit_specimen(submission)[0], "refused")


if __name__ == "__main__":
    unittest.main()
