#!/usr/bin/env python3
"""Actual signed-partition contract on a dimensioned concave literal reference."""
import argparse
from fractions import Fraction as F
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path, name, expected=None):
    if expected is not None:
        assert sha(path) == expected
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec); spec.loader.exec_module(obj)
    return obj


def determinant(xyz):
    p = [[F.from_float(float(x)) for x in row] for row in xyz]
    a, b, c = [[p[i][j]-p[0][j] for j in range(3)] for i in (1, 2, 3)]
    return a[0]*(b[1]*c[2]-b[2]*c[1])-a[1]*(b[0]*c[2]-b[2]*c[0])+a[2]*(b[0]*c[1]-b[1]*c[0])


def contains(nodes, tet, point):
    xyz = nodes[tet].copy(); d = determinant(xyz); assert d > 0
    for i in range(4):
        changed = xyz.copy(); changed[i] = point
        if determinant(changed) < 0:
            return False
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(); args.output.mkdir(mode=0o700, exist_ok=False)
    source = Path(__file__).with_name("signed_partition_contract.py")
    contract = load(source, "actual_signed_domain_contract")
    primitive_path = args.repository/"docs/research/935-residual-source-admission-20261105/source/convex_partition_contract.py"
    geometry = load(primitive_path, "frozen_signed_domain_predicates", "c06c37065561813a27791a4096d41c9e221f83ba48e775b2de6489f1f5a84a07")
    epsilon = 2.**-24
    nodes = np.array([[0, .25+epsilon, 1], [0, .25+epsilon, -1], [0, .25, 0], [1, 0, 0], [0, 1, 0], [-1, 0, 0]], float)
    old = np.array([[0, 1, 2, 3], [0, 1, 3, 4], [0, 1, 4, 5], [0, 1, 5, 2]])
    new = np.array([[2, 4, 0, 3], [2, 4, 3, 1], [2, 4, 1, 5], [2, 4, 5, 0]])
    for cells in (old, new):
        for i, tet in enumerate(cells):
            if determinant(nodes[tet]) < 0:
                cells[i, [1, 2]] = cells[i, [2, 1]]
    proof = contract.certify(nodes, old, new, geometry)
    assert proof["exact_domain_volume"] == F(1, 2)
    assert sum((determinant(nodes[t])/6 for t in old), F(0)) == F(1, 2)
    assert all(determinant(nodes[t])/6 == F(1, 8) for t in new)
    assert proof["old_bins"][0] == 2 and proof["new_bins"][0] == 0
    try:
        geometry.certify(nodes, old, new)
    except AssertionError as error:
        assert "convex hull" in str(error)
    else:
        raise AssertionError("Concave source unexpectedly covers its convex hull")
    notch = np.array([0., .125, 0]); inside = np.array([0., .5, 0])
    assert not any(contains(nodes, tet, notch) for tet in old)
    assert not any(contains(nodes, tet, notch) for tet in new)
    assert any(contains(nodes, tet, inside) for tet in old) and any(contains(nodes, tet, inside) for tet in new)
    count = 0
    for x in (-.75, -.25, .25, .75):
        for y in (.125, .375, .625, .875):
            for z in (-.75, -.25, .25, .75):
                point = np.array([x, y, z])
                assert any(contains(nodes, tet, point) for tet in old) == any(contains(nodes, tet, point) for tet in new)
                count += 1
    for bad in (new[:, [0, 2, 1, 3]], new[[0, 0, 2, 3]]):
        try:
            contract.certify(nodes, old, bad, geometry)
        except AssertionError:
            pass
        else:
            raise AssertionError("Forged partition accepted")
    shifted = contract.certify(nodes+1024., old, new, geometry)
    scaled = contract.certify(nodes*128., old, new, geometry)
    assert shifted["exact_domain_volume"] == proof["exact_domain_volume"]
    assert shifted["new_minimum_quality_cubed"] == proof["new_minimum_quality_cubed"]
    assert scaled["exact_domain_volume"] == proof["exact_domain_volume"]*128**3
    assert scaled["old_minimum_quality_cubed"] == proof["old_minimum_quality_cubed"]
    reference = args.output/"literal-concave-reference.npz"
    np.savez_compressed(reference, nodes=nodes, old_cells=old, reference_cells=new)
    result = {"source_sha256": sha(Path(__file__)), "contract_sha256": sha(source),
        "primitive_sha256": sha(primitive_path), "literal_concave_reference_passed": True,
        "independent_Fraction_total_volume": "1/2", "independent_each_new_volume": "1/8",
        "old_convex_hull_proxy_refusal_reproduced": True,
        "notch_preserved_by_both_domains": True, "independent_barycentric_control_points": count+2,
        "point_sampling_is_a_control_not_the_domain_proof": True,
        "all_twelve_pair_separations_and_oriented_chain_identity_passed": True,
        "old_minimum_quality_approx": float(proof["old_minimum_quality_cubed"])**(1/3),
        "new_minimum_quality_approx": float(proof["new_minimum_quality_cubed"])**(1/3),
        "inverted_and_duplicate_refused": True, "exact_translation_and_power2_scale_passed": True,
        "reference_sha256": sha(reference), "head_geometry_used": False,
        "physics_admitted": False, "manufacturing_qualified": False}
    (args.output/"report.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
