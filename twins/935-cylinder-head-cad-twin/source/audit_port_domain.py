"""Upstream audit for the port CFD row: is there an admissible fluid domain?

The repository rule is to establish that an input is admissible before any
solver consumes it. A steady port-flow calculation needs a closed duct from
the flange face to the chamber, with the valve, its seat and its guide in
place, and walls that are traceable to acquired data. This audit reads what
the twin holds for each port and states the verdict; it runs no solver.

Gates (declared before reading the numbers):
  1. the port's sections are closed curves along the whole centreline;
  2. at least WALL_OBSERVED_MIN of the wall points lie on acquired facets;
  3. the valve, seat and guide are modelled (hypothesis H05 retired or built).

Usage: audit_port_domain.py PARAMS_DIR HYPOTHESES.json OUT.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

WALL_OBSERVED_MIN = 0.95


def audit(fit, hypotheses):
    h05 = next(i for i in hypotheses["items"] if i["id"].startswith("H05"))
    valve_modelled = h05["status"] not in ("not_modelled", "not_modelled_in_v0")
    step = fit["method"]["station_step_mm"]
    ports = []
    for p in fit["ports"]:
        closed_all = p["closed_stations"] == p["stations"]
        gates = {
            "closed_sections_along_whole_centreline": closed_all,
            "wall_observed_share_at_least_min": p["wall_points_observed_share"] >= WALL_OBSERVED_MIN,
            "valve_seat_guide_modelled": valve_modelled,
        }
        ports.append({
            "name": p["name"],
            "centreline_length_mm": round((p["stations"] - 1) * step, 1),
            "stations": p["stations"],
            "closed_stations": p["closed_stations"],
            "lofted_length_mm": p["loft_length_mm"],
            "lofted_share_of_centreline": round(p["loft_length_mm"] / ((p["stations"] - 1) * step), 3),
            "wall_points_observed_share_on_loft": p["wall_points_observed_share"],
            "gates": gates,
            "admissible": all(gates.values()),
        })
    return {
        "schema": "935-cad-twin-port-cfd-audit/1",
        "wall_observed_min": WALL_OBSERVED_MIN,
        "hypothesis_h05_status": h05["status"],
        "ports": ports,
        "verdict": "admissible" if all(p["admissible"] for p in ports) else "not_admissible",
        "consequence": "no port-flow solver run: a flow number on this domain would record the closure "
                       "hypotheses and the missing valve, not the port",
        "retire_with": "registered sections of the port bend and valve pocket (CT, moulds or borescope, H04) "
                       "and the valve, seat and guide geometry (H05)",
    }


def main(params, hypotheses, out):
    fit = json.loads((Path(params) / "port-fit.json").read_text())
    res = audit(fit, json.loads(Path(hypotheses).read_text()))
    Path(out).write_text(json.dumps(res, indent=2) + "\n")
    for p in res["ports"]:
        print(p["name"], "admissible" if p["admissible"] else "not admissible", p["gates"])
    print("verdict:", res["verdict"])


if __name__ == "__main__":
    main(*sys.argv[1:4])
