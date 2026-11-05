"""Propose one four-to-four pass targeting the unchanged ultra-low subset."""
import argparse
import gc
import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import time

import numpy as np


PATTERNS = [np.array([[2, 3, 4, 0], [2, 4, 3, 1], [2, 4, 5, 0], [2, 5, 4, 1]]),
            np.array([[3, 4, 5, 0], [3, 5, 4, 1], [3, 5, 2, 0], [3, 2, 5, 1]])]


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def module(path, name, expected):
    assert sha(path) == expected
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def cycle_vertices(old, center, contract):
    ring, edges = contract.ring_data(old, center)
    first = ring[:, 0]
    maximum = np.iinfo(np.uint32).max
    adjacent = np.where(edges[:, :, 0] == first[:, None], edges[:, :, 1],
        np.where(edges[:, :, 1] == first[:, None], edges[:, :, 0], maximum))
    adjacent.sort(axis=1)
    assert np.all(adjacent[:, 1] < maximum) and np.all(adjacent[:, 2] == maximum)
    second, fourth = adjacent[:, 0], adjacent[:, 1]
    remaining = ~np.any(ring[:, :, None] == np.column_stack((first, second, fourth))[:, None, :], axis=2)
    assert np.all(remaining.sum(axis=1) == 1)
    third = ring[remaining]
    cycle = np.column_stack((first, second, third, fourth))
    expected = np.sort(cycle[:, [[0, 1], [1, 2], [2, 3], [3, 0]]], axis=2)
    key = lambda x: x[:, :, 0].astype(np.uint64) * np.uint64(2**32) + x[:, :, 1]
    assert np.array_equal(np.sort(key(expected), axis=1), np.sort(key(edges), axis=1))
    return np.column_stack((center, cycle))


def alternatives(nodes, old, center, geom, exact, contract):
    ids = cycle_vertices(old, center, contract)
    result = []
    for pattern, diagonal_indices in zip(PATTERNS, ((2, 4), (3, 5))):
        proposed = ids[:, pattern].copy()
        q, signs, _ = geom.quality(nodes[proposed].reshape(-1, 4, 3), exact)
        flat = proposed.reshape(-1, 4)
        flat[signs < 0] = flat[signs < 0][:, [0, 2, 1, 3]]
        result.append((proposed, np.sort(ids[:, diagonal_indices], axis=1), q.reshape(-1, 4), signs.reshape(-1, 4)))
    return result


def controls(reference, geom, exact, contract, verifier):
    assert sha(reference) == "90ae971f7ff2687c60e3bb9460d5241edeedae3fbaf6f07ad69be08604c36690"
    with np.load(reference, allow_pickle=False) as data:
        nodes, old, known = data["nodes"], data["old_cells"][None], data["reference_cells"][None]
    center = np.array([[0, 1]], dtype=np.uint32)
    actual, diagonal, q, signs = alternatives(nodes, old, center, geom, exact, contract)[0]
    assert np.array_equal(np.sort(actual, axis=2), np.sort(known, axis=2))
    gain, old_q, new_q = contract.validate(nodes, old, center, diagonal, actual, exact, verifier.positive_quality)
    assert gain.tolist() == [1] and new_q.min() > .1 and old_q.min() < .0001
    assert not verifier.source_edge_membership(old[0], diagonal).any()
    for corruption in (actual[:, :, [0, 2, 1, 3]], actual[:, [0, 0, 2, 3]]):
        try:
            contract.validate(nodes, old, center, diagonal, corruption, exact, verifier.positive_quality)
        except AssertionError:
            pass
        else:
            raise AssertionError("Forged reference accepted")
    changed = nodes.copy()
    changed[0] = nodes[1:].mean(axis=0)
    assert not contract.strict_support(changed, old, center, exact)[0].any()
    assert verifier.source_edge_membership(np.vstack((old[0], actual[0, :1])), diagonal).all()
    return {"actual_operator_matches_frozen_literal_reference": True,
        "reference_sha256": sha(reference), "reference_minimum_before": float(old_q.min()),
        "reference_minimum_after": float(new_q.min()), "critical_gain": int(gain.sum()),
        "every_bin_nonregression_control": True, "reversed_duplicate_nonconvex_and_existing_edge_refused": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repository", "mesh", "mesh-report", "reference", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--control-only", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, exist_ok=False)
    signal.signal(signal.SIGALRM, signal.SIG_DFL)
    signal.alarm(600)
    started = time.monotonic()
    source = args.repository / "docs/research"
    geom = module(source / "935-local-cavity-20261105/source/assess_initial_cavities.py", "retained_four_geometry",
        "ee60f26e2449fc2da97e34b0fa3f67c5472e0902b8a4166210e2089624887aa6")
    exact = module(source / "935-unoptimized-volume-20261105/source/inspect_interval_volume.py", "retained_four_exact",
        "b0810ac21b35654556dce18ef022f6d4ca8f30a847223c5d566188eab82f4e71")
    indexer = module(source / "935-local-cavity-20261105/source/verify_global_incidence.py", "retained_four_index",
        "2d3d3b44ea5e055b3600231d935bed280197b33cc4400ee0553d826cc239d4f8")
    verifier = module(source / "935-residual-cavities-20261105/source/verify_two_three.py", "retained_four_quality_and_streaming_edges",
        "a785594fcb77460057824a6fe31c192b2131c7907e535b9e458428bf0b578acb")
    contract = module(Path(__file__).with_name("four_four_contract.py"), "four_four_source_contract",
        "a5379daacb7a099810acf678110b74d4e6d9c5f34b01ac38fff1472a4ab0228c")
    tested = controls(args.reference, geom, exact, contract, verifier)
    (args.output / "controls.json").write_text(json.dumps(tested, indent=2) + "\n")
    if args.control_only:
        print(json.dumps(tested), flush=True)
        return
    assert sha(args.mesh) == "233f7bd83072772fa0b92d0287f20cec3cf44c4988546be42addf5579630299e"
    assert sha(args.mesh_report) == "2534890f0c46caaa8394320fa03a8d60057c842d97238dfa57b4cb816c20e596"
    report = json.loads(args.mesh_report.read_text())
    assert report["all_cells_positive_for_stored_binary_coordinates"] and report["actual_complete_boundary_and_orientation_exact"]
    plan = {"source_sha256": sha(Path(__file__)), "contract_sha256": sha(Path(__file__).with_name("four_four_contract.py")),
        "mesh_sha256": sha(args.mesh), "mesh_report_sha256": sha(args.mesh_report),
        "maximum_passes": 1, "target_critical_bin": .0001, "all_new_cells_must_meet": .01,
        "all_five_reported_bin_counts_must_not_increase": True, "point_or_boundary_motion_permitted": False,
        "new_edge_must_be_globally_absent": True, "strict_convexity_and_chain_identity_required": True,
        "alternative_choice": "First admissible opposite-ring diagonal in canonical order; no numerical tie selection",
        "upstream_verdict": "Source geometry/positivity proven; current extreme conditioning fails; one critical-cell topology proposal only",
        "field_solve_permitted": False, "new_paid_compute_usd": 0}
    (args.output / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    with np.load(args.mesh, allow_pickle=False) as data:
        nodes, cells = data["nodes"], data["tets"].astype(np.uint32)
    quality = np.empty(len(cells))
    fallback = 0
    for start in range(0, len(cells), 50000):
        q, signs, count = geom.quality(nodes[cells[start:start + 50000]], exact)
        assert np.all(signs > 0)
        quality[start:start + len(q)] = q
        fallback += count
    bins = {str(x): int((quality < x).sum()) for x in contract.BINS}
    assert bins == report["mean_ratio_below"]
    critical = quality < .0001
    edge_index = indexer.full_index(cells)
    values, starts, counts, order = edge_index
    critical_cells = cells[critical]
    keys = np.column_stack([np.minimum(critical_cells[:, a], critical_cells[:, b]).astype(np.uint64) * np.uint64(2**32)
        + np.maximum(critical_cells[:, a], critical_cells[:, b]) for a, b in geom.PAIRS])
    keys = np.unique(keys)
    critical_edge_count = len(keys)
    positions = np.searchsorted(values, keys)
    assert np.array_equal(values[positions], keys)
    histogram = {str(k): int(v) for k, v in zip(*np.unique(counts[positions], return_counts=True))}
    degree_four = positions[counts[positions] == 4]
    rows = (order[starts[degree_four, None] + np.arange(4)] // 6).astype(np.uint32)
    center_keys = values[degree_four]
    center = np.column_stack((center_keys // np.uint64(2**32), center_keys % np.uint64(2**32))).astype(np.uint32)
    old = cells[rows]
    keep = ~np.any(old[:, :, :, None] == center[:, None, None, :], axis=3)
    outer = np.sort(np.where(keep, old, np.iinfo(np.uint32).max).reshape(-1, 16), axis=1)[:, :8]
    closed = np.all(outer[:, ::2] == outer[:, 1::2], axis=1) & np.all(np.diff(outer[:, ::2].astype(np.int64), axis=1) > 0, axis=1)
    rows, center = rows[closed], center[closed]
    chosen_rows, chosen_centers, chosen_new, chosen_edges, chosen_gains = [], [], [], [], []
    convex_count = exact_support = coplanar = all_quality = absent_quality = 0
    for start in range(0, len(rows), 1500):
        block_rows, block_center = rows[start:start + 1500], center[start:start + 1500]
        old = cells[block_rows]
        support, exact_count, flat_count = contract.strict_support(nodes, old, block_center, exact)
        convex_count += int(support.sum()); exact_support += exact_count; coplanar += flat_count
        block_rows, block_center, old = block_rows[support], block_center[support], old[support]
        if not len(old):
            continue
        old_q = quality[block_rows]
        assert np.all((old_q < .0001).sum(axis=1) > 0)
        accepted = np.zeros(len(old), dtype=bool)
        for new, diagonal, q, signs in alternatives(nodes, old, block_center, geom, exact, contract):
            good = np.all(q >= .01, axis=1) & np.all(signs != 0, axis=1) & contract.chain_equal(old, new)
            for threshold in contract.BINS:
                good &= (q < threshold).sum(axis=1) <= (old_q < threshold).sum(axis=1)
            all_quality += int(good.sum())
            edge_keys = diagonal[:, 0].astype(np.uint64) * np.uint64(2**32) + diagonal[:, 1]
            positions = np.searchsorted(values, edge_keys)
            present = np.zeros(len(positions), dtype=bool)
            inside = positions < len(values)
            present[inside] = values[positions[inside]] == edge_keys[inside]
            good &= ~present
            absent_quality += int(good.sum())
            take = np.flatnonzero(good & ~accepted)
            accepted[take] = True
            chosen_rows.append(block_rows[take]); chosen_centers.append(block_center[take])
            chosen_new.append(new[take]); chosen_edges.append(diagonal[take])
            chosen_gains.append((old_q[take] < .0001).sum(axis=1))
    if chosen_rows:
        selected_rows, selected_centers, selected_new, selected_edges, gains = map(np.concatenate,
            (chosen_rows, chosen_centers, chosen_new, chosen_edges, chosen_gains))
    else:
        selected_rows = np.empty((0, 4), dtype=np.uint32); selected_new = np.empty((0, 4, 4), dtype=np.uint32)
        selected_centers = selected_edges = np.empty((0, 2), dtype=np.uint32); gains = np.empty(0, dtype=np.int64)
    del edge_index, values, starts, counts, order, quality
    gc.collect()
    keys = selected_edges[:, 0].astype(np.uint64) * np.uint64(2**32) + selected_edges[:, 1]
    packed, conflicts, duplicate = geom.pack(selected_rows, selected_edges, gains, keys, len(cells))
    proposal = args.output / "proposal.npz"
    np.savez_compressed(proposal, old_cell_ids=selected_rows[packed], old_center_edges=selected_centers[packed],
        new_cells=selected_new[packed], new_edges=selected_edges[packed], critical_gains=gains[packed])
    result = {**plan, "terminal": "four_four_indexed_proposals_exported_no_mesh_admitted", "controls": tested,
        "current_bins": bins, "current_critical_cells": int(critical.sum()), "exact_cell_sign_fallbacks": fallback,
        "critical_incident_edges": critical_edge_count,
        "critical_source_edge_valence_histogram": histogram, "degree_four_edges": len(degree_four),
        "closed_four_cycle_cavities": len(rows), "strictly_convex_cavities": convex_count,
        "exact_hull_support_fallbacks": exact_support, "known_coplanar_support_rejections": coplanar,
        "admissible_quality_alternatives": all_quality, "globally_absent_edge_alternatives": absent_quality,
        "one_diagonal_selected_per_cavity": len(selected_rows), "packed_disjoint_cavities": len(packed),
        "packing_cell_conflicts": conflicts, "packing_duplicate_new_edges": duplicate,
        "predicted_removed_critical_cells": int(gains[packed].sum()),
        "predicted_remaining_critical_cells": int(critical.sum() - gains[packed].sum()),
        "proposal_sha256": sha(proposal), "input_rehashed_unchanged": sha(args.mesh) == plan["mesh_sha256"],
        "separate_local_and_whole_volume_verification_required": True, "physics_admitted": False,
        "manufacturing_qualified": False, "seconds": time.monotonic() - started}
    (args.output / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    signal.alarm(0)
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
