"""Audit fixed-face limits and propose one bounded two-to-three topology pass.

Only existing coordinates and the exact current boundary are admissible. This
constructor exports indexed proposals, never an admitted mesh or field solve.
"""
import argparse
from fractions import Fraction
import gc
import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import time

import numpy as np


PATTERN = np.array([[0, 1, 2, 3], [0, 1, 3, 4], [0, 1, 4, 2]])


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def module(path, name, expected):
    assert sha(path) == expected
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def edge_membership(values, keys):
    positions = np.searchsorted(values, keys)
    inside = positions < len(values)
    result = np.zeros(len(keys), dtype=bool)
    result[inside] = values[positions[inside]] == keys[inside]
    return result


def controls(geom, exact, indexer):
    epsilon = 2.**-20
    nodes = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.],
                      [.25, .25, epsilon], [.25, .25, -1.]])
    old = np.array([[0, 1, 2, 3], [0, 2, 1, 4]])
    ids = np.array([[3, 4, 0, 1, 2]])
    new = ids[:, PATTERN].copy()
    q_new, signs, _ = geom.quality(nodes[new].reshape(-1, 4, 3), exact)
    flat = new.reshape(-1, 4)
    flat[signs < 0] = flat[signs < 0][:, [0, 2, 1, 3]]
    q_old, old_signs, _ = geom.quality(nodes[old], exact)
    assert np.all(old_signs > 0) and q_old.min() < .01 and q_new.min() > .1
    assert geom.convex(nodes[ids], exact)[0].all()
    assert geom.boundary_chain_equal(new, old[None]).all()
    total = (Fraction(1) + Fraction(epsilon)) / 6
    assert sum(exact.exact_determinant(nodes[cell]) / 6 for cell in old) == total
    volumes = [exact.exact_determinant(nodes[cell]) / 6 for cell in new[0]]
    assert volumes == [total / 4, total / 2, total / 4]
    concave = nodes[ids].copy()
    concave[:, 0] = concave[:, 1:].mean(axis=1)
    assert not geom.convex(concave, exact)[0].any()
    forged = new.copy()
    forged[0, 0, [1, 2]] = forged[0, 0, [2, 1]]
    assert not geom.boundary_chain_equal(forged, old[None]).any()
    selected, conflict, duplicate = geom.pack(np.array([[0, 1], [1, 2]]),
        np.array([[3, 4], [4, 5]]), np.array([1, 2]), np.array([1, 2]), 3)
    assert selected.tolist() == [1] and conflict == 1
    selected, conflict, duplicate = geom.pack(np.array([[0, 1], [2, 3]]),
        np.array([[3, 4], [3, 4]]), np.array([1, 2]), np.array([1, 2]), 4)
    assert selected.tolist() == [1] and duplicate == 1
    edge_values = indexer.full_index(old)[0]
    assert edge_membership(edge_values, np.array([1, 3 * 2**32 + 4], dtype=np.uint64)).tolist() == [True, False]
    return {"explicit_dyadic_fixture": nodes.tolist(), "old_cells": old.tolist(),
        "independently_known_new_cells": new[0].tolist(),
        "analytic_total_volume": str(total), "exact_new_volume_fractions": ["1/4", "1/2", "1/4"],
        "minimum_old_mean_ratio": float(q_old.min()), "minimum_new_mean_ratio": float(q_new.min()),
        "exact_positive_partition_and_boundary_chain": True,
        "concave_and_reversed_cell_refused": True, "cell_conflict_and_duplicate_edge_refused": True,
        "global_existing_edge_present_and_absent_controls_passed": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repository", "native-parent", "winding-parent", "mesh", "mesh-report", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--control-only", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, exist_ok=False)
    signal.signal(signal.SIGALRM, signal.SIG_DFL)
    signal.alarm(600)
    started = time.monotonic()
    root = args.repository / "docs/research"
    geom = module(root / "935-local-cavity-20261105/source/assess_initial_cavities.py", "retained_two_three_geometry",
        "ee60f26e2449fc2da97e34b0fa3f67c5472e0902b8a4166210e2089624887aa6")
    exact = module(root / "935-unoptimized-volume-20261105/source/inspect_interval_volume.py", "retained_two_three_predicates",
        "b0810ac21b35654556dce18ef022f6d4ca8f30a847223c5d566188eab82f4e71")
    indexer = module(root / "935-local-cavity-20261105/source/verify_global_incidence.py", "retained_two_three_edges",
        "2d3d3b44ea5e055b3600231d935bed280197b33cc4400ee0553d826cc239d4f8")
    reader = module(root / "935-native-solver-admission-20261105/source/inspect_foam_readback.py", "retained_two_three_reader",
        "fbcd4fc8dddb319aeff88131c678e26ccba6ae97decb988fcc185872c67644ae")
    tested = controls(geom, exact, indexer)
    (args.output / "controls.json").write_text(json.dumps(tested, indent=2) + "\n")
    if args.control_only:
        print(json.dumps(tested), flush=True)
        return
    assert sha(args.mesh) == "233f7bd83072772fa0b92d0287f20cec3cf44c4988546be42addf5579630299e"
    assert sha(args.mesh_report) == "2534890f0c46caaa8394320fa03a8d60057c842d97238dfa57b4cb816c20e596"
    assert sha(args.native_parent / "manifest.json") == "91fbc0ecc6dfdeb2b95949676698f0ea9a1a8605d783efdfa61e2fe3722ed64d"
    assert sha(args.winding_parent / "manifest.json") == "c58ce27aa0aef9479c3835603034333037dd14f8a75d6aaba8f22f161a625a6a"
    parent = json.loads((args.native_parent / "manifest.json").read_text())
    expected = {row["path"]: row["sha256"] for row in parent["files"]}
    winding_manifest = json.loads((args.winding_parent / "manifest.json").read_text())
    winding_hash = next(row["sha256"] for row in winding_manifest["files"] if row["path"] == "native-winding/report.json")
    assert sha(args.winding_parent / "native-winding/report.json") == winding_hash
    winding = json.loads((args.winding_parent / "native-winding/report.json").read_text())
    assert winding["complete_combinatorial_winding_passed"] and winding["native_cell_order_matches_source"]
    report = json.loads(args.mesh_report.read_text())
    assert report["all_cells_positive_for_stored_binary_coordinates"] and report["actual_complete_boundary_and_orientation_exact"]
    plan = {"source_sha256": sha(Path(__file__)), "mesh_sha256": sha(args.mesh),
        "mesh_report_sha256": sha(args.mesh_report), "maximum_topology_passes": 1,
        "coordinate_or_boundary_motion_allowed": False, "field_solve_permitted": False,
        "upstream_verdict": "Exact current geometry, native winding and positivity; absolute conditioning fails; one indexed topology proposal only",
        "required_new_mean_ratio_minimum": .01, "every_proposed_cell_must_meet_floor": True,
        "new_internal_edge_must_be_absent_from_entire_source_mesh": True,
        "cavity_convexity_oriented_chain_and_disjoint_source_cells_required": True,
        "output_mesh_not_exported_by_this_script": True, "new_paid_compute_usd": 0}
    (args.output / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    with np.load(args.mesh, allow_pickle=False) as data:
        nodes, cells, boundary = data["nodes"], data["tets"].astype(np.uint32), data["boundary"]
    assert (len(nodes), len(cells), len(boundary)) == (4181299, 12981388, 8218458)
    quality = np.empty(len(cells))
    fallback = 0
    for start in range(0, len(cells), 50000):
        q, signs, count = geom.quality(nodes[cells[start:start + 50000]], exact)
        assert np.all(signs > 0)
        quality[start:start + len(q)] = q
        fallback += count
    bins = {str(x): int((quality < x).sum()) for x in (.0001, .001, .01, .05, .1)}
    assert bins == report["mean_ratio_below"]
    bad = quality < .01
    interior = np.ones(len(nodes), dtype=bool)
    interior[boundary] = False
    partition = np.bincount(interior[cells[bad]].sum(axis=1), minlength=5).tolist()
    folder = args.native_parent / "cloud-import-001/recovered/head/constant/polyMesh"
    arrays = {}
    for name, width, face in (("owner", 1, False), ("neighbour", 1, False), ("faces", 4, True)):
        path = folder / name
        assert sha(path) == expected[str(path.relative_to(args.native_parent))]
        arrays[name] = reader.values(path, width, np.int64, face=face)
    owners, neighbours, faces = arrays["owner"], arrays["neighbour"], arrays["faces"]
    assert len(owners) == len(faces) == 30072005 and len(neighbours) == 21853547
    n = len(neighbours)
    # Same complete native boundary as the source. This is an analytic binary64
    # ceiling diagnostic, not an interval certificate or physical allowable.
    forcing = []
    for start in range(n, len(faces), 50000):
        xyz = nodes[faces[start:start + 50000]]
        a, b, c = xyz[:, 1] - xyz[:, 0], xyz[:, 2] - xyz[:, 0], xyz[:, 2] - xyz[:, 1]
        q_face = 2 * np.sqrt(3.) * np.linalg.norm(np.cross(a, b), axis=1) / np.sum(a*a + b*b + c*c, axis=1)
        selected = np.flatnonzero(q_face**(2/3) < .01)
        forcing.extend((start + selected).tolist())
    forcing = np.asarray(forcing, dtype=np.int64)
    forced_cells = np.unique(owners[forcing])
    assert bad[forced_cells].all()
    face_ids = np.flatnonzero(bad[owners[:n]] | bad[neighbours])
    rows = np.column_stack((owners[face_ids], neighbours[face_ids])).astype(np.uint32)
    equator = np.sort(faces[face_ids], axis=1).astype(np.uint32)
    boundary_audit = {"faces_checked": len(faces) - n, "forcing_faces_below_incident_tet_ceiling_001": len(forcing),
        "distinct_current_owners_of_forcing_faces": len(forced_cells),
        "all_forcing_face_owners_in_current_bad_bin": True,
        "unavoidable_cell_lower_bound_if_these_faces_are_fixed": (len(forcing) + 3) // 4,
        "bad_cells_by_number_of_interior_vertices_0_to_4": partition,
        "analytic_ceiling": "q_tet <= q_face^(2/3); binary64 diagnostic, not interval-certified",
        "physical_or_solver_allowable": False}
    np.savez_compressed(args.output / "private-forcing-faces.npz", native_face_ids=forcing, source_cell_ids=forced_cells)
    del arrays, owners, neighbours, faces, boundary, interior
    gc.collect()
    valid_rows, valid_new, valid_edges, valid_faces, gains = [], [], [], [], []
    convex_count = quality_count = chain_count = 0
    for start in range(0, len(rows), 3000):
        old = cells[rows[start:start + 3000]]
        shared = equator[start:start + 3000]
        keep = ~np.any(old[:, :, :, None] == shared[:, None, None, :], axis=3)
        assert np.all(keep.sum(axis=2) == 1)
        apices = np.sort(old[keep].reshape(-1, 2), axis=1)
        assert np.all(apices[:, 0] != apices[:, 1])
        ids = np.column_stack((apices, shared))
        convex, _ = geom.convex(nodes[ids], exact)
        proposed = ids[:, PATTERN].copy()
        q, signs, _ = geom.quality(nodes[proposed].reshape(-1, 4, 3), exact)
        flat = proposed.reshape(-1, 4)
        flat[signs < 0] = flat[signs < 0][:, [0, 2, 1, 3]]
        acceptable = np.all(q.reshape(-1, 3) >= .01, axis=1) & np.all(signs.reshape(-1, 3) != 0, axis=1)
        chain = geom.boundary_chain_equal(proposed, old)
        chosen = np.flatnonzero(convex & acceptable & chain)
        convex_count += int(convex.sum())
        quality_count += int((convex & acceptable).sum())
        chain_count += len(chosen)
        valid_rows.append(rows[start + chosen])
        valid_new.append(proposed[chosen])
        valid_edges.append(apices[chosen])
        valid_faces.append(face_ids[start + chosen])
        gains.append(bad[rows[start + chosen]].sum(axis=1))
    valid_rows, valid_new, valid_edges, valid_faces, gains = map(np.concatenate,
        (valid_rows, valid_new, valid_edges, valid_faces, gains))
    keys = valid_edges[:, 0].astype(np.uint64) * np.uint64(2**32) + valid_edges[:, 1].astype(np.uint64)
    edge_present = np.zeros(len(keys), dtype=bool)
    if len(keys):
        edge_index = indexer.full_index(cells)
        values = edge_index[0]
        edge_present = edge_membership(values, keys)
        del edge_index, values
        gc.collect()
    absent = ~edge_present
    packed, conflicts, duplicate_edges = geom.pack(valid_rows[absent], valid_edges[absent], gains[absent],
        valid_faces[absent], len(cells))
    selected = np.flatnonzero(absent)[packed]
    proposal = args.output / "proposal.npz"
    np.savez_compressed(proposal, old_cell_ids=valid_rows[selected], new_cells=valid_new[selected],
        new_edges=valid_edges[selected], native_face_ids=valid_faces[selected], repair_gains=gains[selected])
    result = {**plan, "terminal": "indexed_two_three_proposals_exported_no_mesh_admitted",
        "controls": tested, "current_bad_cells": int(bad.sum()), "current_mean_ratio_below": bins,
        "exact_source_cell_sign_fallbacks": fallback, "boundary_audit": boundary_audit,
        "internal_faces_incident_to_bad_cells": len(face_ids), "strictly_convex_candidates": convex_count,
        "all_new_cells_pass_floor_in_convex_candidates": quality_count,
        "oriented_chain_candidates": chain_count, "existing_new_edges_refused": int(edge_present.sum()),
        "packing_cell_conflicts": conflicts, "packing_duplicate_new_edges": duplicate_edges,
        "selected_disjoint_cavities": len(selected), "predicted_removed_bad_cells": int(gains[selected].sum()),
        "predicted_remaining_bad_cells": int(bad.sum() - gains[selected].sum()),
        "predicted_cell_count": len(cells) + len(selected), "proposal_sha256": sha(proposal),
        "input_mesh_rehashed_unchanged": sha(args.mesh) == plan["mesh_sha256"],
        "independent_local_domain_and_whole_volume_validation_required": True,
        "physics_admitted": False, "manufacturing_qualified": False, "seconds": time.monotonic() - started}
    (args.output / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    signal.alarm(0)
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
