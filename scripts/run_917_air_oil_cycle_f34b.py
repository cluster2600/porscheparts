#!/usr/bin/env python3
"""F34b CPU-only air/oil cycle screen and fail-closed runtime preflight.

Only two execution modes exist in this lot:

* ``preflight`` validates the selected F34/F34a architecture and the two
  self-contained F34 air/oil seeds using the Python standard library only;
* ``synthetic-smoke`` evaluates two deliberately displaced regression
  fixtures only after proving that their hashes are absent from the canonical
  DOE manifest; it loads Cantera 3.2.0 lazily.

This runtime does not load a legacy liquid-head contract or executable legacy
solver.  Their ancestry is resolved before the self-contained seed bundle is
published.  Outputs are non-correlated numerical screens, not proof of power,
cooling, durability, controls, PhysicsNeMo, Omniverse, or manufacturing
readiness.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import json
import math
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOE_CONTRACT = ROOT / "twins/reference-917-engine/doe-surrogate-f34.json"
ARCHITECTURE_CONTRACT = (
    ROOT / "twins/reference-917-engine/air-oil-core-controls-f34a.json"
)
SEED_BUNDLE = (
    ROOT
    / "twins/reference-917-engine/evidence/f34/air-oil-forward-seeds-f34b.json"
)
DOE_MANIFEST = (
    ROOT / "twins/reference-917-engine/evidence/f34/doe-case-manifest.json"
)

EXPECTED_CONFIGURATIONS = {
    "naturally_aspirated": {
        "variant_id": "917_2026_flat12_na_air_oil_f34b",
        "turbocharger_count": 0,
    },
    "twin_turbo": {
        "variant_id": "917_2026_flat12_twin_turbo_air_oil_f34b",
        "turbocharger_count": 2,
    },
}
EXPECTED_ARCHITECTURE_ID = "F34A-AIR-OIL-CORE-2026-CONTROLS"
EXPECTED_MANAGEMENT_ID = "917_2026_modern_ecu_twin_spark_sequential_efi"
SYNTHETIC_FIXTURE_SPEED_RPM = {
    "naturally_aspirated": 8123.0,
    "twin_turbo": 8377.0,
}
MECHANICAL_HP_W = 745.6998715822702
METRIC_PS_W = 735.49875
SEED_PARENT_SPECS = (
    (
        "f34a_air_oil_core_controls",
        "twins/reference-917-engine/air-oil-core-controls-f34a.json",
        "selected_air_oil_core_and_modern_controls_authority",
    ),
    (
        "f34_doe_contract",
        "twins/reference-917-engine/doe-surrogate-f34.json",
        "validated_seed_generation_contract",
    ),
    (
        "f34_doe_case_manifest",
        "twins/reference-917-engine/evidence/f34/doe-case-manifest.json",
        "verified_zero_execution_case_plan",
    ),
    (
        "f34_doe_generator",
        "scripts/run_917_doe_f34.py",
        "verified_air_oil_seed_transform_source",
    ),
)

COMMON_FORWARD_KEYS = {
    "accessory_power_w",
    "bore_mm",
    "compression_ratio",
    "cylinder_count",
    "engine_management",
    "equivalence_ratio",
    "exhaust_pressure_pa_abs",
    "fmep_model",
    "fuel_lhv_j_kg",
    "fuel_surrogate",
    "indicated_work_retention",
    "manifold_pressure_pa_abs",
    "manifold_temperature_k",
    "selected_architecture",
    "speed_rpm",
    "stroke_mm",
    "thermal_hypotheses",
    "turbo_screening_input",
    "turbocharger_count",
    "unit_registry",
    "volumetric_efficiency",
}
FMEP_KEYS = {
    "base_bar",
    "mean_piston_speed_linear_bar_per_m_s",
    "mean_piston_speed_quadratic_bar_per_m_s2",
}
COMMON_THERMAL_KEYS = {
    "base_oil_heat_fraction_of_fuel_power",
    "cooling_air_cp_j_kg_k",
    "cooling_air_delta_t_k",
    "cylinder_heat_fraction_of_fuel_power",
    "friction_to_oil_fraction",
    "head_heat_fraction_of_fuel_power",
    "head_heat_to_oil_fraction",
    "oil_cp_j_kg_k",
    "oil_delta_t_k",
}
TT_THERMAL_KEYS = {
    "charge_coolant_cp_j_kg_k",
    "charge_coolant_delta_t_k",
}
TURBO_KEYS = {
    "candidate_model",
    "charge_path_loss_pa",
    "compressor_gas_cp_j_kg_k",
    "compressor_gas_gamma",
    "compressor_inlet_pressure_pa_abs",
    "compressor_inlet_temperature_k",
    "compressor_isentropic_efficiency",
    "corrected_flow_reference_pressure_pa_abs",
    "corrected_flow_reference_temperature_k",
    "exhaust_gas_cp_j_kg_k",
    "exhaust_gas_gamma",
    "turbine_inlet_temperature_k",
    "turbine_isentropic_efficiency",
    "turbine_outlet_pressure_pa_abs",
    "turbo_mechanical_efficiency",
}
ARCHITECTURE_KEYS = {
    "auxiliary_liquid_scope",
    "engine_core_heat_rejection",
    "engine_core_liquid_coolant_present",
    "id",
}
MANAGEMENT_KEYS = {
    "architecture_id",
    "can_fd_required",
    "closed_loop_lambda_required",
    "cylinder_attributed_knock_control_candidate",
    "drive_by_wire_actuators_minimum",
    "drive_by_wire_required",
    "dual_electronic_ignition_required",
    "electronic_fuel_injection_required",
    "electronic_wastegate_control_required",
    "hardware_maps_thresholds_validated",
    "independent_ignition_channels_required",
    "independent_injection_channels_target",
    "response_model_present_in_l0",
    "sequential_port_injection_required",
    "staged_port_injection_candidate",
    "variable_cam_timing_candidate",
    "variable_valve_lift_candidate",
}
F34A_TECHNICAL_GATE_IDS = {
    "auxiliary_liquid_isolation_verified",
    "boost_failsafe_validated",
    "communications_architecture_validated",
    "control_maps_available",
    "controls_hardware_selected",
    "core_geometry_defined",
    "dry_sump_oil_network_solved",
    "forced_air_network_solved",
    "hardwired_interlocks_verified",
    "knock_control_calibrated",
    "lambda_closed_loop_calibrated",
    "safety_thresholds_validated",
    "sensor_chains_calibrated",
    "vvt_vvl_hardware_selected",
    "vvt_vvl_maps_available",
}
F34A_RELEASE_GATE_IDS = {
    "air_cooling_validated",
    "architecture_physically_validated",
    "auxiliary_liquid_system_validated",
    "boost_control_validated",
    "communications_validated",
    "controls_and_logging_validated",
    "engine_bench_start_authorized",
    "knock_control_validated",
    "lambda_control_validated",
    "manufacturing_authorized",
    "metal_print_authorized",
    "oil_system_validated",
    "porsche_993_fitment_validated",
    "ruf_compatibility_validated",
    "target_power_proven",
    "vehicle_installation_authorized",
    "vvt_vvl_validated",
}
F34_RELEASE_GATE_IDS = {
    "boost_failsafe_validated",
    "can_fd_architecture_validated",
    "cfd_validated",
    "cht_validated",
    "closed_loop_controls_validated",
    "cooling_system_validated",
    "crank_cam_sync_validated",
    "dataset_ready",
    "doe_execution_complete",
    "ecu_hardware_selected",
    "ecu_io_complete",
    "hil_complete",
    "hydraulic_network_validated",
    "ignition_validated",
    "injector_characterization_validated",
    "knock_control_validated",
    "lambda_control_validated",
    "manufacturing_authorized",
    "metal_print_authorized",
    "one_dimensional_model_validated",
    "ood_policy_calibrated",
    "physical_correlation_complete",
    "porsche_993_vehicle_installation_authorized",
    "sil_complete",
    "surrogate_trained",
    "surrogate_validated_against_0d_solver",
    "target_power_proven",
    "test_bench_start_authorized",
    "training_authorized",
    "vvt_vvl_validated",
}
F34B_SEED_PHYSICAL_GATE_IDS = {
    "air_cooling_physically_validated",
    "auxiliary_liquid_isolation_physically_validated",
    "controls_physically_validated",
    "engine_bench_start_authorized",
    "manufacturing_authorized",
    "metal_print_authorized",
    "oil_system_physically_validated",
    "physical_correlation_complete",
    "target_power_proven",
    "vehicle_installation_authorized",
}


class F34bInputError(ValueError):
    """Raised when an F34 input or its contract ancestry fails closed."""


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant rejected: {value}")


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key rejected: {key}")
        result[key] = value
    return result


def _read_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=_reject_constant,
        object_pairs_hook=_reject_duplicate_pairs,
    )


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _round(value: float) -> float:
    return round(float(value), 12)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _finite_float(value: Any, label: str) -> float:
    if not _is_number(value):
        raise F34bInputError(f"{label} must be a number, not {type(value).__name__}")
    result = float(value)
    if not math.isfinite(result):
        raise F34bInputError(f"{label} must be finite")
    return result


def _positive(value: Any, label: str, *, allow_zero: bool = False) -> float:
    result = _finite_float(value, label)
    if allow_zero:
        if result < 0.0:
            raise F34bInputError(f"{label} must be non-negative")
    elif result <= 0.0:
        raise F34bInputError(f"{label} must be positive")
    return result


def _ratio(value: Any, label: str, *, include_zero: bool = False) -> float:
    result = _finite_float(value, label)
    lower_ok = result >= 0.0 if include_zero else result > 0.0
    if not lower_ok or result > 1.0:
        interval = "[0,1]" if include_zero else "(0,1]"
        raise F34bInputError(f"{label} must be in {interval}")
    return result


def _exact_keys(mapping: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(mapping, dict):
        raise F34bInputError(f"{label} must be an object")
    actual = set(mapping)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise F34bInputError(f"{label} keys mismatch; missing={missing}; extra={extra}")
    return mapping


def _require_closed_gate_set(
    mapping: Any, expected: set[str], label: str
) -> dict[str, Any]:
    gates = _exact_keys(mapping, expected, label)
    if any(value is not False for value in gates.values()):
        raise F34bInputError(f"all {label} must remain false")
    return gates


def _require_finite_tree(value: Any, path: str = "result") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            _require_finite_tree(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _require_finite_tree(child, f"{path}[{index}]")
    elif isinstance(value, float) and not math.isfinite(value):
        raise F34bInputError(f"non-finite numerical output at {path}")


def _walk_keys(value: Any, prefix: str = ""):
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else key
            yield path
            yield from _walk_keys(child, path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_keys(child, f"{prefix}[{index}]")


def _expected_management(configuration: str) -> dict[str, Any]:
    return {
        "architecture_id": EXPECTED_MANAGEMENT_ID,
        "electronic_fuel_injection_required": True,
        "sequential_port_injection_required": True,
        "staged_port_injection_candidate": True,
        "independent_injection_channels_target": 24,
        "dual_electronic_ignition_required": True,
        "independent_ignition_channels_required": 24,
        "drive_by_wire_required": True,
        "drive_by_wire_actuators_minimum": 2,
        "variable_cam_timing_candidate": True,
        "variable_valve_lift_candidate": True,
        "closed_loop_lambda_required": True,
        "cylinder_attributed_knock_control_candidate": True,
        "electronic_wastegate_control_required": configuration == "twin_turbo",
        "can_fd_required": True,
        "hardware_maps_thresholds_validated": False,
        "response_model_present_in_l0": False,
    }


def _expected_architecture(configuration: str) -> dict[str, Any]:
    return {
        "id": EXPECTED_ARCHITECTURE_ID,
        "engine_core_liquid_coolant_present": False,
        "engine_core_heat_rejection": ["forced_air", "dry_sump_oil"],
        "auxiliary_liquid_scope": (
            ["charge_cooling", "turbo_chra_optional_unresolved"]
            if configuration == "twin_turbo"
            else []
        ),
    }


def _expected_units(configuration: str) -> dict[str, str]:
    units = {
        "accessory_power_w": "W",
        "bore_mm": "mm",
        "compression_ratio": "ratio",
        "cylinder_count": "count",
        "equivalence_ratio": "ratio",
        "exhaust_pressure_pa_abs": "Pa_abs",
        "fmep_model.base_bar": "bar",
        "fmep_model.mean_piston_speed_linear_bar_per_m_s": "bar/(m/s)",
        "fmep_model.mean_piston_speed_quadratic_bar_per_m_s2": "bar/(m/s)^2",
        "fuel_lhv_j_kg": "J/kg",
        "indicated_work_retention": "ratio",
        "manifold_pressure_pa_abs": "Pa_abs",
        "manifold_temperature_k": "K",
        "speed_rpm": "rpm",
        "stroke_mm": "mm",
        "thermal_hypotheses.base_oil_heat_fraction_of_fuel_power": "ratio",
        "thermal_hypotheses.cooling_air_cp_j_kg_k": "J/(kg*K)",
        "thermal_hypotheses.cooling_air_delta_t_k": "K",
        "thermal_hypotheses.cylinder_heat_fraction_of_fuel_power": "ratio",
        "thermal_hypotheses.friction_to_oil_fraction": "ratio",
        "thermal_hypotheses.head_heat_fraction_of_fuel_power": "ratio",
        "thermal_hypotheses.head_heat_to_oil_fraction": "ratio",
        "thermal_hypotheses.oil_cp_j_kg_k": "J/(kg*K)",
        "thermal_hypotheses.oil_delta_t_k": "K",
        "turbocharger_count": "count",
        "volumetric_efficiency": "ratio",
    }
    if configuration == "twin_turbo":
        units.update(
            {
                "thermal_hypotheses.charge_coolant_cp_j_kg_k": "J/(kg*K)",
                "thermal_hypotheses.charge_coolant_delta_t_k": "K",
                "turbo_screening_input.charge_path_loss_pa": "Pa",
                "turbo_screening_input.compressor_gas_cp_j_kg_k": "J/(kg*K)",
                "turbo_screening_input.compressor_gas_gamma": "ratio",
                "turbo_screening_input.compressor_inlet_pressure_pa_abs": "Pa_abs",
                "turbo_screening_input.compressor_inlet_temperature_k": "K",
                "turbo_screening_input.compressor_isentropic_efficiency": "ratio",
                "turbo_screening_input.corrected_flow_reference_pressure_pa_abs": "Pa_abs",
                "turbo_screening_input.corrected_flow_reference_temperature_k": "K",
                "turbo_screening_input.exhaust_gas_cp_j_kg_k": "J/(kg*K)",
                "turbo_screening_input.exhaust_gas_gamma": "ratio",
                "turbo_screening_input.turbine_inlet_temperature_k": "K",
                "turbo_screening_input.turbine_isentropic_efficiency": "ratio",
                "turbo_screening_input.turbine_outlet_pressure_pa_abs": "Pa_abs",
                "turbo_screening_input.turbo_mechanical_efficiency": "ratio",
            }
        )
    return units


def validate_f34_forward_input(forward: dict[str, Any], configuration: str) -> None:
    """Fail closed unless ``forward`` is exactly the selected F34 L0 schema."""

    if configuration not in EXPECTED_CONFIGURATIONS:
        raise F34bInputError(f"unsupported configuration: {configuration}")
    _exact_keys(forward, COMMON_FORWARD_KEYS, "forward")
    for path in _walk_keys(forward):
        lowered = path.lower()
        if "requested_power" in lowered or "target_power" in lowered:
            raise F34bInputError(f"power target field is forbidden in forward input: {path}")

    _positive(forward["bore_mm"], "bore_mm")
    _positive(forward["stroke_mm"], "stroke_mm")
    cylinders = _finite_float(forward["cylinder_count"], "cylinder_count")
    if cylinders != 12.0 or int(cylinders) != cylinders:
        raise F34bInputError("cylinder_count must be the frozen integer 12")
    if _finite_float(forward["compression_ratio"], "compression_ratio") <= 1.0:
        raise F34bInputError("compression_ratio must be greater than one")
    _positive(forward["speed_rpm"], "speed_rpm")
    _positive(forward["manifold_pressure_pa_abs"], "manifold_pressure_pa_abs")
    _positive(forward["manifold_temperature_k"], "manifold_temperature_k")
    _positive(forward["volumetric_efficiency"], "volumetric_efficiency")
    _positive(forward["equivalence_ratio"], "equivalence_ratio")
    _positive(forward["exhaust_pressure_pa_abs"], "exhaust_pressure_pa_abs")
    _ratio(forward["indicated_work_retention"], "indicated_work_retention")
    _positive(forward["accessory_power_w"], "accessory_power_w", allow_zero=True)
    _positive(forward["fuel_lhv_j_kg"], "fuel_lhv_j_kg")
    if forward["fuel_surrogate"] != "n_dodecane_cantera_builtin":
        raise F34bInputError("fuel_surrogate must remain n_dodecane_cantera_builtin")

    fmep = _exact_keys(forward["fmep_model"], FMEP_KEYS, "fmep_model")
    for key, value in fmep.items():
        _positive(value, f"fmep_model.{key}", allow_zero=True)

    expected_thermal = COMMON_THERMAL_KEYS | (
        TT_THERMAL_KEYS if configuration == "twin_turbo" else set()
    )
    thermal = _exact_keys(
        forward["thermal_hypotheses"], expected_thermal, "thermal_hypotheses"
    )
    for key in (
        "head_heat_fraction_of_fuel_power",
        "cylinder_heat_fraction_of_fuel_power",
        "base_oil_heat_fraction_of_fuel_power",
        "friction_to_oil_fraction",
        "head_heat_to_oil_fraction",
    ):
        _ratio(thermal[key], f"thermal_hypotheses.{key}", include_zero=True)
    thermal_sum = sum(
        float(thermal[key])
        for key in (
            "head_heat_fraction_of_fuel_power",
            "cylinder_heat_fraction_of_fuel_power",
            "base_oil_heat_fraction_of_fuel_power",
        )
    )
    if not thermal_sum < 0.8:
        raise F34bInputError("thermal fuel-power fractions must sum to less than 0.8")
    for key in (
        "cooling_air_cp_j_kg_k",
        "cooling_air_delta_t_k",
        "oil_cp_j_kg_k",
        "oil_delta_t_k",
    ):
        _positive(thermal[key], f"thermal_hypotheses.{key}")
    if configuration == "twin_turbo":
        for key in TT_THERMAL_KEYS:
            _positive(thermal[key], f"thermal_hypotheses.{key}")

    architecture = _exact_keys(
        forward["selected_architecture"], ARCHITECTURE_KEYS, "selected_architecture"
    )
    if architecture != _expected_architecture(configuration):
        raise F34bInputError("selected architecture does not match F34a air/oil boundary")
    management = _exact_keys(
        forward["engine_management"], MANAGEMENT_KEYS, "engine_management"
    )
    if management != _expected_management(configuration):
        raise F34bInputError("engine management lock does not match F34a")

    expected_turbos = EXPECTED_CONFIGURATIONS[configuration]["turbocharger_count"]
    turbo_count = _finite_float(forward["turbocharger_count"], "turbocharger_count")
    if turbo_count != float(expected_turbos) or int(turbo_count) != turbo_count:
        raise F34bInputError(f"turbocharger_count must be {expected_turbos}")
    turbo = forward["turbo_screening_input"]
    if configuration == "naturally_aspirated":
        if turbo is not None:
            raise F34bInputError("naturally aspirated input must not contain turbo data")
    else:
        turbo = _exact_keys(turbo, TURBO_KEYS, "turbo_screening_input")
        if not isinstance(turbo["candidate_model"], str) or not turbo["candidate_model"]:
            raise F34bInputError("turbo candidate_model must be a non-empty string")
        for key, value in turbo.items():
            if key == "candidate_model":
                continue
            _positive(value, f"turbo_screening_input.{key}", allow_zero=key == "charge_path_loss_pa")
        for key in (
            "compressor_isentropic_efficiency",
            "turbine_isentropic_efficiency",
            "turbo_mechanical_efficiency",
        ):
            _ratio(turbo[key], f"turbo_screening_input.{key}")
        for key in ("compressor_gas_gamma", "exhaust_gas_gamma"):
            if float(turbo[key]) <= 1.0:
                raise F34bInputError(f"turbo_screening_input.{key} must exceed one")
        if float(turbo["turbine_outlet_pressure_pa_abs"]) >= float(
            forward["exhaust_pressure_pa_abs"]
        ):
            raise F34bInputError("turbine outlet pressure must be below exhaust pressure")

    units = forward["unit_registry"]
    if units != _expected_units(configuration):
        raise F34bInputError("unit_registry does not exactly match the F34 schema")

    forbidden_core_keys = {
        "coolant_cp_j_kg_k",
        "head_coolant_delta_t_k",
        "cylinder_air_heat_fraction_of_fuel_power",
    }
    present = forbidden_core_keys & set(thermal)
    if present:
        raise F34bInputError(f"legacy liquid-core thermal fields forbidden: {sorted(present)}")


def _seeds_by_configuration(bundle: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Validate the autonomous bundle and return its two complete F34 seeds."""

    if not isinstance(bundle, dict):
        raise F34bInputError("seed bundle must be an object")
    expected_top_level = {
        "$comment",
        "architecture_id",
        "authority_boundary",
        "bundle_payload_sha256",
        "canonical_doe_cases_executed",
        "execution_ledger",
        "image_runtime_contract",
        "parents",
        "phase",
        "physical_gates",
        "release_gates",
        "schema_version",
        "seeds",
        "source_verification",
        "status",
    }
    if set(bundle) != expected_top_level:
        raise F34bInputError("seed bundle top-level schema mismatch")
    if bundle.get("schema_version") != "1.0.0":
        raise F34bInputError("seed bundle schema version mismatch")
    if bundle.get("phase") != "F34b":
        raise F34bInputError("seed bundle phase must be F34b")
    if bundle.get("status") != (
        "deterministic_air_oil_forward_seed_bundle_zero_solver_cases_executed"
    ):
        raise F34bInputError("seed bundle status mismatch")
    if bundle.get("architecture_id") != EXPECTED_ARCHITECTURE_ID:
        raise F34bInputError("seed bundle architecture identity mismatch")
    if bundle.get("canonical_doe_cases_executed") != 0:
        raise F34bInputError("seed bundle must record zero canonical DOE cases")

    runtime = bundle.get("image_runtime_contract")
    if not isinstance(runtime, dict):
        raise F34bInputError("seed bundle image runtime contract is required")
    for key in (
        "f33_contract_required_in_image",
        "f33_forward_solver_source_required_in_image",
        "f34_generator_source_required_in_image",
        "solver_execution_authorized",
    ):
        if runtime.get(key) is not False:
            raise F34bInputError(f"seed runtime boundary must remain false: {key}")
    if runtime.get("bundle_is_self_contained_for_two_forward_inputs") is not True:
        raise F34bInputError("seed bundle must be self-contained")

    verification = bundle.get("source_verification")
    expected_verification = {
        "f34_contract_validated_against_pinned_parents": True,
        "tracked_manifest_rebuilt_byte_for_byte": True,
        "f34a_air_oil_controls_semantics_validated": True,
        "air_oil_seed_mapping_sha256_matches_manifest": True,
    }
    if verification != expected_verification:
        raise F34bInputError("seed bundle source verification mismatch")

    parents = bundle.get("parents")
    if not isinstance(parents, list) or len(parents) != len(SEED_PARENT_SPECS):
        raise F34bInputError("seed bundle parent set mismatch")
    for parent, (expected_id, expected_path, expected_role) in zip(
        parents, SEED_PARENT_SPECS, strict=True
    ):
        parent = _exact_keys(parent, {"id", "path", "role", "sha256"}, "seed parent")
        if (
            parent.get("id") != expected_id
            or parent.get("path") != expected_path
            or parent.get("role") != expected_role
        ):
            raise F34bInputError(f"seed bundle parent identity mismatch: {expected_id}")
        digest = parent.get("sha256")
        if not isinstance(digest, str) or len(digest) != 64 or any(
            character not in "0123456789abcdef" for character in digest
        ):
            raise F34bInputError(f"seed bundle parent SHA-256 invalid: {expected_id}")

    authority = bundle.get("authority_boundary")
    if not isinstance(authority, dict):
        raise F34bInputError("seed authority boundary is required")
    if authority.get("engine_core_liquid_coolant_present") is not False:
        raise F34bInputError("seed bundle cannot permit engine-core liquid coolant")
    for key in (
        "requested_power_target_present_in_forward_inputs",
        "requested_power_target_used_as_feature",
        "requested_power_target_used_for_calibration",
        "physical_evidence_created",
    ):
        if authority.get(key) is not False:
            raise F34bInputError(f"seed authority gate must remain false: {key}")

    ledger = bundle.get("execution_ledger")
    if not isinstance(ledger, dict):
        raise F34bInputError("seed execution ledger is required")
    if ledger.get("seed_count") != 2 or ledger.get("solver_case_count") != 0:
        raise F34bInputError("seed ledger counts are invalid")
    for key in (
        "solver_executed",
        "calibration_executed",
        "training_executed",
        "physical_test_executed",
    ):
        if ledger.get(key) is not False:
            raise F34bInputError(f"seed execution ledger must remain false: {key}")
    _require_closed_gate_set(
        bundle.get("physical_gates"),
        F34B_SEED_PHYSICAL_GATE_IDS,
        "seed bundle physical_gates",
    )
    _require_closed_gate_set(
        bundle.get("release_gates"),
        F34_RELEASE_GATE_IDS,
        "seed bundle release_gates",
    )

    claimed_hash = bundle.get("bundle_payload_sha256")
    if not isinstance(claimed_hash, str) or len(claimed_hash) != 64 or any(
        character not in "0123456789abcdef" for character in claimed_hash
    ):
        raise F34bInputError("seed bundle payload SHA-256 is invalid")
    payload = copy.deepcopy(bundle)
    payload.pop("bundle_payload_sha256", None)
    if _canonical_sha256(payload) != claimed_hash:
        raise F34bInputError("seed bundle payload SHA-256 mismatch")

    seeds = bundle.get("seeds")
    if not isinstance(seeds, list) or len(seeds) != 2:
        raise F34bInputError("seed bundle must contain exactly two seeds")
    indexed: dict[str, dict[str, Any]] = {}
    expected_seed_keys = {
        "variant_id",
        "configuration",
        "forward_input",
        "forward_input_sha256",
    }
    for item in seeds:
        seed = _exact_keys(item, expected_seed_keys, "seed")
        configuration = seed.get("configuration")
        if configuration not in EXPECTED_CONFIGURATIONS:
            raise F34bInputError(f"unsupported seed configuration: {configuration}")
        if configuration in indexed:
            raise F34bInputError(f"duplicate seed configuration: {configuration}")
        expected = EXPECTED_CONFIGURATIONS[configuration]
        if seed.get("variant_id") != expected["variant_id"]:
            raise F34bInputError(f"seed variant identity mismatch: {configuration}")
        forward = seed.get("forward_input")
        if not isinstance(forward, dict):
            raise F34bInputError(f"seed forward input missing: {configuration}")
        validate_f34_forward_input(forward, configuration)
        if seed.get("forward_input_sha256") != _canonical_sha256(forward):
            raise F34bInputError(f"seed forward input SHA-256 mismatch: {configuration}")
        indexed[configuration] = seed
    if set(indexed) != set(EXPECTED_CONFIGURATIONS):
        raise F34bInputError("seed bundle must provide exactly NA and twin-turbo")
    return indexed


def _validate_architecture_contract(contract: dict[str, Any]) -> None:
    if contract.get("phase") != "F34a":
        raise F34bInputError("architecture contract phase must be F34a")
    decision = contract.get("decision")
    if not isinstance(decision, dict) or decision.get("id") != EXPECTED_ARCHITECTURE_ID:
        raise F34bInputError("F34a decision identity mismatch")
    if decision.get("selected_core_thermal_architecture") != (
        "strict_forced_air_and_dry_sump_oil_only"
    ):
        raise F34bInputError("F34a selected core must be strict forced air and dry-sump oil")
    core = contract.get("engine_core_boundary")
    auxiliary = contract.get("auxiliary_liquid_boundary")
    if not isinstance(core, dict) or not isinstance(auxiliary, dict):
        raise F34bInputError("F34a core and auxiliary boundaries are required")
    if core.get("core_liquid_coolant_loop_present") is not False:
        raise F34bInputError("engine-core liquid loop is forbidden")
    if core.get("core_to_auxiliary_liquid_cross_connection_allowed") is not False:
        raise F34bInputError("core-to-auxiliary liquid cross-connection is forbidden")
    if auxiliary.get("core_cross_connection_allowed") is not False:
        raise F34bInputError("auxiliary liquid cross-connection is forbidden")
    included = core.get("included_components")
    if not isinstance(included, list) or not included:
        raise F34bInputError("F34a core component boundary is missing")
    for component in included:
        if not isinstance(component, dict):
            raise F34bInputError("invalid F34a core component")
        for key in (
            "liquid_coolant_cavity_allowed",
            "liquid_coolant_jacket_allowed",
            "liquid_coolant_passage_geometry_authorized",
        ):
            if component.get(key) is not False:
                raise F34bInputError(f"core component permits liquid cooling: {component.get('id')}")
    _require_closed_gate_set(
        contract.get("technical_gates"),
        F34A_TECHNICAL_GATE_IDS,
        "F34a technical_gates",
    )
    _require_closed_gate_set(
        contract.get("release_gates"),
        F34A_RELEASE_GATE_IDS,
        "F34a release_gates",
    )


def _validate_doe_contract(contract: dict[str, Any]) -> None:
    if contract.get("phase") != "F34":
        raise F34bInputError("DOE contract phase must be F34")
    authority = contract.get("authority_boundary")
    runtime = contract.get("runtime")
    if not isinstance(authority, dict) or not isinstance(runtime, dict):
        raise F34bInputError("F34 authority and runtime boundaries are required")
    if authority.get("engine_core_liquid_coolant_present") is not False:
        raise F34bInputError("F34 DOE cannot permit engine-core liquid coolant")
    for key in ("doe_executed", "surrogate_trained", "physicsnemo_training_authorized"):
        if authority.get(key) is not False:
            raise F34bInputError(f"F34 authority gate must remain false: {key}")
    future = runtime.get("future_solver")
    if not isinstance(future, dict) or future.get("execution_authorized") is not False:
        raise F34bInputError("canonical F34 solver execution must remain unauthorized")
    _require_closed_gate_set(
        contract.get("release_gates"),
        F34_RELEASE_GATE_IDS,
        "F34 release_gates",
    )
    registry = contract.get("variant_registry")
    if not isinstance(registry, list) or len(registry) != 2:
        raise F34bInputError("F34 variant registry must contain exactly two variants")
    for item in registry:
        if not isinstance(item, dict) or item.get("solver_cases_executed") != 0:
            raise F34bInputError("F34 canonical DOE cases must remain unexecuted")


def build_preflight_report(
    doe_contract: dict[str, Any],
    architecture_contract: dict[str, Any],
    seed_bundle: dict[str, Any],
    *,
    doe_path: Path = DOE_CONTRACT,
    architecture_path: Path = ARCHITECTURE_CONTRACT,
    seed_bundle_path: Path = SEED_BUNDLE,
    doe_manifest_path: Path = DOE_MANIFEST,
) -> dict[str, Any]:
    """Validate the runtime contracts and complete F34 seeds without Cantera."""

    _validate_doe_contract(doe_contract)
    _validate_architecture_contract(architecture_contract)
    seeds = _seeds_by_configuration(seed_bundle)
    parents = {parent["path"]: parent for parent in seed_bundle["parents"]}
    runtime_parent_paths = {
        SEED_PARENT_SPECS[0][1]: architecture_path,
        SEED_PARENT_SPECS[1][1]: doe_path,
        SEED_PARENT_SPECS[2][1]: doe_manifest_path,
    }
    for relative_path, runtime_path in runtime_parent_paths.items():
        if parents[relative_path]["sha256"] != _sha256(runtime_path):
            raise F34bInputError(f"embedded seed parent SHA-256 mismatch: {relative_path}")
    validated: list[dict[str, Any]] = []
    for configuration in sorted(seeds):
        seed = seeds[configuration]
        validated.append(
            {
                "configuration": configuration,
                "variant_id": seed["variant_id"],
                "forward_input_sha256": seed["forward_input_sha256"],
                "engine_core_liquid_coolant_present": False,
                "auxiliary_charge_liquid_applicable": configuration == "twin_turbo",
            }
        )
    report = {
        "schema_version": "1.0.0",
        "phase": "F34b",
        "mode": "preflight",
        "status": "source_and_contract_preflight_passed_runtime_dependency_unchecked",
        "canonical_doe_cases_executed": 0,
        "predicted_engine_power": False,
        "validated_1600_hp": False,
        "physical_correlation": False,
        "inputs": {
            "doe_contract": {"path": str(doe_path), "sha256": _sha256(doe_path)},
            "architecture_contract": {
                "path": str(architecture_path),
                "sha256": _sha256(architecture_path),
            },
            "air_oil_seed_bundle": {
                "path": str(seed_bundle_path),
                "sha256": _sha256(seed_bundle_path),
                "payload_sha256_verified": True,
                "legacy_liquid_head_contract_loaded": False,
                "legacy_executable_solver_loaded": False,
            },
            "doe_manifest_hash_binding": {
                "path": str(doe_manifest_path),
                "sha256": _sha256(doe_manifest_path),
                "json_payload_loaded": False,
                "used_for_case_execution": False,
            },
        },
        "validated_f34_air_oil_seed_inputs": validated,
        "execution_boundary": {
            "standard_library_only": True,
            "cantera_import_attempted": False,
            "canonical_doe_manifest_loaded": False,
            "canonical_doe_cases_executed": 0,
            "synthetic_smoke_cases_executed": 0,
            "physicsnemo_executed": False,
            "omniverse_executed": False,
            "vast_used": False,
        },
        "architecture_boundary": {
            "engine_core_heat_rejection": ["forced_air", "dry_sump_oil"],
            "engine_core_liquid_coolant_present": False,
            "engine_core_liquid_cavities_or_jackets_present": False,
            "auxiliary_liquid_isolated_from_core_required": True,
            "auxiliary_liquid_scope_twin_turbo_only": [
                "charge_cooling",
                "turbo_chra_optional_unresolved",
            ],
        },
        "claims": {
            "target_power_proven": False,
            "physical_model_validated": False,
            "cooling_system_validated": False,
            "controls_validated": False,
            "physicsnemo_dataset_authorized": False,
            "manufacturing_authorized": False,
        },
    }
    _require_finite_tree(report)
    return report


def _load_cantera_320() -> Any:
    """Load Cantera only on the explicit synthetic-smoke path."""

    try:
        cantera = importlib.import_module("cantera")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Cantera is unavailable; synthetic-smoke requires the immutable F34b image"
        ) from exc
    if getattr(cantera, "__version__", None) != "3.2.0":
        raise RuntimeError(
            f"Cantera 3.2.0 required for synthetic-smoke, got {getattr(cantera, '__version__', None)}"
        )
    return cantera


def _solve_closed_cycle_cantera(forward: dict[str, Any], cantera: Any) -> dict[str, Any]:
    """Independent F34b four-state smoke backend for an air/oil seed."""

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

    gas = cantera.Solution("nDodecane_Reitz.yaml", "nDodecane_IG")
    gas.TP = (
        float(forward["manifold_temperature_k"]),
        float(forward["manifold_pressure_pa_abs"]),
    )
    gas.set_equivalence_ratio(
        float(forward["equivalence_ratio"]), "c12h26:1", "o2:1,n2:3.76"
    )
    mixture_mass_per_cylinder_kg = (
        gas.density * displacement_per_cylinder_m3 * float(forward["volumetric_efficiency"])
    )
    fuel_mass_fraction = float(gas["c12h26"].Y[0])
    air_mass_fraction = 1.0 - fuel_mass_fraction

    gas.TD = (
        float(forward["manifold_temperature_k"]),
        mixture_mass_per_cylinder_kg / bdc_volume_per_cylinder_m3,
    )
    state_1 = {
        "temperature_k": float(gas.T),
        "pressure_pa_abs": float(gas.P),
        "specific_volume_m3_kg": float(gas.volume_mass),
        "specific_internal_energy_j_kg": float(gas.int_energy_mass),
        "specific_entropy_j_kg_k": float(gas.entropy_mass),
    }
    gas.SV = (
        state_1["specific_entropy_j_kg_k"],
        state_1["specific_volume_m3_kg"] / compression_ratio,
    )
    state_2 = {
        "temperature_k": float(gas.T),
        "pressure_pa_abs": float(gas.P),
        "specific_internal_energy_j_kg": float(gas.int_energy_mass),
    }
    gas.equilibrate("UV")
    state_3 = {
        "temperature_k": float(gas.T),
        "pressure_pa_abs": float(gas.P),
        "specific_internal_energy_j_kg": float(gas.int_energy_mass),
        "specific_entropy_j_kg_k": float(gas.entropy_mass),
    }
    gas.SV = state_3["specific_entropy_j_kg_k"], state_1["specific_volume_m3_kg"]
    state_4 = {
        "temperature_k": float(gas.T),
        "pressure_pa_abs": float(gas.P),
        "specific_internal_energy_j_kg": float(gas.int_energy_mass),
    }

    compression_work_j = mixture_mass_per_cylinder_kg * (
        state_2["specific_internal_energy_j_kg"]
        - state_1["specific_internal_energy_j_kg"]
    )
    expansion_work_j = mixture_mass_per_cylinder_kg * (
        state_3["specific_internal_energy_j_kg"]
        - state_4["specific_internal_energy_j_kg"]
    )
    gross_work_j = expansion_work_j - compression_work_j
    gross_power_w = gross_work_j * cycles_per_second * cylinder_count
    retained_power_w = gross_power_w * float(forward["indicated_work_retention"])
    fmep = forward["fmep_model"]
    fmep_bar = (
        float(fmep["base_bar"])
        + float(fmep["mean_piston_speed_linear_bar_per_m_s"]) * mean_piston_speed_m_s
        + float(fmep["mean_piston_speed_quadratic_bar_per_m_s2"])
        * mean_piston_speed_m_s**2
    )
    friction_power_w = fmep_bar * 100000.0 * displacement_m3 * cycles_per_second
    pumping_power_w = (
        float(forward["exhaust_pressure_pa_abs"]) - state_1["pressure_pa_abs"]
    ) * displacement_m3 * cycles_per_second
    accessory_power_w = float(forward["accessory_power_w"])
    brake_power_w = retained_power_w - friction_power_w - pumping_power_w - accessory_power_w
    if brake_power_w <= 0.0:
        raise RuntimeError("synthetic forward brake power is not positive")

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
    return {
        "geometry": {
            "displacement_m3": displacement_m3,
            "mean_piston_speed_m_s": mean_piston_speed_m_s,
            "cycles_per_second": cycles_per_second,
        },
        "states": {"ivc": state_1, "compression_end": state_2, "equilibrium_end": state_3, "expansion_end": state_4},
        "charge": {
            "mixture_mass_per_cylinder_kg": mixture_mass_per_cylinder_kg,
            "air_mass_flow_kg_s": air_mass_flow_kg_s,
            "fuel_mass_flow_kg_s": fuel_mass_flow_kg_s,
            "exhaust_mass_flow_kg_s": exhaust_mass_flow_kg_s,
        },
        "power": {
            "compression_work_per_cylinder_j": compression_work_j,
            "expansion_work_per_cylinder_j": expansion_work_j,
            "gross_work_per_cylinder_j": gross_work_j,
            "gross_indicated_power_w": gross_power_w,
            "retained_indicated_power_w": retained_power_w,
            "friction_power_w": friction_power_w,
            "pumping_power_w": pumping_power_w,
            "accessory_power_w": accessory_power_w,
            "brake_power_w": brake_power_w,
            "fuel_power_w": fuel_power_w,
        },
    }


def _solve_turbo_screen(
    forward: dict[str, Any], air_mass_flow_kg_s: float, exhaust_mass_flow_kg_s: float
) -> dict[str, Any] | None:
    if int(forward["turbocharger_count"]) == 0:
        return None
    turbo = forward["turbo_screening_input"]
    turbo_count = int(forward["turbocharger_count"])
    p1 = float(turbo["compressor_inlet_pressure_pa_abs"])
    t1 = float(turbo["compressor_inlet_temperature_k"])
    p2 = float(forward["manifold_pressure_pa_abs"]) + float(turbo["charge_path_loss_pa"])
    pressure_ratio = p2 / p1
    if pressure_ratio <= 1.0:
        raise RuntimeError("synthetic turbo compressor pressure ratio must exceed one")
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
    if charge_heat_total <= 0.0:
        raise RuntimeError("synthetic charge-cooler load must be positive")
    corrected_flow = per_turbo_air * math.sqrt(
        t1 / float(turbo["corrected_flow_reference_temperature_k"])
    ) / (p1 / float(turbo["corrected_flow_reference_pressure_pa_abs"]))
    per_turbo_exhaust = exhaust_mass_flow_kg_s / turbo_count
    turbine_inlet_pressure = float(forward["exhaust_pressure_pa_abs"])
    turbine_outlet_pressure = float(turbo["turbine_outlet_pressure_pa_abs"])
    turbine_gamma = float(turbo["exhaust_gas_gamma"])
    expansion_term = 1.0 - (turbine_outlet_pressure / turbine_inlet_pressure) ** (
        (turbine_gamma - 1.0) / turbine_gamma
    )
    turbine_power_full_flow = (
        per_turbo_exhaust
        * float(turbo["exhaust_gas_cp_j_kg_k"])
        * float(turbo["turbine_inlet_temperature_k"])
        * float(turbo["turbine_isentropic_efficiency"])
        * expansion_term
        * float(turbo["turbo_mechanical_efficiency"])
    )
    if turbine_power_full_flow <= 0.0:
        raise RuntimeError("synthetic turbine full-flow power must be positive")
    required_flow_fraction = compressor_power_per_turbo / turbine_power_full_flow
    return {
        "candidate_model": turbo["candidate_model"],
        "compressor_pressure_ratio": _round(pressure_ratio),
        "compressor_outlet_temperature_k": _round(t2),
        "compressor_power_per_turbo_w": _round(compressor_power_per_turbo),
        "compressor_power_total_w": _round(compressor_power_per_turbo * turbo_count),
        "charge_cooler_heat_rejection_w": _round(charge_heat_total),
        "air_mass_flow_per_turbo_kg_s": _round(per_turbo_air),
        "corrected_air_mass_flow_per_turbo_kg_s": _round(corrected_flow),
        "exhaust_mass_flow_per_turbo_kg_s": _round(per_turbo_exhaust),
        "turbine_pressure_ratio": _round(turbine_inlet_pressure / turbine_outlet_pressure),
        "turbine_power_full_flow_per_turbo_w": _round(turbine_power_full_flow),
        "required_turbine_flow_fraction_inverse_screen": _round(required_flow_fraction),
        "required_wastegate_fraction_inverse_screen": _round(1.0 - required_flow_fraction),
        "within_algebraic_full_flow_capacity": 0.0 < required_flow_fraction <= 1.0,
        "compressor_map_digitized": False,
        "turbine_map_digitized": False,
        "map_interpolation_executed": False,
        "shaft_balance_forward_closed": False,
        "turbo_match_validated": False,
        "classification": "algebraic_smoke_only_not_turbo_map_match",
    }


def _near_zero(value: float, scale: float, label: str) -> None:
    tolerance = max(1.0e-9, abs(scale) * 1.0e-12)
    if not math.isfinite(value) or abs(value) > tolerance:
        raise RuntimeError(f"numerical identity failed: {label} residual={value}")


def _build_air_oil_thermal_network(
    forward: dict[str, Any],
    *,
    fuel_power_w: float,
    friction_power_w: float,
    brake_power_w: float,
    charge_heat_w: float | None,
    configuration: str,
) -> dict[str, Any]:
    """Build the selected air/oil split and explicit algebraic identities."""

    thermal = forward["thermal_hypotheses"]
    head_total_w = fuel_power_w * float(thermal["head_heat_fraction_of_fuel_power"])
    head_to_oil_w = head_total_w * float(thermal["head_heat_to_oil_fraction"])
    head_to_air_w = head_total_w - head_to_oil_w
    cylinder_to_air_w = fuel_power_w * float(
        thermal["cylinder_heat_fraction_of_fuel_power"]
    )
    base_oil_w = fuel_power_w * float(
        thermal["base_oil_heat_fraction_of_fuel_power"]
    )
    friction_to_oil_w = friction_power_w * float(thermal["friction_to_oil_fraction"])
    core_air_w = head_to_air_w + cylinder_to_air_w
    oil_loop_w = base_oil_w + friction_to_oil_w + head_to_oil_w
    cooling_air_flow = core_air_w / (
        float(thermal["cooling_air_cp_j_kg_k"])
        * float(thermal["cooling_air_delta_t_k"])
    )
    oil_flow = oil_loop_w / (
        float(thermal["oil_cp_j_kg_k"]) * float(thermal["oil_delta_t_k"])
    )

    head_split_residual = head_total_w - head_to_air_w - head_to_oil_w
    core_air_residual = core_air_w - head_to_air_w - cylinder_to_air_w
    oil_residual = oil_loop_w - base_oil_w - friction_to_oil_w - head_to_oil_w
    cooling_flow_residual = core_air_w - cooling_air_flow * float(
        thermal["cooling_air_cp_j_kg_k"]
    ) * float(thermal["cooling_air_delta_t_k"])
    oil_flow_residual = oil_loop_w - oil_flow * float(thermal["oil_cp_j_kg_k"]) * float(
        thermal["oil_delta_t_k"]
    )
    for label, residual, scale in (
        ("head_split", head_split_residual, head_total_w),
        ("core_air_split", core_air_residual, core_air_w),
        ("oil_loop_split", oil_residual, oil_loop_w),
        ("cooling_air_flow", cooling_flow_residual, core_air_w),
        ("oil_flow", oil_flow_residual, oil_loop_w),
    ):
        _near_zero(residual, scale, label)

    unallocated_w = fuel_power_w - brake_power_w - core_air_w - oil_loop_w
    if unallocated_w < 0.0:
        raise RuntimeError("fuel-energy allocation leaves a negative unmodelled remainder")
    fuel_identity_residual = (
        fuel_power_w - brake_power_w - core_air_w - oil_loop_w - unallocated_w
    )
    _near_zero(fuel_identity_residual, fuel_power_w, "fuel_energy_allocation")

    loads = {
        "head_total": _round(head_total_w),
        "head_to_air": _round(head_to_air_w),
        "head_to_oil": _round(head_to_oil_w),
        "cylinder_fin_air": _round(cylinder_to_air_w),
        "engine_core_air": _round(core_air_w),
        "oil_base_fuel_fraction": _round(base_oil_w),
        "friction_to_oil": _round(friction_to_oil_w),
        "oil_loop": _round(oil_loop_w),
    }
    flows = {"cooling_air": _round(cooling_air_flow), "oil": _round(oil_flow)}
    auxiliary_balance: dict[str, Any] | None = None
    if configuration == "twin_turbo":
        if charge_heat_w is None or charge_heat_w <= 0.0:
            raise RuntimeError("twin-turbo synthetic smoke requires a positive LT charge load")
        charge_flow = charge_heat_w / (
            float(thermal["charge_coolant_cp_j_kg_k"])
            * float(thermal["charge_coolant_delta_t_k"])
        )
        charge_residual = charge_heat_w - charge_flow * float(
            thermal["charge_coolant_cp_j_kg_k"]
        ) * float(thermal["charge_coolant_delta_t_k"])
        _near_zero(charge_residual, charge_heat_w, "auxiliary_charge_flow")
        loads["charge_lt_coolant"] = _round(charge_heat_w)
        flows["charge_coolant"] = _round(charge_flow)
        auxiliary_balance = {
            "charge_lt_flow_identity_residual_w": _round(charge_residual),
            "hydraulically_isolated_from_engine_core_assumed_not_validated": True,
        }
    elif charge_heat_w is not None:
        raise RuntimeError("naturally aspirated synthetic smoke forbids an LT charge load")

    result = {
        "engine_core_liquid_coolant_present": False,
        "engine_core_liquid_cavities_or_jackets_present": False,
        "loads_w": loads,
        "required_mass_flows_kg_s": flows,
        "algebraic_balances": {
            "head_split_residual_w": _round(head_split_residual),
            "core_air_split_residual_w": _round(core_air_residual),
            "oil_loop_split_residual_w": _round(oil_residual),
            "cooling_air_flow_identity_residual_w": _round(cooling_flow_residual),
            "oil_flow_identity_residual_w": _round(oil_flow_residual),
            "fuel_energy_allocation_residual_w": _round(fuel_identity_residual),
            "unmodelled_exhaust_pumping_accessory_and_other_w": _round(unallocated_w),
            "auxiliary_charge": auxiliary_balance,
            "numerically_closed": True,
            "physical_energy_balance_validated": False,
        },
        "flow_values_are_hypothetical_cp_delta_t_requirements": True,
        "fan_or_pump_map_solution_executed": False,
        "hydraulic_solution_executed": False,
        "heat_exchanger_ua_solution_executed": False,
        "cfd_or_cht_executed": False,
        "thermal_system_validated": False,
    }
    _require_finite_tree(result)
    return result


def solve_f34_forward(
    forward: dict[str, Any], configuration: str, *, cantera_module: Any
) -> dict[str, Any]:
    """Evaluate one explicitly supplied F34 input as a synthetic smoke screen."""

    validate_f34_forward_input(forward, configuration)
    if getattr(cantera_module, "__version__", None) != "3.2.0":
        raise RuntimeError("solve_f34_forward requires Cantera 3.2.0")
    cycle = _solve_closed_cycle_cantera(copy.deepcopy(forward), cantera_module)
    charge = cycle["charge"]
    power = cycle["power"]
    turbo = _solve_turbo_screen(
        forward,
        float(charge["air_mass_flow_kg_s"]),
        float(charge["exhaust_mass_flow_kg_s"]),
    )
    thermal = _build_air_oil_thermal_network(
        forward,
        fuel_power_w=float(power["fuel_power_w"]),
        friction_power_w=float(power["friction_power_w"]),
        brake_power_w=float(power["brake_power_w"]),
        charge_heat_w=(
            float(turbo["charge_cooler_heat_rejection_w"]) if turbo is not None else None
        ),
        configuration=configuration,
    )
    mass_residual = (
        float(charge["exhaust_mass_flow_kg_s"])
        - float(charge["air_mass_flow_kg_s"])
        - float(charge["fuel_mass_flow_kg_s"])
    )
    _near_zero(mass_residual, float(charge["exhaust_mass_flow_kg_s"]), "mass")
    gross_work_residual = (
        float(power["gross_work_per_cylinder_j"])
        - float(power["expansion_work_per_cylinder_j"])
        + float(power["compression_work_per_cylinder_j"])
    )
    brake_identity_residual = (
        float(power["brake_power_w"])
        - float(power["retained_indicated_power_w"])
        + float(power["friction_power_w"])
        + float(power["pumping_power_w"])
        + float(power["accessory_power_w"])
    )
    _near_zero(gross_work_residual, float(power["gross_work_per_cylinder_j"]), "gross_work")
    _near_zero(brake_identity_residual, float(power["brake_power_w"]), "brake_power")

    brake_power_w = float(power["brake_power_w"])
    fuel_power_w = float(power["fuel_power_w"])
    speed_rpm = float(forward["speed_rpm"])
    displacement_m3 = float(cycle["geometry"]["displacement_m3"])
    cycles_per_second = float(cycle["geometry"]["cycles_per_second"])
    result = {
        "classification": "non_correlated_f34b_synthetic_four_state_air_oil_screen",
        "configuration": configuration,
        "target_used_as_solver_input": False,
        "geometry_and_speed": {
            "displacement_l": _round(displacement_m3 * 1000.0),
            "speed_rpm": _round(speed_rpm),
            "mean_piston_speed_m_s": _round(cycle["geometry"]["mean_piston_speed_m_s"]),
            "compression_ratio": _round(forward["compression_ratio"]),
        },
        "trapped_charge": {
            "effective_ivc_pressure_pa_abs": _round(cycle["states"]["ivc"]["pressure_pa_abs"]),
            "mixture_mass_per_cylinder_kg": _round(charge["mixture_mass_per_cylinder_kg"]),
            "air_mass_flow_kg_s": _round(charge["air_mass_flow_kg_s"]),
            "fuel_mass_flow_kg_s": _round(charge["fuel_mass_flow_kg_s"]),
            "exhaust_mass_flow_identity_kg_s": _round(charge["exhaust_mass_flow_kg_s"]),
            "mass_identity_residual_kg_s": _round(mass_residual),
            "numerical_mass_identity_closed": True,
            "physical_mass_balance_validated": False,
        },
        "idealized_states": {
            name: {
                "temperature_k": _round(state["temperature_k"]),
                "pressure_pa_abs": _round(state["pressure_pa_abs"]),
            }
            for name, state in cycle["states"].items()
        },
        "work_and_power": {
            "gross_indicated_power_w": _round(power["gross_indicated_power_w"]),
            "retained_indicated_power_w": _round(power["retained_indicated_power_w"]),
            "friction_power_w": _round(power["friction_power_w"]),
            "pumping_power_w": _round(power["pumping_power_w"]),
            "accessory_power_w": _round(power["accessory_power_w"]),
            "synthetic_brake_power_w": _round(brake_power_w),
            "synthetic_mechanical_hp": _round(brake_power_w / MECHANICAL_HP_W),
            "synthetic_metric_ps": _round(brake_power_w / METRIC_PS_W),
            "synthetic_torque_nm": _round(brake_power_w * 60.0 / (2.0 * math.pi * speed_rpm)),
            "synthetic_bmep_bar": _round(
                brake_power_w / (displacement_m3 * cycles_per_second) / 100000.0
            ),
            "synthetic_brake_thermal_efficiency": _round(brake_power_w / fuel_power_w),
            "synthetic_bsfc_g_kwh": _round(
                float(charge["fuel_mass_flow_kg_s"]) * 3.6e9 / brake_power_w
            ),
            "fuel_power_w": _round(fuel_power_w),
            "gross_work_identity_residual_j": _round(gross_work_residual),
            "brake_power_identity_residual_w": _round(brake_identity_residual),
            "numerical_work_identities_closed": True,
            "physical_power_validated": False,
        },
        "turbo_screen": turbo,
        "thermal_network_screen": thermal,
        "numerical_scope": {
            "cantera_equilibrium_uv_executed": True,
            "closed_cycle_four_state_only": True,
            "canonical_doe_case": False,
            "crank_angle_time_marching_executed": False,
            "one_dimensional_gas_dynamics_executed": False,
            "turbo_map_interpolation_executed": False,
            "cfd_or_cht_executed": False,
            "physicsnemo_executed": False,
            "omniverse_executed": False,
            "physical_correlation_complete": False,
        },
        "claims": {
            "target_power_proven": False,
            "1600_mechanical_hp_proven": False,
            "cooling_system_validated": False,
            "engine_operation_authorized": False,
            "manufacturing_authorized": False,
        },
    }
    _require_finite_tree(result)
    return result


def _canonical_case_hashes(
    manifest: dict[str, Any], *, doe_contract_sha256: str
) -> set[str]:
    """Validate the zero-execution manifest and return all canonical hashes."""

    if not isinstance(manifest, dict):
        raise F34bInputError("DOE manifest must be an object")
    if manifest.get("phase") != "F34":
        raise F34bInputError("DOE manifest phase must be F34")
    if manifest.get("contract_file_sha256") != doe_contract_sha256:
        raise F34bInputError("DOE manifest contract SHA-256 mismatch")
    _require_closed_gate_set(
        manifest.get("release_gates"),
        F34_RELEASE_GATE_IDS,
        "DOE manifest release_gates",
    )
    counts = manifest.get("case_counts")
    ledger = manifest.get("execution_ledger")
    cases = manifest.get("cases")
    if not isinstance(counts, dict) or not isinstance(ledger, dict):
        raise F34bInputError("DOE manifest counts and ledger are required")
    if not isinstance(cases, list) or not cases:
        raise F34bInputError("DOE manifest cases are required")
    if counts.get("planned") != len(cases):
        raise F34bInputError("DOE manifest planned count mismatch")
    for key in ("executed", "accepted", "rejected"):
        if counts.get(key) != 0 or ledger.get(key) != 0:
            raise F34bInputError(f"DOE manifest result count must remain zero: {key}")
    if ledger.get("planned_not_executed") != len(cases):
        raise F34bInputError("DOE manifest unexecuted ledger count mismatch")
    hashes: set[str] = set()
    for case in cases:
        if not isinstance(case, dict):
            raise F34bInputError("invalid DOE manifest case")
        if (
            case.get("execution_status") != "planned_not_executed"
            or case.get("training_eligible") is not False
        ):
            raise F34bInputError("DOE manifest contains an executed or eligible case")
        digest = case.get("forward_input_sha256")
        if not isinstance(digest, str) or len(digest) != 64 or any(
            character not in "0123456789abcdef" for character in digest
        ):
            raise F34bInputError("DOE manifest contains an invalid forward input hash")
        if digest in hashes:
            raise F34bInputError("DOE manifest contains duplicate forward input hashes")
        hashes.add(digest)
    return hashes


def _build_noncanonical_synthetic_fixture(
    seed: dict[str, Any], configuration: str, canonical_hashes: set[str]
) -> tuple[dict[str, Any], str, bool]:
    """Derive a finite smoke fixture and prove it is not a canonical DOE case."""

    source_hash = seed["forward_input_sha256"]
    source_seed_is_canonical = source_hash in canonical_hashes
    fixture = copy.deepcopy(seed["forward_input"])
    # A material, versioned speed displacement prevents this regression smoke
    # from masquerading as execution of a source anchor. Membership is checked
    # against every canonical case hash before any solver is invoked.
    original_speed = float(fixture["speed_rpm"])
    fixture["speed_rpm"] = SYNTHETIC_FIXTURE_SPEED_RPM[configuration]
    if abs(fixture["speed_rpm"] - original_speed) < 100.0:
        raise RuntimeError("failed to derive a distinct synthetic fixture")
    validate_f34_forward_input(fixture, configuration)
    fixture_hash = _canonical_sha256(fixture)
    if fixture_hash == source_hash or fixture_hash in canonical_hashes:
        raise F34bInputError(
            f"synthetic fixture collides with a canonical DOE case: {configuration}"
        )
    return fixture, fixture_hash, source_seed_is_canonical


def build_synthetic_smoke_report(
    doe_contract: dict[str, Any],
    architecture_contract: dict[str, Any],
    seed_bundle: dict[str, Any],
    doe_manifest: dict[str, Any],
    *,
    cantera_module: Any | None = None,
    doe_path: Path = DOE_CONTRACT,
    architecture_path: Path = ARCHITECTURE_CONTRACT,
    seed_bundle_path: Path = SEED_BUNDLE,
    doe_manifest_path: Path = DOE_MANIFEST,
) -> dict[str, Any]:
    """Evaluate two derived fixtures proven absent from the canonical DOE."""

    preflight = build_preflight_report(
        doe_contract,
        architecture_contract,
        seed_bundle,
        doe_path=doe_path,
        architecture_path=architecture_path,
        seed_bundle_path=seed_bundle_path,
        doe_manifest_path=doe_manifest_path,
    )
    seeds = _seeds_by_configuration(seed_bundle)
    canonical_hashes = _canonical_case_hashes(
        doe_manifest, doe_contract_sha256=_sha256(doe_path)
    )
    fixtures: list[tuple[str, dict[str, Any], dict[str, Any], str, bool]] = []
    for configuration in sorted(seeds):
        seed = seeds[configuration]
        fixture, fixture_hash, source_is_canonical = _build_noncanonical_synthetic_fixture(
            seed, configuration, canonical_hashes
        )
        fixtures.append(
            (configuration, seed, fixture, fixture_hash, source_is_canonical)
        )

    # The dependency is deliberately loaded only after all fixtures have been
    # proven distinct from all canonical DOE cases.
    cantera = cantera_module if cantera_module is not None else _load_cantera_320()
    if getattr(cantera, "__version__", None) != "3.2.0":
        raise RuntimeError("synthetic-smoke requires Cantera 3.2.0")
    predictions: list[dict[str, Any]] = []
    for configuration, seed, fixture, fixture_hash, source_is_canonical in fixtures:
        predictions.append(
            {
                "variant_id": seed["variant_id"],
                "configuration": configuration,
                "source_seed_forward_input_sha256": seed["forward_input_sha256"],
                "source_seed_is_canonical_doe_case": source_is_canonical,
                "source_seed_speed_rpm": seed["forward_input"]["speed_rpm"],
                "synthetic_fixture_speed_rpm": fixture["speed_rpm"],
                "synthetic_fixture_speed_delta_rpm": (
                    fixture["speed_rpm"] - seed["forward_input"]["speed_rpm"]
                ),
                "synthetic_fixture_forward_input_sha256": fixture_hash,
                "synthetic_fixture_absent_from_all_canonical_cases": True,
                "synthetic_prediction": solve_f34_forward(
                    fixture, configuration, cantera_module=cantera
                ),
            }
        )
    report = {
        "schema_version": "1.0.0",
        "phase": "F34b",
        "mode": "synthetic-smoke",
        "status": "two_noncanonical_fixture_smokes_complete_all_physical_gates_blocked",
        "canonical_doe_cases_executed": 0,
        "synthetic_numerical_power_screen_executed": True,
        "authoritative_engine_power_prediction_available": False,
        "validated_1600_hp": False,
        "physical_correlation": False,
        "preflight_sha256": _canonical_sha256(preflight),
        "doe_manifest_exclusion_check": {
            "path": str(doe_manifest_path),
            "sha256": _sha256(doe_manifest_path),
            "canonical_case_hash_count": len(canonical_hashes),
            "manifest_loaded_for_hash_exclusion_only": True,
            "canonical_forward_solver_inputs_reconstructed_or_executed": False,
        },
        "runtime": {
            "cantera_version": cantera.__version__,
            "cantera_loaded_only_after_preflight": True,
            "legacy_liquid_head_contract_loaded": False,
            "legacy_executable_solver_loaded": False,
        },
        "execution_boundary": {
            "canonical_doe_manifest_loaded_for_hash_exclusion_only": True,
            "canonical_doe_cases_executed": 0,
            "synthetic_noncanonical_fixture_cases_executed": len(predictions),
            "source_seed_cases_executed": 0,
            "all_fixture_hashes_absent_from_canonical_manifest": True,
            "physicsnemo_executed": False,
            "omniverse_executed": False,
            "vast_used": False,
        },
        "synthetic_predictions": predictions,
        "claims": {
            "authoritative_engine_power_prediction_available": False,
            "target_power_proven": False,
            "1600_mechanical_hp_proven": False,
            "mass_balance_physically_validated": False,
            "energy_balance_physically_validated": False,
            "air_cooling_validated": False,
            "oil_system_validated": False,
            "turbo_match_validated": False,
            "physicsnemo_model_trained_or_evaluated": False,
            "engine_start_authorized": False,
            "manufacturing_authorized": False,
        },
    }
    _require_finite_tree(report)
    return report


def _write_report(report: dict[str, Any], output: Path | None) -> None:
    payload = json.dumps(
        report,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
    ) + "\n"
    if output is None:
        sys.stdout.write(payload)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(payload, encoding="utf-8")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="F34b air/oil CPU preflight or explicit noncanonical fixture smoke"
    )
    parser.add_argument("mode", choices=("preflight", "synthetic-smoke"))
    parser.add_argument("--doe-contract", type=Path, default=DOE_CONTRACT)
    parser.add_argument(
        "--architecture-contract", type=Path, default=ARCHITECTURE_CONTRACT
    )
    parser.add_argument("--seed-bundle", type=Path, default=SEED_BUNDLE)
    parser.add_argument("--doe-manifest", type=Path, default=DOE_MANIFEST)
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        doe_contract = _read_json(args.doe_contract)
        architecture_contract = _read_json(args.architecture_contract)
        seed_bundle = _read_json(args.seed_bundle)
        if args.mode == "preflight":
            report = build_preflight_report(
                doe_contract,
                architecture_contract,
                seed_bundle,
                doe_path=args.doe_contract,
                architecture_path=args.architecture_contract,
                seed_bundle_path=args.seed_bundle,
                doe_manifest_path=args.doe_manifest,
            )
        else:
            doe_manifest = _read_json(args.doe_manifest)
            report = build_synthetic_smoke_report(
                doe_contract,
                architecture_contract,
                seed_bundle,
                doe_manifest,
                doe_path=args.doe_contract,
                architecture_path=args.architecture_contract,
                seed_bundle_path=args.seed_bundle,
                doe_manifest_path=args.doe_manifest,
            )
        _write_report(report, args.output)
        return 0
    except (F34bInputError, RuntimeError, ValueError, OSError) as exc:
        print(f"F34b air/oil error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
