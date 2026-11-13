#!/usr/bin/env python3
"""Join the records of steps that run in different environments.

    assemble_records.py t1s PRIVATE_DIR PARAMS_DIR
        after snap_surface.py (twin environment) and unsnap_intersections.py
        (recon image): write the intersection-free surface as STL and add the
        reversion report and the final surface to t1s-snap-summary.json.

    assemble_records.py thermal PRIVATE_DIR PARAMS_DIR LEVEL=LABEL [LEVEL=LABEL]
        after sim_surface_mc.py, sim_thermal.py and check_thermal_balance.py
        for each surface pitch: write thermal-screen.json with one entry per
        level (files t1-sim-LABEL.json, thermal-LABEL/result.json and
        balance-LABEL.json) and how the levels differ.

Only scalars are written. Nothing here computes a physical result.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def t1s(private, params) -> None:
    import trimesh

    private, params = Path(private), Path(params)
    mesh = trimesh.load(private / "t1s-clean.ply", process=False, force="mesh")
    mesh.export(private / "t1s-clean.stl")
    report = json.loads((private / "unsnap.json").read_text())
    path = params / "t1s-snap-summary.json"
    summary = json.loads(path.read_text())
    summary["intersection_reversion"] = {**report, "tool": "unsnap_intersections.py (pymeshlab self-intersection test)"}
    summary["final"] = {
        "faces": int(len(mesh.faces)),
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "volume_mm3": round(float(mesh.volume), 1),
        "self_intersecting_faces": report["final_self_intersecting_faces"],
    }
    path.write_text(json.dumps(summary, indent=2) + "\n")


def thermal(private, params, *levels) -> None:
    private, params = Path(private), Path(params)
    out = {"schema": "935-cad-twin-thermal-screen/1", "levels": {}}
    for item in levels:
        level, label = item.split("=")
        entry = json.loads((private / f"thermal-{label}" / "result.json").read_text())
        entry["surface"] = json.loads((private / f"t1-sim-{label}.json").read_text())
        entry["energy_balance"] = json.loads((private / f"balance-{label}.json").read_text())
        out["levels"][level] = entry
    rows = list(out["levels"].values())
    if len(rows) == 2:
        a, b = rows
        heat = [r["energy_balance"]["chamber_inflow_W"] for r in rows]
        out["mesh_sensitivity"] = {
            "note": "both the surface (geometry resolution) and the mesh change between levels",
            "mean_nodal_C": [r["temperature_C"]["mean_nodal"] for r in rows],
            "p95_C": [r["temperature_C"]["p95"] for r in rows],
            "min_C": [r["temperature_C"]["min"] for r in rows],
            "heat_W": heat,
            "mean_relative_difference": round(b["temperature_C"]["mean_nodal"] / a["temperature_C"]["mean_nodal"] - 1.0, 5),
            "p95_relative_difference": round(b["temperature_C"]["p95"] / a["temperature_C"]["p95"] - 1.0, 5),
            "heat_relative_difference": round(heat[1] / heat[0] - 1.0, 5),
            "min_difference_C": round(b["temperature_C"]["min"] - a["temperature_C"]["min"], 3),
        }
    out["claims"] = rows[0]["claims"]
    (params / "thermal-screen.json").write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    {"t1s": t1s, "thermal": thermal}[sys.argv[1]](*sys.argv[2:])
