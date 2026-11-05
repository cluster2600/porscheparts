"""Fresh complete condition census after independently packed centroid cavities."""
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
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load(path, name, expected):
    assert sha(path) == expected
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repository", "parent", "verified", "volume", "output"):
        parser.add_argument("--"+name, type=Path, required=True)
    args = parser.parse_args(); args.output.mkdir(mode=0o700, exist_ok=False)
    signal.signal(signal.SIGALRM, signal.SIG_DFL); signal.alarm(600); started = time.monotonic()
    base = args.repository/"docs/research"
    helper = load(base/"935-condition-directed-20261105/source/audit_all_conditions.py", "batch_complete_classifier", "0e3ba938b3e575f02b3b35c47f79b64b0fffb015de3acc6709827747cce279ca")
    exact = load(base/"935-unoptimized-volume-20261105/source/inspect_interval_volume.py", "batch_condition_intervals", "b0810ac21b35654556dce18ef022f6d4ca8f30a847223c5d566188eab82f4e71")
    oracle = load(base/"935-native-solver-admission-20261105/source/inspect_metric_disagreement.py", "batch_condition_fractions", "df44407d6d808729fc9cf00f079a6b21ff30260b584b5dec1d9dec064416d64e")
    controls = helper.controls(exact, oracle)
    proof = json.loads((args.verified/"report.json").read_text())
    assert proof["independent_Fraction_condition_counts_match_remote"] and proof["all_complete_boundary_rows_bit_identical"]
    mesh = args.verified/"candidate.npz"; old_mesh = args.parent/"partition-verification/candidate.npz"
    assert sha(mesh) == proof["candidate_sha256"] and sha(old_mesh) == proof["parent_mesh_sha256"]
    volume = json.loads(args.volume.read_text())
    assert volume["mesh_sha256"] == sha(mesh) and volume["all_cells_positive_for_stored_binary_coordinates"] and volume["actual_complete_boundary_and_orientation_exact"]
    with np.load(old_mesh, allow_pickle=False) as data:
        old_nodes, old_cells, old_boundary = data["nodes"], data["tets"], data["boundary"]
    with np.load(mesh, allow_pickle=False) as data:
        nodes, cells, boundary = data["nodes"], data["tets"], data["boundary"]
    assert len(nodes) == len(old_nodes)+proof["new_numerical_interior_points"]
    assert np.array_equal(nodes[:len(old_nodes)].view(np.uint64), old_nodes.view(np.uint64)) and np.array_equal(boundary, old_boundary)
    mapping = args.verified/"private-source-map.npz"; assert sha(mapping) == proof["private_source_map_sha256"]
    with np.load(mapping, allow_pickle=False) as data:
        removed, new_rows = data["replaced_source_cell_ids"], data["new_candidate_cell_ids"]
    assert np.array_equal(removed, np.unique(removed)) and len(removed) == proof["old_cells_replaced"]
    keep = np.ones(len(old_cells), bool); keep[removed] = False
    assert np.array_equal(new_rows, np.arange(keep.sum(), len(cells))) and len(new_rows) == proof["new_cells"]
    assert np.array_equal(cells[:keep.sum()], old_cells[keep])
    before = json.loads((args.parent/"partition-whole-condition/report.json").read_text())
    parent_volume = json.loads((args.parent/"partition-whole-volume/report.json").read_text())
    old_flags, _, _, _ = helper.classify(old_nodes[old_cells[removed]], exact, oracle)
    new_flags, new_severe, _, _ = helper.classify(nodes[cells[new_rows]], exact, oracle)
    assert not new_severe and list(map(int, old_flags.sum(axis=0))) == proof["old_local_condition_counts"]
    assert list(map(int, new_flags.sum(axis=0))) == proof["new_local_condition_counts"]
    expected_counts = np.array([before["counts_kappa_F_at_least"][label] for label in helper.LABELS])-old_flags.sum(axis=0)+new_flags.sum(axis=0)
    for index, threshold in enumerate((.0001, .001, .01, .05, .1)):
        predicted = parent_volume["mean_ratio_below"][str(threshold)]-proof["old_local_bins"][index]+proof["new_local_bins"][index]
        assert predicted == volume["mean_ratio_below"][str(threshold)]
    path = args.parent/"partition-whole-condition/private-exact-severe-values.json"
    assert sha(path) == "e339ca30c5ebf16f68dbaa5a14fe059df9a4de09f3069f0c1a1176f75b8a1878"
    parent = {r["cell_id"]: Fraction(*map(int, r["reciprocal_frobenius_squared"])) for r in json.loads(path.read_text())}
    removed_set = set(map(int, removed)); worst = min(parent, key=parent.__getitem__); assert worst in removed_set
    retained = {int(i-np.searchsorted(removed, i)): value for i, value in parent.items() if i not in removed_set}
    del old_nodes, old_cells, old_boundary
    totals = np.zeros(len(helper.THRESHOLDS), dtype=np.int64); values = []; fallback = sign_fallback = 0
    for start in range(0, len(cells), 50000):
        flags, fractions, n, signs = helper.classify(nodes[cells[start:start+50000]], exact, oracle)
        totals += flags.sum(axis=0); fallback += n; sign_fallback += signs
        values.extend({"cell_id": start+i, "reciprocal_frobenius_squared": [str(r.numerator), str(r.denominator)]} for i, r in fractions.items())
    assert np.array_equal(totals, expected_counts)
    actual = {r["cell_id"]: Fraction(*map(int, r["reciprocal_frobenius_squared"])) for r in values}
    assert actual == retained and len(actual) == totals[helper.SEVERE_COLUMN]
    output = args.output/"private-exact-severe-values.json"; output.write_text(json.dumps(values, separators=(",", ":"))+"\n")
    subsets = args.output/"private-severe-ids.npz"; np.savez_compressed(subsets, cell_ids=np.array(sorted(actual), dtype=np.int64))
    result = {"source_sha256": sha(Path(__file__)), "input_mesh_sha256": sha(mesh), "parent_mesh_sha256": sha(old_mesh),
        "controls": controls, "cells_freshly_classified": len(cells), "old_cells_replaced": len(removed), "new_cells": len(new_rows),
        "all_old_coordinates_and_complete_boundary_exact": True, "all_retained_cell_tuples_exactly_mapped": True,
        "every_retained_severe_exact_condition_value_matches_fresh_census": True,
        "complete_condition_and_quality_counts_match_exact_source_row_prediction": True,
        "global_worst_source_cell_removed": True, "exact_global_max_condition_strictly_decreased": min(actual.values()) > min(parent.values()),
        "approximate_global_max_condition_before": math.sqrt(float(1/min(parent.values()))),
        "approximate_global_max_condition_after": math.sqrt(float(1/min(actual.values()))),
        "counts_kappa_F_at_least": dict(zip(helper.LABELS, map(int, totals))),
        "old_replaced_counts_kappa_F_at_least": dict(zip(helper.LABELS, map(int, old_flags.sum(axis=0)))),
        "new_replaced_counts_kappa_F_at_least": dict(zip(helper.LABELS, map(int, new_flags.sum(axis=0)))),
        "new_cell_condition_upper_bound_from_exact_quality": 12000,
        "bound_derivation": "q>=binary64(0.01)>1/100 and kappa_F^2<=144/q^3 imply kappa_F<12000",
        "exact_threshold_fallbacks": fallback, "orientation_exact_fallbacks": sign_fallback,
        "private_values_sha256": sha(output), "private_ids_sha256": sha(subsets),
        "native_minSICN_not_recomputed_or_inferred": True, "cell_condition_not_PDE_condition_or_accuracy": True,
        "absolute_quality_gate_passed": volume["diagnostic_quality_passed"], "physics_admitted": False,
        "manufacturing_qualified": False, "seconds": time.monotonic()-started}
    with (args.output/"report.json").open("x") as stream:
        stream.write(json.dumps(result, indent=2)+"\n")
    signal.alarm(0); print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
