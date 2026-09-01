#!/usr/bin/env python3
"""Produce a deterministic fail-closed preflight for the 917 F8 interfaces."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from validate_interfaces_f8 import ROOT, is_missing, load_json, validate_contracts


def missing_inputs(config: dict, collection_key: str, measurement_key: str) -> list[dict[str, str]]:
    missing = []
    profiles = config["input_profiles"]
    for item in config[collection_key]:
        values = item[measurement_key]
        for field in profiles[item["input_profile"]]:
            if is_missing(values.get(field)):
                missing.append({"scope": collection_key, "id": item["id"], "input": field})
    return missing


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--mechanical", type=Path)
    parser.add_argument("--seals", type=Path)
    parser.add_argument("--ducts", type=Path)
    parser.add_argument("--external-interfaces", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    project_root = args.project_root.resolve()
    twin_root = project_root / "twins" / "reference-917-engine"
    mechanical_path = (args.mechanical or twin_root / "mechanical-connections-f8.json").resolve()
    seals_path = (args.seals or twin_root / "sealing-interfaces-f8.json").resolve()
    ducts_path = (args.ducts or twin_root / "ducts-f8.json").resolve()
    external_interfaces_path = (
        args.external_interfaces or twin_root / "external-interfaces-f8.json"
    ).resolve()

    validation = validate_contracts(
        project_root,
        mechanical_path,
        seals_path,
        ducts_path,
        external_interfaces_path,
    )
    if validation["status"] != "passed":
        report = {
            "schema_version": "1.0.0",
            "status": "invalid_contract",
            "validation_errors": validation["errors"],
            "physics_joints_authored": False,
            "pressure_boundaries_released": False,
            "flow_simulation_executed": False,
            "external_interface_geometry_released": False,
            "external_boundary_conditions_released": False,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 1

    mechanical = load_json(mechanical_path)
    seals = load_json(seals_path)
    ducts = load_json(ducts_path)
    external = load_json(external_interfaces_path)
    missing = (
        missing_inputs(mechanical, "mechanical_connections", "measurements")
        + missing_inputs(seals, "sealing_interfaces", "seal_specification")
        + missing_inputs(ducts, "ducts", "measurements")
        + missing_inputs(external, "external_interfaces", "measurements")
    )
    inputs_complete = not missing
    prohibited_use = sorted(
        set(mechanical["prohibited_use"])
        | set(seals["prohibited_use"])
        | set(ducts["prohibited_use"])
        | set(external["prohibited_use"])
    )
    report = {
        "schema_version": "1.0.0",
        "status": "inputs_complete_solver_and_authoring_still_blocked" if inputs_complete else "blocked_missing_measured_interfaces",
        "contract_validation": "passed",
        "counts": validation["counts"],
        "missing_input_count": len(missing),
        "missing_inputs": missing,
        "coverage_gaps": [
            item["id"]
            for item in ducts["ducts"]
            if item["coverage_status"].startswith("missing")
            or "unknown" in item["coverage_status"]
        ],
        "physics_joints_authored": False,
        "contact_solution_executed": False,
        "released_seal_instances": 0,
        "pressure_boundaries_released": False,
        "released_duct_instances": 0,
        "flow_simulation_executed": False,
        "registered_external_interface_instances": validation["counts"]["external_interface_instances"],
        "external_interface_geometry_released": False,
        "external_boundary_conditions_released": False,
        "maximum_authorized_use": "semantic_connectivity_and_measurement_planning_only",
        "next_action": "measure_interface_frames_sealing_surfaces_internal_duct_geometry_and_external_boundaries_then_review_each_release_gate",
        "prohibited_use": prohibited_use,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
