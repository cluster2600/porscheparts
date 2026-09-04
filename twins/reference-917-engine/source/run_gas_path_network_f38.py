#!/usr/bin/env python3
"""Exécute le réseau stationnaire fail-closed F38 des deux variantes 917.

Le calcul ferme des identités numériques à un point F33 déjà exécuté. Il ne
résout ni ondes 1D, ni géométrie de conduit, ni cartes turbo, ni combustion
transitoire. Ces limites sont écrites dans le rapport au même niveau que les
résultats afin d'éviter toute promotion accidentelle en preuve physique.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONTRACT = REPO_ROOT / "twins/reference-917-engine/gas-path-network-f38.json"
DEFAULT_OUTPUT = REPO_ROOT / "work/917-gas-path-network-f38"
MECHANICAL_HP_W = 745.6998715822702
METRIC_PS_W = 735.49875
OUTPUT_MARKER_NAME = ".f38-output.json"
REPORT_NAME = "gas-path-network-f38-report.json"
OUTPUT_OWNER = "porsche-917-gas-path-network-f38"
REPORT_SIGNIFICANT_DIGITS = 12


class F38InputError(ValueError):
    """Erreur déterministe de contrat ou de preuve amont."""


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise F38InputError(f"JSON object required: {path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def finite_number(value: Any, label: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise F38InputError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise F38InputError(f"{label} must be finite")
    if positive and result <= 0.0:
        raise F38InputError(f"{label} must be positive")
    return result


def rounded(value: float) -> float:
    result = float(format(float(value), f".{REPORT_SIGNIFICANT_DIGITS}g"))
    return 0.0 if result == 0.0 else result


def relative_residual(residual: float, scale: float) -> float:
    return abs(residual) / max(abs(scale), 1.0e-30)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise F38InputError(message)


def source_bundle(
    project_root: Path, contract: dict[str, Any]
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    declarations = contract.get("source_evidence")
    require(isinstance(declarations, dict), "source_evidence object required")
    documents: dict[str, dict[str, Any]] = {}
    evidence: dict[str, dict[str, Any]] = {}
    for source_id, declaration in declarations.items():
        require(isinstance(declaration, dict), f"source_evidence.{source_id} invalid")
        relative_path = declaration.get("path")
        expected = declaration.get("expected_sha256")
        require(isinstance(relative_path, str), f"{source_id}.path required")
        require(
            isinstance(expected, str) and len(expected) == 64,
            f"{source_id}.expected_sha256 required",
        )
        path = project_root / relative_path
        require(path.is_file(), f"source missing: {relative_path}")
        actual = sha256(path)
        require(actual == expected, f"source hash mismatch: {source_id}")
        documents[source_id] = load_json(path)
        evidence[source_id] = {
            "path": relative_path,
            "expected_sha256": expected,
            "actual_sha256": actual,
            "hash_verified": True,
        }
    require(len(documents) == 7, "exactly seven hash-bound source documents required")
    return documents, evidence


def validate_contract(contract: dict[str, Any]) -> None:
    require(contract.get("phase") == "F38", "contract.phase must be F38")
    require(contract.get("asset_id") == OUTPUT_OWNER, "contract.asset_id mismatch")
    variants = contract.get("variants")
    require(isinstance(variants, list) and len(variants) == 2, "two variants required")
    by_id = {item.get("variant_id"): item for item in variants if isinstance(item, dict)}
    require(
        set(by_id)
        == {
            "917_2026_flat12_na_candidate",
            "917_2026_flat12_twin_turbo_1600hp_target",
        },
        "unexpected variant set",
    )
    require(by_id["917_2026_flat12_na_candidate"].get("turbocharger_count") == 0, "NA turbo count must be zero")
    require(by_id["917_2026_flat12_twin_turbo_1600hp_target"].get("turbocharger_count") == 2, "turbo count must be two")
    for item in variants:
        require(item.get("bench_geometry_identity_match") is False, "bench identity transfer must stay false")
    release = contract.get("release_gates")
    require(isinstance(release, dict) and release, "release_gates required")
    require(all(value is False for value in release.values()), "contract release gates must all be false")
    authority = contract.get("authority_boundary")
    require(isinstance(authority, dict), "authority_boundary required")
    require(
        authority.get("requested_power_target_used_as_direct_f38_solver_input") is False,
        "direct F38 target input gate must be false",
    )
    require(
        authority.get("requested_power_target_has_indirect_sampling_ancestry") is True,
        "indirect target ancestry must remain explicit",
    )
    require(
        authority.get("inverse_sizing_seed_ancestry_present") is True,
        "inverse-sizing ancestry must remain explicit",
    )
    require(
        authority.get("full_target_independence_proven") is False,
        "full target independence must remain false",
    )
    policy = contract.get("numerical_policy")
    require(isinstance(policy, dict), "numerical_policy required")
    require(
        policy.get("report_significant_digits") == REPORT_SIGNIFICANT_DIGITS,
        f"numerical_policy.report_significant_digits must be {REPORT_SIGNIFICANT_DIGITS}",
    )
    require(policy.get("network_access_required") is False, "network access must not be required")
    require(policy.get("external_api_required") is False, "external API must not be required")
    require(
        policy.get("unsteady_one_dimensional_gas_dynamics_executed") is False,
        "unsteady 1D claim must stay false",
    )
    for key in (
        "mass_relative_tolerance",
        "energy_relative_tolerance",
        "upstream_reproduction_relative_tolerance",
        "shaft_balance_relative_tolerance",
    ):
        tolerance = finite_number(policy.get(key), f"numerical_policy.{key}", positive=True)
        require(tolerance < 1.0e-3, f"numerical_policy.{key} is too loose")


def validate_upstream(documents: dict[str, dict[str, Any]]) -> None:
    f33_contract = documents["cycle_thermal_contract_f33"]
    f33 = documents["cycle_thermal_report_f33"]
    f34 = documents["verification_report_f34"]
    f34_doe = documents["doe_contract_f34"]
    f34a = documents["air_oil_controls_contract_f34a"]
    f34b = documents["air_oil_forward_seeds_f34b"]
    f37 = documents["integrated_bench_contract_f37"]
    require(f33_contract.get("phase") == "F33", "F33 contract phase mismatch")
    require(f33.get("phase") == "F33", "F33 report phase mismatch")
    require(f34.get("phase") == "F34", "F34 report phase mismatch")
    require(f34_doe.get("phase") == "F34", "F34 DOE contract phase mismatch")
    require(f34a.get("phase") == "F34a", "F34a controls phase mismatch")
    require(f34b.get("phase") == "F34b", "F34b seed phase mismatch")
    require(f37.get("phase") == "F37", "F37 bench phase mismatch")
    require(f33.get("release_gates", {}).get("target_power_proven") is False, "F33 target power gate must be false")
    require(f33.get("release_gates", {}).get("turbo_match_validated") is False, "F33 turbo gate must be false")
    require(f33.get("model_scope", {}).get("physical_correlation_complete") is False, "F33 correlation gate must be false")
    require(f34.get("cycle_cross_verification", {}).get("target_power_proven") is False, "F34 target power gate must be false")
    require(f34.get("release_gates", {}).get("physical_engine_dyno_correlated") is False, "F34 dyno gate must be false")
    require(
        f34.get("release_gates", {}).get("full_3d_intake_exhaust_cfd_cross_validated") is False,
        "F34 intake/exhaust CFD gate must be false",
    )
    require(f34a.get("release_gates", {}).get("boost_control_validated") is False, "F34a boost control gate must be false")
    require(f34a.get("release_gates", {}).get("target_power_proven") is False, "F34a target power gate must be false")
    require(f34b.get("canonical_doe_cases_executed") == 0, "F34b canonical solver case count must be zero")
    require(f34b.get("release_gates", {}).get("one_dimensional_model_validated") is False, "F34b 1D model gate must be false")
    require(f34b.get("physical_gates", {}).get("target_power_proven") is False, "F34b target power gate must be false")
    require(
        f34a.get("decision", {}).get("selected_core_thermal_architecture")
        == "strict_forced_air_and_dry_sump_oil_only",
        "F34a strict air/oil core decision required",
    )
    require(f34a.get("engine_core_boundary", {}).get("core_liquid_coolant_loop_present") is False, "F34a core liquid loop must be absent")
    require(f34a.get("engine_core_boundary", {}).get("core_to_auxiliary_liquid_cross_connection_allowed") is False, "F34a core/auxiliary cross connection must be forbidden")
    require(f37.get("output_policy", {}).get("physics_schema_authored") is False, "F37 physics schema gate must be false")
    require(f37.get("output_policy", {}).get("cfd_volume_authored") is False, "F37 CFD volume gate must be false")
    require(f37.get("release_gates", {}).get("performance_1600_hp_claim_authorized") is False, "F37 power gate must be false")
    require(f33.get("model_scope", {}).get("maximum_model_dimension") == "0D", "F33 model dimension must be 0D")
    require(f33.get("model_scope", {}).get("one_dimensional_gas_dynamics_executed") is False, "F33 1D gas dynamics gate must be false")
    target_authority = f34_doe.get("authority_boundary")
    require(isinstance(target_authority, dict), "F34 target authority boundary missing")
    require(
        target_authority.get("requested_power_target_scalar_is_direct_doe_input") is False,
        "F34 direct target input gate must be false",
    )
    require(
        target_authority.get("requested_power_target_has_indirect_sampling_ancestry") is True,
        "F34 indirect target ancestry must remain explicit",
    )
    require(
        target_authority.get("inverse_sizing_seed_ancestry_present") is True,
        "F34 inverse-sizing ancestry must remain explicit",
    )
    require(
        target_authority.get("full_target_independence_proven") is False,
        "F34 full target independence must remain false",
    )


def target_ancestry(documents: dict[str, dict[str, Any]]) -> dict[str, Any]:
    authority = documents["doe_contract_f34"]["authority_boundary"]
    return {
        "requested_power_target_used_as_direct_f38_solver_input": False,
        "requested_power_target_has_indirect_sampling_ancestry": bool(
            authority["requested_power_target_has_indirect_sampling_ancestry"]
        ),
        "inverse_sizing_seed_ancestry_present": bool(
            authority["inverse_sizing_seed_ancestry_present"]
        ),
        "full_target_independence_proven": False,
        "scope": "absence_of_direct_target_input_in_f38_only",
    }


def f33_inputs_by_variant(contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    values = contract.get("engine_variants")
    require(isinstance(values, list), "F33 engine_variants required")
    result: dict[str, dict[str, Any]] = {}
    for item in values:
        require(isinstance(item, dict), "F33 engine variant invalid")
        variant_id = item.get("id")
        forward = item.get("forward_solver_input")
        require(isinstance(variant_id, str) and isinstance(forward, dict), "F33 forward input missing")
        result[variant_id] = forward
    return result


def f33_results_by_variant(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    values = report.get("forward_predictions")
    require(isinstance(values, list), "F33 forward_predictions required")
    result: dict[str, dict[str, Any]] = {}
    for item in values:
        require(isinstance(item, dict), "F33 forward prediction invalid")
        variant_id = item.get("variant_id")
        prediction = item.get("forward_prediction")
        require(isinstance(variant_id, str) and isinstance(prediction, dict), "F33 prediction payload missing")
        result[variant_id] = prediction
    return result


def solve_fraction_bisection(
    compressor_power_w: float,
    full_flow_turbine_power_w: float,
    policy: dict[str, Any],
) -> dict[str, Any]:
    settings = policy["wastegate_bisection"]
    lower = finite_number(settings["lower_turbine_flow_fraction"], "bisection.lower")
    upper = finite_number(settings["upper_turbine_flow_fraction"], "bisection.upper")
    maximum_iterations = int(settings["maximum_iterations"])
    require(0.0 <= lower < upper <= 1.0, "invalid bisection bracket")
    require(maximum_iterations >= 16, "bisection iteration budget too small")
    tolerance = finite_number(policy["shaft_balance_relative_tolerance"], "shaft tolerance", positive=True)
    capacity = full_flow_turbine_power_w >= compressor_power_w
    if not capacity:
        return {
            "capacity_available": False,
            "converged": False,
            "iterations": 0,
            "turbine_flow_fraction": None,
            "wastegate_bypass_fraction": None,
            "shaft_power_residual_w": rounded(full_flow_turbine_power_w - compressor_power_w),
            "relative_shaft_power_residual": rounded(
                relative_residual(full_flow_turbine_power_w - compressor_power_w, compressor_power_w)
            ),
        }
    iterations = 0
    midpoint = (lower + upper) / 2.0
    residual = midpoint * full_flow_turbine_power_w - compressor_power_w
    while iterations < maximum_iterations:
        iterations += 1
        midpoint = (lower + upper) / 2.0
        residual = midpoint * full_flow_turbine_power_w - compressor_power_w
        if relative_residual(residual, compressor_power_w) <= tolerance:
            break
        if residual < 0.0:
            lower = midpoint
        else:
            upper = midpoint
    converged = relative_residual(residual, compressor_power_w) <= tolerance
    return {
        "capacity_available": True,
        "converged": converged,
        "iterations": iterations,
        "turbine_flow_fraction": rounded(midpoint),
        "wastegate_bypass_fraction": rounded(1.0 - midpoint),
        "shaft_power_residual_w": rounded(residual),
        "relative_shaft_power_residual": rounded(relative_residual(residual, compressor_power_w)),
    }


def engine_accounting(prediction: dict[str, Any], tolerance: float) -> dict[str, Any]:
    power = prediction.get("work_and_power")
    thermal = prediction.get("thermal_network_screen")
    require(isinstance(power, dict) and isinstance(thermal, dict), "F33 power/thermal payload missing")
    fuel_power = finite_number(power.get("fuel_power_w"), "fuel_power_w", positive=True)
    brake_power = finite_number(power.get("forward_predicted_brake_power_w"), "brake_power_w", positive=True)
    loads = thermal.get("loads_w")
    require(isinstance(loads, dict), "thermal loads missing")
    declared_loads = {
        key: finite_number(value, f"thermal load {key}", positive=True)
        for key, value in loads.items()
        if value is not None
    }
    declared_total = sum(declared_loads.values())
    complement = fuel_power - brake_power - declared_total
    require(complement >= 0.0, "declared energy sinks exceed fuel power")
    residual = fuel_power - brake_power - declared_total - complement
    complement_constructed = relative_residual(residual, fuel_power) <= tolerance
    require(complement_constructed, "constructed energy complement did not close arithmetically")
    return {
        "fuel_power_w": rounded(fuel_power),
        "brake_power_w": rounded(brake_power),
        "brake_power_mechanical_hp": rounded(brake_power / MECHANICAL_HP_W),
        "brake_power_metric_ps": rounded(brake_power / METRIC_PS_W),
        "declared_thermal_loads_w": {key: rounded(value) for key, value in declared_loads.items()},
        "declared_thermal_load_total_w": rounded(declared_total),
        "unresolved_exhaust_wall_and_model_residual_w": rounded(complement),
        "constructed_complement_residual_w": rounded(residual),
        "nonnegative_arithmetic_complement_constructed": complement_constructed,
        "accounting_method": "unresolved_complement_by_difference_not_independent_energy_balance",
        "thermal_load_authority": "legacy_F33_hybrid_head_hypotheses_preserved_for_accounting_not_selected_by_F34a",
        "full_engine_energy_balance_validated": False,
    }


def solve_na(
    variant: dict[str, Any],
    forward: dict[str, Any],
    prediction: dict[str, Any],
    topology: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    require(int(forward.get("turbocharger_count", -1)) == 0, "NA forward turbo count mismatch")
    require(prediction.get("turbo_screen") is None, "NA prediction must not have a turbo screen")
    charge = prediction.get("trapped_charge")
    require(isinstance(charge, dict), "NA trapped charge missing")
    air = finite_number(charge.get("air_mass_flow_kg_s"), "NA air flow", positive=True)
    fuel = finite_number(charge.get("fuel_mass_flow_kg_s"), "NA fuel flow", positive=True)
    exhaust = finite_number(charge.get("exhaust_mass_flow_identity_kg_s"), "NA exhaust flow", positive=True)
    mass_residual = exhaust - air - fuel
    mass_relative = relative_residual(mass_residual, exhaust)
    mass_closed = mass_relative <= finite_number(policy["mass_relative_tolerance"], "mass tolerance", positive=True)
    require(mass_closed, "NA mass identity did not close")
    manifold_p = finite_number(forward.get("manifold_pressure_pa_abs"), "NA manifold pressure", positive=True)
    manifold_t = finite_number(forward.get("manifold_temperature_k"), "NA manifold temperature", positive=True)
    exhaust_p = finite_number(forward.get("exhaust_pressure_pa_abs"), "NA exhaust pressure", positive=True)
    nodes = [
        {"id": "bench_ambient", "pressure_pa_abs": None, "temperature_k": None, "classification": "boundary_state_not_provided_by_f33"},
        {"id": "intake_plenum", "pressure_pa_abs": rounded(manifold_p), "temperature_k": rounded(manifold_t), "mass_flow_kg_s": rounded(air)},
        {"id": "cylinder_control_volume", "air_mass_flow_kg_s": rounded(air), "fuel_mass_flow_kg_s": rounded(fuel), "exhaust_mass_flow_kg_s": rounded(exhaust)},
        {"id": "exhaust_collector", "pressure_pa_abs": rounded(exhaust_p), "temperature_k": None, "mass_flow_kg_s": rounded(exhaust), "classification": "temperature_not_provided_by_f33"},
        {"id": "bench_extraction", "pressure_pa_abs": None, "temperature_k": None, "mass_flow_kg_s": rounded(exhaust), "classification": "boundary_state_not_provided_by_f33"},
    ]
    edges = [
        {"id": "ambient_to_plenum", "mass_flow_kg_s": rounded(air), "pressure_drop_solved": False},
        {"id": "plenum_to_cylinders", "mass_flow_kg_s": rounded(air)},
        {"id": "fuel_rail_to_cylinders", "mass_flow_kg_s": rounded(fuel)},
        {"id": "cylinders_to_collector", "mass_flow_kg_s": rounded(exhaust)},
        {"id": "collector_to_extraction", "mass_flow_kg_s": rounded(exhaust), "pressure_drop_solved": False},
    ]
    require({node["id"] for node in nodes} == set(topology["nodes"]), "NA node topology mismatch")
    require({edge["id"] for edge in edges} == set(topology["edges"]), "NA edge topology mismatch")
    return {
        "variant_id": variant["variant_id"],
        "bench_variant_id": variant["bench_variant_id"],
        "bench_geometry_identity_match": False,
        "configuration": "naturally_aspirated",
        "operating_point": {
            "speed_rpm": rounded(finite_number(forward.get("speed_rpm"), "NA speed", positive=True)),
            "classification": "single_non_correlated_f33_forward_screening_point",
        },
        "nodes": nodes,
        "edges": edges,
        "mass_balance": {
            "air_mass_flow_kg_s": rounded(air),
            "fuel_mass_flow_kg_s": rounded(fuel),
            "exhaust_mass_flow_kg_s": rounded(exhaust),
            "residual_kg_s": rounded(mass_residual),
            "relative_residual": rounded(mass_relative),
            "numerical_identity_closed": True,
            "physical_mass_balance_validated": False,
        },
        "engine_energy_accounting": engine_accounting(
            prediction, finite_number(policy["energy_relative_tolerance"], "energy tolerance", positive=True)
        ),
        "turbo_system": None,
        "target_comparison": {
            "target_power_mechanical_hp": None,
            "forward_predicted_mechanical_hp": rounded(
                finite_number(prediction["work_and_power"]["forward_predicted_mechanical_hp"], "NA power", positive=True)
            ),
            "forward_predicted_metric_ps": rounded(
                finite_number(
                    prediction["work_and_power"]["forward_predicted_metric_ps"],
                    "NA metric power",
                    positive=True,
                )
            ),
            "power_units": "mechanical_hp_and_metric_PS_are_distinct",
            "target_power_proven": False,
        },
    }


def solve_turbo(
    variant: dict[str, Any],
    forward: dict[str, Any],
    prediction: dict[str, Any],
    topology: dict[str, Any],
    policy: dict[str, Any],
    target_history: dict[str, Any],
) -> dict[str, Any]:
    turbo_count = int(forward.get("turbocharger_count", -1))
    require(turbo_count == 2, "turbo forward count must be two")
    charge = prediction.get("trapped_charge")
    upstream_turbo = prediction.get("turbo_screen")
    turbo = forward.get("turbo_screening_input")
    require(isinstance(charge, dict) and isinstance(upstream_turbo, dict) and isinstance(turbo, dict), "turbo source payload missing")
    for key in ("compressor_map_digitized", "turbine_map_digitized", "map_interpolation_executed", "turbo_match_validated"):
        require(upstream_turbo.get(key) is False, f"upstream turbo gate {key} must be false")
    air = finite_number(charge.get("air_mass_flow_kg_s"), "turbo air flow", positive=True)
    fuel = finite_number(charge.get("fuel_mass_flow_kg_s"), "turbo fuel flow", positive=True)
    exhaust = finite_number(charge.get("exhaust_mass_flow_identity_kg_s"), "turbo exhaust flow", positive=True)
    mass_residual = exhaust - air - fuel
    mass_relative = relative_residual(mass_residual, exhaust)
    require(mass_relative <= finite_number(policy["mass_relative_tolerance"], "mass tolerance", positive=True), "turbo mass identity did not close")

    p1 = finite_number(turbo.get("compressor_inlet_pressure_pa_abs"), "compressor inlet pressure", positive=True)
    t1 = finite_number(turbo.get("compressor_inlet_temperature_k"), "compressor inlet temperature", positive=True)
    manifold_p = finite_number(forward.get("manifold_pressure_pa_abs"), "manifold pressure", positive=True)
    manifold_t = finite_number(forward.get("manifold_temperature_k"), "manifold temperature", positive=True)
    charge_loss = finite_number(turbo.get("charge_path_loss_pa"), "charge path loss", positive=True)
    p2 = manifold_p + charge_loss
    pressure_ratio = p2 / p1
    require(pressure_ratio > 1.0, "compressor pressure ratio must exceed one")
    gamma = finite_number(turbo.get("compressor_gas_gamma"), "compressor gamma", positive=True)
    cp = finite_number(turbo.get("compressor_gas_cp_j_kg_k"), "compressor cp", positive=True)
    eta_c = finite_number(turbo.get("compressor_isentropic_efficiency"), "compressor efficiency", positive=True)
    require(1.0 < gamma < 2.0 and eta_c <= 1.0, "invalid compressor gas properties")
    t2s = t1 * pressure_ratio ** ((gamma - 1.0) / gamma)
    t2 = t1 + (t2s - t1) / eta_c
    per_turbo_air = air / turbo_count
    compressor_power_per_turbo = per_turbo_air * cp * (t2 - t1)
    compressor_power_total = compressor_power_per_turbo * turbo_count
    cooler_heat = air * cp * (t2 - manifold_t)
    require(cooler_heat > 0.0, "charge cooler heat must be positive")
    cooler_residual = cooler_heat - air * cp * (t2 - manifold_t)
    cooler_duty_constructed = relative_residual(cooler_residual, cooler_heat) <= finite_number(
        policy["energy_relative_tolerance"], "energy tolerance", positive=True
    )
    require(cooler_duty_constructed, "constructed charge-cooler duty did not close arithmetically")

    turbine_inlet_p = finite_number(forward.get("exhaust_pressure_pa_abs"), "turbine inlet pressure", positive=True)
    turbine_outlet_p = finite_number(turbo.get("turbine_outlet_pressure_pa_abs"), "turbine outlet pressure", positive=True)
    require(turbine_inlet_p > turbine_outlet_p, "turbine pressure expansion required")
    turbine_inlet_t = finite_number(turbo.get("turbine_inlet_temperature_k"), "turbine inlet temperature", positive=True)
    turbine_gamma = finite_number(turbo.get("exhaust_gas_gamma"), "turbine gamma", positive=True)
    turbine_cp = finite_number(turbo.get("exhaust_gas_cp_j_kg_k"), "turbine cp", positive=True)
    eta_t = finite_number(turbo.get("turbine_isentropic_efficiency"), "turbine efficiency", positive=True)
    eta_m = finite_number(turbo.get("turbo_mechanical_efficiency"), "turbo mechanical efficiency", positive=True)
    require(1.0 < turbine_gamma < 2.0 and eta_t <= 1.0 and eta_m <= 1.0, "invalid turbine properties")
    expansion = 1.0 - (turbine_outlet_p / turbine_inlet_p) ** ((turbine_gamma - 1.0) / turbine_gamma)
    per_turbo_exhaust = exhaust / turbo_count
    full_flow_turbine_gas_power = (
        per_turbo_exhaust * turbine_cp * turbine_inlet_t * eta_t * expansion
    )
    full_flow_turbine_shaft_power = full_flow_turbine_gas_power * eta_m
    turbine_outlet_t = turbine_inlet_t * (1.0 - eta_t * expansion)
    shaft = solve_fraction_bisection(
        compressor_power_per_turbo, full_flow_turbine_shaft_power, policy
    )
    require(shaft["converged"] is True, "baseline turbo shaft balance did not converge")
    turbine_fraction = finite_number(shaft["turbine_flow_fraction"], "turbine flow fraction", positive=True)
    bypass_fraction = finite_number(shaft["wastegate_bypass_fraction"], "wastegate fraction")
    turbine_flow_per_side = per_turbo_exhaust * turbine_fraction
    bypass_flow_per_side = per_turbo_exhaust * bypass_fraction
    selected_turbine_gas_power_total = 2.0 * turbine_fraction * full_flow_turbine_gas_power
    selected_turbine_shaft_power_total = (
        2.0 * turbine_fraction * full_flow_turbine_shaft_power
    )
    turbo_mechanical_loss_total = (
        selected_turbine_gas_power_total - selected_turbine_shaft_power_total
    )
    require(turbo_mechanical_loss_total >= 0.0, "turbo mechanical loss must be non-negative")
    mixed_exhaust_t = (
        turbine_flow_per_side * turbine_outlet_t + bypass_flow_per_side * turbine_inlet_t
    ) / per_turbo_exhaust

    reference_tolerance = finite_number(policy["upstream_reproduction_relative_tolerance"], "upstream tolerance", positive=True)
    comparisons = {
        "compressor_pressure_ratio": (pressure_ratio, upstream_turbo.get("compressor_pressure_ratio")),
        "compressor_outlet_temperature_k": (t2, upstream_turbo.get("compressor_outlet_temperature_k")),
        "compressor_power_total_w": (compressor_power_total, upstream_turbo.get("compressor_power_total_w")),
        "charge_cooler_heat_rejection_w": (cooler_heat, upstream_turbo.get("charge_cooler_heat_rejection_w")),
        "turbine_shaft_power_full_flow_per_turbo_w": (
            full_flow_turbine_shaft_power,
            upstream_turbo.get("turbine_power_full_flow_per_turbo_w"),
        ),
    }
    reproduced: dict[str, Any] = {}
    for name, (calculated, source_value) in comparisons.items():
        source_number = finite_number(source_value, f"upstream {name}", positive=True)
        delta = calculated - source_number
        relative = relative_residual(delta, source_number)
        require(relative <= reference_tolerance, f"F33 reproduction failed: {name}")
        reproduced[name] = {
            "calculated": rounded(calculated),
            "upstream": rounded(source_number),
            "relative_difference": rounded(relative),
            "within_tolerance": True,
        }

    corrected_reference_t = finite_number(turbo.get("corrected_flow_reference_temperature_k"), "corrected reference temperature", positive=True)
    corrected_reference_p = finite_number(turbo.get("corrected_flow_reference_pressure_pa_abs"), "corrected reference pressure", positive=True)
    corrected_flow = per_turbo_air * math.sqrt(t1 / corrected_reference_t) / (p1 / corrected_reference_p)
    nodes = [
        {"id": "bench_ambient", "pressure_pa_abs": rounded(p1), "temperature_k": rounded(t1), "classification": "F33_compressor_inlet_hypothesis"},
        {"id": "compressor_inlet_left", "pressure_pa_abs": rounded(p1), "temperature_k": rounded(t1), "mass_flow_kg_s": rounded(per_turbo_air)},
        {"id": "compressor_inlet_right", "pressure_pa_abs": rounded(p1), "temperature_k": rounded(t1), "mass_flow_kg_s": rounded(per_turbo_air)},
        {"id": "compressor_outlet_left", "pressure_pa_abs": rounded(p2), "temperature_k": rounded(t2), "mass_flow_kg_s": rounded(per_turbo_air)},
        {"id": "compressor_outlet_right", "pressure_pa_abs": rounded(p2), "temperature_k": rounded(t2), "mass_flow_kg_s": rounded(per_turbo_air)},
        {"id": "charge_cooler_outlet", "pressure_pa_abs": rounded(manifold_p), "temperature_k": rounded(manifold_t), "mass_flow_kg_s": rounded(air)},
        {"id": "charge_plenum", "pressure_pa_abs": rounded(manifold_p), "temperature_k": rounded(manifold_t), "mass_flow_kg_s": rounded(air)},
        {"id": "cylinder_control_volume", "air_mass_flow_kg_s": rounded(air), "fuel_mass_flow_kg_s": rounded(fuel), "exhaust_mass_flow_kg_s": rounded(exhaust)},
        {"id": "exhaust_collector_left", "pressure_pa_abs": rounded(turbine_inlet_p), "temperature_k": rounded(turbine_inlet_t), "mass_flow_kg_s": rounded(per_turbo_exhaust)},
        {"id": "exhaust_collector_right", "pressure_pa_abs": rounded(turbine_inlet_p), "temperature_k": rounded(turbine_inlet_t), "mass_flow_kg_s": rounded(per_turbo_exhaust)},
        {"id": "turbine_outlet_left", "pressure_pa_abs": rounded(turbine_outlet_p), "temperature_k": rounded(turbine_outlet_t), "mass_flow_kg_s": rounded(turbine_flow_per_side)},
        {"id": "turbine_outlet_right", "pressure_pa_abs": rounded(turbine_outlet_p), "temperature_k": rounded(turbine_outlet_t), "mass_flow_kg_s": rounded(turbine_flow_per_side)},
        {"id": "wastegate_bypass_left", "pressure_pa_abs": rounded(turbine_outlet_p), "temperature_k": rounded(turbine_inlet_t), "mass_flow_kg_s": rounded(bypass_flow_per_side)},
        {"id": "wastegate_bypass_right", "pressure_pa_abs": rounded(turbine_outlet_p), "temperature_k": rounded(turbine_inlet_t), "mass_flow_kg_s": rounded(bypass_flow_per_side)},
        {"id": "bench_extraction", "pressure_pa_abs": rounded(turbine_outlet_p), "temperature_k": rounded(mixed_exhaust_t), "mass_flow_kg_s": rounded(exhaust)},
    ]
    edges = [
        {"id": "ambient_to_compressors", "mass_flow_kg_s": rounded(air)},
        {"id": "compressors_to_charge_cooler", "mass_flow_kg_s": rounded(air), "shaft_power_w": rounded(compressor_power_total)},
        {"id": "charge_cooler_to_plenum", "mass_flow_kg_s": rounded(air), "heat_rejection_w": rounded(cooler_heat)},
        {"id": "plenum_to_cylinders", "mass_flow_kg_s": rounded(air)},
        {"id": "fuel_rail_to_cylinders", "mass_flow_kg_s": rounded(fuel)},
        {"id": "cylinders_to_collectors", "mass_flow_kg_s": rounded(exhaust)},
        {"id": "collectors_to_turbines", "mass_flow_kg_s": rounded(2.0 * turbine_flow_per_side)},
        {"id": "collectors_to_wastegates", "mass_flow_kg_s": rounded(2.0 * bypass_flow_per_side)},
        {"id": "turbines_to_extraction", "mass_flow_kg_s": rounded(2.0 * turbine_flow_per_side)},
        {"id": "wastegates_to_extraction", "mass_flow_kg_s": rounded(2.0 * bypass_flow_per_side)},
    ]
    require({node["id"] for node in nodes} == set(topology["nodes"]), "turbo node topology mismatch")
    require({edge["id"] for edge in edges} == set(topology["edges"]), "turbo edge topology mismatch")
    predicted_hp = finite_number(prediction["work_and_power"]["forward_predicted_mechanical_hp"], "turbo power", positive=True)
    target_hp = finite_number(variant.get("target_power_mechanical_hp"), "target power", positive=True)
    return {
        "variant_id": variant["variant_id"],
        "bench_variant_id": variant["bench_variant_id"],
        "bench_geometry_identity_match": False,
        "configuration": "twin_turbo",
        "operating_point": {
            "speed_rpm": rounded(finite_number(forward.get("speed_rpm"), "turbo speed", positive=True)),
            "classification": "single_non_correlated_f33_forward_screening_point",
        },
        "nodes": nodes,
        "edges": edges,
        "mass_balance": {
            "air_mass_flow_kg_s": rounded(air),
            "fuel_mass_flow_kg_s": rounded(fuel),
            "exhaust_mass_flow_kg_s": rounded(exhaust),
            "residual_kg_s": rounded(mass_residual),
            "relative_residual": rounded(mass_relative),
            "numerical_identity_closed": True,
            "physical_mass_balance_validated": False,
        },
        "charge_cooler_required_duty": {
            "compressor_inlet_temperature_k": rounded(t1),
            "compressor_outlet_temperature_k": rounded(t2),
            "charge_cooler_outlet_temperature_k": rounded(manifold_t),
            "required_charge_cooler_heat_rejection_w": rounded(cooler_heat),
            "constructed_duty_residual_w": rounded(cooler_residual),
            "required_duty_computed_from_prescribed_states": cooler_duty_constructed,
            "independent_charge_enthalpy_balance_validated": False,
            "heat_exchanger_validated": False,
        },
        "engine_energy_accounting": engine_accounting(
            prediction, finite_number(policy["energy_relative_tolerance"], "energy tolerance", positive=True)
        ),
        "turbo_system": {
            "candidate_model": upstream_turbo.get("candidate_model"),
            "candidate_name_is_map_evidence": False,
            "turbocharger_count": 2,
            "compressor_pressure_ratio": rounded(pressure_ratio),
            "corrected_air_mass_flow_per_turbo_kg_s": rounded(corrected_flow),
            "compressor_power_per_turbo_w": rounded(compressor_power_per_turbo),
            "compressor_power_total_w": rounded(compressor_power_total),
            "compressor_fluid_power_total_w": rounded(compressor_power_total),
            "turbine_gas_power_full_flow_per_turbo_w": rounded(full_flow_turbine_gas_power),
            "turbine_shaft_power_full_flow_per_turbo_w": rounded(full_flow_turbine_shaft_power),
            "turbine_gas_power_selected_total_w": rounded(selected_turbine_gas_power_total),
            "turbine_shaft_power_selected_total_w": rounded(selected_turbine_shaft_power_total),
            "turbo_mechanical_loss_total_w": rounded(turbo_mechanical_loss_total),
            "turbo_mechanical_loss_thermal_destination": None,
            "turbo_mechanical_loss_destination_known": False,
            "chra_thermal_model_executed": False,
            "turbine_outlet_temperature_k": rounded(turbine_outlet_t),
            "steady_shaft_balance": shaft,
            "turbine_mass_flow_per_side_kg_s": rounded(turbine_flow_per_side),
            "wastegate_mass_flow_per_side_kg_s": rounded(bypass_flow_per_side),
            "upstream_reproduction": reproduced,
            "compressor_map_digitized": False,
            "turbine_map_digitized": False,
            "map_interpolation_executed": False,
            "compressor_map_containment_validated": False,
            "turbine_map_containment_validated": False,
            "rotor_speed_calculated": False,
            "transient_rotor_dynamics_executed": False,
            "turbo_match_validated": False,
            "independent_model_cross_check": False,
            "classification": "steady_inverse_wastegate_shaft_identity_not_map_match",
        },
        "target_comparison": {
            "target_power_mechanical_hp": rounded(target_hp),
            "target_power_metric_ps": rounded(target_hp * MECHANICAL_HP_W / METRIC_PS_W),
            "target_unit": "mechanical_hp_not_metric_PS_or_ch",
            "forward_predicted_mechanical_hp": rounded(predicted_hp),
            "forward_predicted_metric_ps": rounded(
                finite_number(
                    prediction["work_and_power"]["forward_predicted_metric_ps"],
                    "turbo metric power",
                    positive=True,
                )
            ),
            "relative_difference": rounded(abs(predicted_hp - target_hp) / target_hp),
            "numerically_within_one_percent_of_requirement": abs(predicted_hp - target_hp) / target_hp <= 0.01,
            **target_history,
            "target_power_proven": False,
        },
    }


def build_report(
    project_root: Path,
    contract_path: Path,
    contract: dict[str, Any],
) -> dict[str, Any]:
    validate_contract(contract)
    documents, evidence = source_bundle(project_root, contract)
    validate_upstream(documents)
    forward_inputs = f33_inputs_by_variant(documents["cycle_thermal_contract_f33"])
    predictions = f33_results_by_variant(documents["cycle_thermal_report_f33"])
    topology = contract["station_topology"]
    policy = contract["numerical_policy"]
    target_history = target_ancestry(documents)
    results: list[dict[str, Any]] = []
    for variant in contract["variants"]:
        variant_id = variant["variant_id"]
        require(variant_id in forward_inputs and variant_id in predictions, f"variant missing upstream: {variant_id}")
        if variant["configuration"] == "naturally_aspirated":
            result = solve_na(variant, forward_inputs[variant_id], predictions[variant_id], topology["naturally_aspirated"], policy)
        elif variant["configuration"] == "twin_turbo":
            result = solve_turbo(
                variant,
                forward_inputs[variant_id],
                predictions[variant_id],
                topology["twin_turbo"],
                policy,
                target_history,
            )
        else:
            raise F38InputError(f"unsupported configuration: {variant['configuration']}")
        results.append(result)
    turbo_result = next(item for item in results if item["configuration"] == "twin_turbo")
    all_mass_closed = all(item["mass_balance"]["numerical_identity_closed"] for item in results)
    all_energy_complements_constructed = all(
        item["engine_energy_accounting"][
            "nonnegative_arithmetic_complement_constructed"
        ]
        for item in results
    )
    report = {
        "schema_version": "1.0.0",
        "phase": "F38",
        "asset_id": contract["asset_id"],
        "status": "steady_gas_path_accounting_executed_prescribed_duties_and_shaft_identity_closed_physical_validation_blocked",
        "contract_path": str(contract_path.relative_to(project_root)),
        "contract_sha256": sha256(contract_path),
        "source_evidence": evidence,
        "runtime": {
            "implementation": "python_standard_library",
            "network_access_used": False,
            "external_api_used": False,
            "gpu_used": False,
            "deterministic": True,
        },
        "model_scope": {
            "steady_station_network_executed": True,
            "unsteady_one_dimensional_gas_dynamics_executed": False,
            "duct_geometry_or_wave_action_solved": False,
            "moving_valve_or_piston_cfd_executed": False,
            "independent_model_cross_check": False,
            "physical_correlation_complete": False,
        },
        "target_independence": target_history,
        "thermal_architecture_authority": {
            "source": "F34a",
            "engine_core": "strict_forced_air_and_dry_sump_oil_only",
            "engine_core_liquid_coolant_loop_present": False,
            "auxiliary_liquid_isolated_from_engine_core": True,
            "auxiliary_liquid_allowed_consumers": ["charge_cooling", "turbo_chra"],
            "forced_air_network_solved": False,
            "dry_sump_oil_network_solved": False,
            "physically_validated": False,
        },
        "unit_registry": contract["unit_registry"],
        "variant_count": len(results),
        "variants": results,
        "technical_gates": {
            "source_hashes_verified": True,
            "two_variant_topology_executed": len(results) == 2,
            "upstream_mass_identities_rechecked": all_mass_closed,
            "nonnegative_energy_complements_constructed": all_energy_complements_constructed,
            "charge_cooler_required_duty_computed_from_prescribed_states": turbo_result[
                "charge_cooler_required_duty"
            ]["required_duty_computed_from_prescribed_states"],
            "steady_turbo_shaft_identity_closed": turbo_result["turbo_system"]["steady_shaft_balance"]["converged"],
            "f33_turbo_algebra_subset_recomputed_from_same_inputs": all(
                item["within_tolerance"]
                for item in turbo_result["turbo_system"]["upstream_reproduction"].values()
            ),
        },
        "release_gates": {
            "full_engine_energy_balance_validated": False,
            "unsteady_one_dimensional_gas_dynamics_validated": False,
            "compressor_map_containment_validated": False,
            "turbine_map_containment_validated": False,
            "turbo_rotor_transient_validated": False,
            "combustion_and_knock_validated": False,
            "physical_engine_dyno_correlated": False,
            "target_power_proven": False,
            "engine_start_authorized": False,
            "manufacturing_authorized": False,
        },
        "required_next_evidence": [
            "licensed_digitized_compressor_maps_with_speed_efficiency_and_choke_surge_lines",
            "licensed_digitized_turbine_maps_with_reduced_flow_and_efficiency",
            "turbo_rotor_inertia_bearing_friction_and_speed_limits",
            "turbo_bearing_and_chra_thermal_loss_partition",
            "measured_watertight_intake_and_exhaust_internal_geometry",
            "unsteady_1d_wave_action_model_with_valve_lift_and_discharge_coefficients",
            "moving_piston_valve_combustion_cfd_and_mesh_independence",
            "physical_flowbench_turbo_bench_and_engine_dyno_correlation",
        ],
    }
    require(all(report["technical_gates"].values()), "one or more F38 technical gates failed")
    require(all(value is False for value in report["release_gates"].values()), "F38 release gates must remain false")
    return report


def validate_f38_output_ownership(output: Path) -> None:
    if not output.exists() and not output.is_symlink():
        return
    require(not output.is_symlink(), f"refusing to replace symlink output: {output}")
    require(output.is_dir(), f"refusing to replace non-directory output: {output}")
    report_path = output / REPORT_NAME
    marker_path = output / OUTPUT_MARKER_NAME
    require(report_path.is_file(), f"refusing to replace non-F38 directory: {output}")
    existing_report = load_json(report_path)
    require(existing_report.get("phase") == "F38", f"refusing to replace non-F38 directory: {output}")
    require(
        existing_report.get("asset_id") in (None, OUTPUT_OWNER),
        f"refusing to replace output owned by another asset: {output}",
    )
    if marker_path.is_file():
        marker = load_json(marker_path)
        require(marker.get("phase") == "F38", f"invalid F38 output marker: {output}")
        require(marker.get("asset_id") == OUTPUT_OWNER, f"invalid F38 output owner: {output}")
        require(marker.get("report_name") == REPORT_NAME, f"invalid F38 report marker: {output}")
        require(
            marker.get("report_sha256") == sha256(report_path),
            f"F38 output marker report hash mismatch: {output}",
        )


def publish(output: Path, report: dict[str, Any]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    validate_f38_output_ownership(output)
    temporary = Path(tempfile.mkdtemp(prefix=".f38-", dir=output.parent))
    backup_root: Path | None = None
    previous_output: Path | None = None
    try:
        report_path = temporary / REPORT_NAME
        write_json(report_path, report)
        write_json(
            temporary / OUTPUT_MARKER_NAME,
            {
                "schema_version": "1.0.0",
                "phase": "F38",
                "asset_id": OUTPUT_OWNER,
                "report_name": REPORT_NAME,
                "report_sha256": sha256(report_path),
            },
        )
        if output.exists():
            backup_root = Path(
                tempfile.mkdtemp(prefix=".f38-backup-", dir=output.parent)
            )
            previous_output = backup_root / "previous"
            os.replace(output, previous_output)
        try:
            os.replace(temporary, output)
        except Exception as installation_error:
            if previous_output is not None and previous_output.exists():
                try:
                    os.replace(previous_output, output)
                except Exception as restoration_error:
                    raise F38InputError(
                        "F38 output installation and restoration failed; "
                        f"previous output retained at {previous_output}"
                    ) from restoration_error
            raise installation_error
        if backup_root is not None:
            shutil.rmtree(backup_root)
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)
        if backup_root is not None and backup_root.exists():
            if previous_output is None or not previous_output.exists():
                shutil.rmtree(backup_root, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute the fail-closed F38 steady gas-path network.")
    parser.add_argument("--project-root", default=str(REPO_ROOT))
    parser.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    arguments = parser.parse_args()
    project_root = Path(arguments.project_root).resolve()
    contract_path = Path(arguments.contract).resolve()
    output = Path(arguments.output).resolve()
    try:
        contract = load_json(contract_path)
        report = build_report(project_root, contract_path, contract)
        publish(output, report)
    except (F38InputError, OSError, json.JSONDecodeError, KeyError, TypeError) as error:
        print(f"F38 gas-path error: {error}", file=os.sys.stderr)
        return 2
    print(json.dumps({
        "phase": "F38",
        "status": report["status"],
        "report": str(output / REPORT_NAME),
        "target_power_proven": report["release_gates"]["target_power_proven"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
