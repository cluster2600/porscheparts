"""Read-only indexed counterpart of native.connectivity_metrics for large meshes.

Uses the sorted face-ownership/CSR pattern from audit_envelope_regions, without
normalising orientation or allocating a Python dictionary for every face.
Floating-point geometry and combinatorial incidence are not physical evidence.
"""
import math
import numpy as np


def connectivity_metrics(points, cells, triangles):
    points, cells, triangles = map(np.asarray, (points, cells, triangles))
    if (points.ndim != 2 or points.shape[1] != 3 or points.dtype.kind != 'f'
            or not 0 < len(points) <= 5_000_000 or not np.isfinite(points).all()
            or cells.ndim != 2 or cells.shape[1] != 4 or cells.dtype.kind not in 'iu'
            or not 0 < len(cells) <= 10_000_000
            or triangles.ndim != 2 or triangles.shape[1] != 3 or triangles.dtype.kind not in 'iu'
            or len(triangles) > 2_000_000
            or cells.min() < 0 or cells.max() >= len(points)
            or triangles.min(initial=0) < 0 or triangles.max(initial=0) >= len(points)):
        raise ValueError('bounded_finite_indexed_tetrahedra_and_triangles_required')
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components

    cells = cells.astype(np.uint32)
    triangles = triangles.astype(np.uint32)
    points = points.astype(np.float64, copy=False)
    volumes = np.empty(len(cells), dtype=np.float64)
    repeated = 0
    for start in range(0, len(cells), 100_000):
        batch = cells[start:start+100_000]
        repeated += int(np.any(np.diff(np.sort(batch, axis=1), axis=1) == 0, axis=1).sum())
        xyz = points[batch]
        x, y, z = (xyz[:, i]-xyz[:, 0] for i in (1, 2, 3))
        # Same arithmetic order as the independent scalar native witness.
        volumes[start:start+len(batch)] = (x[:, 0]*(y[:, 1]*z[:, 2]-y[:, 2]*z[:, 1])
            - x[:, 1]*(y[:, 0]*z[:, 2]-y[:, 2]*z[:, 0])
            + x[:, 2]*(y[:, 0]*z[:, 1]-y[:, 1]*z[:, 0]))/6
    if not np.isfinite(volumes).all():
        raise ValueError('nonfinite_tetra_volume')
    result = dict(signed_volume_sum=math.fsum(map(float, volumes)),
        absolute_volume_sum=math.fsum(abs(float(v)) for v in volumes),
        minimum_signed_tetra_volume=float(volumes.min()),
        count_negative=int((volumes < 0).sum()), count_zero=int((volumes == 0).sum()),
        repeated_node_tetrahedra=repeated)
    del volumes

    # ponytail: global O(N log N) face sort, capped at 10M cells; external sort
    # is the next step only if the measured memory cap rejects a larger mesh.
    faces = np.concatenate([np.sort(cells[:, ids], axis=1)
        for ids in ((1, 2, 3), (0, 3, 2), (0, 1, 3), (0, 2, 1))])
    owners = np.tile(np.arange(len(cells), dtype=np.uint32), 4)
    order = np.lexsort(faces.T[::-1])
    faces, owners = faces[order], owners[order]
    del order
    same = np.all(faces[1:] == faces[:-1], axis=1)
    starts = np.r_[0, np.flatnonzero(~same)+1]
    counts = np.diff(np.r_[starts, len(faces)])
    boundary = faces[starts[counts == 1]].copy()
    nonmanifold = int((counts > 2).sum())
    left, right = owners[:-1][same], owners[1:][same]
    del faces, owners, starts, counts, same
    graph = coo_matrix((np.ones(len(left), dtype=np.uint8), (left, right)),
        shape=(len(cells), len(cells))).tocsr()
    del left, right
    components = int(connected_components(graph, directed=False, return_labels=False))
    del graph
    stored = np.unique(np.sort(triangles, axis=1), axis=0)
    duplicates = len(triangles)-len(stored)
    common = len(boundary)+len(stored)-len(np.unique(np.vstack([boundary, stored]), axis=0))
    missing, extra = len(boundary)-common, len(stored)-common
    result.update(tetra_connected_components=components,
        boundary_missing_triangles=missing, stored_triangles_not_on_boundary=extra,
        duplicate_stored_triangles=duplicates, nonmanifold_faces=nonmanifold,
        boundary_triangle_count=len(boundary),
        boundary_matches=not (missing or extra or duplicates or nonmanifold))
    return result
