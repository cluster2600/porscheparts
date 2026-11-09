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

ADOPT_CHAMBER_BORES = False


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
            # Seed at the provisional four-passage pattern (86.74 x 85.92 mm,
            # twins/reference-935-cylinder-head/README.md) about the register.
            c0 = np.array(c_reg) + np.array([qx * 86.74 / 2, qy * 85.92 / 2])
            for _ in range(4):
                keep = np.abs(np.linalg.norm(q - c0, axis=1) - 5.7) < 2.0
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

    # Bores opening into the chamber (valve throats, plug bores): facets more
    # than 1 mm outside the dome sphere, inside the shoulder, below plate top.
    from scipy import ndimage

    dsph = np.linalg.norm(cen - c_sph, axis=1) - r_sph
    bsel = (dsph > 1.0) & (r < sh_d / 2 - 1.0) & (cen[:, 2] > (floor_z or 2.0)) & (cen[:, 2] < zt - 0.3)
    bq, ba = cen[bsel], area[bsel]
    bores = []
    if len(bq):
        lo = bq[:, :2].min(axis=0)
        ij = np.floor((bq[:, :2] - lo) / 0.5).astype(int)
        g = np.zeros(ij.max(axis=0) + 1, dtype=bool)
        g[ij[:, 0], ij[:, 1]] = True
        lab, nl = ndimage.label(ndimage.binary_dilation(g, iterations=2))
        pl = lab[ij[:, 0], ij[:, 1]]
        for k in range(1, nl + 1):
            pts = bq[pl == k]
            if ba[pl == k].sum() < 20.0:
                continue
            mu = pts.mean(axis=0)
            _, _, vt = np.linalg.svd(pts - mu, full_matrices=False)
            best = None
            for ax in (vt[2], vt[1]):
                ax = ax if ax[2] > 0 else -ax
                e1 = np.cross(ax, [1.0, 0, 0]); e1 /= np.linalg.norm(e1)
                e2 = np.cross(ax, e1)
                c2, rb, rs = fit_circle_2d(np.column_stack(((pts - mu) @ e1, (pts - mu) @ e2)))
                rms = float(np.sqrt(np.mean(rs ** 2)))
                if best is None or rms < best[3]:
                    best = (ax, mu + c2[0] * e1 + c2[1] * e2, rb, rms)
            ax, cpt, rb, rms = best
            t = (pts - cpt) @ ax
            boss = None
            if 2.0 < rb < 30.0 and rms < 0.6:
                # Coaxial guide boss: side facets well inside the throat radius.
                d_all = cen - cpt
                t_all = d_all @ ax
                rad_all = np.linalg.norm(d_all - np.outer(t_all, ax), axis=1)
                ins = (rad_all < rb - 4.0) & (np.abs(n @ ax) < 0.3) & (t_all > t.min() - 5.0) & (t_all < t.max() + 40.0)
                if ins.sum() > 200:
                    rr = rad_all[ins]
                    r_boss = float(np.median(rr))
                    keep = np.abs(rr - r_boss) < 1.0
                    if keep.sum() > 100:
                        tb = t_all[ins][keep]
                        boss = {"diameter_mm": round(2 * float(np.median(rr[keep])), 4),
                                "radial_rms_mm": round(float(np.std(rr[keep])), 4),
                                "t_range_mm": [round(float(tb.min()), 3), round(float(tb.max()), 3)],
                                "facets": int(keep.sum())}
            if 2.0 < rb < 30.0 and rms < 0.6:
                bores.append({"guide_boss": boss, "axis": np.round(ax, 5).tolist(), "point": np.round(cpt, 4).tolist(),
                              "diameter_mm": round(2 * rb, 4), "radial_rms_mm": round(rms, 4),
                              "t_range_mm": [round(float(t.min()), 3), round(float(t.max()), 3)],
                              "facets": int(len(pts))})

    # Deck-face outline: sides fitted only just above the deck, and the level
    # where the body steps out to the wider upper outline.
    dband = side & (cen[:, 2] > 0.3) & (cen[:, 2] < 1.8) & (r > reg_d / 2 + 2.0)
    dp, dn = cen[dband], n[dband]
    deck_sides = {}
    for key, axis, sign in (("x_min", 0, -1), ("x_max", 0, 1), ("y_min", 1, -1), ("y_max", 1, 1)):
        sd = (dn[:, axis] * sign > 0.97)
        deck_sides[key] = round(float(np.median(dp[sd, axis])), 4) if sd.sum() > 20 else sides[key]["value"]
    outside = ((cen[:, 0] < deck_sides["x_min"] - 1) | (cen[:, 0] > deck_sides["x_max"] + 1) |
               (cen[:, 1] < deck_sides["y_min"] - 1) | (cen[:, 1] > deck_sides["y_max"] + 1))
    steps = level_peaks(cen[down & outside, 2], area[down & outside], 0.5, zt - 0.2, min_area=5.0)
    step_z, step_a = max(steps, key=lambda t: t[1]) if steps else (None, 0.0)

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
        "deck_outline": {"sides": deck_sides, "step_z": step_z, "step_area_mm2": round(step_a, 1)},
        "chamber": feats_chamber,
        "chamber_bores": bores,
    }
    write_json(params / "deck-features.json", feats)
    print(json.dumps({"plate_top_z": plate_top, "register_d": feats["register"]["diameter_mm"],
                      "register_floor_z": floor_z, "outer": {k: v["value"] for k, v in sides.items()},
                      "corner_r": rc, "passages": [(p_["centre"], p_["diameter_mm"]) for p_ in pas],
                      "bores": [(b["diameter_mm"], b["radial_rms_mm"], b["guide_boss"]) for b in bores]}))
    build_and_score(feats, private, params, bare)


def build_and_score(feats, private, params, bare):
    from build123d import Box, Cylinder, Pos, export_step, export_stl, fillet, Axis

    zt = feats["plate_top_z"]
    o = feats["outer"]["sides"]
    x0, x1, y0, y1 = o["x_min"]["value"], o["x_max"]["value"], o["y_min"]["value"], o["y_max"]["value"]
    rcorner = feats["outer"]["corner_radius_mm"]
    dk = feats.get("deck_outline", {})
    zs = dk.get("step_z")
    if zs:
        ds = dk["sides"]
        low = Pos((ds["x_min"] + ds["x_max"]) / 2, (ds["y_min"] + ds["y_max"]) / 2, zs / 2) * \
            Box(ds["x_max"] - ds["x_min"], ds["y_max"] - ds["y_min"], zs)
        low = fillet(low.edges().filter_by(Axis.Z), radius=rcorner)
        up = Pos((x0 + x1) / 2, (y0 + y1) / 2, (zs + zt) / 2) * Box(x1 - x0, y1 - y0, zt - zs)
        up = fillet(up.edges().filter_by(Axis.Z), radius=rcorner)
        plate = low + up
    else:
        plate = Pos((x0 + x1) / 2, (y0 + y1) / 2, zt / 2) * Box(x1 - x0, y1 - y0, zt)
        plate = fillet(plate.edges().filter_by(Axis.Z), radius=rcorner)
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
    from build123d import Plane, Solid

    # Iteration 3 (2026-11-09): cutting the fitted throats and adding the
    # coaxial bosses lowered the zone score (p95 3.05 -> 3.29 / 3.20 mm); the
    # boss fit (about 30 mm, RMS 0.59 mm) is not a credible guide boss. The
    # fits stay in deck-features.json as data; the solid does not adopt them.
    for b in (feats.get("chamber_bores", []) if ADOPT_CHAMBER_BORES else []):
        ax = np.array(b["axis"])
        t0, t1 = b["t_range_mm"]
        # Start just inside the dome (below t0 is already cut by the sphere)
        # and run on into the port; never back through the deck.
        origin = np.array(b["point"]) + (t0 - 1.0) * ax
        plane = Plane(origin=tuple(origin), z_dir=tuple(ax))
        plate = plate - Solid.make_cylinder(b["diameter_mm"] / 2, (t1 - t0) + 31.0, plane)
        gb = b.get("guide_boss")
        if gb:
            g0, g1 = gb["t_range_mm"]
            gplane = Plane(origin=tuple(np.array(b["point"]) + g0 * ax), z_dir=tuple(ax))
            plate = plate + Solid.make_cylinder(gb["diameter_mm"] / 2, g1 - g0, gplane)
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
