"""Occupancy grid of the v2 loft body, on the lattice of the scan occupancy.

The simulation chain (sim_surface_mc.py, sim_thermal.py) starts from an
occupancy grid. For the scan-derived twin that grid is the winding number of
the open scan. This script writes the same kind of grid for the CAD body, so
the two can go through the identical chain and be compared: each voxel is 1
when its centre is inside the loft solid and 0 otherwise.

For every voxel-centre height the triangles that straddle the plane are cut
into segments, and each row of the slice is filled between pairs of segment
crossings (even-odd rule; the body is a closed manifold, so every row has an
even number of crossings). Heights are shifted by SLICE_SHIFT_MM so that no
cut falls exactly on a datum face. The grid volume is compared with the
solid's volume as a check.

Measured on 2026-11-10: slicing the 2.3 M-triangle body with Manifold took more
than ten minutes for the 560 levels, with or without eight processes (1.1 GB
each); this plane cut takes seconds in one process.

Usage: loft_occupancy.py PRIVATE_DIR BODY.npz OUT_DIR REPORT.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

SLICE_SHIFT_MM = 1.0e-4


def plane_segments(tri, z):
    """Segments (n, 2, 2) in XY where triangles (m, 3, 3) straddle the plane."""

    above = tri[:, :, 2] > z
    cut = tri[above.any(axis=1) & ~above.all(axis=1)]
    if not len(cut):
        return np.zeros((0, 2, 2))
    p, q = cut, np.roll(cut, -1, axis=1)
    crosses = (p[:, :, 2] > z) != (q[:, :, 2] > z)          # exactly two edges per triangle
    t = (z - p[:, :, 2]) / np.where(crosses, q[:, :, 2] - p[:, :, 2], 1.0)
    pts = p[:, :, :2] + t[:, :, None] * (q[:, :, :2] - p[:, :, :2])
    return pts[crosses].reshape(-1, 2, 2)


def fill(segments, shape, x0, y0, h):
    """Mask of pixel centres inside the closed curves made of these segments."""

    nx, ny = shape
    toggles = np.zeros((nx + 1, ny), dtype=np.int32)
    if len(segments):
        a = (segments[:, 0] - (x0, y0)) / h
        b = (segments[:, 1] - (x0, y0)) / h
        lo, hi = np.minimum(a[:, 1], b[:, 1]), np.maximum(a[:, 1], b[:, 1])
        j0, j1 = np.ceil(lo).astype(np.int64), np.ceil(hi).astype(np.int64)     # rows with lo <= j < hi
        count = np.clip(j1 - j0, 0, None)
        seg = np.repeat(np.arange(len(a)), count)
        j = np.repeat(j0, count) + (np.arange(count.sum()) - np.repeat(np.cumsum(count) - count, count))
        x = a[seg, 0] + (j - a[seg, 1]) / (b[seg, 1] - a[seg, 1]) * (b[seg, 0] - a[seg, 0])
        keep = (j >= 0) & (j < ny)
        np.add.at(toggles, (np.clip(np.ceil(x[keep]).astype(np.int64), 0, nx), j[keep]), 1)
    return (np.cumsum(toggles[:nx], axis=0) % 2).astype(bool)


def main(private, body_npz, out_dir, report):
    private, out_dir = Path(private), Path(out_dir)
    grid = json.loads((private / "occupancy-grid.json").read_text())
    d = np.load(body_npz)
    v, f = d["v"].astype(np.float64), d["f"]
    tri = v[f]
    signed = np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum() / 6.0
    order = np.argsort(tri[:, :, 2].min(axis=1))
    tri = tri[order]
    zmin, zmax = tri[:, :, 2].min(axis=1), tri[:, :, 2].max(axis=1)
    out_dir.mkdir(parents=True, exist_ok=True)
    nx, ny, nz = grid["shape"]
    h = grid["pitch_mm"]
    occ = np.lib.format.open_memmap(out_dir / "occupancy-wn.npy", mode="w+", dtype=np.float32, shape=(nx, ny, nz))
    filled = 0
    for k in range(nz):
        z = grid["z0"] + k * h + SLICE_SHIFT_MM
        cand = tri[:np.searchsorted(zmin, z, side="right")]
        mask = fill(plane_segments(cand[zmax[:len(cand)] > z], z), (nx, ny), grid["x0"], grid["y0"], h)
        occ[:, :, k] = mask
        filled += int(mask.sum())
    occ.flush()
    (out_dir / "occupancy-grid.json").write_text(json.dumps({**grid, "array": "occupancy-wn.npy"}, indent=2) + "\n")
    volume = filled * h ** 3
    rep = {"schema": "935-cad-twin-loft-occupancy/1", "pitch_mm": h, "shape": [nx, ny, nz],
           "voxels_inside": filled, "grid_volume_mm3": round(volume, 1),
           "solid_volume_mm3": round(float(signed), 1),
           "relative_difference": round(volume / float(signed) - 1.0, 6),
           "slice_shift_mm": SLICE_SHIFT_MM}
    Path(report).write_text(json.dumps(rep, indent=2) + "\n")
    print(json.dumps(rep))


if __name__ == "__main__":
    main(*sys.argv[1:5])
