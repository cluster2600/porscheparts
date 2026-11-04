"""Audit fixed acquired chamber charts before increasing surface flexibility."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def integer_points(uv):
    ratios = [[float(x).as_integer_ratio() for x in row] for row in uv]
    denominator = max(d for row in ratios for _, d in row)
    return [tuple(n * (denominator // d) for n, d in row) for row in ratios]


def orient(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def intersect(first, second):
    positive = True
    for own, other in ((first, second), (second, first)):
        sign = 1 if orient(*own) > 0 else -1
        for a, b in zip(own, own[1:] + own[:1]):
            maximum = max(sign * orient(a, b, p) for p in other)
            if maximum < 0:
                return False, False
            if maximum == 0:
                positive = False
    return True, positive


def candidates(uv, triangles):
    xyz = uv[triangles]
    low, high = xyz.min(axis=1), xyz.max(axis=1)
    pairs = []
    for i in range(len(triangles)):
        mask = np.all(low[i] <= high[i + 1:], axis=1) & np.all(low[i + 1:] <= high[i], axis=1)
        pairs.extend((i, int(j)) for j in np.flatnonzero(mask) + i + 1)
    return np.asarray(pairs, dtype=np.int64).reshape(-1, 2)


def topology(triangles):
    edges = np.sort(np.concatenate((triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [2, 0]])), axis=1)
    unique, count = np.unique(edges, axis=0, return_counts=True)
    boundary = unique[count == 1]
    _, degrees = np.unique(boundary.ravel(), return_counts=True)
    return {
        "edges": len(unique),
        "edges_with_multiplicity_over_two": int(np.count_nonzero(count > 2)),
        "boundary_edges": len(boundary),
        "boundary_vertex_degree_histogram": {str(int(k)): int(v) for k, v in zip(*np.unique(degrees, return_counts=True))},
        "boundary_vertices_with_degree_not_two": int(np.count_nonzero(degrees != 2)),
    }


def audit(uv, triangles):
    points = integer_points(uv)
    projected = [tuple(points[int(i)] for i in f) for f in triangles]
    signs = np.array([int(orient(*t) > 0) - int(orient(*t) < 0) for t in projected])
    pairs = candidates(uv, triangles)
    overlaps, unshared, degenerate = [], [], 0
    for i, j in pairs:
        if signs[i] == 0 or signs[j] == 0:
            degenerate += 1
            continue
        closed, positive = intersect(projected[i], projected[j])
        if positive:
            overlaps.append((int(i), int(j)))
        if closed and not set(triangles[i]).intersection(triangles[j]):
            unshared.append((int(i), int(j)))
    result = topology(triangles)
    result.update(
        projected_sign_counts={str(k): int(np.count_nonzero(signs == k)) for k in (-1, 0, 1)},
        aabb_candidate_pairs=len(pairs), candidate_pairs_with_degenerate_triangle=degenerate,
        positive_area_overlap_pairs=len(overlaps), closed_contacts_without_original_shared_vertex=len(unshared),
        full_projection_injectivity_accepted=False, native_smooth_surface_admitted=False,
    )
    result["observed_chart_obstruction"] = bool(overlaps or unshared or np.any(signs == 0) or result["boundary_vertices_with_degree_not_two"])
    return result, pairs, np.asarray(overlaps, dtype=np.int64).reshape(-1, 2), np.asarray(unshared, dtype=np.int64).reshape(-1, 2)


def controls():
    uv = np.array([[0., 0.], [1., 0.], [0., 1.], [1., 1.]])
    a = audit(uv, np.array([[0, 1, 2], [1, 3, 2]]))[0]
    assert a["positive_area_overlap_pairs"] == 0 and a["boundary_vertices_with_degree_not_two"] == 0
    # Two originally distinct faces overlap after projection.
    b = audit(np.r_[uv, [[.2, .2], [.6, .2], [.2, .6]]], np.array([[0, 1, 2], [4, 5, 6]]))[0]
    assert b["positive_area_overlap_pairs"] == 1 and b["closed_contacts_without_original_shared_vertex"] == 1
    c = audit(np.r_[uv, [[.2, .2]]], np.array([[0, 1, 2], [1, 0, 4]]))[0]
    assert c["positive_area_overlap_pairs"] == 1 and c["projected_sign_counts"]["-1"] == 1
    d = audit(np.array([[0., 0.], [1., 0.], [2., 0.]]), np.array([[0, 1, 2]]))[0]
    assert d["projected_sign_counts"]["0"] == 1
    return {"shared_edge_square": True, "nested_unshared_overlap": True, "folded_shared_edge": True, "collapsed_projection": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("arrays", "parent", "plan", "output"):
        parser.add_argument("--" + key, type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    if sha(args.arrays) != plan["source_arrays_sha256"]:
        raise ValueError("Original arrays hash mismatch")
    if sha(args.parent / "manifest.json") != plan["parent_manifest_sha256"]:
        raise ValueError("Frozen parent manifest mismatch")
    entries = {x["path"]: x for x in json.loads((args.parent / "manifest.json").read_text())["files"]}
    consumed = ["study-001/study.json"] + [f"study-001/region-{i}-{s}.npz" for i in range(8) for s in ("selection", "models")]
    for name in consumed:
        if sha(args.parent / name) != entries[name]["sha256"]:
            raise ValueError("Frozen parent file mismatch")
    with np.load(args.arrays, allow_pickle=False) as data:
        vertices, faces = data["vertices"], data["triangles"]
    parent = json.loads((args.parent / "study-001/study.json").read_text())
    args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    results = []
    for i in range(8):
        with np.load(args.parent / f"study-001/region-{i}-selection.npz", allow_pickle=False) as d:
            ids = d["selected_original_face_ids"]
        vi, inverse = np.unique(faces[ids], return_inverse=True)
        tri = inverse.reshape(-1, 3)
        with np.load(args.parent / f"study-001/region-{i}-models.npz", allow_pickle=False) as d:
            if not np.array_equal(d["original_source_face_ids"], ids) or not np.array_equal(d["original_source_vertex_ids"], vi):
                raise ValueError("Frozen source membership mismatch")
            uv = ((vertices[vi] - d["origin"]) @ d["frame"].T)[:, :2] / d["uv_scale"]
        report, pairs, overlaps, unshared = audit(uv, tri)
        report.update(region=i, source_faces=len(ids),
                      inherited_source_vertices_split_into_fans=parent["regions"][i]["topology"]["source_vertices_split_into_fans"])
        file = args.output / f"region-{i}-chart.npz"
        np.savez_compressed(file, original_face_ids=ids, original_vertex_ids=vi, uv=uv,
                            original_local_triangles=tri, aabb_pairs=pairs, overlap_pairs=overlaps, unshared_contact_pairs=unshared)
        report["private_chart_sha256"] = sha(file)
        results.append(report)
    report = {"plan_sha256": sha(args.plan), "source_sha256": sha(__file__),
              "regions": results, "synthetic_controls": controls(),
              "physical_acceptance": False, "manufacturing_authorized": False}
    (args.output / "audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
