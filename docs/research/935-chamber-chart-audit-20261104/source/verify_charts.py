"""Independently inspect source chart topology and exact rational projection pairs."""
import argparse
from collections import Counter
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path

import numpy as np


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def det(a, b, c):
    return (a[0] - c[0]) * (b[1] - c[1]) - (a[1] - c[1]) * (b[0] - c[0])


def separate(first, second):
    closed, strict = True, True
    for triangle, other in ((first, second), (second, first)):
        winding = 1 if det(*triangle) > 0 else -1
        for j in range(3):
            values = [winding * det(triangle[j], triangle[(j + 1) % 3], p) for p in other]
            if all(v < 0 for v in values):
                return False, False
            if all(v <= 0 for v in values):
                strict = False
    return closed, strict


def clip_area(first, second):
    polygon = list(first)
    sign = 1 if det(*second) > 0 else -1
    for i in range(3):
        a, b = second[i], second[(i + 1) % 3]
        result = []
        if not polygon:
            return F(0)
        for p, q in zip(polygon, polygon[1:] + polygon[:1]):
            dp, dq = sign * det(a, b, p), sign * det(a, b, q)
            if dp >= 0:
                result.append(p)
            if (dp > 0 and dq < 0) or (dp < 0 and dq > 0):
                t = dp / (dp - dq)
                result.append(tuple(p[k] + t * (q[k] - p[k]) for k in (0, 1)))
        polygon = result
    return abs(sum(p[0] * q[1] - p[1] * q[0] for p, q in zip(polygon, polygon[1:] + polygon[:1]))) / 2


def broadphase(uv, triangles):
    coordinates = uv[triangles]
    low, high = coordinates.min(axis=1), coordinates.max(axis=1)
    ordered = sorted(range(len(triangles)), key=lambda i: (low[i, 0], i))
    active, pairs = [], []
    for i in ordered:
        active = [j for j in active if high[j, 0] >= low[i, 0]]
        for j in active:
            if low[j, 1] <= high[i, 1] and low[i, 1] <= high[j, 1]:
                pairs.append((min(i, j), max(i, j)))
        active.append(i)
    return np.array(sorted(pairs), dtype=np.int64).reshape(-1, 2)


def original_topology(triangles):
    edges = Counter()
    for a, b, c in triangles.tolist():
        edges.update((tuple(sorted((a, b))), tuple(sorted((b, c))), tuple(sorted((c, a)))))
    degrees = Counter()
    for edge, multiplicity in edges.items():
        if multiplicity == 1:
            degrees.update(edge)
    return {
        "edges": len(edges),
        "edges_with_multiplicity_over_two": sum(n > 2 for n in edges.values()),
        "boundary_edges": sum(n == 1 for n in edges.values()),
        "boundary_vertex_degree_histogram": {str(k): v for k, v in sorted(Counter(degrees.values()).items())},
        "boundary_vertices_with_degree_not_two": sum(n != 2 for n in degrees.values()),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("arrays", "parent", "plan", "audit", "output"):
        parser.add_argument("--" + key, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Existing verification output refused")
    plan = json.loads(args.plan.read_text())
    if sha(args.arrays) != plan["source_arrays_sha256"] or sha(args.parent / "manifest.json") != plan["parent_manifest_sha256"]:
        raise ValueError("Pinned input mismatch")
    entries = {x["path"]: x for x in json.loads((args.parent / "manifest.json").read_text())["files"]}
    report = json.loads((args.audit / "audit.json").read_text())
    if report["plan_sha256"] != sha(args.plan):
        raise ValueError("Plan mismatch")
    with np.load(args.arrays, allow_pickle=False) as d:
        vertices, faces = d["vertices"], d["triangles"]
    verified, total_candidates = [], 0
    for i, row in enumerate(report["regions"]):
        if row["region"] != i:
            raise ValueError("Region identity mismatch")
        parent_path = args.parent / f"study-001/region-{i}-models.npz"
        selection_path = args.parent / f"study-001/region-{i}-selection.npz"
        for p in (parent_path, selection_path):
            if sha(p) != entries[str(p.relative_to(args.parent))]["sha256"]:
                raise ValueError("Frozen parent input changed")
        with np.load(parent_path, allow_pickle=False) as d:
            ids, vi = d["original_source_face_ids"], d["original_source_vertex_ids"]
            uv = ((vertices[vi] - d["origin"]) @ d["frame"].T)[:, :2] / d["uv_scale"]
        with np.load(selection_path, allow_pickle=False) as d:
            if not np.array_equal(ids, d["selected_original_face_ids"]):
                raise ValueError("Original selection changed")
        original_vi, inverse = np.unique(faces[ids], return_inverse=True)
        if not np.array_equal(original_vi, vi):
            raise ValueError("Original vertex membership changed")
        triangles = inverse.reshape(-1, 3)
        path = args.audit / f"region-{i}-chart.npz"
        if sha(path) != row["private_chart_sha256"]:
            raise ValueError("Private chart hash mismatch")
        with np.load(path, allow_pickle=False) as data:
            if any(not np.array_equal(data[k], v) for k, v in
                   (("original_face_ids", ids), ("original_vertex_ids", vi), ("uv", uv), ("original_local_triangles", triangles))):
                raise ValueError("Stored chart differs from original source")
            pairs = broadphase(uv, triangles)
            if not np.array_equal(pairs, data["aabb_pairs"]):
                raise ValueError("Candidate pair census mismatch")
            rational = [tuple(F(float(x)) for x in point) for point in uv]
            polygons = [tuple(rational[int(k)] for k in face) for face in triangles]
            signs = [int(det(*p) > 0) - int(det(*p) < 0) for p in polygons]
            overlaps, unshared, degenerate = [], [], 0
            for a, b in pairs:
                if signs[a] == 0 or signs[b] == 0:
                    degenerate += 1
                    continue
                closed, strict = separate(polygons[a], polygons[b])
                if strict:
                    if clip_area(polygons[a], polygons[b]) <= 0:
                        raise ValueError("Strict pair has no positive clipped area")
                    overlaps.append((int(a), int(b)))
                if closed and not set(triangles[a]).intersection(triangles[b]):
                    unshared.append((int(a), int(b)))
            for key, pairs_expected in (("overlap_pairs", overlaps), ("unshared_contact_pairs", unshared)):
                if not np.array_equal(data[key], np.array(pairs_expected, dtype=np.int64).reshape(-1, 2)):
                    raise ValueError("Exact pair classification mismatch")
        expected = original_topology(triangles)
        expected.update(projected_sign_counts={str(k): signs.count(k) for k in (-1, 0, 1)},
                        aabb_candidate_pairs=len(pairs), candidate_pairs_with_degenerate_triangle=degenerate,
                        positive_area_overlap_pairs=len(overlaps), closed_contacts_without_original_shared_vertex=len(unshared))
        for key, value in expected.items():
            if row[key] != value:
                raise ValueError("Aggregate audit mismatch: " + key)
        obstruction = bool(overlaps or unshared or 0 in signs or expected["boundary_vertices_with_degree_not_two"])
        if row["observed_chart_obstruction"] != obstruction or row["native_smooth_surface_admitted"] is not False or row["full_projection_injectivity_accepted"] is not False:
            raise ValueError("Unsupported admission state")
        verified.append(i)
        total_candidates += len(pairs)
    if verified != list(range(8)):
        raise ValueError("Incomplete eight-region audit")
    # A positive overlap and a shared-edge-only contact distinguish area from touch.
    t = [(F(0), F(0)), (F(1), F(0)), (F(0), F(1))]
    assert clip_area(t, t) == F(1, 2)
    assert clip_area(t, [(F(1), F(0)), (F(1), F(1)), (F(0), F(1))]) == 0
    result = {"regions_verified": len(verified), "candidate_pairs_independently_classified": total_candidates,
              "original_membership_and_projection_exact": True, "original_boundary_topology_verified": True,
              "dyadic_predicates_independently_checked_with_Fraction": True,
              "actual_positive_pairs_requiring_clipping": sum(r["positive_area_overlap_pairs"] for r in report["regions"]),
              "positive_pair_clipping_scope": "Every actual positive pair; zero in this run. Two separate synthetic clipping controls also execute.",
              "independent_clip_controls": 2, "full_projection_injectivity_accepted": False,
              "physical_acceptance": False, "manufacturing_authorized": False}
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
