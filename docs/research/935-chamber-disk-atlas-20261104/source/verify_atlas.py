"""Verify source disk coverage, inductive growth, topology and complete contacts."""
import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np


def sha(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def edge_uses(triangles):
    result = defaultdict(list)
    for i, triangle in enumerate(triangles):
        for j in range(3):
            edge = tuple(sorted((int(triangle[j]), int(triangle[(j + 1) % 3]))))
            result[edge].append(i)
    return result


def reachable(nodes, adjacency):
    if not nodes:
        return False
    todo = [next(iter(nodes))]
    seen = set(todo)
    while todo:
        for v in adjacency[todo.pop()]:
            if v in nodes and v not in seen:
                seen.add(v)
                todo.append(v)
    return seen == nodes


def disk_certificate(triangles, recorded_loop):
    uses = edge_uses(triangles)
    if any(len(v) > 2 for v in uses.values()):
        raise ValueError("Domain edge multiplicity")
    adjacency = defaultdict(set)
    for pair in uses.values():
        if len(pair) == 2:
            a, b = pair
            adjacency[a].add(b)
            adjacency[b].add(a)
    if not reachable(set(range(len(triangles))), adjacency):
        raise ValueError("Disconnected domain")
    vertices = set(map(int, triangles.ravel()))
    if len(vertices) - len(uses) + len(triangles) != 1:
        raise ValueError("Domain is not Euler-one")
    boundary = {edge for edge, pair in uses.items() if len(pair) == 1}
    degree = Counter(v for e in boundary for v in e)
    loop = list(map(int, recorded_loop))
    loop_edges = {tuple(sorted((loop[i], loop[(i + 1) % len(loop)]))) for i in range(len(loop))}
    if not loop or len(loop) != len(set(loop)) or len(loop) != len(boundary) or loop_edges != boundary or any(d != 2 for d in degree.values()):
        raise ValueError("Stored domain boundary is not one simple source cycle")
    directed = set()
    for triangle in triangles:
        for j in range(3):
            a, b = int(triangle[j]), int(triangle[(j + 1) % 3])
            if tuple(sorted((a, b))) in boundary:
                directed.add((a, b))
    if {(loop[i], loop[(i + 1) % len(loop)]) for i in range(len(loop))} != directed:
        raise ValueError("Boundary source orientation changed")
    for v in vertices:
        star = set(np.flatnonzero(np.any(triangles == v, axis=1)).tolist())
        if not reachable(star, adjacency):
            raise ValueError("Domain vertex star has disconnected fans")


def replay(triangles, ids, labels, trace, offsets):
    uses = edge_uses(triangles)
    face_edges = [set(uses_key for uses_key in uses if i in uses[uses_key]) for i in range(len(triangles))]
    remaining = set(range(len(triangles)))
    for label, (start, end) in enumerate(zip(offsets[:-1], offsets[1:])):
        order = list(map(int, trace[start:end]))
        if not order or order[0] != min(remaining, key=lambda i: int(ids[i])):
            raise ValueError("Minimum-original-ID domain seed changed")
        counts, vertices = Counter(), set()

        def next_admissible():
            boundary = {e for e, n in counts.items() if n == 1}
            frontier = set()
            for edge in boundary:
                frontier.update(i for i in uses[edge] if i in remaining)
            candidates = []
            for i in frontier:
                shared = boundary & face_edges[i]
                if len(shared) in (1, 2):
                    arc = {v for e in shared for v in e}
                    if vertices & set(map(int, triangles[i])) == arc:
                        candidates.append(i)
            return min(candidates, key=lambda i: int(ids[i])) if candidates else None

        for position, i in enumerate(order):
            if i not in remaining or labels[i] != label:
                raise ValueError("Growth trace lost or duplicated source membership")
            if position and i != next_admissible():
                raise ValueError("First-admissible frontier rule changed")
            counts.update(face_edges[i])
            vertices.update(map(int, triangles[i]))
            remaining.remove(i)
        if next_admissible() is not None:
            raise ValueError("Domain ended before its fixed growth rule")
    if remaining or sorted(map(int, trace)) != list(range(len(triangles))):
        raise ValueError("Growth trace does not cover all original faces once")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("arrays", "parent", "plan", "atlas", "output"):
        p.add_argument("--" + key, type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise ValueError("Existing verification result refused")
    plan = json.loads(a.plan.read_text())
    if sha(a.arrays) != plan["source_arrays_sha256"] or sha(a.parent / "manifest.json") != plan["parent_manifest_sha256"]:
        raise ValueError("Pinned source changed")
    files = {r["path"]: r for r in json.loads((a.parent / "manifest.json").read_text())["files"]}
    helper_path = a.parent / "source/verify_charts.py"
    if sha(helper_path) != files["source/verify_charts.py"]["sha256"]:
        raise ValueError("Frozen independent predicates changed")
    spec = importlib.util.spec_from_file_location("frozen_independent_predicates", helper_path)
    helper = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(helper)
    report = json.loads((a.atlas / "atlas.json").read_text())
    if report["plan_sha256"] != sha(a.plan) or len(report["regions"]) != 8:
        raise ValueError("Plan or eight-region scope changed")
    with np.load(a.arrays, allow_pickle=False) as d:
        original_faces = d["triangles"]
    checks, all_ids, total_pairs = [], [], 0
    for i, row in enumerate(report["regions"]):
        source = a.parent / plan["parent_final_audit"] / f"region-{i}-chart.npz"
        path = a.atlas / f"region-{i}-atlas.npz"
        if sha(source) != files[str(source.relative_to(a.parent))]["sha256"] or sha(path) != row["private_atlas_sha256"]:
            raise ValueError("Input atlas/chart hash mismatch")
        with np.load(source, allow_pickle=False) as frozen, np.load(path, allow_pickle=False) as data:
            ids, vi, triangles = (data[k] for k in ("original_face_ids", "original_vertex_ids", "original_local_triangles"))
            for k in ("original_face_ids", "original_vertex_ids", "original_local_triangles"):
                if not np.array_equal(data[k], frozen[k]):
                    raise ValueError("Frozen original membership changed")
            if not np.array_equal(vi[triangles], original_faces[ids]):
                raise ValueError("Acquired original triangle changed")
            uv, pairs = frozen["uv"], helper.broadphase(frozen["uv"], triangles)
            if not np.array_equal(pairs, frozen["aabb_pairs"]):
                raise ValueError("Projected pair census changed")
            points = [tuple(helper.F(float(x)) for x in p) for p in uv]
            polygons = [tuple(points[int(v)] for v in t) for t in triangles]
            for first, second in pairs:
                closed, strict = helper.separate(polygons[first], polygons[second])
                if not closed:
                    continue
                common = set(triangles[first]) & set(triangles[second])
                if strict or not common:
                    raise ValueError("Projected contact exceeds original shared simplex")
                if len(common) == 1:
                    for own, other in ((first, second), (second, first)):
                        winding = 1 if helper.det(*polygons[other]) > 0 else -1
                        for v in triangles[own]:
                            if int(v) not in common and all(winding * helper.det(polygons[other][j], polygons[other][(j + 1) % 3], points[int(v)]) >= 0 for j in range(3)):
                                raise ValueError("Projected extra segment at a shared source vertex")
            labels, trace, offsets = data["labels"], data["growth_trace"], data["growth_offsets"]
            count = row["disk_domains"]
            if sorted(np.unique(labels).tolist()) != list(range(count)) or len(offsets) != count + 1 or offsets[0] != 0 or offsets[-1] != len(triangles):
                raise ValueError("Invalid complete domain labels or growth offsets")
            replay(triangles, ids, labels, trace, offsets)
            sizes = []
            boundary_offsets = data["boundary_offsets"]
            if len(boundary_offsets) != count + 1 or boundary_offsets[0] != 0 or boundary_offsets[-1] != len(data["boundary_vertices"]):
                raise ValueError("Invalid boundary offsets")
            for label in range(count):
                domain = triangles[labels == label]
                sizes.append(len(domain))
                disk_certificate(domain, data["boundary_vertices"][boundary_offsets[label]:boundary_offsets[label + 1]])
            uses = edge_uses(triangles)
            expected_cuts = [(e[0], e[1], int(labels[p[0]]), int(labels[p[1]])) for e, p in sorted(uses.items()) if len(p) == 2 and labels[p[0]] != labels[p[1]]]
            if not np.array_equal(data["cut_edges"], np.array(expected_cuts, dtype=np.int64).reshape(-1, 4)):
                raise ValueError("Cuts are not the exact existing source edges")
            if row["domain_face_counts"] != sizes or row["source_faces"] != len(ids) or row["existing_source_edges_used_as_cuts"] != len(expected_cuts) or row["new_coordinates"] != 0 or row["source_faces_removed"] != 0 or row["native_export_admitted"] is not False:
                raise ValueError("Atlas aggregate or admission changed")
            checks.append({"region": i, "source_faces": len(ids), "disk_domains": count, "atlas_sha256": sha(path)})
            all_ids.extend(map(int, ids))
            total_pairs += len(pairs)
    if len(set(all_ids)) != len(all_ids):
        raise ValueError("Original source faces duplicated across regions")
    result = {"plan_sha256": sha(a.plan), "atlas_report_sha256": sha(a.atlas / "atlas.json"),
              "regions": checks, "source_faces_once": len(all_ids),
              "disk_domains_verified": sum(r["disk_domains"] for r in checks),
              "complete_shared_simplex_pair_checks": total_pairs,
              "inductive_growth_and_priority_verified": True, "one_cycle_euler_one_and_single_vertex_fans": True,
              "original_membership_and_source_edge_cuts_verified": True,
              "eligible_for_exact_native_reference_export": True,
              "physical_acceptance": False, "manufacturing_authorized": False}
    a.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
