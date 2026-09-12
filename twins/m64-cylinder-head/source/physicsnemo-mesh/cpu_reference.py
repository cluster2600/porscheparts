#!/usr/bin/env python3
"""NumPy float64 surface reference; no geometry edits, scale or admission."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def reference(points, triangles):
    if points.dtype != np.float64 or points.ndim != 2 or points.shape[1] != 3:
        raise ValueError('points_float64_Nx3_required')
    if triangles.dtype != np.int64 or triangles.ndim != 2 or triangles.shape[1] != 3:
        raise ValueError('triangles_int64_Mx3_required')
    if not len(points) or not len(triangles) or not np.isfinite(points).all():
        raise ValueError('nonempty_finite_geometry_required')
    if triangles.min() < 0 or triangles.max() >= len(points):
        raise ValueError('index_out_of_range')
    xyz = points[triangles]
    cross = np.cross(xyz[:, 1] - xyz[:, 0], xyz[:, 2] - xyz[:, 0])
    twice_area = np.linalg.norm(cross, axis=1)
    normals = np.full_like(cross, np.nan)
    np.divide(cross, twice_area[:, None], out=normals, where=twice_area[:, None] > 0)
    origin = points.mean(axis=0)
    shifted = xyz - origin
    signed_volume = np.einsum('ij,ij->i', shifted[:, 0],
                             np.cross(shifted[:, 1], shifted[:, 2])) / 6.0
    return dict(areas=twice_area / 2.0, unit_normals=normals,
                signed_volume_contributions=signed_volume, volume_origin=origin)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mesh', type=Path, required=True)
    parser.add_argument('--sha', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    before = sha256(args.mesh)
    if before != args.sha:
        raise ValueError('input_sha_mismatch')
    with np.load(args.mesh, allow_pickle=False) as data:
        points, triangles = data['points'], data['triangles']
    started = time.perf_counter()
    arrays = reference(points, triangles)
    elapsed = time.perf_counter() - started
    args.output.mkdir(mode=0o700, exist_ok=False)
    target = args.output / 'cpu-reference.npz'
    np.savez(target, **arrays)
    unchanged = sha256(args.mesh) == before
    result = dict(schema='m64-private-numpy-surface-reference/v1',
                  input_sha256=before, source_sha256=sha256(__file__),
                  numpy_version=np.__version__, elapsed_seconds=elapsed,
                  execution='local_CPU_numpy_only', points=len(points), triangles=len(triangles),
                  area_sum_scan_units_squared=float(arrays['areas'].sum()),
                  signed_volume_sum_scan_units_cubed=float(arrays['signed_volume_contributions'].sum()),
                  zero_area_triangles=int(np.sum(arrays['areas'] == 0)),
                  nonfinite_normal_rows=int(np.sum(~np.isfinite(arrays['unit_normals']).all(axis=1))),
                  output_sha256=sha256(target), input_unchanged=unchanged,
                  normal_convention='oriented_cross_v1_minus_v0_v2_minus_v0_unit_length',
                  volume_convention='sum_det_about_saved_mean_point_origin_divided_by_6',
                  length_unit='scan_unit', absolute_scale_certified=False,
                  self_intersections_tested=False, CFD_authorized=False, manufacturing_authorized=False)
    (args.output / 'report.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    if not unchanged:
        raise ValueError('input_changed')
    print(json.dumps(result, allow_nan=False))


if __name__ == '__main__':
    main()
