#!/usr/bin/env python3
"""Improve interior tetrahedron stars with constrained, exactly checked proposals."""
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
import scipy
from scipy.optimize import linprog

from import_conforming_volume import exact_orientation


def quality(points):
    u, v, w = (points[:, j] - points[:, 0] for j in (1, 2, 3))
    determinant = np.einsum('ij,ij->i', u, np.cross(v, w))
    if not np.isfinite(determinant).all() or np.any(determinant <= 0):
        return None
    lengths = sum(((points[:, i] - points[:, j]) ** 2).sum(axis=1)
                  for i, j in ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)))
    return 12 * (determinant / 2) ** (2 / 3) / lengths


def kernel_target(vertices, cells, node):
    points = vertices[cells]
    positions = cells == node
    if not np.all(positions.sum(axis=1) == 1):
        raise ValueError('One movable vertex per incident tetrahedron required')
    u, v, w = (points[:, j] - points[:, 0] for j in (1, 2, 3))
    g1, g2, g3 = np.cross(v, w), np.cross(w, u), np.cross(u, v)
    gradient = np.stack((-(g1 + g2 + g3), g1, g2, g3), axis=1)[np.arange(len(cells)), positions.argmax(axis=1)]
    length = np.linalg.norm(gradient, axis=1)
    determinant = np.einsum('ij,ij->i', u, np.cross(v, w))
    if np.any(length <= 0) or np.any(determinant <= 0):
        raise ValueError('Positive initial star required')
    # Solve in displacement coordinates to avoid cancellation at the scan origin.
    planes = gradient / length[:, None]
    low = points.reshape(-1, 3).min(axis=0) - vertices[node]
    high = points.reshape(-1, 3).max(axis=0) - vertices[node]
    result = linprog([0., 0, 0, -1], A_ub=np.column_stack((-planes, np.ones(len(cells)))),
                     b_ub=determinant / length,
                     bounds=[*zip(low, high), (0, None)], method='highs')
    if not result.success or not np.isfinite(result.x).all():
        return None
    return vertices[node] + result.x[:3]


def optimize(vertices, cells, boundary):
    original = vertices.copy()
    vertices = vertices.copy()
    fixed = np.zeros(len(vertices), dtype=bool); fixed[np.unique(boundary)] = True
    rows, columns = np.where(~fixed[cells])
    nodes = cells[rows, columns]
    stars = {int(node): np.unique(rows[nodes == node]) for node in np.unique(nodes)}
    accepted = []
    for sweep in range(3):
        moves = 0
        for node, incident in stars.items():
            local_cells = cells[incident]
            target = kernel_target(vertices, local_cells, node)
            if target is None:
                continue
            points = vertices[local_cells]
            old_quality = quality(points)
            if old_quality is None:
                raise ValueError('Positive current star required')
            before = float(old_quality.min()); best = before; chosen = None
            positions = (local_cells == node).argmax(axis=1)
            for exponent in range(16):
                proposal = vertices[node] + (target - vertices[node]) / 2 ** exponent
                trial = points.copy(); trial[np.arange(len(trial)), positions] = proposal
                values = quality(trial)
                if values is not None and float(values.min()) > best * (1 + 1e-8):
                    best = float(values.min()); chosen = proposal
            if chosen is None:
                continue
            used = np.unique(local_cells); local_vertices = vertices[used].copy()
            local_vertices[np.searchsorted(used, node)] = chosen
            exact = exact_orientation(local_vertices, np.searchsorted(used, local_cells))
            if exact['negative'] or exact['zero']:
                continue
            vertices[node] = chosen; moves += 1
            accepted.append(dict(sweep=sweep + 1, node_zero_based=node,
                                 minimum_star_quality_before=before, minimum_star_quality_after=best))
        if not moves:
            break
    if not np.array_equal(vertices[fixed], original[fixed]):
        raise ValueError('Boundary changed during star optimization')
    return vertices, accepted


def run(folder):
    folder = Path(folder); inp = folder / 'input.npz'
    if (folder / 'assessment.json').exists() or (folder / 'volume.npz').exists():
        raise ValueError('Fresh private optimizer output required')
    with np.load(inp, allow_pickle=False) as data:
        v, c, f = (data[key] for key in ('vertices', 'tetrahedra', 'boundary'))
    if (v.ndim != 2 or v.shape[1] != 3 or c.ndim != 2 or c.shape[1] != 4 or f.ndim != 2 or f.shape[1] != 3
            or not np.isfinite(v).all() or c.min() < 0 or c.max() >= len(v) or f.min() < 0 or f.max() >= len(v)):
        raise ValueError('Finite indexed linear volume required')
    start = time.monotonic(); xyz, accepted = optimize(v, c, f)
    np.savez_compressed(folder / 'volume.npz', vertices=xyz, tetrahedra=c, boundary=f)
    sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
    report = dict(status='interior_relocated_not_audited', optimizer='StarKernelLinearProgram',
                  source_sha256=sha(__file__), input_sha256=sha(inp), volume_npz_sha256=sha(folder / 'volume.npz'),
                  numpy_version=np.__version__, scipy_version=scipy.__version__, accepted_moves=accepted,
                  boundary_coordinates_exactly_preserved=True, connectivity_exactly_preserved=True,
                  moved_nodes=int(np.any(xyz != v, axis=1).sum()),
                  maximum_interior_shift_native_units=float(np.linalg.norm(xyz - v, axis=1).max()),
                  vertices=len(v), tetrahedra=len(c), boundary_triangles=len(f), elapsed_s=time.monotonic() - start,
                  mechanical_mesh_admitted=False, manufacturing_authorized=False)
    (folder / 'assessment.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'accepted_moves'}), flush=True)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: optimize_interior_stars.py PRIVATE_INPUT_FOLDER')
    run(sys.argv[1])
