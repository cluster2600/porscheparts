#!/usr/bin/env python3
"""Build a deterministic 1998 RoW Turbo integration seed without calling it a BOM."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ROSTER = ROOT / "twins" / "vehicle-993" / "configuration-roster-f0.json"
PART_LINKS = ROOT / "twins" / "vehicle-993" / "configuration-part-links-f0.json"
VARIANTS = ROOT / "twins" / "vehicle-993" / "variant-configurations-f0.json"
PET_INDEX = ROOT / "twins" / "pet-993" / "index-f0.json"
ENGINEERING_EVIDENCE = ROOT / "twins" / "pet-993" / "engineering-evidence-links-f0.json"
OUTPUT = ROOT / "twins" / "vehicle-993" / "turbo-integration-seed-f0.json"

TARGET_CONFIGURATION_CANDIDATE_ID = "CONFIG-CANDIDATE-993-32037F10BE2E4BFAEC9A"
TARGET_VARIANT_CONFIGURATION_ID = "CONFIG-993-TURBO"


class ContractError(ValueError):
    """Raised when the seed no longer closes or starts claiming a BOM."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot_load:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"expected_object:{path}")
    return value


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def load_part_masters(index: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    shards = index.get("output", {}).get("part_master_shards")
    if not isinstance(shards, list):
        raise ContractError("part_master_shards")
    for shard in shards:
        if not isinstance(shard, dict) or not isinstance(shard.get("path"), str):
            raise ContractError("part_master_shard")
        path = ROOT / shard["path"]
        if shard.get("sha256") != sha256_file(path):
            raise ContractError(f"part_master_shard_digest:{shard.get('path')}")
        with path.open(encoding="utf-8") as handle:
            records = [json.loads(line) for line in handle if line.strip()]
        if len(records) != shard.get("record_count"):
            raise ContractError(f"part_master_shard_count:{shard.get('path')}")
        for record in records:
            result[record["twin_id"]] = record
    return result


def entry_from_constraint(
    link: dict[str, Any], master: dict[str, Any], direct_variant_ids: set[str]
) -> dict[str, Any]:
    occurrence_id = str(link["occurrence_twin_id"])
    return {
        "occurrence_twin_id": occurrence_id,
        "part_master_twin_id": link["part_master_twin_id"],
        "oem_reference": link["oem_reference"],
        "descriptions": master.get("subject", {}).get("descriptions", []),
        "pet_illustration": link["pet_illustration"],
        "pet_page": link.get("pet_page"),
        "system_ids": master.get("documentary_graph", {}).get("system_ids", []),
        "candidate_quantity_per_car": link["candidate_quantity_per_car"],
        "integration_evidence_tier": "single_dimension_constraint_candidate",
        "constraint_kind": link["constraint_kind"],
        "constraint_values": link["constraint_values"],
        "also_direct_turbo_model_annotation": occurrence_id in direct_variant_ids,
        "human_reviewed": False,
        "promoted_to_vehicle_bom": False,
        "mounted_transform": None,
        "geometry_revision": None,
        "selected_material": None,
        "manufacturing_route": None,
    }


def entry_from_verified(entry: dict[str, Any], master: dict[str, Any]) -> dict[str, Any]:
    return {
        "occurrence_twin_id": entry["occurrence_twin_id"],
        "part_master_twin_id": entry["part_master_twin_id"],
        "oem_reference": entry["oem_reference"],
        "descriptions": master.get("subject", {}).get("descriptions", []),
        "pet_illustration": entry["pet_illustration"],
        "pet_page": None,
        "system_ids": master.get("documentary_graph", {}).get("system_ids", []),
        "candidate_quantity_per_car": entry["quantity_per_car"],
        "integration_evidence_tier": "human_read_variant_context",
        "constraint_kind": "direct_variant_human_read",
        "constraint_values": ["TURBO"],
        "also_direct_turbo_model_annotation": False,
        "human_reviewed": True,
        "promoted_to_vehicle_bom": False,
        "mounted_transform": None,
        "geometry_revision": None,
        "selected_material": None,
        "manufacturing_route": None,
    }


def build() -> dict[str, Any]:
    roster = load_json(ROSTER)
    part_links = load_json(PART_LINKS)
    variants = load_json(VARIANTS)
    pet_index = load_json(PET_INDEX)
    engineering_evidence = load_json(ENGINEERING_EVIDENCE)
    masters = load_part_masters(pet_index)

    candidates = roster.get("configuration_candidates", [])
    selected = next(
        (
            item
            for item in candidates
            if item.get("configuration_candidate_id")
            == TARGET_CONFIGURATION_CANDIDATE_ID
        ),
        None,
    )
    if not isinstance(selected, dict):
        raise ContractError("target_configuration_candidate")
    turbo_candidates = [
        item for item in candidates if item.get("model_family") == "turbo"
    ]
    variant = next(
        (
            item
            for item in variants.get("configurations", [])
            if item.get("configuration_id") == TARGET_VARIANT_CONFIGURATION_ID
        ),
        None,
    )
    if not isinstance(variant, dict):
        raise ContractError("target_variant_configuration")
    direct_variant_entries = variant.get("machine_resolved_bom_candidates", [])
    verified_entries = variant.get("verified_bom_entries", [])
    direct_occurrence_ids = {
        str(item["occurrence_twin_id"])
        for item in direct_variant_entries
        if isinstance(item, dict) and isinstance(item.get("occurrence_twin_id"), str)
    }
    constraint_links = [
        item
        for item in part_links.get("resolved_constraint_links", [])
        if isinstance(item, dict)
        and TARGET_CONFIGURATION_CANDIDATE_ID
        in item.get("compatible_configuration_candidate_ids", [])
    ]

    entries_by_occurrence: dict[str, dict[str, Any]] = {}
    for link in constraint_links:
        master_id = link.get("part_master_twin_id")
        if master_id not in masters:
            raise ContractError(f"unknown_constraint_master:{master_id}")
        entry = entry_from_constraint(link, masters[master_id], direct_occurrence_ids)
        entries_by_occurrence[entry["occurrence_twin_id"]] = entry
    for source_entry in verified_entries:
        if not isinstance(source_entry, dict):
            raise ContractError("verified_variant_entry")
        master_id = source_entry.get("part_master_twin_id")
        if master_id not in masters:
            raise ContractError(f"unknown_verified_master:{master_id}")
        entry = entry_from_verified(source_entry, masters[master_id])
        if entry["occurrence_twin_id"] in entries_by_occurrence:
            raise ContractError(f"verified_constraint_overlap:{entry['occurrence_twin_id']}")
        entries_by_occurrence[entry["occurrence_twin_id"]] = entry
    entries = sorted(entries_by_occurrence.values(), key=lambda item: item["occurrence_twin_id"])

    master_ids = {str(item["part_master_twin_id"]) for item in entries}
    illustration_ids = {str(item["pet_illustration"]) for item in entries}
    system_occurrences = Counter(
        system_id for item in entries for system_id in item["system_ids"]
    )
    system_masters: dict[str, set[str]] = {}
    for item in entries:
        for system_id in item["system_ids"]:
            system_masters.setdefault(system_id, set()).add(item["part_master_twin_id"])
    evidence_master_ids = {
        str(master_id)
        for link in engineering_evidence.get("links", [])
        if isinstance(link, dict)
        for master_id in link.get("pet_part_master_twin_ids", [])
        if isinstance(master_id, str)
    }
    covered_engineering_masters = sorted(master_ids.intersection(evidence_master_ids))
    missing_engineering_masters = sorted(evidence_master_ids - master_ids)
    total_occurrences = int(pet_index["scope"]["total_documentary_twins"])
    total_masters = int(pet_index["scope"]["part_master_twins"])
    total_illustrations = int(pet_index["scope"]["illustration_count"])

    return {
        "$comment": (
            "Graine d'integration virtuelle pour une Turbo 1998 RoW. "
            "Elle combine preuves de variante relues et contraintes PET mono-dimensionnelles, "
            "sans constituer une nomenclature complete."
        ),
        "schema_version": "1.0.0",
        "generated_by": relative(Path(__file__).resolve()),
        "source_boundary": {
            "configuration_roster": relative(ROSTER),
            "configuration_roster_sha256": sha256_file(ROSTER),
            "configuration_part_links": relative(PART_LINKS),
            "configuration_part_links_sha256": sha256_file(PART_LINKS),
            "variant_configurations": relative(VARIANTS),
            "variant_configurations_sha256": sha256_file(VARIANTS),
            "pet_twin_index": relative(PET_INDEX),
            "pet_twin_index_sha256": sha256_file(PET_INDEX),
            "engineering_evidence_links": relative(ENGINEERING_EVIDENCE),
            "engineering_evidence_links_sha256": sha256_file(ENGINEERING_EVIDENCE),
        },
        "integration_target": {
            "selection_status": "program_hypothesis_not_vehicle_proof",
            "configuration_candidate": selected,
            "variant_configuration_id": TARGET_VARIANT_CONFIGURATION_ID,
            "alternative_turbo_configuration_candidate_count": len(turbo_candidates) - 1,
            "rationale": [
                "first_program_integration_family_is_993_turbo",
                "latest_catalogue_model_year_1998",
                "rest_of_world_unmarked_market_hypothesis",
                "M64.60_engine_and_G64.51_manual_transmission",
                "selected_candidate_has_no_recorded_source_anomaly",
            ],
            "selection_reversible": True,
            "promoted_to_configured_vehicle": False,
        },
        "scope": {
            "candidate_occurrences": len(entries),
            "candidate_part_masters": len(master_ids),
            "candidate_instance_quantity_sum": sum(
                int(item["candidate_quantity_per_car"]) for item in entries
            ),
            "human_read_variant_occurrences": len(verified_entries),
            "single_dimension_constraint_occurrences": len(constraint_links),
            "direct_turbo_annotation_occurrences_within_constraints": sum(
                item["also_direct_turbo_model_annotation"] for item in entries
            ),
            "catalogue_illustrations_touched": len(illustration_ids),
            "detailed_engineering_masters_in_seed": len(covered_engineering_masters),
            "detailed_engineering_masters_outside_seed": len(missing_engineering_masters),
            "catalogue_occurrences_outside_seed": total_occurrences - len(entries),
            "part_masters_outside_seed": total_masters - len(master_ids),
            "catalogue_illustrations_outside_seed": total_illustrations
            - len(illustration_ids),
            "configured_vehicle_bom_entries": 0,
            "mounted_transforms": 0,
            "selected_materials": 0,
            "reference_solver_results": 0,
            "physicsnemo_results": 0,
            "simready_assets": 0,
            "functioning_vehicle_claim": False,
        },
        "coverage": {
            "candidate_occurrences_by_system": dict(sorted(system_occurrences.items())),
            "candidate_part_masters_by_system": {
                key: len(value) for key, value in sorted(system_masters.items())
            },
            "candidate_occurrences_by_evidence_tier": dict(
                sorted(Counter(item["integration_evidence_tier"] for item in entries).items())
            ),
            "candidate_occurrences_by_constraint_kind": dict(
                sorted(Counter(item["constraint_kind"] for item in entries).items())
            ),
            "detailed_engineering_master_ids_in_seed": covered_engineering_masters,
            "detailed_engineering_master_ids_outside_seed": missing_engineering_masters,
        },
        "candidate_entries": entries,
        "assembly_gates": {
            "configuration_selection": "hypothesis_selected_for_virtual_work",
            "complete_bom": "blocked_unresolved_generic_option_year_market_and_supersession_applicability",
            "editable_geometry": "blocked_for_all_candidate_entries",
            "mounted_transforms": "blocked_no_vehicle_coordinate_interfaces",
            "materials_and_processes": "blocked_no_qualified_selection",
            "reference_simulation": "blocked_no_analysis_ready_assembly",
            "physicsnemo": "blocked_no_validated_reference_dataset",
            "omniverse_simready": "blocked_no_validated_assets_or_transforms",
            "physical_correlation": "unavailable_by_program_constraint",
            "functional_vehicle": False,
        },
        "prohibited_claims": [
            "integration_seed_is_complete_vehicle_bom",
            "single_dimension_constraint_proves_mounted_part",
            "candidate_quantity_sum_is_vehicle_part_count",
            "human_read_variant_context_proves_geometry_fit",
            "configuration_hypothesis_is_vehicle_identity",
            "seed_authorizes_simulation_manufacturing_installation_or_road_use",
        ],
    }


def validate(contract: dict[str, Any]) -> None:
    boundary = contract.get("source_boundary", {})
    for name, path in (
        ("configuration_roster", ROSTER),
        ("configuration_part_links", PART_LINKS),
        ("variant_configurations", VARIANTS),
        ("pet_twin_index", PET_INDEX),
        ("engineering_evidence_links", ENGINEERING_EVIDENCE),
    ):
        if boundary.get(f"{name}_sha256") != sha256_file(path):
            raise ContractError(f"source_digest:{name}")
    target = contract.get("integration_target", {})
    candidate = target.get("configuration_candidate", {})
    if candidate.get("configuration_candidate_id") != TARGET_CONFIGURATION_CANDIDATE_ID:
        raise ContractError("selected_candidate")
    expected_target = {
        "model_family": "turbo",
        "body_style": "Coupé",
        "model_year": 1998,
        "market_group": "rest_of_world_unmarked",
        "engine_code": "M64.60",
        "transmission_code": "G64.51",
    }
    for field, value in expected_target.items():
        if candidate.get(field) != value:
            raise ContractError(f"target_field:{field}")
    if candidate.get("source_anomalies") != []:
        raise ContractError("target_source_anomaly")
    if target.get("promoted_to_configured_vehicle") is not False:
        raise ContractError("target_promotion")
    scope = contract.get("scope", {})
    expected_counts = {
        "candidate_occurrences": 325,
        "candidate_part_masters": 316,
        "candidate_instance_quantity_sum": 580,
        "human_read_variant_occurrences": 10,
        "single_dimension_constraint_occurrences": 315,
        "direct_turbo_annotation_occurrences_within_constraints": 108,
        "catalogue_illustrations_touched": 74,
        "detailed_engineering_masters_in_seed": 2,
        "detailed_engineering_masters_outside_seed": 6,
        "catalogue_occurrences_outside_seed": 12554,
        "part_masters_outside_seed": 5697,
        "catalogue_illustrations_outside_seed": 165,
    }
    for field, value in expected_counts.items():
        if scope.get(field) != value:
            raise ContractError(f"scope:{field}:{scope.get(field)}:{value}")
    for field in (
        "configured_vehicle_bom_entries",
        "mounted_transforms",
        "selected_materials",
        "reference_solver_results",
        "physicsnemo_results",
        "simready_assets",
    ):
        if scope.get(field) != 0:
            raise ContractError(f"overclaim:{field}")
    if scope.get("functioning_vehicle_claim") is not False:
        raise ContractError("functioning_vehicle_claim")
    entries = contract.get("candidate_entries")
    if not isinstance(entries, list) or len(entries) != scope["candidate_occurrences"]:
        raise ContractError("candidate_entries")
    if len({item.get("occurrence_twin_id") for item in entries}) != len(entries):
        raise ContractError("duplicate_occurrence")
    for item in entries:
        if item.get("promoted_to_vehicle_bom") is not False:
            raise ContractError(f"entry_promotion:{item.get('occurrence_twin_id')}")
        if any(
            item.get(field) is not None
            for field in (
                "mounted_transform",
                "geometry_revision",
                "selected_material",
                "manufacturing_route",
            )
        ):
            raise ContractError(f"entry_engineering_overclaim:{item.get('occurrence_twin_id')}")
    if contract.get("assembly_gates", {}).get("functional_vehicle") is not False:
        raise ContractError("functional_vehicle_gate")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--check-index", action="store_true")
    args = parser.parse_args(argv)
    try:
        contract = build()
        validate(contract)
        expected = render(contract)
        if args.write:
            OUTPUT.write_text(expected, encoding="utf-8")
            print(f"wrote {relative(OUTPUT)}")
            return 0
        if not OUTPUT.exists():
            print(f"missing:{OUTPUT}")
            return 1
        if args.check and OUTPUT.read_text(encoding="utf-8") != expected:
            print(f"stale:{OUTPUT}")
            return 1
        validate(load_json(OUTPUT))
        print(f"valid {relative(OUTPUT)}")
        return 0
    except ContractError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
