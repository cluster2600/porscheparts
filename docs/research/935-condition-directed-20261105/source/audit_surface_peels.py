#!/usr/bin/env python3
"""Read-only, exact admission of microscopic calculation-surface sliver peels.

This changes the represented boundary if subsequently applied. It is neither an
exact-surface-preserving operation nor permission to change the printing master.
"""
import argparse
from collections import Counter
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path
import signal
import time

import numpy as np

FACES = np.array([[1, 2, 3], [0, 3, 2], [0, 1, 3], [0, 2, 1]])
EDGES = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))


def sha(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def lattice(xyz):
    """Represent the actual binary64 input exactly, without rounding coordinates."""
    ratios = [[float(value).as_integer_ratio() for value in row] for row in xyz]
    denominator = max(q for row in ratios for _, q in row)
    return [tuple(p*(denominator//q) for p, q in row) for row in ratios], denominator


def geometry(xyz, slots, bound):
    """Exact local graph correspondence, normal and triangle-quality contract."""
    p, denominator = lattice(xyz)
    determinant = dot(sub(p[1], p[0]), cross(sub(p[2], p[0]), sub(p[3], p[0])))
    if determinant <= 0:
        return "nonpositive_source", None
    old = [FACES[k].tolist() for k in slots]
    new = [FACES[k][::-1].tolist() for k in range(4) if k not in slots]
    normals = [cross(sub(p[t[1]], p[t[0]]), sub(p[t[2]], p[t[0]])) for t in old + new]
    axis = max(range(3), key=lambda k: abs(normals[0][k]))
    projected = [n[axis] for n in normals]
    if not all(v*projected[0] > 0 for v in projected):
        return "nonconvex_projected_patch", None
    # Both triangulations cover the same strictly convex projected quadrilateral.
    # Subtract the affine plane of old[0]. Three vertex residuals vanish; the
    # fourth equals det/projected_area. Both graph interpolants stay in its range.
    deviation = Q(abs(determinant), abs(projected[0])*denominator)
    if deviation > bound:
        return "correspondence_budget", None
    for a in normals[:2]:
        for b in normals[2:]:
            product = dot(a, b)
            if product <= 0 or product*product*(1 << 80) < ((1 << 40)-1)**2*dot(a, a)*dot(b, b):
                return "normal_change", None
    quality = []
    for tri, normal in zip(old + new, normals):
        lengths = sum(dot(sub(p[tri[a]], p[tri[b]]), sub(p[tri[a]], p[tri[b]]))
                      for a, b in ((0, 1), (1, 2), (2, 0)))
        quality.append(Q(12*dot(normal, normal), lengths*lengths))
    if min(quality[2:]) < min(quality[:2]):
        return "triangle_quality_worsens", None
    if min(quality[2:]) < Q.from_float(.01)**3:
        return "new_forced_face", None
    return "admitted_geometry", {"deviation": deviation,
        "removed_volume": Q(determinant, 6*denominator**3), "old": old, "new": new}


def edge_key(edge):
    a, b = sorted(map(int, edge))
    return a*(1 << 32)+b


def links(cells, edge):
    """An interior edge's complete tetrahedral link must be one simple cycle."""
    a, b = edge
    graph = {}
    seen = set()
    for tet in cells:
        if a not in tet or b not in tet:
            return False
        other = tuple(sorted(set(map(int, tet)) - {a, b}))
        if len(other) != 2 or other in seen:
            return False
        seen.add(other)
        x, y = other
        graph.setdefault(x, set()).add(y); graph.setdefault(y, set()).add(x)
    if len(graph) < 3 or any(len(v) != 2 for v in graph.values()):
        return False
    reached = set(); todo = [next(iter(graph))]
    while todo:
        vertex = todo.pop()
        if vertex not in reached:
            reached.add(vertex); todo.extend(graph[vertex] - reached)
    return len(reached) == len(graph)


def incidences(rows, edge_pairs):
    """Complete streaming source incidence, not an assumed local neighborhood."""
    queries = np.array(sorted(set(edge_key(e) for e in edge_pairs)), dtype=np.uint64)
    hits = {int(k): [] for k in queries}
    pairs = EDGES if rows.shape[1] == 4 else ((0, 1), (1, 2), (2, 0))
    if not len(queries):
        return hits
    for start in range(0, len(rows), 200000):
        chunk = rows[start:start+200000]
        for a, b in pairs:
            key = np.minimum(chunk[:, a], chunk[:, b]).astype(np.uint64)*(1 << 32) + np.maximum(chunk[:, a], chunk[:, b])
            positions = np.searchsorted(queries, key)
            valid = positions < len(queries)
            indices = np.flatnonzero(valid)
            indices = indices[queries[positions[indices]] == key[indices]]
            for index in indices:
                hits[int(key[index])].append(start + int(index))
    return hits


def controls():
    epsilon = 2.**-44
    points = np.array([[0., 0, 0], [1., 1, epsilon], [1., 0, 0], [0., 1, 0], [.5, .5, -1]])
    old = np.array([[0, 1, 2, 3], [4, 0, 2, 3], [4, 1, 3, 2]])
    verdict, proof = geometry(points[:4], [2, 3], Q(512, 1 << 52))
    assert verdict == "admitted_geometry" and proof["deviation"] == Q(1, 1 << 44)
    assert proof["removed_volume"] == Q(1, 6*(1 << 44))
    assert links(old, (2, 3)) and not links(old[:2], (2, 3))
    assert not links(np.concatenate((old, old[:1])), (2, 3))
    incidence = incidences(old, [(0, 1), (2, 3)])
    assert incidence[edge_key((0, 1))] == [0] and len(incidence[edge_key((2, 3))]) == 3
    boundary = []
    for tet in old:
        for face in tet[FACES]:
            key = tuple(sorted(face))
            if any(tuple(sorted(f)) == key for f in boundary):
                boundary = [f for f in boundary if tuple(sorted(f)) != key]
            else:
                boundary.append(face)
    assert not incidences(np.asarray(boundary), [(2, 3)])[edge_key((2, 3))]
    assert geometry(points[:4], [2, 3], Q(1, 1 << 45))[0] == "correspondence_budget"
    inverted = points[:4].copy(); inverted[[0, 1]] = inverted[[1, 0]]
    assert geometry(inverted, [2, 3], Q(1))[0] == "nonpositive_source"
    flat = points[:4].copy(); flat[1, 2] = 0
    assert geometry(flat, [2, 3], Q(1))[0] == "nonpositive_source"
    assert geometry(points[:4], [0, 2], Q(1))[0] == "nonconvex_projected_patch"
    return {"actual_five_point_three_tet_fixture": True, "exact_expected_volume_and_graph_bound": True,
        "complete_edge_link_cycle": True, "open_and_duplicate_links_refused": True,
        "nonconvex_flat_inverted_and_excess_displacement_refused": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("mesh", "surface-parent", "attribution", "features", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--control-only", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, exist_ok=False)
    signal.signal(signal.SIGALRM, signal.SIG_DFL); signal.alarm(600)
    started = time.monotonic(); tested = controls()
    if args.control_only:
        (args.output / "report.json").write_text(json.dumps(tested, indent=2)+"\n")
        print(json.dumps(tested)); return
    assert sha(args.mesh) == "62717026bdfc3dc9c1a6cde682b32db12900cad8460f158a7319c41d001e2462"
    assert sha(args.attribution) == "2095e05ff33b6570872c23eb5e3c340f0956e7463cc866789c72efed7559aed6"
    assert sha(args.features) == "e5087c3cd5c90208acb56adff830bb39edc58bb0d93362b9a57b5cbf944b70f3"
    surface_path = args.surface_parent / "regularization-001/candidate.npz"
    tags_path = args.surface_parent / "regularization-001/candidate-tags.npy"
    mapping_path = args.surface_parent / "regularization-001/private-collapse-map.npz"
    assert sha(surface_path) == "5b04e72b5f7b48f340a39c14009292c52c1bf1ac422ad64cd3250c17ddf51db4"
    assert sha(tags_path) == "716a7c0f155551ec42db10527b4c53ea2ed95948d0cc027e7b786f3b9f4ce0b5"
    manifest = json.loads((args.surface_parent / "manifest.json").read_text())
    assert sha(args.surface_parent / "manifest.json") == "3d23346c1d874be4fed6f58ce3164f00c8e6fab066caef033f5eacb005bfc3c2"
    expected = {row["path"]: row["sha256"] for row in manifest["files"]}
    assert sha(mapping_path) == expected["regularization-001/private-collapse-map.npz"]
    with np.load(args.mesh, allow_pickle=False) as data:
        nodes, cells = data["nodes"], data["tets"]
    with np.load(surface_path, allow_pickle=False) as data:
        vertices, faces = data["vertices"], data["triangles"]
    assert np.array_equal(nodes[:len(vertices)].view(np.uint64), vertices.view(np.uint64))
    tags = np.load(tags_path, allow_pickle=False)
    with np.load(mapping_path, allow_pickle=False) as data:
        mapping, used = data["mapping"], data["used_source_vertices"]
    inverse = np.full(len(mapping), -1, dtype=np.int64); inverse[used] = np.arange(len(used))
    original = np.load(args.features, allow_pickle=False)
    mapped = inverse[mapping[np.column_stack((original//len(mapping), original%len(mapping)))]]
    assert (mapped >= 0).all()
    protected = {edge_key(e) for e in mapped if e[0] != e[1]}
    with np.load(args.attribution, allow_pickle=False) as data:
        ids, boundary_rows, caps = data["cell_ids"], data["source_boundary_face_ids"], data["vertex_cap_memberships"]
    # Fixed numerical envelope before examining candidates; not a process tolerance.
    extent = max(Q.from_float(float(v)) for v in np.ptp(vertices, axis=0))
    bound = Q(512, 1 << 52)*extent
    parent_bound = Q.from_float(.009643215373731693)
    assert parent_bound + bound < Q.from_float(.01)
    reasons = Counter(); proposed = []
    for position, cell_id in enumerate(ids):
        slots = np.flatnonzero(boundary_rows[position] >= 0).tolist()
        if len(slots) != 2:
            reasons["not_two_boundary_faces"] += 1; continue
        tet = cells[cell_id]
        if caps[position].any() or np.any(tags[boundary_rows[position, slots]] != 0):
            reasons["construction_cap_constraint"] += 1; continue
        diagonal = sorted(set(map(int, tet[FACES[slots[0]]])) & set(map(int, tet[FACES[slots[1]]])))
        other = sorted(set(map(int, tet)) - set(diagonal))
        if edge_key(diagonal) in protected:
            reasons["protected_marked_curve"] += 1; continue
        verdict, proof = geometry(nodes[tet], slots, bound)
        reasons[verdict] += 1
        if proof is not None:
            proposed.append((int(cell_id), slots, diagonal, other, proof, boundary_rows[position, slots]))
    pairs = [edge for row in proposed for edge in row[2:4]]
    volume_incidence = incidences(cells, pairs)
    surface_incidence = incidences(faces, [row[3] for row in proposed])
    admitted = []
    for row in proposed:
        cell_id, slots, diagonal, other, proof, rows = row
        if volume_incidence[edge_key(diagonal)] != [cell_id]:
            reasons["old_diagonal_tet_valence_not_one"] += 1; continue
        if surface_incidence[edge_key(other)]:
            reasons["new_diagonal_already_on_surface"] += 1; continue
        if not links(cells[volume_incidence[edge_key(other)]], other):
            reasons["new_diagonal_source_link_not_simple_cycle"] += 1; continue
        admitted.append(row)
    # Vertex-disjoint patches glue to the unchanged surface on disjoint cycles.
    packed = []; occupied = set()
    for row in sorted(admitted, key=lambda r: (r[4]["removed_volume"], r[0])):
        vertices_here = set(map(int, cells[row[0]]))
        if occupied & vertices_here:
            reasons["simultaneous_vertex_conflict"] += 1; continue
        occupied.update(vertices_here); packed.append(row)
    proposals = args.output / "private-admitted-peels.npz"
    np.savez_compressed(proposals, cell_ids=np.asarray([r[0] for r in packed], dtype=np.int64),
        boundary_slots=np.asarray([r[1] for r in packed], dtype=np.int64).reshape(-1, 2),
        source_surface_face_ids=np.asarray([r[5] for r in packed], dtype=np.int64).reshape(-1, 2))
    max_deviation = max((r[4]["deviation"] for r in packed), default=Q(0))
    removed_volume = sum((r[4]["removed_volume"] for r in packed), Q(0))
    result = {"source_sha256": sha(Path(__file__)), "input_mesh_sha256": sha(args.mesh),
        "input_attribution_sha256": sha(args.attribution), "controls": tested,
        "severe_cells_examined": len(ids), "exact_geometry_and_global_incidence_admitted": len(admitted),
        "vertex_disjoint_peels_admitted": len(packed), "reasons": dict(reasons),
        "fixed_maximum_graph_deviation_nominal_mm": float(bound),
        "maximum_admitted_exact_graph_deviation_nominal_mm": float(max_deviation),
        "exact_total_material_loss_fraction_nominal_mm3": [str(removed_volume.numerator), str(removed_volume.denominator)],
        "approximate_total_material_loss_nominal_mm3": float(removed_volume),
        "parent_complete_correspondence_bound_nominal_mm": float(parent_bound),
        "proposed_complete_correspondence_bound_nominal_mm": float(parent_bound+max_deviation),
        "marked_curve_images_and_cap_faces_protected": True, "every_input_coordinate_retained": True,
        "surface_geometry_would_change": True, "printing_master_change_permitted": False,
        "geometry_modified_in_this_audit": False, "manufacturing_qualified": False,
        "private_proposals_sha256": sha(proposals), "new_paid_compute_usd": 0,
        "seconds": time.monotonic()-started}
    (args.output / "report.json").write_text(json.dumps(result, indent=2)+"\n")
    signal.alarm(0); print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
