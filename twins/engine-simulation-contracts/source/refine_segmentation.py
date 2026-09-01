#!/usr/bin/env python3
"""Refine existing 917/935 scan regions without changing or closing source meshes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import trimesh


def export_part(mesh: trimesh.Trimesh, mask: np.ndarray, path: Path) -> dict[str, object]:
    part = mesh.submesh([mask], append=True, repair=False)
    part.export(path, file_type="ply", encoding="binary")
    return {
        "path": str(path.resolve()),
        "vertices": int(len(part.vertices)),
        "triangles": int(len(part.faces)),
        "dimensions_obj_units": np.asarray(part.extents).tolist(),
        "watertight": bool(part.is_watertight),
    }


def refine_917(root: Path, spec: dict[str, object], output: Path) -> dict[str, object]:
    mesh_path = root / str(spec["mesh"])
    interfaces_path = root / str(spec["interfaces"])
    mesh = trimesh.load_mesh(mesh_path, process=False)
    interfaces = json.loads(interfaces_path.read_text())
    centroid = np.asarray(interfaces["centroid_scan_coordinates"])
    frame = np.asarray(interfaces["frame_rows_longitudinal_bank_axis_vertical"])
    coordinates = (np.asarray(mesh.triangles_center) - centroid) @ frame.T
    radius = float(spec["opening_neighborhood_radius_obj_units"])
    depth = float(spec["bank_depth_threshold_obj_units"])
    assigned = np.zeros(len(mesh.faces), dtype=bool)
    parts: dict[str, object] = {}

    for bank_name, sign in (("positive", 1), ("negative", -1)):
        openings = interfaces["banks"][bank_name]
        centres = np.asarray(
            [item["center_longitudinal_vertical"] for item in openings], dtype=float
        )
        face_lv = coordinates[:, [0, 2]]
        distances = np.linalg.norm(face_lv[:, None, :] - centres[None, :, :], axis=2)
        nearest = np.argmin(distances, axis=1)
        minimum = distances[np.arange(len(distances)), nearest]
        in_bank = sign * coordinates[:, 1] > depth
        for index in range(len(openings)):
            mask = in_bank & (nearest == index) & (minimum < radius)
            if np.any(mask & assigned):
                raise RuntimeError("917 refined selections overlap")
            assigned |= mask
            identifier = f"{bank_name}-opening-{index + 1:02d}-neighborhood"
            parts[identifier] = {
                **export_part(mesh, mask, output / "917" / f"{identifier}.ply"),
                "classification": "visible_opening_neighborhood",
                "semantic_confidence": "medium_geometry_low_component_identity",
                "interface_center_scan_coordinates": openings[index]["center_scan_coordinates"],
                "interface_axis_scan_coordinates": openings[index]["axis_scan_coordinates"],
                "visible_diameter_obj_units": openings[index]["diameter_obj_units"],
            }

    remainder = ~assigned
    parts["remainder-unclassified"] = {
        **export_part(mesh, remainder, output / "917" / "remainder-unclassified.ply"),
        "classification": "engine_remainder_unclassified",
        "semantic_confidence": "low",
    }
    return {
        "input": str(mesh_path.resolve()),
        "interfaces": str(interfaces_path.resolve()),
        "method": "unique nearest-opening face assignment in the detected PCA frame",
        "source_triangles": int(len(mesh.faces)),
        "assigned_opening_triangles": int(np.count_nonzero(assigned)),
        "remainder_triangles": int(np.count_nonzero(remainder)),
        "coverage_ratio": float(np.count_nonzero(assigned) / len(mesh.faces)),
        "parts": parts,
        "overlap_triangles": 0,
    }


def component_candidate(component: trimesh.Trimesh) -> tuple[str, str]:
    extents = np.sort(np.asarray(component.extents))
    if 9.0 <= extents[0] <= 16.0 and 34.0 <= extents[2] <= 52.0:
        return "stud_or_long_fastener_candidate", "low_requires_visual_confirmation"
    if extents[2] <= 25.0:
        return "small_external_hardware_candidate", "low_requires_visual_confirmation"
    return "external_component_unclassified", "low"


def refine_935(root: Path, spec: dict[str, object], output: Path) -> dict[str, object]:
    removed_path = root / str(spec["removed_geometry"])
    head_path = root / str(spec["head_envelope"])
    removed = trimesh.load_mesh(removed_path, process=False)
    minimum = int(spec["minimum_component_triangles"])
    components = sorted(
        removed.split(only_watertight=False), key=lambda item: len(item.faces), reverse=True
    )
    kept = []
    ignored_triangles = 0
    for rank, component in enumerate(components, start=1):
        if len(component.faces) < minimum:
            ignored_triangles += len(component.faces)
            continue
        classification, confidence = component_candidate(component)
        path = output / "935" / f"external-component-{rank:02d}.ply"
        component.export(path, file_type="ply", encoding="binary")
        kept.append(
            {
                "id": f"external-component-{rank:02d}",
                "path": str(path.resolve()),
                "classification": classification,
                "semantic_confidence": confidence,
                "vertices": int(len(component.vertices)),
                "triangles": int(len(component.faces)),
                "dimensions_obj_units": np.asarray(component.extents).tolist(),
                "watertight": bool(component.is_watertight),
            }
        )
    return {
        "head_envelope": str(head_path.resolve()),
        "removed_input": str(removed_path.resolve()),
        "method": "topological connected-component split of previously removed external geometry",
        "components_kept": kept,
        "minimum_component_triangles": minimum,
        "ignored_small_component_triangles": int(ignored_triangles),
        "limitations": [
            "Connectivity separates geometry but does not identify its mechanical function.",
            "Stud labels are candidates based on envelope only and require visual confirmation.",
            "Attached hardware still connected to the head envelope is not separated by this pass.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.project_root.resolve()
    config = json.loads(args.config.read_text())
    output = args.output.resolve()
    (output / "917").mkdir(parents=True, exist_ok=True)
    (output / "935").mkdir(parents=True, exist_ok=True)
    report = {
        "schema_version": "1.0.0",
        "status": "passed_geometric_segmentation_requires_semantic_review",
        "source_contract": str(args.config.resolve()),
        "engine_917": refine_917(root, config["engine_917"], output),
        "head_935": refine_935(root, config["head_935"], output),
        "limitations": config["limitations"],
    }
    report_path = output / "refined-segmentation.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
