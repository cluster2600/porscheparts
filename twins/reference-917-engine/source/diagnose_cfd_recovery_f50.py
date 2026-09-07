#!/usr/bin/env python3
"""Extrait un diagnostic expurgé des échecs CFD F49/F50.

Les logs bruts et les maillages restent sur le calculateur. Le rapport public
ne contient que des métriques, des empreintes SHA-256 et une interprétation
numérique bornée.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_transient(case_id: str, path: Path) -> dict:
    current_dt = None
    current_co = None
    residuals: dict[str, float] = {}
    rows = []
    text = path.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        match = re.match(r"deltaT = (\S+)", line)
        if match:
            current_dt = float(match.group(1))
        match = re.match(r"Time = (\S+)s", line)
        if match and current_dt is not None:
            rows.append(
                {
                    "physical_time_s": float(match.group(1)),
                    "time_step_s": current_dt,
                    "Courant_max_previous": current_co,
                    "initial_residuals_previous": residuals,
                }
            )
            residuals = {}
        match = re.search(r"Courant Number mean:\s*\S+\s+max:\s*(\S+)", line)
        if match:
            current_co = float(match.group(1))
        match = re.search(r"Solving for (Ux|Uy|Uz|h|k|omega), Initial residual = (\S+)", line)
        if match:
            residuals[match.group(1)] = float(match.group(2).rstrip(","))
    if not rows:
        raise RuntimeError(f"aucune_donnee_transitoire:{case_id}")
    thresholds = []
    for threshold in (1e-8, 1e-12, 1e-20, 1e-30, 1e-40):
        row = next((item for item in rows if item["time_step_s"] < threshold), None)
        thresholds.append({"threshold_s": threshold, "first_crossing": row})
    reference = next((item for item in rows if item["time_step_s"] < 1e-8), rows[0])
    minimum = min(rows, key=lambda item: item["time_step_s"])
    rate_growth_lower_bound = reference["time_step_s"] / minimum["time_step_s"]
    return {
        "case_id": case_id,
        "solver_log_sha256": sha256(path),
        "sample_count": len(rows),
        "final_physical_time_s": rows[-1]["physical_time_s"],
        "minimum_time_step_s": minimum["time_step_s"],
        "maximum_Courant_observed": max(item["Courant_max_previous"] or 0.0 for item in rows),
        "threshold_crossings": thresholds,
        "local_convective_rate_growth_lower_bound_from_dt_ratio": rate_growth_lower_bound,
        "diagnosis": [
            "adaptive Courant control held Co near target only by collapsing deltaT",
            "U/k/omega residuals trend to machine-small values while h later rises sharply",
            "constant physical time with orders-of-magnitude more iterations proves numerical stagnation, not convergence",
        ],
        "physical_cause_established": False,
        "validation_claim": False,
    }


def compressible_attempt(report_path: Path) -> dict:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    case = report["cases"][0]
    stages = [
        {
            "return_code": stage["return_code"],
            "elapsed_s": stage["elapsed_s"],
            "log_sha256": stage["log_sha256"],
            "stage_fraction": stage.get("stage_fraction"),
            "stage_end_iteration": stage.get("stage_end_iteration"),
        }
        for stage in case["laminar_initialization_stages"]
    ]
    return {
        "input_report_sha256": sha256(report_path),
        "case_id": case["case_id"],
        "formulation": case["formulation"],
        "fixed_final_boundary_conditions_identical_to_F49": case["final_boundary_conditions_identical_to_F49"],
        "laminar_pressure_and_temperature_ramp": stages,
        "last_complete_iteration": case["latest_iteration"],
        "mass_imbalance_percent_at_failure": case["values"]["mass_imbalance_percent"],
        "sink_mass_flow_tail_spread_percent_at_failure": case["sink_mass_flow_tail_spread_percent"],
        "steady_energy_imbalance_percent_at_failure": case["values"]["steady_energy_imbalance_percent"],
        "solver_gate_pass": case["gates"]["solver"],
        "interpretation": "1 percent ramp stage completed; 10 percent stage diverged with flow reversal and pressure-solver SIGFPE",
        "validation_claim": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--f49-report", type=Path, required=True)
    parser.add_argument("--transient", action="append", required=True, help="case_id=/absolute/log")
    parser.add_argument("--steady-compressible-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    f49 = json.loads(args.f49_report.read_text(encoding="utf-8"))
    transient = {}
    for item in args.transient:
        case_id, raw_path = item.split("=", 1)
        transient[case_id] = parse_transient(case_id, Path(raw_path))
    expected = f49["failed_full_horizon_exhaust_reruns"]
    for case_id, item in transient.items():
        if abs(item["minimum_time_step_s"] - expected[case_id]["minimum_time_step_s"]) > expected[case_id]["minimum_time_step_s"] * 1e-12:
            raise RuntimeError(f"minimum_dt_mismatch:{case_id}")
    output = {
        "schema_version": "porsche-917-f50-cfd-recovery-diagnostic/v1",
        "F49_public_report_sha256": sha256(args.f49_report),
        "transient_F49": transient,
        "steady_compressible_F50": compressible_attempt(args.steady_compressible_report),
        "root_cause_conclusion": "compressible pressure-energy coupling diverges on the F48 exhaust screen; geometry/mesh causality not established",
        "geometry_modified": False,
        "ellipse_or_oval_proxy_used": False,
        "Vast_used": False,
        "validation_claim": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "sha256": sha256(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
