"""Safety boundaries for the empty 993 dashboard intake and private packet gate."""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

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

    def test_template_rejects_prefilled_specimen_and_reading(self) -> None:
        data = self._template()
        data["specimen_id"] = "SPEC-993-DASH-TEST"
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
        packet["specimen_id"] = "SPEC-993-DASH-TEST"
        packet["capture_campaign_id"] = "SESSION-993-DASH-TEST"
        packet["target_scenario"]["model_year_observed"] = 1996
        packet["target_scenario"]["physical_vehicle_confirmed"] = True
        packet["identity_evidence"]["E1_option_code_observed"] = "M564"
        packet["identity_evidence"]["E2_passenger_module_present"] = False
        packet["identity_evidence"]["E2_passenger_flap_present"] = False
        packet["contract"]["sha256"] = "0" * 64
        packet["contract"]["status"] = "frozen_for_intake"
        packet["review"]["verdict"] = "submitted_unreviewed"
        for interface in packet["interface_evidence"]:
            interface["status"] = "submitted_unreviewed"
        return packet

    def test_submission_rejects_variant_conflict_and_release_claim(self) -> None:
        packet = self._submission()
        packet["identity_evidence"]["E1_option_code_observed"] = "M562"
        packet["identity_evidence"]["E2_passenger_module_present"] = True
        packet["claims"]["occupant_safety"] = True
        path = self.root / "private-packet.json"
        path.write_text(json.dumps(packet), encoding="utf-8")
        problems = intake.check_packet(path, self.root)
        self.assertTrue(any("expected observed M564" in problem for problem in problems), problems)
        self.assertTrue(any("passenger restraint configuration" in problem for problem in problems), problems)
        self.assertTrue(any("all claims must remain false" in problem for problem in problems), problems)
        self.assertTrue(any("not independently frozen" in problem or "cannot read JSON" in problem for problem in problems), problems)

    def test_submission_rejects_mixed_specimen_and_unverified_rights(self) -> None:
        packet = self._submission()
        packet["assets"].append({
            "asset_id": "A-TEST", "specimen_id": "SPEC-993-DASH-OTHER", "kind": "option_label_redacted",
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
