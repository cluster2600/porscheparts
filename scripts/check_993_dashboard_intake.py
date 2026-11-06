#!/usr/bin/env python3
"""Fail closed on the public 993 dashboard intake template and private packets.

This checks provenance and completeness of a submission, not physical truth.
Passing a packet only puts it on hold for independent review. It never changes
the catalogue, interface contract, CAD, or release status.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

try:
    from scripts.validate_measurements import validate_measurement
    from scripts.check_993_dashboard_pet_identity import admit_specimen
except ModuleNotFoundError:  # Direct `python scripts/check_993_dashboard_intake.py`.
    from validate_measurements import validate_measurement
    from check_993_dashboard_pet_identity import admit_specimen

ROOT = Path(__file__).resolve().parents[1]
INTAKE = Path("twins/993-dashboard-f0/intake")
ASSEMBLY = Path("twins/993-dashboard-f0/assembly.json")
CONTRACT = Path("twins/993-dashboard-f0/interface-contracts.json")
DIMENSIONS = [f"D{number:02}" for number in range(1, 15)]
CAPTURE_STATES = ["fitted", "removed", "host"]
SPECIMEN = re.compile(r"^SPEC-993-DASH-[0-9]{4}$")
CAMPAIGN = re.compile(r"^SESSION-993-DASH-[A-Z0-9]{4,16}$")
ASSET_ID = re.compile(r"^A-[A-Z0-9._-]{3,64}$")
MEAS_ID = re.compile(r"^MEAS-[A-Z0-9._-]{3,64}$")
CONTRACT_DATUM = re.compile(r"^[A-Z]{2,4}-[PH][0-9]{2}$")
MEASURAND = re.compile(r"^[A-Z]{2,4}_[PH][0-9]{2}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_KINDS = {
    "fitted_scan": "fitted",
    "removed_scan": "removed",
    "reverse_support_scan": "removed",
    "host_scan": "host",
    "scale_calibration": None,
    "instrument_calibration": None,
}
ROOT_KEYS = {
    "$comment", "schema_version", "packet_kind", "status", "target_scenario",
    "specimen_id", "capture_campaign_id", "identity_evidence", "contract", "required_capture_states",
    "required_dimension_ids", "assets", "measurement_records", "vehicle_frame_reading_ids", "interface_evidence",
    "review", "claims",
}
ASSET_KEYS = {
    "asset_id", "specimen_id", "kind", "capture_state", "relative_path",
    "sha256", "bytes", "creator_role", "licence", "inspection_permission",
    "publication_permission", "rights_proof_asset_id", "redacted",
}
MEAS_KEYS = {
    "record_id", "specimen_id", "capture_state", "relative_path", "sha256",
    "bytes", "dimension_ids", "interface_measurand_ids", "calibration_asset_ids",
}
INTERFACE_KEYS = {"interface_id", "part_reading_ids", "host_reading_ids", "asset_ids", "status"}


def contract_datum_to_measurand(datum_id: str) -> str:
    """Map the frozen contract's hyphen ID to a MEAS-compatible ID."""
    if not CONTRACT_DATUM.fullmatch(datum_id):
        raise ValueError(f"unsupported contract datum ID: {datum_id!r}")
    return datum_id.replace("-", "_", 1)


def measurand_to_contract_datum(measurand_id: str) -> str:
    """Invert the mapping without accepting arbitrary or lossy aliases."""
    if not MEASURAND.fullmatch(measurand_id):
        raise ValueError(f"unsupported MEAS interface ID: {measurand_id!r}")
    return measurand_id.replace("_", "-", 1)


def _read_json(path: Path, errors: list[str], label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"{label}: cannot read JSON: {exc}")
        return None


def _keys(value: Any, expected: set[str], errors: list[str], label: str, optional: set[str] = frozenset()) -> bool:
    if not isinstance(value, dict):
        errors.append(f"{label}: expected object")
        return False
    missing = expected - value.keys() - optional
    extra = value.keys() - expected
    if missing:
        errors.append(f"{label}: missing {', '.join(sorted(missing))}")
    if extra:
        errors.append(f"{label}: unknown {', '.join(sorted(extra))}")
    return not (missing or extra)


def _interface_ids(root: Path, errors: list[str]) -> set[str]:
    assembly = _read_json(root / ASSEMBLY, errors, str(ASSEMBLY))
    if not isinstance(assembly, dict) or not isinstance(assembly.get("interfaces"), list):
        errors.append("assembly: interface inventory missing")
        return set()
    ids = [row.get("interface_id") for row in assembly["interfaces"] if isinstance(row, dict)]
    if len(ids) != 13 or not all(isinstance(item, str) for item in ids):
        errors.append("assembly: expected 13 unique interface IDs")
        return set()
    if len(set(ids)) != 13:
        errors.append("assembly: expected 13 unique interface IDs")
    return set(ids)


def _safe_file(base: Path, relative: Any, digest: Any, size: Any, errors: list[str], label: str) -> Path | None:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        errors.append(f"{label}.relative_path: expected a relative POSIX path")
        return None
    path = PurePosixPath(relative)
    if path.is_absolute() or path.as_posix() != relative or any(part in {".", ".."} for part in relative.split("/")):
        errors.append(f"{label}.relative_path: path escapes or is not normalized")
        return None
    if not isinstance(digest, str) or not DIGEST.fullmatch(digest):
        errors.append(f"{label}.sha256: expected lowercase SHA-256")
        return None
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        errors.append(f"{label}.bytes: expected positive byte count")
        return None
    try:
        target = (base / Path(*path.parts)).resolve()
        if not target.is_relative_to(base.resolve()) or not target.is_file():
            errors.append(f"{label}.relative_path: file absent or outside packet directory")
            return None
        actual_size = target.stat().st_size
    except (OSError, ValueError) as exc:
        errors.append(f"{label}.relative_path: cannot inspect file: {exc}")
        return None
    if actual_size != size:
        errors.append(f"{label}.bytes: declared {size}, found {actual_size}")
    hasher = hashlib.sha256()
    try:
        with target.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                hasher.update(chunk)
    except OSError as exc:
        errors.append(f"{label}.relative_path: cannot hash file: {exc}")
        return None
    actual_digest = hasher.hexdigest()
    if actual_digest != digest:
        errors.append(f"{label}.sha256: does not match file bytes")
    return target


def _check_contract_coverage(row: dict, contract_row: dict, errors: list[str], label: str) -> None:
    """Require every contract datum on the corresponding part/host side."""
    for field, contract_field in (("part_reading_ids", "part_datums"), ("host_reading_ids", "host_datums")):
        datums = contract_row.get(contract_field)
        if not isinstance(datums, list):
            errors.append(f"{label}: contract {contract_field} is malformed")
            continue
        expected: set[str] = set()
        for datum in datums:
            datum_id = datum.get("id") if isinstance(datum, dict) else None
            try:
                expected.add(contract_datum_to_measurand(datum_id))
            except (TypeError, ValueError):
                errors.append(f"{label}: unsupported contract datum {datum_id!r}")
        observed: set[str] = set()
        references = row.get(field)
        if not isinstance(references, list):
            errors.append(f"{label}.{field}: expected reading references")
            continue
        for reference in references:
            measurand_id = reference.rsplit(":", 1)[-1] if isinstance(reference, str) and ":" in reference else None
            try:
                measurand_to_contract_datum(measurand_id)
                observed.add(measurand_id)
            except (TypeError, ValueError):
                errors.append(f"{label}.{field}: invalid MEAS interface reference {reference!r}")
        missing = expected - observed
        extra = observed - expected
        if missing or extra:
            errors.append(f"{label}.{field}: contract datum coverage differs; missing={sorted(missing)}, extra={sorted(extra)}")


def _common(packet: Any, root: Path, errors: list[str]) -> set[str]:
    if not _keys(packet, ROOT_KEYS, errors, "packet", {"$comment"}):
        return set()
    if packet["schema_version"] != "1.0.0":
        errors.append("schema_version: expected 1.0.0")
    if packet["required_capture_states"] != CAPTURE_STATES:
        errors.append("required_capture_states: must list fitted, removed and host")
    if packet["required_dimension_ids"] != DIMENSIONS:
        errors.append("required_dimension_ids: must list D01–D14")
    target = packet["target_scenario"]
    if _keys(target, {"generation", "option_code_candidate", "driving_position_candidate", "rs_candidate", "model_year_observed", "physical_vehicle_confirmed"}, errors, "target_scenario"):
        if (target["generation"], target["option_code_candidate"], target["driving_position_candidate"], target["rs_candidate"]) != ("993", "M564", "left_hand_drive", False):
            errors.append("target_scenario: this packet covers only candidate M564 LHD non-RS")
    claims = packet["claims"]
    if _keys(claims, {"dimensional_fit", "occupant_safety", "manufacturing_release"}, errors, "claims"):
        if any(value is not False for value in claims.values()):
            errors.append("claims: all claims must remain false")
    if not isinstance(packet["assets"], list):
        errors.append("assets: expected array")
    if not isinstance(packet["measurement_records"], list):
        errors.append("measurement_records: expected array")
    vehicle_refs = packet["vehicle_frame_reading_ids"]
    if not isinstance(vehicle_refs, list) or any(not isinstance(value, str) for value in vehicle_refs) or len(vehicle_refs) != len(set(vehicle_refs)):
        errors.append("vehicle_frame_reading_ids: expected unique reading references")
    interface_ids = _interface_ids(root, errors)
    rows = packet["interface_evidence"]
    if not isinstance(rows, list):
        errors.append("interface_evidence: expected array")
    else:
        seen = []
        for index, row in enumerate(rows):
            label = f"interface_evidence[{index}]"
            if not _keys(row, INTERFACE_KEYS, errors, label):
                continue
            identifier = row["interface_id"]
            if not isinstance(identifier, str):
                errors.append(f"{label}.interface_id: expected string")
                continue
            seen.append(identifier)
            for field in ("part_reading_ids", "host_reading_ids", "asset_ids"):
                if not isinstance(row[field], list) or len(row[field]) != len(set(map(str, row[field]))):
                    errors.append(f"{label}.{field}: expected unique array")
        if len(seen) != 13 or set(seen) != interface_ids or len(set(seen)) != 13:
            errors.append("interface_evidence: IDs must match all 13 assembly interfaces exactly")
    return interface_ids


def check_template(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    schema = _read_json(root / INTAKE / "packet.schema.json", errors, "packet.schema.json")
    if not isinstance(schema, dict):
        errors.append("packet.schema.json: expected object")
    else:
        allowed = schema.get("properties", {}).get("claims", {}).get("properties", {})
        if any(allowed.get(key, {}).get("const") is not False for key in ("dimensional_fit", "occupant_safety", "manufacturing_release")):
            errors.append("packet.schema.json: claims must be fixed false")
        statuses = schema.get("properties", {}).get("status", {}).get("enum", [])
        if any(status in statuses for status in ("admitted", "approved", "released")):
            errors.append("packet.schema.json: admission status is forbidden")
    packet = _read_json(root / INTAKE / "packet-template.json", errors, "packet-template.json")
    if not isinstance(packet, dict):
        errors.append("packet-template.json: expected object")
        return errors
    _common(packet, root, errors)
    if packet.get("packet_kind") != "template" or packet.get("status") != "blocked_missing_external_evidence":
        errors.append("template: must remain blocked and marked template")
    if packet.get("specimen_id") is not None or packet.get("capture_campaign_id") is not None or packet.get("assets") != [] or packet.get("measurement_records") != []:
        errors.append("template: no specimen, campaign, assets or measurement records are allowed")
    target = packet.get("target_scenario", {})
    if isinstance(target, dict) and (target.get("model_year_observed") is not None or target.get("physical_vehicle_confirmed") is not False):
        errors.append("template: no physical vehicle has been confirmed")
    identity = packet.get("identity_evidence", {})
    if (not isinstance(identity, dict)
            or identity.get("E1_m_codes_observed") != []
            or identity.get("E4_linking_marks") != []
            or any(value is not None for key, value in identity.items() if key not in {"E1_m_codes_observed", "E4_linking_marks"})):
        errors.append("template: E1–E5 must remain null or empty")
    if packet.get("vehicle_frame_reading_ids") != []:
        errors.append("template: vehicle-frame readings must remain empty")
    contract = packet.get("contract", {})
    if not isinstance(contract, dict) or contract.get("sha256") is not None or contract.get("status") != "awaiting_frozen_independent_review":
        errors.append("template: no interface contract is frozen")
    review = packet.get("review", {})
    if not isinstance(review, dict) or review.get("verdict") != "blocked_missing_external_evidence" or any(value is not None for key, value in review.items() if key != "verdict"):
        errors.append("template: no reviewer or verdict may be prefilled")
    for row in packet.get("interface_evidence", []):
        if isinstance(row, dict) and (row.get("status") != "missing_data" or any(row.get(key) != [] for key in ("part_reading_ids", "host_reading_ids", "asset_ids"))):
            errors.append(f"template: {row.get('interface_id')} must remain empty")
    return errors


def check_packet(packet_path: Path, root: Path = ROOT, hold_reasons: list[str] | None = None) -> list[str]:
    """Check a private submission for documentary coherence; never admit it."""
    errors: list[str] = []
    packet = _read_json(packet_path, errors, str(packet_path))
    if not isinstance(packet, dict):
        errors.append(f"{packet_path}: expected packet object")
        return errors
    interface_ids = _common(packet, root, errors)
    if not interface_ids:
        return errors
    if any(not isinstance(packet.get(field), list) for field in ("assets", "measurement_records", "vehicle_frame_reading_ids", "interface_evidence")):
        return errors
    if packet.get("packet_kind") != "external_submission" or packet.get("status") not in ("submitted_unreviewed", "held_for_independent_review"):
        errors.append("packet: expected an unreviewed external submission")
    specimen = packet.get("specimen_id")
    if not isinstance(specimen, str) or not SPECIMEN.fullmatch(specimen):
        errors.append("specimen_id: expected opaque SPEC-993-DASH- identifier")
    campaign = packet.get("capture_campaign_id")
    if not isinstance(campaign, str) or not CAMPAIGN.fullmatch(campaign):
        errors.append("capture_campaign_id: expected opaque SESSION-993-DASH- identifier")
    target = packet.get("target_scenario", {})
    if isinstance(target, dict):
        year = target.get("model_year_observed")
        if not isinstance(year, int) or isinstance(year, bool) or not 1994 <= year <= 1998 or target.get("physical_vehicle_confirmed") is not True:
            errors.append("target_scenario: observed 1994–1998 vehicle confirmation required")
    contract_meta = packet.get("contract", {})
    if not _keys(contract_meta, {"path", "sha256", "status"}, errors, "contract"):
        contract_meta = {}
    if contract_meta.get("path") != CONTRACT.as_posix() or contract_meta.get("status") != "frozen_for_intake":
        errors.append("contract: exact independent contract must be frozen for intake")
    contract = _read_json(root / CONTRACT, errors, str(CONTRACT))
    contract_sha = contract_meta.get("sha256")
    if not isinstance(contract_sha, str) or not DIGEST.fullmatch(contract_sha):
        errors.append("contract.sha256: expected frozen contract digest")
    elif (root / CONTRACT).is_file() and hashlib.sha256((root / CONTRACT).read_bytes()).hexdigest() != contract_sha:
        errors.append("contract.sha256: does not match local contract")
    if isinstance(contract, dict):
        if contract.get("status") != "frozen_for_intake":
            errors.append("contract: local contract is not independently frozen for intake")
        contract_rows = contract.get("interfaces") if isinstance(contract.get("interfaces"), list) else []
        contract_ids = {row.get("interface_id") for row in contract_rows if isinstance(row, dict) and isinstance(row.get("interface_id"), str)}
        if contract_ids != interface_ids:
            errors.append("contract: interface IDs differ from assembly")
    contract_measurands: set[str] = set()
    if isinstance(contract, dict) and isinstance(contract.get("interfaces"), list):
        for interface in contract["interfaces"]:
            if not isinstance(interface, dict):
                continue
            for side in ("part_datums", "host_datums"):
                for datum in interface.get(side, []) if isinstance(interface.get(side), list) else []:
                    try:
                        contract_measurands.add(contract_datum_to_measurand(datum.get("id")))
                    except (AttributeError, TypeError, ValueError):
                        errors.append(f"contract: unsupported {side} datum ID")
    frame_datums: set[str] = set()
    vehicle_frame = contract.get("vehicle_frame") if isinstance(contract, dict) else None
    features = vehicle_frame.get("host_datum_features") if isinstance(vehicle_frame, dict) else None
    if not isinstance(features, list):
        errors.append("contract: vehicle-frame host datums missing")
    else:
        for datum in features:
            try:
                frame_datums.add(contract_datum_to_measurand(datum.get("id")))
            except (AttributeError, TypeError, ValueError):
                errors.append("contract: unsupported vehicle-frame host datum ID")
        if len(frame_datums) != len(features) or len(frame_datums) != 4:
            errors.append("contract: expected four unique vehicle-frame host datums")
    contract_measurands.update(frame_datums)
    base = packet_path.parent
    assets: dict[str, dict] = {}
    paths: set[str] = set()
    resolved_paths: set[Path] = set()
    for index, asset in enumerate(packet.get("assets", [])):
        label = f"assets[{index}]"
        if not _keys(asset, ASSET_KEYS, errors, label):
            continue
        asset_id = asset["asset_id"]
        if not isinstance(asset_id, str) or not ASSET_ID.fullmatch(asset_id) or asset_id in assets:
            errors.append(f"{label}.asset_id: invalid or duplicate")
            continue
        assets[asset_id] = asset
        if asset["specimen_id"] != specimen:
            errors.append(f"{label}.specimen_id: different specimen")
        relative = asset["relative_path"]
        if not isinstance(relative, str):
            errors.append(f"{label}.relative_path: expected string")
            continue
        if relative in paths:
            errors.append(f"{label}.relative_path: duplicate file")
        paths.add(relative)
        resolved = _safe_file(base, relative, asset["sha256"], asset["bytes"], errors, label)
        if resolved is not None:
            if resolved in resolved_paths:
                errors.append(f"{label}.relative_path: same file used by multiple manifest entries")
            resolved_paths.add(resolved)
        if not isinstance(asset["creator_role"], str) or not asset["creator_role"].strip() or not isinstance(asset["licence"], str) or not asset["licence"].strip() or asset["inspection_permission"] is not True or not isinstance(asset["publication_permission"], bool):
            errors.append(f"{label}: creator, licence and explicit permissions required")
    identity = packet.get("identity_evidence", {})
    if not _keys(identity, {"E1_option_label_asset_id", "E1_identifiers_visible", "E1_m_codes_observed", "E2_passenger_reverse_asset_id", "E2_region_shown", "E2_passenger_module_present", "E2_tear_line_present", "E2_passenger_flap_present", "E3_trim_label_asset_id", "E3_trim_part_number_observed", "E4_continuity_manifest_asset_id", "E4_linking_marks", "E5_rights_manifest_asset_id", "E5_personal_data_removed"}, errors, "identity_evidence"):
        identity = {}
    identity_assets = {
        "E1_option_label_asset_id": "option_label_redacted",
        "E2_passenger_reverse_asset_id": "passenger_reverse",
        "E3_trim_label_asset_id": "trim_label",
        "E4_continuity_manifest_asset_id": "continuity_manifest",
        "E5_rights_manifest_asset_id": "rights_grant",
    }
    for field, kind in identity_assets.items():
        asset_id = identity.get(field)
        asset = assets.get(asset_id) if isinstance(asset_id, str) else None
        if asset is None or asset.get("kind") != kind:
            errors.append(f"identity_evidence.{field}: required {kind} asset")
        elif asset.get("capture_state") != {"E1_option_label_asset_id": "fitted", "E2_passenger_reverse_asset_id": "removed", "E3_trim_label_asset_id": "removed", "E4_continuity_manifest_asset_id": "not_applicable", "E5_rights_manifest_asset_id": "not_applicable"}[field]:
            errors.append(f"identity_evidence.{field}: wrong capture state")
    codes = identity.get("E1_m_codes_observed")
    if (not isinstance(codes, list) or not codes or any(not isinstance(code, str) or not re.fullmatch(r"M[0-9]{3}", code) for code in codes)
            or len(codes) != len(set(codes))):
        errors.append("identity_evidence.E1_m_codes_observed: transcribe every distinct M-code")
        codes = []
    if "M564" not in codes:
        errors.append("identity_evidence.E1_m_codes_observed: target M564 not observed")
    if "M562" in codes:
        errors.append("identity_evidence.E1_m_codes_observed: M562 passenger airbag is out of scope")
    if "M561" in codes:
        errors.append("identity_evidence.E1_m_codes_observed: M561 needs a separate variant review")
    if "M002" in codes or "M003" in codes:
        errors.append("identity_evidence.E1_m_codes_observed: Carrera RS M002/M003 is outside the non-RS target")
    if identity.get("E1_identifiers_visible") is not False:
        errors.append("identity_evidence.E1_identifiers_visible: VIN and personal identifiers must be masked")
    if (identity.get("E2_region_shown") is not True or identity.get("E2_passenger_module_present") is not False
            or identity.get("E2_tear_line_present") is not False or identity.get("E2_passenger_flap_present") is not False):
        errors.append("identity_evidence.E2: passenger restraint configuration unresolved or contradictory")
    if identity.get("E5_personal_data_removed") is not True:
        errors.append("identity_evidence.E5_personal_data_removed: independent privacy review pending")
    part_number = identity.get("E3_trim_part_number_observed")
    if part_number is not None and (not isinstance(part_number, str) or not part_number.strip()):
        errors.append("identity_evidence.E3_trim_part_number_observed: expected null or observed label text")
    rights_id = identity.get("E5_rights_manifest_asset_id")
    for asset_id, asset in assets.items():
        if asset_id != rights_id and asset.get("rights_proof_asset_id") != rights_id:
            errors.append(f"assets[{asset_id}].rights_proof_asset_id: must bind E5 rights manifest")
        if asset_id == rights_id and asset.get("rights_proof_asset_id") is not None:
            errors.append(f"assets[{asset_id}].rights_proof_asset_id: rights grant has no self-reference")
    for kind, state in REQUIRED_KINDS.items():
        if not any(asset.get("kind") == kind and (state is None or asset.get("capture_state") == state) for asset in assets.values()):
            errors.append(f"assets: missing {kind} capture")
    selected_e1 = identity.get("E1_option_label_asset_id")
    selected_e1_asset = assets.get(selected_e1) if isinstance(selected_e1, str) else None
    if selected_e1_asset is None or selected_e1_asset.get("redacted") is not True:
        errors.append("identity_evidence.E1_option_label_asset_id: selected option label must be redacted")
    selected_e5 = assets.get(rights_id) if isinstance(rights_id, str) else None
    if selected_e5 is None or selected_e5.get("publication_permission") is not True:
        errors.append("identity_evidence.E5_rights_manifest_asset_id: written publication permission missing")
    image_kinds = {"option_label_redacted", "passenger_reverse", "trim_label", "fitted_scan", "removed_scan", "reverse_support_scan", "host_scan", "interface_photo"}
    for asset_id, asset in assets.items():
        if asset.get("kind") in image_kinds and asset.get("publication_permission") is not True:
            errors.append(f"assets[{asset_id}]: image publication permission missing")
    marks = identity.get("E4_linking_marks")
    if not isinstance(marks, list) or len(marks) < 2:
        errors.append("identity_evidence.E4_linking_marks: at least two fitted/removed marks required")
        marks = []
    seen_marks: set[str] = set()
    for index, mark in enumerate(marks):
        label = f"identity_evidence.E4_linking_marks[{index}]"
        if not _keys(mark, {"mark_id", "fitted_asset_id", "removed_asset_id"}, errors, label):
            continue
        mark_id = mark["mark_id"]
        if not isinstance(mark_id, str) or not re.fullmatch(r"MARK-[A-Z0-9._-]{3,32}", mark_id) or mark_id in seen_marks:
            errors.append(f"{label}.mark_id: invalid or duplicate")
        else:
            seen_marks.add(mark_id)
        for side, state in (("fitted_asset_id", "fitted"), ("removed_asset_id", "removed")):
            asset_id = mark[side]
            asset = assets.get(asset_id) if isinstance(asset_id, str) else None
            if asset is None or asset.get("capture_state") != state:
                errors.append(f"{label}.{side}: must reference a {state} capture of this specimen")
        if mark.get("fitted_asset_id") == mark.get("removed_asset_id"):
            errors.append(f"{label}: fitted and removed captures must differ")
    continuity_id = identity.get("E4_continuity_manifest_asset_id")
    continuity = assets.get(continuity_id) if isinstance(continuity_id, str) else None
    if isinstance(continuity, dict):
        continuity_path = _safe_file(base, continuity.get("relative_path"), continuity.get("sha256"), continuity.get("bytes"), errors, "E4 continuity manifest")
        continuity_doc = _read_json(continuity_path, errors, "E4 continuity manifest") if continuity_path else None
        if not isinstance(continuity_doc, dict) or continuity_doc.get("specimen_id") != specimen or continuity_doc.get("capture_campaign_id") != campaign:
            errors.append("E4 continuity manifest: specimen or capture campaign mismatch")
        else:
            listed_assets = continuity_doc.get("asset_ids")
            listed_records = continuity_doc.get("measurement_record_ids")
            packet_records = packet.get("measurement_records")
            expected_records = [item.get("record_id") for item in packet_records if isinstance(item, dict)] if isinstance(packet_records, list) else []
            if (not all(isinstance(value, str) for value in expected_records)
                    or not isinstance(listed_assets, list) or not all(isinstance(value, str) for value in listed_assets)
                    or not isinstance(listed_records, list) or not all(isinstance(value, str) for value in listed_records)
                    or len(listed_assets) != len(set(listed_assets)) or len(listed_records) != len(set(listed_records))
                    or set(listed_assets) != set(assets) or set(listed_records) != set(expected_records)
                    or continuity_doc.get("linking_marks") != marks):
                errors.append("E4 continuity manifest: file, measurement or linking-mark IDs do not match this packet")
    readings: dict[str, str] = {}
    dimensions: dict[str, set[str]] = {state: set() for state in CAPTURE_STATES}
    records_by_state: set[str] = set()
    record_ids: set[str] = set()
    for index, item in enumerate(packet.get("measurement_records", [])):
        label = f"measurement_records[{index}]"
        if not _keys(item, MEAS_KEYS, errors, label):
            continue
        if item["specimen_id"] != specimen:
            errors.append(f"{label}.specimen_id: different specimen")
        record_id = item["record_id"]
        if not isinstance(record_id, str) or not MEAS_ID.fullmatch(record_id) or record_id in record_ids:
            errors.append(f"{label}.record_id: invalid or duplicate")
            continue
        record_ids.add(record_id)
        state = item["capture_state"]
        if state not in CAPTURE_STATES:
            errors.append(f"{label}.capture_state: expected fitted, removed or host")
            continue
        records_by_state.add(state)
        relative = item["relative_path"]
        if not isinstance(relative, str):
            errors.append(f"{label}.relative_path: expected string")
            continue
        if relative in paths:
            errors.append(f"{label}.relative_path: duplicate file")
        paths.add(relative)
        path = _safe_file(base, relative, item["sha256"], item["bytes"], errors, label)
        if path is None:
            continue
        if path in resolved_paths:
            errors.append(f"{label}.relative_path: same file used by multiple manifest entries")
        resolved_paths.add(path)
        record = _read_json(path, errors, label)
        if not isinstance(record, dict):
            errors.append(f"{label}: expected measurement record object")
            continue
        for problem in validate_measurement(record):
            errors.append(f"{label}: {problem}")
        if record.get("measurement_id") != item["record_id"] or record.get("record_kind", "physical_measurement") != "physical_measurement":
            errors.append(f"{label}: record ID or physical kind mismatch")
        declared = item["dimension_ids"]
        interface_measurands = item["interface_measurand_ids"]
        if (not isinstance(declared, list) or not isinstance(interface_measurands, list)
                or any(value not in DIMENSIONS for value in declared)
                or any(not isinstance(value, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]{1,15}", value) or value in DIMENSIONS for value in interface_measurands)):
            errors.append(f"{label}: invalid D01–D14 or interface measurand list")
            continue
        if not set(interface_measurands).issubset(contract_measurands):
            errors.append(f"{label}: interface measurand is not in the frozen contract")
        record_readings = record.get("readings") if isinstance(record.get("readings"), list) else []
        actual = {reading.get("dimension_id") for reading in record_readings if isinstance(reading, dict) and isinstance(reading.get("dimension_id"), str)}
        if actual != set(declared) | set(interface_measurands) or len(declared) != len(set(declared)) or len(interface_measurands) != len(set(interface_measurands)):
            errors.append(f"{label}: manifest dimension IDs differ from record readings")
        if state == "host" and declared:
            errors.append(f"{label}: D01–D14 are part dimensions, not host measurements")
        dimensions[state].update(declared)
        evidence = record.get("evidence") if isinstance(record.get("evidence"), dict) else {}
        if evidence.get("level") != "A" or not evidence.get("files"):
            errors.append(f"{label}: repeated calibrated level-A readings and evidence files required")
        files = evidence.get("files")
        if isinstance(files, list):
            asset_paths = {asset.get("relative_path"): asset for asset in assets.values() if isinstance(asset.get("relative_path"), str)}
            for evidence_file in files:
                if not isinstance(evidence_file, str) or evidence_file not in asset_paths:
                    errors.append(f"{label}: evidence file is not bound to an asset: {evidence_file}")
                elif asset_paths[evidence_file].get("capture_state") != state:
                    errors.append(f"{label}: evidence file {evidence_file} is not from {state} capture state")
        for reading in record_readings:
            if not isinstance(reading, dict):
                continue
            samples = reading.get("samples")
            if not isinstance(samples, list) or len(samples) < 3:
                errors.append(f"{label}: {reading.get('dimension_id')} needs at least three samples")
            if state == "host" and reading.get("method") == "derived":
                errors.append(f"{label}: host reading cannot be derived from the part or model")
            key = f"{item['record_id']}:{reading.get('dimension_id')}"
            if key in readings:
                errors.append(f"{label}: duplicate reading reference {key}")
            readings[key] = state
        calibrations = item["calibration_asset_ids"]
        if not isinstance(calibrations, list) or not calibrations or any(not isinstance(asset_id, str) or assets.get(asset_id, {}).get("kind") not in {"scale_calibration", "instrument_calibration"} for asset_id in calibrations):
            errors.append(f"{label}: calibration asset linkage required")
    if records_by_state != set(CAPTURE_STATES):
        errors.append("measurement_records: fitted, removed and host records required")
    if not set(DIMENSIONS).issubset(dimensions["fitted"] | dimensions["removed"]):
        errors.append("measurement_records: D01–D14 coverage incomplete")
    for state in ("fitted", "removed"):
        if not set(DIMENSIONS[:4]).issubset(dimensions[state]):
            errors.append(f"measurement_records: D01–D04 {state} comparison missing")
    used_interface_readings: set[str] = set()
    frame_refs = packet.get("vehicle_frame_reading_ids", [])
    frame_observed: set[str] = set()
    for reference in frame_refs:
        if not isinstance(reference, str) or readings.get(reference) != "host":
            errors.append(f"vehicle_frame_reading_ids: missing or wrong-state host reading {reference}")
            continue
        measurand = reference.rsplit(":", 1)[-1]
        try:
            measurand_to_contract_datum(measurand)
        except (TypeError, ValueError):
            errors.append(f"vehicle_frame_reading_ids: invalid contract datum mapping {reference}")
            continue
        frame_observed.add(measurand)
        used_interface_readings.add(reference)
    if frame_observed != frame_datums:
        errors.append(f"vehicle_frame_reading_ids: contract datum coverage differs; missing={sorted(frame_datums - frame_observed)}, extra={sorted(frame_observed - frame_datums)}")
    for row in packet.get("interface_evidence", []):
        if not isinstance(row, dict) or row.get("interface_id") not in interface_ids:
            continue
        label = f"interface_evidence[{row['interface_id']}]"
        if row.get("status") != "submitted_unreviewed":
            errors.append(f"{label}.status: must remain submitted_unreviewed")
        for field, side in (("part_reading_ids", {"fitted", "removed"}), ("host_reading_ids", {"host"})):
            refs = row.get(field)
            if not isinstance(refs, list):
                continue
            for reference in refs:
                if not isinstance(reference, str) or readings.get(reference) not in side:
                    errors.append(f"{label}.{field}: missing or wrong-state reading {reference}")
                elif reference.rsplit(":", 1)[-1] in contract_measurands:
                    used_interface_readings.add(reference)
        asset_refs = row.get("asset_ids")
        for asset_id in asset_refs if isinstance(asset_refs, list) else []:
            if not isinstance(asset_id, str) or asset_id not in assets:
                errors.append(f"{label}.asset_ids: unknown asset {asset_id}")
        contract_rows = contract.get("interfaces") if isinstance(contract, dict) and isinstance(contract.get("interfaces"), list) else []
        contract_row = next((entry for entry in contract_rows if isinstance(entry, dict) and entry.get("interface_id") == row["interface_id"]), None)
        if isinstance(contract_row, dict):
            _check_contract_coverage(row, contract_row, errors, label)
        if not row.get("asset_ids"):
            errors.append(f"{label}: interface images/captures missing")
    unused = {reference for reference in readings if reference.rsplit(":", 1)[-1] in contract_measurands} - used_interface_readings
    if unused:
        errors.append(f"interface_evidence: interface readings are unbound: {sorted(unused)}")
    preflight_files = [
        {"specimen_id": item.get("specimen_id"), "sha256": item.get("sha256")}
        for item in [*packet["assets"], *packet["measurement_records"]] if isinstance(item, dict)
    ]
    preflight = {
        "specimen_id": specimen,
        "E1-option-label": {"identifiers_visible": identity.get("E1_identifiers_visible"), "m_codes": codes},
        "E2-passenger-reverse": {
            "region_shown": identity.get("E2_region_shown"),
            "airbag_module": identity.get("E2_passenger_module_present"),
            "tear_line": identity.get("E2_tear_line_present"),
            "deployment_flap": identity.get("E2_passenger_flap_present"),
        },
        "E3-trim-label": {"part_number": part_number, "matches_matrix_row": False},
        "E4-continuity": {"files": preflight_files, "linking_marks": len(seen_marks)},
        "E5-rights": {
            "licence": selected_e5.get("licence") if isinstance(selected_e5, dict) else None,
            "personal_data_removed": identity.get("E5_personal_data_removed"),
        },
    }
    preflight_status, preflight_reasons = admit_specimen(preflight)
    if preflight_status == "held":
        if hold_reasons is not None:
            hold_reasons.extend(preflight_reasons)
    else:
        errors.extend(f"PET E1–E5 preflight refused: {reason}" for reason in preflight_reasons)
    review = packet.get("review", {})
    if not _keys(review, {"independent_measurement_reviewer", "independent_interface_reviewer", "rights_privacy_reviewer", "professional_engineering_reviewer", "verdict"}, errors, "review") or not isinstance(review, dict) or review.get("verdict") not in ("submitted_unreviewed", "held_for_independent_review"):
        errors.append("review: an intake checker cannot record admission or release")
    return errors


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, help="private packet JSON; paths are relative to its directory")
    arguments = parser.parse_args(arguments)
    errors = check_template()
    holds: list[str] = []
    if arguments.packet is not None:
        errors.extend(check_packet(arguments.packet.resolve(), hold_reasons=holds))
    for reason in holds:
        print(f"HOLD PET E1–E5: {reason}")
    if errors:
        for error in errors:
            print(f"FAIL {error}")
        return 1
    if arguments.packet is None:
        print("OK public dashboard intake template remains empty and blocked")
    else:
        print("OK metadata coherent; held for independent review. No geometry or safety admission.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
