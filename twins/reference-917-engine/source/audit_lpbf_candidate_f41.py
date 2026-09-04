#!/usr/bin/env python3
"""Audite l'epaisseur, les vides, l'orientation et les couches LPBF F41."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import runpy

import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def layer_activation(
    points: np.ndarray,
    centroids: np.ndarray,
    areas: np.ndarray,
    transform: np.ndarray,
    layer_height_um: float,
) -> dict:
    rotated_points = points @ transform.T
    rotated_centres = centroids @ transform.T
    lower = rotated_points.min(axis=0)
    upper = rotated_points.max(axis=0)
    height = float(upper[2] - lower[2])
    layer_height = layer_height_um / 1000.0
    layer_count = int(math.ceil(height / layer_height))
    indices = np.clip(((rotated_centres[:, 2] - lower[2]) / layer_height).astype(np.int64), 0, layer_count - 1)
    activated_area = np.bincount(indices, weights=areas, minlength=layer_count)
    nonempty = np.flatnonzero(activated_area > 0.0)
    return {
        "method": f"triangle_centroid_layer_activation_at_{layer_height_um:g}_um_not_laser_scan_path_or_melt_pool",
        "layer_height_um": layer_height_um,
        "layer_count": layer_count,
        "height_mm_if_scale_is_mm": height,
        "nonempty_layer_count": int(len(nonempty)),
        "maximum_activated_triangle_area_mm2_if_scale_is_mm": float(np.max(activated_area)),
        "p95_activated_triangle_area_mm2_if_scale_is_mm": float(np.quantile(activated_area[nonempty], 0.95)),
        "first_nonempty_layer": int(nonempty[0]),
        "last_nonempty_layer": int(nonempty[-1]),
        "complete_layer_schedule_generated": True,
        "machine_build_file_generated": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--head", type=Path, required=True)
    parser.add_argument("--build-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--thickness-min", type=float, default=1.5)
    parser.add_argument("--layer-height-um", type=float, default=40.0)
    parser.add_argument("--reuse-report", type=Path)
    args = parser.parse_args()
    if args.layer_height_um <= 0.0:
        raise SystemExit("hauteur_couche_invalide")
    args.output.mkdir(parents=True, exist_ok=True)

    shared = runpy.run_path(str(Path(__file__).with_name("f39-lpbf-scan-only-audit.py")))
    poly, points, faces = shared["load_stl"](args.head)
    topology = shared["topology"](poly)
    if not topology["watertight_manifold_screen"]:
        raise RuntimeError(f"maillage_non_etanche:{topology}")
    triangles, centroids, normals, areas, signed_volume = shared["triangle_geometry"](points, faces)
    bounds = np.column_stack((points.min(axis=0), points.max(axis=0)))
    if args.reuse_report is not None:
        report = json.loads(args.reuse_report.read_text(encoding="utf-8"))
        selected = report["orientation_and_support"]["selected"]
        layers = layer_activation(
            points,
            centroids,
            areas,
            np.asarray(selected["transform"], dtype=float),
            args.layer_height_um,
        )
        report["virtual_layer_activation"] = layers
        report["gates"].pop("complete_50_um_layer_activation_schedule", None)
        report["gates"]["complete_machine_layer_activation_schedule"] = layers[
            "complete_layer_schedule_generated"
        ]
        destination = args.output / "917-head-lpbf-candidate-f41-audit.json"
        destination.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"report": str(destination), "verdict": report["verdict"], "gates": report["gates"]}, sort_keys=True))
        return 0
    diagonal = float(np.linalg.norm(bounds[:, 1] - bounds[:, 0]))
    chords = shared["exhaustive_normal_chords"](poly, centroids, normals, diagonal)
    thickness = shared["thickness_summary"](chords, areas, args.thickness_min)
    thickness["classification"] = "exhaustive_faceted_chord_screen_not_continuous_medial_thickness_or_CT"
    map_path = args.output / "917-head-lpbf-candidate-f41-thickness-map.npz"
    np.savez_compressed(
        map_path,
        triangle_id=np.arange(len(faces), dtype=np.int32),
        centroid_mm_if_scale_is_mm=centroids.astype(np.float32),
        face_area_mm2_if_scale_is_mm=areas.astype(np.float32),
        normal=normals.astype(np.float32),
        thickness_chord_mm_if_scale_is_mm=chords.astype(np.float32),
    )
    thickness["map"] = {"path": map_path.name, "sha256": sha256(map_path), "bytes": map_path.stat().st_size}

    voids = [shared["trapped_void_screen"](poly, bounds, pitch) for pitch in (2.0, 1.25)]
    orientations, selected = shared["orientation_screen"](
        points,
        centroids,
        normals,
        areas,
        np.asarray([250.0, 250.0, 325.0]),
        45.0,
    )
    layers = layer_activation(
        points,
        centroids,
        areas,
        np.asarray(selected["transform"], dtype=float),
        args.layer_height_um,
    )
    finest_void = voids[-1]
    build = json.loads(args.build_report.read_text(encoding="utf-8"))
    gates = {
        "source_brep_one_valid_solid": build["step_roundtrip"] == {
            "valid": True,
            "solid_count": 1,
            "shell_count": 1,
            "discarded_zero_area_components": build["step_roundtrip"].get("discarded_zero_area_components", 0),
        },
        "surface_mesh_watertight_volume": bool(topology["watertight_manifold_screen"]),
        "all_triangle_chords_resolved": thickness["unresolved_triangle_count"] == 0,
        "all_resolved_chords_at_least_1_5_mm": thickness["all_resolved_chords_meet_inherited_requirement"],
        "no_closed_void_detected_at_both_voxel_pitches": all(item["trapped_component_count"] == 0 for item in voids),
        "orientation_fits_conditional_machine_envelope": bool(selected["fits_inherited_250x250x325_envelope_if_scale_is_mm"]),
        "complete_machine_layer_activation_schedule": layers["complete_layer_schedule_generated"],
        "machine_scan_path_and_supports_sliced": False,
        "calibrated_process_simulation_complete": False,
        "metal_print_authorized": False,
        "engine_start_authorized": False,
    }
    report = {
        "schema_version": "1.0.0",
        "phase": "F41",
        "status": "lpbf_geometry_audit_complete_release_depends_on_gates",
        "classification": "virtual_geometry_and_layer_activation_screen_not_machine_qualification_or_physical_release",
        "inputs": {
            "head": {"path": args.head.name, "sha256": sha256(args.head)},
            "build_report": {"path": args.build_report.name, "sha256": sha256(args.build_report)},
        },
        "mesh": {
            **topology,
            "bounds_mm_if_scale_is_mm": bounds.tolist(),
            "signed_volume_mm3_if_scale_is_mm": signed_volume,
            "surface_area_mm2_if_scale_is_mm": float(np.sum(areas)),
        },
        "exhaustive_thickness_screen": thickness,
        "closed_void_and_powder_escape": {
            "resolutions": voids,
            "finest_trapped_volume_mm3_if_scale_is_mm": finest_void["trapped_volume_mm3_if_scale_is_mm"],
            "physical_powder_removal_test_complete": False,
        },
        "orientation_and_support": {
            "candidates": orientations,
            "selected": selected,
            "support_geometry_generated": False,
            "supplier_slicer_review_complete": False,
        },
        "virtual_layer_activation": layers,
        "gates": gates,
        "verdict": "virtually_printable" if all(gates[key] for key in (
            "source_brep_one_valid_solid",
            "surface_mesh_watertight_volume",
            "all_triangle_chords_resolved",
            "all_resolved_chords_at_least_1_5_mm",
            "no_closed_void_detected_at_both_voxel_pitches",
            "orientation_fits_conditional_machine_envelope",
            "complete_machine_layer_activation_schedule",
        )) else "geometry_correction_required_before_supplier_slicing",
    }
    destination = args.output / "917-head-lpbf-candidate-f41-audit.json"
    destination.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(destination), "verdict": report["verdict"], "gates": gates}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
