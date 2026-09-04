#!/usr/bin/env python3
"""Execute la campagne de convergence numerique F40 du reseau motored F39.

La campagne reconstruit un reseau Aeolus1D par cas, puis conserve exactement
ce meme reseau pendant quatre fenetres successives de 720 degres. Elle ne
contient ni combustion, ni turbo, ni calcul de puissance. Une convergence
numerique observee ne constitue donc jamais une validation physique.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.metadata
import importlib.util
import json
import math
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from types import ModuleType
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONTRACT = REPO_ROOT / "twins/reference-917-engine/unsteady-convergence-campaign-f40.json"
DEFAULT_OUTPUT = REPO_ROOT / "work/917-unsteady-convergence-f40"
REPORT_NAME = "unsteady-convergence-f40-report.json"
OUTPUT_OWNER = "porsche-917-unsteady-convergence-f40"

F39_CONTRACT_PATH = "twins/reference-917-engine/unsteady-network-f39.json"
F39_CONTRACT_SHA256 = "c62d1dffcd57a13dce569eb1af05e61c84b893b27613f77c01b0878831743432"
F39_RUNNER_PATH = "twins/reference-917-engine/source/run_unsteady_network_f39.py"
F39_RUNNER_SHA256 = "4a2f7b905cd512a77b5c9719f79423c5c3eff1b606bd9390b7de47539188d174"
DOCUMENTARY_COMMIT = "ddc7703d4ad949b2712bdf178a28dbaaf0ae3cda"
RUNTIME_DIGEST = "sha256:742569a45becdd00b9f8d32b057156e68d0bb0489cef1fa97d2e6543fce096a3"
RUNTIME_IMAGE = f"ghcr.io/cluster2600/3dprinting993-wave-action-f39@{RUNTIME_DIGEST}"

EXPECTED_CASES = {
    "mesh_0p5_cfl_0p2_init_1p00": (0.5, 0.2, 1.0),
    "mesh_1p0_cfl_0p2_init_1p00": (1.0, 0.2, 1.0),
    "mesh_2p0_cfl_0p2_init_0p95": (2.0, 0.2, 0.95),
    "mesh_2p0_cfl_0p2_init_1p00": (2.0, 0.2, 1.0),
    "mesh_2p0_cfl_0p2_init_1p05": (2.0, 0.2, 1.05),
    "mesh_2p0_cfl_0p4_init_1p00": (2.0, 0.4, 1.0),
}

EXPECTED_COMPARISONS = {
    "mesh": {
        "reference_case_id": "mesh_2p0_cfl_0p2_init_1p00",
        "candidate_case_ids": [
            "mesh_0p5_cfl_0p2_init_1p00",
            "mesh_1p0_cfl_0p2_init_1p00",
        ],
    },
    "temporal": {
        "reference_case_id": "mesh_2p0_cfl_0p2_init_1p00",
        "candidate_case_ids": ["mesh_2p0_cfl_0p4_init_1p00"],
    },
    "initial_state": {
        "reference_case_id": "mesh_2p0_cfl_0p2_init_1p00",
        "candidate_case_ids": [
            "mesh_2p0_cfl_0p2_init_0p95",
            "mesh_2p0_cfl_0p2_init_1p05",
        ],
    },
}

NUMERICAL_GATE_NAMES = {
    "source_hashes_verified",
    "matrix_validated",
    "all_cases_executed_four_cycles",
    "all_runtime_fields_finite",
    "all_runtime_states_positive",
    "all_cases_have_three_consecutive_deltas",
    "aggregate_cycle_boundary_convergence_all_cases_demonstrated",
    "mesh_sensitivity_evaluated",
    "mesh_sensitivity_within_tolerance",
    "temporal_sensitivity_evaluated",
    "temporal_sensitivity_within_tolerance",
    "initial_state_sensitivity_evaluated",
    "initial_state_sensitivity_within_tolerance",
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
    "numerical_convergence_is_physical_validation",
    "finite_positive_state_is_mass_or_energy_conservation",
    "motored_cycles_predict_fired_power_or_torque",
    "f40_models_combustion_or_turbochargers",
    "f40_proves_1600_hp",
    "f40_authorizes_engine_start_or_manufacturing",
]

F40_TOLERANCES = {
    "relative_floor": 1.0e-12,
    "cyclic_max_relative_delta": 0.001,
    "sensitivity_tolerances": {
        "mesh_max_relative_delta": 0.02,
        "temporal_max_relative_delta": 0.01,
        "initial_state_max_relative_delta": 0.01,
    },
}


class F40InputError(ValueError):
    """Erreur deterministe de contrat, provenance, matrice ou resultat."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise F40InputError(message)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"JSON object required: {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            value,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
        )
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
    require(contract.get("phase") == "F40", "contract.phase must be F40")
    require(
        contract.get("status") == "numerical_convergence_campaign_contract_fail_closed",
        "contract.status mismatch",
    )
    require(contract.get("asset_id") == OUTPUT_OWNER, "contract.asset_id mismatch")

    sources = contract.get("source_bindings")
    require(isinstance(sources, dict), "source_bindings object required")
    require(set(sources) == {"f39_contract", "f39_runner"}, "exact F39 source bindings required")
    expected_sources = {
        "f39_contract": (F39_CONTRACT_PATH, F39_CONTRACT_SHA256),
        "f39_runner": (F39_RUNNER_PATH, F39_RUNNER_SHA256),
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
    require(
        image.get("runtime_digest_verified_by_runner") is False,
        "runner must not claim local container digest verification",
    )

    authority = contract.get("authority_boundary")
    require(isinstance(authority, dict), "authority_boundary required")
    require(authority.get("motored_only") is True, "F40 must remain motored only")
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
    require(campaign.get("cycles_per_case") == 4, "exactly four cycles per case required")
    require(finite_number(campaign.get("cycle_degrees"), "campaign.cycle_degrees") == 720.0, "each cycle must cover 720 degrees")
    for key in (
        "one_runtime_network_per_case",
        "state_preserved_between_cycles",
        "cumulative_t_start_required",
    ):
        require(campaign.get(key) is True, f"campaign.{key} must be true")
    parallel = campaign.get("parallelism")
    require(isinstance(parallel, dict), "campaign.parallelism required")
    require(parallel.get("explicit_workers_required_for_execute") is True, "explicit workers required")
    require(parallel.get("minimum_workers") == 1, "minimum workers must be one")
    require(parallel.get("maximum_workers") == 6, "maximum workers must equal case count")
    require(parallel.get("unit_of_parallelism") == "case", "cases must be the parallel unit")
    require(parallel.get("deterministic_sorted_report") is True, "sorted report required")
    require(parallel.get("wall_clock_fields_prohibited") is True, "wall-clock fields must be prohibited")
    mesh_policy = campaign.get("mesh_scaling")
    require(isinstance(mesh_policy, dict), "campaign.mesh_scaling required")
    require(mesh_policy.get("target") == "all_27_f39_pipe_n_cells", "mesh scaling target mismatch")
    require(mesh_policy.get("rounding") == "nearest_integer_half_up", "mesh rounding policy mismatch")
    require(mesh_policy.get("minimum_cells_per_pipe") == 4, "minimum cells must be four")
    init_policy = campaign.get("initial_state_scaling")
    require(isinstance(init_policy, dict), "campaign.initial_state_scaling required")
    require(init_policy.get("target") == "initial_absolute_pressure_only", "initial scaling target mismatch")
    require(
        init_policy.get("scaled_specs")
        == ["27_pipe_uniform_init", "3_junction_uniform_init", "12_cylinder_uniform_init"],
        "initial pressure scaling coverage mismatch",
    )
    require(init_policy.get("boundary_pressures_scaled") is False, "boundary pressures must not be scaled")
    require(init_policy.get("temperature_scaled") is False, "initial temperatures must not be scaled")
    validate_matrix(contract)

    policy = contract.get("convergence_policy")
    require(isinstance(policy, dict), "convergence_policy required")
    require(policy.get("policy_version") == "f40-v1", "convergence policy version mismatch")
    require(
        finite_number(policy.get("relative_floor"), "convergence_policy.relative_floor", positive=True)
        == F40_TOLERANCES["relative_floor"],
        "f40-v1 relative floor mismatch",
    )
    require(policy.get("required_cycle_boundaries") == 4, "four cycle boundaries required")
    require(policy.get("required_consecutive_deltas") == 3, "three consecutive deltas required")
    expected_metrics = {
        "total_pipe_mass_kg",
        "total_component_mass_kg",
        "total_gas_mass_kg",
        "pipe_pressure_volume_mean_pa_abs",
        "pipe_temperature_mass_mean_k",
        "component_pressure_volume_mean_pa_abs",
        "component_temperature_mass_mean_k",
    }
    metrics = policy.get("cycle_metrics")
    require(isinstance(metrics, list) and set(metrics) == expected_metrics and len(metrics) == 7, "exact seven cycle metrics required")
    require(
        finite_number(policy.get("cyclic_max_relative_delta"), "cyclic tolerance", positive=True)
        == F40_TOLERANCES["cyclic_max_relative_delta"],
        "f40-v1 cyclic tolerance mismatch",
    )
    tolerances = policy.get("sensitivity_tolerances")
    require(isinstance(tolerances, dict), "sensitivity_tolerances required")
    require(
        set(tolerances)
        == {
            "mesh_max_relative_delta",
            "temporal_max_relative_delta",
            "initial_state_max_relative_delta",
        },
        "exact sensitivity tolerances required",
    )
    for key, value in tolerances.items():
        finite_number(value, f"sensitivity_tolerances.{key}", positive=True)
    require(
        tolerances == F40_TOLERANCES["sensitivity_tolerances"],
        "f40-v1 sensitivity tolerances mismatch",
    )
    require(policy.get("comparison_boundary") == "cycle_4_end", "cycle-four comparison required")
    require(policy.get("all_metrics_must_pass") is True, "all metrics must pass")
    require(policy.get("failure_does_not_suppress_report") is True, "failed convergence must still report")

    numerical_gates = contract.get("numerical_gates")
    require(
        isinstance(numerical_gates, dict) and set(numerical_gates) == NUMERICAL_GATE_NAMES,
        "exact numerical_gates contract required",
    )
    require(all(value is False for value in numerical_gates.values()), "contract numerical gates must start false")
    physical_gates = contract.get("physical_release_gates")
    require(
        isinstance(physical_gates, dict) and set(physical_gates) == PHYSICAL_GATE_NAMES,
        "exact physical_release_gates contract required",
    )
    require(all(value is False for value in physical_gates.values()), "physical release gates must remain false")
    require(contract.get("prohibited_claims") == PROHIBITED_CLAIMS, "exact prohibited claims required")


def validate_matrix(contract: dict[str, Any]) -> list[dict[str, Any]]:
    campaign = contract.get("campaign")
    require(isinstance(campaign, dict), "campaign object required")
    cases = campaign.get("cases")
    require(isinstance(cases, list) and len(cases) == 6, "exactly six deduplicated cases required")
    by_id: dict[str, tuple[float, float, float]] = {}
    tuples: set[tuple[float, float, float]] = set()
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(cases):
        require(isinstance(item, dict), f"campaign.cases[{index}] invalid")
        case_id = item.get("case_id")
        require(isinstance(case_id, str) and case_id, f"campaign.cases[{index}].case_id required")
        mesh = finite_number(item.get("mesh_scale"), f"{case_id}.mesh_scale", positive=True)
        cfl = finite_number(item.get("cfl"), f"{case_id}.cfl", positive=True)
        factor = finite_number(item.get("initial_pressure_factor"), f"{case_id}.initial_pressure_factor", positive=True)
        require(case_id not in by_id, f"duplicate case_id: {case_id}")
        signature = (mesh, cfl, factor)
        require(signature not in tuples, f"duplicate numerical case: {case_id}")
        by_id[case_id] = signature
        tuples.add(signature)
        normalized.append(
            {
                "case_id": case_id,
                "mesh_scale": mesh,
                "cfl": cfl,
                "initial_pressure_factor": factor,
            }
        )
    require(by_id == EXPECTED_CASES, "F40 six-case matrix mismatch")
    comparisons = campaign.get("comparisons")
    require(comparisons == EXPECTED_COMPARISONS, "F40 comparison matrix mismatch")
    return sorted(normalized, key=lambda item: item["case_id"])


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


def load_f39_runner(project_root: Path) -> ModuleType:
    path = project_root / F39_RUNNER_PATH
    require(path.is_file(), f"source missing: {F39_RUNNER_PATH}")
    require(sha256(path) == F39_RUNNER_SHA256, "source hash mismatch: f39_runner")
    spec = importlib.util.spec_from_file_location("f40_hash_bound_f39_runner", path)
    require(spec is not None and spec.loader is not None, "unable to load hash-bound F39 runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def half_up_scaled_cells(base_cells: int, scale: float, minimum: int) -> int:
    require(isinstance(base_cells, int) and base_cells > 0, "base cell count must be positive integer")
    finite_number(scale, "mesh scale", positive=True)
    require(isinstance(minimum, int) and minimum >= 1, "minimum cell count must be positive integer")
    return max(minimum, int(math.floor(float(base_cells) * float(scale) + 0.5)))


def apply_initial_pressure_factor(case: Any, factor: float) -> dict[str, int]:
    """Modifie seulement les conditions initiales internes, jamais les BC."""
    finite_number(factor, "initial pressure factor", positive=True)
    counts = {"pipe_specs": 0, "junction_specs": 0, "cylinder_specs": 0}
    for pipe in case.pipes:
        pipe.init.p = float(pipe.init.p) * factor
        counts["pipe_specs"] += 1
    for junction in case.junctions:
        junction.init.p = float(junction.init.p) * factor
        counts["junction_specs"] += 1
    for cylinder in case.cylinders:
        cylinder.init.p = float(cylinder.init.p) * factor
        counts["cylinder_specs"] += 1
    require(counts == {"pipe_specs": 27, "junction_specs": 3, "cylinder_specs": 12}, "initial pressure scaling coverage mismatch")
    return counts


def build_case_for_campaign(
    project_root: Path,
    case_spec: dict[str, Any],
    campaign_contract: dict[str, Any],
) -> tuple[Any, ModuleType, dict[str, Any]]:
    f39 = load_f39_runner(project_root)
    f39_contract_path = project_root / F39_CONTRACT_PATH
    require(sha256(f39_contract_path) == F39_CONTRACT_SHA256, "source hash mismatch: f39_contract")
    f39_contract = f39.load_json(f39_contract_path)
    f39.validate_contract(f39_contract)
    f39.verify_sources(project_root, f39_contract)
    topology = f39.build_topology(f39_contract)
    f39.validate_topology(topology, f39_contract)
    minimum = int(campaign_contract["campaign"]["mesh_scaling"]["minimum_cells_per_pipe"])
    scale = float(case_spec["mesh_scale"])
    for pipe in topology["pipes"]:
        pipe["n_cells"] = half_up_scaled_cells(int(pipe["n_cells"]), scale, minimum)
    f39_contract = copy.deepcopy(f39_contract)
    f39_contract["numerical_policy"]["cfl"] = float(case_spec["cfl"])
    case = f39.build_aeolus_case(f39_contract, topology)
    case.case.name = f"porsche_917_f40_{case_spec['case_id']}"
    scaling_counts = apply_initial_pressure_factor(case, float(case_spec["initial_pressure_factor"]))
    summary = f39.case_summary(case)
    summary.update(
        {
            "case_id": case_spec["case_id"],
            "mesh_scale": float(case_spec["mesh_scale"]),
            "initial_pressure_factor": float(case_spec["initial_pressure_factor"]),
            "total_pipe_cells": sum(int(pipe.n_cells) for pipe in case.pipes),
            "initial_pressure_scaling_counts": scaling_counts,
            "boundary_pressures_scaled": False,
        }
    )
    return case, f39, summary


def _pipe_cell_areas(pipe: Any, count: int) -> list[float]:
    raw = getattr(pipe, "A_cell", None)
    if raw is None:
        raw = getattr(pipe, "A", None)
    if isinstance(raw, (int, float)):
        values = [float(raw)] * count
    else:
        try:
            values = [float(value) for value in raw]
        except TypeError as exc:
            raise F40InputError("runtime pipe cell areas unavailable") from exc
    require(len(values) == count, "runtime pipe cell area shape mismatch")
    require(all(math.isfinite(value) and value > 0.0 for value in values), "runtime pipe cell areas must be finite and positive")
    return values


def collect_boundary_state(
    f39: ModuleType,
    pipes: dict[str, Any],
    components: list[Any],
) -> dict[str, Any]:
    diagnostics = f39.collect_runtime_diagnostics(pipes, components)
    metrics: dict[str, float | None] = {
        "total_pipe_mass_kg": None,
        "total_component_mass_kg": None,
        "total_gas_mass_kg": None,
        "pipe_pressure_volume_mean_pa_abs": None,
        "pipe_temperature_mass_mean_k": None,
        "component_pressure_volume_mean_pa_abs": None,
        "component_temperature_mass_mean_k": None,
    }
    if diagnostics["finite_fields"] and diagnostics["positive_state"]:
        pipe_masses: list[float] = []
        pipe_volumes: list[float] = []
        pipe_pressure_volume: list[float] = []
        pipe_temperature_mass: list[float] = []
        for _pipe_id, pipe in sorted(pipes.items()):
            rho_raw, _velocity_raw, pressure_raw = pipe.primitives()
            rho = [float(value) for value in rho_raw]
            pressure = [float(value) for value in pressure_raw]
            areas = _pipe_cell_areas(pipe, len(rho))
            length = float(getattr(pipe, "L"))
            require(math.isfinite(length) and length > 0.0, "runtime pipe length must be finite and positive")
            dx = length / len(rho)
            gas_constant = float(getattr(pipe, "R_gas", 287.05))
            for density, p_abs, area in zip(rho, pressure, areas):
                volume = area * dx
                mass = density * volume
                temperature = p_abs / (density * gas_constant)
                pipe_volumes.append(volume)
                pipe_masses.append(mass)
                pipe_pressure_volume.append(p_abs * volume)
                pipe_temperature_mass.append(temperature * mass)

        component_masses: list[float] = []
        component_volumes: list[float] = []
        component_pressure_volume: list[float] = []
        component_temperature_mass: list[float] = []
        for component in sorted(components, key=lambda item: str(getattr(item, "id", ""))):
            volume = component.volume
            volume_m3 = float(volume.V)
            mass = float(volume.m)
            component_volumes.append(volume_m3)
            component_masses.append(mass)
            component_pressure_volume.append(float(volume.p) * volume_m3)
            component_temperature_mass.append(float(volume.T) * mass)

        total_pipe_volume = math.fsum(pipe_volumes)
        total_pipe_mass = math.fsum(pipe_masses)
        total_component_volume = math.fsum(component_volumes)
        total_component_mass = math.fsum(component_masses)
        require(total_pipe_volume > 0.0 and total_pipe_mass > 0.0, "pipe aggregate state must be positive")
        require(total_component_volume > 0.0 and total_component_mass > 0.0, "component aggregate state must be positive")
        metrics = {
            "total_pipe_mass_kg": total_pipe_mass,
            "total_component_mass_kg": total_component_mass,
            "total_gas_mass_kg": total_pipe_mass + total_component_mass,
            "pipe_pressure_volume_mean_pa_abs": math.fsum(pipe_pressure_volume) / total_pipe_volume,
            "pipe_temperature_mass_mean_k": math.fsum(pipe_temperature_mass) / total_pipe_mass,
            "component_pressure_volume_mean_pa_abs": math.fsum(component_pressure_volume) / total_component_volume,
            "component_temperature_mass_mean_k": math.fsum(component_temperature_mass) / total_component_mass,
        }
        require(all(math.isfinite(float(value)) and float(value) > 0.0 for value in metrics.values()), "cycle metrics must be finite and positive")
    return {
        "finite_fields": bool(diagnostics["finite_fields"]),
        "positive_state": bool(diagnostics["positive_state"]),
        "exact_runtime_coverage": bool(diagnostics["exact_runtime_coverage"]),
        "pipe_diagnostic_count": diagnostics["pipe_diagnostic_count"],
        "component_diagnostic_count": diagnostics["component_diagnostic_count"],
        "state_minima": diagnostics["state_minima"],
        "pipe_diagnostics": diagnostics["pipe_diagnostics"],
        "component_diagnostics": diagnostics["component_diagnostics"],
        "metrics": metrics,
    }


def validate_runtime_crank_on_network(case: Any, network: Any) -> dict[str, Any]:
    cylinders = [
        component
        for component in network.junctions
        if isinstance(getattr(component, "id", None), str)
        and component.id.startswith("c")
        and hasattr(component, "omega_crank")
    ]
    expected = 2.0 * math.pi * float(case.crankshaft.rpm) / 60.0
    require(len(cylinders) == 12, "runtime network must contain twelve cylinders")
    require(
        all(
            math.isclose(
                float(cylinder.omega_crank),
                expected,
                rel_tol=1.0e-12,
                abs_tol=1.0e-12,
            )
            for cylinder in cylinders
        ),
        "runtime cylinders did not inherit crankshaft speed",
    )
    return {
        "runtime_cylinder_count": len(cylinders),
        "expected_omega_rad_s": expected,
        "minimum_runtime_omega_rad_s": min(float(item.omega_crank) for item in cylinders),
        "maximum_runtime_omega_rad_s": max(float(item.omega_crank) for item in cylinders),
        "global_crank_inheritance_verified": True,
    }


def advance_four_cycles(
    *,
    case: Any,
    network: Any,
    clock: Any,
    dispatch_fn: Callable[..., float],
    boundary_builder: Callable[[dict[str, Any], list[Any]], dict[str, Any]],
    cycle_duration_s: float,
    cycles: int,
    maximum_steps_per_cycle: int,
    completion_relative_tolerance: float,
) -> list[dict[str, Any]]:
    """Avance un unique reseau, sans reconstruction entre les segments."""
    require(cycles == 4, "F40 runtime requires exactly four cycles")
    finite_number(cycle_duration_s, "cycle duration", positive=True)
    finite_number(completion_relative_tolerance, "completion tolerance", positive=True)
    require(maximum_steps_per_cycle > 0, "maximum steps must be positive")
    boundaries: list[dict[str, Any]] = []
    t_start = 0.0
    crank_degrees_per_second = float(case.crankshaft.rpm) * 6.0
    require(crank_degrees_per_second > 0.0, "crankshaft speed must be positive")
    for cycle_index in range(1, cycles + 1):
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
        if not math.isfinite(t_final):
            break
        t_start = t_final
    return boundaries


def relative_delta(value: float, reference: float, floor: float) -> float:
    finite_number(value, "comparison value")
    finite_number(reference, "comparison reference")
    finite_number(floor, "relative floor", positive=True)
    return abs(float(value) - float(reference)) / max(abs(float(reference)), float(floor))


def evaluate_cycle_convergence(
    boundaries: list[dict[str, Any]],
    policy: dict[str, Any],
) -> dict[str, Any]:
    metric_names = list(policy["cycle_metrics"])
    threshold = float(policy["cyclic_max_relative_delta"])
    floor = float(policy["relative_floor"])
    required_boundaries = int(policy["required_cycle_boundaries"])
    required_deltas = int(policy["required_consecutive_deltas"])
    deltas: list[dict[str, Any]] = []
    valid_boundaries = len(boundaries) == required_boundaries
    if valid_boundaries:
        for boundary in boundaries:
            metrics = boundary.get("metrics")
            valid_boundaries = valid_boundaries and isinstance(metrics, dict)
            if not valid_boundaries:
                break
            for metric in metric_names:
                value = metrics.get(metric)
                if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
                    valid_boundaries = False
                    break
            if not valid_boundaries:
                break
    if valid_boundaries:
        for previous, current in zip(boundaries, boundaries[1:]):
            metric_deltas = {
                metric: relative_delta(
                    float(current["metrics"][metric]),
                    float(previous["metrics"][metric]),
                    floor,
                )
                for metric in metric_names
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
    has_required = valid_boundaries and len(deltas) == required_deltas
    return {
        "policy_version": policy["policy_version"],
        "required_cycle_boundaries": required_boundaries,
        "observed_cycle_boundaries": len(boundaries),
        "required_consecutive_deltas": required_deltas,
        "observed_consecutive_deltas": len(deltas),
        "cyclic_max_relative_delta_tolerance": threshold,
        "relative_deltas": deltas,
        "evaluated": has_required,
        "has_required_consecutive_deltas": has_required,
        "passed": bool(has_required and all(item["within_tolerance"] for item in deltas)),
    }


def _final_metrics(case_report: dict[str, Any], policy: dict[str, Any]) -> dict[str, float] | None:
    if (
        case_report.get("status") != "completed"
        or case_report.get("four_cycles_completed") is not True
        or case_report.get("all_runtime_fields_finite") is not True
        or case_report.get("all_runtime_states_positive") is not True
        or case_report.get("cycle_convergence", {}).get("passed") is not True
    ):
        return None
    boundaries = case_report.get("cycle_boundaries")
    if not isinstance(boundaries, list) or len(boundaries) != policy["required_cycle_boundaries"]:
        return None
    metrics = boundaries[-1].get("metrics")
    if not isinstance(metrics, dict):
        return None
    result: dict[str, float] = {}
    for metric in policy["cycle_metrics"]:
        value = metrics.get(metric)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
            return None
        result[metric] = float(value)
    return result


def evaluate_sensitivity(
    case_reports: list[dict[str, Any]],
    contract: dict[str, Any],
) -> dict[str, Any]:
    policy = contract["convergence_policy"]
    floor = float(policy["relative_floor"])
    tolerances = policy["sensitivity_tolerances"]
    by_id = {item["case_id"]: item for item in case_reports}
    result: dict[str, Any] = {}
    for kind in ("mesh", "temporal", "initial_state"):
        definition = contract["campaign"]["comparisons"][kind]
        tolerance = float(tolerances[f"{kind}_max_relative_delta"])
        reference_id = definition["reference_case_id"]
        reference_metrics = _final_metrics(by_id.get(reference_id, {}), policy)
        comparisons: list[dict[str, Any]] = []
        for candidate_id in sorted(definition["candidate_case_ids"]):
            candidate_metrics = _final_metrics(by_id.get(candidate_id, {}), policy)
            if reference_metrics is None or candidate_metrics is None:
                comparisons.append(
                    {
                        "candidate_case_id": candidate_id,
                        "evaluated": False,
                        "metric_relative_deltas": {},
                        "maximum_relative_delta": None,
                        "within_tolerance": False,
                    }
                )
                continue
            metric_deltas = {
                metric: relative_delta(candidate_metrics[metric], reference_metrics[metric], floor)
                for metric in policy["cycle_metrics"]
            }
            maximum = max(metric_deltas.values())
            comparisons.append(
                {
                    "candidate_case_id": candidate_id,
                    "evaluated": True,
                    "metric_relative_deltas": metric_deltas,
                    "maximum_relative_delta": maximum,
                    "within_tolerance": maximum <= tolerance,
                }
            )
        evaluated = bool(comparisons) and all(item["evaluated"] for item in comparisons)
        result[kind] = {
            "policy_version": policy["policy_version"],
            "reference_case_id": reference_id,
            "comparison_boundary": policy["comparison_boundary"],
            "maximum_relative_delta_tolerance": tolerance,
            "comparisons": comparisons,
            "evaluated": evaluated,
            "within_tolerance": bool(evaluated and all(item["within_tolerance"] for item in comparisons)),
        }
    return result


def execute_one_case(payload: tuple[str, dict[str, Any], dict[str, Any]]) -> dict[str, Any]:
    project_root_text, case_spec, campaign_contract = payload
    try:
        project_root = Path(project_root_text)
        case, f39, case_summary = build_case_for_campaign(project_root, case_spec, campaign_contract)
        from aeolus1d.bc.transient import Clock
        from aeolus1d.io.build import build_network
        from aeolus1d.io.case import dispatch_advance

        clock = Clock()
        network = build_network(case, clock=clock)
        crank_validation = validate_runtime_crank_on_network(case, network)
        f39_contract = f39.load_json(project_root / F39_CONTRACT_PATH)
        cycle_duration = float(f39_contract["numerical_policy"]["expected_duration_s"])
        boundaries = advance_four_cycles(
            case=case,
            network=network,
            clock=clock,
            dispatch_fn=dispatch_advance,
            boundary_builder=lambda pipes, components: collect_boundary_state(f39, pipes, components),
            cycle_duration_s=cycle_duration,
            cycles=int(campaign_contract["campaign"]["cycles_per_case"]),
            maximum_steps_per_cycle=int(f39_contract["numerical_policy"]["maximum_steps"]),
            completion_relative_tolerance=float(f39_contract["numerical_policy"]["time_completion_relative_tolerance"]),
        )
        convergence = evaluate_cycle_convergence(boundaries, campaign_contract["convergence_policy"])
        completed = len(boundaries) == 4 and all(item["cycle_window_completed"] for item in boundaries)
        finite = completed and all(item["finite_fields"] for item in boundaries)
        positive = finite and all(item["positive_state"] for item in boundaries)
        return {
            "case_id": case_spec["case_id"],
            "case_spec": case_spec,
            "status": "completed" if completed else "incomplete",
            "backend": "aeolus1d",
            "backend_version": importlib.metadata.version("aeolus1d"),
            "case_summary": case_summary,
            "crank_validation": crank_validation,
            "runtime_network_build_count": 1,
            "cycle_boundaries": boundaries,
            "four_cycles_completed": completed,
            "all_runtime_fields_finite": finite,
            "all_runtime_states_positive": positive,
            "cycle_convergence": convergence,
        }
    except Exception as exc:  # Le rapport doit rester disponible et fail-closed.
        return {
            "case_id": case_spec.get("case_id", "unknown"),
            "case_spec": case_spec,
            "status": "execution_failed",
            "error_class": type(exc).__name__,
            "error": str(exc),
            "runtime_network_build_count": 0,
            "cycle_boundaries": [],
            "four_cycles_completed": False,
            "all_runtime_fields_finite": False,
            "all_runtime_states_positive": False,
            "cycle_convergence": {
                "evaluated": False,
                "has_required_consecutive_deltas": False,
                "passed": False,
                "relative_deltas": [],
            },
        }


def run_parallel_cases(
    project_root: Path,
    contract: dict[str, Any],
    cases: list[dict[str, Any]],
    workers: int,
) -> list[dict[str, Any]]:
    limits = contract["campaign"]["parallelism"]
    require(limits["minimum_workers"] <= workers <= limits["maximum_workers"], "workers must be between 1 and 6")
    payloads = [(str(project_root), item, contract) for item in sorted(cases, key=lambda value: value["case_id"])]
    with ProcessPoolExecutor(max_workers=workers) as executor:
        reports = list(executor.map(execute_one_case, payloads))
    return sorted(reports, key=lambda item: item["case_id"])


def derive_numerical_gates(
    *,
    source_hashes_verified: bool,
    matrix_validated: bool,
    case_reports: list[dict[str, Any]],
    sensitivity: dict[str, Any],
) -> dict[str, bool]:
    reported_ids = [item.get("case_id") for item in case_reports]
    all_cases_present = (
        len(reported_ids) == 6
        and len(set(reported_ids)) == 6
        and set(reported_ids) == set(EXPECTED_CASES)
    )
    completed = all_cases_present and all(item.get("four_cycles_completed") is True for item in case_reports)
    finite = completed and all(item.get("all_runtime_fields_finite") is True for item in case_reports)
    positive = finite and all(item.get("all_runtime_states_positive") is True for item in case_reports)
    deltas = completed and all(
        item.get("cycle_convergence", {}).get("has_required_consecutive_deltas") is True
        for item in case_reports
    )
    cyclic = deltas and all(item.get("cycle_convergence", {}).get("passed") is True for item in case_reports)
    return {
        "source_hashes_verified": bool(source_hashes_verified),
        "matrix_validated": bool(matrix_validated),
        "all_cases_executed_four_cycles": bool(completed),
        "all_runtime_fields_finite": bool(finite),
        "all_runtime_states_positive": bool(positive),
        "all_cases_have_three_consecutive_deltas": bool(deltas),
        "aggregate_cycle_boundary_convergence_all_cases_demonstrated": bool(cyclic),
        "mesh_sensitivity_evaluated": bool(sensitivity.get("mesh", {}).get("evaluated")),
        "mesh_sensitivity_within_tolerance": bool(sensitivity.get("mesh", {}).get("within_tolerance")),
        "temporal_sensitivity_evaluated": bool(sensitivity.get("temporal", {}).get("evaluated")),
        "temporal_sensitivity_within_tolerance": bool(sensitivity.get("temporal", {}).get("within_tolerance")),
        "initial_state_sensitivity_evaluated": bool(sensitivity.get("initial_state", {}).get("evaluated")),
        "initial_state_sensitivity_within_tolerance": bool(sensitivity.get("initial_state", {}).get("within_tolerance")),
    }


def build_report(
    contract: dict[str, Any],
    project_root: Path,
    *,
    execute: bool,
    workers: int | None,
    case_executor: Callable[[Path, dict[str, Any], list[dict[str, Any]], int], list[dict[str, Any]]] = run_parallel_cases,
) -> dict[str, Any]:
    validate_contract(contract)
    sources = verify_source_bindings(project_root, contract)
    cases = validate_matrix(contract)
    case_reports: list[dict[str, Any]] = []
    sensitivity = {
        kind: {
            "policy_version": contract["convergence_policy"]["policy_version"],
            "reference_case_id": contract["campaign"]["comparisons"][kind]["reference_case_id"],
            "comparison_boundary": contract["convergence_policy"]["comparison_boundary"],
            "maximum_relative_delta_tolerance": contract["convergence_policy"]["sensitivity_tolerances"][f"{kind}_max_relative_delta"],
            "comparisons": [],
            "evaluated": False,
            "within_tolerance": False,
        }
        for kind in ("mesh", "temporal", "initial_state")
    }
    if execute:
        require(workers is not None, "--execute requires explicit --workers")
        case_reports = case_executor(project_root, contract, cases, workers)
        case_reports = sorted(case_reports, key=lambda item: item["case_id"])
        sensitivity = evaluate_sensitivity(case_reports, contract)
    elif workers is not None:
        raise F40InputError("--workers is only valid with --execute")

    gates = derive_numerical_gates(
        source_hashes_verified=True,
        matrix_validated=True,
        case_reports=case_reports,
        sensitivity=sensitivity,
    )
    return {
        "schema_version": contract["schema_version"],
        "phase": "F40",
        "asset_id": contract["asset_id"],
        "status": "numerical_campaign_executed" if execute else "numerical_campaign_manifest",
        "mode": "execute" if execute else "manifest",
        "source_bindings": sources,
        "repository_snapshot": contract["repository_snapshot"],
        "runtime_image": contract["runtime_image"],
        "authority_boundary": contract["authority_boundary"],
        "campaign": {
            "cycles_per_case": contract["campaign"]["cycles_per_case"],
            "cycle_degrees": contract["campaign"]["cycle_degrees"],
            "one_runtime_network_per_case": contract["campaign"]["one_runtime_network_per_case"],
            "state_preserved_between_cycles": contract["campaign"]["state_preserved_between_cycles"],
            "cumulative_t_start_required": contract["campaign"]["cumulative_t_start_required"],
            "workers": workers if execute else None,
            "case_matrix": cases,
            "case_reports": case_reports,
        },
        "convergence_policy": contract["convergence_policy"],
        "sensitivity": sensitivity,
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
    mode.add_argument("--manifest", action="store_true", help="Valide et publie la matrice sans execution Aeolus")
    mode.add_argument("--execute", action="store_true", help="Execute les six cas de quatre cycles")
    parser.add_argument("--workers", type=int, help="Nombre explicite de cas paralleles, entre 1 et 6")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    contract = load_json(args.contract.resolve())
    report = build_report(
        contract,
        args.project_root.resolve(),
        execute=bool(args.execute),
        workers=args.workers,
    )
    output = args.output_dir.resolve() / REPORT_NAME
    write_json(output, report)
    print(output)
    if args.execute:
        integrity_gates = (
            "all_cases_executed_four_cycles",
            "all_runtime_fields_finite",
            "all_runtime_states_positive",
            "all_cases_have_three_consecutive_deltas",
        )
        if not all(report["numerical_gates"][name] for name in integrity_gates):
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
