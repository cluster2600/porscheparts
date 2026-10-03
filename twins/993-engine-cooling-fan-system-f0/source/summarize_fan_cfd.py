#!/usr/bin/env python3
"""Summarize fan pilot numerics without promoting them to physical validation."""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path
import runpy
import statistics

# Reuse the repository's strict OpenFOAM function-object table reader.
table = runpy.run_path(str(Path(__file__).resolve().parents[2] /
    "m64-cylinder-head/source/flowbench-intake/audit_openfoam_flow.py"))["table"]


def diagnostics(inlet, outlet, window=100):
    if len(inlet) < 2 * window or [r[0] for r in inlet] != [r[0] for r in outlet]:
        raise ValueError("Two matching complete convergence windows required")
    if any(b[0] - a[0] != 1 for a, b in zip(inlet, inlet[1:])):
        raise ValueError("Incomplete iteration history")
    previous = statistics.fmean(r[1] for r in outlet[-2*window:-window])
    recent = [r[1] for r in outlet[-window:]]
    mean = statistics.fmean(recent)
    if mean <= 0 or any(r[1] >= 0 for r in inlet[-window:]):
        raise ValueError("Reversed or zero flow")
    imbalance = max(abs(a[1] + b[1]) / max(abs(a[1]), abs(b[1]))
                    for a, b in zip(inlet[-window:], outlet[-window:]))
    drift = abs(mean - previous) / mean
    spread = (max(recent) - min(recent)) / mean
    return {"mean_outlet_m3_s": mean, "mean_outlet_m3_h": mean * 3600,
            "maximum_relative_mass_imbalance": imbalance,
            "relative_mean_change_between_windows": drift,
            "relative_peak_to_peak_last_window": spread,
            "numerical_window_checks_passed": imbalance < .001 and drift < .001 and spread < .002}


def mrf_interface_passed(text):
    try:
        line, = [line for line in text.splitlines() if line.startswith("MRF_AUDIT ")]
        fields = dict(item.split("=") for item in line.split()[1:])
        cells, total, faces = (int(fields[k]) for k in ("cells", "totalCells", "interfaceFaces"))
        area, mean, maximum = (float(fields[k]) for k in
            ("interfaceArea_m2", "meanNormalSpeed_per_rad_s", "maxNormalSpeed_per_rad_s"))
        return ("MRF REJECTED" not in text and 0 < cells <= total and faces >= 0
                and all(math.isfinite(v) for v in (area, mean, maximum))
                and 0 <= mean <= maximum <= 1e-8
                and ((faces == 0 and area == 0 and cells == total)
                     or (faces > 0 and area > 0 and cells < total)))
    except (ValueError, KeyError):
        return False


def residual_diagnostics(log, last_iteration, window=100):
    limits = {"U": 1e-4, "p": 1e-3, "k": 1e-3, "omega": 1e-3}
    maxima = dict.fromkeys(limits, 0.)
    starts = list(re.finditer(r"^Time = ([0-9.]+)s?\s*$", log, re.M))
    expected = set(range(int(last_iteration) - window + 1, int(last_iteration) + 1))
    seen = set()
    for i, start in enumerate(starts):
        iteration = float(start[1])
        if iteration not in expected:
            continue
        if iteration in seen:
            raise ValueError("Repeated residual iteration")
        seen.add(iteration)
        block = log[start.end():starts[i+1].start() if i+1 < len(starts) else len(log)]
        values = {}
        for field, value in re.findall(r"Solving for (Ux|Uy|Uz|p|k|omega), Initial residual = ([^,\s]+)", block):
            value = float(value)
            if not math.isfinite(value) or value < 0:
                raise ValueError("Invalid nonlinear residual")
            values[field] = max(values.get(field, 0.), value)
        if set(values) != {"Ux", "Uy", "Uz", "p", "k", "omega"}:
            raise ValueError("Incomplete nonlinear residual history")
        for field, value in values.items():
            key = "U" if field.startswith("U") else field
            maxima[key] = max(maxima[key], value)
    if seen != expected:
        raise ValueError("Incomplete nonlinear residual window")
    return {"maximum_initial_residual_last_window": maxima,
            "initial_residual_acceptance_limits": limits,
            "nonlinear_residual_checks_passed": all(maxima[k] <= limits[k] for k in limits)}


def summarize(case, *, allow_running=False):
    histories = []
    for patch in ("inletFlow", "outletFlow"):
        folder = max((case / "postProcessing" / patch).iterdir(), key=lambda p: float(p.name))
        histories.append(table((folder / "surfaceFieldValue.dat").read_text(), ["Time", "sum(phi)"]))
    log = (case / "log.foamRun").read_text()
    if ("\nEnd\n" not in log and not allow_running) or "FOAM FATAL" in log:
        raise ValueError("Solver has not completed normally")
    result = diagnostics(*histories)
    force_folder = max((case / "postProcessing/rotorForces").iterdir(), key=lambda p: float(p.name))
    forces = [list(map(float, line.replace("(", " ").replace(")", " ").split()))
              for line in (force_folder / "forces.dat").read_text().splitlines()
              if line.strip() and not line.startswith("#")]
    if any(len(row) != 13 or not all(math.isfinite(v) for v in row) for row in forces):
        raise ValueError("Unexpected force/moment table")
    if [r[0] for r in forces] != [r[0] for r in histories[0]]:
        raise ValueError("Forces and flow histories do not match")
    manifest = json.loads((case / "fan-input.json").read_text())
    moment = statistics.fmean(row[9] + row[12] for row in forces[-100:])
    prior_moment = statistics.fmean(row[9] + row[12] for row in forces[-200:-100])
    moments = [row[9] + row[12] for row in forces[-100:]]
    torque_drift = abs(moment - prior_moment) / max(abs(moment), 1e-12)
    torque_spread = (max(moments) - min(moments)) / max(abs(moment), 1e-12)
    result["numerical_window_checks_passed"] &= torque_drift < .001 and torque_spread < .002
    result.update({"status": "exploratory_numerics_only", "normal_solver_exit": "\nEnd\n" in log, "last_iteration": forces[-1][0],
        "model_scope": manifest.get("model_scope", "legacy_isolated_rotor_without_alternator"),
        "alternator_envelope_included": manifest.get("alternator_envelope_included", False),
        "installed_assembly_represented": False,
        "installed_airflow_m3_s": None,
        "relative_torque_mean_change_between_windows": torque_drift,
        "relative_torque_peak_to_peak_last_window": torque_spread,
        "rpm": manifest["rpm"], "mean_fluid_torque_Nm": moment,
        "mean_shaft_power_to_fluid_W": -moment * manifest["rpm"] * math.pi / 30,
        "standard_mesh_check_passed": "Mesh OK." in (case / "log.checkMesh-standard").read_text(),
        "rotating_frame_interface_check_passed": mrf_interface_passed((case / "log.mrf-interface").read_text()),
        "extended_mesh_check_passed": "Mesh OK." in (case / "log.checkMesh").read_text(),
        "validated_airflow_m3_s": None, "grid_independence_demonstrated": False,
        "wall_resolution_qualified": False, "optimized": False,
        "input_sha256": {name: hashlib.sha256((case / name).read_bytes()).hexdigest()
            for name in ("fan-input.json", "constant/geometry/rotor.stl", "constant/MRFProperties",
                         "system/controlDict", "system/fvSchemes", "system/fvSolution", "0/U", "0/p")
                         + (("constant/geometry/alternator.stl",) if manifest.get("alternator_envelope_included") else ())}})
    result.update(residual_diagnostics(log, forces[-1][0]))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path, nargs="?")
    args = parser.parse_args()
    if args.case is None:
        inlet = [[i, -1.] for i in range(200)]
        outlet = [[i, 1.] for i in range(200)]
        assert diagnostics(inlet, outlet)["numerical_window_checks_passed"]
        outlet[-1][1] = 1.1
        assert not diagnostics(inlet, outlet)["numerical_window_checks_passed"]
        audit = "MRF_AUDIT cells=100 totalCells=100 interfaceFaces=0 interfaceArea_m2=0 meanNormalSpeed_per_rad_s=0 maxNormalSpeed_per_rad_s=0"
        assert mrf_interface_passed(audit)
        for invalid in ("", audit.replace("maxNormalSpeed_per_rad_s=0", "maxNormalSpeed_per_rad_s=nan"),
                        audit.replace("cells=100", "cells=50"), audit + "\nMRF REJECTED",
                        "MRF_AUDIT cells=50 totalCells=100 interfaceFaces=10 interfaceArea_m2=.15 meanNormalSpeed_per_rad_s=.035 maxNormalSpeed_per_rad_s=.123"):
            assert not mrf_interface_passed(invalid)
        residual_log = "".join(f"Time = {i}s\n" + "".join(
            f"Solving for {field}, Initial residual = 1e-5, Final residual = 1e-8\n"
            for field in ("Ux", "Uy", "Uz", "p", "k", "omega")) for i in (1, 2))
        assert residual_diagnostics(residual_log, 2, 2)["nonlinear_residual_checks_passed"]
        assert not residual_diagnostics(residual_log.replace("1e-5", "0.01"), 2, 2)["nonlinear_residual_checks_passed"]
        for bad in (residual_log.replace("1e-5", "nan"), residual_log.replace("for Ux", "for absent"), residual_log * 2, "Time = 2s\n"):
            try:
                residual_diagnostics(bad, 2, 2)
            except ValueError:
                pass
            else:
                raise AssertionError("Invalid residual history accepted")
        print("Fan flow diagnostic checks passed")
    else:
        result = summarize(args.case)
        (args.case / "flow-summary.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
        print(json.dumps(result, indent=2))
