#!/usr/bin/env python3
"""Audit native compressible MRF histories; failed gates never rank performance."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import statistics

from prepare_case import CRITERIA, IMAGE


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table(path, width):
    rows = []
    for line in path.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        values = [float(v) for v in line.translate(str.maketrans("()", "  ")).split()]
        if len(values) != width or not all(math.isfinite(v) for v in values):
            raise ValueError("Malformed or nonfinite native table: " + str(path))
        if rows and values[0] <= rows[-1][0]:
            raise ValueError("Restarted or unordered history: " + str(path))
        rows.append(values)
    if not rows:
        raise ValueError("Empty native table: " + str(path))
    return rows


def window_metrics(values, window, criteria):
    before, after = values[-2*window:-window], values[-window:]
    mean, old = statistics.fmean(after), statistics.fmean(before)
    scale = abs(mean)
    if scale <= 0:
        return {"passed":False, "mean":mean}
    change = abs(mean-old)/scale
    std = statistics.pstdev(after)/scale
    spread = (max(after)-min(after))/scale
    return {"mean":mean, "previous_mean":old, "relative_mean_change":change,
            "relative_stddev":std, "relative_peak_to_peak":spread,
            "passed":change <= criteria["relative_mean_change_max"] and
            std <= criteria["relative_stddev_max"] and spread <= criteria["relative_peak_to_peak_max"]}


def evaluate(series, iterations, omega, criteria):
    """All samples come from native tables at the same complete unit-step times."""
    required = {f"{kind}_{p}" for kind in ("mass", "magnitude") for p in ("inlet", "outlet", "rotor", "stator")}
    required |= {"energy_inlet", "energy_outlet", "torque", "minima"}
    if set(series) != required:
        raise ValueError("Incomplete observable set")
    times = [r[0] for r in series["mass_inlet"]]
    if any([r[0] for r in rows] != times for rows in series.values()):
        raise ValueError("Histories do not share every sampled iteration")
    if times not in (list(range(iterations+1)), list(range(1, iterations+1))):
        raise ValueError("Complete unrestarted unit-step history ending at declared iteration required")
    window = criteria["window_iterations"]
    if len(times) < 2*window or not math.isfinite(omega) or omega == 0:
        raise ValueError("Insufficient continuous history or invalid rotation")
    flow = [r[1] for r in series["mass_outlet"]]
    torque = [r[1] for r in series["torque"]]
    power = [-omega*t for t in torque]  # Native moment is fluid-on-rotor.
    energy = [a[1]+b[1] for a,b in zip(series["energy_inlet"],series["energy_outlet"])]
    checks, balances, wall_flux, reverse, energy_errors = {}, [], [], [], []
    for i in range(len(times)-window, len(times)):
        mi, mo = series["mass_inlet"][i][1], flow[i]
        denom = max(abs(mi), abs(mo), 1e-30)
        balances.append(abs(sum(series["mass_"+p][i][1] for p in ("inlet","outlet","rotor","stator")))/denom)
        wall_flux.append(sum(series["magnitude_"+p][i][1] for p in ("rotor","stator"))/denom)
        for p in ("inlet","outlet","rotor","stator"):
            net, gross = series["mass_"+p][i][1], series["magnitude_"+p][i][1]
            if gross < 0 or gross < abs(net)-1e-10:
                raise ValueError("Gross boundary flux inconsistent with signed flux")
            if p in ("inlet","outlet"):
                if gross == 0:
                    raise ValueError("Zero gross port flux")
                reverse.append(max(0., (gross-abs(net))/(2*gross)))
        energy_errors.append(abs(energy[i]-power[i])/max(abs(power[i]),1e-30))
    checks["expected_flow_signs"] = all(r[1]<0 for r in series["mass_inlet"][-window:]) and all(v>0 for v in flow[-window:])
    checks["positive_shaft_power_and_enthalpy_rise"] = all(v>0 for v in power[-window:]) and all(v>0 for v in energy[-window:])
    checks["positive_pressure_temperature"] = all(min(r[1:])>0 for r in series["minima"])
    checks["mass_balance"] = max(balances)<=criteria["relative_mass_imbalance_max"]
    checks["impermeable_walls"] = max(wall_flux)<=criteria["relative_wall_flux_max"]
    checks["limited_port_reverse_flow"] = max(reverse)<=criteria["port_reverse_flow_fraction_max"]
    checks["shaft_work_energy_balance"] = max(energy_errors)<=criteria["relative_energy_imbalance_max"]
    metrics = {"outlet_mass_flow_kg_s":window_metrics(flow,window,criteria),
               "fluid_on_rotor_torque_z_nm":window_metrics(torque,window,criteria),
               "shaft_input_power_w":window_metrics(power,window,criteria),
               "net_outward_total_enthalpy_flux_w":window_metrics(energy,window,criteria)}
    checks["stationary_observables"] = all(v["passed"] for v in metrics.values())
    return {"checks":checks, "numerical_history_gate_passed":all(checks.values()), "metrics":metrics,
        "maximum_relative_mass_imbalance":max(balances), "maximum_relative_wall_flux":max(wall_flux),
        "maximum_port_reverse_flow_fraction":max(reverse), "maximum_relative_energy_imbalance":max(energy_errors),
        "window_iterations":window, "completed_iterations":iterations}


def residual_check(text, iterations, window, limit):
    histories, current = {}, None
    for line in text.splitlines():
        time = re.fullmatch(r"Time = (\d+)\s*",line)
        if time:
            current = int(time[1])
            histories.setdefault(current,{})
        match = re.search(r"Solving for (\w+), Initial residual = ([^,]+),",line)
        if match and current is not None:
            value = float(match[2])
            if not math.isfinite(value):
                raise ValueError("Nonfinite equation residual")
            histories[current][match[1]] = max(value,histories[current].get(match[1],0))
    required = {"p","Ux","Uy","Uz","h","k","omega"}
    selected = [histories.get(i,{}) for i in range(iterations-window+1,iterations+1)]
    if any(not required <= set(row) for row in selected):
        return {"passed":False,"reason":"incomplete_equation_residual_history"}
    maxima = {field:max(row[field] for row in selected) for field in required}
    return {"passed":max(maxima.values())<=limit,"initial_residual_maxima":maxima,"limit":limit}


def audit(case):
    manifest = json.loads((case/"case-manifest.json").read_text())
    execution = json.loads((case/"run-solve.json").read_text())
    mesh = json.loads((case/"run-mesh.json").read_text())
    if list(case.glob("FAILED*.json")):
        raise ValueError("Failed execution marker present")
    if manifest.get("schema") != "bionic-turbo-compressible-mrf/v1" or manifest.get("image") != IMAGE or manifest.get("criteria") != CRITERIA:
        raise ValueError("Unexpected schema, solver image or acceptance criteria")
    for report in (execution,mesh):
        if report.get("status") != "completed" or report.get("case_manifest_sha256") != sha(case/"case-manifest.json"):
            raise ValueError("Unverified mesh or solver execution")
        for stage in report["stages"]:
            log = case/stage["log"]
            if stage["exit_code"] != 0 or sha(log) != stage["sha256"] or "FOAM FATAL" in log.read_text():
                raise ValueError("Execution log mismatch or failure")
    if not mesh.get("mesh_gate_passed") or "Mesh OK." not in (case/"log.checkMesh").read_text():
        raise ValueError("Mesh checks did not pass")
    inputs = {"case-manifest.json":sha(case/"case-manifest.json"), "run-mesh.json":sha(case/"run-mesh.json"), "run-solve.json":sha(case/"run-solve.json")}
    for name, expected in manifest["file_sha256"].items():
        if not (case/name).resolve().is_relative_to(case.resolve()):
            raise ValueError("Input path escapes case")
        if sha(case/name) != expected:
            raise ValueError("Prepared input changed: "+name)
        inputs[name] = expected
    for name, expected in mesh["mesh_sha256"].items():
        if not (case/name).resolve().is_relative_to(case.resolve()):
            raise ValueError("Mesh path escapes case")
        if sha(case/name) != expected:
            raise ValueError("Mesh changed after inspection: "+name)
        inputs[name] = expected
    series = {}
    for kind in ("mass","magnitude","energy"):
        for patch in (("inlet","outlet") if kind=="energy" else ("inlet","outlet","rotor","stator")):
            key = kind+"_"+patch
            path = case/"postProcessing"/key/"0/surfaceFieldValue.dat"
            rows = table(path,3 if kind=="energy" else 2)
            series[key] = [[r[0],r[1]+.5*r[2]] for r in rows] if kind=="energy" else rows
            inputs[str(path.relative_to(case))] = sha(path)
    path = case/"postProcessing/rotorForces/0/moment.dat"
    rows = table(path,10)
    series["torque"] = [[r[0],r[3]] for r in rows]  # total vector already includes pressure + viscous.
    inputs[str(path.relative_to(case))] = sha(path)
    path = case/"postProcessing/scalarMinima/0/volFieldValue.dat"
    series["minima"] = table(path,3)
    inputs[str(path.relative_to(case))] = sha(path)
    report = evaluate(series, manifest["steady_iterations"], manifest["rpm"]*manifest["rotation_sign"]*math.pi/30,manifest["criteria"])
    report["residuals"] = residual_check((case/"log.rhoSimpleFoam").read_text(),manifest["steady_iterations"],manifest["criteria"]["window_iterations"],manifest["criteria"]["initial_residual_max"])
    report["checks"]["equation_residuals"] = report["residuals"]["passed"]
    report["numerical_history_gate_passed"] = all(report["checks"].values())
    if any(sha(case/name)!=expected for name,expected in inputs.items()):
        raise ValueError("Input changed during audit")
    report.update({"schema":"bionic-turbo-mrf-audit/v1", "status":"numerical_history_pass" if report["numerical_history_gate_passed"] else "rejected_numerical_history",
        "input_sha256":inputs, "audit_source_sha256":sha(Path(__file__)), "mesh_independence_established":False,
        "performance_ranking_authorized":False, "efficiency_validated":False, "maximum_flow_established":False,
        "wall_resolution_qualified":False, "transient_response_validated":False, "engineering_validated":False,
        "manufacturing_authorized":False, "enthalpy_accounting":"sum(phi*(h+|U_absolute|^2/2)) at ports outside MRF versus -omega*M_fluid_on_rotor"})
    return report


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case",type=Path)
    parser.add_argument("output",type=Path)
    args=parser.parse_args()
    report=audit(args.case)
    with args.output.open("x") as stream:
        json.dump(report,stream,indent=2,allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status":report["status"],"performance_ranking_authorized":False}))
    raise SystemExit(0 if report["numerical_history_gate_passed"] else 1)
