#!/usr/bin/env python3
"""Generate the fail-closed, catalogue-scoped Porsche 993 vehicle program.

The PET-derived skeleton is an aggregate of references across incompatible
variants.  This generator turns its systems and illustrations into engineering
work packages; it does not turn catalogue references into mounted part
instances, geometry, material decisions, or simulation evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SKELETON = ROOT / "catalog" / "reference" / "993-assembly-skeleton.json"
DEFINITION = ROOT / "twins" / "vehicle-993" / "program-definition.json"
OUTPUT = ROOT / "twins" / "vehicle-993" / "program-f0.json"
CATALOGUE_TWIN_INDEX = ROOT / "twins" / "catalogue-parts" / "index.json"
PET_TWIN_INDEX = ROOT / "twins" / "pet-993" / "index-f0.json"
VARIANT_CONFIGURATIONS = ROOT / "twins" / "vehicle-993" / "variant-configurations-f0.json"
CONFIGURATION_AXES = ROOT / "twins" / "vehicle-993" / "configuration-axes-f0.json"
CONFIGURATION_ROSTER = ROOT / "twins" / "vehicle-993" / "configuration-roster-f0.json"
CONFIGURATION_PART_LINKS = ROOT / "twins" / "vehicle-993" / "configuration-part-links-f0.json"
CONFIGURATION_EXCEPTIONS = ROOT / "twins" / "vehicle-993" / "configuration-exceptions-f0.json"
APPLICABILITY_EVIDENCE = ROOT / "twins" / "pet-993" / "applicability-evidence-f0.json"
PET_ENGINEERING_READINESS = ROOT / "twins" / "pet-993" / "engineering-readiness-f0.json"
PET_PORSCHEFANATICS_CROSSWALK = (
    ROOT / "twins" / "pet-993" / "porschefanatics-crosswalk-f0.json"
)
PET_MATERIAL_PROCESS_ROUTING = (
    ROOT / "twins" / "pet-993" / "material-process-routing-f0.json"
)
PET_OPENUSD_FEDERATION = ROOT / "twins" / "pet-993" / "openusd-federation-f0.json"
PET_VISUAL_PROXY_ATLAS = ROOT / "twins" / "pet-993" / "visual-proxy-atlas-f0.json"
PET_VISUAL_PROXY_OPENUSD_VALIDATION = (
    ROOT / "twins" / "pet-993" / "visual-proxy-atlas-openusd-validation-f0.json"
)
MANUAL_EVIDENCE_ROUTING = ROOT / "twins" / "vehicle-993" / "manual-evidence-routing-f0.json"
TURBO_INTEGRATION_SEED = ROOT / "twins" / "vehicle-993" / "turbo-integration-seed-f0.json"
FUNCTIONAL_FLOW_GRAPH = ROOT / "twins" / "vehicle-993" / "functional-flow-graph-f0.json"
FUNCTIONAL_FLOW_OPENUSD = ROOT / "twins" / "vehicle-993" / "functional-flow-openusd-f0.json"
FUNCTIONAL_FLOW_SIMREADY_PREFLIGHT = (
    ROOT / "twins" / "vehicle-993" / "functional-flow-simready-preflight-f0.json"
)
TWIN_REFERENCE_ENVELOPE = ROOT / "twin" / "993" / "reference-envelope.json"
VEHICLE_REFERENCE_FRAME = (
    ROOT / "twins" / "vehicle-993" / "reference-frame-openusd-f1.json"
)
VEHICLE_REFERENCE_FRAME_USD = (
    ROOT / "twins" / "vehicle-993" / "usd" / "993-reference-frame-f1.usda"
)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def count_json_files(path: Path) -> int:
    return sum(1 for candidate in path.glob("*.json") if candidate.is_file())


def validate_definition(skeleton: dict[str, Any], definition: dict[str, Any]) -> None:
    if skeleton.get("generation") != definition.get("vehicle", {}).get("generation"):
        raise ValueError("definition and skeleton generations differ")

    systems = skeleton.get("systems")
    routes = definition.get("system_routes")
    domains = definition.get("simulation_domains")
    if not isinstance(systems, list) or not systems:
        raise ValueError("skeleton.systems must be a non-empty array")
    if not isinstance(routes, list) or not routes:
        raise ValueError("definition.system_routes must be a non-empty array")
    if not isinstance(domains, dict) or not domains:
        raise ValueError("definition.simulation_domains must be a non-empty object")

    skeleton_ids = [system.get("system_id") for system in systems]
    route_ids = [route.get("system_id") for route in routes]
    if len(route_ids) != len(set(route_ids)):
        raise ValueError("definition.system_routes contains duplicate system ids")
    if set(skeleton_ids) != set(route_ids):
        raise ValueError(
            f"system route mismatch: missing={sorted(set(skeleton_ids) - set(route_ids))}, "
            f"extra={sorted(set(route_ids) - set(skeleton_ids))}"
        )

    for route in routes:
        for domain_id in route.get("simulation_domains", []):
            if domain_id not in domains:
                raise ValueError(f"{route['system_id']}: unknown simulation domain {domain_id}")
        for peer in route.get("integration_interfaces", []):
            if peer != "all_systems" and peer not in skeleton_ids:
                raise ValueError(f"{route['system_id']}: unknown integration peer {peer}")

    workstreams = definition.get("engineering_workstreams")
    if not isinstance(workstreams, list) or not workstreams:
        raise ValueError("definition.engineering_workstreams must be a non-empty array")
    workstream_ids = [item.get("workstream_id") for item in workstreams]
    if len(workstream_ids) != len(set(workstream_ids)):
        raise ValueError("definition.engineering_workstreams contains duplicate ids")
    known_workstreams: set[str] = set()
    for item in workstreams:
        for dependency in item.get("depends_on", []):
            if dependency not in known_workstreams:
                raise ValueError(f"{item['workstream_id']}: unknown or forward dependency {dependency}")
        known_workstreams.add(item["workstream_id"])

    reference_total = sum(int(system["reference_count"]) for system in systems)
    if reference_total != int(skeleton.get("reference_count", -1)):
        raise ValueError("skeleton reference counts do not close")
    for system in systems:
        illustrations = system.get("illustrations", [])
        if int(system.get("illustration_count", -1)) != len(illustrations):
            raise ValueError(f"{system['system_id']}: illustration count does not close")
        if int(system["reference_count"]) != sum(int(item["reference_count"]) for item in illustrations):
            raise ValueError(f"{system['system_id']}: reference count does not close")

    claims = definition.get("claim_policy", {})
    if claims.get("virtual_only") is not True:
        raise ValueError("the program must remain virtual_only")
    for claim in ("functioning_vehicle_claim", "roadworthy_claim", "manufacturing_release_claim"):
        if claims.get(claim) is not False:
            raise ValueError(f"claim policy must fail closed: {claim}")
    if definition.get("physicsnemo_policy", {}).get("execution_enabled") is not False:
        raise ValueError("PhysicsNeMo cannot be enabled before a reference dataset exists")
    if definition.get("omniverse_policy", {}).get("simready_claim") is not False:
        raise ValueError("SimReady cannot be claimed by this F0 program")


def inventory() -> dict[str, Any]:
    catalogue_twins = load_json(CATALOGUE_TWIN_INDEX) if CATALOGUE_TWIN_INDEX.is_file() else {"twins": []}
    pet_twins = load_json(PET_TWIN_INDEX) if PET_TWIN_INDEX.is_file() else {"scope": {}, "quality": {}}
    variants = load_json(VARIANT_CONFIGURATIONS) if VARIANT_CONFIGURATIONS.is_file() else {"scope": {}}
    engineering = (
        load_json(PET_ENGINEERING_READINESS)
        if PET_ENGINEERING_READINESS.is_file()
        else {"scope": {}, "coverage": {}}
    )
    pet_openusd = (
        load_json(PET_OPENUSD_FEDERATION)
        if PET_OPENUSD_FEDERATION.is_file()
        else {"scope": {}, "validation": {}}
    )
    material_process_routing = (
        load_json(PET_MATERIAL_PROCESS_ROUTING)
        if PET_MATERIAL_PROCESS_ROUTING.is_file()
        else {"scope": {}, "coverage": {}, "claim_boundary": {}}
    )
    porschefanatics_crosswalk = (
        load_json(PET_PORSCHEFANATICS_CROSSWALK)
        if PET_PORSCHEFANATICS_CROSSWALK.is_file()
        else {"scope": {}, "coverage": {}, "claim_boundary": {}}
    )
    visual_atlas = (
        load_json(PET_VISUAL_PROXY_ATLAS)
        if PET_VISUAL_PROXY_ATLAS.is_file()
        else {"atlas": {}, "output": {}, "validation": {}}
    )
    visual_openusd_validation = (
        load_json(PET_VISUAL_PROXY_OPENUSD_VALIDATION)
        if PET_VISUAL_PROXY_OPENUSD_VALIDATION.is_file()
        else {"status": "missing", "scope": {}, "results": {}}
    )
    manual_routing = (
        load_json(MANUAL_EVIDENCE_ROUTING)
        if MANUAL_EVIDENCE_ROUTING.is_file()
        else {"scope": {}}
    )
    turbo_seed = (
        load_json(TURBO_INTEGRATION_SEED)
        if TURBO_INTEGRATION_SEED.is_file()
        else {"scope": {}}
    )
    flow_graph = (
        load_json(FUNCTIONAL_FLOW_GRAPH)
        if FUNCTIONAL_FLOW_GRAPH.is_file()
        else {"scope": {}}
    )
    flow_openusd = (
        load_json(FUNCTIONAL_FLOW_OPENUSD)
        if FUNCTIONAL_FLOW_OPENUSD.is_file()
        else {"stage": {}, "validation": {}}
    )
    flow_preflight = (
        load_json(FUNCTIONAL_FLOW_SIMREADY_PREFLIGHT)
        if FUNCTIONAL_FLOW_SIMREADY_PREFLIGHT.is_file()
        else {"status": "missing", "result_boundary": {}}
    )
    reference_frame = (
        load_json(VEHICLE_REFERENCE_FRAME)
        if VEHICLE_REFERENCE_FRAME.is_file()
        else {"scope": {}, "validation": {}, "claim_boundary": {}}
    )
    pet_scope = pet_twins.get("scope", {})
    pet_quality = pet_twins.get("quality", {})
    variant_scope = variants.get("scope", {})
    engineering_scope = engineering.get("scope", {})
    engineering_readiness = engineering.get("engineering_readiness", {})
    engineering_coverage = engineering.get("coverage", {})
    classification_audit = engineering.get("classification_audit", {})
    next_gate_counts = engineering_coverage.get(
        "tasks_by_next_required_gate", {}
    )
    fidelity_counts = engineering_coverage.get("tasks_by_current_fidelity", {})
    manual_scope = manual_routing.get("scope", {})
    turbo_seed_scope = turbo_seed.get("scope", {})
    flow_scope = flow_graph.get("scope", {})
    reference_frame_scope = reference_frame.get("scope", {})
    pet_openusd_scope = pet_openusd.get("scope", {})
    material_process_scope = material_process_routing.get("scope", {})
    porschefanatics_scope = porschefanatics_crosswalk.get("scope", {})
    visual_atlas_scope = visual_atlas.get("atlas", {})
    visual_atlas_output = visual_atlas.get("output", {})
    return {
        "catalog_part_records": count_json_files(ROOT / "catalog" / "parts"),
        "catalog_component_records": count_json_files(ROOT / "catalog" / "components"),
        "catalog_assembly_records": count_json_files(ROOT / "catalog" / "assemblies"),
        "registered_twin_zones": count_json_files(ROOT / "catalog" / "twins"),
        "catalogue_part_proxy_twins": len(catalogue_twins.get("twins", [])),
        "pet_documentary_twins": int(pet_scope.get("total_documentary_twins", 0)),
        "pet_unique_oem_references": int(pet_scope.get("unique_oem_references", 0)),
        "pet_part_master_twins": int(pet_scope.get("part_master_twins", 0)),
        "pet_records_with_proven_variants": int(pet_quality.get("records_with_proven_variants", 0)),
        "documented_variant_configuration_contracts": int(
            variant_scope.get("variant_configuration_count", 0)
        ),
        "complete_variant_boms": int(variant_scope.get("complete_variant_bom_count", 0)),
        "variant_assignment_links": int(variant_scope.get("variant_assignment_links", 0)),
        "pet_machine_bom_candidate_occurrences": int(
            variant_scope.get("machine_resolved_bom_candidate_occurrences", 0)
        ),
        "pet_machine_bom_candidate_vehicle_links": int(
            variant_scope.get("machine_resolved_bom_candidate_links", 0)
        ),
        "provisional_configuration_axis_contracts": int(
            variant_scope.get("provisional_configuration_axis_contracts", 0)
        ),
        "pet_summary_type_records": int(variant_scope.get("pet_summary_type_records", 0)),
        "pet_summary_configuration_candidates": int(
            variant_scope.get("pet_summary_configuration_candidates", 0)
        ),
        "pet_summary_configuration_gaps": int(
            variant_scope.get("pet_summary_configuration_gaps", 0)
        ),
        "single_dimension_part_constraint_occurrences": int(
            variant_scope.get("single_dimension_part_constraint_occurrences", 0)
        ),
        "resolved_configuration_part_constraint_occurrences": int(
            variant_scope.get("resolved_configuration_part_constraint_occurrences", 0)
        ),
        "configuration_part_candidate_links": int(
            variant_scope.get("configuration_part_candidate_links", 0)
        ),
        "configuration_exception_contracts": int(
            variant_scope.get("configuration_exception_contracts", 0)
        ),
        "mapped_configuration_exception_occurrences": int(
            variant_scope.get("mapped_configuration_exception_occurrences", 0)
        ),
        "fully_resolved_configuration_exceptions": int(
            variant_scope.get("fully_resolved_configuration_exceptions", 0)
        ),
        "pet_part_master_engineering_tasks": int(
            engineering_scope.get("engineering_tasks", 0)
        ),
        "pet_engineering_archetype_count": int(
            classification_audit.get("archetype_count", 0)
        ),
        "pet_tasks_with_lexical_archetype_hypothesis": int(
            engineering_scope.get("tasks_with_lexical_archetype_hypothesis", 0)
        ),
        "pet_tasks_with_system_fallback_archetype_hypothesis": int(
            engineering_scope.get(
                "tasks_with_system_fallback_archetype_hypothesis", 0
            )
        ),
        "pet_unclassified_archetype_routes": int(
            engineering_scope.get("unclassified_archetype_routes", 0)
        ),
        "pet_human_reviewed_archetype_classifications": int(
            engineering_scope.get("human_reviewed_archetype_classifications", 0)
        ),
        "pet_tasks_with_configuration_evidence": int(
            engineering_scope.get("tasks_with_configuration_evidence", 0)
        ),
        "pet_tasks_without_configuration_evidence": int(
            engineering_scope.get("tasks_without_configuration_evidence", 0)
        ),
        "pet_tasks_with_turbo_integration_evidence": int(
            engineering_scope.get("tasks_with_turbo_integration_evidence", 0)
        ),
        "pet_tasks_ready_for_editable_geometry_authoring": int(
            next_gate_counts.get("author_editable_geometry_and_measured_interfaces", 0)
        ),
        "pet_tasks_with_F1_envelope_identity_linked_unvalidated": int(
            fidelity_counts.get("F1_envelope_identity_linked_unvalidated", 0)
        ),
        "pet_tasks_with_exact_oem_F1_envelope_candidates": int(
            engineering_scope.get("tasks_with_exact_oem_F1_envelope_candidates", 0)
        ),
        "pet_tasks_with_F1_valve_dimensional_surrogate_unvalidated": int(
            engineering_scope.get("tasks_with_valve_dimensional_surrogate", 0)
        ),
        "pet_tasks_with_F1_k16_envelope_diameter_guides_unvalidated": int(
            engineering_scope.get("tasks_with_k16_envelope_flow_surrogate", 0)
        ),
        "pet_tasks_with_F1_charge_air_chain_guides_unvalidated": int(
            engineering_scope.get("tasks_with_charge_air_chain_surrogate", 0)
        ),
        "pet_tasks_with_F1_heat_shield_envelope_thermal_readiness_unvalidated": int(
            engineering_scope.get("tasks_with_heat_shield_thermal_surrogate", 0)
        ),
        "pet_tasks_with_F1_turbo_lubrication_control_topology_readiness_unvalidated": int(
            fidelity_counts.get(
                "F1_turbo_lubrication_control_topology_readiness_unvalidated", 0
            )
        ),
        "pet_tasks_with_F1_oil_tank_circuit_topology_readiness_unvalidated": int(
            fidelity_counts.get(
                "F1_oil_tank_circuit_topology_readiness_unvalidated", 0
            )
        ),
        "pet_tasks_with_F1_oil_cooler_circuit_topology_readiness_unvalidated": int(
            fidelity_counts.get(
                "F1_oil_cooler_circuit_topology_readiness_unvalidated", 0
            )
        ),
        "pet_tasks_with_F1_mass_constrained_structural_surrogate_virtual_F2_readiness": int(
            fidelity_counts.get(
                "F1_mass_constrained_structural_surrogate_virtual_F2_readiness", 0
            )
        ),
        "pet_tasks_ready_for_F2_interface_geometry": int(
            next_gate_counts.get("replace_F1_envelope_with_F2_interface_geometry", 0)
        ),
        "pet_tasks_ready_for_virtual_F2_interface_inference": int(
            next_gate_counts.get(
                "infer_and_cross_check_F2_interface_coordinates_with_uncertainty", 0
            )
        ),
        "pet_valve_tasks_ready_for_F2_interface_geometry": int(
            next_gate_counts.get(
                "replace_F1_valve_surrogate_with_F2_interface_geometry", 0
            )
        ),
        "pet_tasks_ready_for_202_16_topology_and_F2_interfaces": int(
            next_gate_counts.get(
                "resolve_202_16_configuration_topology_side_assignment_and_F2_interfaces",
                0,
            )
        ),
        "pet_tasks_ready_for_104_01_topology_F2_interfaces_and_oil_properties": int(
            next_gate_counts.get(
                "resolve_104_01_configuration_topology_F2_interfaces_and_oil_properties",
                0,
            )
        ),
        "pet_tasks_ready_for_104_05_topology_F2_interfaces_oil_air_properties_and_fan_control": int(
            next_gate_counts.get(
                "resolve_104_05_configuration_topology_F2_interfaces_oil_air_properties_and_fan_control",
                0,
            )
        ),
        "pet_tasks_with_F2_interface_geometry": int(
            engineering_readiness.get("F2_interface_geometry", 0)
        ),
        "pet_material_process_routing_tasks": int(
            material_process_scope.get("part_master_routing_tasks", 0)
        ),
        "pet_porschefanatics_exact_replacement_links": int(
            porschefanatics_scope.get("exact_pet_replacement_links", 0)
        ),
        "pet_part_masters_with_porschefanatics_exact_replacement_links": int(
            porschefanatics_scope.get("linked_pet_part_masters", 0)
        ),
        "pet_porschefanatics_qualified_material_basis_links": int(
            porschefanatics_scope.get("links_with_qualified_material_basis", 0)
        ),
        "pet_material_process_archetype_profiles": int(
            material_process_scope.get("archetype_profiles", 0)
        ),
        "pet_tasks_with_additive_route_candidate": int(
            material_process_scope.get("tasks_with_additive_route_candidate", 0)
        ),
        "pet_tasks_with_titanium_family_candidate": int(
            material_process_scope.get("tasks_with_titanium_family_candidate", 0)
        ),
        "pet_selected_materials": int(
            material_process_scope.get("selected_materials", 0)
        ),
        "pet_selected_manufacturing_routes": int(
            material_process_scope.get("selected_manufacturing_routes", 0)
        ),
        "vehicle_reference_frame_sourced_dimensions": int(
            reference_frame_scope.get("sourced_dimensions", 0)
        ),
        "vehicle_reference_frame_sourced_mass_constraints": int(
            reference_frame_scope.get("sourced_mass_constraints", 0)
        ),
        "vehicle_reference_frame_curve_prims": int(
            reference_frame_scope.get("reference_curve_prims", 0)
        ),
        "vehicle_reference_frame_positioned_parts": int(
            reference_frame_scope.get("positioned_vehicle_parts", 0)
        ),
        "pet_tasks_with_workshop_manual_candidates": int(
            engineering_scope.get("tasks_with_workshop_manual_candidates", 0)
        ),
        "workshop_manual_candidate_links": int(
            engineering_scope.get("workshop_manual_candidate_links", 0)
        ),
        "workshop_manual_records": int(manual_scope.get("manual_records", 0)),
        "workshop_manual_system_routed_records": int(
            manual_scope.get("system_routed_records", 0)
        ),
        "workshop_manual_unresolved_system_records": int(
            manual_scope.get("unresolved_system_records", 0)
        ),
        "workshop_manual_part_review_candidate_records": int(
            manual_scope.get("part_review_candidate_records", 0)
        ),
        "promoted_workshop_manual_measurements_or_torques": int(
            manual_scope.get("promoted_part_measurements_or_torques", 0)
        ),
        "pet_tasks_with_linked_catalog_part_engineering_records": int(
            engineering_scope.get(
                "tasks_with_linked_catalog_part_engineering_records", 0
            )
        ),
        "linked_catalog_part_engineering_record_links": int(
            engineering_scope.get("linked_catalog_part_engineering_record_links", 0)
        ),
        "pet_tasks_with_linked_simulation_evidence": int(
            engineering_scope.get("tasks_with_linked_simulation_evidence", 0)
        ),
        "linked_simulation_evidence_record_links": int(
            engineering_scope.get("linked_simulation_evidence_record_links", 0)
        ),
        "pet_tasks_with_virtual_F2_readiness_contract": int(
            engineering_scope.get("tasks_with_virtual_F2_readiness_contract", 0)
        ),
        "virtual_F2_readiness_contract_links": int(
            engineering_scope.get("virtual_F2_readiness_contract_links", 0)
        ),
        "pet_tasks_with_mass_constrained_structural_surrogate": int(
            engineering_scope.get(
                "tasks_with_mass_constrained_structural_surrogate", 0
            )
        ),
        "mass_constrained_structural_surrogate_component_credits": int(
            engineering_scope.get(
                "mass_constrained_structural_surrogate_component_credits", 0
            )
        ),
        "pet_tasks_with_valve_dimensional_surrogate": int(
            engineering_scope.get("tasks_with_valve_dimensional_surrogate", 0)
        ),
        "valve_dimensional_surrogate_component_CAE_credits": int(
            engineering_scope.get(
                "valve_dimensional_surrogate_component_CAE_credits", 0
            )
        ),
        "pet_tasks_with_k16_envelope_flow_surrogate": int(
            engineering_scope.get("tasks_with_k16_envelope_flow_surrogate", 0)
        ),
        "k16_envelope_flow_surrogate_links": int(
            engineering_scope.get("k16_envelope_flow_surrogate_links", 0)
        ),
        "k16_evaluated_zeroD_operating_points": int(
            engineering_scope.get("k16_evaluated_zeroD_operating_points", 0)
        ),
        "k16_envelope_flow_surrogate_component_CAE_credits": int(
            engineering_scope.get(
                "k16_envelope_flow_surrogate_component_CAE_credits", 0
            )
        ),
        "pet_tasks_with_charge_air_chain_surrogate": int(
            engineering_scope.get("tasks_with_charge_air_chain_surrogate", 0)
        ),
        "charge_air_chain_surrogate_links": int(
            engineering_scope.get("charge_air_chain_surrogate_links", 0)
        ),
        "charge_air_evaluated_zeroD_operating_points": int(
            engineering_scope.get("charge_air_evaluated_zeroD_operating_points", 0)
        ),
        "charge_air_chain_surrogate_component_CAE_credits": int(
            engineering_scope.get(
                "charge_air_chain_surrogate_component_CAE_credits", 0
            )
        ),
        "pet_tasks_with_heat_shield_thermal_surrogate": int(
            engineering_scope.get("tasks_with_heat_shield_thermal_surrogate", 0)
        ),
        "heat_shield_thermal_surrogate_links": int(
            engineering_scope.get("heat_shield_thermal_surrogate_links", 0)
        ),
        "heat_shield_evaluated_thermal_operating_points": int(
            engineering_scope.get("heat_shield_evaluated_thermal_operating_points", 0)
        ),
        "heat_shield_thermal_surrogate_component_CAE_credits": int(
            engineering_scope.get(
                "heat_shield_thermal_surrogate_component_CAE_credits", 0
            )
        ),
        "pet_tasks_with_turbo_lubrication_control_topology_contract": int(
            engineering_scope.get(
                "tasks_with_turbo_lubrication_control_topology_contract", 0
            )
        ),
        "turbo_lubrication_control_topology_links": int(
            engineering_scope.get("turbo_lubrication_control_topology_links", 0)
        ),
        "turbo_lubrication_control_symbolic_equations": int(
            engineering_scope.get("turbo_lubrication_control_symbolic_equations", 0)
        ),
        "turbo_lubrication_control_blocked_load_cases": int(
            engineering_scope.get("turbo_lubrication_control_blocked_load_cases", 0)
        ),
        "turbo_lubrication_control_component_CAE_credits": int(
            engineering_scope.get("turbo_lubrication_control_component_CAE_credits", 0)
        ),
        "promoted_linked_reference_solver_physicsnemo_simready_or_manufacturing_results": int(
            engineering_scope.get(
                "promoted_linked_reference_solver_physicsnemo_simready_or_manufacturing_results",
                0,
            )
        ),
        "turbo_integration_seed_candidate_occurrences": int(
            turbo_seed_scope.get("candidate_occurrences", 0)
        ),
        "turbo_integration_seed_candidate_part_masters": int(
            turbo_seed_scope.get("candidate_part_masters", 0)
        ),
        "turbo_integration_seed_human_read_occurrences": int(
            turbo_seed_scope.get("human_read_variant_occurrences", 0)
        ),
        "turbo_integration_seed_configured_bom_entries": int(
            turbo_seed_scope.get("configured_vehicle_bom_entries", 0)
        ),
        "functional_flow_types": int(flow_scope.get("flow_type_count", 0)),
        "functional_flow_edges": int(flow_scope.get("flow_edge_count", 0)),
        "functional_flow_work_package_bindings": int(
            flow_scope.get("work_package_bindings", 0)
        ),
        "virtual_mission_contracts": int(
            flow_scope.get("virtual_mission_contracts", 0)
        ),
        "closed_multiphysics_balance_equations": int(
            flow_scope.get("closed_balance_equations", 0)
        ),
        "passed_virtual_vehicle_missions": int(
            flow_scope.get("passed_virtual_missions", 0)
        ),
        "pet_openusd_part_master_prims": int(
            pet_openusd_scope.get("part_master_prims", 0)
        ),
        "pet_openusd_shard_layers": int(
            pet_openusd_scope.get("shard_layer_count", 0)
        ),
        "pet_openusd_system_membership_links": int(
            pet_openusd_scope.get("system_membership_links", 0)
        ),
        "pet_openusd_masters_with_exact_oem_proxy_candidate": int(
            pet_openusd_scope.get("with_exact_oem_proxy_candidate", 0)
        ),
        "pet_openusd_exact_oem_proxy_candidate_links": int(
            pet_openusd_scope.get("exact_oem_proxy_candidate_links", 0)
        ),
        "pet_openusd_geometry_prims": int(
            pet_openusd_scope.get("geometry_prim_count", 0)
        ),
        "pet_openusd_simready_validated_prims": int(
            pet_openusd_scope.get("simready_validated", 0)
        ),
        "pet_visual_proxy_instances": int(
            visual_atlas_scope.get("part_master_proxy_instances", 0)
        ),
        "pet_visual_proxy_catalogue_coverage_ratio": float(
            visual_atlas_scope.get("catalogue_master_coverage_ratio", 0.0)
        ),
        "pet_visual_proxy_archetype_prototypes": int(
            visual_atlas_scope.get("archetype_prototypes", 0)
        ),
        "pet_visual_proxy_system_groups": int(
            visual_atlas_scope.get("system_groups", 0)
        ),
        "pet_visual_proxy_shard_layers": int(
            visual_atlas_scope.get("shard_layers", 0)
        ),
        "pet_visual_proxy_engineering_geometry": int(
            visual_atlas_scope.get("engineering_geometry_count", 0)
        ),
        "pet_visual_proxy_positioned_vehicle_parts": int(
            visual_atlas_scope.get("positioned_vehicle_part_count", 0)
        ),
        "pet_catalogue_digital_twin_composed_stages": int(
            isinstance(
                visual_atlas_output.get("composed_catalogue_digital_twin_stage"),
                str,
            )
        ),
        "pet_visual_proxy_simready_validated": int(
            visual_atlas.get("validation", {}).get("simready_validated") is True
        ),
        "pet_catalogue_openusd_strict_validated_root_stages": int(
            visual_openusd_validation.get("scope", {}).get("validated_root_stages", 0)
        ),
        "pet_catalogue_openusd_validation_passes": int(
            visual_openusd_validation.get("status")
            == "passed_openusd_strict_not_simready"
        ),
        "pet_catalogue_openusd_composition_resolution_passes": int(
            visual_openusd_validation.get("results", {}).get("composition_resolution")
            == "passed"
        ),
        "functional_flow_openusd_f0_stages": int(
            flow_openusd.get("stage", {}).get("format") == "OpenUSD_ASCII"
        ),
        "functional_flow_openusd_system_markers": int(
            flow_openusd.get("stage", {}).get("system_marker_count", 0)
        ),
        "functional_flow_openusd_curves": int(
            flow_openusd.get("stage", {}).get("flow_curve_count", 0)
        ),
        "functional_flow_simready_preflight_passes": int(
            flow_preflight.get("status") == "ready"
        ),
        "reference_cae_cases_passed_for_catalogue_parts": 0,
        "physicsnemo_models_trained_for_993_vehicle": 0,
        "simready_993_vehicle_assets": 0,
        "functional_manufacturing_releases": 0,
    }


def build_work_package(
    system: dict[str, Any], illustration: dict[str, Any], route: dict[str, Any]
) -> dict[str, Any]:
    illustration_id = str(illustration["illustration"])
    return {
        "work_package_id": f"WP-993-{illustration_id}",
        "system_id": system["system_id"],
        "catalogue_illustration": illustration_id,
        "catalogue_reference_count_aggregate": int(illustration["reference_count"]),
        "catalogue_labels": illustration.get("labels", []),
        "catalogue_semantics": "aggregate_reference_rows_not_mounted_part_instances",
        "current_fidelity": "F0_reference",
        "current_status": "inventory_only",
        "criticality": route["criticality"],
        "simulation_domain_ids": route["simulation_domains"],
        "evidence_state": {
            "individual_identity_and_variant_selection": "missing",
            "editable_geometry": "missing",
            "vehicle_transform": "missing",
            "interfaces_and_tolerances": "missing",
            "qualified_material": "missing",
            "loads_and_boundary_conditions": "missing",
            "reference_solver_result": "not_run",
            "physicsnemo_result": "not_run",
            "omniverse_simready_result": "not_run",
            "physical_correlation": "unavailable_by_program_constraint",
        },
        "decisions": {
            "material": None,
            "manufacturing_route": None,
            "functional_release": False,
        },
    }


def build_program() -> dict[str, Any]:
    skeleton = load_json(SKELETON)
    definition = load_json(DEFINITION)
    validate_definition(skeleton, definition)
    variant_contract = (
        load_json(VARIANT_CONFIGURATIONS)
        if VARIANT_CONFIGURATIONS.is_file()
        else {"strategy": {}, "scope": {}}
    )
    engineering_readiness = (
        load_json(PET_ENGINEERING_READINESS)
        if PET_ENGINEERING_READINESS.is_file()
        else {"scope": {}, "coverage": {}, "classification_audit": {}}
    )
    material_process_routing = (
        load_json(PET_MATERIAL_PROCESS_ROUTING)
        if PET_MATERIAL_PROCESS_ROUTING.is_file()
        else {"source_boundary": {}, "scope": {}, "coverage": {}, "claim_boundary": {}}
    )
    porschefanatics_crosswalk = (
        load_json(PET_PORSCHEFANATICS_CROSSWALK)
        if PET_PORSCHEFANATICS_CROSSWALK.is_file()
        else {"source_boundary": {}, "scope": {}, "coverage": {}, "claim_boundary": {}}
    )
    turbo_seed = (
        load_json(TURBO_INTEGRATION_SEED)
        if TURBO_INTEGRATION_SEED.is_file()
        else {"integration_target": {}, "scope": {}, "coverage": {}, "assembly_gates": {}}
    )
    flow_graph = (
        load_json(FUNCTIONAL_FLOW_GRAPH)
        if FUNCTIONAL_FLOW_GRAPH.is_file()
        else {"scope": {}, "flow_types": {}, "flow_edges": [], "virtual_missions": [], "assembly_readiness": {}}
    )
    flow_openusd = (
        load_json(FUNCTIONAL_FLOW_OPENUSD)
        if FUNCTIONAL_FLOW_OPENUSD.is_file()
        else {"stage": {}, "validation": {}, "claim_boundary": {}}
    )
    flow_preflight = (
        load_json(FUNCTIONAL_FLOW_SIMREADY_PREFLIGHT)
        if FUNCTIONAL_FLOW_SIMREADY_PREFLIGHT.is_file()
        else {"status": "missing", "blockers": [], "result_boundary": {}}
    )
    reference_frame = (
        load_json(VEHICLE_REFERENCE_FRAME)
        if VEHICLE_REFERENCE_FRAME.is_file()
        else {
            "source_boundary": {},
            "scope": {},
            "stage": {},
            "validation": {},
            "claim_boundary": {},
        }
    )
    pet_openusd = (
        load_json(PET_OPENUSD_FEDERATION)
        if PET_OPENUSD_FEDERATION.is_file()
        else {"output": {}, "scope": {}, "validation": {}, "claim_boundary": {}}
    )
    visual_atlas = (
        load_json(PET_VISUAL_PROXY_ATLAS)
        if PET_VISUAL_PROXY_ATLAS.is_file()
        else {
            "atlas": {},
            "output": {},
            "physicsnemo_dataset_boundary": {},
            "validation": {},
            "claim_boundary": {},
        }
    )
    visual_openusd_validation = (
        load_json(PET_VISUAL_PROXY_OPENUSD_VALIDATION)
        if PET_VISUAL_PROXY_OPENUSD_VALIDATION.is_file()
        else {"status": "missing", "source": {}, "scope": {}, "results": {}, "claim_boundary": {}}
    )

    engineering_scope = engineering_readiness.get("scope", {})
    classification_audit = engineering_readiness.get("classification_audit", {})
    lexical_routes = int(
        engineering_scope.get("tasks_with_lexical_archetype_hypothesis", 0)
    )
    system_fallback_routes = int(
        engineering_scope.get(
            "tasks_with_system_fallback_archetype_hypothesis", 0
        )
    )
    if lexical_routes + system_fallback_routes != int(
        engineering_scope.get("engineering_tasks", -1)
    ):
        raise ValueError("PET archetype routing partition does not close")
    if engineering_scope.get("unclassified_archetype_routes") != 0:
        raise ValueError("PET archetype routing still contains unclassified routes")
    if engineering_scope.get("human_reviewed_archetype_classifications") != 0:
        raise ValueError("machine archetype hypotheses cannot be promoted as human reviewed")
    classification_policy = classification_audit.get("policy", {})
    if classification_policy.get("description_keywords_are_hypotheses") is not True:
        raise ValueError("lexical archetype routes must remain hypotheses")
    if classification_policy.get("system_fallback_is_part_classification") is not False:
        raise ValueError("system fallback cannot be promoted as part classification")
    if classification_policy.get("simulation_domain_route_is_solver_result") is not False:
        raise ValueError("simulation routing cannot be promoted as a solver result")
    if classification_policy.get("manual_or_geometry_review_required") is not True:
        raise ValueError("archetype classification must require manual or geometry review")

    material_process_scope = material_process_routing.get("scope", {})
    porschefanatics_scope = porschefanatics_crosswalk.get("scope", {})
    if porschefanatics_crosswalk.get("source_boundary", {}).get(
        "engineering_readiness_index_sha256"
    ) != sha256_file(PET_ENGINEERING_READINESS):
        raise ValueError("PorscheFanatics crosswalk is stale against engineering readiness")
    if porschefanatics_scope.get("exact_pet_replacement_links") != 6:
        raise ValueError("PorscheFanatics exact replacement link count does not close")
    if porschefanatics_scope.get("linked_pet_part_masters") != 2:
        raise ValueError("PorscheFanatics linked PET master count does not close")
    if porschefanatics_scope.get("links_with_qualified_material_basis") != 0:
        raise ValueError("PorscheFanatics commercial materials cannot be promoted")
    if any(
        value is not False
        for value in porschefanatics_crosswalk.get("claim_boundary", {}).values()
    ):
        raise ValueError("PorscheFanatics crosswalk claim boundary must fail closed")
    if material_process_scope.get("part_master_routing_tasks") != engineering_scope.get(
        "engineering_tasks"
    ):
        raise ValueError("material-process routing does not cover every PET engineering task")
    if material_process_scope.get("selected_materials") != 0:
        raise ValueError("material candidate routing cannot select materials")
    if material_process_scope.get("selected_manufacturing_routes") != 0:
        raise ValueError("manufacturing candidate routing cannot select processes")
    if material_process_routing.get("source_boundary", {}).get(
        "engineering_readiness_index_sha256"
    ) != sha256_file(PET_ENGINEERING_READINESS):
        raise ValueError("material-process routing is stale against engineering readiness")
    if material_process_routing.get("source_boundary", {}).get(
        "porschefanatics_crosswalk_sha256"
    ) != sha256_file(PET_PORSCHEFANATICS_CROSSWALK):
        raise ValueError("material-process routing is stale against PorscheFanatics crosswalk")
    if any(
        value is not False
        for value in material_process_routing.get("claim_boundary", {}).values()
    ):
        raise ValueError("material-process routing claim boundary must fail closed")

    visual_scope = visual_atlas.get("atlas", {})
    if visual_scope.get("part_master_proxy_instances") != pet_openusd.get("scope", {}).get(
        "part_master_prims"
    ):
        raise ValueError("visual proxy coverage does not match PET part-master coverage")
    if visual_scope.get("catalogue_master_coverage_ratio") != 1.0:
        raise ValueError("visual proxy atlas does not cover the complete PET master catalogue")
    if visual_scope.get("engineering_geometry_count") != 0:
        raise ValueError("visual proxy symbols cannot be promoted as engineering geometry")
    if any(value is not False for value in visual_atlas.get("claim_boundary", {}).values()):
        raise ValueError("visual proxy atlas claim boundary must fail closed")
    if visual_openusd_validation.get("status") != "passed_openusd_strict_not_simready":
        raise ValueError("visual proxy atlas lacks strict OpenUSD validation")
    if visual_openusd_validation.get("source", {}).get(
        "atlas_manifest_sha256"
    ) != sha256_file(PET_VISUAL_PROXY_ATLAS):
        raise ValueError("visual proxy OpenUSD validation is stale")
    if visual_openusd_validation.get("results", {}).get("composition_resolution") != "passed":
        raise ValueError("visual proxy OpenUSD composition did not resolve")
    if visual_openusd_validation.get("results", {}).get("simready_validated") is not False:
        raise ValueError("OpenUSD validation cannot be promoted to SimReady")
    if any(
        value is not False
        for value in visual_openusd_validation.get("claim_boundary", {}).values()
    ):
        raise ValueError("OpenUSD validation claim boundary must fail closed")

    reference_frame_scope = reference_frame.get("scope", {})
    if reference_frame.get("source_boundary", {}).get(
        "reference_envelope_sha256"
    ) != sha256_file(TWIN_REFERENCE_ENVELOPE):
        raise ValueError("vehicle reference frame is stale against reference envelope")
    if reference_frame.get("stage", {}).get("sha256") != sha256_file(
        VEHICLE_REFERENCE_FRAME_USD
    ):
        raise ValueError("vehicle reference frame USD is stale")
    if reference_frame_scope.get("sourced_dimensions") != 7:
        raise ValueError("vehicle reference frame must retain seven sourced dimensions")
    if reference_frame_scope.get("sourced_mass_constraints") != 4:
        raise ValueError("vehicle reference frame must retain four sourced mass constraints")
    if reference_frame_scope.get("positioned_vehicle_parts") != 0:
        raise ValueError("reference frame cannot promote positioned vehicle parts")
    if reference_frame.get("validation", {}).get("minimum_usd_validation") != (
        "not_run_preflight_blocked"
    ):
        raise ValueError("reference frame must preserve the SimReady preflight guardrail")
    if any(
        value is not False
        for value in reference_frame.get("claim_boundary", {}).values()
    ):
        raise ValueError("vehicle reference frame claim boundary must fail closed")

    route_by_id = {route["system_id"]: route for route in definition["system_routes"]}
    systems: list[dict[str, Any]] = []
    all_packages: list[dict[str, Any]] = []
    for system in skeleton["systems"]:
        route = route_by_id[system["system_id"]]
        packages = [build_work_package(system, item, route) for item in system["illustrations"]]
        all_packages.extend(packages)
        systems.append(
            {
                "system_id": system["system_id"],
                "name": system["name"],
                "catalogue_reference_count_aggregate": int(system["reference_count"]),
                "work_package_count": len(packages),
                "criticality": route["criticality"],
                "simulation_domain_ids": route["simulation_domains"],
                "integration_interfaces": route["integration_interfaces"],
                "current_status": "inventory_only",
                "work_packages": packages,
            }
        )

    illustration_total = sum(len(system["illustrations"]) for system in skeleton["systems"])
    if illustration_total != len(all_packages):
        raise ValueError("generated work-package count does not close")

    gates = definition["integration_gates"]
    documentary_passes = sum(gate["current_status"].startswith("pass_") for gate in gates)
    return {
        "$comment": (
            "Programme F0 genere depuis le squelette PET agrege. Les comptes couvrent le catalogue, "
            "pas la nomenclature d'une voiture configuree; tous les lots restent des inventaires virtuels."
        ),
        "schema_version": definition["schema_version"],
        "generated_by": relative(Path(__file__).resolve()),
        "sources": {
            "assembly_skeleton": relative(SKELETON),
            "program_definition": relative(DEFINITION),
            "catalogue_part_twin_index": relative(CATALOGUE_TWIN_INDEX),
            "pet_documentary_twin_index": relative(PET_TWIN_INDEX),
            "variant_configuration_contract": relative(VARIANT_CONFIGURATIONS),
            "configuration_axis_contract": relative(CONFIGURATION_AXES),
            "configuration_roster": relative(CONFIGURATION_ROSTER),
            "configuration_part_links": relative(CONFIGURATION_PART_LINKS),
            "configuration_exceptions": relative(CONFIGURATION_EXCEPTIONS),
            "pet_applicability_evidence": relative(APPLICABILITY_EVIDENCE),
            "pet_engineering_readiness": relative(PET_ENGINEERING_READINESS),
            "pet_porschefanatics_crosswalk": relative(
                PET_PORSCHEFANATICS_CROSSWALK
            ),
            "pet_material_process_routing": relative(PET_MATERIAL_PROCESS_ROUTING),
            "pet_openusd_federation": relative(PET_OPENUSD_FEDERATION),
            "pet_visual_proxy_atlas": relative(PET_VISUAL_PROXY_ATLAS),
            "pet_visual_proxy_openusd_validation": relative(
                PET_VISUAL_PROXY_OPENUSD_VALIDATION
            ),
            "workshop_manual_evidence_routing": relative(MANUAL_EVIDENCE_ROUTING),
            "turbo_integration_seed": relative(TURBO_INTEGRATION_SEED),
            "functional_flow_graph": relative(FUNCTIONAL_FLOW_GRAPH),
            "functional_flow_openusd": relative(FUNCTIONAL_FLOW_OPENUSD),
            "functional_flow_simready_preflight": relative(
                FUNCTIONAL_FLOW_SIMREADY_PREFLIGHT
            ),
            "vehicle_reference_frame": relative(VEHICLE_REFERENCE_FRAME),
            "vehicle_reference_frame_openusd": relative(
                VEHICLE_REFERENCE_FRAME_USD
            ),
        },
        "program_id": definition["program_id"],
        "vehicle": definition["vehicle"],
        "catalogue_scope": {
            "generation": skeleton["generation"],
            "reference_count_aggregate": int(skeleton["reference_count"]),
            "system_count": len(systems),
            "illustration_work_package_count": len(all_packages),
            "configured_vehicle_bom_count": 0,
            "warning": (
                "Les references agregees melangent variantes, millesimes, carrosseries, transmissions, "
                "options et quantites; elles ne sont pas les pieces montees sur un vehicule."
            ),
        },
        "inventory": inventory(),
        "variant_configuration": {
            "strategy": variant_contract.get("strategy", {}),
            "scope": variant_contract.get("scope", {}),
            "catalogue_configuration_universe": variant_contract.get(
                "catalogue_configuration_universe", {}
            ),
        },
        "pet_archetype_classification": {
            "contract": relative(PET_ENGINEERING_READINESS),
            "scope": {
                "part_master_routes": int(
                    classification_audit.get("part_master_routes", 0)
                ),
                "lexical_hypothesis_routes": lexical_routes,
                "system_context_only_fallback_routes": system_fallback_routes,
                "unclassified_routes": int(
                    engineering_scope.get("unclassified_archetype_routes", 0)
                ),
                "human_reviewed_routes": int(
                    engineering_scope.get(
                        "human_reviewed_archetype_classifications", 0
                    )
                ),
            },
            "audit": classification_audit,
            "coverage": {
                "tasks_by_engineering_archetype": engineering_readiness.get(
                    "coverage", {}
                ).get("tasks_by_engineering_archetype", {}),
                "tasks_by_classification_rule": engineering_readiness.get(
                    "coverage", {}
                ).get("tasks_by_classification_rule", {}),
                "tasks_by_classification_confidence": engineering_readiness.get(
                    "coverage", {}
                ).get("tasks_by_classification_confidence", {}),
                "tasks_by_classification_evidence_kind": engineering_readiness.get(
                    "coverage", {}
                ).get("tasks_by_classification_evidence_kind", {}),
            },
        },
        "pet_material_process_routing": {
            "contract": relative(PET_MATERIAL_PROCESS_ROUTING),
            "scope": material_process_scope,
            "coverage": material_process_routing.get("coverage", {}),
            "profile_registry": material_process_routing.get(
                "profile_registry", {}
            ),
            "selection_policy": material_process_routing.get(
                "selection_policy", {}
            ),
            "physicsnemo_boundary": material_process_routing.get(
                "physicsnemo_boundary", {}
            ),
            "claim_boundary": material_process_routing.get(
                "claim_boundary", {}
            ),
        },
        "pet_porschefanatics_crosswalk": {
            "contract": relative(PET_PORSCHEFANATICS_CROSSWALK),
            "scope": porschefanatics_scope,
            "coverage": porschefanatics_crosswalk.get("coverage", {}),
            "claim_boundary": porschefanatics_crosswalk.get(
                "claim_boundary", {}
            ),
        },
        "first_vehicle_integration_seed": {
            "contract": relative(TURBO_INTEGRATION_SEED),
            "integration_target": turbo_seed.get("integration_target", {}),
            "scope": turbo_seed.get("scope", {}),
            "coverage": turbo_seed.get("coverage", {}),
            "assembly_gates": turbo_seed.get("assembly_gates", {}),
        },
        "functional_flow_integration": {
            "contract": relative(FUNCTIONAL_FLOW_GRAPH),
            "scope": flow_graph.get("scope", {}),
            "flow_types": flow_graph.get("flow_types", {}),
            "flow_edges": flow_graph.get("flow_edges", []),
            "virtual_missions": flow_graph.get("virtual_missions", []),
            "assembly_readiness": flow_graph.get("assembly_readiness", {}),
            "openusd_f0": {
                "contract": relative(FUNCTIONAL_FLOW_OPENUSD),
                "stage": flow_openusd.get("stage", {}),
                "validation": flow_openusd.get("validation", {}),
                "claim_boundary": flow_openusd.get("claim_boundary", {}),
            },
            "simready_preflight": {
                "contract": relative(FUNCTIONAL_FLOW_SIMREADY_PREFLIGHT),
                "status": flow_preflight.get("status"),
                "blockers": flow_preflight.get("blockers", []),
                "result_boundary": flow_preflight.get("result_boundary", {}),
            },
        },
        "vehicle_reference_frame": {
            "contract": relative(VEHICLE_REFERENCE_FRAME),
            "stage": reference_frame.get("stage", {}),
            "scope": reference_frame_scope,
            "mathematical_sanity_checks": reference_frame.get(
                "mathematical_sanity_checks", {}
            ),
            "documented_mass_constraints": reference_frame.get(
                "documented_mass_constraints", {}
            ),
            "uncertainty_boundary": reference_frame.get(
                "uncertainty_boundary", {}
            ),
            "validation": reference_frame.get("validation", {}),
            "claim_boundary": reference_frame.get("claim_boundary", {}),
        },
        "pet_openusd_federation": {
            "contract": relative(PET_OPENUSD_FEDERATION),
            "output": pet_openusd.get("output", {}),
            "scope": pet_openusd.get("scope", {}),
            "validation": pet_openusd.get("validation", {}),
            "claim_boundary": pet_openusd.get("claim_boundary", {}),
            "proxy_linkage": pet_openusd.get("proxy_linkage", {}),
        },
        "pet_catalogue_visual_twin": {
            "contract": relative(PET_VISUAL_PROXY_ATLAS),
            "atlas": visual_atlas.get("atlas", {}),
            "output": visual_atlas.get("output", {}),
            "physicsnemo_dataset_boundary": visual_atlas.get(
                "physicsnemo_dataset_boundary", {}
            ),
            "validation": visual_atlas.get("validation", {}),
            "claim_boundary": visual_atlas.get("claim_boundary", {}),
            "openusd_validation": {
                "contract": relative(PET_VISUAL_PROXY_OPENUSD_VALIDATION),
                "status": visual_openusd_validation.get("status"),
                "validator": visual_openusd_validation.get("validator", {}),
                "scope": visual_openusd_validation.get("scope", {}),
                "results": visual_openusd_validation.get("results", {}),
                "claim_boundary": visual_openusd_validation.get(
                    "claim_boundary", {}
                ),
            },
        },
        "readiness": {
            "documentary_gates_passed": documentary_passes,
            "integration_gate_count": len(gates),
            "F2_work_packages": 0,
            "F3_work_packages": 0,
            "reference_simulation_work_packages": 0,
            "physicsnemo_surrogate_work_packages": 0,
            "integrated_vehicle_systems": 0,
            "functioning_vehicle_claim": False,
        },
        "claim_policy": definition["claim_policy"],
        "llm_policy": definition["llm_policy"],
        "material_selection_policy": definition["material_selection_policy"],
        "manufacturing_policy": definition["manufacturing_policy"],
        "engineering_workstreams": definition["engineering_workstreams"],
        "simulation_domains": definition["simulation_domains"],
        "physicsnemo_policy": definition["physicsnemo_policy"],
        "omniverse_policy": definition["omniverse_policy"],
        "integration_gates": gates,
        "systems": systems,
    }


def render(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def run(*, write: bool) -> int:
    expected = render(build_program())
    if write:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(expected, encoding="utf-8")
        print(f"wrote {relative(OUTPUT)}")
        return 0
    if not OUTPUT.is_file():
        print(f"missing generated program: {relative(OUTPUT)}", file=sys.stderr)
        return 1
    if OUTPUT.read_text(encoding="utf-8") != expected:
        print(f"stale generated program: {relative(OUTPUT)}", file=sys.stderr)
        return 1
    print(f"current {relative(OUTPUT)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="write the generated F0 program")
    mode.add_argument("--check", action="store_true", help="check the committed program is current")
    args = parser.parse_args(argv)
    return run(write=args.write)


if __name__ == "__main__":
    raise SystemExit(main())
