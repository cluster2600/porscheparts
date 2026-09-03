#!/usr/bin/env python3
"""Publish a coordinate-free F42.2 verdict; never publish private geometry."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def gmsh_summary(log_path: Path, mesh_path: Path | None) -> dict:
    log = log_path.read_text(encoding="utf-8", errors="replace")
    events = [
        (int(count), int(face))
        for count, face in re.findall(r"Warning : (\d+) elements remain invalid in surface (\d+)", log)
    ]
    mesh_exists = bool(mesh_path and mesh_path.is_file())
    return {
        "software": "Gmsh 4.12.1 using OpenCASCADE STEP importer",
        "container_image_digest": "sha256:4a19fa7d1f253beb3106970ae2635cff85d5aeeaf062aaf807d1dab7b940fb33",
        "input_mount": "read_only",
        "done_meshing_1D": "Done meshing 1D" in log,
        "done_meshing_2D": "Done meshing 2D" in log,
        "done_meshing_3D": "Done meshing 3D" in log,
        "mesh_file_created": mesh_exists,
        "warning_event_count": len(events),
        "unique_invalid_surface_count": len({face for _, face in events}),
        "cumulative_invalid_elements_across_repeated_refinement_warnings": sum(
            count for count, _ in events
        ),
        "volume_mesh_success": "Done meshing 3D" in log and mesh_exists,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-report", type=Path, required=True)
    parser.add_argument("--gmsh-log", type=Path, required=True)
    parser.add_argument("--gmsh-mesh", type=Path)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    private = json.loads(args.private_report.read_text(encoding="utf-8"))
    gmsh = gmsh_summary(args.gmsh_log, args.gmsh_mesh)
    target = private["mapped_25_face_trial"]
    expanded = private["diagnostic_expanded_trial"]
    roundtrip = private["roundtrip"]
    pre_bop = private["pre_export_full_BOPAlgo"]
    roundtrip_bop = roundtrip["full_BOPAlgo"]
    clean = (
        private["gates_before_gmsh"]["pre_gmsh_candidate_accepted"]
        and gmsh["volume_mesh_success"]
    )
    if clean:
        raise RuntimeError("unexpected_clean_candidate_requires_manual_release_review")
    result = {
        "schema": "porsche-917-f42.2-public-surgical-pcurve-diagnostic/v1",
        "phase": "F42.2",
        "verdict": "REPAIR_REJECTED_FAIL_CLOSED",
        "private_evidence_binding": {
            "source_STEP_sha256": private["input"]["sha256"],
            "rejected_candidate_STEP_sha256": private["private_candidate"]["sha256"],
            "private_report_sha256": sha256(args.private_report),
            "repository_policy": "all_STEP_logs_meshes_and_coordinate_bearing_reports_private_local_only",
        },
        "repair_contract": private["repair_contract"],
        "mapped_25_face_trial": {
            "target_face_count": 25,
            "attempted_pair_count": target["repair"]["attempted_pair_count"],
            "baseline_pcurve_fault_count": target["baseline_pcurve_faults"]["result_count"],
            "residual_pcurve_fault_count": target["residual_pcurve_faults"]["result_count"],
            "residual_unique_face_count": target["residual_pcurve_faults"]["unique_face_count"],
            "property_delta": target["property_delta"],
            "same_3D_surfaces": target["shared_geometry"]["all_3D_surfaces_identical"],
            "same_3D_curves": target["shared_geometry"]["all_3D_curves_identical_or_both_null"],
        },
        "diagnostic_expansion": {
            "reason": "zero_BOP_gate_requires_testing_all_preexisting_curve_on_surface_fault_pairs",
            "attempted_pair_count": expanded["repair"]["attempted_pair_count"],
            "pre_export_residual_pcurve_fault_count": expanded["residual_pcurve_faults"]["result_count"],
            "pre_export_residual_unique_face_count": expanded["residual_pcurve_faults"]["unique_face_count"],
            "pre_export_residual_unique_edge_count": expanded["residual_pcurve_faults"]["unique_edge_count"],
            "maximum_sampled_edge_surface_deviation_scan_units": private[
                "residual_pair_chord_deviation"
            ]["maximum_deviation_scan_units"],
            "edge_surface_sample_classification": private["residual_pair_chord_deviation"][
                "classification"
            ],
            "property_delta": expanded["property_delta"],
            "same_3D_surfaces": expanded["shared_geometry"]["all_3D_surfaces_identical"],
            "same_3D_curves": expanded["shared_geometry"]["all_3D_curves_identical_or_both_null"],
            "maximum_edge_tolerance_scan_units": expanded["subshape_tolerances"][
                "maximum_edge_tolerance_scan_units"
            ],
        },
        "pre_export_full_BOPAlgo": {
            "result_count": pre_bop["result_count"],
            "status_counts": pre_bop["status_counts"],
            "private_indices_published": False,
        },
        "roundtrip": {
            "property_delta": roundtrip["property_delta"],
            "sampled_skin_distance": roundtrip["sampled_skin_distance"],
            "brepcheck": roundtrip["brepcheck"],
            "topology": roundtrip["topology"],
            "full_BOPAlgo": {
                "result_count": roundtrip_bop["result_count"],
                "status_counts": roundtrip_bop["status_counts"],
                "self_intersecting_face_count": len(
                    roundtrip_bop["self_intersecting_face_indices_private"]
                ),
                "invalid_pcurve_face_count": len(
                    roundtrip_bop["invalid_pcurve_face_indices_private"]
                ),
                "invalid_pcurve_edge_count": len(
                    roundtrip_bop["invalid_pcurve_edge_indices_private"]
                ),
                "private_indices_published": False,
            },
        },
        "gmsh_replay": gmsh,
        "gates": {
            **private["gates_before_gmsh"],
            "gmsh_3D_mesh_success": gmsh["volume_mesh_success"],
            "private_candidate_accepted": False,
            "manufacturing_authorized": False,
        },
        "decision": private["decision"],
        "image": {
            "filename": args.image.name,
            "sha256": sha256(args.image),
            "bytes": args.image.stat().st_size,
            "classification": "diagnostic_render_not_geometry_not_validation",
        },
        "publication": {
            "source_STEP_published": False,
            "candidate_STEP_published": False,
            "gmsh_mesh_or_log_published": False,
            "scan_derived_coordinates_published": False,
            "manufacturing_claim": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "verdict": result["verdict"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
