"""Classify every current edge Jacobian by interval/exact Frobenius condition.

The old native-disagreement subset is not assumed to cover every severe cell.
This audit never moves points, changes connectivity or executes a field solve.
"""
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


THRESHOLDS = (10**3, 10**6, 10**9, 10**12, 10**15, 2**52, 10**16, 3 * 2**52)
LABELS = ("1e3", "1e6", "1e9", "1e12", "1e15", "eps_inverse", "1e16", "3_eps_inverse")
SEVERE_COLUMN = 3


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def module(path, name, expected):
    assert sha(path) == expected
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def square(value, exact):
    low, high = exact.multiply(value, value)
    return np.maximum(low, 0), high


def sum_components(value, exact):
    lo, hi = square(value, exact)
    total = (np.zeros(len(lo)), np.zeros(len(lo)))
    for index in np.ndindex(lo.shape[1:]):
        total = exact.add(total, (lo[(slice(None), *index)], hi[(slice(None), *index)]))
    return total


def norm_product_and_determinant(xyz, exact):
    edges = exact.subtract((xyz[:, 1:], xyz[:, 1:]), (xyz[:, :1], xyz[:, :1]))
    norm_a = sum_components(edges, exact)
    components = []
    for a, b in ((1, 2), (2, 0), (0, 1)):
        for i, j in ((1, 2), (2, 0), (0, 1)):
            first = exact.multiply((edges[0][:, a, i], edges[1][:, a, i]), (edges[0][:, b, j], edges[1][:, b, j]))
            second = exact.multiply((edges[0][:, a, j], edges[1][:, a, j]), (edges[0][:, b, i], edges[1][:, b, i]))
            components.append(exact.subtract(first, second))
    adjugate = (np.stack([x[0] for x in components], axis=1), np.stack([x[1] for x in components], axis=1))
    numerator = exact.multiply(norm_a, sum_components(adjugate, exact))
    determinant = exact.determinant_interval(xyz)
    return numerator, determinant


def exact_reciprocal(points, oracle):
    xyz = [[Fraction(float(value)) for value in point] for point in points]
    matrix = [[xyz[j + 1][i] - xyz[0][i] for j in range(3)] for i in range(3)]
    determinant, reciprocal = oracle.exact_condition(matrix)
    assert determinant > 0, "Nonpositive stored-coordinate source cell"
    return reciprocal


def classify(xyz, exact, oracle):
    numerator, determinant = norm_product_and_determinant(xyz, exact)
    denominator = square(determinant, exact)
    above = np.zeros((len(xyz), len(THRESHOLDS)), dtype=bool)
    uncertain = determinant[0] <= 0
    for column, threshold in enumerate(THRESHOLDS):
        squared = float(threshold**2)
        constant = (squared, squared) if Fraction(squared) == threshold**2 else exact.expand(squared, squared)
        right = exact.multiply(constant, denominator)
        yes, no = numerator[0] >= right[1], numerator[1] < right[0]
        above[:, column] = yes
        uncertain |= ~(yes | no)
    reciprocal = {}
    for i in np.flatnonzero(uncertain):
        value = exact_reciprocal(xyz[i], oracle)
        reciprocal[int(i)] = value
        for column, threshold in enumerate(THRESHOLDS):
            above[i, column] = value <= Fraction(1, threshold**2)
    # Exact values for the complete severe set permit exact maximum ordering
    # and subsequent targeted work without depending on native metric flags.
    for i in np.flatnonzero(above[:, SEVERE_COLUMN]):
        if int(i) not in reciprocal:
            reciprocal[int(i)] = exact_reciprocal(xyz[i], oracle)
        value = reciprocal[int(i)]
        assert all(above[i, column] == (value <= Fraction(1, threshold**2))
                   for column, threshold in enumerate(THRESHOLDS))
    severe = {i: value for i, value in reciprocal.items() if above[i, SEVERE_COLUMN]}
    return above, severe, int(uncertain.sum()), int((determinant[0] <= 0).sum())


def controls(exact, oracle):
    base = oracle.controls()
    rng = np.random.default_rng(935)
    matrices = []
    for exponent in (0, 20, 30, 40, 50, 60):
        for _ in range(16):
            matrix = np.eye(3)
            matrix[np.triu_indices(3, 1)] = rng.integers(-4, 5, 3) / 8
            matrix[2, 2] = 2.**-exponent
            matrices.append(matrix)
    for threshold in THRESHOLDS:
        height = np.sqrt(2.) / threshold
        for value in (np.nextafter(height, 0.), height, np.nextafter(height, np.inf)):
            matrices.append(np.diag([1., 1., value]))
    xyz = np.zeros((len(matrices), 4, 3))
    xyz[:, 1:] = np.asarray(matrices).transpose(0, 2, 1)
    actual, _, fallback, _ = classify(xyz, exact, oracle)
    expected = np.array([[exact_reciprocal(points, oracle) <= Fraction(1, threshold**2)
        for threshold in THRESHOLDS] for points in xyz])
    assert np.array_equal(actual, expected) and fallback > 0
    scaled, _, _, _ = classify(xyz[:4] * 2**20, exact, oracle)
    assert np.array_equal(scaled, actual[:4])
    for invalid in (np.diag([1., 1., -1.]), np.diag([1., 1., 0.])):
        points = np.zeros((1, 4, 3)); points[0, 1:] = invalid.T
        try:
            classify(points, exact, oracle)
        except (AssertionError, ValueError):
            pass
        else:
            raise AssertionError("Invalid source cell accepted")
    return {**base, "independent_exact_classifications_compared": int(expected.size),
        "dyadic_and_near_threshold_fixtures": len(xyz), "interval_and_exact_fallback_paths_exercised": True,
        "interval_power_of_two_scale_invariance": True,
        "inverted_and_singular_source_cells_refused": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repository", "parent", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--control-only", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, exist_ok=False)
    signal.signal(signal.SIGALRM, signal.SIG_DFL); signal.alarm(600)
    started = time.monotonic()
    source = args.repository / "docs/research"
    exact = module(source / "935-unoptimized-volume-20261105/source/inspect_interval_volume.py", "whole_condition_intervals",
        "b0810ac21b35654556dce18ef022f6d4ca8f30a847223c5d566188eab82f4e71")
    oracle = module(source / "935-native-solver-admission-20261105/source/inspect_metric_disagreement.py", "whole_condition_fraction_oracle",
        "df44407d6d808729fc9cf00f079a6b21ff30260b584b5dec1d9dec064416d64e")
    tested = controls(exact, oracle)
    (args.output / "controls.json").write_text(json.dumps(tested, indent=2) + "\n")
    if args.control_only:
        print(json.dumps(tested), flush=True)
        return
    assert sha(args.parent / "manifest.json") == "70ea643568877eb271a0ec379950d8e1230fe9f6947d17c8876a4b02900a60b4"
    index = {row["path"]: row["sha256"] for row in json.loads((args.parent / "manifest.json").read_text())["files"]}
    for name in ("local-proof/candidate.npz", "whole-volume/report.json", "condition-coverage/private-subset-map.npz"):
        assert sha(args.parent / name) == index[name]
    mesh = args.parent / "local-proof/candidate.npz"
    assert sha(mesh) == "62717026bdfc3dc9c1a6cde682b32db12900cad8460f158a7319c41d001e2462"
    volume = json.loads((args.parent / "whole-volume/report.json").read_text())
    assert volume["all_cells_positive_for_stored_binary_coordinates"] and volume["actual_complete_boundary_and_orientation_exact"]
    plan = {"source_sha256": sha(Path(__file__)), "input_mesh_sha256": sha(mesh),
        "upstream_verdict": "Complete source geometry and positivity proven; known conditioning defects remain; read-only full coverage before any further repair or field run",
        "thresholds": dict(zip(LABELS, THRESHOLDS)), "severe_target": "1e12",
        "every_cell_classified": True, "exact_values_for_every_severe_cell": True,
        "geometry_or_connectivity_change_permitted": False, "field_solve_permitted": False, "new_paid_compute_usd": 0}
    (args.output / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    with np.load(mesh, allow_pickle=False) as data:
        nodes, cells = data["nodes"], data["tets"]
    totals = np.zeros(len(THRESHOLDS), dtype=np.int64)
    severe_rows = []; fallback = sign_fallback = 0
    for start in range(0, len(cells), 50000):
        flags, values, count, sign_count = classify(nodes[cells[start:start + 50000]], exact, oracle)
        totals += flags.sum(axis=0); fallback += count; sign_fallback += sign_count
        severe_rows.extend({"cell_id": start + i, "reciprocal_frobenius_squared": [str(value.numerator), str(value.denominator)]}
            for i, value in values.items())
    ids = np.array(sorted(row["cell_id"] for row in severe_rows), dtype=np.int64)
    assert len(ids) == len(np.unique(ids)) == totals[SEVERE_COLUMN]
    with np.load(args.parent / "condition-coverage/private-subset-map.npz", allow_pickle=False) as data:
        previous = data["retained_candidate_ids"]
    assert len(previous) == 2624 and np.isin(previous, ids).all()
    assert np.all(ids < len(cells) - 27016), "New-cell bound disagrees with full conditioning audit"
    values_path = args.output / "private-exact-severe-values.json"
    values_path.write_text(json.dumps(severe_rows, separators=(",", ":")) + "\n")
    subset = args.output / "private-severe-ids.npz"
    np.savez_compressed(subset, cell_ids=ids)
    reciprocal = [Fraction(*map(int, row["reciprocal_frobenius_squared"])) for row in severe_rows]
    result = {**plan, "controls": tested, "cells_classified": len(cells), "exact_condition_values": len(ids),
        "counts_kappa_F_at_least": {key: int(value) for key, value in zip(LABELS, totals)},
        "ambiguous_threshold_or_orientation_cells_exactly_resolved": fallback,
        "orientation_exact_fallbacks": sign_fallback,
        "previous_native_subset_retained_and_verified": len(previous),
        "additional_severe_cells_outside_previous_subset": len(ids) - len(previous),
        "all_new_cells_remain_below_severe_threshold": True,
        "maximum_ordered_by_exact_reciprocal_comparison": True,
        "approximate_global_maximum_kappa_F": math.sqrt(float(1/min(reciprocal))) if reciprocal else None,
        "private_exact_values_sha256": sha(values_path), "private_ids_sha256": sha(subset),
        "source_rehashed_unchanged": sha(mesh) == plan["input_mesh_sha256"],
        "cell_condition_not_PDE_condition_or_error_bound": True,
        "native_minSICN_not_recomputed_or_inferred": True,
        "physics_admitted": False, "manufacturing_qualified": False, "seconds": time.monotonic() - started}
    (args.output / "report.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    signal.alarm(0); print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
