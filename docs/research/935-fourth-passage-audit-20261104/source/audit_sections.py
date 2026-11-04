#!/usr/bin/env python3
"""Replay legacy passage sections on immutable acquired triangles, without repair."""

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares


ARRAY_SHA = "dd94c37117a1f1277a4f2b7f0bf0023e0d1858991b943f766cf447db319a101a"
FRAME_SHA = "3a5ffb7316148716b3668ec762e284feb67bda040cbda81ba7697cf39765b289"
SUPPORT_SHA = {
    91: "a9fc3e297215ad43b2244116e773f7f5b03043c0a91336310428c730c732aa10",
    94: "9a74fefe5fd01b80e0050b843981e08f43f601b4b1542be0195e6ae550cdc9cd",
    97: "abf828415b0d29a9228d629ea11751f78e95fe7124b272ddcc029a62cd9b78f2",
}


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def require_hash(path, expected):
    if sha(path) != expected:
        raise ValueError(f"Input hash mismatch: {Path(path).name}")


def intersect_face(vertices, face, frame, offset):
    """Identify cuts by original source-edge IDs, never proximity welding."""
    local = vertices[face] @ frame.T
    distance = local[:, 2] - offset
    if np.any(np.abs(distance) <= 1e-10):
        raise ValueError("Source vertex on section plane needs explicit handling")
    cuts = []
    for i, j in [(0, 1), (1, 2), (2, 0)]:
        if (distance[i] < 0) != (distance[j] < 0):
            t = distance[i] / (distance[i] - distance[j])
            point = local[i] + t * (local[j] - local[i])
            cuts.append((tuple(sorted((int(face[i]), int(face[j])))), point))
    if len(cuts) != 2:
        raise ValueError("Selected source face does not have a proper section segment")
    return cuts


def replay_support(vertices, faces, frame, support, offset):
    ids = support["source_face_ids"]
    points = support["points_ABC"]
    if ids.shape != (len(points),) or points.shape[1:] != (3,):
        raise ValueError("Invalid legacy section support shape")
    segments, coordinates, max_error = [], {}, 0.0
    for face_id in np.unique(ids):
        if not 0 <= face_id < len(faces):
            raise ValueError("Invalid original face ID")
        cuts = intersect_face(vertices, faces[face_id], frame, offset)
        old = points[ids == face_id]
        if old.shape != (2, 3):
            raise ValueError("Expected exactly two legacy endpoints per original face")
        new = np.array([c[1] for c in cuts])
        error = min(np.max(np.linalg.norm(new - old, axis=1)),
                    np.max(np.linalg.norm(new - old[::-1], axis=1)))
        max_error = max(max_error, float(error))
        if error > 1e-8:
            raise ValueError("Legacy endpoint does not replay on its original source face")
        for edge, point in cuts:
            if edge in coordinates and np.linalg.norm(coordinates[edge] - point) > 1e-8:
                raise ValueError("Shared source-edge section coordinates disagree")
            coordinates[edge] = point
        segments.append((int(face_id), cuts[0][0], cuts[1][0]))
    return segments, coordinates, max_error


def components(segments):
    adjacency = defaultdict(list)
    for index, (_, a, b) in enumerate(segments):
        adjacency[a].append(index)
        adjacency[b].append(index)
    unseen = set(range(len(segments)))
    result = []
    while unseen:
        pending = [min(unseen)]
        group = set()
        while pending:
            index = pending.pop()
            if index in group:
                continue
            group.add(index)
            for edge in segments[index][1:]:
                pending.extend(k for k in adjacency[edge] if k not in group)
        unseen.difference_update(group)
        degree = Counter(edge for index in group for edge in segments[index][1:])
        result.append({"segment_indices": sorted(group), "degree": degree})
    return result


def circle_diagnostic(points, keys):
    if len(points) < 5:
        return {"state": "insufficient_points", "points": len(points)}
    xy = points[:, :2]
    # Hash-like split by original edge IDs; within-scan, correlated validation only.
    holdout = np.array([(a * 1000003 + b) % 5 == 0 for a, b in keys])
    train = xy[~holdout]
    if len(train) < 3 or holdout.sum() < 2:
        return {"state": "insufficient_split", "points": len(points)}
    center = train.mean(axis=0)
    radius = np.linalg.norm(train - center, axis=1).mean()
    fit = least_squares(lambda p: np.linalg.norm(train - p[:2], axis=1) - p[2],
                        np.r_[center, radius], max_nfev=2000)
    if not fit.success or fit.x[2] <= 0:
        raise ValueError("Circle diagnostic did not converge")
    residual = np.abs(np.linalg.norm(xy - fit.x[:2], axis=1) - fit.x[2])
    angles = np.sort(np.mod(np.arctan2(*(xy - fit.x[:2]).T[::-1]), 2 * np.pi))
    coverage = float(np.degrees(2 * np.pi - np.diff(np.r_[angles, angles[0] + 2 * np.pi]).max()))
    p95 = float(np.quantile(residual[holdout], .95))
    return {"state": "diagnostic_only", "points": len(xy),
            "training_points": int((~holdout).sum()), "holdout_points": int(holdout.sum()),
            "center_AB_mm": fit.x[:2].tolist(), "diameter_mm": float(2 * fit.x[2]),
            "coverage_degrees": coverage, "holdout_p95_mm": p95,
            "holdout_max_mm": float(residual[holdout].max()),
            "all_point_max_mm": float(residual.max()),
            "legacy_exploratory_limits_pass": bool(coverage >= 300 and p95 <= .4),
            "physical_dimension_accepted": False}


def controls():
    square = [(0, (0, 1), (1, 2)), (1, (1, 2), (2, 3)),
              (2, (2, 3), (0, 3)), (3, (0, 3), (0, 1))]
    closed = components(square)
    assert len(closed) == 1 and set(closed[0]["degree"].values()) == {2}
    opened = components(square[:-1])
    assert list(opened[0]["degree"].values()).count(1) == 2
    separate = components([(0, (0, 1), (1, 2)), (1, (3, 4), (4, 5))])
    assert len(separate) == 2  # Coordinates cannot merge distinct source IDs.
    frame = np.eye(3)
    v = np.array([[0., 0., -1.], [2., 0., 1.], [0., 2., 1.]])
    f = np.array([[0, 1, 2]])
    valid = {"source_face_ids": np.array([0, 0]),
             "points_ABC": np.array([[1., 0., 0.], [0., 1., 0.]])}
    replay_support(v, f, frame, valid, 0.)
    invalid = {**valid, "points_ABC": valid["points_ABC"] + .01}
    try:
        replay_support(v, f, frame, invalid, 0.)
    except ValueError:
        pass
    else:
        raise AssertionError("Altered source support was accepted")
    return {"closed_loop": True, "open_chain": True, "distinct_edge_identity": True,
            "known_triangle_cut": True, "altered_support_refused": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arrays", type=Path, required=True)
    parser.add_argument("--engineering", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Output directory already exists")
    checks = controls()
    require_hash(args.arrays, ARRAY_SHA)
    frame_path = args.engineering / "geometry/source-frame-ABC.npy"
    require_hash(frame_path, FRAME_SHA)
    support_paths = {s: args.engineering / f"geometry/stud_passage_4_C_{s}-section-support.npz"
                     for s in SUPPORT_SHA}
    for station, path in support_paths.items():
        require_hash(path, SUPPORT_SHA[station])
    frame = np.load(frame_path)
    if not np.allclose(frame @ frame.T, np.eye(3), atol=1e-10, rtol=0):
        raise ValueError("Source frame is not orthonormal")
    with np.load(args.arrays) as data:
        vertices, faces = data["vertices"], data["triangles"]
    stations, exports = [], {}
    all_endpoint_edges = set()
    for station, path in support_paths.items():
        with np.load(path) as support:
            segments, coordinates, replay_error = replay_support(vertices, faces, frame, support, -station)
        groups = []
        for group in components(segments):
            degree = group["degree"]
            keys = sorted(degree)
            endpoints = [edge for edge, count in degree.items() if count == 1]
            all_endpoint_edges.update(endpoints)
            groups.append({"segments": len(group["segment_indices"]), "points": len(keys),
                           "closed": bool(set(degree.values()) == {2}),
                           "branch_nodes": sum(d > 2 for d in degree.values()),
                           "endpoint_edges": endpoints,
                           "circle": circle_diagnostic(np.array([coordinates[k] for k in keys]), keys)})
        stations.append({"station_id": f"legacy_C_{station}", "source_faces": len(segments),
                         "source_endpoint_replay_max_mm": replay_error, "components": groups})
        exports[station] = {"source_face_ids": np.array([s[0] for s in segments]),
                            "endpoint_source_edges": np.array([s[1:] for s in segments]),
                            "points_ABC": np.array([[coordinates[s[1]], coordinates[s[2]]] for s in segments])}
    # Count full-original-mesh incidence only for actual section-chain endpoints.
    incidence = Counter()
    for i, j in [(0, 1), (1, 2), (2, 0)]:
        edges = np.sort(faces[:, [i, j]], axis=1)
        for edge in all_endpoint_edges:
            incidence[edge] += int(np.count_nonzero(np.all(edges == edge, axis=1)))
    for station in stations:
        for group in station["components"]:
            group["endpoint_origin_counts"] = dict(Counter(
                "original_mesh_boundary" if incidence[tuple(e)] == 1 else
                "support_selection_boundary" if incidence[tuple(e)] == 2 else
                "nonmanifold_or_invalid_original_edge" for e in group["endpoint_edges"]))
    report = {"scope": "Original-source fourth passage candidate audit; no anatomical acceptance",
              "arrays_sha256": ARRAY_SHA, "frame_sha256": FRAME_SHA,
              "legacy_support_sha256": SUPPORT_SHA, "controls": checks, "stations": stations,
              "physical_metrology_accepted": False, "cylinder_accepted": False,
              "manufacturing_authorized": False, "hidden_geometry_created": False}
    args.output.mkdir(parents=True)
    for station, values in exports.items():
        np.savez(args.output / f"section-{station}.npz", **values)
    (args.output / "audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Source section replay and endpoint audit completed; no cylinder accepted.")


if __name__ == "__main__":
    main()
