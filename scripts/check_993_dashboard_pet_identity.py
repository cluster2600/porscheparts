#!/usr/bin/env python3
"""Check the 993 dashboard-trim PET identity record and admit specimens.

The identity record (``parts/993-int-dashboard-trim-0001/evidence/
pet-identity.json``) maps option code and handedness to PET Kat 017 plates and
positions. This script refuses a mapping that its own plate does not support,
and refuses a part record that claims more than the matrix. It also holds the
same-specimen admission rules (evidence E1-E5) so that later measurement work
applies one rule set rather than restating it.

It checks documentary consistency only. Passing it says nothing about
geometry, fit, occupant safety or manufacturing.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDENTITY = ROOT / "parts/993-int-dashboard-trim-0001/evidence/pet-identity.json"
RECORD = ROOT / "catalog/parts/993-int-dashboard-trim-0001.json"

PART_NUMBER = re.compile(r"^\d{3} \d{3} \d{3} \d{2}$")
HAND_REMARK = {"LHD": "/LL", "RHD": "/RL"}
MAPPED = {"mapped_by_option_code", "title_match_only"}
UNMAPPED = {"unmapped_in_kat017"}
AIRBAG_COMPATIBLE = {
    "absent_by_option_code": {"passenger_airbag_absent"},
    "absent_by_plate_title": {"passenger_airbag_absent"},
    "present_by_plate_title": {"passenger_airbag_present"},
}
REQUIRED_ROWS = {f"{code}-{hand}" for code in ("M564", "M561", "M562", "M002", "M003") for hand in ("LHD", "RHD")}
EVIDENCE_IDS = ("E1-option-label", "E2-passenger-reverse", "E3-trim-label", "E4-continuity", "E5-rights")


def _entries(row: dict) -> list[tuple[str, dict]]:
    found = []
    for key in ("dashboard_trim", "knee_protection_strip"):
        for item in row.get(key) or []:
            found.append((key, item))
    return found


def check_identity(identity: dict) -> list[str]:
    """Return every inconsistency between the matrix and its own plates."""
    errors: list[str] = []
    plates = {plate["illustration"]: plate for plate in identity.get("plates", [])}
    rows = identity.get("matrix", [])
    ids = [row.get("row_id") for row in rows]
    missing = REQUIRED_ROWS - set(ids)
    if missing:
        errors.append(f"matrix: missing rows {sorted(missing)}")
    if len(ids) != len(set(ids)):
        errors.append("matrix: duplicate row_id")

    for row in rows:
        label = f"matrix[{row.get('row_id')}]"
        status = row.get("mapping_status")
        if status in UNMAPPED:
            for key in ("plate", "dashboard_trim", "knee_protection_strip"):
                if row.get(key) is not None:
                    errors.append(f"{label}.{key}: an unmapped row keeps this null")
            if not row.get("basis"):
                errors.append(f"{label}.basis: an unmapped row states why")
            continue
        if status not in MAPPED:
            errors.append(f"{label}.mapping_status: unknown value {status!r}")
            continue

        plate = plates.get(row.get("plate"))
        if plate is None:
            errors.append(f"{label}.plate: not a declared plate")
            continue
        allowed = AIRBAG_COMPATIBLE.get(row.get("passenger_airbag"), set())
        if plate.get("airbag_state_by_title") not in allowed:
            errors.append(
                f"{label}: plate {plate['illustration']} is titled "
                f"{plate.get('airbag_state_by_title')}, row says {row.get('passenger_airbag')}"
            )
        codes = plate.get("option_code_on_lines")
        if status == "mapped_by_option_code" and (not codes or row.get("option_code") not in codes):
            errors.append(f"{label}: plate {plate['illustration']} carries no line-level {row.get('option_code')}")
        if status == "title_match_only" and codes:
            errors.append(f"{label}: plate {plate['illustration']} has option codes; title_match_only is not allowed")
        if not row.get("dashboard_trim"):
            errors.append(f"{label}.dashboard_trim: a mapped row names at least one trim")

        hand = HAND_REMARK.get(row.get("handedness"))
        for key, item in _entries(row):
            where = f"{label}.{key}[{item.get('part_number')}]"
            if not PART_NUMBER.match(item.get("part_number") or ""):
                errors.append(f"{where}: malformed part number")
            if not isinstance(item.get("pdf_page"), int):
                errors.append(f"{where}: pdf_page required")
            if not item.get("position"):
                errors.append(f"{where}: position required")
            remark = item.get("remark") or ""
            if hand is None or hand not in remark.split():
                errors.append(f"{where}: remark {remark!r} does not state {hand}")
            source_plate = plates.get(item.get("plate", row.get("plate")))
            if source_plate is None:
                errors.append(f"{where}: plate not declared")
            else:
                if item.get("pdf_page") not in source_plate.get("pdf_pages", []):
                    errors.append(f"{where}: page {item.get('pdf_page')} is not a page of plate {source_plate['illustration']}")
                if source_plate.get("airbag_state_by_title") not in allowed:
                    errors.append(
                        f"{where}: plate {source_plate['illustration']} is titled "
                        f"{source_plate.get('airbag_state_by_title')}, row says {row.get('passenger_airbag')}"
                    )
                item_codes = source_plate.get("option_code_on_lines")
                if status == "mapped_by_option_code" and (not item_codes or row.get("option_code") not in item_codes):
                    errors.append(f"{where}: plate {source_plate['illustration']} carries no line-level {row.get('option_code')}")
                if status == "title_match_only" and item_codes:
                    errors.append(f"{where}: plate {source_plate['illustration']} has option codes; title_match_only is not allowed")

    target = identity.get("f0_target", {})
    target_row = f"{target.get('variant')}-{target.get('handedness')}"
    matching = [row for row in rows if row.get("row_id") == target_row]
    if matching and matching[0].get("mapping_status") in UNMAPPED:
        for key in ("dashboard_trim_part_number", "knee_protection_strip_part_numbers"):
            if target.get(key) is not None:
                errors.append(f"f0_target.{key}: must stay null while {target_row} is unmapped")

    protocol = identity.get("specimen_protocol", {})
    declared = tuple(item.get("evidence_id") for item in protocol.get("required_evidence", []))
    if declared != EVIDENCE_IDS:
        errors.append(f"specimen_protocol.required_evidence: expected {EVIDENCE_IDS}, found {declared}")
    return errors


def matrix_numbers(identity: dict, key: str) -> set[str]:
    return {item["part_number"] for row in identity.get("matrix", []) for k, item in _entries(row) if k == key}


def check_record(record: dict, identity: dict) -> list[str]:
    """Refuse a part record that claims identity the matrix does not support."""
    errors: list[str] = []
    trims = matrix_numbers(identity, "dashboard_trim")
    knees = matrix_numbers(identity, "knee_protection_strip")
    unmapped_codes = {
        row["option_code"] for row in identity.get("matrix", []) if row.get("mapping_status") in UNMAPPED
    }
    vehicle = record.get("vehicle", {})
    for number in vehicle.get("porsche_part_numbers", []):
        if number not in trims:
            errors.append(f"record: part number {number} is not a dashboard trim in the identity matrix")
    for variant in vehicle.get("variants", []):
        code = variant.split()[0]
        if code in unmapped_codes and "unmapped" not in variant.lower():
            errors.append(f"record: variant {variant!r} must say its trim number is unmapped")
    limits = " ".join(record.get("validation", {}).get("known_limits", []))
    for number in re.findall(r"\b\d{3} 552 0[5-7]\d \d{2}\b", limits):
        if number not in knees and number not in trims:
            errors.append(f"record: {number} in known_limits is not in the identity matrix")
    if "pet-identity" not in limits:
        errors.append("record: known_limits must point to evidence/pet-identity.md")
    return errors


def admit_specimen(evidence: dict) -> tuple[str, list[str]]:
    """Apply the E1-E5 rules to one specimen submission.

    This documentary preflight refuses explicit exclusions and holds otherwise
    complete submissions. It cannot independently verify off-repository photos,
    file hashes, specimen continuity or the contributor's publication rights.
    A missing key is a missing submission.
    """
    reasons: list[str] = []
    held: list[str] = []
    specimen = evidence.get("specimen_id") or ""
    if not re.fullmatch(r"SPEC-993-DASH-\d{4}", specimen):
        reasons.append("specimen_id: expected SPEC-993-DASH-NNNN")

    label = evidence.get("E1-option-label")
    if not label:
        reasons.append("E1: option-label evidence missing")
    else:
        if label.get("identifiers_visible") is not False:
            reasons.append("E1: VIN, chassis or personal identifiers not confirmed masked")
        codes = set(label.get("m_codes") or [])
        if "M562" in codes:
            reasons.append("E1: M562 passenger airbag, out of scope")
        elif "M561" in codes:
            held.append("E1: M561 driver-only airbag needs review")
        elif not codes & {"M564", "M002", "M003"}:
            held.append("E1: no airbag-state option code read")

    reverse = evidence.get("E2-passenger-reverse")
    if not reverse:
        reasons.append("E2: passenger-side reverse inspection missing")
    else:
        if reverse.get("region_shown") is not True:
            reasons.append("E2: photographs do not show the passenger-side region")
        for feature in ("airbag_module", "tear_line", "deployment_flap"):
            if reverse.get(feature) is not False:
                reasons.append(f"E2: {feature} observed or not ruled out")

    trim_label = evidence.get("E3-trim-label")
    if not trim_label:
        reasons.append("E3: trim-label transcription or 'none found' statement missing")
    elif trim_label.get("part_number") and trim_label.get("matches_matrix_row") is not True:
        held.append("E3: trim label is not confirmed against the matrix; open a contradiction")

    continuity = evidence.get("E4-continuity")
    if not continuity:
        reasons.append("E4: continuity manifest missing")
    else:
        files = continuity.get("files") or []
        if not files or any(
            not isinstance(f, dict)
            or f.get("specimen_id") != specimen
            or not isinstance(f.get("sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", f["sha256"]) is None
            or f["sha256"] == "0" * 64
            for f in files
        ):
            reasons.append("E4: every file needs this specimen ID and a non-zero SHA-256")
        if (continuity.get("linking_marks") or 0) < 2:
            reasons.append("E4: fewer than two marks link installed and removed states")

    rights = evidence.get("E5-rights")
    if not rights or not rights.get("licence") or rights.get("personal_data_removed") is not True:
        reasons.append("E5: publication licence or personal-data confirmation missing")

    if reasons:
        return "refused", reasons + held
    held.append("E1-E5: independent file, continuity and rights verification pending")
    return "held", held


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="check the identity record and the part record")
    parser.parse_args()
    identity = json.loads(IDENTITY.read_text(encoding="utf-8"))
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    errors = check_identity(identity) + check_record(record, identity)
    for error in errors:
        print(f"ERROR {error}", file=sys.stderr)
    if errors:
        return 1
    print("993 dashboard PET identity: consistent (documentary check only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
