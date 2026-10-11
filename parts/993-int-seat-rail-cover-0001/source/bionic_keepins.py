#!/usr/bin/env python3
"""Exact keep-in bodies of the bionic seat rail cover (closed STLs).

    python bionic_keepins.py

Writes source/bionic-keepins/*.stl, referenced by source/bionic.json:
  shell.stl        crowned, drafted outer shell (2.5 mm wall) with rounded
                   edges, end ramps, and the inward hook lips of the snap
                   tongues; open underneath (same field as the F0 PicoGK
                   generator parts/picogk-catalog/trim/SeatRailCover.cs,
                   rounded by a distance-transform opening, meshed by VTK)
  shell_topo_<k>.stl  the same shell in 7 closed pieces along X, decimated,
                   for topopt.py (see segments())
  cavity_band_<k>.stl design region in 7 pieces: inside of the shell above
                   z = 20 (rail clearance)
  countersinks.stl two 90 deg countersinks (void) at the screw bosses
X along the rail, Z up, open face at z = 0, values of source/picogk.json.
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
L, W, H, WALL = P["length_mm"], P["width_mm"], P["height_mm"], P["wall_mm"]
CROWN, DRAFT, RAMP, NOSE = P["crown_mm"], P["side_draft_mm"], P["end_ramp_length_mm"], P["nose_height_mm"]
RC, EDGE = P["plan_corner_radius_mm"], P["edge_radius_mm"]
CLIPS, CLIP_L, HOOK = int(P["clips_per_side"]), P["clip_length_mm"], P["clip_hook_mm"]
CS_D, HOLE_D = P["countersink_diameter_mm"], P["screw_hole_diameter_mm"]
HX, HY = L / 2, W / 2
SPAN = L - 2 * RAMP
XB = HX - RAMP * 0.55
STEP = 0.4
SEGMENTS = 7


def smooth(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def height(x):
    return NOSE + (H - NOSE) * smooth((HX - np.abs(x)) / RAMP)


def half_w(z):
    return HY - DRAFT * np.clip(z / H, 0, 1)


def round_rect(x, y, hx, hy, r):
    r = np.minimum(r, np.minimum(hx, hy))
    qx, qy = np.abs(x) - hx + r, np.abs(y) - hy + r
    return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r


def shell_field(X, Y, Z, inset, z_min):
    hw = half_w(Z) - inset
    d2 = round_rect(X, Y, HX - inset, hw, max(RC - inset, 0.5))
    top = height(X) - inset - CROWN * np.clip((Y / hw) ** 2, 0, 1)
    return np.maximum(d2, np.maximum((Z - top) * 0.85, z_min - Z))


def mesh_mask(mask, origin, step, max_faces=150_000):
    """Closed surface of a boolean grid (x fastest in VTK order)."""
    sd = distance_transform_edt(~mask) - distance_transform_edt(mask)
    img = pv.ImageData(dimensions=mask.shape, spacing=(step,) * 3, origin=origin)
    img.point_data["d"] = sd.ravel(order="F")
    surf = img.contour([0.0], scalars="d").triangulate().clean()
    surf = surf.smooth_taubin(n_iter=20, pass_band=0.1)
    if surf.n_cells > max_faces:
        surf = surf.decimate(1.0 - max_faces / surf.n_cells)
    faces = surf.faces.reshape(-1, 4)[:, 1:]
    m = trimesh.Trimesh(np.asarray(surf.points), faces, process=True)
    trimesh.repair.fix_normals(m)
    return m


def shell():
    pad = 1.0
    xs = np.arange(-HX - pad, HX + pad + STEP / 2, STEP)
    ys = np.arange(-HY - pad, HY + pad + STEP / 2, STEP)
    zs = np.arange(-pad, H + pad + STEP / 2, STEP)
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
    outer = shell_field(X, Y, Z, 0.0, -6.0) <= 0
    # round convex edges by EDGE: opening (erode then dilate) of the outer body
    r = EDGE / STEP
    eroded = distance_transform_edt(outer) > r
    outer = distance_transform_edt(~eroded) <= r
    outer &= Z >= 0                                   # crisp open face at z = 0
    body = outer & ~(shell_field(X, Y, Z, WALL, -2.0) <= 0)
    # snap tongue hook lips with lead-in chamfer (as SeatRailCover.cs)
    hw_bot = half_w(0.0)
    pitch = SPAN / CLIPS
    for i in range(CLIPS):
        x = -SPAN / 2 + pitch * (i + 0.5)
        qy = np.abs(Y)
        box = (np.abs(X - x) <= CLIP_L / 2 - 1) & (np.abs(qy - (hw_bot - WALL - HOOK / 2 + 0.3)) <= HOOK / 2 + 0.3) & (Z >= 0) & (Z <= 3.2)
        keep = ((hw_bot - WALL - HOOK) + HOOK * 0.8 - qy - Z) <= 0
        body |= box & keep
    return body, (xs, ys, zs)


def segments(n=SEGMENTS):
    """x limits of the pieces of the topopt.py copies: trimesh.contains (pure
    python ray test here) runs out of memory on the full 420 mm shell, so the
    optimization reads it as n closed pieces, each tested only inside its own
    bounding box."""
    edges = np.linspace(-HX - 1, HX + 1, n + 1)
    return list(zip(edges[:-1], edges[1:]))


def shell_pieces(body, grid):
    xs, ys, zs = grid
    out = []
    for a, b in segments():
        i0, i1 = np.searchsorted(xs, a), np.searchsorted(xs, b)
        lo, hi = max(i0 - 3, 0), min(i1 + 3, len(xs))
        sub = np.zeros((hi - lo,) + body.shape[1:], bool)
        sub[i0 - lo:i1 - lo] = body[i0:i1]
        out.append(mesh_mask(sub, (xs[lo], ys[0], zs[0]), STEP, max_faces=6_000))
    return out


def cavity_band(z_floor=20.0, grow=0.3, x_range=None):
    """Design domain: the inside of the shell above the rail clearance plane
    (F0: ribs end 20 mm above the open face to clear the rail), grown by
    `grow` so it overlaps the shell keep-in."""
    xs = np.arange(-HX - 1, HX + 1 + STEP / 2, STEP)
    ys = np.arange(-HY - 1, HY + 1 + STEP / 2, STEP)
    zs = np.arange(z_floor - 1, H + 1 + STEP / 2, STEP)
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
    f = np.maximum(shell_field(X, Y, Z, WALL, -2.0), z_floor - Z) - grow
    if x_range is not None:
        f = np.maximum(f, np.maximum(x_range[0] - X, X - x_range[1]))
    img = pv.ImageData(dimensions=f.shape, spacing=(STEP,) * 3, origin=(xs[0], ys[0], zs[0]))
    img.point_data["d"] = f.ravel(order="F")
    surf = img.contour([0.0], scalars="d").triangulate().clean()
    if surf.n_cells > 3_000:                         # design region of topopt.py only
        surf = surf.decimate(1.0 - 3_000 / surf.n_cells)
    m = trimesh.Trimesh(np.asarray(surf.points), surf.faces.reshape(-1, 4)[:, 1:], process=True)
    trimesh.repair.fix_normals(m)
    return m


def countersinks():
    parts = []
    for x in (XB, -XB):
        top = float(height(np.array(x)))
        r0 = CS_D / 2 + 1.2                          # 90 deg: radius = height; CS_D at the surface
        cone = trimesh.creation.cone(radius=r0, height=r0, sections=48)
        # trimesh cone: base at z = 0, apex up; flip so the base is on top
        cone.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))
        cone.apply_translation([x, 0, top + 1.2])
        parts.append(cone)
    return trimesh.util.concatenate(parts)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    body, grid = shell()
    bodies = [("shell", mesh_mask(body, (grid[0][0], grid[1][0], grid[2][0]), STEP))]
    bodies += [(f"shell_topo_{k}", m) for k, m in enumerate(shell_pieces(body, grid))]
    bodies += [(f"cavity_band_{k}", cavity_band(x_range=s)) for k, s in enumerate(segments())]
    bodies += [("countersinks", countersinks())]
    for name, m in bodies:
        if len(m.faces) == 0:
            continue
        m.export(OUT / f"{name}.stl")
        print(name, len(m.faces), "faces, watertight", m.is_watertight, round(float(m.volume), 1), "mm3",
              np.round(m.bounds, 2).tolist())
