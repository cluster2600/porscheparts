#!/usr/bin/env python3
"""Résume des reruns OpenFOAM interrompus après effondrement du pas de temps."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def parse_case(specification: str, minimum_horizon_s: float, collapse_threshold_s: float) -> dict:
    case_id, raw_path = specification.split("=", 1)
    case = Path(raw_path).resolve()
    log_path = case / "log.foamRun-fluid"
    solution_path = case / "system" / "fvSolution"
    require(log_path.is_file(), f"solver_log_absent:{case_id}")
    require(solution_path.is_file(), f"fvSolution_absent:{case_id}")
    solution = solution_path.read_text(encoding="utf-8", errors="replace")
    require("residualControl" not in solution, f"residualControl_present:{case_id}")
    log = log_path.read_text(encoding="utf-8", errors="replace")
    time_values = [float(value) for value in re.findall(r"^Time = ([+\-0-9.eE]+)s$", log, re.MULTILINE)]
    delta_values = [float(value) for value in re.findall(r"^deltaT = ([+\-0-9.eE]+)$", log, re.MULTILINE)]
    courant_values = [
        float(value)
        for value in re.findall(r"Courant Number mean:\s*[^\s]+\s+max:\s*([+\-0-9.eE]+)", log)
    ]
    require(time_values and delta_values and courant_values, f"solver_metrics_absent:{case_id}")
    final_time = time_values[-1]
    minimum_delta_t = min(delta_values)
    collapse = minimum_delta_t <= collapse_threshold_s and final_time < minimum_horizon_s
    require(collapse, f"time_step_collapse_not_proved:{case_id}")
    return {
        "case_id": case_id,
        "status": "TIME_STEP_COLLAPSE_FAIL",
        "solver_completed": False,
        "termination": "operator_interrupt_after_time_step_collapse",
        "PIMPLE_residualControl_present": False,
        "final_physical_time_s": final_time,
        "minimum_required_horizon_s": minimum_horizon_s,
        "minimum_horizon_reached": False,
        "last_time_step_s": delta_values[-1],
        "minimum_time_step_s": minimum_delta_t,
        "time_step_collapse_threshold_s": collapse_threshold_s,
        "maximum_Courant_number_observed": max(courant_values),
        "last_Courant_number_observed": courant_values[-1],
        "solver_log_sha256": sha256(log_path),
        "fvSolution_sha256": sha256(solution_path),
        "cause_interpretation": "numerical_instability_observed; physical_cause_not_established",
        "validation_claim": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", action="append", required=True, help="case_id=/absolute/case/path")
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--correction", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--minimum-horizon-s", type=float, default=0.005)
    parser.add_argument("--collapse-threshold-s", type=float, default=1.0e-12)
    args = parser.parse_args()
    cases = [parse_case(item, args.minimum_horizon_s, args.collapse_threshold_s) for item in args.case]
    require({case["case_id"] for case in cases} == {"2v-coarse-exhaust", "4v-coarse-exhaust"}, "rerun_case_matrix_mismatch")
    report = {
        "schema_version": "porsche-917-f49-failed-reruns/v1",
        "contract_sha256": sha256(args.contract),
        "numerical_correction_sha256": sha256(args.correction),
        "case_count": len(cases),
        "cases": cases,
        "Vast_used": False,
        "validation_claim": False,
    }
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "sha256": sha256(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
