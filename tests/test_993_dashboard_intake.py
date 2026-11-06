"""Safety boundaries for the empty 993 dashboard intake and private packet gate."""

from __future__ import annotations

import copy
import contextlib
import hashlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import check_993_dashboard_intake as intake


class DashboardIntakeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        source = intake.ROOT
        for relative in (intake.ASSEMBLY, intake.INTAKE / "packet-template.json", intake.INTAKE / "packet.schema.json"):
            destination = self.root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / relative, destination)
        self.template_path = self.root / intake.INTAKE / "packet-template.json"

    def _template(self) -> dict:
        return json.loads(self.template_path.read_text(encoding="utf-8"))

    def _write_template(self, data: dict) -> None:
        self.template_path.write_text(json.dumps(data), encoding="utf-8")

    def test_empty_public_template_is_closed(self) -> None:
        self.assertEqual(intake.check_template(self.root), [])

    def test_non_object_public_template_and_schema_fail_closed(self) -> None:
        schema_path = self.root / intake.INTAKE / "packet.schema.json"
        original_schema = schema_path.read_text(encoding="utf-8")
        for value in (None, [], "text"):
            with self.subTest(value=value):
                self.template_path.write_text(json.dumps(value), encoding="utf-8")
                self.assertTrue(any("packet-template.json: expected object" in error
                                    for error in intake.check_template(self.root)))
        self.template_path.write_text((intake.ROOT / intake.INTAKE / "packet-template.json").read_text(encoding="utf-8"), encoding="utf-8")
        for value in (None, [], "text"):
            with self.subTest(schema=value):
                schema_path.write_text(json.dumps(value), encoding="utf-8")
                self.assertTrue(any("packet.schema.json: expected object" in error
                                    for error in intake.check_template(self.root)))
        schema_path.write_text(original_schema, encoding="utf-8")

    def test_non_object_private_packet_exits_nonzero(self) -> None:
        packet_path = self.root / "private-packet.json"
        for value in (None, [], "text"):
            with self.subTest(value=value):
                packet_path.write_text(json.dumps(value), encoding="utf-8")
                self.assertTrue(any("expected packet object" in error
                                    for error in intake.check_packet(packet_path, intake.ROOT)))
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    result = intake.main(["--packet", str(packet_path)])
                self.assertNotEqual(result, 0)
                self.assertIn("expected packet object", output.getvalue())

    def test_template_rejects_prefilled_specimen_and_reading(self) -> None:
        data = self._template()
        data["specimen_id"] = "SPEC-993-DASH-0001"
        data["capture_campaign_id"] = "SESSION-993-DASH-TEST"
        data["interface_evidence"][0]["part_reading_ids"] = ["MEAS-TEST:BP_H01"]
        self._write_template(data)
        problems = intake.check_template(self.root)
        self.assertTrue(any("no specimen, campaign" in problem for problem in problems), problems)
        self.assertTrue(any("must remain empty" in problem for problem in problems), problems)

    def test_template_rejects_missing_interface_and_claim_schema_drift(self) -> None:
        data = self._template()
        data["interface_evidence"].pop()
        self._write_template(data)
        schema_path = self.root / intake.INTAKE / "packet.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        schema["properties"]["claims"]["properties"]["manufacturing_release"]["const"] = True
        schema_path.write_text(json.dumps(schema), encoding="utf-8")
        problems = intake.check_template(self.root)
        self.assertTrue(any("all 13 assembly interfaces" in problem for problem in problems), problems)
        self.assertTrue(any("claims must be fixed false" in problem for problem in problems), problems)

    def test_safe_file_rejects_traversal_symlink_and_hash_mismatch(self) -> None:
        base = self.root / "private"
        base.mkdir()
        file = base / "capture.bin"
        file.write_bytes(b"synthetic test bytes")
        digest = hashlib.sha256(file.read_bytes()).hexdigest()
        problems: list[str] = []
        self.assertEqual(intake._safe_file(base, "capture.bin", digest, file.stat().st_size, problems, "asset"), file)
        self.assertEqual(problems, [])
        intake._safe_file(base, "capture.bin", "0" * 64, file.stat().st_size, problems, "asset")
        self.assertTrue(any("does not match file bytes" in problem for problem in problems), problems)
        problems.clear()
        self.assertIsNone(intake._safe_file(base, "../capture.bin", digest, file.stat().st_size, problems, "asset"))
        self.assertTrue(any("path escapes" in problem for problem in problems), problems)
        outside = self.root / "outside.bin"
        outside.write_bytes(b"outside")
        (base / "linked.bin").symlink_to(outside)
        problems.clear()
        self.assertIsNone(intake._safe_file(base, "linked.bin", hashlib.sha256(outside.read_bytes()).hexdigest(), outside.stat().st_size, problems, "asset"))
        self.assertTrue(any("outside packet directory" in problem for problem in problems), problems)

    def _submission(self) -> dict:
        packet = copy.deepcopy(self._template())
        packet["packet_kind"] = "external_submission"
        packet["status"] = "submitted_unreviewed"
        packet["specimen_id"] = "SPEC-993-DASH-0001"
        packet["capture_campaign_id"] = "SESSION-993-DASH-TEST"
        packet["target_scenario"]["model_year_observed"] = 1996
        packet["target_scenario"]["physical_vehicle_confirmed"] = True
        packet["identity_evidence"]["E1_identifiers_visible"] = False
        packet["identity_evidence"]["E1_m_codes_observed"] = ["M564"]
        packet["identity_evidence"]["E2_region_shown"] = True
        packet["identity_evidence"]["E2_passenger_module_present"] = False
        packet["identity_evidence"]["E2_tear_line_present"] = False
        packet["identity_evidence"]["E2_passenger_flap_present"] = False
        packet["identity_evidence"]["E5_personal_data_removed"] = True
        packet["contract"]["sha256"] = "0" * 64
        packet["contract"]["status"] = "frozen_for_intake"
        packet["review"]["verdict"] = "submitted_unreviewed"
        for interface in packet["interface_evidence"]:
            interface["status"] = "submitted_unreviewed"
        return packet

    def _add_asset(self, packet: dict, asset_id: str, path: str, state: str, *, redacted: bool, kind: str | None = None, publication: bool = False) -> None:
        raw = f"synthetic {asset_id}".encode("ascii")
        (self.root / path).write_bytes(raw)
        packet["assets"].append({
            "asset_id": asset_id, "specimen_id": packet["specimen_id"],
            "kind": kind or ("option_label_redacted" if state == "fitted" else "interface_photo"),
            "capture_state": state, "relative_path": path,
            "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
            "creator_role": "test_contributor", "licence": "synthetic test only",
            "inspection_permission": True, "publication_permission": publication,
            "rights_proof_asset_id": "A-RIGHTS", "redacted": redacted,
        })

    def test_specimen_id_matches_existing_pet_gate_and_schema(self) -> None:
        self.assertIsNotNone(intake.SPECIMEN.fullmatch("SPEC-993-DASH-0001"))
        self.assertIsNone(intake.SPECIMEN.fullmatch("SPEC-993-DASH-TEST"))
        self.assertIsNone(intake.SPECIMEN.fullmatch("SPEC-993-DASH-00001"))
        schema = json.loads((self.root / intake.INTAKE / "packet.schema.json").read_text())
        patterns = [
            schema["properties"]["specimen_id"]["pattern"],
            schema["$defs"]["asset"]["properties"]["specimen_id"]["pattern"],
            schema["$defs"]["measurement_record"]["properties"]["specimen_id"]["pattern"],
        ]
        self.assertEqual(patterns, [intake.SPECIMEN.pattern] * 3)

    def test_selected_e1_asset_must_be_redacted_even_if_spare_is_redacted(self) -> None:
        packet = self._submission()
        self._add_asset(packet, "A-SELECTED", "selected.jpg", "fitted", redacted=False)
        self._add_asset(packet, "A-SPARE", "spare.jpg", "fitted", redacted=True)
        packet["identity_evidence"]["E1_option_label_asset_id"] = "A-SELECTED"
        path = self.root / "private-packet.json"
        path.write_text(json.dumps(packet), encoding="utf-8")
        problems = intake.check_packet(path, intake.ROOT)
        self.assertTrue(any("selected option label must be redacted" in problem for problem in problems), problems)

    def test_host_measurement_cannot_cite_fitted_asset(self) -> None:
        packet = self._submission()
        self._add_asset(packet, "A-FITTED", "fitted.jpg", "fitted", redacted=True)
        record = json.loads((intake.ROOT / "catalog/templates/measurement-record.json").read_text())
        record["measurement_id"] = "MEAS-HOST-0001"
        record["readings"][0]["dimension_id"] = "BP_H01"
        record["evidence"]["files"] = ["fitted.jpg"]
        raw = json.dumps(record).encode("utf-8")
        (self.root / "host-measurement.json").write_bytes(raw)
        packet["measurement_records"].append({
            "record_id": "MEAS-HOST-0001", "specimen_id": packet["specimen_id"],
            "capture_state": "host", "relative_path": "host-measurement.json",
            "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
            "dimension_ids": [], "interface_measurand_ids": ["BP_H01"],
            "calibration_asset_ids": [],
        })
        path = self.root / "private-packet.json"
        path.write_text(json.dumps(packet), encoding="utf-8")
        problems = intake.check_packet(path, intake.ROOT)
        self.assertTrue(any("fitted.jpg is not from host capture state" in problem for problem in problems), problems)

    def test_vehicle_frame_requires_all_four_host_datums(self) -> None:
        packet = self._submission()
        self._add_asset(packet, "A-HOSTSCAN", "host.jpg", "host", redacted=True)
        record = json.loads((intake.ROOT / "catalog/templates/measurement-record.json").read_text())
        record["measurement_id"] = "MEAS-HOST-0001"
        record["readings"] = []
        for number in range(1, 5):
            reading = copy.deepcopy(json.loads((intake.ROOT / "catalog/templates/measurement-record.json").read_text())["readings"][0])
            reading["dimension_id"] = f"VF_H{number:02}"
            record["readings"].append(reading)
        record["evidence"]["files"] = ["host.jpg"]
        raw = json.dumps(record).encode("utf-8")
        (self.root / "frame-measurement.json").write_bytes(raw)
        packet["measurement_records"].append({
            "record_id": "MEAS-HOST-0001", "specimen_id": packet["specimen_id"],
            "capture_state": "host", "relative_path": "frame-measurement.json",
            "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
            "dimension_ids": [], "interface_measurand_ids": [f"VF_H{number:02}" for number in range(1, 5)],
            "calibration_asset_ids": [],
        })
        packet["vehicle_frame_reading_ids"] = [f"MEAS-HOST-0001:VF_H{number:02}" for number in range(1, 4)]
        path = self.root / "private-packet.json"
        path.write_text(json.dumps(packet), encoding="utf-8")
        problems = intake.check_packet(path, intake.ROOT)
        self.assertTrue(any("vehicle_frame_reading_ids: contract datum coverage differs" in problem and "VF_H04" in problem for problem in problems), problems)
        packet["vehicle_frame_reading_ids"].append("MEAS-HOST-0001:VF_H04")
        path.write_text(json.dumps(packet), encoding="utf-8")
        problems = intake.check_packet(path, intake.ROOT)
        self.assertFalse(any("vehicle_frame_reading_ids: contract datum coverage differs" in problem for problem in problems), problems)

    def test_vehicle_frame_rejects_part_state_reading(self) -> None:
        packet = self._submission()
        self._add_asset(packet, "A-FITTED", "fitted.jpg", "fitted", redacted=True)
        record = json.loads((intake.ROOT / "catalog/templates/measurement-record.json").read_text())
        record["measurement_id"] = "MEAS-FITTED-0001"
        record["readings"][0]["dimension_id"] = "VF_H01"
        record["evidence"]["files"] = ["fitted.jpg"]
        raw = json.dumps(record).encode("utf-8")
        (self.root / "fitted-measurement.json").write_bytes(raw)
        packet["measurement_records"].append({
            "record_id": "MEAS-FITTED-0001", "specimen_id": packet["specimen_id"],
            "capture_state": "fitted", "relative_path": "fitted-measurement.json",
            "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
            "dimension_ids": [], "interface_measurand_ids": ["VF_H01"],
            "calibration_asset_ids": [],
        })
        packet["vehicle_frame_reading_ids"] = ["MEAS-FITTED-0001:VF_H01"]
        path = self.root / "private-packet.json"
        path.write_text(json.dumps(packet), encoding="utf-8")
        problems = intake.check_packet(path, intake.ROOT)
        self.assertTrue(any("vehicle_frame_reading_ids: missing or wrong-state host reading" in problem for problem in problems), problems)

    def test_pet_preflight_refuses_hidden_tear_line_and_missing_region(self) -> None:
        packet = self._submission()
        packet["identity_evidence"]["E2_tear_line_present"] = True
        packet["identity_evidence"]["E2_region_shown"] = False
        path = self.root / "private-packet.json"
        path.write_text(json.dumps(packet), encoding="utf-8")
        problems = intake.check_packet(path, intake.ROOT)
        self.assertTrue(any("PET E1–E5 preflight refused: E2: tear_line" in problem for problem in problems), problems)
        self.assertTrue(any("PET E1–E5 preflight refused: E2: photographs do not show" in problem for problem in problems), problems)

    def test_pet_preflight_requires_two_fitted_removed_marks_and_rights(self) -> None:
        packet = self._submission()
        packet["identity_evidence"]["E5_personal_data_removed"] = False
        path = self.root / "private-packet.json"
        path.write_text(json.dumps(packet), encoding="utf-8")
        problems = intake.check_packet(path, intake.ROOT)
        self.assertTrue(any("E4_linking_marks: at least two" in problem for problem in problems), problems)
        self.assertTrue(any("PET E1–E5 preflight refused: E4: fewer than two marks" in problem for problem in problems), problems)
        self.assertTrue(any("PET E1–E5 preflight refused: E5:" in problem for problem in problems), problems)

    def test_linking_marks_need_distinct_ids_and_both_capture_states(self) -> None:
        packet = self._submission()
        self._add_asset(packet, "A-FITTED1", "fitted-one.jpg", "fitted", redacted=True)
        self._add_asset(packet, "A-REMOVED1", "removed-one.jpg", "removed", redacted=True)
        self._add_asset(packet, "A-FITTED2", "fitted-two.jpg", "fitted", redacted=True)
        packet["identity_evidence"]["E4_linking_marks"] = [
            {"mark_id": "MARK-ONE", "fitted_asset_id": "A-FITTED1", "removed_asset_id": "A-REMOVED1"},
            {"mark_id": "MARK-ONE", "fitted_asset_id": "A-FITTED2", "removed_asset_id": "A-FITTED2"},
        ]
        path = self.root / "private-packet.json"
        path.write_text(json.dumps(packet), encoding="utf-8")
        problems = intake.check_packet(path, intake.ROOT)
        self.assertTrue(any("mark_id: invalid or duplicate" in problem for problem in problems), problems)
        self.assertTrue(any("removed_asset_id: must reference a removed capture" in problem for problem in problems), problems)
        self.assertTrue(any("PET E1–E5 preflight refused: E4: fewer than two marks" in problem for problem in problems), problems)

    def test_contract_datum_mapping_is_reversible_and_complete(self) -> None:
        contract = json.loads((intake.ROOT / intake.CONTRACT).read_text())
        all_datums = [datum["id"] for interface in contract["interfaces"] for side in ("part_datums", "host_datums") for datum in interface[side]]
        self.assertEqual(len(all_datums), 56)
        self.assertEqual(len(set(all_datums)), 56)
        for datum_id in all_datums:
            mapped = intake.contract_datum_to_measurand(datum_id)
            self.assertEqual(intake.measurand_to_contract_datum(mapped), datum_id)
        for interface in contract["interfaces"]:
            row = {
                "part_reading_ids": [f"MEAS-PART-0001:{intake.contract_datum_to_measurand(d['id'])}" for d in interface["part_datums"]],
                "host_reading_ids": [f"MEAS-HOST-0001:{intake.contract_datum_to_measurand(d['id'])}" for d in interface["host_datums"]],
            }
            problems: list[str] = []
            intake._check_contract_coverage(row, interface, problems, interface["interface_id"])
            self.assertEqual(problems, [])
            if row["host_reading_ids"]:
                row["host_reading_ids"].pop()
                intake._check_contract_coverage(row, interface, problems, interface["interface_id"])
                self.assertTrue(any("coverage differs" in problem for problem in problems), problems)

    def test_submission_rejects_variant_conflict_and_release_claim(self) -> None:
        packet = self._submission()
        packet["identity_evidence"]["E1_m_codes_observed"] = ["M564", "M562"]
        packet["identity_evidence"]["E2_passenger_module_present"] = True
        packet["claims"]["occupant_safety"] = True
        path = self.root / "private-packet.json"
        path.write_text(json.dumps(packet), encoding="utf-8")
        problems = intake.check_packet(path, self.root)
        self.assertTrue(any("M562 passenger airbag is out of scope" in problem for problem in problems), problems)
        self.assertTrue(any("PET E1–E5 preflight refused: E1: M562" in problem for problem in problems), problems)
        self.assertTrue(any("passenger restraint configuration" in problem for problem in problems), problems)
        self.assertTrue(any("all claims must remain false" in problem for problem in problems), problems)
        self.assertTrue(any("not independently frozen" in problem or "cannot read JSON" in problem for problem in problems), problems)

    def test_m564_mixed_with_rs_codes_does_not_pass_non_rs_target(self) -> None:
        for rs_code in ("M002", "M003"):
            with self.subTest(rs_code=rs_code):
                packet = self._submission()
                packet["identity_evidence"]["E1_m_codes_observed"] = ["M564", rs_code]
                path = self.root / "private-packet.json"
                path.write_text(json.dumps(packet), encoding="utf-8")
                problems = intake.check_packet(path, intake.ROOT)
                self.assertTrue(any("Carrera RS M002/M003 is outside the non-RS target" in problem for problem in problems), problems)

    def test_observed_trim_number_preserves_pet_held_reason(self) -> None:
        packet = self._submission()
        identity = packet["identity_evidence"]
        identity["E3_trim_part_number_observed"] = "993 552 055 00"
        assets = (
            ("A-OPTION", "option.jpg", "fitted", "option_label_redacted"),
            ("A-REVERSE", "reverse.jpg", "removed", "passenger_reverse"),
            ("A-TRIM", "trim.jpg", "removed", "trim_label"),
            ("A-RIGHTS", "rights.txt", "not_applicable", "rights_grant"),
            ("A-CONTINUITY", "continuity.json", "not_applicable", "continuity_manifest"),
            ("A-FITMARK1", "fitted-mark-one.jpg", "fitted", "interface_photo"),
            ("A-REMMARK1", "removed-mark-one.jpg", "removed", "interface_photo"),
            ("A-FITMARK2", "fitted-mark-two.jpg", "fitted", "interface_photo"),
            ("A-REMMARK2", "removed-mark-two.jpg", "removed", "interface_photo"),
        )
        for asset_id, path, state, kind in assets:
            self._add_asset(packet, asset_id, path, state, redacted=True, kind=kind, publication=True)
        for asset in packet["assets"]:
            asset["rights_proof_asset_id"] = None if asset["asset_id"] == "A-RIGHTS" else "A-RIGHTS"
        identity["E1_option_label_asset_id"] = "A-OPTION"
        identity["E2_passenger_reverse_asset_id"] = "A-REVERSE"
        identity["E3_trim_label_asset_id"] = "A-TRIM"
        identity["E4_continuity_manifest_asset_id"] = "A-CONTINUITY"
        identity["E5_rights_manifest_asset_id"] = "A-RIGHTS"
        identity["E4_linking_marks"] = [
            {"mark_id": "MARK-ONE", "fitted_asset_id": "A-FITMARK1", "removed_asset_id": "A-REMMARK1"},
            {"mark_id": "MARK-TWO", "fitted_asset_id": "A-FITMARK2", "removed_asset_id": "A-REMMARK2"},
        ]
        continuity = {
            "specimen_id": packet["specimen_id"], "capture_campaign_id": packet["capture_campaign_id"],
            "asset_ids": [asset["asset_id"] for asset in packet["assets"]],
            "measurement_record_ids": [], "linking_marks": identity["E4_linking_marks"],
        }
        raw = json.dumps(continuity).encode("utf-8")
        (self.root / "continuity.json").write_bytes(raw)
        manifest = next(asset for asset in packet["assets"] if asset["asset_id"] == "A-CONTINUITY")
        manifest["bytes"] = len(raw)
        manifest["sha256"] = hashlib.sha256(raw).hexdigest()
        path = self.root / "private-packet.json"
        path.write_text(json.dumps(packet), encoding="utf-8")
        held: list[str] = []
        intake.check_packet(path, intake.ROOT, hold_reasons=held)
        self.assertTrue(any("E3: trim label is not confirmed against the matrix" in reason for reason in held), held)

    def test_cli_prints_pet_hold_reasons(self) -> None:
        output = io.StringIO()

        def held_packet(_path: Path, root: Path = intake.ROOT, hold_reasons: list[str] | None = None) -> list[str]:
            self.assertIsNotNone(hold_reasons)
            hold_reasons.append("E3: trim label is not confirmed against the matrix; open a contradiction")
            return []

        with patch.object(intake, "check_template", return_value=[]), patch.object(intake, "check_packet", side_effect=held_packet), contextlib.redirect_stdout(output):
            result = intake.main(["--packet", str(self.root / "synthetic-packet.json")])
        self.assertEqual(result, 0)
        self.assertIn("HOLD PET E1–E5: E3: trim label is not confirmed", output.getvalue())
        self.assertIn("held for independent review", output.getvalue())

    def test_submission_rejects_mixed_specimen_and_unverified_rights(self) -> None:
        packet = self._submission()
        packet["assets"].append({
            "asset_id": "A-TEST", "specimen_id": "SPEC-993-DASH-0002", "kind": "option_label_redacted",
            "capture_state": "fitted", "relative_path": "../escape.bin", "sha256": "0" * 64,
            "bytes": 12, "creator_role": "contributor", "licence": "private inspection only",
            "inspection_permission": False, "publication_permission": False,
            "rights_proof_asset_id": None, "redacted": False,
        })
        packet["identity_evidence"]["E1_option_label_asset_id"] = "A-TEST"
        path = self.root / "private-packet.json"
        path.write_text(json.dumps(packet), encoding="utf-8")
        problems = intake.check_packet(path, self.root)
        self.assertTrue(any("different specimen" in problem for problem in problems), problems)
        self.assertTrue(any("path escapes" in problem for problem in problems), problems)
        self.assertTrue(any("explicit permissions required" in problem for problem in problems), problems)
        self.assertTrue(any("option label must be redacted" in problem for problem in problems), problems)

    def test_submission_rejects_continuity_manifest_from_another_campaign(self) -> None:
        packet = self._submission()
        continuity = {
            "specimen_id": packet["specimen_id"],
            "capture_campaign_id": "SESSION-993-DASH-OTHER",
            "asset_ids": ["A-CONTINUITY"],
            "measurement_record_ids": [],
        }
        raw = json.dumps(continuity).encode("utf-8")
        (self.root / "continuity.json").write_bytes(raw)
        packet["assets"].append({
            "asset_id": "A-CONTINUITY", "specimen_id": packet["specimen_id"],
            "kind": "continuity_manifest", "capture_state": "not_applicable",
            "relative_path": "continuity.json", "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw), "creator_role": "contributor", "licence": "private inspection only",
            "inspection_permission": True, "publication_permission": False,
            "rights_proof_asset_id": "A-RIGHTS", "redacted": True,
        })
        packet["identity_evidence"]["E4_continuity_manifest_asset_id"] = "A-CONTINUITY"
        path = self.root / "private-packet.json"
        path.write_text(json.dumps(packet), encoding="utf-8")
        problems = intake.check_packet(path, self.root)
        self.assertTrue(any("capture campaign mismatch" in problem for problem in problems), problems)


if __name__ == "__main__":
    unittest.main()
