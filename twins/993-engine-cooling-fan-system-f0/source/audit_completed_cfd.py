#!/usr/bin/env python3
"""Recheck final flow/torque windows and nonlinear residuals from native receipts."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import statistics


def audit(case):
    expected = json.loads((case / "flow-summary.json").read_text())
    log = (case / "log.foamRun").read_text()
    if "\nEnd\n" not in log or "FOAM FATAL" in log:
        raise ValueError("Missing normal solver completion")
    tables = []
    for name in ["inletFlow", "outletFlow", "rotorForces"]:
        folder = max((case / "postProcessing" / name).iterdir(), key=lambda p: float(p.name))
        path = folder / ("forces.dat" if name == "rotorForces" else "surfaceFieldValue.dat")
        rows = [[float(v) for v in line.replace("(", " ").replace(")", " ").split()]
                for line in path.read_text().splitlines() if line.strip() and not line.startswith("#")]
        if len(rows) < 200 or any(len(r) != (13 if name == "rotorForces" else 2) for r in rows):
            raise ValueError("Incomplete or malformed integral table")
        if any(not math.isfinite(v) for r in rows for v in r):
            raise ValueError("Nonfinite integral table")
        if any(b[0] - a[0] != 1 for a, b in zip(rows, rows[1:])):
            raise ValueError("Incomplete iteration history")
        tables.append(rows)
    inlet, outlet, forces = tables
    if not [r[0] for r in inlet] == [r[0] for r in outlet] == [r[0] for r in forces]:
        raise ValueError("Unmatched integral histories")
    mean = statistics.fmean(r[1] for r in outlet[-100:])
    if mean <= 0 or any(r[1] >= 0 for r in inlet[-100:]):
        raise ValueError("Reversed or zero flow")
    recent_torque = [r[9] + r[12] for r in forces[-100:]]
    torque = statistics.fmean(recent_torque)
    recomputed = {
        "mean_outlet_m3_s": mean,
        "maximum_relative_mass_imbalance": max(abs(a[1] + b[1]) / max(abs(a[1]), abs(b[1]))
                                                for a, b in zip(inlet[-100:], outlet[-100:])),
        "relative_mean_change_between_windows": abs(mean - statistics.fmean(r[1] for r in outlet[-200:-100])) / mean,
        "relative_peak_to_peak_last_window": (max(r[1] for r in outlet[-100:]) - min(r[1] for r in outlet[-100:])) / mean,
        "mean_fluid_torque_Nm": torque,
        "relative_torque_mean_change_between_windows": abs(torque - statistics.fmean(r[9] + r[12] for r in forces[-200:-100])) / abs(torque),
        "relative_torque_peak_to_peak_last_window": (max(recent_torque) - min(recent_torque)) / abs(torque),
    }
    for name, value in recomputed.items():
        if abs(value - expected[name]) > 1e-10 * max(1, abs(value)):
            raise ValueError(f"Summary disagrees with native table: {name}")
    last = int(outlet[-1][0])
    starts = list(re.finditer(r"^Time = ([0-9.]+)s?\s*$", log, re.M))
    maxima = {"U": 0., "p": 0., "k": 0., "omega": 0.}
    seen = set()
    for i, start in enumerate(starts):
        iteration = float(start[1])
        if not last - 99 <= iteration <= last:
            continue
        if iteration in seen:
            raise ValueError("Repeated residual iteration")
        seen.add(iteration)
        block = log[start.end():starts[i + 1].start() if i + 1 < len(starts) else len(log)]
        fields = set()
        for name, value in re.findall(r"Solving for (Ux|Uy|Uz|p|k|omega), Initial residual = ([^,\s]+)", block):
            if not math.isfinite(float(value)) or float(value) < 0:
                raise ValueError("Invalid residual")
            fields.add(name)
            key = "U" if name.startswith("U") else name
            maxima[key] = max(maxima[key], float(value))
        if fields != {"Ux", "Uy", "Uz", "p", "k", "omega"}:
            raise ValueError("Incomplete residual iteration")
    if seen != set(range(last - 99, last + 1)) or maxima != expected["maximum_initial_residual_last_window"]:
        raise ValueError("Residual summary disagrees with complete native window")
    integral_pass = (recomputed["maximum_relative_mass_imbalance"] < .001
                     and recomputed["relative_mean_change_between_windows"] < .001
                     and recomputed["relative_peak_to_peak_last_window"] < .002
                     and recomputed["relative_torque_mean_change_between_windows"] < .001
                     and recomputed["relative_torque_peak_to_peak_last_window"] < .002)
    residual_pass = all(maxima[k] <= v for k, v in {"U": 1e-4, "p": 1e-3, "k": 1e-3, "omega": 1e-3}.items())
    if integral_pass != expected["numerical_window_checks_passed"] or residual_pass != expected["nonlinear_residual_checks_passed"]:
        raise ValueError("Acceptance flags disagree with native receipts")
    return {"status": "native_receipts_match_summary", "last_iteration": last,
            "recomputed": recomputed, "maximum_initial_residual_last_window": maxima,
            "integral_checks_passed": integral_pass, "nonlinear_residual_checks_passed": residual_pass,
            "physical_gain_validated": False,
            "receipt_sha256": {str(p.relative_to(case)): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in sorted(case.rglob("*")) if p.is_file()}}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("case", type=Path)
    ap.add_argument("output", type=Path)
    args = ap.parse_args()
    with args.output.open("x") as stream:
        json.dump(audit(args.case), stream, indent=2, allow_nan=False)
        stream.write("\n")
    print("Native CFD receipts verified; this audit grants no numerical or physical acceptance")
