#!/usr/bin/env python3
"""Exact keep-in body of the bionic switch blank (closed STL).

    python bionic_keepins.py

Writes source/bionic-keepins/face_clips.stl (and face_clips_topo.stl, 20k
triangles for topopt.py), referenced by source/bionic.json:
the pillow-crowned face plate with rolled edges, a short locating skirt that
sits in the dashboard opening (from the face down through the panel), and
the two snap tongues with their lead-in barbs - the same fields as the F0
PicoGK generator parts/picogk-catalog/trim/SwitchBlank.cs, edges rounded by
a distance-transform opening, meshed by VTK. Everything between face and
tongues is left to the topology optimization.
Insertion axis Z, back at z = 0, values of source/picogk.json.
"""
import json
from pathlib import Path

import numpy as np
import pyvista as pv
import trimesh
from scipy.ndimage import distance_transform_edt

HERE = Path(__file__).resolve().parent
OUT = HERE / "bionic-keepins"
P = {k: v["value"] for k, v in json.loads((HERE / "picogk.json").read_text(encoding="utf-8"))["parameters"].items()}
FW, FH, FT = P["face_width_mm"] / 2, P["face_height_mm"] / 2, P["face_thickness_mm"]
FR, ER, CROWN = P["face_corner_radius_mm"], P["face_edge_radius_mm"], P["face_crown_mm"]
BX, BY = P["opening_width_mm"] / 2 - P["body_clearance_mm"], P["opening_height_mm"] / 2 - P["body_clearance_mm"]
Z0 = P["tab_length_mm"]
Z1 = Z0 + FT
WALL, BR = P["tab_thickness_mm"], P["body_corner_radius_mm"]
CLIP_W, BARB, PANEL, BARB_L = P["clip_width_mm"] / 2, P["clip_barb_mm"], P["panel_thickness_mm"], P["clip_barb_length_mm"]
SKIRT_DEPTH = PANEL + 1.0          # locating skirt: through the panel plus 1 mm
STEP = 0.15


def round_rect(x, y, hx, hy, r):
    r = np.minimum(r, np.minimum(hx, hy))
    qx, qy = np.abs(x) - hx + r, np.abs(y) - hy + r
    return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r


def build():
    pad = 0.6
    xs = np.arange(-FW - pad, FW + pad + STEP / 2, STEP)
    ys = np.arange(-FH - pad, FH + pad + STEP / 2, STEP)
    zs = np.arange(-pad, Z1 + pad + STEP / 2, STEP)
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
    top = Z1 - CROWN * np.clip((X / FW) ** 2 + (Y / FH) ** 2, 0, 1)
    face = (round_rect(X, Y, FW, FH, FR) <= 0) & (Z >= Z0) & (Z <= top)
    r = ER / STEP                                     # rolled face edge: opening by ER
    face = distance_transform_edt(~(distance_transform_edt(face) > r)) <= r
    plan_out = round_rect(X, Y, BX, BY, BR)
    plan_in = round_rect(X, Y, BX - WALL, BY - WALL, max(BR - WALL, 0.3))
    ring = (plan_out <= 0) & (plan_in > 0)
    skirt = ring & (Z >= Z0 - SKIRT_DEPTH) & (Z <= Z0 + 0.5)
    ax = np.abs(X)
    tongue = (ax >= BX - WALL) & (ax <= BX) & (np.abs(Y) <= CLIP_W) & (Z >= 0) & (Z <= Z0 + 0.5)
    zl = Z0 - PANEL
    zb = zl - BARB_L
    t = np.clip((Z - zb) / (zl - zb), 0, 1)
    barb = (ax >= BX - WALL) & (ax <= BX + BARB * t) & (np.abs(Y) <= CLIP_W - 0.3) & (Z >= zb) & (Z <= zl)
    body = face | skirt | tongue | barb
    sd = distance_transform_edt(~body) - distance_transform_edt(body)
    img = pv.ImageData(dimensions=body.shape, spacing=(STEP,) * 3, origin=(xs[0], ys[0], zs[0]))
    img.point_data["d"] = sd.ravel(order="F")
    surf = img.contour([0.0], scalars="d").triangulate().clean().smooth_taubin(n_iter=20, pass_band=0.1)
    if surf.n_cells > 120_000:
        surf = surf.decimate(1.0 - 120_000 / surf.n_cells)
    m = trimesh.Trimesh(np.asarray(surf.points), surf.faces.reshape(-1, 4)[:, 1:], process=True)
    trimesh.repair.fix_normals(m)
    return m


def above_face(n=48):
    """Void: everything above the crowned face top (to z = Z1 + 1.5), 1 mm
    beyond the face outline, so no member can grow on the visible face.
    A height-field slab: crowned underside, flat lid, four side walls."""
    xs = np.linspace(-FW - 1.0, FW + 1.0, n)
    ys = np.linspace(-FH - 1.0, FH + 1.0, int(n * FH / FW))
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    top = Z1 - CROWN * np.clip((X / FW) ** 2 + (Y / FH) ** 2, 0, 1)
    nx, ny = X.shape
    lo = np.c_[X.ravel(), Y.ravel(), top.ravel()]
    hi = np.c_[X.ravel(), Y.ravel(), np.full(X.size, Z1 + 1.5)]
    v = np.vstack([lo, hi])
    idx = lambda i, j, k: k * nx * ny + i * ny + j
    f = []
    for i in range(nx - 1):
        for j in range(ny - 1):
            for k in (0, 1):
                a, b, c, d = idx(i, j, k), idx(i + 1, j, k), idx(i + 1, j + 1, k), idx(i, j + 1, k)
                f += [(a, b, c), (a, c, d)]
    ring = [(i, 0) for i in range(nx)] + [(nx - 1, j) for j in range(1, ny)] + \
           [(i, ny - 1) for i in range(nx - 2, -1, -1)] + [(0, j) for j in range(ny - 2, 0, -1)]
    for s in range(len(ring)):
        (i0, j0), (i1, j1) = ring[s], ring[(s + 1) % len(ring)]
        a, b, c, d = idx(i0, j0, 0), idx(i1, j1, 0), idx(i1, j1, 1), idx(i0, j0, 1)
        f += [(a, b, c), (a, c, d)]
    m = trimesh.Trimesh(v, np.array(f), process=True)
    trimesh.repair.fix_normals(m)
    return m


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    af = above_face()
    af.export(OUT / "above_face.stl")
    print("above_face", len(af.faces), "faces, watertight", af.is_watertight, round(float(af.volume), 1), "mm3",
          np.round(af.bounds, 2).tolist())
    m = build()
    # coarser copy for topopt.py (trimesh.contains runs out of memory on the
    # full mesh); PicoGK adds the full mesh as shaping.base_stl
    surf = pv.wrap(m).triangulate().clean()
    surf = surf.decimate_pro(1.0 - 20_000 / surf.n_cells, preserve_topology=True)
    topo = trimesh.Trimesh(np.asarray(surf.points), surf.faces.reshape(-1, 4)[:, 1:], process=True)
    trimesh.repair.fix_normals(topo)
    for name, mm in (("face_clips", m), ("face_clips_topo", topo)):
        mm.export(OUT / f"{name}.stl")
        print(name, len(mm.faces), "faces, watertight", mm.is_watertight, round(float(mm.volume), 1), "mm3",
              np.round(mm.bounds, 2).tolist())
