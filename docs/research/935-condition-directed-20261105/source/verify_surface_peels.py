#!/usr/bin/env python3
"""Independently verify and apply admitted calculation-surface sliver peels.

All local proofs use Fraction coordinates, independently of the proposal's
integer lattice implementation. Complete native surface and volume validation
must still succeed after this export. No original printing master is changed.
"""
import argparse
from collections import defaultdict
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import signal
import time

import numpy as np

PATTERN = np.array([[1, 2, 3], [0, 3, 2], [0, 1, 3], [0, 2, 1]])


def sha(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def difference(a, b):
    return tuple(x-y for x, y in zip(a, b))


def product(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def inner(a, b):
    return sum(x*y for x, y in zip(a, b))


def patch_proof(xyz, old_slots, bound):
    assert len(set(old_slots)) == 2 and all(0 <= x < 4 for x in old_slots)
    points = [tuple(F.from_float(float(x)) for x in p) for p in xyz]
    det = inner(difference(points[1], points[0]), product(difference(points[2], points[0]), difference(points[3], points[0])))
    assert det > 0
    old = [PATTERN[k].tolist() for k in old_slots]
    new = [PATTERN[k][::-1].tolist() for k in range(4) if k not in old_slots]
    normals = [product(difference(points[b], points[a]), difference(points[c], points[a])) for a, b, c in old+new]
    axis = max(range(3), key=lambda i: abs(normals[0][i]))
    assert all(n[axis]*normals[0][axis] > 0 for n in normals)
    # Plane interpolation in a common convex projected quad. Residuals at the
    # first three vertices vanish; the fourth is det/projected determinant.
    deviation = abs(det/normals[0][axis]); assert deviation <= bound
    cosine = 1-F(1, 1 << 40)
    for left in normals[:2]:
        for right in normals[2:]:
            ip = inner(left, right)
            assert ip > 0 and ip*ip >= cosine*cosine*inner(left, left)*inner(right, right)
    quality = []
    for tri, normal in zip(old+new, normals):
        edge_sum = sum(inner(difference(points[tri[a]], points[tri[b]]), difference(points[tri[a]], points[tri[b]])) for a, b in ((0, 1), (1, 2), (2, 0)))
        quality.append(12*inner(normal, normal)/(edge_sum*edge_sum))
    assert min(quality[2:]) >= min(quality[:2]) and min(quality[2:]) >= F.from_float(.01)**3
    return deviation, det/6, old, new


def key(a, b):
    return min(int(a), int(b))*(1 << 32)+max(int(a), int(b))


def all_edge_cells(rows, wanted):
    queries = np.asarray(sorted(wanted), dtype=np.uint64)
    found = defaultdict(list)
    if not len(queries):
        return found
    width = rows.shape[1]
    for start in range(0, len(rows), 200000):
        part = rows[start:start+200000].astype(np.uint64)
        for i in range(width):
            for j in range(i+1, width):
                values = np.minimum(part[:, i], part[:, j])*np.uint64(1 << 32)+np.maximum(part[:, i], part[:, j])
                at = np.searchsorted(queries, values)
                indices = np.flatnonzero(at < len(queries))
                indices = indices[queries[at[indices]] == values[indices]]
                for index in indices:
                    found[int(values[index])].append(start+int(index))
    return found


def cycle_link(tets, endpoints):
    edges = [tuple(sorted(set(map(int, t))-set(endpoints))) for t in tets]
    assert all(len(e) == 2 for e in edges) and len(set(edges)) == len(edges) and len(edges) >= 3
    neighbors = defaultdict(set)
    for a, b in edges:
        neighbors[a].add(b); neighbors[b].add(a)
    assert all(len(adjacent) == 2 for adjacent in neighbors.values())
    remaining = set(neighbors); todo = [next(iter(remaining))]
    while todo:
        p = todo.pop()
        if p in remaining:
            remaining.remove(p); todo.extend(neighbors[p])
    assert not remaining


def upper(value):
    result = float(value)
    return math.nextafter(result, math.inf) if F.from_float(result) < value else result


def controls():
    epsilon = 2.**-44
    points = np.array([[0., 0, 0], [1., 1, epsilon], [1., 0, 0], [0., 1, 0]])
    delta, loss, old, new = patch_proof(points, [2, 3], F(512, 1 << 52))
    assert delta == F(1, 1 << 44) and loss == F(1, 6*(1 << 44))
    assert new == [[3, 2, 1], [2, 3, 0]]
    try:
        patch_proof(points, [2, 3], delta/2)
    except AssertionError:
        pass
    else:
        raise AssertionError("Excess displacement accepted")
    source = np.array([[0, 1, 2, 3], [4, 0, 2, 3], [4, 1, 3, 2]])
    cycle_link(source, (2, 3))
    for bad in (source[:2], np.concatenate((source, source[:1]))):
        try:
            cycle_link(bad, (2, 3))
        except AssertionError:
            pass
        else:
            raise AssertionError("Non-cycle link accepted")
    assert all_edge_cells(np.array([[2100001, 2100003, 2100005]], dtype=np.int64), {key(2100001, 2100005)})[key(2100001, 2100005)] == [0]
    assert F.from_float(upper(F(1, 3))) >= F(1, 3)
    return {"independent_fraction_fixture": True, "exact_reference_delta_and_volume": True,
        "actual_new_outward_face_orders": True, "invalid_link_and_excess_delta_refusals": True,
        "large_exact_edge_key_and_upward_reporting": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("mesh", "surface-parent", "proposal-root", "features", "output"):
        parser.add_argument("--"+name, type=Path, required=True)
    parser.add_argument("--control-only", action="store_true")
    args = parser.parse_args(); args.output.mkdir(mode=0o700, exist_ok=False)
    signal.signal(signal.SIGALRM, signal.SIG_DFL); signal.alarm(600)
    started = time.monotonic(); tested = controls()
    if args.control_only:
        (args.output/"report.json").write_text(json.dumps(tested, indent=2)+"\n")
        print(json.dumps(tested), flush=True); return
    assert sha(args.mesh) == "62717026bdfc3dc9c1a6cde682b32db12900cad8460f158a7319c41d001e2462"
    proposed = args.proposal_root/"private-admitted-peels.npz"
    admission = json.loads((args.proposal_root/"report.json").read_text())
    assert admission["source_sha256"] == "8207fca00a84be3243a04fe899c7977a7d41fe1d95526fd02c24396af271588d"
    assert sha(proposed) == admission["private_proposals_sha256"] == "9c94972e34279a6a32365f7b318b871ae62d664331bfe0856dae98df6930d9b8"
    with np.load(proposed, allow_pickle=False) as data:
        ids, slots, rows = data["cell_ids"], data["boundary_slots"], data["source_surface_face_ids"]
    assert len(ids) > 0 and len(ids) == len(np.unique(ids)) and slots.shape == rows.shape == (len(ids), 2)
    surface_path = args.surface_parent/"regularization-001/candidate.npz"
    tags_path = args.surface_parent/"regularization-001/candidate-tags.npy"
    assert sha(surface_path) == "5b04e72b5f7b48f340a39c14009292c52c1bf1ac422ad64cd3250c17ddf51db4"
    assert sha(tags_path) == "716a7c0f155551ec42db10527b4c53ea2ed95948d0cc027e7b786f3b9f4ce0b5"
    assert sha(args.surface_parent/"manifest.json") == "3d23346c1d874be4fed6f58ce3164f00c8e6fab066caef033f5eacb005bfc3c2"
    manifest = {r["path"]: r["sha256"] for r in json.loads((args.surface_parent/"manifest.json").read_text())["files"]}
    map_path = args.surface_parent/"regularization-001/private-collapse-map.npz"
    assert sha(map_path) == manifest["regularization-001/private-collapse-map.npz"]
    with np.load(args.mesh, allow_pickle=False) as data:
        nodes, cells = data["nodes"], data["tets"]
    with np.load(surface_path, allow_pickle=False) as data:
        vertices, faces = data["vertices"], data["triangles"]
    assert np.array_equal(nodes[:len(vertices)].view(np.uint64), vertices.view(np.uint64))
    tags = np.load(tags_path, allow_pickle=False)
    cap_vertices = np.unique(faces[tags > 0])
    assert not np.isin(cells[ids], cap_vertices).any()
    with np.load(map_path, allow_pickle=False) as data:
        mapping, used = data["mapping"], data["used_source_vertices"]
    assert sha(args.features) == "e5087c3cd5c90208acb56adff830bb39edc58bb0d93362b9a57b5cbf944b70f3"
    original = np.load(args.features, allow_pickle=False)
    inverse = np.full(len(mapping), -1, dtype=np.int64); inverse[used] = np.arange(len(used))
    curves = inverse[mapping[np.column_stack((original//len(mapping), original%len(mapping)))]]
    assert (curves >= 0).all()
    protected = {key(a, b) for a, b in curves if a != b}
    assert len(np.unique(cells[ids])) == 4*len(ids), "Patches share vertices"
    bound = F(512, 1 << 52)*max(F.from_float(float(x)) for x in np.ptp(vertices, axis=0))
    parent_bound = F.from_float(math.nextafter(.009643215373731693, math.inf))
    maximum = F(0); loss = F(0); old_edges = []; new_edges = []; new_faces = []
    assert np.all(tags[rows] == 0)
    for cell_id, old_slots, source_rows in zip(ids, slots, rows):
        cell = cells[cell_id]
        old_triangles = cell[PATTERN[old_slots]]
        assert np.array_equal(np.sort(old_triangles, axis=1), np.sort(faces[source_rows], axis=1))
        diagonal = sorted(set(map(int, old_triangles[0])) & set(map(int, old_triangles[1])))
        alternate = sorted(set(map(int, cell))-set(diagonal))
        assert len(diagonal) == len(alternate) == 2 and key(*diagonal) not in protected
        delta, removed, _, new = patch_proof(nodes[cell], old_slots.tolist(), bound)
        maximum = max(maximum, delta); loss += removed
        old_edges.append(diagonal); new_edges.append(alternate); new_faces.append(cell[np.asarray(new)])
    assert parent_bound+maximum < F.from_float(.01)
    tetra_incidence = all_edge_cells(cells, {key(*e) for e in old_edges+new_edges})
    boundary_incidence = all_edge_cells(faces, {key(*e) for e in new_edges})
    for cell_id, previous, alternate in zip(ids, old_edges, new_edges):
        assert tetra_incidence[key(*previous)] == [int(cell_id)]
        assert not boundary_incidence[key(*alternate)]
        cycle_link(cells[tetra_incidence[key(*alternate)]], alternate)
    # Exactly two boundary triangles are replaced, no vertex or cap is moved.
    changed = faces.copy(); changed[rows.reshape(-1)] = np.asarray(new_faces).reshape(-1, 3)
    assert np.array_equal(changed[tags > 0], faces[tags > 0])
    retained = np.ones(len(cells), dtype=bool); retained[ids] = False
    candidate_cells = cells[retained]
    volume_path = args.output/"candidate-volume.npz"; surface_out = args.output/"candidate-surface.npz"
    np.savez_compressed(volume_path, nodes=nodes, tets=candidate_cells, boundary=changed)
    np.savez_compressed(surface_out, vertices=vertices, triangles=changed)
    np.save(args.output/"candidate-tags.npy", tags)
    np.save(args.output/"private-removed-source-cell-ids.npy", np.sort(ids))
    # Reload actual exports and compare every tuple/coordinate bit before release.
    with np.load(volume_path, allow_pickle=False) as exported:
        assert np.array_equal(exported["nodes"].view(np.uint64), nodes.view(np.uint64))
        assert np.array_equal(exported["tets"], candidate_cells) and np.array_equal(exported["boundary"], changed)
    with np.load(surface_out, allow_pickle=False) as exported:
        assert np.array_equal(exported["vertices"].view(np.uint64), vertices.view(np.uint64)) and np.array_equal(exported["triangles"], changed)
    result = {"source_sha256": sha(Path(__file__)), "controls": tested, "parent_mesh_sha256": sha(args.mesh),
        "proposal_sha256": sha(proposed), "removed_tetrahedra": len(ids), "retained_tetrahedra": len(candidate_cells),
        "changed_surface_faces": 2*len(ids), "independent_exact_local_proofs": len(ids),
        "all_complete_old_edge_valences_one": True, "all_complete_new_edge_links_simple_cycles": True,
        "new_surface_edges_absent_from_parent_boundary": True, "patches_pairwise_vertex_disjoint": True,
        "all_node_coordinates_bitwise_identical": True, "all_retained_tetrahedron_tuples_identical": True,
        "all_construction_caps_identical": True, "marked_curve_images_preserved": True,
        "exact_same_surface_claimed": False, "surface_map_scope": "Continuous bijection on each convex projected quadrilateral; identity on its outer edges and the unchanged surface; bound is nominal geometry, not acquired-scan metrology",
        "maximum_local_graph_correspondence_bound_nominal_mm": upper(maximum),
        "composed_complete_surface_correspondence_bound_nominal_mm": upper(parent_bound+maximum),
        "exact_removed_volume_fraction_nominal_mm3": [str(loss.numerator), str(loss.denominator)],
        "removed_volume_upper_nominal_mm3": upper(loss), "candidate_volume_sha256": sha(volume_path),
        "candidate_surface_sha256": sha(surface_out), "candidate_tags_sha256": sha(args.output/"candidate-tags.npy"),
        "complete_native_surface_validation_pending": True, "complete_volume_validation_pending": True,
        "original_printing_master_changed": False, "physics_admitted": False, "manufacturing_qualified": False,
        "new_paid_compute_usd": 0, "seconds": time.monotonic()-started}
    (args.output/"report.json").write_text(json.dumps(result, indent=2)+"\n")
    signal.alarm(0); print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
