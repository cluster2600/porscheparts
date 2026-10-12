#!/usr/bin/env python3
"""Run an uncalibrated blade-element / six-branch resistance sensitivity study."""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[3]
STUDY = Path(__file__).resolve().parents[1]
AERO = ROOT / "parts/993-eng-cooling-impeller-we43-f1-0001/source/cooling_impeller_f1.py"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def branches(total_flow, resistance):
    if not math.isfinite(total_flow) or total_flow < 0 or len(resistance) != 6:
        raise ValueError("Six branches and nonnegative finite flow required")
    if any(not math.isfinite(k) or k <= 0 for k in resistance):
        raise ValueError("Positive finite branch resistances required")
    conductance = [1 / math.sqrt(k) for k in resistance]
    flows = [total_flow * c / sum(conductance) for c in conductance]
    return flows, (total_flow / sum(conductance)) ** 2


def validate(card):
    if any(card[k] for k in ("manufacturing_authorized", "installed_fit_verified", "airflow_gain_verified")):
        raise ValueError("This screen cannot establish fit, performance or manufacturing qualification")
    f = card["flow_screen"]
    for key, value in f.items():
        if isinstance(value, (float, int)) and not isinstance(value, bool):
            if not math.isfinite(value) or value <= 0:
                raise ValueError("Invalid positive physical input: " + key)
    branches(1, f["branch_k_pa_per_m3_s_squared"])


def run(output):
    card = json.loads((STUDY / "study.json").read_text())
    validate(card)
    f = card["flow_screen"]
    aero = runpy.run_path(str(AERO))
    reference = aero["design_f1_rotor"]()
    aero["rotor_performance"].__globals__["air_density"] = lambda: f["rho_kg_m3"]
    spec_path = ROOT / card["rotor_parameters"]
    params = json.loads(spec_path.read_text())["parameters"]
    # shortcut: reuse the existing inviscid/cascade loss model; resolve 3D installed flow before ranking blades.
    aero["rotor_performance"].__globals__["HOUSING_SYNTHETIC_THROAT_MM"] = 2 * (card["geometry"]["fan_radius_mm"] + card["geometry"]["tip_gap_mm"])
    def interpolate(key, r):
        xs = [params[f"blade_{s}_radius_mm"]["value"] for s in ("hub", "mid", "tip")]
        values = [params[f"blade_{s}_{key}"]["value"] for s in ("hub", "mid", "tip")]
        r = min(max(r, xs[0]), xs[-1])
        return sum(values[i] * math.prod((r-xs[j])/(xs[i]-xs[j]) for j in range(3) if j != i) for i in range(3))
    cases = []
    curves = {}
    for twist in (0, -4, 4):
        rotor = copy.deepcopy(reference)
        for s in rotor["sections"]:
            r = s["radius_mm"]
            span = (r-params["blade_hub_radius_mm"]["value"])/(params["blade_tip_radius_mm"]["value"]-params["blade_hub_radius_mm"]["value"])
            stagger = interpolate("stagger_deg", r) + twist * min(max(span,0),1)
            camber = interpolate("camber_deg", r)
            s.update(chord_mm=interpolate("chord_mm", r), thickness_mm=interpolate("thickness_mm", r),
                     inlet_metal_deg=stagger+camber/2, outlet_metal_deg=stagger-camber/2,
                     stagger_deg=stagger, camber_deg=camber)
            s["solidity"] = s["chord_mm"] * rotor["blade_count"] / (2*math.pi*r)
        def performance(q):
            return aero["rotor_performance"](rotor,q,f["fan_speed_rpm"],shrouded=True,stator=False,bellmouth=True)
        curve = [performance(q/10) for q in range(5, 36, 2)]
        curves[str(twist)] = [{k:p[k] for k in ("flow_m3_s","useful_pressure_pa","shaft_power_w","stalled_station_count")} for p in curve]
        for width, length in ((500,360),(620,450),(700,500)):
            area = width*length/1e6
            core_k = f["core_k_pa_per_m3_s_squared"] * (f["core_reference_face_area_m2"]/area)**2
            for balance in (False, True):
                resistances = ([15000]*6 if balance else f["branch_k_pa_per_m3_s_squared"])
                _, branch_k = branches(1.,resistances)
                k = f["common_k_pa_per_m3_s_squared"] + core_k + branch_k
                brackets = [(a["flow_m3_s"],b["flow_m3_s"]) for a,b in zip(curve,curve[1:])
                            if a["useful_pressure_pa"]-k*a["flow_m3_s"]**2 > 0
                            and b["useful_pressure_pa"]-k*b["flow_m3_s"]**2 < 0]
                if len(brackets) != 1:
                    raise ValueError("No unique sampled stable operating-point crossing")
                lo,hi=brackets[0]
                for _ in range(28):
                    q=(lo+hi)/2
                    if performance(q)["useful_pressure_pa"] > k*q*q: lo=q
                    else: hi=q
                q=(lo+hi)/2; p=performance(q)
                flows, dp=branches(q,resistances)
                if abs(p["useful_pressure_pa"]-k*q*q)>1e-3 or p["shaft_power_w"]<=0:
                    raise ValueError("Operating point or energy sign failed")
                cases.append({"id":f"twist{twist}_core{width}x{length}_balance{int(balance)}",
                    "tip_stagger_delta_deg":twist,"core_face_mm":[width,length],"hypothetical_equal_branch_resistance":balance,
                    "flow_m3_s":q,"branch_flows_m3_s":flows,"minimum_branch_flow_m3_s":min(flows),
                    "branch_flow_cv":math.sqrt(sum((x-q/6)**2 for x in flows)/6)/(q/6),
                    "core_face_speed_m_s":q/area,"core_pressure_loss_pa":core_k*q*q,"branch_pressure_loss_pa":dp,
                    "pressure_balance_residual_pa":p["useful_pressure_pa"]-k*q*q,
                    "shaft_power_w":p["shaft_power_w"],"rpm":f["fan_speed_rpm"],
                    "stalled_station_count":p["stalled_station_count"],"collapsed_station_count":p["exit_collapsed_station_count"],
                    "engine_inlet_warming_k_if_20kw_rejected":f["core_assumed_heat_rejection_w"]/(f["rho_kg_m3"]*q*f["air_cp_j_kg_k"]),
                    "cfd_computed":False,"physical_measurement":False,"performance_accepted":False})
    baseline = next(c for c in cases if c["id"] == "twist0_core620x450_balance0")
    for c in cases:
        factor=(baseline["shaft_power_w"]/c["shaft_power_w"])**(1/3)
        c["equal_power_affinity_flow_m3_s"] = c["flow_m3_s"]*factor
        c["equal_power_affinity_rpm"] = c["rpm"]*factor
    output.mkdir(parents=True,exist_ok=False)
    report={"status":"uncalibrated_network_sensitivity_completed","measured_performance":False,
            "source_hashes":{str(p.relative_to(ROOT)):sha(p) for p in (Path(__file__),AERO,STUDY/"study.json",spec_path)},
            "baseline":baseline["id"],"cases":cases,"fan_curves":curves,
            "limitations":["Branch and core losses are hypotheses, not derived from exported 3D geometry.",
                "The porous core envelope does not resolve fins; no UA or charge outlet temperature prediction.",
                "No optimized blade accepted; full installed CFD, equal-power comparison and bench validation remain required."]}
    (output/"flow-screen.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"cases":len(cases),"baseline":baseline},indent=2))


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    run(parser.parse_args().output)
