#!/usr/bin/env python3
"""Generate fail-closed Porsche 993 variant configuration contracts from PET evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_ROOT = ROOT.parent / "porschefanatics.com"
PET_INDEX = ROOT / "twins" / "pet-993" / "index-f0.json"
APPLICABILITY_EVIDENCE = ROOT / "twins" / "pet-993" / "applicability-evidence-f0.json"
CONFIGURATION_AXES = ROOT / "twins" / "vehicle-993" / "configuration-axes-f0.json"
CONFIGURATION_ROSTER = ROOT / "twins" / "vehicle-993" / "configuration-roster-f0.json"
CONFIGURATION_PART_LINKS = ROOT / "twins" / "vehicle-993" / "configuration-part-links-f0.json"
CONFIGURATION_EXCEPTIONS = ROOT / "twins" / "vehicle-993" / "configuration-exceptions-f0.json"
OUTPUT = ROOT / "twins" / "vehicle-993" / "variant-configurations-f0.json"
GENERATION = "993"


class ContractError(ValueError):
    """Raised when variant evidence violates the F0 contract."""


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


def normalize_oem_reference(value: str) -> str:
    return "".join(character for character in value.upper() if character.isalnum())


def source_key(row: dict[str, Any]) -> str:
    values = (row.get("petSourceId"), row.get("petIllustration"), row.get("oemReference"))
    if not all(isinstance(value, str) and value.strip() for value in values):
        raise ContractError(f"incomplete_source_key:{values}")
    return "::".join(value.strip() for value in values)


def occurrence_twin_id(row: dict[str, Any]) -> str:
    return f"TWIN-PET-993-{sha256_text(source_key(row))[:20].upper()}"


def part_master_twin_id(reference: str) -> str:
    normalized = normalize_oem_reference(reference)
    return f"TWIN-PET-993-PART-{sha256_text(normalized)[:20].upper()}"


def build(source_root: Path) -> dict[str, Any]:
    vehicles_path = source_root / "data" / "vehicles.json"
    parts_path = source_root / "data" / "oem-parts.json"
    vehicles_payload = load_json(vehicles_path)
    parts_payload = load_json(parts_path)
    pet_index = load_json(PET_INDEX)
    applicability = load_json(APPLICABILITY_EVIDENCE)
    configuration_axes = load_json(CONFIGURATION_AXES)
    configuration_roster = load_json(CONFIGURATION_ROSTER)
    configuration_part_links = load_json(CONFIGURATION_PART_LINKS)
    configuration_exceptions = load_json(CONFIGURATION_EXCEPTIONS)
    if applicability.get("scope", {}).get("generation") != GENERATION:
        raise ContractError("applicability_generation")
    if applicability.get("scope", {}).get("complete_variant_boms") != 0:
        raise ContractError("applicability_must_fail_closed")
    if configuration_axes.get("scope", {}).get("complete_vehicle_configuration_count") != 0:
        raise ContractError("configuration_axes_must_fail_closed")
    if configuration_roster.get("scope", {}).get("complete_vehicle_configurations") != 0:
        raise ContractError("configuration_roster_must_fail_closed")
    if configuration_part_links.get("scope", {}).get("promoted_vehicle_bom_entries") != 0:
        raise ContractError("configuration_part_links_must_fail_closed")
    if configuration_exceptions.get("scope", {}).get("promoted_vehicle_configurations") != 0:
        raise ContractError("configuration_exceptions_must_fail_closed")

    vehicles = [
        value
        for value in vehicles_payload.get("vehicles", [])
        if isinstance(value, dict) and value.get("generationId") == GENERATION
    ]
    vehicles.sort(key=lambda item: str(item.get("id")))
    if len(vehicles) != 8:
        raise ContractError(f"expected_eight_993_variants:{len(vehicles)}")
    vehicle_ids = [str(vehicle.get("id")) for vehicle in vehicles]
    if len(vehicle_ids) != len(set(vehicle_ids)) or any(not value for value in vehicle_ids):
        raise ContractError("duplicate_or_missing_vehicle_id")

    mvp_ids = [str(vehicle["id"]) for vehicle in vehicles if vehicle.get("mvp") is True]
    if len(mvp_ids) != 1:
        raise ContractError(f"expected_one_mvp_variant:{mvp_ids}")

    rows = [
        value
        for value in parts_payload.get("oemParts", [])
        if isinstance(value, dict) and value.get("generationId") == GENERATION
    ]
    rows.sort(key=source_key)
    row_keys = [source_key(row) for row in rows]
    if len(row_keys) != len(set(row_keys)):
        raise ContractError("duplicate_read_pet_source_key")

    known_vehicle_ids = set(vehicle_ids)
    for row in rows:
        fits = row.get("fitsVehicles")
        fits = fits if isinstance(fits, list) else []
        unknown = sorted({str(value) for value in fits if value not in known_vehicle_ids})
        if unknown:
            raise ContractError(f"unknown_vehicle_fitment:{row.get('oemReference')}:{unknown}")

    configurations: list[dict[str, Any]] = []
    assignment_links = 0
    machine_candidate_links = 0
    for vehicle in vehicles:
        vehicle_id = str(vehicle["id"])
        entries: list[dict[str, Any]] = []
        for row in rows:
            fits = row.get("fitsVehicles")
            if not isinstance(fits, list) or vehicle_id not in fits:
                continue
            reference = str(row["oemReference"])
            key = f"{vehicle_id}::{source_key(row)}"
            quantity = row.get("quantityPerCar")
            if not isinstance(quantity, int) or quantity <= 0:
                raise ContractError(f"invalid_quantity:{vehicle_id}:{reference}:{quantity}")
            entries.append(
                {
                    "entry_id": f"BOM-993-{sha256_text(key)[:20].upper()}",
                    "oem_reference": reference,
                    "description": row.get("englishName"),
                    "quantity_per_car": quantity,
                    "pet_illustration": row.get("petIllustration"),
                    "pet_position": row.get("petPosition"),
                    "pet_source_id": row.get("petSourceId"),
                    "occurrence_twin_id": occurrence_twin_id(row),
                    "part_master_twin_id": part_master_twin_id(reference),
                    "evidence_depth": "human_read_in_catalogue_context",
                    "mounted_transform": None,
                    "geometry_revision": None,
                    "selected_material": None,
                    "manufacturing_route": None,
                }
            )
        entries.sort(key=lambda item: item["entry_id"])
        assignment_links += len(entries)
        machine_candidates: list[dict[str, Any]] = []
        for record in applicability.get("records", []):
            if not isinstance(record, dict) or record.get("machine_bom_candidate") is not True:
                continue
            if vehicle_id not in record.get("directly_resolved_vehicle_ids", []):
                continue
            reference = record.get("oem_reference")
            quantity = record.get("candidate_quantity_per_car")
            if not isinstance(reference, str) or not isinstance(quantity, int) or quantity <= 0:
                raise ContractError(f"invalid_machine_candidate:{vehicle_id}:{reference}")
            key = f"{vehicle_id}::{record.get('occurrence_twin_id')}"
            machine_candidates.append(
                {
                    "candidate_id": f"BOMC-993-{sha256_text(key)[:20].upper()}",
                    "oem_reference": reference,
                    "quantity_per_car": quantity,
                    "pet_illustration": record.get("pet_illustration"),
                    "pet_page": record.get("pet_page"),
                    "occurrence_twin_id": record.get("occurrence_twin_id"),
                    "part_master_twin_id": record.get("part_master_twin_id"),
                    "direct_model_annotations": [
                        annotation.get("token") for annotation in record.get("annotations", [])
                    ],
                    "evidence_status": "machine_extracted_direct_model_column_not_human_reviewed",
                    "evidence_contract": relative(APPLICABILITY_EVIDENCE),
                    "mounted_transform": None,
                    "geometry_revision": None,
                    "selected_material": None,
                    "manufacturing_route": None,
                    "promoted_to_verified_bom": False,
                }
            )
        machine_candidates.sort(key=lambda item: item["candidate_id"])
        machine_candidate_links += len(machine_candidates)
        configurations.append(
            {
                "configuration_id": f"CONFIG-{vehicle_id.upper()}",
                "vehicle_id": vehicle_id,
                "documentary_vehicle_fields": {
                    key: vehicle.get(key)
                    for key in (
                        "manufacturer",
                        "model",
                        "variant",
                        "bodyStyle",
                        "yearStart",
                        "yearEnd",
                        "engineCode",
                        "transmissionCodes",
                        "drivetrain",
                        "optionCodes",
                        "notes",
                        "mvp",
                    )
                    if key in vehicle
                },
                "verified_bom_entries": entries,
                "machine_resolved_bom_candidates": machine_candidates,
                "readiness": {
                    "verified_bom_entry_count": len(entries),
                    "verified_instance_quantity": sum(item["quantity_per_car"] for item in entries),
                    "configured_pet_occurrence_count": len(entries),
                    "machine_resolved_bom_candidate_count": len(machine_candidates),
                    "machine_candidate_instance_quantity": sum(
                        item["quantity_per_car"] for item in machine_candidates
                    ),
                    "complete_variant_bom": False,
                    "editable_geometry_entries": 0,
                    "mounted_transform_entries": 0,
                    "selected_material_entries": 0,
                    "reference_solver_results": 0,
                    "physicsnemo_results": 0,
                    "simready_assets": 0,
                    "functional_vehicle_claim": False,
                },
                "missing_gates": [
                    "resolve_applicability_for_all_listed_pet_occurrences",
                    "resolve_option_year_body_transmission_and_supersession_rules",
                    "prove_quantities_and_exclusions",
                    "author_editable_geometry_and_interfaces",
                    "select_materials_from_loads_environment_and_process",
                    "run_and_converge_reference_solvers",
                    "assemble_and_preflight_in_omniverse",
                    "correlate_with_physical_measurement_and_test",
                ],
            }
        )

    parts_with_variants = [row for row in rows if isinstance(row.get("fitsVehicles"), list) and row["fitsVehicles"]]
    unassigned_rows = [row for row in rows if not isinstance(row.get("fitsVehicles"), list) or not row["fitsVehicles"]]
    annotation_counts_by_kind: dict[str, Counter[str]] = defaultdict(Counter)
    for record in applicability.get("records", []):
        if not isinstance(record, dict):
            continue
        for annotation in record.get("annotations", []):
            if not isinstance(annotation, dict):
                continue
            kind = annotation.get("kind")
            token = annotation.get("token")
            if isinstance(kind, str) and isinstance(token, str):
                annotation_counts_by_kind[kind][token] += 1
    observed_body_tokens = annotation_counts_by_kind["body_style"]
    missing_body_contracts = [
        body
        for body in ("CABRIO", "TARGA")
        if any(body in token for token in observed_body_tokens)
        and not any(body.casefold() in str(vehicle.get("bodyStyle", "")).casefold() for vehicle in vehicles)
    ]
    result = {
        "$comment": (
            "Contrats F0 de configuration par variante. Les entrees ne sont incluses que lorsque la "
            "variante et la quantite sont relues dans le contexte PET; aucun BOM n'est complet."
        ),
        "schema_version": "1.0.0",
        "generated_by": relative(Path(__file__).resolve()),
        "source_boundary": {
            "expected_relative_repository": "../porschefanatics.com",
            "vehicles_path": "data/vehicles.json",
            "vehicles_sha256": sha256_file(vehicles_path),
            "oem_parts_path": "data/oem-parts.json",
            "oem_parts_sha256": sha256_file(parts_path),
            "pet_twin_index": relative(PET_INDEX),
            "pet_twin_index_sha256": sha256_file(PET_INDEX),
            "applicability_evidence": relative(APPLICABILITY_EVIDENCE),
            "applicability_evidence_sha256": sha256_file(APPLICABILITY_EVIDENCE),
            "configuration_axes": relative(CONFIGURATION_AXES),
            "configuration_axes_sha256": sha256_file(CONFIGURATION_AXES),
            "configuration_roster": relative(CONFIGURATION_ROSTER),
            "configuration_roster_sha256": sha256_file(CONFIGURATION_ROSTER),
            "configuration_part_links": relative(CONFIGURATION_PART_LINKS),
            "configuration_part_links_sha256": sha256_file(CONFIGURATION_PART_LINKS),
            "configuration_exceptions": relative(CONFIGURATION_EXCEPTIONS),
            "configuration_exceptions_sha256": sha256_file(CONFIGURATION_EXCEPTIONS),
        },
        "strategy": {
            "configuration_model": "one_separate_bom_contract_per_documented_vehicle_variant",
            "first_integration_target": mvp_ids[0],
            "first_integration_target_basis": "source_vehicle_record_mvp_true",
            "universal_993_bom_allowed": False,
        },
        "scope": {
            "variant_configuration_count": len(configurations),
            "complete_variant_bom_count": 0,
            "human_read_pet_part_count": len(rows),
            "human_read_parts_with_variant_proof": len(parts_with_variants),
            "human_read_parts_without_variant_proof": len(unassigned_rows),
            "variant_assignment_links": assignment_links,
            "machine_resolved_bom_candidate_occurrences": int(
                applicability.get("scope", {}).get("machine_bom_candidate_occurrences", 0)
            ),
            "machine_resolved_bom_candidate_links": machine_candidate_links,
            "unresolved_listed_pet_occurrences": int(
                pet_index.get("scope", {}).get("listed_documentary_twins", 0)
            ),
            "listed_occurrences_without_direct_model_candidate": int(
                pet_index.get("scope", {}).get("listed_documentary_twins", 0)
            )
            - int(applicability.get("scope", {}).get("machine_bom_candidate_occurrences", 0)),
            "complete_configuration_universe": False,
            "provisional_configuration_axis_contracts": int(
                configuration_axes.get("scope", {}).get("axis_contract_count", 0)
            ),
            "pet_summary_type_records": int(
                configuration_roster.get("scope", {}).get("type_record_count", 0)
            ),
            "pet_summary_configuration_candidates": int(
                configuration_roster.get("scope", {}).get("configuration_candidate_count", 0)
            ),
            "pet_summary_configuration_gaps": int(
                configuration_roster.get("scope", {}).get("configuration_gap_count", 0)
            ),
            "single_dimension_part_constraint_occurrences": int(
                configuration_part_links.get("scope", {}).get(
                    "eligible_single_dimension_constraint_occurrences", 0
                )
            ),
            "resolved_configuration_part_constraint_occurrences": int(
                configuration_part_links.get("scope", {}).get(
                    "resolved_constraint_occurrences", 0
                )
            ),
            "configuration_part_candidate_links": int(
                configuration_part_links.get("scope", {}).get(
                    "configuration_candidate_links", 0
                )
            ),
            "configuration_exception_contracts": int(
                configuration_exceptions.get("scope", {}).get("exception_contract_count", 0)
            ),
            "mapped_configuration_exception_occurrences": int(
                configuration_exceptions.get("scope", {}).get("mapped_exception_occurrences", 0)
            ),
            "fully_resolved_configuration_exceptions": int(
                configuration_exceptions.get("scope", {}).get(
                    "fully_resolved_configuration_exceptions", 0
                )
            ),
        },
        "catalogue_configuration_universe": {
            "status": "incomplete_source_vehicle_records_do_not_cover_all_pet_dimensions",
            "source_vehicle_record_count": len(vehicles),
            "source_vehicle_body_styles": sorted(
                {str(vehicle.get("bodyStyle")) for vehicle in vehicles if vehicle.get("bodyStyle")}
            ),
            "observed_body_style_tokens": dict(sorted(observed_body_tokens.items())),
            "missing_body_style_contracts": missing_body_contracts,
            "provisional_axis_contracts": [
                {
                    "contract_id": item.get("contract_id"),
                    "axis": item.get("axis"),
                    "value": item.get("value"),
                    "candidate_occurrence_count": item.get("candidate_occurrence_count"),
                    "complete_vehicle_bom": item.get("complete_vehicle_bom"),
                    "combined_with_model_variant": item.get("combined_with_model_variant"),
                }
                for item in configuration_axes.get("axis_contracts", [])
                if isinstance(item, dict)
            ],
            "pet_summary_roster": {
                "status": "candidate_intersections_not_human_reviewed",
                "type_record_count": configuration_roster.get("scope", {}).get(
                    "type_record_count", 0
                ),
                "engine_option_count": configuration_roster.get("scope", {}).get(
                    "engine_option_count", 0
                ),
                "transmission_option_count": configuration_roster.get("scope", {}).get(
                    "transmission_option_count", 0
                ),
                "configuration_candidate_count": configuration_roster.get("scope", {}).get(
                    "configuration_candidate_count", 0
                ),
                "configuration_gap_count": configuration_roster.get("scope", {}).get(
                    "configuration_gap_count", 0
                ),
                "review_queue_entry_count": configuration_roster.get("review_queue", {}).get(
                    "entry_count", 0
                ),
                "promoted_vehicle_configurations": configuration_roster.get("scope", {}).get(
                    "promoted_vehicle_configurations", 0
                ),
            },
            "configuration_part_linkage": {
                "status": "single_dimension_constraints_not_vehicle_bom",
                "eligible_constraint_occurrences": configuration_part_links.get(
                    "scope", {}
                ).get("eligible_single_dimension_constraint_occurrences", 0),
                "resolved_constraint_occurrences": configuration_part_links.get(
                    "scope", {}
                ).get("resolved_constraint_occurrences", 0),
                "unresolved_constraint_occurrences": configuration_part_links.get(
                    "scope", {}
                ).get("unresolved_constraint_occurrences", 0),
                "configuration_candidate_links": configuration_part_links.get(
                    "scope", {}
                ).get("configuration_candidate_links", 0),
                "promoted_vehicle_bom_entries": configuration_part_links.get(
                    "scope", {}
                ).get("promoted_vehicle_bom_entries", 0),
            },
            "configuration_exceptions": {
                "status": "all_unmatched_constraints_tracked_but_not_resolved",
                "exception_contract_count": configuration_exceptions.get("scope", {}).get(
                    "exception_contract_count", 0
                ),
                "mapped_exception_occurrences": configuration_exceptions.get("scope", {}).get(
                    "mapped_exception_occurrences", 0
                ),
                "unmapped_exception_occurrences": configuration_exceptions.get("scope", {}).get(
                    "unmapped_exception_occurrences", 0
                ),
                "fully_resolved_configuration_exceptions": configuration_exceptions.get(
                    "scope", {}
                ).get("fully_resolved_configuration_exceptions", 0),
                "contract_ids": sorted(
                    str(item.get("contract_id"))
                    for item in configuration_exceptions.get("exception_contracts", [])
                    if isinstance(item, dict) and item.get("contract_id")
                ),
            },
            "observed_engine_code_tokens": dict(
                sorted(annotation_counts_by_kind["engine_code"].items())
            ),
            "observed_transmission_code_tokens": dict(
                sorted(annotation_counts_by_kind["transmission_code"].items())
            ),
            "observed_option_code_tokens": dict(
                sorted(annotation_counts_by_kind["option_code"].items())
            ),
            "blockers": [
                "join_provisional_cabriolet_targa_and_transmission_axes_to_model_year_market_rules",
                "map_engine_transmission_option_and_model_year_rules_from_pet_context",
                "review_compound_and_exclusion_annotations",
            ],
        },
        "configurations": configurations,
        "unassigned_human_read_parts": [
            {
                "oem_reference": row.get("oemReference"),
                "description": row.get("englishName"),
                "quantity_per_car": row.get("quantityPerCar"),
                "pet_illustration": row.get("petIllustration"),
                "occurrence_twin_id": occurrence_twin_id(row),
                "part_master_twin_id": part_master_twin_id(str(row.get("oemReference"))),
                "blocker": "variant_not_proven_in_read_context",
            }
            for row in unassigned_rows
        ],
        "prohibited_claims": [
            "configuration_contract_is_complete_vehicle_bom",
            "source_vehicle_metadata_is_independently_verified",
            "missing_variant_assignment_means_part_is_excluded",
            "bom_identity_entry_proves_geometry_or_mounting",
            "virtual_only_program_authorizes_functional_manufacturing_or_road_use",
        ],
    }
    return result


def validate_contract(contract: dict[str, Any]) -> None:
    scope = contract.get("scope", {})
    strategy = contract.get("strategy", {})
    configurations = contract.get("configurations")
    if not isinstance(configurations, list) or len(configurations) != scope.get("variant_configuration_count"):
        raise ContractError("configuration_count")
    if scope.get("variant_configuration_count") != 8:
        raise ContractError("expected_eight_configurations")
    if scope.get("complete_variant_bom_count") != 0:
        raise ContractError("complete_variant_bom_must_be_zero")
    if scope.get("complete_configuration_universe") is not False:
        raise ContractError("configuration_universe_must_be_incomplete")
    if scope.get("provisional_configuration_axis_contracts") != 4:
        raise ContractError("provisional_configuration_axis_contract_count")
    if scope.get("pet_summary_type_records") != 69:
        raise ContractError("pet_summary_type_record_count")
    if scope.get("pet_summary_configuration_candidates") != 149:
        raise ContractError("pet_summary_configuration_candidate_count")
    if scope.get("pet_summary_configuration_gaps") != 2:
        raise ContractError("pet_summary_configuration_gap_count")
    if scope.get("single_dimension_part_constraint_occurrences") != 694:
        raise ContractError("single_dimension_part_constraint_count")
    if scope.get("resolved_configuration_part_constraint_occurrences") != 682:
        raise ContractError("resolved_configuration_part_constraint_count")
    if scope.get("configuration_part_candidate_links") != 24063:
        raise ContractError("configuration_part_candidate_link_count")
    if scope.get("configuration_exception_contracts") != 4:
        raise ContractError("configuration_exception_contract_count")
    if scope.get("mapped_configuration_exception_occurrences") != 12:
        raise ContractError("mapped_configuration_exception_occurrence_count")
    if scope.get("fully_resolved_configuration_exceptions") != 0:
        raise ContractError("configuration_exception_resolution_overclaim")
    if strategy.get("universal_993_bom_allowed") is not False:
        raise ContractError("universal_bom_must_be_blocked")
    universe = contract.get("catalogue_configuration_universe", {})
    if universe.get("status") != "incomplete_source_vehicle_records_do_not_cover_all_pet_dimensions":
        raise ContractError("configuration_universe_status")
    if set(universe.get("missing_body_style_contracts", [])) != {"CABRIO", "TARGA"}:
        raise ContractError("missing_body_style_contracts")
    provisional_axes = universe.get("provisional_axis_contracts")
    if not isinstance(provisional_axes, list) or len(provisional_axes) != 4:
        raise ContractError("provisional_axis_contracts")
    if any(
        item.get("complete_vehicle_bom") is not False
        or item.get("combined_with_model_variant") is not False
        for item in provisional_axes
    ):
        raise ContractError("provisional_axis_overclaim")
    roster = universe.get("pet_summary_roster", {})
    if roster.get("status") != "candidate_intersections_not_human_reviewed":
        raise ContractError("pet_summary_roster_status")
    if roster.get("promoted_vehicle_configurations") != 0:
        raise ContractError("pet_summary_roster_promotion_overclaim")
    linkage = universe.get("configuration_part_linkage", {})
    if linkage.get("status") != "single_dimension_constraints_not_vehicle_bom":
        raise ContractError("configuration_part_linkage_status")
    if linkage.get("promoted_vehicle_bom_entries") != 0:
        raise ContractError("configuration_part_linkage_promotion_overclaim")
    exceptions = universe.get("configuration_exceptions", {})
    if exceptions.get("status") != "all_unmatched_constraints_tracked_but_not_resolved":
        raise ContractError("configuration_exceptions_status")
    if exceptions.get("unmapped_exception_occurrences") != 0:
        raise ContractError("configuration_exceptions_unmapped")
    if exceptions.get("fully_resolved_configuration_exceptions") != 0:
        raise ContractError("configuration_exceptions_resolution_overclaim")
    vehicle_ids = [item.get("vehicle_id") for item in configurations]
    if len(vehicle_ids) != len(set(vehicle_ids)) or strategy.get("first_integration_target") not in vehicle_ids:
        raise ContractError("configuration_vehicle_ids")
    total_links = 0
    entry_ids: set[str] = set()
    candidate_ids: set[str] = set()
    machine_candidate_links = 0
    for configuration in configurations:
        entries = configuration.get("verified_bom_entries")
        candidates = configuration.get("machine_resolved_bom_candidates")
        readiness = configuration.get("readiness", {})
        if not isinstance(entries, list) or not isinstance(candidates, list):
            raise ContractError(f"configuration_entries:{configuration.get('vehicle_id')}")
        if readiness.get("verified_bom_entry_count") != len(entries):
            raise ContractError(f"configuration_entry_count:{configuration.get('vehicle_id')}")
        if readiness.get("complete_variant_bom") is not False:
            raise ContractError(f"configuration_complete_bom:{configuration.get('vehicle_id')}")
        if readiness.get("machine_resolved_bom_candidate_count") != len(candidates):
            raise ContractError(f"configuration_machine_candidate_count:{configuration.get('vehicle_id')}")
        for field in (
            "editable_geometry_entries",
            "mounted_transform_entries",
            "selected_material_entries",
            "reference_solver_results",
            "physicsnemo_results",
            "simready_assets",
        ):
            if readiness.get(field) != 0:
                raise ContractError(f"configuration_overclaim:{configuration.get('vehicle_id')}:{field}")
        if readiness.get("functional_vehicle_claim") is not False:
            raise ContractError(f"configuration_vehicle_claim:{configuration.get('vehicle_id')}")
        total_links += len(entries)
        for entry in entries:
            entry_id = entry.get("entry_id")
            if not isinstance(entry_id, str) or entry_id in entry_ids:
                raise ContractError(f"duplicate_or_missing_entry_id:{entry_id}")
            entry_ids.add(entry_id)
            reference = entry.get("oem_reference")
            if not isinstance(reference, str) or entry.get("part_master_twin_id") != part_master_twin_id(reference):
                raise ContractError(f"entry_master_id:{entry_id}")
            if not isinstance(entry.get("quantity_per_car"), int) or entry["quantity_per_car"] <= 0:
                raise ContractError(f"entry_quantity:{entry_id}")
            for field in ("mounted_transform", "geometry_revision", "selected_material", "manufacturing_route"):
                if entry.get(field) is not None:
                    raise ContractError(f"entry_engineering_overclaim:{entry_id}:{field}")
        machine_candidate_links += len(candidates)
        for candidate in candidates:
            candidate_id = candidate.get("candidate_id")
            if not isinstance(candidate_id, str) or candidate_id in candidate_ids:
                raise ContractError(f"duplicate_or_missing_candidate_id:{candidate_id}")
            candidate_ids.add(candidate_id)
            reference = candidate.get("oem_reference")
            if not isinstance(reference, str) or candidate.get("part_master_twin_id") != part_master_twin_id(
                reference
            ):
                raise ContractError(f"candidate_master_id:{candidate_id}")
            if candidate.get("promoted_to_verified_bom") is not False:
                raise ContractError(f"candidate_promotion_overclaim:{candidate_id}")
            if candidate.get("evidence_status") != "machine_extracted_direct_model_column_not_human_reviewed":
                raise ContractError(f"candidate_evidence_status:{candidate_id}")
            for field in ("mounted_transform", "geometry_revision", "selected_material", "manufacturing_route"):
                if candidate.get(field) is not None:
                    raise ContractError(f"candidate_engineering_overclaim:{candidate_id}:{field}")
    if total_links != scope.get("variant_assignment_links"):
        raise ContractError("variant_assignment_link_count")
    if machine_candidate_links != scope.get("machine_resolved_bom_candidate_links"):
        raise ContractError("machine_candidate_link_count")
    if len(contract.get("unassigned_human_read_parts", [])) != scope.get(
        "human_read_parts_without_variant_proof"
    ):
        raise ContractError("unassigned_part_count")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--check-index", action="store_true")
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    args = parser.parse_args(argv)
    try:
        if args.check_index:
            validate_contract(load_json(OUTPUT))
            print(f"valid {relative(OUTPUT)}")
            return 0
        contract = build(args.source_root)
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
        print(f"993 variant configuration contract error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
