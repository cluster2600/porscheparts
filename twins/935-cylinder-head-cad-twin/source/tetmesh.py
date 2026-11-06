"""Volume mesh of the twin with fTetWild (pytetwild) inside a declared envelope.

fTetWild keeps the output boundary within EPSILON_MM of the input surface and
tolerates input self-intersections, so the decimated surface is admissible as
its input. Quality is reported as the normalised volume ratio
q = 6*sqrt(2)*V / l_rms^3 (1 for a regular tetrahedron).

Usage: tetmesh.py SURFACE.stl OUT.npz EDGE_MM EPSILON_MM REPORT.json
"""

from __future__ import annotations

import json
import sys
import time

import numpy as np


def quality(v, t):
    p = v[t]
    vol = np.einsum("ij,ij->i", np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]), p[:, 3] - p[:, 0]) / 6.0
    e = [p[:, b] - p[:, a] for a, b in ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))]
    lrms = np.sqrt(sum((x * x).sum(axis=1) for x in e) / 6.0)
    return vol, 6.0 * np.sqrt(2.0) * vol / lrms ** 3


def main(surface, out, edge, eps, report):
    import pytetwild
    import trimesh

    m = trimesh.load(surface, process=False, force="mesh")
    bbox = float(np.linalg.norm(m.extents))
    t0 = time.time()
    v, t = pytetwild.tetrahedralize(np.asarray(m.vertices, dtype=np.float64), np.asarray(m.faces, dtype=np.int32),
                                    edge_length_abs=float(edge), epsilon=float(eps) / bbox, quiet=True)
    secs = time.time() - t0
    vol, q = quality(v, t)
    if (vol < 0).mean() > 0.5:
        t = t[:, [0, 2, 1, 3]]
        vol, q = quality(v, t)
    np.savez(out, v=v, t=t.astype(np.int64))
    rep = {"tool": "fTetWild via pytetwild", "input_triangles": int(len(m.faces)),
           "edge_length_mm": float(edge), "envelope_mm": float(eps), "nodes": int(len(v)), "tets": int(len(t)),
           "volume_mm3": round(float(vol.sum()), 1), "input_surface_volume_mm3": round(float(m.volume), 1),
           "negative_or_zero_volume_tets": int((vol <= 0).sum()),
           "quality_normalised_volume": {"min": round(float(q.min()), 4), "p1": round(float(np.percentile(q, 1)), 4),
                                         "median": round(float(np.median(q)), 4),
                                         "share_below_0p1": round(float((q < 0.1).mean()), 6)},
           "seconds": round(secs, 1)}
    with open(report, "w") as fh:
        json.dump(rep, fh, indent=2)
    print(json.dumps(rep))


if __name__ == "__main__":
    main(*sys.argv[1:6])
