#!/usr/bin/env python3
"""Fresh all-cell condition census and exact source-row accounting after flips."""
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
    for name in ("repository", "parent", "verified", "volume", "output"):
        parser.add_argument("--"+name, type=Path, required=True)
    args = parser.parse_args(); args.output.mkdir(mode=0o700, exist_ok=False)
    signal.signal(signal.SIGALRM, signal.SIG_DFL); signal.alarm(600); started = time.monotonic()
    base = args.repository/"docs/research"
    helper = load(base/"935-condition-directed-20261105/source/audit_all_conditions.py", "partition_full_condition_classifier", "0e3ba938b3e575f02b3b35c47f79b64b0fffb015de3acc6709827747cce279ca")
    exact = load(base/"935-unoptimized-volume-20261105/source/inspect_interval_volume.py", "partition_condition_intervals", "b0810ac21b35654556dce18ef022f6d4ca8f30a847223c5d566188eab82f4e71")
    oracle = load(base/"935-native-solver-admission-20261105/source/inspect_metric_disagreement.py", "partition_condition_fraction_oracle", "df44407d6d808729fc9cf00f079a6b21ff30260b584b5dec1d9dec064416d64e")
    tested = helper.controls(exact, oracle)
    proof = json.loads((args.verified/"report.json").read_text())
    assert proof["source_sha256"] == "beb8cde3ec10a526726c117c38e9cdc029c3eab6f325a80dfe32b61a1ea57301"
    mesh = args.verified/"candidate.npz"; assert sha(mesh) == proof["candidate_sha256"]
    old_mesh = args.parent/"peel-proof/candidate-volume.npz"
    assert sha(old_mesh) == proof["parent_mesh_sha256"] == "a4b19f3303e55e4a13830829664e26596247d26cd41632704d4584706773538a"
    volume = json.loads(args.volume.read_text())
    assert volume["mesh_sha256"] == sha(mesh) and volume["all_cells_positive_for_stored_binary_coordinates"] and volume["actual_complete_boundary_and_orientation_exact"]
    with np.load(old_mesh, allow_pickle=False) as data:
        old_nodes, old_cells, old_boundary = data["nodes"], data["tets"], data["boundary"]
    with np.load(mesh, allow_pickle=False) as data:
        nodes, cells, boundary = data["nodes"], data["tets"], data["boundary"]
    assert np.array_equal(nodes.view(np.uint64), old_nodes.view(np.uint64)) and np.array_equal(boundary, old_boundary)
    mapping = args.verified/"private-source-row-map.npz"; assert sha(mapping) == proof["private_source_map_sha256"]
    with np.load(mapping, allow_pickle=False) as data:
        rows = data["replaced_source_cell_ids"]
    assert len(rows) == len(np.unique(rows)) == 2640
    unchanged = np.ones(len(cells), bool); unchanged[rows] = False
    assert np.array_equal(cells[unchanged], old_cells[unchanged])
    before = json.loads((args.parent/"peeled-whole-condition/report.json").read_text())
    assert before["input_mesh_sha256"] == sha(old_mesh) and before["cells_classified"] == len(old_cells) == len(cells)
    old_flags, _, _, _ = helper.classify(nodes[old_cells[rows]], exact, oracle)
    new_flags, _, _, _ = helper.classify(nodes[cells[rows]], exact, oracle)
    assert not new_flags[:, helper.SEVERE_COLUMN].any()
    expected = np.array([before["counts_kappa_F_at_least"][label] for label in helper.LABELS])-old_flags.sum(axis=0)+new_flags.sum(axis=0)
    parent_volume = json.loads((args.parent/"peeled-whole-volume/report.json").read_text())
    for index, threshold in enumerate((.0001, .001, .01, .05, .1)):
        prediction = parent_volume["mean_ratio_below"][str(threshold)]-proof["exact_local_old_bin_totals"][index]+proof["exact_local_new_bin_totals"][index]
        assert prediction == volume["mean_ratio_below"][str(threshold)]
    totals = np.zeros(len(helper.THRESHOLDS), dtype=np.int64); fallback = orientation_fallback = 0; values = []
    for start in range(0, len(cells), 50000):
        flags, fractions, n, signs = helper.classify(nodes[cells[start:start+50000]], exact, oracle)
        totals += flags.sum(axis=0); fallback += n; orientation_fallback += signs
        values.extend({"cell_id": start+i, "reciprocal_frobenius_squared": [str(r.numerator), str(r.denominator)]} for i, r in fractions.items())
    assert np.array_equal(totals, expected)
    ids = np.array(sorted(row["cell_id"] for row in values), dtype=np.int64)
    assert len(ids) == len(np.unique(ids)) == totals[helper.SEVERE_COLUMN] and not np.isin(ids, rows).any()
    output = args.output/"private-exact-severe-values.json"; output.write_text(json.dumps(values, separators=(",", ":"))+"\n")
    subsets = args.output/"private-severe-ids.npz"; np.savez_compressed(subsets, cell_ids=ids)
    reciprocal = [Fraction(*map(int, row["reciprocal_frobenius_squared"])) for row in values]
    result = {"source_sha256": sha(Path(__file__)), "input_mesh_sha256": sha(mesh), "parent_mesh_sha256": sha(old_mesh),
        "controls": tested, "cells_freshly_classified": len(cells), "replaced_rows_independently_mapped": len(rows),
        "all_unchanged_tuples_nodes_and_boundary_exact": True,
        "complete_condition_counts_equal_independent_old_new_row_prediction": True,
        "complete_quality_counts_equal_independent_exact_local_prediction": True,
        "counts_kappa_F_at_least": dict(zip(helper.LABELS, map(int, totals))),
        "old_replaced_counts_kappa_F_at_least": dict(zip(helper.LABELS, map(int, old_flags.sum(axis=0)))),
        "new_replaced_counts_kappa_F_at_least": dict(zip(helper.LABELS, map(int, new_flags.sum(axis=0)))),
        "exact_threshold_fallbacks": fallback, "orientation_exact_fallbacks": orientation_fallback,
        "approximate_maximum_kappa_F": math.sqrt(float(1/min(reciprocal))),
        "private_values_sha256": sha(output), "private_ids_sha256": sha(subsets),
        "native_minSICN_not_recomputed_or_inferred": True, "condition_does_not_establish_PDE_accuracy": True,
        "absolute_quality_gate_passed": volume["diagnostic_quality_passed"], "physics_admitted": False,
        "manufacturing_qualified": False, "new_paid_compute_usd": 0, "seconds": time.monotonic()-started}
    (args.output/"report.json").write_text(json.dumps(result, indent=2)+"\n")
    signal.alarm(0); print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
