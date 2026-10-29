#!/usr/bin/env python3
"""Index observed boundary curves for review without closing or classifying them."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
import trimesh

from audit_935_faithful_scan import EXPECTED_SHA256, inspect, sha256


def inventory(vertices, edges):
    vertices, edges = np.asarray(vertices), np.asarray(edges)
    if vertices.ndim != 2 or vertices.shape[1] != 3 or not np.isfinite(vertices).all():
        raise ValueError("invalid vertices")
    if edges.ndim != 2 or edges.shape[1] != 2 or edges.dtype.kind not in "iu":
        raise ValueError("invalid edge indices")
    if not len(edges):
        return [], np.empty(0, dtype=np.int64)
    if edges.min() < 0 or edges.max() >= len(vertices):
        raise ValueError("edge index outside vertex array")
    if np.any(edges[:, 0] == edges[:, 1]):
        raise ValueError("self edge")
    if len(np.unique(np.sort(edges, axis=1), axis=0)) != len(edges):
        raise ValueError("duplicate edge")
    used, inverse = np.unique(edges, return_inverse=True)
    local = inverse.reshape((-1, 2))
    degrees = np.bincount(local.ravel(), minlength=len(used))
    graph = coo_matrix((np.ones(len(edges)), (local[:, 0], local[:, 1])),
                       shape=(len(used), len(used)))
    count, labels = connected_components(graph, directed=False)
    edge_labels = labels[local[:, 0]]
    edge_counts = np.bincount(edge_labels, minlength=count)
    lengths = np.linalg.norm(vertices[edges[:, 1]] - vertices[edges[:, 0]], axis=1)
    totals = np.bincount(edge_labels, weights=lengths, minlength=count)
    rows = []
    for component in range(count):
        selected = labels == component
        ids = used[selected]
        points = vertices[ids]
        centre = points.mean(axis=0)
        _, singular, axes = np.linalg.svd(points - centre, full_matrices=False)
        tolerance = singular.max() * max(points.shape) * np.finfo(float).eps
        rank = int(np.count_nonzero(singular > tolerance))
        # Plane residual describes the contour only, not a machined datum.
        distances = np.abs((points - centre) @ axes[-1])
        rows.append({
            "component_id": component, "first_source_vertex": int(ids.min()),
            "edges": int(edge_counts[component]), "vertices": len(ids),
            "simple_cycle_topology": bool(np.all(degrees[selected] == 2)),
            "max_vertex_degree": int(degrees[selected].max()),
            "length_source_units": float(totals[component]),
            "bounds_source_units": [points.min(axis=0).tolist(), points.max(axis=0).tolist()],
            "affine_rank": rank,
            "plane_rms_source_units": float(np.sqrt(np.mean(distances ** 2))) if rank >= 2 else None,
            "plane_max_source_units": float(distances.max()) if rank >= 2 else None,
            "physical_classification": "unreviewed",
            "closure_authorized": False,
        })
    return rows, edge_labels


def run(source, output):
    if sha256(source) != EXPECTED_SHA256:
        raise ValueError("unexpected source SHA-256")
    if output.exists():
        raise FileExistsError(output)
    mesh = trimesh.load_mesh(source, process=False, maintain_order=True)
    _, edges, _, _ = inspect(mesh)
    rows, labels = inventory(mesh.vertices, edges)
    if sha256(source) != EXPECTED_SHA256:
        raise ValueError("source changed during inventory")
    output.mkdir(parents=True, exist_ok=False)
    np.save(output / "source-boundary-edges.npy", edges)
    np.save(output / "edge-component-labels.npy", labels)
    with (output / "review.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["component_id", "edges", "vertices",
            "simple_cycle_topology", "length_source_units", "plane_rms_source_units",
            "physical_classification", "closure_authorized"])
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row[k] for k in writer.fieldnames})
    report = {
        "source_sha256": EXPECTED_SHA256, "units": "unverified_OBJ_units",
        "source_modified": False, "boundary_edges": len(edges),
        "boundary_components": len(rows),
        "simple_cycle_components": sum(r["simple_cycle_topology"] for r in rows),
        "exact_duplicate_vertices": len(mesh.vertices) - len(np.unique(mesh.vertices, axis=0)),
        "classification": "topology_only_no_port_or_scan_gap_decision",
        "self_intersections": "not_evaluated", "print_ready": False,
        "components": rows,
    }
    (output / "inventory.json").write_text(json.dumps(report, indent=2) + "\n")
    manifest = {p.name: sha256(p) for p in sorted(output.iterdir()) if p.is_file()}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return {k: v for k, v in report.items() if k != "components"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.source, args.output), indent=2))
