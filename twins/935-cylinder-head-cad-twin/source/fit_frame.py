"""Phase 1: datum frame and attached hardware of the 935 head scan.

Fits, from acquired scan facets only:
  * the deck (combustion) plane, which fixes the bore axis Z;
  * the register and chamber-shoulder circles, which fix the origin;
  * the intake/exhaust flange planes and the cam-housing face;
  * every rod protruding beyond those faces (studs = hardware, not head).

Twin frame: origin on the deck plane at the register centre, Z along the bore
axis pointing from the deck into the head (toward the cam housing), X along
the fin-normal hint A, Y = Z x X. Units: mm.

Usage: fit_frame.py SCAN.obj PRIVATE_DIR PARAMS_DIR
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
from twin_common import (  # noqa: E402
    B_HINT, C_HINT, SCAN_SHA256, face_geometry, fit_circle_2d, fit_plane, load_scan, stats, write_json,
)


def orthonormal(c, b_hint):
    a = np.cross(b_hint, c)
    a /= np.linalg.norm(a)
    b = np.cross(c, a)
    return a, b / np.linalg.norm(b), c


def plane_record(name, cen, n, area, mask, axis, sign):
    nrm, pt, res = fit_plane(cen[mask], area[mask])
    if np.dot(nrm, axis) * sign < 0:
        nrm = -nrm
    return {
        "name": name,
        "normal_scan": nrm.tolist(),
        "point_scan": pt.tolist(),
        "area_mm2": round(float(area[mask].sum()), 1),
        "facets": int(mask.sum()),
        "residual": stats(res),
    }, nrm, pt


def rods_beyond(points, axis_index, limit, outward, origin_scale=0.5, clearance=6.0):
    """Connected clusters of vertices beyond a face, measured along one axis.

    Only points more than `clearance` mm beyond the face are clustered, so low
    pads and bosses on the face do not merge with the rods standing on them.
    """

    sel = points[:, axis_index] * outward > limit * outward + clearance
    q = points[sel]
    if len(q) == 0:
        return []
    other = [i for i in range(3) if i != axis_index]
    lo = q[:, other].min(axis=0)
    ij = np.floor((q[:, other] - lo) / origin_scale).astype(int)
    grid = np.zeros(ij.max(axis=0) + 1, dtype=bool)
    grid[ij[:, 0], ij[:, 1]] = True
    grid = ndimage.binary_dilation(grid, iterations=2)
    lab, nlab = ndimage.label(grid)
    pl = lab[ij[:, 0], ij[:, 1]]
    rods = []
    for k in range(1, nlab + 1):
        p = q[pl == k]
        if len(p) < 200:
            continue
        mu = p.mean(axis=0)
        _, s, vt = np.linalg.svd(p - mu, full_matrices=False)
        ax = vt[0] if abs(vt[0][axis_index]) > 0.5 else np.eye(3)[axis_index]
        if ax[axis_index] * outward < 0:
            ax = -ax
        e1 = np.cross(ax, [1.0, 0, 0] if abs(ax[0]) < 0.9 else [0, 1.0, 0])
        e1 /= np.linalg.norm(e1)
        e2 = np.cross(ax, e1)
        xy = np.column_stack(((p - mu) @ e1, (p - mu) @ e2))
        c2, r, res = fit_circle_2d(xy)
        centre = mu + c2[0] * e1 + c2[1] * e2
        t = (p - centre) @ ax
        tip = centre + t.max() * ax
        base_t = (limit - centre[axis_index]) / ax[axis_index]
        rods.append({
            "points": int(len(p)),
            "axis": np.round(ax, 5).tolist(),
            "point_on_axis": np.round(centre, 4).tolist(),
            "radius_mm": round(r, 4),
            "radial_residual": stats(res),
            "base_point": np.round(centre + base_t * ax, 4).tolist(),
            "tip_point": np.round(tip, 4).tolist(),
            "protrusion_mm": round(float(t.max() - base_t), 3),
            "pca_extent_mm": np.round(2 * s / np.sqrt(len(p)) * np.sqrt(3), 2).tolist(),
        })
    return rods


def main(scan, private, params):
    v, f = load_scan(Path(scan), Path(private))
    cen, n, area = face_geometry(v, f)

    a, b, c = orthonormal(C_HINT, B_HINT)
    abc = cen @ np.vstack((a, b, c)).T
    nc = n @ c

    deck_mask = (nc > 0.995) & (abc[:, 2] > -88.0) & (abc[:, 2] < -86.0)
    deck, c_fit, deck_pt = plane_record("deck", cen, n, area, deck_mask, c, +1)

    a, b, c = orthonormal(c_fit, B_HINT)
    frame_abc = np.vstack((a, b, c))
    abc = cen @ frame_abc.T
    nb, nc = n @ b, n @ c
    vabc = v @ frame_abc.T
    deck_c = float(deck_pt @ c)

    planes = [deck]
    intake_mask = (nb > 0.99) & (abc[:, 1] > -63.0) & (abc[:, 1] < -60.5)
    rec, _, p_int = plane_record("flange_high_B", cen, n, area, intake_mask, b, +1)
    planes.append(rec)
    exhaust_mask = (nb < -0.99) & (abc[:, 1] > -252.5) & (abc[:, 1] < -250.0)
    rec, _, p_exh = plane_record("flange_low_B", cen, n, area, exhaust_mask, b, -1)
    planes.append(rec)
    cam_mask = (nc < -0.995) & (abc[:, 2] > -175.0) & (abc[:, 2] < -170.5)
    rec, _, p_cam = plane_record("cam_face_region", cen, n, area, cam_mask, c, -1)
    levels = abc[cam_mask, 2]
    hist, edges = np.histogram(levels, bins=np.arange(-175.0, -170.49, 0.25), weights=area[cam_mask])
    rec["level_area_histogram_c"] = {f"{e + 0.125:.3f}": round(float(h), 1) for e, h in zip(edges[:-1], hist) if h > 5}
    planes.append(rec)
    for p in planes:
        nrm = np.array(p["normal_scan"])
        p["angle_to_frame_axis_deg"] = {
            ax: round(float(np.degrees(np.arccos(min(1.0, abs(nrm @ vec))))), 4)
            for ax, vec in (("A", a), ("B", b), ("C", c))
        }

    # Cylindrical bands near the deck: points whose facets are parallel to C.
    wall = (np.abs(nc) < 0.15) & (abc[:, 2] < deck_c) & (abc[:, 2] > deck_c - 8.0)
    deck_ab = abc[deck_mask][:, :2]
    guess = deck_ab.mean(axis=0)
    rings = []
    for name, r0 in (("register", 56.8), ("chamber_shoulder", 45.4)):
        sel = wall & (np.abs(np.hypot(abc[:, 0] - guess[0], abc[:, 1] - guess[1]) - r0) < 2.0)
        ctr, r, res = fit_circle_2d(abc[sel][:, :2])
        sel2 = wall & (np.abs(np.hypot(abc[:, 0] - ctr[0], abc[:, 1] - ctr[1]) - r) < 0.5)
        ctr, r, res = fit_circle_2d(abc[sel2][:, :2])
        cz = abc[sel2, 2]
        rings.append({
            "name": name,
            "centre_ab": np.round(ctr, 4).tolist(),
            "diameter_mm": round(2 * r, 4),
            "radial_residual": stats(res),
            "c_band": [round(float(cz.min()), 3), round(float(cz.max()), 3)],
            "depth_below_deck_mm": round(float(deck_c - cz.min()), 3),
            "facets": int(sel2.sum()),
        })
    reg = rings[0]
    origin = a * reg["centre_ab"][0] + b * reg["centre_ab"][1] + c * deck_c

    # Twin frame: X = A, Z = -C (into the head), Y = Z x X.
    ex, ez = a, -c
    ey = np.cross(ez, ex)
    rot = np.vstack((ex, ey, ez))
    xyz = (v - origin) @ rot.T

    def z_of(point_scan):
        return float((np.asarray(point_scan) - origin) @ ez)

    def y_of(point_scan):
        return float((np.asarray(point_scan) - origin) @ ey)

    cam_z = z_of(p_cam)
    y_high = y_of(p_int)
    y_low = y_of(p_exh)
    rods = {
        "beyond_cam_face": rods_beyond(xyz, 2, cam_z, +1),
        "beyond_flange_y_max": rods_beyond(xyz, 1, max(y_high, y_low), +1),
        "beyond_flange_y_min": rods_beyond(xyz, 1, min(y_high, y_low), -1),
    }

    frame = {
        "schema": "935-cad-twin-frame/1",
        "scan_sha256": SCAN_SHA256,
        "units": "mm (owner-confirmed 1 OBJ unit = 1 mm; no physical calibration)",
        "definition": "origin on deck plane at register centre; Z = bore axis into the head; X = fin-normal hint A orthogonalised; Y = Z x X",
        "origin_scan": np.round(origin, 6).tolist(),
        "rotation_scan_to_twin_rows": np.round(rot, 9).tolist(),
        "planes": planes,
        "rings": rings,
        "levels_twin": {
            "deck_z": 0.0,
            "cam_face_z": round(cam_z, 4),
            "flange_y_high_B": round(y_high, 4),
            "flange_y_low_B": round(y_low, 4),
        },
        "rods": rods,
        "bounds_twin": {"min": np.round(xyz.min(axis=0), 3).tolist(), "max": np.round(xyz.max(axis=0), 3).tolist()},
        "evidence": "acquired scan facets only; fits are geometric, not metrological calibration",
    }
    write_json(Path(params) / "frame.json", frame)
    np.save(Path(private) / "scan-twin-xyz.npy", xyz)
    print("deck", deck["residual"], "rings", [(r["name"], r["diameter_mm"], r["radial_residual"]["rms_mm"]) for r in rings])
    for k, rl in rods.items():
        print(k, [(round(r["radius_mm"] * 2, 2), r["protrusion_mm"], r["radial_residual"]["rms_mm"]) for r in rl])
    print("levels", frame["levels_twin"], "bounds", frame["bounds_twin"])
    for p in planes:
        print(p["name"], p["area_mm2"], p["residual"], p["angle_to_frame_axis_deg"])


if __name__ == "__main__":
    main(*sys.argv[1:4])
