#!/usr/bin/env python3
"""Transient 3D conduction during a whole WE43 impeller build, with uncalibrated inputs."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import runpy

import numpy as np
from scipy import sparse
import trimesh

ROOT = Path(__file__).resolve().parents[3]
SOLVER_PATH = ROOT / "twins/993-engine-cooling-fan-system-f0/source/simulate_zrapid_print.py"
SOLVER = runpy.run_path(str(SOLVER_PATH))
KERNEL = SOLVER["GEOMETRY"]["load_kernel"]()
CARD = Path(__file__).with_name("lpbf-thermal-study.json")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def voxel_body(mesh, pitch):
    mesh = mesh.copy()
    mesh.apply_translation(-mesh.bounds[0])
    body = SOLVER["interior_voxels"](mesh, pitch)
    if abs(body.sum() * pitch**3 / mesh.volume - 1) > .02:
        raise ValueError("Thermal grid volume differs from CAD by more than two percent")
    return body


def validate(card, pitch, absorption, substeps):
    if pitch not in (1.0, 1.5, 2.0) or not 1 <= substeps <= 32:
        raise ValueError("Unsupported spatial or temporal resolution")
    if not math.isfinite(absorption) or not 0 < absorption <= 1:
        raise ValueError("Absorptivity must be in (0, 1]")
    for section, keys in (("process", ("power_w", "scan_speed_mm_s", "hatch_mm", "layer_mm")),
                          ("material", ("rho_kg_m3", "cp_j_kg_k", "conductivity_w_m_k")),
                          ("assumptions", ("plate_temperature_k", "ambient_temperature_k", "standoff_mm",
                                           "support_solid_fraction", "recoat_seconds_per_layer",
                                           "convection_w_m2_k", "emissivity", "cooldown_seconds"))):
        if any(not math.isfinite(card[section][key]) or card[section][key] <= 0 for key in keys):
            raise ValueError(f"Invalid {section} inputs")
    a = card["assumptions"]
    if a["support_solid_fraction"] > 1 or a["emissivity"] > 1:
        raise ValueError("Invalid support or radiation fraction")
    if abs(round(a["standoff_mm"] / pitch) * pitch - a["standoff_mm"]) > 1e-9:
        raise ValueError("Standoff must align with the thermal grid")
    if card["manufacturing_authorized"] or card["process"]["supplier_calibrated"]:
        raise ValueError("This exploratory model cannot grant process qualification")


def run(output, pitch, absorption, substeps):
    card = json.loads(CARD.read_text())
    validate(card, pitch, absorption, substeps)
    p, m, a = (card[key] for key in ("process", "material", "assumptions"))
    report_path, surface, layers_path = (ROOT / card[key] for key in ("geometry_report", "surface", "layers"))
    inputs = {"card": CARD, "surface": surface, "layers": layers_path,
              "geometry_report": report_path, "script": Path(__file__), "reused_solver": SOLVER_PATH}
    hashes = {key: sha(path) for key, path in inputs.items()}
    report = json.loads(report_path.read_text())
    if sha(surface) != report["analysis_surface"]["sha256"]:
        raise ValueError("Surface differs from the admitted geometric report")
    if p["layer_mm"] != report["full_build_slicing"]["layer_thickness_mm"]:
        raise ValueError("Slice and process thickness differ")
    mesh = trimesh.load_mesh(surface, process=True)
    if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.body_count != 1 or mesh.volume <= 0:
        raise ValueError("A closed, consistently oriented single positive solid is required")
    mesh = KERNEL.orient(mesh, report["selected_candidate_orientation"])
    height = float(mesh.extents[2])
    with layers_path.open() as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != report["full_build_slicing"]["layer_count"]:
        raise ValueError("Incomplete physical layer schedule")
    if any(int(row["layer_index"]) != i or not math.isfinite(float(row["part_area_mm2"]))
           or float(row["part_area_mm2"]) < 0
           or not math.isfinite(float(row["z_mm"]))
           or abs(float(row["z_mm"]) - .5 * (i * p["layer_mm"] + min((i + 1) * p["layer_mm"], height))) > 1e-7
           for i, row in enumerate(rows)):
        raise ValueError("Invalid physical slice schedule")
    sliced_volume = sum(float(row["part_area_mm2"]) * min(p["layer_mm"], height - i * p["layer_mm"])
                        for i, row in enumerate(rows))
    if abs(sliced_volume / mesh.volume - 1) > .001:
        raise ValueError("Slice energy volume differs from CAD by more than 0.1 percent")

    body = voxel_body(mesh, pitch)
    part = np.pad(body, ((0, 0), (0, 0), (round(a["standoff_mm"] / pitch), 0)))
    first = np.argmax(part, axis=2)
    supports = part.any(axis=2)[:, :, None] & (np.arange(part.shape[2])[None, None, :] < first[:, :, None])
    cells = np.argwhere(part | supports)
    cells = cells[np.argsort(cells[:, 2], kind="stable")]
    grid = np.full(part.shape, -1, dtype=np.int32)
    grid[tuple(cells.T)] = np.arange(len(cells))
    is_part = part[tuple(cells.T)]
    fraction = np.where(is_part, 1., a["support_solid_fraction"])
    dx = pitch / 1000
    capacity = m["rho_kg_m3"] * m["cp_j_kg_k"] * dx**3 * fraction
    left, right = [], []
    for axis in range(3):
        s1 = [slice(None)] * 3
        s2 = s1.copy()
        s1[axis], s2[axis] = slice(None, -1), slice(1, None)
        x, y = grid[tuple(s1)], grid[tuple(s2)]
        valid = (x >= 0) & (y >= 0)
        left.extend(x[valid]); right.extend(y[valid])
    left, right = np.array(left), np.array(right)
    g_all = m["conductivity_w_m_k"] * dx * 2 * fraction[left] * fraction[right] / (fraction[left] + fraction[right])
    energy = np.zeros(part.shape[2])
    counts = np.zeros(part.shape[2], dtype=int)
    total_layers = math.ceil((height + a["standoff_mm"]) / p["layer_mm"])
    for index in range(total_layers):
        counts[min(int((index + .5) * p["layer_mm"] / pitch), len(counts) - 1)] += 1
    energy_density = p["power_w"] / (p["scan_speed_mm_s"] * p["hatch_mm"] * p["layer_mm"])
    for i, row in enumerate(rows):
        index = min(int((float(row["z_mm"]) + a["standoff_mm"]) / pitch), len(energy) - 1)
        energy[index] += energy_density * float(row["part_area_mm2"]) * min(p["layer_mm"], height - i * p["layer_mm"])
    support_volume = np.bincount(cells[~is_part, 2], minlength=len(energy)) * pitch**3 * a["support_solid_fraction"]
    energy += energy_density * support_volume
    output.mkdir(parents=True, exist_ok=False)
    temperature = np.full(len(cells), a["plate_temperature_k"])
    peak = temperature.copy()
    history, snapshots = [], []
    elapsed = absorbed = stored = rejected = residual = 0.
    for layer in range(part.shape[2]):
        n = int(np.searchsorted(cells[:, 2], layer, side="right"))
        if not n:
            continue
        valid = (left < n) & (right < n)
        i, j, g = left[valid], right[valid], g_all[valid]
        diagonal = np.bincount(np.r_[i, j], weights=np.r_[g, g], minlength=n)
        lap = sparse.csr_matrix((np.r_[diagonal, -g, -g], (np.r_[np.arange(n), i, j], np.r_[np.arange(n), j, i])), shape=(n, n))
        plate = cells[:n, 2] == 0
        exposed = 6 - np.bincount(np.r_[i, j], minlength=n) - plate.astype(int)
        plate_sink = np.where(plate, 2 * m["conductivity_w_m_k"] * dx * fraction[:n], 0.)
        weights = fraction[:n] * (cells[:n, 2] == layer)
        power = absorption * p["power_w"] * weights / weights.sum()
        scan = energy[layer] / p["power_w"]
        cooling = counts[layer] * a["recoat_seconds_per_layer"]
        # shortcut: group physical layers into macro scan/cooling phases, use resolved hatches for melt pools.
        phases = [(scan / substeps, power, "scan"), (cooling / substeps, np.zeros(n), "recoat")]
        for _ in range(substeps):
            for dt, source, phase in phases:
                if dt <= 0:
                    continue
                t = temperature[:n]
                ambient = a["ambient_temperature_k"]
                h = a["convection_w_m2_k"] + a["emissivity"] * 5.670374419e-8 * (t + ambient) * (t*t + ambient*ambient)
                gas = h * exposed * dx**2
                sink = plate_sink + gas
                bath = plate_sink * a["plate_temperature_k"] + gas * ambient
                t, error, ds, dq, de = SOLVER["implicit_step"](t, capacity[:n], lap, sink, bath, source, dt)
                temperature[:n] = t
                peak[:n] = np.maximum(peak[:n], t)
                elapsed += dt; stored += ds; rejected += dq; absorbed += de; residual = max(residual, error)
                history.append({"macro_layer": layer, "phase": phase, "time_s": elapsed,
                                "max_part_k": float(t[is_part[:n]].max()) if is_part[:n].any() else None,
                                "max_all_k": float(t.max()), "absorbed_energy_j": de})
        if layer % max(1, part.shape[2] // 20) == 0 or layer == part.shape[2] - 1:
            frame = np.full(len(cells), np.nan)
            frame[:n] = temperature[:n]
            snapshots.append(frame)
        print(f"{layer+1}/{part.shape[2]} macro layers, {n} cells, peak {peak[:n].max():.3f} K", flush=True)
    build = temperature.copy()
    build_time = elapsed
    for _ in range(12):
        t = temperature
        ambient = a["ambient_temperature_k"]
        h = a["convection_w_m2_k"] + a["emissivity"] * 5.670374419e-8 * (t + ambient) * (t*t + ambient*ambient)
        gas = h * exposed * dx**2
        temperature, error, ds, dq, de = SOLVER["implicit_step"](t, capacity, lap, plate_sink + gas,
            plate_sink * a["plate_temperature_k"] + gas * ambient, np.zeros(n), a["cooldown_seconds"] / 12)
        stored += ds; rejected += dq; absorbed += de; residual = max(residual, error)
    if hashes != {key: sha(path) for key, path in inputs.items()}:
        raise ValueError("Inputs changed during the calculation; results cannot be published")
    np.savez_compressed(output / "thermal-fields.npz", centres_mm=(cells + .5) * pitch, is_part=is_part,
                        peak_k=peak, end_build_k=build, cooled_k=temperature, snapshots=np.array(snapshots))
    write(output / "history.json", history)
    summary = {"part_id": card["part_id"], "status": "transient_3d_bulk_thermal_solve_completed",
        "orientation": report["selected_candidate_orientation"], "pitch_mm": pitch, "substeps": substeps,
        "absorptivity": absorption, "cells": len(cells), "part_cells": int(is_part.sum()),
        "hashes": hashes,
        "output_hashes": {name: sha(output / name) for name in ("thermal-fields.npz", "history.json")},
        "physical_part_layers": len(rows), "physical_layers_including_standoff": total_layers,
        "cad_volume_mm3": float(mesh.volume), "sliced_volume_mm3": sliced_volume,
        "voxel_part_volume_mm3": float(is_part.sum() * pitch**3),
        "voxel_relative_volume_error": float(is_part.sum() * pitch**3 / mesh.volume - 1),
        "assumed_support_solid_volume_mm3": float(support_volume.sum()),
        "scan_time_h": float(energy.sum() / p["power_w"] / 3600),
        "recoat_time_h": float(total_layers * a["recoat_seconds_per_layer"] / 3600),
        "build_time_h": build_time / 3600, "cooldown_seconds": a["cooldown_seconds"],
        "peak_bulk_part_k": float(peak[is_part].max()), "end_build_peak_part_k": float(build[is_part].max()),
        "cooled_peak_part_k": float(temperature[is_part].max()), "maximum_step_energy_residual": residual,
        "absorbed_energy_j": absorbed, "net_rejected_energy_j": rejected, "stored_energy_change_j": stored,
        "global_energy_residual_j": stored + rejected - absorbed,
        "cp_reference_temperature_range_exceeded": bool(peak.max() > m["cp_reference_range_k"][1]),
        "whole_geometry_resolved_within_two_percent_volume": bool(abs(is_part.sum()*pitch**3/mesh.volume - 1) < .02),
        "melt_pool_resolved": False, "powder_conduction_resolved": False, "distortion_computed": False,
        "machine_calibrated": False, "manufacturing_authorized": False}
    write(output / "summary.json", summary)
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pitch-mm", type=float, default=1.)
    parser.add_argument("--absorptivity", type=float, default=.35)
    parser.add_argument("--substeps", type=int, default=4)
    args = parser.parse_args()
    run(args.output, args.pitch_mm, args.absorptivity, args.substeps)
