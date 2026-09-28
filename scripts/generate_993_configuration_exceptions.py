#!/usr/bin/env python3
"""Generate fail-closed contracts for 993 configuration constraints absent from PET summaries."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_ROOT = ROOT.parent / "porschefanatics.com"
DEFAULT_PET_TEXT = Path("/tmp/kat517-993.txt")
APPLICABILITY_EVIDENCE = ROOT / "twins" / "pet-993" / "applicability-evidence-f0.json"
CONFIGURATION_ROSTER = ROOT / "twins" / "vehicle-993" / "configuration-roster-f0.json"
CONFIGURATION_PART_LINKS = ROOT / "twins" / "vehicle-993" / "configuration-part-links-f0.json"
OUTPUT = ROOT / "twins" / "vehicle-993" / "configuration-exceptions-f0.json"
PET_SOURCE_ID = "pet-classic-993"

VARIANT_EXCEPTION_SPECS = (
    {
        "contract_id": "CONFIG-EXCEPTION-993-CARRERA-S",
        "vehicle_id": "993-carrera-s",
        "constraint_value": "993-carrera-s",
        "presence_pattern": r"CARRERA S FROM MODEL YEAR 1997",
        "presence_kind": "pet_order_information",
        "expected_occurrence_count": 8,
    },
    {
        "contract_id": "CONFIG-EXCEPTION-993-CARRERA-4S",
        "vehicle_id": "993-carrera-4s",
        "constraint_value": "993-carrera-4s",
        "presence_pattern": r"CARRERA 4S FROM MODEL YEAR 1996",
        "presence_kind": "pet_order_information",
        "expected_occurrence_count": 2,
    },
    {
        "contract_id": "CONFIG-EXCEPTION-993-TURBO-S",
        "vehicle_id": "993-turbo-s",
        "constraint_value": "993-turbo-s",
        "presence_pattern": r"M092\s+Special model Turbo S",
        "presence_kind": "pet_option_legend",
        "expected_occurrence_count": 1,
    },
)
A50_CONTRACT_ID = "CONFIG-EXCEPTION-993-A50-07"


class ContractError(ValueError):
    """Raised when configuration exception evidence does not close."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot_load:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"expected_object:{path}")
    return value


def render_json(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def matching_line_numbers(lines: list[str], pattern: str) -> list[int]:
    expression = re.compile(pattern, re.IGNORECASE)
    return [index for index, line in enumerate(lines, start=1) if expression.search(line)]


def vehicles_by_id(source_root: Path) -> dict[str, dict[str, Any]]:
    payload = load_json(source_root / "data" / "vehicles.json")
    rows = payload.get("vehicles")
    if not isinstance(rows, list):
        raise ContractError("vehicle_rows")
    result = {
        str(row["id"]): row
        for row in rows
        if isinstance(row, dict) and row.get("generationId") == "993" and row.get("id")
    }
    return result


def variant_contract(
    spec: dict[str, Any],
    vehicle: dict[str, Any],
    mappings: list[dict[str, Any]],
    lines: list[str],
) -> dict[str, Any]:
    presence_lines = matching_line_numbers(lines, str(spec["presence_pattern"]))
    if len(presence_lines) != 1:
        raise ContractError(
            f"variant_presence_evidence:{spec['vehicle_id']}:{presence_lines}"
        )
    if len(mappings) != spec["expected_occurrence_count"]:
        raise ContractError(
            f"variant_occurrence_count:{spec['vehicle_id']}:{len(mappings)}"
        )
    metadata = {
        key: vehicle.get(key)
        for key in (
            "manufacturer",
            "model",
            "generationId",
            "variant",
            "bodyStyle",
            "yearStart",
            "yearEnd",
            "engineCode",
            "transmissionCodes",
            "drivetrain",
            "optionCodes",
            "notes",
        )
        if key in vehicle
    }
    engine_status = (
        "explicitly_unverified_in_source_vehicle_note"
        if spec["vehicle_id"] == "993-turbo-s"
        else "source_vehicle_metadata_not_pet_summary_verified"
    )
    return {
        "contract_id": spec["contract_id"],
        "exception_kind": "variant_absent_from_pet_summary_types",
        "vehicle_id": spec["vehicle_id"],
        "constraint_value": spec["constraint_value"],
        "status": "tracked_exception_not_configuration_candidate",
        "catalogue_vehicle_metadata": metadata,
        "catalogue_vehicle_metadata_authority": (
            "documentary_source_record_not_independent_fitment_validation"
        ),
        "engine_code_status": engine_status,
        "pet_presence_evidence": {
            "kind": spec["presence_kind"],
            "pet_source_id": PET_SOURCE_ID,
            "logical_text_line_numbers": presence_lines,
        },
        "exact_part_constraint_occurrence_count": len(mappings),
        "exact_part_constraint_occurrence_ids": sorted(
            str(item["occurrence_twin_id"]) for item in mappings
        ),
        "pet_summary_type_record_count": 0,
        "configuration_candidate_count": 0,
        "human_reviewed": False,
        "promoted_to_vehicle_configuration": False,
        "complete_vehicle_bom": False,
        "missing_gates": [
            "find_or_review_direct_variant_type_vin_evidence",
            "resolve_engine_transmission_market_and_model_year_intersections",
            "review_all_variant_specific_part_constraints",
            "author_mounted_geometry_interfaces_materials_and_load_cases",
        ],
    }


def a50_contract(
    mappings: list[dict[str, Any]],
    applicability: dict[str, Any],
    lines: list[str],
) -> dict[str, Any]:
    if len(mappings) != 1:
        raise ContractError(f"a50_07_occurrence_count:{len(mappings)}")
    mapping = mappings[0]
    applicability_record = next(
        (
            record
            for record in applicability.get("records", [])
            if isinstance(record, dict)
            and record.get("occurrence_twin_id") == mapping.get("occurrence_twin_id")
        ),
        None,
    )
    if not isinstance(applicability_record, dict):
        raise ContractError("a50_07_applicability_record")
    annotation_lines = sorted(
        {
            line_number
            for annotation in applicability_record.get("annotations", [])
            if isinstance(annotation, dict) and annotation.get("token") == "A50.07"
            for line_number in annotation.get("logical_text_line_numbers", [])
            if isinstance(line_number, int)
        }
    )
    summary_lines = [
        index
        for index, line in enumerate(lines, start=1)
        if "TIPTRONIC" in line.upper()
        and "A50.05" in line
        and "A5007" in line
        and re.search(r"\b(?:97\s+V|98\s+W)\b", line)
    ]
    if len(annotation_lines) != 1 or len(summary_lines) != 2:
        raise ContractError(
            f"a50_07_relation_evidence:annotation={annotation_lines}:summary={summary_lines}"
        )
    return {
        "contract_id": A50_CONTRACT_ID,
        "exception_kind": "part_model_token_absent_from_pet_transmission_summary_type_codes",
        "constraint_value": "A50.07",
        "status": "tracked_exception_not_transmission_equivalence",
        "exact_part_constraint_occurrence_count": 1,
        "exact_part_constraint_occurrence_ids": [mapping["occurrence_twin_id"]],
        "part_annotation_evidence": {
            "oem_reference": mapping["oem_reference"],
            "part_master_twin_id": mapping["part_master_twin_id"],
            "pet_illustration": mapping["pet_illustration"],
            "candidate_quantity_per_car": mapping["candidate_quantity_per_car"],
            "model_token": "A50.07",
            "logical_text_line_numbers": annotation_lines,
        },
        "pet_summary_relation_hypothesis": {
            "summary_transmission_type_code": "A50.05",
            "summary_transmission_number_prefix": "A5007",
            "summary_model_years": [1997, 1998],
            "logical_text_line_numbers": summary_lines,
            "relation_status": "unresolved_do_not_equate_a50_07_with_a50_05_or_a5007",
            "equivalence_claim": False,
        },
        "configuration_candidate_count": 0,
        "human_reviewed": False,
        "promoted_to_vehicle_configuration": False,
        "complete_vehicle_bom": False,
        "missing_gates": [
            "review_pet_illustration_320_00_context_and_footnotes",
            "resolve_type_code_part_number_and_transmission_number_semantics",
            "prove_model_year_market_and_supersession_rules",
            "do_not_promote_until_a50_07_identity_is_unambiguous",
        ],
    }


def build(source_root: Path, pet_text_path: Path) -> dict[str, Any]:
    applicability = load_json(APPLICABILITY_EVIDENCE)
    roster = load_json(CONFIGURATION_ROSTER)
    part_links = load_json(CONFIGURATION_PART_LINKS)
    source_vehicles = vehicles_by_id(source_root)
    expected_sha256 = applicability.get("source_boundary", {}).get("pet_text_sha256")
    actual_sha256 = sha256_file(pet_text_path)
    if not isinstance(expected_sha256, str) or actual_sha256 != expected_sha256:
        raise ContractError("pet_text_sha256_mismatch")
    if roster.get("scope", {}).get("promoted_vehicle_configurations") != 0:
        raise ContractError("configuration_roster_must_fail_closed")
    if part_links.get("scope", {}).get("unresolved_constraint_occurrences") != 12:
        raise ContractError("expected_twelve_unresolved_constraints")
    unresolved = part_links.get("unresolved_constraint_links")
    if not isinstance(unresolved, list):
        raise ContractError("unresolved_constraint_links")
    lines = pet_text_path.read_text(encoding="utf-8").splitlines()

    by_value: dict[str, list[dict[str, Any]]] = {}
    for mapping in unresolved:
        if not isinstance(mapping, dict):
            continue
        values = mapping.get("constraint_values")
        if not isinstance(values, list) or len(values) != 1 or not isinstance(values[0], str):
            raise ContractError(f"exception_constraint_values:{mapping.get('constraint_link_id')}")
        by_value.setdefault(values[0], []).append(mapping)

    contracts: list[dict[str, Any]] = []
    contract_by_value: dict[str, str] = {}
    for spec in VARIANT_EXCEPTION_SPECS:
        vehicle_id = str(spec["vehicle_id"])
        vehicle = source_vehicles.get(vehicle_id)
        if not isinstance(vehicle, dict):
            raise ContractError(f"missing_source_vehicle:{vehicle_id}")
        value = str(spec["constraint_value"])
        contract = variant_contract(spec, vehicle, by_value.get(value, []), lines)
        contracts.append(contract)
        contract_by_value[value] = str(spec["contract_id"])
    a50 = a50_contract(by_value.get("A50.07", []), applicability, lines)
    contracts.append(a50)
    contract_by_value["A50.07"] = A50_CONTRACT_ID
    contracts.sort(key=lambda item: item["contract_id"])

    mappings: list[dict[str, Any]] = []
    for item in unresolved:
        value = item["constraint_values"][0]
        contract_id = contract_by_value.get(value)
        if contract_id is None:
            raise ContractError(f"unmapped_exception_value:{value}")
        mappings.append(
            {
                "exception_mapping_id": (
                    f"CONFIG-EXCEPTION-MAP-993-"
                    f"{sha256_text(str(item['constraint_link_id']) + '::' + contract_id)[:20].upper()}"
                ),
                "constraint_link_id": item["constraint_link_id"],
                "occurrence_twin_id": item["occurrence_twin_id"],
                "part_master_twin_id": item["part_master_twin_id"],
                "oem_reference": item["oem_reference"],
                "candidate_quantity_per_car": item["candidate_quantity_per_car"],
                "constraint_value": value,
                "exception_contract_id": contract_id,
                "mapping_status": "tracked_by_exception_contract_not_configuration_resolved",
                "promoted_to_vehicle_bom": False,
            }
        )
    mappings.sort(key=lambda item: item["exception_mapping_id"])
    mapping_counts = Counter(item["exception_contract_id"] for item in mappings)
    return {
        "$comment": (
            "Contrats F0 pour contraintes PET sans configuration de synthese. Chaque occurrence est "
            "tracee, mais aucune exception ne devient une configuration ou un BOM."
        ),
        "schema_version": "1.0.0",
        "generated_by": relative(Path(__file__).resolve()),
        "source_boundary": {
            "pet_source_id": PET_SOURCE_ID,
            "pet_text_expected_path": str(pet_text_path),
            "pet_text_sha256": actual_sha256,
            "raw_pet_text_copied": False,
            "source_vehicles_path": "../porschefanatics.com/data/vehicles.json",
            "source_vehicles_sha256": sha256_file(source_root / "data" / "vehicles.json"),
            "applicability_evidence": relative(APPLICABILITY_EVIDENCE),
            "applicability_evidence_sha256": sha256_file(APPLICABILITY_EVIDENCE),
            "configuration_roster": relative(CONFIGURATION_ROSTER),
            "configuration_roster_sha256": sha256_file(CONFIGURATION_ROSTER),
            "configuration_part_links": relative(CONFIGURATION_PART_LINKS),
            "configuration_part_links_sha256": sha256_file(CONFIGURATION_PART_LINKS),
        },
        "scope": {
            "exception_contract_count": len(contracts),
            "variant_exception_contract_count": 3,
            "transmission_exception_contract_count": 1,
            "input_unresolved_constraint_occurrences": len(unresolved),
            "mapped_exception_occurrences": len(mappings),
            "unmapped_exception_occurrences": len(unresolved) - len(mappings),
            "fully_resolved_configuration_exceptions": 0,
            "promoted_vehicle_configurations": 0,
            "promoted_vehicle_bom_entries": 0,
            "complete_vehicle_boms": 0,
        },
        "coverage": {
            "mapped_occurrences_by_contract": dict(sorted(mapping_counts.items())),
        },
        "exception_contracts": contracts,
        "exception_occurrence_mappings": mappings,
        "review_queue": {
            "status": "not_started",
            "entries": [
                {
                    "contract_id": contract["contract_id"],
                    "priority": "P0" if contract["contract_id"] == A50_CONTRACT_ID else "P1",
                    "review_status": "not_started",
                    "promoted": False,
                }
                for contract in contracts
            ],
        },
        "prohibited_claims": [
            "tracked_exception_is_resolved_configuration",
            "source_vehicle_metadata_is_independent_pet_fitment_proof",
            "a50_07_equals_a50_05_or_a5007",
            "variant_specific_part_annotation_is_complete_variant_bom",
            "exception_mapping_authorizes_geometry_manufacturing_or_road_use",
        ],
    }


def validate_contract(contract: dict[str, Any]) -> None:
    scope = contract.get("scope", {})
    contracts = contract.get("exception_contracts")
    mappings = contract.get("exception_occurrence_mappings")
    if not isinstance(contracts, list) or len(contracts) != scope.get("exception_contract_count"):
        raise ContractError("exception_contract_count")
    if not isinstance(mappings, list) or len(mappings) != scope.get(
        "mapped_exception_occurrences"
    ):
        raise ContractError("exception_mapping_count")
    if scope.get("input_unresolved_constraint_occurrences") != len(mappings) + scope.get(
        "unmapped_exception_occurrences"
    ):
        raise ContractError("exception_input_partition")
    for field in (
        "unmapped_exception_occurrences",
        "fully_resolved_configuration_exceptions",
        "promoted_vehicle_configurations",
        "promoted_vehicle_bom_entries",
        "complete_vehicle_boms",
    ):
        if scope.get(field) != 0:
            raise ContractError(f"scope_overclaim:{field}")
    contract_ids = [item.get("contract_id") for item in contracts]
    if None in contract_ids or len(contract_ids) != len(set(contract_ids)):
        raise ContractError("exception_contract_ids")
    expected_ids = {
        "CONFIG-EXCEPTION-993-CARRERA-S",
        "CONFIG-EXCEPTION-993-CARRERA-4S",
        "CONFIG-EXCEPTION-993-TURBO-S",
        A50_CONTRACT_ID,
    }
    if set(contract_ids) != expected_ids:
        raise ContractError("exception_contract_set")
    for item in contracts:
        if item.get("configuration_candidate_count") != 0:
            raise ContractError(f"exception_configuration_candidate:{item.get('contract_id')}")
        if item.get("human_reviewed") is not False:
            raise ContractError(f"exception_human_review_overclaim:{item.get('contract_id')}")
        if item.get("promoted_to_vehicle_configuration") is not False:
            raise ContractError(f"exception_promotion:{item.get('contract_id')}")
        if item.get("complete_vehicle_bom") is not False:
            raise ContractError(f"exception_complete_bom:{item.get('contract_id')}")
    a50 = next(item for item in contracts if item.get("contract_id") == A50_CONTRACT_ID)
    relation = a50.get("pet_summary_relation_hypothesis", {})
    if relation.get("relation_status") != "unresolved_do_not_equate_a50_07_with_a50_05_or_a5007":
        raise ContractError("a50_relation_status")
    if relation.get("equivalence_claim") is not False:
        raise ContractError("a50_equivalence_overclaim")
    mapping_ids: set[str] = set()
    occurrence_ids: set[str] = set()
    for mapping in mappings:
        mapping_id = mapping.get("exception_mapping_id")
        occurrence_id = mapping.get("occurrence_twin_id")
        if not isinstance(mapping_id, str) or mapping_id in mapping_ids:
            raise ContractError(f"exception_mapping_id:{mapping_id}")
        if not isinstance(occurrence_id, str) or occurrence_id in occurrence_ids:
            raise ContractError(f"exception_occurrence_id:{occurrence_id}")
        mapping_ids.add(mapping_id)
        occurrence_ids.add(occurrence_id)
        if mapping.get("exception_contract_id") not in expected_ids:
            raise ContractError(f"exception_mapping_contract:{mapping_id}")
        if mapping.get("mapping_status") != "tracked_by_exception_contract_not_configuration_resolved":
            raise ContractError(f"exception_mapping_status:{mapping_id}")
        if mapping.get("promoted_to_vehicle_bom") is not False:
            raise ContractError(f"exception_mapping_promotion:{mapping_id}")
    queue = contract.get("review_queue", {}).get("entries")
    if not isinstance(queue, list) or {item.get("contract_id") for item in queue} != expected_ids:
        raise ContractError("exception_review_queue")
    if any(item.get("review_status") != "not_started" or item.get("promoted") is not False for item in queue):
        raise ContractError("exception_review_queue_overclaim")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--check-index", action="store_true")
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--pet-text", type=Path, default=DEFAULT_PET_TEXT)
    args = parser.parse_args(argv)
    try:
        if args.check_index:
            validate_contract(load_json(OUTPUT))
            print(f"valid {relative(OUTPUT)}")
            return 0
        contract = build(args.source_root, args.pet_text)
        validate_contract(contract)
        expected = render_json(contract)
        if args.write:
            OUTPUT.parent.mkdir(parents=True, exist_ok=True)
            OUTPUT.write_text(expected, encoding="utf-8")
            print(f"wrote {relative(OUTPUT)}")
            return 0
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != expected:
            print(f"stale:{OUTPUT}", file=sys.stderr)
            return 1
        print(f"current {relative(OUTPUT)}")
        return 0
    except ContractError as exc:
        print(f"993 configuration exception error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
