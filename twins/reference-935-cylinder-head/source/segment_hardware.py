#!/usr/bin/env python3
"""Separate the head envelope from external hardware and protrusions.

This is a conservative geometric segmentation, not semantic proof.  The cuts
are deliberately left open so that functional ports are never silently capped.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import trimesh

from scan_frame import B_AXIS, C_AXIS, HEAD_BACK_C, HIGH_PORT_FACE_B, LOW_PORT_FACE_B


def keep_halfspace(mesh: trimesh.Trimesh, normal: np.ndarray, offset: float) -> trimesh.Trimesh:
    return trimesh.intersections.slice_mesh_plane(
        mesh, plane_normal=normal, plane_origin=normal * offset, cap=False
    )


def component_summary(mesh: trimesh.Trimesh) -> list[dict[str, object]]:
    result = []
    for rank, component in enumerate(
        sorted(mesh.split(only_watertight=False), key=lambda item: len(item.faces), reverse=True),
        start=1,
    ):
        if len(component.faces) < 3:
            continue
        result.append(
            {
                "rank": rank,
                "vertices": int(len(component.vertices)),
                "triangles": int(len(component.faces)),
                "dimensions_obj_units": np.asarray(component.extents).tolist(),
            }
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    mesh = trimesh.load_mesh(args.input, process=False)
    head = keep_halfspace(mesh, C_AXIS, HEAD_BACK_C)
    head = keep_halfspace(head, B_AXIS, LOW_PORT_FACE_B)
    head = keep_halfspace(head, -B_AXIS, -HIGH_PORT_FACE_B)

    kept_centres = np.asarray(head.triangles_center)
    source_centres = np.asarray(mesh.triangles_center)
    abc = source_centres @ np.vstack((B_AXIS, C_AXIS)).T
    removed_mask = (
        (abc[:, 1] < HEAD_BACK_C)
        | (abc[:, 0] < LOW_PORT_FACE_B)
        | (abc[:, 0] > HIGH_PORT_FACE_B)
    )
    removed = mesh.submesh([removed_mask], append=True, repair=False)

    head_path = args.output / "head-envelope-uncapped.ply"
    removed_path = args.output / "external-hardware-and-protrusions.ply"
    head.export(head_path, encoding="binary")
    removed.export(removed_path, encoding="binary")

    report = {
        "input": str(args.input.resolve()),
        "units": "OBJ units; millimetres plausible but unconfirmed",
        "method": "three conservative planar half-space cuts",
        "planes": {
            "head_back_C_min": HEAD_BACK_C,
            "low_port_B_min": LOW_PORT_FACE_B,
            "high_port_B_max": HIGH_PORT_FACE_B,
        },
        "head_envelope": {
            "path": str(head_path.resolve()),
            "vertices": int(len(head.vertices)),
            "triangles": int(len(head.faces)),
            "watertight": bool(head.is_watertight),
        },
        "removed": {
            "path": str(removed_path.resolve()),
            "vertices": int(len(removed.vertices)),
            "triangles": int(len(removed.faces)),
            "components": component_summary(removed),
        },
        "confidence": "medium",
        "limitations": [
            "The removed set includes external hardware and protrusions, not only studs.",
            "The largest removed component may include an attached plate or fixture.",
            "No cut or scan opening is capped at this stage.",
            "Semantic classification requires comparison with the physical part.",
        ],
    }
    (args.output / "segmentation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

