"""Verify all indexed two-to-three cavities before exporting a candidate.

Reconstructs the expected combinatorial alternative and its supporting hull
from the old cells. Entire-source edge membership uses a streaming query,
independent of the constructor's global sorted-edge index.
"""
import argparse
from fractions import Fraction
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import signal
import time

import numpy as np


FACES = np.array([[1, 2, 3], [0, 3, 2], [0, 1, 3], [0, 2, 1]])
EDGES = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load(path, name, expected):
    assert sha(path) == expected
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def source_edge_membership(cells, queries):
    assert np.all(queries[:, 0] < queries[:, 1])
    query_keys = queries[:, 0].astype(np.uint64) * np.uint64(2**32) + queries[:, 1]
    unique = np.unique(query_keys)
    found = np.zeros(len(unique), dtype=bool)
    if not len(unique):
        return found
    for start in range(0, len(cells), 50000):
        block = cells[start:start + 50000]
        for left, right in EDGES:
            a, b = np.minimum(block[:, left], block[:, right]), np.maximum(block[:, left], block[:, right])
            keys = a.astype(np.uint64) * np.uint64(2**32) + b
            positions = np.searchsorted(unique, keys)
            inside = positions < len(unique)
            positions, keys = positions[inside], keys[inside]
            found[positions[unique[positions] == keys]] = True
    return found[np.searchsorted(unique, query_keys)]


def positive_quality(xyz, exact):
    low, high = exact.determinant_interval(xyz)
    det = np.einsum("ij,ij->i", xyz[:, 1] - xyz[:, 0], np.cross(xyz[:, 2] - xyz[:, 0], xyz[:, 3] - xyz[:, 0]))
    for i in np.flatnonzero(low <= 0):
        value = exact.exact_determinant(xyz[i])
        assert value > 0, "Nonpositive stored-coordinate cell"
        det[i] = float(value)
    assert np.all(det > 0) and np.all(high > 0)
    edge_sum = sum(np.sum((xyz[:, i] - xyz[:, j])**2, axis=1) for i, j in EDGES)
    volume = det / 6
    return 12 * (3 * volume)**(2/3) / edge_sum


def chain_equal(old, new):
    faces = np.concatenate((old[:, :, FACES].reshape(-1, 8, 3), new[:, :, FACES].reshape(-1, 12, 3)), axis=1)
    parity = ((faces[:, :, 0] > faces[:, :, 1]).astype(np.int8)
              + (faces[:, :, 0] > faces[:, :, 2]).astype(np.int8)
              + (faces[:, :, 1] > faces[:, :, 2]).astype(np.int8))
    signs = 1 - 2 * (parity % 2)
    signs[:, 8:] *= -1
    keys = np.sort(faces, axis=2)
    order = np.lexsort((keys[:, :, 2], keys[:, :, 1], keys[:, :, 0]), axis=1)
    ordered = np.take_along_axis(keys, order[:, :, None], axis=1)
    signs = np.take_along_axis(signs, order, axis=1)
    return (np.all(ordered[:, ::2] == ordered[:, 1::2], axis=(1, 2))
            & np.all(signs[:, ::2] + signs[:, 1::2] == 0, axis=1)
            & np.all(np.any(ordered[:, 2::2] != ordered[:, :-2:2], axis=2), axis=1))


def local_contract(nodes, old, new, new_edges, exact):
    # Three common face vertices occur twice, two distinct apices once.
    shared = np.sort(old[:, 0], axis=1)
    common = np.any(shared[:, :, None] == old[:, 1, None, :], axis=2)
    assert np.all(common.sum(axis=1) == 3)
    equator = shared[common].reshape(-1, 3)
    apex = old[~np.any(old[:, :, :, None] == equator[:, None, None, :], axis=3)].reshape(-1, 2)
    apex.sort(axis=1)
    assert np.all(apex[:, 0] != apex[:, 1]) and np.array_equal(apex, new_edges)
    expected = np.stack([np.column_stack((apex, equator[:, pair])) for pair in ([0, 1], [1, 2], [0, 2])], axis=1)
    actual = np.sort(new, axis=2)
    expected = np.sort(expected, axis=2)
    # The equator vertex omitted from each alternative cell is unique.
    actual_order = np.lexsort(tuple(actual[:, :, i] for i in reversed(range(4))), axis=1)
    expected_order = np.lexsort(tuple(expected[:, :, i] for i in reversed(range(4))), axis=1)
    assert np.array_equal(np.take_along_axis(actual, actual_order[:, :, None], axis=1),
                          np.take_along_axis(expected, expected_order[:, :, None], axis=1))
    assert chain_equal(old, new).all(), "Changed oriented cavity boundary"
    # Derive all six outward hull triangles from the old representation.
    hull = old[:, :, FACES].reshape(-1, 8, 3)
    exterior = ~np.all(np.sort(hull, axis=2) == equator[:, None, :], axis=2)
    assert np.all(exterior.sum(axis=1) == 6)
    hull = hull[exterior].reshape(-1, 6, 3)
    vertices = np.column_stack((apex, equator))
    missing = ~np.any(vertices[:, None, :, None] == hull[:, :, None, :], axis=3)
    assert np.all(missing.sum(axis=2) == 2)
    other = np.broadcast_to(vertices[:, None, :], missing.shape)[missing].reshape(-1, 6, 2)
    probes = np.concatenate((np.broadcast_to(hull[:, :, None, :], (len(old), 6, 2, 3)), other[:, :, :, None]), axis=3)
    xyz = nodes[probes.reshape(-1, 4)]
    low, high = exact.determinant_interval(xyz)
    assert not np.any(low >= 0), "Old cavity is not strictly convex"
    for i in np.flatnonzero(high >= 0):
        assert exact.exact_determinant(xyz[i]) < 0, "Old cavity support plane failed"
    old_q = positive_quality(nodes[old].reshape(-1, 4, 3), exact).reshape(-1, 2)
    new_q = positive_quality(nodes[new].reshape(-1, 4, 3), exact).reshape(-1, 3)
    assert np.all(new_q >= .01), "New cell misses the fixed diagnostic floor"
    assert np.all(new_q.min(axis=1) >= old_q.min(axis=1))
    return (old_q < .01).sum(axis=1)


def controls(exact):
    nodes = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.], [.25, .25, 2.**-20], [.25, .25, -1.]])
    old = np.array([[[0, 1, 2, 3], [0, 2, 1, 4]]])
    new = np.array([[[3, 0, 4, 1], [3, 1, 4, 2], [3, 2, 4, 0]]])
    edge = np.array([[3, 4]])
    assert local_contract(nodes, old, new, edge, exact).tolist() == [1]
    assert not source_edge_membership(old[0], edge).any()
    assert source_edge_membership(np.vstack((old[0], [[3, 4, 0, 1]])), edge).all()
    for corruption in (new[:, :, [0, 2, 1, 3]], new[:, [0, 0, 2]]):
        try:
            local_contract(nodes, old, corruption, edge, exact)
        except AssertionError:
            pass
        else:
            raise AssertionError("Corrupt reference was accepted")
    nonconvex = nodes.copy()
    nonconvex[3, 2] = -.1
    try:
        local_contract(nonconvex, old, new, edge, exact)
    except AssertionError:
        pass
    else:
        raise AssertionError("Nonconvex source was accepted")
    total = (Fraction(1) + Fraction(2.**-20)) / 6
    assert sum(exact.exact_determinant(nodes[cell]) / 6 for cell in new[0]) == total
    return {"literal_independent_cell_reference_passed": True,
        "streaming_source_edge_absence_and_conflict_controls": True,
        "reversed_and_duplicate_cell_controls_refused": True,
        "nonconvex_source_control_refused": True,
        "analytic_volume_exact": str(total)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repository", "mesh", "proposal", "proposal-report", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--control-only", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, exist_ok=False)
    signal.signal(signal.SIGALRM, signal.SIG_DFL)
    signal.alarm(600)
    started = time.monotonic()
    exact = load(args.repository / "docs/research/935-unoptimized-volume-20261105/source/inspect_interval_volume.py",
        "retained_two_three_validation_predicates", "b0810ac21b35654556dce18ef022f6d4ca8f30a847223c5d566188eab82f4e71")
    tested = controls(exact)
    (args.output / "controls.json").write_text(json.dumps(tested, indent=2) + "\n")
    if args.control_only:
        print(json.dumps(tested), flush=True)
        return
    report = json.loads(args.proposal_report.read_text())
    assert report["source_sha256"] == "805d7ede2dad5bcdb6df6435caf90f129efa5e4f9865963fd66e3b5e30969e97"
    assert sha(args.mesh) == report["mesh_sha256"] == "233f7bd83072772fa0b92d0287f20cec3cf44c4988546be42addf5579630299e"
    assert sha(args.proposal) == report["proposal_sha256"]
    with np.load(args.mesh, allow_pickle=False) as data:
        nodes, cells, boundary = data["nodes"], data["tets"], data["boundary"]
    with np.load(args.proposal, allow_pickle=False) as data:
        old_ids, proposed, new_edges, gains = data["old_cell_ids"], data["new_cells"], data["new_edges"], data["repair_gains"]
    assert old_ids.shape == (report["selected_disjoint_cavities"], 2)
    assert proposed.shape == (len(old_ids), 3, 4) and new_edges.shape == (len(old_ids), 2)
    assert all(value.dtype.kind in "ui" for value in (old_ids, proposed, new_edges))
    assert np.all(old_ids >= 0) and np.all(proposed >= 0) and np.all(proposed < len(nodes))
    assert len(np.unique(old_ids)) == old_ids.size and np.all(old_ids < len(cells))
    assert len(np.unique(new_edges, axis=0)) == len(new_edges)
    assert not source_edge_membership(cells, new_edges).any(), "Proposed internal edge already exists in source"
    checked_gains = []
    for start in range(0, len(old_ids), 1000):
        checked_gains.extend(local_contract(nodes, cells[old_ids[start:start + 1000]], proposed[start:start + 1000],
            new_edges[start:start + 1000], exact).tolist())
    assert np.array_equal(np.asarray(checked_gains), gains) and np.all(gains > 0)
    assert int(gains.sum()) == report["predicted_removed_bad_cells"]
    removed = np.zeros(len(cells), dtype=bool)
    removed[old_ids] = True
    replacement = np.vstack((cells[~removed], proposed.reshape(-1, 4)))
    assert len(replacement) == report["predicted_cell_count"]
    assert shutil.disk_usage(args.output).free > 4 * 1024**3 + 2 * args.mesh.stat().st_size
    candidate = args.output / "candidate.npz"
    np.savez_compressed(candidate, nodes=nodes, tets=replacement, boundary=boundary)
    with np.load(candidate, allow_pickle=False) as data:
        assert np.array_equal(data["nodes"].view(np.uint64), nodes.view(np.uint64))
        assert np.array_equal(data["boundary"], boundary) and np.array_equal(data["tets"], replacement)
    result = {"source_sha256": sha(Path(__file__)), "input_mesh_sha256": sha(args.mesh),
        "proposal_sha256": sha(args.proposal), "candidate_sha256": sha(candidate),
        "terminal": "complete_local_cavity_contract_passed_candidate_exported_global_validation_pending",
        "controls": tested, "cavities_checked": len(old_ids), "old_cells_checked": old_ids.size,
        "new_cells_checked": int(proposed.shape[0] * 3), "removed_bad_cells": int(gains.sum()),
        "all_source_cell_cavities_disjoint": True, "all_new_edges_distinct_and_absent_from_entire_source": True,
        "all_expected_new_cell_sets_exact": True, "all_old_hull_supporting_planes_strict": True,
        "all_oriented_local_boundary_chains_identical": True, "all_new_cell_mean_ratios_at_least_001": True,
        "all_coordinate_bits_and_boundary_faces_preserved": True,
        "old_mesh_global_intersection_status_inherited_not_newly_certified": True,
        "whole_volume_inspection_required": True, "native_solver_readback_not_repeated_for_new_connectivity": True,
        "physics_admitted": False, "manufacturing_qualified": False, "new_paid_compute_usd": 0,
        "seconds": time.monotonic() - started}
    (args.output / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    signal.alarm(0)
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
