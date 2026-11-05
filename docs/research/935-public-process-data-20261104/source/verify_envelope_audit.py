"""Independently check an actual original-vertex witness, without pair search."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np


def sha(path):
    result = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def verify(method_path, arrays_path, directory):
    method = json.loads(method_path.read_text())
    aggregate = json.loads((directory / "aggregate.json").read_text())
    witness_path = directory / "private-witness.json"
    witness = json.loads(witness_path.read_text())
    if sha(arrays_path) != method["source_arrays_sha256"]:
        raise ValueError("Source hash mismatch")
    if aggregate["method_sha256"] != sha(method_path):
        raise ValueError("Method hash mismatch")
    if aggregate["private_witness_sha256"] != sha(witness_path):
        raise ValueError("Witness hash mismatch")
    with np.load(arrays_path, allow_pickle=False) as data:
        vertices, faces = data["vertices"], data["triangles"]
    ids = witness["source_vertex_ids"]
    if len(ids) != 2 or ids[0] == ids[1] or any(type(i) is not int or i < 0 or i >= len(vertices) for i in ids):
        raise ValueError("Invalid original vertex IDs")
    points = vertices[ids]
    if not np.array_equal(points, np.asarray(witness["source_coordinates_mm"])):
        raise ValueError("Witness coordinates differ from original vertices")
    for vertex_id in ids:
        incident = faces[np.any(faces == vertex_id, axis=1)]
        if not any(np.linalg.norm(np.cross(vertices[f[1]] - vertices[f[0]],
                                           vertices[f[2]] - vertices[f[0]])) > 0 for f in incident):
            raise ValueError("Witness not on a nondegenerate source triangle")
    distance = math.dist(points[0], points[1])
    if not math.isclose(distance, aggregate["witness_pair_distance_mm"], abs_tol=1e-10, rel_tol=0):
        raise ValueError("Pair distance mismatch")
    checks = {}
    for name, dims in method["boxes"].items():
        diagonal = math.sqrt(sum(x * x for x in dims))
        excluded = distance > diagonal + method["floating_point_margin_mm"]
        recorded = aggregate["boxes"][name]
        if (recorded["nominal_box_mm"] != dims or
                not math.isclose(diagonal, recorded["box_diagonal_mm"], abs_tol=1e-10, rel_tol=0) or
                excluded != recorded["rigid_placement_excluded_by_source_pair"] or
                recorded["manufacturing_fit_accepted"] is not False):
            raise ValueError("Nominal-box proof mismatch")
        checks[name] = True
    return {"original_vertex_membership": True, "coordinates_exact": True,
            "source_pair_distance": True, "box_proofs": checks,
            "verified_scope": "source-pair exclusion only; not producer ranking or full bounding spans",
            "manufacturing_authorized": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("method", type=Path)
    parser.add_argument("arrays", type=Path)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.method, args.arrays, args.directory), indent=2))
