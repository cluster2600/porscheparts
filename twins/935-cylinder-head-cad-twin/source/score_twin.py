"""Independent scorecard: how much of the scan a twin surface explains.

This checker imports nothing from the twin producers. It reads the original
OBJ (and verifies its SHA-256), applies the declared frame from frame.json,
re-derives the hardware exclusion from the declared stud rods, and measures
distances with NVIDIA Warp BVH queries. A trimesh closest-point oracle
cross-checks a random subsample.

Metrics
  scan -> twin  area-weighted distance of every non-hardware scan facet
                centroid to the twin surface (fidelity on observed geometry);
  twin -> scan  share of twin surface area within SUPPORT_MM of the scan
                ("observed-supported") versus farther ("inferred").

Usage: score_twin.py SCAN.obj FRAME.json TWIN_SURFACE(.stl|.ply) OUT.json [LABEL]
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

SCAN_SHA256 = "4623d5d3b73fe3d03ca988a47543a8dd1be7834d3040e6f7efd1e1e95c766486"
SUPPORT_MM = 0.2
THRESHOLDS = (0.05, 0.1, 0.2, 0.5, 1.0)
Z_BANDS = (("deck_zone", -5.0, 12.0), ("fin_zone", 12.0, 78.0), ("cam_zone", 78.0, 200.0))


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def tri_props(v, f):
    t = v[f]
    c = t.mean(axis=1)
    a = 0.5 * np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]), axis=1)
    return c, a


def warp_distances(points, mesh_v, mesh_f):
    import warp as wp

    wp.config.quiet = True
    wp.init()
    device = "cpu"

    @wp.kernel
    def closest(mesh: wp.uint64, pts: wp.array(dtype=wp.vec3), out: wp.array(dtype=float)):
        i = wp.tid()
        p = pts[i]
        q = wp.mesh_query_point_no_sign(mesh, p, 1.0e6)
        if q.result:
            out[i] = wp.length(p - wp.mesh_eval_position(mesh, q.face, q.u, q.v))
        else:
            out[i] = -1.0

    m = wp.Mesh(points=wp.array(mesh_v.astype(np.float32), dtype=wp.vec3, device=device),
                indices=wp.array(mesh_f.astype(np.int32).ravel(), dtype=wp.int32, device=device))
    # Query in float32 relative to the mesh frame; coordinates are within +-300 mm,
    # so float32 spacing is below 4e-5 mm.
    pts = wp.array(points.astype(np.float32), dtype=wp.vec3, device=device)
    out = wp.zeros(len(points), dtype=float, device=device)
    wp.launch(closest, dim=len(points), inputs=[m.id, pts, out], device=device)
    return out.numpy().astype(np.float64)


def weighted_percentiles(d, w, qs):
    o = np.argsort(d)
    cw = np.cumsum(w[o]) / w.sum()
    return {f"p{int(q)}": round(float(d[o][min(len(o) - 1, np.searchsorted(cw, q / 100.0))]), 4) for q in qs}


def summary(d, w):
    out = {"area_mm2": round(float(w.sum()), 1)}
    out.update(weighted_percentiles(d, w, (50, 90, 95, 99)))
    out["max_mm"] = round(float(d.max()), 4)
    out["area_share_within_mm"] = {str(t): round(float(w[d <= t].sum() / w.sum()), 5) for t in THRESHOLDS}
    return out


def hardware_mask(cen, frame):
    mask = np.zeros(len(cen), dtype=bool)
    for rods in frame["rods"].values():
        for r in rods:
            ax = np.array(r["axis"], dtype=float)
            if not (3.0 <= r["radius_mm"] <= 4.5 and r["radial_residual"]["rms_mm"] <= 1.0
                    and r["protrusion_mm"] >= 12.0 and np.abs(ax).max() > 0.99):
                continue
            ax /= np.linalg.norm(ax)
            c0 = np.array(r["point_on_axis"])
            t_base = float((np.array(r["base_point"]) - c0) @ ax)
            d = cen - c0
            t = d @ ax
            radial = np.linalg.norm(d - np.outer(t, ax), axis=1)
            mask |= (radial < r["radius_mm"] + 0.8) & (t > t_base - 1.5)
            # Beyond the height from which the rod was fitted, its whole cluster is hardware:
            # the scanned studs are smeared shells, wider than their fitted cylinder.
            mask |= (radial < r["radius_mm"] + r["radial_residual"]["max_mm"] + 0.05) & (t > t_base + 6.0)
    return mask


def main(scan, frame_path, twin, out, label="twin"):
    import trimesh

    t0 = time.time()
    if sha256(scan) != SCAN_SHA256:
        raise SystemExit("scan hash mismatch")
    frame = json.loads(Path(frame_path).read_text())
    sm = trimesh.load(scan, process=False, force="mesh")
    rot = np.array(frame["rotation_scan_to_twin_rows"])
    sv = (np.asarray(sm.vertices, dtype=np.float64) - np.array(frame["origin_scan"])) @ rot.T
    sf = np.asarray(sm.faces, dtype=np.int64)
    s_cen, s_area = tri_props(sv, sf)
    hw = hardware_mask(s_cen, frame)

    tm = trimesh.load(twin, process=False, force="mesh")
    tv = np.asarray(tm.vertices, dtype=np.float64)
    tf = np.asarray(tm.faces, dtype=np.int64)
    t_cen, t_area = tri_props(tv, tf)

    d_scan = warp_distances(s_cen, tv, tf)
    keep_f = sf[~hw]
    used = np.unique(keep_f)
    remap = -np.ones(len(sv), dtype=np.int64)
    remap[used] = np.arange(len(used))
    d_twin = warp_distances(t_cen, sv[used], remap[keep_f])

    rng = np.random.default_rng(935)
    idx = rng.choice(np.where(~hw)[0], size=min(5000, int((~hw).sum())), replace=False)
    _, d_oracle, _ = trimesh.proximity.closest_point(trimesh.Trimesh(tv, tf, process=False), s_cen[idx])
    oracle_diff = float(np.abs(d_oracle - d_scan[idx]).max())

    obs = ~hw
    report = {
        "schema": "935-cad-twin-scorecard/1",
        "label": label,
        "twin_surface_sha256": sha256(twin),
        "twin_triangles": int(len(tf)),
        "scan_sha256": SCAN_SHA256,
        "checker": "score_twin.py (independent of producers); NVIDIA Warp mesh_query_point_no_sign on CPU",
        "hardware_scan_area_excluded_mm2": round(float(s_area[hw].sum()), 1),
        "scan_to_twin": summary(d_scan[obs], s_area[obs]),
        "scan_to_twin_by_zone": {
            name: summary(d_scan[obs & (s_cen[:, 2] >= lo) & (s_cen[:, 2] < hi)],
                          s_area[obs & (s_cen[:, 2] >= lo) & (s_cen[:, 2] < hi)])
            for name, lo, hi in Z_BANDS
        },
        "twin_to_scan": summary(d_twin, t_area),
        "twin_area_observed_supported_share": round(float(t_area[d_twin <= SUPPORT_MM].sum() / t_area.sum()), 5),
        "twin_area_inferred_mm2": round(float(t_area[d_twin > SUPPORT_MM].sum()), 1),
        "support_threshold_mm": SUPPORT_MM,
        "oracle_check": {"samples": int(len(idx)), "max_abs_difference_mm": round(oracle_diff, 7),
                         "passed": bool(oracle_diff < 1e-3)},
        "seconds": round(time.time() - t0, 1),
        "limits": "distances to the acquired surface only; says nothing about unobserved geometry, physical "
                  "calibration or function",
    }
    Path(out).write_text(json.dumps(report, indent=2) + "\n")
    s = report["scan_to_twin"]
    print(label, "scan->twin p95", s["p95"], "within 0.1mm", s["area_share_within_mm"]["0.1"],
          "| twin supported", report["twin_area_observed_supported_share"], "| oracle", report["oracle_check"])


if __name__ == "__main__":
    main(*sys.argv[1:6])
