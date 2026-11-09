"""Fit the revolved (axisymmetric) hub profile of the 935 rotor.

Only surfaces seen at most angles around the axis count as revolved: each
(r, z) cell of 0.25 mm is scored by the share of 6-degree sectors in which
the scan has a point there. Cells with coverage >= COVERAGE form the profile
line (the threshold is low because blade roots, windows and bosses hide the
revolved surface over much of the circumference); the largest region its
centreline encloses is traced as one closed loop, then every loop vertex is
moved along its normal to the dominant mode of the nearby scan points (sub-cell
accuracy), smoothed and simplified. Lugs, bolt bosses, windows and blades
are not revolved and are fitted separately.

Usage: fit_hub_profile.py ROTOR.obj PRIVATE_CACHE_DIR OUT.json
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree
from skimage.measure import find_contours
from skimage.morphology import skeletonize

from fan_common import ROTOR_SCAN_SHA256, cylindrical, load_frame, load_obj, to_fan, tri_centroids_areas, write_json

PX = 0.25
SECTORS = 60
COVERAGE = 0.18
R_MAX = 91.5
Z0 = -50.0
SIMPLIFY_MM = 0.04


def rdp(pts: np.ndarray, tol: float) -> np.ndarray:
    keep = np.zeros(len(pts), bool)
    keep[[0, -1]] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        a, b = pts[i], pts[j]
        ab = b - a
        L = np.linalg.norm(ab)
        seg = pts[i + 1:j] - a
        d = np.abs(ab[0] * seg[:, 1] - ab[1] * seg[:, 0]) / L if L > 0 else np.linalg.norm(seg, axis=1)
        k = int(np.argmax(d))
        if d[k] > tol:
            keep[i + 1 + k] = True
            stack += [(i, i + 1 + k), (i + 1 + k, j)]
    return pts[keep]


def main(obj: str, cache: str, out: str) -> int:
    v, f = load_obj(Path(obj), ROTOR_SCAN_SHA256, Path(cache))
    frame = load_frame()
    c, _, _ = tri_centroids_areas(v, f)
    p = to_fan(np.r_[v, c], frame)
    r, th, z = cylindrical(p)
    m = r < R_MAX
    nr, nz = int(R_MAX / PX) + 1, int(100 / PX)
    ir = (r[m] / PX).astype(int)
    iz = np.clip(((z[m] - Z0) / PX).astype(int), 0, nz - 1)
    it = ((th[m] + np.pi) / (2 * np.pi) * SECTORS).astype(int) % SECTORS
    cells = np.unique((ir * nz + iz) * SECTORS + it) // SECTORS
    cov = (np.bincount(cells, minlength=nr * nz).reshape(nr, nz)) / SECTORS
    line = ndimage.binary_closing(cov >= COVERAGE, iterations=2)
    lab, n = ndimage.label(line)
    line = lab == (np.argmax(np.bincount(lab.ravel())[1:]) + 1)
    skel = skeletonize(line)
    holes, _ = ndimage.label(ndimage.binary_fill_holes(skel) & ~skel)
    region = holes == (np.argmax(np.bincount(holes.ravel())[1:]) + 1)
    region = ndimage.binary_dilation(region, iterations=1)
    contours = find_contours(region.astype(float), 0.5)
    loop = max(contours, key=len)
    loop = np.c_[loop[:, 0] * PX + PX / 2, loop[:, 1] * PX + Z0 + PX / 2]
    # Resample at 0.2 mm and refine along normals against the axisymmetric cloud.
    seg = np.r_[0, np.cumsum(np.linalg.norm(np.diff(loop, axis=0), axis=1))]
    s = np.arange(0, seg[-1], 0.2)
    loop = np.c_[np.interp(s, seg, loop[:, 0]), np.interp(s, seg, loop[:, 1])]
    rz = np.c_[r[m], z[m]]
    covpt = cov[ir, iz] >= COVERAGE
    tree = cKDTree(rz[covpt])
    pts = rz[covpt]
    tang = np.gradient(loop, axis=0)
    tang /= np.linalg.norm(tang, axis=1)[:, None]
    nrm = np.c_[-tang[:, 1], tang[:, 0]]
    refined, spread = loop.copy(), np.full(len(loop), np.nan)
    for i, (q, nn) in enumerate(zip(loop, nrm)):
        idx = tree.query_ball_point(q, 0.9)
        if len(idx) < 8:
            continue
        d = pts[idx] - q
        along = d @ tang[i]
        off = d @ nn
        sel = np.abs(along) < 0.3
        if sel.sum() < 5:
            continue
        o = off[sel]
        hist, edges = np.histogram(o, bins=np.arange(-0.9, 0.9001, 0.05))
        hist = ndimage.gaussian_filter1d(hist.astype(float), 1.5)
        peak = edges[np.argmax(hist)] + 0.025
        near = np.abs(o - peak) < 0.15
        mode = float(np.mean(o[near])) if near.sum() >= 3 else peak
        refined[i] = q + mode * nn
        spread[i] = float(np.sqrt(np.mean((o[near] - mode) ** 2))) if near.sum() >= 3 else np.nan
    # Light smoothing along the loop (wrap-around), then simplification.
    k = 5
    pad = np.r_[refined[-k:], refined, refined[:k]]
    sm = np.c_[np.convolve(pad[:, 0], np.ones(2 * k + 1) / (2 * k + 1), "same"),
               np.convolve(pad[:, 1], np.ones(2 * k + 1) / (2 * k + 1), "same")][k:-k]
    # Keep sharp corners: use raw refined points where smoothing moves > 0.08 mm.
    moved = np.linalg.norm(sm - refined, axis=1)
    final = np.where((moved > 0.08)[:, None], refined, sm)
    simp = rdp(np.r_[final, final[:1]], SIMPLIFY_MM)[:-1]
    if np.sum(simp[:, 0] * np.roll(simp[:, 1], -1) - np.roll(simp[:, 0], -1) * simp[:, 1]) < 0:
        simp = simp[::-1]
    area = 0.5 * abs(np.sum(simp[:, 0] * np.roll(simp[:, 1], -1) - np.roll(simp[:, 0], -1) * simp[:, 1]))
    write_json(Path(out), {
        "schema": "935-horizontal-fan-cad-twin/hub-profile/1",
        "scan_sha256": ROTOR_SCAN_SHA256,
        "frame": "params/frame.json",
        "method": {"cell_mm": PX, "sectors": SECTORS, "coverage_min": COVERAGE, "simplify_mm": SIMPLIFY_MM,
                   "refinement": "dominant mode of the normal offsets of axisymmetric points within 0.9 mm, |along| < 0.3 mm (robust to bosses, lugs and blade roots on one side)"},
        "profile_rz_mm": [[round(float(a), 3), round(float(b), 3)] for a, b in simp],
        "vertices": int(len(simp)),
        "section_area_mm2": round(float(area), 1),
        "r_range_mm": [round(float(simp[:, 0].min()), 3), round(float(simp[:, 0].max()), 3)],
        "z_range_mm": [round(float(simp[:, 1].min()), 3), round(float(simp[:, 1].max()), 3)],
        "mode_rms_mm": {"median": round(float(np.nanmedian(spread)), 3), "p95": round(float(np.nanpercentile(spread, 95)), 3)},
        "interior": "unobserved: the closed loop is the observed outer surface; see hypotheses H-HUB-INTERIOR",
    })
    print(f"loop {len(loop)} -> {len(simp)} vertices, area {area:.0f} mm2, r {simp[:,0].min():.2f}-{simp[:,0].max():.2f}, z {simp[:,1].min():.2f}-{simp[:,1].max():.2f}, spread median {np.nanmedian(spread):.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:]))
