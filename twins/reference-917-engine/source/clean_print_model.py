#!/usr/bin/env python3
"""Keep the main closed body and validate one scale-specific print model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import trimesh


def topology(mesh: trimesh.Trimesh) -> dict[str, object]:
    incidence = np.bincount(np.asarray(mesh.edges_unique_inverse))
    return {
        "vertices": int(len(mesh.vertices)),
        "triangles": int(len(mesh.faces)),
        "boundary_edges": int(np.count_nonzero(incidence == 1)),
        "non_manifold_edges": int(np.count_nonzero(incidence > 2)),
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "is_volume": bool(mesh.is_volume),
        "body_count": int(mesh.body_count),
        "dimensions_candidate_mm": np.asarray(mesh.extents).tolist(),
        "volume_candidate_mm3": float(abs(mesh.volume)),
        "area_candidate_mm2": float(mesh.area),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--scale-label", required=True)
    parser.add_argument("--voxel-size-mm", type=float, required=True)
    parser.add_argument("--interfaces", type=Path, required=True)
    parser.add_argument("--source-scale", type=float, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)

    raw = trimesh.load_mesh(args.input, process=True)
    parts = sorted(raw.split(only_watertight=False), key=lambda item: len(item.faces), reverse=True)
    if not parts:
        raise SystemExit("voxel reconstruction contains no body")
    main = parts[0]
    main.remove_unreferenced_vertices()
    main.fix_normals()
    interfaces = json.loads(args.interfaces.read_text())
    centroid = np.asarray(interfaces["centroid_scan_coordinates"]) * args.source_scale
    frame = np.asarray(interfaces["frame_rows_longitudinal_bank_axis_vertical"])
    main.vertices = (np.asarray(main.vertices) - centroid) @ frame.T
    bounds = np.asarray(main.bounds)
    main.apply_translation(
        [-(bounds[0, 0] + bounds[1, 0]) / 2.0, -(bounds[0, 1] + bounds[1, 1]) / 2.0, -bounds[0, 2]]
    )
    checks = topology(main)
    if not checks["watertight"] or checks["non_manifold_edges"] or not checks["is_volume"]:
        raise SystemExit("main display body is not a closed printable volume")
    main.export(args.output)

    report = {
        "status": "geometrically_printable_display_model",
        "classification": "display_only_nonfunctional",
        "input": str(args.input.resolve()),
        "output": str(args.output.resolve()),
        "scale": args.scale_label,
        "scale_assumption": "1 source OBJ unit equals 1 mm; unconfirmed",
        "voxel_size_in_output_mm": args.voxel_size_mm,
        "print_frame": "X longitudinal, Y opposed-cylinder axis, Z PCA vertical; centred on XY and placed on Z=0",
        "discarded_disconnected_bodies": len(parts) - 1,
        "checks": checks,
        "manufacturing_status": "blocked_pending_scale_and_slicer_review",
        "allowed_use": "static display model",
        "prohibited_use": "engine, structural, pressure, thermal or vehicle use",
        "next_checks": [
            "confirm a physical dimension and the source OBJ unit",
            "inspect the STL visually for lost or bridged details",
            "run the selected slicer with the actual printer and material profile",
            "add supports and, for resin, a deliberate hollowing and drainage strategy",
        ],
    }
    args.output.with_suffix(".json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
