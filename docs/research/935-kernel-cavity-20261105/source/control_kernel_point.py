"""Literal concave control whose volume centroid lies outside its strict kernel."""
import argparse
from fractions import Fraction as F
import hashlib
import importlib.util
from itertools import combinations
import json
from pathlib import Path
import signal

import numpy as np


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load(path, name, expected=None):
    if expected is not None:
        assert sha(path) == expected
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def fixture():
    epsilon = 2.**-24; height = 7/8
    nodes = np.array([[0, height+epsilon, 1], [0, height+epsilon, -1],
                      [0, height, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [-1, 1, 0], [-1, 0, 0]], dtype=np.float64)
    old = np.array([[0, 1, 2+i, 2+(i+1)%6] for i in range(6)], dtype=np.uint32)
    # Sign is independently known from the oriented polygon and vertical axis.
    old = old[:, [0, 1, 3, 2]]
    reference = np.array([0, 61/64, 0], dtype=np.float64)
    return nodes, old, reference


def run(repository, output):
    base = repository/"docs/research"
    geometry = load(base/"935-residual-source-admission-20261105/source/convex_partition_contract.py", "kernel_control_integer_geometry", "c06c37065561813a27791a4096d41c9e221f83ba48e775b2de6489f1f5a84a07")
    contract = load(base/"935-signed-partition-20261105/source/centroid_star_contract.py", "kernel_control_shared_domain", "0983f355f6983a3d5611144362871f404e969bd5f11e6ad7889a0fce35b054bb")
    oracle = load(base/"935-residual-source-admission-20261105/source/verify_partition_flips.py", "kernel_control_Fraction_planes", "beb8cde3ec10a526726c117c38e9cdc029c3eab6f325a80dfe32b61a1ea57301")
    worker = load(Path(__file__).with_name("kernel_point.py"), "kernel_control_proposer")
    nodes, old, reference = fixture()
    faces, centroid = contract.volume_centroid(nodes, old, geometry)
    assert centroid == (F(0), F(103, 144)+F(1, 1 << 26), F(0))
    old_geometry, volume, _ = oracle.fractions(nodes, old); assert volume == F(3, 4)
    centroid_nodes = np.vstack((nodes, list(map(float, centroid))))
    new = np.array([[len(nodes), *face] for face in faces], dtype=np.uint32)
    try:
        contract.certify(centroid_nodes, old, new, geometry)
    except AssertionError as error:
        assert str(error) == "Centroid is not strictly inside every cavity face"
    else:
        raise AssertionError("Outside-kernel volume centroid accepted")
    literal = np.vstack((nodes, reference)); literal_proof = contract.certify(literal, old, new, geometry)
    proposal = worker.propose(nodes, faces, geometry)
    assert proposal["strict_kernel_for_stored_point"]
    proposed_nodes = np.vstack((nodes, [float.fromhex(x) for x in proposal["point_hex"]]))
    proposed_proof = contract.certify(proposed_nodes, old, new, geometry)
    independent_pairs = []
    for coords in (literal, proposed_nodes):
        new_geometry, new_volume, cubes = oracle.fractions(coords, new)
        assert new_volume == volume and min(cubes) >= F.from_float(.01)**3
        planes = [oracle.witness(a, b) for group in (old_geometry, new_geometry) for a, b in combinations(group, 2)]
        assert len(planes) == 81; independent_pairs.append(len(planes))
    # Separate contradictory and zero-width halfspace controls require an
    # exact nonnegative dual bound, not a floating solver infeasibility flag.
    rows = [(F(1), F(0), F(0), F(1)), (F(-1), F(0), F(0), F(1)),
            (F(0), F(1), F(0), F(1)), (F(0), F(-1), F(0), F(1)),
            (F(0), F(0), F(1), F(1)), (F(0), F(0), F(-1), F(1))]
    for first, second, expected in ((0, -1, F(-1, 2)), (0, 0, F(0))):
        bounds = list(map(F, (first, second, 1, 1, 1, 1)))
        negative = worker.linear_proposal(rows, bounds)
        dual = negative["exact_dual"]; assert dual is not None
        upper = F(*map(int, dual["normalized_margin_upper_bound"]))
        assert upper == expected and dual["no_strict_kernel_proved"]
        try:
            worker.exact_dual(rows, bounds, [0])
        except AssertionError:
            pass
        else:
            raise AssertionError("Forged incomplete dual accepted")
    np.savez_compressed(output/"literal-kernel-reference.npz", source_nodes=nodes, old_cells=old,
                        reference_nodes=literal, reference_cells=new)
    result = {"source_sha256": sha(Path(__file__)), "kernel_source_sha256": sha(Path(__file__).with_name("kernel_point.py")),
              "literal_exact_volume": "3/4", "literal_exact_centroid_y": "103/144 + 2^-26",
              "centroid_outside_strict_kernel_refused": True, "literal_independent_reference_point": [0, "61/64", 0],
              "literal_reference_and_proposed_cone_exact_volume_domain_and_quality_passed": True,
              "independent_Fraction_plane_witnesses_per_candidate": independent_pairs,
              "negative_and_zero_width_exact_dual_bounds_passed": True, "forged_dual_refused": True,
              "reference_sha256": sha(output/"literal-kernel-reference.npz"),
              "literal_new_minimum_quality_approx": float(literal_proof["new_minimum_quality_cubed"])**(1/3),
              "proposed_new_minimum_quality_approx": float(proposed_proof["new_minimum_quality_cubed"])**(1/3),
              "proposal": proposal, "head_opened": False, "physics_admitted": False, "manufacturing_qualified": False}
    (output/"report.json").write_text(json.dumps(result, indent=2)+"\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True); parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(); args.output.mkdir(mode=0o700, exist_ok=False)
    signal.signal(signal.SIGALRM, signal.SIG_DFL); signal.alarm(60)
    print(json.dumps(run(args.repository, args.output)), flush=True); signal.alarm(0)


if __name__ == "__main__":
    main()
