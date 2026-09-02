#!/usr/bin/env python3
"""Valide et matérialise le plan DOE F34 sans lancer de solveur.

Le manifeste produit contient des entrées forward déterministes et des splits
préassignés. Il ne contient aucun résultat Cantera, label, poids ML ou preuve
physique. La cible de puissance est volontairement absente de la génération.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "twins/reference-917-engine/doe-surrogate-f34.json"
F33_CONTRACT = ROOT / "twins/reference-917-engine/clean-sheet-cycle-thermal-f33.json"
TRACKED_MANIFEST = (
    ROOT / "twins/reference-917-engine/evidence/f34/doe-case-manifest.json"
)

EXPECTED_PARENT_HASHES = {
    "twins/reference-917-engine/air-oil-core-controls-f34a.json":
        "a1e4c7626fccf634856df4f167edfa0f1ad2a32337e4ff9e2386a6abf930c8fa",
    "twins/reference-917-engine/clean-sheet-cycle-thermal-f33.json":
        "6bbd5a5373660641c50e85dce6b45ac23222751d77f9f86783d82bd72530e73b",
    "twins/reference-917-engine/evidence/f33/cycle-thermal-report.json":
        "b12ba3dc54b66e1a5a6c695eee0d9fe3e4093508ebc999133284e32a0edc10ed",
    "twins/reference-917-engine/evidence/f33/engine-cycle-image-publication.json":
        "fa267c15d8a14214f45d27bde21de02cd4f94e71d2f98ed74388ec3af0866229",
    "scripts/run_917_cycle_thermal_f33.py":
        "82300e61084414cda920fe6c90d05014b192b749b0f2ce96f092fc4cb1018f15",
}
EXPECTED_PARENT_IDENTITIES = {
    "twins/reference-917-engine/air-oil-core-controls-f34a.json": (
        "f34a_air_oil_core_controls_decision",
        "selected_air_oil_core_and_modern_controls_authority",
    ),
    "twins/reference-917-engine/clean-sheet-cycle-thermal-f33.json": (
        "f33_cycle_contract",
        "parameter_centers_topology_and_fail_closed_authority",
    ),
    "twins/reference-917-engine/evidence/f33/cycle-thermal-report.json": (
        "f33_cycle_report",
        "single_point_0d_reference_output_not_physical_truth",
    ),
    "twins/reference-917-engine/evidence/f33/engine-cycle-image-publication.json": (
        "f33_image_publication",
        "immutable_linux_amd64_runtime_evidence",
    ),
    "scripts/run_917_cycle_thermal_f33.py": (
        "f33_forward_runner",
        "target_independent_reference_solver_source",
    ),
}
EXPECTED_VARIANTS = {
    "naturally_aspirated": {
        "id": "917_2026_flat12_na_candidate",
        "short_id": "NA",
        "axis_count": 17,
        "morris_count": 216,
        "lhs_count": 512,
        "ood_count": 128,
    },
    "twin_turbo": {
        "id": "917_2026_flat12_twin_turbo_1600hp_target",
        "short_id": "TT",
        "axis_count": 26,
        "morris_count": 432,
        "lhs_count": 1024,
        "ood_count": 256,
    },
}
EXPECTED_AXIS_UNITS = {
    "compression_ratio": "ratio",
    "speed_rpm": "rpm",
    "manifold_pressure_pa_abs": "Pa_abs",
    "manifold_temperature_k": "K",
    "volumetric_efficiency": "ratio",
    "equivalence_ratio": "ratio",
    "exhaust_to_manifold_pressure_ratio": "ratio",
    "indicated_work_retention": "ratio",
    "fmep_coefficient_scale": "ratio",
    "accessory_power_w": "W",
    "head_heat_fraction_of_fuel_power": "ratio",
    "cylinder_heat_fraction_of_fuel_power": "ratio",
    "base_oil_heat_fraction_of_fuel_power": "ratio",
    "friction_to_oil_fraction": "ratio",
    "head_heat_to_oil_fraction": "ratio",
    "cooling_air_delta_t_k": "K",
    "oil_delta_t_k": "K",
    "compressor_inlet_pressure_pa_abs": "Pa_abs",
    "compressor_inlet_temperature_k": "K",
    "charge_path_loss_pa": "Pa",
    "compressor_isentropic_efficiency": "ratio",
    "turbine_inlet_temperature_k": "K",
    "turbine_outlet_pressure_pa_abs": "Pa_abs",
    "turbine_isentropic_efficiency": "ratio",
    "turbo_mechanical_efficiency": "ratio",
    "charge_coolant_delta_t_k": "K",
}
EXPECTED_AXIS_ORDER = list(EXPECTED_AXIS_UNITS)
EXPECTED_AXIS_PATHS = {
    "compression_ratio": "compression_ratio",
    "speed_rpm": "speed_rpm",
    "manifold_pressure_pa_abs": "manifold_pressure_pa_abs",
    "manifold_temperature_k": "manifold_temperature_k",
    "volumetric_efficiency": "volumetric_efficiency",
    "equivalence_ratio": "equivalence_ratio",
    "exhaust_to_manifold_pressure_ratio": "exhaust_pressure_pa_abs",
    "indicated_work_retention": "indicated_work_retention",
    "fmep_coefficient_scale": "fmep_model",
    "accessory_power_w": "accessory_power_w",
    "head_heat_fraction_of_fuel_power": "thermal_hypotheses.head_heat_fraction_of_fuel_power",
    "cylinder_heat_fraction_of_fuel_power": "thermal_hypotheses.cylinder_heat_fraction_of_fuel_power",
    "base_oil_heat_fraction_of_fuel_power": "thermal_hypotheses.base_oil_heat_fraction_of_fuel_power",
    "friction_to_oil_fraction": "thermal_hypotheses.friction_to_oil_fraction",
    "head_heat_to_oil_fraction": "thermal_hypotheses.head_heat_to_oil_fraction",
    "cooling_air_delta_t_k": "thermal_hypotheses.cooling_air_delta_t_k",
    "oil_delta_t_k": "thermal_hypotheses.oil_delta_t_k",
    "compressor_inlet_pressure_pa_abs": "turbo_screening_input.compressor_inlet_pressure_pa_abs",
    "compressor_inlet_temperature_k": "turbo_screening_input.compressor_inlet_temperature_k",
    "charge_path_loss_pa": "turbo_screening_input.charge_path_loss_pa",
    "compressor_isentropic_efficiency": "turbo_screening_input.compressor_isentropic_efficiency",
    "turbine_inlet_temperature_k": "turbo_screening_input.turbine_inlet_temperature_k",
    "turbine_outlet_pressure_pa_abs": "turbo_screening_input.turbine_outlet_pressure_pa_abs",
    "turbine_isentropic_efficiency": "turbo_screening_input.turbine_isentropic_efficiency",
    "turbo_mechanical_efficiency": "turbo_screening_input.turbo_mechanical_efficiency",
    "charge_coolant_delta_t_k": "thermal_hypotheses.charge_coolant_delta_t_k",
}
EXPECTED_AXIS_TRANSFORMS = {
    "exhaust_to_manifold_pressure_ratio": "multiply_by_axis:manifold_pressure_pa_abs",
    "fmep_coefficient_scale": "multiply_f33_center_coefficients",
}
EXPECTED_COMMON_AXES = set(EXPECTED_AXIS_ORDER[:17])
EXPECTED_TURBO_AXES = set(EXPECTED_AXIS_ORDER[17:])
EXPECTED_CONSTRAINTS = {
    "C-TARGET-INDEPENDENCE",
    "C-VARIANT-SEPARATION",
    "C-THERMAL-FRACTIONS",
    "C-MEAN-PISTON-SPEED",
    "C-MASS-IDENTITY",
    "C-TURBO-PRESSURE-RATIO",
    "C-TURBINE-EXPANSION",
    "C-POSITIVE-FORWARD-POWER",
}
EXPECTED_LABELS = {
    "forward_predicted_brake_power_w": ("work_and_power.forward_predicted_brake_power_w", "W", {"naturally_aspirated", "twin_turbo"}),
    "forward_predicted_mechanical_hp": ("work_and_power.forward_predicted_mechanical_hp", "mechanical_hp", {"naturally_aspirated", "twin_turbo"}),
    "forward_predicted_torque_nm": ("work_and_power.forward_predicted_torque_nm", "N*m", {"naturally_aspirated", "twin_turbo"}),
    "forward_predicted_bmep_bar": ("work_and_power.forward_predicted_bmep_bar", "bar", {"naturally_aspirated", "twin_turbo"}),
    "brake_thermal_efficiency": ("work_and_power.brake_thermal_efficiency", "ratio", {"naturally_aspirated", "twin_turbo"}),
    "bsfc_g_kwh": ("work_and_power.bsfc_g_kwh", "g/kWh", {"naturally_aspirated", "twin_turbo"}),
    "air_mass_flow_kg_s": ("trapped_charge.air_mass_flow_kg_s", "kg/s", {"naturally_aspirated", "twin_turbo"}),
    "fuel_mass_flow_kg_s": ("trapped_charge.fuel_mass_flow_kg_s", "kg/s", {"naturally_aspirated", "twin_turbo"}),
    "head_total_heat_load_w": ("thermal_network_screen.loads_w.head_total", "W", {"naturally_aspirated", "twin_turbo"}),
    "head_to_air_load_w": ("thermal_network_screen.loads_w.head_to_air", "W", {"naturally_aspirated", "twin_turbo"}),
    "head_to_oil_load_w": ("thermal_network_screen.loads_w.head_to_oil", "W", {"naturally_aspirated", "twin_turbo"}),
    "cylinder_fin_air_load_w": ("thermal_network_screen.loads_w.cylinder_fin_air", "W", {"naturally_aspirated", "twin_turbo"}),
    "engine_core_air_load_w": ("thermal_network_screen.loads_w.engine_core_air", "W", {"naturally_aspirated", "twin_turbo"}),
    "oil_loop_load_w": ("thermal_network_screen.loads_w.oil_loop", "W", {"naturally_aspirated", "twin_turbo"}),
    "cooling_air_flow_kg_s": ("thermal_network_screen.required_mass_flows_kg_s.cooling_air", "kg/s", {"naturally_aspirated", "twin_turbo"}),
    "oil_flow_kg_s": ("thermal_network_screen.required_mass_flows_kg_s.oil", "kg/s", {"naturally_aspirated", "twin_turbo"}),
    "charge_lt_load_w": ("thermal_network_screen.loads_w.charge_lt_coolant", "W", {"twin_turbo"}),
    "charge_coolant_flow_kg_s": ("thermal_network_screen.required_mass_flows_kg_s.charge_coolant", "kg/s", {"twin_turbo"}),
    "compressor_pressure_ratio": ("turbo_screen.compressor_pressure_ratio", "ratio", {"twin_turbo"}),
    "compressor_power_total_w": ("turbo_screen.compressor_power_total_w", "W", {"twin_turbo"}),
    "required_turbine_flow_fraction_inverse_screen": ("turbo_screen.required_turbine_flow_fraction_inverse_screen", "ratio", {"twin_turbo"}),
}
EXPECTED_TECHNICAL_GATES = {
    "contract_valid",
    "doe_plan_valid",
    "case_manifest_generated",
    "selected_air_oil_architecture_locked",
    "modern_controls_contract_valid",
    "future_solver_image_available",
    "requested_target_scalar_excluded_from_fields",
    "full_target_independence_proven",
    "split_plan_generated",
}
EXPECTED_RELEASE_GATES = {
    "doe_execution_complete",
    "dataset_ready",
    "training_authorized",
    "surrogate_trained",
    "surrogate_validated_against_0d_solver",
    "ood_policy_calibrated",
    "one_dimensional_model_validated",
    "hydraulic_network_validated",
    "cfd_validated",
    "cht_validated",
    "physical_correlation_complete",
    "target_power_proven",
    "cooling_system_validated",
    "test_bench_start_authorized",
    "porsche_993_vehicle_installation_authorized",
    "metal_print_authorized",
    "manufacturing_authorized",
    "ecu_hardware_selected",
    "ecu_io_complete",
    "crank_cam_sync_validated",
    "injector_characterization_validated",
    "ignition_validated",
    "closed_loop_controls_validated",
    "vvt_vvl_validated",
    "lambda_control_validated",
    "knock_control_validated",
    "boost_failsafe_validated",
    "can_fd_architecture_validated",
    "sil_complete",
    "hil_complete",
}
TOP_LEVEL_KEYS = {
    "$comment",
    "schema_version",
    "phase",
    "status",
    "parents",
    "authority_boundary",
    "runtime",
    "variant_registry",
    "frozen_inputs",
    "axis_registry",
    "constraints",
    "sampling_plan",
    "dataset_partition",
    "feature_schema",
    "label_schema",
    "ood_policy",
    "physicsnemo_discovery",
    "fidelity_ladder",
    "physical_evidence_boundary",
    "unknown_registry",
    "technical_gates",
    "release_gates",
    "prohibited_claims",
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
IMMUTABLE_IMAGE_RE = re.compile(r"^[^\s@]+@sha256:[0-9a-f]{64}$")


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


def _canonical_json(value: Any) -> str:
    return (
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    )


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _finite(value: Any) -> bool:
    return _is_number(value) and math.isfinite(float(value))


def _unexpected_keys(value: Any, allowed: set[str], label: str) -> list[str]:
    if not isinstance(value, dict):
        return [f"{label}_not_object"]
    return [f"unexpected_key:{label}.{key}" for key in sorted(set(value) - allowed)] + [
        f"missing_key:{label}.{key}" for key in sorted(allowed - set(value))
    ]


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
    if not _inside(candidate, root.resolve()):
        return None
    if not candidate.is_file() or candidate.is_symlink():
        return None
    return candidate


def _target_leak(value: Any, path: str = "") -> str | None:
    forbidden = (
        "requested_power",
        "target_power",
        "delta_to_target",
        "distance_to_1600",
        "meets_1600",
        "inverse_sizing_seed",
    )
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{path}.{key}" if path else key
            if any(token in key.lower() for token in forbidden):
                return child
            nested = _target_leak(item, child)
            if nested:
                return nested
    elif isinstance(value, list):
        for index, item in enumerate(value):
            nested = _target_leak(item, f"{path}[{index}]")
            if nested:
                return nested
    elif isinstance(value, str):
        lowered = value.lower()
        if any(token in lowered for token in forbidden) or "1600hp" in lowered:
            return path
    return None


def _validate_parents(contract: dict[str, Any], root: Path, errors: list[str]) -> None:
    parents = contract.get("parents")
    if not isinstance(parents, list) or len(parents) != len(EXPECTED_PARENT_HASHES):
        errors.append("parents_count_invalid")
        return
    paths: set[str] = set()
    ids: set[str] = set()
    for index, parent in enumerate(parents):
        errors.extend(_unexpected_keys(parent, {"id", "path", "sha256", "role"}, f"parents[{index}]"))
        if not isinstance(parent, dict):
            continue
        parent_id = parent.get("id")
        path = parent.get("path")
        digest = parent.get("sha256")
        if not isinstance(parent_id, str) or not parent_id or parent_id in ids:
            errors.append(f"parent_id_invalid_or_duplicate:{index}")
        else:
            ids.add(parent_id)
        if not isinstance(path, str) or path in paths:
            errors.append(f"parent_path_invalid_or_duplicate:{index}")
            continue
        paths.add(path)
        expected = EXPECTED_PARENT_HASHES.get(path)
        if expected is None:
            errors.append(f"parent_unexpected:{path}")
            continue
        if digest != expected or not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            errors.append(f"parent_sha_invalid:{path}")
        resolved = _safe_file(root, path)
        if resolved is None:
            errors.append(f"parent_missing_or_unsafe:{path}")
        elif _sha256(resolved) != digest:
            errors.append(f"parent_sha_mismatch:{path}")
        elif path == "twins/reference-917-engine/air-oil-core-controls-f34a.json":
            try:
                decision_contract = _read_json(resolved)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                errors.append(f"f34a_parent_unreadable:{exc}")
            else:
                _validate_f34a_decision_parent(decision_contract, errors)
        expected_identity = EXPECTED_PARENT_IDENTITIES.get(path)
        if expected_identity is not None:
            expected_id, expected_role = expected_identity
            if parent_id != expected_id:
                errors.append(f"parent_id_invalid:{path}")
            if parent.get("role") != expected_role:
                errors.append(f"parent_role_invalid:{path}")
    if paths != set(EXPECTED_PARENT_HASHES):
        errors.append("parents_required_set_mismatch")


def _validate_f34a_decision_parent(value: Any, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append("f34a_parent_not_object")
        return
    decision = value.get("decision")
    if not isinstance(decision, dict):
        errors.append("f34a_parent_decision_missing")
    else:
        expected = {
            "id": "F34A-AIR-OIL-CORE-2026-CONTROLS",
            "selected_core_thermal_architecture": (
                "strict_forced_air_and_dry_sump_oil_only"
            ),
            "selected_controls_architecture": (
                "electronic_2026_requirements_only"
            ),
        }
        for key, expected_value in expected.items():
            if decision.get(key) != expected_value:
                errors.append(f"f34a_parent_decision_invalid:{key}")
    core = value.get("engine_core_boundary")
    if (
        not isinstance(core, dict)
        or core.get("core_liquid_coolant_loop_present") is not False
        or core.get("core_to_auxiliary_liquid_cross_connection_allowed") is not False
    ):
        errors.append("f34a_parent_core_liquid_boundary_invalid")
    controls = value.get("controls_architecture")
    if not isinstance(controls, dict):
        errors.append("f34a_parent_controls_missing")
    else:
        injection = controls.get("fuel_injection")
        ignition = controls.get("ignition")
        drive_by_wire = controls.get("drive_by_wire")
        valvetrain = controls.get("valvetrain_control")
        lambda_control = controls.get("lambda_control")
        knock_control = controls.get("knock_control")
        wastegates = controls.get("wastegates")
        communications = controls.get("communications")
        if (
            not isinstance(injection, dict)
            or injection.get("mode_requirement")
            != "sequential_electronic_port_injection"
            or injection.get("minimum_independent_channels") != 12
            or injection.get("target_independent_channels") != 24
            or injection.get("validated") is not False
        ):
            errors.append("f34a_parent_injection_invalid")
        if (
            not isinstance(ignition, dict)
            or ignition.get("mode_requirement") != "dual_electronic_ignition"
            or ignition.get("independent_channels_required") != 24
            or ignition.get("validated") is not False
        ):
            errors.append("f34a_parent_ignition_invalid")
        if (
            not isinstance(drive_by_wire, dict)
            or drive_by_wire.get("mode_requirement")
            != "redundant_electronic_throttle_control"
            or drive_by_wire.get("actuator_count_minimum") != 2
            or drive_by_wire.get("one_actuator_per_bank_required") is not True
            or drive_by_wire.get("validated") is not False
        ):
            errors.append("f34a_parent_dbw_invalid")
        if (
            not isinstance(valvetrain, dict)
            or valvetrain.get("variable_cam_timing_candidate") is not True
            or valvetrain.get("variable_valve_lift_candidate") is not True
            or valvetrain.get("selected") is not False
            or valvetrain.get("validated") is not False
        ):
            errors.append("f34a_parent_valvetrain_invalid")
        if (
            not isinstance(lambda_control, dict)
            or lambda_control.get("closed_loop_required") is not True
            or lambda_control.get("selected") is not False
            or lambda_control.get("validated") is not False
        ):
            errors.append("f34a_parent_lambda_control_invalid")
        if (
            not isinstance(knock_control, dict)
            or knock_control.get("mode_requirement")
            != "crank_angle_windowed_cylinder_attributed_knock_control"
            or knock_control.get("selected") is not False
            or knock_control.get("validated") is not False
        ):
            errors.append("f34a_parent_knock_control_invalid")
        if (
            not isinstance(wastegates, dict)
            or wastegates.get("mode_requirement")
            != "electronic_wastegate_actuation"
            or wastegates.get("deenergized_safe_open_state_required") is not True
            or wastegates.get("validated") is not False
        ):
            errors.append("f34a_parent_wastegate_invalid")
        if (
            not isinstance(communications, dict)
            or communications.get("can_fd_required") is not True
            or communications.get("selected") is not False
            or communications.get("validated") is not False
        ):
            errors.append("f34a_parent_communications_invalid")
    sensors = value.get("sensor_registry")
    if not isinstance(sensors, list):
        errors.append("f34a_parent_sensor_registry_invalid")
    else:
        by_id = {
            sensor.get("id"): sensor
            for sensor in sensors
            if isinstance(sensor, dict) and isinstance(sensor.get("id"), str)
        }
        required_scopes = {
            "cam_phase": "each_actuated_camshaft",
            "valve_lift_state": "each_variable_lift_actuator",
            "lambda": "each_control_zone",
            "knock": "each_combustion_monitoring_zone",
            "exhaust_gas_temperature": "each_cylinder",
            "fuel_differential_pressure": "each_fuel_rail_and_reference_manifold",
            "core_metal_temperature": "each_cylinder_head",
        }
        for sensor_id, scope in required_scopes.items():
            sensor = by_id.get(sensor_id)
            if not isinstance(sensor, dict) or sensor.get("scope") != scope:
                errors.append(f"f34a_parent_sensor_invalid:{sensor_id}")
    for section in ("technical_gates", "release_gates"):
        gates = value.get(section)
        if not isinstance(gates, dict) or any(item is not False for item in gates.values()):
            errors.append(f"f34a_parent_gates_not_fail_closed:{section}")


def _validate_authority_and_runtime(contract: dict[str, Any], errors: list[str]) -> None:
    authority_expected = {
        "requested_power_target_scalar_is_direct_doe_input": False,
        "requested_power_target_is_feature": False,
        "requested_power_target_is_label": False,
        "requested_power_target_is_filter_or_weight": False,
        "requested_power_target_has_indirect_sampling_ancestry": True,
        "inverse_sizing_seed_ancestry_present": True,
        "full_target_independence_proven": False,
        "na_and_twin_turbo_models_are_separate": True,
        "parameter_bounds_are_measured_limits": False,
        "parameter_bounds_classification": "f34_design_hypotheses_for_numerical_screening_only",
        "numerical_holdout_is_physical_evidence": False,
        "geometry_holdout_available": False,
        "doe_executed": False,
        "surrogate_trained": False,
        "physicsnemo_training_authorized": False,
        "physical_calibration_available": False,
        "physical_correlation_complete": False,
        "selected_engine_core_cooling": "forced_air_and_dry_sump_oil",
        "engine_core_liquid_coolant_present": False,
        "legacy_f33_liquid_head_result_transfer_authorized": False,
        "modern_controls_contract_required": True,
        "electronic_controls_response_modeled_in_l0": False,
        "f33_runtime_compatible_with_selected_architecture": False,
    }
    authority = contract.get("authority_boundary")
    errors.extend(_unexpected_keys(authority, set(authority_expected), "authority_boundary"))
    if isinstance(authority, dict):
        for key, expected in authority_expected.items():
            if authority.get(key) != expected:
                errors.append(f"authority_value_invalid:{key}")

    runtime = contract.get("runtime")
    errors.extend(_unexpected_keys(runtime, {"plan_generation", "future_solver"}, "runtime"))
    if not isinstance(runtime, dict):
        return
    plan_runtime_expected = {
        "classification": "unattested_host_python_stdlib_only",
        "solver_executed": False,
        "container_used": False,
        "python_version_pinned": False,
        "host_platform_attested": False,
        "network_isolation_attested": False,
        "root_filesystem_read_only_attested": False,
    }
    plan_runtime = runtime.get("plan_generation")
    errors.extend(_unexpected_keys(plan_runtime, set(plan_runtime_expected), "runtime.plan_generation"))
    if isinstance(plan_runtime, dict):
        for key, expected in plan_runtime_expected.items():
            if plan_runtime.get(key) != expected:
                errors.append(f"plan_runtime_value_invalid:{key}")

    solver_runtime_keys = {
        "reuse_existing_minimal_image",
        "immutable_ref",
        "blocked_reason",
        "platform",
        "user",
        "network",
        "root_filesystem_read_only",
        "cantera_version",
        "numpy_version",
        "dependency_versions_pinned",
        "execution_authorized",
        "execution_verified_for_f34",
        "gpu_required",
        "vast_rental_authorized",
    }
    solver_runtime = runtime.get("future_solver")
    errors.extend(_unexpected_keys(solver_runtime, solver_runtime_keys, "runtime.future_solver"))
    if not isinstance(solver_runtime, dict):
        return
    if solver_runtime.get("reuse_existing_minimal_image") is not False:
        errors.append("runtime_reuse_image_must_be_false")
    if solver_runtime.get("immutable_ref") is not None:
        errors.append("runtime_immutable_ref_must_be_null")
    if solver_runtime.get("blocked_reason") != (
        "f33_image_models_liquid_cooled_heads_and_is_incompatible_with_selected_air_oil_core"
    ):
        errors.append("runtime_blocked_reason_invalid")
    fixed_values = {
        "platform": "linux/amd64",
        "user": "9133:9133",
        "network": "none",
        "root_filesystem_read_only": True,
        "cantera_version": "3.2.0",
        "numpy_version": "2.5.2",
        "dependency_versions_pinned": False,
        "execution_authorized": False,
        "execution_verified_for_f34": False,
        "gpu_required": False,
        "vast_rental_authorized": False,
    }
    for key, expected in fixed_values.items():
        if solver_runtime.get(key) != expected:
            errors.append(f"runtime_value_invalid:{key}")


def _validate_variants_and_axes(contract: dict[str, Any], errors: list[str]) -> None:
    variants = contract.get("variant_registry")
    if not isinstance(variants, list) or len(variants) != 2:
        errors.append("variant_registry_invalid")
        variants = []
    seen_configs: set[str] = set()
    variant_keys = {
        "id",
        "configuration",
        "short_id",
        "active_axis_count",
        "legacy_f33_forward_input_ref",
        "f34_seed_transform",
        "selected_architecture_id",
        "separate_model_required",
        "solver_cases_executed",
    }
    for index, variant in enumerate(variants):
        errors.extend(_unexpected_keys(variant, variant_keys, f"variant_registry[{index}]"))
        if not isinstance(variant, dict):
            continue
        configuration = variant.get("configuration")
        expected = EXPECTED_VARIANTS.get(configuration)
        if expected is None or configuration in seen_configs:
            errors.append(f"variant_configuration_invalid:{index}")
            continue
        seen_configs.add(configuration)
        if variant.get("id") != expected["id"]:
            errors.append(f"variant_id_invalid:{configuration}")
        if variant.get("short_id") != expected["short_id"]:
            errors.append(f"variant_short_id_invalid:{configuration}")
        if variant.get("active_axis_count") != expected["axis_count"]:
            errors.append(f"variant_axis_count_invalid:{configuration}")
        if variant.get("separate_model_required") is not True:
            errors.append(f"variant_separate_model_required:{configuration}")
        if variant.get("solver_cases_executed") != 0:
            errors.append(f"variant_solver_cases_must_be_zero:{configuration}")
        if variant.get("f34_seed_transform") != (
            "strip_engine_core_coolant_add_air_oil_thermal_and_modern_controls_lock"
        ):
            errors.append(f"variant_seed_transform_invalid:{configuration}")
        if variant.get("selected_architecture_id") != (
            "F34A-AIR-OIL-CORE-2026-CONTROLS"
        ):
            errors.append(f"variant_architecture_invalid:{configuration}")
    if seen_configs != set(EXPECTED_VARIANTS):
        errors.append("variant_configuration_set_mismatch")

    frozen_expected = {
        "classification": "design_hypotheses_frozen_only_to_reduce_f34_dimensionality",
        "legacy_center_source": "pinned_f33_forward_input_with_declared_inverse_sizing_ancestry",
        "selected_architecture_id": "F34A-AIR-OIL-CORE-2026-CONTROLS",
        "bore_mm": 90.0,
        "stroke_mm": 70.4,
        "cylinder_count": 12,
        "fuel_surrogate": "n_dodecane_cantera_builtin",
        "fuel_lhv_j_kg": 43000000.0,
        "cooling_air_cp_j_kg_k": 1005.0,
        "oil_cp_j_kg_k": 2080.0,
        "charge_coolant_cp_j_kg_k": 3600.0,
        "engine_core_liquid_coolant_present": False,
        "electronic_controls_response_model_present": False,
        "physical_authority": False,
        "future_geometry_optimization_authorized": False,
    }
    frozen = contract.get("frozen_inputs")
    errors.extend(_unexpected_keys(frozen, set(frozen_expected), "frozen_inputs"))
    if isinstance(frozen, dict):
        for key, expected_value in frozen_expected.items():
            if frozen.get(key) != expected_value or (
                _is_number(expected_value) and not _is_number(frozen.get(key))
            ):
                errors.append(f"frozen_input_invalid:{key}")

    axes = contract.get("axis_registry")
    if not isinstance(axes, list) or len(axes) != 26:
        errors.append("axis_registry_count_invalid")
        return
    ids = [axis.get("id") if isinstance(axis, dict) else None for axis in axes]
    if ids != EXPECTED_AXIS_ORDER:
        errors.append("axis_order_or_identity_invalid")
    axis_keys = {"id", "target_path", "unit", "applies_to", "bounds", "classification"}
    allowed_configs = set(EXPECTED_VARIANTS)
    for index, axis in enumerate(axes):
        if not isinstance(axis, dict):
            errors.append(f"axis_not_object:{index}")
            continue
        allowed = set(axis_keys)
        if axis.get("id") in {"exhaust_to_manifold_pressure_ratio", "fmep_coefficient_scale"}:
            allowed.add("transform")
        errors.extend(_unexpected_keys(axis, allowed, f"axis_registry[{index}]"))
        axis_id = axis.get("id")
        if axis.get("unit") != EXPECTED_AXIS_UNITS.get(axis_id):
            errors.append(f"unit_registry_mismatch:{axis_id}")
        applies = axis.get("applies_to")
        expected_applies = allowed_configs if axis_id in EXPECTED_COMMON_AXES else {"twin_turbo"}
        if not isinstance(applies, list) or set(applies) != expected_applies or len(applies) != len(expected_applies):
            errors.append(f"axis_applicability_invalid:{axis_id}")
            continue
        bounds = axis.get("bounds")
        if not isinstance(bounds, dict) or set(bounds) != expected_applies:
            errors.append(f"axis_bounds_keys_invalid:{axis_id}")
            continue
        for configuration, interval in bounds.items():
            if (
                not isinstance(interval, list)
                or len(interval) != 2
                or not all(_finite(value) for value in interval)
                or float(interval[0]) >= float(interval[1])
            ):
                errors.append(f"axis_bounds_invalid:{axis_id}:{configuration}")
        if not isinstance(axis.get("target_path"), str) or not axis["target_path"]:
            errors.append(f"axis_target_path_invalid:{axis_id}")
        elif axis["target_path"] != EXPECTED_AXIS_PATHS.get(axis_id):
            errors.append(f"axis_target_path_mismatch:{axis_id}")
        expected_transform = EXPECTED_AXIS_TRANSFORMS.get(axis_id)
        if expected_transform is None:
            if "transform" in axis:
                errors.append(f"axis_transform_unexpected:{axis_id}")
        elif axis.get("transform") != expected_transform:
            errors.append(f"axis_transform_mismatch:{axis_id}")
    for configuration, expected in EXPECTED_VARIANTS.items():
        active = [axis for axis in axes if isinstance(axis, dict) and configuration in axis.get("applies_to", [])]
        if len(active) != expected["axis_count"]:
            errors.append(f"active_axis_count_mismatch:{configuration}")


def _validate_plan_and_splits(contract: dict[str, Any], errors: list[str]) -> None:
    constraints = contract.get("constraints")
    if not isinstance(constraints, list):
        errors.append("constraints_invalid")
    else:
        ids: list[str] = []
        for index, constraint in enumerate(constraints):
            if not isinstance(constraint, dict):
                errors.append(f"constraint_not_object:{index}")
                continue
            allowed = {"id", "rule", "failure_action", "classification"}
            required = {"id", "rule", "failure_action"}
            extra = set(constraint) - allowed
            missing = required - set(constraint)
            errors.extend(f"unexpected_key:constraints[{index}].{key}" for key in sorted(extra))
            errors.extend(f"missing_key:constraints[{index}].{key}" for key in sorted(missing))
            ids.append(constraint.get("id"))
        if set(ids) != EXPECTED_CONSTRAINTS or len(ids) != len(EXPECTED_CONSTRAINTS):
            errors.append("constraint_set_invalid")

    plan = contract.get("sampling_plan")
    plan_keys = {
        "generator",
        "case_ordering",
        "deduplication",
        "seed_derivation",
        "seed_namespace",
        "permutation_rng",
        "seeds",
        "anchors",
        "morris_screening",
        "space_filling",
        "ood_challenge",
        "planned_solver_calls_before_deduplication",
        "executed_case_count",
    }
    errors.extend(_unexpected_keys(plan, plan_keys, "sampling_plan"))
    if not isinstance(plan, dict):
        return
    if plan.get("generator") != "f34_air_oil_deterministic_plan_v2":
        errors.append("sampling_generator_invalid")
    if plan.get("permutation_rng") != "sha256_counter_fisher_yates_v1":
        errors.append("sampling_permutation_rng_invalid")
    seeds = plan.get("seeds")
    errors.extend(_unexpected_keys(seeds, {"morris", "lhs", "partition", "ood"}, "sampling_plan.seeds"))
    if isinstance(seeds, dict):
        for key, value in seeds.items():
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0 or value >= 2**63:
                errors.append(f"invalid_seed:{key}")
    anchors = plan.get("anchors")
    errors.extend(_unexpected_keys(anchors, {"method", "naturally_aspirated_cases", "twin_turbo_cases", "executed"}, "sampling_plan.anchors"))
    if isinstance(anchors, dict):
        if anchors.get("method") != "transformed_f33_centers_with_air_oil_architecture_lock" or anchors.get("naturally_aspirated_cases") != 1 or anchors.get("twin_turbo_cases") != 1 or anchors.get("executed") is not False:
            errors.append("anchor_plan_invalid")
    morris = plan.get("morris_screening")
    morris_keys = {"method", "grid_levels", "step_normalized", "naturally_aspirated", "twin_turbo", "used_for_surrogate_training", "executed"}
    errors.extend(_unexpected_keys(morris, morris_keys, "sampling_plan.morris_screening"))
    if isinstance(morris, dict):
        if morris.get("method") != "deterministic_balanced_morris_trajectories_v2" or morris.get("grid_levels") != 6 or not _finite(morris.get("step_normalized")) or float(morris["step_normalized"]) != 0.2 or morris.get("used_for_surrogate_training") is not False or morris.get("executed") is not False:
            errors.append("morris_plan_invalid")
        for configuration, expected in EXPECTED_VARIANTS.items():
            entry = morris.get(configuration)
            errors.extend(_unexpected_keys(entry, {"axis_count", "trajectories", "planned_cases"}, f"sampling_plan.morris_screening.{configuration}"))
            if isinstance(entry, dict):
                if entry.get("axis_count") != expected["axis_count"] or entry.get("planned_cases") != expected["morris_count"] or entry.get("planned_cases") != entry.get("trajectories", -1) * (entry.get("axis_count", -1) + 1):
                    errors.append(f"morris_counts_invalid:{configuration}")
    lhs = plan.get("space_filling")
    errors.extend(_unexpected_keys(lhs, {"method", "jitter", "naturally_aspirated_cases", "twin_turbo_cases", "executed"}, "sampling_plan.space_filling"))
    if isinstance(lhs, dict):
        if lhs.get("method") != "centered_latin_hypercube_v1" or lhs.get("jitter") is not False or lhs.get("executed") is not False:
            errors.append("lhs_plan_invalid")
        for configuration, expected in EXPECTED_VARIANTS.items():
            if lhs.get(f"{configuration}_cases") != expected["lhs_count"]:
                errors.append(f"lhs_count_invalid:{configuration}")
    ood = plan.get("ood_challenge")
    errors.extend(_unexpected_keys(ood, {"method", "shell_fraction_outside_training_bounds", "naturally_aspirated_cases", "twin_turbo_cases", "used_for_training", "executed"}, "sampling_plan.ood_challenge"))
    if isinstance(ood, dict):
        if ood.get("method") != "deterministic_single_axis_shell_v1" or not _finite(ood.get("shell_fraction_outside_training_bounds")) or not 0.0 < float(ood["shell_fraction_outside_training_bounds"]) <= 0.25 or ood.get("used_for_training") is not False or ood.get("executed") is not False:
            errors.append("ood_plan_invalid")
        for configuration, expected in EXPECTED_VARIANTS.items():
            if ood.get(f"{configuration}_cases") != expected["ood_count"]:
                errors.append(f"ood_count_invalid:{configuration}")
    expected_total = sum(1 + item["morris_count"] + item["lhs_count"] + item["ood_count"] for item in EXPECTED_VARIANTS.values())
    if plan.get("planned_solver_calls_before_deduplication") != expected_total or plan.get("executed_case_count") != 0:
        errors.append("sampling_total_or_execution_count_invalid")

    partition = contract.get("dataset_partition")
    partition_keys = {
        "assignment_must_precede_solver_execution",
        "applies_only_to_space_filling_cases",
        "design_block_size",
        "group_keys_available_now",
        "group_keys_missing_now",
        "naturally_aspirated",
        "twin_turbo",
        "morris_in_training",
        "ood_in_training",
        "digital_holdout_is_physical_holdout",
        "geometry_holdout_present",
        "normalization_fit_scope",
        "normalization_executed",
        "split_manifest_generated",
    }
    errors.extend(_unexpected_keys(partition, partition_keys, "dataset_partition"))
    if not isinstance(partition, dict):
        return
    fixed = {
        "assignment_must_precede_solver_execution": True,
        "applies_only_to_space_filling_cases": True,
        "design_block_size": 16,
        "morris_in_training": False,
        "ood_in_training": False,
        "digital_holdout_is_physical_holdout": False,
        "geometry_holdout_present": False,
        "normalization_fit_scope": "train_only_after_execution_and_acceptance",
        "normalization_executed": False,
        "split_manifest_generated": False,
    }
    for key, expected in fixed.items():
        if partition.get(key) != expected:
            errors.append(f"dataset_partition_value_invalid:{key}")
    if partition.get("group_keys_available_now") != [
        "variant_id",
        "design_block_id",
        "solver_campaign_id",
    ]:
        errors.append("dataset_partition_available_group_keys_invalid")
    if partition.get("group_keys_missing_now") != [
        "released_geometry_family_id",
        "physical_test_campaign_id",
    ]:
        errors.append("dataset_partition_missing_group_keys_invalid")
    split_keys = {"train", "validation", "conformal_calibration", "locked_digital_holdout"}
    for configuration, expected in EXPECTED_VARIANTS.items():
        entry = partition.get(configuration)
        errors.extend(_unexpected_keys(entry, split_keys, f"dataset_partition.{configuration}"))
        if isinstance(entry, dict):
            values = list(entry.values())
            if any(not isinstance(value, int) or isinstance(value, bool) or value <= 0 for value in values) or sum(values) != expected["lhs_count"] or any(value % 16 for value in values):
                errors.append(f"dataset_partition_counts_invalid:{configuration}")


def _validate_remaining_sections(contract: dict[str, Any], errors: list[str]) -> None:
    feature = contract.get("feature_schema")
    feature_expected = {
        "source": "axis_registry_in_declared_order",
        "variant_id_is_metadata_not_feature": True,
        "requested_target_fields_forbidden": True,
        "units_source": "axis_registry.unit",
        "normalization": None,
        "schema_frozen": True,
    }
    errors.extend(_unexpected_keys(feature, set(feature_expected), "feature_schema"))
    if isinstance(feature, dict):
        for key, expected in feature_expected.items():
            if feature.get(key) != expected:
                errors.append(f"feature_schema_value_invalid:{key}")

    labels = contract.get("label_schema")
    if not isinstance(labels, list) or not labels:
        errors.append("label_schema_invalid")
    else:
        label_ids: set[str] = set()
        for index, label in enumerate(labels):
            errors.extend(_unexpected_keys(label, {"id", "path", "unit", "applies_to"}, f"label_schema[{index}]"))
            if not isinstance(label, dict):
                continue
            label_id = label.get("id")
            if not isinstance(label_id, str) or not label_id or label_id in label_ids:
                errors.append(f"label_id_invalid_or_duplicate:{index}")
            else:
                label_ids.add(label_id)
            applies = label.get("applies_to")
            if not isinstance(applies, list) or not applies or not set(applies).issubset(EXPECTED_VARIANTS) or len(applies) != len(set(applies)):
                errors.append(f"label_applicability_invalid:{label_id}")
            expected = EXPECTED_LABELS.get(label_id)
            if expected is None:
                errors.append(f"label_unexpected:{label_id}")
            elif (
                label.get("path") != expected[0]
                or label.get("unit") != expected[1]
                or set(applies or []) != expected[2]
            ):
                errors.append(f"label_schema_mismatch:{label_id}")
        if label_ids != set(EXPECTED_LABELS):
            errors.append("label_schema_set_invalid")

    leak_sections = {
        "axis_registry": contract.get("axis_registry"),
        "sampling_plan": contract.get("sampling_plan"),
        "dataset_partition": contract.get("dataset_partition"),
        "label_schema": contract.get("label_schema"),
    }
    for section, value in leak_sections.items():
        leaked_path = _target_leak(value, section)
        if leaked_path:
            errors.append(f"target_leakage_forbidden:{leaked_path}")

    ood = contract.get("ood_policy")
    ood_keys = {
        "hard_ood_conditions",
        "soft_ood_scores",
        "nearest_distance_threshold",
        "ensemble_disagreement_threshold",
        "interval_width_threshold",
        "default_ood_action",
        "ood_criteria_calibrated",
    }
    errors.extend(_unexpected_keys(ood, ood_keys, "ood_policy"))
    if isinstance(ood, dict):
        expected_hard = {
            "outside_declared_axis_bounds",
            "constraint_violation",
            "unknown_variant_or_topology",
            "different_turbocharger_count",
            "different_turbo_candidate_identity",
            "different_fuel_surrogate",
            "different_cooling_architecture",
            "different_fidelity_level",
        }
        expected_soft = {
            "normalized_nearest_training_point_distance",
            "ensemble_disagreement",
            "conformal_interval_width",
        }
        if set(ood.get("hard_ood_conditions", [])) != expected_hard:
            errors.append("ood_hard_conditions_invalid")
        if set(ood.get("soft_ood_scores", [])) != expected_soft:
            errors.append("ood_soft_scores_invalid")
        for key in (
            "nearest_distance_threshold",
            "ensemble_disagreement_threshold",
            "interval_width_threshold",
        ):
            if ood.get(key) is not None:
                errors.append(f"ood_threshold_must_be_null:{key}")
        if ood.get("default_ood_action") != "reject_prediction_and_request_new_solver_case":
            errors.append("ood_default_action_invalid")
        if ood.get("ood_criteria_calibrated") is not False:
            errors.append("ood_calibration_gate_must_be_false")

    discovery = contract.get("physicsnemo_discovery")
    discovery_keys = {"repository", "commit", "inspected_on", "runtime_compatibility_verified", "candidate_models", "candidate_datapipes", "reference_examples", "training_executed", "training_authorized"}
    errors.extend(_unexpected_keys(discovery, discovery_keys, "physicsnemo_discovery"))
    if isinstance(discovery, dict):
        if discovery.get("repository") != "https://github.com/NVIDIA/physicsnemo" or not isinstance(discovery.get("commit"), str) or not COMMIT_RE.fullmatch(discovery["commit"]):
            errors.append("physicsnemo_discovery_source_invalid")
        for key in ("runtime_compatibility_verified", "training_executed", "training_authorized"):
            if discovery.get(key) is not False:
                errors.append(f"physicsnemo_gate_must_be_false:{key}")
        models = discovery.get("candidate_models")
        if not isinstance(models, list) or {item.get("name") for item in models if isinstance(item, dict)} != {"FullyConnected", "DoMINO", "GeoTransolver", "FIGConvUNet"}:
            errors.append("physicsnemo_model_menu_invalid")
        else:
            expected_model_paths = {
                "FullyConnected": "physicsnemo/models/mlp/fully_connected.py",
                "DoMINO": "physicsnemo/models/domino/model.py",
                "GeoTransolver": "physicsnemo/models/geotransolver/geotransolver.py",
                "FIGConvUNet": "physicsnemo/models/figconvnet/figconvunet.py",
            }
            for index, model in enumerate(models):
                errors.extend(_unexpected_keys(model, {"name", "repo_path", "role", "selected"}, f"physicsnemo_discovery.candidate_models[{index}]"))
                if model.get("selected") is not False:
                    errors.append(f"physicsnemo_model_selection_must_be_false:{model.get('name')}")
                if model.get("repo_path") != expected_model_paths.get(model.get("name")):
                    errors.append(f"physicsnemo_model_path_invalid:{model.get('name')}")
            if len(models) != 4:
                errors.append("physicsnemo_model_menu_duplicate")
        datapipes = discovery.get("candidate_datapipes")
        if not isinstance(datapipes, list) or len(datapipes) != 3:
            errors.append("physicsnemo_datapipe_menu_invalid")
        else:
            expected_datapipes = {
                "NumpyReader": ["physicsnemo/datapipes/readers/numpy.py"],
                "DoMINODataPipe": ["physicsnemo/datapipes/cae/domino_datapipe.py"],
                "DomainMeshReader_and_MeshDataset": [
                    "physicsnemo/datapipes/readers/mesh.py",
                    "physicsnemo/datapipes/mesh_dataset.py",
                ],
            }
            seen: set[str] = set()
            for index, datapipe in enumerate(datapipes):
                if not isinstance(datapipe, dict):
                    errors.append(f"physicsnemo_datapipe_not_object:{index}")
                    continue
                name = datapipe.get("name")
                seen.add(name)
                allowed = {"name", "role", "repo_paths" if name == "DomainMeshReader_and_MeshDataset" else "repo_path"}
                errors.extend(_unexpected_keys(datapipe, allowed, f"physicsnemo_discovery.candidate_datapipes[{index}]"))
                actual_paths = datapipe.get("repo_paths") if "repo_paths" in datapipe else [datapipe.get("repo_path")]
                if actual_paths != expected_datapipes.get(name):
                    errors.append(f"physicsnemo_datapipe_path_invalid:{name}")
            if seen != set(expected_datapipes):
                errors.append("physicsnemo_datapipe_set_invalid")
        examples = discovery.get("reference_examples")
        expected_examples = {
            "examples/cfd/darcy_physics_informed/README.md",
            "examples/cfd/transient_conjugate_heat_transfer_tank_fill/README.md",
        }
        if not isinstance(examples, list) or len(examples) != 2:
            errors.append("physicsnemo_reference_examples_invalid")
        else:
            for index, example in enumerate(examples):
                errors.extend(_unexpected_keys(example, {"repo_path", "role"}, f"physicsnemo_discovery.reference_examples[{index}]"))
            if {item.get("repo_path") for item in examples if isinstance(item, dict)} != expected_examples:
                errors.append("physicsnemo_reference_example_paths_invalid")

    ladder = contract.get("fidelity_ladder")
    expected_ladder_ids = [
        "L0_F34_AIR_OIL_0D",
        "L1_OPEN_CYLINDER_1D_GAS_DYNAMICS",
        "L1_THERMAL_HYDRAULIC_NETWORK",
        "L2_RANS_CFD",
        "L3_CHT",
    ]
    if not isinstance(ladder, list) or [item.get("id") for item in ladder if isinstance(item, dict)] != expected_ladder_ids:
        errors.append("fidelity_ladder_invalid")
    else:
        for index, item in enumerate(ladder):
            if index == 0:
                errors.extend(_unexpected_keys(item, {"id", "planned_cases", "executed_cases", "physical_correlation"}, f"fidelity_ladder[{index}]"))
                if item.get("planned_cases") != 2570 or item.get("executed_cases") != 0 or item.get("physical_correlation") is not False:
                    errors.append("fidelity_l0_state_invalid")
            else:
                errors.extend(_unexpected_keys(item, {"id", "planned_case_budget", "solver_ready", "executed"}, f"fidelity_ladder[{index}]"))
                if item.get("solver_ready") is not False or item.get("executed") is not False:
                    errors.append(f"fidelity_gate_must_be_false:{item.get('id')}")

    physical = contract.get("physical_evidence_boundary")
    physical_expected = {
        "bench_dataset_ref": None,
        "measurement_uncertainty_model_ref": None,
        "sensor_calibration_manifest_ref": None,
        "physical_calibration_record_count": 0,
        "physical_validation_record_count": 0,
        "locked_physical_holdout_record_count": 0,
        "physical_split_preregistered": False,
        "physical_test_execution_authorized": False,
        "held_out_physical_correlation_complete": False,
        "synthetic_data_may_open_physical_gate": False,
    }
    errors.extend(_unexpected_keys(physical, set(physical_expected), "physical_evidence_boundary"))
    if isinstance(physical, dict):
        for key, expected in physical_expected.items():
            if physical.get(key) != expected:
                errors.append(f"physical_evidence_value_invalid:{key}")

    unknowns = contract.get("unknown_registry")
    if not isinstance(unknowns, list) or not unknowns:
        errors.append("unknown_registry_invalid")
    else:
        ids: set[str] = set()
        for index, unknown in enumerate(unknowns):
            errors.extend(_unexpected_keys(unknown, {"id", "value", "blocking_for"}, f"unknown_registry[{index}]"))
            if not isinstance(unknown, dict):
                continue
            unknown_id = unknown.get("id")
            if not isinstance(unknown_id, str) or not unknown_id or unknown_id in ids:
                errors.append(f"unknown_id_invalid_or_duplicate:{index}")
            else:
                ids.add(unknown_id)
            if unknown.get("value") is not None:
                errors.append(f"unknown_value_must_be_null:{unknown_id}")

    technical = contract.get("technical_gates")
    if not isinstance(technical, dict) or set(technical) != EXPECTED_TECHNICAL_GATES:
        errors.append("technical_gate_set_invalid")
    elif any(value is not False for value in technical.values()):
        errors.append("technical_gates_must_be_false_in_contract")
    release = contract.get("release_gates")
    if not isinstance(release, dict) or set(release) != EXPECTED_RELEASE_GATES:
        errors.append("release_gate_set_invalid")
    elif any(value is not False for value in release.values()):
        errors.append("release_gates_must_all_be_false")
    prohibited = contract.get("prohibited_claims")
    if (
        not isinstance(prohibited, list)
        or len(prohibited) != len(set(prohibited))
        or any(not isinstance(value, str) or not value for value in prohibited)
    ):
        errors.append("prohibited_claims_invalid")


def validate_contract(contract: Any, project_root: Path = ROOT) -> list[str]:
    """Return all fail-closed validation errors for the F34 contract."""

    if not isinstance(contract, dict):
        return ["contract_not_object"]
    errors = _unexpected_keys(contract, TOP_LEVEL_KEYS, "contract")
    if contract.get("schema_version") != "1.0.0":
        errors.append("schema_version_invalid")
    if contract.get("phase") != "F34":
        errors.append("phase_invalid")
    if contract.get("status") != "doe_contract_and_case_plan_only_no_solver_cases_executed":
        errors.append("status_invalid")
    _validate_parents(contract, project_root, errors)
    _validate_authority_and_runtime(contract, errors)
    _validate_variants_and_axes(contract, errors)
    _validate_plan_and_splits(contract, errors)
    _validate_remaining_sections(contract, errors)
    return sorted(set(errors))


def _seed(contract: dict[str, Any], configuration: str, block: str, suffix: str = "") -> int:
    plan = contract["sampling_plan"]
    base = int(plan["seeds"][block])
    payload = f"{plan['seed_namespace']}|{base}|{configuration}|{block}|{suffix}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big", signed=False)


class _HashRng:
    """Versioned SHA-256 counter RNG used only for deterministic DOE ordering."""

    def __init__(self, seed: int):
        if not isinstance(seed, int) or isinstance(seed, bool) or not 0 <= seed < 2**64:
            raise ValueError("hash RNG seed must be an unsigned 64-bit integer")
        self._seed = seed.to_bytes(8, "big", signed=False)
        self._counter = 0

    def _u64(self) -> int:
        block = hashlib.sha256(
            b"f34-hash-rng-v1\x00"
            + self._seed
            + self._counter.to_bytes(8, "big", signed=False)
        ).digest()
        self._counter += 1
        return int.from_bytes(block[:8], "big", signed=False)

    def randbelow(self, upper: int) -> int:
        if not isinstance(upper, int) or isinstance(upper, bool) or upper <= 0:
            raise ValueError("randbelow upper bound must be a positive integer")
        limit = 2**64 - (2**64 % upper)
        while True:
            value = self._u64()
            if value < limit:
                return value % upper

    def shuffle(self, values: list[Any]) -> None:
        for index in range(len(values) - 1, 0, -1):
            other = self.randbelow(index + 1)
            values[index], values[other] = values[other], values[index]


def _active_axes(contract: dict[str, Any], configuration: str) -> list[dict[str, Any]]:
    return [axis for axis in contract["axis_registry"] if configuration in axis["applies_to"]]


def _index_variants(f33_contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    variants = f33_contract.get("engine_variants")
    if not isinstance(variants, list):
        raise ValueError("invalid F33 contract: engine_variants missing")
    result = {
        item["configuration"]: item
        for item in variants
        if isinstance(item, dict) and isinstance(item.get("configuration"), str)
    }
    if set(result) != set(EXPECTED_VARIANTS):
        raise ValueError("invalid F33 contract: exact NA and twin_turbo variants required")
    for configuration, expected in EXPECTED_VARIANTS.items():
        if result[configuration].get("id") != expected["id"]:
            raise ValueError(f"invalid F33 variant identity:{configuration}")
        if not isinstance(result[configuration].get("forward_solver_input"), dict):
            raise ValueError(f"invalid F33 forward input:{configuration}")
    return result


def _f34_base_forward_input(
    legacy_forward: dict[str, Any], configuration: str
) -> dict[str, Any]:
    """Create the selected air/oil F34 seed without rewriting F33 history."""

    result = copy.deepcopy(legacy_forward)
    thermal = result.get("thermal_hypotheses")
    units = result.get("unit_registry")
    if not isinstance(thermal, dict) or not isinstance(units, dict):
        raise ValueError(f"F33 thermal or unit registry missing:{configuration}")

    try:
        cylinder_fraction = thermal.pop(
            "cylinder_air_heat_fraction_of_fuel_power"
        )
        thermal.pop("coolant_cp_j_kg_k")
        thermal.pop("head_coolant_delta_t_k")
    except KeyError as exc:
        raise ValueError(
            f"F33 legacy liquid-head seed schema mismatch:{configuration}"
        ) from exc
    thermal["cylinder_heat_fraction_of_fuel_power"] = cylinder_fraction
    thermal["head_heat_to_oil_fraction"] = 0.35
    thermal["cooling_air_cp_j_kg_k"] = 1005.0
    thermal["cooling_air_delta_t_k"] = 80.0

    units.pop("thermal_hypotheses.cylinder_air_heat_fraction_of_fuel_power", None)
    units.pop("thermal_hypotheses.coolant_cp_j_kg_k", None)
    units.pop("thermal_hypotheses.head_coolant_delta_t_k", None)
    units.update(
        {
            "thermal_hypotheses.cylinder_heat_fraction_of_fuel_power": "ratio",
            "thermal_hypotheses.head_heat_to_oil_fraction": "ratio",
            "thermal_hypotheses.cooling_air_cp_j_kg_k": "J/(kg*K)",
            "thermal_hypotheses.cooling_air_delta_t_k": "K",
        }
    )
    result["selected_architecture"] = {
        "id": "F34A-AIR-OIL-CORE-2026-CONTROLS",
        "engine_core_liquid_coolant_present": False,
        "engine_core_heat_rejection": ["forced_air", "dry_sump_oil"],
        "auxiliary_liquid_scope": (
            ["charge_cooling", "turbo_chra_optional_unresolved"]
            if configuration == "twin_turbo"
            else []
        ),
    }
    result["engine_management"] = {
        "architecture_id": "917_2026_modern_ecu_twin_spark_sequential_efi",
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
    return result


def _validate_f33_forward_schema(
    contract: dict[str, Any], variants: dict[str, dict[str, Any]]
) -> None:
    """Bind F33 ancestry and every F34 axis to the transformed air/oil seed."""

    for configuration, variant in variants.items():
        legacy_forward = variant["forward_solver_input"]
        forward = _f34_base_forward_input(legacy_forward, configuration)
        units = forward.get("unit_registry")
        if not isinstance(units, dict):
            raise ValueError(f"F33 unit registry missing:{configuration}")
        for axis in _active_axes(contract, configuration):
            axis_id = axis["id"]
            target_path = axis["target_path"]
            if axis_id == "fmep_coefficient_scale":
                fmep = forward.get("fmep_model")
                expected_units = {
                    "base_bar": "bar",
                    "mean_piston_speed_linear_bar_per_m_s": "bar/(m/s)",
                    "mean_piston_speed_quadratic_bar_per_m_s2": "bar/(m/s)^2",
                }
                if not isinstance(fmep, dict) or set(fmep) != set(expected_units):
                    raise ValueError(f"F33 FMEP schema mismatch:{configuration}")
                for key, expected_unit in expected_units.items():
                    if not _finite(fmep[key]) or units.get(f"fmep_model.{key}") != expected_unit:
                        raise ValueError(f"F33 FMEP unit/value mismatch:{configuration}:{key}")
                continue
            try:
                value = _get_dotted(forward, target_path)
            except (KeyError, TypeError) as exc:
                raise ValueError(
                    f"F33 axis target missing:{configuration}:{axis_id}:{target_path}"
                ) from exc
            if not _finite(value):
                raise ValueError(f"F33 axis target non-finite:{configuration}:{axis_id}")
            expected_unit = axis["unit"]
            if axis_id == "exhaust_to_manifold_pressure_ratio":
                expected_unit = "Pa_abs"
                if units.get("manifold_pressure_pa_abs") != "Pa_abs":
                    raise ValueError(f"F33 manifold pressure unit mismatch:{configuration}")
            if units.get(target_path) != expected_unit:
                raise ValueError(
                    f"F33 axis unit mismatch:{configuration}:{axis_id}:{units.get(target_path)}"
                )

        frozen = contract["frozen_inputs"]
        frozen_paths = {
            "bore_mm": "bore_mm",
            "stroke_mm": "stroke_mm",
            "cylinder_count": "cylinder_count",
            "fuel_surrogate": "fuel_surrogate",
            "fuel_lhv_j_kg": "fuel_lhv_j_kg",
            "cooling_air_cp_j_kg_k": "thermal_hypotheses.cooling_air_cp_j_kg_k",
            "oil_cp_j_kg_k": "thermal_hypotheses.oil_cp_j_kg_k",
        }
        if configuration == "twin_turbo":
            frozen_paths["charge_coolant_cp_j_kg_k"] = (
                "thermal_hypotheses.charge_coolant_cp_j_kg_k"
            )
        for frozen_key, path in frozen_paths.items():
            if _get_dotted(forward, path) != frozen[frozen_key]:
                raise ValueError(f"F34 frozen input mismatch:{configuration}:{frozen_key}")
        if (
            forward["selected_architecture"]["engine_core_liquid_coolant_present"]
            is not False
            or frozen["engine_core_liquid_coolant_present"] is not False
        ):
            raise ValueError(f"engine core liquid coolant forbidden:{configuration}")
        expected_management = {
            "architecture_id": "917_2026_modern_ecu_twin_spark_sequential_efi",
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
        if forward.get("engine_management") != expected_management:
            raise ValueError(f"F34 engine management lock mismatch:{configuration}")


def _get_dotted(mapping: dict[str, Any], dotted: str) -> Any:
    value: Any = mapping
    for key in dotted.split("."):
        value = value[key]
    return value


def _set_dotted(mapping: dict[str, Any], dotted: str, value: Any) -> None:
    keys = dotted.split(".")
    parent = mapping
    for key in keys[:-1]:
        child = parent[key]
        if not isinstance(child, dict):
            raise ValueError(f"target path is not a mapping: {dotted}")
        parent = child
    parent[keys[-1]] = value


def _center_axis_values(
    axes: list[dict[str, Any]],
    base_forward: dict[str, Any],
) -> list[float]:
    values: list[float] = []
    for axis in axes:
        axis_id = axis["id"]
        if axis_id == "exhaust_to_manifold_pressure_ratio":
            value = float(base_forward["exhaust_pressure_pa_abs"]) / float(base_forward["manifold_pressure_pa_abs"])
        elif axis_id == "fmep_coefficient_scale":
            value = 1.0
        else:
            value = float(_get_dotted(base_forward, axis["target_path"]))
        values.append(value)
    return values


def _scale_axes(
    axes: list[dict[str, Any]],
    configuration: str,
    normalized: list[float],
) -> list[float]:
    if len(axes) != len(normalized):
        raise ValueError("normalized vector length does not match axis count")
    values: list[float] = []
    for axis, coordinate in zip(axes, normalized, strict=True):
        low, high = axis["bounds"][configuration]
        values.append(float(low) + float(coordinate) * (float(high) - float(low)))
    return values


def _forward_input(
    base_forward: dict[str, Any],
    axes: list[dict[str, Any]],
    values: list[float],
) -> dict[str, Any]:
    result = copy.deepcopy(base_forward)
    axis_values = {axis["id"]: float(value) for axis, value in zip(axes, values, strict=True)}
    for axis, value in zip(axes, values, strict=True):
        axis_id = axis["id"]
        if axis_id == "exhaust_to_manifold_pressure_ratio":
            _set_dotted(
                result,
                axis["target_path"],
                axis_values["manifold_pressure_pa_abs"] * float(value),
            )
        elif axis_id == "fmep_coefficient_scale":
            for key, center in base_forward["fmep_model"].items():
                result["fmep_model"][key] = float(center) * float(value)
        else:
            _set_dotted(result, axis["target_path"], float(value))
    return result


def _input_constraint_flags(
    forward: dict[str, Any], configuration: str
) -> list[str]:
    flags: list[str] = []
    thermal = forward["thermal_hypotheses"]
    thermal_sum = (
        float(thermal["head_heat_fraction_of_fuel_power"])
        + float(thermal["cylinder_heat_fraction_of_fuel_power"])
        + float(thermal["base_oil_heat_fraction_of_fuel_power"])
    )
    if not thermal_sum < 0.8:
        flags.append("C-THERMAL-FRACTIONS")
    mean_piston_speed = (
        2.0
        * (float(forward["stroke_mm"]) / 1000.0)
        * float(forward["speed_rpm"])
        / 60.0
    )
    if not mean_piston_speed <= 24.0:
        flags.append("C-MEAN-PISTON-SPEED")
    if configuration == "twin_turbo":
        turbo = forward["turbo_screening_input"]
        pressure_ratio = (
            float(forward["manifold_pressure_pa_abs"])
            + float(turbo["charge_path_loss_pa"])
        ) / float(turbo["compressor_inlet_pressure_pa_abs"])
        if not 1.2 <= pressure_ratio <= 4.0:
            flags.append("C-TURBO-PRESSURE-RATIO")
        if not float(turbo["turbine_outlet_pressure_pa_abs"]) < float(
            forward["exhaust_pressure_pa_abs"]
        ):
            flags.append("C-TURBINE-EXPANSION")
    return flags


def _partition_blocks(
    contract: dict[str, Any], configuration: str, count: int
) -> dict[int, str]:
    block_size = int(contract["dataset_partition"]["design_block_size"])
    if count % block_size:
        raise ValueError("LHS count is not divisible by design block size")
    block_count = count // block_size
    block_ids = list(range(block_count))
    _HashRng(_seed(contract, configuration, "partition")).shuffle(block_ids)
    requested = contract["dataset_partition"][configuration]
    role_blocks = {key: int(value) // block_size for key, value in requested.items()}
    assignment: dict[int, str] = {}
    cursor = 0
    for role in ("train", "validation", "conformal_calibration", "locked_digital_holdout"):
        for block_id in block_ids[cursor : cursor + role_blocks[role]]:
            assignment[block_id] = role
        cursor += role_blocks[role]
    if len(assignment) != block_count:
        raise ValueError("split block assignment is incomplete")
    return assignment


def _make_case(
    *,
    contract: dict[str, Any],
    configuration: str,
    block: str,
    design_index: int,
    axes: list[dict[str, Any]],
    values: list[float],
    base_forward: dict[str, Any],
    future_dataset_role: str,
    design_block_id: str,
    ood_axis_id: str | None = None,
) -> dict[str, Any]:
    variant = EXPECTED_VARIANTS[configuration]
    block_token = {"anchor": "ANCHOR", "morris": "MORRIS", "lhs": "LHS", "ood": "OOD"}[block]
    case_id = f"F34-{variant['short_id']}-{block_token}-{design_index:04d}"
    forward = _forward_input(base_forward, axes, values)
    feature_values = [float(value) for value in values]
    case = {
        "case_id": case_id,
        "variant_id": variant["id"],
        "configuration": configuration,
        "design_block": block,
        "design_index": design_index,
        "design_block_id": design_block_id,
        "solver_campaign_id": "F34-L0-PLANNED",
        "feature_values": feature_values,
        "forward_input_sha256": _canonical_payload_sha256(forward),
        "preflight_input_constraint_flags": _input_constraint_flags(
            forward, configuration
        ),
        "execution_status": "planned_not_executed",
        "source_kind": "planned_classical_simulation",
        "future_dataset_role": future_dataset_role,
        "training_eligible": False,
    }
    if ood_axis_id is not None:
        case["ood_axis_id"] = ood_axis_id
    return case


def _variant_cases(
    contract: dict[str, Any],
    f33_variant: dict[str, Any],
) -> list[dict[str, Any]]:
    configuration = f33_variant["configuration"]
    expected = EXPECTED_VARIANTS[configuration]
    axes = _active_axes(contract, configuration)
    base_forward = _f34_base_forward_input(
        f33_variant["forward_solver_input"], configuration
    )
    cases: list[dict[str, Any]] = []

    center = _center_axis_values(axes, base_forward)
    cases.append(
        _make_case(
            contract=contract,
            configuration=configuration,
            block="anchor",
            design_index=1,
            axes=axes,
            values=center,
            base_forward=base_forward,
            future_dataset_role="anchor_reference_only",
            design_block_id=f"{expected['short_id']}-ANCHOR-0001",
        )
    )

    morris = contract["sampling_plan"]["morris_screening"]
    trajectories = int(morris[configuration]["trajectories"])
    delta = float(morris["step_normalized"])
    morris_index = 0
    for trajectory in range(trajectories):
        rng = _HashRng(_seed(contract, configuration, "morris", str(trajectory)))
        directions = [
            1.0 if (trajectory + axis_index) % 2 == 0 else -1.0
            for axis_index in range(len(axes))
        ]
        normalized = []
        for axis_index, direction in enumerate(directions):
            pair_index = trajectory // 2
            parity = trajectory % 2
            epoch = pair_index // 5
            level_cycle = (
                pair_index
                + axis_index
                + parity * (2 * axis_index + 1)
                + epoch * (3 * axis_index + 2)
            ) % 5
            level_index = level_cycle if direction > 0.0 else level_cycle + 1
            normalized.append(level_index / 5.0)
        order = list(range(len(axes)))
        rng.shuffle(order)
        trajectory_id = f"{expected['short_id']}-MORRIS-T{trajectory + 1:02d}"
        morris_index += 1
        cases.append(
            _make_case(
                contract=contract,
                configuration=configuration,
                block="morris",
                design_index=morris_index,
                axes=axes,
                values=_scale_axes(axes, configuration, normalized),
                base_forward=base_forward,
                future_dataset_role="sensitivity_screening_only",
                design_block_id=trajectory_id,
            )
        )
        for axis_index in order:
            normalized[axis_index] += directions[axis_index] * delta
            morris_index += 1
            cases.append(
                _make_case(
                    contract=contract,
                    configuration=configuration,
                    block="morris",
                    design_index=morris_index,
                    axes=axes,
                    values=_scale_axes(axes, configuration, normalized),
                    base_forward=base_forward,
                    future_dataset_role="sensitivity_screening_only",
                    design_block_id=trajectory_id,
                )
            )
    if morris_index != expected["morris_count"]:
        raise ValueError(f"Morris count mismatch for {configuration}")

    lhs_count = expected["lhs_count"]
    columns: list[list[int]] = []
    for axis in axes:
        permutation = list(range(lhs_count))
        _HashRng(_seed(contract, configuration, "lhs", axis["id"])).shuffle(permutation)
        columns.append(permutation)
    split_blocks = _partition_blocks(contract, configuration, lhs_count)
    block_size = int(contract["dataset_partition"]["design_block_size"])
    for index in range(lhs_count):
        normalized = [(column[index] + 0.5) / lhs_count for column in columns]
        block_id = index // block_size
        role = split_blocks[block_id]
        cases.append(
            _make_case(
                contract=contract,
                configuration=configuration,
                block="lhs",
                design_index=index + 1,
                axes=axes,
                values=_scale_axes(axes, configuration, normalized),
                base_forward=base_forward,
                future_dataset_role=role,
                design_block_id=f"{expected['short_id']}-LHS-B{block_id + 1:03d}",
            )
        )

    ood_count = expected["ood_count"]
    shell = float(contract["sampling_plan"]["ood_challenge"]["shell_fraction_outside_training_bounds"])
    ood_columns: list[list[int]] = []
    for axis in axes:
        permutation = list(range(ood_count))
        _HashRng(_seed(contract, configuration, "ood", axis["id"])).shuffle(permutation)
        ood_columns.append(permutation)
    for index in range(ood_count):
        normalized = [(column[index] + 0.5) / ood_count for column in ood_columns]
        outside_axis = index % len(axes)
        side = (index // len(axes)) % 2
        normalized[outside_axis] = -shell if side == 0 else 1.0 + shell
        cases.append(
            _make_case(
                contract=contract,
                configuration=configuration,
                block="ood",
                design_index=index + 1,
                axes=axes,
                values=_scale_axes(axes, configuration, normalized),
                base_forward=base_forward,
                future_dataset_role="ood_challenge_only",
                design_block_id=f"{expected['short_id']}-OOD-{index + 1:04d}",
                ood_axis_id=axes[outside_axis]["id"],
            )
        )
    return cases


def _assert_manifest_invariants(cases: list[dict[str, Any]]) -> None:
    case_ids = [case["case_id"] for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("duplicate_sample_id")
    input_keys = [(case["variant_id"], case["forward_input_sha256"]) for case in cases]
    if len(input_keys) != len(set(input_keys)):
        duplicate = next(key for key in input_keys if input_keys.count(key) > 1)
        raise ValueError(f"duplicate_doe_input:{duplicate[0]}:{duplicate[1]}")
    if len(cases) != 2570:
        raise ValueError(f"planned case count mismatch: {len(cases)}")
    for case in cases:
        if case["training_eligible"] is not False:
            raise ValueError(f"unexecuted case gained training authority:{case['case_id']}")
        if (
            case["design_block"] != "ood"
            and case["preflight_input_constraint_flags"]
        ):
            raise ValueError(
                "in_domain_preflight_constraint_violation:"
                f"{case['case_id']}:{','.join(case['preflight_input_constraint_flags'])}"
            )


def _build_cases_from_f33(
    contract: dict[str, Any], f33_contract: dict[str, Any]
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Internal pure builder; production provenance is enforced by build_manifest."""

    variants = _index_variants(f33_contract)
    _validate_f33_forward_schema(contract, variants)
    cases: list[dict[str, Any]] = []
    for configuration in ("naturally_aspirated", "twin_turbo"):
        cases.extend(_variant_cases(contract, variants[configuration]))
    _assert_manifest_invariants(cases)
    return variants, cases


def build_manifest(
    contract: dict[str, Any],
    *,
    contract_path: Path = CONTRACT,
    project_root: Path = ROOT,
) -> dict[str, Any]:
    """Build the deterministic F34 case plan from the pinned on-disk parent."""

    errors = validate_contract(contract, project_root=project_root)
    if errors:
        raise ValueError("invalid F34 contract:\n- " + "\n- ".join(errors))
    f33_path = project_root / F33_CONTRACT.relative_to(ROOT)
    if _sha256(f33_path) != EXPECTED_PARENT_HASHES[
        "twins/reference-917-engine/clean-sheet-cycle-thermal-f33.json"
    ]:
        raise ValueError("pinned F33 parent changed after contract validation")
    f33_contract = _read_json(f33_path)
    variants, cases = _build_cases_from_f33(contract, f33_contract)

    by_block: dict[str, int] = {}
    by_configuration: dict[str, int] = {}
    for case in cases:
        by_block[case["design_block"]] = by_block.get(case["design_block"], 0) + 1
        by_configuration[case["configuration"]] = by_configuration.get(case["configuration"], 0) + 1
    lhs_cases = [case for case in cases if case["design_block"] == "lhs"]
    split_counts: dict[str, dict[str, int]] = {configuration: {} for configuration in EXPECTED_VARIANTS}
    group_roles: dict[tuple[str, str], str] = {}
    for case in lhs_cases:
        configuration = case["configuration"]
        role = case["future_dataset_role"]
        split_counts[configuration][role] = split_counts[configuration].get(role, 0) + 1
        group_key = (configuration, case["design_block_id"])
        previous = group_roles.setdefault(group_key, role)
        if previous != role:
            raise ValueError(f"split_group_leakage:{group_key}")
    split_membership = [
        {"case_id": case["case_id"], "future_dataset_role": case["future_dataset_role"]}
        for case in lhs_cases
    ]

    legacy_f33_forward_inputs = {
        configuration: copy.deepcopy(variants[configuration]["forward_solver_input"])
        for configuration in ("naturally_aspirated", "twin_turbo")
    }
    f34_forward_seed_inputs = {
        configuration: _f34_base_forward_input(
            variants[configuration]["forward_solver_input"], configuration
        )
        for configuration in ("naturally_aspirated", "twin_turbo")
    }
    doe_plan_payload = {
        "schema": "F34-air-oil-doe-plan-root-v2",
        "generator": contract["sampling_plan"]["generator"],
        "legacy_f33_forward_inputs_sha256": _canonical_payload_sha256(
            legacy_f33_forward_inputs
        ),
        "f34_air_oil_forward_seed_inputs_sha256": _canonical_payload_sha256(
            f34_forward_seed_inputs
        ),
        "f33_runner_sha256": EXPECTED_PARENT_HASHES["scripts/run_917_cycle_thermal_f33.py"],
        "runtime": contract["runtime"],
        "axis_registry": contract["axis_registry"],
        "constraints": contract["constraints"],
        "sampling_plan": contract["sampling_plan"],
        "dataset_partition": contract["dataset_partition"],
        "feature_schema": contract["feature_schema"],
        "label_schema": contract["label_schema"],
        "ood_policy": contract["ood_policy"],
        "cases": cases,
    }
    preflight_by_constraint: dict[str, list[str]] = {}
    for case in cases:
        for constraint_id in case["preflight_input_constraint_flags"]:
            preflight_by_constraint.setdefault(constraint_id, []).append(case["case_id"])
    technical_gates = {
        "contract_valid": True,
        "doe_plan_valid": True,
        "case_manifest_generated": True,
        "selected_air_oil_architecture_locked": True,
        "modern_controls_contract_valid": True,
        "future_solver_image_available": False,
        "requested_target_scalar_excluded_from_fields": True,
        "full_target_independence_proven": False,
        "split_plan_generated": True,
    }
    manifest = {
        "schema_version": "1.0.0",
        "phase": "F34",
        "status": "deterministic_case_manifest_generated_zero_solver_cases_executed",
        "contract_sha256": _canonical_payload_sha256(contract),
        "contract_file_sha256": _sha256(contract_path),
        "doe_plan_root_sha256": _canonical_payload_sha256(doe_plan_payload),
        "legacy_f33_forward_inputs_sha256": _canonical_payload_sha256(
            legacy_f33_forward_inputs
        ),
        "f34_air_oil_forward_seed_inputs_sha256": _canonical_payload_sha256(
            f34_forward_seed_inputs
        ),
        "generator": {
            "id": contract["sampling_plan"]["generator"],
            "script_path": str(Path(__file__).resolve().relative_to(ROOT)),
            "script_sha256": _sha256(Path(__file__).resolve()),
            "solver_executed": False,
        },
        "runtime": copy.deepcopy(contract["runtime"]),
        "feature_schema": {
            configuration: [
                {"id": axis["id"], "unit": axis["unit"]}
                for axis in _active_axes(contract, configuration)
            ]
            for configuration in ("naturally_aspirated", "twin_turbo")
        },
        "label_schema": copy.deepcopy(contract["label_schema"]),
        "unexecuted_case_policy": {
            "labels_present": False,
            "solver_result_refs_present": False,
            "convergence_claims_present": False,
            "zero_fill_for_missing_results_allowed": False,
        },
        "case_counts": {
            "planned": len(cases),
            "executed": 0,
            "accepted": 0,
            "rejected": 0,
            "by_configuration": by_configuration,
            "by_design_block": by_block,
        },
        "preflight_input_constraints": {
            "evaluated_constraint_ids": [
                "C-THERMAL-FRACTIONS",
                "C-MEAN-PISTON-SPEED",
                "C-TURBO-PRESSURE-RATIO",
                "C-TURBINE-EXPANSION",
            ],
            "output_dependent_constraint_ids_not_evaluated": [
                "C-MASS-IDENTITY",
                "C-POSITIVE-FORWARD-POWER",
            ],
            "in_domain_violation_count": 0,
            "ood_challenge_violation_count": sum(
                len(case["preflight_input_constraint_flags"])
                for case in cases
                if case["design_block"] == "ood"
            ),
            "case_ids_by_constraint": preflight_by_constraint,
        },
        "cases": cases,
        "split_manifest": {
            "assignment_precedes_solver_execution": True,
            "applies_only_to_lhs": True,
            "counts": split_counts,
            "group_count": len(group_roles),
            "group_closed": True,
            "geometry_holdout_present": False,
            "physical_campaign_holdout_present": False,
            "membership_sha256": _canonical_payload_sha256(split_membership),
            "normalization_executed": False,
        },
        "execution_ledger": {
            "planned_not_executed": len(cases),
            "executed": 0,
            "accepted": 0,
            "rejected": 0,
            "case_status_sha256": _canonical_payload_sha256(
                [{"case_id": case["case_id"], "status": case["execution_status"]} for case in cases]
            ),
            "silent_drop_count": 0,
        },
        "authority_boundary": {
            "requested_target_scalar_is_direct_field": False,
            "inverse_sizing_seed_ancestry_present": True,
            "full_target_independence_proven": False,
            "selected_engine_core_cooling": "forced_air_and_dry_sump_oil",
            "engine_core_liquid_coolant_present": False,
            "legacy_f33_liquid_head_result_transfer_authorized": False,
            "electronic_fuel_injection_required": True,
            "electronic_ignition_required": True,
            "modern_controls_response_modeled_in_l0": False,
            "future_solver_image_available": False,
            "doe_plan_generated": True,
            "doe_executed": False,
            "dataset_ready": False,
            "training_authorized": False,
            "physicsnemo_executed": False,
            "omniverse_executed": False,
            "physical_correlation_complete": False,
            "target_power_proven": False,
        },
        "technical_gates": technical_gates,
        "release_gates": copy.deepcopy(contract["release_gates"]),
    }
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=CONTRACT)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--output", type=Path)
    action.add_argument("--check", type=Path)
    args = parser.parse_args(argv)

    try:
        contract = _read_json(args.contract)
        manifest = build_manifest(contract, contract_path=args.contract, project_root=ROOT)
        rendered = _canonical_json(manifest)
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        else:
            if not args.check.is_file():
                raise ValueError(f"tracked manifest missing: {args.check}")
            existing = args.check.read_text(encoding="utf-8")
            if existing != rendered:
                raise ValueError(f"stale F34 manifest: {args.check}")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"F34 DOE error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
