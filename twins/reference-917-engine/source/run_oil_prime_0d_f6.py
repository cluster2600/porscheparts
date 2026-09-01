#!/usr/bin/env python3
"""Audit the measured inputs required before a 917 oil-prime calculation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def missing_inputs(values: dict) -> list[str]:
    missing = []
    for key, value in values.items():
        if value is None or value == [] or value == {} or value == "":
            missing.append(key)
    return missing


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    missing = missing_inputs(config["required_inputs"])
    solver_ready = not missing
    report = {
        "schema_version": "1.0.0",
        "status": "ready_for_solver_implementation" if solver_ready else "blocked_missing_measured_inputs",
        "solver_executed": False,
        "pressure_prediction_produced": False,
        "missing_input_count": len(missing),
        "missing_inputs": missing,
        "known_topology": config["known_topology"],
        "planned_outputs": config["planned_outputs"],
        "next_action": "populate_measured_inputs_then_implement_and_verify_mass_conserving_0D_solver",
        "prohibited_use": config["prohibited_use"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
