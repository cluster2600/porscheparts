#!/usr/bin/env python3
"""Check the 993 dashboard F0 interface and measurement contracts (#567).

The contracts (``twins/993-dashboard-f0/interface-contracts.json``) are written
before any functional CAD. This script refuses a contract that:

- does not cover exactly the interfaces and load paths of the F0 assembly;
- carries a value, uncertainty or tolerance that no admitted reading supports;
- lets a host reading come from a derived, modelled or assumed method, or
  cites the PicoGK concept or another model as evidence;
- attaches to an unmapped variant a part number the PET identity audit (#566)
  assigns to another variant, or cites a catalogue item without its plate,
  page and position;
- leaves a safety-relevant interface without a professional engineering
  reviewer, or lets a model or one person hold two review roles.

This F0 revision freezes physical evidence admission, frame geometry, datum
values, attachment geometry and tolerances at missing data. A later #568
admission implementation must explicitly replace that freeze after independent
review; listing an existing repository file never admits a reading. It also
detects contradictions between readings when invoked separately. Passing it
is a documentary check: no fit, clearance or safety verdict follows from it.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "twins/993-dashboard-f0/interface-contracts.json"
ASSEMBLY = ROOT / "twins/993-dashboard-f0/assembly.json"
IDENTITY = ROOT / "parts/993-int-dashboard-trim-0001/evidence/pet-identity.json"

SIDES = {"part": "P", "host": "H"}
HOST_ONLY_KINDS = {"structural_attachment", "restraint_exclusion"}
MODEL_NAMES = re.compile(r"agent|claude|codex|gpt|model|picogk|generator|qwen", re.I)
REQUIRED_SAFETY_INTERFACES = {
    "IF_BODY_PANEL_TO_SHELL",
    "IF_TRIM_TO_BODY_PANEL",
    "IF_GLOVEBOX_TO_HOST",
    "IF_KNEE_STRIP_TO_ORIGINAL_MOUNTS",
    "IF_COLUMN_CLEARANCE",
    "IF_AIRBAG_CONFIGURATION",
}
M564_STATUS_EXCEPTIONS = {
    "IF_BODY_PANEL_TO_SHELL": "group_502_identity_only",
    "IF_COLUMN_CLEARANCE": "plate_heading",
    "IF_AIRBAG_CONFIGURATION": "option_code_definition",
}
M564_COLUMN_ITEMS = {
    ("964 347 013 02", "403-07", 266, "1", "/LL"),
    ("964 347 051 00", "403-07", 266, "2", "/LL"),
}


def _measurands(contract: dict):
    frame = contract.get("vehicle_frame", {})
    for item in frame.get("host_datum_features", []):
        yield "vehicle_frame", item
    for interface in contract.get("interfaces", []):
        for key in ("part_datums", "host_datums"):
            for item in interface.get(key, []):
                yield interface.get("interface_id"), item


def check_contract(contract: dict, assembly: dict, identity: dict) -> list[str]:
    errors: list[str] = []
    if contract.get("assembly") != str(ASSEMBLY.relative_to(ROOT)):
        errors.append("assembly: contract must cite the checked F0 assembly")
    if contract.get("identity_record") != str(IDENTITY.relative_to(ROOT)):
        errors.append("identity_record: contract must cite the checked PET matrix")
    if contract.get("status") != "proposed_awaiting_independent_review":
        errors.append("status: F0 contract must remain proposed pending independent review")
    frame = contract.get("vehicle_frame", {})
    if frame.get("origin") is not None or frame.get("axes") is not None:
        errors.append("vehicle_frame: F0 origin and axes must remain null")
    if frame.get("status") != "missing_data":
        errors.append("vehicle_frame: F0 status must remain missing_data")
    if frame.get("units") != "mm":
        errors.append("vehicle_frame: units must remain mm")
    frame_ids = [item.get("id") for item in frame.get("host_datum_features", [])]
    if set(frame_ids) != {"VF-H01", "VF-H02", "VF-H03", "VF-H04"} or len(frame_ids) != 4:
        errors.append("vehicle_frame: four independent body datum features are required")
    admission = contract.get("admission", {})
    admitted_paths = contract.get("evidence_layers", {}).get("admitted_physical_evidence")
    if admitted_paths != []:
        errors.append("evidence_layers.admitted_physical_evidence: F0 must remain empty until a separate admission gate is implemented")
    admitted = {path for path in admitted_paths if isinstance(path, str)} if isinstance(admitted_paths, list) else set()
    forbidden_methods = set(admission.get("host_methods_forbidden") or [])
    forbidden_sources = admission.get("forbidden_sources") or []
    if not {"derived", "model", "assumed"} <= forbidden_methods:
        errors.append("admission.host_methods_forbidden: must forbid derived, model and assumed")
    if not forbidden_sources:
        errors.append("admission.forbidden_sources: must list the F0 concept and model outputs")

    interface_list = contract.get("interfaces", [])
    interfaces = {i.get("interface_id"): i for i in interface_list}
    expected = {i["interface_id"] for i in assembly.get("interfaces", [])}
    if len(interfaces) != len(interface_list):
        errors.append("interfaces: duplicate interface_id")
    if set(interfaces) != expected:
        errors.append(f"interfaces: expected {sorted(expected)}, missing {sorted(expected - set(interfaces))}, "
                      f"extra {sorted(set(interfaces) - expected)}")
    load_paths = {lp["load_path_id"] for lp in assembly.get("load_paths_to_establish", [])}
    covered = set()
    for interface in interfaces.values():
        for lp in interface.get("load_paths", []):
            if lp not in load_paths:
                errors.append(f"{interface['interface_id']}.load_paths: unknown {lp}")
            covered.add(lp)
    if load_paths - covered:
        errors.append(f"load_paths: not covered by any interface {sorted(load_paths - covered)}")

    seen: set[str] = set()
    for owner, item in _measurands(contract):
        mid = item.get("id", "")
        where = f"{owner}.{mid}"
        if mid in seen:
            errors.append(f"{where}: duplicate measurand id")
        seen.add(mid)
        side = item.get("side")
        if side not in SIDES or SIDES[side] not in mid.split("-")[-1][:1]:
            errors.append(f"{where}: side {side!r} does not match its id")
        if not item.get("methods"):
            errors.append(f"{where}: no method")
        if item.get("unit") != "mm" and item.get("kind") not in {"count", "identity", "state", "observation"}:
            errors.append(f"{where}: geometric measurand must use mm")
        if not isinstance(item.get("repetitions_min"), int) or item["repetitions_min"] < 3:
            errors.append(f"{where}: at least three independent repetitions required")
        if side == "host" and forbidden_methods & set(item.get("methods", [])):
            errors.append(f"{where}: host reading by a forbidden method")
        evidence = item.get("evidence")
        if any(item.get(key) is not None for key in ("value", "uncertainty", "evidence")):
            errors.append(f"{where}: F0 datum value, uncertainty and evidence must remain null")
        if item.get("value") is not None or item.get("uncertainty") is not None:
            if evidence is None or evidence not in admitted:
                errors.append(f"{where}: value without an admitted reading")
            elif item.get("uncertainty") is None:
                errors.append(f"{where}: value without uncertainty")
        if evidence is not None:
            if any(token in str(evidence) for token in forbidden_sources):
                errors.append(f"{where}: evidence cites a model or the F0 concept")
            if evidence not in admitted:
                errors.append(f"{where}: evidence {evidence!r} is not admitted")

    for path in admitted:
        if any(token in path for token in forbidden_sources) or not (ROOT / path).is_file():
            errors.append(f"evidence_layers.admitted_physical_evidence: refused {path}")

    role_list = contract.get("reviewer_roles", [])
    roles = {r.get("role"): r for r in role_list}
    if len(roles) != len(role_list) or set(roles) != {
        "preparer", "independent_measurement_reviewer", "independent_interface_reviewer",
        "rights_privacy_reviewer", "professional_engineering_reviewer",
    }:
        errors.append("reviewer_roles: all five distinct roles are required")
    people = [r.get("assigned_to") for r in roles.values() if r.get("assigned_to")]
    if len(people) != len(set(people)):
        errors.append("reviewer_roles: one person holds two roles")
    if any(MODEL_NAMES.search(str(p)) for p in people):
        errors.append("reviewer_roles: a model or generator cannot hold a role")
    interface_reviewer = roles.get("independent_interface_reviewer", {}).get("assigned_to")

    rows = {row["row_id"]: row for row in identity.get("matrix", [])}
    candidate_list = contract.get("candidate_variants", [])
    candidates = {c["row_id"]: c for c in candidate_list}
    if len(candidates) != len(candidate_list) or set(candidates) != {"M564-LHD", "M002-LHD", "M003-LHD"}:
        errors.append("candidate_variants: F0 target and documented alternatives must remain M564-LHD, M002-LHD and M003-LHD")
    if candidates.get("M564-LHD", {}).get("role") != "F0 target":
        errors.append("candidate_variants: M564-LHD must remain the F0 target")
    for row_id, candidate in candidates.items():
        if row_id not in rows:
            errors.append(f"candidate_variants: {row_id} is not a row of the identity matrix")
        elif candidate.get("identity_status") != rows[row_id]["mapping_status"]:
            errors.append(f"candidate_variants: {row_id} status differs from the identity matrix")
    borrowed = {
        row_id: {item["part_number"]
                 for other_id, other in rows.items() if other_id != row_id
                 for key in ("dashboard_trim", "knee_protection_strip")
                 for item in other.get(key) or []}
        for row_id in rows
    }
    own = {row_id: {item["part_number"] for key in ("dashboard_trim", "knee_protection_strip")
                    for item in row.get(key) or []} for row_id, row in rows.items()}

    for iid, interface in interfaces.items():
        if interface.get("status") != "missing_data":
            errors.append(f"{iid}: F0 interface status must remain missing_data")
        attachments = interface.get("attachments", {})
        if any(attachments.get(key) is not None for key in ("count", "hole_pattern", "axes")):
            errors.append(f"{iid}.attachments: F0 physical attachment fields must remain null")
        if attachments.get("fastener_identity") not in (None, "see catalogue_identity; assignment unknown"):
            errors.append(f"{iid}.attachments: F0 fastener assignment must remain unknown")
        if interface.get("tolerances", {}).get("value") is not None:
            errors.append(f"{iid}.tolerances: F0 tolerance value must remain null")
        if iid in REQUIRED_SAFETY_INTERFACES and interface.get("safety_relevant") is not True:
            errors.append(f"{iid}: required safety interface must be marked safety_relevant")
        if not interface.get("acceptance"):
            errors.append(f"{iid}: no acceptance rule")
        if not interface.get("required_images"):
            errors.append(f"{iid}: no required images")
        if interface.get("tolerances", {}).get("value") is not None and not interface_reviewer:
            errors.append(f"{iid}: tolerance set without an assigned interface reviewer")
        if interface.get("safety_relevant") and "professional_engineering_reviewer" not in roles:
            errors.append(f"{iid}: safety-relevant without a professional engineering reviewer role")
        has_part = bool(interface.get("part_datums"))
        has_host = bool(interface.get("host_datums"))
        if not has_host:
            errors.append(f"{iid}: no independent host datum")
        if not has_part and interface.get("kind") not in HOST_ONLY_KINDS and not interface.get("delegated_to"):
            errors.append(f"{iid}: no part datum")
        if interface.get("delegated_to") and not (ROOT / interface["delegated_to"]).is_file():
            errors.append(f"{iid}.delegated_to: file not found")

        identities = interface.get("catalogue_identity", {})
        if set(identities) != set(candidates):
            errors.append(f"{iid}.catalogue_identity: variants differ from candidate_variants")
        for row_id, block in identities.items():
            if row_id == "M564-LHD":
                expected_status = M564_STATUS_EXCEPTIONS.get(iid, "unmapped_in_kat017")
                if block.get("status") != expected_status:
                    errors.append(f"{iid}.catalogue_identity[M564-LHD]: F0 status must remain {expected_status}")
                if iid != "IF_COLUMN_CLEARANCE" and block.get("items") is not None:
                    errors.append(f"{iid}.catalogue_identity[M564-LHD]: unmapped dashboard target cannot gain part numbers")
                if iid == "IF_COLUMN_CLEARANCE":
                    actual = {
                        (item.get("part_number"), item.get("plate"), item.get("pdf_page"),
                         item.get("position"), item.get("remark"))
                        for item in block.get("items") or []
                    }
                    if actual != M564_COLUMN_ITEMS or len(block.get("items") or []) != len(M564_COLUMN_ITEMS):
                        errors.append(f"{iid}.catalogue_identity[M564-LHD]: steering items must match the reviewed PET inventory")
            for item in block.get("items") or []:
                where = f"{iid}.catalogue_identity[{row_id}][{item.get('part_number')}]"
                if not all(item.get(k) for k in ("source_id", "plate", "pdf_page", "position")):
                    errors.append(f"{where}: plate, page and position required")
                number = item.get("part_number")
                if number in borrowed.get(row_id, set()) and number not in own.get(row_id, set()):
                    errors.append(f"{where}: number belongs to another variant in the identity matrix")
            if rows.get(row_id, {}).get("mapping_status") == "unmapped_in_kat017":
                if block.get("status") == "plate_inventory":
                    errors.append(f"{iid}.catalogue_identity[{row_id}]: an unmapped variant has no plate inventory")
                if block.get("status") == "unmapped_in_kat017" and block.get("items") is not None:
                    errors.append(f"{iid}.catalogue_identity[{row_id}]: an unmapped dashboard identity has no part numbers")
    return errors


def find_contradictions(readings: list[dict]) -> list[tuple[dict, dict]]:
    """Pairs of readings of one measurand on one specimen whose intervals do not overlap."""
    found = []
    for a, b in combinations(readings, 2):
        if a["measurand"] != b["measurand"] or a["specimen_id"] != b["specimen_id"]:
            continue
        if abs(a["value"] - b["value"]) > a["uncertainty"] + b["uncertainty"]:
            found.append((a, b))
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="check the contracts against the assembly and identity")
    parser.parse_args()
    load = lambda p: json.loads(p.read_text(encoding="utf-8"))  # noqa: E731
    errors = check_contract(load(CONTRACTS), load(ASSEMBLY), load(IDENTITY))
    for error in errors:
        print(f"ERROR {error}", file=sys.stderr)
    if errors:
        return 1
    print("993 dashboard F0 interface contracts: consistent, all values null (documentary check only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
