"""Simulation surface by marching cubes on a coarsened occupancy field.

Block-averages the 0.25 mm winding-number grid by FACTOR (default 3, i.e.
0.75 mm) and extracts the w = 0.5 iso-surface. Marching cubes output cannot
self-intersect, so Gmsh can tetrahedralise it as given; decimating the fine
surface instead produced 357 self-intersecting faces (see README).

Usage: sim_surface_mc.py PRIVATE_DIR OUT.stl REPORT.json [FACTOR]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np


def main(private, out, report, factor="3"):
    import trimesh
    from skimage.measure import marching_cubes

    private, k = Path(private), int(factor)
    grid = json.loads((private / "occupancy-grid.json").read_text())
    wn = np.load(private / grid["array"], mmap_mode="r")
    sx, sy, sz = (s // k * k for s in wn.shape)
    w = np.asarray(wn[:sx, :sy, :sz], dtype=np.float32)
    w = w.reshape(sx // k, k, sy // k, k, sz // k, k).mean(axis=(1, 3, 5))
    h = grid["pitch_mm"] * k
    w = np.pad(w, 1, constant_values=0.0)
    v, f, _, _ = marching_cubes(w, level=0.5, spacing=(h, h, h), allow_degenerate=False)
    # Block centres sit at the mean of the k fine sample positions.
    v += np.array([grid["x0"], grid["y0"], grid["z0"]]) + grid["pitch_mm"] * (k - 1) / 2.0 - h
    m = trimesh.Trimesh(v, f, process=True)
    parts = sorted(m.split(only_watertight=False), key=lambda p: -abs(p.volume))
    body = parts[0]
    if body.volume < 0:
        body.invert()
    body.export(out)
    rep = {"pitch_mm": h, "triangles": int(len(body.faces)), "watertight": bool(body.is_watertight),
           "winding_consistent": bool(body.is_winding_consistent), "genus": int(round(1 - body.euler_number / 2)),
           "volume_mm3": round(float(body.volume), 1), "discarded_components": len(parts) - 1}
    Path(report).write_text(json.dumps(rep, indent=2) + "\n")
    print(json.dumps(rep))


if __name__ == "__main__":
    main(*sys.argv[1:5])
