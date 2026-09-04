#!/usr/bin/env python3
"""Publie un resume F42 sans coordonnees derivees du STEP prive."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def public_summary(
    local: dict[str, Any],
    local_path: Path,
    gmsh_log: Path | None = None,
    image: Path | None = None,
) -> dict[str, Any]:
    thickness = local["exact_sampled_thickness"]
    argument = local["boolean_argument_analyzer"]
    result = {
        "schema": "porsche-917-f42-public-brep-audit-summary/v1",
        "phase": "F42",
        "verdict": local["verdict"],
        "private_evidence_binding": {
            "input_sha256": local["input"]["sha256"],
            "input_bytes": local["input"]["bytes"],
            "input_repository_policy": "private_local_only_not_copied_to_git",
            "full_local_report_sha256": sha256(local_path),
            "full_local_report_repository_policy": "private_local_only_contains_scan_derived_coordinates",
        },
        "unit_status": local["unit_status"],
        "external_envelope_lock": local["external_envelope_lock"],
        "exact_properties": local["exact_properties"],
        "topology": local["topology"],
        "brepcheck": local["brepcheck"],
        "tolerances_and_small_features": local["tolerances_and_small_features"],
        "boolean_argument_analyzer": {
            "modes": argument["modes"],
            "has_faulty": argument["has_faulty"],
            "has_error": argument["has_error"],
            "has_warning": argument["has_warning"],
            "result_count": argument["result_count"],
            "status_counts": argument["status_counts"],
            "faulty_shape_type_counts": argument["faulty_shape_type_counts"],
            "coordinates_published": False,
        },
        "exact_sampled_thickness": {
            key: value
            for key, value in thickness.items()
            if key != "smallest_fifty_samples"
        },
        "gates": local["gates"],
        "repair_decision": local["repair_decision"],
        "release_gates": local["release_gates"],
        "publication": {
            "raw_STEP_published": False,
            "repaired_STEP_published": False,
            "scan_derived_point_coordinates_published": False,
        },
    }
    if gmsh_log is not None:
        log = gmsh_log.read_text(encoding="utf-8", errors="replace")
        invalid = [
            (int(count), int(surface))
            for count, surface in re.findall(
                r"Warning : (\d+) elements remain invalid in surface (\d+)", log
            )
        ]
        result["independent_gmsh_screen"] = {
            "software": "Gmsh 4.12.1 using OpenCASCADE STEP importer",
            "container_image_digest": "sha256:4a19fa7d1f253beb3106970ae2635cff85d5aeeaf062aaf807d1dab7b940fb33",
            "input_mount": "read_only",
            "surface_invalid_warning_event_count": len(invalid),
            "unique_surfaces_with_invalid_element_warning": sorted({surface for _, surface in invalid}),
            "cumulative_invalid_elements_across_repeated_refinement_warnings": sum(
                count for count, _ in invalid
            ),
            "cumulative_count_is_not_unique_elements": True,
            "three_dimensional_mesh_completed": "Done meshing 3D" in log,
            "output_mesh_published": False,
            "terminated_after_repeated_surface_refinement": "forcefully exiting" in log,
            "gate_independent_volume_mesh_completed": False,
        }
    if image is not None:
        result["public_image"] = {
            "filename": image.name,
            "sha256": sha256(image),
            "bytes": image.stat().st_size,
            "classification": "diagnostic_render_not_geometry_not_validation",
        }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--local-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--gmsh-log", type=Path)
    parser.add_argument("--image", type=Path)
    args = parser.parse_args()
    local = json.loads(args.local_report.read_text(encoding="utf-8"))
    result = public_summary(local, args.local_report, args.gmsh_log, args.image)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "verdict": result["verdict"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
