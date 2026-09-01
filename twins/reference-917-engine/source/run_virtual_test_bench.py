#!/usr/bin/env python3
"""Execute the evidence gates for the 917 virtual engine test bench."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bench", type=Path, required=True)
    parser.add_argument("--systems", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    bench = json.loads(args.bench.read_text(encoding="utf-8"))
    systems = json.loads(args.systems.read_text(encoding="utf-8"))

    blockers = list(bench["critical_blockers"])
    if systems["acceptance"]["simulation_ready"]:
        blockers = [item for item in blockers if "fluid" not in item and "electrical" not in item]

    stages = []
    for item in bench["run_sequence"]:
        if item["id"] == "structural_preflight":
            status = "blocked"
            reasons = [
                "engine_mount_coordinates_and_load_limits",
                "crankshaft_output_flange_interface_and_dyno_alignment_tolerance",
            ]
        elif item["id"] == "dry_crank":
            status = "visualization_only"
            reasons = [
                "The F2 timeline can be externally driven at the declared 120 rpm.",
                "No contact force, torque, oil film, compression or inertia result is available.",
            ]
        else:
            status = "blocked"
            reasons = blockers
        stages.append({"id": item["id"], "status": status, "reasons": reasons})

    report = {
        "schema_version": "1.0.0",
        "status": "stopped_at_preflight_as_designed",
        "requested_action": "virtual_engine_start",
        "highest_completed_stage": "kinematic_dry_crank_visualization_only",
        "fired_run_executed": False,
        "stages": stages,
        "missing_parts_and_data": blockers,
        "fluid_domains": [item["id"] for item in systems["fluid_domains"]],
        "electrical_node_types": [item["id"] for item in systems["electrical_system"]["nodes"]],
        "next_release_gate": "measure_mounts_output_flange_and_starter_interface_then_validate_oil_prime_network",
        "prohibited_use": bench["prohibited_use"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
