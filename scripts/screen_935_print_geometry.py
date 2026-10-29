#!/usr/bin/env python3
"""Inspect a frozen closed study mesh; never grant manufacturing acceptance."""

import argparse
import hashlib
import json
from pathlib import Path
import time

import igl
import numpy as np
from scipy import ndimage
import trimesh


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def enclosed_air(air):
    labels, count = ndimage.label(air, ndimage.generate_binary_structure(3, 1))
    exterior = np.unique(np.concatenate([
        labels[0].ravel(), labels[-1].ravel(), labels[:, 0].ravel(),
        labels[:, -1].ravel(), labels[:, :, 0].ravel(), labels[:, :, -1].ravel(),
    ]))
    internal = np.ones(count + 1, dtype=bool)
    internal[0] = False
    internal[exterior] = False
    return internal[labels]


def cavity_screen(vertices, faces, pitch):
    if not np.isfinite(pitch) or pitch <= 0:
        raise ValueError("Positive finite grid pitch required")
    lower = np.floor(vertices.min(axis=0) / pitch) * pitch - 2 * pitch
    upper = np.ceil(vertices.max(axis=0) / pitch) * pitch + 2 * pitch
    raw_shape = np.ceil((upper - lower) / pitch)
    if not np.isfinite(raw_shape).all() or (raw_shape > 12_000_000).any():
        raise ValueError("Grid exceeds the bounded 12 million cell workload")
    shape = raw_shape.astype(int)
    if int(shape[0]) * int(shape[1]) * int(shape[2]) > 12_000_000:
        raise ValueError("Grid exceeds the bounded 12 million cell workload")
    points = (np.indices(shape).reshape(3, -1).T + 0.5) * pitch + lower
    winding = igl.fast_winding_number(vertices, faces, points).reshape(shape)
    if not np.isfinite(winding).all():
        raise ValueError("Nonfinite winding classification")
    certain_air = np.abs(winding) < 0.1
    certain_solid = np.abs(winding - 1.0) < 0.1
    uncertain = ~(certain_air | certain_solid)
    boundary = np.concatenate([
        certain_air[0].ravel(), certain_air[-1].ravel(),
        certain_air[:, 0].ravel(), certain_air[:, -1].ravel(),
        certain_air[:, :, 0].ravel(), certain_air[:, :, -1].ravel(),
    ])
    if not boundary.all():
        raise ValueError("Exterior grid boundary is not confidently air")
    optimistic = enclosed_air(~certain_solid) & certain_air
    pessimistic = enclosed_air(certain_air)
    nominal = enclosed_air(winding < 0.5)
    report = {
        "pitch_mm": pitch, "grid_shape": shape.tolist(),
        "query_count": int(winding.size),
        "uncertain_winding_cells": int(uncertain.sum()),
        "nominal_enclosed_air_cells": int(nominal.sum()),
        "nominal_enclosed_air_volume_mm3": float(nominal.sum() * pitch**3),
        "certain_air_enclosed_with_uncertain_cells_open": int(optimistic.sum()),
        "certain_air_enclosed_with_uncertain_cells_blocked": int(pessimistic.sum()),
        "method": "Approximate winding at cell centres; 6-connected air flood-fill from every grid boundary; no solid filling",
        "limitation": "Sampled connectivity can miss sub-grid walls and passages; not a depowdering or cavity-clearance certificate",
    }
    return report, points[nominal.ravel()]


def bounded_thickness(mesh, points):
    from trimesh.proximity import thickness
    # The triangle-ray fallback otherwise materializes millions of candidates at once.
    return np.concatenate([
        thickness(mesh, points[start:start + 16], method="max_sphere")
        for start in range(0, len(points), 16)
    ])


def run(args):
    started = time.monotonic()
    if digest(args.source) != args.sha256:
        raise ValueError("Source hash mismatch")
    if args.output.exists():
        raise ValueError("A fresh output directory is required")
    with np.load(args.source, allow_pickle=False) as source:
        vertices, faces = source["vertices"], source["triangles"]
    if (vertices.ndim != 2 or vertices.shape[1] != 3 or
            faces.ndim != 2 or faces.shape[1] != 3 or
            not np.issubdtype(faces.dtype, np.integer) or
            not np.isfinite(vertices).all() or not len(faces) or
            faces.min() < 0 or faces.max() >= len(vertices)):
        raise ValueError("Invalid mesh arrays")
    print("Validating the unchanged mesh", flush=True)
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    if not mesh.is_volume:
        raise ValueError("Closed, consistently wound positive-volume mesh required")
    # Reuse the repository's deterministic area-weighted face-centre sampling.
    from run_metal_am_geometry_screen import load_kernel
    kernel = load_kernel()
    if args.samples <= 0:
        raise ValueError("Positive sample count required")
    points, face_ids = kernel.deterministic_area_points(mesh, args.samples)
    args.output.mkdir(parents=True)
    print("Sampling local thickness", flush=True)
    values = bounded_thickness(mesh, points)
    if not (np.isfinite(values).all() and (values >= 0).all()):
        raise ValueError("Unresolved thickness probes")
    wall_report = {
        "method": "Trimesh max_sphere at deterministic area-weighted face centres",
        "sample_count": args.samples,
        "quantile_mm": dict(zip(["min", "p01", "p05", "median", "p95"],
                                np.quantile(values, [0, .01, .05, .5, .95]).tolist())),
        "sample_fractions_below_mm": {str(t): float(np.mean(values < t)) for t in [.5, 1, 1.5, 2]},
        "limitation": "Exploratory local thickness samples, not a certified minimum wall; thresholds are reporting bins, not process limits",
    }
    (args.output / "thickness.json").write_text(json.dumps(wall_report, indent=2) + "\n")
    np.savez_compressed(args.output / "private-thickness-probes.npz",
                        surface_points=points, face_ids=face_ids, local_thickness_mm=values)
    print("Thickness saved; evaluating orientation and air connectivity", flush=True)
    orientations = []
    for axis in range(3):
        for direction in [-1, 1]:
            vertical = mesh.face_normals[:, axis] * direction
            down = vertical < -np.cos(np.pi / 4)
            orientations.append({
                "up_axis": "XYZ"[axis], "direction": direction,
                "build_height_mm": float(mesh.extents[axis]),
                "downward_projected_area_mm2_at_45deg": float(np.sum(mesh.area_faces[down] * -vertical[down])),
            })
    cavity_report, cavity_points = cavity_screen(vertices, faces, args.pitch)
    if digest(args.source) != args.sha256:
        raise ValueError("Source changed during inspection")
    report = {
        "classification": "process_independent_study_mesh_printability_screen",
        "input_sha256": args.sha256, "scale": "owner_confirmed_1_OBJ_unit_is_1_mm",
        "vertices": len(vertices), "triangles": len(faces),
        "elapsed_seconds": time.monotonic() - started,
        "thickness": wall_report, "orientations": orientations, "cavities": cavity_report,
        "orientation_selected": False, "supports_validated": False,
        "material_or_machine_selected": False, "print_ready": False,
        "source_fidelity_accepted": False,
    }
    np.savez_compressed(args.output / "private-cavity-probes.npz",
                        nominal_enclosed_air_centres=cavity_points)
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    manifest = {p.name: digest(p) for p in sorted(args.output.iterdir())}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("sha256")
    parser.add_argument("output", type=Path)
    parser.add_argument("--pitch", type=float, default=2.0)
    parser.add_argument("--samples", type=int, default=500)
    run(parser.parse_args())
