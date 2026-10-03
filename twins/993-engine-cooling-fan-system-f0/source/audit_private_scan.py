#!/usr/bin/env python3
"""Audit an OBJ without repair, scaling or geometry export. Keep output private."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def surface_component_sizes(vertex_count, edges, used):
    """Union-find over original indices; do not weld nearby scan vertices."""
    parent = list(range(vertex_count))
    rank = [0] * vertex_count

    def root(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    for a, b in edges.tolist():
        a, b = root(a), root(b)
        if a != b:
            if rank[a] < rank[b]:
                a, b = b, a
            parent[b] = a
            if rank[a] == rank[b]:
                rank[a] += 1
    _, counts = np.unique([root(int(i)) for i in used], return_counts=True)
    return sorted(counts.tolist(), reverse=True)


def read_obj(path):
    vertices, faces = [], []
    ignored = set()
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            fields = line.split()
            if not fields or fields[0].startswith("#"):
                continue
            if fields[0] == "v":
                if len(fields) != 4:
                    raise ValueError(f"Unsupported vertex at line {line_number}")
                vertices.append([float(v) for v in fields[1:]])
            elif fields[0] == "f":
                if len(fields) != 4:
                    raise ValueError(f"Non-triangle face at line {line_number}")
                indices = [int(v.split("/")[0]) for v in fields[1:]]
                if 0 in indices:
                    raise ValueError("OBJ indices cannot be zero")
                faces.append([i - 1 if i > 0 else len(vertices) + i for i in indices])
            else:
                ignored.add(fields[0])
    v, f = np.asarray(vertices, dtype=float), np.asarray(faces, dtype=np.int64)
    if v.ndim != 2 or v.shape[1] != 3 or not np.isfinite(v).all():
        raise ValueError("Nonfinite or missing vertices")
    if f.ndim != 2 or f.shape[1] != 3 or f.min() < 0 or f.max() >= len(v):
        raise ValueError("Missing faces or invalid vertex index")
    return v, f, sorted(ignored)


def boundary_graph_summary(boundary_edges):
    """Separate simple boundary cycles from pinched or branching contours."""
    adjacency = {}
    for a, b in boundary_edges.tolist():
        adjacency.setdefault(a, []).append(b)
        adjacency.setdefault(b, []).append(a)
    remaining = set(adjacency)
    components = []
    while remaining:
        pending = [remaining.pop()]
        members = []
        while pending:
            vertex = pending.pop()
            members.append(vertex)
            for neighbor in adjacency[vertex]:
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    pending.append(neighbor)
        degrees = [len(adjacency[vertex]) for vertex in members]
        components.append({"vertices": len(members), "edges": sum(degrees) // 2,
                           "simple_cycle": all(degree == 2 for degree in degrees),
                           "endpoints": sum(degree == 1 for degree in degrees),
                           "branch_vertices": sum(degree > 2 for degree in degrees)})
    components.sort(key=lambda component: component["edges"], reverse=True)
    return {"connected_contours": len(components),
            "simple_cycles": sum(component["simple_cycle"] for component in components),
            "branch_vertices": sum(component["branch_vertices"] for component in components),
            "contours": components,
            "cycles_are_not_classified_as_missing_surface_holes": True}


def audit(path):
    vertices, faces, ignored = read_obj(path)
    edges = np.concatenate((faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]))
    canonical = np.sort(edges, axis=1)
    unique, inverse, count = np.unique(canonical, axis=0, return_inverse=True, return_counts=True)
    orientation = np.where(edges[:, 0] < edges[:, 1], 1, -1)
    sums = np.bincount(inverse, weights=orientation, minlength=len(unique))
    used = np.unique(faces)
    sizes = surface_component_sizes(len(vertices), unique, used)
    triangles = vertices[faces]
    area2 = np.linalg.norm(np.cross(triangles[:, 1] - triangles[:, 0],
                                    triangles[:, 2] - triangles[:, 0]), axis=1)
    aligned = vertices - vertices.mean(axis=0)
    _, axes = np.linalg.eigh(aligned.T @ aligned / len(aligned))
    pca = aligned @ axes
    return {
        "status": "private_scan_audit_only", "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size, "vertices": len(vertices), "triangles": len(faces),
        "ignored_obj_record_types": ignored, "units": None, "scale_verified": False,
        "identity_verified": False, "equivalence_935_993_verified": False,
        "rights_status": "unconfirmed_private_only", "geometry_exported": False,
        "geometry_repaired": False, "bounds_source_units": [vertices.min(0).tolist(), vertices.max(0).tolist()],
        "pca_extents_source_units": np.ptp(pca, axis=0).tolist(),
        "pca_is_rigid_visual_diagnostic_not_a_measured_datum": True,
        "boundary_edges": int(np.sum(count == 1)), "nonmanifold_edges": int(np.sum(count > 2)),
        "boundary_graph": boundary_graph_summary(unique[count == 1]),
        "inconsistent_two_face_edges": int(np.sum((count == 2) & (sums != 0))),
        "watertight_edge_topology": bool(np.all(count == 2)),
        "duplicate_faces": int(len(faces) - len(np.unique(np.sort(faces, axis=1), axis=0))),
        "zero_area_triangles": int(np.sum(area2 == 0)), "unreferenced_vertices": int(len(vertices) - len(used)),
        "connected_surface_components": len(sizes),
        "largest_component_vertex_counts": sizes[:10],
        "self_intersections_checked": False, "dimensional_accuracy_verified": False,
        "solver_ready": False,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scan", type=Path)
    ap.add_argument("output", type=Path, help="New JSON under ignored work/ or outside the repository")
    args = ap.parse_args()
    root = Path(__file__).resolve().parents[3]
    out = args.output.resolve()
    if out == args.scan.resolve() or (out.is_relative_to(root) and not out.is_relative_to(root / "work")):
        ap.error("Output must remain private, outside versioned repository paths")
    result = audit(args.scan)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    out.chmod(0o600)
    print("Private scan audit written; no repair or geometry export")


if __name__ == "__main__":
    main()
