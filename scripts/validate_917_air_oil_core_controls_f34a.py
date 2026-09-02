#!/usr/bin/env python3
"""Valide le contrat de décision F34a air/huile et contrôles 2026."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "twins/reference-917-engine/air-oil-core-controls-f34a.json"

EXPECTED_PARENTS = [
    {
        "id": "f11_reengineering_contract",
        "path": "twins/reference-917-engine/reengineering-contract-f11.json",
        "sha256": "5760114ed81d041f4656d0d68e9eaa9818f19f9d0278ce310ddda37f63df3989",
        "reuse_scope": "proof_levels_unknowns_and_fail_closed_authority_only",
        "physical_validation_transferred": False,
    },
    {
        "id": "f32_clean_sheet_2026",
        "path": "twins/reference-917-engine/clean-sheet-2026-f32.json",
        "sha256": "485a381b26f4d02da82d66b277e9e4ab16dbeaf7f72b5eb341b02304355ddfb4",
        "reuse_scope": "air_oil_variant_and_electronic_management_intent_only",
        "physical_validation_transferred": False,
    },
    {
        "id": "f33_cycle_thermal_contract",
        "path": "twins/reference-917-engine/clean-sheet-cycle-thermal-f33.json",
        "sha256": "6bbd5a5373660641c50e85dce6b45ac23222751d77f9f86783d82bd72530e73b",
        "reuse_scope": "semantic_air_oil_charge_chra_and_controls_topology_only",
        "head_liquid_loop_selection_transferred": False,
        "physical_validation_transferred": False,
    },
]

EXPECTED_DECISION = {
    "id": "F34A-AIR-OIL-CORE-2026-CONTROLS",
    "scope": "modern_flat12_thermal_and_controls_architecture",
    "selected_core_thermal_architecture": "strict_forced_air_and_dry_sump_oil_only",
    "selected_controls_architecture": "electronic_2026_requirements_only",
    "f33_hybrid_head_liquid_branch_disposition": (
        "not_selected_for_f34a_core_preserved_as_historical_hypothesis"
    ),
    "existing_f33_or_f34_artifacts_mutated": False,
    "decision_is_geometry": False,
    "decision_is_solver_result": False,
    "decision_is_physical_validation": False,
}

EXPECTED_AUTHORITY = {
    "architecture_requirements_only": True,
    "historical_replica_claimed": False,
    "hardware_selected": False,
    "operating_ranges_defined": False,
    "control_maps_available": False,
    "safety_thresholds_defined": False,
    "sensor_chains_calibrated": False,
    "hardwired_interlocks_verified": False,
    "thermal_solver_executed": False,
    "engine_bench_data_available": False,
    "target_power_used_as_validation": False,
    "target_power_proven": False,
    "ruf_compatibility_evaluated": False,
    "porsche_993_fitment_evaluated": False,
    "engine_operation_authorized": False,
    "manufacturing_authorized": False,
}

EXPECTED_CORE_COMPONENTS = ["crankcase", "cylinder_barrels", "cylinder_heads"]
EXPECTED_FORCED_AIR_TOPOLOGY = [
    "ambient_air_inlet",
    "fan",
    "bank_plenums",
    "head_and_cylinder_fins",
    "controlled_hot_air_discharge",
]
EXPECTED_OIL_TOPOLOGY = [
    "external_oil_tank",
    "pressure_stage",
    "filtered_main_gallery",
    "bearings_valvetrain_and_piston_jets",
    "distributed_sumps",
    "scavenge_stages",
    "deairation",
    "air_to_oil_heat_rejection",
    "external_oil_tank",
]

EXPECTED_AUXILIARY_CONSUMERS = {
    "charge_cooling": {
        "applicability": "forced_induction_variant_only",
        "authorization": "allowed_candidate_not_selected",
        "optional": False,
        "hardware_slot_ref": "U-F34A-CHARGE-COOLING-LOOP",
        "range_slot_ref": "U-F34A-CHARGE-COOLING-RANGES",
        "map_slot_ref": "U-F34A-CHARGE-COOLING-MAP",
    },
    "turbo_chra": {
        "applicability": "forced_induction_variant_only",
        "authorization": "optional_candidate_only_if_separate_chra_evidence_requires_it",
        "optional": True,
        "hardware_slot_ref": "U-F34A-CHRA-LIQUID-LOOP",
        "range_slot_ref": "U-F34A-CHRA-LIQUID-RANGES",
        "map_slot_ref": "U-F34A-CHRA-AFTER-RUN-MAP",
    },
}

EXPECTED_SENSOR_METADATA = {
    "crank_position": (
        "engine",
        "engine_position_and_speed",
        "independent_sync_plausibility_required",
    ),
    "cam_phase": (
        "each_actuated_camshaft",
        "sequential_phase_and_vvt_feedback",
        "cross_check_against_crank_required",
    ),
    "valve_lift_state": (
        "each_variable_lift_actuator",
        "variable_lift_state_feedback",
        "plausibility_requirement_unresolved",
    ),
    "pedal_position": (
        "driver_input",
        "dbw_driver_demand",
        "minimum_two_independent_channels",
    ),
    "throttle_position": (
        "each_throttle_actuator",
        "dbw_position_feedback",
        "minimum_two_independent_channels",
    ),
    "manifold_pressure": (
        "each_bank",
        "load_and_boost_observation",
        "safety_redundancy_unresolved",
    ),
    "charge_air_temperature": (
        "each_bank",
        "charge_state_observation",
        "safety_redundancy_unresolved",
    ),
    "lambda": (
        "each_control_zone",
        "closed_loop_combustion_mixture_observation",
        "safety_redundancy_unresolved",
    ),
    "knock": (
        "each_combustion_monitoring_zone",
        "crank_angle_windowed_cylinder_attributed_knock_observation",
        "coverage_and_redundancy_unresolved",
    ),
    "exhaust_gas_temperature": (
        "each_cylinder",
        "individual_cylinder_thermal_balance_observation",
        "coverage_and_redundancy_unresolved",
    ),
    "fuel_differential_pressure": (
        "each_fuel_rail_and_reference_manifold",
        "injector_differential_pressure_observation",
        "safety_redundancy_unresolved",
    ),
    "main_oil_pressure": (
        "main_gallery",
        "lubrication_safety_observation",
        "independent_hardwired_trip_channel_required",
    ),
    "oil_temperature": (
        "pressure_and_return_paths",
        "lubrication_and_heat_rejection_observation",
        "safety_redundancy_unresolved",
    ),
    "core_metal_temperature": (
        "each_cylinder_head",
        "per_cylinder_head_air_oil_core_thermal_observation",
        "coverage_and_redundancy_unresolved",
    ),
    "fan_speed": (
        "forced_air_fan",
        "forced_air_path_observation",
        "safety_redundancy_unresolved",
    ),
    "turbo_speed": (
        "each_turbo_candidate",
        "turbo_overspeed_observation",
        "safety_redundancy_unresolved",
    ),
    "wastegate_position": (
        "each_electronic_wastegate",
        "boost_actuator_feedback",
        "safety_redundancy_unresolved",
    ),
    "auxiliary_liquid_state": (
        "each_permitted_auxiliary_loop",
        "isolated_loop_pressure_temperature_and_flow_observation",
        "safety_redundancy_unresolved",
    ),
}

EXPECTED_INTERLOCK_METADATA = {
    "emergency_stop": (
        "dedicated_hardwired_input",
        "deenergize_fuel_ignition_and_dbw_torque_authority",
    ),
    "main_oil_pressure_loss": (
        "independent_main_oil_pressure_channel",
        "deenergize_fuel_and_ignition",
    ),
    "engine_overspeed": (
        "independent_engine_speed_channel",
        "deenergize_fuel_and_ignition",
    ),
    "dbw_plausibility_loss": (
        "independent_pedal_and_throttle_plausibility_monitor",
        "deenergize_dbw_torque_authority_and_inhibit_fuel",
    ),
    "turbo_overspeed": (
        "independent_turbo_speed_safety_channel",
        "deenergize_wastegates_and_inhibit_fuel",
    ),
}

EXPECTED_UNRESOLVED = {
    "U-F34A-FAN-HARDWARE": "hardware",
    "U-F34A-FAN-DRIVE": "hardware",
    "U-F34A-PLENUM-AND-BAFFLE-GEOMETRY": "hardware",
    "U-F34A-FORCED-AIR-RANGES": "range",
    "U-F34A-FAN-MAP": "map",
    "U-F34A-OIL-PRESSURE-PUMP": "hardware",
    "U-F34A-OIL-SCAVENGE-SYSTEM": "hardware",
    "U-F34A-PISTON-OIL-JETS": "hardware",
    "U-F34A-OIL-TANK-DEAIRATION": "hardware",
    "U-F34A-AIR-OIL-COOLER": "hardware",
    "U-F34A-OIL-SYSTEM-RANGES": "range",
    "U-F34A-OIL-PUMP-MAPS": "map",
    "U-F34A-CHARGE-COOLING-LOOP": "hardware",
    "U-F34A-CHARGE-COOLING-RANGES": "range",
    "U-F34A-CHARGE-COOLING-MAP": "map",
    "U-F34A-CHRA-LIQUID-LOOP": "hardware",
    "U-F34A-CHRA-LIQUID-RANGES": "range",
    "U-F34A-CHRA-AFTER-RUN-MAP": "map",
    "U-F34A-ECU-HARDWARE": "hardware",
    "U-F34A-ECU-FIRMWARE": "hardware",
    "U-F34A-ECU-IO-BUDGET": "range",
    "U-F34A-INJECTION-HARDWARE": "hardware",
    "U-F34A-INJECTION-RANGES": "range",
    "U-F34A-FUEL-MAPS": "map",
    "U-F34A-IGNITION-HARDWARE": "hardware",
    "U-F34A-IGNITION-RANGES": "range",
    "U-F34A-IGNITION-MAPS": "map",
    "U-F34A-DBW-HARDWARE": "hardware",
    "U-F34A-DBW-RANGES": "range",
    "U-F34A-DBW-MAPS": "map",
    "U-F34A-DBW-THRESHOLDS": "threshold",
    "U-F34A-VVT-VVL-HARDWARE": "hardware",
    "U-F34A-VVT-VVL-RANGES": "range",
    "U-F34A-VVT-VVL-MAPS": "map",
    "U-F34A-LAMBDA-HARDWARE": "hardware",
    "U-F34A-LAMBDA-RANGES": "range",
    "U-F34A-LAMBDA-MAPS": "map",
    "U-F34A-LAMBDA-THRESHOLDS": "threshold",
    "U-F34A-KNOCK-HARDWARE": "hardware",
    "U-F34A-KNOCK-RANGES": "range",
    "U-F34A-KNOCK-MAPS": "map",
    "U-F34A-KNOCK-THRESHOLDS": "threshold",
    "U-F34A-WASTEGATE-HARDWARE": "hardware",
    "U-F34A-WASTEGATE-RANGES": "range",
    "U-F34A-WASTEGATE-MAPS": "map",
    "U-F34A-WASTEGATE-THRESHOLDS": "threshold",
    "U-F34A-COMMS-HARDWARE": "hardware",
    "U-F34A-COMMS-SCHEMA": "schema",
    "U-F34A-SAFETY-THRESHOLDS": "threshold",
}

EXPECTED_TECHNICAL_GATES = {
    "core_geometry_defined",
    "forced_air_network_solved",
    "dry_sump_oil_network_solved",
    "auxiliary_liquid_isolation_verified",
    "controls_hardware_selected",
    "control_maps_available",
    "vvt_vvl_hardware_selected",
    "vvt_vvl_maps_available",
    "lambda_closed_loop_calibrated",
    "knock_control_calibrated",
    "boost_failsafe_validated",
    "communications_architecture_validated",
    "sensor_chains_calibrated",
    "safety_thresholds_validated",
    "hardwired_interlocks_verified",
}

EXPECTED_RELEASE_GATES = {
    "architecture_physically_validated",
    "air_cooling_validated",
    "oil_system_validated",
    "auxiliary_liquid_system_validated",
    "controls_and_logging_validated",
    "vvt_vvl_validated",
    "lambda_control_validated",
    "knock_control_validated",
    "boost_control_validated",
    "communications_validated",
    "engine_bench_start_authorized",
    "target_power_proven",
    "ruf_compatibility_validated",
    "porsche_993_fitment_validated",
    "vehicle_installation_authorized",
    "metal_print_authorized",
    "manufacturing_authorized",
}

EXPECTED_PROHIBITED_CLAIMS = [
    "ruf_compatibility_or_validation",
    "1600_hp_achieved_simulated_or_validated",
    "validated_air_oil_engine_cooling",
    "validated_controls_logging_or_safety",
    "validated_porsche_993_fitment_or_installation",
    "safe_for_engine_operation",
    "ready_for_metal_print_or_manufacturing",
]

TOP_LEVEL_KEYS = {
    "$comment",
    "schema_version",
    "phase",
    "status",
    "parents",
    "decision",
    "authority_boundary",
    "engine_core_boundary",
    "forced_air_architecture",
    "dry_sump_oil_architecture",
    "auxiliary_liquid_boundary",
    "controls_architecture",
    "sensor_registry",
    "logging_architecture",
    "hardwired_interlocks",
    "unresolved_registry",
    "technical_gates",
    "release_gates",
    "prohibited_claims",
}

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant rejected: {value}")


def _read_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=_reject_constant,
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _unexpected_keys(value: Any, expected: set[str], label: str) -> list[str]:
    if not isinstance(value, dict):
        return [f"{label}_not_object"]
    actual = set(value)
    return [f"unexpected_key:{label}.{key}" for key in sorted(actual - expected)] + [
        f"missing_key:{label}.{key}" for key in sorted(expected - actual)
    ]


def _exact(value: Any, expected: Any) -> bool:
    return type(value) is type(expected) and value == expected


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _safe_file(root: Path, relative: Any) -> Path | None:
    if not isinstance(relative, str) or not relative:
        return None
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        return None
    unresolved = root
    for part in rel.parts:
        unresolved = unresolved / part
        if unresolved.is_symlink():
            return None
    candidate = unresolved.resolve()
    resolved_root = root.resolve()
    if not _inside(candidate, resolved_root):
        return None
    if not candidate.is_file() or candidate.is_symlink():
        return None
    return candidate


def _validate_exact_mapping(
    value: Any,
    expected: dict[str, Any],
    label: str,
    errors: list[str],
) -> None:
    errors.extend(_unexpected_keys(value, set(expected), label))
    if not isinstance(value, dict):
        return
    for key, expected_value in expected.items():
        if key in value and not _exact(value[key], expected_value):
            errors.append(f"value_invalid:{label}.{key}")


def _validate_parents(contract: dict[str, Any], root: Path, errors: list[str]) -> None:
    parents = contract.get("parents")
    if not isinstance(parents, list) or len(parents) != len(EXPECTED_PARENTS):
        errors.append("parents_invalid")
        return
    for index, expected in enumerate(EXPECTED_PARENTS):
        parent = parents[index]
        _validate_exact_mapping(parent, expected, f"parents[{index}]", errors)
        if not isinstance(parent, dict):
            continue
        path = parent.get("path")
        digest = parent.get("sha256")
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            errors.append(f"parent_sha_format_invalid:{index}")
            continue
        resolved = _safe_file(root, path)
        if resolved is None:
            errors.append(f"parent_path_missing_or_unsafe:{index}")
        elif _sha256(resolved) != digest:
            errors.append(f"parent_sha_mismatch:{index}")


def _validate_core(contract: dict[str, Any], errors: list[str]) -> None:
    core = contract.get("engine_core_boundary")
    keys = {
        "id",
        "included_components",
        "core_liquid_coolant_loop_present",
        "core_to_auxiliary_liquid_cross_connection_allowed",
        "oil_to_auxiliary_liquid_heat_exchanger_allowed",
        "external_air_and_oil_surfaces_geometry_ref",
        "thermal_network_ref",
        "physically_validated",
    }
    errors.extend(_unexpected_keys(core, keys, "engine_core_boundary"))
    if not isinstance(core, dict):
        return
    fixed = {
        "id": "strict_air_oil_engine_core",
        "core_liquid_coolant_loop_present": False,
        "core_to_auxiliary_liquid_cross_connection_allowed": False,
        "oil_to_auxiliary_liquid_heat_exchanger_allowed": False,
        "external_air_and_oil_surfaces_geometry_ref": None,
        "thermal_network_ref": None,
        "physically_validated": False,
    }
    for key, expected in fixed.items():
        if not _exact(core.get(key), expected):
            errors.append(f"core_boundary_value_invalid:{key}")
    components = core.get("included_components")
    if not isinstance(components, list) or len(components) != 3:
        errors.append("core_components_invalid")
        return
    if [item.get("id") if isinstance(item, dict) else None for item in components] != EXPECTED_CORE_COMPONENTS:
        errors.append("core_component_ids_invalid")
    component_keys = {
        "id",
        "permitted_heat_transfer_media",
        "liquid_coolant_jacket_allowed",
        "liquid_coolant_cavity_allowed",
        "liquid_coolant_passage_geometry_authorized",
    }
    for index, component in enumerate(components):
        errors.extend(_unexpected_keys(component, component_keys, f"engine_core_boundary.included_components[{index}]"))
        if not isinstance(component, dict):
            continue
        if component.get("permitted_heat_transfer_media") != ["forced_air", "dry_sump_oil"]:
            errors.append(f"core_media_invalid:{index}")
        for key in (
            "liquid_coolant_jacket_allowed",
            "liquid_coolant_cavity_allowed",
            "liquid_coolant_passage_geometry_authorized",
        ):
            if component.get(key) is not False:
                errors.append(f"core_liquid_prohibition_invalid:{index}:{key}")


def _validate_air_and_oil(contract: dict[str, Any], errors: list[str]) -> None:
    air = contract.get("forced_air_architecture")
    air_keys = {
        "required",
        "topology",
        "fan_required",
        "bank_plenums_required",
        "head_fins_required",
        "cylinder_fins_required",
        "baffles_and_seals_required",
        "uniformity_and_local_hotspot_assessment_required",
        "hardware_slot_refs",
        "range_slot_refs",
        "map_slot_refs",
        "solver_ready",
        "physically_validated",
    }
    errors.extend(_unexpected_keys(air, air_keys, "forced_air_architecture"))
    if isinstance(air, dict):
        if air.get("topology") != EXPECTED_FORCED_AIR_TOPOLOGY:
            errors.append("forced_air_topology_invalid")
        for key in (
            "required",
            "fan_required",
            "bank_plenums_required",
            "head_fins_required",
            "cylinder_fins_required",
            "baffles_and_seals_required",
            "uniformity_and_local_hotspot_assessment_required",
        ):
            if air.get(key) is not True:
                errors.append(f"forced_air_requirement_invalid:{key}")
        if air.get("hardware_slot_refs") != [
            "U-F34A-FAN-HARDWARE",
            "U-F34A-FAN-DRIVE",
            "U-F34A-PLENUM-AND-BAFFLE-GEOMETRY",
        ]:
            errors.append("forced_air_hardware_slots_invalid")
        if air.get("range_slot_refs") != ["U-F34A-FORCED-AIR-RANGES"]:
            errors.append("forced_air_range_slots_invalid")
        if air.get("map_slot_refs") != ["U-F34A-FAN-MAP"]:
            errors.append("forced_air_map_slots_invalid")
        if air.get("solver_ready") is not False or air.get("physically_validated") is not False:
            errors.append("forced_air_gates_invalid")

    oil = contract.get("dry_sump_oil_architecture")
    oil_keys = {
        "required",
        "topology",
        "pressure_stage_required",
        "scavenge_stages_required",
        "deairation_required",
        "filtration_required",
        "piston_underside_oil_jets_required",
        "air_to_oil_heat_rejection_required",
        "liquid_to_oil_heat_rejection_allowed",
        "hardware_slot_refs",
        "range_slot_refs",
        "map_slot_refs",
        "solver_ready",
        "physically_validated",
    }
    errors.extend(_unexpected_keys(oil, oil_keys, "dry_sump_oil_architecture"))
    if isinstance(oil, dict):
        if oil.get("topology") != EXPECTED_OIL_TOPOLOGY:
            errors.append("dry_sump_topology_invalid")
        for key in (
            "required",
            "pressure_stage_required",
            "scavenge_stages_required",
            "deairation_required",
            "filtration_required",
            "piston_underside_oil_jets_required",
            "air_to_oil_heat_rejection_required",
        ):
            if oil.get(key) is not True:
                errors.append(f"dry_sump_requirement_invalid:{key}")
        if oil.get("liquid_to_oil_heat_rejection_allowed") is not False:
            errors.append("dry_sump_liquid_heat_rejection_must_be_false")
        expected_slots = [
            "U-F34A-OIL-PRESSURE-PUMP",
            "U-F34A-OIL-SCAVENGE-SYSTEM",
            "U-F34A-PISTON-OIL-JETS",
            "U-F34A-OIL-TANK-DEAIRATION",
            "U-F34A-AIR-OIL-COOLER",
        ]
        if oil.get("hardware_slot_refs") != expected_slots:
            errors.append("dry_sump_hardware_slots_invalid")
        if oil.get("range_slot_refs") != ["U-F34A-OIL-SYSTEM-RANGES"]:
            errors.append("dry_sump_range_slots_invalid")
        if oil.get("map_slot_refs") != ["U-F34A-OIL-PUMP-MAPS"]:
            errors.append("dry_sump_map_slots_invalid")
        if oil.get("solver_ready") is not False or oil.get("physically_validated") is not False:
            errors.append("dry_sump_gates_invalid")


def _validate_auxiliary_liquid(contract: dict[str, Any], errors: list[str]) -> None:
    auxiliary = contract.get("auxiliary_liquid_boundary")
    keys = {
        "hydraulically_isolated_from_engine_core_required",
        "shared_core_cavity_allowed",
        "shared_core_manifold_allowed",
        "core_cross_connection_allowed",
        "allowed_consumers",
        "all_other_liquid_consumers_forbidden",
        "liquid_medium_selected",
        "leak_containment_design_ref",
        "isolation_test_ref",
        "physically_validated",
    }
    errors.extend(_unexpected_keys(auxiliary, keys, "auxiliary_liquid_boundary"))
    if not isinstance(auxiliary, dict):
        return
    fixed = {
        "hydraulically_isolated_from_engine_core_required": True,
        "shared_core_cavity_allowed": False,
        "shared_core_manifold_allowed": False,
        "core_cross_connection_allowed": False,
        "all_other_liquid_consumers_forbidden": True,
        "liquid_medium_selected": None,
        "leak_containment_design_ref": None,
        "isolation_test_ref": None,
        "physically_validated": False,
    }
    for key, expected in fixed.items():
        if not _exact(auxiliary.get(key), expected):
            errors.append(f"auxiliary_liquid_value_invalid:{key}")
    consumers = auxiliary.get("allowed_consumers")
    if not isinstance(consumers, list) or len(consumers) != 2:
        errors.append("auxiliary_consumers_invalid")
        return
    ids = [item.get("id") if isinstance(item, dict) else None for item in consumers]
    if ids != list(EXPECTED_AUXILIARY_CONSUMERS):
        errors.append("auxiliary_consumer_ids_invalid")
    keys = {
        "id",
        "applicability",
        "authorization",
        "optional",
        "isolation_validation_complete",
        "hardware_slot_ref",
        "range_slot_ref",
        "map_slot_ref",
    }
    for index, consumer in enumerate(consumers):
        errors.extend(_unexpected_keys(consumer, keys, f"auxiliary_liquid_boundary.allowed_consumers[{index}]"))
        if not isinstance(consumer, dict):
            continue
        consumer_id = consumer.get("id")
        expected = EXPECTED_AUXILIARY_CONSUMERS.get(consumer_id)
        if expected is None:
            continue
        for key, expected_value in expected.items():
            if not _exact(consumer.get(key), expected_value):
                errors.append(f"auxiliary_consumer_value_invalid:{consumer_id}:{key}")
        if consumer.get("isolation_validation_complete") is not False:
            errors.append(f"auxiliary_consumer_isolation_gate_invalid:{consumer_id}")


def _validate_controls(contract: dict[str, Any], errors: list[str]) -> None:
    controls = contract.get("controls_architecture")
    expected_sections = {
        "ecu",
        "fuel_injection",
        "ignition",
        "drive_by_wire",
        "valvetrain_control",
        "lambda_control",
        "knock_control",
        "wastegates",
        "communications",
    }
    errors.extend(_unexpected_keys(controls, expected_sections, "controls_architecture"))
    if not isinstance(controls, dict):
        return

    ecu = controls.get("ecu")
    ecu_expected = {
        "requirement": "programmable_engine_control_unit_with_deterministic_crank_angle_scheduling",
        "hardware_slot_ref": "U-F34A-ECU-HARDWARE",
        "firmware_slot_ref": "U-F34A-ECU-FIRMWARE",
        "io_budget_slot_ref": "U-F34A-ECU-IO-BUDGET",
        "selected": False,
        "validated": False,
    }
    _validate_exact_mapping(ecu, ecu_expected, "controls_architecture.ecu", errors)

    injection_expected = {
        "mode_requirement": "sequential_electronic_port_injection",
        "staged_port_injection_candidate": True,
        "minimum_independent_channels": 12,
        "target_independent_channels": 24,
        "channel_counts_are_hardware_or_calibration_proof": False,
        "hardware_slot_ref": "U-F34A-INJECTION-HARDWARE",
        "range_slot_ref": "U-F34A-INJECTION-RANGES",
        "map_slot_ref": "U-F34A-FUEL-MAPS",
        "selected": False,
        "validated": False,
    }
    _validate_exact_mapping(
        controls.get("fuel_injection"),
        injection_expected,
        "controls_architecture.fuel_injection",
        errors,
    )

    ignition_expected = {
        "mode_requirement": "dual_electronic_ignition",
        "spark_plugs_per_cylinder": 2,
        "independent_channels_required": 24,
        "channel_count_is_hardware_or_calibration_proof": False,
        "hardware_slot_ref": "U-F34A-IGNITION-HARDWARE",
        "range_slot_ref": "U-F34A-IGNITION-RANGES",
        "map_slot_ref": "U-F34A-IGNITION-MAPS",
        "selected": False,
        "validated": False,
    }
    _validate_exact_mapping(
        controls.get("ignition"),
        ignition_expected,
        "controls_architecture.ignition",
        errors,
    )

    dbw_expected = {
        "mode_requirement": "redundant_electronic_throttle_control",
        "actuator_count_minimum": 2,
        "one_actuator_per_bank_required": True,
        "pedal_position_channels_minimum": 2,
        "throttle_position_channels_minimum": 2,
        "independent_plausibility_monitor_required": True,
        "deenergized_safe_state_required": True,
        "hardware_slot_ref": "U-F34A-DBW-HARDWARE",
        "range_slot_ref": "U-F34A-DBW-RANGES",
        "map_slot_ref": "U-F34A-DBW-MAPS",
        "threshold_slot_ref": "U-F34A-DBW-THRESHOLDS",
        "selected": False,
        "validated": False,
    }
    _validate_exact_mapping(
        controls.get("drive_by_wire"),
        dbw_expected,
        "controls_architecture.drive_by_wire",
        errors,
    )

    valvetrain_expected = {
        "mode_requirement": "electronic_variable_cam_timing_with_variable_lift_candidate",
        "variable_cam_timing_candidate": True,
        "variable_valve_lift_candidate": True,
        "actuated_camshaft_count_unresolved": True,
        "closed_loop_position_feedback_required": True,
        "hardware_slot_ref": "U-F34A-VVT-VVL-HARDWARE",
        "range_slot_ref": "U-F34A-VVT-VVL-RANGES",
        "map_slot_ref": "U-F34A-VVT-VVL-MAPS",
        "selected": False,
        "validated": False,
    }
    _validate_exact_mapping(
        controls.get("valvetrain_control"),
        valvetrain_expected,
        "controls_architecture.valvetrain_control",
        errors,
    )

    lambda_expected = {
        "mode_requirement": "closed_loop_wideband_lambda_control",
        "closed_loop_required": True,
        "minimum_control_zones": 2,
        "per_cylinder_trim_candidate": True,
        "hardware_slot_ref": "U-F34A-LAMBDA-HARDWARE",
        "range_slot_ref": "U-F34A-LAMBDA-RANGES",
        "map_slot_ref": "U-F34A-LAMBDA-MAPS",
        "threshold_slot_ref": "U-F34A-LAMBDA-THRESHOLDS",
        "selected": False,
        "validated": False,
    }
    _validate_exact_mapping(
        controls.get("lambda_control"),
        lambda_expected,
        "controls_architecture.lambda_control",
        errors,
    )

    knock_expected = {
        "mode_requirement": "crank_angle_windowed_cylinder_attributed_knock_control",
        "closed_loop_ignition_retard_candidate": True,
        "sensor_channel_count_unresolved": True,
        "hardware_slot_ref": "U-F34A-KNOCK-HARDWARE",
        "range_slot_ref": "U-F34A-KNOCK-RANGES",
        "map_slot_ref": "U-F34A-KNOCK-MAPS",
        "threshold_slot_ref": "U-F34A-KNOCK-THRESHOLDS",
        "selected": False,
        "validated": False,
    }
    _validate_exact_mapping(
        controls.get("knock_control"),
        knock_expected,
        "controls_architecture.knock_control",
        errors,
    )

    wastegate_expected = {
        "applicability": "forced_induction_variant_only",
        "mode_requirement": "electronic_wastegate_actuation",
        "independent_closed_loop_per_actuator_required": True,
        "position_feedback_required": True,
        "deenergized_safe_open_state_required": True,
        "sensor_or_actuator_fault_action_requirement": (
            "remove_boost_authority_and_return_to_spring_pressure"
        ),
        "hardware_slot_ref": "U-F34A-WASTEGATE-HARDWARE",
        "range_slot_ref": "U-F34A-WASTEGATE-RANGES",
        "map_slot_ref": "U-F34A-WASTEGATE-MAPS",
        "threshold_slot_ref": "U-F34A-WASTEGATE-THRESHOLDS",
        "selected": False,
        "validated": False,
    }
    _validate_exact_mapping(
        controls.get("wastegates"),
        wastegate_expected,
        "controls_architecture.wastegates",
        errors,
    )

    communications_expected = {
        "mode_requirement": "can_fd_for_control_diagnostics_and_synchronized_logging",
        "can_fd_required": True,
        "network_redundancy_requirement": (
            "safety_and_logging_partitioning_to_be_defined"
        ),
        "hardware_slot_ref": "U-F34A-COMMS-HARDWARE",
        "schema_slot_ref": "U-F34A-COMMS-SCHEMA",
        "selected": False,
        "validated": False,
    }
    _validate_exact_mapping(
        controls.get("communications"),
        communications_expected,
        "controls_architecture.communications",
        errors,
    )


def _validate_sensors_logging_and_interlocks(
    contract: dict[str, Any], errors: list[str]
) -> None:
    sensors = contract.get("sensor_registry")
    if not isinstance(sensors, list) or len(sensors) != len(EXPECTED_SENSOR_METADATA):
        errors.append("sensor_registry_invalid")
    else:
        ids = [item.get("id") if isinstance(item, dict) else None for item in sensors]
        if ids != list(EXPECTED_SENSOR_METADATA):
            errors.append("sensor_ids_invalid")
        sensor_keys = {
            "id",
            "scope",
            "purpose",
            "redundancy_requirement",
            "hardware_ref",
            "operating_range",
            "calibration_ref",
            "status",
        }
        for index, sensor in enumerate(sensors):
            errors.extend(_unexpected_keys(sensor, sensor_keys, f"sensor_registry[{index}]"))
            if not isinstance(sensor, dict):
                continue
            sensor_id = sensor.get("id")
            expected = EXPECTED_SENSOR_METADATA.get(sensor_id)
            if expected is not None and (
                sensor.get("scope"),
                sensor.get("purpose"),
                sensor.get("redundancy_requirement"),
            ) != expected:
                errors.append(f"sensor_metadata_invalid:{sensor_id}")
            for key in ("hardware_ref", "operating_range", "calibration_ref"):
                if sensor.get(key) is not None:
                    errors.append(f"sensor_evidence_must_be_null:{sensor_id}:{key}")
            if sensor.get("status") != "blocked_missing_evidence":
                errors.append(f"sensor_status_invalid:{sensor_id}")

    logging = contract.get("logging_architecture")
    logging_expected = {
        "required": True,
        "source": "sensor_registry_and_control_state",
        "monotonic_timestamp_required": True,
        "command_feedback_and_fault_state_required": True,
        "data_loss_detection_required": True,
        "logger_hardware_ref": None,
        "schema_ref": None,
        "sample_rate_plan": None,
        "retention_plan": None,
        "time_sync_evidence_ref": None,
        "status": "blocked_missing_evidence",
    }
    _validate_exact_mapping(logging, logging_expected, "logging_architecture", errors)

    interlocks = contract.get("hardwired_interlocks")
    if not isinstance(interlocks, list) or len(interlocks) != len(EXPECTED_INTERLOCK_METADATA):
        errors.append("hardwired_interlocks_invalid")
        return
    ids = [item.get("id") if isinstance(item, dict) else None for item in interlocks]
    if ids != list(EXPECTED_INTERLOCK_METADATA):
        errors.append("hardwired_interlock_ids_invalid")
    keys = {
        "id",
        "trigger_source",
        "action_requirement",
        "ecu_override_allowed",
        "hardware_ref",
        "threshold",
        "logic_ref",
        "verification_ref",
        "status",
    }
    for index, interlock in enumerate(interlocks):
        errors.extend(_unexpected_keys(interlock, keys, f"hardwired_interlocks[{index}]"))
        if not isinstance(interlock, dict):
            continue
        interlock_id = interlock.get("id")
        expected = EXPECTED_INTERLOCK_METADATA.get(interlock_id)
        if expected is not None and (
            interlock.get("trigger_source"),
            interlock.get("action_requirement"),
        ) != expected:
            errors.append(f"hardwired_interlock_metadata_invalid:{interlock_id}")
        if interlock.get("ecu_override_allowed") is not False:
            errors.append(f"hardwired_interlock_override_invalid:{interlock_id}")
        for key in ("hardware_ref", "threshold", "logic_ref", "verification_ref"):
            if interlock.get(key) is not None:
                errors.append(f"hardwired_interlock_evidence_must_be_null:{interlock_id}:{key}")
        if interlock.get("status") != "blocked_missing_evidence":
            errors.append(f"hardwired_interlock_status_invalid:{interlock_id}")


def _collect_slot_refs(value: Any, found: list[tuple[str, str]]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key.endswith("_slot_ref") and isinstance(child, str):
                kind = key.removesuffix("_slot_ref")
                found.append((kind, child))
            elif key.endswith("_slot_refs") and isinstance(child, list):
                kind = key.removesuffix("_slot_refs")
                for item in child:
                    if isinstance(item, str):
                        found.append((kind, item))
            _collect_slot_refs(child, found)
    elif isinstance(value, list):
        for child in value:
            _collect_slot_refs(child, found)


def _validate_unresolved(contract: dict[str, Any], errors: list[str]) -> None:
    unresolved = contract.get("unresolved_registry")
    if not isinstance(unresolved, list) or len(unresolved) != len(EXPECTED_UNRESOLVED):
        errors.append("unresolved_registry_invalid")
        return
    ids = [item.get("id") if isinstance(item, dict) else None for item in unresolved]
    if ids != list(EXPECTED_UNRESOLVED):
        errors.append("unresolved_ids_invalid")
    keys = {"id", "kind", "value", "evidence_ref", "status"}
    for index, item in enumerate(unresolved):
        errors.extend(_unexpected_keys(item, keys, f"unresolved_registry[{index}]"))
        if not isinstance(item, dict):
            continue
        item_id = item.get("id")
        if item.get("kind") != EXPECTED_UNRESOLVED.get(item_id):
            errors.append(f"unresolved_kind_invalid:{item_id}")
        if item.get("value") is not None or item.get("evidence_ref") is not None:
            errors.append(f"unresolved_value_or_evidence_must_be_null:{item_id}")
        if item.get("status") != "blocked_missing_evidence":
            errors.append(f"unresolved_status_invalid:{item_id}")

    refs: list[tuple[str, str]] = []
    for section in (
        "forced_air_architecture",
        "dry_sump_oil_architecture",
        "auxiliary_liquid_boundary",
        "controls_architecture",
    ):
        _collect_slot_refs(contract.get(section), refs)
    kind_aliases = {"firmware": "hardware", "io_budget": "range"}
    for kind, ref in refs:
        expected_kind = kind_aliases.get(kind, kind)
        if ref not in EXPECTED_UNRESOLVED:
            errors.append(f"unknown_unresolved_slot_ref:{ref}")
        elif EXPECTED_UNRESOLVED[ref] != expected_kind:
            errors.append(f"unresolved_slot_kind_mismatch:{ref}:{expected_kind}")
    referenced = {ref for _, ref in refs}
    exempt = {"U-F34A-SAFETY-THRESHOLDS"}
    if referenced | exempt != set(EXPECTED_UNRESOLVED):
        errors.append("unresolved_registry_reference_coverage_invalid")


def _validate_gates_and_claims(contract: dict[str, Any], errors: list[str]) -> None:
    technical = contract.get("technical_gates")
    errors.extend(_unexpected_keys(technical, EXPECTED_TECHNICAL_GATES, "technical_gates"))
    if isinstance(technical, dict) and any(value is not False for value in technical.values()):
        errors.append("technical_gates_must_all_be_false")
    release = contract.get("release_gates")
    errors.extend(_unexpected_keys(release, EXPECTED_RELEASE_GATES, "release_gates"))
    if isinstance(release, dict) and any(value is not False for value in release.values()):
        errors.append("release_gates_must_all_be_false")
    if contract.get("prohibited_claims") != EXPECTED_PROHIBITED_CLAIMS:
        errors.append("prohibited_claims_invalid")


def validate_contract(contract: Any, project_root: Path = ROOT) -> list[str]:
    """Return every fail-closed validation error for the F34a decision."""

    if not isinstance(contract, dict):
        return ["contract_not_object"]
    errors = _unexpected_keys(contract, TOP_LEVEL_KEYS, "contract")
    fixed = {
        "schema_version": "1.0.0",
        "phase": "F34a",
        "status": "architecture_decision_only_all_hardware_calibration_safety_and_release_gates_blocked",
    }
    for key, expected in fixed.items():
        if not _exact(contract.get(key), expected):
            errors.append(f"top_level_value_invalid:{key}")
    if not isinstance(contract.get("$comment"), str) or not contract["$comment"]:
        errors.append("comment_invalid")
    _validate_parents(contract, project_root, errors)
    _validate_exact_mapping(contract.get("decision"), EXPECTED_DECISION, "decision", errors)
    _validate_exact_mapping(
        contract.get("authority_boundary"),
        EXPECTED_AUTHORITY,
        "authority_boundary",
        errors,
    )
    _validate_core(contract, errors)
    _validate_air_and_oil(contract, errors)
    _validate_auxiliary_liquid(contract, errors)
    _validate_controls(contract, errors)
    _validate_sensors_logging_and_interlocks(contract, errors)
    _validate_unresolved(contract, errors)
    _validate_gates_and_claims(contract, errors)
    return sorted(set(errors))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=CONTRACT)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)
    try:
        contract = _read_json(args.contract)
        errors = validate_contract(contract, project_root=ROOT)
        if errors:
            raise ValueError("invalid F34a contract:\n- " + "\n- ".join(errors))
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(f"F34a contract error: {exc}", file=sys.stderr)
        return 2
    if not args.quiet:
        print("F34a air/oil core and controls decision contract valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
