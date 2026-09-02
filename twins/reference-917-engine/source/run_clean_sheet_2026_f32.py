#!/usr/bin/env python3
"""Run the F32 clean-sheet 2026 algebraic screening model.

The model closes arithmetic identities and a declared heat split.  It is not an
engine-cycle solver, a turbo-map match, CFD, CHT, FEA or dyno evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONTRACT = ROOT / "twins/reference-917-engine/clean-sheet-2026-f32.json"
DEFAULT_OUTPUT = ROOT / "work/917-clean-sheet-2026-f32/screening-report.json"
MECHANICAL_HP_TO_W = 745.6998715822702
POUND_TO_KG = 0.45359237
REQUIRED_VARIANTS = {
    "917_2026_hybrid_head_liquid_air_oil_cylinders",
    "917_2026_air_oil_engine_air_air_charge",
}
EXPECTED_PROGRAM_ID = "917_2026_turbo_1600hp_clean_sheet"
EXPECTED_DESIGN_INTENT = "modern_2026_flat12_twin_turbo_test_bench_then_porsche_911_993_integration"
EXPECTED_SCAN_ROLE = "external_reference_and_packaging_context_only"
EXPECTED_CONVERSION_BASELINE = "new_dedicated_hybrid_multiloop_system_not_a_stock_993_system"
EXPECTED_UPSTREAM_LAYOUT = "twins/reference-917-engine/parametric-layout-authoring-f30.template.json"
EXPECTED_UPSTREAM_HEAD = "twins/reference-917-engine/clean-sheet-cylinder-head-f29.json"
EXPECTED_UPSTREAM_HEAD_REFERENCE_CAE = "twins/reference-917-engine/head-reference-cae-f31.json"
REQUIRED_993_SOURCE_IDS = {
    "SRC-PORSCHE-NEWSROOM-993",
    "SRC-PORSCHE-PET-993",
}
REQUIRED_ALLOWED_CLAIMS = {
    "algebraic_power_torque_bmep_identity",
    "declared_air_plus_fuel_mass_identity_and_residual_energy_partition",
    "comparison_against_declared_thermal_load_limits",
}
REQUIRED_FORBIDDEN_CLAIMS = {
    "historically_accurate_porsche_917_replica",
    "validated_1600_hp_engine",
    "validated_turbo_match",
    "validated_liquid_or_air_oil_cooling_system",
    "porsche_993_fitment",
    "safe_for_engine_operation",
    "ready_for_metal_print",
}
REQUIRED_RELEASE_GATES = {
    "target_definition_complete",
    "target_power_proven",
    "mass_and_energy_balance_validated",
    "thermodynamic_cycle_validated",
    "turbo_match_validated",
    "combustion_and_knock_validated",
    "cooling_system_validated",
    "oil_system_validated",
    "structural_and_fatigue_validated",
    "controls_and_overspeed_protection_validated",
    "test_bench_start_authorized",
    "porsche_993_packaging_validated",
    "porsche_993_vehicle_installation_authorized",
    "held_out_physical_correlation_complete",
    "metal_print_authorized",
    "manufacturing_authorized",
}
REQUIRED_993_INTEGRATION_EVIDENCE_KEYS = {
    "engine_bay_envelope_and_uncertainty",
    "powertrain_mass_and_center_of_gravity",
    "rear_axle_load_budget",
    "mount_and_body_load_paths",
    "transaxle_torque_capacity_and_durability",
    "radiator_core_and_duct_packaging",
    "coolant_pipe_routes_and_bleed_strategy",
    "oil_tank_pump_and_cooler_package",
    "charge_cooler_and_plenum_package",
    "exhaust_turbo_and_firewall_clearances",
    "fuel_electrical_ecu_and_safety_architecture",
    "braking_suspension_tyre_and_chassis_validation",
    "road_approval_and_insurance_basis",
}
REQUIRED_NEXT_SOLVER_EVIDENCE_KEYS = {
    "mechanical_hp_and_accessory_boundary",
    "duty_cycle_and_1600hp_duration",
    "ambient_altitude_and_vehicle_speed_envelope",
    "fuel_specification_and_batch_certificate",
    "one_dimensional_engine_cycle_model",
    "measured_combustion_or_calibration_dataset",
    "digitized_compressor_and_turbine_maps",
    "turbo_bearing_housing_thermal_load_and_hot_soak",
    "three_dimensional_intake_and_exhaust_cfd",
    "conjugate_heat_transfer_model",
    "head_case_crank_rod_piston_and_mount_fea",
    "oil_and_coolant_network_model",
    "vehicle_underhood_and_radiator_airflow_cfd",
    "instrumented_test_bench_plan",
    "held_out_physical_correlation_dataset",
}


def _is_positive_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and value > 0.0
    )


def _canonical_bytes(payload: Any) -> bytes:
    return (
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n"
    ).encode("utf-8")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _round_floats(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 9)
    if isinstance(value, list):
        return [_round_floats(item) for item in value]
    if isinstance(value, dict):
        return {key: _round_floats(item) for key, item in value.items()}
    return value


def _known_source_ids() -> set[str]:
    source_ids: set[str] = set()
    for path in (ROOT / "catalog/sources").glob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict) and isinstance(payload.get("source_id"), str):
            source_ids.add(payload["source_id"])
    return source_ids


def _all_none(value: Any) -> bool:
    if isinstance(value, dict):
        return bool(value) and all(_all_none(item) for item in value.values())
    return value is None


def validate_contract(contract: Any) -> list[str]:
    if not isinstance(contract, dict):
        return ["root: expected object"]

    errors: list[str] = []
    if contract.get("schema_version") != "1.0.0":
        errors.append("schema_version: expected 1.0.0")
    if contract.get("phase") != "F32":
        errors.append("phase: expected F32")
    if contract.get("status") != "clean_sheet_2026_algebraic_screening_only_all_release_gates_blocked":
        errors.append("status: unexpected F32 status")

    program = contract.get("program")
    if not isinstance(program, dict):
        errors.append("program: expected object")
    else:
        if program.get("id") != EXPECTED_PROGRAM_ID:
            errors.append(f"program.id: expected {EXPECTED_PROGRAM_ID}")
        if program.get("design_intent") != EXPECTED_DESIGN_INTENT:
            errors.append("program.design_intent: unexpected design intent")
        if program.get("scan_role") != EXPECTED_SCAN_ROLE:
            errors.append("program.scan_role: unexpected scan authority")
        target = program.get("target_power")
        if not isinstance(target, dict):
            errors.append("program.target_power: expected object")
        else:
            if target.get("value") != 1600.0 or target.get("unit") != "mechanical_hp":
                errors.append("program.target_power: expected exactly 1600 mechanical hp")
            if target.get("origin") != "user_design_requirement":
                errors.append("program.target_power.origin: expected user_design_requirement")
            for flag in ("measured", "simulated", "proven"):
                if target.get(flag) is not False:
                    errors.append(f"program.target_power.{flag}: must remain false")
        if program.get("historical_replica") is not False:
            errors.append("program.historical_replica: must remain false")
        if program.get("historical_geometry_authority") is not False:
            errors.append("program.historical_geometry_authority: must remain false")
        if program.get("target_vehicle") != "porsche_911_type_993_shell":
            errors.append("program.target_vehicle: expected porsche_911_type_993_shell")

    boundary = contract.get("authority_boundary")
    if not isinstance(boundary, dict):
        errors.append("authority_boundary: expected object")
    else:
        if boundary.get("upstream_layout_contract") != EXPECTED_UPSTREAM_LAYOUT:
            errors.append("authority_boundary.upstream_layout_contract: unexpected path")
        if boundary.get("upstream_head_study") != EXPECTED_UPSTREAM_HEAD:
            errors.append("authority_boundary.upstream_head_study: unexpected path")
        if boundary.get("upstream_head_reference_cae") != EXPECTED_UPSTREAM_HEAD_REFERENCE_CAE:
            errors.append("authority_boundary.upstream_head_reference_cae: unexpected path")
        if boundary.get("upstream_head_reference_cae_role") != (
            "non_correlated_reference_solver_screening_only"
        ):
            errors.append("authority_boundary.upstream_head_reference_cae_role: unexpected authority")
        if boundary.get("f31_head_reference_cae_released_for_engine_operation") is not False:
            errors.append(
                "authority_boundary.f31_head_reference_cae_released_for_engine_operation: must remain false"
            )
        if boundary.get("f29_or_f30_geometry_released_for_engine_operation") is not False:
            errors.append("authority_boundary.f29_or_f30_geometry_released_for_engine_operation: must remain false")
        allowed_claims = boundary.get("allowed_claims")
        if (
            not isinstance(allowed_claims, list)
            or len(allowed_claims) != len(REQUIRED_ALLOWED_CLAIMS)
            or set(allowed_claims) != REQUIRED_ALLOWED_CLAIMS
        ):
            errors.append("authority_boundary.allowed_claims: expected exact F32 claim registry")
        forbidden_claims = boundary.get("forbidden_claims")
        if (
            not isinstance(forbidden_claims, list)
            or len(forbidden_claims) != len(REQUIRED_FORBIDDEN_CLAIMS)
            or set(forbidden_claims) != REQUIRED_FORBIDDEN_CLAIMS
        ):
            errors.append("authority_boundary.forbidden_claims: expected exact F32 prohibition registry")
        if boundary.get("f32_dimensions_classification") != "clean_sheet_design_hypotheses_for_screening_only":
            errors.append("authority_boundary.f32_dimensions_classification: unexpected classification")

    architecture = contract.get("architecture_seed")
    if not isinstance(architecture, dict):
        errors.append("architecture_seed: expected object")
    else:
        if architecture.get("classification") != "design_seed_not_measured_engine_geometry":
            errors.append("architecture_seed.classification: unexpected authority")
        exact_values = {
            "arrangement": "horizontally_opposed_flat12",
            "cycle": "four_stroke_spark_ignition",
            "cylinder_count": 12,
            "valves_per_cylinder": 4,
            "camshaft_count": 4,
            "turbocharger_count": 2,
            "turbo_arrangement": "one_per_bank_parallel",
            "lubrication": "dry_sump_multistage_hypothesis",
            "induction": "electronic_fuel_injection_and_closed_loop_boost_hypothesis",
        }
        for key, expected in exact_values.items():
            if architecture.get(key) != expected:
                errors.append(f"architecture_seed.{key}: expected {expected}")
        for field in ("bore_mm", "stroke_mm", "design_speed_rpm"):
            if not _is_positive_number(architecture.get(field)):
                errors.append(f"architecture_seed.{field}: expected positive number")

    air_fuel = contract.get("air_and_fuel_screening")
    if not isinstance(air_fuel, dict):
        errors.append("air_and_fuel_screening: expected object")
    else:
        if air_fuel.get("classification") != "sizing_hypotheses_not_calibration_data":
            errors.append("air_and_fuel_screening.classification: unexpected authority")
        numeric_fields = (
            "brake_specific_fuel_consumption_lb_hp_h",
            "air_fuel_ratio_mass",
            "volumetric_efficiency",
            "manifold_temperature_k",
            "compressor_inlet_pressure_pa",
            "compressor_inlet_temperature_k",
            "charge_path_pressure_loss_pa",
            "compressor_isentropic_efficiency",
            "gas_gamma",
            "gas_cp_j_kg_k",
            "gas_constant_j_kg_k",
            "fuel_lower_heating_value_j_kg",
        )
        for field in numeric_fields:
            if not _is_positive_number(air_fuel.get(field)):
                errors.append(f"air_and_fuel_screening.{field}: expected positive number")
        bounded_fields = {
            "brake_specific_fuel_consumption_lb_hp_h": (0.05, 2.0),
            "air_fuel_ratio_mass": (1.0, 30.0),
            "volumetric_efficiency": (0.1, 2.0),
            "compressor_isentropic_efficiency": (0.1, 1.0),
            "gas_gamma": (1.0, 2.0),
            "manifold_temperature_k": (200.0, 500.0),
            "compressor_inlet_pressure_pa": (10000.0, 200000.0),
            "compressor_inlet_temperature_k": (200.0, 400.0),
            "charge_path_pressure_loss_pa": (0.0, 200000.0),
            "gas_cp_j_kg_k": (500.0, 2000.0),
            "gas_constant_j_kg_k": (200.0, 400.0),
            "fuel_lower_heating_value_j_kg": (10000000.0, 60000000.0),
        }
        for field, (lower, upper) in bounded_fields.items():
            value = air_fuel.get(field)
            if _is_positive_number(value) and not lower < value <= upper:
                errors.append(f"air_and_fuel_screening.{field}: expected ({lower}, {upper}]")
        if _is_positive_number(air_fuel.get("compressor_isentropic_efficiency")) and not (
            0.0 < air_fuel["compressor_isentropic_efficiency"] <= 1.0
        ):
            errors.append("air_and_fuel_screening.compressor_isentropic_efficiency: expected (0, 1]")
        shortlist = air_fuel.get("turbo_candidate_shortlist")
        if not isinstance(shortlist, dict):
            errors.append("air_and_fuel_screening.turbo_candidate_shortlist: expected object")
        elif any(
            shortlist.get(flag) is not False
            for flag in (
                "compressor_map_digitized",
                "turbine_map_available",
                "surge_choke_speed_and_efficiency_margins_verified",
            )
        ):
            errors.append("air_and_fuel_screening.turbo_candidate_shortlist: map gates must remain false")

    thermal = contract.get("thermal_screening")
    if not isinstance(thermal, dict):
        errors.append("thermal_screening: expected object")
    else:
        if thermal.get("load_allocation_classification") != (
            "declared_energy_partition_hypotheses_not_cht_or_test_data"
        ):
            errors.append("thermal_screening.load_allocation_classification: unexpected authority")
        fractions = (
            "head_heat_fraction_of_fuel_power",
            "base_oil_heat_fraction_of_fuel_power",
            "base_cylinder_fin_air_heat_fraction_of_fuel_power",
            "radiation_and_unmodelled_heat_fraction_of_fuel_power",
            "air_oil_head_heat_split_to_oil",
        )
        for field in fractions:
            value = thermal.get(field)
            if not _is_positive_number(value) or value >= 1.0:
                errors.append(f"thermal_screening.{field}: expected fraction in (0, 1)")
        for field in (
            "coolant_cp_j_kg_k",
            "head_coolant_delta_t_k",
            "charge_coolant_cp_j_kg_k",
            "charge_coolant_delta_t_k",
            "oil_cp_j_kg_k",
            "oil_delta_t_k",
        ):
            if not _is_positive_number(thermal.get(field)):
                errors.append(f"thermal_screening.{field}: expected positive finite number")
        thermal_bounds = {
            "coolant_cp_j_kg_k": (500.0, 10000.0),
            "head_coolant_delta_t_k": (1.0, 100.0),
            "charge_coolant_cp_j_kg_k": (500.0, 10000.0),
            "charge_coolant_delta_t_k": (1.0, 100.0),
            "oil_cp_j_kg_k": (500.0, 5000.0),
            "oil_delta_t_k": (1.0, 100.0),
        }
        for field, (lower, upper) in thermal_bounds.items():
            value = thermal.get(field)
            if _is_positive_number(value) and not lower <= value <= upper:
                errors.append(f"thermal_screening.{field}: expected [{lower}, {upper}]")
        variants = thermal.get("variants")
        if not isinstance(variants, list):
            errors.append("thermal_screening.variants: expected array")
        else:
            variant_ids = {item.get("id") for item in variants if isinstance(item, dict)}
            if variant_ids != REQUIRED_VARIANTS or len(variants) != len(REQUIRED_VARIANTS):
                errors.append("thermal_screening.variants: expected exact hybrid and air/oil variants")
            for index, variant in enumerate(variants):
                if not isinstance(variant, dict):
                    errors.append(f"thermal_screening.variants[{index}]: expected object")
                    continue
                if variant.get("stock_993_liquid_cooling_claim") is not False:
                    errors.append(f"thermal_screening.variants[{index}].stock_993_liquid_cooling_claim: must be false")
                if variant.get("turbo_bearing_housing_heat_load_w") is not None:
                    errors.append(
                        f"thermal_screening.variants[{index}].turbo_bearing_housing_heat_load_w: "
                        "must remain null until measured or solved"
                    )
                limits = variant.get("screening_limits_w")
                if not isinstance(limits, dict) or not limits or any(not _is_positive_number(v) for v in limits.values()):
                    errors.append(f"thermal_screening.variants[{index}].screening_limits_w: invalid limits")
                    continue
                if variant.get("id") == "917_2026_hybrid_head_liquid_air_oil_cylinders":
                    if variant.get("engine_cooling") != (
                        "air_oil_cylinders_plus_liquid_cooled_heads_and_turbo_bearing_housings"
                    ):
                        errors.append(f"thermal_screening.variants[{index}]: unexpected hybrid engine cooling")
                    if variant.get("charge_cooling") != "water_to_air_intercoolers":
                        errors.append(f"thermal_screening.variants[{index}]: unexpected hybrid charge cooling")
                    if variant.get("dedicated_conversion_coolant_circuit_required") is not True:
                        errors.append(f"thermal_screening.variants[{index}]: hybrid coolant circuit must be required")
                    if variant.get("turbo_bearing_cooling") != "liquid_after_run_candidate_load_not_yet_available":
                        errors.append(f"thermal_screening.variants[{index}]: unexpected hybrid turbo cooling status")
                    if set(limits) != {
                        "head_high_temperature_liquid_loop",
                        "turbo_bearing_housings",
                        "charge_low_temperature_liquid_loop",
                        "oil_loop",
                        "cylinder_fin_air",
                    }:
                        errors.append(f"thermal_screening.variants[{index}]: unexpected hybrid limit registry")
                elif variant.get("id") == "917_2026_air_oil_engine_air_air_charge":
                    if variant.get("engine_cooling") != "air_and_oil_only_no_engine_coolant_jacket":
                        errors.append(f"thermal_screening.variants[{index}]: unexpected air/oil engine cooling")
                    if variant.get("charge_cooling") != "air_to_air_intercoolers":
                        errors.append(f"thermal_screening.variants[{index}]: unexpected air/oil charge cooling")
                    if variant.get("dedicated_conversion_coolant_circuit_required") is not False:
                        errors.append(f"thermal_screening.variants[{index}]: air/oil coolant circuit must remain false")
                    if variant.get("turbo_bearing_cooling") != "unresolved_no_liquid_candidate_required":
                        errors.append(f"thermal_screening.variants[{index}]: unexpected air/oil turbo cooling status")
                    if set(limits) != {
                        "air_to_air_charge_cooler",
                        "oil_loop",
                        "cylinder_and_head_fin_air",
                    }:
                        errors.append(f"thermal_screening.variants[{index}]: unexpected air/oil limit registry")

    materials = contract.get("material_hypotheses")
    if not isinstance(materials, dict):
        errors.append("material_hypotheses: expected object")
    else:
        if materials.get("manufacturing_released") is not False:
            errors.append("material_hypotheses.manufacturing_released: must remain false")
        if materials.get("fatigue_thermal_corrosion_and_process_qualification_complete") is not False:
            errors.append(
                "material_hypotheses.fatigue_thermal_corrosion_and_process_qualification_complete: must remain false"
            )
        for field in (
            "crankcase_and_heads",
            "pistons",
            "connecting_rods",
            "crankshaft",
            "intake_valves",
            "exhaust_valves",
            "exhaust_manifolds",
        ):
            value = materials.get(field)
            if not isinstance(value, str) or ("candidate" not in value and "unselected" not in value):
                errors.append(f"material_hypotheses.{field}: expected an unqualified candidate")

    integration = contract.get("porsche_993_integration")
    if not isinstance(integration, dict):
        errors.append("porsche_993_integration: expected object")
    else:
        if integration.get("historical_993_engine_cooling") != "air_and_oil_cooled":
            errors.append("porsche_993_integration.historical_993_engine_cooling: expected air_and_oil_cooled")
        if integration.get("conversion_baseline") != EXPECTED_CONVERSION_BASELINE:
            errors.append("porsche_993_integration.conversion_baseline: unexpected conversion architecture")
        if integration.get("vehicle_installation_authorized") is not False:
            errors.append("porsche_993_integration.vehicle_installation_authorized: must remain false")
        if integration.get("measured_vehicle_package_available") is not False:
            errors.append("porsche_993_integration.measured_vehicle_package_available: must remain false")
        sources = integration.get("historical_fact_source_ids")
        known_sources = _known_source_ids()
        if (
            not isinstance(sources, list)
            or len(sources) != len(REQUIRED_993_SOURCE_IDS)
            or set(sources) != REQUIRED_993_SOURCE_IDS
        ):
            errors.append("porsche_993_integration.historical_fact_source_ids: expected exact Porsche 993 sources")
        elif any(source not in known_sources for source in sources):
            errors.append("porsche_993_integration.historical_fact_source_ids: source registry drift")
        required_evidence = integration.get("required_evidence")
        if (
            not isinstance(required_evidence, dict)
            or set(required_evidence) != REQUIRED_993_INTEGRATION_EVIDENCE_KEYS
            or not _all_none(required_evidence)
        ):
            errors.append(
                "porsche_993_integration.required_evidence: expected exact F32 registry with null values"
            )

    next_evidence = contract.get("required_next_solver_evidence")
    if (
        not isinstance(next_evidence, dict)
        or set(next_evidence) != REQUIRED_NEXT_SOLVER_EVIDENCE_KEYS
        or not _all_none(next_evidence)
    ):
        errors.append("required_next_solver_evidence: expected exact F32 registry with null values")

    release_gates = contract.get("release_gates")
    if not isinstance(release_gates, dict) or set(release_gates) != REQUIRED_RELEASE_GATES:
        errors.append("release_gates: expected exact F32 gate registry")
    elif any(value is not False for value in release_gates.values()):
        errors.append("release_gates: every gate must remain literal false")
    return errors


def _powertrain_point(contract: dict[str, Any]) -> dict[str, Any]:
    architecture = contract["architecture_seed"]
    assumptions = contract["air_and_fuel_screening"]
    target_hp = contract["program"]["target_power"]["value"]

    bore_m = architecture["bore_mm"] / 1000.0
    stroke_m = architecture["stroke_mm"] / 1000.0
    displacement_m3 = math.pi * bore_m**2 * stroke_m * architecture["cylinder_count"] / 4.0
    speed_rpm = architecture["design_speed_rpm"]
    power_w = target_hp * MECHANICAL_HP_TO_W
    torque_nm = power_w * 60.0 / (2.0 * math.pi * speed_rpm)
    bmep_pa = 4.0 * math.pi * torque_nm / displacement_m3
    mean_piston_speed_m_s = 2.0 * stroke_m * speed_rpm / 60.0

    fuel_mass_flow_kg_s = (
        target_hp
        * assumptions["brake_specific_fuel_consumption_lb_hp_h"]
        * POUND_TO_KG
        / 3600.0
    )
    air_mass_flow_kg_s = fuel_mass_flow_kg_s * assumptions["air_fuel_ratio_mass"]
    intake_volume_flow_m3_s = (
        displacement_m3
        * speed_rpm
        * assumptions["volumetric_efficiency"]
        / (2.0 * 60.0)
    )
    manifold_density_kg_m3 = air_mass_flow_kg_s / intake_volume_flow_m3_s
    manifold_pressure_pa = (
        manifold_density_kg_m3
        * assumptions["gas_constant_j_kg_k"]
        * assumptions["manifold_temperature_k"]
    )
    compressor_outlet_pressure_pa = manifold_pressure_pa + assumptions["charge_path_pressure_loss_pa"]
    compressor_pressure_ratio = compressor_outlet_pressure_pa / assumptions["compressor_inlet_pressure_pa"]
    exponent = (assumptions["gas_gamma"] - 1.0) / assumptions["gas_gamma"]
    compressor_outlet_temperature_k = assumptions["compressor_inlet_temperature_k"] * (
        1.0
        + (compressor_pressure_ratio**exponent - 1.0)
        / assumptions["compressor_isentropic_efficiency"]
    )
    compressor_power_w = (
        air_mass_flow_kg_s
        * assumptions["gas_cp_j_kg_k"]
        * (compressor_outlet_temperature_k - assumptions["compressor_inlet_temperature_k"])
    )
    intercooler_heat_w = (
        air_mass_flow_kg_s
        * assumptions["gas_cp_j_kg_k"]
        * (compressor_outlet_temperature_k - assumptions["manifold_temperature_k"])
    )
    fuel_power_w = fuel_mass_flow_kg_s * assumptions["fuel_lower_heating_value_j_kg"]

    return {
        "target_power": {
            "mechanical_hp": target_hp,
            "w": power_w,
            "kw": power_w / 1000.0,
            "power_requirement_identity_closed": True,
            "target_power_proven": False,
        },
        "geometry_and_mechanics": {
            "displacement_l": displacement_m3 * 1000.0,
            "design_speed_rpm": speed_rpm,
            "specific_power_kw_per_l": (power_w / 1000.0) / (displacement_m3 * 1000.0),
            "required_torque_nm": torque_nm,
            "required_bmep_bar": bmep_pa / 100000.0,
            "mean_piston_speed_m_s": mean_piston_speed_m_s,
        },
        "air_and_fuel": {
            "fuel_mass_flow_kg_s": fuel_mass_flow_kg_s,
            "fuel_mass_flow_kg_h": fuel_mass_flow_kg_s * 3600.0,
            "air_mass_flow_kg_s": air_mass_flow_kg_s,
            "air_mass_flow_per_turbo_kg_s": air_mass_flow_kg_s / architecture["turbocharger_count"],
            "exhaust_mass_flow_kg_s": air_mass_flow_kg_s + fuel_mass_flow_kg_s,
            "air_plus_fuel_mass_balance_closed": True,
            "intake_volume_flow_m3_s": intake_volume_flow_m3_s,
            "manifold_density_kg_m3": manifold_density_kg_m3,
            "required_manifold_absolute_pressure_pa": manifold_pressure_pa,
            "required_manifold_gauge_pressure_bar_at_declared_inlet": (
                manifold_pressure_pa - assumptions["compressor_inlet_pressure_pa"]
            )
            / 100000.0,
            "compressor_pressure_ratio": compressor_pressure_ratio,
            "compressor_outlet_temperature_k": compressor_outlet_temperature_k,
            "compressor_power_total_w": compressor_power_w,
            "compressor_power_per_turbo_w": compressor_power_w / architecture["turbocharger_count"],
            "intercooler_heat_rejection_w": intercooler_heat_w,
            "turbo_map_match_verified": False,
        },
        "energy": {
            "fuel_power_w": fuel_power_w,
            "screening_brake_thermal_efficiency": power_w / fuel_power_w,
        },
    }


def _numeric_leaves(value: Any, prefix: str = ""):
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{prefix}.{key}" if prefix else key
            yield from _numeric_leaves(item, child)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        yield prefix, float(value)


def _validate_derived_point(contract: dict[str, Any], point: dict[str, Any]) -> None:
    for path, value in _numeric_leaves(point):
        if not math.isfinite(value):
            raise ValueError(f"derived point is non-finite: {path}")
    flow = point["air_and_fuel"]
    energy = point["energy"]
    assumptions = contract["air_and_fuel_screening"]
    if flow["compressor_pressure_ratio"] <= 1.0:
        raise ValueError("derived compressor pressure ratio must exceed 1")
    if flow["compressor_outlet_temperature_k"] < assumptions["compressor_inlet_temperature_k"]:
        raise ValueError("derived compressor outlet temperature is below inlet temperature")
    if flow["compressor_power_total_w"] <= 0.0:
        raise ValueError("derived compressor power must be positive")
    if flow["intercooler_heat_rejection_w"] < 0.0:
        raise ValueError("derived intercooler heat rejection must be non-negative")
    if not 0.0 < energy["screening_brake_thermal_efficiency"] < 1.0:
        raise ValueError("derived brake thermal efficiency must be in (0, 1)")
    if flow["exhaust_mass_flow_kg_s"] <= flow["air_mass_flow_kg_s"]:
        raise ValueError("derived exhaust flow must include positive fuel flow")


def _load_status(load_w: float, limit_w: float) -> dict[str, Any]:
    if not math.isfinite(load_w) or load_w < 0.0:
        raise ValueError("thermal load must be finite and non-negative")
    if not math.isfinite(limit_w) or limit_w <= 0.0:
        raise ValueError("thermal screening limit must be finite and positive")
    return {
        "load_w": load_w,
        "screening_limit_w": limit_w,
        "margin_w": limit_w - load_w,
        "within_declared_screening_limit": load_w <= limit_w,
        "validated_capacity": False,
    }


def _missing_load_status(limit_w: float) -> dict[str, Any]:
    if not math.isfinite(limit_w) or limit_w <= 0.0:
        raise ValueError("thermal screening limit must be finite and positive")
    return {
        "load_w": None,
        "screening_limit_w": limit_w,
        "margin_w": None,
        "within_declared_screening_limit": False,
        "validated_capacity": False,
        "missing_input": True,
    }


def _validate_report_numeric_invariants(report: dict[str, Any]) -> None:
    for path, value in _numeric_leaves(report):
        if not math.isfinite(value):
            raise ValueError(f"F32 report contains a non-finite number: {path}")
    for variant in report["cooling_variants"]:
        for name, mass_flow in variant["required_mass_flows_kg_s"].items():
            if mass_flow is not None and mass_flow <= 0.0:
                raise ValueError(f"F32 thermal mass flow must be positive: {variant['id']}.{name}")
        for name, load in variant["loads"].items():
            if load["load_w"] is not None and load["load_w"] < 0.0:
                raise ValueError(f"F32 thermal load must be non-negative: {variant['id']}.{name}")


def _thermal_variants(contract: dict[str, Any], point: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    thermal = contract["thermal_screening"]
    fuel_power_w = point["energy"]["fuel_power_w"]
    brake_power_w = point["target_power"]["w"]
    intercooler_heat_w = point["air_and_fuel"]["intercooler_heat_rejection_w"]
    head_heat_w = fuel_power_w * thermal["head_heat_fraction_of_fuel_power"]
    base_oil_heat_w = fuel_power_w * thermal["base_oil_heat_fraction_of_fuel_power"]
    base_fin_air_heat_w = fuel_power_w * thermal["base_cylinder_fin_air_heat_fraction_of_fuel_power"]
    radiation_heat_w = fuel_power_w * thermal["radiation_and_unmodelled_heat_fraction_of_fuel_power"]
    tailpipe_exhaust_heat_w = fuel_power_w - (
        brake_power_w
        + intercooler_heat_w
        + head_heat_w
        + base_oil_heat_w
        + base_fin_air_heat_w
        + radiation_heat_w
    )
    if tailpipe_exhaust_heat_w <= 0.0:
        raise ValueError("declared thermal partition leaves no positive tailpipe exhaust heat")

    energy_outputs_w = {
        "brake_power": brake_power_w,
        "intercooler_heat": intercooler_heat_w,
        "head_heat": head_heat_w,
        "base_oil_heat": base_oil_heat_w,
        "base_cylinder_fin_air_heat": base_fin_air_heat_w,
        "radiation_and_unmodelled_heat": radiation_heat_w,
        "tailpipe_exhaust_heat": tailpipe_exhaust_heat_w,
    }
    closure_error_w = fuel_power_w - sum(energy_outputs_w.values())
    energy_balance = {
        "input_fuel_power_w": fuel_power_w,
        "declared_outputs_w": energy_outputs_w,
        "closure_error_w": closure_error_w,
        "relative_closure_error": closure_error_w / fuel_power_w,
        "partition_is_hypothesis_not_measurement": True,
        "closure_kind": "residual_arithmetic_closure_not_turbine_or_exhaust_enthalpy_balance",
        "turbo_shaft_power_balance_closed": False,
    }

    by_id = {variant["id"]: variant for variant in thermal["variants"]}
    hybrid_contract = by_id["917_2026_hybrid_head_liquid_air_oil_cylinders"]
    hybrid_limits = hybrid_contract["screening_limits_w"]
    hybrid_loads = {
        "head_high_temperature_liquid_loop": _load_status(
            head_heat_w,
            hybrid_limits["head_high_temperature_liquid_loop"],
        ),
        "turbo_bearing_housings": _missing_load_status(
            hybrid_limits["turbo_bearing_housings"],
        ),
        "charge_low_temperature_liquid_loop": _load_status(
            intercooler_heat_w,
            hybrid_limits["charge_low_temperature_liquid_loop"],
        ),
        "oil_loop": _load_status(base_oil_heat_w, hybrid_limits["oil_loop"]),
        "cylinder_fin_air": _load_status(base_fin_air_heat_w, hybrid_limits["cylinder_fin_air"]),
    }
    hybrid = {
        "id": hybrid_contract["id"],
        "architecture": hybrid_contract["engine_cooling"],
        "charge_cooling": hybrid_contract["charge_cooling"],
        "loads": hybrid_loads,
        "required_mass_flows_kg_s": {
            "head_coolant": head_heat_w / (thermal["coolant_cp_j_kg_k"] * thermal["head_coolant_delta_t_k"]),
            "turbo_bearing_coolant": None,
            "charge_coolant": intercooler_heat_w
            / (thermal["charge_coolant_cp_j_kg_k"] * thermal["charge_coolant_delta_t_k"]),
            "oil": base_oil_heat_w / (thermal["oil_cp_j_kg_k"] * thermal["oil_delta_t_k"]),
        },
        "evaluated_loads_within_declared_screening_limits": all(
            load["within_declared_screening_limit"]
            for load in hybrid_loads.values()
            if not load.get("missing_input", False)
        ),
        "within_all_declared_screening_limits": False,
        "missing_load_inputs": ["turbo_bearing_housing_heat_load_and_hot_soak"],
        "screening_complete": False,
        "thermal_system_validated": False,
        "vehicle_packaging_validated": False,
    }

    air_oil_contract = by_id["917_2026_air_oil_engine_air_air_charge"]
    air_oil_limits = air_oil_contract["screening_limits_w"]
    head_to_oil_w = head_heat_w * thermal["air_oil_head_heat_split_to_oil"]
    head_to_fin_air_w = head_heat_w - head_to_oil_w
    air_oil_total_oil_w = base_oil_heat_w + head_to_oil_w
    air_oil_total_fin_w = base_fin_air_heat_w + head_to_fin_air_w
    air_oil_loads = {
        "air_to_air_charge_cooler": _load_status(
            intercooler_heat_w,
            air_oil_limits["air_to_air_charge_cooler"],
        ),
        "oil_loop": _load_status(air_oil_total_oil_w, air_oil_limits["oil_loop"]),
        "cylinder_and_head_fin_air": _load_status(
            air_oil_total_fin_w,
            air_oil_limits["cylinder_and_head_fin_air"],
        ),
    }
    air_oil = {
        "id": air_oil_contract["id"],
        "architecture": air_oil_contract["engine_cooling"],
        "charge_cooling": air_oil_contract["charge_cooling"],
        "head_heat_redistribution_w": {
            "to_oil": head_to_oil_w,
            "to_fin_air": head_to_fin_air_w,
        },
        "loads": air_oil_loads,
        "required_mass_flows_kg_s": {
            "oil": air_oil_total_oil_w / (thermal["oil_cp_j_kg_k"] * thermal["oil_delta_t_k"]),
        },
        "evaluated_loads_within_declared_screening_limits": all(
            load["within_declared_screening_limit"] for load in air_oil_loads.values()
        ),
        "within_all_declared_screening_limits": False,
        "missing_load_inputs": ["turbo_bearing_housing_heat_load_and_cooling_method"],
        "screening_complete": False,
        "thermal_system_validated": False,
        "vehicle_packaging_validated": False,
    }
    return [hybrid, air_oil], energy_balance


def build_report(contract: dict[str, Any]) -> dict[str, Any]:
    errors = validate_contract(contract)
    if errors:
        raise ValueError("invalid F32 contract:\n- " + "\n- ".join(errors))

    point = _powertrain_point(contract)
    _validate_derived_point(contract, point)
    variants, energy_balance = _thermal_variants(contract, point)
    hybrid = next(item for item in variants if item["id"].startswith("917_2026_hybrid"))
    air_oil = next(item for item in variants if item["id"].startswith("917_2026_air_oil"))
    hybrid_evaluated = hybrid["evaluated_loads_within_declared_screening_limits"]
    air_oil_evaluated = air_oil["evaluated_loads_within_declared_screening_limits"]
    if hybrid_evaluated and not air_oil_evaluated:
        candidate_for_next_study = hybrid["id"]
        candidate_reason = (
            "evaluated_hybrid_head_charge_oil_and_fin_loads_are_inside_provisional_limits_"
            "while_air_oil_exceeds_oil_and_fin_limits_but_turbo_bearing_load_is_missing"
        )
    elif air_oil_evaluated and not hybrid_evaluated:
        candidate_for_next_study = air_oil["id"]
        candidate_reason = (
            "evaluated_air_oil_loads_are_inside_provisional_limits_while_hybrid_evaluated_loads_"
            "exceed_them_but_turbo_bearing_method_and_load_remain_missing"
        )
    else:
        candidate_for_next_study = None
        candidate_reason = "no_unique_candidate_from_evaluated_provisional_load_limits"
    report = {
        "schema_version": "1.0.0",
        "phase": "F32",
        "status": "algebraic_screen_complete_no_engine_or_vehicle_release",
        "model_scope": {
            "clean_sheet_2026": True,
            "historical_replica": False,
            "zero_dimensional_algebraic_screen_only": True,
            "engine_cycle_solver": False,
            "cfd_cht_fea_or_dyno_result": False,
        },
        "contract_sha256": _sha256_bytes(_canonical_bytes(contract)),
        "design_point": point,
        "declared_residual_energy_partition": energy_balance,
        "cooling_variants": variants,
        "screening_decision": {
            "candidate_for_next_study": candidate_for_next_study,
            "candidate_reason": candidate_reason,
            "hybrid_evaluated_loads_within_declared_limits": hybrid_evaluated,
            "hybrid_complete_limit_screen": hybrid["screening_complete"],
            "air_oil_evaluated_loads_within_declared_limits": air_oil_evaluated,
            "air_oil_complete_limit_screen": air_oil["screening_complete"],
            "decision_is_design_screen_not_validation": True,
            "stock_993_liquid_cooling_claim": False,
            "dedicated_conversion_system_required": True,
        },
        "porsche_993_integration": {
            "target_vehicle": contract["program"]["target_vehicle"],
            "historical_993_engine_cooling": contract["porsche_993_integration"]["historical_993_engine_cooling"],
            "conversion_baseline": contract["porsche_993_integration"]["conversion_baseline"],
            "missing_evidence": sorted(contract["porsche_993_integration"]["required_evidence"]),
            "vehicle_installation_authorized": False,
        },
        "required_next_solver_evidence": sorted(contract["required_next_solver_evidence"]),
        "release_gates": dict(contract["release_gates"]),
    }
    _validate_report_numeric_invariants(report)
    rounded_report = _round_floats(report)
    _validate_report_numeric_invariants(rounded_report)
    return rounded_report


def _json_text(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    mode = parser.add_mutually_exclusive_group(required=False)
    mode.add_argument("--output", type=Path, default=None)
    mode.add_argument("--check", type=Path, default=None)
    args = parser.parse_args()

    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    report = build_report(contract)
    expected_text = _json_text(report)

    if args.check is not None:
        if not args.check.is_file():
            raise SystemExit(f"F32 evidence missing: {args.check}")
        if args.check.read_text(encoding="utf-8") != expected_text:
            raise SystemExit(f"F32 evidence stale: {args.check}")
        print(f"OK   {args.check} (F32 screening current; all release gates blocked)")
        return 0

    output = args.output or DEFAULT_OUTPUT
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(expected_text, encoding="utf-8")
    print(f"WROTE {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
