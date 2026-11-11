"""Phase 1b: bare-head occupancy field from the open scan.

1. Moves the unmodified scan into the twin frame (frame.json).
2. Separates hardware: facets on fitted studs beyond their local seating face
   are removed and written to a separate hardware mesh.
3. Evaluates the generalized winding number (libigl fast winding number) on a
   regular grid. w > 0.5 is inside. Where the scan never observed a surface
   (fin roots, deep passages) the field is ambiguous; the voxels with
   0.2 < w < 0.8 are counted and reported as inferred, never as observed.

Usage: occupancy.py PRIVATE_DIR PARAMS_DIR [PITCH_MM]
Outputs (private): occupancy-wn.npy (float32, x,y,z), occupancy-grid.json,
bare-scan-twin.npz, hardware-twin.npz. Output (params): occupancy-summary.json.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from twin_common import face_geometry, load_scan, write_json  # noqa: E402

STUD_RADIUS_RANGE = (3.0, 4.5)  # mm; M8-class threaded rods fit 6.5-7.3 mm
STUD_MAX_RADIAL_RMS = 1.0
STUD_MIN_PROTRUSION = 12.0
CLEAR = 0.8  # mm radial clearance used to collect stud facets
# fit_frame.py fits each rod on every vertex standing more than this far beyond
# its face, so above that height the rod's own cluster reaches its radius plus
# its largest radial residual. Everything inside that envelope is the rod: the
# studs are scanned as smeared shells up to 3.7 mm off their fitted cylinder,
# and the 0.8 mm rule alone left 8,881 of their facets in the bare head
# (measured on 2026-11-11: slivers up to 26 mm above the cam face).
ROD_CLUSTER_CLEARANCE = 6.0
ENVELOPE_MARGIN = 0.05


def select_studs(frame):
    studs = []
    for group, rods in frame["rods"].items():
        for r in rods:
            ok = (
                STUD_RADIUS_RANGE[0] <= r["radius_mm"] <= STUD_RADIUS_RANGE[1]
                and r["radial_residual"]["rms_mm"] <= STUD_MAX_RADIAL_RMS
                and r["protrusion_mm"] >= STUD_MIN_PROTRUSION
                and abs(max(r["axis"], key=abs)) > 0.99
            )
            studs.append({"group": group, "accepted": bool(ok), **r})
    return studs


def local_seat(xyz_c, n, area, axis, centre, r):
    """Level along the axis of the seating face around the stud (facets whose
    normal is parallel to the axis, in an annulus just outside the stud)."""

    d = xyz_c - centre
    t = d @ axis
    radial = np.linalg.norm(d - np.outer(t, axis), axis=1)
    sel = (radial > r + 1.0) & (radial < r + 5.0) & ((n @ axis) > 0.97)
    if sel.sum() < 20:
        return None
    w = area[sel]
    order = np.argsort(t[sel])
    cw = np.cumsum(w[order]) / w.sum()
    return float(t[sel][order][np.searchsorted(cw, 0.5)])


def main(private, params, pitch="0.25"):
    import igl

    private, params = Path(private), Path(params)
    pitch = float(pitch)
    frame = json.loads((params / "frame.json").read_text())
    v, f = load_scan(None, private)
    rot = np.array(frame["rotation_scan_to_twin_rows"])
    origin = np.array(frame["origin_scan"])
    xyz = (v - origin) @ rot.T
    cen, n, area = face_geometry(xyz, f)

    studs = select_studs(frame)
    remove = np.zeros(len(f), dtype=bool)
    for s in studs:
        if not s["accepted"]:
            continue
        ax = np.array(s["axis"], dtype=float)
        ax /= np.linalg.norm(ax)
        # rod geometry was fitted in twin coordinates
        c0 = np.array(s["point_on_axis"], dtype=float)
        seat = local_seat(cen, n, area, ax, c0, s["radius_mm"])
        base = np.array(s["base_point"], dtype=float)
        t_seat = seat if seat is not None else float((base - c0) @ ax)
        d = cen - c0
        t = d @ ax
        radial = np.linalg.norm(d - np.outer(t, ax), axis=1)
        sel = (radial < s["radius_mm"] + CLEAR) & (t > t_seat + 0.15)
        t_base = float((base - c0) @ ax)
        envelope = s["radius_mm"] + s["radial_residual"]["max_mm"] + ENVELOPE_MARGIN
        cluster = (radial < envelope) & (t > t_base + ROD_CLUSTER_CLEARANCE) & ~sel
        s["removed_facets_beyond_the_cylinder"] = int(cluster.sum())
        sel |= cluster
        remove |= sel
        s["seat_level_along_axis"] = round(t_seat, 4)
        s["seat_from"] = "annulus facets" if seat is not None else "fitted face plane"
        s["removed_facets"] = int(sel.sum())

    keep_f = f[~remove]
    np.savez(private / "bare-scan-twin.npz", v=xyz, f=keep_f)
    np.savez(private / "hardware-twin.npz", v=xyz, f=f[remove])

    used = np.unique(keep_f)
    lo = np.floor((xyz[used].min(axis=0) - 1.5) / pitch) * pitch
    hi = np.ceil((xyz[used].max(axis=0) + 1.5) / pitch) * pitch
    xs = np.arange(lo[0], hi[0] + pitch / 2, pitch)
    ys = np.arange(lo[1], hi[1] + pitch / 2, pitch)
    zs = np.arange(lo[2], hi[2] + pitch / 2, pitch)
    gx, gy = np.meshgrid(xs, ys, indexing="ij")
    q2 = np.column_stack((gx.ravel(), gy.ravel()))
    wn = np.lib.format.open_memmap(private / "occupancy-wn.npy", mode="w+", dtype=np.float32,
                                   shape=(len(xs), len(ys), len(zs)))
    bvh = igl.FastWindingNumberBVH()
    bvh.init(np.ascontiguousarray(xyz), np.ascontiguousarray(keep_f))
    t0 = time.time()
    amb = np.zeros(len(zs))
    for k, z in enumerate(zs):
        q = np.column_stack((q2, np.full(len(q2), z)))
        w = np.asarray(bvh.winding_number(q)).reshape(gx.shape)
        wn[:, :, k] = w
        amb[k] = float(((w > 0.2) & (w < 0.8)).sum())
        if k % 40 == 0:
            print(f"slice {k}/{len(zs)} z={z:.2f} {time.time() - t0:.0f}s", flush=True)
    wn.flush()
    inside = 0
    for k in range(len(zs)):
        inside += int((wn[:, :, k] > 0.5).sum())
    grid = {"pitch_mm": pitch, "x0": float(xs[0]), "y0": float(ys[0]), "z0": float(zs[0]),
            "shape": [len(xs), len(ys), len(zs)], "array": "occupancy-wn.npy", "order": "x,y,z"}
    write_json(private / "occupancy-grid.json", grid)
    summary = {
        "schema": "935-cad-twin-occupancy/1",
        "method": "libigl fast_winding_number on the bare scan (stud facets removed); inside = w > 0.5",
        "grid": {k: grid[k] for k in ("pitch_mm", "x0", "y0", "z0", "shape")},
        "scan_facets": int(len(f)),
        "hardware_facets_removed": int(remove.sum()),
        "studs": [{k: s[k] for k in ("group", "accepted", "radius_mm", "protrusion_mm", "axis", "point_on_axis",
                                     "seat_level_along_axis", "seat_from", "removed_facets",
                                     "removed_facets_beyond_the_cylinder") if k in s}
                  for s in studs],
        "inside_volume_mm3": round(inside * pitch ** 3, 1),
        "ambiguous_voxels_0p2_0p8": int(amb.sum()),
        "ambiguous_volume_mm3": round(float(amb.sum()) * pitch ** 3, 1),
        "seconds": round(time.time() - t0, 1),
    }
    write_json(params / "occupancy-summary.json", summary)
    print(json.dumps({k: summary[k] for k in ("hardware_facets_removed", "inside_volume_mm3", "ambiguous_volume_mm3", "seconds")}))


if __name__ == "__main__":
    main(*sys.argv[1:])
