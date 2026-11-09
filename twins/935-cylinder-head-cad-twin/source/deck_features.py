"""v1 feature tree, first region: the deck (combustion-face) plate.

Fits analytic features to acquired facets only, writes them to
params/deck-features.json, builds an editable build123d solid from those
numbers (private STEP), and measures the scan facets of the deck zone against
it with the independent Warp distance kernel of score_twin.py.

Features (twin frame, mm):
  outer      rounded rectangle: four side lines and a corner radius
  register   recess cylinder (fitted diameter) and its floor plane
  passages   four stud through-passages: circle centre and diameter
  plate      top of the plate (first outward horizontal face above the deck)

Usage: deck_features.py PRIVATE_DIR PARAMS_DIR
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from twin_common import face_geometry, fit_circle_2d, stats, write_json  # noqa: E402


def level_peaks(z, a, lo, hi, res=0.02, min_area=15.0):
    sel = (z > lo) & (z < hi)
    if not sel.any():
        return []
    edges = np.arange(lo, hi + res, res)
    h, _ = np.histogram(z[sel], bins=edges, weights=a[sel])
    out = []
    for i in range(1, len(h) - 1):
        if h[i] >= min_area and h[i] >= h[i - 1] and h[i] > h[i + 1]:
            out.append((float(edges[i] + res / 2), float(h[max(0, i - 2):i + 3].sum())))
    return out


def main(private, params):
    private, params = Path(private), Path(params)
    frame = json.loads((params / "frame.json").read_text())
    bare = np.load(private / "bare-scan-twin.npz")
    cen, n, area = face_geometry(bare["v"], bare["f"])
    r = np.hypot(cen[:, 0], cen[:, 1])
    side = np.abs(n[:, 2]) < 0.15
    up = n[:, 2] > 0.98      # faces looking into the head (+z)
    down = n[:, 2] < -0.98   # faces looking toward the cylinder (-z)

    reg_d = next(x["diameter_mm"] for x in frame["rings"] if x["name"] == "register")
    # Register floor: -z facing plane inside the recess, beyond the deck.
    floor = level_peaks(cen[down & (r < reg_d / 2 - 1.0), 2], area[down & (r < reg_d / 2 - 1.0)], 0.3, 15.0)
    floor_z, floor_a = max(floor, key=lambda t: t[1]) if floor else (None, 0.0)
    # Register wall refit between deck and floor.
    wsel = side & (np.abs(r - reg_d / 2) < 0.8) & (cen[:, 2] > 0.2) & (cen[:, 2] < (floor_z or 8.0) - 0.2)
    c_reg, r_reg, res_reg = fit_circle_2d(cen[wsel][:, :2])

    # Plate top: +z facing plane outside the recess, nearest above the deck.
    tops = level_peaks(cen[up & (r > reg_d / 2 + 4.0), 2], area[up & (r > reg_d / 2 + 4.0)], 1.0, 20.0)
    plate_top, plate_a = min(tops, key=lambda t: t[0]) if tops else (None, 0.0)
    zt = plate_top or 5.0

    # Outer rounded rectangle from side facets of the plate.
    band = side & (cen[:, 2] > 0.3) & (cen[:, 2] < zt - 0.3) & (r > reg_d / 2 + 6.0)
    p, nn = cen[band], n[band]
    sides = {}
    for key, axis, sign in (("x_min", 0, -1), ("x_max", 0, 1), ("y_min", 1, -1), ("y_max", 1, 1)):
        s = (nn[:, axis] * sign > 0.97)
        vals = p[s, axis]
        sides[key] = {"value": round(float(np.median(vals)), 4), "residual": stats(vals - np.median(vals)),
                      "facets": int(s.sum())}
    xr = (sides["x_min"]["value"], sides["x_max"]["value"])
    yr = (sides["y_min"]["value"], sides["y_max"]["value"])
    corner_radii = []
    for cx, cy, sx, sy in ((xr[0], yr[0], 1, 1), (xr[1], yr[0], -1, 1), (xr[0], yr[1], 1, -1), (xr[1], yr[1], -1, -1)):
        s = (np.abs(nn[:, 0]) < 0.95) & (np.abs(nn[:, 1]) < 0.95) & \
            ((p[:, 0] - cx) * sx < 15) & ((p[:, 0] - cx) * sx > -0.5) & ((p[:, 1] - cy) * sy < 15) & ((p[:, 1] - cy) * sy > -0.5)
        if s.sum() > 30:
            _, rc, res = fit_circle_2d(p[s][:, :2])
            corner_radii.append((rc, float(np.sqrt(np.mean(res ** 2)))))
    rc = float(np.median([c[0] for c in corner_radii])) if corner_radii else 5.0

    # Stud passages: side facets in the corners, outside the register.
    pas = []
    psel = side & (cen[:, 2] > 0.3) & (cen[:, 2] < zt - 0.3) & (r > reg_d / 2 - 2.0) & (r < 80)
    for qx in (-1, 1):
        for qy in (-1, 1):
            s = psel & (np.sign(cen[:, 0]) == qx) & (np.sign(cen[:, 1]) == qy)
            q = cen[s][:, :2]
            c0 = np.median(q, axis=0)
            for _ in range(4):
                keep = np.linalg.norm(q - c0, axis=1) < 8.0
                if keep.sum() < 30:
                    break
                c0, rp, res = fit_circle_2d(q[keep])
            if keep.sum() >= 30 and 3.0 < rp < 8.0:
                pas.append({"centre": np.round(c0, 4).tolist(), "diameter_mm": round(2 * rp, 4),
                            "radial_residual": stats(res), "facets": int(keep.sum())})

    # Chamber dome: algebraic sphere fit to facets inside the chamber shoulder,
    # above the register floor, below the plate top.
    sh_d = next(x["diameter_mm"] for x in frame["rings"] if x["name"] == "chamber_shoulder")
    csel = (r < sh_d / 2 - 2.0) & (cen[:, 2] > (floor_z or 2.0) + 0.5) & (cen[:, 2] < zt - 0.5) & (n[:, 2] < -0.3)
    q = cen[csel]
    A = np.column_stack((q, np.ones(len(q))))
    b = -(q * q).sum(axis=1)
    sol = np.linalg.lstsq(A, b, rcond=None)[0]
    c_sph = -sol[:3] / 2
    r_sph = float(np.sqrt(c_sph @ c_sph - sol[3]))
    res_sph = np.linalg.norm(q - c_sph, axis=1) - r_sph
    feats_chamber = {"sphere_centre": np.round(c_sph, 4).tolist(), "sphere_radius_mm": round(r_sph, 4),
                     "radial_residual": stats(res_sph), "facets": int(csel.sum()), "shoulder_diameter_mm": sh_d}

    feats = {
        "schema": "935-cad-twin-deck-features/1",
        "source": "acquired bare-scan facets in the twin frame; numbers only",
        "deck_z": 0.0,
        "plate_top_z": plate_top, "plate_top_area_mm2": round(plate_a, 1),
        "register": {"centre": np.round(c_reg, 4).tolist(), "diameter_mm": round(2 * r_reg, 4),
                     "radial_residual": stats(res_reg), "floor_z": floor_z, "floor_area_mm2": round(floor_a, 1)},
        "outer": {"sides": sides, "corner_radius_mm": round(rc, 3),
                  "corner_fits": [[round(a, 3), round(b, 4)] for a, b in corner_radii]},
        "passages": pas,
        "chamber": feats_chamber,
    }
    write_json(params / "deck-features.json", feats)
    print(json.dumps({"plate_top_z": plate_top, "register_d": feats["register"]["diameter_mm"],
                      "register_floor_z": floor_z, "outer": {k: v["value"] for k, v in sides.items()},
                      "corner_r": rc, "passages": [(p_["centre"], p_["diameter_mm"]) for p_ in pas]}))
    build_and_score(feats, private, params, bare)


def build_and_score(feats, private, params, bare):
    from build123d import Box, Cylinder, Pos, export_step, export_stl, fillet, Axis

    zt = feats["plate_top_z"]
    o = feats["outer"]["sides"]
    x0, x1, y0, y1 = o["x_min"]["value"], o["x_max"]["value"], o["y_min"]["value"], o["y_max"]["value"]
    plate = Pos((x0 + x1) / 2, (y0 + y1) / 2, zt / 2) * Box(x1 - x0, y1 - y0, zt)
    plate = fillet(plate.edges().filter_by(Axis.Z), radius=feats["outer"]["corner_radius_mm"])
    reg = feats["register"]
    depth = (reg["floor_z"] or zt) + 0.0
    cut = Pos(reg["centre"][0], reg["centre"][1], depth / 2 - 0.01) * Cylinder(reg["diameter_mm"] / 2, depth + 0.02)
    plate = plate - cut
    ch = feats.get("chamber")
    if ch:
        from build123d import Sphere

        floor = reg["floor_z"] or 0.0
        sph = Pos(*ch["sphere_centre"]) * Sphere(ch["sphere_radius_mm"])
        cyl = Pos(reg["centre"][0], reg["centre"][1], (floor + zt) / 2) * Cylinder(ch["shoulder_diameter_mm"] / 2, zt - floor)
        plate = plate - (sph & cyl)
    for p in feats["passages"]:
        plate = plate - Pos(p["centre"][0], p["centre"][1], zt / 2) * Cylinder(p["diameter_mm"] / 2, zt + 1.0)
    export_step(plate, str(private / "v1-deck-plate.step"))
    export_stl(plate, str(private / "v1-deck-plate.stl"), tolerance=0.005, angular_tolerance=0.05)

    import trimesh
    from score_twin import warp_distances

    m = trimesh.load(private / "v1-deck-plate.stl", force="mesh")
    cen, n, area = face_geometry(bare["v"], bare["f"])
    # Scan facets this feature set claims to describe: inside the plate slab,
    # within the outer rectangle, excluding the chamber beyond the floor.
    zone = (cen[:, 2] > -0.5) & (cen[:, 2] < zt + 0.05) & (cen[:, 0] > x0 - 1) & (cen[:, 0] < x1 + 1) & \
           (cen[:, 1] > y0 - 1) & (cen[:, 1] < y1 + 1)
    d = warp_distances(cen[zone], np.asarray(m.vertices), np.asarray(m.faces))
    w = area[zone]
    o_ = np.argsort(d)
    cw = np.cumsum(w[o_]) / w.sum()
    pct = {f"p{q}": round(float(d[o_][np.searchsorted(cw, q / 100)]), 4) for q in (50, 90, 95)}
    score = {"zone_scan_area_mm2": round(float(w.sum()), 1), **pct,
             "share_within_mm": {str(t): round(float(w[d <= t].sum() / w.sum()), 4) for t in (0.1, 0.2, 0.5, 1.0)},
             "solid_valid": bool(plate.is_valid), "volume_mm3": round(float(plate.volume), 1),
             "faces": len(plate.faces())}
    write_json(params / "deck-features-score.json", score)
    print(json.dumps(score))


if __name__ == "__main__":
    main(*sys.argv[1:3])
