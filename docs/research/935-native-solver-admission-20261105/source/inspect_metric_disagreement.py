"""Inspect native minSICN failures with exact edge-matrix conditioning.

The Frobenius condition metric here is explicitly different from Gmsh minSICN.
No field boundary condition or physical/material acceptance threshold is set.
"""
import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import signal
import time

import numpy as np


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def exact_condition(matrix):
    a = matrix
    determinant = a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1]) - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0]) + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0])
    if determinant == 0:
        raise ValueError("Singular edge matrix")
    adjugate = []
    for i in range(3):
        row = []
        for j in range(3):
            remaining_rows = [r for r in range(3) if r != j]
            remaining_columns = [c for c in range(3) if c != i]
            minor = a[remaining_rows[0]][remaining_columns[0]] * a[remaining_rows[1]][remaining_columns[1]] - a[remaining_rows[0]][remaining_columns[1]] * a[remaining_rows[1]][remaining_columns[0]]
            row.append((-1) ** (i + j) * minor)
        adjugate.append(row)
    for i in range(3):
        for j in range(3):
            assert sum(a[i][k] * adjugate[k][j] for k in range(3)) == (determinant if i == j else 0)
    norm_a_squared = sum(value * value for row in a for value in row)
    norm_adjugate_squared = sum(value * value for row in adjugate for value in row)
    reciprocal_squared = determinant ** 2 / (norm_a_squared * norm_adjugate_squared)
    assert 0 < reciprocal_squared <= Fraction(1, 9)
    return determinant, reciprocal_squared


def controls():
    identity = [[Fraction(int(i == j)) for j in range(3)] for i in range(3)]
    assert exact_condition(identity) == (Fraction(1), Fraction(1, 9))
    scaled = [[value * 2**20 for value in row] for row in identity]
    assert exact_condition(scaled)[1] == Fraction(1, 9)
    thin = [row.copy() for row in identity]
    thin[2][2] = Fraction(1, 2**60)
    assert exact_condition(thin)[0] > 0 and exact_condition(thin)[1] < Fraction(1, 10**32)
    inverted = [row.copy() for row in identity]
    inverted[2][2] = -1
    assert exact_condition(inverted)[0] < 0
    singular = [row.copy() for row in identity]
    singular[2] = singular[1].copy()
    try:
        exact_condition(singular)
    except ValueError:
        pass
    else:
        raise AssertionError("Singular control accepted")
    return {"analytic_identity": True, "exact_uniform_scale_invariance": True,
            "thin_positive_and_inverted_distinguished": True, "singular_refused": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("mesh", "surface", "native-report", "native-failures", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, exist_ok=False)
    signal.signal(signal.SIGALRM, signal.SIG_DFL)
    signal.alarm(600)
    started = time.monotonic()
    tests = controls()
    native = json.loads(args.native_report.read_text())
    assert sha(args.mesh) == native["input_sha256"] == "233f7bd83072772fa0b92d0287f20cec3cf44c4988546be42addf5579630299e"
    assert sha(args.surface) == "5b04e72b5f7b48f340a39c14009292c52c1bf1ac422ad64cd3250c17ddf51db4"
    assert sha(args.native_failures) == native["native_metrics"]["minSICN"]["private_indices_sha256"]
    assert native["native_metrics"]["minDetJac"]["nonpositive_or_nonfinite_cells"] == 0
    assert native["native_metrics"]["volume"]["nonpositive_or_nonfinite_cells"] == 0
    with np.load(args.mesh, allow_pickle=False) as data:
        nodes, cells, boundary = data["nodes"], data["tets"], data["boundary"]
    with np.load(args.surface, allow_pickle=False) as data:
        vertices = data["vertices"]
    assert np.array_equal(nodes[:len(vertices)], vertices)
    assert np.array_equal(np.unique(boundary), np.arange(len(vertices)))
    with np.load(args.native_failures, allow_pickle=False) as data:
        ids, values = data["cell_ids"], data["values"]
    assert len(ids) == native["native_metrics"]["minSICN"]["nonpositive_or_nonfinite_cells"]
    assert np.all(np.isfinite(values)) and np.all(values <= 0)
    interior = (cells[ids] >= len(vertices)).sum(axis=1)
    affected = np.unique(cells[ids][cells[ids] >= len(vertices)])
    conditions = []
    exact_rows = []
    bins = {12: 0, 15: 0, 16: 0, 18: 0}
    epsilon = Fraction(1, 2**52)
    amplification = spectral_lower_bound_amplification = 0
    for cell_id in ids:
        xyz = [[Fraction.from_float(float(value)) for value in point] for point in nodes[cells[cell_id]]]
        matrix = [[xyz[j + 1][i] - xyz[0][i] for j in range(3)] for i in range(3)]
        determinant, reciprocal_squared = exact_condition(matrix)
        assert determinant > 0
        for power in bins:
            bins[power] += reciprocal_squared <= Fraction(1, 10**(2 * power))
        amplification += reciprocal_squared <= epsilon ** 2
        spectral_lower_bound_amplification += reciprocal_squared <= epsilon ** 2 / 9
        conditions.append(math.sqrt(float(1 / reciprocal_squared)))
        exact_rows.append({"cell_id": int(cell_id), "positive_determinant": [str(determinant.numerator), str(determinant.denominator)],
                           "reciprocal_frobenius_squared": [str(reciprocal_squared.numerator), str(reciprocal_squared.denominator)]})
    exact_path = args.output / "private-exact-condition-values.json"
    exact_path.write_text(json.dumps(exact_rows, separators=(",", ":")) + "\n")
    result = {"source_sha256": sha(Path(__file__)), "mesh_sha256": sha(args.mesh), "native_report_sha256": sha(args.native_report),
              "native_failure_file_sha256": sha(args.native_failures), "native_failed_metric": "minSICN",
              "native_negative_cells": int((values < 0).sum()), "native_zero_cells": int((values == 0).sum()),
              "all_failed_metric_cells_exact_determinants_positive": True, "exact_cells_inspected": len(ids),
              "edge_matrix_definition": "Columns x1-x0, x2-x0, x3-x0; exact differences of stored binary64 coordinates",
              "condition_definition": "kappa_F = norm_F(A)*norm_F(adj(A))/abs(det(A)); exact squared comparisons; different from Gmsh minSICN",
              "frobenius_condition_at_least": {"1e" + str(k): int(v) for k, v in bins.items()},
              "condition_epsilon_indicator_at_least_one": int(amplification),
              "spectral_condition_lower_bound_times_epsilon_at_least_one": int(spectral_lower_bound_amplification),
              "approximate_frobenius_condition_quantiles": dict(zip(("minimum", "median", "maximum"), map(float, np.quantile(conditions, [0, .5, 1])))),
              "failed_cells_by_interior_vertex_count": np.bincount(interior, minlength=5).tolist(),
              "unique_interior_vertices_incident_to_failed_metric_cells": len(affected),
              "boundary_classification_is_not_engine_boundary_condition": True,
              "exact_private_values_sha256": sha(exact_path), "controls": tests,
              "geometry_or_connectivity_modified": False, "field_solve_executed": False,
              "case_specific_solver_admission": False, "physics_admitted": False, "manufacturing_qualified": False,
              "new_paid_compute_usd": 0, "seconds": time.monotonic() - started}
    (args.output / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)
    signal.alarm(0)


if __name__ == "__main__":
    main()
