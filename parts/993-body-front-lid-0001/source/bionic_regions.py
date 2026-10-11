#!/usr/bin/env python3
"""Region meshes for the front-lid topology optimization (bionic.json).

    python bionic_regions.py

Writes closed STL tiles into parts/picogk-catalog/out/bionic-regions/<PART>/
and prints the matching bionic.json shape entries:
  design-*.stl : slab 0.3 to 27 mm under the outer skin surface, 20 mm inside
                 the lid edge (where the inner frame may grow);
  above-*.stl  : everything from 0.3 mm under the outer skin surface upward
                 (a "void": the frame never prints through the skin).
The skin formulas are those of body/FrontLid.cs (F0 hypothesis, not measured).
The regions are tiled (6 x 6) so that topopt.py's point-in-mesh test only
sees the grid points of each small tile (one large mesh took ~9 min).

The skin itself (shaping.base_stl, 993-BODY-FRONT-LID-0001-SKIN.stl) is the
FrontLid.cs generator run with this part's picogk.json parameters of the
previous model and frame_inset_mm = 5000 (no frame, no ribs).
"""
import json
from pathlib import Path

import numpy as np
import pyvista as pv
import trimesh

ROOT = Path(__file__).resolve().parents[3]
PART = "993-BODY-FRONT-LID-0001"
OUT = ROOT / "parts" / "picogk-catalog" / "out" / "bionic-regions" / PART

W, L, R, D = 1250.0, 1100.0, 3000.0, 70.0
W2 = W / 2
wf = 0.72 * W2
y0, y1, nose = 0.12, 0.55, 70.0
zBase = np.sqrt(R * R - W2 * W2)
INSET, DEPTH, TOP = 20.0, 27.0, 0.3


def smooth(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def F(x, y):
    return np.sqrt(np.maximum(R * R - x * x, 0)) - zBase - D * (1 - y / L) ** 2


def plan(x, y):
    wy = wf + (W2 - wf) * smooth((y / L - y0) / (y1 - y0))
    return np.maximum(np.maximum(np.abs(x) - wy, nose * (x / wf) ** 2 - y), y - L)


def design(X, Y, Z):
    return np.maximum(plan(X, Y) + INSET, np.maximum(Z - (F(X, Y) - TOP), (F(X, Y) - DEPTH) - Z))


def above(X, Y, Z):
    return np.maximum(plan(X, Y) - 40.0, np.maximum((F(X, Y) - TOP) - Z, Z - (F(X, Y) + 30.0)))


def tiles(field, lo, hi, n, h, name, note, decimate=True, overlap=1.0):
    """Closed meshes of {field <= 0} cut into n x n tiles (overlapping)."""
    xs, ys = np.linspace(lo[0], hi[0], n + 1), np.linspace(lo[1], hi[1], n + 1)
    shapes = []
    for i in range(n):
        for j in range(n):
            a = np.array([xs[i] - overlap, ys[j] - overlap, lo[2]])
            b = np.array([xs[i + 1] + overlap, ys[j + 1] + overlap, hi[2]])
            g0 = np.floor((a - 2 * h) / h) * h          # one global lattice: neighbouring tiles agree exactly
            dims = np.ceil((b - a) / h).astype(int) + 5
            ax = [g0[k] + h * np.arange(dims[k]) for k in range(3)]
            X, Y, Z = np.meshgrid(*ax, indexing="ij")
            box = np.max(np.stack([a[0] - X, X - b[0], a[1] - Y, Y - b[1], a[2] - Z, Z - b[2]]), axis=0)
            f = np.maximum(field(X, Y, Z), box)
            if f.min() >= 0:
                continue
            g = pv.ImageData(dimensions=tuple(int(d) for d in dims), spacing=(h, h, h), origin=tuple(g0))
            g.point_data["f"] = f.ravel(order="F")
            s = g.contour([0.0], scalars="f").triangulate().clean()
            m = None
            for target in ((1500, 3000, 6000) if decimate else ()):   # few triangles: topopt's ray test is O(points x triangles)
                d = s.decimate_pro(max(0.0, 1 - target / s.n_cells), preserve_topology=True) if s.n_cells > target else s
                c = trimesh.Trimesh(d.points, d.faces.reshape(-1, 4)[:, 1:], process=True)
                if c.is_watertight:
                    m = c
                    break
            if m is None:
                m = trimesh.Trimesh(s.points, s.faces.reshape(-1, 4)[:, 1:], process=True)
            if not m.is_watertight:
                raise SystemExit(f"{name} tile {i},{j} not watertight")
            if m.volume < 0:
                m.invert()
            path = OUT / f"{name}-{i}{j}.stl"
            m.export(path)
            shapes.append({"type": "stl", "path": path.relative_to(ROOT).as_posix(), "basis": "assumption", "note": note})
    return shapes


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    d = tiles(design, (-W2, 0, -80), (W2, L, 75), 6, 3.0, "design",
              "frame slab under the skin (0.3 to 27 mm deep, 20 mm inside the edge), one tile")
    v = tiles(above, (-W2 - 45, -45, -100), (W2 + 45, L + 45, 105), 6, 6.0, "above",
              "space from 0.3 mm under the outer skin surface upward, one tile", decimate=False, overlap=12.0)
    print(json.dumps({"design": d, "void": v}, indent=1))
