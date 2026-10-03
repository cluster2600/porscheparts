#!/usr/bin/env python3
"""Private boundary-circle diagnostics; never establishes measured interfaces."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from scipy.optimize import least_squares
from scipy.sparse import csr_array
from scipy.sparse.csgraph import connected_components

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "twins/993-engine-cooling-fan-system-f0/source"))
from audit_private_scan import read_obj

CRITERIA = {"minimum_points": 24, "minimum_coverage_deg": 330,
            "maximum_plane_rms_over_radius": 0.005,
            "maximum_radial_rms_over_radius": 0.005}


def boundary_loops(edges):
    """Return ordered simple cycles and flag pinched/branching boundaries."""
    adjacency = {}
    for a, b in edges.tolist():
        adjacency.setdefault(a, []).append(b)
        adjacency.setdefault(b, []).append(a)
    remaining, result = set(adjacency), []
    while remaining:
        start = min(remaining)
        remaining.remove(start)
        pending, members = [start], []
        while pending:
            v = pending.pop()
            members.append(v)
            for w in adjacency[v]:
                if w in remaining:
                    remaining.remove(w)
                    pending.append(w)
        simple = all(len(adjacency[v]) == 2 for v in members)
        ordered = sorted(members)
        if simple:
            ordered, previous, current = [start], start, min(adjacency[start])
            while current != start:
                ordered.append(current)
                following = [v for v in adjacency[current] if v != previous]
                previous, current = current, following[0]
            if len(ordered) != len(members):
                raise ValueError("Cycle traversal lost original indices")
        result.append({"original_vertex_indices": ordered, "simple_cycle": simple})
    return sorted(result, key=lambda loop: (-len(loop["original_vertex_indices"]),
                                          loop["original_vertex_indices"][0]))


def fit_circle(points):
    """Fit plane and geometric circle; reject partial arcs and degenerate input."""
    p = np.asarray(points, dtype=float)
    if p.ndim != 2 or p.shape[1] != 3 or not np.isfinite(p).all():
        raise ValueError("Invalid circle points")
    if len(p) < CRITERIA["minimum_points"]:
        return {"candidate": False, "reason": "too_few_points"}
    centre = p.mean(0)
    values, axes = np.linalg.eigh((p - centre).T @ (p - centre) / len(p))
    if values[1] <= np.finfo(float).eps * max(1, values[2]) * 128:
        return {"candidate": False, "reason": "collinear_or_coincident"}
    normal = axes[:, 0]
    if normal[np.argmax(np.abs(normal))] < 0:
        normal = -normal
    basis = axes[:, [2, 1]]
    xy = (p - centre) @ basis
    initial, _, rank, _ = np.linalg.lstsq(
        np.column_stack((2 * xy, np.ones(len(xy)))), np.sum(xy * xy, axis=1), rcond=None)
    if rank != 3:
        return {"candidate": False, "reason": "circle_fit_rank_deficient"}
    r2 = initial[2] + initial[0] ** 2 + initial[1] ** 2
    if r2 <= 0:
        return {"candidate": False, "reason": "invalid_radius"}
    fit = least_squares(lambda x: np.linalg.norm(xy - x[:2], axis=1) - x[2],
                        [initial[0], initial[1], np.sqrt(r2)],
                        bounds=([-np.inf, -np.inf, np.finfo(float).tiny], [np.inf] * 3),
                        max_nfev=200)
    if not fit.success:
        return {"candidate": False, "reason": "circle_fit_not_converged"}
    radius = float(fit.x[2])
    radial = np.linalg.norm(xy - fit.x[:2], axis=1) - radius
    plane = (p - centre) @ normal
    angles = np.sort(np.mod(np.arctan2(xy[:, 1] - fit.x[1], xy[:, 0] - fit.x[0]), 2 * np.pi))
    coverage = float(np.rad2deg(2 * np.pi - np.max(np.diff(np.r_[angles, angles[0] + 2 * np.pi]))))
    plane_rms = float(np.sqrt(np.mean(plane * plane)))
    radial_rms = float(np.sqrt(np.mean(radial * radial)))
    accepted = (coverage >= CRITERIA["minimum_coverage_deg"]
                and plane_rms / radius <= CRITERIA["maximum_plane_rms_over_radius"]
                and radial_rms / radius <= CRITERIA["maximum_radial_rms_over_radius"])
    return {"candidate": accepted, "reason": "geometric_candidate_only" if accepted else "screen_rejected",
            "centre_source_units": (centre + basis @ fit.x[:2]).tolist(),
            "normal_unsigned": normal.tolist(), "radius_source_units": radius,
            "plane_rms_source_units": plane_rms, "radial_rms_source_units": radial_rms,
            "plane_rms_over_radius": plane_rms / radius,
            "radial_rms_over_radius": radial_rms / radius, "angular_coverage_deg": coverage,
            "functional_role": None, "independent_measurement_verified": False}


def inspect(vertices, faces):
    edges = np.sort(np.concatenate((faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]])), axis=1)
    unique, count = np.unique(edges, axis=0, return_counts=True)
    graph = csr_array((np.ones(len(unique), dtype=np.int8), (unique[:, 0], unique[:, 1])),
                      shape=(len(vertices), len(vertices)))
    _, labels = connected_components(graph, directed=False)
    used = np.unique(faces)
    component_ids, sizes = np.unique(labels[used], return_counts=True)
    ranked = sorted(zip(component_ids.tolist(), sizes.tolist()), key=lambda row: (-row[1], row[0]))
    rank = {label: i for i, (label, _) in enumerate(ranked)}
    features = []
    for i, loop in enumerate(boundary_loops(unique[count == 1])):
        indices = np.asarray(loop["original_vertex_indices"])
        fit = fit_circle(vertices[indices]) if loop["simple_cycle"] else {"candidate": False, "reason": "branched_boundary"}
        features.append({"id": f"boundary-{i:03d}", "surface_component": rank[int(labels[indices[0]])],
                         **loop, **fit})
    return {"status": "private_geometric_candidates_not_measured_interfaces",
            "source_unit": None, "scale_verified": False,
            "criteria": CRITERIA, "criteria_are_diagnostic_not_metrology_tolerances": True,
            "surface_components": [{"id": i, "vertices": n} for i, (_, n) in enumerate(ranked)],
            "boundary_edges": int(np.sum(count == 1)), "boundary_contours": len(features),
            "circular_candidates": sum(f["candidate"] for f in features), "features": features,
            "mechanical_component_segmentation_complete": False,
            "assembly_transform": None, "measured_datum_established": False,
            "hole_filling_executed": False, "solver_ready": False}


def render_review(vertices, report, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    selected = vertices[np.linspace(0, len(vertices) - 1, min(35000, len(vertices)), dtype=int)]
    fig, panels = plt.subplots(1, 3, figsize=(17, 6))
    candidates = [f for f in report["features"] if f["candidate"]]
    for ax, (a, b) in zip(panels, ((0, 1), (0, 2), (1, 2))):
        ax.scatter(selected[:, a], selected[:, b], s=0.12, color="#7891a5", alpha=0.32, rasterized=True)
        for i, f in enumerate(candidates):
            c = np.asarray(f["centre_source_units"])
            normal = np.asarray(f["normal_unsigned"])
            points = vertices[f["original_vertex_indices"]]
            color = plt.cm.tab20(i % 20)
            ax.plot(points[:, a], points[:, b], lw=1, color=color)
            line = c + np.array([-1, 1])[:, None] * normal * f["radius_source_units"] * 1.6
            ax.plot(line[:, a], line[:, b], lw=0.7, ls="--", color=color)
            ax.text(c[a], c[b], f["id"], fontsize=6, color=color)
        ax.set_aspect("equal")
        ax.set_xlabel(f"PCA coordinate {a + 1} — unknown source unit")
        ax.set_ylabel(f"PCA coordinate {b + 1} — unknown source unit")
    fig.suptitle("Private scan review — circular boundary candidates and unsigned axes\n"
                 "No physical datums, assembly registration or scale calibration")
    fig.tight_layout()
    fig.savefig(output / "interface-candidates.png", dpi=170)
    plt.close(fig)
    (output / "interface-candidates.png").chmod(0o600)


def run(source, output, expected_sha256):
    source, output = source.resolve(), output.resolve()
    sha = hashlib.sha256(source.read_bytes()).hexdigest()
    if sha != expected_sha256:
        raise ValueError("Input hash differs from preparation receipt")
    if output.exists() or (output.is_relative_to(ROOT) and not output.is_relative_to(ROOT / "work")):
        raise ValueError("Use a new private output directory")
    vertices, faces, ignored = read_obj(source)
    if ignored:
        raise ValueError("Position/triangle OBJ required")
    report = inspect(vertices, faces)
    report.update({"input_sha256": sha, "raw_or_prepared_input_unchanged": True,
                   "geometry_or_parameters_publication_permitted": False})
    output.mkdir(parents=True, mode=0o700)
    render_review(vertices, report, output)
    if hashlib.sha256(source.read_bytes()).hexdigest() != sha:
        raise ValueError("Input changed during inspection")
    path = output / "inspection.json"
    path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    path.chmod(0o600)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--expected-sha256", required=True)
    args = parser.parse_args()
    report = run(args.source.resolve(), args.output.resolve(), args.expected_sha256)
    print(f"Private inspection written: {report['circular_candidates']} geometric circle candidates; no measured interfaces")
