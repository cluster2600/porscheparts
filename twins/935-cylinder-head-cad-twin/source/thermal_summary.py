"""Assemble one thermal level and compare it with a reference level.

sim_thermal.py writes result.json in its work directory, sim_surface_mc.py
the surface report and check_thermal_balance.py the independent energy
balance. This script joins the three into one committed summary and, when a
reference summary is given, states the differences of the global quantities
against its level of the same surface pitch. It computes nothing new: every
number comes from those files.

Usage: thermal_summary.py RESULT.json SURFACE.json BALANCE.json OUT.json
                          [REFERENCE.json REFERENCE_LEVEL]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def compare(level, ref):
    t, r = level["temperature_C"], ref["temperature_C"]
    heat, heat_ref = level["energy_balance"]["chamber_inflow_W"], ref["energy_balance"]["chamber_inflow_W"]
    area = level["energy_balance"]["film_area_mm2"]
    area_ref = ref["energy_balance"]["film_area_mm2"]
    return {
        "reference_label": ref["label"],
        "mean_nodal_C": [t["mean_nodal"], r["mean_nodal"]],
        "mean_nodal_difference_C": round(t["mean_nodal"] - r["mean_nodal"], 3),
        "p95_difference_C": round(t["p95"] - r["p95"], 3),
        "min_difference_C": round(t["min"] - r["min"], 3),
        "heat_W": [heat, heat_ref],
        "heat_relative_difference": round(heat / heat_ref - 1.0, 5),
        "film_area_mm2": [area, area_ref],
        "film_area_relative_difference": round(area / area_ref - 1.0, 5),
        "volume_relative_difference": round(level["mesh"]["volume_mm3"] / ref["mesh"]["volume_mm3"] - 1.0, 5),
    }


def main(result, surface, balance, out, reference=None, reference_level=None):
    level = json.loads(Path(result).read_text())
    level["surface"] = json.loads(Path(surface).read_text())
    level["energy_balance"] = json.loads(Path(balance).read_text())
    summary = {"schema": "935-cad-twin-thermal-screen/1", "level": level, "claims": level["claims"]}
    if reference:
        ref = json.loads(Path(reference).read_text())["levels"][reference_level]
        summary["against_reference"] = compare(level, ref)
    Path(out).write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary.get("against_reference", level["temperature_C"])))


if __name__ == "__main__":
    main(*sys.argv[1:7])
