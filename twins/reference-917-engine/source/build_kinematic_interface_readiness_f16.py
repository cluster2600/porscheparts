#!/usr/bin/env python3
"""Build the fail-closed F16-001 kinematic interface readiness artifacts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONTRACT = ROOT / "twins/reference-917-engine/kinematic-interface-readiness-f16.json"

EXPECTED_SOURCE_PATHS = {
    "fact_registry": "twins/reference-917-engine/classical-solver-cases-f13.json",
    "dimensional_skeleton": "twins/reference-917-engine/dimensional-skeleton-f14.json",
    "scan_metrology": "twins/reference-917-engine/scan-metrology-f13.json",
    "mechanical_connections": "twins/reference-917-engine/mechanical-connections-f8.json",
    "mechanical_cycle_closure": "twins/reference-917-engine/mechanical-cycle-closure-f15.json",
}
EXPECTED_FACTS = {
    "FACT-CYLINDER-COUNT": {
        "quantity": "cylinder_count",
        "value": 12,
        "unit": "count",
        "variant": "type_912_5_0_na",
        "role": "candidate_instance_count_only",
        "candidate_kind": "published_point",
        "source_refs": ["SRC-AMS-917-ENGINE-TECHNICAL-ANALYSIS"],
        "usage": "candidate_only",
        "contradiction_refs": ["CONTRADICTION-ARCHITECTURE"],
    },
    "FACT-50-BORE": {
        "quantity": "cylinder_bore",
        "value": 86.8,
        "unit": "mm",
        "variant": "type_912_5_0_na",
        "role": "published_candidate_not_interface_tolerance",
        "candidate_kind": "published_point",
        "source_refs": ["SRC-AMS-917-ENGINE-TECHNICAL-ANALYSIS"],
        "usage": "candidate_only",
        "contradiction_refs": ["CONTRADICTION-VARIANT-MIXING"],
    },
    "FACT-50-STROKE": {
        "quantity": "piston_stroke",
        "value": 70.4,
        "unit": "mm",
        "variant": "type_912_5_0_na",
        "role": "published_candidate_for_transparent_kinematic_derivation",
        "candidate_kind": "published_point",
        "source_refs": ["SRC-AMS-917-ENGINE-TECHNICAL-ANALYSIS"],
        "usage": "candidate_only",
        "contradiction_refs": ["CONTRADICTION-VARIANT-MIXING"],
    },
    "FACT-50-DISPLACEMENT": {
        "quantity": "engine_displacement",
        "value": 4999.0,
        "unit": "cm3",
        "variant": "type_912_5_0_na",
        "role": "published_consistency_candidate_only",
        "candidate_kind": "published_point",
        "source_refs": ["SRC-AMS-917-ENGINE-TECHNICAL-ANALYSIS"],
        "usage": "candidate_only",
        "contradiction_refs": ["CONTRADICTION-VARIANT-MIXING"],
    },
    "FACT-MAIN-BEARING-COUNT": {
        "quantity": "main_bearing_count",
        "value": 8,
        "unit": "count",
        "role": "candidate_station_count_only",
        "candidate_kind": "published_point",
        "source_refs": [
            "SRC-AMS-917-ENGINE-TECHNICAL-ANALYSIS",
            "SRC-KFZ-TECH-917-TYPE912-ENGINE",
        ],
        "usage": "candidate_only",
        "contradiction_refs": [],
    },
    "FACT-FIRING-ORDER": {
        "quantity": "firing_order",
        "value": [1, 9, 5, 12, 3, 8, 6, 10, 2, 7, 4, 11],
        "unit": "cylinder_id",
        "role": "candidate_sequence_with_unresolved_cylinder_numbering",
        "candidate_kind": "published_sequence",
        "source_refs": ["SRC-AMS-917-ENGINE-TECHNICAL-ANALYSIS"],
        "usage": "candidate_only",
        "contradiction_refs": ["CONTRADICTION-CYLINDER-NUMBERING"],
    },
}
EXPECTED_FIXED_DATUM_IDS = {
    "engine_reference_frame",
    "crankshaft_axis",
    "crankcase_split_plane",
    "bank_positive_deck_plane",
    "bank_negative_deck_plane",
}
EXPECTED_FIXED_DATUMS = {
    "engine_reference_frame": {
        "id": "engine_reference_frame",
        "kind": "coordinate_frame",
        "origin_mm": None,
        "orientation": None,
        "status": "unknown_unverified",
    },
    "crankshaft_axis": {
        "id": "crankshaft_axis",
        "kind": "axis",
        "origin_mm": None,
        "direction": None,
        "status": "unknown_unverified",
    },
    "crankcase_split_plane": {
        "id": "crankcase_split_plane",
        "kind": "plane",
        "origin_mm": None,
        "normal": None,
        "status": "unknown_unverified",
    },
    "bank_positive_deck_plane": {
        "id": "bank_positive_deck_plane",
        "kind": "plane",
        "origin_mm": None,
        "normal": None,
        "status": "unknown_unverified",
    },
    "bank_negative_deck_plane": {
        "id": "bank_negative_deck_plane",
        "kind": "plane",
        "origin_mm": None,
        "normal": None,
        "status": "unknown_unverified",
    },
}
EXPECTED_COMPONENT_COUNTS = {
    "crankcase": 1,
    "crankshaft": 1,
    "main_bearing": 8,
    "individual_cylinder": 12,
    "connecting_rod": 12,
    "piston_pin": 12,
    "piston": 12,
}
EXPECTED_COMPONENT_CONTRACT = {
    "crankcase": {
        "family": "crankcase",
        "id_prefix": "crankcase_",
        "count": 1,
        "count_fact_ref": None,
    },
    "crankshaft": {
        "family": "crankshaft",
        "id_prefix": "crankshaft_",
        "count": 1,
        "count_fact_ref": None,
    },
    "main_bearing": {
        "family": "main_bearing",
        "id_prefix": "main_bearing_",
        "count": 8,
        "count_fact_ref": "FACT-MAIN-BEARING-COUNT",
    },
    "individual_cylinder": {
        "family": "individual_cylinder",
        "id_prefix": "cylinder_geometric_",
        "count": 12,
        "count_fact_ref": "FACT-CYLINDER-COUNT",
    },
    "connecting_rod": {
        "family": "connecting_rod",
        "id_prefix": "connecting_rod_geometric_",
        "count": 12,
        "count_fact_ref": "FACT-CYLINDER-COUNT",
    },
    "piston_pin": {
        "family": "piston_pin",
        "id_prefix": "piston_pin_geometric_",
        "count": 12,
        "count_fact_ref": "FACT-CYLINDER-COUNT",
    },
    "piston": {
        "family": "piston",
        "id_prefix": "piston_geometric_",
        "count": 12,
        "count_fact_ref": "FACT-CYLINDER-COUNT",
    },
}
EXPECTED_INSTANCE_NULL_TEMPLATE = {
    "transform_mm": None,
    "orientation": None,
    "geometry_ref": None,
    "material_specification": None,
    "mass_kg": None,
    "inertia_kg_m2": None,
    "interface_dimensions": None,
    "physics_body_enabled": False,
    "manufacturing_released": False,
    "status": "semantic_instance_only_unplaced",
}
EXPECTED_RELATIONS = {
    "crankcase_supports_crankshaft": (8, "crankshaft_main_bearing"),
    "crankshaft_to_connecting_rod": (12, "connecting_rod_to_crankshaft"),
    "connecting_rod_to_piston_pin": (12, "connecting_rod_to_piston_pin"),
    "piston_pin_to_piston": (12, None),
    "piston_to_cylinder": (12, "piston_to_cylinder"),
    "cylinder_to_crankcase": (12, "cylinder_to_crankcase"),
}
EXPECTED_RELATION_GROUPS = {
    "crankcase_supports_crankshaft": {
        "id": "crankcase_supports_crankshaft",
        "source_connection_ref": "crankshaft_main_bearing",
        "count": 8,
        "from_family": "crankcase",
        "via_family": "main_bearing",
        "to_family": "crankshaft",
        "planned_relation": "revolute_bearing_candidate",
        "coordinates": None,
        "active": False,
        "physics_joint_enabled": False,
    },
    "crankshaft_to_connecting_rod": {
        "id": "crankshaft_to_connecting_rod",
        "source_connection_ref": "connecting_rod_to_crankshaft",
        "count": 12,
        "from_family": "crankshaft",
        "via_family": None,
        "to_family": "connecting_rod",
        "planned_relation": "revolute_candidate",
        "coordinates": None,
        "active": False,
        "physics_joint_enabled": False,
    },
    "connecting_rod_to_piston_pin": {
        "id": "connecting_rod_to_piston_pin",
        "source_connection_ref": "connecting_rod_to_piston_pin",
        "count": 12,
        "from_family": "connecting_rod",
        "via_family": None,
        "to_family": "piston_pin",
        "planned_relation": "revolute_candidate",
        "coordinates": None,
        "active": False,
        "physics_joint_enabled": False,
    },
    "piston_pin_to_piston": {
        "id": "piston_pin_to_piston",
        "source_connection_ref": None,
        "requirement_role": "required_topology_not_evidence",
        "count": 12,
        "from_family": "piston_pin",
        "via_family": None,
        "to_family": "piston",
        "planned_relation": "fit_definition_unknown",
        "coordinates": None,
        "active": False,
        "physics_joint_enabled": False,
    },
    "piston_to_cylinder": {
        "id": "piston_to_cylinder",
        "source_connection_ref": "piston_to_cylinder",
        "count": 12,
        "from_family": "piston",
        "via_family": None,
        "to_family": "individual_cylinder",
        "planned_relation": "prismatic_candidate",
        "coordinates": None,
        "active": False,
        "physics_joint_enabled": False,
    },
    "cylinder_to_crankcase": {
        "id": "cylinder_to_crankcase",
        "source_connection_ref": "cylinder_to_crankcase",
        "count": 12,
        "from_family": "individual_cylinder",
        "via_family": None,
        "to_family": "crankcase",
        "planned_relation": "fixed_interface_candidate",
        "coordinates": None,
        "active": False,
        "physics_joint_enabled": False,
    },
}
EXPECTED_MEASUREMENT_IDS = {
    "MC-IDENTITY-01",
    "MC-SCALE-01",
    "MC-SCALE-02",
    "MC-SCALE-03",
    "MC-CASE-01",
    "MC-BEARING-01",
    "MC-BEARING-02",
    "MC-CRANK-01",
    "MC-ROD-01",
    "MC-PIN-01",
    "MC-PISTON-01",
    "MC-CYLINDER-01",
    "MC-ASSEMBLY-01",
    "MC-PHASE-01",
}
EXPECTED_MEASUREMENT_TEMPLATES = {
    "MC-IDENTITY-01": {
        "id": "MC-IDENTITY-01",
        "target": "physical_engine_or_part_set",
        "quantity": "identity_variant_and_part_numbers",
        "unit": "documented_identity",
        "preferred_method": "documentary_trace_and_teardown",
        "minimum_occurrences": 1,
        "value": None,
    },
    "MC-SCALE-01": {
        "id": "MC-SCALE-01",
        "target": "regular_cylinder_centres",
        "quantity": "regular_cylinder_center_pitch",
        "unit": "mm",
        "preferred_method": "traceable_CMM_or_calibrated_scan",
        "minimum_occurrences": 3,
        "value": None,
    },
    "MC-SCALE-02": {
        "id": "MC-SCALE-02",
        "target": "identified_head_studs",
        "quantity": "head_stud_free_length",
        "unit": "mm",
        "preferred_method": "traceable_length_metrology",
        "minimum_occurrences": 3,
        "value": None,
    },
    "MC-SCALE-03": {
        "id": "MC-SCALE-03",
        "target": "identified_head_studs",
        "quantity": "head_stud_shaft_diameter",
        "unit": "mm",
        "preferred_method": "traceable_diameter_metrology",
        "minimum_occurrences": 3,
        "value": None,
    },
    "MC-CASE-01": {
        "id": "MC-CASE-01",
        "target": "crankcase_main_bearing_line",
        "quantity": "crankshaft_axis_origin_and_direction",
        "unit": "mm_and_unit_vector",
        "preferred_method": "CMM_or_CT_with_named_datums",
        "minimum_occurrences": 1,
        "value": None,
    },
    "MC-BEARING-01": {
        "id": "MC-BEARING-01",
        "target": "all_main_bearing_stations",
        "quantity": "station_centres_and_axial_coordinates",
        "unit": "mm",
        "preferred_method": "CMM_or_CT",
        "minimum_occurrences": 8,
        "value": None,
    },
    "MC-BEARING-02": {
        "id": "MC-BEARING-02",
        "target": "all_main_bearing_stations",
        "quantity": "seat_diameter_width_and_clearance",
        "unit": "mm",
        "preferred_method": "CMM_bore_gauge_and_teardown",
        "minimum_occurrences": 8,
        "value": None,
    },
    "MC-CRANK-01": {
        "id": "MC-CRANK-01",
        "target": "crankshaft",
        "quantity": "crankpin_topology_centres_phase_diameter_and_width",
        "unit": "mm_and_deg",
        "preferred_method": "CMM_and_teardown",
        "minimum_occurrences": None,
        "value": None,
    },
    "MC-ROD-01": {
        "id": "MC-ROD-01",
        "target": "all_connecting_rods",
        "quantity": "centre_distance_big_end_small_end_bores_and_widths",
        "unit": "mm",
        "preferred_method": "CMM_and_teardown",
        "minimum_occurrences": 12,
        "value": None,
    },
    "MC-PIN-01": {
        "id": "MC-PIN-01",
        "target": "all_piston_pins",
        "quantity": "diameter_length_and_fit",
        "unit": "mm_and_fit_class",
        "preferred_method": "CMM_micrometer_and_teardown",
        "minimum_occurrences": 12,
        "value": None,
    },
    "MC-PISTON-01": {
        "id": "MC-PISTON-01",
        "target": "all_pistons",
        "quantity": "compression_height_skirt_diameter_and_pin_axis",
        "unit": "mm",
        "preferred_method": "CMM_and_teardown",
        "minimum_occurrences": 12,
        "value": None,
    },
    "MC-CYLINDER-01": {
        "id": "MC-CYLINDER-01",
        "target": "all_cylinders_and_crankcase_registers",
        "quantity": "axis_spigot_deck_and_register_geometry",
        "unit": "mm_and_unit_vector",
        "preferred_method": "CMM_or_CT_with_named_datums",
        "minimum_occurrences": 12,
        "value": None,
    },
    "MC-ASSEMBLY-01": {
        "id": "MC-ASSEMBLY-01",
        "target": "assembled_cranktrain",
        "quantity": "deck_clearance_end_floats_and_kinematic_loop_closure",
        "unit": "mm",
        "preferred_method": "instrumented_teardown_and_CMM",
        "minimum_occurrences": 12,
        "value": None,
    },
    "MC-PHASE-01": {
        "id": "MC-PHASE-01",
        "target": "crankshaft_and_cylinder_numbering",
        "quantity": "crankpin_phase_cylinder_mapping_and_firing_order",
        "unit": "deg_and_cylinder_id",
        "preferred_method": "degree_wheel_teardown_and_documentary_cross_check",
        "minimum_occurrences": 1,
        "value": None,
    },
}
EXPECTED_PARENT_AUTHORITY_BOUNDARY = {
    "mechanical_cycle_closure_execution_authorized": True,
    "thermodynamic_solver_execution_authorized": False,
    "cantera_execution_authorized": False,
    "combustion_simulation_authorized": False,
    "gas_exchange_simulation_authorized": False,
    "turbo_simulation_authorized": False,
    "physicsnemo_training_authorized": False,
    "performance_claim_authorized": False,
    "fabrication_authorized": False,
    "metal_print_authorized": False,
    "engine_start_authorized": False,
}
REQUIRED_FALSE_GATES = {
    "scan_identity_verified",
    "scan_scale_verified",
    "variant_identity_verified",
    "interface_semantics_verified",
    "datums_verified",
    "coordinates_verified",
    "crankshaft_geometry_verified",
    "connecting_rod_geometry_verified",
    "piston_and_pin_geometry_verified",
    "kinematic_loop_closed",
    "collision_clearance_verified",
    "cad_solids_authorized",
    "kinematic_joints_authorized",
    "physx_authorized",
    "animation_authorized",
    "solver_execution_authorized",
    "physicsnemo_training_authorized",
    "fabrication_authorized",
    "metal_print_authorized",
    "engine_start_authorized",
}
REQUIRED_PROHIBITIONS = {
    "bind_the_scan_to_the_5L_NA_branch",
    "treat_scan_native_units_as_mm",
    "invent_datum_coordinates_or_component_transforms",
    "treat_candidate_crank_radius_as_a_manufacturing_dimension",
    "author_solids_meshes_materials_or_fabrication_geometry",
    "author_or_activate_physx_joints_rigid_bodies_or_animation",
    "claim_kinematic_loop_collision_or_clearance_validation",
    "use_as_classical_solver_or_physicsnemo_training_data",
    "authorize_engine_hardware_fabrication_printing_or_start",
}
USD_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
USD_SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9_.:/-]+$")


def _index_by(values: Any, field: str) -> dict[str, dict[str, Any]]:
    if not isinstance(values, list):
        return {}
    return {
        item[field]: item
        for item in values
        if isinstance(item, dict) and isinstance(item.get(field), str)
    }


def _strict_equal(actual: Any, expected: Any) -> bool:
    """JSON-style equality that never treats booleans as integers."""

    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(actual) == set(expected) and all(
            _strict_equal(actual[key], value) for key, value in expected.items()
        )
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(
            _strict_equal(left, right) for left, right in zip(actual, expected)
        )
    return actual == expected


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _display_path(path: Path, project_root: Path = ROOT) -> str:
    try:
        return str(path.resolve().relative_to(project_root.resolve()))
    except ValueError:
        return str(path.resolve())


def _safe_usd_name(value: str) -> str:
    if not isinstance(value, str) or USD_IDENTIFIER_RE.fullmatch(value) is None:
        raise ValueError(f"unsafe USD identifier refused: {value!r}")
    return value


def _usd_string_token(value: str, field: str) -> str:
    """Encode a deliberately narrow semantic token as a USDA string literal."""

    if not isinstance(value, str) or USD_SAFE_TOKEN_RE.fullmatch(value) is None:
        raise ValueError(f"unsafe USD string token refused for {field}: {value!r}")
    return json.dumps(value, ensure_ascii=True)


def _json_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def validate_contract(
    contract: Any,
    fact_registry: Any,
    dimensional_skeleton: Any,
    scan_metrology: Any,
    mechanical_connections: Any,
    mechanical_cycle_closure: Any,
    project_root: Path = ROOT,
) -> list[str]:
    """Validate that F16 remains a source-bounded, coordinate-free contract."""

    payloads = {
        "contract": contract,
        "fact_registry": fact_registry,
        "dimensional_skeleton": dimensional_skeleton,
        "scan_metrology": scan_metrology,
        "mechanical_connections": mechanical_connections,
        "mechanical_cycle_closure": mechanical_cycle_closure,
    }
    type_errors = [f"{name}: expected an object" for name, value in payloads.items() if not isinstance(value, dict)]
    if type_errors:
        return type_errors

    errors: list[str] = []
    if contract.get("schema_version") != "1.0.0":
        errors.append("schema_version: expected 1.0.0")
    if contract.get("phase") != "F16-001":
        errors.append("phase: expected F16-001")
    if contract.get("status") != "kinematic_interface_contract_ready_all_geometry_and_motion_blocked":
        errors.append("status: must remain kinematic_interface_contract_ready_all_geometry_and_motion_blocked")
    if contract.get("asset_id") != "porsche-917-kinematic-interface-readiness-f16":
        errors.append("asset_id: unexpected asset")

    source_contracts = contract.get("source_contracts")
    if source_contracts != EXPECTED_SOURCE_PATHS:
        errors.append("source_contracts: expected the exact F8/F13/F14/F15 inputs")
    else:
        for label, relative_path in source_contracts.items():
            if not (project_root / relative_path).is_file():
                errors.append(f"source_contracts.{label}: missing {relative_path}")

    branch = contract.get("work_branch")
    if not isinstance(branch, dict):
        errors.append("work_branch: expected an object")
    else:
        expected_branch = {
            "variant_id": "type_912_5_0_na",
            "dimensional_skeleton_variant_id": "917_5_0_na_4999",
            "role": "engineering_reference_branch_not_scan_identification",
            "scan_binding": False,
            "scan_asset_id": None,
            "scan_identity_status": "unbound",
            "scan_scale_mm_per_unit": None,
            "variant_identity_proven": False,
            "manufacturing_identity_proven": False,
        }
        if not _strict_equal(branch, expected_branch):
            errors.append("work_branch: scan must remain unbound from the 5.0 L NA reference branch")

    requirements = contract.get("source_fact_requirements")
    requirement_index = _index_by(requirements, "fact_ref")
    if set(requirement_index) != set(EXPECTED_FACTS) or not isinstance(requirements, list) or len(requirements) != len(EXPECTED_FACTS):
        errors.append("source_fact_requirements: expected exactly the six approved F13 facts")
    facts = _index_by(fact_registry.get("fact_registry"), "id")
    for fact_ref, expected in EXPECTED_FACTS.items():
        requirement = requirement_index.get(fact_ref)
        if requirement is None:
            continue
        if requirement.get("role") != expected["role"]:
            errors.append(f"source_fact_requirements.{fact_ref}.role: unexpected role")
        fact = facts.get(fact_ref)
        if fact is None:
            errors.append(f"fact_registry.{fact_ref}: missing fact")
            continue
        candidate = fact.get("candidate")
        if not isinstance(candidate, dict):
            errors.append(f"fact_registry.{fact_ref}.candidate: expected an object")
            continue
        if fact.get("quantity") != expected["quantity"]:
            errors.append(f"fact_registry.{fact_ref}.quantity: unexpected quantity")
        if (
            candidate.get("kind") != expected["candidate_kind"]
            or candidate.get("value") != expected["value"]
            or candidate.get("unit") != expected["unit"]
        ):
            errors.append(f"fact_registry.{fact_ref}.candidate: published value changed")
        if "variant" in expected and fact.get("variant") != expected["variant"]:
            errors.append(f"fact_registry.{fact_ref}.variant: wrong branch")
        if fact.get("design_lock") is not False:
            errors.append(f"fact_registry.{fact_ref}.design_lock: must remain false")
        if fact.get("source_refs") != expected["source_refs"]:
            errors.append(f"fact_registry.{fact_ref}.source_refs: exact provenance changed")
        if fact.get("usage") != expected["usage"]:
            errors.append(f"fact_registry.{fact_ref}.usage: must remain candidate_only")
        if fact.get("contradiction_refs") != expected["contradiction_refs"]:
            errors.append(f"fact_registry.{fact_ref}.contradiction_refs: exact unresolved set changed")

    derivations = contract.get("transparent_derivations")
    if not isinstance(derivations, list) or len(derivations) != 1 or not isinstance(derivations[0], dict):
        errors.append("transparent_derivations: expected only candidate_crank_radius")
    else:
        derivation = derivations[0]
        expected_derivation = {
            "id": "candidate_crank_radius",
            "source_fact_ref": "FACT-50-STROKE",
            "formula": "stroke_mm / 2",
            "result_unit": "mm",
            "value_in_contract": None,
            "status": "derived_candidate_not_measured",
            "manufacturing_dimension": False,
            "geometry_authority": False,
            "load_model_authority": False,
        }
        if not _strict_equal(derivation, expected_derivation):
            errors.append("transparent_derivations[0]: only stroke/2 with no manufacturing authority is allowed")

    variants = _index_by(dimensional_skeleton.get("variants"), "variant_id")
    variant = variants.get("917_5_0_na_4999")
    if variant is None:
        errors.append("dimensional_skeleton: missing 917_5_0_na_4999")
    else:
        if variant.get("branch_role") != "scan_comparison_candidate_not_selected":
            errors.append("dimensional_skeleton.917_5_0_na_4999.branch_role: scan candidate must remain unselected")
        if variant.get("identity_status") != "numerically_closest_scan_candidate_not_identified":
            errors.append("dimensional_skeleton.917_5_0_na_4999.identity_status: must remain unidentified")
        dimension_facts = _index_by(variant.get("facts"), "fact_id")
        expected_dimensions = {
            "cylinder_count": (12, "count"),
            "bore_diameter_mm": (86.8, "mm"),
            "stroke_mm": (70.4, "mm"),
            "documented_displacement_cm3": (4999.0, "cm3"),
        }
        for fact_id, (value, unit) in expected_dimensions.items():
            item = dimension_facts.get(fact_id)
            if item is None or item.get("value") != value or item.get("unit") != unit:
                errors.append(f"dimensional_skeleton.{fact_id}: expected sourced F14 candidate")
            elif item.get("manufacturing_dimension") is not False:
                errors.append(f"dimensional_skeleton.{fact_id}: must not be a manufacturing dimension")

    if scan_metrology.get("status") != "hypothesis_only_physical_calibration_missing":
        errors.append("scan_metrology.status: physical calibration must remain missing")
    scan_release = scan_metrology.get("release_authority")
    if not isinstance(scan_release, dict):
        errors.append("scan_metrology.release_authority: expected an object")
    else:
        for flag in (
            "identity_release_enabled",
            "scale_release_enabled",
            "variant_release_enabled",
            "functional_release_enabled",
            "fabrication_release_enabled",
        ):
            if scan_release.get(flag) is not False:
                errors.append(f"scan_metrology.release_authority.{flag}: must remain false")

    if mechanical_cycle_closure.get("status") != "sourced_mechanical_cycle_closure_ready_thermodynamic_blocked":
        errors.append("mechanical_cycle_closure.status: unexpected F15 parent")
    cycle_authority = mechanical_cycle_closure.get("authority_boundary")
    if not isinstance(cycle_authority, dict):
        errors.append("mechanical_cycle_closure.authority_boundary: expected an object")
    elif (
        set(cycle_authority) != set(EXPECTED_PARENT_AUTHORITY_BOUNDARY)
        or any(
            type(cycle_authority[key]) is not bool
            or cycle_authority[key] is not expected_value
            for key, expected_value in EXPECTED_PARENT_AUTHORITY_BOUNDARY.items()
        )
    ):
        errors.append(
            "mechanical_cycle_closure.authority_boundary: expected the exact F15 authority set and booleans"
        )

    datum_contract = contract.get("datum_registry_contract")
    if not isinstance(datum_contract, dict):
        errors.append("datum_registry_contract: expected an object")
    else:
        fixed = datum_contract.get("fixed_datums")
        fixed_index = _index_by(fixed, "id")
        if not isinstance(fixed, list) or len(fixed) != 5 or set(fixed_index) != EXPECTED_FIXED_DATUM_IDS:
            errors.append("datum_registry_contract.fixed_datums: expected five unverified datums")
        for datum_id, datum in fixed_index.items():
            if not _strict_equal(datum, EXPECTED_FIXED_DATUMS.get(datum_id)):
                errors.append(
                    f"datum_registry_contract.{datum_id}: exact kind, null coordinates and status required"
                )
        repeated = datum_contract.get("repeated_datums")
        if not isinstance(repeated, list) or len(repeated) != 1 or not isinstance(repeated[0], dict):
            errors.append("datum_registry_contract.repeated_datums: expected the cylinder axis family")
        else:
            item = repeated[0]
            expected_repeated = {
                "family": "cylinder_axis",
                "id_prefix": "cylinder_axis_geometric_",
                "count_fact_ref": "FACT-CYLINDER-COUNT",
                "expected_count": 12,
                "origin_mm": None,
                "direction": None,
                "historical_cylinder_number": None,
                "status": "unknown_unplaced_unverified",
            }
            if not _strict_equal(item, expected_repeated):
                errors.append("datum_registry_contract.repeated_datums[0]: all 12 cylinder axes must remain unplaced")

    station = contract.get("main_bearing_station_contract")
    if not isinstance(station, dict):
        errors.append("main_bearing_station_contract: expected an object")
    else:
        expected_station_header = {
            "id_prefix": "main_bearing_station_",
            "count_fact_ref": "FACT-MAIN-BEARING-COUNT",
            "expected_count": 8,
            "axis_ref": "crankshaft_axis",
            "status": "unknown_unmeasured",
            "manufacturing_dimension": False,
        }
        for field, value in expected_station_header.items():
            if station.get(field) != value:
                errors.append(f"main_bearing_station_contract.{field}: unexpected value")
        for field in (
            "axial_coordinate_mm",
            "seat_center_mm",
            "seat_axis",
            "seat_diameter_mm",
            "seat_width_mm",
            "bearing_clearance_mm",
        ):
            if station.get(field) is not None:
                errors.append(f"main_bearing_station_contract.{field}: unmeasured value must be null")

    component_contract = contract.get("component_instance_contract")
    components = _index_by(component_contract, "family")
    if not isinstance(component_contract, list) or len(component_contract) != len(EXPECTED_COMPONENT_COUNTS) or set(components) != set(EXPECTED_COMPONENT_COUNTS):
        errors.append("component_instance_contract: unexpected family set")
    for family, expected_component in EXPECTED_COMPONENT_CONTRACT.items():
        item = components.get(family)
        if item is None:
            continue
        if not _strict_equal(item, expected_component):
            errors.append(
                f"component_instance_contract.{family}: exact family, id_prefix, count and provenance required"
            )
    if (
        isinstance(component_contract, list)
        and all(
            isinstance(item, dict)
            and type(item.get("count")) is int
            and 0 < item["count"] <= 100
            for item in component_contract
        )
    ):
        candidate_ids = [
            f"{item.get('id_prefix')}{ordinal:02d}"
            for item in component_contract
            if isinstance(item.get("count"), int) and item["count"] > 0
            for ordinal in range(1, item["count"] + 1)
        ]
        if len(candidate_ids) != 58 or len(set(candidate_ids)) != 58:
            errors.append("component_instance_contract: expected exactly 58 unique semantic instance ids")
    else:
        errors.append("component_instance_contract: counts must be bounded positive integers")

    null_template = contract.get("instance_null_template")
    if not _strict_equal(null_template, EXPECTED_INSTANCE_NULL_TEMPLATE):
        errors.append(
            "instance_null_template: exact null fields, false authorities and safe status required"
        )

    graph = contract.get("minimal_graph_contract")
    if not isinstance(graph, dict):
        errors.append("minimal_graph_contract: expected an object")
    else:
        if set(graph.get("node_families", [])) != set(EXPECTED_COMPONENT_COUNTS):
            errors.append("minimal_graph_contract.node_families: unexpected family set")
        relations = graph.get("relation_groups")
        relation_index = _index_by(relations, "id")
        if not isinstance(relations, list) or len(relations) != len(EXPECTED_RELATIONS) or set(relation_index) != set(EXPECTED_RELATIONS):
            errors.append("minimal_graph_contract.relation_groups: unexpected relation set")
        connection_index = _index_by(mechanical_connections.get("mechanical_connections"), "id")
        for relation_id, (count, source_ref) in EXPECTED_RELATIONS.items():
            relation = relation_index.get(relation_id)
            if relation is None:
                continue
            if not _strict_equal(relation, EXPECTED_RELATION_GROUPS[relation_id]):
                errors.append(
                    f"minimal_graph_contract.{relation_id}: exact endpoints, count, planned relation and inactive flags required"
                )
            if source_ref is None:
                continue
            source_connection = connection_index.get(source_ref)
            if source_connection is None:
                errors.append(f"mechanical_connections.{source_ref}: missing source connection")
            else:
                if source_connection.get("count") != count:
                    errors.append(f"mechanical_connections.{source_ref}.count: does not match F16")
                if source_connection.get("measurements") != {}:
                    errors.append(f"mechanical_connections.{source_ref}.measurements: must remain empty")
                if source_connection.get("physics_enabled") is not False:
                    errors.append(f"mechanical_connections.{source_ref}.physics_enabled: must remain false")

    measurements = contract.get("measurement_campaign_template")
    measurement_index = _index_by(measurements, "id")
    if not isinstance(measurements, list) or len(measurements) != len(EXPECTED_MEASUREMENT_IDS) or set(measurement_index) != EXPECTED_MEASUREMENT_IDS:
        errors.append("measurement_campaign_template: expected the complete 14-item campaign")
    for measurement_id, measurement in measurement_index.items():
        if not _strict_equal(measurement, EXPECTED_MEASUREMENT_TEMPLATES.get(measurement_id)):
            errors.append(
                f"measurement_campaign_template.{measurement_id}: exact target, quantity, unit, method, minimum occurrences and null value required"
            )

    evidence = contract.get("measurement_evidence_template")
    if not isinstance(evidence, dict):
        errors.append("measurement_evidence_template: expected an object")
    else:
        for field in (
            "instrument_id",
            "calibration_certificate",
            "measurement_temperature_c",
            "operator_or_lab",
            "datum_scheme",
            "uncertainty",
            "evidence_path",
        ):
            if evidence.get(field) is not None:
                errors.append(f"measurement_evidence_template.{field}: missing evidence must be null")
        if evidence.get("review_status") != "missing":
            errors.append("measurement_evidence_template.review_status: must remain missing")

    policy = contract.get("authoring_policy")
    if not isinstance(policy, dict):
        errors.append("authoring_policy: expected an object")
    else:
        if policy.get("allowed_output_formats") != ["json", "csv", "usda"]:
            errors.append("authoring_policy.allowed_output_formats: expected json/csv/usda only")
        if policy.get("allowed_usd_prims") != ["Xform", "Scope"]:
            errors.append("authoring_policy.allowed_usd_prims: expected Xform and Scope only")
        for flag in (
            "xform_operations_allowed",
            "coordinates_allowed",
            "solids_allowed",
            "meshes_allowed",
            "curves_allowed",
            "materials_allowed",
            "physics_schemas_allowed",
            "joints_allowed",
            "animation_allowed",
            "fabrication_exports_allowed",
        ):
            if policy.get(flag) is not False:
                errors.append(f"authoring_policy.{flag}: must remain false")
        if policy.get("unknown_values_must_be_null") is not True:
            errors.append("authoring_policy.unknown_values_must_be_null: expected true")

    gates = contract.get("release_gates")
    if not isinstance(gates, dict) or set(gates) != REQUIRED_FALSE_GATES:
        errors.append("release_gates: expected the exact fail-closed gate set")
    elif any(value is not False for value in gates.values()):
        errors.append("release_gates: every gate must remain false")

    output = contract.get("output")
    if not isinstance(output, dict):
        errors.append("output: expected an object")
    else:
        if output.get("directory") != "work/917-kinematic-interface-readiness-f16":
            errors.append("output.directory: unexpected work path")
        if output.get("readiness_json") != "kinematic-interface-readiness.json":
            errors.append("output.readiness_json: unexpected filename")
        if output.get("registry_csv") != "kinematic-interface-registry.csv":
            errors.append("output.registry_csv: unexpected filename")
        if output.get("semantic_usda") != "kinematic-interface-axes.usda":
            errors.append("output.semantic_usda: unexpected filename")
        if output.get("tracked") is not False:
            errors.append("output.tracked: generated readiness artifacts must remain untracked")

    prohibited = contract.get("prohibited_use")
    if not isinstance(prohibited, list) or not REQUIRED_PROHIBITIONS <= set(prohibited):
        errors.append("prohibited_use: missing fail-closed limits")

    return errors


def _resolved_fact(fact: dict[str, Any], role: str) -> dict[str, Any]:
    return {
        "fact_ref": fact["id"],
        "quantity": fact["quantity"],
        "variant": fact["variant"],
        "value": fact["candidate"]["value"],
        "unit": fact["candidate"]["unit"],
        "source_refs": fact["source_refs"],
        "usage": fact["usage"],
        "design_lock": fact["design_lock"],
        "role": role,
        "manufacturing_dimension": False,
    }


def _expand_datums(contract: dict[str, Any]) -> list[dict[str, Any]]:
    datums = [dict(item) for item in contract["datum_registry_contract"]["fixed_datums"]]
    repeated = contract["datum_registry_contract"]["repeated_datums"][0]
    for ordinal in range(1, repeated["expected_count"] + 1):
        datums.append(
            {
                "id": f"{repeated['id_prefix']}{ordinal:02d}",
                "kind": repeated["family"],
                "ordinal": ordinal,
                "origin_mm": None,
                "direction": None,
                "historical_cylinder_number": None,
                "status": repeated["status"],
            }
        )
    return datums


def _expand_bearing_stations(contract: dict[str, Any]) -> list[dict[str, Any]]:
    template = contract["main_bearing_station_contract"]
    null_fields = (
        "axial_coordinate_mm",
        "seat_center_mm",
        "seat_axis",
        "seat_diameter_mm",
        "seat_width_mm",
        "bearing_clearance_mm",
    )
    return [
        {
            "id": f"{template['id_prefix']}{ordinal:02d}",
            "ordinal": ordinal,
            "axis_ref": template["axis_ref"],
            **{field: None for field in null_fields},
            "status": template["status"],
            "manufacturing_dimension": False,
        }
        for ordinal in range(1, template["expected_count"] + 1)
    ]


def _expand_instances(contract: dict[str, Any]) -> list[dict[str, Any]]:
    instances: list[dict[str, Any]] = []
    null_template = contract["instance_null_template"]
    for family in contract["component_instance_contract"]:
        for ordinal in range(1, family["count"] + 1):
            instances.append(
                {
                    "id": f"{family['id_prefix']}{ordinal:02d}",
                    "family": family["family"],
                    "ordinal": ordinal,
                    "count_fact_ref": family["count_fact_ref"],
                    **null_template,
                }
            )
    return instances


def _instance_ids(instances: list[dict[str, Any]]) -> dict[str, list[str]]:
    by_family: dict[str, list[str]] = {}
    for instance in instances:
        by_family.setdefault(instance["family"], []).append(instance["id"])
    return by_family


def _expand_relations(contract: dict[str, Any], instances: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_family = _instance_ids(instances)
    relations: list[dict[str, Any]] = []
    for group in contract["minimal_graph_contract"]["relation_groups"]:
        for ordinal in range(1, group["count"] + 1):
            from_ids = by_family[group["from_family"]]
            to_ids = by_family[group["to_family"]]
            via_family = group.get("via_family")
            relation = {
                "id": f"{group['id']}_{ordinal:02d}",
                "group_id": group["id"],
                "ordinal": ordinal,
                "source_connection_ref": group.get("source_connection_ref"),
                "requirement_role": group.get("requirement_role"),
                "from_id": from_ids[0] if len(from_ids) == 1 else from_ids[ordinal - 1],
                "via_id": None,
                "to_id": to_ids[0] if len(to_ids) == 1 else to_ids[ordinal - 1],
                "planned_relation": group["planned_relation"],
                "coordinates": None,
                "active": False,
                "physics_joint_enabled": False,
            }
            if via_family:
                via_ids = by_family[via_family]
                relation["via_id"] = via_ids[0] if len(via_ids) == 1 else via_ids[ordinal - 1]
            relations.append(relation)
    return relations


def _measurement_register(contract: dict[str, Any]) -> list[dict[str, Any]]:
    evidence = contract["measurement_evidence_template"]
    return [{**item, "evidence": dict(evidence), "status": "missing"} for item in contract["measurement_campaign_template"]]


def build_report(
    contract: dict[str, Any],
    fact_registry: dict[str, Any],
    dimensional_skeleton: dict[str, Any],
    scan_metrology: dict[str, Any],
    mechanical_connections: dict[str, Any],
    mechanical_cycle_closure: dict[str, Any],
    input_paths: dict[str, Path],
    contract_path: Path = DEFAULT_CONTRACT,
    project_root: Path = ROOT,
) -> dict[str, Any]:
    errors = validate_contract(
        contract,
        fact_registry,
        dimensional_skeleton,
        scan_metrology,
        mechanical_connections,
        mechanical_cycle_closure,
        project_root,
    )
    if errors:
        raise ValueError("invalid F16-001 contract:\n" + "\n".join(f"- {error}" for error in errors))

    facts = _index_by(fact_registry["fact_registry"], "id")
    resolved = [
        _resolved_fact(facts[item["fact_ref"]], item["role"])
        for item in contract["source_fact_requirements"]
    ]
    stroke_mm = float(facts["FACT-50-STROKE"]["candidate"]["value"])
    datums = _expand_datums(contract)
    bearing_stations = _expand_bearing_stations(contract)
    instances = _expand_instances(contract)
    relations = _expand_relations(contract, instances)
    measurements = _measurement_register(contract)

    generated_from = {
        "contract_path": _display_path(contract_path, project_root),
        "contract_sha256": _sha256(contract_path),
    }
    for key, path in input_paths.items():
        generated_from[f"{key}_path"] = _display_path(path, project_root)
        generated_from[f"{key}_sha256"] = _sha256(path)

    return {
        "$comment": "F16-001 genere uniquement des registres semantiques sans coordonnees, geometrie, joints, animation, materiaux ou autorite de fabrication.",
        "schema_version": "1.0.0",
        "phase": "F16-001",
        "status": "passed_readiness_generation_all_kinematics_blocked",
        "generated_from": generated_from,
        "work_branch": dict(contract["work_branch"]),
        "resolved_source_facts": resolved,
        "transparent_derivations": [
            {
                "id": "candidate_crank_radius",
                "source_fact_ref": "FACT-50-STROKE",
                "formula": "stroke_mm / 2",
                "value": stroke_mm / 2.0,
                "unit": "mm",
                "status": "derived_candidate_not_measured",
                "manufacturing_dimension": False,
                "geometry_authority": False,
                "load_model_authority": False,
            }
        ],
        "datum_registry": datums,
        "main_bearing_station_registry": bearing_stations,
        "component_instance_registry": instances,
        "minimal_graph": {
            "nodes": [item["id"] for item in instances],
            "relations": relations,
            "all_relations_inactive": True,
            "physics_joint_count": 0,
        },
        "measurement_campaign": measurements,
        "readiness_summary": {
            "fixed_datum_count": 5,
            "cylinder_axis_count": 12,
            "main_bearing_station_count": 8,
            "component_instance_count": len(instances),
            "relation_instance_count": len(relations),
            "measurement_requirement_count": len(measurements),
            "verified_coordinate_count": 0,
            "solid_count": 0,
            "mesh_count": 0,
            "curve_count": 0,
            "material_binding_count": 0,
            "physics_body_count": 0,
            "physics_joint_count": 0,
            "animated_prim_count": 0,
            "classical_solver_sample_count": 0,
            "physicsnemo_sample_count": 0,
        },
        "blocking_unknowns": [
            "scan_identity_and_variant",
            "traceable_scan_scale_and_interface_semantics",
            "engine_reference_frame_and_crankshaft_axis",
            "eight_main_bearing_station_coordinates_and_seats",
            "crankpin_topology_geometry_and_phase",
            "connecting_rod_centre_distance_and_interfaces",
            "piston_pin_geometry_and_fits",
            "piston_compression_height_and_running_geometry",
            "twelve_cylinder_axes_spigots_and_deck_interfaces",
            "cylinder_numbering_and_firing_order_mapping",
            "assembled_kinematic_loop_and_clearances",
        ],
        "authoring_policy": dict(contract["authoring_policy"]),
        "release_gates": dict(contract["release_gates"]),
        "prohibited_use": list(contract["prohibited_use"]),
    }


def build_registry_csv(report: dict[str, Any]) -> str:
    fields = [
        "record_kind",
        "id",
        "family",
        "parent_id",
        "ordinal",
        "status",
        "value",
        "unit",
        "source_fact_ref",
        "manufacturing_dimension",
        "position_mm",
        "orientation",
        "coordinates_verified",
        "active",
        "physics_joint_enabled",
    ]
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()

    def write(**values: Any) -> None:
        writer.writerow({field: _json_value(values.get(field)) for field in fields})

    for fact in report["resolved_source_facts"]:
        write(
            record_kind="source_fact",
            id=fact["fact_ref"],
            family=fact["quantity"],
            status=fact["role"],
            value=fact["value"],
            unit=fact["unit"],
            source_fact_ref=fact["fact_ref"],
            manufacturing_dimension=False,
            coordinates_verified=False,
        )
    for derivation in report["transparent_derivations"]:
        write(
            record_kind="transparent_derivation",
            id=derivation["id"],
            family="kinematic_scalar",
            status=derivation["status"],
            value=derivation["value"],
            unit=derivation["unit"],
            source_fact_ref=derivation["source_fact_ref"],
            manufacturing_dimension=False,
            coordinates_verified=False,
        )
    for datum in report["datum_registry"]:
        write(
            record_kind="datum",
            id=datum["id"],
            family=datum["kind"],
            ordinal=datum.get("ordinal"),
            status=datum["status"],
            position_mm=datum.get("origin_mm"),
            orientation=datum.get("orientation", datum.get("direction", datum.get("normal"))),
            coordinates_verified=False,
        )
    for station in report["main_bearing_station_registry"]:
        write(
            record_kind="main_bearing_station",
            id=station["id"],
            family="main_bearing_station",
            parent_id=station["axis_ref"],
            ordinal=station["ordinal"],
            status=station["status"],
            manufacturing_dimension=False,
            position_mm=station["seat_center_mm"],
            orientation=station["seat_axis"],
            coordinates_verified=False,
        )
    for instance in report["component_instance_registry"]:
        write(
            record_kind="component_instance",
            id=instance["id"],
            family=instance["family"],
            ordinal=instance["ordinal"],
            status=instance["status"],
            source_fact_ref=instance["count_fact_ref"],
            position_mm=instance["transform_mm"],
            orientation=instance["orientation"],
            coordinates_verified=False,
            active=False,
        )
    for relation in report["minimal_graph"]["relations"]:
        write(
            record_kind="relation_requirement",
            id=relation["id"],
            family=relation["group_id"],
            parent_id=relation["from_id"],
            ordinal=relation["ordinal"],
            status=relation["planned_relation"],
            source_fact_ref=relation["source_connection_ref"],
            position_mm=relation["coordinates"],
            coordinates_verified=False,
            active=False,
            physics_joint_enabled=False,
        )
    for measurement in report["measurement_campaign"]:
        write(
            record_kind="measurement_requirement",
            id=measurement["id"],
            family=measurement["quantity"],
            parent_id=measurement["target"],
            status=measurement["status"],
            value=measurement["value"],
            unit=measurement["unit"],
            coordinates_verified=False,
        )
    return output.getvalue()


def build_semantic_usda(report: dict[str, Any]) -> str:
    lines = [
        "#usda 1.0",
        "(",
        '    defaultPrim = "KinematicInterfaceReadinessF16"',
        "    metersPerUnit = 0.001",
        '    upAxis = "Z"',
        ")",
        "",
        'def Xform "KinematicInterfaceReadinessF16"',
        "{",
        f"    custom string f16:phase = {_usd_string_token('F16-001', 'phase')}",
        "    custom string f16:status = "
        + _usd_string_token("all_coordinates_and_motion_blocked", "root status"),
        "    custom bool f16:scanBound = false",
        "    custom bool f16:coordinatesVerified = false",
        "    custom bool f16:physicsEnabled = false",
        "",
        '    def Scope "Datums"',
        "    {",
    ]
    for datum in report["datum_registry"]:
        name = _safe_usd_name(datum["id"])
        lines.extend(
            [
                f'        def Xform "{name}"',
                "        {",
                "            custom string f16:kind = "
                + _usd_string_token(datum["kind"], f"datum {datum['id']} kind"),
                "            custom string f16:status = "
                + _usd_string_token(datum["status"], f"datum {datum['id']} status"),
                "            custom bool f16:coordinatesVerified = false",
                "        }",
            ]
        )
    lines.extend(["    }", "", '    def Scope "MainBearingStations"', "    {"])
    for station in report["main_bearing_station_registry"]:
        name = _safe_usd_name(station["id"])
        lines.extend(
            [
                f'        def Xform "{name}"',
                "        {",
                "            custom string f16:status = "
                + _usd_string_token(station["status"], f"station {station['id']} status"),
                "            custom bool f16:coordinatesVerified = false",
                "        }",
            ]
        )
    lines.extend(["    }", "", '    def Scope "Components"', "    {"])
    for instance in report["component_instance_registry"]:
        name = _safe_usd_name(instance["id"])
        lines.extend(
            [
                f'        def Xform "{name}"',
                "        {",
                "            custom string f16:family = "
                + _usd_string_token(instance["family"], f"instance {instance['id']} family"),
                "            custom string f16:status = "
                + _usd_string_token(instance["status"], f"instance {instance['id']} status"),
                "            custom bool f16:coordinatesVerified = false",
                "            custom bool f16:physicsBodyEnabled = false",
                "        }",
            ]
        )
    lines.extend(["    }", "}", ""])
    return "\n".join(lines)


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"F16-001: cannot read {label}: {exc}")
    if not isinstance(payload, dict):
        raise SystemExit(f"F16-001: {label} must contain an object")
    return payload


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(arguments)

    project_root = args.project_root.resolve()
    contract_path = args.contract.resolve()
    contract = _load_json(contract_path, "contract")
    # Never dereference paths supplied by a mutated contract.  The validator
    # still requires the contract to name this exact set, but source loading is
    # anchored to the known repository paths first.
    source_paths = {
        key: (project_root / relative_path).resolve()
        for key, relative_path in EXPECTED_SOURCE_PATHS.items()
    }
    sources = {key: _load_json(path, key) for key, path in source_paths.items()}
    errors = validate_contract(
        contract,
        sources["fact_registry"],
        sources["dimensional_skeleton"],
        sources["scan_metrology"],
        sources["mechanical_connections"],
        sources["mechanical_cycle_closure"],
        project_root,
    )
    if errors:
        raise SystemExit(
            "F16-001: invalid contract\n"
            + "\n".join(f"  - {error}" for error in errors)
        )

    report = build_report(
        contract,
        sources["fact_registry"],
        sources["dimensional_skeleton"],
        sources["scan_metrology"],
        sources["mechanical_connections"],
        sources["mechanical_cycle_closure"],
        source_paths,
        contract_path=contract_path,
        project_root=project_root,
    )
    output_dir = (
        args.output_dir.resolve()
        if args.output_dir is not None
        else (project_root / contract["output"]["directory"]).resolve()
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / contract["output"]["readiness_json"]
    csv_path = output_dir / contract["output"]["registry_csv"]
    usda_path = output_dir / contract["output"]["semantic_usda"]
    json_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    csv_path.write_text(build_registry_csv(report), encoding="utf-8")
    usda_path.write_text(build_semantic_usda(report), encoding="utf-8")
    print(
        "F16-001 OK: "
        f"{report['readiness_summary']['component_instance_count']} semantic instances, "
        f"{report['readiness_summary']['verified_coordinate_count']} verified coordinates, "
        "all geometry/motion/release gates remain blocked; "
        f"output={_display_path(output_dir, project_root)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
