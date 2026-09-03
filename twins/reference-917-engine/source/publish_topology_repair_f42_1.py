#!/usr/bin/env python3
"""Publie le verdict F42.1 sans STEP ni coordonnees privees."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-report", type=Path, required=True)
    parser.add_argument("--face-map", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    private = json.loads(args.private_report.read_text(encoding="utf-8"))
    face_map = json.loads(args.face_map.read_text(encoding="utf-8"))
    roundtrip = private["roundtrip"]
    result = {
        "schema": "porsche-917-f42.1-public-topology-repair-summary/v1",
        "phase": "F42.1",
        "verdict": private["verdict"],
        "private_evidence_binding": {
            "source_STEP_sha256": private["input"]["sha256"],
            "rejected_candidate_STEP_sha256": private["private_candidate"]["sha256"],
            "private_report_sha256": sha256(args.private_report),
            "repository_policy": "all_STEP_and_coordinate_bearing_reports_private_local_only",
        },
        "repair_scope": private["repair_scope"],
        "baseline": private["baseline"],
        "tolerance_trials": [
            {
                "same_parameter_tolerance_scan_units": trial[
                    "same_parameter_tolerance_scan_units"
                ],
                "pcurve_fault_count": trial["pcurve_screen"]["fault_count"],
                "maximum_bbox_coordinate_delta_scan_units": trial["property_delta"][
                    "maximum_bbox_coordinate_delta_scan_units"
                ],
                "volume_delta_scan_units_cubed": trial["property_delta"][
                    "volume_delta_scan_units_cubed"
                ],
                "surface_area_delta_scan_units_squared": trial["property_delta"][
                    "surface_area_delta_scan_units_squared"
                ],
                "all_3D_surfaces_identical": trial["shared_geometry"][
                    "all_3D_surfaces_identical"
                ],
                "all_3D_curves_identical_or_both_null": trial["shared_geometry"][
                    "all_3D_curves_identical_or_both_null"
                ],
                "strict_non_deformation_invariants_pass": trial[
                    "strict_non_deformation_invariants_pass"
                ],
            }
            for trial in private["tolerance_trials"]
        ],
        "selected_tolerance_scan_units": private["selected_tolerance_scan_units"],
        "roundtrip": {
            "property_delta": roundtrip["property_delta"],
            "brepcheck": roundtrip["brepcheck"],
            "topology": roundtrip["topology"],
            "sampled_skin_distance": roundtrip["sampled_skin_distance"],
            "boolean_argument_analyzer": {
                "result_count": roundtrip["boolean_argument_analyzer"]["result_count"],
                "status_counts": roundtrip["boolean_argument_analyzer"]["status_counts"],
                "self_intersecting_face_count": len(
                    roundtrip["boolean_argument_analyzer"][
                        "self_intersecting_face_indices_private"
                    ]
                ),
                "invalid_pcurve_face_count": len(
                    roundtrip["boolean_argument_analyzer"][
                        "invalid_pcurve_face_indices_private"
                    ]
                ),
                "invalid_pcurve_edge_count": len(
                    roundtrip["boolean_argument_analyzer"][
                        "invalid_pcurve_edge_indices_private"
                    ]
                ),
                "private_indices_published": False,
            },
        },
        "gmsh_replay": face_map["gmsh"],
        "face_reconstruction_map": {
            "filename": args.face_map.name,
            "sha256": sha256(args.face_map),
            "unique_face_count": len(face_map["faces"]),
            "all_faces_are_BSpline": all(
                face["surface_type"] == "GeomAbs_BSplineSurface" for face in face_map["faces"]
            ),
            "self_intersection_overlap_count": sum(
                bool(face["BOP_self_intersect"]) for face in face_map["faces"]
            ),
            "invalid_pcurve_overlap_count": sum(
                bool(face["BOP_invalid_curve_on_surface"]) for face in face_map["faces"]
            ),
        },
        "image": {
            "filename": args.image.name,
            "sha256": sha256(args.image),
            "bytes": args.image.stat().st_size,
            "classification": "diagnostic_face_map_not_geometry_not_validation",
        },
        "gates": private["gates"],
        "decision": private["decision"],
        "publication": {
            "source_STEP_published": False,
            "candidate_STEP_published": False,
            "scan_derived_face_or_sample_coordinates_published": False,
            "aggregate_bbox_and_center_metrics_published": True,
            "manufacturing_claim": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "verdict": result["verdict"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
