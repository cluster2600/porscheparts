"""T1s: project observed twin vertices onto the acquired scan.

Marching cubes on a 0.25 mm grid leaves a ~0.1 mm aliasing ripple on
surfaces the scanner did observe. Each T1 vertex whose closest point on the
bare scan lies within SNAP_MM is moved onto that point; vertices farther away
(inferred closure) are not touched. Any triangle whose normal would turn by
more than MAX_TURN_DEG, or whose area would collapse, has its vertices
reverted; this repeats until no triangle is rejected. Connectivity is never
changed, so watertightness and genus are preserved.

Usage: snap_surface.py PRIVATE_DIR PARAMS_DIR [SNAP_MM]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from twin_common import write_json  # noqa: E402

MAX_TURN_DEG = 60.0
MAX_ROUNDS = 100


def closest_points(points, v, f):
    import warp as wp

    wp.config.quiet = True
    wp.init()

    @wp.kernel
    def k(mesh: wp.uint64, pts: wp.array(dtype=wp.vec3), cp: wp.array(dtype=wp.vec3), d: wp.array(dtype=float)):
        i = wp.tid()
        q = wp.mesh_query_point_no_sign(mesh, pts[i], 1.0e6)
        c = wp.mesh_eval_position(mesh, q.face, q.u, q.v)
        cp[i] = c
        d[i] = wp.length(pts[i] - c)

    m = wp.Mesh(points=wp.array(v.astype(np.float32), dtype=wp.vec3),
                indices=wp.array(f.astype(np.int32).ravel(), dtype=wp.int32))
    cp = wp.zeros(len(points), dtype=wp.vec3)
    d = wp.zeros(len(points), dtype=float)
    wp.launch(k, dim=len(points), inputs=[m.id, wp.array(points.astype(np.float32), dtype=wp.vec3), cp, d])
    return cp.numpy().astype(np.float64), d.numpy().astype(np.float64)


def normals(v, f):
    n = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]])
    a = np.linalg.norm(n, axis=1)
    return n / np.maximum(a, 1e-30)[:, None], 0.5 * a


def main(private, params, snap_mm="0.3"):
    import trimesh

    private, params = Path(private), Path(params)
    snap_mm = float(snap_mm)
    # PLY keeps shared vertices; an STL would duplicate them per triangle.
    t1 = trimesh.load(private / "t1-bare-head.ply", process=False, force="mesh")
    v0, f = np.asarray(t1.vertices, dtype=np.float64), np.asarray(t1.faces, dtype=np.int64)
    bare = np.load(private / "bare-scan-twin.npz")
    used = np.unique(bare["f"])
    remap = -np.ones(len(bare["v"]), dtype=np.int64)
    remap[used] = np.arange(len(used))
    cp, d = closest_points(v0, bare["v"][used], remap[bare["f"]])

    move = d <= snap_mm
    n0, a0 = normals(v0, f)
    cos_lim = np.cos(np.radians(MAX_TURN_DEG))
    rounds = []
    for _ in range(MAX_ROUNDS):
        v = np.where(move[:, None], cp, v0)
        n1, a1 = normals(v, f)
        bad = (((n0 * n1).sum(axis=1) < cos_lim) | (a1 < 1e-6)) & (a0 >= 1e-6)
        rounds.append(int(bad.sum()))
        if not bad.any():
            break
        move[np.unique(f[bad])] = False
    else:
        raise SystemExit("snap rejection did not converge; no output written")
    out = trimesh.Trimesh(v, f, process=False)
    out.export(private / "t1s-bare-head.stl")
    out.export(private / "t1s-bare-head.ply")
    summary = {
        "schema": "935-cad-twin-t1s-snap/1",
        "snap_threshold_mm": snap_mm,
        "max_normal_turn_deg": MAX_TURN_DEG,
        "vertices": int(len(v)),
        "vertices_snapped": int(move.sum()),
        "vertices_within_threshold": int((d <= snap_mm).sum()),
        "rejection_rounds": rounds,
        "watertight": bool(out.is_watertight),
        "winding_consistent": bool(out.is_winding_consistent),
        "volume_mm3": round(float(out.volume), 1),
        "volume_change_mm3": round(float(out.volume - t1.volume), 1),
        "connectivity_changed": False,
    }
    write_json(params / "t1s-snap-summary.json", summary)
    print(json.dumps(summary))


if __name__ == "__main__":
    main(*sys.argv[1:4])
