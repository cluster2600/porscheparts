#!/usr/bin/env python3
"""Fresh complete condition census of the independently verified peeled volume."""
import argparse
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repository", "parent-mesh", "proof-root", "condition-root", "output"):
        parser.add_argument("--"+name, type=Path, required=True)
    args = parser.parse_args(); args.output.mkdir(mode=0o700, exist_ok=False)
    signal.signal(signal.SIGALRM, signal.SIG_DFL); signal.alarm(600)
    started = time.monotonic(); base = args.repository/"docs/research"
    helper = load(base/"935-condition-directed-20261105/source/audit_all_conditions.py", "peeled_condition_classification", "0e3ba938b3e575f02b3b35c47f79b64b0fffb015de3acc6709827747cce279ca")
    exact = load(base/"935-unoptimized-volume-20261105/source/inspect_interval_volume.py", "peeled_condition_intervals", "b0810ac21b35654556dce18ef022f6d4ca8f30a847223c5d566188eab82f4e71")
    oracle = load(base/"935-native-solver-admission-20261105/source/inspect_metric_disagreement.py", "peeled_condition_fractions", "df44407d6d808729fc9cf00f079a6b21ff30260b584b5dec1d9dec064416d64e")
    tested = helper.controls(exact, oracle)
    proof = json.loads((args.proof_root/"report.json").read_text())
    assert proof["source_sha256"] == "986bae3440420f1220b790f5ae8d54a92ebd427fb0c4a2c706712733317ddaf6"
    assert sha(args.parent_mesh) == proof["parent_mesh_sha256"] == "62717026bdfc3dc9c1a6cde682b32db12900cad8460f158a7319c41d001e2462"
    mesh = args.proof_root/"candidate-volume.npz"
    assert sha(mesh) == proof["candidate_volume_sha256"]
    before = json.loads((args.condition_root/"report.json").read_text())
    assert before["source_sha256"] == helper.sha(base/"935-condition-directed-20261105/source/audit_all_conditions.py")
    assert before["input_mesh_sha256"] == sha(args.parent_mesh)
    exact_path = args.condition_root/"private-exact-severe-values.json"
    assert sha(exact_path) == before["private_exact_values_sha256"] == "f4b54a89ce2506228c99abd37e8bce3d7ac9db7b1f2c4c188f4bb76cc499a87b"
    parent_severe = json.loads(exact_path.read_text())
    with np.load(args.parent_mesh, allow_pickle=False) as data:
        old_nodes, old_cells = data["nodes"], data["tets"]
    with np.load(mesh, allow_pickle=False) as data:
        nodes, cells = data["nodes"], data["tets"]
    removed = np.load(args.proof_root/"private-removed-source-cell-ids.npy", allow_pickle=False)
    assert len(removed) == proof["removed_tetrahedra"] and np.array_equal(removed, np.unique(removed))
    keep = np.ones(len(old_cells), dtype=bool); keep[removed] = False
    assert np.array_equal(nodes.view(np.uint64), old_nodes.view(np.uint64))
    assert np.array_equal(cells, old_cells[keep])
    parent_ids = {row["cell_id"] for row in parent_severe}
    assert all(int(i) in parent_ids for i in removed)
    deleted_counts = np.zeros(len(helper.THRESHOLDS), dtype=np.int64)
    removed_set = set(map(int, removed))
    for row in parent_severe:
        if row["cell_id"] in removed_set:
            r = Fraction(*map(int, row["reciprocal_frobenius_squared"]))
            deleted_counts += np.array([r*t*t <= 1 for t in helper.THRESHOLDS])
    expected = np.array([before["counts_kappa_F_at_least"][label] for label in helper.LABELS])-deleted_counts
    del old_nodes, old_cells
    totals = np.zeros(len(helper.THRESHOLDS), dtype=np.int64)
    values = []; fallback = sign_fallback = 0
    for start in range(0, len(cells), 50000):
        flags, fractions, count, sign_count = helper.classify(nodes[cells[start:start+50000]], exact, oracle)
        totals += flags.sum(axis=0); fallback += count; sign_fallback += sign_count
        values.extend({"cell_id": start+i, "reciprocal_frobenius_squared": [str(r.numerator), str(r.denominator)]} for i, r in fractions.items())
    assert np.array_equal(totals, expected), "Fresh census differs from exact unchanged-cell derivation"
    ids = np.array(sorted(row["cell_id"] for row in values), dtype=np.int64)
    assert len(ids) == len(np.unique(ids)) == totals[helper.SEVERE_COLUMN]
    output_values = args.output/"private-exact-severe-values.json"
    output_values.write_text(json.dumps(values, separators=(",", ":"))+"\n")
    output_ids = args.output/"private-severe-ids.npz"; np.savez_compressed(output_ids, cell_ids=ids)
    reciprocals = [Fraction(*map(int, row["reciprocal_frobenius_squared"])) for row in values]
    result = {"source_sha256": sha(Path(__file__)), "input_mesh_sha256": sha(mesh),
        "parent_mesh_sha256": sha(args.parent_mesh), "controls": tested,
        "cells_classified": len(cells), "every_remaining_cell_freshly_classified": True,
        "exact_values_for_every_severe_cell": True, "removed_cells": len(removed),
        "removed_cells_all_in_complete_parent_severe_set": True,
        "all_remaining_cells_and_coordinates_identical_to_parent": True,
        "fresh_counts_equal_independent_exact_deletion_prediction": True,
        "counts_kappa_F_at_least": dict(zip(helper.LABELS, map(int, totals))),
        "removed_counts_kappa_F_at_least": dict(zip(helper.LABELS, map(int, deleted_counts))),
        "ambiguous_cells_exactly_resolved": fallback, "orientation_exact_fallbacks": sign_fallback,
        "approximate_global_maximum_kappa_F": math.sqrt(float(1/min(reciprocals))) if reciprocals else None,
        "private_exact_values_sha256": sha(output_values), "private_ids_sha256": sha(output_ids),
        "native_minSICN_not_recomputed_or_inferred": True, "cell_condition_not_PDE_condition_or_error_bound": True,
        "physics_admitted": False, "manufacturing_qualified": False, "new_paid_compute_usd": 0,
        "seconds": time.monotonic()-started}
    (args.output/"report.json").write_text(json.dumps(result, indent=2)+"\n")
    signal.alarm(0); print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
