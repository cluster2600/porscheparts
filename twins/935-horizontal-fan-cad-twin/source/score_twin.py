"""Independent scorecard: how much of the 935 rotor scan the CAD explains.

This checker imports nothing from the fitting or CAD programs. It reads the
original OBJ (SHA-256 checked), applies the declared frame from frame.json,
and measures exact point-to-triangle distances with NVIDIA Warp BVH queries
against a CAD tessellation.

Metrics
  scan -> CAD   area-weighted distance of every scan facet centroid to the
                CAD surface, overall and per zone (hub, blades, tip);
  CAD -> scan   share of CAD surface area within SUPPORT_MM of a scan facet
                ("observed-supported") versus farther ("inferred").

Scan facets farther than OUTLIER_MM from the CAD are counted separately as
unexplained (debris, flash, fixtures, or missing features), not averaged.

Usage: score_twin.py ROTOR.obj FRAME.json CAD.stl OUT.json [LABEL]
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

SCAN_SHA256 = "244d4caeb2c4ac4a692b650ec9d766bee2a8124335a0236a55a1d30c1b2b98ba"
SUPPORT_MM = 0.5
OUTLIER_MM = 3.0
THRESHOLDS = (0.1, 0.2, 0.3, 0.5, 1.0, 2.0)
ZONES = (("hub", 0.0, 88.0), ("blade_root_fillet", 88.0, 93.0), ("blades", 93.0, 134.0), ("tip", 134.0, 1e9))


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_obj(path):
    v, f = [], []
    with open(path) as fh:
        for line in fh:
            if line.startswith("v "):
                v.append(line.split()[1:4])
            elif line.startswith("f "):
                f.append([int(t.split("/")[0]) for t in line.split()[1:4]])
    return np.asarray(v, float), np.asarray(f, np.int64) - 1


def read_stl(path):
    data = Path(path).read_bytes()
    if data[:5] == b"solid" and b"facet" in data[:400]:
        tri = []
        for line in data.decode().splitlines():
            line = line.strip()
            if line.startswith("vertex"):
                tri.append(line.split()[1:4])
        t = np.asarray(tri, float).reshape(-1, 3, 3)
    else:
        n = int(np.frombuffer(data[80:84], np.uint32)[0])
        rec = np.frombuffer(data[84:84 + 50 * n], dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]))
        t = rec["v"].astype(float)
    verts, inv = np.unique(np.round(t.reshape(-1, 3), 6), axis=0, return_inverse=True)
    return verts, inv.reshape(-1, 3)


def tri_props(v, f):
    t = v[f]
    a = 0.5 * np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]), axis=1)
    return t.mean(axis=1), a


def distances(points, mesh_v, mesh_f):
    import warp as wp
    wp.config.quiet = True
    wp.init()

    @wp.kernel
    def closest(mesh: wp.uint64, pts: wp.array(dtype=wp.vec3), out: wp.array(dtype=float)):
        i = wp.tid()
        p = pts[i]
        q = wp.mesh_query_point_no_sign(mesh, p, 1.0e6)
        if q.result:
            c = wp.mesh_eval_position(mesh, q.face, q.u, q.v)
            out[i] = wp.length(p - c)
        else:
            out[i] = 1.0e6

    mesh = wp.Mesh(points=wp.array(mesh_v.astype(np.float32), dtype=wp.vec3, device="cpu"),
                   indices=wp.array(mesh_f.astype(np.int32).ravel(), dtype=int, device="cpu"))
    pts = wp.array(points.astype(np.float32), dtype=wp.vec3, device="cpu")
    out = wp.zeros(len(points), dtype=float, device="cpu")
    wp.launch(closest, dim=len(points), inputs=[mesh.id, pts, out], device="cpu")
    return out.numpy().astype(float)


def summarise(d, a):
    inl = d <= OUTLIER_MM
    res = {"area_mm2": round(float(a.sum()), 1), "unexplained_area_share": round(float(a[~inl].sum() / a.sum()), 4)}
    for t in THRESHOLDS:
        res[f"within_{t}mm"] = round(float(a[d <= t].sum() / a.sum()), 4)
    if inl.any():
        res["rms_explained_mm"] = round(float(np.sqrt(np.sum(a[inl] * d[inl] ** 2) / a[inl].sum())), 4)
        order = np.argsort(d[inl])
        cum = np.cumsum(a[inl][order]) / a[inl].sum()
        res["p50_mm"] = round(float(d[inl][order][np.searchsorted(cum, 0.5)]), 4)
        res["p95_mm"] = round(float(d[inl][order][np.searchsorted(cum, 0.95)]), 4)
    return res


def main(obj, frame_path, cad, out, label="cad"):
    if sha256(obj) != SCAN_SHA256:
        raise SystemExit("scan hash mismatch")
    frame = json.loads(Path(frame_path).read_text())
    rot, tr = np.asarray(frame["rotation"]), np.asarray(frame["translation_mm"])
    v, f = read_obj(obj)
    v = v @ rot.T + tr
    c, a = tri_props(v, f)
    ok = a > 0
    c, a = c[ok], a[ok]
    cv, cf = read_stl(cad)
    d = distances(c, cv, cf)
    r = np.hypot(c[:, 0], c[:, 1])
    report = {"schema": "935-horizontal-fan-cad-twin/scorecard/1", "label": label, "scan_sha256": SCAN_SHA256,
              "cad_sha256": sha256(cad), "support_mm": SUPPORT_MM, "outlier_mm": OUTLIER_MM,
              "scan_to_cad": {"all": summarise(d, a)}}
    for name, lo, hi in ZONES:
        m = (r >= lo) & (r < hi)
        report["scan_to_cad"][name] = summarise(d[m], a[m])
    cc, ca = tri_props(cv, cf)
    dc = distances(cc, v, f)
    report["cad_to_scan"] = {"cad_area_mm2": round(float(ca.sum()), 1),
                             "observed_supported_share": round(float(ca[dc <= SUPPORT_MM].sum() / ca.sum()), 4),
                             "inferred_share": round(float(ca[dc > SUPPORT_MM].sum() / ca.sum()), 4)}
    Path(out).write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(report["scan_to_cad"]["all"]), json.dumps(report["cad_to_scan"]))
    for name, *_ in ZONES:
        print(name, json.dumps(report["scan_to_cad"][name]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:]))
