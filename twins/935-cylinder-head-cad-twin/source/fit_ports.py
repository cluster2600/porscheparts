"""v1 feature tree, ports and other enclosed cavities: centreline and cross-sections.

The body stack models every wall as a vertical prism, so the curved port walls
come out as a staircase. This script fits each port as a loft instead:

  1. cavities: material mask of the occupancy field at 1 mm, closed with a
     CLOSE_MM ball and opened with an OPEN_MM ball; what the closing adds is the
     set of enclosed voids. A port is a void that reaches a flange face and
     exceeds PORT_MIN_VOLUME_MM3; every other void above CAVITY_MIN_VOLUME_MM3
     is fitted the same way and named cavity_<rank by volume>;
  2. centreline: geodesic distance inside the void from its flange end,
     centroids of the distance shells, smoothed and resampled every STEP_MM;
  3. sections: in the plane normal to the centreline at each station, RAYS rays
     are marched through the 0.25 mm occupancy field to the wall (w = 0.5);
  4. evidence: a wall point counts as observed when an acquired scan facet lies
     within OBSERVED_MM of it. The rest is winding-number closure, i.e. the
     H04 hypothesis, and is reported as such per station.

Section profiles are geometry and stay private (PRIVATE/port-sections.npz).
PARAMS/port-fit.json receives scalars only.

Usage: fit_ports.py PRIVATE_DIR PARAMS_DIR
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from twin_common import face_geometry, write_json  # noqa: E402

COARSE = 4
CLOSE_MM = 26.0
OPEN_MM = 5.0
PORT_MIN_VOLUME_MM3 = 30000.0
CAVITY_MIN_VOLUME_MM3 = 5000.0
MIN_LOFT_STATIONS = 4
FLANGE_REACH_MM = 10.0
STEP_MM = 3.0
RAYS = 48
RAY_MAX_MM = 45.0
RAY_STEP_MM = 0.125
OBSERVED_MM = 0.35
SPACING_MAX = 1.1


def flange_levels(cen, n, area):
    """Y of the two flange faces: largest planar area facing +Y and -Y."""

    out = {}
    for sign, name in ((1, "y_plus"), (-1, "y_minus")):
        s = sign * n[:, 1] > 0.98
        e = np.arange(-140.0, 140.5, 0.5)
        h, _ = np.histogram(cen[s, 1], bins=e, weights=area[s])
        k = int(np.argmax(np.convolve(h, np.ones(3), mode="same")))
        out[name] = float(e[k] + 0.25)
    return out


def cavities(wn, grid):
    from scipy import ndimage as ndi

    h = grid["pitch_mm"] * COARSE
    pad = int(CLOSE_MM / h) + 2
    m = np.pad(np.asarray(wn[::COARSE, ::COARSE, ::COARSE]) > 0.5, pad, constant_values=False)
    closed = ndi.distance_transform_edt(ndi.distance_transform_edt(~m) * h <= CLOSE_MM) * h > CLOSE_MM
    fill = closed & ~m
    core = ndi.distance_transform_edt(fill) * h > OPEN_MM
    void = (ndi.distance_transform_edt(~core) * h <= OPEN_MM) & fill
    lab, count = ndi.label(void)
    org = np.array([grid["x0"], grid["y0"], grid["z0"]]) - pad * h
    return lab, count, org, h


def centreline(mask, org, h, flange_y):
    """Stations along the void, ordered from the flange end.

    A cavity that reaches no flange starts from one end of its principal axis.
    Returns None when the void is too short to carry a centreline.
    """

    from scipy import ndimage as ndi
    from scipy.interpolate import splev, splprep

    idx = np.argwhere(mask)
    if flange_y is None:
        q = (idx - idx.mean(axis=0)) * h
        along = q @ np.linalg.svd(q, full_matrices=False)[2][0]
        end = along >= along.max() - 3.0
    else:
        y = org[1] + idx[:, 1] * h
        end = np.abs(y - flange_y) <= np.abs(y - flange_y).min() + 3.0
    front = np.zeros_like(mask)
    front[tuple(idx[end].T)] = True
    dist = np.full(mask.shape, -1, dtype=np.int32)
    dist[front] = 0
    step, struct = 0, np.ones((3, 3, 3), dtype=bool)
    while True:
        grown = ndi.binary_dilation(front, structure=struct) & mask & (dist < 0)
        if not grown.any():
            break
        step += 1
        dist[grown] = step
        front = grown
    pts = []
    for s in range(0, step + 1, 3):
        shell = (dist >= s) & (dist < s + 3)
        lab, count = ndi.label(shell)
        if count == 0:
            continue
        if count > 1:
            shell = lab == 1 + int(np.argmax(ndi.sum(shell, lab, range(1, count + 1))))
        pts.append(org + np.argwhere(shell).mean(axis=0) * h)
    pts = np.array(pts)
    if len(pts) < 5:
        return None
    tck, _ = splprep(pts.T, s=len(pts) * 1.0)
    fine = np.array(splev(np.linspace(0, 1, 400), tck)).T
    arc = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(fine, axis=0), axis=1))])
    u = np.interp(np.arange(0.0, arc[-1], STEP_MM), arc, np.linspace(0, 1, 400))
    c = np.array(splev(u, tck)).T
    t = np.array(splev(u, tck, der=1)).T
    return c, t / np.linalg.norm(t, axis=1)[:, None]


def section(sub, sub_org, pitch, centre, tangent):
    """Wall radius along RAYS rays in the plane normal to the tangent."""

    from scipy.ndimage import map_coordinates

    ref = np.array([1.0, 0.0, 0.0])
    u = ref - (ref @ tangent) * tangent
    u /= np.linalg.norm(u)
    v = np.cross(tangent, u)
    ang = np.linspace(0.0, 2 * np.pi, RAYS, endpoint=False)
    dirs = np.outer(np.cos(ang), u) + np.outer(np.sin(ang), v)
    r = np.arange(0.0, RAY_MAX_MM, RAY_STEP_MM)
    p = centre[None, None, :] + r[None, :, None] * dirs[:, None, :]
    w = map_coordinates(sub, ((p - sub_org) / pitch).reshape(-1, 3).T, order=1, mode="nearest").reshape(RAYS, len(r))
    radii = np.full(RAYS, np.nan)
    if w[:, 0].max() > 0.5:
        return radii, u, v, False
    for k in range(RAYS):
        hit = np.argmax(w[k] > 0.5)
        if w[k, hit] > 0.5:
            a, b = w[k, hit - 1], w[k, hit]
            radii[k] = r[hit - 1] + RAY_STEP_MM * (0.5 - a) / (b - a)
    return radii, u, v, True


def main(private, params):
    from scipy import ndimage as ndi
    from scipy.spatial import cKDTree

    private, params = Path(private), Path(params)
    grid = json.loads((private / "occupancy-grid.json").read_text())
    wn = np.load(private / grid["array"], mmap_mode="r")
    pitch = grid["pitch_mm"]
    bare = np.load(private / "bare-scan-twin.npz")
    cen, n, area = face_geometry(bare["v"], bare["f"])
    tree = cKDTree(cen)
    flanges = flange_levels(cen, n, area)
    lab, count, org, h = cavities(wn, grid)
    vol = ndi.sum(lab > 0, lab, range(1, count + 1)) * h ** 3
    found, ports, store = [], [], {}
    for i in np.argsort(-vol):
        idx = np.argwhere(lab == i + 1)
        lo, hi = org + idx.min(axis=0) * h, org + idx.max(axis=0) * h
        rec = {"volume_mm3": round(float(vol[i]), 0), "bbox_min": lo.round(1).tolist(), "bbox_max": hi.round(1).tolist()}
        side = "y_plus" if hi[1] >= flanges["y_plus"] - FLANGE_REACH_MM else \
            "y_minus" if lo[1] <= flanges["y_minus"] + FLANGE_REACH_MM else None
        rec["port"] = bool(side and vol[i] >= PORT_MIN_VOLUME_MM3)
        if vol[i] < CAVITY_MIN_VOLUME_MM3:
            continue
        found.append(rec)
        name = f"port_{side}" if rec["port"] else f"cavity_{len(found)}"
        rec["name"] = name
        line = centreline(lab == i + 1, org, h, flanges[side] if rec["port"] else None)
        if line is None:
            rec["loft"] = "none: too short for a centreline"
            continue
        c, t = line
        lo_i = np.maximum(((lo - RAY_MAX_MM - np.array([grid["x0"], grid["y0"], grid["z0"]])) / pitch).astype(int), 0)
        hi_i = np.minimum(((hi + RAY_MAX_MM - np.array([grid["x0"], grid["y0"], grid["z0"]])) / pitch).astype(int) + 1,
                          grid["shape"])
        sub = np.asarray(wn[lo_i[0]:hi_i[0], lo_i[1]:hi_i[1], lo_i[2]:hi_i[2]], dtype=np.float32)
        sub_org = np.array([grid["x0"], grid["y0"], grid["z0"]]) + lo_i * pitch
        stations, keep = [], []
        for cj, tj in zip(c, t):
            radii, u, v, ok = section(sub, sub_org, pitch, cj, tj)
            if ok and np.isfinite(radii).all():
                # Recentre once on the section's area centroid, then re-measure.
                ang = np.linspace(0.0, 2 * np.pi, RAYS, endpoint=False)
                x, y = radii * np.cos(ang), radii * np.sin(ang)
                cross = x * np.roll(y, -1) - np.roll(x, -1) * y
                a = cross.sum() / 2
                gx = ((x + np.roll(x, -1)) * cross).sum() / (6 * a)
                gy = ((y + np.roll(y, -1)) * cross).sum() / (6 * a)
                cj = cj + gx * u + gy * v
                radii, u, v, ok = section(sub, sub_org, pitch, cj, tj)
            closed = bool(ok and np.isfinite(radii).all())
            st = {"centre": cj.round(2).tolist(), "closed": closed}
            if closed:
                ang = np.linspace(0.0, 2 * np.pi, RAYS, endpoint=False)
                wall = cj + (radii * np.cos(ang))[:, None] * u + (radii * np.sin(ang))[:, None] * v
                seen = tree.query(wall)[0] <= OBSERVED_MM
                sec_area = 0.5 * float((radii * np.roll(radii, -1)).sum() * np.sin(2 * np.pi / RAYS))
                st.update(area_mm2=round(sec_area, 1), equivalent_diameter_mm=round(2 * (sec_area / np.pi) ** 0.5, 2),
                          radius_min_mm=round(float(radii.min()), 2), radius_max_mm=round(float(radii.max()), 2),
                          observed_share=round(float(seen.mean()), 3))
                keep.append((cj, tj, u, v, radii, seen))
            else:
                keep.append(None)
            stations.append(st)
        # The loft uses the longest run of consecutive closed stations.
        runs, start = [], None
        for j, k in enumerate(keep + [None]):
            if k is not None and start is None:
                start = j
            if k is None and start is not None:
                runs.append((start, j))
                start = None
        if not runs:
            rec["loft"] = "none: no closed section"
            continue
        a, b = max(runs, key=lambda r: r[1] - r[0])
        # Recentring moves a station sideways where the section stops being a
        # tube (valve pocket). The loft ends before the first such jump.
        for j in range(a + 1, b):
            if np.linalg.norm(keep[j][0] - keep[j - 1][0]) > SPACING_MAX * STEP_MM:
                b = j
                break
        if b - a < MIN_LOFT_STATIONS:
            rec["loft"] = f"none: only {b - a} consecutive closed sections"
            continue
        rec["loft"] = "fitted"
        store[name] = {key: np.array([k[q] for k in keep[a:b]]) for q, key in
                       enumerate(("centre", "tangent", "u", "v", "radii", "observed"))}
        obs = store[name]["observed"]
        ports.append({
            "name": name, "flange_y_mm": round(flanges[side], 2) if rec["port"] else None, "cavity": rec,
            "stations": len(stations), "closed_stations": int(sum(s["closed"] for s in stations)),
            "loft_station_range": [a, b], "loft_length_mm": round((b - a - 1) * STEP_MM, 1),
            "wall_points_observed_share": round(float(obs.mean()), 3),
            "stations_fully_inferred": int((obs.mean(axis=1) < 0.05).sum()),
            "station_detail": stations,
        })
    np.savez_compressed(private / "port-sections.npz", **{f"{p}__{k}": v for p, d in store.items() for k, v in d.items()})
    write_json(params / "port-fit.json", {
        "schema": "935-cad-twin-port-fit/1",
        "method": {"coarse_pitch_mm": h, "close_mm": CLOSE_MM, "open_mm": OPEN_MM, "station_step_mm": STEP_MM,
                   "rays": RAYS, "observed_within_mm": OBSERVED_MM,
                   "station_spacing_max_ratio": SPACING_MAX},
        "evidence_class": "sections of the winding-number field; observed only where an acquired facet lies on the "
                          "wall point, otherwise hypothesis H04. No physical calibration.",
        "flange_faces_y_mm": flanges,
        "cavities_over_5000_mm3": found,
        "ports": ports,
    })
    for p in ports:
        print(p["name"], "stations", p["stations"], "closed", p["closed_stations"], "loft", p["loft_station_range"],
              "length", p["loft_length_mm"], "observed", p["wall_points_observed_share"],
              "fully inferred stations", p["stations_fully_inferred"])
        print("   eq. diameter:", " ".join(f"{s.get('equivalent_diameter_mm', 0):.0f}" if s["closed"] else "x"
                                           for s in p["station_detail"]))
        print("   observed:    ", " ".join(f"{int(100 * s['observed_share']):d}" if s["closed"] else "x"
                                           for s in p["station_detail"]))


if __name__ == "__main__":
    main(*sys.argv[1:3])
