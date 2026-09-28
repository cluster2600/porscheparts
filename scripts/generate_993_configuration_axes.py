#!/usr/bin/env python3
"""Generate fail-closed 993 body and transmission configuration-axis contracts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
APPLICABILITY_EVIDENCE = ROOT / "twins" / "pet-993" / "applicability-evidence-f0.json"
DEFAULT_PET_TEXT = Path("/tmp/kat517-993.txt")
OUTPUT = ROOT / "twins" / "vehicle-993" / "configuration-axes-f0.json"


class ContractError(ValueError):
    """Raised when configuration-axis evidence does not close."""


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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def summary_transmission_evidence(text: str) -> dict[str, Any]:
    tiptronic_codes: dict[str, set[int]] = {}
    manual_codes: dict[str, set[int]] = {}
    for line_number, line in enumerate(text.splitlines(), start=1):
        if "4-SPEED" in line and ("TIPTRONIC" in line or "TIPTRINIC" in line):
            match = re.search(r"\b(A50\.\d{2})\b", line)
            if match:
                tiptronic_codes.setdefault(match.group(1), set()).add(line_number)
        if "6-SPEED" in line:
            match = re.search(r"\b(G(?:50|64)\.\d{2})\b", line)
            if match:
                manual_codes.setdefault(match.group(1), set()).add(line_number)
    if not tiptronic_codes or not manual_codes:
        raise ContractError("missing_pet_transmission_summary_evidence")
    return {
        "tiptronic_4_speed_code_examples": {
            code: sorted(line_numbers) for code, line_numbers in sorted(tiptronic_codes.items())
        },
        "manual_6_speed_code_examples": {
            code: sorted(line_numbers) for code, line_numbers in sorted(manual_codes.items())
        },
        "interpretation": (
            "Le sommaire PET associe explicitement TIPTRONIC aux codes A50 et 4-SPEED; "
            "les lignes 6-SPEED observees utilisent les familles G50 et G64."
        ),
        "claims": {
            "complete_code_mapping": False,
            "vehicle_fitment": False,
            "functional_validation": False,
        },
    }


def annotation_matches(
    record: dict[str, Any], kind: str, token_predicate: Callable[[str], bool]
) -> bool:
    return any(
        isinstance(annotation, dict)
        and annotation.get("kind") == kind
        and isinstance(annotation.get("token"), str)
        and token_predicate(annotation["token"])
        for annotation in record.get("annotations", [])
    )


def axis_candidate(record: dict[str, Any]) -> dict[str, Any]:
    quantities = record.get("observed_quantities_per_car")
    quantity = quantities[0] if isinstance(quantities, list) and len(quantities) == 1 else None
    return {
        "occurrence_twin_id": record.get("occurrence_twin_id"),
        "part_master_twin_id": record.get("part_master_twin_id"),
        "oem_reference": record.get("oem_reference"),
        "pet_illustration": record.get("pet_illustration"),
        "pet_page": record.get("pet_page"),
        "matching_model_annotations": [
            annotation.get("token")
            for annotation in record.get("annotations", [])
            if isinstance(annotation, dict)
        ],
        "candidate_quantity_per_car": quantity,
        "evidence_status": "machine_extracted_configuration_axis_not_human_reviewed",
        "promoted_to_vehicle_bom": False,
        "geometry_revision": None,
        "mounted_transform": None,
        "selected_material": None,
        "manufacturing_route": None,
    }


def build_axis_contract(
    records: list[dict[str, Any]],
    *,
    contract_id: str,
    axis: str,
    value: str,
    evidence_kind: str,
    token_predicate: Callable[[str], bool],
    interpretation_status: str,
) -> dict[str, Any]:
    matched = [
        record
        for record in records
        if annotation_matches(record, evidence_kind, token_predicate)
    ]
    candidates = [axis_candidate(record) for record in matched]
    candidates.sort(key=lambda item: str(item.get("occurrence_twin_id")))
    if not candidates:
        raise ContractError(f"empty_axis_contract:{contract_id}")
    return {
        "contract_id": contract_id,
        "axis": axis,
        "value": value,
        "status": "provisional_axis_contract_not_a_vehicle_configuration",
        "interpretation_status": interpretation_status,
        "candidate_occurrence_count": len(candidates),
        "candidate_occurrences_with_single_quantity": sum(
            candidate["candidate_quantity_per_car"] is not None for candidate in candidates
        ),
        "candidate_occurrences": candidates,
        "complete_vehicle_bom": False,
        "combined_with_model_variant": False,
        "human_reviewed": False,
        "missing_gates": [
            "resolve_model_year_market_engine_and_option_intersections",
            "review_quantities_exclusions_and_supersessions",
            "promote_only_after_human_pet_review",
            "author_geometry_interfaces_materials_and_load_cases",
        ],
    }


def build(pet_text_path: Path) -> dict[str, Any]:
    applicability = load_json(APPLICABILITY_EVIDENCE)
    source_boundary = applicability.get("source_boundary", {})
    expected_sha256 = source_boundary.get("pet_text_sha256")
    actual_sha256 = sha256_file(pet_text_path)
    if not isinstance(expected_sha256, str) or expected_sha256 != actual_sha256:
        raise ContractError("pet_text_sha256_mismatch")
    text = pet_text_path.read_text(encoding="utf-8")
    records = applicability.get("records")
    if not isinstance(records, list):
        raise ContractError("applicability_records")
    typed_records = [record for record in records if isinstance(record, dict)]

    contracts = [
        build_axis_contract(
            typed_records,
            contract_id="CONFIG-AXIS-993-BODY-CABRIOLET",
            axis="body_style",
            value="Cabriolet",
            evidence_kind="body_style",
            token_predicate=lambda token: "CABRIO" in token,
            interpretation_status="direct_pet_body_style_token",
        ),
        build_axis_contract(
            typed_records,
            contract_id="CONFIG-AXIS-993-BODY-TARGA",
            axis="body_style",
            value="Targa",
            evidence_kind="body_style",
            token_predicate=lambda token: "TARGA" in token,
            interpretation_status="direct_pet_body_style_token",
        ),
        build_axis_contract(
            typed_records,
            contract_id="CONFIG-AXIS-993-TRANSMISSION-MANUAL-6-SPEED",
            axis="transmission_family",
            value="manual_6_speed_candidate",
            evidence_kind="transmission_code",
            token_predicate=lambda token: token.startswith(("G50", "G64")),
            interpretation_status="pet_summary_maps_g50_g64_examples_to_6_speed",
        ),
        build_axis_contract(
            typed_records,
            contract_id="CONFIG-AXIS-993-TRANSMISSION-TIPTRONIC-4-SPEED",
            axis="transmission_family",
            value="tiptronic_4_speed_candidate",
            evidence_kind="transmission_code",
            token_predicate=lambda token: token.startswith("A50"),
            interpretation_status="pet_summary_explicitly_maps_tiptronic_to_a50_4_speed",
        ),
    ]
    return {
        "$comment": (
            "Contrats F0 d'axes de configuration derives du PET. Ils isolent carrosserie et famille "
            "de boite mais ne constituent ni des variantes completes ni des nomenclatures vehicule."
        ),
        "schema_version": "1.0.0",
        "generated_by": relative(Path(__file__).resolve()),
        "source_boundary": {
            "applicability_evidence": relative(APPLICABILITY_EVIDENCE),
            "applicability_evidence_sha256": sha256_file(APPLICABILITY_EVIDENCE),
            "pet_source_id": source_boundary.get("pet_source_id"),
            "pet_text_expected_path": str(pet_text_path),
            "pet_text_sha256": actual_sha256,
            "raw_pet_text_copied": False,
        },
        "scope": {
            "axis_contract_count": len(contracts),
            "body_axis_contract_count": 2,
            "transmission_axis_contract_count": 2,
            "complete_vehicle_configuration_count": 0,
            "promoted_vehicle_bom_candidate_count": 0,
        },
        "transmission_summary_evidence": summary_transmission_evidence(text),
        "axis_contracts": contracts,
        "combination_policy": {
            "cartesian_product_allowed": False,
            "reason": (
                "Une annotation de carrosserie ou de boite ne prouve pas son intersection avec une "
                "variante, un moteur, un marche, un millesime ou une option."
            ),
            "required_join_dimensions": [
                "model_variant",
                "body_style",
                "model_year",
                "market",
                "engine_code",
                "transmission_code",
                "option_codes",
            ],
        },
        "prohibited_claims": [
            "axis_candidate_is_complete_vehicle_bom",
            "body_token_proves_model_variant",
            "transmission_token_proves_vehicle_fitment",
            "candidate_quantity_authorizes_manufacturing",
            "virtual_configuration_proves_roadworthy_vehicle",
        ],
    }


def validate_contract(contract: dict[str, Any]) -> None:
    scope = contract.get("scope", {})
    contracts = contract.get("axis_contracts")
    if not isinstance(contracts, list) or len(contracts) != 4:
        raise ContractError("axis_contract_count")
    if scope.get("axis_contract_count") != len(contracts):
        raise ContractError("axis_scope_count")
    if scope.get("complete_vehicle_configuration_count") != 0:
        raise ContractError("complete_vehicle_configuration_overclaim")
    if scope.get("promoted_vehicle_bom_candidate_count") != 0:
        raise ContractError("promoted_vehicle_bom_overclaim")
    if contract.get("combination_policy", {}).get("cartesian_product_allowed") is not False:
        raise ContractError("cartesian_product_must_be_blocked")
    ids: set[str] = set()
    expected_values = {
        "Cabriolet",
        "Targa",
        "manual_6_speed_candidate",
        "tiptronic_4_speed_candidate",
    }
    for axis_contract in contracts:
        contract_id = axis_contract.get("contract_id")
        if not isinstance(contract_id, str) or contract_id in ids:
            raise ContractError(f"axis_contract_id:{contract_id}")
        ids.add(contract_id)
        if axis_contract.get("status") != "provisional_axis_contract_not_a_vehicle_configuration":
            raise ContractError(f"axis_status:{contract_id}")
        if axis_contract.get("complete_vehicle_bom") is not False:
            raise ContractError(f"axis_complete_bom:{contract_id}")
        if axis_contract.get("combined_with_model_variant") is not False:
            raise ContractError(f"axis_combination_overclaim:{contract_id}")
        candidates = axis_contract.get("candidate_occurrences")
        if not isinstance(candidates, list) or len(candidates) != axis_contract.get(
            "candidate_occurrence_count"
        ):
            raise ContractError(f"axis_candidate_count:{contract_id}")
        for candidate in candidates:
            if candidate.get("promoted_to_vehicle_bom") is not False:
                raise ContractError(f"axis_candidate_promotion:{contract_id}")
            for field in (
                "geometry_revision",
                "mounted_transform",
                "selected_material",
                "manufacturing_route",
            ):
                if candidate.get(field) is not None:
                    raise ContractError(f"axis_candidate_overclaim:{contract_id}:{field}")
    if {item.get("value") for item in contracts} != expected_values:
        raise ContractError("axis_values")
    transmission = contract.get("transmission_summary_evidence", {})
    if not transmission.get("tiptronic_4_speed_code_examples"):
        raise ContractError("tiptronic_summary_evidence")
    if not transmission.get("manual_6_speed_code_examples"):
        raise ContractError("manual_summary_evidence")
    for value in transmission.get("claims", {}).values():
        if value is not False:
            raise ContractError("transmission_summary_overclaim")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--check-index", action="store_true")
    parser.add_argument("--pet-text", type=Path, default=DEFAULT_PET_TEXT)
    args = parser.parse_args(argv)
    try:
        if args.check_index:
            validate_contract(load_json(OUTPUT))
            print(f"valid {relative(OUTPUT)}")
            return 0
        contract = build(args.pet_text)
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
        print(f"993 configuration-axis contract error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
