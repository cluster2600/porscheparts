#!/usr/bin/env python3
"""Actual cavity-centroid cone control, with an independently known centroid."""
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
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repository", "reference", "output"):
        parser.add_argument("--"+name, type=Path, required=True)
    args = parser.parse_args(); args.output.mkdir(mode=0o700, exist_ok=False)
    contract_path = Path(__file__).with_name("centroid_star_contract.py")
    contract = load(contract_path, "actual_centroid_star_contract")
    geometry = load(args.repository/"docs/research/935-residual-source-admission-20261105/source/convex_partition_contract.py", "centroid_exact_primitives", "c06c37065561813a27791a4096d41c9e221f83ba48e775b2de6489f1f5a84a07")
    oracle = load(Path(__file__).with_name("control_signed_partition.py"), "centroid_independent_fraction_oracle", "2fedd90d524960f95a75742e4fa84ba1ae834698f202301cd63f713c32cc9c9c")
    assert sha(args.reference) == "490a8b78c0d1063138c506d3a22171dc3367b387d180a16b3215f20b5646b0c9"
    with np.load(args.reference, allow_pickle=False) as data:
        nodes, old = data["nodes"], data["old_cells"]
    faces, ideal = contract.volume_centroid(nodes, old, geometry)
    # Polygon centroid is47/84; each pyramid centroid is3/4 base+1/4 apex.
    expected = (F(0), F(27, 56)+F(1, 4*(1 << 24)), F(0))
    assert ideal == expected and len(faces) == 12
    actual = np.array([float(x) for x in ideal]); augmented = np.vstack((nodes, actual))
    new = np.array([[len(nodes), *face] for face in faces])
    proof = contract.certify(augmented, old, new, geometry)
    assert proof["exact_domain_volume"] == F(7, 6)
    assert sum((oracle.determinant(augmented[t])/6 for t in new), F(0)) == F(7, 6)
    assert proof["old_bins"][0] == 2 and proof["new_bins"][0] == 0
    notch = np.array([0., .125, 0])
    assert not any(oracle.contains(augmented, t, notch) for t in new)
    error = max(abs(F.from_float(float(x))-v) for x, v in zip(actual, ideal))
    assert all(abs(F.from_float(float(x))-v) <= F.from_float(float(np.spacing(abs(x))))/2 for x, v in zip(actual, ideal) if x != 0)
    outside = augmented.copy(); outside[-1] = notch
    try:
        contract.certify(outside, old, new, geometry)
    except AssertionError as failure:
        assert "strictly inside" in str(failure)
    else:
        raise AssertionError("Outside kernel point accepted")
    thin = nodes.copy(); thin[:, 0] *= 2.**-30
    try:
        contract.source_admission(thin, old, geometry)
    except AssertionError as failure:
        assert "Fixed cavity faces" in str(failure)
    else:
        raise AssertionError("Inadmissible fixed-face shape accepted")
    try:
        contract.source_admission(augmented, new, geometry)
    except AssertionError as failure:
        assert "interior numerical nodes" in str(failure)
    else:
        raise AssertionError("Unsupported interior-node retention policy bypassed")
    reference = args.output/"literal-centroid-star-reference.npz"
    np.savez_compressed(reference, source_nodes=nodes, old_cells=old, augmented_nodes=augmented, reference_cells=new)
    result = {"source_sha256": sha(Path(__file__)), "contract_sha256": sha(contract_path),
        "actual_volume_centroid_and_cone_path_passed": True, "independent_ideal_centroid_y": "27/56+2^-26",
        "independent_Fraction_domain_volume": "7/6", "old_cells": 6, "new_cells": 12,
        "new_numerical_interior_nodes": 1, "old_and_new_pair_separations": 81,
        "exact_complete_boundary_and_all_old_points_preserved": True, "concave_notch_preserved": True,
        "old_minimum_quality_approx": float(proof["old_minimum_quality_cubed"])**(1/3),
        "new_minimum_quality_approx": float(proof["new_minimum_quality_cubed"])**(1/3),
        "stored_centroid_rounding_error_approx": float(error), "rounding_at_most_half_ulp": True,
        "outside_kernel_and_forced_face_and_unsupported_interior_node_controls_refused": True,
        "reference_sha256": sha(reference), "head_geometry_used": False,
        "physics_admitted": False, "manufacturing_qualified": False}
    (args.output/"report.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
