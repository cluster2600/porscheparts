#!/usr/bin/env python3
"""Valide l'autorite F46 sans transformer un nom de solveur en preuve."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


CONTRACT = Path("twins/reference-917-engine/engine-solver-authority-f46.json")
EXPECTED_VARIANTS = [
    "917_30_turbo_5374_2v_f45",
    "917_30_turbo_5374_4v_f45",
]


def load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    contract = load(root / CONTRACT)
    if contract.get("phase") != "F46":
        errors.append("phase_must_be_F46")

    names = contract.get("name_resolution", {})
    if names.get("exact_ICEEngineFoam_executable_found_in_official_sources") is not False:
        errors.append("unproved_ICEEngineFoam_name_must_remain_false")
    if names.get("fabricated_alias_allowed") is not False:
        errors.append("fabricated_solver_alias_forbidden")
    if names.get("accepted_current_engine_framework") != "AATE_OpenFOAM_ICengines":
        errors.append("current_framework_must_be_AATE")
    if names.get("accepted_historical_counter_solver") != "OpenFOAM_3.0.x_engineFoam":
        errors.append("historical_counter_solver_must_be_engineFoam")

    locks = contract.get("source_locks", {})
    current = locks.get("current_engine_framework", {})
    if current.get("repository") != "https://github.com/OpenFOAM/ICengines":
        errors.append("AATE_repository_drift")
    if current.get("revision") != "c0f75f953d67cd325d28d1300672d14288f22934":
        errors.append("AATE_revision_drift")
    historical = locks.get("historical_counter_solver", {})
    if historical.get("repository") != "https://github.com/OpenFOAM/OpenFOAM-3.0.x":
        errors.append("engineFoam_repository_drift")
    if historical.get("revision") != "221b8ab77307b0ea3831a055bedc2cd77c1417f9":
        errors.append("engineFoam_revision_drift")
    if historical.get("executable") != "engineFoam":
        errors.append("historical_executable_must_be_engineFoam")
    if locks.get("thermochemistry", {}).get("version") != "3.2.0":
        errors.append("Cantera_must_be_3_2_0")

    comparison = contract.get("comparison_contract", {})
    if comparison.get("variants") != EXPECTED_VARIANTS:
        errors.append("exact_comparable_2v_4v_variants_required")
    if comparison.get("same_external_scan_contour_required") is not True:
        errors.append("same_scan_contour_required")
    if comparison.get("same_bore_stroke_compression_boost_fuel_and_boundary_conditions_required") is not True:
        errors.append("same_physical_boundary_conditions_required")
    if comparison.get("minimum_mesh_levels") != 3:
        errors.append("three_mesh_levels_required")
    for key, expected in (
        ("mass_and_energy_balance_limit_fraction", 0.01),
        ("mesh_convergence_limit_fraction", 0.05),
        ("cross_method_difference_limit_fraction", 0.05),
    ):
        if comparison.get(key) != expected:
            errors.append(f"{key}_must_equal_{expected}")

    evidence = contract.get("runtime_evidence_required", {})
    if not evidence or any(value is not True for value in evidence.values()):
        errors.append("all_runtime_evidence_must_be_required")

    gates = contract.get("execution_gates", {})
    if not gates or any(value is not False for value in gates.values()):
        errors.append("all_execution_gates_must_start_false")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    errors = validate(args.project_root.resolve())
    print(json.dumps({"phase": "F46", "status": "passed" if not errors else "failed", "errors": errors}, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
