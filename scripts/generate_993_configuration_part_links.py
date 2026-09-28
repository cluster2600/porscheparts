#!/usr/bin/env python3
"""Link PET part constraints to candidate 993 configurations without creating BOMs."""

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
APPLICABILITY_EVIDENCE = ROOT / "twins" / "pet-993" / "applicability-evidence-f0.json"
CONFIGURATION_ROSTER = ROOT / "twins" / "vehicle-993" / "configuration-roster-f0.json"
OUTPUT = ROOT / "twins" / "vehicle-993" / "configuration-part-links-f0.json"
ELIGIBLE_KINDS = {"direct_variant", "body_style", "engine_code", "transmission_code"}
FAMILY_DIRECT_VEHICLE_IDS = {
    "carrera_family": {"993-carrera"},
    "carrera_4_family": {"993-carrera-4"},
    "carrera_rs": {"993-rs"},
    "turbo": {"993-turbo"},
}
BODY_TOKEN_BY_STYLE = {"Coupé": "COUPE", "Cabriolet": "CABRIO", "Targa": "TARGA"}


class ContractError(ValueError):
    """Raised when configuration-to-part links violate the F0 contract."""


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


def expand_prefixed_token(token: str) -> set[str]:
    if re.match(r"^(?:M64|G50|G64|A50|Z64)\.\d{2}(?:/\d{2})*$", token):
        head, *suffixes = token.split("/")
        prefix = head.rsplit(".", 1)[0]
        return {head, *(f"{prefix}.{suffix}" for suffix in suffixes)}
    return {value for value in re.split(r"[/,]", token) if value}


def constraint_values(record: dict[str, Any], kind: str) -> list[str]:
    values: set[str] = set()
    for annotation in record.get("annotations", []):
        if not isinstance(annotation, dict) or annotation.get("kind") != kind:
            continue
        if kind == "direct_variant":
            values.update(
                value
                for value in annotation.get("resolved_vehicle_ids", [])
                if isinstance(value, str)
            )
        else:
            token = annotation.get("token")
            if isinstance(token, str):
                values.update(expand_prefixed_token(token))
    return sorted(values)


def candidate_matches(kind: str, values: set[str], candidate: dict[str, Any]) -> bool:
    if kind == "direct_variant":
        family_values = FAMILY_DIRECT_VEHICLE_IDS.get(str(candidate.get("model_family")), set())
        return bool(family_values.intersection(values))
    if kind == "body_style":
        return BODY_TOKEN_BY_STYLE.get(candidate.get("body_style")) in values
    if kind == "engine_code":
        return candidate.get("engine_code") in values
    if kind == "transmission_code":
        return candidate.get("transmission_code") in values
    return False


def build() -> dict[str, Any]:
    applicability = load_json(APPLICABILITY_EVIDENCE)
    roster = load_json(CONFIGURATION_ROSTER)
    if applicability.get("scope", {}).get("complete_variant_boms") != 0:
        raise ContractError("applicability_must_fail_closed")
    if roster.get("scope", {}).get("promoted_vehicle_configurations") != 0:
        raise ContractError("configuration_roster_must_fail_closed")
    records = applicability.get("records")
    candidates = roster.get("configuration_candidates")
    if not isinstance(records, list) or not isinstance(candidates, list):
        raise ContractError("source_records")
    typed_candidates = [item for item in candidates if isinstance(item, dict)]
    candidate_ids = {
        str(item["configuration_candidate_id"]) for item in typed_candidates
    }

    links: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    eligible_by_kind: Counter[str] = Counter()
    resolved_by_kind: Counter[str] = Counter()
    link_count_by_kind: Counter[str] = Counter()
    configuration_link_counts: Counter[str] = Counter()
    for record in records:
        if not isinstance(record, dict):
            continue
        kinds = {
            annotation.get("kind")
            for annotation in record.get("annotations", [])
            if isinstance(annotation, dict) and isinstance(annotation.get("kind"), str)
        }
        quantities = record.get("observed_quantities_per_car")
        if (
            len(kinds) != 1
            or next(iter(kinds)) not in ELIGIBLE_KINDS
            or not isinstance(quantities, list)
            or len(quantities) != 1
            or not isinstance(quantities[0], int)
            or quantities[0] <= 0
        ):
            continue
        kind = next(iter(kinds))
        eligible_by_kind[kind] += 1
        values_list = constraint_values(record, kind)
        values = set(values_list)
        compatible_ids = sorted(
            str(candidate["configuration_candidate_id"])
            for candidate in typed_candidates
            if candidate_matches(kind, values, candidate)
        )
        base = {
            "constraint_link_id": (
                f"CONFIG-PART-LINK-993-"
                f"{sha256_text(str(record.get('occurrence_twin_id')) + '::' + kind)[:20].upper()}"
            ),
            "occurrence_twin_id": record.get("occurrence_twin_id"),
            "part_master_twin_id": record.get("part_master_twin_id"),
            "oem_reference": record.get("oem_reference"),
            "pet_illustration": record.get("pet_illustration"),
            "pet_page": record.get("pet_page"),
            "constraint_kind": kind,
            "constraint_values": values_list,
            "candidate_quantity_per_car": quantities[0],
            "evidence_status": "single_dimension_pet_constraint_not_human_reviewed",
            "promoted_to_vehicle_bom": False,
            "geometry_fit": False,
            "manufacturing_release": False,
        }
        if compatible_ids:
            resolved_by_kind[kind] += 1
            link_count_by_kind[kind] += len(compatible_ids)
            configuration_link_counts.update(compatible_ids)
            links.append(
                {
                    **base,
                    "compatible_configuration_candidate_count": len(compatible_ids),
                    "compatible_configuration_candidate_ids": compatible_ids,
                }
            )
        else:
            unresolved.append(
                {
                    **base,
                    "unresolved_reason": "no_exact_pet_summary_configuration_candidate_for_constraint",
                    "compatible_configuration_candidate_count": 0,
                    "compatible_configuration_candidate_ids": [],
                }
            )
    links.sort(key=lambda item: item["constraint_link_id"])
    unresolved.sort(key=lambda item: item["constraint_link_id"])
    coverage = [
        {
            "configuration_candidate_id": candidate_id,
            "single_dimension_constraint_occurrence_count": configuration_link_counts[candidate_id],
            "complete_vehicle_bom": False,
        }
        for candidate_id in sorted(candidate_ids)
    ]
    linked_configuration_count = sum(
        item["single_dimension_constraint_occurrence_count"] > 0 for item in coverage
    )
    return {
        "$comment": (
            "Liens F0 entre contraintes PET de piece et configurations candidates. Un lien filtre une "
            "seule dimension et ne constitue jamais une entree de BOM ou une preuve de montage."
        ),
        "schema_version": "1.0.0",
        "generated_by": relative(Path(__file__).resolve()),
        "source_boundary": {
            "applicability_evidence": relative(APPLICABILITY_EVIDENCE),
            "applicability_evidence_sha256": sha256_file(APPLICABILITY_EVIDENCE),
            "configuration_roster": relative(CONFIGURATION_ROSTER),
            "configuration_roster_sha256": sha256_file(CONFIGURATION_ROSTER),
        },
        "scope": {
            "eligible_single_dimension_constraint_occurrences": sum(eligible_by_kind.values()),
            "resolved_constraint_occurrences": len(links),
            "unresolved_constraint_occurrences": len(unresolved),
            "configuration_candidate_links": sum(link_count_by_kind.values()),
            "linked_configuration_candidates": linked_configuration_count,
            "unlinked_configuration_candidates": len(candidate_ids) - linked_configuration_count,
            "human_reviewed_constraint_occurrences": 0,
            "promoted_vehicle_bom_entries": 0,
            "complete_configuration_boms": 0,
        },
        "coverage": {
            "eligible_occurrences_by_constraint_kind": dict(sorted(eligible_by_kind.items())),
            "resolved_occurrences_by_constraint_kind": dict(sorted(resolved_by_kind.items())),
            "configuration_links_by_constraint_kind": dict(sorted(link_count_by_kind.items())),
            "per_configuration_candidate": coverage,
        },
        "resolved_constraint_links": links,
        "unresolved_constraint_links": unresolved,
        "join_policy": {
            "eligible_annotation_kind_count": 1,
            "unique_positive_quantity_required": True,
            "same_kind_tokens_use_union": True,
            "different_annotation_kinds_are_not_automatically_intersected": True,
            "option_codes_deferred_until_configuration_option_roster_exists": True,
            "automatic_bom_promotion_allowed": False,
        },
        "prohibited_claims": [
            "single_dimension_constraint_is_complete_fitment",
            "compatible_configuration_candidate_is_mounted_part_instance",
            "candidate_quantity_is_reviewed_bom_quantity",
            "configuration_link_proves_geometry_material_or_function",
            "unresolved_constraint_means_part_is_excluded",
        ],
    }


def validate_contract(contract: dict[str, Any]) -> None:
    scope = contract.get("scope", {})
    resolved = contract.get("resolved_constraint_links")
    unresolved = contract.get("unresolved_constraint_links")
    coverage = contract.get("coverage", {}).get("per_configuration_candidate")
    if not isinstance(resolved, list) or len(resolved) != scope.get(
        "resolved_constraint_occurrences"
    ):
        raise ContractError("resolved_constraint_count")
    if not isinstance(unresolved, list) or len(unresolved) != scope.get(
        "unresolved_constraint_occurrences"
    ):
        raise ContractError("unresolved_constraint_count")
    if scope.get("eligible_single_dimension_constraint_occurrences") != len(resolved) + len(
        unresolved
    ):
        raise ContractError("eligible_constraint_count")
    if not isinstance(coverage, list):
        raise ContractError("configuration_coverage")
    if scope.get("linked_configuration_candidates") + scope.get(
        "unlinked_configuration_candidates"
    ) != len(coverage):
        raise ContractError("configuration_coverage_count")
    for field in (
        "human_reviewed_constraint_occurrences",
        "promoted_vehicle_bom_entries",
        "complete_configuration_boms",
    ):
        if scope.get(field) != 0:
            raise ContractError(f"scope_overclaim:{field}")
    if contract.get("join_policy", {}).get("automatic_bom_promotion_allowed") is not False:
        raise ContractError("automatic_bom_promotion_must_be_blocked")
    link_ids: set[str] = set()
    calculated_links = 0
    for link in [*resolved, *unresolved]:
        link_id = link.get("constraint_link_id")
        if not isinstance(link_id, str) or link_id in link_ids:
            raise ContractError(f"constraint_link_id:{link_id}")
        link_ids.add(link_id)
        if link.get("constraint_kind") not in ELIGIBLE_KINDS:
            raise ContractError(f"constraint_kind:{link_id}")
        if link.get("evidence_status") != "single_dimension_pet_constraint_not_human_reviewed":
            raise ContractError(f"constraint_status:{link_id}")
        if link.get("promoted_to_vehicle_bom") is not False:
            raise ContractError(f"constraint_promotion:{link_id}")
        if link.get("geometry_fit") is not False or link.get("manufacturing_release") is not False:
            raise ContractError(f"constraint_engineering_overclaim:{link_id}")
        ids = link.get("compatible_configuration_candidate_ids")
        if not isinstance(ids, list) or len(ids) != link.get(
            "compatible_configuration_candidate_count"
        ):
            raise ContractError(f"compatible_configuration_count:{link_id}")
        calculated_links += len(ids)
    if calculated_links != scope.get("configuration_candidate_links"):
        raise ContractError("configuration_candidate_link_count")
    if any(item.get("complete_vehicle_bom") is not False for item in coverage):
        raise ContractError("configuration_coverage_bom_overclaim")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--check-index", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.check_index:
            validate_contract(load_json(OUTPUT))
            print(f"valid {relative(OUTPUT)}")
            return 0
        contract = build()
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
        print(f"993 configuration part-link error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
