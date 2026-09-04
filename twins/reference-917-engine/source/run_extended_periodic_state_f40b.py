#!/usr/bin/env python3
"""Recherche un regime periodique agrege du cas nominal motored F40.

F40b conserve un unique reseau Aeolus et son etat pendant 4 a 24 cycles de
720 degres. L'arret anticipe n'est permis qu'apres trois deltas consecutifs
inferieurs ou egaux a 0,1 % sur les sept metriques F40. Ce test numerique ne
modele ni combustion, ni turbocompresseurs, ni puissance.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.metadata
import importlib.util
import json
import math
from pathlib import Path
from types import ModuleType
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONTRACT = REPO_ROOT / "twins/reference-917-engine/extended-periodic-state-f40b.json"
DEFAULT_OUTPUT = REPO_ROOT / "work/917-extended-periodic-state-f40b"
REPORT_NAME = "extended-periodic-state-f40b-report.json"
OUTPUT_OWNER = "porsche-917-extended-periodic-state-f40b"

F40_CONTRACT_PATH = "twins/reference-917-engine/unsteady-convergence-campaign-f40.json"
F40_CONTRACT_SHA256 = "6fff578fe167b8563b48271b9234f36c05b9bb1b2003a5ddee594acd6de9178c"
F40_RUNNER_PATH = "twins/reference-917-engine/source/run_unsteady_convergence_f40.py"
F40_RUNNER_SHA256 = "fa2e529389c6a493789fb4528e973e7c987100f941f83ab744ea45822ff925d3"
DOCUMENTARY_COMMIT = "c3d68ba9eddbaf19e316ff79ef39037d3d7e5bd6"
RUNTIME_DIGEST = "sha256:742569a45becdd00b9f8d32b057156e68d0bb0489cef1fa97d2e6543fce096a3"
RUNTIME_IMAGE = f"ghcr.io/cluster2600/3dprinting993-wave-action-f39@{RUNTIME_DIGEST}"

NOMINAL_CASE = {
    "case_id": "mesh_2p0_cfl_0p2_init_1p00",
    "mesh_scale": 2.0,
    "cfl": 0.2,
    "initial_pressure_factor": 1.0,
}

CYCLE_METRICS = [
    "total_pipe_mass_kg",
    "total_component_mass_kg",
    "total_gas_mass_kg",
    "pipe_pressure_volume_mean_pa_abs",
    "pipe_temperature_mass_mean_k",
    "component_pressure_volume_mean_pa_abs",
    "component_temperature_mass_mean_k",
]

NUMERICAL_GATE_NAMES = {
    "source_hashes_verified",
    "nominal_case_validated",
    "runtime_network_built_once",
    "minimum_cycles_completed",
    "maximum_cycle_budget_not_exceeded",
    "all_cycle_windows_completed",
    "all_runtime_fields_finite",
    "all_runtime_states_positive",
    "exact_runtime_coverage_all_boundaries",
    "all_cycle_boundaries_recorded",
    "three_consecutive_deltas_evaluated",
    "early_stop_rule_respected",
    "aggregate_periodic_state_demonstrated",
    "phase_resolved_convergence_evaluated",
}

PHYSICAL_GATE_NAMES = {
    "measured_network_geometry_available",
    "measured_valve_cda_available",
    "absolute_crank_phase_validated",
    "physical_cycle_correlation_complete",
    "mass_balance_validated",
    "energy_balance_validated",
    "physical_engine_dyno_correlated",
    "power_or_torque_prediction_authorized",
    "target_power_proven",
    "engine_start_authorized",
    "manufacturing_authorized",
}

PROHIBITED_CLAIMS = [
    "aggregate_periodicity_is_phase_resolved_convergence",
    "numerical_convergence_is_physical_validation",
    "finite_positive_state_is_mass_or_energy_conservation",
    "motored_cycles_predict_fired_power_or_torque",
    "f40b_models_combustion_or_turbochargers",
    "f40b_proves_1600_hp",
    "f40b_authorizes_engine_start_or_manufacturing",
]


class F40bInputError(ValueError):
    """Erreur deterministe de contrat, provenance ou resultat F40b."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise F40bInputError(message)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"JSON object required: {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def finite_number(value: Any, label: str, *, positive: bool = False) -> float:
    require(
        not isinstance(value, bool) and isinstance(value, (int, float)),
        f"{label} must be numeric",
    )
    result = float(value)
    require(math.isfinite(result), f"{label} must be finite")
    if positive:
        require(result > 0.0, f"{label} must be positive")
    return result


def validate_contract(contract: dict[str, Any]) -> None:
    require(contract.get("schema_version") == "1.0.0", "schema_version must be 1.0.0")
    require(contract.get("phase") == "F40b", "contract.phase must be F40b")
    require(
        contract.get("status") == "extended_periodic_state_contract_fail_closed",
        "contract.status mismatch",
    )
    require(contract.get("asset_id") == OUTPUT_OWNER, "contract.asset_id mismatch")

    sources = contract.get("source_bindings")
    require(isinstance(sources, dict), "source_bindings object required")
    require(set(sources) == {"f40_contract", "f40_runner"}, "exact F40 source bindings required")
    expected_sources = {
        "f40_contract": (F40_CONTRACT_PATH, F40_CONTRACT_SHA256),
        "f40_runner": (F40_RUNNER_PATH, F40_RUNNER_SHA256),
    }
    for source_id, (expected_path, expected_hash) in expected_sources.items():
        item = sources.get(source_id)
        require(isinstance(item, dict), f"source_bindings.{source_id} required")
        require(item.get("path") == expected_path, f"{source_id} path mismatch")
        require(item.get("expected_sha256") == expected_hash, f"{source_id} hash binding mismatch")

    snapshot = contract.get("repository_snapshot")
    require(isinstance(snapshot, dict), "repository_snapshot required")
    require(snapshot.get("commit") == DOCUMENTARY_COMMIT, "documentary commit mismatch")
    require(
        snapshot.get("classification") == "documentary_snapshot_not_runtime_head_requirement",
        "repository snapshot classification mismatch",
    )
    require(snapshot.get("enforce_current_head") is False, "documentary commit must not enforce current HEAD")

    image = contract.get("runtime_image")
    require(isinstance(image, dict), "runtime_image required")
    require(image.get("reference") == RUNTIME_IMAGE, "immutable runtime image reference mismatch")
    require(image.get("digest") == RUNTIME_DIGEST, "runtime image digest mismatch")
    require(image.get("runtime_digest_verified_by_runner") is False, "runner cannot claim local digest verification")

    authority = contract.get("authority_boundary")
    require(isinstance(authority, dict), "authority_boundary required")
    require(authority.get("motored_only") is True, "F40b must remain motored only")
    for key in (
        "combustion_enabled",
        "fuel_injection_enabled",
        "turbochargers_enabled",
        "power_or_torque_evaluated",
        "physical_correlation_complete",
        "manufacturing_authorized",
    ):
        require(authority.get(key) is False, f"authority_boundary.{key} must remain false")

    campaign = contract.get("campaign")
    require(isinstance(campaign, dict), "campaign object required")
    require(campaign.get("nominal_case") == NOMINAL_CASE, "exact F40 nominal case required")
    require(finite_number(campaign.get("cycle_degrees"), "campaign.cycle_degrees") == 720.0, "cycle must cover 720 degrees")
    require(campaign.get("minimum_cycles") == 4, "minimum cycle count must be four")
    require(campaign.get("maximum_cycles") == 24, "maximum cycle count must be 24")
    for key in (
        "one_runtime_network",
        "state_preserved_between_cycles",
        "cumulative_t_start_required",
        "record_every_cycle_boundary",
        "wall_clock_fields_prohibited",
    ):
        require(campaign.get(key) is True, f"campaign.{key} must be true")
    early_stop = campaign.get("early_stop")
    require(
        early_stop
        == {
            "permitted_only_after_minimum_cycles": True,
            "stop_on_first_satisfied_window": True,
            "all_metrics_must_pass": True,
        },
        "exact early-stop policy required",
    )

    policy = contract.get("convergence_policy")
    require(isinstance(policy, dict), "convergence_policy required")
    require(policy.get("policy_version") == "f40b-v1", "convergence policy version mismatch")
    require(finite_number(policy.get("relative_floor"), "relative floor", positive=True) == 1.0e-12, "f40b-v1 relative floor mismatch")
    require(policy.get("required_consecutive_deltas") == 3, "three consecutive deltas required")
    require(finite_number(policy.get("cyclic_max_relative_delta"), "cyclic tolerance", positive=True) == 0.001, "f40b-v1 cyclic tolerance mismatch")
    require(policy.get("cycle_metrics") == CYCLE_METRICS, "exact seven ordered cycle metrics required")
    require(policy.get("comparison") == "successive_cycle_boundaries", "successive boundary comparison required")
    require(policy.get("failure_on_cycle_budget_exhaustion") is True, "cycle budget exhaustion must fail closed")
    require(policy.get("failure_does_not_suppress_report") is True, "failed convergence must still report")

    sampling = contract.get("phase_resolved_sampling")
    require(isinstance(sampling, dict), "phase_resolved_sampling required")
    require(sampling.get("status") == "not_implemented_fail_closed", "phase-resolved status must remain fail-closed")
    require(isinstance(sampling.get("reason"), str) and sampling["reason"], "phase-resolved reason required")
    for key in ("sampling_evaluated", "l2_norm_evaluated", "linf_norm_evaluated"):
        require(sampling.get(key) is False, f"phase_resolved_sampling.{key} must remain false")

    numerical = contract.get("numerical_gates")
    require(isinstance(numerical, dict) and set(numerical) == NUMERICAL_GATE_NAMES, "exact numerical_gates contract required")
    require(all(value is False for value in numerical.values()), "contract numerical gates must start false")
    physical = contract.get("physical_release_gates")
    require(isinstance(physical, dict) and set(physical) == PHYSICAL_GATE_NAMES, "exact physical_release_gates contract required")
    require(all(value is False for value in physical.values()), "physical release gates must remain false")
    require(contract.get("prohibited_claims") == PROHIBITED_CLAIMS, "exact prohibited claims required")


def verify_source_bindings(project_root: Path, contract: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for source_id in sorted(contract["source_bindings"]):
        binding = contract["source_bindings"][source_id]
        path = project_root / binding["path"]
        require(path.is_file(), f"source missing: {binding['path']}")
        actual = sha256(path)
        require(actual == binding["expected_sha256"], f"source hash mismatch: {source_id}")
        result[source_id] = {
            "path": binding["path"],
            "expected_sha256": binding["expected_sha256"],
            "actual_sha256": actual,
            "hash_verified": True,
        }
    return result


def load_f40_runner(project_root: Path) -> ModuleType:
    path = project_root / F40_RUNNER_PATH
    require(path.is_file(), f"source missing: {F40_RUNNER_PATH}")
    require(sha256(path) == F40_RUNNER_SHA256, "source hash mismatch: f40_runner")
    spec = importlib.util.spec_from_file_location("f40b_hash_bound_f40_runner", path)
    require(spec is not None and spec.loader is not None, "unable to load hash-bound F40 runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_upstream_f40(project_root: Path, contract: dict[str, Any]) -> tuple[ModuleType, dict[str, Any]]:
    f40 = load_f40_runner(project_root)
    upstream = f40.load_json(project_root / F40_CONTRACT_PATH)
    f40.validate_contract(upstream)
    f40.verify_source_bindings(project_root, upstream)
    cases = f40.validate_matrix(upstream)
    by_id = {item["case_id"]: item for item in cases}
    require(by_id.get(NOMINAL_CASE["case_id"]) == NOMINAL_CASE, "F40 nominal case mismatch")
    require(contract["campaign"]["nominal_case"] == NOMINAL_CASE, "F40b nominal case mismatch")
    return f40, upstream


def relative_delta(value: float, reference: float, floor: float) -> float:
    finite_number(value, "comparison value")
    finite_number(reference, "comparison reference")
    finite_number(floor, "relative floor", positive=True)
    return abs(float(value) - float(reference)) / max(abs(float(reference)), float(floor))


def _valid_boundary_metrics(boundary: dict[str, Any], metrics: list[str]) -> bool:
    values = boundary.get("metrics")
    if not isinstance(values, dict):
        return False
    for metric in metrics:
        value = values.get(metric)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            return False
    return True


def evaluate_periodicity(
    boundaries: list[dict[str, Any]],
    policy: dict[str, Any],
    *,
    minimum_cycles: int,
) -> dict[str, Any]:
    metrics = list(policy["cycle_metrics"])
    floor = float(policy["relative_floor"])
    threshold = float(policy["cyclic_max_relative_delta"])
    required = int(policy["required_consecutive_deltas"])
    valid_boundaries = all(_valid_boundary_metrics(item, metrics) for item in boundaries)
    deltas: list[dict[str, Any]] = []
    if valid_boundaries:
        for previous, current in zip(boundaries, boundaries[1:]):
            metric_deltas = {
                metric: relative_delta(
                    float(current["metrics"][metric]),
                    float(previous["metrics"][metric]),
                    floor,
                )
                for metric in metrics
            }
            maximum = max(metric_deltas.values())
            deltas.append(
                {
                    "from_cycle": int(previous["cycle_index"]),
                    "to_cycle": int(current["cycle_index"]),
                    "metric_relative_deltas": metric_deltas,
                    "maximum_relative_delta": maximum,
                    "within_tolerance": maximum <= threshold,
                }
            )

    first_satisfied_at_cycle: int | None = None
    satisfied_window: list[dict[str, Any]] = []
    if valid_boundaries and len(deltas) >= required:
        for end in range(required - 1, len(deltas)):
            window = deltas[end - required + 1 : end + 1]
            cycle = int(window[-1]["to_cycle"])
            if cycle >= minimum_cycles and all(item["within_tolerance"] for item in window):
                first_satisfied_at_cycle = cycle
                satisfied_window = window
                break

    return {
        "policy_version": policy["policy_version"],
        "minimum_cycles": minimum_cycles,
        "observed_cycle_boundaries": len(boundaries),
        "required_consecutive_deltas": required,
        "observed_consecutive_deltas": len(deltas),
        "cyclic_max_relative_delta_tolerance": threshold,
        "relative_deltas": deltas,
        "metrics_valid_at_all_boundaries": valid_boundaries,
        "has_required_consecutive_deltas": bool(valid_boundaries and len(deltas) >= required),
        "first_satisfied_at_cycle": first_satisfied_at_cycle,
        "satisfied_window": satisfied_window,
        "evaluated": bool(valid_boundaries and len(deltas) >= required),
        "passed": first_satisfied_at_cycle is not None,
    }


def advance_until_periodic(
    *,
    case: Any,
    network: Any,
    clock: Any,
    dispatch_fn: Callable[..., float],
    boundary_builder: Callable[[dict[str, Any], list[Any]], dict[str, Any]],
    cycle_duration_s: float,
    minimum_cycles: int,
    maximum_cycles: int,
    maximum_steps_per_cycle: int,
    completion_relative_tolerance: float,
    convergence_policy: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Avance le meme reseau jusqu'au premier fenetrage convergent ou au budget."""
    require(minimum_cycles == 4, "F40b runtime minimum must be four cycles")
    require(maximum_cycles == 24, "F40b runtime maximum must be 24 cycles")
    require(maximum_cycles >= minimum_cycles, "invalid cycle bounds")
    finite_number(cycle_duration_s, "cycle duration", positive=True)
    finite_number(completion_relative_tolerance, "completion tolerance", positive=True)
    require(maximum_steps_per_cycle > 0, "maximum steps must be positive")
    boundaries: list[dict[str, Any]] = []
    t_start = 0.0
    crank_degrees_per_second = float(case.crankshaft.rpm) * 6.0
    require(crank_degrees_per_second > 0.0, "crankshaft speed must be positive")

    for cycle_index in range(1, maximum_cycles + 1):
        target = cycle_duration_s * cycle_index
        case.case.t_end = target
        call_t_start = t_start
        t_final = float(
            dispatch_fn(
                case,
                network.pipes,
                network.junctions,
                network.bcs,
                clock=clock,
                max_steps=maximum_steps_per_cycle,
                t_start=call_t_start,
                coolant_couplings=network.coolant_couplings,
                wall_thermal_pairs=network.wall_thermal_pairs,
            )
        )
        completed = math.isfinite(t_final) and abs(t_final - target) <= completion_relative_tolerance * max(abs(target), cycle_duration_s)
        state = boundary_builder(network.pipes, network.junctions)
        boundaries.append(
            {
                "cycle_index": cycle_index,
                "t_start_s": call_t_start,
                "t_target_s": target,
                "t_final_s": t_final if math.isfinite(t_final) else None,
                "crank_degrees_start": call_t_start * crank_degrees_per_second,
                "crank_degrees_target": target * crank_degrees_per_second,
                "crank_degrees_final": t_final * crank_degrees_per_second if math.isfinite(t_final) else None,
                "cycle_window_completed": completed,
                **state,
            }
        )
        convergence = evaluate_periodicity(
            boundaries,
            convergence_policy,
            minimum_cycles=minimum_cycles,
        )
        integrity = (
            completed
            and state.get("finite_fields") is True
            and state.get("positive_state") is True
            and state.get("exact_runtime_coverage") is True
        )
        if not integrity or not math.isfinite(t_final):
            return boundaries, convergence
        if convergence["passed"]:
            require(
                convergence["first_satisfied_at_cycle"] == cycle_index,
                "early stop must occur at first satisfied window",
            )
            return boundaries, convergence
        t_start = t_final

    return boundaries, evaluate_periodicity(
        boundaries,
        convergence_policy,
        minimum_cycles=minimum_cycles,
    )


def execute_nominal_case(project_root: Path, contract: dict[str, Any]) -> dict[str, Any]:
    try:
        f40, upstream = validate_upstream_f40(project_root, contract)
        case, f39, case_summary = f40.build_case_for_campaign(
            project_root,
            copy.deepcopy(NOMINAL_CASE),
            upstream,
        )
        from aeolus1d.bc.transient import Clock
        from aeolus1d.io.build import build_network
        from aeolus1d.io.case import dispatch_advance

        clock = Clock()
        network = build_network(case, clock=clock)
        crank_validation = f40.validate_runtime_crank_on_network(case, network)
        f39_contract = f39.load_json(project_root / f40.F39_CONTRACT_PATH)
        cycle_duration = float(f39_contract["numerical_policy"]["expected_duration_s"])
        boundaries, convergence = advance_until_periodic(
            case=case,
            network=network,
            clock=clock,
            dispatch_fn=dispatch_advance,
            boundary_builder=lambda pipes, components: f40.collect_boundary_state(f39, pipes, components),
            cycle_duration_s=cycle_duration,
            minimum_cycles=int(contract["campaign"]["minimum_cycles"]),
            maximum_cycles=int(contract["campaign"]["maximum_cycles"]),
            maximum_steps_per_cycle=int(f39_contract["numerical_policy"]["maximum_steps"]),
            completion_relative_tolerance=float(f39_contract["numerical_policy"]["time_completion_relative_tolerance"]),
            convergence_policy=contract["convergence_policy"],
        )
        completed = all(item.get("cycle_window_completed") is True for item in boundaries)
        finite = completed and all(item.get("finite_fields") is True for item in boundaries)
        positive = finite and all(item.get("positive_state") is True for item in boundaries)
        exact = positive and all(item.get("exact_runtime_coverage") is True for item in boundaries)
        periodic = exact and convergence.get("passed") is True
        exhausted = exact and len(boundaries) == contract["campaign"]["maximum_cycles"] and not periodic
        return {
            "case_id": NOMINAL_CASE["case_id"],
            "case_spec": copy.deepcopy(NOMINAL_CASE),
            "status": (
                "periodic_state_demonstrated"
                if periodic
                else "cycle_budget_exhausted_without_periodicity"
                if exhausted
                else "incomplete"
            ),
            "backend": "aeolus1d",
            "backend_version": importlib.metadata.version("aeolus1d"),
            "case_summary": case_summary,
            "crank_validation": crank_validation,
            "runtime_network_build_count": 1,
            "cycles_attempted": len(boundaries),
            "cycles_completed": len(boundaries) if completed else sum(bool(item.get("cycle_window_completed")) for item in boundaries),
            "cycle_boundaries": boundaries,
            "all_cycle_windows_completed": completed,
            "all_runtime_fields_finite": finite,
            "all_runtime_states_positive": positive,
            "exact_runtime_coverage_all_boundaries": exact,
            "cycle_budget_exhausted": exhausted,
            "stopped_early": bool(periodic and len(boundaries) < contract["campaign"]["maximum_cycles"]),
            "convergence": convergence,
        }
    except Exception as exc:  # Le rapport reste disponible et fail-closed.
        return {
            "case_id": NOMINAL_CASE["case_id"],
            "case_spec": copy.deepcopy(NOMINAL_CASE),
            "status": "execution_failed",
            "error_class": type(exc).__name__,
            "error": str(exc),
            "runtime_network_build_count": 0,
            "cycles_attempted": 0,
            "cycles_completed": 0,
            "cycle_boundaries": [],
            "all_cycle_windows_completed": False,
            "all_runtime_fields_finite": False,
            "all_runtime_states_positive": False,
            "exact_runtime_coverage_all_boundaries": False,
            "cycle_budget_exhausted": False,
            "stopped_early": False,
            "convergence": {
                "evaluated": False,
                "has_required_consecutive_deltas": False,
                "passed": False,
                "first_satisfied_at_cycle": None,
                "relative_deltas": [],
            },
        }


def derive_numerical_gates(
    *,
    source_hashes_verified: bool,
    nominal_case_validated: bool,
    execution: dict[str, Any] | None,
    contract: dict[str, Any],
) -> dict[str, bool]:
    if execution is None:
        return {
            name: bool(
                (name == "source_hashes_verified" and source_hashes_verified)
                or (name == "nominal_case_validated" and nominal_case_validated)
            )
            for name in NUMERICAL_GATE_NAMES
        }

    boundaries = execution.get("cycle_boundaries")
    boundaries = boundaries if isinstance(boundaries, list) else []
    observed = len(boundaries)
    minimum = int(contract["campaign"]["minimum_cycles"])
    maximum = int(contract["campaign"]["maximum_cycles"])
    convergence = execution.get("convergence")
    convergence = convergence if isinstance(convergence, dict) else {}
    periodic = convergence.get("passed") is True
    first_satisfied = convergence.get("first_satisfied_at_cycle")
    indices_exact = [item.get("cycle_index") for item in boundaries] == list(range(1, observed + 1))
    all_recorded = observed == execution.get("cycles_attempted") and indices_exact
    completed = observed >= minimum and execution.get("all_cycle_windows_completed") is True
    finite = completed and execution.get("all_runtime_fields_finite") is True
    positive = finite and execution.get("all_runtime_states_positive") is True
    exact = positive and execution.get("exact_runtime_coverage_all_boundaries") is True
    if periodic:
        early_stop_respected = (
            exact
            and isinstance(first_satisfied, int)
            and first_satisfied == observed
            and minimum <= observed <= maximum
        )
    else:
        early_stop_respected = exact and observed == maximum and execution.get("cycle_budget_exhausted") is True
    return {
        "source_hashes_verified": bool(source_hashes_verified),
        "nominal_case_validated": bool(nominal_case_validated),
        "runtime_network_built_once": execution.get("runtime_network_build_count") == 1,
        "minimum_cycles_completed": bool(completed),
        "maximum_cycle_budget_not_exceeded": bool(observed <= maximum and observed > 0),
        "all_cycle_windows_completed": bool(completed),
        "all_runtime_fields_finite": bool(finite),
        "all_runtime_states_positive": bool(positive),
        "exact_runtime_coverage_all_boundaries": bool(exact),
        "all_cycle_boundaries_recorded": bool(all_recorded and observed > 0),
        "three_consecutive_deltas_evaluated": convergence.get("has_required_consecutive_deltas") is True,
        "early_stop_rule_respected": bool(early_stop_respected),
        "aggregate_periodic_state_demonstrated": bool(exact and periodic and early_stop_respected),
        "phase_resolved_convergence_evaluated": False,
    }


def build_report(
    contract: dict[str, Any],
    project_root: Path,
    *,
    execute: bool,
    executor: Callable[[Path, dict[str, Any]], dict[str, Any]] = execute_nominal_case,
) -> dict[str, Any]:
    validate_contract(contract)
    sources = verify_source_bindings(project_root, contract)
    validate_upstream_f40(project_root, contract)
    execution = executor(project_root, contract) if execute else None
    gates = derive_numerical_gates(
        source_hashes_verified=True,
        nominal_case_validated=True,
        execution=execution,
        contract=contract,
    )
    if not execute:
        status = "extended_periodic_state_manifest"
    elif gates["aggregate_periodic_state_demonstrated"]:
        status = "aggregate_periodic_state_demonstrated"
    elif execution and execution.get("cycle_budget_exhausted") is True:
        status = "cycle_budget_exhausted_without_periodicity"
    else:
        status = "extended_periodic_state_execution_failed"
    return {
        "schema_version": contract["schema_version"],
        "phase": "F40b",
        "asset_id": contract["asset_id"],
        "status": status,
        "mode": "execute" if execute else "manifest",
        "source_bindings": sources,
        "repository_snapshot": contract["repository_snapshot"],
        "runtime_image": contract["runtime_image"],
        "authority_boundary": contract["authority_boundary"],
        "campaign": {
            **copy.deepcopy(contract["campaign"]),
            "execution": execution,
        },
        "convergence_policy": contract["convergence_policy"],
        "phase_resolved_sampling": copy.deepcopy(contract["phase_resolved_sampling"]),
        "numerical_gates": gates,
        "physical_release_gates": copy.deepcopy(contract["physical_release_gates"]),
        "prohibited_claims": contract["prohibited_claims"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--manifest", action="store_true", help="Valide le contrat sans execution Aeolus")
    mode.add_argument("--execute", action="store_true", help="Execute 4 a 24 cycles du cas nominal")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    contract = load_json(args.contract.resolve())
    report = build_report(
        contract,
        args.project_root.resolve(),
        execute=bool(args.execute),
    )
    output = args.output_dir.resolve() / REPORT_NAME
    write_json(output, report)
    print(output)
    if args.execute:
        integrity_gates = (
            "runtime_network_built_once",
            "minimum_cycles_completed",
            "maximum_cycle_budget_not_exceeded",
            "all_cycle_windows_completed",
            "all_runtime_fields_finite",
            "all_runtime_states_positive",
            "exact_runtime_coverage_all_boundaries",
            "all_cycle_boundaries_recorded",
            "three_consecutive_deltas_evaluated",
            "early_stop_rule_respected",
        )
        if not all(report["numerical_gates"][name] for name in integrity_gates):
            return 2
        if not report["numerical_gates"]["aggregate_periodic_state_demonstrated"]:
            return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
