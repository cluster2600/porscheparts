#!/usr/bin/env python3
"""Complete boundary-vertex cavities and one face-neighbor ring at the worst cell.

Read-only source admission precedes each deterministic volume-centroid proposal.
The method preserves every old point and boundary triangle, adds one numerical
interior point, and requires an exact full signed-domain partition certificate.
"""
import argparse
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import time

import igl
import numpy as np

FACES = np.array([[1, 2, 3], [0, 3, 2], [0, 1, 3], [0, 2, 1]])
MAX_OLD_CELLS = 96
MAX_BOUNDARY_FACES = 196


def sha(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load(path, name, expected):
    assert sha(path) == expected
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def complete_vertex_stars(cells, vertices):
    query = np.array(sorted(vertices), dtype=cells.dtype)
    result = {int(v): [] for v in query}
    for start in range(0, len(cells), 200000):
        chunk = cells[start:start+200000]
        for column in range(4):
            values = chunk[:, column]; positions = np.searchsorted(query, values)
            ids = np.flatnonzero(positions < len(query))
            ids = ids[query[positions[ids]] == values[ids]]
            for i in ids:
                result[int(values[i])].append(start+int(i))
    for vertex, ids in result.items():
        assert len(ids) == len(set(ids)) and np.all(np.any(cells[ids] == vertex, axis=1))
        result[vertex] = sorted(ids)
    return result


def complete_face_hits(cells, query_tuples, records):
    queries = records(np.array(query_tuples, dtype=np.uint32)); result = [[] for _ in queries]
    for start in range(0, len(cells), 100000):
        chunk = cells[start:start+100000]
        for face in FACES:
            values = records(np.sort(chunk[:, face], axis=1))
            positions = np.searchsorted(queries, values); ids = np.flatnonzero(positions < len(queries))
            ids = ids[queries[positions[ids]] == values[ids]]
            for i in ids:
                result[int(positions[i])].append(start+int(i))
    assert all(1 <= len(hits) <= 2 and len(hits) == len(set(hits)) for hits in result)
    return {face:hits for face, hits in zip(query_tuples, result)}


def boundary_tags(surface, tags, query_tuples, records):
    queries = records(np.array(query_tuples, dtype=np.uint32)); result = np.full(len(queries), -1, dtype=np.int64)
    for start in range(0, len(surface), 50000):
        values = records(np.sort(surface[start:start+50000], axis=1))
        positions = np.searchsorted(queries, values); ids = np.flatnonzero(positions < len(queries))
        ids = ids[queries[positions[ids]] == values[ids]]
        assert np.all(result[positions[ids]] == -1)
        result[positions[ids]] = tags[start+ids]
    return dict(zip(query_tuples, map(int, result)))


def local_region(nodes, old, labels, contract, geometry):
    vertices = np.unique(old)
    local_nodes = nodes[vertices]
    local_old = np.searchsorted(vertices, old)
    faces = contract.boundary(local_old)
    result = {"old_cells": len(old), "source_vertices": len(vertices), "boundary_faces": len(faces),
        "global_boundary_faces": sum(labels.get(tuple(sorted(int(vertices[v]) for v in f)), -1) >= 0 for f in faces)}
    if len(old) > MAX_OLD_CELLS or len(faces) > MAX_BOUNDARY_FACES:
        result["verdict"] = "declared_local_resource_profile_exceeded"; return result, None
    try:
        contract.topology(faces)
    except AssertionError as error:
        result["verdict"] = str(error); return result, None
    used_boundary = {v for face in faces for v in face}
    result["old_vertices_interior_to_cavity"] = len(vertices)-len(used_boundary)
    points, _ = geometry.exact_points(local_nodes, range(len(vertices)))
    forced = []
    for face in faces:
        p = [points[v] for v in face]
        normal = geometry.cross(geometry.sub(p[1], p[0]), geometry.sub(p[2], p[0]))
        s = sum(geometry.dot(geometry.sub(p[a], p[b]), geometry.sub(p[a], p[b])) for a, b in ((0, 1), (0, 2), (1, 2)))
        assert geometry.dot(normal, normal) > 0
        if Q(12*geometry.dot(normal, normal), s*s) < Q.from_float(.01)**3:
            forced.append(tuple(sorted(int(vertices[v]) for v in face)))
    result.update(forced_fixed_faces=len(forced), forced_global_faces=sum(labels.get(f, -1) >= 0 for f in forced),
        forced_internal_interface_faces=sum(labels.get(f, -1) < 0 for f in forced))
    if forced:
        result["verdict"] = "fixed_faces_preclude_new_cell_quality_floor"; return result, None
    if len(used_boundary) != len(vertices):
        result["verdict"] = "old_interior_numerical_node_policy_not_admitted"; return result, None
    found, pairs, _ = igl.predicates.find_self_intersections(np.ascontiguousarray(local_nodes), np.asarray(faces, dtype=np.int64), False)
    assert bool(found) == bool(len(pairs)); result["source_boundary_intersection_pairs"] = len(pairs)
    if len(pairs):
        result["verdict"] = "source_cavity_boundary_intersections"; return result, None
    faces, ideal = contract.volume_centroid(local_nodes, local_old, geometry)
    actual = np.array([float(value) for value in ideal])
    augmented = np.vstack((local_nodes, actual))
    new = np.array([[len(vertices), *face] for face in faces], dtype=np.int64)
    try:
        proof = contract.certify(augmented, local_old, new, geometry)
    except AssertionError as error:
        result["verdict"] = str(error) or "exact_domain_or_shape_contract_failed"; return result, None
    result.update(verdict="exact_source_and_centroid_partition_admitted_pending_separate_verification",
        new_cells=len(new), old_bins=proof["old_bins"], new_bins=proof["new_bins"],
        old_pair_separations=proof["old_pair_separations"], new_pair_separations=proof["new_pair_separations"],
        old_minimum_quality_approx=float(proof["old_minimum_quality_cubed"])**(1/3),
        new_minimum_quality_approx=float(proof["new_minimum_quality_cubed"])**(1/3))
    global_new = np.empty_like(new)
    global_new[:, 0] = len(nodes); global_new[:, 1:] = vertices[new[:, 1:]]
    proposal = {"new_point": actual.tolist(), "ideal_volume_centroid": [[str(v.numerator), str(v.denominator)] for v in ideal],
        "new_cells": global_new.tolist(), "source_vertices": vertices.tolist(),
        "exact_domain_volume": [str(proof["exact_domain_volume"].numerator), str(proof["exact_domain_volume"].denominator)]}
    return result, proposal


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repository", "parent", "reference", "output"):
        parser.add_argument("--"+name, type=Path, required=True)
    parser.add_argument("--control-only", action="store_true")
    args = parser.parse_args(); args.output.mkdir(mode=0o700, exist_ok=False)
    signal.signal(signal.SIGALRM, signal.SIG_DFL); signal.alarm(600); started = time.monotonic()
    contract = load(Path(__file__).with_name("centroid_star_contract.py"), "actual_centroid_cavity_contract", "0983f355f6983a3d5611144362871f404e969bd5f11e6ad7889a0fce35b054bb")
    base = args.repository/"docs/research"
    geometry = load(base/"935-residual-source-admission-20261105/source/convex_partition_contract.py", "centroid_cavity_exact_primitives", "c06c37065561813a27791a4096d41c9e221f83ba48e775b2de6489f1f5a84a07")
    helper = load(base/"935-local-physics-20261105/source/inspect_tetrahedra.py", "centroid_cavity_face_keys", "fe8c7fa88f35d2d14094438bbae3b0860bde085a39b68f7ab941790cb4d1bec3")
    assert sha(args.reference) == "c7538b9d60465ddc94f11f28e0d04700ab22bd7c03c1fbbcd50bb82f5a9e7194"
    with np.load(args.reference, allow_pickle=False) as data:
        nodes, old, expected_nodes, expected_cells = data["source_nodes"], data["old_cells"], data["augmented_nodes"], data["reference_cells"]
    labels = {tuple(sorted(face)): 0 for face in contract.boundary(old)}
    tested, actual = local_region(nodes, old, labels, contract, geometry)
    assert actual and np.array_equal(np.array(actual["new_point"]).view(np.uint64), expected_nodes[-1].view(np.uint64))
    assert np.array_equal(np.array(actual["new_cells"]), expected_cells)
    stars = complete_vertex_stars(old, {0, 1}); assert stars[0] == stars[1] == list(range(6))
    face_queries = sorted({tuple(sorted(map(int, face))) for tet in old for face in tet[FACES]})
    hits = complete_face_hits(old, face_queries, helper.records)
    assert all(sorted(hits[face]) == [i for i, tet in enumerate(old) if all(v in tet for v in face)] for face in face_queries)
    source_boundary = np.array(contract.boundary(old), dtype=np.int64)
    classified = boundary_tags(source_boundary, np.zeros(len(source_boundary), dtype=np.int64), face_queries, helper.records)
    surface_keys = {tuple(sorted(map(int, face))) for face in source_boundary}
    assert all(classified[face] == (0 if face in surface_keys else -1) for face in face_queries)
    try:
        complete_face_hits(old, [(7, 8, 9)], helper.records)
    except AssertionError:
        pass
    else:
        raise AssertionError("Absent source face admitted")
    tri = np.array([[0, 0, 0], [2, 0, 0], [0, 2, 0], [.5, .5, -1], [.5, .5, 1], [1, 1, 0]], float)
    assert igl.predicates.find_self_intersections(tri, np.array([[0, 1, 2], [3, 4, 5]]), False)[0]
    tri[3:] += 10
    assert not igl.predicates.find_self_intersections(tri, np.array([[0, 1, 2], [3, 4, 5]]), False)[0]
    control = {"actual_source_admission_centroid_and_cone_path_matches_literal_reference": True,
        "complete_vertex_incidence_control": True, "native_intersection_positive_and_negative_controls": True,
        "reference_new_minimum_quality": tested["new_minimum_quality_approx"]}
    (args.output/"controls.json").write_text(json.dumps(control, indent=2)+"\n")
    if args.control_only:
        print(json.dumps(control), flush=True); return
    assert sha(args.parent/"manifest.json") == "e651636ad4a9aaa5640f69d12df304f52bb7f539bda1a65433a53fdd1bb6fb00"
    mesh = args.parent/"partition-verification/candidate.npz"
    assert sha(mesh) == "1bc2e8dddaf07c43ca36d35608f4fdb508f22e0694e922108a96466887f6182d"
    values = args.parent/"partition-whole-condition/private-exact-severe-values.json"
    assert sha(values) == "e339ca30c5ebf16f68dbaa5a14fe059df9a4de09f3069f0c1a1176f75b8a1878"
    conditions = {r["cell_id"]: Q(*map(int, r["reciprocal_frobenius_squared"])) for r in json.loads(values.read_text())}
    worst = min(conditions, key=conditions.__getitem__)
    with np.load(mesh, allow_pickle=False) as data:
        nodes, cells, surface = data["nodes"], data["tets"], data["boundary"]
    vertices = set(map(int, cells[worst])); stars = complete_vertex_stars(cells, vertices)
    base_boundaries = {v:contract.boundary(cells[ids]) for v, ids in stars.items()}
    queries = sorted({tuple(sorted(f)) for faces in base_boundaries.values() for f in faces})
    neighbors = complete_face_hits(cells, queries, helper.records)
    regions = []
    for seed in sorted(vertices):
        base_ids = stars[seed]; expanded = set(base_ids)
        for face in base_boundaries[seed]:
            expanded.update(neighbors[tuple(sorted(face))])
        regions.extend(((seed, 0, base_ids), (seed, 1, sorted(expanded))))
    all_faces = sorted({tuple(sorted(f)) for _, _, ids in regions for f in contract.boundary(cells[ids])})
    tags_path = Path('/Users/maxime/Developer/PorschePartsArtifacts/935-condition-directed-20261105-001/peel-proof/candidate-tags.npy')
    assert sha(tags_path) == "716a7c0f155551ec42db10527b4c53ea2ed95948d0cc027e7b786f3b9f4ce0b5"
    with np.load('/Users/maxime/Developer/PorschePartsArtifacts/935-condition-directed-20261105-001/peel-proof/candidate-surface.npz', allow_pickle=False) as data:
        assert np.array_equal(surface, data["triangles"])
    labels = boundary_tags(surface, np.load(tags_path, allow_pickle=False), all_faces, helper.records)
    profiles = []; admitted = []
    for number, (seed, level, ids) in enumerate(regions):
        verdict, proposed = local_region(nodes, cells[ids], labels, contract, geometry)
        profiles.append({"profile": number, "face_neighbor_ring": level, **verdict})
        if proposed is not None:
            proposed.update(profile=number, source_seed_vertex=seed, face_neighbor_ring=level, old_cell_ids=ids,
                contains_global_worst=worst in ids, severe_gain=sum(i in conditions for i in ids))
            admitted.append(proposed)
    selected = admitted[:1]
    output = args.output/"private-centroid-cavity-proposal.json"; output.write_text(json.dumps(selected, separators=(",", ":"))+"\n")
    result = {"source_sha256": sha(Path(__file__)), "mesh_sha256": sha(mesh), "controls": control,
        "complete_current_worst_boundary_vertex_stars": len(stars), "fixed_source_cavity_profiles": len(regions),
        "profiles": profiles, "admitted_profiles": len(admitted), "canonical_selected_profiles": len(selected),
        "global_worst_replaced_if_applied": bool(selected), "proposal_sha256": sha(output),
        "new_point_is_numerical_interior_mesh_only": True, "all_original_points_and_surface_faces_required_identical": True,
        "geometry_or_connectivity_modified": False, "separate_verification_and_complete_volume_required": True,
        "new_paid_compute_usd": 0, "physics_admitted": False, "manufacturing_qualified": False,
        "seconds": time.monotonic()-started}
    (args.output/"report.json").write_text(json.dumps(result, indent=2)+"\n")
    signal.alarm(0); print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
