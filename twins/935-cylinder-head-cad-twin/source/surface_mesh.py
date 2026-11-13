"""T1: watertight bare-head surface from the occupancy field.

Marching cubes at w = 0.5, largest component, consistent outward winding.
Writes the private surface (PLY + STL) and a scalar summary for Git.

Usage: surface_mesh.py PRIVATE_DIR PARAMS_DIR
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from twin_common import write_json  # noqa: E402


def main(private, params):
    import trimesh
    from skimage.measure import marching_cubes

    private, params = Path(private), Path(params)
    grid = json.loads((private / "occupancy-grid.json").read_text())
    wn = np.load(private / grid["array"], mmap_mode="r")
    h = grid["pitch_mm"]
    vol = np.asarray(wn, dtype=np.float32)
    # Pad so that the iso-surface closes on the grid boundary.
    vol = np.pad(vol, 1, mode="constant", constant_values=0.0)
    verts, faces, _, _ = marching_cubes(vol, level=0.5, spacing=(h, h, h), allow_degenerate=False)
    verts += np.array([grid["x0"], grid["y0"], grid["z0"]]) - h
    mesh = trimesh.Trimesh(verts, faces, process=True)
    parts = mesh.split(only_watertight=False)
    parts = sorted(parts, key=lambda m: -abs(m.volume))
    body = parts[0]
    if body.volume < 0:
        body.invert()
    trimesh.repair.fix_normals(body)
    body.export(private / "t1-bare-head.ply")
    body.export(private / "t1-bare-head.stl")
    edges = body.edges_sorted
    _, counts = np.unique(edges, axis=0, return_counts=True)
    summary = {
        "schema": "935-cad-twin-t1-surface/1",
        "method": "skimage marching_cubes at winding number 0.5 on the occupancy grid; largest component kept",
        "pitch_mm": h,
        "triangles": int(len(body.faces)),
        "vertices": int(len(body.vertices)),
        "watertight": bool(body.is_watertight),
        "winding_consistent": bool(body.is_winding_consistent),
        "edge_use_histogram": {str(k): int(v) for k, v in zip(*np.unique(counts, return_counts=True))},
        "euler_number": int(body.euler_number),
        "genus": int(round(1 - body.euler_number / 2)),
        "volume_mm3": round(float(body.volume), 1),
        "area_mm2": round(float(body.area), 1),
        "bounds": np.round(body.bounds, 3).tolist(),
        "discarded_components": [{"triangles": int(len(p.faces)), "volume_mm3": round(float(abs(p.volume)), 3)}
                                 for p in parts[1:20]],
        "discarded_component_count": len(parts) - 1,
    }
    write_json(params / "t1-surface-summary.json", summary)
    print(json.dumps({k: summary[k] for k in ("triangles", "watertight", "winding_consistent", "genus",
                                                 "volume_mm3", "discarded_component_count")}))


if __name__ == "__main__":
    main(*sys.argv[1:3])
