"""Audit the optimistic coverage of initial closed degree-three edge cavities.

No coordinate or connectivity changes. Each candidate must have exactly three
incident source cells and a three-vertex cyclic link. Geometry, improvement and
packing checks are still required before any 3-to-2 replacement can be admitted.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import time

import numpy as np


PAIRS = np.array([[0, 1], [0, 2], [0, 3], [1, 2], [1, 3], [2, 3]])
EMPTY = np.iinfo(np.uint32).max


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def edges(cells):
    endpoints = cells[:, PAIRS]
    lower = endpoints.min(axis=2).astype(np.uint64)
    upper = endpoints.max(axis=2).astype(np.uint64)
    return (lower << np.uint64(32)) | upper


def incidence(cells, selected):
    """Count every selected edge globally and retain its first three cell IDs."""
    counts = np.zeros(len(selected), dtype=np.uint32)
    first = np.full((len(selected), 3), EMPTY, dtype=np.uint32)
    for start in range(0, len(cells), 50000):
        block = cells[start:start + 50000]
        keys = edges(block).ravel()
        position = np.searchsorted(selected, keys)
        matched = position < len(selected)
        matched[matched] = selected[position[matched]] == keys[matched]
        hits = position[matched]
        if not len(hits):
            continue
        ids = np.repeat(np.arange(start, start + len(block), dtype=np.uint32), 6)[matched]
        order = np.argsort(hits, kind="stable")
        hits, ids = hits[order], ids[order]
        initial = np.r_[True, hits[1:] != hits[:-1]]
        ranks = np.arange(len(hits)) - np.maximum.accumulate(np.where(initial, np.arange(len(hits)), 0))
        slots = counts[hits].astype(np.int64) + ranks
        retained = slots < 3
        first[hits[retained], slots[retained]] = ids[retained]
        np.add.at(counts, hits, 1)
    return counts, first


def controls():
    fixture = np.array([[3, 4, 0, 1], [3, 4, 1, 2], [3, 4, 2, 0]], dtype=np.uint32)
    oracle = {}
    for cell_id, row in enumerate(fixture):
        for left, right in PAIRS:
            a, b = sorted([int(row[left]), int(row[right])])
            oracle.setdefault((a << 32) | b, []).append(cell_id)
    absent = (np.uint64(8) << np.uint64(32)) | np.uint64(9)
    selected = np.sort(np.r_[np.array(list(oracle), dtype=np.uint64), absent])
    counts, first = incidence(fixture, selected)
    for index, key in enumerate(selected):
        expected = oracle.get(int(key), [])
        assert counts[index] == len(expected)
        assert first[index, :min(3, len(expected))].tolist() == expected[:3]
        assert np.all(first[index, min(3, len(expected)):] == EMPTY)
    assert np.array_equal(edges(fixture), edges(fixture[:, ::-1])) is False
    assert np.array_equal(np.sort(edges(fixture), axis=1), np.sort(edges(fixture[:, ::-1]), axis=1))
    return {"scalar_all_edge_incidence_oracle": True, "absent_edge_detected": True,
            "connectivity_permutation_invariant_edge_sets": True, "known_three_cell_link": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("mesh", "mesh-report", "surface", "inspector", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, exist_ok=False)
    signal.signal(signal.SIGALRM, signal.SIG_DFL)
    signal.alarm(600)
    started = time.monotonic()
    control = controls()
    assert sha(args.mesh) == "b06d28ec39019fa8f91c2e8cd0397c2eb9cd87bf84df7006c8526025aef03450"
    assert sha(args.surface) == "5b04e72b5f7b48f340a39c14009292c52c1bf1ac422ad64cd3250c17ddf51db4"
    assert sha(args.mesh_report) == "105cbe8f04c702923672f133e86c57835da1c261df56f6df13ed830eca8d2327"
    assert sha(args.inspector) == "b0810ac21b35654556dce18ef022f6d4ca8f30a847223c5d566188eab82f4e71"
    upstream = json.loads(args.mesh_report.read_text())
    assert upstream["all_cells_positive_for_stored_binary_coordinates"] and upstream["all_internal_faces_oppositely_oriented"]
    assert upstream["actual_complete_boundary_and_orientation_exact"] and upstream["mesh_sha256"] == sha(args.mesh)
    spec = importlib.util.spec_from_file_location("frozen_cavity_signs", args.inspector)
    exact = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exact)
    exact.controls()
    with np.load(args.mesh, allow_pickle=False) as data:
        nodes, tets = data["nodes"], data["tets"]
    assert len(nodes) < 2**32 and len(tets) < int(EMPTY) and 0 <= tets.min() <= tets.max() < len(nodes)
    tets = tets.astype(np.uint32, copy=False)
    with np.load(args.surface, allow_pickle=False) as data:
        boundary_vertices = data["vertices"]
    assert np.array_equal(nodes[:len(boundary_vertices)], boundary_vertices)
    bad = np.zeros(len(tets), dtype=bool)
    fallback = 0
    for start in range(0, len(tets), 50000):
        xyz = nodes[tets[start:start + 50000]]
        low, high = exact.determinant_interval(xyz)
        determinant = np.einsum("ij,ij->i", xyz[:, 1] - xyz[:, 0], np.cross(xyz[:, 2] - xyz[:, 0], xyz[:, 3] - xyz[:, 0]))
        for i in np.flatnonzero(low <= 0):
            value = exact.exact_determinant(xyz[i])
            assert value > 0
            determinant[i] = float(value)
            fallback += 1
        assert np.all(determinant > 0)
        volume = determinant / 6
        edge_sum = sum(np.sum((xyz[:, i] - xyz[:, j]) ** 2, axis=1) for i, j in PAIRS)
        quality = 12 * (3 * volume) ** (2 / 3) / edge_sum
        bad[start:start + len(xyz)] = quality < .01
    assert bad.sum() == upstream["mean_ratio_below"]["0.01"]
    selected = np.unique(edges(tets[bad]).ravel())
    save = {"source_sha256": sha(Path(__file__)), "mesh_sha256": sha(args.mesh),
            "upstream_verdict": "Positive consistent hypothetical raw mesh; shape quality and physical/process gates fail; topology coverage audit only",
            "initial_source_cavities_only": True, "target_bin": .01, "target_reduction_min_fraction": .5,
            "selected_edges": len(selected), "new_paid_compute_usd": 0, "coordinates_modified": False}
    (args.output / "plan.json").write_text(json.dumps(save, indent=2) + "\n")
    print(json.dumps({"stage": "full_edge_incidence", "selected_edges": len(selected)}), flush=True)
    counts, first = incidence(tets, selected)
    assert counts.min() >= 1 and counts.max() <= len(tets)
    degree_three = np.flatnonzero(counts == 3)
    cells = first[degree_three]
    assert np.all(cells != EMPTY) and np.all(np.diff(np.sort(cells, axis=1), axis=1) > 0)
    keys = selected[degree_three]
    endpoints = np.column_stack((keys >> np.uint64(32), keys & np.uint64(0xffffffff))).astype(np.uint32)
    vertices = tets[cells]
    assert np.all((vertices == endpoints[:, None, 0, None]).sum(axis=2) == 1)
    assert np.all((vertices == endpoints[:, None, 1, None]).sum(axis=2) == 1)
    keep = (vertices != endpoints[:, None, 0, None]) & (vertices != endpoints[:, None, 1, None])
    outer = np.sort(np.where(keep, vertices, EMPTY).reshape(-1, 12), axis=1)[:, :6]
    cyclic = ((outer[:, 0] == outer[:, 1]) & (outer[:, 2] == outer[:, 3]) & (outer[:, 4] == outer[:, 5])
              & (outer[:, 0] < outer[:, 2]) & (outer[:, 2] < outer[:, 4]))
    cavity_cells, cavity_keys = cells[cyclic], keys[cyclic]
    covered = np.unique(cavity_cells.ravel())
    covered_bad = covered[bad[covered]]
    required = (int(bad.sum()) + 1) // 2
    cache = args.output / "private-initial-cavities.npz"
    np.savez_compressed(cache, edge_keys=cavity_keys, cell_ids=cavity_cells,
                        outer_vertices=outer[cyclic][:, [0, 2, 4]], bad_cell_ids=np.flatnonzero(bad).astype(np.uint32))
    values, frequencies = np.unique(counts, return_counts=True)
    result = {**save, "surface_sha256": sha(args.surface), "inspector_sha256": sha(args.inspector),
              "tetrahedra": len(tets), "bad_cells": int(bad.sum()), "exact_positive_fallbacks": fallback,
              "selected_edge_valence_histogram": {str(int(k)): int(v) for k, v in zip(values, frequencies)},
              "degree_three_edges": len(degree_three), "closed_three_vertex_link_cavities": len(cavity_keys),
              "distinct_covered_cells": len(covered), "optimistically_repairable_bad_cells": len(covered_bad),
              "required_bad_cell_repairs": required, "optimistic_initial_pass_target_reachable": len(covered_bad) >= required,
              "geometry_convexity_and_quality_not_yet_checked": True, "overlap_packing_not_yet_checked": True,
              "dynamic_sequences_or_other_valences_not_excluded": True, "controls": control,
              "private_cavity_cache_sha256": sha(cache), "physics_admitted": False,
              "manufacturing_qualified": False, "seconds": time.monotonic() - started}
    (args.output / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)
    signal.alarm(0)


if __name__ == "__main__":
    main()
