#!/usr/bin/env python3
"""Conservatively separate the two cylinder rows from the central assembly."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import trimesh


def export_selection(mesh: trimesh.Trimesh, mask: np.ndarray, path: Path) -> dict[str, object]:
    part = mesh.submesh([mask], append=True, repair=False)
    part.export(path, file_type="ply", encoding="binary")
    return {
        "path": str(path.resolve()),
        "vertices": int(len(part.vertices)),
        "triangles": int(len(part.faces)),
        "watertight": bool(part.is_watertight),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("interfaces", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    mesh = trimesh.load_mesh(args.input, process=False)
    data = json.loads(args.interfaces.read_text())
    centroid = np.asarray(data["centroid_scan_coordinates"])
    frame = np.asarray(data["frame_rows_longitudinal_bank_axis_vertical"])
    centres = np.asarray(mesh.triangles_center)
    coordinates = (centres - centroid) @ frame.T

    bank_masks = {}
    for label, sign in (("positive", 1), ("negative", -1)):
        mask = np.zeros(len(mesh.faces), dtype=bool)
        for opening in data["banks"][label]:
            longitudinal, vertical = opening["center_longitudinal_vertical"]
            radial = np.linalg.norm(coordinates[:, [0, 2]] - [longitudinal, vertical], axis=1)
            mask |= (radial < 72.0) & (sign * coordinates[:, 1] > 115.0)
        bank_masks[label] = mask

    central_mask = np.abs(coordinates[:, 1]) <= 115.0
    classified = central_mask | bank_masks["positive"] | bank_masks["negative"]
    unclassified_mask = ~classified
    report = {
        "input": str(args.input.resolve()),
        "method": "PCA-frame spatial masks around twelve detected openings",
        "classification_confidence": "medium_for_rows_low_for_remaining_semantics",
        "parts": {
            "central_crankcase_envelope_uncapped": export_selection(
                mesh, central_mask, args.output / "central-crankcase-envelope-uncapped.ply"
            ),
            "positive_six_cylinders_uncapped": export_selection(
                mesh, bank_masks["positive"], args.output / "positive-six-cylinders-uncapped.ply"
            ),
            "negative_six_cylinders_uncapped": export_selection(
                mesh, bank_masks["negative"], args.output / "negative-six-cylinders-uncapped.ply"
            ),
            "external_unclassified": export_selection(
                mesh, unclassified_mask, args.output / "external-unclassified.ply"
            ),
        },
        "limitations": [
            "Parts are spatial review regions, not manufacturing bodies.",
            "Cut boundaries are intentionally left open.",
            "The central region may include accessories and the outer region may include crankcase surfaces.",
            "No surface is deleted from the source or accepted reference mesh.",
        ],
    }
    (args.output / "segmentation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
