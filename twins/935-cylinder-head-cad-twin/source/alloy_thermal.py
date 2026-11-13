#!/usr/bin/env python3
"""Rank candidate alloys by the heat the head rejects, on one fixed mesh.

The steady thermal screen (sim_thermal.py) fixes the chamber wall temperature
and cools every other face with a film coefficient. Only the conductivity
changes between alloys, so this script reuses the deck of an existing run of
the CAD body, replaces the conductivity, and solves again with CalculiX: same
mesh, same boundary faces, same case.

Three numbers per alloy:

* heat entering at the chamber for the declared wall temperature (W);
* the thermal resistance from chamber wall to air, ``(T_wall - T_air) / Q``;
* the fin efficiency ``Q / Q_ideal``, where ``Q_ideal = h A (T_wall - T_air)``
  is the heat an isothermal body would reject through the same film area. It
  is the upper bound no conductivity can exceed at this film coefficient.

The conductivities come from ``params/alloy-candidates.json``, each with its
source and condition. The script supplies none and qualifies no alloy: the
case is a declared hypothesis set, the film coefficient is uncorrelated with
any engine, and strength at temperature is not part of this ranking.

Runs inside the cadsim image (ccx 2.21).
Usage: alloy_thermal.py REFERENCE_WORKDIR CANDIDATES.json OUT_DIR SUMMARY.json
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_thermal_balance  # noqa: E402
from sim_thermal import CASE, read_frd_temperatures  # noqa: E402

SCHEMA = "935-cad-twin-alloy-thermal/1"
CONDUCTIVITY = re.compile(r"(\*CONDUCTIVITY\n)([^\n]+)(\n)")


def deck_with(deck: str, conductivity_w_per_mmk: float) -> str:
    """The reference deck with its conductivity card replaced."""

    if len(CONDUCTIVITY.findall(deck)) != 1:
        raise SystemExit("the reference deck must hold exactly one *CONDUCTIVITY card")
    return CONDUCTIVITY.sub(lambda m: f"{m.group(1)}{conductivity_w_per_mmk:g}{m.group(3)}", deck)


def derived(heat_w: float, film_area_mm2: float) -> dict:
    """Resistance and fin efficiency of one solve under the declared case."""

    delta = CASE["chamber_wall_temperature_C"] - CASE["air_temperature_C"]
    ideal = CASE["film_coefficient_W_per_mm2K"] * film_area_mm2 * delta
    return {"thermal_resistance_K_per_W": round(delta / heat_w, 6),
            "ideal_heat_W": round(ideal, 2),
            "fin_efficiency": round(heat_w / ideal, 5)}


def solve(work: Path) -> dict:
    run = subprocess.run(["ccx", "-i", "head"], cwd=work, capture_output=True, text=True,
                         env={"OMP_NUM_THREADS": "1", "CCX_NPROC_EQUATION_SOLVER": "1", "PATH": "/usr/bin:/bin"})
    (work / "ccx.log").write_text(run.stdout + run.stderr)
    if run.returncode or not (work / "head.frd").exists():
        raise SystemExit(f"{work.name}: ccx returned {run.returncode}")
    temps = read_frd_temperatures(work / "head.frd")
    check_thermal_balance.main(work, work / "balance.json")
    balance = json.loads((work / "balance.json").read_text())
    # The field files are large and regenerate from the deck: keep the deck and the scalars.
    for name in ("head.frd", "head.dat", "head.12d", "head.cvg", "head.sta"):
        (work / name).unlink(missing_ok=True)
    return {"temperature_C": {"min": round(float(temps.min()), 3), "mean_nodal": round(float(temps.mean()), 3),
                              "p95": round(float(np.percentile(temps, 95)), 3)},
            "heat_W": balance["chamber_inflow_W"],
            "convective_loss_W": balance["convective_loss_W"],
            "relative_imbalance": balance["relative_imbalance"],
            "film_area_mm2": balance["film_area_mm2"]}


def main(reference, candidates, out_dir, summary) -> None:
    reference, out_dir = Path(reference), Path(out_dir)
    spec = json.loads(Path(candidates).read_text())
    deck = (reference / "head.inp").read_text()
    if out_dir.exists():
        raise SystemExit(f"{out_dir} exists: give a new private directory")
    rows, solved = [], {}
    for item in spec["candidates"]:
        k = item["conductivity_W_per_mK"]
        if k not in solved:                       # the field depends on the conductivity only
            work = out_dir / f"k{k:g}"
            work.mkdir(parents=True)
            (work / "head.inp").write_text(deck_with(deck, k * 1.0e-3))
            solved[k] = solve(work)
        result = solved[k]
        rows.append({"id": item["id"], "alloy": item["alloy"], "condition": item["condition"],
                     "conductivity_W_per_mK": k, "method": item["method"], "verification": item["verification"], **result,
                     **derived(result["heat_W"], result["film_area_mm2"])})
        print(item["id"], rows[-1]["heat_W"], rows[-1]["fin_efficiency"], flush=True)
    shutil.copyfile(candidates, out_dir / "alloy-candidates.json")
    rows.sort(key=lambda r: (-r["heat_W"], r["id"]))
    best, worst = rows[0], rows[-1]
    Path(summary).write_text(json.dumps({
        "schema": SCHEMA,
        "case": CASE,
        "distinct_conductivities_solved": len(solved),
        "reference_deck": "the v2 CAD-body thermal screen at 1.0 mm (thermal-screen-cad.json); only the conductivity changes",
        "ranking_by_heat_rejected": rows,
        "spread": {"heat_best_over_worst": round(best["heat_W"] / worst["heat_W"], 5),
                   "conductivity_best_over_worst": round(best["conductivity_W_per_mK"] / worst["conductivity_W_per_mK"], 5)},
        "claims": "a ranking under one declared hypothesis case, on conductivities quoted from the sources in "
                  "alloy-candidates.json; not an engine prediction, not a material qualification, and strength at "
                  "temperature is not considered",
    }, indent=2) + "\n")


if __name__ == "__main__":
    main(*sys.argv[1:5])
