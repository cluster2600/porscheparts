"""Partition every fixed acquired chamber face into source-edge disk domains."""
import argparse
from collections import defaultdict
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np


def sha(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def edges(face):
    return tuple(tuple(sorted((int(face[i]), int(face[(i + 1) % 3])))) for i in range(3))


def incidence(triangles):
    uses = defaultdict(list)
    for i, face in enumerate(triangles):
        for edge in edges(face):
            uses[edge].append(i)
    if any(len(v) > 2 for v in uses.values()):
        raise ValueError("Nonmanifold selected source edge")
    return uses


def inside(point, triangle, predicate):
    sign = 1 if predicate.orient(*triangle) > 0 else -1
    return all(sign * predicate.orient(a, b, point) >= 0 for a, b in zip(triangle, triangle[1:] + triangle[:1]))


def contact_audit(uv, triangles, candidate_pairs, predicate):
    points = predicate.integer_points(uv)
    polygons = [tuple(points[int(v)] for v in face) for face in triangles]
    if any(predicate.orient(*p) == 0 for p in polygons):
        raise ValueError("Collapsed projected source face")
    illegal = []
    for i, j in candidate_pairs:
        closed, positive = predicate.intersect(polygons[i], polygons[j])
        if not closed:
            continue
        common = set(triangles[i]).intersection(triangles[j])
        bad = positive or not common
        if not bad and len(common) == 1:
            for own, other in ((i, j), (j, i)):
                if any(int(v) not in common and inside(points[int(v)], polygons[other], predicate) for v in triangles[own]):
                    bad = True
        if bad:
            illegal.append((int(i), int(j)))
    return np.array(illegal, dtype=np.int64).reshape(-1, 2)


def partition(triangles, original_ids):
    uses = incidence(triangles)
    face_edges = [set(edges(face)) for face in triangles]
    face_vertices = [set(map(int, face)) for face in triangles]
    remaining = set(range(len(triangles)))
    labels = np.full(len(triangles), -1, dtype=np.int64)
    trace, offsets = [], [0]
    label = 0
    while remaining:
        seed = min(remaining, key=lambda i: int(original_ids[i]))
        boundary, present = set(), set()
        chosen = seed
        while chosen is not None:
            labels[chosen] = label
            remaining.remove(chosen)
            trace.append(chosen)
            boundary.symmetric_difference_update(face_edges[chosen])
            present.update(face_vertices[chosen])
            frontier = sorted({i for e in boundary for i in uses[e] if i in remaining},
                              key=lambda i: int(original_ids[i]))
            chosen = None
            for i in frontier:
                shared = boundary.intersection(face_edges[i])
                if len(shared) not in (1, 2):
                    continue
                arc_vertices = set().union(*map(set, shared))
                if present.intersection(face_vertices[i]) == arc_vertices:
                    chosen = i
                    break
        offsets.append(len(trace))
        label += 1
    return labels, np.array(trace, dtype=np.int64), np.array(offsets, dtype=np.int64), uses


def domain_boundary(triangles):
    uses = incidence(triangles)
    directed = {}
    for face in triangles:
        for a, b in zip(face, np.roll(face, -1)):
            if len(uses[tuple(sorted((int(a), int(b))))]) == 1:
                if int(a) in directed:
                    raise ValueError("Branched domain boundary")
                directed[int(a)] = int(b)
    if not directed or set(directed) != set(directed.values()):
        raise ValueError("Domain boundary is not cycles")
    start = min(directed)
    loop, current = [], start
    while current not in loop:
        loop.append(current)
        current = directed[current]
    if current != start or len(loop) != len(directed):
        raise ValueError("Domain has multiple boundary cycles")
    if len(np.unique(triangles)) - len(uses) + len(triangles) != 1:
        raise ValueError("Domain Euler characteristic is not one")
    return loop


def controls(predicate):
    uv = np.array([[0., 0.], [1., 0.], [0., 1.], [-1., 0.], [0., -1.]])
    triangles = np.array([[0, 1, 2], [0, 3, 4]])
    labels, _, _, _ = partition(triangles, np.array([9, 3]))
    assert len(np.unique(labels)) == 2 and labels[1] == 0
    # Two triangles share one original point and have a further collinear overlap.
    bad_uv = np.array([[0., 0.], [2., 0.], [0., 1.], [1., 0.], [0., -1.]])
    bad = contact_audit(bad_uv, np.array([[0, 1, 2], [0, 4, 3]]), np.array([[0, 1]]), predicate)
    assert len(bad) == 1
    assert len(contact_audit(uv, triangles, np.array([[0, 1]]), predicate)) == 0
    ring = np.array([[0, 1, 4], [0, 4, 3], [1, 2, 5], [1, 5, 4],
                     [3, 4, 7], [3, 7, 6], [4, 5, 8], [4, 8, 7]])
    groups, _, _, _ = partition(ring, np.arange(len(ring)))
    for group in np.unique(groups):
        domain_boundary(ring[groups == group])
    return {"point_contact_separated": True, "minimum_original_id_seed": True,
            "unshared_collinear_segment_refused": True, "legal_common_vertex_contact": True,
            "all_square_triangles_preserved_in_disk_domains": True}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("arrays", "parent", "plan", "output"):
        p.add_argument("--" + key, type=Path, required=True)
    a = p.parse_args()
    plan = json.loads(a.plan.read_text())
    if sha(a.arrays) != plan["source_arrays_sha256"] or sha(a.parent / "manifest.json") != plan["parent_manifest_sha256"]:
        raise ValueError("Pinned source or chart bundle changed")
    files = {r["path"]: r for r in json.loads((a.parent / "manifest.json").read_text())["files"]}
    helper = a.parent / "source/audit_charts.py"
    if sha(helper) != plan["retained_predicate_source_sha256"]:
        raise ValueError("Frozen predicate source changed")
    spec = importlib.util.spec_from_file_location("retained_chart_predicates", helper)
    predicate = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(predicate)
    with np.load(a.arrays, allow_pickle=False) as d:
        original = d["triangles"]
    a.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    results = []
    for i in range(8):
        source = a.parent / plan["parent_final_audit"] / f"region-{i}-chart.npz"
        if sha(source) != files[str(source.relative_to(a.parent))]["sha256"]:
            raise ValueError("Frozen source chart changed")
        with np.load(source, allow_pickle=False) as d:
            vi, ids, triangles, uv, pairs = (d[k] for k in ("original_vertex_ids", "original_face_ids", "original_local_triangles", "uv", "aabb_pairs"))
        if not np.array_equal(vi[triangles], original[ids]):
            raise ValueError("Source face membership changed")
        illegal = contact_audit(uv, triangles, pairs, predicate)
        if len(illegal):
            np.save(a.output / f"region-{i}-illegal-pairs.npy", illegal)
            raise ValueError("Shared-simplex projection contact obstruction")
        labels, trace, offsets, uses = partition(triangles, ids)
        boundary_loops, loop_offsets, sizes = [], [0], []
        for label in range(len(offsets) - 1):
            domain = triangles[labels == label]
            loop = domain_boundary(domain)
            boundary_loops.extend(loop)
            loop_offsets.append(len(boundary_loops))
            sizes.append(len(domain))
        cuts = [(edge[0], edge[1], int(labels[use[0]]), int(labels[use[1]]))
                for edge, use in sorted(uses.items()) if len(use) == 2 and labels[use[0]] != labels[use[1]]]
        target = a.output / f"region-{i}-atlas.npz"
        np.savez_compressed(target, original_face_ids=ids, original_vertex_ids=vi,
                            original_local_triangles=triangles, labels=labels,
                            growth_trace=trace, growth_offsets=offsets,
                            boundary_vertices=np.array(boundary_loops, dtype=np.int64),
                            boundary_offsets=np.array(loop_offsets, dtype=np.int64),
                            cut_edges=np.array(cuts, dtype=np.int64).reshape(-1, 4))
        results.append({"region": i, "source_faces": len(ids), "disk_domains": len(sizes),
                        "domain_face_counts": sizes, "existing_source_edges_used_as_cuts": len(cuts),
                        "complete_projected_simplex_contact_obstructions": 0,
                        "private_atlas_sha256": sha(target), "new_coordinates": 0,
                        "source_faces_removed": 0, "native_export_admitted": False})
    report = {"plan_sha256": sha(a.plan), "producer_sha256": sha(__file__),
              "regions": results, "controls": controls(predicate),
              "physical_acceptance": False, "manufacturing_authorized": False}
    (a.output / "atlas.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
