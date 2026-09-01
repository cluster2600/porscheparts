#!/usr/bin/env python3
"""Run the sourced F15 mechanical cycle-energy closure for the Porsche 917."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONTRACT = ROOT / "twins/reference-917-engine/mechanical-cycle-closure-f15.json"

EXPECTED_PARENT_CASE_IDS = {
    "CASE-917-F14-001A-5L-NA",
    "CASE-917-F14-001A-5374-TURBO-1973",
}
EXPECTED_THERMODYNAMIC_BLOCKERS = {
    "fuel_definition",
    "combustion_calibration",
    "gas_exchange_boundaries",
    "friction_model",
    "cylinder_numbering",
    "valve_lift_profiles",
    "injection_law",
}
EXPECTED_REQUIRED_UNKNOWN_INPUTS = {
    "fuel_definition",
    "combustion_calibration",
    "gas_exchange_boundaries",
    "friction_model",
}
REQUIRED_FALSE_AUTHORITY_FLAGS = (
    "thermodynamic_solver_execution_authorized",
    "cantera_execution_authorized",
    "combustion_simulation_authorized",
    "gas_exchange_simulation_authorized",
    "turbo_simulation_authorized",
    "physicsnemo_training_authorized",
    "performance_claim_authorized",
    "fabrication_authorized",
    "metal_print_authorized",
    "engine_start_authorized",
)
REQUIRED_PROHIBITIONS = {
    "claim_that_a_thermodynamic_or_cantera_solver_ran",
    "claim_that_combustion_gas_exchange_or_turbo_was_simulated",
    "claim_that_reported_power_was_predicted_reproduced_or_proven",
    "claim_that_1600_hp_was_computed_simulated_or_proven",
    "derive_instantaneous_cylinder_bearing_or_rod_loads",
    "interpolate_or_extrapolate_a_power_or_torque_curve",
    "use_as_physicsnemo_training_data",
    "engine_hardware_or_manufacturing_release",
    "physical_engine_start_or_dyno_release",
}
EXPECTED_PATHS = {
    "fact_registry_path": "twins/reference-917-engine/classical-solver-cases-f13.json",
    "parent_benchmark_path": "twins/reference-917-engine/mechanical-benchmark-f14.json",
    "parent_runner_path": "twins/reference-917-engine/source/run_mechanical_benchmark_f14.py",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _display_path(path: Path, project_root: Path = ROOT) -> str:
    try:
        return str(path.resolve().relative_to(project_root.resolve()))
    except ValueError:
        return str(path.resolve())


def _round(value: float) -> float:
    return round(float(value), 12)


def _relative_residual(actual: float, reference: float) -> float:
    if reference == 0.0:
        return 0.0 if actual == 0.0 else math.inf
    return (actual - reference) / reference


def _index_by_id(values: Any, field: str = "id") -> dict[str, dict[str, Any]]:
    if not isinstance(values, list):
        return {}
    return {
        item[field]: item
        for item in values
        if isinstance(item, dict) and isinstance(item.get(field), str)
    }


def _load_parent_runner(project_root: Path, relative_path: str) -> Any:
    runner_path = project_root / relative_path
    spec = importlib.util.spec_from_file_location(
        "mechanical_benchmark_917_f14_for_f15",
        runner_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load F14 parent runner: {runner_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_contract(
    payload: Any,
    parent_benchmark: Any,
    fact_registry: Any,
    project_root: Path = ROOT,
) -> list[str]:
    """Validate F15 and its exact F13/F14 provenance chain."""

    if not isinstance(payload, dict):
        return ["root: expected an object"]
    if not isinstance(parent_benchmark, dict):
        return ["parent_benchmark: expected an object"]
    if not isinstance(fact_registry, dict):
        return ["fact_registry: expected an object"]

    errors: list[str] = []
    if payload.get("schema_version") != "1.0.0":
        errors.append("schema_version: expected 1.0.0")
    if payload.get("phase") != "F15-001":
        errors.append("phase: expected F15-001")
    if payload.get("status") != "sourced_mechanical_cycle_closure_ready_thermodynamic_blocked":
        errors.append("status: must remain sourced_mechanical_cycle_closure_ready_thermodynamic_blocked")
    if payload.get("asset_id") != "porsche-917-mechanical-cycle-closure-f15":
        errors.append("asset_id: unexpected asset")
    if payload.get("parent_asset_ids") != [
        "porsche-917-classical-solver-cases-f13",
        "porsche-917-mechanical-benchmark-f14",
    ]:
        errors.append("parent_asset_ids: expected the exact F13/F14 chain")

    for field, expected_path in EXPECTED_PATHS.items():
        if payload.get(field) != expected_path:
            errors.append(f"{field}: expected {expected_path}")
        elif not (project_root / expected_path).is_file():
            errors.append(f"{field}: missing file {expected_path}")

    if payload.get("thermodynamic_case_ref") != "CASE-917-F13-001":
        errors.append("thermodynamic_case_ref: expected CASE-917-F13-001")

    authority = payload.get("authority_boundary")
    if not isinstance(authority, dict):
        errors.append("authority_boundary: expected an object")
    else:
        if authority.get("mechanical_cycle_closure_execution_authorized") is not True:
            errors.append(
                "authority_boundary.mechanical_cycle_closure_execution_authorized: expected true"
            )
        for flag in REQUIRED_FALSE_AUTHORITY_FLAGS:
            if authority.get(flag) is not False:
                errors.append(f"authority_boundary.{flag}: must remain false")

    model = payload.get("model_definition")
    if not isinstance(model, dict):
        errors.append("model_definition: expected an object")
    else:
        if model.get("kind") != "deterministic_four_stroke_mechanical_cycle_energy_closure":
            errors.append("model_definition.kind: unexpected model")
        if model.get("revolutions_per_engine_cycle") != 2:
            errors.append("model_definition.revolutions_per_engine_cycle: expected 2")
        if model.get("firing_events_per_cylinder_per_engine_cycle") != 1:
            errors.append(
                "model_definition.firing_events_per_cylinder_per_engine_cycle: expected 1"
            )
        if model.get("definition_role") != "four_stroke_cycle_accounting_not_porsche_calibration":
            errors.append("model_definition.definition_role: unexpected role")
        for flag in (
            "generic_engine_defaults_used",
            "thermodynamic_state_variables_present",
            "pressure_trace_present",
            "heat_release_law_present",
            "friction_model_present",
            "volumetric_efficiency_present",
            "turbo_maps_present",
        ):
            if model.get(flag) is not False:
                errors.append(f"model_definition.{flag}: must remain false")

    approved = payload.get("approved_parent_case_ids")
    if not isinstance(approved, list) or set(approved) != EXPECTED_PARENT_CASE_IDS or len(approved) != 2:
        errors.append("approved_parent_case_ids: expected exactly the two sourced F14 anchors")
    parent_case_ids = {
        case.get("id")
        for case in parent_benchmark.get("cases", [])
        if isinstance(case, dict)
    }
    if parent_case_ids != EXPECTED_PARENT_CASE_IDS:
        errors.append("parent_benchmark.cases: exact F14 anchor set required")

    numerical = payload.get("numerical_acceptance")
    if not isinstance(numerical, dict):
        errors.append("numerical_acceptance: expected an object")
    else:
        tolerance = numerical.get("relative_closure_tolerance")
        if not isinstance(tolerance, (int, float)) or isinstance(tolerance, bool):
            errors.append("numerical_acceptance.relative_closure_tolerance: expected a number")
        elif not 0.0 < float(tolerance) <= 1e-12:
            errors.append(
                "numerical_acceptance.relative_closure_tolerance: must be in (0, 1e-12]"
            )
        if numerical.get("role") != "floating_point_identity_check_only_not_physical_acceptance":
            errors.append("numerical_acceptance.role: unexpected role")

    blockers = payload.get("thermodynamic_blockers_required")
    if not isinstance(blockers, list) or set(blockers) != EXPECTED_THERMODYNAMIC_BLOCKERS:
        errors.append("thermodynamic_blockers_required: expected the seven F13 blockers")

    solver_cases = _index_by_id(fact_registry.get("solver_cases"))
    thermodynamic_case = solver_cases.get("CASE-917-F13-001")
    if thermodynamic_case is None:
        errors.append("fact_registry.solver_cases: missing CASE-917-F13-001")
    else:
        if thermodynamic_case.get("domain") != "engine_cycle_0d_1d":
            errors.append("CASE-917-F13-001.domain: expected engine_cycle_0d_1d")
        case_blockers = thermodynamic_case.get("blocking_unknowns")
        if not isinstance(case_blockers, list) or set(case_blockers) != EXPECTED_THERMODYNAMIC_BLOCKERS:
            errors.append("CASE-917-F13-001.blocking_unknowns: exact unresolved set required")
        inputs = _index_by_id(thermodynamic_case.get("inputs"))
        unknown_inputs = {
            input_id
            for input_id, item in inputs.items()
            if item.get("required") is True and item.get("status") == "unknown"
        }
        if unknown_inputs != EXPECTED_REQUIRED_UNKNOWN_INPUTS:
            errors.append("CASE-917-F13-001.inputs: exact required unknown input set required")
        execution = thermodynamic_case.get("execution")
        if not isinstance(execution, dict):
            errors.append("CASE-917-F13-001.execution: expected an object")
        else:
            if execution.get("authorized") is not False:
                errors.append("CASE-917-F13-001.execution.authorized: must remain false")
            if execution.get("results_present") is not False:
                errors.append("CASE-917-F13-001.execution.results_present: must remain false")
            if not isinstance(execution.get("status"), str) or not execution["status"].startswith("blocked_"):
                errors.append("CASE-917-F13-001.execution.status: must remain blocked")

    f13_authority = fact_registry.get("authority_boundary")
    if not isinstance(f13_authority, dict):
        errors.append("fact_registry.authority_boundary: expected an object")
    else:
        if f13_authority.get("solver_execution_authorized") is not False:
            errors.append("fact_registry.authority_boundary.solver_execution_authorized: must remain false")
        if f13_authority.get("results_present") is not False:
            errors.append("fact_registry.authority_boundary.results_present: must remain false")

    if all(payload.get(field) == path for field, path in EXPECTED_PATHS.items()):
        try:
            parent_runner = _load_parent_runner(project_root, payload["parent_runner_path"])
            parent_errors = parent_runner.validate_contract(
                parent_benchmark,
                fact_registry,
                project_root,
            )
        except (OSError, RuntimeError, ImportError) as exc:
            errors.append(f"parent_runner: cannot validate F14: {exc}")
        else:
            errors.extend(f"parent_f14.{error}" for error in parent_errors)

    output = payload.get("output")
    if not isinstance(output, dict):
        errors.append("output: expected an object")
    else:
        if output.get("tracked") is not False:
            errors.append("output.tracked: work output must remain untracked")
        if output.get("dataset_role") != "documentary_regression_oracle_only_not_physicsnemo_training_data":
            errors.append("output.dataset_role: must not authorize training")

    prohibited = payload.get("prohibited_use")
    if not isinstance(prohibited, list) or not REQUIRED_PROHIBITIONS <= set(prohibited):
        errors.append("prohibited_use: missing fail-closed claim limits")

    return errors


def _build_closure_case(
    parent_case: dict[str, Any],
    model: dict[str, Any],
    relative_tolerance: float,
) -> dict[str, Any]:
    inputs = parent_case["resolved_inputs"]
    parent_derived = parent_case["derived"]
    cylinder_count = int(inputs["cylinder_count"]["value"])
    speed_rpm = float(inputs["reported_power_speed"]["value"])
    power_w = float(parent_derived["reported_power_w"])
    published_displacement_m3 = float(parent_derived["published_displacement_m3"])
    parent_torque_nm = float(parent_derived["torque_nm"])
    parent_bmep_pa = float(
        parent_derived["four_stroke_bmep_using_published_displacement_pa"]
    )
    revolutions_per_cycle = int(model["revolutions_per_engine_cycle"])
    firings_per_cylinder_cycle = int(
        model["firing_events_per_cylinder_per_engine_cycle"]
    )

    crankshaft_revolutions_per_second = speed_rpm / 60.0
    engine_cycles_per_second = crankshaft_revolutions_per_second / revolutions_per_cycle
    engine_cycle_period_s = 1.0 / engine_cycles_per_second
    firing_events_per_second = (
        engine_cycles_per_second * cylinder_count * firings_per_cylinder_cycle
    )
    interval_between_firing_events_s = 1.0 / firing_events_per_second
    brake_work_per_crank_revolution_j = power_w / crankshaft_revolutions_per_second
    brake_work_per_engine_cycle_j = power_w / engine_cycles_per_second
    brake_work_per_cylinder_firing_j = power_w / firing_events_per_second
    torque_reconstructed_nm = brake_work_per_engine_cycle_j / (
        2.0 * math.pi * revolutions_per_cycle
    )
    bmep_reconstructed_pa = brake_work_per_engine_cycle_j / published_displacement_m3
    power_reconstructed_w = brake_work_per_engine_cycle_j * engine_cycles_per_second

    power_relative_residual = _relative_residual(power_reconstructed_w, power_w)
    torque_relative_residual = _relative_residual(torque_reconstructed_nm, parent_torque_nm)
    bmep_relative_residual = _relative_residual(bmep_reconstructed_pa, parent_bmep_pa)
    checks = {
        "power_identity_passed": abs(power_relative_residual) <= relative_tolerance,
        "torque_identity_passed": abs(torque_relative_residual) <= relative_tolerance,
        "bmep_identity_passed": abs(bmep_relative_residual) <= relative_tolerance,
    }
    if not all(checks.values()):
        raise ValueError(f"F15 numerical closure failed for {parent_case['id']}: {checks}")

    return {
        "id": parent_case["id"].replace("F14-001A", "F15-001"),
        "variant": parent_case["variant"],
        "parent_case_id": parent_case["id"],
        "status": "passed_floating_point_mechanical_cycle_identity_only",
        "source_trace": {
            "cylinder_count": inputs["cylinder_count"],
            "reported_power": inputs["reported_power"],
            "reported_power_speed": inputs["reported_power_speed"],
            "published_displacement": inputs["published_displacement"],
            "parent_claim_status": parent_case["power_speed_pair_provenance"]["claim_status"],
        },
        "derived": {
            "crankshaft_revolutions_per_second": _round(
                crankshaft_revolutions_per_second
            ),
            "engine_cycles_per_second": _round(engine_cycles_per_second),
            "engine_cycle_period_s": _round(engine_cycle_period_s),
            "firing_events_per_second": _round(firing_events_per_second),
            "interval_between_firing_events_s": _round(
                interval_between_firing_events_s
            ),
            "brake_work_per_crank_revolution_j": _round(
                brake_work_per_crank_revolution_j
            ),
            "brake_work_per_engine_cycle_j": _round(brake_work_per_engine_cycle_j),
            "brake_work_per_cylinder_firing_j": _round(
                brake_work_per_cylinder_firing_j
            ),
            "torque_reconstructed_nm": _round(torque_reconstructed_nm),
            "bmep_reconstructed_pa": _round(bmep_reconstructed_pa),
            "bmep_reconstructed_bar": _round(bmep_reconstructed_pa / 1e5),
            "power_reconstructed_w": _round(power_reconstructed_w),
        },
        "numerical_closure": {
            "relative_tolerance": relative_tolerance,
            "power_relative_residual": _round(power_relative_residual),
            "torque_relative_residual": _round(torque_relative_residual),
            "bmep_relative_residual": _round(bmep_relative_residual),
            **checks,
            "role": "algebraic_regression_oracle_not_physical_validation",
        },
        "claim_limits": {
            "reported_power_is_input_not_prediction": True,
            "instantaneous_cylinder_pressure_computed": False,
            "instantaneous_component_loads_computed": False,
            "thermodynamic_cycle_simulated": False,
            "turbo_simulated": False,
            "dyno_correlation_complete": False,
        },
    }


def build_report(
    payload: dict[str, Any],
    parent_benchmark: dict[str, Any],
    fact_registry: dict[str, Any],
    contract_path: Path = DEFAULT_CONTRACT,
    benchmark_path: Path | None = None,
    registry_path: Path | None = None,
    project_root: Path = ROOT,
) -> dict[str, Any]:
    errors = validate_contract(payload, parent_benchmark, fact_registry, project_root)
    if errors:
        raise ValueError("invalid F15 contract:\n" + "\n".join(f"- {error}" for error in errors))

    benchmark_path = benchmark_path or project_root / payload["parent_benchmark_path"]
    registry_path = registry_path or project_root / payload["fact_registry_path"]
    parent_runner = _load_parent_runner(project_root, payload["parent_runner_path"])
    parent_report = parent_runner.build_report(
        parent_benchmark,
        fact_registry,
        config_path=benchmark_path,
        registry_path=registry_path,
        project_root=project_root,
    )
    relative_tolerance = float(
        payload["numerical_acceptance"]["relative_closure_tolerance"]
    )
    cases = [
        _build_closure_case(case, payload["model_definition"], relative_tolerance)
        for case in parent_report["cases"]
    ]

    thermodynamic_case = _index_by_id(fact_registry["solver_cases"])[
        payload["thermodynamic_case_ref"]
    ]
    inputs = thermodynamic_case["inputs"]
    missing_required_inputs = [
        item["id"]
        for item in inputs
        if item.get("required") is True and item.get("status") == "unknown"
    ]
    additional_blockers = [
        item
        for item in thermodynamic_case["blocking_unknowns"]
        if item not in missing_required_inputs
    ]

    return {
        "$comment": "Sortie F15-001: fermeture mecanique par cycle sourcée; aucun etat thermodynamique, aucune combustion et aucune preuve de puissance.",
        "schema_version": "1.0.0",
        "phase": payload["phase"],
        "status": "passed_sourced_mechanical_cycle_closure_thermodynamic_blocked",
        "generated_from": {
            "contract_path": _display_path(contract_path, project_root),
            "contract_sha256": _sha256(contract_path),
            "parent_benchmark_path": _display_path(benchmark_path, project_root),
            "parent_benchmark_sha256": _sha256(benchmark_path),
            "fact_registry_path": _display_path(registry_path, project_root),
            "fact_registry_sha256": _sha256(registry_path),
            "parent_runner_path": payload["parent_runner_path"],
            "parent_runner_sha256": _sha256(project_root / payload["parent_runner_path"]),
        },
        "model": {
            **payload["model_definition"],
            "mechanical_cycle_closure_executed": True,
            "thermodynamic_solver_executed": False,
            "cantera_executed": False,
            "combustion_simulated": False,
            "gas_exchange_simulated": False,
            "turbo_simulated": False,
        },
        "cases": cases,
        "thermodynamic_readiness": {
            "case_ref": thermodynamic_case["id"],
            "case_domain": thermodynamic_case["domain"],
            "ready": False,
            "execution_authorized": False,
            "results_present": False,
            "backend_selected": None,
            "cantera_container_prepared": False,
            "required_input_count": len(inputs),
            "missing_required_inputs": missing_required_inputs,
            "additional_blocking_unknowns": additional_blockers,
            "all_blockers": thermodynamic_case["blocking_unknowns"],
            "next_evidence_required": [
                "fuel_definition_and_versioned_chemical_mechanism",
                "measured_cylinder_pressure_or_validated_heat_release_law",
                "measured_intake_and_exhaust_pressure_temperature_boundaries",
                "validated_friction_map",
                "confirmed_cylinder_numbering_and_firing_order",
                "measured_valve_lift_profiles_and_flow_coefficients",
                "measured_injection_law",
                "traceable_dyno_correlation_with_uncertainties",
            ],
            "reason_no_cantera_container": "Sans ces entrees, une execution Cantera serait un moteur generique et non un modele Porsche 917.",
        },
        "documentary_uncomputed_claims": parent_report[
            "documentary_uncomputed_claims"
        ],
        "classical_solver_case_gate": {
            "case_917_f13_001_passed": False,
            "classical_cases_passed": 0,
            "thermodynamic_dataset_sample_created": False,
        },
        "physicsnemo_dataset_gate": {
            "dataset_ready": False,
            "training_authorized": False,
            "sample_count_added": 0,
            "reason": "Un oracle de fermeture algebrique n'est pas un champ solveur correle.",
        },
        "release_gates": {
            "performance_claim_authorized": False,
            "dyno_correlation_complete": False,
            "engine_simulation_validated": False,
            "fabrication_authorized": False,
            "metal_print_authorized": False,
            "engine_start_authorized": False,
        },
        "prohibited_use": payload["prohibited_use"],
    }


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--benchmark", type=Path)
    parser.add_argument("--registry", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(arguments)

    project_root = args.project_root.resolve()
    contract_path = args.contract.resolve()
    try:
        payload = json.loads(contract_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"F15-001: cannot read contract: {exc}")

    benchmark_path = (
        args.benchmark.resolve()
        if args.benchmark is not None
        else (project_root / payload.get("parent_benchmark_path", "")).resolve()
    )
    registry_path = (
        args.registry.resolve()
        if args.registry is not None
        else (project_root / payload.get("fact_registry_path", "")).resolve()
    )
    try:
        parent_benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
        fact_registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"F15-001: cannot read F13/F14 parent data: {exc}")

    errors = validate_contract(payload, parent_benchmark, fact_registry, project_root)
    if errors:
        raise SystemExit(
            "F15-001: invalid contract\n"
            + "\n".join(f"  - {error}" for error in errors)
        )
    output_path = (
        args.output.resolve()
        if args.output is not None
        else (project_root / payload["output"]["default_path"]).resolve()
    )
    report = build_report(
        payload,
        parent_benchmark,
        fact_registry,
        contract_path=contract_path,
        benchmark_path=benchmark_path,
        registry_path=registry_path,
        project_root=project_root,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"F15-001 OK: {len(report['cases'])} sourced cycle closures; "
        f"thermodynamic/Cantera execution remains blocked; "
        f"output={_display_path(output_path, project_root)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
