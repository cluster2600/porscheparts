#!/usr/bin/env python3
"""Complete severe-cell weak-convex edge coverage before boundary-exact proposals."""
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import time

import numpy as np


def sha(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load(path, name, expected):
    assert sha(path) == expected
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def weak_only(nodes, old, center, cycle, exact):
    ring, _ = cycle.ring_data(old, center)
    vertices = np.column_stack((center, ring))
    faces = old[:, :, cycle.FACES].reshape(-1, 16, 3)
    internal = np.all(np.any(faces[:, :, :, None] == center[:, None, None, :], axis=2), axis=2)
    assert np.all(internal.sum(axis=1) == 8)
    hull = faces[~internal].reshape(-1, 8, 3)
    missing = ~np.any(vertices[:, None, :, None] == hull[:, :, None, :], axis=3)
    other = np.broadcast_to(vertices[:, None, :], missing.shape)[missing].reshape(-1, 8, 3)
    probes = np.concatenate((np.broadcast_to(hull[:, :, None, :], (len(old), 8, 3, 3)), other[:, :, :, None]), axis=3)
    xyz = nodes[probes.reshape(-1, 4)].reshape(-1, 24, 4, 3)
    low, high = exact.determinant_interval(xyz.reshape(-1, 4, 3))
    low, high = low.reshape(-1, 24), high.reshape(-1, 24)
    passed = ~np.any(low > 0, axis=1); coplanar = np.zeros(len(old), bool); fallbacks = 0
    for row in np.flatnonzero(passed):
        for column in np.flatnonzero(high[row] >= 0):
            value = exact.exact_determinant(xyz[row, column]); fallbacks += 1
            if value > 0:
                passed[row] = False; break
            coplanar[row] |= value == 0
    return passed & coplanar, int((passed & ~coplanar).sum()), fallbacks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repository", "parent", "reference", "output"):
        parser.add_argument("--"+name, type=Path, required=True)
    parser.add_argument("--control-only", action="store_true")
    args = parser.parse_args(); args.output.mkdir(mode=0o700, exist_ok=False)
    signal.signal(signal.SIGALRM, signal.SIG_DFL); signal.alarm(600); started = time.monotonic()
    base = args.repository/"docs/research"
    prior = load(Path(__file__).with_name("propose_partition_flips.py"), "complete_weak_alternatives", "2c4df1e1e708c24813eba5eb0e8176ce34933500f614636524a04891db912967")
    partition = load(Path(__file__).with_name("convex_partition_contract.py"), "complete_exact_partition", "c06c37065561813a27791a4096d41c9e221f83ba48e775b2de6489f1f5a84a07")
    four = load(base/"935-four-four-cavities-20261105/source/propose_four_four.py", "complete_ring_operator", "4298598e1fc5da3f28ad85fcb41cd5db427f5c5a6418f849b13c5bb07963c236")
    geom = load(base/"935-local-cavity-20261105/source/assess_initial_cavities.py", "complete_proposal_quality", "ee60f26e2449fc2da97e34b0fa3f67c5472e0902b8a4166210e2089624887aa6")
    exact = load(base/"935-unoptimized-volume-20261105/source/inspect_interval_volume.py", "complete_weak_intervals", "b0810ac21b35654556dce18ef022f6d4ca8f30a847223c5d566188eab82f4e71")
    cycle = load(base/"935-four-four-cavities-20261105/source/four_four_contract.py", "complete_cycle_topology", "a5379daacb7a099810acf678110b74d4e6d9c5f34b01ac38fff1472a4ab0228c")
    indexer = load(base/"935-local-cavity-20261105/source/verify_global_incidence.py", "complete_weak_edge_index", "2d3d3b44ea5e055b3600231d935bed280197b33cc4400ee0553d826cc239d4f8")
    assert sha(args.reference) == "8dbad69d7fe07762fa7c2cfda2f165ccae35b7c846cb8bb1b1efda220bedeb83"
    with np.load(args.reference, allow_pickle=False) as data:
        nodes, old, literal = data["nodes"], data["old_cells"], data["reference_cells"]
    weak, strict_count, _ = weak_only(nodes, old[None], np.array([[0, 1]]), cycle, exact)
    assert weak.tolist() == [True] and strict_count == 0
    alternatives, _ = prior.actual_alternatives(nodes, old, (0, 1), four, geom, exact, cycle, partition)
    assert alternatives and {tuple(sorted(map(int, t))) for t in alternatives[0][1]} == {tuple(sorted(map(int, t))) for t in literal}
    bad = nodes.copy(); bad[:2, 1] = .5; bad[2, 1] = .25
    assert not weak_only(bad, old[None], np.array([[0, 1]]), cycle, exact)[0].any()
    tested = {"actual_complete_path_reproduces_literal_weak_reference": True,
        "genuine_nonconvex_source_filtered_before_trial": True, "exact_partition_contract_unchanged": True}
    (args.output/"controls.json").write_text(json.dumps(tested, indent=2)+"\n")
    if args.control_only:
        print(json.dumps(tested), flush=True); return
    assert sha(args.parent/"manifest.json") == "5daee08ce4a12bbe1c389d7eecd7125c63392b3c961954e7d5bb1d18078c02ea"
    mesh = args.parent/"peel-proof/candidate-volume.npz"
    assert sha(mesh) == "a4b19f3303e55e4a13830829664e26596247d26cd41632704d4584706773538a"
    path = args.parent/"peeled-whole-condition/private-exact-severe-values.json"
    assert sha(path) == "e9747f2b6e05e8046039b2eb5622445a0141b8e6ca7edea8ba3ab27142aa3f11"
    conditions = {r["cell_id"]: Fraction(*map(int, r["reciprocal_frobenius_squared"])) for r in json.loads(path.read_text())}
    severe_ids = np.array(sorted(conditions)); assert len(severe_ids) == 15945
    worst = min(conditions, key=conditions.__getitem__)
    with np.load(mesh, allow_pickle=False) as data:
        nodes, cells = data["nodes"], data["tets"].astype(np.uint32)
    values, starts, counts, order = indexer.full_index(cells)
    severe = cells[severe_ids]
    queries = np.unique(np.column_stack([np.minimum(severe[:, a], severe[:, b]).astype(np.uint64)*np.uint64(2**32)+np.maximum(severe[:, a], severe[:, b]) for a, b in geom.PAIRS]))
    positions = np.searchsorted(values, queries); assert np.array_equal(values[positions], queries)
    degree = positions[counts[positions] == 4]
    source_rows = (order[starts[degree, None]+np.arange(4)]//6).astype(np.uint32)
    center = np.column_stack((values[degree]//np.uint64(2**32), values[degree]%np.uint64(2**32))).astype(np.uint32)
    old = cells[source_rows]
    keep = ~np.any(old[:, :, :, None] == center[:, None, None, :], axis=3)
    outer = np.sort(np.where(keep, old, np.iinfo(np.uint32).max).reshape(-1, 16), axis=1)[:, :8]
    closed = np.all(outer[:, ::2] == outer[:, 1::2], axis=1)&np.all(np.diff(outer[:, ::2].astype(np.int64), axis=1) > 0, axis=1)
    source_rows, center = source_rows[closed], center[closed]
    reasons = Counter(); weak_count = strict_count = fallback = 0; candidates = []
    for start in range(0, len(source_rows), 1000):
        ids, axes = source_rows[start:start+1000], center[start:start+1000]
        admitted, strict, extra = weak_only(nodes, cells[ids], axes, cycle, exact)
        weak_count += int(admitted.sum()); strict_count += strict; fallback += extra
        for row, axis in zip(ids[admitted], axes[admitted]):
            row = list(map(int, row)); axis = list(map(int, axis))
            alternatives, rejected = prior.actual_alternatives(nodes, cells[row], axis, four, geom, exact, cycle, partition)
            reasons.update(rejected)
            for alternative_index, new, diagonal, proof in alternatives:
                new_key = np.uint64(diagonal[0])*np.uint64(2**32)+np.uint64(diagonal[1])
                at = int(np.searchsorted(values, new_key))
                if at < len(values) and values[at] == new_key:
                    reasons["created_edge_already_present"] += 1; continue
                candidates.append({"old_cell_ids": row, "old_center": axis, "new_cells": new.tolist(), "new_edge": diagonal.tolist(),
                    "alternative_index": alternative_index, "contains_global_worst": worst in row,
                    "severe_gain": sum(i in conditions for i in row), "critical_gain": proof["old_bins"][0]-proof["new_bins"][0],
                    "hull_facets": proof["hull_facets"], "exact_domain_volume": [str(proof["exact_domain_volume"].numerator), str(proof["exact_domain_volume"].denominator)]})
    selected = []; used = set(); entities = set()
    for c in sorted(candidates, key=lambda c: (-int(c["contains_global_worst"]), -c["severe_gain"], tuple(c["old_center"]), c["alternative_index"])):
        edge = tuple(c["new_edge"])
        if used & set(c["old_cell_ids"]) or edge in entities:
            reasons["packing_conflict"] += 1; continue
        used.update(c["old_cell_ids"]); entities.add(edge); selected.append(c)
    proposal = args.output/"private-complete-weak-proposals.json"; proposal.write_text(json.dumps(selected, separators=(",", ":"))+"\n")
    result = {"source_sha256": sha(Path(__file__)), "contract_sha256": sha(Path(__file__).with_name("convex_partition_contract.py")),
        "mesh_sha256": sha(mesh), "controls": tested, "complete_severe_cells": len(severe_ids),
        "unique_severe_incident_edges": len(queries), "degree_four_edges": len(degree), "closed_four_cycles": len(source_rows),
        "strictly_supported_stars": strict_count, "weakly_supported_stars_with_exact_coplanarity": weak_count,
        "exact_support_fallbacks": fallback, "exact_domain_and_absent_edge_alternatives": len(candidates),
        "packed_cavities": len(selected), "severe_cells_replaced_if_applied": sum(c["severe_gain"] for c in selected),
        "critical_cells_removed_if_applied": sum(c["critical_gain"] for c in selected),
        "global_worst_replaced_if_applied": any(c["contains_global_worst"] for c in selected), "reasons": dict(reasons),
        "quality_floor_and_all_bins_exact_contract_unchanged": True, "same_exact_domain_boundary_and_coordinates_required": True,
        "source_strictness_proxy_replaced_by_actual_convex_partition_proof": True,
        "proposal_sha256": sha(proposal), "geometry_or_connectivity_modified": False,
        "separate_source_star_and_whole_volume_verification_required": True,
        "physics_admitted": False, "manufacturing_qualified": False, "new_paid_compute_usd": 0, "seconds": time.monotonic()-started}
    (args.output/"report.json").write_text(json.dumps(result, indent=2)+"\n")
    signal.alarm(0); print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
