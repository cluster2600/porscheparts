#!/usr/bin/env python3
"""Generate fail-closed Porsche 993 PET occurrence and part-master twins.

The detailed PET transcription stays in the PorscheFanatics repository.  This
script reads it through an explicit source boundary, creates sharded F0
occurrence twins plus one master per normalized OEM reference in ``work/``, and
commits only aggregate indexes with source and output digests.
No PDF, illustration, raw scan, or claim of fit, geometry, material, simulation,
SimReady conformance, or manufacturing release is copied into the catalogue.
"""

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
SKELETON = ROOT / "catalog" / "reference" / "993-assembly-skeleton.json"
VEHICLE_PROGRAM = ROOT / "twins" / "vehicle-993" / "program-f0.json"
DECLARED_PART_DATA = ROOT / "catalog" / "reference" / "993-declared-part-data.json"
TRACKED_INDEX = ROOT / "twins" / "pet-993" / "index-f0.json"
TRACKED_CROSSWALK = ROOT / "twins" / "pet-993" / "catalog-crosswalk-f0.json"
DEFAULT_OUTPUT_ROOT = ROOT / "work" / "pet-993"
GENERATION = "993"
MASTER_SHARD_IDS = tuple("0123456789abcdef")


class ContractError(ValueError):
    """Raised when source or generated records violate the F0 contract."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot_load:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"expected_object:{path}")
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


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


def source_paths(source_root: Path) -> tuple[Path, Path]:
    return source_root / "data" / "oem-listed.json", source_root / "data" / "oem-parts.json"


def skeleton_context() -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, list[str]]]:
    skeleton = load_json(SKELETON)
    program = load_json(VEHICLE_PROGRAM)
    if skeleton.get("generation") != GENERATION:
        raise ContractError("unexpected_skeleton_generation")
    if program.get("vehicle", {}).get("generation") != GENERATION:
        raise ContractError("unexpected_vehicle_program_generation")

    illustrations: dict[str, dict[str, Any]] = {}
    for system in skeleton.get("systems", []):
        system_id = system["system_id"]
        for item in system.get("illustrations", []):
            illustration = item["illustration"]
            if illustration in illustrations:
                raise ContractError(f"duplicate_skeleton_illustration:{illustration}")
            illustrations[illustration] = {
                "system_id": system_id,
                "system_name": system["name"],
                "listed_reference_count": item["reference_count"],
            }

    domains = {
        system["system_id"]: list(system["simulation_domain_ids"])
        for system in program.get("systems", [])
    }
    expected_systems = {system["system_id"] for system in skeleton.get("systems", [])}
    if set(domains) != expected_systems:
        raise ContractError("vehicle_program_system_routes_do_not_match_skeleton")
    return skeleton, illustrations, domains


def rights_summary(oem_payload: dict[str, Any]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for source in oem_payload.get("petSources", []):
        if not isinstance(source, dict) or source.get("generationId") != GENERATION:
            continue
        rights = source.get("rights") if isinstance(source.get("rights"), dict) else {}
        sources.append(
            {
                "pet_source_id": source.get("id"),
                "title": source.get("title"),
                "url": source.get("url"),
                "catalogue_revision": source.get("catalogueRevision"),
                "verified_on": source.get("verifiedOn"),
                "method": source.get("method"),
                "rights": {
                    "illustrations_published": rights.get("illustrationsPublished"),
                    "basis": rights.get("basis"),
                    "documentation_status": rights.get("documentation"),
                },
            }
        )
    return sorted(sources, key=lambda item: str(item["pet_source_id"]))


def listed_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("listings")
    if not isinstance(rows, list):
        raise ContractError("oem_listed.listings_must_be_array")
    return [row for row in rows if isinstance(row, dict) and row.get("generationId") == GENERATION]


def read_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("oemParts")
    if not isinstance(rows, list):
        raise ContractError("oem_parts.oemParts_must_be_array")
    return [row for row in rows if isinstance(row, dict) and row.get("generationId") == GENERATION]


def source_key(row: dict[str, Any]) -> str:
    values = (row.get("petSourceId"), row.get("petIllustration"), row.get("oemReference"))
    if not all(isinstance(value, str) and value.strip() for value in values):
        raise ContractError(f"incomplete_source_key:{values}")
    return "::".join(value.strip() for value in values)


def documentary_twin(
    row: dict[str, Any],
    *,
    depth: str,
    illustration_context: dict[str, Any],
    simulation_domains: list[str],
) -> dict[str, Any]:
    key = source_key(row)
    digest = sha256_text(key)
    is_read = depth == "read"
    variants = row.get("fitsVehicles") if is_read and isinstance(row.get("fitsVehicles"), list) else []
    variants = [value for value in variants if isinstance(value, str) and value.strip()]
    if is_read and variants:
        applicability = "verified_in_context_for_named_variants"
    elif is_read:
        applicability = "read_in_context_but_variant_not_proven"
    else:
        applicability = "unresolved_catalogue_appearance_only"

    description = row.get("englishName") if is_read else row.get("description")
    pet_group = row.get("petGroup")
    position = row.get("petPosition") if is_read else row.get("position")
    pet_page = row.get("petIllustrationPage") if is_read else row.get("petPage")
    revision = row.get("revision") if not is_read else None
    safety_level = row.get("safetyLevel") if is_read else None
    material = row.get("oemMaterial") if is_read else None
    quantity = row.get("quantityPerCar") if is_read else None

    return {
        "schema_version": "1.0.0",
        "twin_id": f"TWIN-PET-993-{digest[:20].upper()}",
        "twin_kind": "documentary_catalogue_occurrence",
        "source_record_key_sha256": digest,
        "source_record_sha256": sha256_text(canonical_json(row)),
        "subject": {
            "oem_reference": row.get("oemReference"),
            "revision": revision,
            "description": description,
        },
        "catalogue_context": {
            "generation": GENERATION,
            "pet_source_id": row.get("petSourceId"),
            "pet_illustration": row.get("petIllustration"),
            "pet_group": pet_group,
            "pet_page": pet_page,
            "position": position,
            "sightings": row.get("sightings", 1),
            "record_depth": depth,
            "linked_work_package": f"WP-993-{row.get('petIllustration')}",
            "system_id": illustration_context["system_id"],
            "system_name": illustration_context["system_name"],
        },
        "vehicle_configuration": {
            "applicability_status": applicability,
            "proven_variants": variants,
            "quantity_per_car": quantity if isinstance(quantity, int) else None,
            "configured_vehicle_instance": False,
        },
        "source_evidence": {
            "pet_verified": row.get("petVerified") is True if is_read else False,
            "pet_evidence": row.get("petEvidence") if is_read else None,
            "depth_semantics": (
                "human_read_in_catalogue_context" if is_read else "machine_transcription_not_read_in_context"
            ),
        },
        "engineering_state": {
            "fidelity": "F0_reference",
            "geometry": "missing",
            "vehicle_transform": "missing",
            "interfaces_and_tolerances": "missing",
            "material_source_value": material,
            "material_decision": None,
            "loads_and_boundary_conditions": "missing",
            "reference_solver": "not_run",
            "physicsnemo": "not_run",
            "omniverse_simready": "not_run",
            "physical_correlation": "unavailable_by_program_constraint",
            "simulation_domain_ids": simulation_domains,
        },
        "safety": {
            "source_safety_level": safety_level if isinstance(safety_level, int) else None,
            "classification_status": "source_classified" if isinstance(safety_level, int) else "unclassified",
            "professional_review_required_for_functional_release": True,
        },
        "manufacturing": {
            "candidate_route": None,
            "functional_release": False,
        },
        "prohibited_claims": [
            "catalogue_appearance_proves_variant_fitment",
            "F0_record_is_geometry",
            "unknown_material_is_selected_material",
            "LLM_output_is_solver_evidence",
            "documentary_twin_is_SimReady",
            "documentary_twin_authorizes_manufacturing_or_road_use",
        ],
    }


def normalize_oem_reference(value: str) -> str:
    return "".join(character for character in value.upper() if character.isalnum())


def part_master_twin_id(normalized_reference: str) -> str:
    return f"TWIN-PET-993-PART-{sha256_text(normalized_reference)[:20].upper()}"


def build_part_master_twins(
    twins: list[dict[str, Any]], declared_entries: list[dict[str, Any]] | None = None
) -> list[dict[str, Any]]:
    by_reference: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for twin in twins:
        reference = twin["subject"].get("oem_reference")
        if not isinstance(reference, str) or not reference.strip():
            raise ContractError(f"part_master_missing_reference:{twin.get('twin_id')}")
        by_reference[normalize_oem_reference(reference)].append(twin)

    declared_by_reference: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in declared_entries or []:
        reference = entry.get("oem_reference")
        if isinstance(reference, str) and reference.strip():
            declared_by_reference[normalize_oem_reference(reference)].append(entry)

    masters: list[dict[str, Any]] = []
    for normalized_reference, occurrences in sorted(by_reference.items()):
        occurrences.sort(key=lambda item: item["twin_id"])
        display_references = sorted({item["subject"]["oem_reference"] for item in occurrences})
        descriptions = sorted(
            {
                item["subject"]["description"]
                for item in occurrences
                if isinstance(item["subject"].get("description"), str)
                and item["subject"]["description"].strip()
            }
        )
        revisions = sorted(
            {
                str(item["subject"]["revision"])
                for item in occurrences
                if item["subject"].get("revision") is not None
            }
        )
        contexts = [
            {
                "occurrence_twin_id": item["twin_id"],
                "pet_source_id": item["catalogue_context"]["pet_source_id"],
                "pet_illustration": item["catalogue_context"]["pet_illustration"],
                "system_id": item["catalogue_context"]["system_id"],
                "position": item["catalogue_context"]["position"],
                "record_depth": item["catalogue_context"]["record_depth"],
            }
            for item in occurrences
        ]
        proven_variant_contexts = [
            {
                "occurrence_twin_id": item["twin_id"],
                "proven_variants": item["vehicle_configuration"]["proven_variants"],
            }
            for item in occurrences
            if item["vehicle_configuration"]["proven_variants"]
        ]
        material_observations = [
            {
                "occurrence_twin_id": item["twin_id"],
                "source_material": item["engineering_state"]["material_source_value"],
            }
            for item in occurrences
            if item["engineering_state"]["material_source_value"] is not None
        ]
        safety_observations = [
            {
                "occurrence_twin_id": item["twin_id"],
                "source_safety_level": item["safety"]["source_safety_level"],
            }
            for item in occurrences
            if item["safety"]["source_safety_level"] is not None
        ]
        declared_observations = [
            {
                "entry_id": entry.get("entry_id"),
                "source_id": entry.get("source_id"),
                "confidence": entry.get("confidence"),
                "bounding_box_mm": entry.get("dimensions_mm"),
                "mass_kg": entry.get("mass_kg"),
                "material": entry.get("material"),
                "observation_status": "declared_not_independently_measured_or_qualified",
            }
            for entry in declared_by_reference.get(normalized_reference, [])
        ]
        masters.append(
            {
                "schema_version": "1.0.0",
                "twin_id": part_master_twin_id(normalized_reference),
                "twin_kind": "documentary_part_identity_master",
                "subject": {
                    "normalized_oem_reference": normalized_reference,
                    "display_references": display_references,
                    "descriptions": descriptions,
                    "revisions": revisions,
                },
                "documentary_graph": {
                    "occurrence_count": len(occurrences),
                    "occurrences": contexts,
                    "system_ids": sorted({item["system_id"] for item in contexts}),
                    "pet_illustrations": sorted({item["pet_illustration"] for item in contexts}),
                    "pet_source_ids": sorted({item["pet_source_id"] for item in contexts}),
                    "proven_variant_contexts": proven_variant_contexts,
                    "source_material_observations": material_observations,
                    "source_safety_observations": safety_observations,
                    "declared_engineering_observations": declared_observations,
                },
                "identity_quality": {
                    "normalization_only": True,
                    "description_variant_count": len(descriptions),
                    "revision_count": len(revisions),
                    "cross_reference_or_supersession_resolved": False,
                    "same_reference_in_multiple_contexts_is_not_a_duplicate": True,
                },
                "engineering_state": {
                    "fidelity": "F0_reference",
                    "editable_geometry": None,
                    "interfaces": [],
                    "selected_material": None,
                    "loads_and_boundary_conditions": [],
                    "reference_solver": "not_run",
                    "physicsnemo": "not_run",
                    "omniverse_simready": "not_run",
                    "physical_correlation": "unavailable_by_program_constraint",
                },
                "manufacturing": {
                    "candidate_route": None,
                    "functional_release": False,
                },
                "prohibited_claims": [
                    "normalized_reference_proves_supersession",
                    "occurrence_context_proves_universal_variant_fitment",
                    "source_material_observation_is_selected_material",
                    "documentary_master_is_geometry_or_simulation",
                    "documentary_master_authorizes_manufacturing_or_road_use",
                ],
            }
        )
    return masters


def build_catalog_crosswalk(twins: list[dict[str, Any]]) -> dict[str, Any]:
    by_reference: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for twin in twins:
        reference = twin["subject"].get("oem_reference")
        if not isinstance(reference, str) or not reference.strip():
            continue
        by_reference[normalize_oem_reference(reference)].append(twin)

    records: list[dict[str, Any]] = []
    total_links = 0
    unmatched_references = 0
    for path in sorted((ROOT / "catalog" / "parts").glob("*.json")):
        part = load_json(path)
        vehicle = part.get("vehicle") if isinstance(part.get("vehicle"), dict) else {}
        references = vehicle.get("porsche_part_numbers")
        references = references if isinstance(references, list) else []
        references = [value for value in references if isinstance(value, str) and value.strip()]
        matches: list[dict[str, Any]] = []
        unmatched: list[str] = []
        for reference in references:
            occurrences = by_reference.get(normalize_oem_reference(reference), [])
            if not occurrences:
                unmatched.append(reference)
                continue
            for occurrence in occurrences:
                matches.append(
                    {
                        "oem_reference": reference,
                        "part_master_twin_id": part_master_twin_id(
                            normalize_oem_reference(occurrence["subject"]["oem_reference"])
                        ),
                        "twin_id": occurrence["twin_id"],
                        "pet_source_id": occurrence["catalogue_context"]["pet_source_id"],
                        "pet_illustration": occurrence["catalogue_context"]["pet_illustration"],
                        "system_id": occurrence["catalogue_context"]["system_id"],
                        "record_depth": occurrence["catalogue_context"]["record_depth"],
                    }
                )
        matches.sort(key=lambda item: (item["oem_reference"], item["twin_id"]))
        total_links += len(matches)
        unmatched_references += len(unmatched)
        if not references:
            status = "blocked_no_oem_reference_in_part_record"
        elif unmatched:
            status = "partial_documentary_identity_match"
        else:
            status = "matched_documentary_identity_only"
        records.append(
            {
                "part_id": part.get("part_id"),
                "part_record": relative(path),
                "porsche_part_numbers": references,
                "status": status,
                "pet_occurrence_matches": matches,
                "unmatched_oem_references": unmatched,
                "claims": {
                    "identity_crosswalk": bool(matches),
                    "variant_fitment": False,
                    "geometry_fit": False,
                    "manufacturing_release": False,
                },
            }
        )

    return {
        "$comment": (
            "Crosswalk des fiches catalog/parts vers les occurrences PET F0. Une correspondance de "
            "reference etablit seulement une identite documentaire; elle ne prouve ni variante, ni montage."
        ),
        "schema_version": "1.0.0",
        "generated_by": relative(Path(__file__).resolve()),
        "source_twin_index": relative(TRACKED_INDEX),
        "summary": {
            "catalog_part_records": len(records),
            "records_with_oem_references": sum(bool(item["porsche_part_numbers"]) for item in records),
            "records_with_at_least_one_pet_match": sum(bool(item["pet_occurrence_matches"]) for item in records),
            "pet_occurrence_links": total_links,
            "unmatched_oem_references": unmatched_references,
            "variant_fitment_claims": 0,
            "geometry_fit_claims": 0,
            "manufacturing_releases": 0,
        },
        "parts": records,
    }


def build(
    source_root: Path,
) -> tuple[dict[str, Any], dict[str, str], dict[str, str], dict[str, Any]]:
    listed_path, oem_path = source_paths(source_root)
    listed_payload = load_json(listed_path)
    oem_payload = load_json(oem_path)
    skeleton, illustrations, domains = skeleton_context()
    declared_payload = load_json(DECLARED_PART_DATA)
    declared_entries = [
        value for value in declared_payload.get("entries", []) if isinstance(value, dict)
    ]

    listed = listed_rows(listed_payload)
    read = read_rows(oem_payload)
    expected_listed = int(skeleton["reference_count"])
    if len(listed) != expected_listed:
        raise ContractError(f"listed_count_mismatch:{len(listed)}:{expected_listed}")

    listed_by_illustration = Counter(str(row.get("petIllustration")) for row in listed)
    for illustration, context in illustrations.items():
        actual = listed_by_illustration.get(illustration, 0)
        expected = int(context["listed_reference_count"])
        if actual != expected:
            raise ContractError(f"illustration_count_mismatch:{illustration}:{actual}:{expected}")
    unknown_illustrations = set(listed_by_illustration) - set(illustrations)
    if unknown_illustrations:
        raise ContractError(f"unknown_listed_illustrations:{sorted(unknown_illustrations)}")

    combined: list[tuple[dict[str, Any], str]] = [(row, "listed") for row in listed]
    combined.extend((row, "read") for row in read)
    combined.sort(key=lambda item: source_key(item[0]))
    keys = [source_key(row) for row, _depth in combined]
    duplicates = [key for key, count in Counter(keys).items() if count > 1]
    if duplicates:
        raise ContractError(f"duplicate_source_keys:{duplicates[:5]}")

    twins: list[dict[str, Any]] = []
    for row, depth in combined:
        illustration = str(row.get("petIllustration"))
        context = illustrations.get(illustration)
        if context is None:
            raise ContractError(f"unknown_read_illustration:{illustration}")
        twins.append(
            documentary_twin(
                row,
                depth=depth,
                illustration_context=context,
                simulation_domains=domains[context["system_id"]],
            )
        )

    twin_ids = [twin["twin_id"] for twin in twins]
    if len(twin_ids) != len(set(twin_ids)):
        raise ContractError("twin_id_collision")

    shards: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for twin in twins:
        shards[twin["catalogue_context"]["system_id"]].append(twin)
    expected_system_ids = [system["system_id"] for system in skeleton["systems"]]
    if set(shards) != set(expected_system_ids):
        raise ContractError("generated_shards_do_not_match_skeleton_systems")

    shard_texts: dict[str, str] = {}
    shard_records: list[dict[str, Any]] = []
    for system_id in expected_system_ids:
        records = sorted(shards[system_id], key=lambda twin: twin["twin_id"])
        content = "".join(canonical_json(record) + "\n" for record in records)
        path = DEFAULT_OUTPUT_ROOT / "twins" / f"{system_id}.jsonl"
        shard_texts[system_id] = content
        shard_records.append(
            {
                "system_id": system_id,
                "path": relative(path),
                "record_count": len(records),
                "sha256": sha256_text(content),
            }
        )

    reference_counts = Counter(twin["subject"]["oem_reference"] for twin in twins)
    source_counts = Counter(twin["catalogue_context"]["pet_source_id"] for twin in twins)
    depth_counts = Counter(twin["catalogue_context"]["record_depth"] for twin in twins)
    applicability_counts = Counter(
        twin["vehicle_configuration"]["applicability_status"] for twin in twins
    )
    verified_variant_records = sum(bool(twin["vehicle_configuration"]["proven_variants"]) for twin in twins)

    crosswalk = build_catalog_crosswalk(twins)
    crosswalk_text = render_json(crosswalk)
    part_masters = build_part_master_twins(twins, declared_entries)
    if len(part_masters) != len(reference_counts):
        raise ContractError("part_master_count_does_not_match_unique_references")
    master_ids = [master["twin_id"] for master in part_masters]
    if len(master_ids) != len(set(master_ids)):
        raise ContractError("part_master_twin_id_collision")
    part_master_shards: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for master in part_masters:
        shard_id = sha256_text(master["subject"]["normalized_oem_reference"])[0]
        part_master_shards[shard_id].append(master)
    master_shard_texts: dict[str, str] = {}
    master_shard_records: list[dict[str, Any]] = []
    for shard_id in MASTER_SHARD_IDS:
        records = sorted(part_master_shards[shard_id], key=lambda item: item["twin_id"])
        content = "".join(canonical_json(record) + "\n" for record in records)
        path = DEFAULT_OUTPUT_ROOT / "part-masters" / f"{shard_id}.jsonl"
        master_shard_texts[shard_id] = content
        master_shard_records.append(
            {
                "shard_id": shard_id,
                "path": relative(path),
                "record_count": len(records),
                "sha256": sha256_text(content),
            }
        )
    masters_with_declared_dimensions = sum(
        any(
            isinstance(observation.get("bounding_box_mm"), list)
            and len(observation["bounding_box_mm"]) == 3
            for observation in master["documentary_graph"]["declared_engineering_observations"]
        )
        for master in part_masters
    )
    placeholder_materials = {"", "a_determiner", "unknown", "inconnue", "non determine"}
    masters_with_non_placeholder_material = sum(
        any(
            isinstance(observation.get("material"), str)
            and observation["material"].strip().lower() not in placeholder_materials
            for observation in master["documentary_graph"]["declared_engineering_observations"]
        )
        for master in part_masters
    )
    masters_with_dimensions_and_material = sum(
        any(
            isinstance(observation.get("bounding_box_mm"), list)
            and len(observation["bounding_box_mm"]) == 3
            and isinstance(observation.get("material"), str)
            and observation["material"].strip().lower() not in placeholder_materials
            for observation in master["documentary_graph"]["declared_engineering_observations"]
        )
        for master in part_masters
    )
    index = {
        "$comment": (
            "Index agrege des jumeaux documentaires PET 993. Les records complets restent sous work/; "
            "cet index ne contient ni PDF, ni illustration, ni CAO, ni resultat de simulation."
        ),
        "schema_version": "1.0.0",
        "generated_by": relative(Path(__file__).resolve()),
        "source_boundary": {
            "repository_role": "PorscheFanatics_external_catalogue_source",
            "expected_relative_location": "../porschefanatics.com",
            "raw_pet_pdf_copied": False,
            "pet_illustrations_copied": False,
            "oem_listed_path": "data/oem-listed.json",
            "oem_listed_sha256": sha256_file(listed_path),
            "oem_parts_path": "data/oem-parts.json",
            "oem_parts_sha256": sha256_file(oem_path),
            "declared_part_data_path": relative(DECLARED_PART_DATA),
            "declared_part_data_sha256": sha256_file(DECLARED_PART_DATA),
            "pet_sources": rights_summary(oem_payload),
        },
        "scope": {
            "generation": GENERATION,
            "fidelity": "F0_reference",
            "listed_documentary_twins": depth_counts["listed"],
            "read_documentary_twins": depth_counts["read"],
            "total_documentary_twins": len(twins),
            "unique_oem_references": len(reference_counts),
            "part_master_twins": len(part_masters),
            "reference_occurrences_reused_across_illustrations": sum(
                count - 1 for count in reference_counts.values() if count > 1
            ),
            "system_count": len(shard_records),
            "illustration_count": len({twin["catalogue_context"]["pet_illustration"] for twin in twins}),
            "configured_vehicle_bom_count": 0,
        },
        "quality": {
            "duplicate_source_keys": 0,
            "twin_id_collisions": 0,
            "orphan_illustrations": 0,
            "missing_oem_reference": sum(not twin["subject"]["oem_reference"] for twin in twins),
            "missing_description": sum(not twin["subject"]["description"] for twin in twins),
            "missing_position": sum(twin["catalogue_context"]["position"] is None for twin in twins),
            "records_with_proven_variants": verified_variant_records,
            "records_without_proven_variants": len(twins) - verified_variant_records,
            "applicability_status_counts": dict(sorted(applicability_counts.items())),
            "source_record_counts": dict(sorted((str(key), value) for key, value in source_counts.items())),
            "part_master_evidence_coverage": {
                "masters_with_declared_bounding_box": masters_with_declared_dimensions,
                "masters_with_non_placeholder_declared_material": masters_with_non_placeholder_material,
                "masters_with_declared_bounding_box_and_non_placeholder_material": (
                    masters_with_dimensions_and_material
                ),
                "qualified_material_decisions": 0,
            },
        },
        "engineering_readiness": {
            "editable_geometry": 0,
            "F2_interfaces": 0,
            "qualified_material_decisions": 0,
            "reference_solver_results": 0,
            "physicsnemo_results": 0,
            "simready_assets": 0,
            "physical_correlations": 0,
            "functional_manufacturing_releases": 0,
            "functioning_vehicle_claim": False,
        },
        "output": {
            "format": "canonical_JSONL_one_record_per_twin",
            "root": relative(DEFAULT_OUTPUT_ROOT),
            "shards": shard_records,
            "part_master_shards": master_shard_records,
            "catalog_crosswalk": {
                "path": relative(TRACKED_CROSSWALK),
                "sha256": sha256_text(crosswalk_text),
                "catalog_part_records": crosswalk["summary"]["catalog_part_records"],
                "pet_occurrence_links": crosswalk["summary"]["pet_occurrence_links"],
            },
        },
        "prohibited_claims": [
            "12879_records_are_12879_parts_mounted_on_one_car",
            "catalogue_appearance_proves_variant_fitment",
            "documentary_twin_is_geometry_or_simulation",
            "documentary_twin_is_SimReady",
            "documentary_twin_authorizes_manufacturing_or_road_use",
        ],
    }
    return index, shard_texts, master_shard_texts, crosswalk


def render_json(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def validate_tracked_index(index: dict[str, Any]) -> None:
    skeleton = load_json(SKELETON)
    scope = index.get("scope", {})
    readiness = index.get("engineering_readiness", {})
    if scope.get("generation") != GENERATION:
        raise ContractError("tracked_index_generation")
    if scope.get("listed_documentary_twins") != skeleton.get("reference_count"):
        raise ContractError("tracked_index_listed_count")
    if scope.get("total_documentary_twins") != (
        scope.get("listed_documentary_twins", 0) + scope.get("read_documentary_twins", 0)
    ):
        raise ContractError("tracked_index_total_count")
    if scope.get("part_master_twins") != scope.get("unique_oem_references"):
        raise ContractError("tracked_index_part_master_count")
    shards = index.get("output", {}).get("shards", [])
    if not isinstance(shards, list) or sum(item.get("record_count", 0) for item in shards) != scope.get(
        "total_documentary_twins"
    ):
        raise ContractError("tracked_index_shard_count")
    master_shards = index.get("output", {}).get("part_master_shards", [])
    if not isinstance(master_shards, list) or [item.get("shard_id") for item in master_shards] != list(
        MASTER_SHARD_IDS
    ):
        raise ContractError("tracked_index_part_master_shards")
    if sum(item.get("record_count", 0) for item in master_shards) != scope.get("part_master_twins"):
        raise ContractError("tracked_index_part_master_shard_count")
    for item in master_shards:
        if not isinstance(item.get("sha256"), str) or len(item["sha256"]) != 64:
            raise ContractError(f"tracked_index_part_master_shard_digest:{item.get('shard_id')}")
    for field in (
        "editable_geometry",
        "F2_interfaces",
        "qualified_material_decisions",
        "reference_solver_results",
        "physicsnemo_results",
        "simready_assets",
        "physical_correlations",
        "functional_manufacturing_releases",
    ):
        if readiness.get(field) != 0:
            raise ContractError(f"tracked_index_must_fail_closed:{field}")
    if readiness.get("functioning_vehicle_claim") is not False:
        raise ContractError("tracked_index_functioning_vehicle_claim")
    evidence_coverage = index.get("quality", {}).get("part_master_evidence_coverage", {})
    if evidence_coverage.get("qualified_material_decisions") != 0:
        raise ContractError("tracked_index_qualified_material_overclaim")
    if evidence_coverage.get("masters_with_declared_bounding_box_and_non_placeholder_material", 0) > min(
        evidence_coverage.get("masters_with_declared_bounding_box", 0),
        evidence_coverage.get("masters_with_non_placeholder_declared_material", 0),
    ):
        raise ContractError("tracked_index_evidence_coverage_does_not_close")
    source_boundary = index.get("source_boundary", {})
    if source_boundary.get("raw_pet_pdf_copied") is not False:
        raise ContractError("tracked_index_raw_pdf_boundary")
    if source_boundary.get("pet_illustrations_copied") is not False:
        raise ContractError("tracked_index_illustration_boundary")
    crosswalk_info = index.get("output", {}).get("catalog_crosswalk", {})
    crosswalk = load_json(TRACKED_CROSSWALK)
    if crosswalk_info.get("path") != relative(TRACKED_CROSSWALK):
        raise ContractError("tracked_crosswalk_path")
    if crosswalk_info.get("sha256") != sha256_text(render_json(crosswalk)):
        raise ContractError("tracked_crosswalk_digest")
    summary = crosswalk.get("summary", {})
    parts = crosswalk.get("parts")
    if not isinstance(parts, list):
        raise ContractError("tracked_crosswalk_parts")
    if crosswalk.get("source_twin_index") != relative(TRACKED_INDEX):
        raise ContractError("tracked_crosswalk_source_index")
    if summary.get("catalog_part_records") != len(parts):
        raise ContractError("tracked_crosswalk_part_count")
    if crosswalk_info.get("catalog_part_records") != len(parts):
        raise ContractError("tracked_index_crosswalk_part_count")
    part_ids = [part.get("part_id") for part in parts]
    part_paths = [part.get("part_record") for part in parts]
    if None in part_ids or len(part_ids) != len(set(part_ids)):
        raise ContractError("tracked_crosswalk_duplicate_part_id")
    if None in part_paths or len(part_paths) != len(set(part_paths)):
        raise ContractError("tracked_crosswalk_duplicate_part_path")
    actual_links = 0
    actual_unmatched = 0
    link_keys: set[tuple[str, str, str]] = set()
    for part in parts:
        matches = part.get("pet_occurrence_matches")
        unmatched = part.get("unmatched_oem_references")
        references = part.get("porsche_part_numbers")
        claims = part.get("claims", {})
        if not isinstance(matches, list) or not isinstance(unmatched, list) or not isinstance(references, list):
            raise ContractError(f"tracked_crosswalk_invalid_part:{part.get('part_id')}")
        if claims.get("identity_crosswalk") is not bool(matches):
            raise ContractError(f"tracked_crosswalk_identity_claim:{part.get('part_id')}")
        for claim in ("variant_fitment", "geometry_fit", "manufacturing_release"):
            if claims.get(claim) is not False:
                raise ContractError(f"tracked_crosswalk_overclaim:{part.get('part_id')}:{claim}")
        actual_links += len(matches)
        actual_unmatched += len(unmatched)
        for match in matches:
            expected_master_id = part_master_twin_id(normalize_oem_reference(str(match.get("oem_reference"))))
            if match.get("part_master_twin_id") != expected_master_id:
                raise ContractError(f"tracked_crosswalk_part_master_id:{part.get('part_id')}")
            key = (str(part.get("part_id")), str(match.get("oem_reference")), str(match.get("twin_id")))
            if key in link_keys:
                raise ContractError(f"tracked_crosswalk_duplicate_link:{key}")
            link_keys.add(key)
    if summary.get("pet_occurrence_links") != actual_links:
        raise ContractError("tracked_crosswalk_link_count")
    if crosswalk_info.get("pet_occurrence_links") != actual_links:
        raise ContractError("tracked_index_crosswalk_link_count")
    if summary.get("unmatched_oem_references") != actual_unmatched:
        raise ContractError("tracked_crosswalk_unmatched_count")
    if summary.get("records_with_oem_references") != sum(
        bool(part["porsche_part_numbers"]) for part in parts
    ):
        raise ContractError("tracked_crosswalk_records_with_references")
    if summary.get("records_with_at_least_one_pet_match") != sum(
        bool(part["pet_occurrence_matches"]) for part in parts
    ):
        raise ContractError("tracked_crosswalk_records_with_matches")
    if summary.get("variant_fitment_claims") != 0 or summary.get("geometry_fit_claims") != 0:
        raise ContractError("tracked_crosswalk_overclaims_fit")
    if summary.get("manufacturing_releases") != 0:
        raise ContractError("tracked_crosswalk_overclaims_release")


def write_outputs(
    index: dict[str, Any],
    shard_texts: dict[str, str],
    master_shard_texts: dict[str, str],
    crosswalk: dict[str, Any],
    output_root: Path,
) -> None:
    if output_root.resolve() != DEFAULT_OUTPUT_ROOT.resolve():
        raise ContractError("custom_output_root_not_supported_by_tracked_index")
    twin_root = output_root / "twins"
    twin_root.mkdir(parents=True, exist_ok=True)
    for system_id, content in shard_texts.items():
        (twin_root / f"{system_id}.jsonl").write_text(content, encoding="utf-8")
    master_root = output_root / "part-masters"
    master_root.mkdir(parents=True, exist_ok=True)
    for shard_id, content in master_shard_texts.items():
        (master_root / f"{shard_id}.jsonl").write_text(content, encoding="utf-8")
    (output_root / "index.json").write_text(render_json(index), encoding="utf-8")
    (output_root / "catalog-crosswalk.json").write_text(render_json(crosswalk), encoding="utf-8")
    TRACKED_INDEX.parent.mkdir(parents=True, exist_ok=True)
    TRACKED_INDEX.write_text(render_json(index), encoding="utf-8")
    TRACKED_CROSSWALK.write_text(render_json(crosswalk), encoding="utf-8")


def check_outputs(
    index: dict[str, Any],
    shard_texts: dict[str, str],
    master_shard_texts: dict[str, str],
    crosswalk: dict[str, Any],
    output_root: Path,
) -> list[str]:
    errors: list[str] = []
    expected_index = render_json(index)
    for path in (TRACKED_INDEX, output_root / "index.json"):
        if not path.is_file():
            errors.append(f"missing:{path}")
        elif path.read_text(encoding="utf-8") != expected_index:
            errors.append(f"stale:{path}")
    for system_id, content in shard_texts.items():
        path = output_root / "twins" / f"{system_id}.jsonl"
        if not path.is_file():
            errors.append(f"missing:{path}")
        elif path.read_text(encoding="utf-8") != content:
            errors.append(f"stale:{path}")
    for shard_id, content in master_shard_texts.items():
        path = output_root / "part-masters" / f"{shard_id}.jsonl"
        if not path.is_file():
            errors.append(f"missing:{path}")
        elif path.read_text(encoding="utf-8") != content:
            errors.append(f"stale:{path}")
    expected_crosswalk = render_json(crosswalk)
    for path in (TRACKED_CROSSWALK, output_root / "catalog-crosswalk.json"):
        if not path.is_file():
            errors.append(f"missing:{path}")
        elif path.read_text(encoding="utf-8") != expected_crosswalk:
            errors.append(f"stale:{path}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="generate tracked index and work shards")
    mode.add_argument("--check", action="store_true", help="compare source, tracked index and work shards")
    mode.add_argument("--check-index", action="store_true", help="validate only the tracked aggregate index")
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args(argv)

    try:
        if args.check_index:
            validate_tracked_index(load_json(TRACKED_INDEX))
            print(f"valid {relative(TRACKED_INDEX)}")
            return 0
        index, shards, master_shards, crosswalk = build(args.source_root)
        if args.write:
            write_outputs(index, shards, master_shards, crosswalk, args.output_root)
            validate_tracked_index(index)
            print(
                f"wrote {index['scope']['total_documentary_twins']} documentary twins "
                f"and {index['scope']['part_master_twins']} part masters across "
                f"{len(shards) + len(master_shards)} shards and {relative(TRACKED_INDEX)}"
            )
            return 0
        validate_tracked_index(index)
        errors = check_outputs(index, shards, master_shards, crosswalk, args.output_root)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        print(f"current {relative(TRACKED_INDEX)} and {relative(args.output_root)}")
        return 0
    except ContractError as exc:
        print(f"PET 993 twin contract error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
