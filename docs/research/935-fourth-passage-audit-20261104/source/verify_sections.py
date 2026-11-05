#!/usr/bin/env python3
"""Independently inspect section bytes against acquired XYZ source edges."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def inspect(arrays, engineering, replay):
    if digest(arrays) != "dd94c37117a1f1277a4f2b7f0bf0023e0d1858991b943f766cf447db319a101a":
        raise ValueError("Wrong original source arrays")
    frame_path = engineering / "geometry/source-frame-ABC.npy"
    if digest(frame_path) != "3a5ffb7316148716b3668ec762e284feb67bda040cbda81ba7697cf39765b289":
        raise ValueError("Wrong source frame")
    frame = np.load(frame_path)
    with np.load(arrays) as source:
        vertices, faces = source["vertices"], source["triangles"]
    prior = json.loads((replay / "audit.json").read_text())
    results = []
    support_hashes = ["a9fc3e297215ad43b2244116e773f7f5b03043c0a91336310428c730c732aa10",
                      "9a74fefe5fd01b80e0050b843981e08f43f601b4b1542be0195e6ae550cdc9cd",
                      "abf828415b0d29a9228d629ea11751f78e95fe7124b272ddcc029a62cd9b78f2"]
    for station, support_hash, recorded in zip([91, 94, 97], support_hashes, prior["stations"], strict=True):
        support_path = engineering / f"geometry/stud_passage_4_C_{station}-section-support.npz"
        if digest(support_path) != support_hash:
            raise ValueError("Wrong legacy observed-face selection")
        with np.load(support_path) as support:
            expected_faces = np.unique(support["source_face_ids"])
        with np.load(replay / f"section-{station}.npz") as section:
            ids, edges, points = (section[k] for k in
                                  ["source_face_ids", "endpoint_source_edges", "points_ABC"])
        if not np.array_equal(ids, expected_faces):
            raise ValueError("Section omitted or invented an observed original face")
        if edges.shape != (len(ids), 2, 2) or points.shape != (len(ids), 2, 3):
            raise ValueError("Invalid section array dimensions")
        selected = faces[ids]
        # Invert the recorded frame rather than repeating the producer's local-plane interpolation.
        actual_xyz = points @ np.linalg.inv(frame.T)
        a, b = vertices[edges[:, :, 0]], vertices[edges[:, :, 1]]
        direction = b - a
        t = np.einsum("ijk,ijk->ij", actual_xyz - a, direction) / np.einsum("ijk,ijk->ij", direction, direction)
        edge_distance = np.linalg.norm(actual_xyz - (a + t[:, :, None] * direction), axis=2)
        plane_distance = np.abs(actual_xyz @ frame[2] + station)
        if (edge_distance.max() > 1e-8 or plane_distance.max() > 1e-8 or
                not np.all((t > 0) & (t < 1))):
            raise ValueError("Section point is off its acquired edge or plane")
        for endpoint in [0, 1]:
            membership = (edges[:, endpoint, :, None] == selected[:, None, :]).any(axis=2)
            if not membership.all() or np.any(edges[:, endpoint, 0] >= edges[:, endpoint, 1]):
                raise ValueError("Section edge does not belong to its recorded original face")
        if np.any(np.all(edges[:, 0] == edges[:, 1], axis=1)):
            raise ValueError("Duplicated segment endpoint")
        unique_edges, inverse = np.unique(edges.reshape(-1, 2), axis=0, return_inverse=True)
        nodes = inverse.reshape(-1, 2)
        graph = coo_matrix((np.ones(2 * len(nodes)),
                            (np.r_[nodes[:, 0], nodes[:, 1]], np.r_[nodes[:, 1], nodes[:, 0]])),
                           shape=(len(unique_edges), len(unique_edges))).tocsr()
        count, labels = connected_components(graph, directed=False)
        degree = np.bincount(inverse, minlength=len(unique_edges))
        flat_points = points.reshape(-1, 3)
        for node in range(len(unique_edges)):
            positions = flat_points[inverse == node]
            if np.max(np.linalg.norm(positions - positions[0], axis=1)) > 1e-8:
                raise ValueError("Inconsistent shared section node")
        observed = []
        boundary_counts = []
        for label in range(count):
            mask = labels == label
            edge_count = int(np.count_nonzero(labels[nodes[:, 0]] == label))
            endpoints = unique_edges[mask & (degree == 1)]
            incidence = [int(np.count_nonzero(((faces == e[0]).any(axis=1)) &
                                             ((faces == e[1]).any(axis=1)))) for e in endpoints]
            boundary_counts.extend(incidence)
            observed.append((edge_count, int(mask.sum()), bool(np.all(degree[mask] == 2)),
                             int(np.count_nonzero(degree[mask] > 2))))
        expected = [(c["segments"], c["points"], c["closed"], c["branch_nodes"])
                    for c in recorded["components"]]
        if Counter(observed) != Counter(expected) or not all(n == 1 for n in boundary_counts):
            raise ValueError("Topology or original-boundary origin claim changed")
        results.append({"station_id": recorded["station_id"], "source_faces": len(ids),
                        "components": count, "closed_components": sum(c[2] for c in observed),
                        "open_endpoints_on_original_boundary": len(boundary_counts),
                        "edge_distance_max_mm": float(edge_distance.max()),
                        "plane_distance_max_mm": float(plane_distance.max()),
                        "section_sha256": digest(replay / f"section-{station}.npz")})
    return {"status": "passed", "checks": {"exact_legacy_source_face_coverage": True,
            "actual_points_on_original_XYZ_edges": True, "actual_points_on_source_section_planes": True,
            "shared_source_edge_identity": True, "independent_graph_components": True,
            "all_open_endpoints_are_original_mesh_boundaries": True}, "stations": results,
            "physical_acceptance": False, "manufacturing_authorized": False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ["arrays", "engineering", "replay", "output"]:
        p.add_argument("--" + name, type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        raise ValueError("Output already exists")
    result = inspect(args.arrays, args.engineering, args.replay)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        stream.write(json.dumps(result, indent=2) + "\n")
    print("Independent source-edge section verification passed.")


if __name__ == "__main__":
    main()
