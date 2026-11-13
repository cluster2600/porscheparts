"""Fit the non-revolved hub features of the 935 rotor.

Features (positions in the twin frame, angles from +X):
- front heads: 8 bosses (rivet or bolt heads) proud of datum A at r ~ 52;
- back tails: 8 bosses proud of the back annulus at r ~ 52;
- step bosses: 4 bosses proud of the inner step face (z ~ -9.2), r < 30
  (fragments of the step-wall fillet near r 33 are excluded);
- drive dogs: 2 crescent pads proud of the flange back face (z ~ -26.4),
  outlines traced from the scan, each with its holes.

Bosses are reported as cylinders (centre, diameter from the footprint
area, height from the base face). Whether a boss is a rivet, a bolt head
or cast material is not established (hypothesis H-FASTENERS).

Usage: fit_features.py ROTOR.obj PRIVATE_CACHE_DIR OUT.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage
from skimage.measure import find_contours

from fan_common import PARAMS, ROTOR_SCAN_SHA256, cylindrical, load_frame, load_obj, to_fan, tri_centroids_areas, write_json

CELL = 0.3


def base_z(profile: np.ndarray, r_lo: float, r_hi: float, z_lo: float, z_hi: float) -> float:
    sel = (profile[:, 0] > r_lo) & (profile[:, 0] < r_hi) & (profile[:, 1] > z_lo) & (profile[:, 1] < z_hi)
    return float(np.median(profile[sel, 1]))


def clusters(xy: np.ndarray, min_area: float):
    lo = xy.min(0) - 2 * CELL
    ij = ((xy - lo) / CELL).astype(int)
    grid = np.zeros(ij.max(0) + 3, bool)
    grid[ij[:, 0], ij[:, 1]] = True
    grid = ndimage.binary_closing(grid, iterations=2)
    grid = ndimage.binary_fill_holes(grid)
    lab, n = ndimage.label(grid)
    out = []
    for k in range(1, n + 1):
        mask = lab == k
        area = mask.sum() * CELL ** 2
        if area < min_area:
            continue
        pts = lab[ij[:, 0], ij[:, 1]] == k
        out.append((mask, lo, area, pts))
    return out


def bosses(p, r_rng, z_rng, base, sign, min_area, expect):
    r, th, z = cylindrical(p)
    m = (r > r_rng[0]) & (r < r_rng[1]) & (z > z_rng[0]) & (z < z_rng[1])
    q = p[m]
    found = []
    for mask, lo, area, pts in clusters(q[:, :2], min_area):
        c = q[pts, :2].mean(0)
        h = float(np.percentile(sign * (q[pts, 2] - base), 98))
        found.append({"centre_xy_mm": [round(float(c[0]), 3), round(float(c[1]), 3)],
                      "r_mm": round(float(np.hypot(*c)), 3), "angle_deg": round(float(np.degrees(np.arctan2(c[1], c[0]))), 2),
                      "diameter_mm": round(float(np.sqrt(4 * area / np.pi)), 3), "height_mm": round(h, 3)})
    found.sort(key=lambda b: b["angle_deg"])
    return {"base_z_mm": round(base, 3), "direction": "+z" if sign > 0 else "-z", "expected_count": expect,
            "found_count": len(found), "items": found}


def outline(mask: np.ndarray, lo: np.ndarray) -> np.ndarray:
    cont = max(find_contours(np.pad(mask, 1).astype(float), 0.5), key=len)
    xy = (cont - 1) * CELL + lo + CELL / 2
    keep = [0]
    for i in range(1, len(xy)):
        if np.linalg.norm(xy[i] - xy[keep[-1]]) >= 0.6:
            keep.append(i)
    return xy[keep]


def main(obj: str, cache: str, out: str) -> int:
    v, f = load_obj(Path(obj), ROTOR_SCAN_SHA256, Path(cache))
    c, _, _ = tri_centroids_areas(v, f)
    p = to_fan(np.r_[v, c], load_frame())
    prof = np.asarray(json.loads((PARAMS / "hub-profile.json").read_text())["profile_rz_mm"])
    front = base_z(prof, 38, 56, -1, 1)
    back_annulus = base_z(prof, 44, 56, -23, -18)
    step = base_z(prof, 21, 33, -10.5, -8)
    flange_back = base_z(prof, 14, 34, -28, -25)
    feats = {
        "front_heads": bosses(p, (44, 60), (front + 0.6, front + 12), front, 1, 15, 8),
        "back_tails": bosses(p, (44, 60), (back_annulus - 10, back_annulus - 0.6), back_annulus, -1, 15, 8),
        "step_bosses": bosses(p, (18, 30), (step + 0.5, step + 6), step, 1, 6, 4),
    }
    # Drive dogs: pads below the flange back face.
    r, th, z = cylindrical(p)
    m = (r > 11.5) & (r < 39) & (z < flange_back - 1.0) & (z > flange_back - 20)
    q = p[m]
    dogs = []
    for mask, lo, area, pts in clusters(q[:, :2], 150):
        poly = outline(mask, lo)
        face_z = float(np.percentile(q[pts, 2], 2))
        bottom = q[pts]
        # Holes: gaps in the dog's flat face (filled footprint minus observed face).
        face = bottom[np.abs(bottom[:, 2] - face_z) < 0.6]
        flo = face[:, :2].min(0) - 2 * CELL
        fij = ((face[:, :2] - flo) / CELL).astype(int)
        fg = np.zeros(fij.max(0) + 3, bool)
        fg[fij[:, 0], fij[:, 1]] = True
        fg = ndimage.binary_closing(fg, iterations=1)
        gaps, ng = ndimage.label(ndimage.binary_fill_holes(fg) & ~fg)
        holes = []
        for k in range(1, ng + 1):
            gm = gaps == k
            garea = gm.sum() * CELL ** 2
            if not 2.0 < garea < 120.0:
                continue
            gi = np.argwhere(gm)
            cc = gi.mean(0) * CELL + flo + CELL / 2
            ext = (gi.max(0) - gi.min(0) + 1) * CELL
            if max(ext) > 2.0 * min(ext):
                continue
            holes.append({"centre_xy_mm": [round(float(cc[0]), 3), round(float(cc[1]), 3)],
                          "diameter_mm": round(float(np.sqrt(4 * garea / np.pi)), 3),
                          "basis": "unobserved gap in the dog face; depth not observed"})
        dogs.append({"face_z_mm": round(face_z, 3), "height_mm": round(flange_back - face_z, 3), "area_mm2": round(area, 1),
                     "centroid_angle_deg": round(float(np.degrees(np.arctan2(*bottom[:, :2].mean(0)[::-1]))), 2),
                     "outline_xy_mm": [[round(float(a), 3), round(float(b), 3)] for a, b in poly], "holes": holes})
    feats["drive_dogs"] = {"base_z_mm": round(flange_back, 3), "found_count": len(dogs), "items": dogs,
                           "role": "probable coupling to the drive output (hypothesis H-DRIVE-DOGS)"}
    write_json(Path(out), {"schema": "935-horizontal-fan-cad-twin/features/1", "scan_sha256": ROTOR_SCAN_SHA256,
                           "frame": "params/frame.json", "features": feats})
    for k, val in feats.items():
        items = val["items"]
        print(k, val["found_count"], [ (it.get("r_mm"), it.get("angle_deg"), it.get("diameter_mm"), it.get("height_mm")) for it in items][:9] if k != "drive_dogs" else
              [(d["area_mm2"], d["height_mm"], d["centroid_angle_deg"], [(h["diameter_mm"], h["centre_xy_mm"]) for h in d["holes"]]) for d in items])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:]))
