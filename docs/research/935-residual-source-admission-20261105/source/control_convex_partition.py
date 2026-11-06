#!/usr/bin/env python3
"""Exercise the exact partition contract on a literal coplanar-facet reference."""
import argparse
from fractions import Fraction as F
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(); args.output.mkdir(mode=0o700, exist_ok=False)
    path = Path(__file__).with_name("convex_partition_contract.py")
    spec = importlib.util.spec_from_file_location("actual_partition_contract", path)
    contract = importlib.util.module_from_spec(spec); spec.loader.exec_module(contract)
    epsilon = 2.**-24
    nodes = np.array([[0, epsilon, 1], [0, epsilon, -1], [0, 0, 0], [1, 0, 0], [0, 1, 0], [-1, 0, 0]], float)
    old = np.array([[0, 1, 2, 3], [0, 1, 3, 4], [0, 1, 4, 5], [0, 1, 5, 2]])
    literal = np.array([[2, 4, 0, 3], [2, 4, 3, 1], [2, 4, 1, 5], [2, 4, 5, 0]])
    def orient(cells):
        points, _ = contract.exact_points(nodes, range(6))
        result = cells.copy()
        for i, tet in enumerate(cells):
            if contract.determinant([points[int(v)] for v in tet]) < 0:
                result[i, [1, 2]] = result[i, [2, 1]]
        return result
    old = orient(old); new = orient(literal)
    proof = contract.certify(nodes, old, new)
    assert proof["exact_domain_volume"] == F(2, 3)
    assert proof["hull_facets"] == 6 and proof["old_bins"][0] == 2 and proof["new_bins"][0] == 0
    # Independent Fraction determinant checks every literal new cell: 1/6 each.
    def det_fraction(xyz):
        p = [[F.from_float(float(x)) for x in row] for row in xyz]
        a, b, c = [[p[i][k]-p[0][k] for k in range(3)] for i in (1, 2, 3)]
        return a[0]*(b[1]*c[2]-b[2]*c[1])-a[1]*(b[0]*c[2]-b[2]*c[0])+a[2]*(b[0]*c[1]-b[1]*c[0])
    assert all(det_fraction(nodes[tet])/6 == F(1, 6) for tet in new)
    assert sum((det_fraction(nodes[tet])/6 for tet in old), F(0)) == F(2, 3)
    translated = contract.certify(nodes+1024., old, new)
    scaled = contract.certify(nodes*128., old, new)
    assert translated["exact_domain_volume"] == proof["exact_domain_volume"]
    assert translated["old_minimum_quality_cubed"] == proof["old_minimum_quality_cubed"]
    assert scaled["exact_domain_volume"] == proof["exact_domain_volume"]*128**3
    assert scaled["new_minimum_quality_cubed"] == proof["new_minimum_quality_cubed"]
    # Strict hull rejection is a proxy limitation, not an invalid source union.
    base = args.repository/"docs/research"
    exact_path = base/"935-unoptimized-volume-20261105/source/inspect_interval_volume.py"
    exact_spec = importlib.util.spec_from_file_location("control_partition_intervals", exact_path)
    exact = importlib.util.module_from_spec(exact_spec); exact_spec.loader.exec_module(exact)
    strict_path = base/"935-four-four-cavities-20261105/source/four_four_contract.py"
    strict_spec = importlib.util.spec_from_file_location("control_strict_proxy", strict_path)
    strict = importlib.util.module_from_spec(strict_spec); strict_spec.loader.exec_module(strict)
    admitted, _, coplanar = strict.strict_support(nodes, old[None], np.array([[0, 1]]), exact)
    assert not admitted[0] and coplanar > 0
    for bad in (new[:, [0, 2, 1, 3]], new[[0, 0, 2, 3]]):
        try:
            contract.certify(nodes, old, bad)
        except AssertionError:
            pass
        else:
            raise AssertionError("Forged partition accepted")
    concave = nodes.copy(); concave[:2, 1] = .5; concave[2, 1] = .25
    assert all(det_fraction(concave[t]) > 0 for t in old)
    try:
        contract.certify(concave, old, new)
    except AssertionError as error:
        assert "convex hull" in str(error)
    else:
        raise AssertionError("Nonconvex source union accepted")
    tetra = [(0, 0, 0), (2, 0, 0), (0, 2, 0), (0, 0, 2)]
    assert not contract.disjoint_interiors(tetra, tetra)
    assert contract.disjoint_interiors(tetra, [tuple(x+10 for x in p) for p in tetra])
    assert contract.disjoint_interiors(tetra, [(2, 0, 0), (3, 0, 0), (2, 1, 0), (2, 0, 1)])
    assert not contract.disjoint_interiors(tetra, [tuple(F(x)+F(1, 10) for x in p) for p in tetra])
    reference = args.output/"literal-reference.npz"
    np.savez_compressed(reference, nodes=nodes, old_cells=old, reference_cells=new)
    result = {"source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "contract_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "actual_contract_accepts_literal_coplanar_reference": True,
        "strict_proxy_refusal_reproduced": True, "independent_exact_reference_total_volume": "2/3",
        "independent_exact_each_new_volume": "1/6", "source_critical_cells": 2,
        "new_critical_cells": 0, "old_minimum_mean_ratio_approx": float(proof["old_minimum_quality_cubed"])**(1/3),
        "new_minimum_mean_ratio_approx": float(proof["new_minimum_quality_cubed"])**(1/3),
        "all_twelve_old_and_new_pair_separations_passed": True,
        "inverted_duplicate_and_nonconvex_positive_source_refused": True,
        "exact_translation_and_power_of_two_scale_controls": True,
        "SAT_overlap_separation_and_touch_controls": True,
        "reference_sha256": hashlib.sha256(reference.read_bytes()).hexdigest(),
        "head_geometry_used": False, "manufacturing_qualified": False}
    (args.output/"report.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
