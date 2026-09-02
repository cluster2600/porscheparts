#!/usr/bin/env python3
"""Reference 0D forward screen for the F33 clean-sheet flat-12 variants.

The requested power is deliberately excluded from ``solve_forward``.  The
solver is a four-state, closed-cycle thermochemistry screen; it is not a 1D gas
dynamics model, a calibrated combustion model, or physical proof of power.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

try:
    import cantera as ct
except ModuleNotFoundError:  # Le validateur statique reste utilisable hors image.
    ct = None  # type: ignore[assignment]


class _UnavailableCanteraError(Exception):
    """Placeholder used only to keep the CLI exception tuple import-safe."""


CANTERA_ERROR = ct.CanteraError if ct is not None else _UnavailableCanteraError


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "twins/reference-917-engine/clean-sheet-cycle-thermal-f33.json"
IMAGE_PUBLICATION = (
    ROOT
    / "twins/reference-917-engine/evidence/f33/engine-cycle-image-publication.json"
)
REPORT = ROOT / "twins/reference-917-engine/evidence/f33/cycle-thermal-report.json"

MECHANICAL_HP_W = 745.6998715822702
METRIC_PS_W = 735.49875
EXPECTED_VARIANTS = {
    "917_2026_flat12_na_candidate": 0,
    "917_2026_flat12_twin_turbo_1600hp_target": 2,
}
PHYSICAL_RELEASE_GATES = {
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
TOP_LEVEL_KEYS = {
    "$comment",
    "schema_version",
    "phase",
    "status",
    "program",
    "upstream_manifest",
    "authority_boundary",
    "requested_power_target",
    "engine_variants",
    "variant_registry",
    "cooling_architecture_registry",
    "operating_point_registry",
    "domain_registry",
    "component_registry",
    "port_registry",
    "network_edge_defaults",
    "network_edge_registry",
    "thermal_coupling_registry",
    "joint_and_seal_registry",
    "pump_and_fan_registry",
    "heat_exchanger_registry",
    "sensor_registry",
    "safety_interlock_registry",
    "load_case_registry",
    "f13_case_crosswalk",
    "unknown_registry",
    "validation_policy",
    "topology_acceptance",
    "release_gates",
    "prohibited_claims",
}
AUTHORITY_KEYS = {
    "f33_authority",
    "semantic_topology_closure_may_be_claimed",
    "semantic_topology_closure_definition",
    "semantic_topology_closure_is_physical_closure",
    "legacy_variant_identity_equivalence",
    "legacy_mechanical_injection_transferred",
    "f32_efi_intent_retained_as_unreleased_design_hypothesis",
    "f29_head_contains_released_coolant_jackets",
    "f32_algebraic_screening_is_solver_result",
    "allowed_claims",
    "all_physical_geometry_known",
    "all_dimensions_known",
    "all_pressure_temperature_boundaries_known",
    "all_seals_defined",
    "all_material_properties_known",
    "all_component_maps_known",
    "all_sensor_chains_calibrated",
    "solver_ready",
    "physicsnemo_dataset_authorized",
    "omniverse_simready_authorized",
    "test_bench_start_authorized",
    "manufacturing_authorized",
}
UPSTREAM_KEYS = {
    "id",
    "path",
    "sha256",
    "reuse_scope",
    "geometry_or_dimension_transfer_authorized",
    "manufacturing_authority",
    "boundary_condition_transfer_authorized",
    "result_transfer_authorized",
    "legacy_variant_identity_equivalence",
    "coolant_jacket_geometry_transfer_authorized",
    "load_or_result_transfer_authorized",
    "screening_values_are_physical_evidence",
    "engine_cycle_solver_executed",
}
VARIANT_KEYS = {
    "id",
    "configuration",
    "classification",
    "description",
    "turbocharger_count",
    "requested_power_ref",
    "forward_solver_input",
    "turbo_data",
    "cooling_architecture_ref",
    "semantic_topology_ref",
    "solver_ready",
    "geometry_released",
    "engine_operation_authorized",
}
TURBO_DATA_KEYS = {
    "candidate_model",
    "candidate_role",
    "compressor_map_evidence",
    "turbine_map_evidence",
    "compressor_map_digitized",
    "turbine_map_digitized",
    "map_interpolation_executed",
    "shaft_balance_forward_closed",
    "turbo_match_validated",
}
COMMON_FORWARD_KEYS = {
    "bore_mm",
    "stroke_mm",
    "cylinder_count",
    "compression_ratio",
    "speed_rpm",
    "manifold_pressure_pa_abs",
    "manifold_temperature_k",
    "volumetric_efficiency",
    "equivalence_ratio",
    "exhaust_pressure_pa_abs",
    "indicated_work_retention",
    "fmep_model",
    "accessory_power_w",
    "fuel_surrogate",
    "fuel_lhv_j_kg",
    "thermal_hypotheses",
    "turbocharger_count",
    "turbo_screening_input",
    "unit_registry",
}
FMEP_KEYS = {
    "base_bar",
    "mean_piston_speed_linear_bar_per_m_s",
    "mean_piston_speed_quadratic_bar_per_m_s2",
}
THERMAL_KEYS = {
    "head_heat_fraction_of_fuel_power",
    "cylinder_air_heat_fraction_of_fuel_power",
    "base_oil_heat_fraction_of_fuel_power",
    "friction_to_oil_fraction",
    "coolant_cp_j_kg_k",
    "head_coolant_delta_t_k",
    "oil_cp_j_kg_k",
    "oil_delta_t_k",
    "charge_coolant_cp_j_kg_k",
    "charge_coolant_delta_t_k",
}
TURBO_SCREENING_KEYS = {
    "candidate_model",
    "compressor_inlet_pressure_pa_abs",
    "compressor_inlet_temperature_k",
    "charge_path_loss_pa",
    "compressor_isentropic_efficiency",
    "compressor_gas_cp_j_kg_k",
    "compressor_gas_gamma",
    "corrected_flow_reference_pressure_pa_abs",
    "corrected_flow_reference_temperature_k",
    "turbine_inlet_temperature_k",
    "turbine_outlet_pressure_pa_abs",
    "turbine_isentropic_efficiency",
    "turbo_mechanical_efficiency",
    "exhaust_gas_cp_j_kg_k",
    "exhaust_gas_gamma",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_payload_sha256(value: Any) -> str:
    payload = (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant rejected: {value}")


def _read_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=_reject_constant,
    )


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _finite_number(
    errors: list[str],
    value: Any,
    label: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
    strict_minimum: bool = False,
) -> None:
    if not _is_number(value) or not math.isfinite(float(value)):
        errors.append(f"{label} must be a finite number, not bool")
        return
    number = float(value)
    if minimum is not None:
        invalid = number <= minimum if strict_minimum else number < minimum
        if invalid:
            operator = ">" if strict_minimum else ">="
            errors.append(f"{label} must be {operator} {minimum}")
    if maximum is not None and number > maximum:
        errors.append(f"{label} must be <= {maximum}")


def _unexpected_keys(value: Any, allowed: set[str], label: str) -> list[str]:
    if not isinstance(value, dict):
        return [f"{label} must be an object"]
    extras = sorted(set(value) - allowed)
    return [f"{label} contains unknown keys: {extras}"] if extras else []


def _expected_units(forward: dict[str, Any], turbo_count: int) -> dict[str, str]:
    units = {
        "bore_mm": "mm",
        "stroke_mm": "mm",
        "cylinder_count": "count",
        "compression_ratio": "ratio",
        "speed_rpm": "rpm",
        "manifold_pressure_pa_abs": "Pa_abs",
        "manifold_temperature_k": "K",
        "volumetric_efficiency": "ratio",
        "equivalence_ratio": "ratio",
        "exhaust_pressure_pa_abs": "Pa_abs",
        "indicated_work_retention": "ratio",
        "accessory_power_w": "W",
        "fuel_lhv_j_kg": "J/kg",
        "turbocharger_count": "count",
        "fmep_model.base_bar": "bar",
        "fmep_model.mean_piston_speed_linear_bar_per_m_s": "bar/(m/s)",
        "fmep_model.mean_piston_speed_quadratic_bar_per_m_s2": "bar/(m/s)^2",
        "thermal_hypotheses.head_heat_fraction_of_fuel_power": "ratio",
        "thermal_hypotheses.cylinder_air_heat_fraction_of_fuel_power": "ratio",
        "thermal_hypotheses.base_oil_heat_fraction_of_fuel_power": "ratio",
        "thermal_hypotheses.friction_to_oil_fraction": "ratio",
        "thermal_hypotheses.coolant_cp_j_kg_k": "J/(kg*K)",
        "thermal_hypotheses.head_coolant_delta_t_k": "K",
        "thermal_hypotheses.oil_cp_j_kg_k": "J/(kg*K)",
        "thermal_hypotheses.oil_delta_t_k": "K",
    }
    if turbo_count == 2:
        units.update(
            {
                "thermal_hypotheses.charge_coolant_cp_j_kg_k": "J/(kg*K)",
                "thermal_hypotheses.charge_coolant_delta_t_k": "K",
                "turbo_screening_input.compressor_inlet_pressure_pa_abs": "Pa_abs",
                "turbo_screening_input.compressor_inlet_temperature_k": "K",
                "turbo_screening_input.charge_path_loss_pa": "Pa",
                "turbo_screening_input.compressor_isentropic_efficiency": "ratio",
                "turbo_screening_input.compressor_gas_cp_j_kg_k": "J/(kg*K)",
                "turbo_screening_input.compressor_gas_gamma": "ratio",
                "turbo_screening_input.corrected_flow_reference_pressure_pa_abs": "Pa_abs",
                "turbo_screening_input.corrected_flow_reference_temperature_k": "K",
                "turbo_screening_input.turbine_inlet_temperature_k": "K",
                "turbo_screening_input.turbine_outlet_pressure_pa_abs": "Pa_abs",
                "turbo_screening_input.turbine_isentropic_efficiency": "ratio",
                "turbo_screening_input.turbo_mechanical_efficiency": "ratio",
                "turbo_screening_input.exhaust_gas_cp_j_kg_k": "J/(kg*K)",
                "turbo_screening_input.exhaust_gas_gamma": "ratio",
            }
        )
    return units


def _validate_forward_input(
    forward: Any,
    turbo_count: int,
    label: str,
) -> list[str]:
    errors = _unexpected_keys(forward, COMMON_FORWARD_KEYS, label)
    if not isinstance(forward, dict):
        return errors
    missing = sorted(COMMON_FORWARD_KEYS - set(forward))
    if missing:
        errors.append(f"{label} missing keys: {missing}")
        return errors
    if forward.get("fuel_surrogate") != "n_dodecane_cantera_builtin":
        errors.append(f"{label}.fuel_surrogate must be n_dodecane_cantera_builtin")
    if forward.get("turbocharger_count") != turbo_count:
        errors.append(f"{label}.turbocharger_count inconsistent with variant")

    ranges = {
        "bore_mm": (50.0, 150.0),
        "stroke_mm": (40.0, 120.0),
        "cylinder_count": (12.0, 12.0),
        "compression_ratio": (6.0, 15.0),
        "speed_rpm": (500.0, 12000.0),
        "manifold_pressure_pa_abs": (50000.0, 500000.0),
        "manifold_temperature_k": (250.0, 450.0),
        "volumetric_efficiency": (0.5, 1.5),
        "equivalence_ratio": (0.5, 1.5),
        "exhaust_pressure_pa_abs": (50000.0, 600000.0),
        "indicated_work_retention": (0.01, 1.0),
        "accessory_power_w": (0.0, 200000.0),
        "fuel_lhv_j_kg": (30000000.0, 50000000.0),
        "turbocharger_count": (float(turbo_count), float(turbo_count)),
    }
    for key, (minimum, maximum) in ranges.items():
        _finite_number(
            errors,
            forward.get(key),
            f"{label}.{key}",
            minimum=minimum,
            maximum=maximum,
        )

    fmep = forward.get("fmep_model")
    errors.extend(_unexpected_keys(fmep, FMEP_KEYS, f"{label}.fmep_model"))
    if isinstance(fmep, dict):
        if set(fmep) != FMEP_KEYS:
            errors.append(f"{label}.fmep_model must contain exact coefficient set")
        for key in FMEP_KEYS:
            _finite_number(
                errors,
                fmep.get(key),
                f"{label}.fmep_model.{key}",
                minimum=0.0,
                maximum=20.0,
            )

    thermal = forward.get("thermal_hypotheses")
    errors.extend(
        _unexpected_keys(thermal, THERMAL_KEYS, f"{label}.thermal_hypotheses")
    )
    expected_thermal = set(THERMAL_KEYS)
    if turbo_count == 0:
        expected_thermal -= {
            "charge_coolant_cp_j_kg_k",
            "charge_coolant_delta_t_k",
        }
    if isinstance(thermal, dict):
        if set(thermal) != expected_thermal:
            errors.append(
                f"{label}.thermal_hypotheses must contain exact variant key set"
            )
        for key in (
            "head_heat_fraction_of_fuel_power",
            "cylinder_air_heat_fraction_of_fuel_power",
            "base_oil_heat_fraction_of_fuel_power",
            "friction_to_oil_fraction",
        ):
            _finite_number(
                errors,
                thermal.get(key),
                f"{label}.thermal_hypotheses.{key}",
                minimum=0.0,
                maximum=1.0,
            )
        for key in (
            "coolant_cp_j_kg_k",
            "oil_cp_j_kg_k",
        ) + (("charge_coolant_cp_j_kg_k",) if turbo_count == 2 else ()):
            _finite_number(
                errors,
                thermal.get(key),
                f"{label}.thermal_hypotheses.{key}",
                minimum=1000.0,
                maximum=6000.0,
            )
        for key in (
            "head_coolant_delta_t_k",
            "oil_delta_t_k",
        ) + (("charge_coolant_delta_t_k",) if turbo_count == 2 else ()):
            _finite_number(
                errors,
                thermal.get(key),
                f"{label}.thermal_hypotheses.{key}",
                minimum=1.0,
                maximum=80.0,
            )
        fractions = [
            thermal.get("head_heat_fraction_of_fuel_power"),
            thermal.get("cylinder_air_heat_fraction_of_fuel_power"),
            thermal.get("base_oil_heat_fraction_of_fuel_power"),
        ]
        if all(_is_number(value) and math.isfinite(float(value)) for value in fractions):
            if sum(float(value) for value in fractions) >= 0.8:
                errors.append(f"{label} declared thermal fractions must sum below 0.8")

    turbo = forward.get("turbo_screening_input")
    if turbo_count == 0:
        if turbo is not None:
            errors.append(f"{label}.turbo_screening_input must be null for NA")
    else:
        errors.extend(
            _unexpected_keys(turbo, TURBO_SCREENING_KEYS, f"{label}.turbo_screening_input")
        )
        if isinstance(turbo, dict):
            if set(turbo) != TURBO_SCREENING_KEYS:
                errors.append(f"{label}.turbo_screening_input must be complete")
            if turbo.get("candidate_model") != "Garrett_G42_1325_pair_candidate":
                errors.append(f"{label} unexpected turbo candidate")
            for key, minimum, maximum in (
                ("compressor_inlet_pressure_pa_abs", 50000.0, 150000.0),
                ("compressor_inlet_temperature_k", 250.0, 350.0),
                ("charge_path_loss_pa", 0.0, 100000.0),
                ("compressor_isentropic_efficiency", 0.01, 1.0),
                ("compressor_gas_cp_j_kg_k", 500.0, 2000.0),
                ("compressor_gas_gamma", 1.01, 1.67),
                ("corrected_flow_reference_pressure_pa_abs", 50000.0, 150000.0),
                ("corrected_flow_reference_temperature_k", 250.0, 350.0),
                ("turbine_inlet_temperature_k", 500.0, 1600.0),
                ("turbine_outlet_pressure_pa_abs", 50000.0, 200000.0),
                ("turbine_isentropic_efficiency", 0.01, 1.0),
                ("turbo_mechanical_efficiency", 0.01, 1.0),
                ("exhaust_gas_cp_j_kg_k", 500.0, 2500.0),
                ("exhaust_gas_gamma", 1.01, 1.67),
            ):
                _finite_number(
                    errors,
                    turbo.get(key),
                    f"{label}.turbo_screening_input.{key}",
                    minimum=minimum,
                    maximum=maximum,
                )

    units = forward.get("unit_registry")
    if not isinstance(units, dict):
        errors.append(f"{label}.unit_registry must be an object")
    else:
        expected_units = _expected_units(forward, turbo_count)
        if units != expected_units:
            errors.append(f"{label}.unit_registry does not match exact SI unit contract")
    return errors


def validate_contract(contract: Any, project_root: Path = ROOT) -> list[str]:
    """Return all fail-closed contract errors without executing Cantera."""

    errors: list[str] = []
    if not isinstance(contract, dict):
        return ["contract must be an object"]
    errors.extend(_unexpected_keys(contract, TOP_LEVEL_KEYS, "contract"))
    missing_top = sorted((TOP_LEVEL_KEYS - {"$comment"}) - set(contract))
    if missing_top:
        errors.append(f"contract missing top-level keys: {missing_top}")
    if contract.get("schema_version") != "1.0.0":
        errors.append("schema_version must be 1.0.0")
    if contract.get("phase") != "F33":
        errors.append("phase must be F33")

    target = contract.get("requested_power_target")
    target_keys = {
        "value",
        "unit",
        "speed_rpm",
        "configuration",
        "origin",
        "measured",
        "simulated",
        "proven",
    }
    errors.extend(_unexpected_keys(target, target_keys, "requested_power_target"))
    if isinstance(target, dict):
        if set(target) != target_keys:
            errors.append("requested_power_target must contain exact keys")
        _finite_number(
            errors,
            target.get("value"),
            "requested_power_target.value",
            minimum=100.0,
            maximum=5000.0,
        )
        _finite_number(
            errors,
            target.get("speed_rpm"),
            "requested_power_target.speed_rpm",
            minimum=500.0,
            maximum=12000.0,
        )
        if target.get("unit") != "mechanical_hp":
            errors.append("requested power unit must be mechanical_hp")
        if target.get("configuration") != "twin_turbo":
            errors.append("requested power configuration must be twin_turbo")
        for key in ("measured", "simulated", "proven"):
            if target.get(key) is not False:
                errors.append(f"requested_power_target.{key} must be false")

    variants = contract.get("engine_variants")
    if not isinstance(variants, list):
        errors.append("engine_variants must be an array")
    else:
        ids = [item.get("id") for item in variants if isinstance(item, dict)]
        if len(variants) != 2 or set(ids) != set(EXPECTED_VARIANTS) or len(set(ids)) != 2:
            errors.append("engine_variants must contain exactly the NA and twin-turbo IDs")
        for index, variant in enumerate(variants):
            label = f"engine_variants[{index}]"
            errors.extend(_unexpected_keys(variant, VARIANT_KEYS, label))
            if not isinstance(variant, dict):
                continue
            if set(variant) != VARIANT_KEYS:
                errors.append(f"{label} must contain exact keys")
            variant_id = variant.get("id")
            if variant_id not in EXPECTED_VARIANTS:
                continue
            expected_count = EXPECTED_VARIANTS[variant_id]
            expected_configuration = (
                "naturally_aspirated" if expected_count == 0 else "twin_turbo"
            )
            if variant.get("configuration") != expected_configuration:
                errors.append(
                    f"{label}.configuration must be {expected_configuration}"
                )
            if variant.get("turbocharger_count") != expected_count:
                errors.append(f"{label}.turbocharger_count must be {expected_count}")
            if variant.get("solver_ready") is not False:
                errors.append(f"{label}.solver_ready must remain false")
            if variant.get("geometry_released") is not False:
                errors.append(f"{label}.geometry_released must remain false")
            if variant.get("engine_operation_authorized") is not False:
                errors.append(f"{label}.engine_operation_authorized must remain false")
            if expected_count == 0:
                if variant.get("requested_power_ref") is not None:
                    errors.append(f"{label} must not invent a NA requested power")
                if variant.get("turbo_data") is not None:
                    errors.append(f"{label}.turbo_data must be null for NA")
            else:
                if variant.get("requested_power_ref") != "requested_power_target":
                    errors.append(f"{label} must reference requested_power_target")
                turbo_data = variant.get("turbo_data")
                if not isinstance(turbo_data, dict):
                    errors.append(f"{label}.turbo_data must be an object")
                else:
                    errors.extend(
                        _unexpected_keys(turbo_data, TURBO_DATA_KEYS, f"{label}.turbo_data")
                    )
                    if set(turbo_data) != TURBO_DATA_KEYS:
                        errors.append(f"{label}.turbo_data must contain exact keys")
                    if any(
                        turbo_data.get(key) is not False
                        for key in (
                            "compressor_map_digitized",
                            "turbine_map_digitized",
                            "map_interpolation_executed",
                            "shaft_balance_forward_closed",
                            "turbo_match_validated",
                        )
                    ):
                        errors.append(f"{label}.turbo_data validation flags must be false")
                    for key in ("compressor_map_evidence", "turbine_map_evidence"):
                        if turbo_data.get(key) is not None:
                            errors.append(f"{label}.turbo_data.{key} must remain null")
            errors.extend(
                _validate_forward_input(
                    variant.get("forward_solver_input"), expected_count, f"{label}.forward_solver_input"
                )
            )

    gates = contract.get("release_gates")
    if not isinstance(gates, dict) or set(gates) != PHYSICAL_RELEASE_GATES:
        errors.append("release_gates must contain the exact F33 physical gate registry")
    elif any(value is not False for value in gates.values()):
        errors.append("all F33 physical release gates must remain false")

    semantic = contract.get("topology_acceptance")
    if not isinstance(semantic, dict):
        errors.append("topology_acceptance must be an object")
    else:
        if semantic.get("engine_variant_count") != 2:
            errors.append("topology_acceptance.engine_variant_count must be 2")
        if set(semantic.get("engine_variant_ids", [])) != set(EXPECTED_VARIANTS):
            errors.append("topology_acceptance.engine_variant_ids mismatch")
        if semantic.get("cooling_architecture_separate_from_engine_variant_identity") is not True:
            errors.append("cooling architecture must remain separate from variant identity")
        for branch_name in ("na", "turbo"):
            branch = semantic.get(branch_name)
            if not isinstance(branch, dict):
                errors.append(f"topology_acceptance.{branch_name} must be an object")
                continue
            if branch.get("semantic_topology_closed") is not True:
                errors.append(f"topology_acceptance.{branch_name} must be semantically closed")
            for key in (
                "physical_bom_complete",
                "geometry_complete",
                "boundary_conditions_complete",
                "solver_ready",
            ):
                if branch.get(key) is not False:
                    errors.append(f"topology_acceptance.{branch_name}.{key} must remain false")
        for key in (
            "all_pressure_boundaries_released",
            "all_seal_definitions_released",
            "all_sensor_chains_calibrated",
            "porsche_993_packaging_validated",
            "physical_correlation_complete",
        ):
            if semantic.get(key) is not False:
                errors.append(f"topology_acceptance.{key} must remain false")

    authority = contract.get("authority_boundary")
    errors.extend(_unexpected_keys(authority, AUTHORITY_KEYS, "authority_boundary"))
    if isinstance(authority, dict):
        if set(authority) != AUTHORITY_KEYS:
            errors.append("authority_boundary must contain exact keys")
        if authority.get("semantic_topology_closure_may_be_claimed") is not True:
            errors.append("semantic topology closure claim must be explicit")
        if authority.get("semantic_topology_closure_is_physical_closure") is not False:
            errors.append("semantic topology must not claim physical closure")
        for key in AUTHORITY_KEYS - {
            "f33_authority",
            "semantic_topology_closure_may_be_claimed",
            "semantic_topology_closure_definition",
            "allowed_claims",
            "f32_efi_intent_retained_as_unreleased_design_hypothesis",
        }:
            if authority.get(key) is not False:
                errors.append(f"authority_boundary.{key} must remain false")
        if authority.get("f32_efi_intent_retained_as_unreleased_design_hypothesis") is not True:
            errors.append("F32 EFI intent hypothesis flag must remain true")

    parents = contract.get("upstream_manifest")
    if not isinstance(parents, list) or not parents:
        errors.append("upstream_manifest must be a non-empty array")
    else:
        seen_paths: set[str] = set()
        for index, parent in enumerate(parents):
            label = f"upstream_manifest[{index}]"
            if not isinstance(parent, dict):
                errors.append(f"{label} must be an object")
                continue
            errors.extend(_unexpected_keys(parent, UPSTREAM_KEYS, label))
            path_value = parent.get("path")
            digest_value = parent.get("sha256")
            if not isinstance(path_value, str) or not path_value:
                errors.append(f"{label}.path missing")
                continue
            if path_value in seen_paths:
                errors.append(f"duplicate parent path: {path_value}")
            seen_paths.add(path_value)
            path = project_root / path_value
            if not path.is_file():
                errors.append(f"parent path missing: {path_value}")
            elif not isinstance(digest_value, str) or not re_full_sha256(digest_value):
                errors.append(f"{label}.sha256 invalid")
            elif _sha256(path) != digest_value:
                errors.append(f"parent SHA-256 mismatch: {path_value}")
        image_relative = str(IMAGE_PUBLICATION.relative_to(ROOT))
        if image_relative not in seen_paths:
            errors.append("runtime image publication must be a hashed parent")
    return errors


def re_full_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _round(value: float) -> float:
    return round(float(value), 12)


def _require_finite_mapping(value: Any, path: str = "result") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            _require_finite_mapping(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _require_finite_mapping(child, f"{path}[{index}]")
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"non-finite solver result: {path}")


def _solve_turbo_screen(
    forward: dict[str, Any],
    air_mass_flow_kg_s: float,
    exhaust_mass_flow_kg_s: float,
) -> dict[str, Any] | None:
    turbo_count = int(forward["turbocharger_count"])
    if turbo_count == 0:
        return None
    turbo = forward["turbo_screening_input"]
    p1 = float(turbo["compressor_inlet_pressure_pa_abs"])
    t1 = float(turbo["compressor_inlet_temperature_k"])
    p2 = float(forward["manifold_pressure_pa_abs"]) + float(turbo["charge_path_loss_pa"])
    pressure_ratio = p2 / p1
    gamma = float(turbo["compressor_gas_gamma"])
    cp = float(turbo["compressor_gas_cp_j_kg_k"])
    eta = float(turbo["compressor_isentropic_efficiency"])
    t2_isentropic = t1 * pressure_ratio ** ((gamma - 1.0) / gamma)
    t2 = t1 + (t2_isentropic - t1) / eta
    per_turbo_air = air_mass_flow_kg_s / turbo_count
    compressor_power_per_turbo = per_turbo_air * cp * (t2 - t1)
    charge_heat_total = air_mass_flow_kg_s * cp * (
        t2 - float(forward["manifold_temperature_k"])
    )
    corrected_flow = per_turbo_air * math.sqrt(
        t1 / float(turbo["corrected_flow_reference_temperature_k"])
    ) / (p1 / float(turbo["corrected_flow_reference_pressure_pa_abs"]))

    turbine_inlet_pressure = float(forward["exhaust_pressure_pa_abs"])
    turbine_outlet_pressure = float(turbo["turbine_outlet_pressure_pa_abs"])
    turbine_gamma = float(turbo["exhaust_gas_gamma"])
    turbine_cp = float(turbo["exhaust_gas_cp_j_kg_k"])
    turbine_eta = float(turbo["turbine_isentropic_efficiency"])
    mechanical_eta = float(turbo["turbo_mechanical_efficiency"])
    per_turbo_exhaust = exhaust_mass_flow_kg_s / turbo_count
    expansion_term = 1.0 - (turbine_outlet_pressure / turbine_inlet_pressure) ** (
        (turbine_gamma - 1.0) / turbine_gamma
    )
    turbine_power_full_flow = (
        per_turbo_exhaust
        * turbine_cp
        * float(turbo["turbine_inlet_temperature_k"])
        * turbine_eta
        * expansion_term
        * mechanical_eta
    )
    required_flow_fraction = compressor_power_per_turbo / turbine_power_full_flow
    inverse_wastegate_fraction = 1.0 - required_flow_fraction
    within_algebraic_capacity = 0.0 < required_flow_fraction <= 1.0
    return {
        "candidate_model": turbo["candidate_model"],
        "compressor_pressure_ratio": _round(pressure_ratio),
        "compressor_outlet_temperature_k": _round(t2),
        "compressor_power_per_turbo_w": _round(compressor_power_per_turbo),
        "compressor_power_total_w": _round(compressor_power_per_turbo * turbo_count),
        "charge_cooler_heat_rejection_w": _round(charge_heat_total),
        "air_mass_flow_per_turbo_kg_s": _round(per_turbo_air),
        "corrected_air_mass_flow_per_turbo_kg_s": _round(corrected_flow),
        "corrected_air_mass_flow_per_turbo_lb_min": _round(corrected_flow * 132.27735731),
        "exhaust_mass_flow_per_turbo_kg_s": _round(per_turbo_exhaust),
        "turbine_pressure_ratio": _round(turbine_inlet_pressure / turbine_outlet_pressure),
        "turbine_power_full_flow_per_turbo_w": _round(turbine_power_full_flow),
        "required_turbine_flow_fraction_inverse_screen": _round(required_flow_fraction),
        "required_wastegate_fraction_inverse_screen": _round(inverse_wastegate_fraction),
        "within_algebraic_full_flow_capacity": within_algebraic_capacity,
        "compressor_map_digitized": False,
        "turbine_map_digitized": False,
        "map_interpolation_executed": False,
        "shaft_balance_forward_closed": False,
        "turbo_match_validated": False,
        "classification": "algebraic_capacity_and_inverse_wastegate_screen_not_map_match",
    }


def solve_forward(forward: dict[str, Any]) -> dict[str, Any]:
    """Calculate a target-independent four-state closed-cycle screen."""

    if ct is None:
        raise RuntimeError(
            "Cantera is unavailable; execute the forward solver in the immutable F33 image"
        )
    if ct.__version__ != "3.2.0":
        raise RuntimeError(f"Cantera 3.2.0 required, got {ct.__version__}")
    bore_m = float(forward["bore_mm"]) / 1000.0
    stroke_m = float(forward["stroke_mm"]) / 1000.0
    cylinder_count = int(forward["cylinder_count"])
    compression_ratio = float(forward["compression_ratio"])
    speed_rpm = float(forward["speed_rpm"])
    displacement_per_cylinder_m3 = math.pi * bore_m**2 * stroke_m / 4.0
    displacement_m3 = displacement_per_cylinder_m3 * cylinder_count
    clearance_per_cylinder_m3 = displacement_per_cylinder_m3 / (compression_ratio - 1.0)
    bdc_volume_per_cylinder_m3 = displacement_per_cylinder_m3 + clearance_per_cylinder_m3
    cycles_per_second = speed_rpm / 120.0
    mean_piston_speed_m_s = 2.0 * stroke_m * speed_rpm / 60.0

    gas = ct.Solution("nDodecane_Reitz.yaml", "nDodecane_IG")
    gas.TP = (
        float(forward["manifold_temperature_k"]),
        float(forward["manifold_pressure_pa_abs"]),
    )
    gas.set_equivalence_ratio(
        float(forward["equivalence_ratio"]),
        "c12h26:1",
        "o2:1,n2:3.76",
    )
    mixture_mass_per_cylinder_kg = (
        gas.density
        * displacement_per_cylinder_m3
        * float(forward["volumetric_efficiency"])
    )
    fuel_mass_fraction = float(gas["c12h26"].Y[0])
    air_mass_fraction = 1.0 - fuel_mass_fraction

    # Volumetric efficiency follows the conventional displaced-volume basis;
    # therefore the effective IVC pressure is solved from trapped mass and BDC
    # volume rather than silently assuming the manifold pressure at BDC.
    gas.TD = (
        float(forward["manifold_temperature_k"]),
        mixture_mass_per_cylinder_kg / bdc_volume_per_cylinder_m3,
    )
    state_1 = {
        "temperature_k": gas.T,
        "pressure_pa_abs": gas.P,
        "specific_volume_m3_kg": gas.volume_mass,
        "specific_internal_energy_j_kg": gas.int_energy_mass,
        "specific_entropy_j_kg_k": gas.entropy_mass,
    }
    gas.SV = state_1["specific_entropy_j_kg_k"], state_1["specific_volume_m3_kg"] / compression_ratio
    state_2 = {
        "temperature_k": gas.T,
        "pressure_pa_abs": gas.P,
        "specific_internal_energy_j_kg": gas.int_energy_mass,
    }
    gas.equilibrate("UV")
    state_3 = {
        "temperature_k": gas.T,
        "pressure_pa_abs": gas.P,
        "specific_internal_energy_j_kg": gas.int_energy_mass,
        "specific_entropy_j_kg_k": gas.entropy_mass,
    }
    gas.SV = state_3["specific_entropy_j_kg_k"], state_1["specific_volume_m3_kg"]
    state_4 = {
        "temperature_k": gas.T,
        "pressure_pa_abs": gas.P,
        "specific_internal_energy_j_kg": gas.int_energy_mass,
    }
    compression_work_per_cylinder_j = mixture_mass_per_cylinder_kg * (
        state_2["specific_internal_energy_j_kg"]
        - state_1["specific_internal_energy_j_kg"]
    )
    expansion_work_per_cylinder_j = mixture_mass_per_cylinder_kg * (
        state_3["specific_internal_energy_j_kg"]
        - state_4["specific_internal_energy_j_kg"]
    )
    gross_indicated_work_per_cylinder_j = (
        expansion_work_per_cylinder_j - compression_work_per_cylinder_j
    )
    gross_indicated_power_w = (
        gross_indicated_work_per_cylinder_j * cycles_per_second * cylinder_count
    )
    retained_indicated_power_w = gross_indicated_power_w * float(
        forward["indicated_work_retention"]
    )

    fmep = forward["fmep_model"]
    fmep_bar = (
        float(fmep["base_bar"])
        + float(fmep["mean_piston_speed_linear_bar_per_m_s"])
        * mean_piston_speed_m_s
        + float(fmep["mean_piston_speed_quadratic_bar_per_m_s2"])
        * mean_piston_speed_m_s**2
    )
    friction_power_w = fmep_bar * 100000.0 * displacement_m3 * cycles_per_second
    pumping_mep_pa = float(forward["exhaust_pressure_pa_abs"]) - state_1["pressure_pa_abs"]
    pumping_power_w = pumping_mep_pa * displacement_m3 * cycles_per_second
    accessory_power_w = float(forward["accessory_power_w"])
    brake_power_w = (
        retained_indicated_power_w
        - friction_power_w
        - pumping_power_w
        - accessory_power_w
    )
    if brake_power_w <= 0.0:
        raise RuntimeError("forward brake power is not positive")

    fuel_mass_flow_kg_s = (
        mixture_mass_per_cylinder_kg
        * fuel_mass_fraction
        * cycles_per_second
        * cylinder_count
    )
    air_mass_flow_kg_s = (
        mixture_mass_per_cylinder_kg
        * air_mass_fraction
        * cycles_per_second
        * cylinder_count
    )
    exhaust_mass_flow_kg_s = fuel_mass_flow_kg_s + air_mass_flow_kg_s
    fuel_power_w = fuel_mass_flow_kg_s * float(forward["fuel_lhv_j_kg"])
    brake_thermal_efficiency = brake_power_w / fuel_power_w
    bsfc_g_kwh = fuel_mass_flow_kg_s * 3.6e9 / brake_power_w
    torque_nm = brake_power_w * 60.0 / (2.0 * math.pi * speed_rpm)
    bmep_pa = brake_power_w / (displacement_m3 * cycles_per_second)

    turbo = _solve_turbo_screen(
        forward,
        air_mass_flow_kg_s=air_mass_flow_kg_s,
        exhaust_mass_flow_kg_s=exhaust_mass_flow_kg_s,
    )
    thermal = forward["thermal_hypotheses"]
    head_heat_w = fuel_power_w * float(thermal["head_heat_fraction_of_fuel_power"])
    cylinder_air_heat_w = fuel_power_w * float(
        thermal["cylinder_air_heat_fraction_of_fuel_power"]
    )
    oil_heat_w = (
        fuel_power_w * float(thermal["base_oil_heat_fraction_of_fuel_power"])
        + friction_power_w * float(thermal["friction_to_oil_fraction"])
    )
    charge_heat_w = turbo["charge_cooler_heat_rejection_w"] if turbo else 0.0
    head_coolant_flow_kg_s = head_heat_w / (
        float(thermal["coolant_cp_j_kg_k"])
        * float(thermal["head_coolant_delta_t_k"])
    )
    oil_flow_kg_s = oil_heat_w / (
        float(thermal["oil_cp_j_kg_k"]) * float(thermal["oil_delta_t_k"])
    )
    charge_coolant_flow_kg_s = None
    if turbo:
        charge_coolant_flow_kg_s = charge_heat_w / (
            float(thermal["charge_coolant_cp_j_kg_k"])
            * float(thermal["charge_coolant_delta_t_k"])
        )

    result = {
        "classification": "non_correlated_four_state_closed_cycle_0d_forward_screen",
        "target_used_as_solver_input": False,
        "geometry_and_speed": {
            "displacement_l": _round(displacement_m3 * 1000.0),
            "speed_rpm": _round(speed_rpm),
            "mean_piston_speed_m_s": _round(mean_piston_speed_m_s),
            "compression_ratio": _round(compression_ratio),
        },
        "trapped_charge": {
            "effective_ivc_pressure_pa_abs": _round(state_1["pressure_pa_abs"]),
            "mixture_mass_per_cylinder_kg": _round(mixture_mass_per_cylinder_kg),
            "air_mass_flow_kg_s": _round(air_mass_flow_kg_s),
            "fuel_mass_flow_kg_s": _round(fuel_mass_flow_kg_s),
            "exhaust_mass_flow_identity_kg_s": _round(exhaust_mass_flow_kg_s),
            "mass_identity_residual_kg_s": _round(
                exhaust_mass_flow_kg_s - air_mass_flow_kg_s - fuel_mass_flow_kg_s
            ),
        },
        "idealized_states": {
            "ivc": {
                "temperature_k": _round(state_1["temperature_k"]),
                "pressure_pa_abs": _round(state_1["pressure_pa_abs"]),
            },
            "compression_end": {
                "temperature_k": _round(state_2["temperature_k"]),
                "pressure_pa_abs": _round(state_2["pressure_pa_abs"]),
            },
            "constant_volume_equilibrium_end": {
                "temperature_k": _round(state_3["temperature_k"]),
                "pressure_pa_abs": _round(state_3["pressure_pa_abs"]),
            },
            "expansion_end": {
                "temperature_k": _round(state_4["temperature_k"]),
                "pressure_pa_abs": _round(state_4["pressure_pa_abs"]),
            },
        },
        "work_and_power": {
            "gross_indicated_power_w": _round(gross_indicated_power_w),
            "retained_indicated_power_w": _round(retained_indicated_power_w),
            "friction_power_w": _round(friction_power_w),
            "pumping_power_w": _round(pumping_power_w),
            "accessory_power_w": _round(accessory_power_w),
            "forward_predicted_brake_power_w": _round(brake_power_w),
            "forward_predicted_mechanical_hp": _round(brake_power_w / MECHANICAL_HP_W),
            "forward_predicted_metric_ps": _round(brake_power_w / METRIC_PS_W),
            "forward_predicted_torque_nm": _round(torque_nm),
            "forward_predicted_bmep_bar": _round(bmep_pa / 100000.0),
            "brake_thermal_efficiency": _round(brake_thermal_efficiency),
            "bsfc_g_kwh": _round(bsfc_g_kwh),
            "fuel_power_w": _round(fuel_power_w),
        },
        "turbo_screen": turbo,
        "thermal_network_screen": {
            "loads_w": {
                "head_ht_coolant": _round(head_heat_w),
                "cylinder_fin_air": _round(cylinder_air_heat_w),
                "oil_loop": _round(oil_heat_w),
                "charge_lt_coolant": _round(charge_heat_w) if turbo else None,
                "turbo_chra_and_hot_soak": None,
            },
            "required_mass_flows_kg_s": {
                "head_coolant": _round(head_coolant_flow_kg_s),
                "oil": _round(oil_flow_kg_s),
                "charge_coolant": _round(charge_coolant_flow_kg_s)
                if charge_coolant_flow_kg_s is not None
                else None,
                "turbo_chra_coolant": None,
            },
            "hydraulic_solution_executed": False,
            "heat_exchanger_ua_solution_executed": False,
            "cht_executed": False,
            "thermal_system_validated": False,
        },
        "numerical_scope": {
            "cantera_equilibrium_uv_executed": True,
            "closed_cycle_four_state_only": True,
            "crank_angle_time_marching_executed": False,
            "cyclic_convergence_executed": False,
            "one_dimensional_gas_dynamics_executed": False,
            "cfd_or_cht_executed": False,
            "combustion_calibrated": False,
            "knock_model_executed": False,
            "physical_correlation_complete": False,
        },
    }
    _require_finite_mapping(result)
    return result


def build_report(
    contract: dict[str, Any],
    contract_path: Path = CONTRACT,
    project_root: Path = ROOT,
) -> dict[str, Any]:
    """Validate the contract and build deterministic target-independent outputs."""

    errors = validate_contract(contract, project_root=project_root)
    if errors:
        raise ValueError("invalid F33 contract:\n- " + "\n- ".join(errors))
    predictions: list[dict[str, Any]] = []
    for variant in sorted(contract["engine_variants"], key=lambda item: item["id"]):
        forward_prediction = solve_forward(copy.deepcopy(variant["forward_solver_input"]))
        predictions.append(
            {
                "variant_id": variant["id"],
                "configuration": variant["configuration"],
                "forward_prediction": forward_prediction,
            }
        )

    target = contract["requested_power_target"]
    turbo_prediction = next(
        item
        for item in predictions
        if item["variant_id"] == "917_2026_flat12_twin_turbo_1600hp_target"
    )
    predicted_hp = turbo_prediction["forward_prediction"]["work_and_power"][
        "forward_predicted_mechanical_hp"
    ]
    target_delta_hp = predicted_hp - float(target["value"])
    image_publication_path = project_root / IMAGE_PUBLICATION.relative_to(ROOT)
    image_publication = _read_json(image_publication_path)
    topology = contract["topology_acceptance"]
    normalized_topology = {
        "source": "topology_acceptance",
        "semantic_topology_closed": bool(
            topology["na"]["semantic_topology_closed"]
            and topology["turbo"]["semantic_topology_closed"]
        ),
        "physical_bom_complete": False,
        "solver_ready": False,
        "cooling_validated": False,
        "target_power_proven": False,
        "engine_start_authorized": False,
        "vehicle_installation_authorized": False,
    }
    report = {
        "schema_version": "1.0.0",
        "phase": "F33",
        "status": "non_correlated_0d_forward_screen_complete_all_physical_gates_blocked",
        "contract_sha256": _canonical_payload_sha256(contract),
        "contract_file_sha256": _sha256(contract_path),
        "parent_image_publication": {
            "path": str(IMAGE_PUBLICATION.relative_to(ROOT)),
            "sha256": _sha256(image_publication_path),
            "immutable_ref": image_publication["image"]["immutable_ref"],
            "workflow_run_id": image_publication["workflow"]["run_id"],
            "anonymous_exact_digest_access_verified": image_publication["image"][
                "anonymous_exact_digest_access_verified"
            ],
            "verified": True,
            "engine_solver_in_image": False,
        },
        "requested_power_target": copy.deepcopy(target),
        "forward_predictions": predictions,
        "target_comparison": {
            "variant_id": turbo_prediction["variant_id"],
            "requested_mechanical_hp": float(target["value"]),
            "forward_predicted_mechanical_hp": predicted_hp,
            "delta_mechanical_hp": _round(target_delta_hp),
            "absolute_relative_delta": _round(abs(target_delta_hp) / float(target["value"])),
            "target_used_as_solver_input": False,
            "inverse_sizing_seed_present": True,
            "screening_target_within_one_percent": abs(target_delta_hp) / float(target["value"])
            <= 0.01,
            "target_power_proven": False,
        },
        "semantic_topology": normalized_topology,
        "model_scope": {
            "maximum_model_dimension": "0D",
            "cantera_role": "zero_dimensional_thermochemistry_only_not_engine_cycle_proof",
            "cantera_version": ct.__version__,
            "thermochemistry_backend": "Cantera_nDodecane_IG_builtin",
            "forward_closed_cycle_0d_executed": True,
            "twelve_open_cylinders_executed": False,
            "one_dimensional_gas_dynamics_executed": False,
            "turbo_map_interpolation_executed": False,
            "hydraulic_network_executed": False,
            "cfd_executed": False,
            "cht_executed": False,
            "physicsnemo_executed": False,
            "omniverse_executed": False,
            "dyno_measurement_available": False,
            "physical_bench_correlation_complete": False,
            "physical_correlation_complete": False,
        },
        "technical_gates": {
            "reference_solver_executed": True,
            "finite_outputs_emitted": True,
            "target_independence_by_construction": True,
            "semantic_topology_closed": True,
        },
        "release_gates": copy.deepcopy(contract["release_gates"]),
        "required_next_evidence": [
            "open_cylinder_crank_angle_cycle_with_valves_and_plenums",
            "angular_step_and_cycle_convergence",
            "measured_or_calibrated_combustion_and_friction",
            "digitized_compressor_and_turbine_maps_with_licenses_and_hashes",
            "forward_coupled_turbo_shaft_balance_and_transient_rotor_dynamics",
            "measured_conduit_geometry_and_one_dimensional_gas_dynamics",
            "oil_ht_lt_pressure_drop_pump_and_heat_exchanger_curves",
            "turbo_chra_heat_and_hot_soak_load",
            "classical_cfd_cht_and_fea_with_independence_studies",
            "instrumented_progressive_test_bench_and_held_out_correlation",
            "measured_porsche_993_packaging_and_vehicle_validation",
        ],
    }
    _require_finite_mapping(report)
    if any(report["release_gates"].values()):
        raise RuntimeError("a physical release gate opened in F33 report")
    return report


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
    ) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=CONTRACT)
    destination = parser.add_mutually_exclusive_group(required=True)
    destination.add_argument("--output", type=Path)
    destination.add_argument("--check", type=Path)
    args = parser.parse_args(argv)
    try:
        contract = _read_json(args.contract)
        report = build_report(
            contract,
            contract_path=args.contract,
            project_root=ROOT,
        )
        rendered = _canonical_json(report)
        if args.check is not None:
            expected = _canonical_json(_read_json(args.check))
            if rendered != expected:
                raise ValueError(f"stale F33 report: {args.check}")
            print(f"F33 report check OK: {args.check}")
            return 0
        assert args.output is not None
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"F33 report written: {args.output}")
        return 0
    except (
        KeyError,
        OSError,
        TypeError,
        ValueError,
        RuntimeError,
        CANTERA_ERROR,
    ) as error:
        print(f"F33 cycle/thermal error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
