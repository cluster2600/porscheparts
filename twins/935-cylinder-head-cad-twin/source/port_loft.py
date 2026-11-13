"""v1 feature tree, ports: loft each port through its fitted sections and
measure the loft against the acquired port-wall facets.

Each section becomes a closed periodic spline through its RAYS wall points; the
port is the loft through those wires (private BREP). The check uses the Warp
distance kernel of score_twin.py on the scan facets of the port wall: facets
between the loft's end planes, within WALL_BAND_MM of the loft surface, whose
normal faces the centreline. The same facets are measured against a body stack
(its private STL) so the two models are compared on equal terms.

Usage: port_loft.py PRIVATE_DIR PARAMS_DIR STACK_LABEL
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from twin_common import face_geometry, write_json  # noqa: E402

WALL_BAND_MM = 1.5
STL_TOL_MM = 0.02


def wall_points(d):
    ang = np.linspace(0.0, 2 * np.pi, d["radii"].shape[1], endpoint=False)
    return (d["centre"][:, None, :] + (d["radii"] * np.cos(ang))[:, :, None] * d["u"][:, None, :]
            + (d["radii"] * np.sin(ang))[:, :, None] * d["v"][:, None, :])


def build_loft(d):
    from build123d import Solid, Spline, Wire

    wires = [Wire([Spline(*[tuple(map(float, p)) for p in ring], periodic=True)]) for ring in wall_points(d)]
    return Solid.make_loft(wires)


def stats(dist, w):
    o = np.argsort(dist)
    cw = np.cumsum(w[o]) / w.sum()
    pick = lambda q: round(float(dist[o][min(len(o) - 1, np.searchsorted(cw, q))]), 4)  # noqa: E731
    return {"p50": pick(0.5), "p95": pick(0.95), "share_within_mm": {
        str(t): round(float(w[dist <= t].sum() / w.sum()), 4) for t in (0.1, 0.2, 0.5, 1.0)}}


def main(private, params, stack_label):
    from build123d import export_brep
    from scipy.spatial import cKDTree
    from score_twin import warp_distances

    private, params = Path(private), Path(params)
    raw = np.load(private / "port-sections.npz")
    names = sorted({k.split("__")[0] for k in raw.files})
    bare = np.load(private / "bare-scan-twin.npz")
    cen, n, area = face_geometry(bare["v"], bare["f"])
    import trimesh

    stack = trimesh.load(private / f"v1-body-stack-{stack_label}.stl", process=False, force="mesh")
    sv, sf = np.asarray(stack.vertices, dtype=np.float64), np.asarray(stack.faces, dtype=np.int64)
    out = {"schema": "935-cad-twin-port-loft/1", "compared_stack": stack_label, "wall_band_mm": WALL_BAND_MM, "ports": []}
    for name in names:
        d = {k.split("__")[1]: raw[k] for k in raw.files if k.startswith(name + "__")}
        t0 = time.time()
        try:
            loft = build_loft(d)
            if not loft.is_valid:
                raise ValueError("loft is not a valid solid")
        except Exception as exc:  # recorded, never hidden
            out["ports"].append({"name": name, "valid": False, "adopted": False, "error": repr(exc)[:200]})
            print(name, "loft failed:", repr(exc)[:120], flush=True)
            continue
        export_brep(loft, str(private / f"v1-{name}.brep"))
        v, f = loft.tessellate(STL_TOL_MM, 0.1)
        lv = np.array([(p.X, p.Y, p.Z) for p in v])
        lf = np.asarray(f, dtype=np.int64)
        np.savez(private / f"v1-{name}-mesh.npz", v=lv, f=lf)
        c, t = d["centre"], d["tangent"]
        near = np.linalg.norm(cen - c.mean(axis=0), axis=1) < np.linalg.norm(c - c.mean(axis=0), axis=1).max() + 40.0
        idx = np.where(near)[0]
        between = ((cen[idx] - c[0]) @ t[0] > 0) & ((cen[idx] - c[-1]) @ t[-1] < 0)
        idx = idx[between]
        print(name, "loft and mesh", round(time.time() - t0, 1), "s;", len(lf), "triangles;", len(idx), "candidate facets", flush=True)
        dl = warp_distances(cen[idx], lv, lf)
        k = cKDTree(c).query(cen[idx])[1]
        facing = np.einsum("ij,ij->i", c[k] - cen[idx], n[idx]) > 0
        wall = (dl < WALL_BAND_MM) & facing
        idx, dl = idx[wall], dl[wall]
        np.save(private / f"v1-{name}-wall-facets.npy", idx)
        if len(idx) == 0:
            out["ports"].append({"name": name, "valid": True, "adopted": False, "error": "no acquired wall facet"})
            continue
        on_loft, on_stack = stats(dl, area[idx]), stats(warp_distances(cen[idx], sv, sf), area[idx])
        out["ports"].append({
            "name": name, "valid": bool(loft.is_valid),
            # Adopted only when the loft explains more of its own wall than the stack does.
            "adopted": bool(on_loft["share_within_mm"]["0.2"] > on_stack["share_within_mm"]["0.2"]), "volume_mm3": round(float(loft.volume), 1),
            "sections": int(len(c)), "faces": len(loft.faces()), "seconds": round(time.time() - t0, 1),
            "wall_scan_area_mm2": round(float(area[idx].sum()), 1),
            "scan_to_loft": on_loft,
            "scan_to_stack": on_stack,
        })
        p = out["ports"][-1]
        print(name, "adopted", p["adopted"], "wall area", p["wall_scan_area_mm2"],
              "| loft p50/p95", p["scan_to_loft"]["p50"], p["scan_to_loft"]["p95"], "<=0.2", p["scan_to_loft"]["share_within_mm"]["0.2"],
              "| stack p50/p95", p["scan_to_stack"]["p50"], p["scan_to_stack"]["p95"], "<=0.2", p["scan_to_stack"]["share_within_mm"]["0.2"])
    write_json(params / "port-loft-check.json", out)


if __name__ == "__main__":
    main(*sys.argv[1:4])
