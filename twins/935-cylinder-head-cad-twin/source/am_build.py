#!/usr/bin/env python3
"""Layer-by-layer build in Adamantine: the deposition witness.

Every Adamantine case of this repository so far ran with material deposition
switched off. A build simulation adds material over time, so that path needs
its own witness before it is trusted on the head. This script runs the
smallest case whose answer is known in closed form:

    a block 20 x 8 mm in plan; a substrate 4 mm high at 300 K; two lumped
    layers of 4 mm each, added at 500 K at t = 1 s and t = 6 s; every
    boundary adiabatic; one material with constant properties.

What must come out, from the VTU files alone:

* the active volume is 640, 1,280 and 1,920 mm3 before, between and after
  the two depositions;
* with adiabatic walls and constant properties the volume-mean temperature
  is a mixing temperature. Treating a layer as its whole volume at 500 K
  gives 300, 400 and 433.33 K. A nodal method gives new nodes 500 K and
  leaves the interface nodes as they were, so half a row of cells per layer
  arrives cold: 300, 375 and 406.25 K on 2 mm cells. The witness holds the
  solver to the nodal values and reports the nominal ones beside them;
* long after each deposition the field is uniform at that temperature.

Two things this witness found on its first runs (2026-11-11), both now in
the case: a deposition box whose face lies on a cell boundary also activates
the cells beyond it, so the boxes are inset; and the input validation of
this build refuses a deposition file unless a second, literal key names it.

Deposition is read from a file of boxes (``material_deposition_method
file``): one box per lumped layer, covering the whole cross-section. There is
no laser, no powder and no mechanics here. Passing shows that the solver adds
material when and where the file says and conserves energy while doing so. It
says nothing about a process, a machine or a part.

Usage: am_build.py witness STUDY_DIR SUMMARY.json   (STUDY_DIR new, under /home)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import am_cooldown  # noqa: E402

WITNESS = {
    "length_mm": 20.0, "width_mm": 8.0, "height_mm": 12.0, "cell_mm": 2.0,
    "substrate_height_mm": 4.0, "layer_height_mm": 4.0, "deposition_times_s": [1.0, 6.0], "box_inset_mm": 0.1,
    "substrate_temperature_K": 300.0, "deposition_temperature_K": 500.0,
    "duration_s": 11.0, "time_step_s": 0.005, "output_every_steps": 100,
    "tolerance_volume_mm3": 1.0e-3, "tolerance_mean_temperature_K": 0.05, "tolerance_uniformity_K": 0.5,
}

DECK = """geometry
{{
{geometry}
  material_deposition true
  material_deposition_method file
  material_deposition_file layers.txt
  material_height {substrate}
  use_powder false
}}
physics
{{
  thermal true
  mechanical false
}}
discretization
{{
  thermal
  {{
    fe_degree 1
    quadrature gauss
  }}
}}
boundary
{{
  type adiabatic
}}
refinement
{{
  n_refinements 0
  time_steps_between_refinement 100000
}}
materials
{{
  initial_temperature {t_substrate}
  new_material_temperature {t_deposit}
  property_format polynomial
  n_materials 1
  material_0
  {{
    solidus {solidus}
    solid
    {{
      density {density}
      specific_heat {specific_heat}
      thermal_conductivity_x {conductivity}
      thermal_conductivity_y {conductivity}
      thermal_conductivity_z {conductivity}
    }}
  }}
}}
sources
{{
  n_beams 0
}}
time_stepping
{{
  method rk_fourth_order
  scan_path_for_duration false
  duration {duration}
  time_step {dt}
}}
post_processor
{{
  filename_prefix cooldown
  time_steps_between_output {every}
  additional_output_refinement 0
}}
memory_space host
verbose_output false
geometry.material_deposition_file layers.txt
"""
# The last line of the deck works around the input validation of this Adamantine build: it
# looks for a top-level key literally named "geometry.material_deposition_file" (a property
# tree count() on a dotted path) and refuses the deck otherwise, although the solver reads the
# file name from the geometry section. Measured on 2026-11-11 with rombur/adamantine:1.1.


GEOMETRY_BUILT_IN = """  import_mesh false
  dim 3
  length {length}
  height {height}
  width {width}
  length_divisions {nx}
  height_divisions {nz}
  width_divisions {ny}"""
GEOMETRY_IMPORTED = """  import_mesh true
  mesh_file /case/mesh.msh
  mesh_format gmsh
  reset_material_id true
  dim 3"""


def write_hex_mesh(path: Path, kept: np.ndarray, origin_mm, pitch_mm: float) -> dict:
    """Gmsh 2.2 hexahedra (metres) of a boolean block array; the lowest faces get boundary id 4, the others 1."""

    cells = np.argwhere(kept)
    node_id = -np.ones(tuple(n + 1 for n in kept.shape), dtype=np.int64)
    corner = (cells[:, None, :] + am_cooldown.HEX_CORNERS[None]).reshape(-1, 3)
    node_id[corner[:, 0], corner[:, 1], corner[:, 2]] = 0
    used = np.argwhere(node_id == 0)
    node_id[used[:, 0], used[:, 1], used[:, 2]] = np.arange(len(used))
    hexes = node_id[corner[:, 0], corner[:, 1], corner[:, 2]].reshape(-1, 8)
    nodes = (np.asarray(origin_mm, dtype=float) + used * pitch_mm) / 1000.0
    padded = np.pad(kept, 1)
    quads, ids = [], []
    k_min = int(cells[:, 2].min())
    for d, corners in am_cooldown.FACE_OF_DIRECTION.items():
        neighbour = padded[1 + d[0]:padded.shape[0] - 1 + d[0], 1 + d[1]:padded.shape[1] - 1 + d[1],
                           1 + d[2]:padded.shape[2] - 1 + d[2]]
        ext = np.argwhere(kept & ~neighbour)
        c = (ext[:, None, :] + am_cooldown.HEX_CORNERS[corners][None]).reshape(-1, 3)
        quads.append(node_id[c[:, 0], c[:, 1], c[:, 2]].reshape(-1, 4))
        lowest = (ext[:, 2] == k_min) if d == (0, 0, -1) else np.zeros(len(ext), dtype=bool)
        ids.append(np.where(lowest, 4, 1))
    quads, ids = np.concatenate(quads), np.concatenate(ids)
    with open(path, "w") as out:
        out.write("$MeshFormat\n2.2 0 8\n$EndMeshFormat\n$Nodes\n%d\n" % len(nodes))
        for i, q in enumerate(nodes, 1):
            out.write("%d %.12g %.12g %.12g\n" % (i, q[0], q[1], q[2]))
        out.write("$EndNodes\n$Elements\n%d\n" % (len(hexes) + len(quads)))
        for i, c in enumerate(hexes + 1, 1):
            out.write("%d 5 2 0 1 %d %d %d %d %d %d %d %d\n" % (i, *c))
        for i, (c, b) in enumerate(zip(quads + 1, ids), len(hexes) + 1):
            out.write("%d 3 2 %d 1 %d %d %d %d\n" % (i, b, *c))
        out.write("$EndElements\n")
    return {"hexahedra": int(len(hexes)), "nodes": int(len(nodes)), "exterior_faces": int(len(quads))}


def expected(w: dict) -> list:
    """Active volume and mean temperature in each interval between depositions.

    Two means are given. ``nominal`` treats a layer as its whole volume at the
    deposition temperature. ``nodal`` is what a nodal method does: the new
    nodes take the deposition temperature and the nodes of the interface keep
    theirs, so half a row of cells per layer arrives at the old temperature.
    With linear elements on equal rows the volume mean is the trapezoid rule
    over the node rows, which is what the solver's energy is.
    """

    plan = w["length_mm"] * w["width_mm"]
    rows_of = lambda height: round(height / w["cell_mm"])
    nodes = [w["substrate_temperature_K"]] * (rows_of(w["substrate_height_mm"]) + 1)
    volume, nominal = plan * w["substrate_height_mm"], w["substrate_temperature_K"]

    def trapezoid(values):
        weights = [1.0] + [2.0] * (len(values) - 2) + [1.0]
        return sum(a * b for a, b in zip(weights, values)) / sum(weights)

    out = [{"from_s": 0.0, "volume_mm3": volume, "nominal_mean_K": nominal, "nodal_mean_K": trapezoid(nodes)}]
    for t in w["deposition_times_s"]:
        added = plan * w["layer_height_mm"]
        nominal = (volume * nominal + added * w["deposition_temperature_K"]) / (volume + added)
        volume += added
        nodes = nodes + [w["deposition_temperature_K"]] * rows_of(w["layer_height_mm"])
        mixed = trapezoid(nodes)
        out.append({"from_s": t, "volume_mm3": volume, "nominal_mean_K": round(nominal, 6), "nodal_mean_K": round(mixed, 6)})
        nodes = [mixed] * len(nodes)             # adiabatic and long enough: the field is uniform before the next layer
    return out


def prepare(case: Path, imported: bool) -> None:
    w, m = WITNESS, am_cooldown.MATERIAL
    case.mkdir(parents=True, exist_ok=False)
    lines = ["3"]
    z = w["substrate_height_mm"]
    for t in w["deposition_times_s"]:
        centre = (0.5 * w["length_mm"], 0.5 * w["width_mm"], z + 0.5 * w["layer_height_mm"])
        # A box face lying on a cell boundary also activates the cells beyond it: stay inside.
        size = (w["length_mm"], w["width_mm"], w["layer_height_mm"] - 2.0 * w["box_inset_mm"])
        lines.append(" ".join(f"{v * 1.0e-3:.9g}" for v in (*centre, *size)) + f" {t:.9g} 0")
        z += w["layer_height_mm"]
    (case / "layers.txt").write_text("\n".join(lines) + "\n")
    n = [round(w[key] / w["cell_mm"]) for key in ("length_mm", "width_mm", "height_mm")]
    if imported:
        write_hex_mesh(case / "mesh.msh", np.ones(n, dtype=bool), (0.0, 0.0, 0.0), w["cell_mm"])
        geometry = GEOMETRY_IMPORTED
    else:
        geometry = GEOMETRY_BUILT_IN.format(length=w["length_mm"] * 1e-3, height=w["height_mm"] * 1e-3,
                                            width=w["width_mm"] * 1e-3, nx=n[0], ny=n[1], nz=n[2])
    (case / "cooldown.info").write_text(DECK.format(
        geometry=geometry, substrate=w["substrate_height_mm"] * 1e-3,
        t_substrate=w["substrate_temperature_K"], t_deposit=w["deposition_temperature_K"],
        solidus=m["solidus_K"], density=m["density_kg_m3"], specific_heat=m["specific_heat_J_kgK"],
        conductivity=m["conductivity_W_mK"], duration=w["duration_s"], dt=w["time_step_s"], every=w["output_every_steps"]))


def read_outputs(case: Path) -> list:
    """Time, active volume and temperature statistics of every output, from the VTU files alone.

    The files hold every cell of the final domain; a cell not yet deposited
    carries a temperature of zero at all its corners.
    """

    steps = sorted({int(p.name.split(".")[1]) for p in case.glob("cooldown.*.*.vtu")})
    rows = []
    for step in steps:
        data = am_cooldown.read_step(sorted(case.glob(f"cooldown.{step:06d}.*.vtu")) or sorted(case.glob(f"cooldown.{step}.*.vtu")))
        xyz = data["x"][data["conn"]]
        volume = np.prod(np.ptp(xyz, axis=1), axis=1)
        corner_t = data["fields"]["temperature"].astype(np.float64)[data["conn"]]
        active = corner_t.min(axis=1) > 1.0
        cell_t = corner_t.mean(axis=1)[active]
        rows.append({"time_s": round(data["time"], 6), "cells": int(len(volume)), "active_cells": int(active.sum()),
                     "volume_mm3": round(float(volume[active].sum() * 1e9), 6),
                     "mean_temperature_K": round(float(np.dot(volume[active], cell_t) / volume[active].sum()), 6),
                     "min_temperature_K": round(float(corner_t[active].min()), 4),
                     "max_temperature_K": round(float(corner_t[active].max()), 4),
                     "top_mm": round(float(xyz[active][:, :, 2].max() * 1e3), 6)})
    return rows


def judge(rows: list, w: dict) -> dict:
    """Compare every output with the closed-form expectation of its interval."""

    plan = expected(w)
    worst = {"volume_mm3": 0.0, "mean_temperature_K": 0.0}
    settled = []
    for row in rows:
        if any(abs(row["time_s"] - t) < 1e-9 for t in w["deposition_times_s"]):
            continue                                  # an output written at the very instant of a deposition
        want = [p for p in plan if p["from_s"] <= row["time_s"] + 1e-9][-1]
        worst["volume_mm3"] = max(worst["volume_mm3"], abs(row["volume_mm3"] - want["volume_mm3"]))
        worst["mean_temperature_K"] = max(worst["mean_temperature_K"], abs(row["mean_temperature_K"] - want["nodal_mean_K"]))
    for i, p in enumerate(plan):
        end = plan[i + 1]["from_s"] if i + 1 < len(plan) else w["duration_s"] + 1.0
        last = [r for r in rows if p["from_s"] < r["time_s"] < end - 1e-9]
        if last:
            settled.append({"interval_from_s": p["from_s"], "at_s": last[-1]["time_s"], "expected_nodal_K": p["nodal_mean_K"],
                            "nominal_K": p["nominal_mean_K"], "computed_K": last[-1]["mean_temperature_K"],
                            "spread_K": round(last[-1]["max_temperature_K"] - last[-1]["min_temperature_K"], 4)})
    # Every planned interval must have left an output, and the field must be uniform at the end of
    # each: a run that stops after the substrate would otherwise pass on its initial state alone.
    passed = (worst["volume_mm3"] <= w["tolerance_volume_mm3"]
              and worst["mean_temperature_K"] <= w["tolerance_mean_temperature_K"]
              and len(settled) == len(plan)
              and all(s["spread_K"] <= w["tolerance_uniformity_K"] for s in settled))
    rows_per_layer = round(w["layer_height_mm"] / w["cell_mm"])
    return {"expected": plan, "largest_volume_error_mm3": round(worst["volume_mm3"], 6),
            "largest_mean_temperature_error_K": round(worst["mean_temperature_K"], 6),
            "field_at_the_end_of_each_interval": settled,
            "heat_carried_by_a_layer_over_nominal": round((rows_per_layer - 0.5) / rows_per_layer, 4),
            "passed": bool(passed)}


def passed(cases: dict) -> bool:
    """A case counts only when its outputs hold and the solver itself ended without an error."""

    return bool(cases) and all(c["verdict"]["passed"] and c["solver"].get("returncode") == 0 for c in cases.values())


def witness(study, summary) -> None:
    study = Path(study)
    study.mkdir(parents=True, exist_ok=False)
    cases, image = {}, {}
    for name, imported in (("built_in_mesh", False), ("imported_mesh", True)):
        case = study / name
        prepare(case, imported)
        run = am_cooldown.run(case, 1)
        rows = read_outputs(case)
        verdict = judge(rows, WITNESS) if rows else {"passed": False, "reason": "the solver wrote no output"}
        cases[name] = {"solver": {k: run[k] for k in ("returncode", "wall_seconds", "mpi_ranks") if k in run},
                       "outputs_read": len(rows), "verdict": verdict}
        image = {k: v for k, v in run.items() if "image" in k}
        print(name, json.dumps({k: verdict.get(k) for k in ("passed", "largest_volume_error_mm3",
                                                             "largest_mean_temperature_error_K", "reason")}))
    Path(summary).write_text(json.dumps({
        "schema": "935-cad-twin-am-build-witness/1",
        "what": "two lumped layers added from a deposition file onto a substrate, adiabatic, constant properties; "
                "once on the solver's own mesh and once on an imported hexahedral mesh, as the head will be",
        "case": WITNESS, "material": am_cooldown.MATERIAL["label"], "image": image,
        "cases": cases,
        "passed": passed(cases),
        "found_on_the_way": [
            "a deposition box whose face lies on a cell boundary also activates the cells beyond it: boxes are inset",
            "new nodes take the deposition temperature and interface nodes keep theirs: a layer of n cell rows carries "
            "(n - 0.5) / n of its nominal heat",
            "this build's input validation refuses a deposition file unless a second, literal key names it"],
        "claims": "a software witness of material deposition and energy conservation on a block; no laser, powder, "
                  "mechanics, process or part is qualified",
    }, indent=2) + "\n")


if __name__ == "__main__":
    {"witness": witness}[sys.argv[1]](*sys.argv[2:])
