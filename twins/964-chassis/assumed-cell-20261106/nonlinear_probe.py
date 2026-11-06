#!/usr/bin/env python3
"""Two bounded geometric-nonlinearity probes of frozen assumed-cell decks.

Only STEP/STATIC controls change. Elastic materials, geometry, mesh, ideal
joints, clamps and dead nodal loads are preserved; no damage or qualification.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
LINEAR_SOURCE_SHA = "ad70de944af810552a5bc3ce30fb9e0ac84aabc8d8cc1114c91637d533d076ae"
SPEC = importlib.util.spec_from_file_location("frozen_linear_solver", HERE / "solve.py")
linear = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(linear)
STATIC_CONTROLS = "0.1,1.,1.e-5,0.25"
STEP = "*STEP,NLGEOM,INC=60"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def changed_deck(original):
    lines = original.splitlines()
    linear.require(lines.count("*STEP") == 1 and lines.count("*STATIC") == 1,
                   "Require exactly the frozen single static step")
    changed = []
    for line in lines:
        if line == "*STEP":
            changed.append(STEP)
        elif line == "*STATIC":
            changed.extend([line, STATIC_CONTROLS])
        else:
            changed.append(line)
    reversed_lines = ["*STEP" if line == STEP else line for line in changed
                      if line != STATIC_CONTROLS]
    linear.require("\n".join(reversed_lines) + "\n" == original,
                   "Nonlinear deck changes extend beyond STEP/STATIC controls")
    return "\n".join(changed) + "\n"


def final_dat(path):
    """Select the last complete U/RF pair at the same actually printed time."""
    snapshots, totals, active = [], [], None
    lines = path.read_text().splitlines()
    for i, line in enumerate(lines):
        if "displacements (" in line:
            match = re.search(r"and time\s+(" + linear.FLOAT + r")", line)
            linear.require(match is not None, "Displacement time is missing")
            active = {"time": float(match.group(1).replace("D", "E")), "U": {}}
            snapshots.append(active)
            continue
        if "forces (" in line:
            active = None
        if active is not None:
            fields = line.split()
            if len(fields) == 4 and fields[0].isdigit():
                active["U"][int(fields[0])] = [float(v.replace("D", "E")) for v in fields[1:]]
        if "total force (fx,fy,fz) for set CLAMP" in line:
            match = re.search(r"and time\s+(" + linear.FLOAT + r")", line)
            linear.require(match is not None, "RF time is missing")
            for row in lines[i + 1:i + 5]:
                fields = row.split()
                if len(fields) == 3:
                    totals.append({"time": float(match.group(1).replace("D", "E")),
                                   "RF": [float(v.replace("D", "E")) for v in fields]})
                    break
    linear.require(snapshots and totals, "No complete nonlinear U/RF output")
    final, force = snapshots[-1], totals[-1]
    linear.require(abs(final["time"] - force["time"]) < 1e-10,
                   "Final displacement and force outputs have different times")
    linear.require(abs(final["time"] - 1.) < 1e-8, "Requested full load was not reached")
    linear.require(all(math.isfinite(v) for p in final["U"].values() for v in p),
                   "Nonfinite displacement")
    return final, force, [block["time"] for block in snapshots]


def probe(source, output):
    linear.require(sha(HERE / "solve.py") == LINEAR_SOURCE_SHA, "Frozen linear script changed")
    linear.require(not output.exists(), "Use a fresh private output path")
    original = json.loads((source / "result.json").read_text())
    preflight = json.loads((source / "preflight.json").read_text())
    linear.require(original["case"] == "bending" and original["mesh_size_mm"] == 80
                   and original["material"] == "laminate" and original["load_factor"] == 1
                   and original["minimum_subdivisions_per_shared_interval"] == 2,
                   "Only the frozen full-load h80 laminate bending case is admitted")
    linear.require(sha(source / "model.inp") == original["deck_sha256"], "Source deck changed")
    for path, expected in preflight["input_hashes"].items():
        linear.require(sha(path) == expected, "Upstream source hash changed")
    geometry = next(Path(p) for p in preflight["input_hashes"] if p.endswith("surfaces.json"))
    model = json.loads(geometry.read_text())
    linear.require(model["variant"] in ("baseline", "open-tunnel"), "Probe variant is out of scope")
    nodes, elements = linear.mesh(model, 80)
    loads, _ = linear.make_loads(model, nodes, elements, "bending")
    fixed = [n for n, p in nodes.items() if abs(p[0]) < 1e-8]
    output.mkdir(parents=True)
    (output / "model.inp").write_text(changed_deck((source / "model.inp").read_text()))
    manifest = {"classification": "predeclared_bounded_geometric_nonlinearity_probe",
                "variant": model["variant"], "source_directory": str(source),
                "source_deck_sha256": sha(source / "model.inp"),
                "probe_deck_sha256": sha(output / "model.inp"),
                "source_result_sha256": sha(source / "result.json"),
                "probe_script_sha256": sha(__file__),
                "frozen_linear_script_sha256": LINEAR_SOURCE_SHA,
                "input_hashes": preflight["input_hashes"], "elements": len(elements),
                "nodes": len(nodes), "changed_cards": [STEP, "*STATIC", STATIC_CONTROLS],
                "reference_geometry_material_mesh_load_clamp_unchanged": True,
                "load_path": "Static default ramp from zero to full dead nodal CLOAD over time1",
                "initial_increment": .1, "total_time": 1., "minimum_increment": 1e-5,
                "maximum_increment": .25, "maximum_increments": 60,
                "timeout_s": 600, "memory_gib": 8, "threads": 1,
                "physical_validation": False, "manufacturing_authorized": False,
                "primary_manual": "https://www.dhondt.de/ccx_2.21.pdf",
                "manual_sections": ["7.122 STATIC pp587-590", "7.124 STEP pp593-594"]}
    write(output / "preflight.json", manifest)
    try:
        elapsed = linear.run_solver(output, 8, 600)
        stdout = (output / "stdout.log").read_text()
        linear.require("Nonlinear geometric effects are taken into account" in stdout,
                       "Actual geometric-nonlinearity solver witness is missing")
        for path, expected in preflight["input_hashes"].items():
            linear.require(sha(path) == expected, "Input changed during nonlinear solve")
        final, force, times = final_dat(output / "model.dat")
        U = final["U"]
        linear.require(set(U) == set(nodes), "Final original-node output coverage mismatch")
        product = sum(sum(f[k] * U[n][k] for k in range(3)) for n, f in loads.items())
        linear.require(product > 0, "Nonpositive endpoint force-displacement product")
        weighted = product / 10000
        before = original["metrics"]["work_conjugate_floor_deflection_mm"]
        linU = json.loads((source / "displacements.json").read_text())
        result = dict(manifest, classification="executed_full_load_geometric_nonlinearity_probe",
                      elapsed_seconds=elapsed, actual_output_times=times, final_time=final["time"],
                      final_load_factor=final["time"], final_RF_time=force["time"],
                      max_abs_U_mm=max(math.sqrt(sum(v * v for v in p)) for p in U.values()),
                      max_clamp_U_mm=max(math.sqrt(sum(v * v for v in U[n])) for n in fixed),
                      endpoint_F_dot_U_Nmm=product,
                      endpoint_product_is_not_nonlinear_strain_energy_or_path_work=True,
                      force_weighted_floor_deflection_mm=weighted,
                      linear_force_weighted_floor_deflection_mm=before,
                      relative_weighted_deflection_change=weighted / before - 1,
                      maximum_original_node_U_difference_mm=max(math.dist(U[n], linU[str(n)]) for n in nodes),
                      corrected_force_balance=linear.force_balance(nodes, loads, fixed, force["RF"]),
                      reaction_moment_equilibrium_verified=False, independent_energy_verified=False,
                      material_damage_buckling_imperfection_or_strength_qualified=False,
                      DAT_sha256=sha(output / "model.dat"),
                      status="full_requested_load_reached_numerical_response_only")
        write(output / "result.json", result)
        return result
    except Exception as error:
        # The solver wrapper removes only its own timeout container. Retain
        # partial DAT/STA and any captured streams; no retuning/retry is made.
        if isinstance(error, subprocess.TimeoutExpired):
            for name, captured in (("stdout.log", error.stdout), ("stderr.log", error.stderr)):
                if captured is not None:
                    (output / name).write_bytes(captured if isinstance(captured, bytes) else captured.encode())
        write(output / "probe-failure.json", dict(manifest, status="bounded_probe_failed",
                                                  error_type=type(error).__name__, error=str(error)))
        raise


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    print(json.dumps(probe(args.source, args.output)))


if __name__ == "__main__":
    main()
