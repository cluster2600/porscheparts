#!/usr/bin/env python3
"""Publie les preuves geometriques F39 sans publier le scan ni ses maillages."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil

import numpy as np
from scipy.spatial import cKDTree
import trimesh


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load_mesh(path: Path) -> trimesh.Trimesh:
    mesh = trimesh.load(path, force="mesh", process=True)
    require(isinstance(mesh, trimesh.Trimesh) and len(mesh.faces) > 0, f"mesh_absent:{path}")
    return mesh


def load_audit_module(source: Path):
    spec = importlib.util.spec_from_file_location("f39_brep_lpbf_audit", source)
    require(spec is not None and spec.loader is not None, "audit_module_import_failed")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def distribution(distances: np.ndarray) -> dict[str, float]:
    return {
        "mean": float(np.mean(distances)),
        "median": float(np.quantile(distances, 0.50)),
        "p95": float(np.quantile(distances, 0.95)),
        "p99": float(np.quantile(distances, 0.99)),
        "maximum": float(np.max(distances)),
    }


def scan_conformance(model: trimesh.Trimesh, scan: trimesh.Trimesh, sample_count: int) -> dict:
    model_points, _ = trimesh.sample.sample_surface(model, sample_count, seed=1939)
    scan_points, _ = trimesh.sample.sample_surface(scan, sample_count, seed=917)
    model_to_scan = cKDTree(scan_points).query(model_points, workers=-1)[0]
    scan_to_model = cKDTree(model_points).query(scan_points, workers=-1)[0]
    return {
        "method": "bidirectional_nearest_between_deterministic_surface_samples_not_exact_Hausdorff",
        "sample_count_per_surface": sample_count,
        "analytic_to_scan_distance_units": distribution(model_to_scan),
        "scan_to_analytic_distance_units": distribution(scan_to_model),
        "symmetric_sampled_max_distance_units": float(max(np.max(model_to_scan), np.max(scan_to_model))),
        "scale_or_fitment_certification": False,
        "limitation": "Approximation par nuages echantillonnes; les details organiques du scan ne sont pas une definition OEM.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--build-report", type=Path, required=True)
    parser.add_argument("--head-stl-local", type=Path, required=True)
    parser.add_argument("--step", type=Path, required=True)
    parser.add_argument("--f37-scan-local", type=Path, required=True)
    parser.add_argument("--audit-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wall-samples", type=int, default=2400)
    parser.add_argument("--scan-samples", type=int, default=20000)
    args = parser.parse_args()

    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    build = json.loads(args.build_report.read_text(encoding="utf-8"))
    require(contract.get("phase") == "F39", "contract_phase_not_F39")
    require(build.get("phase") == "F39", "build_phase_not_F39")
    require(sha256(args.step) == build["files"]["step"]["sha256"], "STEP_hash_mismatch")
    require(sha256(args.head_stl_local) == build["files"]["surface_stl_local"]["sha256"], "STL_hash_mismatch")
    require(sha256(args.f37_scan_local) == contract["inputs"]["f37_local_scan_derived_mesh_sha256"], "scan_hash_mismatch")
    require(args.wall_samples >= 1000 and args.scan_samples >= 5000, "insufficient_sampling")

    head = load_mesh(args.head_stl_local)
    scan = load_mesh(args.f37_scan_local)
    audit = load_audit_module(args.audit_source)
    wall = audit.thickness_audit(head, sample_count=args.wall_samples)
    wall["requirement_mm_if_unit_convention_holds"] = float(contract["validation_targets"]["minimum_wall_mm"])
    wall["p01_gate_passes"] = bool(
        wall["p01_mm_if_scale_is_mm"] >= wall["requirement_mm_if_unit_convention_holds"]
    )
    wall["limitation"] = "Echantillonnage non exhaustif; les intersections proches des levres et raccords sont incluses."

    voxel_results = []
    for pitch in (2.0, 1.5, 1.0):
        result = audit.voxel_audit(head, pitch_mm=pitch)
        voxel_results.append(
            {
                "pitch_mm_if_unit_convention_holds": pitch,
                "grid_shape": result["grid_shape"],
                "trapped_void_voxels": result["trapped_void_voxels"],
                "trapped_void_volume_mm3": result["trapped_void_volume_mm3"],
            }
        )
    voxel_zero = all(item["trapped_void_voxels"] == 0 for item in voxel_results)

    outer = contract["outer_reconstruction"]
    functional = contract["functional_geometry"]
    named_walls = {
        "fin_thickness_mm": float(outer["fin_thickness_mm"]),
        "intake_boss_nominal_radial_wall_mm": float(outer["intake_boss_outer_radius_mm"])
        - float(functional["intake_port_radius_mm"]),
        "exhaust_boss_nominal_radial_wall_mm": float(outer["exhaust_boss_outer_radius_mm"])
        - float(functional["exhaust_port_radius_mm"]),
    }
    named_minimum = min(named_walls.values())
    named_feature_screen = {
        "method": "analytic_named_feature_dimensions_before_local_boolean_intersection",
        "features": named_walls,
        "minimum_mm": named_minimum,
        "requirement_mm": float(contract["validation_targets"]["minimum_wall_mm"]),
        "passes_named_features": named_minimum >= float(contract["validation_targets"]["minimum_wall_mm"]),
        "proves_global_post_boolean_minimum": False,
    }

    topology = {
        "surface_stl_watertight": bool(head.is_watertight),
        "surface_stl_winding_consistent": bool(head.is_winding_consistent),
        "surface_stl_body_count": int(head.body_count),
        "step_reimport_solid_count": int(build["geometry"]["step_reimport_volume_count"]),
        "step_boundary_shell_components": int(build["geometry"]["boundary_shell_components"]),
        "closed_internal_shells_detected": int(build["geometry"]["closed_internal_shells_detected"]),
    }
    topology_passes = bool(
        topology["surface_stl_watertight"]
        and topology["surface_stl_body_count"] == 1
        and topology["step_reimport_solid_count"] == 1
        and topology["step_boundary_shell_components"] == 1
        and voxel_zero
    )

    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    published_step = output / "f39-brep-scan-only-head.step"
    published_build = output / "f39-brep-build-report.json"
    shutil.copyfile(args.step, published_step)
    shutil.copyfile(args.build_report, published_build)

    report = {
        "schema_version": "1.0.0",
        "phase": "F39",
        "status": "scan_only_analytic_brep_geometric_evidence_complete_release_blocked",
        "classification": contract["classification"],
        "contract_sha256": sha256(args.contract),
        "input_policy": {
            "raw_or_scan_derived_geometry_published": False,
            "local_scan_sha256": contract["inputs"]["f37_local_scan_derived_mesh_sha256"],
            "additional_dimensions_available": False,
            "scan_unit_is_mm_by_convention_only": True,
        },
        "geometry_master": {
            "role": "analytic_OCC_STEP_master_not_scan_mesh",
            "path": published_step.name,
            "bytes": published_step.stat().st_size,
            "sha256": sha256(published_step),
            "local_derivatives_not_published": [
                build["files"]["surface_stl_local"]["path"],
                build["files"]["volume_mesh_local"]["path"],
            ],
        },
        "topology_and_open_voids": {
            **topology,
            "voxel_method": "surface_voxel_components_plus_chunked_winding_number_without_fill_holes",
            "voxel_resolution_study": voxel_results,
            "zero_at_all_three_resolutions": voxel_zero,
            "passes": topology_passes,
            "limitation": "Le flood-fill voxel n'est ni une CT ni une verification de depoudrage machine.",
        },
        "minimum_wall": {
            "named_analytic_features": named_feature_screen,
            "independent_sampled_mesh": wall,
            "global_minimum_1_5_mm_proven": bool(named_feature_screen["passes_named_features"] and wall["p01_gate_passes"]),
        },
        "scan_conformance": scan_conformance(head, scan, args.scan_samples),
        "step_volume_mesh": build["volume_mesh"],
        "release_decision": {
            "geometric_step_reimport_and_mesh_demonstrated": True,
            "no_closed_void_screen_passed": topology_passes,
            "minimum_wall_gate_passed": False,
            "mesh_quality_gate_passed": bool(build["volume_mesh"]["quality_gate_minSICN_above_0_1"]),
            "oem_fitment_certified": False,
            "metal_print_authorized": False,
            "engine_start_authorized": False,
            "reason": "Epaisseur globale et qualite minimale du maillage restent sous les portes; echelle et interfaces OEM non mesurees.",
        },
        "release_gates": contract["release_gates"],
    }
    report_path = output / "f39-brep-validation-report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report["status"],
                "step": report["geometry_master"],
                "topology": report["topology_and_open_voids"],
                "minimum_wall": report["minimum_wall"],
                "mesh_quality_gate": report["release_decision"]["mesh_quality_gate_passed"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
