"""Measure oriented mesh creases before interpreting a mechanical mesh sweep.

These floating-point diagnostics identify candidates for upstream inspection;
they neither prove continuum singularities nor establish measured interfaces.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def audit(vertices, faces):
    vertices = np.asarray(vertices, dtype=np.float64)
    faces = np.asarray(faces, dtype=np.int64)
    if (vertices.ndim != 2 or vertices.shape[1] != 3
            or faces.ndim != 2 or faces.shape[1] != 3 or not len(faces)
            or not np.isfinite(vertices).all() or faces.min() < 0
            or faces.max() >= len(vertices)):
        raise ValueError('Finite indexed triangles required')
    triangles = vertices[faces]
    normals = np.cross(triangles[:, 1] - triangles[:, 0],
                       triangles[:, 2] - triangles[:, 0])
    norm = np.linalg.norm(normals, axis=1)
    if np.any(norm == 0):
        raise ValueError('Degenerate face')
    normals /= norm[:, None]
    directed = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]],
                               faces[:, [2, 0]]])
    keys = np.sort(directed, axis=1)
    order = np.lexsort((keys[:, 1], keys[:, 0]))
    keys = keys[order]
    starts = np.r_[0, np.flatnonzero(np.any(keys[1:] != keys[:-1], axis=1)) + 1,
                   len(keys)]
    if np.any(np.diff(starts) != 2):
        raise ValueError('Every edge must have exactly two incident faces')
    pairs = order.reshape(-1, 2)
    edge = directed[pairs[:, 0]]
    if not np.array_equal(edge, directed[pairs[:, 1]][:, ::-1]):
        raise ValueError('Opposite incident-face edge orientation required')
    first, second = normals[pairs[:, 0] % len(faces)], normals[pairs[:, 1] % len(faces)]
    delta = vertices[edge[:, 1]] - vertices[edge[:, 0]]
    length = np.linalg.norm(delta, axis=1)
    sine = np.einsum('ij,ij->i', delta / length[:, None], np.cross(first, second))
    cosine = np.einsum('ij,ij->i', first, second)
    angle = np.degrees(np.arctan2(sine, cosine))
    worst = np.argsort(angle)[:12]
    return {
        'vertices': len(vertices), 'faces': len(faces), 'edges': len(edge),
        'closed_oppositely_oriented_edges': True,
        'edge_length_percentiles_mm': {str(q): float(np.percentile(length, q))
                                      for q in [0, .001, .01, .1, 1, 50, 100]},
        'edges_below_mm': {str(x): int(np.count_nonzero(length < x))
                           for x in [.001, .01, .05, .1]},
        'reentrant_edges_above_degrees': {
            str(x): int(np.count_nonzero(angle < -x)) for x in [1, 5, 15, 30, 45, 60, 90]},
        'convex_edges_above_45_degrees': int(np.count_nonzero(angle > 45)),
        'most_reentrant_edges': [
            {'vertices': edge[i].tolist(), 'normal_turn_degrees': float(angle[i]),
             'midpoint_mm': vertices[edge[i]].mean(axis=0).tolist(),
             'length_mm': float(length[i])} for i in worst],
        'sign_convention': 'Negative normal turn is reentrant for an outward-oriented shell',
        'singularity_proved': False, 'mechanical_admissibility_established': False,
        'scope': 'Mesh-crease diagnostic; inspect CAD intent, corner radius and loads before stress interpretation',
    }


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    digest = hashlib.sha256(args.input.read_bytes()).hexdigest()
    if digest != args.sha256 or args.output.exists():
        raise ValueError('Matching frozen input and fresh output required')
    with np.load(args.input, allow_pickle=False) as data:
        result = audit(data['vertices'], data['triangles'])
    result.update(input_sha256=digest,
                  source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  numpy_version=np.__version__, manufacturing_authorized=False)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'most_reentrant_edges'}))


if __name__ == '__main__':
    main()
