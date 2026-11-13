"""Fit one 935 blade on all nine scanned blades, pooled.

At each radius station, scan points within +-0.35 mm of the station radius
are unrolled to (s = r * phase, z), where phase is the angle from the
nominal position of their blade (40 degree pitch). Each blade's angular
placement error is estimated and removed first, so the nine blades can fill
each other's occlusions. The pooled section is described in its chord frame:
leading edge, trailing edge, then upper and lower surface offsets at
cosine-spaced chord stations. Parameters are finally smoothed across radius
with low-order polynomials, and the blade-to-blade scatter is reported.

Leading edge = the end at negative s / low z: the blade angle from the
tangential direction increases towards the other end, as for a rotor that
moves towards -s and pushes air towards +z (hypothesis H-FLOW-DIRECTION).

Usage: fit_blades.py ROTOR.obj PRIVATE_CACHE_DIR OUT.json
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree

from fan_common import BLADE_COUNT, ROTOR_SCAN_SHA256, cylindrical, load_frame, load_obj, to_fan, tri_centroids_areas, write_json

PITCH = 2 * np.pi / BLADE_COUNT
BAND = 0.35
NX = 25
X = 0.5 * (1 - np.cos(np.linspace(0, np.pi, NX)))


def largest_cluster(sz: np.ndarray, cell: float = 0.5) -> np.ndarray:
    lo = sz.min(0)
    ij = ((sz - lo) / cell).astype(int)
    grid = np.zeros(ij.max(0) + 1, bool)
    grid[ij[:, 0], ij[:, 1]] = True
    lab, n = ndimage.label(ndimage.binary_dilation(grid, iterations=2))
    if n == 0:
        return np.zeros(len(sz), bool)
    big = np.argmax(np.bincount(lab.ravel())[1:]) + 1
    return lab[ij[:, 0], ij[:, 1]] == big


def station_points(r, th, z, rk, offsets):
    m = np.abs(r - rk) < BAND
    b = np.round(th[m] / PITCH).astype(int) % BLADE_COUNT
    ph = th[m] - np.round(th[m] / PITCH) * PITCH - offsets[b]
    sz = np.c_[rk * ph, z[m]]
    keep = largest_cluster(sz)
    return sz[keep], b[keep]


def section(sz: np.ndarray, b: np.ndarray | None = None) -> dict | None:
    if len(sz) < 200:
        return None
    mu = sz.mean(0)
    d = np.linalg.svd(sz - mu, full_matrices=False)[2][0]
    if d[0] < 0:
        d = -d
    nrm = np.array([-d[1], d[0]])
    u = (sz - mu) @ d
    w = (sz - mu) @ nrm
    # Ends: median over blades of each blade's own extent, so flash, debris or
    # one damaged blade cannot drag the pooled leading or trailing edge.
    if b is None:
        b = np.zeros(len(sz), int)
    ends = np.array([np.percentile(u[b == k], [0.5, 99.5]) for k in np.unique(b) if (b == k).sum() > 50])
    u0, u1 = np.median(ends[:, 0]), np.median(ends[:, 1])
    # Lateral position of each end: midway between the two surfaces there
    # (a median would snap to one surface on a blunt end).
    def mid(sel):
        lo_, hi_ = np.percentile(w[sel], [5, 95])
        return 0.5 * (lo_ + hi_)
    le = mu + u0 * d + mid(np.abs(u - u0) < 0.5) * nrm
    te = mu + u1 * d + mid(np.abs(u - u1) < 0.5) * nrm
    chord_vec = te - le
    chord = float(np.linalg.norm(chord_vec))
    cd = chord_vec / chord
    cn = np.array([-cd[1], cd[0]])
    x = ((sz - le) @ cd) / chord
    y = (sz - le) @ cn
    inside = (x > -0.02) & (x < 1.02)
    x, y = x[inside], y[inside]
    upper, lower = np.full(NX, np.nan), np.full(NX, np.nan)
    for i, xi in enumerate(X[1:-1], 1):
        half = max(0.004, 0.6 / chord)
        sel = np.abs(x - xi) < half
        if sel.sum() < 10:
            continue
        ys = np.sort(y[sel])
        gaps = np.diff(ys)
        k = int(np.argmax(gaps))
        if gaps[k] < 0.3:
            continue
        upper[i] = np.median(ys[k + 1:])
        lower[i] = np.median(ys[:k + 1])
    upper[0] = lower[0] = upper[-1] = lower[-1] = 0.0
    good = ~np.isnan(upper)
    upper = np.interp(X, X[good], upper[good])
    lower = np.interp(X, X[good], lower[good])
    angle = np.degrees(np.arctan2(chord_vec[1], chord_vec[0]))
    return {"le_sz": le, "te_sz": te, "chord": chord, "stagger_deg": float(angle), "upper": upper, "lower": lower,
            "interpolated_stations": int((~good).sum())}


def section_curve(sec: dict, n_side: int = 200) -> np.ndarray:
    le, te = np.asarray(sec["le_sz"]), np.asarray(sec["te_sz"])
    cd = (te - le) / np.linalg.norm(te - le)
    cn = np.array([-cd[1], cd[0]])
    xs = 0.5 * (1 - np.cos(np.linspace(0, np.pi, n_side)))
    up = np.interp(xs, X, sec["upper"])
    lo = np.interp(xs, X, sec["lower"])
    c = sec["chord"]
    top = le + np.outer(xs * c, cd) + np.outer(up, cn)
    bot = le + np.outer(xs * c, cd) + np.outer(lo, cn)
    return np.r_[top, bot[::-1][1:-1]]


def main(obj: str, cache: str, out: str) -> int:
    v, f = load_obj(Path(obj), ROTOR_SCAN_SHA256, Path(cache))
    c, _, _ = tri_centroids_areas(v, f)
    p = to_fan(np.r_[v, c], load_frame())
    r, th, z = cylindrical(p)
    # Tip: the radially facing tip faces make a density peak in r; fit a circle to that band.
    hist, edges = np.histogram(r[(r > 125) & (r < 142)], bins=np.arange(125, 142, 0.2))
    peak = edges[np.argmax(hist)] + 0.1
    tb = (r > peak - 0.9) & (r < peak + 0.9)
    xx, yy = p[tb, 0], p[tb, 1]
    sol = np.linalg.lstsq(np.c_[2 * xx, 2 * yy, np.ones(tb.sum())], xx ** 2 + yy ** 2, rcond=None)[0]
    tip_r = float(np.sqrt(sol[2] + sol[0] ** 2 + sol[1] ** 2))
    tip_centre = [float(sol[0]), float(sol[1])]
    # Root stations start clear of the blade-to-drum fillet (drum r ~ 89.3).
    stations = np.r_[np.arange(93.0, tip_r - 1.5, 2.5), tip_r - 0.8]
    offsets = np.zeros(BLADE_COUNT)
    for it in range(3):
        shifts = [[] for _ in range(BLADE_COUNT)]
        for rk in stations[2:-1]:
            sz, b = station_points(r, th, z, rk, offsets)
            sec = section(sz, b)
            if sec is None:
                continue
            tree = cKDTree(section_curve(sec))
            for k in range(BLADE_COUNT):
                q = sz[b == k]
                if len(q) < 50:
                    continue
                best = min(np.arange(-1.5, 1.501, 0.05), key=lambda ds: np.mean(np.minimum(tree.query(q + [ds, 0])[0], 1.0)))
                shifts[k].append(best / rk)
        delta = np.array([np.median(s) if s else 0.0 for s in shifts])
        offsets = offsets - delta + np.mean(delta)
    secs, scatter = [], []
    for rk in stations:
        sz, b = station_points(r, th, z, rk, offsets)
        sec = section(sz, b)
        if sec is None:
            continue
        tree = cKDTree(section_curve(sec, 400))
        dist, _ = tree.query(sz)
        per_blade = [float(np.sqrt(np.mean(np.minimum(dist[b == k], 2.0) ** 2))) for k in range(BLADE_COUNT) if (b == k).sum() > 30]
        sec.update(r=float(rk), points=int(len(sz)), pooled_rms=float(np.sqrt(np.mean(np.minimum(dist, 2.0) ** 2))),
                   per_blade_rms_max=float(max(per_blade)))
        secs.append(sec)
    rr = np.array([s["r"] for s in secs])
    smooth = {}
    for key in ("chord", "stagger_deg"):
        coef = np.polyfit(rr, [s[key] for s in secs], 2)
        smooth[key] = [float(x) for x in coef]
    for key in ("le_sz", "te_sz"):
        arr = np.array([s[key] for s in secs])
        smooth[key] = [[float(x) for x in np.polyfit(rr, arr[:, j], 3)] for j in range(2)]
    for key in ("upper", "lower"):
        arr = np.array([s[key] for s in secs])
        smooth[key] = [[float(x) for x in np.polyfit(rr, arr[:, i], 2)] for i in range(NX)]
    write_json(Path(out), {
        "schema": "935-horizontal-fan-cad-twin/blade/1",
        "scan_sha256": ROTOR_SCAN_SHA256,
        "frame": "params/frame.json",
        "blade_count": BLADE_COUNT,
        "tip_radius_mm": round(tip_r, 3),
        "tip_radius_basis": "circle fitted to the tip-face density peak (+-0.9 mm); per-blade tips scatter by about +-0.5 mm",
        "tip_circle_centre_xy_mm": [round(x, 3) for x in tip_centre],
        "root": "first station at r = 93 mm, clear of the blade-to-drum fillet; the fillet itself is not fitted yet",
        "leading_edge": "negative-s, low-z end (hypothesis H-FLOW-DIRECTION)",
        "blade_angular_offsets_deg": [round(float(np.degrees(o)), 4) for o in offsets],
        "chord_stations_x": [round(float(x), 5) for x in X],
        "sections": [{
            "r_mm": round(s["r"], 3), "points": s["points"], "chord_mm": round(s["chord"], 3),
            "stagger_from_tangential_deg": round(s["stagger_deg"], 3),
            "le_sz_mm": [round(float(x), 3) for x in s["le_sz"]], "te_sz_mm": [round(float(x), 3) for x in s["te_sz"]],
            "upper_mm": [round(float(x), 3) for x in s["upper"]], "lower_mm": [round(float(x), 3) for x in s["lower"]],
            "max_thickness_mm": round(float(np.max(s["upper"] - s["lower"])), 3),
            "interpolated_stations": s["interpolated_stations"],
            "pooled_rms_mm": round(s["pooled_rms"], 3), "worst_blade_rms_mm": round(s["per_blade_rms_max"], 3),
        } for s in secs],
        "radial_polynomials": {"note": "numpy.polyfit coefficients in r (mm), highest power first", **smooth},
    })
    for s in secs:
        print(f"r={s['r']:6.1f} n={s['points']:5d} chord={s['chord']:6.2f} stagger={s['stagger_deg']:6.2f} tmax={np.max(s['upper']-s['lower']):5.2f} interp={s['interpolated_stations']} rms={s['pooled_rms']:.3f} worst={s['per_blade_rms_max']:.3f}")
    print("tip r", round(tip_r, 2), "offsets deg", np.round(np.degrees(offsets), 3))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:]))
