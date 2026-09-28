#!/usr/bin/env python3
"""Federate every Porsche 993 PET part-master twin as an OpenUSD metadata prim.

Detailed PET-derived identity text remains under ``work/``.  The tracked
manifest contains only aggregate counts, input/output digests, and fail-closed
claim boundaries.  No geometry, transform, material, physics, or SimReady
result is invented by this federation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PET_INDEX = ROOT / "twins" / "pet-993" / "index-f0.json"
READINESS_INDEX = ROOT / "twins" / "pet-993" / "engineering-readiness-f0.json"
SKELETON = ROOT / "catalog" / "reference" / "993-assembly-skeleton.json"
SIMREADY_PREFLIGHT = (
    ROOT / "twins" / "vehicle-993" / "functional-flow-simready-preflight-f0.json"
)
CATALOGUE_TWIN_INDEX = ROOT / "twins" / "catalogue-parts" / "index.json"
OUTPUT_ROOT = ROOT / "work" / "pet-993" / "openusd"
ROOT_STAGE = OUTPUT_ROOT / "pet-993-part-masters-f0.usda"
SHARD_ROOT = OUTPUT_ROOT / "shards"
MANIFEST = ROOT / "twins" / "pet-993" / "openusd-federation-f0.json"
SHARD_IDS = tuple("0123456789abcdef")


class ContractError(ValueError):
    """Raised when the source twins, generated USD, or claims do not close."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot_load:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"expected_object:{path}")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    try:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ContractError(f"expected_jsonl_object:{path}:{line_number}")
            records.append(value)
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot_load_jsonl:{path}:{exc}") from exc
    return records


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def usd_string(value: object) -> str:
    return json.dumps(str(value), ensure_ascii=True)


def usd_string_array(values: list[object]) -> str:
    return "[" + ", ".join(usd_string(value) for value in values) + "]"


def usd_name(value: str) -> str:
    name = re.sub(r"[^A-Za-z0-9_]", "_", value)
    if not name or name[0].isdigit():
        name = f"N_{name}"
    return name


def usd_bool(value: object) -> str:
    return "true" if value is True else "false"


def usd_asset_array(paths: list[str]) -> str:
    return "[" + ", ".join(f"@{path}@" for path in paths) + "]"


def normalize_oem_reference(value: str) -> str:
    return "".join(character for character in value.upper() if character.isalnum())


def catalogue_proxy_candidates() -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    index = load_json(CATALOGUE_TWIN_INDEX)
    twins = index.get("twins", [])
    if not isinstance(twins, list):
        raise ContractError("catalogue_twin_index_twins")
    by_reference: dict[str, list[dict[str, Any]]] = {}
    normalized: list[dict[str, Any]] = []
    for twin in twins:
        if not isinstance(twin, dict):
            raise ContractError("catalogue_twin_record")
        subject = twin.get("subject", {})
        geometry = twin.get("geometry", {})
        reference = subject.get("oem_reference")
        usd_path = geometry.get("file")
        editable_path = geometry.get("editable_proxy_file")
        record = {
            "proxy_twin_id": twin.get("twin_id"),
            "oem_reference_present": isinstance(reference, str) and bool(reference.strip()),
            "normalized_oem_reference": (
                normalize_oem_reference(reference)
                if isinstance(reference, str) and reference.strip()
                else None
            ),
            "usd_asset": usd_path,
            "editable_proxy_asset": editable_path,
            "fidelity": twin.get("fidelity"),
            "validation_status": twin.get("validation", {}).get("status"),
            "geometry_fit_validated": twin.get("validation", {}).get(
                "geometry_fit_validated"
            ),
        }
        normalized.append(record)
        if record["normalized_oem_reference"] is None:
            continue
        if not isinstance(usd_path, str) or not (ROOT / usd_path).is_file():
            raise ContractError(f"missing_catalogue_proxy_usd:{twin.get('twin_id')}")
        if not isinstance(editable_path, str) or not (ROOT / editable_path).is_file():
            raise ContractError(f"missing_catalogue_proxy_editable:{twin.get('twin_id')}")
        by_reference.setdefault(record["normalized_oem_reference"], []).append(record)
    for candidates in by_reference.values():
        candidates.sort(key=lambda item: str(item["proxy_twin_id"]))
    return by_reference, normalized


def descriptor_map(index: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    values = index.get("output", {}).get(key, [])
    if not isinstance(values, list):
        raise ContractError(f"index_output:{key}")
    result: dict[str, dict[str, Any]] = {}
    for item in values:
        if not isinstance(item, dict):
            raise ContractError(f"index_descriptor:{key}")
        shard_id = str(item.get("shard_id"))
        if shard_id in result:
            raise ContractError(f"duplicate_shard:{key}:{shard_id}")
        result[shard_id] = item
    if set(result) != set(SHARD_IDS):
        raise ContractError(f"shard_set:{key}")
    return result


def validated_shard_records(
    descriptors: dict[str, dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for shard_id in SHARD_IDS:
        descriptor = descriptors[shard_id]
        path = ROOT / str(descriptor["path"])
        if not path.is_file():
            raise ContractError(f"missing_shard:{path}")
        if sha256_file(path) != descriptor.get("sha256"):
            raise ContractError(f"stale_shard_digest:{path}")
        records = load_jsonl(path)
        if len(records) != int(descriptor.get("record_count", -1)):
            raise ContractError(f"shard_record_count:{path}")
        result[shard_id] = records
    return result


def merged_records() -> tuple[
    dict[str, list[tuple[dict[str, Any], dict[str, Any]]]],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    pet_index = load_json(PET_INDEX)
    readiness_index = load_json(READINESS_INDEX)
    skeleton = load_json(SKELETON)
    master_descriptors = descriptor_map(pet_index, "part_master_shards")
    task_descriptors = descriptor_map(readiness_index, "shards")
    masters = validated_shard_records(master_descriptors)
    tasks = validated_shard_records(task_descriptors)
    merged: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {}
    all_master_ids: set[str] = set()
    all_task_ids: set[str] = set()
    for shard_id in SHARD_IDS:
        master_by_id = {str(item.get("twin_id")): item for item in masters[shard_id]}
        task_by_id = {
            str(item.get("part_master_twin_id")): item for item in tasks[shard_id]
        }
        if len(master_by_id) != len(masters[shard_id]):
            raise ContractError(f"duplicate_master_id:{shard_id}")
        if len(task_by_id) != len(tasks[shard_id]):
            raise ContractError(f"duplicate_task_master_id:{shard_id}")
        if set(master_by_id) != set(task_by_id):
            raise ContractError(f"master_task_mismatch:{shard_id}")
        all_master_ids.update(master_by_id)
        all_task_ids.update(task_by_id)
        merged[shard_id] = [
            (master_by_id[twin_id], task_by_id[twin_id])
            for twin_id in sorted(master_by_id)
        ]
    expected = int(pet_index.get("scope", {}).get("part_master_twins", -1))
    if len(all_master_ids) != expected or all_master_ids != all_task_ids:
        raise ContractError("global_master_task_identity")
    if expected != 6013:
        raise ContractError(f"unexpected_master_count:{expected}")
    return merged, pet_index, readiness_index, skeleton


def render_root_stage(skeleton: dict[str, Any], master_count: int) -> str:
    sublayers = ",\n".join(f"        @shards/{shard_id}.usda@" for shard_id in SHARD_IDS)
    lines = [
        "#usda 1.0",
        "(",
        '    defaultPrim = "PET993Catalogue"',
        "    metersPerUnit = 1",
        '    upAxis = "Z"',
        "    subLayers = [",
        sublayers,
        "    ]",
        ")",
        "",
        'def Xform "PET993Catalogue" (',
        "    customData = {",
        '        string fidelity = "F0_documentary_part_master_federation"',
        '        string purpose = "catalogue_identity_and_engineering_readiness_not_vehicle_assembly"',
        f"        int partMasterCount = {master_count}",
        "        int geometryPrimCount = 0",
        "        int positionedVehiclePartCount = 0",
        "        int qualifiedMaterialDecisionCount = 0",
        "        int referenceSolverPassCount = 0",
        "        int physicsNeMoPassCount = 0",
        "        int simreadyValidatedCount = 0",
        "        bool functioningVehicle = false",
        "    }",
        ")",
        "{",
        '    def Scope "Systems"',
        "    {",
    ]
    systems = skeleton.get("systems", [])
    if len(systems) != 10:
        raise ContractError("skeleton_system_count")
    for system in systems:
        system_id = str(system["system_id"])
        lines.extend(
            [
                f'        def Scope "{usd_name(f"System_{system_id}")}"',
                "        {",
                f"            custom string systemId = {usd_string(system_id)}",
                f"            custom string systemName = {usd_string(system.get('name', ''))}",
                f"            custom int illustrationCount = {int(system.get('illustration_count', 0))}",
                "        }",
            ]
        )
    lines.extend(
        [
            "    }",
            "",
            '    def Scope "PartMasters"',
            "    {",
            "    }",
            "}",
            "",
        ]
    )
    return "\n".join(lines)


def render_master_prim(
    master: dict[str, Any],
    task: dict[str, Any],
    proxy_candidates: list[dict[str, Any]],
) -> list[str]:
    twin_id = str(master["twin_id"])
    subject = master.get("subject", {})
    documentary = master.get("documentary_graph", {})
    gates = task.get("engineering_gates", {})
    route = task.get("engineering_route", {})
    configuration = task.get("configuration_evidence", {})
    risk = task.get("risk_and_priority", {})
    claims = task.get("claims", {})
    input_evidence = task.get("input_evidence", {})
    catalogue = task.get("catalog_part_engineering", {})
    simulations = task.get("linked_simulation_evidence", {})
    manual = task.get("workshop_manual_evidence", {})
    system_ids = [str(value) for value in documentary.get("system_ids", [])]
    system_targets = ", ".join(
        f"</PET993Catalogue/Systems/{usd_name(f'System_{system_id}')}>"
        for system_id in system_ids
    )
    descriptions = [str(value) for value in subject.get("descriptions", [])]
    references = [str(value) for value in subject.get("display_references", [])]
    proxy_twin_ids = [str(value["proxy_twin_id"]) for value in proxy_candidates]
    proxy_usd_assets = [
        os.path.relpath(ROOT / str(value["usd_asset"]), SHARD_ROOT)
        for value in proxy_candidates
    ]
    proxy_editable_assets = [
        os.path.relpath(ROOT / str(value["editable_proxy_asset"]), SHARD_ROOT)
        for value in proxy_candidates
    ]
    return [
        f'        def Xform "{usd_name(twin_id)}"',
        "        {",
        f"            custom string twinId = {usd_string(twin_id)}",
        f"            custom string engineeringTaskId = {usd_string(task.get('engineering_task_id', ''))}",
        f"            custom string normalizedOemReference = {usd_string(subject.get('normalized_oem_reference', ''))}",
        f"            custom string[] displayReferences = {usd_string_array(references)}",
        f"            custom string[] descriptions = {usd_string_array(descriptions)}",
        f"            custom int documentaryOccurrenceCount = {int(documentary.get('occurrence_count', 0))}",
        f"            custom string fidelity = {usd_string(gates.get('current_fidelity', 'F0_reference'))}",
        f"            custom string priority = {usd_string(risk.get('priority', ''))}",
        f"            custom string criticalityTier = {usd_string(risk.get('criticality_tier', ''))}",
        f"            custom string engineeringArchetype = {usd_string(route.get('engineering_archetype', ''))}",
        f"            custom string nextRequiredGate = {usd_string(gates.get('next_required_gate', ''))}",
        f"            custom string configurationStatus = {usd_string(configuration.get('status', ''))}",
        f"            custom bool turboIntegrationEvidence = {usd_bool(configuration.get('turbo_integration_evidence'))}",
        f"            custom int compatibleConfigurationCandidateCount = {int(configuration.get('compatible_configuration_candidate_count', 0))}",
        f"            custom int declaredBoundingBoxCount = {int(input_evidence.get('declared_bounding_box_count', 0))}",
        f"            custom int declaredMassCount = {int(input_evidence.get('declared_mass_count', 0))}",
        f"            custom int declaredMaterialObservationCount = {int(input_evidence.get('non_placeholder_declared_material_count', 0))}",
        f"            custom int workshopManualCandidateCount = {int(manual.get('candidate_record_count', 0))}",
        f"            custom int linkedCatalogueEngineeringRecordCount = {int(catalogue.get('record_count', 0))}",
        f"            custom int linkedSimulationEvidenceCount = {int(simulations.get('record_count', 0))}",
        f"            custom string[] candidateProxyTwinIds = {usd_string_array(proxy_twin_ids)}",
        f"            custom asset[] candidateProxyUsdAssets = {usd_asset_array(proxy_usd_assets)}",
        f"            custom asset[] candidateEditableProxyAssets = {usd_asset_array(proxy_editable_assets)}",
        '            custom string candidateProxyLinkStatus = "exact_normalized_oem_reference_only_not_geometry_fit"',
        "            custom bool candidateProxyComposed = false",
        f"            custom bool humanReviewed = {usd_bool(claims.get('human_reviewed_task'))}",
        f"            custom bool editableEnvelopeCandidatePresent = {usd_bool(str(gates.get('editable_geometry', '')).startswith('F1_editable_envelope'))}",
        f"            custom bool editableValveDimensionalSurrogatePresent = {usd_bool(str(gates.get('editable_geometry', '')).startswith('F1_editable_valve'))}",
        f"            custom bool editableK16EnvelopeDiameterGuidesPresent = {usd_bool(str(gates.get('editable_geometry', '')).startswith('F1_editable_K16'))}",
        f"            custom bool editableHeatShieldEnvelopeThermalReadinessPresent = {usd_bool(str(gates.get('editable_geometry', '')).startswith('F1_editable_heat_shield'))}",
        f"            custom bool turboLubricationControlTopologyReadinessPresent = {usd_bool(str(gates.get('editable_geometry', '')).startswith('F1_generated_nonspatial_turbo_lubrication_control'))}",
        f"            custom bool oilTankCircuitTopologyReadinessPresent = {usd_bool(str(gates.get('editable_geometry', '')).startswith('F1_generated_nonspatial_oil_tank_circuit'))}",
        f"            custom bool oilCoolerCircuitTopologyReadinessPresent = {usd_bool(str(gates.get('editable_geometry', '')).startswith('F1_generated_nonspatial_oil_cooler_circuit'))}",
        f"            custom bool massConstrainedStructuralSurrogateVirtualF2ReadinessPresent = {usd_bool(str(gates.get('editable_geometry', '')).startswith('F1_mass_constrained_structural_surrogate'))}",
        "            custom bool F2InterfaceGeometryPresent = false",
        f"            custom bool qualifiedMaterialSelected = {usd_bool(claims.get('material_selected'))}",
        f"            custom bool referenceSimulationPassed = {usd_bool(claims.get('reference_simulation_passed'))}",
        f"            custom bool physicsNeMoValidated = {usd_bool(claims.get('physicsnemo_validated'))}",
        f"            custom bool simreadyValidated = {usd_bool(claims.get('simready_validated'))}",
        f"            custom bool manufacturingReleased = {usd_bool(claims.get('manufacturing_released'))}",
        f"            rel systemMembership = [{system_targets}]",
        "        }",
    ]


def render_shard(
    shard_id: str,
    records: list[tuple[dict[str, Any], dict[str, Any]]],
    proxies_by_reference: dict[str, list[dict[str, Any]]],
) -> str:
    lines = [
        "#usda 1.0",
        "",
        'over "PET993Catalogue"',
        "{",
        '    over "PartMasters"',
        "    {",
    ]
    for master, task in records:
        reference = str(master.get("subject", {}).get("normalized_oem_reference", ""))
        lines.extend(render_master_prim(master, task, proxies_by_reference.get(reference, [])))
    lines.extend(["    }", "}", ""])
    return "\n".join(lines)


def aggregate_counts(
    merged: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]],
    proxies_by_reference: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    priority = Counter()
    next_gate = Counter()
    systems = Counter()
    archetypes = Counter()
    fidelities = Counter()
    totals = Counter()
    for shard_id in SHARD_IDS:
        for master, task in merged[shard_id]:
            documentary = master.get("documentary_graph", {})
            gates = task.get("engineering_gates", {})
            route = task.get("engineering_route", {})
            configuration = task.get("configuration_evidence", {})
            evidence = task.get("input_evidence", {})
            claims = task.get("claims", {})
            reference = str(master.get("subject", {}).get("normalized_oem_reference", ""))
            proxy_candidates = proxies_by_reference.get(reference, [])
            priority[str(task.get("risk_and_priority", {}).get("priority"))] += 1
            next_gate[str(gates.get("next_required_gate"))] += 1
            archetypes[str(route.get("engineering_archetype"))] += 1
            fidelities[str(gates.get("current_fidelity"))] += 1
            for system_id in documentary.get("system_ids", []):
                systems[str(system_id)] += 1
                totals["system_membership_links"] += 1
            totals["part_master_prims"] += 1
            totals["documentary_occurrences"] += int(documentary.get("occurrence_count", 0))
            totals["with_turbo_integration_evidence"] += int(
                configuration.get("turbo_integration_evidence") is True
            )
            totals["with_declared_bounding_box"] += int(
                int(evidence.get("declared_bounding_box_count", 0)) > 0
            )
            totals["with_declared_mass"] += int(
                int(evidence.get("declared_mass_count", 0)) > 0
            )
            totals["with_non_placeholder_material_observation"] += int(
                int(evidence.get("non_placeholder_declared_material_count", 0)) > 0
            )
            totals["with_workshop_manual_candidates"] += int(
                int(task.get("workshop_manual_evidence", {}).get("candidate_record_count", 0)) > 0
            )
            totals["with_linked_catalogue_engineering"] += int(
                int(task.get("catalog_part_engineering", {}).get("record_count", 0)) > 0
            )
            totals["with_linked_simulation_evidence"] += int(
                int(task.get("linked_simulation_evidence", {}).get("record_count", 0)) > 0
            )
            totals["human_reviewed"] += int(claims.get("human_reviewed_task") is True)
            totals["selected_material"] += int(claims.get("material_selected") is True)
            totals["reference_simulation_passed"] += int(
                claims.get("reference_simulation_passed") is True
            )
            totals["physicsnemo_validated"] += int(
                claims.get("physicsnemo_validated") is True
            )
            totals["simready_validated"] += int(claims.get("simready_validated") is True)
            totals["manufacturing_released"] += int(
                claims.get("manufacturing_released") is True
            )
            totals["with_exact_oem_proxy_candidate"] += int(bool(proxy_candidates))
            totals["exact_oem_proxy_candidate_links"] += len(proxy_candidates)
    return {
        **dict(sorted(totals.items())),
        "by_priority": dict(sorted(priority.items())),
        "by_next_required_gate": dict(sorted(next_gate.items())),
        "by_system_membership": dict(sorted(systems.items())),
        "by_engineering_archetype": dict(sorted(archetypes.items())),
        "by_current_fidelity": dict(sorted(fidelities.items())),
    }


def build() -> tuple[str, dict[str, str], dict[str, Any]]:
    merged, pet_index, readiness_index, skeleton = merged_records()
    proxies_by_reference, catalogue_proxies = catalogue_proxy_candidates()
    counts = aggregate_counts(merged, proxies_by_reference)
    root_stage = render_root_stage(skeleton, counts["part_master_prims"])
    shard_texts = {
        shard_id: render_shard(shard_id, merged[shard_id], proxies_by_reference)
        for shard_id in SHARD_IDS
    }
    master_sources = descriptor_map(pet_index, "part_master_shards")
    task_sources = descriptor_map(readiness_index, "shards")
    manifest = {
        "$comment": (
            "Federation OpenUSD F0 des jumeaux maitres PET. Les couches detaillees "
            "restent sous work/ et ne constituent ni geometrie, ni BOM, ni preuve SimReady."
        ),
        "schema_version": "1.0.0",
        "generated_by": relative(Path(__file__).resolve()),
        "source_boundary": {
            "pet_twin_index": relative(PET_INDEX),
            "pet_twin_index_sha256": sha256_file(PET_INDEX),
            "engineering_readiness_index": relative(READINESS_INDEX),
            "engineering_readiness_index_sha256": sha256_file(READINESS_INDEX),
            "assembly_skeleton": relative(SKELETON),
            "assembly_skeleton_sha256": sha256_file(SKELETON),
            "simready_preflight": relative(SIMREADY_PREFLIGHT),
            "simready_preflight_sha256": sha256_file(SIMREADY_PREFLIGHT),
            "catalogue_twin_index": relative(CATALOGUE_TWIN_INDEX),
            "catalogue_twin_index_sha256": sha256_file(CATALOGUE_TWIN_INDEX),
            "part_master_shards": [master_sources[value] for value in SHARD_IDS],
            "engineering_task_shards": [task_sources[value] for value in SHARD_IDS],
        },
        "output": {
            "root_stage": relative(ROOT_STAGE),
            "root_stage_sha256": sha256_bytes(root_stage.encode("utf-8")),
            "format": "OpenUSD_ASCII_sublayer_federation",
            "fidelity": "F0_documentary_part_master_federation",
            "tracked": False,
            "shards": [
                {
                    "shard_id": shard_id,
                    "path": relative(SHARD_ROOT / f"{shard_id}.usda"),
                    "part_master_prim_count": len(merged[shard_id]),
                    "sha256": sha256_bytes(shard_texts[shard_id].encode("utf-8")),
                }
                for shard_id in SHARD_IDS
            ],
        },
        "scope": {
            **counts,
            "root_stage_count": 1,
            "shard_layer_count": len(SHARD_IDS),
            "system_scope_count": 10,
            "geometry_prim_count": 0,
            "positioned_vehicle_part_count": 0,
            "configured_vehicle_bom_entries": 0,
            "catalogue_proxy_assets": len(catalogue_proxies),
            "catalogue_proxy_assets_with_oem_reference": sum(
                item["oem_reference_present"] for item in catalogue_proxies
            ),
        },
        "proxy_linkage": {
            "method": "exact_normalized_oem_reference",
            "candidate_only": True,
            "geometry_composed_into_federation": False,
            "links": [
                {
                    "part_master_twin_id": master["twin_id"],
                    "proxy_twin_id": proxy["proxy_twin_id"],
                    "usd_asset": proxy["usd_asset"],
                    "editable_proxy_asset": proxy["editable_proxy_asset"],
                    "fidelity": proxy["fidelity"],
                    "validation_status": proxy["validation_status"],
                    "geometry_fit_validated": proxy["geometry_fit_validated"],
                    "link_status": "identity_candidate_not_geometry_fit",
                }
                for shard_id in SHARD_IDS
                for master, _task in merged[shard_id]
                for proxy in proxies_by_reference.get(
                    str(master.get("subject", {}).get("normalized_oem_reference", "")),
                    [],
                )
            ],
        },
        "validation": {
            "source_shard_digests": "passed",
            "master_task_one_to_one_identity": "passed",
            "deterministic_ascii_contract": "passed",
            "openusd_python_api": "blocked_by_recorded_preflight",
            "asset_validator": "blocked_by_recorded_preflight",
            "simready_foundation": "blocked_by_recorded_preflight",
            "content_agents_material_physics": "blocked_by_recorded_preflight",
            "simready_validated": False,
        },
        "rights_boundary": {
            "detailed_pet_identity_text_location": "work_only_untracked",
            "tracked_manifest_contains_oem_references_or_descriptions": False,
            "raw_pet_pdf_or_illustrations_copied": False,
            "do_not_commit_generated_usd_layers": True,
        },
        "claim_boundary": {
            "part_master_prim_is_geometry": False,
            "part_master_prim_is_configured_vehicle_instance": False,
            "system_membership_is_vehicle_transform": False,
            "declared_observation_is_qualified_material": False,
            "engineering_route_is_solver_result": False,
            "federation_is_simready": False,
            "federation_authorizes_manufacturing_or_road_use": False,
        },
        "next_gate": (
            "promote_each_master_only_with_configuration_evidence_editable_geometry_"
            "interfaces_material_loads_reference_solver_and_successful_SimReady_validation"
        ),
    }
    validate(root_stage, shard_texts, manifest)
    return root_stage, shard_texts, manifest


def validate(root_stage: str, shard_texts: dict[str, str], manifest: dict[str, Any]) -> None:
    scope = manifest.get("scope", {})
    if scope.get("part_master_prims") != 6013:
        raise ContractError("part_master_prim_count")
    if scope.get("shard_layer_count") != 16 or set(shard_texts) != set(SHARD_IDS):
        raise ContractError("output_shard_count")
    if sum(text.count('def Xform "TWIN_') for text in shard_texts.values()) != 6013:
        raise ContractError("rendered_part_master_prim_count")
    if root_stage.count('def Scope "System_') != 10:
        raise ContractError("rendered_system_scope_count")
    if scope.get("documentary_occurrences") != 12879:
        raise ContractError("documentary_occurrence_count")
    if scope.get("by_current_fidelity") != {
        "F0_reference": 5842,
        "F1_charge_air_chain_guides_unvalidated": 5,
        "F1_heat_shield_envelope_thermal_readiness_unvalidated": 1,
        "F1_k16_envelope_diameter_guides_unvalidated": 4,
        "F1_mass_constrained_structural_surrogate_virtual_F2_readiness": 1,
        "F1_oil_tank_circuit_topology_readiness_unvalidated": 81,
        "F1_oil_cooler_circuit_topology_readiness_unvalidated": 41,
        "F1_turbo_lubrication_control_topology_readiness_unvalidated": 35,
        "F1_valve_dimensional_surrogate_unvalidated": 3,
    }:
        raise ContractError("current_fidelity_partition")
    linkage = manifest.get("proxy_linkage", {})
    if len(linkage.get("links", [])) != scope.get("exact_oem_proxy_candidate_links"):
        raise ContractError("proxy_link_count")
    if linkage.get("geometry_composed_into_federation") is not False:
        raise ContractError("proxy_geometry_composition")
    for link in linkage.get("links", []):
        if link.get("geometry_fit_validated") is not False:
            raise ContractError(f"proxy_fit_overclaim:{link.get('proxy_twin_id')}")
    for field in (
        "geometry_prim_count",
        "positioned_vehicle_part_count",
        "configured_vehicle_bom_entries",
        "human_reviewed",
        "selected_material",
        "reference_simulation_passed",
        "physicsnemo_validated",
        "simready_validated",
        "manufacturing_released",
    ):
        if scope.get(field) != 0:
            raise ContractError(f"overclaim:{field}:{scope.get(field)}")
    combined = root_stage + "\n" + "\n".join(shard_texts.values())
    for prohibited in (
        "UsdPhysics",
        "RigidBodyAPI",
        "CollisionAPI",
        "MassAPI",
        "MaterialBindingAPI",
        "xformOp:translate",
        "def Mesh",
        "def Cube",
    ):
        if prohibited in combined:
            raise ContractError(f"prohibited_usd_claim:{prohibited}")
    if manifest.get("output", {}).get("tracked") is not False:
        raise ContractError("output_tracking_boundary")
    rights = manifest.get("rights_boundary", {})
    if rights.get("tracked_manifest_contains_oem_references_or_descriptions") is not False:
        raise ContractError("rights_boundary")
    if any(value is not False for value in manifest.get("claim_boundary", {}).values()):
        raise ContractError("claim_boundary")
    preflight = load_json(SIMREADY_PREFLIGHT)
    if preflight.get("status") != "blocked":
        raise ContractError("unexpected_preflight_status")
    if manifest.get("validation", {}).get("simready_validated") is not False:
        raise ContractError("simready_overclaim")


def render_json(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def write_outputs(root_stage: str, shards: dict[str, str], manifest: dict[str, Any]) -> None:
    SHARD_ROOT.mkdir(parents=True, exist_ok=True)
    ROOT_STAGE.write_text(root_stage, encoding="utf-8")
    for shard_id in SHARD_IDS:
        (SHARD_ROOT / f"{shard_id}.usda").write_text(shards[shard_id], encoding="utf-8")
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(render_json(manifest), encoding="utf-8")


def check_outputs(root_stage: str, shards: dict[str, str], manifest: dict[str, Any]) -> None:
    expected: dict[Path, str] = {ROOT_STAGE: root_stage, MANIFEST: render_json(manifest)}
    expected.update({SHARD_ROOT / f"{key}.usda": value for key, value in shards.items()})
    for path, content in expected.items():
        if not path.is_file():
            raise ContractError(f"missing_output:{path}")
        if path.read_text(encoding="utf-8") != content:
            raise ContractError(f"stale_output:{path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--check-index", action="store_true")
    args = parser.parse_args(argv)
    try:
        root_stage, shards, manifest = build()
        if args.write:
            write_outputs(root_stage, shards, manifest)
            print(f"wrote {relative(ROOT_STAGE)} and {len(shards)} shard layers")
            print(f"wrote {relative(MANIFEST)}")
            return 0
        check_outputs(root_stage, shards, manifest)
        print(
            f"valid {relative(ROOT_STAGE)}: "
            f"{manifest['scope']['part_master_prims']} part-master metadata prims"
        )
        print(f"valid {relative(MANIFEST)}")
        return 0
    except ContractError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
