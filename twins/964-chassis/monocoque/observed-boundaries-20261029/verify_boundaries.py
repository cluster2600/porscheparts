#!/usr/bin/env python3
"""Recompute the boundary inventory using endpoint pairs, not packed edge keys."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

HERE = Path(__file__).resolve().parent
COVERAGE = HERE.parent / "scan-coverage-20261029"


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pair_inventory(faces):
    """Interleaved face edges and lexicographic pair ordering are independent of the author."""
    edges = np.asarray(faces, dtype=np.int64)[:, [[0, 1], [1, 2], [2, 0]]].reshape(-1, 2)
    pairs = np.sort(edges, axis=1)
    order = np.lexsort((pairs[:, 1], pairs[:, 0]))
    sorted_pairs = pairs[order]
    change = np.any(sorted_pairs[1:] != sorted_pairs[:-1], axis=1)
    starts = np.r_[0, np.flatnonzero(change) + 1]
    counts = np.diff(np.r_[starts, len(order)])
    incident_a = order[:-1][~change] // 3
    incident_b = order[1:][~change] // 3
    graph = coo_matrix((np.ones(len(incident_a), dtype=np.uint8), (incident_a, incident_b)),
                       shape=(len(faces), len(faces))).tocsr()
    number, labels = connected_components(graph, directed=False)
    orientation = np.where(edges[:, 0] < edges[:, 1], 1, -1)
    winding = np.add.reduceat(orientation[order], starts)
    return sorted_pairs[starts], counts, labels, {
        "unique_edges": len(starts), "open_edges": int(np.sum(counts == 1)),
        "nonmanifold_edges": int(np.sum(counts > 2)),
        "same_direction_two_face_edges": int(np.sum((counts == 2) & (winding != 0))),
        "edge_connected_surface_components": int(number),
    }


def verify(vertices_path, faces_path, review):
    receipt = Path(review) / "verification.json"
    require(not receipt.exists(), "Verification receipt already exists")
    report = json.loads((Path(review) / "run.json").read_text())
    require(digest(COVERAGE / "run.json") == "70a4634dd933cbf74a3d388260bee7717496f6f5a06b8b58eef26b34a2d7fea4", "Parent receipt changed")
    parent = json.loads((COVERAGE / "run.json").read_text())
    require(set(report["regions"]) == {"FloorLeftSearch", "FloorRightSearch", "CentralRouteSearch"}, "Incomplete region inventory")
    require(report["parent_run_sha256"] == digest(COVERAGE / "run.json"), "Parent identity mismatch")
    require(report["source_sha256"] == parent["source_sha256"], "Source identity changed")
    require(report["input_array_sha256"] == parent["input_array_sha256"], "Array identity changed")
    for path, name in ((vertices_path, "verts_vehicle.npy"), (faces_path, "faces.npy")):
        require(digest(path) == parent["input_array_sha256"][name], "Input array hash mismatch")
    require(report["author_sha256"] == digest(HERE / "inspect_boundaries.py"), "Author code mismatch")
    require(report["regions_sha256"] == digest(COVERAGE / "regions.json") == parent["regions_sha256"], "Region definition changed")
    for name, expected in report["private_outputs_sha256"].items():
        require(Path(name).name == name, "Invalid output path")
        require(digest(Path(review) / name) == expected, "Output hash mismatch: " + name)
    for key in ("geometry_modified", "physical_segmentation_validated", "surface_fit_performed",
                "self_intersections_checked", "vertex_manifoldness_checked", "structural_analysis_admitted"):
        require(report[key] is False, "Unsupported completion claim: " + key)
    vertices = np.load(vertices_path, allow_pickle=False)
    faces = np.load(faces_path, allow_pickle=False)
    pairs, counts, labels, summary = pair_inventory(faces)
    require(report["source_vertices"] == len(vertices) and report["source_triangles"] == len(faces), "Source size mismatch")
    for key, value in summary.items():
        require(report["source"][key] == value, "Source summary mismatch: " + key)
    require(np.array_equal(np.load(Path(review) / "source_face_components.npy"), labels), "Source component partition mismatch")
    require(report["source"]["component_triangle_counts"] == np.bincount(labels).tolist(), "Source component sizes mismatch")
    require(np.array_equal(np.load(Path(review) / "source_open_edges.npz")["source_vertex_ids"], pairs[counts == 1]), "Source open-edge set mismatch")
    zero_area = 0
    for start in range(0, len(faces), 100_000):
        p = vertices[faces[start:start + 100_000]].astype(np.float64)
        a, b = p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]
        zero_area += int(np.sum((a[:, 1]*b[:, 2] == a[:, 2]*b[:, 1]) &
                               (a[:, 2]*b[:, 0] == a[:, 0]*b[:, 2]) &
                               (a[:, 0]*b[:, 1] == a[:, 1]*b[:, 0])))
    require(report["source"]["zero_area_triangles_exact_float64_cross"] == zero_area, "Zero-area count mismatch")
    # Only retain the original open/non-manifold endpoint sets for region classification.
    open_pairs = {tuple(edge) for edge in pairs[counts == 1]}
    ambiguous_pairs = {tuple(edge) for edge in pairs[counts > 2]}
    config = json.loads((COVERAGE / "regions.json").read_text())
    used = np.zeros(len(faces), dtype=bool)
    checked_edges = 0
    for region in config["regions"]:
        bounds = np.asarray(region["bounds"]).reshape(3, 2)
        tri = vertices[faces]
        selected = np.flatnonzero(np.all(tri.min(axis=1) >= bounds[:, 0], axis=1) &
                                  np.all(tri.max(axis=1) <= bounds[:, 1], axis=1) & ~used)
        used[selected] = True
        if region["name"] not in report["regions"]:
            continue
        row = report["regions"][region["name"]]
        data = np.load(Path(review) / (region["name"] + ".npz"), allow_pickle=False)
        require(np.array_equal(data["source_face_ids"], selected), "Region membership mismatch")
        require(hashlib.sha256(selected.astype("<i4").tobytes()).hexdigest() == row["source_face_ids_sha256"] == parent["groups"][region["name"]]["source_face_ids_sha256"], "Source face-ID digest mismatch")
        local_pairs, local_counts, local_labels, local_summary = pair_inventory(faces[selected])
        for key, value in local_summary.items():
            require(row[key] == value, "Region topology mismatch: " + key)
        edges = local_pairs[local_counts == 1]
        origins = np.array([0 if tuple(e) in open_pairs else 2 if tuple(e) in ambiguous_pairs else 1 for e in edges], dtype=np.uint8)
        require(np.array_equal(data["source_vertex_ids"], edges), "Region boundary endpoint mismatch")
        require(np.array_equal(data["boundary_origin"], origins), "Original/cut boundary classification mismatch")
        require(np.array_equal(data["local_face_components"], local_labels), "Local component partition mismatch")
        require(row["triangles"] == len(selected) and row["boundary_edges"] == len(edges), "Region size mismatch")
        require(row["source_open_edges"] == int(np.sum(origins == 0)), "Original boundary count mismatch")
        require(row["selection_cut_edges"] == int(np.sum(origins == 1)), "Cut boundary count mismatch")
        require(row["ambiguous_source_nonmanifold_edges"] == int(np.sum(origins == 2)), "Ambiguous boundary count mismatch")
        require(row["physical_boundary_identified"] is False, "Unsupported physical-boundary claim")
        require(row["local_component_triangle_counts"] == np.bincount(local_labels).tolist(), "Local component size mismatch")
        lab, nums = np.unique(labels[selected], return_counts=True)
        overlap = [{"component": int(x), "region_triangles": int(c),
                    "full_component_triangles": int(np.sum(labels == x))} for x, c in zip(lab, nums)]
        require(row["source_component_overlap"] == overlap, "Source component overlap mismatch")
        # Independent boundary traversal counts cycles without a sparse graph.
        adjacent = {}
        for a, b in edges.tolist():
            adjacent.setdefault(a, []).append(b)
            adjacent.setdefault(b, []).append(a)
        unseen = set(adjacent)
        number = cycles = 0
        while unseen:
            todo = [unseen.pop()]
            regular = True
            while todo:
                a = todo.pop()
                regular &= len(adjacent[a]) == 2
                for b in adjacent[a]:
                    if b in unseen:
                        unseen.remove(b)
                        todo.append(b)
            number += 1
            cycles += int(regular)
        require(row["boundary_graph"] == {"components": number, "simple_cycles": cycles, "other_components": number - cycles}, "Boundary contour topology mismatch")
        checked_edges += len(edges)
    result = {"status": "passed", "scope": "source and three-region mesh topology, not physical segmentation",
              "source_edges_checked": len(pairs), "region_boundary_edges_checked": checked_edges,
              "run_sha256": digest(Path(review) / "run.json"), "verifier_sha256": digest(__file__),
              "independent_representation": "lexicographic endpoint pairs and interleaved face edges; boundary contours checked by graph traversal",
              "shared_library": "SciPy connected_components for face partitions in both programs",
              "geometry_or_engineering_approval": False}
    receipt.write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vertices", type=Path, required=True)
    parser.add_argument("--faces", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.vertices, args.faces, args.review)))
