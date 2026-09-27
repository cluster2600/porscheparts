#!/usr/bin/env python3
"""Collect run metrics from the two fan-baseline cases (pure stdlib).
Run from the deck root after ./run_case.sh for both cases."""
import json, os, re

P = json.load(open("parameters.json"))
out = {}
for case in ("caseA_published", "caseB_corrected"):
    log = open(os.path.join(case, "simpleFoam.log")).read()
    meta = json.load(open(os.path.join(case, "case_meta.json")))
    times = re.findall(r"^Time = (\d+)", log, re.M)
    p_res = [float(m) for m in re.findall(r"GAMG:  Solving for p, Initial residual = ([0-9.e+-]+)", log)]
    cont = re.findall(r"cumulative = ([-0-9.e+]+)", log)
    def last_dat(fo):
        f = os.path.join(case, "postProcessing", fo, "0", "surfaceFieldValue.dat")
        rows = [l for l in open(f) if not l.startswith("#") and l.strip()]
        toks = re.findall(r"-?\d+\.?\d*(?:e[-+]\d+)?", rows[-1])
        return float(toks[1])
    Ux, p_in, p_out = last_dat("outFlow"), last_dat("pIn"), last_dat("pOut")
    rho = P["common"]["rho_air_kg_m3"]
    A = meta["A_disc_m2"]
    out[case] = {
        "iterations": int(times[-1]) if times else None,
        "final_outer_p_initial_residual": p_res[-2] if len(p_res) > 1 else None,
        "final_continuity_cumulative": float(cont[-1]),
        "outlet_mean_Ux_m_s": Ux,
        "outlet_mass_flow_kg_s": rho * A * Ux,
        "target_mass_flow_kg_s": rho * meta["Q_l_s"] / 1000.0,
        "avg_p_inlet_Pa": p_in,
        "avg_p_outlet_Pa": p_out,
        "note": "inlet/outlet patches span the full annulus; avg_p_inlet is the duct-loss "
                "proxy balanced by the ASSUMED disc dp; pressure rise is an input, not a prediction",
    }
json.dump(out, open("run_metrics.json", "w"), indent=2)
print(json.dumps(out, indent=2))
