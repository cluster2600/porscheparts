"""Certify new-cell conditioning and map the previously severe exact subset.

For mean ratio q and an edge Jacobian A, kappa_F(A) <= 12/q^(3/2).
An interval/exact certificate of q >= binary64(0.01) implies kappa_F <= 12000.
This is a cell-Jacobian bound, not a PDE-system condition or accuracy bound.
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


PAIRS = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def floor_certificate(xyz, exact):
    determinant = exact.determinant_interval(xyz)
    total = (np.zeros(len(xyz)), np.zeros(len(xyz)))
    for a, b in PAIRS:
        difference = exact.subtract((xyz[:, a], xyz[:, a]), (xyz[:, b], xyz[:, b]))
        square = exact.multiply(difference, difference)
        square = (np.maximum(square[0], 0), square[1])
        for axis in range(3):
            total = exact.add(total, (square[0][:, axis], square[1][:, axis]))
    left = exact.multiply((432., 432.), exact.multiply(determinant, determinant))
    cube = float(Fraction(.01)**3)
    right = exact.multiply(exact.expand(cube, cube), exact.multiply(exact.multiply(total, total), total))
    passed = (determinant[0] > 0) & (left[0] >= right[1])
    failed = (determinant[1] <= 0) | (left[1] < right[0])
    uncertain = np.flatnonzero(~passed & ~failed)
    for i in uncertain:
        det = exact.exact_determinant(xyz[i])
        points = [[Fraction(float(v)) for v in point] for point in xyz[i]]
        edge_sum = sum((points[a][axis] - points[b][axis])**2 for a, b in PAIRS for axis in range(3))
        passed[i] = det > 0 and 432 * det**2 >= Fraction(.01)**3 * edge_sum**3
    return passed, len(uncertain)


def controls(reference, exact):
    assert sha(reference) == "90ae971f7ff2687c60e3bb9460d5241edeedae3fbaf6f07ad69be08604c36690"
    with np.load(reference, allow_pickle=False) as data:
        nodes, old, new = data["nodes"], data["old_cells"], data["reference_cells"]
    assert floor_certificate(nodes[old], exact)[0].tolist() == [False, True, True, True]
    assert floor_certificate(nodes[new], exact)[0].all()
    inverted = nodes[new].copy()
    inverted[0, [1, 2]] = inverted[0, [2, 1]]
    assert floor_certificate(inverted, exact)[0].tolist() == [False, True, True, True]
    coplanar = nodes[new].copy()
    coplanar[0, :, 2] = 0.
    assert not floor_certificate(coplanar, exact)[0][0]
    assert Fraction(.01) >= Fraction(1, 100)
    return {"known_thin_cell_refused": True, "all_literal_reference_cells_certified": True,
        "inverted_and_coplanar_refused": True, "binary64_floor_at_least_exact_one_hundredth": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repository", "native-parent", "old-mesh", "candidate", "proposal", "volume-report", "reference", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, exist_ok=False)
    signal.signal(signal.SIGALRM, signal.SIG_DFL)
    signal.alarm(600)
    started = time.monotonic()
    path = args.repository / "docs/research/935-unoptimized-volume-20261105/source/inspect_interval_volume.py"
    assert sha(path) == "b0810ac21b35654556dce18ef022f6d4ca8f30a847223c5d566188eab82f4e71"
    spec = importlib.util.spec_from_file_location("retained_four_condition_intervals", path)
    exact = importlib.util.module_from_spec(spec); spec.loader.exec_module(exact)
    tested = controls(args.reference, exact)
    assert sha(args.old_mesh) == "233f7bd83072772fa0b92d0287f20cec3cf44c4988546be42addf5579630299e"
    assert sha(args.candidate) == "62717026bdfc3dc9c1a6cde682b32db12900cad8460f158a7319c41d001e2462"
    assert sha(args.proposal) == "5eab7cddce5454a0e5aac81d80e82ead120c718b3dd0684bb0efbd34d92515f4"
    volume = json.loads(args.volume_report.read_text())
    assert volume["source_sha256"] == sha(path) and volume["mesh_sha256"] == sha(args.candidate)
    assert volume["all_cells_positive_for_stored_binary_coordinates"] and volume["actual_complete_boundary_and_orientation_exact"]
    assert sha(args.native_parent / "manifest.json") == "91fbc0ecc6dfdeb2b95949676698f0ea9a1a8605d783efdfa61e2fe3722ed64d"
    manifest = {row["path"]: row["sha256"] for row in json.loads((args.native_parent / "manifest.json").read_text())["files"]}
    for name in ("head/private-nonpositive-minSICN.npz", "conditioning/report.json", "conditioning/private-exact-condition-values.json"):
        assert sha(args.native_parent / name) == manifest[name]
    prior = json.loads((args.native_parent / "conditioning/report.json").read_text())
    assert prior["mesh_sha256"] == sha(args.old_mesh) and prior["all_failed_metric_cells_exact_determinants_positive"]
    with np.load(args.old_mesh, allow_pickle=False) as data:
        old_nodes, old_cells, old_boundary = data["nodes"], data["tets"], data["boundary"]
    with np.load(args.candidate, allow_pickle=False) as data:
        nodes, cells, boundary = data["nodes"], data["tets"], data["boundary"]
    with np.load(args.proposal, allow_pickle=False) as data:
        removed, replacements = np.unique(data["old_cell_ids"]), data["new_cells"].reshape(-1, 4)
    keep = np.ones(len(old_cells), dtype=bool); keep[removed] = False
    assert np.array_equal(old_nodes.view(np.uint64), nodes.view(np.uint64)) and np.array_equal(boundary, old_boundary)
    assert np.array_equal(cells[:keep.sum()], old_cells[keep]) and np.array_equal(cells[keep.sum():], replacements)
    certificate, exact_fallbacks = floor_certificate(nodes[replacements], exact)
    assert certificate.all(), "A new cell fails the exact mean-ratio floor"
    with np.load(args.native_parent / "head/private-nonpositive-minSICN.npz", allow_pickle=False) as data:
        flagged = data["cell_ids"]
    rows = json.loads((args.native_parent / "conditioning/private-exact-condition-values.json").read_text())
    assert sorted(row["cell_id"] for row in rows) == sorted(flagged.tolist()) and len(flagged) == 3130
    replaced = np.isin(flagged, removed)
    retained = flagged[~replaced]
    mapped = retained - np.searchsorted(removed, retained)
    assert np.array_equal(cells[mapped], old_cells[retained])
    epsilon = Fraction(1, 2**52)
    classes = {}
    for label, ids in (("replaced", set(flagged[replaced].tolist())), ("retained", set(retained.tolist()))):
        reciprocal = [Fraction(*map(int, row["reciprocal_frobenius_squared"])) for row in rows if row["cell_id"] in ids]
        classes[label] = {"cells": len(reciprocal),
            "exact_kappa_F_at_least": {"1e" + str(power): sum(value <= Fraction(1, 10**(2*power)) for value in reciprocal) for power in (12, 15, 16, 18)},
            "exact_kappa_F_times_epsilon_at_least_one": sum(value <= epsilon**2 for value in reciprocal),
            "spectral_lower_bound_times_epsilon_at_least_one": sum(value <= epsilon**2/9 for value in reciprocal),
            "approximate_maximum_kappa_F": math.sqrt(float(1 / min(reciprocal))) if reciprocal else None}
    private = args.output / "private-subset-map.npz"
    np.savez_compressed(private, retained_source_ids=retained, retained_candidate_ids=mapped, replaced_source_ids=flagged[replaced])
    result = {"source_sha256": sha(Path(__file__)), "source_mesh_sha256": sha(args.old_mesh),
        "candidate_sha256": sha(args.candidate), "new_cells_certified": len(replacements),
        "all_new_exact_mean_ratios_at_least_binary64_001": True,
        "new_cell_floor_certificate_interval_passes": int(certificate.sum()) - exact_fallbacks,
        "new_cell_floor_certificate_exact_fallbacks": exact_fallbacks,
        "guaranteed_new_cell_edge_matrix_kappa_F_upper_bound": 12000,
        "bound": "kappa_F <= ||A||_F^3/(sqrt(3)*abs(det A)) <= 12/q^(3/2); q >= binary64(0.01) >= 1/100",
        "all_unmodified_cells_and_nodes_exactly_preserved": True, "prior_severe_metric_subset": classes,
        "retained_exact_condition_values_still_applicable": True,
        "native_minSICN_not_recomputed_or_inferred": True,
        "cell_Jacobian_bound_is_not_PDE_matrix_condition_or_physics_accuracy": True,
        "controls": tested, "private_subset_map_sha256": sha(private),
        "physics_admitted": False, "manufacturing_qualified": False, "new_paid_compute_usd": 0,
        "seconds": time.monotonic() - started}
    (args.output / "report.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    signal.alarm(0)
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
