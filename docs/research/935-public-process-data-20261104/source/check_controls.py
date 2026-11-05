"""Exercise proof polarity, rotation limits and forged source-witness refusals."""
import argparse
import itertools
import json
import shutil
from pathlib import Path

import numpy as np

from build_envelope_audit import screen
from verify_envelope_audit import sha, verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("method", type=Path)
    parser.add_argument("arrays", type=Path)
    parser.add_argument("accepted_trial", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    cube = np.array(list(itertools.product((0., 1.), repeat=3)))
    checks = {"unit_cube_not_excluded": not screen(cube, {"box": [1, 1, 1]}, 1e-6)[3]["box"]["rigid_placement_excluded_by_source_pair"]}
    segment = np.array([[0., 0., 0.], [2., 0., 0.]])
    checks["long_segment_excluded"] = screen(segment, {"box": [1, 1, 1]}, 1e-6)[3]["box"]["rigid_placement_excluded_by_source_pair"]
    rectangle = np.array([[0., 0., 0.], [140., 0., 0.], [140., 20., 0.], [0., 20., 0.]])
    result = screen(rectangle, {"box": [120, 120, 100]}, 1e-6)[3]["box"]
    checks["rotation_not_rejected_from_one_axis"] = not result["original_pose_spans_fit_nominal_box"] and not result["rigid_placement_excluded_by_source_pair"]
    rotation = np.array([[2 ** -.5, -2 ** -.5, 0.], [2 ** -.5, 2 ** -.5, 0.], [0., 0., 1.]])
    checks["known_diagonal_placement_has_contained_spans"] = bool(np.all(np.ptp(rectangle @ rotation.T, axis=0) < [120, 120, 100]))
    short = np.array([[0., 0., 0.], [1.5, 0., 0.]])
    result = screen(short, {"box": [1, 1, 1]}, 1e-6)[3]["box"]
    checks["necessary_pass_not_axis_fit"] = not result["rigid_placement_excluded_by_source_pair"] and not result["original_pose_spans_fit_nominal_box"] and not result["manufacturing_fit_accepted"]
    for kind in ("coordinates", "distance", "source_hash"):
        trial = args.output / kind
        shutil.copytree(args.accepted_trial, trial)
        aggregate = json.loads((trial / "aggregate.json").read_text())
        method_path = args.method
        if kind == "coordinates":
            path = trial / "private-witness.json"
            witness = json.loads(path.read_text())
            witness["source_coordinates_mm"][0][0] += 1
            path.write_text(json.dumps(witness))
            aggregate["private_witness_sha256"] = sha(path)
        elif kind == "distance":
            aggregate["witness_pair_distance_mm"] += 1
        else:
            method = json.loads(args.method.read_text())
            method["source_arrays_sha256"] = "0" * 64
            method_path = trial / "bad-method.json"
            method_path.write_text(json.dumps(method))
        (trial / "aggregate.json").write_text(json.dumps(aggregate))
        try:
            verify(method_path, args.arrays, trial)
        except ValueError as error:
            checks[f"forged_{kind}_refused"] = str(error)
        else:
            raise AssertionError(f"Forgery accepted: {kind}")
    if not all(checks.values()):
        raise AssertionError("Geometric control failed")
    (args.output / "controls.json").write_text(json.dumps(checks, indent=2) + "\n")
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()
