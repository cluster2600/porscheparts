"""Local float32 handoff, with image-preserving zero-face cleanup only."""

import argparse
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path
import struct

import numpy as np


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exact_point(v, index):
    return [Q(float(x)) for x in v[index]]


def write_binary(path, v, f):
    with path.open("wb") as stream:
        stream.write(struct.pack("<QQ", len(v), len(f)))
        v.astype("<f8").tofile(stream)
        f.astype("<u8").tofile(stream)


def transfer(source, output, origin):
    if output.exists():
        raise ValueError("Output exists")
    z = np.load(source, allow_pickle=False)
    v, f = z["vertices"], z["triangles"]
    if v.ndim != 2 or v.shape[1] != 3 or not np.isfinite(v).all():
        raise ValueError("Invalid vertices")
    if f.ndim != 2 or f.shape[1] != 3 or f.dtype.kind not in "iu":
        raise ValueError("Invalid triangles")
    if f.min() < 0 or f.max() >= len(v):
        raise ValueError("Invalid index")
    origin = np.asarray(origin, dtype=np.float64)
    if origin.shape != (3,) or not np.isfinite(origin).all():
        raise ValueError("Invalid origin")
    q = (v - origin).astype(np.float32).astype(np.float64)
    if not np.isfinite(q).all():
        raise ValueError("Float32 coordinate overflow")
    u, inverse = np.unique(q, axis=0, return_inverse=True)
    g = inverse[f]
    repeated = np.any(g == np.roll(g, 1, axis=1), axis=1)
    keep = g[~repeated].copy()
    base = np.uint64(len(u))
    edge_array = np.sort(keep[:, [[0, 1], [1, 2], [2, 0]]].reshape(-1, 2), axis=1)
    edges = np.unique(edge_array[:, 0].astype(np.uint64) * base + edge_array[:, 1])
    used = np.zeros(len(u), dtype=bool)
    used[keep.ravel()] = True
    for face in g[repeated]:
        ids = np.unique(face)
        if len(ids) == 1:
            covered = bool(used[ids[0]])
        else:
            key = np.uint64(ids[0]) * base + np.uint64(ids[1])
            pos = np.searchsorted(edges, key)
            covered = pos < len(edges) and edges[pos] == key
        if not covered:
            raise ValueError("Removed zero face image is not covered")
    t = u[keep]
    zeros = np.flatnonzero(np.all(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]) == 0, axis=1))
    flips = []
    for raw_i in zeros:
        i = int(raw_i)
        face = keep[i].tolist()
        candidates = [(face[k], face[(k + 1) % 3], face[(k + 2) % 3]) for k in range(3)]
        def distance_squared(edge):
            a, b = exact_point(u, edge[0]), exact_point(u, edge[1])
            return sum((y - x) ** 2 for x, y in zip(a, b))
        a_id, b_id, m_id = max(candidates, key=distance_squared)
        a, b, m = [exact_point(u, index) for index in (a_id, b_id, m_id)]
        delta = [y - x for x, y in zip(a, b)]
        axis = max(range(3), key=lambda k: abs(delta[k]))
        ratio = (m[axis] - a[axis]) / delta[axis]
        if not (0 < ratio < 1 and all(m[k] == a[k] + ratio * delta[k] for k in range(3))):
            raise ValueError("Exact strict collinearity not established")
        hits = np.flatnonzero(np.isin(keep, [a_id, b_id]).sum(axis=1) == 2)
        if len(hits) != 2 or i not in hits:
            raise ValueError("Collinear face has no unique adjacent partition")
        j = int(hits[hits != i][0])
        other = keep[j].tolist()
        d_id = next(x for x in other if x not in (a_id, b_id))
        if not any(other[k:] + other[:k] == [b_id, a_id, d_id] for k in range(3)):
            raise ValueError("Inconsistent orientation")
        if np.any(np.isin(keep, [m_id, d_id]).sum(axis=1) == 2):
            raise ValueError("Replacement edge exists")
        new = np.array([[m_id, d_id, b_id], [d_id, m_id, a_id]])
        def normal(ids):
            p, q_, r = [exact_point(u, index) for index in ids]
            x, y = [[b_ - a_ for a_, b_ in zip(p, end)] for end in (q_, r)]
            return [x[1]*y[2]-x[2]*y[1], x[2]*y[0]-x[0]*y[2], x[0]*y[1]-x[1]*y[0]]
        old_normal = normal(keep[j])
        if not all(sum(x*y for x, y in zip(normal(row), old_normal)) > 0 for row in new):
            raise ValueError("Partition reverses orientation")
        keep[i], keep[j] = new
        flips.append({"changed_face_indices": [i, j], "strict_middle_ratio": str(ratio)})
    tri = u[keep]
    if np.any(np.all(np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0]) == 0, axis=1)):
        raise ValueError("Remaining zero face")
    oriented = keep[:, [[0, 1], [1, 2], [2, 0]]].reshape(-1, 2)
    keys = np.sort(oriented, axis=1)
    _, idx, counts = np.unique(keys, axis=0, return_inverse=True, return_counts=True)
    signs = np.where(oriented[:, 0] < oriented[:, 1], 1, -1)
    balances = np.bincount(idx, weights=signs)
    if not np.all(counts == 2) or np.any(balances != 0):
        raise ValueError("Closed oriented edge contract failed")
    used_ids = np.unique(keep)
    remap = np.full(len(u), -1, dtype=np.int64)
    remap[used_ids] = np.arange(len(used_ids))
    local, keep = u[used_ids], remap[keep]
    world = local + origin
    # TwoSum separates the exact addition error from the rounded sum.
    # A subtraction round trip alone can miss a small lost translation.
    virtual_origin = world - local
    virtual_local = world - virtual_origin
    translation_error = (local - virtual_local) + (origin - virtual_origin)
    if not np.isfinite(world).all() or np.any(translation_error != 0):
        raise ValueError("World translation is not exact")
    output.mkdir(parents=True)
    np.savez(output / "candidate.npz", vertices=world, triangles=keep)
    write_binary(output / "candidate.meshbin", world, keep)
    dt = np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attribute", "<u2")])
    stl = np.zeros(len(keep), dtype=dt)
    stl["vertices"] = local[keep]
    n = np.cross(local[keep[:, 1]]-local[keep[:, 0]], local[keep[:, 2]]-local[keep[:, 0]])
    stl["normal"] = n / np.linalg.norm(n, axis=1)[:, None]
    with (output / "input-local.stl").open("wb") as stream:
        stream.write(b"local millimetres; translation in assessment.json".ljust(80, b" "))
        stream.write(struct.pack("<I", len(stl)))
        stl.tofile(stream)
    decoded = stl["vertices"].astype(np.float64)
    if not np.array_equal(decoded, local[keep]):
        raise ValueError("STL round trip changes cleaned local vertices")
    report = {
        "status": "precision_transfer_authored_independent_checks_pending",
        "source_sha256": digest(source), "origin_mm": origin.tolist(),
        "source_vertices": len(v), "source_faces": len(f),
        "merged_exact_coordinate_duplicates": len(q)-len(u),
        "removed_repeated_index_faces": int(repeated.sum()),
        "removed_face_images_covered_by_retained_edges_or_vertices": True,
        "collinear_partition_flips": flips,
        "cleanup_complete_geometric_change_bound_mm": 0,
        "precleanup_complete_vertex_l1_cast_bound_mm": float(np.abs(q+origin-v).sum(axis=1).max()),
        "retained_vertices": len(world), "retained_faces": len(keep),
        "closed_oppositely_paired_edges": True,
        "stl_preserves_cleaned_local_vertices_exactly": True,
        "local_to_world_addition_exact": True,
        "output_sha256": {p.name: digest(p) for p in output.iterdir()},
        "manufacturing_authorized": False,
    }
    (output / "assessment.json").write_text(json.dumps(report, indent=2)+"\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--origin", type=float, nargs=3, required=True)
    args = parser.parse_args()
    print(json.dumps(transfer(args.source, args.output, np.array(args.origin))))
