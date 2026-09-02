#!/usr/bin/env python3
"""Construit le contrat CAO parametrique dual-variant F28 sans geometrie."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_RELATIVE_PATH = Path(
    "twins/reference-917-engine/dual-variant-parametric-cad-contract-f28.json"
)
NA_VARIANT = "type_912_5_0_na"
TURBO_VARIANT = "917_30_1973_turbo_5374"
REPORTED_POWER_FACT_VARIANT = "917_30_1600_hp_reported_qualifying_target"
TARGET_VARIANTS = (NA_VARIANT, TURBO_VARIANT)

# La validation consomme directement ce tuple canonique. UPSTREAMS est une vue
# en lecture seule : modifier une table de travail ne peut pas rebinder un
# fichier amont modifie.
_CANONICAL_UPSTREAM_BINDINGS = (
    ("classical_solver_facts_f13", "twins/reference-917-engine/classical-solver-cases-f13.json", "add18d3c64ad481d20052fd6b6a3b0db773bb67ad534831b23dd11c996d0a08b", "documentary_fact_records_only_not_design_dimensions", True),
    ("kinematic_interfaces_f16", "twins/reference-917-engine/kinematic-interface-readiness-f16.json", "ec5e56cdd750071462e00dcec978182916ee4c266435bfea0720dea2fda2f2e2", "family_cardinality_and_null_datum_policy_only", True),
    ("manufacturing_routing_f19", "twins/reference-917-engine/manufacturing-routing-f19.json", "f9fc00c4f51840bb5781ffc21078f7e30febecd6bef202e32e882f0da3130d6f", "all_family_route_classes_and_requirement_taxonomy_not_selection", True),
    ("dual_variant_functional_readiness_f24", "twins/reference-917-engine/dual-variant-functional-readiness-f24.json", "27fd052a45e051f75836e4116255a655f760b1d36c600a14778eb69fed0a7d5b", "canonical_variant_ids_and_documentary_fact_crosswalk_only", True),
    ("physical_metrology_campaign_f27", "twins/reference-917-engine/physical-metrology-campaign-f27.template.json", "9d2157383f50a0e3b4db76c49b9ef8ad9ab2aec56ff60e95efe388ea4d90a822", "blank_measurement_and_review_slots_only", True),
    ("variant_visualization_f10", "twins/reference-917-engine/variant-configurations-f10.json", "dfb6ee25f367c934b11ff020e34d9d77296d2b5a535030a73221696af7c7a640", "excluded_lineage_check_no_dimensions_solids_or_transforms", False),
    ("valvetrain_flow_f20", "twins/reference-917-engine/valvetrain-flow-inputs-f20.json", "4f5e1eee41711d9012f703211fa44de053dd0f266fc7f41ee001b2273c12136c", "excluded_lineage_check_no_dimensions_solids_or_transforms", False),
    ("parametric_cad_f22", "twins/reference-917-engine/parametric-cad-assembly-contract-f22.json", "5086429d0514d7206083bda450bd271b74406f249b58f60aa365c16f1f6b2144", "excluded_lineage_check_no_dimensions_solids_or_transforms", False),
)
UPSTREAMS = MappingProxyType(
    {
        source_id: MappingProxyType(
            {
                "path": path,
                "sha256": digest,
                "reuse_scope": scope,
                "primary_contract_input": primary,
            }
        )
        for source_id, path, digest, scope, primary in _CANONICAL_UPSTREAM_BINDINGS
    }
)
PRIMARY_UPSTREAMS = frozenset(
    source_id
    for source_id, _path, _digest, _scope, primary in _CANONICAL_UPSTREAM_BINDINGS
    if primary
)
EXCLUDED_GEOMETRY_UPSTREAMS = frozenset(
    {"variant_visualization_f10", "valvetrain_flow_f20", "parametric_cad_f22"}
)

_CANONICAL_FACTS = MappingProxyType(
    {
        "FACT-50-BORE": MappingProxyType({"quantity": "cylinder_bore", "variant": "type_912_5_0_na", "kind": "published_point", "value": 86.8, "unit": "mm", "usage": "candidate_only", "source_refs": ("SRC-AMS-917-ENGINE-TECHNICAL-ANALYSIS",)}),
        "FACT-50-STROKE": MappingProxyType({"quantity": "piston_stroke", "variant": "type_912_5_0_na", "kind": "published_point", "value": 70.4, "unit": "mm", "usage": "candidate_only", "source_refs": ("SRC-AMS-917-ENGINE-TECHNICAL-ANALYSIS",)}),
        "FACT-5374-BORE": MappingProxyType({"quantity": "cylinder_bore", "variant": "917_30_turbo_5374", "kind": "published_point", "value": 90.0, "unit": "mm", "usage": "candidate_only", "source_refs": ("SRC-AMS-917-ENGINE-TECHNICAL-ANALYSIS",)}),
        "FACT-5374-STROKE": MappingProxyType({"quantity": "piston_stroke", "variant": "917_30_turbo_5374", "kind": "published_point", "value": 70.4, "unit": "mm", "usage": "candidate_only", "source_refs": ("SRC-AMS-917-ENGINE-TECHNICAL-ANALYSIS",)}),
        "FACT-TURBO-POWER-1600-REPORTED": MappingProxyType({"quantity": "reported_engine_power", "variant": REPORTED_POWER_FACT_VARIANT, "kind": "reported_claim", "value": 1600.0, "unit": "hp", "usage": "documentary_claim_not_calibration_target", "source_refs": ("SRC-PORSCHE-NEWSROOM-91730-1600-QUALIFYING",)}),
    }
)

# Couverture litterale des 31 familles F19 : id, route, portee F28.
F19_FAMILY_SPECS = (
    ("crankcase_half", "conventional_candidate", "common"),
    ("main_bearing", "purchased_non_printable", "common"),
    ("crankshaft", "conventional_candidate", "common"),
    ("central_output_gear", "conventional_candidate", "common"),
    ("output_shaft", "unresolved", "common"),
    ("connecting_rod", "conventional_candidate", "common"),
    ("piston", "unresolved", "common"),
    ("piston_pin", "purchased_non_printable", "common"),
    ("piston_ring", "purchased_non_printable", "common"),
    ("individual_cylinder", "conventional_candidate", "common"),
    ("individual_head", "metal_additive_candidate", "common"),
    ("intake_valve", "purchased_non_printable", "common"),
    ("exhaust_valve", "purchased_non_printable", "common"),
    ("valve_spring", "purchased_non_printable", "common"),
    ("bucket_tappet", "purchased_non_printable", "common"),
    ("camshaft", "unresolved", "common"),
    ("cam_carrier", "conventional_candidate", "common"),
    ("cam_drive_gear", "conventional_candidate", "common"),
    ("cooling_blower", "conventional_candidate", "common"),
    ("blower_shroud", "metal_additive_candidate", "common"),
    ("intake_trumpet", "metal_additive_candidate", "common"),
    ("injector", "purchased_non_printable", "common"),
    ("spark_plug", "purchased_non_printable", "common"),
    ("distributor", "purchased_non_printable", "common"),
    ("pressure_oil_pump", "purchased_non_printable", "common"),
    ("scavenge_oil_pump", "purchased_non_printable", "common"),
    ("exhaust_primary", "conventional_candidate", "common"),
    ("exhaust_collector", "conventional_candidate", "common"),
    ("alternator", "purchased_non_printable", "common"),
    ("turbocharger", "purchased_non_printable", TURBO_VARIANT),
    ("charge_plenum", "metal_additive_candidate", TURBO_VARIANT),
)

# Extension : id, route, portee, registre F19, ids sources, relation, derivation.
# Les decompositions sans route enfant F19 restent volontairement unresolved.
EXTENSION_FAMILY_SPECS = (
    ("auxiliary_bearing", "purchased_non_printable", "common", "routing_rules.backlog_route_classes", ("additional_bearings_bushings_and_thrust_elements",), "requirement_to_family_extension", "exact_source_route_class"),
    ("sensor", "purchased_non_printable", "common", "routing_rules.backlog_route_classes", ("sensors_and_instrumentation",), "requirement_to_family_extension", "exact_source_route_class"),
    ("turbo_chra", "purchased_non_printable", TURBO_VARIANT, "family_route_registry", ("turbocharger",), "turbocharger_decomposition_extension", "conservative_purchased_boundary_from_parent"),
    ("wastegate", "purchased_non_printable", TURBO_VARIANT, "family_route_registry", ("turbocharger",), "turbocharger_control_decomposition_extension", "conservative_purchased_boundary_from_parent"),
    ("seal", "purchased_non_printable", "common", "routing_rules.backlog_route_classes", ("gaskets_and_dynamic_seals",), "requirement_to_family_extension", "exact_source_route_class"),
    ("fastener", "purchased_non_printable", "common", "routing_rules.backlog_route_classes", ("fasteners_and_threaded_hardware",), "requirement_to_family_extension", "exact_source_route_class"),
    ("dyno_coupling", "hybrid_candidate", "common", "f8_interface_route_registry.mechanical_connections", ("crank_output_to_dyno_adapter",), "interface_requirement_to_assembly_extension", "exact_source_route_class"),
    ("gear_train_support", "hybrid_candidate", "common", "f8_interface_route_registry.mechanical_connections", ("cam_drive_gear_train",), "interface_requirement_to_support_extension", "exact_source_route_class"),
    ("gear_train_assembly", "hybrid_candidate", "common", "f8_interface_route_registry.mechanical_connections", ("cam_drive_gear_train", "cooling_blower_bevel_pair"), "interface_group_to_assembly_extension", "exact_source_route_class"),
    ("lubrication_duct_assembly", "hybrid_candidate", "common", "f8_interface_route_registry.ducts", ("pressure_pump_to_main_bearings", "scavenge_pumps_to_oil_cooler", "turbo_pressure_oil_feed", "turbo_scavenge_oil_drain"), "duct_requirements_to_assembly_extension", "exact_source_route_class"),
    ("fuel_duct_assembly", "hybrid_candidate", "common", "f8_interface_route_registry.ducts", ("injection_pump_to_injectors", "bench_fuel_supply_to_injection_pump"), "duct_requirements_to_assembly_extension", "exact_source_route_class"),
    ("cooling_air_duct_assembly", "hybrid_candidate", "common", "f8_interface_route_registry.ducts", ("bench_cooling_air_to_blower", "blower_to_engine_cooling_field"), "duct_requirements_to_assembly_extension", "exact_source_route_class"),
    ("intake_duct_assembly", "hybrid_candidate", "common", "f8_interface_route_registry.ducts", ("intake_trumpet_to_head", "charge_plenum_to_intake_trumpets"), "duct_requirements_to_assembly_extension", "exact_source_route_class"),
    ("exhaust_duct_assembly", "hybrid_candidate", "common", "f8_interface_route_registry.ducts", ("head_to_exhaust_primary", "exhaust_primary_to_collector", "turbo_turbine_outlet_to_bench_extraction"), "duct_requirements_to_assembly_extension", "exact_source_route_class"),
    ("compressor_duct_assembly", "hybrid_candidate", TURBO_VARIANT, "f8_interface_route_registry.ducts", ("ambient_to_turbo_compressor_inlet", "turbo_to_charge_plenum"), "duct_requirements_to_assembly_extension", "exact_source_route_class"),
    ("turbine_inlet_duct_assembly", "hybrid_candidate", TURBO_VARIANT, "f8_interface_route_registry.ducts", ("collector_to_turbo_hot_side",), "duct_requirements_to_assembly_extension", "exact_source_route_class"),
    ("test_bench_mount_assembly", "hybrid_candidate", "common", "f8_interface_route_registry.mechanical_connections", ("engine_mount_to_bedplate",), "interface_requirement_to_assembly_extension", "exact_source_route_class"),
    ("throttle_assembly", "hybrid_candidate", "common", "routing_rules.backlog_route_classes", ("controls_linkages_and_actuators",), "requirement_to_assembly_extension", "exact_source_route_class"),
    ("intake_plenum", "hybrid_candidate", NA_VARIANT, "f8_interface_route_registry.ducts", ("ambient_to_intake_trumpets",), "duct_requirement_to_semantic_plenum_extension", "route_class_only_legacy_visual_variant_not_identity"),
    ("duct_body", "hybrid_candidate", TURBO_VARIANT, "f8_interface_route_registry.ducts", ("collector_to_turbo_hot_side", "turbo_to_charge_plenum"), "duct_requirements_to_body_extension", "exact_source_route_class"),
    ("turbo_compressor_housing", "unresolved", TURBO_VARIANT, "family_route_registry", ("turbocharger",), "turbocharger_decomposition_extension", "deliberately_unresolved_no_child_route_in_f19"),
    ("turbo_turbine_housing", "unresolved", TURBO_VARIANT, "family_route_registry", ("turbocharger",), "turbocharger_decomposition_extension", "deliberately_unresolved_no_child_route_in_f19"),
    ("test_bench_frame", "unresolved", "common", "f8_interface_route_registry.mechanical_connections", ("engine_mount_to_bedplate",), "interface_requirement_to_bedplate_extension", "deliberately_unresolved_no_frame_route_in_f19"),
)

_FAMILY_SPEC_BY_ID: dict[str, dict[str, Any]] = {}
for family_id, route_class, scope in F19_FAMILY_SPECS:
    _FAMILY_SPEC_BY_ID[family_id] = {
        "id": family_id,
        "route_class": route_class,
        "scope": scope,
        "registry": "family_route_registry",
        "source_ids": (family_id,),
        "relationship": "exact_f19_family",
        "route_derivation": "exact_source_route_class",
    }
for family_id, route_class, scope, registry, source_ids, relationship, derivation in EXTENSION_FAMILY_SPECS:
    if family_id in _FAMILY_SPEC_BY_ID:
        raise RuntimeError(f"duplicate_family_spec:{family_id}")
    _FAMILY_SPEC_BY_ID[family_id] = {
        "id": family_id,
        "route_class": route_class,
        "scope": scope,
        "registry": registry,
        "source_ids": source_ids,
        "relationship": relationship,
        "route_derivation": derivation,
    }

ROUTE_CLASS_ORDER = ("purchased_non_printable", "conventional_candidate", "metal_additive_candidate", "hybrid_candidate", "unresolved")
FAMILY_IDS = tuple(
    family_id
    for route_class in ROUTE_CLASS_ORDER
    for family_id, specification in _FAMILY_SPEC_BY_ID.items()
    if specification["route_class"] == route_class
)
ROUTE_PARTITIONS = MappingProxyType(
    {
        route_class: tuple(
            family_id
            for family_id in FAMILY_IDS
            if _FAMILY_SPEC_BY_ID[family_id]["route_class"] == route_class
        )
        for route_class in ROUTE_CLASS_ORDER
    }
)
COMMON_FAMILIES = tuple(family_id for family_id in FAMILY_IDS if _FAMILY_SPEC_BY_ID[family_id]["scope"] == "common")
NA_ONLY_FAMILIES = tuple(family_id for family_id in FAMILY_IDS if _FAMILY_SPEC_BY_ID[family_id]["scope"] == NA_VARIANT)
TURBO_ONLY_FAMILIES = tuple(family_id for family_id in FAMILY_IDS if _FAMILY_SPEC_BY_ID[family_id]["scope"] == TURBO_VARIANT)

UNKNOWN_FIELDS = ("dimension_set", "interface_definition", "material_specification", "placement_transform", "tolerance_set", "provenance_ref", "review_status", "datum_ref")
FORBIDDEN_OUTPUT_SUFFIXES = (".FCStd", ".step", ".stp", ".stl", ".3mf", ".usd", ".usda", ".usdc")
RELEASE_GATE_IDS = (
    "na_cad_authorized", "turbo_cad_authorized", "scan_binding_authorized", "master_cad_authorized",
    "interface_release_authorized", "material_selection_authorized", "solver_execution_authorized",
    "physicsnemo_dataset_authorized", "physicsnemo_training_authorized", "omniverse_simready_authorized",
    "fabrication_authorized", "metal_additive_authorized", "assembly_authorized", "engine_function_claim_authorized",
)
F16_RELEASE_GATE_IDS = (
    "scan_identity_verified", "scan_scale_verified", "variant_identity_verified", "interface_semantics_verified",
    "datums_verified", "coordinates_verified", "crankshaft_geometry_verified", "connecting_rod_geometry_verified",
    "piston_and_pin_geometry_verified", "kinematic_loop_closed", "collision_clearance_verified",
    "cad_solids_authorized", "kinematic_joints_authorized", "physx_authorized", "animation_authorized",
    "solver_execution_authorized", "physicsnemo_training_authorized", "fabrication_authorized",
    "metal_print_authorized", "engine_start_authorized",
)
F24_RELEASE_GATE_IDS = (
    "scan_identity_verified", "na_variant_identity_verified", "turbo_variant_identity_verified",
    "na_dimensioned_cad_ready", "turbo_dimensioned_cad_ready", "na_solver_execution_authorized",
    "turbo_solver_execution_authorized", "na_reference_cases_correlated", "turbo_reference_cases_correlated",
    "physicsnemo_dataset_ready", "physicsnemo_training_authorized", "instrumented_bench_validated",
    "functional_variants_authorized", "manufacturing_authorized",
)
F27_RELEASE_GATE_IDS = (
    "scan_identity_verified", "three_independent_scale_controls_verified",
    "same_feature_physical_correspondence_verified", "traceable_provenance_verified",
    "uncertainty_budget_accepted", "scan_scale_verified", "orientation_primary_axis_verified",
    "orientation_secondary_plane_verified", "orientation_handedness_verified", "scan_orientation_verified",
    "f11_source_identity_and_scale_adapter_ready", "scan_variant_binding_authorized",
    "cad_reconstruction_authorized", "classical_solver_authorized", "physicsnemo_dataset_authorized",
    "physicsnemo_training_authorized", "omniverse_simready_authorized", "fabrication_authorized",
    "metal_print_authorized", "engine_start_authorized",
)
F20_RELEASE_GATE_IDS = (
    "cad_ready", "cfd_ready", "combustion_ready", "manufacturing_ready", "print_ready", "physicsnemo_ready",
)
F22_RELEASE_GATE_IDS = (
    "f21_scale_and_orientation_validated", "physical_variant_identity_validated", "real_bom_enumerated",
    "datums_measured_and_reviewed", "all_critical_parameters_measured", "interface_graph_dimensioned",
    "tolerance_stacks_validated", "cad_layout_authorized", "cad_solids_authorized",
    "assembly_constraints_authorized", "materials_selected_and_sourced",
    "classical_solver_execution_authorized", "physicsnemo_training_authorized",
    "prototype_print_authorized", "metal_print_authorized", "functional_engine_authorized",
)
F10_VISUAL_TRUE_GATE_IDS = (
    "separate_visual_geometry_config_ready", "separate_visual_kinematics_config_ready",
)
F10_PHYSICAL_FALSE_GATE_IDS = (
    "measured_variant_geometry_ready", "physical_kinematics_ready", "manufacturing_geometry_ready",
    "clearance_validation_ready", "combustion_simulation_ready", "performance_claim_authorized",
)


class ContractError(ValueError):
    """Un upstream suivi ou une frontiere fail-closed F28 est invalide."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ContractError(f"missing_input:{path}") from exc
    except json.JSONDecodeError as exc:
        raise ContractError(f"invalid_json:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"expected_json_object:{path}")
    return value


def _all_false(value: Any) -> bool:
    """N'accepte que des feuilles booleennes strictement false."""
    if isinstance(value, bool):
        return value is False
    if isinstance(value, dict):
        return bool(value) and all(_all_false(item) for item in value.values())
    if isinstance(value, list):
        return bool(value) and all(_all_false(item) for item in value)
    return False


def _strict_false_map(value: Any, expected_keys: tuple[str, ...] | set[str]) -> bool:
    return isinstance(value, dict) and set(value) == set(expected_keys) and all(item is False for item in value.values())


def _records_by_id(items: Any, label: str) -> dict[str, dict[str, Any]]:
    if not isinstance(items, list):
        raise ContractError(f"{label}_missing")
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise ContractError(f"{label}_record_invalid")
        if item["id"] in result:
            raise ContractError(f"{label}_duplicate:{item['id']}")
        result[item["id"]] = item
    return result


def _registry_records(f19: dict[str, Any], registry: str) -> dict[str, Any]:
    if registry == "family_route_registry":
        return _records_by_id(f19.get("family_route_registry"), registry)
    if registry == "routing_rules.backlog_route_classes":
        value = f19.get("routing_rules", {}).get("backlog_route_classes")
        if not isinstance(value, dict):
            raise ContractError("f19_backlog_route_classes_missing")
        return value
    prefix = "f8_interface_route_registry."
    if registry.startswith(prefix):
        group = registry[len(prefix):]
        return _records_by_id(f19.get("f8_interface_route_registry", {}).get(group), registry)
    raise ContractError(f"unknown_f19_registry:{registry}")


def validate_upstream_invariants(loaded: dict[str, dict[str, Any]]) -> None:
    """Valide les invariants independamment des empreintes de fichiers."""
    f13 = loaded["classical_solver_facts_f13"]
    if f13.get("phase") != "F13":
        raise ContractError("f13_contract_mismatch")
    facts = _records_by_id(f13.get("fact_registry"), "f13_fact_registry")
    for fact_id, expected in _CANONICAL_FACTS.items():
        fact = facts.get(fact_id)
        if fact is None:
            raise ContractError(f"f13_fact_missing:{fact_id}")
        candidate = fact.get("candidate", {})
        actual = {
            "quantity": fact.get("quantity"), "variant": fact.get("variant"), "kind": candidate.get("kind"),
            "value": candidate.get("value"), "unit": candidate.get("unit"), "usage": fact.get("usage"),
            "source_refs": tuple(fact.get("source_refs", [])),
        }
        if actual != dict(expected) or fact.get("design_lock") is not False:
            raise ContractError(f"f13_fact_invariant_mismatch:{fact_id}")

    f16 = loaded["kinematic_interfaces_f16"]
    if f16.get("phase") != "F16-001" or f16.get("work_branch", {}).get("variant_id") != NA_VARIANT:
        raise ContractError("f16_contract_mismatch")
    if f16.get("work_branch", {}).get("scan_binding") is not False:
        raise ContractError("f16_scan_must_remain_unbound")
    expected_instances = (
        ("crankcase", 1, None), ("crankshaft", 1, None), ("main_bearing", 8, "FACT-MAIN-BEARING-COUNT"),
        ("individual_cylinder", 12, "FACT-CYLINDER-COUNT"), ("connecting_rod", 12, "FACT-CYLINDER-COUNT"),
        ("piston_pin", 12, "FACT-CYLINDER-COUNT"), ("piston", 12, "FACT-CYLINDER-COUNT"),
    )
    actual_instances = tuple((item.get("family"), item.get("count"), item.get("count_fact_ref")) for item in f16.get("component_instance_contract", []) if isinstance(item, dict))
    if actual_instances != expected_instances:
        raise ContractError("f16_component_instance_contract_mismatch")
    expected_graph = (
        ("crankcase_supports_crankshaft", "crankcase", "main_bearing", "crankshaft", 8, "revolute_bearing_candidate"),
        ("crankshaft_to_connecting_rod", "crankshaft", None, "connecting_rod", 12, "revolute_candidate"),
        ("connecting_rod_to_piston_pin", "connecting_rod", None, "piston_pin", 12, "revolute_candidate"),
        ("piston_pin_to_piston", "piston_pin", None, "piston", 12, "fit_definition_unknown"),
        ("piston_to_cylinder", "piston", None, "individual_cylinder", 12, "prismatic_candidate"),
        ("cylinder_to_crankcase", "individual_cylinder", None, "crankcase", 12, "fixed_interface_candidate"),
    )
    graph = f16.get("minimal_graph_contract", {}).get("relation_groups", [])
    actual_graph = tuple((item.get("id"), item.get("from_family"), item.get("via_family"), item.get("to_family"), item.get("count"), item.get("planned_relation")) for item in graph if isinstance(item, dict))
    if actual_graph != expected_graph:
        raise ContractError("f16_minimal_graph_contract_mismatch")
    for datum in f16.get("datum_registry_contract", {}).get("fixed_datums", []):
        if datum.get("origin_mm") is not None:
            raise ContractError("f16_datum_coordinates_must_remain_null")
    if not _strict_false_map(f16.get("release_gates"), F16_RELEASE_GATE_IDS):
        raise ContractError("f16_release_gates_must_remain_false")

    f19 = loaded["manufacturing_routing_f19"]
    if f19.get("phase") != "F19" or f19.get("routing_rules", {}).get("classification_is_selection") is not False:
        raise ContractError("f19_contract_mismatch")
    records = _records_by_id(f19.get("family_route_registry"), "f19_family_route_registry")
    if tuple(records) != tuple(item[0] for item in F19_FAMILY_SPECS):
        raise ContractError("f19_family_registry_coverage_mismatch")
    family_release_keys = {"prototype_print", "metal_additive", "functional", "engine_use", "assembly"}
    for family_id, route_class, scope in F19_FAMILY_SPECS:
        record = records[family_id]
        if record.get("functional_disposition", {}).get("route_class") != route_class:
            raise ContractError(f"f19_route_mismatch:{family_id}")
        expected_scope = "917_30_only" if scope == TURBO_VARIANT else "base_and_turbo"
        if record.get("source_visual_variant") != expected_scope:
            raise ContractError(f"f19_visual_scope_mismatch:{family_id}")
        if not _strict_false_map(record.get("release"), family_release_keys):
            raise ContractError(f"f19_family_release_invalid:{family_id}")
    if records["intake_trumpet"].get("source_visual_variant") != "base_and_turbo":
        raise ContractError("f19_intake_trumpet_must_cover_base_and_turbo")
    f19_gate_keys = {
        "prototype_print_authorized", "metal_additive_build_authorized", "conventional_manufacturing_authorized",
        "purchased_component_specification_released", "hybrid_assembly_authorized", "all_materials_and_routes_sourced",
        "all_tolerances_sourced_and_validated", "real_bom_complete", "functional_engine_authorized", "vehicle_use_authorized",
    }
    if not _strict_false_map(f19.get("release_gates"), f19_gate_keys):
        raise ContractError("f19_release_gates_must_remain_false")
    for specification in _FAMILY_SPEC_BY_ID.values():
        registry = specification["registry"]
        source_records = _registry_records(f19, registry)
        for source_id in specification["source_ids"]:
            if source_id not in source_records:
                raise ContractError(f"f19_extension_source_missing:{specification['id']}:{source_id}")
            source_record = source_records[source_id]
            if registry == "family_route_registry":
                source_route = source_record.get("functional_disposition", {}).get("route_class")
            elif registry == "routing_rules.backlog_route_classes":
                source_route = source_record
            else:
                source_route = source_record.get("route_class")
            if specification["route_derivation"] in {"exact_source_route_class", "route_class_only_legacy_visual_variant_not_identity"} and source_route != specification["route_class"]:
                raise ContractError(f"f19_extension_route_mismatch:{specification['id']}:{source_id}")
    external_boundaries = _registry_records(
        f19, "f8_interface_route_registry.external_interfaces"
    )
    ambient_boundary = external_boundaries.get("bench_intake_ambient")
    if not isinstance(ambient_boundary, dict) or (
        ambient_boundary.get("count"),
        ambient_boundary.get("variant"),
        ambient_boundary.get("input_profile"),
        ambient_boundary.get("route_class"),
    ) != (1, "all", "external_boundary_definition", "not_a_part"):
        raise ContractError("f19_bench_intake_ambient_boundary_mismatch")
    if not _strict_false_map(ambient_boundary.get("release"), family_release_keys):
        raise ContractError("f19_bench_intake_ambient_release_invalid")

    f24 = loaded["dual_variant_functional_readiness_f24"]
    crosswalk = f24.get("variant_crosswalk", [])
    variants = tuple(item.get("canonical_variant_id") for item in crosswalk if isinstance(item, dict))
    if f24.get("phase") != "F24" or variants != TARGET_VARIANTS:
        raise ContractError("f24_variant_contract_mismatch")
    scan = f24.get("scan_evidence_boundary", {})
    if scan.get("selected_variant_id") is not None or scan.get("scan_binding_authorized") is not False:
        raise ContractError("f24_scan_must_remain_unbound")
    turbo = crosswalk[1]
    if turbo.get("reported_1600_hp_fact_ref") != "FACT-TURBO-POWER-1600-REPORTED" or turbo.get("reported_1600_hp_role") != "documentary_only_not_boundary_condition":
        raise ContractError("f24_reported_power_scope_mismatch")
    if not _strict_false_map(f24.get("release_gates"), F24_RELEASE_GATE_IDS):
        raise ContractError("f24_release_gates_must_remain_false")

    f27 = loaded["physical_metrology_campaign_f27"]
    if f27.get("phase") != "F27" or f27.get("record_status") != "blank_template_not_executed":
        raise ContractError("f27_template_mismatch")
    binding = f27.get("source_binding", {})
    if binding.get("working_scan_sha256") is not None or binding.get("identity_status") != "missing":
        raise ContractError("f27_scan_binding_must_remain_missing")
    if not _strict_false_map(f27.get("release_gates"), F27_RELEASE_GATE_IDS):
        raise ContractError("f27_release_gates_must_remain_false")

    f10, f20, f22 = loaded["variant_visualization_f10"], loaded["valvetrain_flow_f20"], loaded["parametric_cad_f22"]
    f10_gates = f10.get("release_gates", {})
    expected_f10_gate_ids = set(F10_VISUAL_TRUE_GATE_IDS) | set(F10_PHYSICAL_FALSE_GATE_IDS)
    if f10.get("phase") != "F10" or not isinstance(f10_gates, dict) or set(f10_gates) != expected_f10_gate_ids or any(f10_gates.get(key) is not True for key in F10_VISUAL_TRUE_GATE_IDS) or any(f10_gates.get(key) is not False for key in F10_PHYSICAL_FALSE_GATE_IDS):
        raise ContractError("f10_excluded_source_mismatch")
    if f20.get("phase") != "F20" or not _strict_false_map(f20.get("release_gates"), F20_RELEASE_GATE_IDS):
        raise ContractError("f20_excluded_source_mismatch")
    if f22.get("phase") != "F22" or f22.get("asset", {}).get("geometry_generated") is not False or not _strict_false_map(f22.get("release_gates"), F22_RELEASE_GATE_IDS):
        raise ContractError("f22_excluded_source_mismatch")


def load_and_validate_upstreams(root: Path) -> dict[str, dict[str, Any]]:
    root = root.resolve()
    loaded: dict[str, dict[str, Any]] = {}
    for source_id, relative_path, expected_digest, _scope, _primary in _CANONICAL_UPSTREAM_BINDINGS:
        path = root / relative_path
        try:
            actual_digest = sha256(path)
        except FileNotFoundError as exc:
            raise ContractError(f"missing_input:{path}") from exc
        if actual_digest != expected_digest:
            raise ContractError(f"upstream_sha256_mismatch:{source_id}")
        loaded[source_id] = load_json(path)
    validate_upstream_invariants(loaded)
    return loaded


def _unknown_state() -> dict[str, None]:
    return {field: None for field in UNKNOWN_FIELDS}


def _route_for(family_id: str) -> str:
    try:
        return str(_FAMILY_SPEC_BY_ID[family_id]["route_class"])
    except KeyError as exc:
        raise ContractError(f"unknown_family:{family_id}") from exc


def _family_record(family_id: str) -> dict[str, Any]:
    specification = _FAMILY_SPEC_BY_ID[family_id]
    return {
        "id": family_id,
        "variant_scope": specification["scope"],
        "semantic_family_only": True,
        "real_bom_quantity": None,
        "route_class": specification["route_class"],
        "source_crosswalk": {
            "contract_id": "manufacturing_routing_f19",
            "registry": specification["registry"],
            "source_ids": list(specification["source_ids"]),
            "relationship": specification["relationship"],
            "route_derivation": specification["route_derivation"],
        },
        "route_selected": False,
        "released": False,
        "engineering_unknowns": _unknown_state(),
    }


def _relation(relation_id: str, source: str | None, target: str, *, cardinality: int | str, planned_interface_type: str, upstream_contract: str, upstream_relation_ref: str, via: str | None = None, source_boundary_ref: str | None = None, requirement_role: str = "upstream_semantic_topology_only") -> dict[str, Any]:
    return {
        "id": relation_id, "source_family": source, "source_boundary_ref": source_boundary_ref,
        "via_family": via, "target_family": target,
        "cardinality": cardinality, "planned_interface_type": planned_interface_type,
        "upstream_contract": upstream_contract, "upstream_relation_ref": upstream_relation_ref,
        "requirement_role": requirement_role, "planned_topology_only": True,
        "interface_definition": None, "placement_transform": None, "tolerance_set": None,
        "provenance_ref": None, "review_status": None, "datum_ref": None,
        "joint_created": False, "active": False,
    }


def _common_relations() -> list[dict[str, Any]]:
    f16, f19 = "kinematic_interfaces_f16", "manufacturing_routing_f19"
    req = "f28_required_topology_not_physical_evidence"
    return [
        _relation("crankcase_supports_crankshaft", "crankcase_half", "crankshaft", via="main_bearing", cardinality=8, planned_interface_type="revolute_bearing_candidate", upstream_contract=f16, upstream_relation_ref="minimal_graph_contract/crankcase_supports_crankshaft"),
        _relation("crankshaft_to_connecting_rod", "crankshaft", "connecting_rod", cardinality=12, planned_interface_type="revolute_candidate", upstream_contract=f16, upstream_relation_ref="minimal_graph_contract/crankshaft_to_connecting_rod"),
        _relation("connecting_rod_to_piston_pin", "connecting_rod", "piston_pin", cardinality=12, planned_interface_type="revolute_candidate", upstream_contract=f16, upstream_relation_ref="minimal_graph_contract/connecting_rod_to_piston_pin"),
        _relation("piston_pin_to_piston", "piston_pin", "piston", cardinality=12, planned_interface_type="fit_definition_unknown", upstream_contract=f16, upstream_relation_ref="minimal_graph_contract/piston_pin_to_piston"),
        _relation("piston_to_cylinder", "piston", "individual_cylinder", cardinality=12, planned_interface_type="prismatic_candidate", upstream_contract=f16, upstream_relation_ref="minimal_graph_contract/piston_to_cylinder"),
        _relation("cylinder_to_crankcase", "individual_cylinder", "crankcase_half", cardinality=12, planned_interface_type="fixed_interface_candidate", upstream_contract=f16, upstream_relation_ref="minimal_graph_contract/cylinder_to_crankcase"),
        _relation("piston_ring_to_piston_and_cylinder", "piston_ring", "individual_cylinder", via="piston", cardinality="unknown_sets_for_12_cylinders", planned_interface_type="reciprocating_seal_candidate", upstream_contract=f19, upstream_relation_ref="family_route_registry/piston_ring", requirement_role=req),
        _relation("head_to_cylinder", "individual_head", "individual_cylinder", cardinality=12, planned_interface_type="fixed_fastened", upstream_contract=f19, upstream_relation_ref="f8_interface_route_registry/mechanical_connections/head_to_cylinder"),
        _relation("head_fire_joint", "individual_head", "individual_cylinder", via="seal", cardinality=12, planned_interface_type="combustion_fire_joint", upstream_contract=f19, upstream_relation_ref="f8_interface_route_registry/sealing_interfaces/head_to_cylinder_fire_joint"),
        _relation("camshaft_to_cam_carrier", "camshaft", "cam_carrier", cardinality=4, planned_interface_type="revolute_bearing", upstream_contract=f19, upstream_relation_ref="f8_interface_route_registry/mechanical_connections/camshaft_to_cam_carrier"),
        _relation("cam_carrier_to_head", "cam_carrier", "individual_head", cardinality=2, planned_interface_type="fixed_fastened", upstream_contract=f19, upstream_relation_ref="f8_interface_route_registry/mechanical_connections/cam_carrier_to_head"),
        _relation("camshaft_to_bucket_tappet", "camshaft", "bucket_tappet", cardinality=24, planned_interface_type="cam_contact_candidate", upstream_contract=f19, upstream_relation_ref="family_route_registry/camshaft+bucket_tappet", requirement_role=req),
        _relation("bucket_tappet_to_intake_valve", "bucket_tappet", "intake_valve", cardinality=12, planned_interface_type="axial_contact_candidate", upstream_contract=f19, upstream_relation_ref="family_route_registry/bucket_tappet+intake_valve", requirement_role=req),
        _relation("bucket_tappet_to_exhaust_valve", "bucket_tappet", "exhaust_valve", cardinality=12, planned_interface_type="axial_contact_candidate", upstream_contract=f19, upstream_relation_ref="family_route_registry/bucket_tappet+exhaust_valve", requirement_role=req),
        _relation("intake_valve_spring_stack", "valve_spring", "intake_valve", via="individual_head", cardinality=12, planned_interface_type="spring_return_candidate", upstream_contract=f19, upstream_relation_ref="family_route_registry/valve_spring+intake_valve", requirement_role=req),
        _relation("exhaust_valve_spring_stack", "valve_spring", "exhaust_valve", via="individual_head", cardinality=12, planned_interface_type="spring_return_candidate", upstream_contract=f19, upstream_relation_ref="family_route_registry/valve_spring+exhaust_valve", requirement_role=req),
        _relation("intake_valve_to_head_guide", "intake_valve", "individual_head", cardinality=12, planned_interface_type="prismatic_guided", upstream_contract=f19, upstream_relation_ref="f8_interface_route_registry/mechanical_connections/intake_valve_to_head_guide"),
        _relation("exhaust_valve_to_head_guide", "exhaust_valve", "individual_head", cardinality=12, planned_interface_type="prismatic_guided", upstream_contract=f19, upstream_relation_ref="f8_interface_route_registry/mechanical_connections/exhaust_valve_to_head_guide"),
        _relation("crankshaft_to_camshafts_via_gear_train", "crankshaft", "camshaft", via="gear_train_assembly", cardinality=4, planned_interface_type="gear_mesh", upstream_contract=f19, upstream_relation_ref="f8_interface_route_registry/mechanical_connections/cam_drive_gear_train"),
        _relation("cam_drive_gear_to_gear_train", "cam_drive_gear", "gear_train_assembly", cardinality="unknown_with_10_meshes", planned_interface_type="gear_mesh", upstream_contract=f19, upstream_relation_ref="f8_interface_route_registry/mechanical_connections/cam_drive_gear_train"),
        _relation("gear_train_support_to_crankcase", "gear_train_support", "crankcase_half", cardinality="unknown", planned_interface_type="fixed_support_candidate", upstream_contract=f19, upstream_relation_ref="f8_interface_route_registry/mechanical_connections/cam_drive_gear_train", requirement_role=req),
        _relation("crankshaft_to_central_output_gear", "crankshaft", "central_output_gear", cardinality=1, planned_interface_type="fixed_or_splined_unknown", upstream_contract=f19, upstream_relation_ref="family_route_registry/central_output_gear", requirement_role=req),
        _relation("central_output_gear_to_output_shaft", "central_output_gear", "output_shaft", cardinality=1, planned_interface_type="gear_or_spline_unknown", upstream_contract=f19, upstream_relation_ref="family_route_registry/central_output_gear+output_shaft", requirement_role=req),
        _relation("output_shaft_support", "output_shaft", "crankcase_half", via="auxiliary_bearing", cardinality="unknown", planned_interface_type="revolute_bearing_candidate", upstream_contract=f19, upstream_relation_ref="routing_rules/backlog_route_classes/additional_bearings_bushings_and_thrust_elements", requirement_role=req),
        _relation("output_shaft_to_dyno_coupling", "output_shaft", "dyno_coupling", cardinality=1, planned_interface_type="torsional_coupling", upstream_contract=f19, upstream_relation_ref="f8_interface_route_registry/mechanical_connections/crank_output_to_dyno_adapter"),
        _relation("dyno_coupling_to_bench", "dyno_coupling", "test_bench_frame", cardinality=1, planned_interface_type="torsional_coupling", upstream_contract=f19, upstream_relation_ref="f8_interface_route_registry/mechanical_connections/crank_output_to_dyno_adapter"),
        _relation("engine_to_bench", "crankcase_half", "test_bench_frame", via="test_bench_mount_assembly", cardinality=4, planned_interface_type="compliant_mount", upstream_contract=f19, upstream_relation_ref="f8_interface_route_registry/mechanical_connections/engine_mount_to_bedplate"),
        _relation("crankshaft_to_cooling_blower", "crankshaft", "cooling_blower", via="gear_train_assembly", cardinality=1, planned_interface_type="gear_mesh", upstream_contract=f19, upstream_relation_ref="f8_interface_route_registry/mechanical_connections/cooling_blower_bevel_pair"),
        _relation("cooling_blower_to_shroud", "cooling_blower", "blower_shroud", cardinality=1, planned_interface_type="fixed_fastened", upstream_contract=f19, upstream_relation_ref="f8_interface_route_registry/mechanical_connections/cooling_blower_shaft_to_blower"),
        _relation("cooling_air_to_engine", "cooling_blower", "individual_head", via="cooling_air_duct_assembly", cardinality=1, planned_interface_type="cooling_air", upstream_contract=f19, upstream_relation_ref="f8_interface_route_registry/ducts/blower_to_engine_cooling_field"),
        _relation("cooling_air_to_cylinders", "cooling_air_duct_assembly", "individual_cylinder", cardinality=1, planned_interface_type="cooling_air", upstream_contract=f19, upstream_relation_ref="f8_interface_route_registry/external_interfaces/cylinder_and_head_fin_field"),
        _relation("intake_distribution_to_trumpets", "intake_duct_assembly", "intake_trumpet", via="throttle_assembly", cardinality=12, planned_interface_type="compressible_intake", upstream_contract=f19, upstream_relation_ref="f8_interface_route_registry/ducts/intake_trumpet_to_head", requirement_role=req),
        _relation("intake_trumpet_to_head", "intake_trumpet", "individual_head", cardinality=12, planned_interface_type="compressible_intake", upstream_contract=f19, upstream_relation_ref="f8_interface_route_registry/ducts/intake_trumpet_to_head"),
        _relation("injector_to_head", "injector", "individual_head", via="fuel_duct_assembly", cardinality=12, planned_interface_type="threaded_pressure_boundary", upstream_contract=f19, upstream_relation_ref="f8_interface_route_registry/sealing_interfaces/injector_to_head_seal"),
        _relation("spark_plug_to_head", "spark_plug", "individual_head", cardinality=24, planned_interface_type="threaded_pressure_boundary", upstream_contract=f19, upstream_relation_ref="f8_interface_route_registry/sealing_interfaces/spark_plug_pressure_seat"),
        _relation("distributor_to_spark_plugs", "distributor", "spark_plug", cardinality="unknown_ignition_channels", planned_interface_type="electrical_ignition_topology_unknown", upstream_contract=f19, upstream_relation_ref="family_route_registry/distributor+spark_plug", requirement_role=req),
        _relation("alternator_drive", "crankshaft", "alternator", via="gear_train_assembly", cardinality=1, planned_interface_type="drive_topology_unknown", upstream_contract=f19, upstream_relation_ref="family_route_registry/alternator", requirement_role=req),
        _relation("pressure_pump_to_main_bearings", "pressure_oil_pump", "main_bearing", via="lubrication_duct_assembly", cardinality=8, planned_interface_type="oil_line", upstream_contract=f19, upstream_relation_ref="f8_interface_route_registry/ducts/pressure_pump_to_main_bearings"),
        _relation("scavenge_pumps_to_lubrication_network", "scavenge_oil_pump", "lubrication_duct_assembly", cardinality=6, planned_interface_type="oil_line", upstream_contract=f19, upstream_relation_ref="f8_interface_route_registry/ducts/scavenge_pumps_to_oil_cooler"),
        _relation("lubrication_network_to_crankcase", "lubrication_duct_assembly", "crankcase_half", cardinality="unknown", planned_interface_type="oil_line", upstream_contract=f19, upstream_relation_ref="f8_interface_route_registry/external_interfaces/dry_sump_oil_network"),
        _relation("fuel_network_to_injectors", "fuel_duct_assembly", "injector", cardinality=12, planned_interface_type="fuel_line", upstream_contract=f19, upstream_relation_ref="f8_interface_route_registry/ducts/injection_pump_to_injectors"),
        _relation("head_to_exhaust_primary", "individual_head", "exhaust_primary", cardinality=12, planned_interface_type="compressible_exhaust", upstream_contract=f19, upstream_relation_ref="f8_interface_route_registry/ducts/head_to_exhaust_primary"),
        _relation("exhaust_primary_to_collector", "exhaust_primary", "exhaust_collector", cardinality=12, planned_interface_type="compressible_exhaust", upstream_contract=f19, upstream_relation_ref="f8_interface_route_registry/ducts/exhaust_primary_to_collector"),
        _relation("sensors_to_bench", "sensor", "test_bench_frame", cardinality="unknown", planned_interface_type="instrumentation_topology_unknown", upstream_contract=f19, upstream_relation_ref="routing_rules/backlog_route_classes/sensors_and_instrumentation", requirement_role=req),
        _relation("fastener_crosscutting_requirement", "fastener", "crankcase_half", cardinality="unknown", planned_interface_type="fixed_fastened", upstream_contract=f19, upstream_relation_ref="routing_rules/backlog_route_classes/fasteners_and_threaded_hardware", requirement_role=req),
    ]


def _na_relations() -> list[dict[str, Any]]:
    f19 = "manufacturing_routing_f19"
    return [
        _relation("na_intake_plenum_to_distribution", "intake_plenum", "intake_duct_assembly", cardinality=1, planned_interface_type="compressible_intake", upstream_contract=f19, upstream_relation_ref="f8_interface_route_registry/ducts/ambient_to_intake_trumpets", requirement_role="route_class_only_legacy_visual_variant_not_identity"),
        _relation("na_exhaust_collector_to_bench_extraction", "exhaust_collector", "exhaust_duct_assembly", cardinality=2, planned_interface_type="compressible_exhaust", upstream_contract=f19, upstream_relation_ref="f8_interface_route_registry/ducts/na_exhaust_collector_to_bench_extraction", requirement_role="route_class_only_legacy_visual_variant_not_identity"),
    ]


def _turbo_relations() -> list[dict[str, Any]]:
    f19 = "manufacturing_routing_f19"
    return [
        _relation("turbocharger_to_chra_via_compressor_housing", "turbocharger", "turbo_chra", via="turbo_compressor_housing", cardinality=2, planned_interface_type="assembly_decomposition_only", upstream_contract=f19, upstream_relation_ref="family_route_registry/turbocharger", requirement_role="f28_decomposition_not_physical_evidence"),
        _relation("turbocharger_to_chra_via_turbine_housing", "turbocharger", "turbo_chra", via="turbo_turbine_housing", cardinality=2, planned_interface_type="assembly_decomposition_only", upstream_contract=f19, upstream_relation_ref="family_route_registry/turbocharger", requirement_role="f28_decomposition_not_physical_evidence"),
        _relation("collector_to_turbine_inlet_duct", "exhaust_collector", "turbine_inlet_duct_assembly", cardinality=2, planned_interface_type="compressible_exhaust", upstream_contract=f19, upstream_relation_ref="f8_interface_route_registry/ducts/collector_to_turbo_hot_side"),
        _relation("turbine_inlet_duct_to_turbine_housing", "turbine_inlet_duct_assembly", "turbo_turbine_housing", via="duct_body", cardinality=2, planned_interface_type="compressible_exhaust", upstream_contract=f19, upstream_relation_ref="f8_interface_route_registry/ducts/collector_to_turbo_hot_side"),
        _relation("turbine_housing_to_chra", "turbo_turbine_housing", "turbo_chra", cardinality=2, planned_interface_type="turbo_rotor_support", upstream_contract=f19, upstream_relation_ref="f8_interface_route_registry/mechanical_connections/turbo_rotor_support"),
        _relation("chra_to_compressor_housing", "turbo_chra", "turbo_compressor_housing", cardinality=2, planned_interface_type="turbo_rotor_support", upstream_contract=f19, upstream_relation_ref="f8_interface_route_registry/mechanical_connections/turbo_rotor_support"),
        _relation("ambient_to_two_compressor_inlets", None, "turbo_compressor_housing", via="compressor_duct_assembly", source_boundary_ref="bench_intake_ambient", cardinality=2, planned_interface_type="compressible_intake", upstream_contract=f19, upstream_relation_ref="f8_interface_route_registry/ducts/ambient_to_turbo_compressor_inlet"),
        _relation("compressor_housing_to_compressor_duct", "turbo_compressor_housing", "compressor_duct_assembly", via="duct_body", cardinality=2, planned_interface_type="compressible_intake", upstream_contract=f19, upstream_relation_ref="f8_interface_route_registry/ducts/turbo_to_charge_plenum"),
        _relation("compressor_duct_to_charge_plenum", "compressor_duct_assembly", "charge_plenum", cardinality=2, planned_interface_type="compressible_intake", upstream_contract=f19, upstream_relation_ref="f8_interface_route_registry/ducts/turbo_to_charge_plenum"),
        _relation("charge_plenum_to_intake_distribution", "charge_plenum", "intake_duct_assembly", cardinality=12, planned_interface_type="compressible_intake", upstream_contract=f19, upstream_relation_ref="f8_interface_route_registry/ducts/charge_plenum_to_intake_trumpets"),
        _relation("turbine_housing_to_exhaust_duct", "turbo_turbine_housing", "exhaust_duct_assembly", cardinality=2, planned_interface_type="compressible_exhaust", upstream_contract=f19, upstream_relation_ref="f8_interface_route_registry/ducts/turbo_turbine_outlet_to_bench_extraction"),
        _relation("wastegate_inlet_bypass", "turbine_inlet_duct_assembly", "wastegate", cardinality=2, planned_interface_type="exhaust_bypass_control_unknown", upstream_contract=f19, upstream_relation_ref="family_route_registry/turbocharger", requirement_role="f28_required_topology_not_physical_evidence"),
        _relation("wastegate_outlet_bypass", "wastegate", "exhaust_duct_assembly", cardinality=2, planned_interface_type="exhaust_bypass_control_unknown", upstream_contract=f19, upstream_relation_ref="family_route_registry/turbocharger", requirement_role="f28_required_topology_not_physical_evidence"),
        _relation("turbo_pressure_oil_feed", "lubrication_duct_assembly", "turbo_chra", cardinality=2, planned_interface_type="oil_line", upstream_contract=f19, upstream_relation_ref="f8_interface_route_registry/ducts/turbo_pressure_oil_feed"),
        _relation("turbo_scavenge_oil_drain", "turbo_chra", "lubrication_duct_assembly", cardinality=2, planned_interface_type="oil_line", upstream_contract=f19, upstream_relation_ref="f8_interface_route_registry/ducts/turbo_scavenge_oil_drain"),
    ]


def _fact_record(facts: dict[str, dict[str, Any]], fact_id: str) -> dict[str, Any]:
    try:
        return facts[fact_id]
    except KeyError as exc:
        raise ContractError(f"f13_fact_missing:{fact_id}") from exc


def _guide(variant_id: str, bore: dict[str, Any], stroke: dict[str, Any]) -> dict[str, Any]:
    return {
        "variant_id": variant_id,
        "source_fact_variant_id": bore["variant"],
        "bore": {"value": bore["candidate"]["value"], "unit": bore["candidate"]["unit"], "fact_ref": bore["id"]},
        "stroke": {"value": stroke["candidate"]["value"], "unit": stroke["candidate"]["unit"], "fact_ref": stroke["id"]},
        "source_contract": "classical_solver_facts_f13",
        "classification": "documentary_guide_not_design_dimension",
        "design_lock": False, "cad_parameter_applied": False, "boundary_condition": False,
    }


def build_contract(root: Path = REPO_ROOT) -> dict[str, Any]:
    loaded = load_and_validate_upstreams(root)
    facts = _records_by_id(loaded["classical_solver_facts_f13"]["fact_registry"], "f13_fact_registry")
    upstream_records = [
        {"id": source_id, "path": path, "sha256": digest, "reuse_scope": scope, "primary_contract_input": primary, "geometry_payload_transfer_authorized": False, "manufacturing_authority": False}
        for source_id, path, digest, scope, primary in _CANONICAL_UPSTREAM_BINDINGS
    ]
    power = _fact_record(facts, "FACT-TURBO-POWER-1600-REPORTED")
    common, na, turbo = _common_relations(), _na_relations(), _turbo_relations()
    return {
        "$comment": "F28 fige un contrat CAO dual-variant sans geometrie; aucun guide documentaire ne remplit un slot de conception.",
        "schema_version": "2.0.0", "phase": "F28",
        "status": "zero_geometry_semantic_contract_all_physical_and_release_gates_blocked",
        "asset": {"id": "porsche-917-dual-variant-parametric-cad-contract-f28", "target_variants": list(TARGET_VARIANTS), "contract_only": True, "real_bom_complete": False, "geometry_generated": False, "scan_bound": False, "functional_claim": False, "printable_claim": False},
        "upstream_contracts": upstream_records,
        "authority_boundary": {"allowed_output": str(OUTPUT_RELATIVE_PATH), "contract_json_only": True, "cad_master_generated": False, "step_generated": False, "stl_generated": False, "three_mf_generated": False, "usd_generated": False, "physics_joint_generated": False, "solver_deck_generated": False, "scan_binding_authorized": False, "dimension_transfer_authorized": False, "solid_transfer_authorized": False, "transform_transfer_authorized": False},
        "nontransfer_policy": {
            "excluded_geometry_sources": sorted(EXCLUDED_GEOMETRY_UPSTREAMS),
            "blocked_payload_classes": ["design_dimension", "interface_dimension", "solid", "mesh", "coordinate", "placement", "transform", "tolerance", "material_selection", "fact_promoted_to_design_lock"],
            "f10_dimensions_solids_transforms_transferred": False, "f20_dimensions_solids_transforms_transferred": False,
            "f22_dimensions_solids_transforms_transferred": False, "scan_coordinates_or_scale_transferred": False,
        },
        "documentary_design_guides": [
            _guide(NA_VARIANT, _fact_record(facts, "FACT-50-BORE"), _fact_record(facts, "FACT-50-STROKE")),
            _guide(TURBO_VARIANT, _fact_record(facts, "FACT-5374-BORE"), _fact_record(facts, "FACT-5374-STROKE")),
        ],
        "reported_power_boundary": {
            "fact_ref": power["id"], "source_fact_variant_id": power["variant"], "related_design_branch_id": TURBO_VARIANT,
            "reported_value": power["candidate"]["value"], "unit": power["candidate"]["unit"],
            "source_contract": "classical_solver_facts_f13", "f24_crosswalk_ref": "dual_variant_functional_readiness_f24",
            "role": "documentary_only_not_boundary_condition", "design_lock": False, "boundary_condition": False,
            "solver_target": False, "validation_result": False,
        },
        "f19_coverage": {
            "source_registry": "manufacturing_routing_f19/family_route_registry", "source_family_count": 31,
            "covered_source_family_refs": [item[0] for item in F19_FAMILY_SPECS], "missing_source_family_refs": [],
            "coverage_status": "exact_31_of_31_routes_preserved", "taxonomy_extension_family_refs": [item[0] for item in EXTENSION_FAMILY_SPECS],
            "turbocharger_decomposition_crosswalk": {
                "source_family_ref": "turbocharger", "source_instance_count": 2,
                "semantic_assembly_instance_refs": ["turbo_semantic_01", "turbo_semantic_02"],
                "child_family_refs": ["turbo_chra", "turbo_compressor_housing", "turbo_turbine_housing", "wastegate"],
                "parent_route_inherited_by_housings": False, "decomposition_geometry_created": False,
            },
        },
        "routing_partitions": {route: list(families) for route, families in ROUTE_PARTITIONS.items()},
        "component_family_registry": [_family_record(family_id) for family_id in FAMILY_IDS],
        "variant_contracts": [
            {"variant_id": NA_VARIANT, "family_refs": list(COMMON_FAMILIES + NA_ONLY_FAMILIES), "semantic_bom_scope_frozen": True, "real_bom_complete": False, "variant_geometry": None, "variant_placement": None, "variant_material_set": None, "variant_tolerance_set": None, "provenance_ref": None, "review_status": None, "datum_ref": None},
            {"variant_id": TURBO_VARIANT, "family_refs": list(COMMON_FAMILIES + TURBO_ONLY_FAMILIES), "semantic_bom_scope_frozen": True, "real_bom_complete": False, "variant_geometry": None, "variant_placement": None, "variant_material_set": None, "variant_tolerance_set": None, "provenance_ref": None, "review_status": None, "datum_ref": None},
        ],
        "common_topology_requirements": common,
        "na_topology_requirements": na,
        "turbo_topology_requirement": {
            "variant_id": TURBO_VARIANT, "architecture": "two_turbo_semantic_topology_only", "f19_source_family_ref": "turbocharger", "required_instance_count": 2,
            "instances": [
                {"id": instance_id, "family_ref": "turbocharger", "component_family_refs": {"chra": "turbo_chra", "compressor_housing": "turbo_compressor_housing", "turbine_housing": "turbo_turbine_housing", "wastegate": "wastegate"}, "commercial_model": None, "compressor_map_ref": None, "turbine_map_ref": None, "placement_transform": None, "interface_definition": None, "material_specification": None, "tolerance_set": None, "provenance_ref": None, "review_status": None, "datum_ref": None, "geometry_ref": None, "released": False}
                for instance_id in ("turbo_semantic_01", "turbo_semantic_02")
            ],
            "planned_relations": turbo, "topology_bound_to_geometry": False, "maps_selected": False,
            "flow_network_released": False, "lubrication_network_released": False,
        },
        "topology_coverage": {"common_relation_count": len(common), "na_relation_count": len(na), "turbo_relation_count": len(turbo), "family_connectivity_status": "all_declared_families_referenced_semantically", "physical_connectivity_verified": False, "kinematic_loop_closed": False, "fluid_network_closed": False, "electrical_network_closed": False},
        "release_gates": {gate_id: False for gate_id in RELEASE_GATE_IDS},
    }


def _referenced_families(relations: list[dict[str, Any]]) -> set[str]:
    result: set[str] = set()
    for relation in relations:
        for key in ("source_family", "via_family", "target_family"):
            value = relation.get(key)
            if isinstance(value, str):
                result.add(value)
    return result


def evaluate(root: Path, contract: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    try:
        expected = build_contract(root)
    except (ContractError, OSError) as exc:
        expected = None
        errors.append(str(exc))
    if contract.get("phase") != "F28":
        errors.append("phase_mismatch")
    authority = contract.get("authority_boundary", {})
    if not isinstance(authority, dict) or authority.get("allowed_output") != str(OUTPUT_RELATIVE_PATH):
        errors.append("allowed_output_mismatch")
    authority_false = {"cad_master_generated", "step_generated", "stl_generated", "three_mf_generated", "usd_generated", "physics_joint_generated", "solver_deck_generated", "scan_binding_authorized", "dimension_transfer_authorized", "solid_transfer_authorized", "transform_transfer_authorized"}
    if not isinstance(authority, dict) or set(authority) != authority_false | {"allowed_output", "contract_json_only"} or any(authority.get(key) is not False for key in authority_false):
        errors.append("authority_gate_open_or_not_boolean")
    if authority.get("contract_json_only") is not True:
        errors.append("contract_json_only_required")
    if not _strict_false_map(contract.get("release_gates"), RELEASE_GATE_IDS):
        errors.append("release_gates_must_be_exact_booleans_false")

    asset = contract.get("asset", {})
    if asset.get("scan_bound") is not False or authority.get("scan_binding_authorized") is not False:
        errors.append("scan_binding_forbidden")
    for key in ("geometry_generated", "functional_claim", "printable_claim"):
        if asset.get(key) is not False:
            errors.append(f"asset_gate_must_be_false:{key}")
    nontransfer = contract.get("nontransfer_policy", {})
    for source_id, key in {"variant_visualization_f10": "f10_dimensions_solids_transforms_transferred", "valvetrain_flow_f20": "f20_dimensions_solids_transforms_transferred", "parametric_cad_f22": "f22_dimensions_solids_transforms_transferred"}.items():
        if nontransfer.get(key) is not False:
            errors.append(f"geometry_transfer_forbidden:{source_id}")
    if nontransfer.get("scan_coordinates_or_scale_transferred") is not False:
        errors.append("scan_payload_transfer_forbidden")

    families = contract.get("component_family_registry", [])
    if not isinstance(families, list):
        errors.append("component_family_registry_missing")
        families = []
    ids = tuple(item.get("id") for item in families if isinstance(item, dict))
    if ids != FAMILY_IDS:
        errors.append("component_family_ids_mismatch")
    for item in families:
        if not isinstance(item, dict):
            errors.append("component_family_record_invalid")
            continue
        family_id = item.get("id", "unknown")
        try:
            expected_route = _route_for(family_id)
            source = _FAMILY_SPEC_BY_ID[family_id]
        except (ContractError, KeyError):
            expected_route, source = None, None
        if item.get("route_class") != expected_route:
            errors.append(f"route_laundering_forbidden:{family_id}")
        if item.get("route_selected") is not False or item.get("released") is not False:
            errors.append(f"family_release_forbidden:{family_id}")
        if item.get("semantic_family_only") is not True:
            errors.append(f"semantic_family_flag_invalid:{family_id}")
        if source is not None:
            crosswalk = item.get("source_crosswalk", {})
            if crosswalk.get("registry") != source["registry"] or tuple(crosswalk.get("source_ids", [])) != tuple(source["source_ids"]) or crosswalk.get("route_derivation") != source["route_derivation"]:
                errors.append(f"family_source_crosswalk_mismatch:{family_id}")
        unknowns = item.get("engineering_unknowns")
        if not isinstance(unknowns, dict) or set(unknowns) != set(UNKNOWN_FIELDS):
            errors.append(f"engineering_unknown_schema_mismatch:{family_id}")
        else:
            for field in UNKNOWN_FIELDS:
                if unknowns.get(field) is not None:
                    errors.append(f"engineering_unknown_must_be_null:{family_id}:{field}")

    coverage = contract.get("f19_coverage", {})
    if tuple(coverage.get("covered_source_family_refs", [])) != tuple(item[0] for item in F19_FAMILY_SPECS) or coverage.get("missing_source_family_refs") != []:
        errors.append("f19_family_coverage_mismatch")
    if "intake_trumpet" not in COMMON_FAMILIES:
        errors.append("intake_trumpet_scope_mismatch")
    guides = contract.get("documentary_design_guides", [])
    if not isinstance(guides, list) or len(guides) != 2:
        errors.append("documentary_design_guides_mismatch")
        guides = []
    for guide in guides:
        if guide.get("design_lock") is not False or guide.get("cad_parameter_applied") is not False or guide.get("boundary_condition") is not False or guide.get("source_contract") != "classical_solver_facts_f13":
            errors.append(f"documentary_guide_promoted:{guide.get('variant_id')}")
    power = contract.get("reported_power_boundary", {})
    if power.get("source_fact_variant_id") != REPORTED_POWER_FACT_VARIANT or power.get("related_design_branch_id") != TURBO_VARIANT or power.get("source_fact_variant_id") == power.get("related_design_branch_id") or power.get("role") != "documentary_only_not_boundary_condition" or any(power.get(key) is not False for key in ("design_lock", "boundary_condition", "solver_target", "validation_result")):
        errors.append("reported_1600_hp_promoted_or_misbound")

    common = contract.get("common_topology_requirements", [])
    na = contract.get("na_topology_requirements", [])
    turbo = contract.get("turbo_topology_requirement", {})
    turbo_relations = turbo.get("planned_relations", [])
    for group_name, relations in (("common", common), ("na", na), ("turbo", turbo_relations)):
        if not isinstance(relations, list):
            errors.append(f"topology_group_missing:{group_name}")
            continue
        seen: set[str] = set()
        for relation in relations:
            relation_id = relation.get("id", "unknown")
            if relation_id in seen:
                errors.append(f"topology_relation_duplicate:{relation_id}")
            seen.add(relation_id)
            source_family = relation.get("source_family")
            source_boundary_ref = relation.get("source_boundary_ref")
            if source_family is None:
                if not isinstance(source_boundary_ref, str) or not source_boundary_ref:
                    errors.append(f"topology_source_missing:{relation_id}")
            elif source_family not in _FAMILY_SPEC_BY_ID or source_boundary_ref is not None:
                errors.append(f"topology_unknown_or_ambiguous_source:{relation_id}")
            if relation.get("target_family") not in _FAMILY_SPEC_BY_ID:
                errors.append(f"topology_unknown_family:{relation_id}:target_family")
            via = relation.get("via_family")
            if via is not None and via not in _FAMILY_SPEC_BY_ID:
                errors.append(f"topology_unknown_family:{relation_id}:via_family")
            if relation.get("cardinality") is None or not isinstance(relation.get("planned_interface_type"), str):
                errors.append(f"topology_semantics_missing:{relation_id}")
            for key in ("interface_definition", "placement_transform", "tolerance_set", "provenance_ref", "review_status", "datum_ref"):
                if relation.get(key) is not None:
                    errors.append(f"topology_input_must_be_null:{relation_id}:{key}")
            if relation.get("planned_topology_only") is not True or relation.get("joint_created") is not False or relation.get("active") is not False:
                errors.append(f"topology_activation_forbidden:{relation_id}")
    if isinstance(common, list) and isinstance(na, list) and set(COMMON_FAMILIES + NA_ONLY_FAMILIES) - (_referenced_families(common) | _referenced_families(na)):
        errors.append("na_family_isolated")
    if isinstance(common, list) and isinstance(turbo_relations, list) and set(COMMON_FAMILIES + TURBO_ONLY_FAMILIES) - (_referenced_families(common) | _referenced_families(turbo_relations)):
        errors.append("turbo_family_isolated")

    instances = turbo.get("instances", [])
    if turbo.get("architecture") != "two_turbo_semantic_topology_only" or turbo.get("f19_source_family_ref") != "turbocharger" or turbo.get("required_instance_count") != 2 or not isinstance(instances, list) or len(instances) != 2:
        errors.append("two_turbo_topology_required")
        instances = instances if isinstance(instances, list) else []
    expected_components = {"chra": "turbo_chra", "compressor_housing": "turbo_compressor_housing", "turbine_housing": "turbo_turbine_housing", "wastegate": "wastegate"}
    for instance in instances:
        turbo_id = instance.get("id", "unknown")
        if instance.get("family_ref") != "turbocharger" or instance.get("component_family_refs") != expected_components:
            errors.append(f"turbo_decomposition_mismatch:{turbo_id}")
        for field in ("commercial_model", "compressor_map_ref", "turbine_map_ref", "placement_transform", "interface_definition", "material_specification", "tolerance_set", "provenance_ref", "review_status", "datum_ref", "geometry_ref"):
            if instance.get(field) is not None:
                errors.append(f"turbo_input_must_be_null:{turbo_id}:{field}")
        if instance.get("released") is not False:
            errors.append(f"turbo_release_forbidden:{turbo_id}")
    for key in ("topology_bound_to_geometry", "maps_selected", "flow_network_released", "lubrication_network_released"):
        if turbo.get(key) is not False:
            errors.append(f"turbo_gate_must_be_false:{key}")

    output_name = authority.get("allowed_output", "")
    if any(str(output_name).lower().endswith(suffix.lower()) for suffix in FORBIDDEN_OUTPUT_SUFFIXES):
        errors.append("geometry_output_forbidden")
    if expected is not None and contract != expected:
        errors.append("tracked_contract_not_deterministic")
    return {
        "report_status": "passed" if not errors else "failed", "contract_errors": errors,
        "variant_count": len(contract.get("variant_contracts", [])), "family_count": len(families),
        "f19_source_family_count": len(F19_FAMILY_SPECS), "turbo_semantic_instance_count": len(instances),
        "geometry_artifact_count": 0, "release": {gate_id: False for gate_id in RELEASE_GATE_IDS},
    }


def write_contract(path: Path, contract: dict[str, Any]) -> None:
    if path.suffix.lower() != ".json":
        raise ContractError("output_must_be_json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--output", type=Path, default=OUTPUT_RELATIVE_PATH)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--write", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output if args.output.is_absolute() else root / args.output
    try:
        expected = build_contract(root)
        if args.write:
            write_contract(output, expected)
            return 0
        current = load_json(output)
        report = evaluate(root, current)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if report["report_status"] == "passed" else 1
    except (ContractError, OSError) as exc:
        print(json.dumps({"report_status": "failed", "contract_errors": [str(exc)]}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
