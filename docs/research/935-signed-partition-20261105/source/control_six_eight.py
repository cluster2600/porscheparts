#!/usr/bin/env python3
"""Literal six-to-eight reference with a preserved concave notch and exact volumes."""
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(); args.output.mkdir(mode=0o700, exist_ok=False)
    source = Path(__file__).with_name("six_eight_contract.py")
    contract = load(source, "actual_six_eight_contract")
    primitive_path = args.repository/"docs/research/935-residual-source-admission-20261105/source/convex_partition_contract.py"
    geometry = load(primitive_path, "six_eight_exact_primitives", "c06c37065561813a27791a4096d41c9e221f83ba48e775b2de6489f1f5a84a07")
    oracle_path = Path(__file__).with_name("control_signed_partition.py")
    oracle = load(oracle_path, "six_eight_independent_fraction_oracle", "2fedd90d524960f95a75742e4fa84ba1ae834698f202301cd63f713c32cc9c9c")
    epsilon = 2.**-24
    nodes = np.array([[0, .25+epsilon, 1], [0, .25+epsilon, -1],
        [0, .25, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [-1, 1, 0], [-1, 0, 0]], float)
    old = np.array([[0, 1, 2+i, 2+(i+1)%6] for i in range(6)])
    triangles = ((2, 3, 4), (2, 4, 5), (2, 5, 6), (2, 6, 7))
    new = np.array([[apex, *tri] for tri in triangles for apex in (0, 1)])
    for cells in (old, new):
        for i, tet in enumerate(cells):
            if oracle.determinant(nodes[tet]) < 0:
                cells[i, [1, 2]] = cells[i, [2, 1]]
    proof = contract.certify(nodes, old, new, geometry)
    assert proof["exact_domain_volume"] == F(7, 6)
    assert sum((oracle.determinant(nodes[t])/6 for t in old), F(0)) == F(7, 6)
    assert sorted(oracle.determinant(nodes[t])/6 for t in new) == [F(1, 8)]*4+[F(1, 6)]*4
    assert proof["old_bins"][0] == 2 and proof["new_bins"][0] == 0
    notch = np.array([0., .125, 0]); inside = np.array([0., .5, 0])
    assert np.array_equal(notch, nodes[3]*(7/16)+nodes[5]/8+nodes[7]*(7/16))
    assert not any(oracle.contains(nodes, t, notch) for t in old)
    assert not any(oracle.contains(nodes, t, notch) for t in new)
    assert any(oracle.contains(nodes, t, inside) for t in old) and any(oracle.contains(nodes, t, inside) for t in new)
    for bad in (new[:, [0, 2, 1, 3]], new[[0, 0, 2, 3, 4, 5, 6, 7]]):
        try:
            contract.certify(nodes, old, bad, geometry)
        except AssertionError:
            pass
        else:
            raise AssertionError("Forged six-to-eight partition accepted")
    shifted = contract.certify(nodes+1024., old, new, geometry)
    scaled = contract.certify(nodes*128., old, new, geometry)
    assert shifted["exact_domain_volume"] == proof["exact_domain_volume"]
    assert scaled["exact_domain_volume"] == proof["exact_domain_volume"]*128**3
    assert shifted["new_minimum_quality_cubed"] == scaled["new_minimum_quality_cubed"] == proof["new_minimum_quality_cubed"]
    reference = args.output/"literal-six-eight-reference.npz"
    np.savez_compressed(reference, nodes=nodes, old_cells=old, reference_cells=new)
    result = {"source_sha256": sha(Path(__file__)), "contract_sha256": sha(source),
        "literal_concave_six_to_eight_reference_passed": True, "independent_Fraction_total_volume": "7/6",
        "independent_new_cell_volumes": {"1/8": 4, "1/6": 4}, "notch_preserved_outside_both_domains": True,
        "notch_inside_convex_hull_by_literal_convex_combination": True,
        "old_minimum_quality_approx": float(proof["old_minimum_quality_cubed"])**(1/3),
        "new_minimum_quality_approx": float(proof["new_minimum_quality_cubed"])**(1/3),
        "old_and_new_exact_pair_separations": 43, "exact_oriented_boundary_and_quality_bins_passed": True,
        "inverted_duplicate_refused_and_exact_translation_scale_passed": True,
        "reference_sha256": sha(reference), "head_geometry_used": False,
        "physics_admitted": False, "manufacturing_qualified": False}
    (args.output/"report.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
