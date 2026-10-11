#!/usr/bin/env python3
"""Prove that a saved staircase mesh consists only of closed axis-aligned boxes."""
import json
from pathlib import Path
import re
import sys

import numpy as np

from prepare_case import sha
from run_case import ascii_faces, inspect_mesh, label_list

TOL = 1e-12  # Metres; below 1e-8 of the smallest admitted cell edge.


def rectangles(vertices):
    lo, hi = vertices.min(axis=1), vertices.max(axis=1)
    extent = hi - lo
    axis = np.argmin(extent, axis=1)
    rows = np.arange(len(vertices))
    if np.any(extent[rows, axis] > TOL) or np.any(np.count_nonzero(extent > TOL, axis=1) != 2):
        raise ValueError("Face is not an axis-aligned plane")
    edges = np.roll(vertices, -1, axis=1) - vertices
    area_vector = .5 * np.cross(vertices - vertices[:, :1], np.roll(vertices, -1, axis=1) - vertices[:, :1]).sum(axis=1)
    area = abs(area_vector[rows, axis])
    expected = extent[rows, (axis + 1) % 3] * extent[rows, (axis + 2) % 3]
    if np.any(abs(area - expected) > expected * 1e-7):
        raise ValueError("Face does not cover its bounding rectangle")
    sign = np.where(area_vector[rows, axis] > 0, 1, -1)
    turns = np.cross(edges, np.roll(edges, -1, axis=1))[rows, :, axis] * sign[:, None]
    if np.any(turns.min(axis=1) < -expected * 1e-7):
        raise ValueError("Non-convex face")
    return lo, hi, axis, sign, area


def box_proof(points, faces, owners, neighbours):
    """Check every face, both cell incidences, and all six box-side area sums."""
    count = int(max(owners.max(), neighbours.max(initial=-1)) + 1)
    bounds_lo = np.full((count, 3), np.inf)
    bounds_hi = np.full((count, 3), -np.inf)
    lows = np.empty((len(faces), 3)); highs = np.empty_like(lows)
    axes = np.empty(len(faces), dtype=np.int8)
    signs = np.empty(len(faces), dtype=np.int8)
    areas = np.empty(len(faces))
    lengths = np.fromiter(map(len, faces), dtype=np.int64, count=len(faces))
    for length in np.unique(lengths):
        selected = np.flatnonzero(lengths == length)
        for start in range(0, len(selected), 20000):
            ids = selected[start:start + 20000]
            vertices = points[np.stack([faces[i] for i in ids])]
            lows[ids], highs[ids], axes[ids], signs[ids], areas[ids] = rectangles(vertices)
    for cells, size in ((owners, len(owners)), (neighbours, len(neighbours))):
        np.minimum.at(bounds_lo, cells, lows[:size])
        np.maximum.at(bounds_hi, cells, highs[:size])
    extent = bounds_hi - bounds_lo
    if not np.isfinite(extent).all() or extent.min() < 1e-4:
        raise ValueError("Missing or undersized Cartesian cell")
    side_areas = np.zeros((count, 6))
    for cells, direction in ((owners, 1), (neighbours, -1)):
        size = len(cells)
        axis = axes[:size]
        upper = signs[:size] * direction > 0
        plane = (lows[:size] + highs[:size])[np.arange(size), axis] * .5
        expected_plane = np.where(upper, bounds_hi[cells, axis], bounds_lo[cells, axis])
        if np.max(np.abs(plane - expected_plane), initial=0) > TOL:
            raise ValueError("Face is not on its cell's outward bounding plane")
        np.add.at(side_areas, (cells, axis * 2 + upper), areas[:size])
    expected_areas = np.repeat(np.column_stack((extent[:, 1]*extent[:, 2], extent[:, 0]*extent[:, 2], extent[:, 0]*extent[:, 1])), 2, axis=1)
    error = float(np.max(np.abs(side_areas - expected_areas) / expected_areas))
    if error > 1e-7:
        raise ValueError("Incomplete or overlapping box-side coverage")
    return {"cells": count, "faces": len(faces), "minimum_cell_edge_m": float(extent.min()),
            "maximum_relative_side_area_error": error, "total_box_volume_m3": float(np.prod(extent, axis=1).sum()),
            "coordinate_tolerance_m": TOL, "all_cells_axis_aligned_boxes": True}


def check(case):
    manifest = json.loads((case / "case-manifest.json").read_text())
    if manifest.get("diagnostic_recipe", {}).get("snapping") is not False:
        raise ValueError("Only explicitly declared staircase diagnostics supported")
    execution = json.loads((case / "run-mesh.json").read_text())
    if execution.get("error") != "Extended checkMesh did not pass" or execution["case_manifest_sha256"] != sha(case / "case-manifest.json"):
        raise ValueError("Expected the recorded extended-check failure on these inputs")
    for stage in execution["stages"]:
        if stage["exit_code"] or sha(case / stage["log"]) != stage["sha256"]:
            raise ValueError("Native log changed or execution failed")
    log = (case / "log.checkMesh").read_text()
    if "Failed 1 mesh checks." not in log or not re.search(r"Concave cells .*number of cells: \d+", log):
        raise ValueError("Only the isolated concavity check can be investigated")
    for name, digest in manifest["file_sha256"].items():
        if not (case / name).resolve().is_relative_to(case.resolve()) or sha(case / name) != digest:
            raise ValueError("Prepared input changed")
    topology = inspect_mesh(case, manifest["surface"]["boundary_topology"])
    mesh = case / "constant/polyMesh"
    raw = re.sub(r"/\*.*?\*/|//[^\n]*", "", (mesh / "points").read_text(), flags=re.S)
    match = re.fullmatch(r"\s*FoamFile\s*\{[^{}]*\bformat\s+ascii\s*;[^{}]*\}\s*(\d+)\s*\((.*)\)\s*", raw, re.S)
    if not match:
        raise ValueError("Complete ASCII points required")
    points = np.fromstring(match[2].translate(str.maketrans("()", "  ")), sep=" ").reshape(-1, 3)
    if len(points) != int(match[1]) or not np.isfinite(points).all():
        raise ValueError("Invalid points")
    faces = [np.array(f, dtype=np.int64) for f in ascii_faces((mesh / "faces").read_text())]
    owners = np.array(label_list((mesh / "owner").read_text()))
    neighbours = np.array(label_list((mesh / "neighbour").read_text()))
    proof = box_proof(points, faces, owners, neighbours)
    for name, digest in topology["mesh_sha256"].items():
        if sha(case / name) != digest:
            raise ValueError("Mesh changed during inspection")
    return {"schema": "bionic-cartesian-diagnostic-admission/v1", "status": "cartesian_geometry_proven",
            "case_manifest_sha256": sha(case / "case-manifest.json"), "source_sha256": sha(Path(__file__)),
            "native_extended_check_passed": False, "canonical_mesh_gate_passed": False,
            "proof": proof, "mesh": topology, "diagnostic_solver_authorized": True,
            "performance_ranking_authorized": False, "engineering_validated": False}


if __name__ == "__main__":
    case = Path(sys.argv[1])
    result = check(case)
    with (case / "cartesian-proof.json").open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(result["proof"]))
