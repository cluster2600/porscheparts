#!/usr/bin/env python3
"""Region meshes for the dashboard-trim topology optimization (bionic.json).

    python bionic_regions.py

Input: parts/picogk-catalog/out/993-INT-DASHBOARD-TRIM-0001-SOLID.stl, the
closed outer body of the previous F0 trim: body/DashboardTrim.cs run with this
part's previous picogk.json and wall_mm = 35, front_lip_mm = 200,
rib_clearance_mm = 1000, voxel 0.75 mm (no shell, no ribs, open bottom not cut;
vents, vanes and instrument opening kept).
Writes closed STL tiles into parts/picogk-catalog/out/bionic-regions/<PART>/:
  inside-*.stl  : inside the outer body (where the inner ribs may grow);
  outside-*.stl : everything outside the body and 0.3 mm into it (a "void":
                  ribs never show through the skin, they end flush with it).
Tiled along the car width (10 tiles) so topopt.py's point-in-mesh test stays
fast. The skin (shaping.base_stl, ...-SKIN.stl) is the same generator with
the previous parameters and rib_clearance_mm = 1000 (no ribs).
"""
import json
from pathlib import Path

import numpy as np
import pyvista as pv
import trimesh

ROOT = Path(__file__).resolve().parents[3]
PART = "993-INT-DASHBOARD-TRIM-0001"
OUT = ROOT / "parts" / "picogk-catalog" / "out" / "bionic-regions" / PART
SOLID = ROOT / "parts" / "picogk-catalog" / "out" / f"{PART}-SOLID.stl"
H = 2.0


def closed(s):
    for target in (2000, 4000, 8000, 16000):
        d = s.decimate_pro(max(0.0, 1 - target / s.n_cells), preserve_topology=True) if s.n_cells > target else s
        c = trimesh.Trimesh(d.points, d.faces.reshape(-1, 4)[:, 1:], process=True)
        if c.is_watertight:
            return c
    c = trimesh.Trimesh(s.points, s.faces.reshape(-1, 4)[:, 1:], process=True)
    if not c.is_watertight:
        raise SystemExit("tile not watertight")
    return c


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tm = trimesh.load_mesh(SOLID, process=True)
    body = pv.PolyData(np.asarray(tm.vertices), np.hstack([np.full((len(tm.faces), 1), 3), tm.faces]).astype(np.int64))
    body = body.decimate_pro(1 - 250_000 / body.n_cells, preserve_topology=True)
    lo, hi = np.array([-680.0, -80.0, -8.0]), np.array([680.0, 66.0, 68.0])
    xs = np.linspace(lo[0], hi[0], 11)
    shapes = {"inside": [], "outside": []}
    for i in range(10):
        a = np.array([xs[i] - 1, lo[1], lo[2]])
        b = np.array([xs[i + 1] + 1, hi[1], hi[2]])
        g0 = a - 2 * H
        dims = np.ceil((b - a) / H).astype(int) + 5
        g = pv.ImageData(dimensions=tuple(int(d) for d in dims), spacing=(H, H, H), origin=tuple(g0))
        g = g.compute_implicit_distance(body)            # negative inside the body
        P = g.points
        box = np.max(np.stack([a[0] - P[:, 0], P[:, 0] - b[0], a[1] - P[:, 1], P[:, 1] - b[1],
                               a[2] - P[:, 2], P[:, 2] - b[2]]), axis=0)
        sd = g.point_data["implicit_distance"]
        for name, f in (("inside", np.maximum(sd, box)), ("outside", np.maximum(-(sd + 0.3), box))):
            if f.min() >= 0:
                continue
            g.point_data["f"] = f
            m = closed(g.contour([0.0], scalars="f").triangulate().clean())
            if m.volume < 0:
                m.invert()
            path = OUT / f"{name}-{i}.stl"
            m.export(path)
            note = ("inside the F0 outer body (rib design domain), one tile" if name == "inside"
                    else "outside the F0 outer body and 0.3 mm into it (ribs end flush with the skin), one tile")
            shapes[name].append({"type": "stl", "path": path.relative_to(ROOT).as_posix(), "basis": "assumption", "note": note})
    print(json.dumps(shapes, indent=1))


if __name__ == "__main__":
    main()
