#!/usr/bin/env python3
"""Upstream audit of the rejected 5 mm duct mesh (issue #452).

Six meshing attempts on the delivery-duct pilot changed snappyHexMesh settings;
none audited the surface they were meshing. This script does that audit and
changes nothing: no geometry, no mesh setting, no earlier receipt.

It reads the retained reproduction inputs of attempt 5 and an OpenFOAM case in
which they were re-meshed and checked with ``checkMesh -allGeometry
-allTopology`` and ``postProcess -func writeCellCentres``. It then maps every
sharp edge of the analysis surface, and every concave face and cell, to the
constructive surfaces of ``source/Program.cs``, re-implemented below from the
exact generator revision recorded in ``derived/geometry-review.json``.

The constructive model is checked against each surface before it is used: its
fluid signed distance must stay within one generator voxel at every vertex.
"""
import argparse
import gzip
import hashlib
import io
import json
import re
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[3]
STUDY = Path(__file__).resolve().parents[1]
CFD = STUDY / "results/cfd"

# Constants written literally in Program.cs (generator sha256 below), in mm.
# Everything else comes from study.json.
PROGRAM_SHA256 = "d36e2094f21143523bda8154dde390e48d8da42ce9cb5888de95ee8094d6a050"
CYLINDER_END_Y = -5.0          # CylY(p, radius, rear, -5)
BOX_CENTRE = (0.0, 125.0, 155.0)
BOX_HALF = (255.0, 175.0, 70.0)
BOX_ROUND = 30.0
CONE_START_X, CONE_START_Z, CONE_START_EXTRA_R = 170.0, 135.0, 8.0
CONE_END_DZ = -25.0            # cone ends at z = outlet_z - 25
CONE_BLEND_K = 12.0            # RotKit.SMin(d, cone, 12)
ALTERNATOR_FRONT_DY = -30.0    # alternator starts at rear - 30

SHARP_DEG = 30.0               # snappyHexMesh resolveFeatureAngle of attempts 1-6
SURFACE_TOL_MM = 3.0           # two 1.5 mm voxels
CELL_TOL_MM = 5.0 * 3 ** 0.5   # one 5 mm background-cell diagonal


def sha256(data):
    return hashlib.sha256(data).hexdigest()


# --- Constructive surfaces of Program.cs, vectorised over points (N, 3) in mm ---

def cylinder_y_parts(p, zf, r, y0, y1):
    """Side and flat-end distances of Sdf.CylZ applied in Program.cs's CylY frame."""
    radial = np.hypot(p[:, 0], p[:, 2] - zf)
    dr = radial - r
    dz = np.maximum(y0 - p[:, 1], p[:, 1] - y1)
    sdf = np.minimum(np.maximum(dr, dz), 0) + np.hypot(np.maximum(dr, 0), np.maximum(dz, 0))
    return sdf, dr, dz, radial


def round_box(p, centre, half, r):
    q = np.abs(p - np.array(centre)) - (np.array(half) - r)
    return np.linalg.norm(np.maximum(q, 0), axis=1) + np.minimum(q.max(axis=1), 0) - r


def cone(p, a, b, ra, rb):
    a, b = np.array(a), np.array(b)
    pa, ba = p - a, b - a
    h = np.clip(pa @ ba / (ba @ ba), 0, 1)
    return np.linalg.norm(pa - h[:, None] * ba, axis=1) - (ra + (rb - ra) * h)


def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b + (a - b) * h - k * h * (1 - h)


def constituents(p, g):
    """Signed distances of every constructive surface that can bound the fluid."""
    zf, rear = g["fan_centre_z_mm"], g["fan_rear_y_mm"]
    radius = g["fan_radius_mm"] + g["tip_gap_mm"]
    out = {}
    fan, fan_dr, fan_dz, _ = cylinder_y_parts(p, zf, radius, rear, CYLINDER_END_Y)
    alt, alt_dr, alt_dz, _ = cylinder_y_parts(
        p, zf, g["alternator_radius_mm"], rear + ALTERNATOR_FRONT_DY, g["alternator_rear_y_mm"])
    out["fan_cylinder"] = fan
    out["plenum_box"] = round_box(p, BOX_CENTRE, BOX_HALF, BOX_ROUND)
    for side, sign in (("left", -1), ("right", 1)):
        for i, y in enumerate(g["outlet_y_mm"]):
            out[f"branch_cone_{side}{i + 1}"] = cone(
                p, (sign * CONE_START_X, y, CONE_START_Z),
                (sign * g["outlet_x_mm"], y, g["outlet_z_mm"] + CONE_END_DZ),
                g["outlet_radius_mm"] + CONE_START_EXTRA_R, g["outlet_radius_mm"])
    out["alternator"] = alt
    out["inlet_plane"] = rear - p[:, 1]
    out["outlet_plane"] = g["outlet_z_mm"] - p[:, 2]
    parts = {"fan_cylinder": (fan_dr, fan_dz), "alternator": (alt_dr, alt_dz)}
    return out, parts


def fluid_sdf(values):
    union = np.minimum(values["fan_cylinder"], values["plenum_box"])
    for name in sorted(values):
        if name.startswith("branch_cone_"):
            union = smin(union, values[name], CONE_BLEND_K)
    return np.maximum(np.maximum(union, -values["alternator"]),
                      np.maximum(values["inlet_plane"], values["outlet_plane"]))


FACES = ("fan_cylinder_side", "fan_cylinder_end", "plenum_box",
         *(f"branch_cone_{s}{i}" for s in ("left", "right") for i in (1, 2, 3)),
         "alternator_side", "alternator_end", "inlet_plane", "outlet_plane")


def face_distances(p, g):
    """Unsigned distance from each point to every constructive face, shape (N, len(FACES)).

    Cylinders are split into their side and their flat rear end (y = y1),
    because the edge between the two is itself sharp: Sdf.CylZ has no blend.
    Their front ends lie on or beyond the inlet plane and never bound the fluid.
    """
    values, parts = constituents(p, g)
    columns = []
    for name in FACES:
        if name.endswith("_side") or name.endswith("_end"):
            cyl = name.rsplit("_", 1)[0]
            dr, dz = parts[cyl]
            y1 = CYLINDER_END_Y if cyl == "fan_cylinder" else g["alternator_rear_y_mm"]
            if name.endswith("_side"):
                columns.append(np.hypot(dr, np.maximum(dz, 0)))
            else:
                columns.append(np.hypot(p[:, 1] - y1, np.maximum(dr, 0)))
        else:
            columns.append(np.abs(values[name]))
    d = np.stack(columns, axis=1)
    # A face of one union member bounds the fluid only outside the other member:
    # the fan cylinder's end plane runs through the plenum's interior, and vice versa.
    for name in ("fan_cylinder_side", "fan_cylinder_end"):
        d[:, FACES.index(name)] = np.maximum(d[:, FACES.index(name)], -values["plenum_box"])
    d[:, FACES.index("plenum_box")] = np.maximum(d[:, FACES.index("plenum_box")], -values["fan_cylinder"])
    return d


UNION = {"fan_cylinder_side", "fan_cylinder_end", "plenum_box"}
HARD_RE_ENTRANT = ("fan_cylinder_plenum_hard_union_seam", "alternator_rear_rim_hard_subtraction",
                   "alternator_hard_subtraction_edge")


def junction_kind(a, b):
    """How Program.cs joins two constructive faces."""
    s = {a, b}
    cones = {n for n in s if n.startswith("branch_cone_")}
    if s == {"alternator_side", "alternator_end"}:
        return "alternator_rear_rim_hard_subtraction"
    if s == {"fan_cylinder_side", "fan_cylinder_end"}:
        return "fan_cylinder_rear_edge"
    if "outlet_plane" in s and cones:
        return "outlet_rim_plane_cut"
    if "inlet_plane" in s and "fan_cylinder_side" in s:
        return "inlet_outer_rim_plane_cut"
    if "inlet_plane" in s and "alternator_side" in s:
        return "inlet_inner_rim_plane_cut"
    if s & {"alternator_side", "alternator_end"}:
        return "alternator_hard_subtraction_edge"
    if cones and s & UNION:
        return "branch_cone_smooth_union_k12"
    if s <= UNION:
        return "fan_cylinder_plenum_hard_union_seam"
    return "other_constructive_pair"


def nearest_junctions(p, g, tol):
    """Two nearest constructive faces per point; a junction only if both lie within tol."""
    d = face_distances(p, g)
    order = np.argsort(d, axis=1)
    rows = []
    for i in range(len(p)):
        a, b = FACES[order[i, 0]], FACES[order[i, 1]]
        gap = float(d[i, order[i, 1]])
        kind = junction_kind(a, b) if gap <= tol else "smooth_surface_no_constructive_edge"
        rows.append({"faces": [a, b], "junction_distance_mm": round(gap, 2), "construction": kind,
                     "nearest_faces_mm": {FACES[j]: round(float(d[i, j]), 2) for j in order[i, :4]}})
    return rows


# --- Inputs ---

def load_analysis_surface(path):
    """Attempt-5 triSurface with its regions, merged exactly on written vertices."""
    raw = gzip.decompress(path.read_bytes())
    regions, faces_region = [], []
    for match in re.finditer(rb"solid (\w+)\n(.*?)endsolid", raw, re.S):
        count = match.group(2).count(b"outer loop")
        regions.append(match.group(1).decode())
        faces_region += [len(regions) - 1] * count
    loaded = trimesh.load(io.BytesIO(raw), file_type="stl", force="mesh", process=False)
    keys = np.round(loaded.vertices * 1e9).astype(np.int64)
    unique, inverse = np.unique(keys, axis=0, return_inverse=True)
    mesh = trimesh.Trimesh(unique / 1e9 * 1000.0, inverse.reshape(-1)[loaded.faces], process=False)
    if len(faces_region) != len(mesh.faces):
        raise ValueError("Region parse does not match the facet count")
    return raw, mesh, regions, np.array(faces_region)


def parse_check_log(text):
    def number(pattern, cast=int):
        match = re.search(pattern, text)
        return cast(match.group(1)) if match else None
    return {
        "build": number(r"Build\s*:\s*(\S+ OPENFOAM=\d+)", str),
        "cells": number(r"cells:\s+(\d+)"),
        "faces": number(r"\n\s+faces:\s+(\d+)"),
        "points": number(r"\n\s+points:\s+(\d+)"),
        "concave_angle_faces": number(r"There are (\d+) faces with concave angles"),
        "max_concave_angle_deg": number(r"Max concave angle = ([\d.]+)", float),
        "concave_cells": number(r"Concave cells \(using face planes\) found, number of cells: (\d+)"),
        "failed_checks": number(r"Failed (\d+) mesh checks"),
        "min_determinant": number(r"Cell determinant \(wellposedness\) : minimum: ([\d.eE+-]+)", float),
        "max_non_orthogonality_deg": number(r"Mesh non-orthogonality Max: ([\d.]+)", float),
    }


def read_label_list(path):
    text = path.read_text()
    body = text[text.index("//", text.index("FoamFile")):]
    match = re.search(r"(\d+)\s*\(([^)]*)\)", body)
    labels = [int(v) for v in match.group(2).split()]
    if len(labels) != int(match.group(1)):
        raise ValueError(f"Bad label list {path}")
    return labels


def read_vectors(path, count=None):
    text = path.read_text()
    match = re.search(r"\n(\d+)\s*\n\(\n", text)
    n = int(match.group(1))
    start = match.end()
    rows = re.findall(r"\(([-\d.eE+]+) ([-\d.eE+]+) ([-\d.eE+]+)\)", text[start:])[:n]
    data = np.array(rows, float)
    if count is not None and len(data) != count:
        raise ValueError(f"Vector count mismatch in {path}")
    return data


def read_faces(path):
    text = path.read_text()
    match = re.search(r"\n(\d+)\s*\n\(\n", text)
    rows = re.findall(r"\d+\(([\d ]+)\)", text[match.end():])
    return [list(map(int, r.split())) for r in rows[: int(match.group(1))]]


# --- Audit ---

def load_native_surface(path):
    """Cleaned PicoGK fluid-domain export (mm) that attempt 5 decimated."""
    raw = gzip.decompress(path.read_bytes())
    loaded = trimesh.load(io.BytesIO(raw), file_type="stl", force="mesh", process=False)
    keys = np.round(loaded.vertices * 1e6).astype(np.int64)
    unique, inverse = np.unique(keys, axis=0, return_inverse=True)
    return raw, trimesh.Trimesh(unique / 1e6, inverse.reshape(-1)[loaded.faces], process=False)


def surface_audit(mesh, g, regions=None, face_region=None):
    if not (mesh.is_watertight and mesh.is_winding_consistent and mesh.body_count == 1 and mesh.volume > 0):
        raise ValueError("Analysis surface is not one closed, outward-oriented fluid body")
    values, _ = constituents(mesh.vertices, g)
    residual = np.abs(fluid_sdf(values))
    if residual.max() > g["voxel_mm"]:
        raise ValueError("Constructive model does not describe this surface to within one voxel")
    angles = np.degrees(mesh.face_adjacency_angles)
    convex = mesh.face_adjacency_convex
    edges = mesh.face_adjacency_edges
    sharp = angles > SHARP_DEG
    midpoints = mesh.vertices[edges[sharp]].mean(axis=1)
    lengths = np.linalg.norm(np.diff(mesh.vertices[edges[sharp]], axis=1)[:, 0], axis=1)
    kinds = {}
    for row, length, angle, salient in zip(nearest_junctions(midpoints, g, SURFACE_TOL_MM),
                                           lengths, angles[sharp], convex[sharp]):
        item = kinds.setdefault(row["construction"], {"edges": 0, "length_mm": 0.0, "re_entrant_edges": 0,
                                                      "re_entrant_length_mm": 0.0, "salient_edges": 0,
                                                      "max_normal_angle_deg": 0.0})
        item["edges"] += 1
        item["length_mm"] += float(length)
        if salient:
            item["salient_edges"] += 1
        else:
            item["re_entrant_edges"] += 1
            item["re_entrant_length_mm"] += float(length)
        item["max_normal_angle_deg"] = max(item["max_normal_angle_deg"], float(angle))
    for item in kinds.values():
        for key in ("length_mm", "re_entrant_length_mm"):
            item[key] = round(item[key], 1)
        item["max_normal_angle_deg"] = round(item["max_normal_angle_deg"], 2)
    tri_edges = np.linalg.norm(mesh.vertices[mesh.edges_unique[:, 0]] - mesh.vertices[mesh.edges_unique[:, 1]], axis=1)
    corner = mesh.face_angles.min(axis=1)
    report = {
        "triangles": int(len(mesh.faces)),
        "vertices_after_exact_merge": int(len(mesh.vertices)),
        "closed_single_outward_body": True,
        "volume_mm3": round(float(mesh.volume), 1),
        "constructive_model_residual_mm": {
            "meaning": "|fluid SDF of the Program.cs re-implementation| at analysis-surface vertices",
            "p50": round(float(np.percentile(residual, 50)), 3),
            "p95": round(float(np.percentile(residual, 95)), 3),
            "p99": round(float(np.percentile(residual, 99)), 3),
            "max": round(float(residual.max()), 3),
        },
        "edge_length_mm": {
            "min": round(float(tri_edges.min()), 3),
            "p05": round(float(np.percentile(tri_edges, 5)), 3),
            "median": round(float(np.median(tri_edges)), 3),
            "p95": round(float(np.percentile(tri_edges, 95)), 3),
            "max": round(float(tri_edges.max()), 3),
        },
        "triangles_with_min_angle_below_5_deg": int((np.degrees(corner) < 5).sum()),
        "normal_angle_histogram_deg": {
            f"{lo}-{hi}": int(((angles > lo) & (angles <= hi)).sum())
            for lo, hi in ((30, 45), (45, 60), (60, 90), (90, 120), (120, 180))
        },
        "sharp_edges_over_30_deg": int(sharp.sum()),
        "sharp_edges_by_construction": dict(sorted(kinds.items())),
    }
    if regions is not None:
        boundary = face_region[mesh.face_adjacency[:, 0]] != face_region[mesh.face_adjacency[:, 1]]
        report["regions"] = regions
        report["sharp_edges_on_region_boundaries"] = int((sharp & boundary).sum())
    return report


def locate(points, g, distances):
    rows = []
    for point, distance, junction in zip(points, distances, nearest_junctions(points, g, CELL_TOL_MM)):
        rows.append({
            "centre_mm": [round(float(c), 1) for c in point],
            "radius_from_fan_axis_mm": round(float(np.hypot(point[0], point[2] - g["fan_centre_z_mm"])), 1),
            "distance_to_analysis_surface_mm": round(float(distance), 2),
            **junction,
        })
    return rows


def run(case, output):
    if output.exists():
        raise FileExistsError(output)
    program = (STUDY / "source/Program.cs").read_bytes()
    if sha256(program) != PROGRAM_SHA256:
        raise ValueError("Program.cs changed; re-derive the constructive constants first")
    review = json.loads((STUDY / "derived/geometry-review.json").read_text())
    if review["source_hashes"]["twins/993-installed-cooling-f1/source/Program.cs"] != PROGRAM_SHA256:
        raise ValueError("Geometry review was not produced by this generator revision")
    receipt = json.loads((CFD / "receipt.json").read_text())
    reference = receipt["reproduction_reference_attempt"]
    inputs = CFD / "reproduction-inputs"
    for rel, digest in receipt["files"].items():
        if rel.startswith("reproduction-inputs/") and sha256((CFD / rel).read_bytes()) != digest:
            raise ValueError("Reproduction input differs from its receipt: " + rel)
    card = json.loads((inputs / "study.json").read_text())
    g = card["geometry"]

    raw, mesh, regions, face_region = load_analysis_surface(inputs / "duct.stl.gz")
    if sha256(raw) != sha256((case / "constant/triSurface/duct.stl").read_bytes()):
        raise ValueError("Case surface is not the retained reproduction input")
    for name in ("blockMeshDict", "snappyHexMeshDict"):
        if (case / "system" / name).read_bytes() != (inputs / "system" / name).read_bytes():
            raise ValueError("Case mesh dictionary differs from the reproduction input: " + name)

    reproduced = parse_check_log((case / "log.checkMesh").read_text())
    original = parse_check_log(gzip.decompress((CFD / f"attempt-{reference:03d}/log.checkMesh.gz").read_bytes()).decode())
    compared = [k for k in original if k != "build"]
    identical = {k: reproduced[k] == original[k] for k in compared}

    cells = read_label_list(case / "constant/polyMesh/sets/concaveCells")
    faces = read_label_list(case / "constant/polyMesh/sets/concaveFaces")
    if len(cells) != reproduced["concave_cells"] or len(faces) != reproduced["concave_angle_faces"]:
        raise ValueError("Written sets disagree with the checkMesh log")
    centres = read_vectors(case / "0/C")[: reproduced["cells"]] * 1000.0
    points = read_vectors(case / "constant/polyMesh/points") * 1000.0
    face_points = read_faces(case / "constant/polyMesh/faces")
    face_centres = np.array([points[face_points[f]].mean(axis=0) for f in faces])

    query = trimesh.proximity.ProximityQuery(mesh)
    cell_points = centres[cells]
    _, cell_dist, _ = query.on_surface(cell_points)
    _, face_dist, _ = query.on_surface(face_centres)
    located_cells = locate(cell_points, g, cell_dist)
    for label, row in zip(cells, located_cells):
        row["cell"] = label
    located_faces = locate(face_centres, g, face_dist)
    face_summary = {}
    for row in located_faces:
        face_summary[row["construction"]] = face_summary.get(row["construction"], 0) + 1

    surface = surface_audit(mesh, g, regions, face_region)
    native_path = STUDY / "derived/native/delivery-fluid-domain.stl.gz"
    native_raw, native = load_native_surface(native_path)
    entry = next(p for p in review["parts"] if p["name"] == "delivery-fluid-domain")
    if sha256(native_raw) != entry["cleaned_stl_sha256"]:
        raise ValueError("Native fluid surface differs from the geometry review")
    native_surface = {"path": str(native_path.relative_to(ROOT)), "sha256": entry["cleaned_stl_sha256"],
                      "generator_output_sha256": entry["input_sha256"], **surface_audit(native, g)}
    kinds = surface["sharp_edges_by_construction"]
    hard_re_entrant = {k: kinds[k]["re_entrant_length_mm"] for k in HARD_RE_ENTRANT if k in kinds}
    creases = kinds.get("smooth_surface_no_constructive_edge", {"edges": 0, "length_mm": 0.0})
    at_designed_edges = all(r["construction"] != "smooth_surface_no_constructive_edge" for r in located_cells)
    # Rule fixed before the sweep, after AGENTS.md: a surface with unblended re-entrant
    # construction edges, or with creases that no construction explains, is not an
    # admissible input for a mesh-settings sweep.
    admissible = not any(hard_re_entrant.values()) and creases["edges"] == 0
    native_creases = native_surface["sharp_edges_by_construction"].get(
        "smooth_surface_no_constructive_edge", {"edges": 0})["edges"]
    parts = [f"{v:.0f} mm of re-entrant {k}" for k, v in hard_re_entrant.items()]
    reason = (
        f"All {len(located_cells)} concave cells lie within one cell diagonal of a sharp constructive edge "
        f"({', '.join(r['construction'] for r in located_cells)}). The surface carries "
        + (", ".join(parts[:-1]) + " and " + parts[-1] if len(parts) > 1 else "".join(parts) or "no hard re-entrant edge")
        + f". It also carries {creases['edges']} creases over {SHARP_DEG:.0f} deg ({creases['length_mm']:.0f} mm) "
        f"on smooth constructive faces; the undecimated native surface has {native_creases}, so the "
        "90 % decimation in prepare_duct_cfd.py introduced them."
    )
    report = {
        "status": "upstream_audit_complete_mesh_not_admitted",
        "issue": 452,
        "scope": "read-only audit of attempt 5; no geometry, mesh setting or earlier receipt changed",
        "generator": {"path": "twins/993-installed-cooling-f1/source/Program.cs", "sha256": PROGRAM_SHA256},
        "auditor_sha256": sha256(Path(__file__).read_bytes()),
        "reproduction": {
            "reference_attempt": reference,
            "surface_sha256": sha256(raw),
            "reproduced": reproduced,
            "retained_attempt_metrics": original,
            "metrics_identical": identical,
            "all_compared_metrics_identical": all(identical.values()),
        },
        "native_voxel_surface": native_surface,
        "analysis_surface": {"preparation": "prepare_duct_cfd.py: pyvista decimate_pro(0.90, preserve_topology)",
                             **surface},
        "concave_cells": located_cells,
        "concave_faces": {"count": len(faces), "by_construction": dict(sorted(face_summary.items())),
                          "faces": located_faces},
        "verdict": {
            "concave_cells_at_designed_sharp_edges": at_designed_edges,
            "input_admissible_for_settings_sweep": admissible,
            "mesh_admitted": False,
            "flow_solver_started": False,
            "reason": reason,
            "hard_re_entrant_length_mm": hard_re_entrant,
            "decimation_creases": {"edges": creases["edges"], "length_mm": creases["length_mm"]},
        },
        "manufacturing_authorized": False,
        "physical_validation": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--case", type=Path, required=True,
                        help="OpenFOAM case re-meshed from the reproduction inputs, after checkMesh and writeCellCentres")
    parser.add_argument("--output", type=Path, required=True, help="new JSON report path")
    args = parser.parse_args()
    report = run(args.case, args.output)
    print(json.dumps({k: report[k] for k in ("status", "verdict")}, indent=2))


if __name__ == "__main__":
    main()
