"""Write a private source-pair witness and aggregate nominal-box screen."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np


def digest(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def screen(points, boxes, margin):
    extremes = np.unique(np.r_[np.argmin(points, axis=0), np.argmax(points, axis=0)])
    pairs = list(itertools.combinations(extremes.tolist(), 2))
    if not pairs:
        raise ValueError("At least two distinct extreme vertices required")
    pair = max(pairs, key=lambda p: float(np.linalg.norm(points[p[1]] - points[p[0]])))
    distance = float(np.linalg.norm(points[pair[1]] - points[pair[0]]))
    spans = np.ptp(points, axis=0)
    results = {}
    for name, dims in boxes.items():
        dims = np.asarray(dims, dtype=float)
        diagonal = float(np.linalg.norm(dims))
        results[name] = {
            "nominal_box_mm": dims.tolist(),
            "box_diagonal_mm": diagonal,
            "rigid_placement_excluded_by_source_pair": distance > diagonal + margin,
            "original_pose_spans_fit_nominal_box": bool(np.all(spans <= dims)),
            "manufacturing_fit_accepted": False,
        }
    return pair, distance, spans, results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("method", type=Path)
    parser.add_argument("arrays", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    method = json.loads(args.method.read_text())
    if digest(args.arrays) != method["source_arrays_sha256"]:
        raise ValueError("Source arrays hash mismatch")
    with np.load(args.arrays, allow_pickle=False) as data:
        vertices, faces = data["vertices"], data["triangles"]
    if not np.isfinite(vertices).all() or faces.min() < 0 or faces.max() >= len(vertices):
        raise ValueError("Invalid source arrays")
    triangles = vertices[faces]
    area2 = np.linalg.norm(np.cross(triangles[:, 1] - triangles[:, 0],
                                  triangles[:, 2] - triangles[:, 0]), axis=1)
    ids = np.unique(faces[area2 > 0])
    pair, distance, spans, boxes = screen(vertices[ids], method["boxes"],
                                         method["floating_point_margin_mm"])
    witness_ids = ids[list(pair)]
    args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    private = {"source_vertex_ids": witness_ids.tolist(),
               "source_coordinates_mm": vertices[witness_ids].tolist()}
    (args.output / "private-witness.json").write_text(json.dumps(private, indent=2) + "\n")
    public = {
        "schema_version": 1,
        "source_arrays_sha256": digest(args.arrays),
        "method_sha256": digest(args.method),
        "private_witness_sha256": digest(args.output / "private-witness.json"),
        "source_vertices": len(vertices), "source_triangles": len(faces),
        "zero_area_triangles_excluded_from_metric_only": int(np.count_nonzero(area2 == 0)),
        "metric_vertex_count": len(ids),
        "source_spans_mm": spans.tolist(),
        "witness_pair_distance_mm": distance,
        "boxes": boxes,
        "complete_head_accepted": False,
        "manufacturing_authorized": False,
    }
    (args.output / "aggregate.json").write_text(json.dumps(public, indent=2) + "\n")
    print(json.dumps(public))


if __name__ == "__main__":
    main()
