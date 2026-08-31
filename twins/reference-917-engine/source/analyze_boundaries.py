#!/usr/bin/env python3
"""Find circular, planar open boundaries that may be cylinder interfaces."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import trimesh
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components


def fit_circle(points: np.ndarray) -> tuple[np.ndarray, float, np.ndarray]:
    matrix = np.column_stack((2.0 * points, np.ones(len(points))))
    rhs = np.einsum("ij,ij->i", points, points)
    solution, *_ = np.linalg.lstsq(matrix, rhs, rcond=None)
    centre = solution[:2]
    radius = float(np.sqrt(max(solution[2] + centre @ centre, 0.0)))
    residuals = np.abs(np.linalg.norm(points - centre, axis=1) - radius)
    return centre, radius, residuals


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)

    mesh = trimesh.load_mesh(args.input, process=False, maintain_order=True)
    edge_counts = np.bincount(np.asarray(mesh.edges_unique_inverse))
    boundary_edges = np.asarray(mesh.edges_unique)[edge_counts == 1]
    active_vertices, inverse = np.unique(boundary_edges, return_inverse=True)
    compact_edges = inverse.reshape((-1, 2))
    rows = np.concatenate((compact_edges[:, 0], compact_edges[:, 1]))
    cols = np.concatenate((compact_edges[:, 1], compact_edges[:, 0]))
    graph = coo_matrix(
        (np.ones(len(rows), dtype=np.uint8), (rows, cols)),
        shape=(len(active_vertices), len(active_vertices)),
    ).tocsr()
    count, labels = connected_components(graph, directed=False, return_labels=True)

    candidates = []
    vertices = np.asarray(mesh.vertices)
    for component_id in range(count):
        compact_ids = np.flatnonzero(labels == component_id)
        if not 20 <= len(compact_ids) <= 20_000:
            continue
        vertex_ids = active_vertices[compact_ids]
        points = vertices[vertex_ids]
        centre_3d = points.mean(axis=0)
        covariance = np.cov((points - centre_3d).T)
        values, vectors = np.linalg.eigh(covariance)
        order = np.argsort(values)[::-1]
        values = values[order]
        vectors = vectors[:, order]
        if values[1] <= 0:
            continue
        projected = (points - centre_3d) @ vectors[:, :2]
        centre_2d, radius, residuals = fit_circle(projected)
        centre_fit_3d = centre_3d + vectors[:, :2] @ centre_2d
        angles = np.unwrap(np.sort(np.arctan2(projected[:, 1] - centre_2d[1], projected[:, 0] - centre_2d[0])))
        gaps = np.diff(np.r_[angles, angles[0] + 2.0 * np.pi])
        coverage = float(1.0 - np.max(gaps) / (2.0 * np.pi))
        p95 = float(np.percentile(residuals, 95))
        degrees = np.asarray(graph[compact_ids].getnnz(axis=1)).ravel()
        candidates.append(
            {
                "component_id": component_id,
                "vertex_count": int(len(points)),
                "closed_loop": bool(np.all(degrees == 2)),
                "center": centre_fit_3d.tolist(),
                "normal": vectors[:, 2].tolist(),
                "diameter_obj_units": float(2.0 * radius),
                "circle_fit_p95_obj_units": p95,
                "relative_circle_fit_p95": float(p95 / radius) if radius else None,
                "plane_rms_obj_units": float(np.sqrt(values[2])),
                "planarity_ratio": float(values[2] / values[1]),
                "angular_coverage": coverage,
            }
        )

    likely = [
        item
        for item in candidates
        if 40.0 <= item["diameter_obj_units"] <= 180.0
        and item["relative_circle_fit_p95"] <= 0.12
        and item["planarity_ratio"] <= 0.05
        and item["angular_coverage"] >= 0.65
    ]
    likely.sort(key=lambda item: (item["relative_circle_fit_p95"], -item["angular_coverage"]))
    report = {
        "input": str(args.input.resolve()),
        "boundary_edges": int(len(boundary_edges)),
        "boundary_components": int(count),
        "likely_circular_interfaces": likely,
        "candidate_count_before_filter": len(candidates),
        "method": "planar boundary-component least-squares circle screening",
        "limitations": [
            "A circular scan gap can be mistaken for a functional interface.",
            "Interrupted rims connected to other open boundaries may not be detected.",
            "Every candidate requires visual confirmation before semantic naming.",
        ],
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
