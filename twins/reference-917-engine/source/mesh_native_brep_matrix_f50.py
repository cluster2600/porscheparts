#!/usr/bin/env python3
"""Mesh an immutable native OCCT B-Rep through one explicit Gmsh profile.

Every invocation starts a fresh Gmsh process so failures (including HXT
allocator failures) cannot contaminate another profile.  The B-Rep is imported
read-only and no OCC boolean, healing, sewing or geometry mutation is called.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

import gmsh


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def classify_error(message: str) -> str:
    lowered = message.lower()
    if "two facets intersect" in lowered or "plc error" in lowered:
        return "PLC_FACET_INTERSECTION"
    if "requires netgen" in lowered:
        return "NETGEN_NOT_AVAILABLE"
    if "invalid boundary mesh" in lowered:
        return "INVALID_BOUNDARY_MESH"
    return "GMSH_EXCEPTION"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-brep", type=Path, required=True)
    parser.add_argument("--expected-sha256")
    parser.add_argument("--output-mesh", type=Path, required=True)
    parser.add_argument("--output-report", type=Path, required=True)
    parser.add_argument("--surface-algorithm", type=int, choices=(5, 6), required=True)
    parser.add_argument("--volume-algorithm", type=int, choices=(1, 4, 10), required=True)
    parser.add_argument("--minimum", type=float, required=True)
    parser.add_argument("--maximum", type=float, required=True)
    parser.add_argument("--curvature-points", type=int, default=0)
    parser.add_argument("--geometry-tolerance", type=float, default=1.0e-8)
    parser.add_argument("--facet-overlap-angle", type=float, default=0.1)
    args = parser.parse_args()
    input_sha = sha256(args.input_brep)
    if args.expected_sha256 and input_sha != args.expected_sha256:
        raise RuntimeError("native_BREP_SHA256_mismatch")
    args.output_mesh.parent.mkdir(parents=True, exist_ok=True)
    args.output_report.parent.mkdir(parents=True, exist_ok=True)

    profile = {
        "surface_algorithm": args.surface_algorithm,
        "volume_algorithm": args.volume_algorithm,
        "minimum_mm": args.minimum,
        "maximum_mm": args.maximum,
        "curvature_points_per_2pi": args.curvature_points,
        "geometry_tolerance_mm": args.geometry_tolerance,
        "facet_overlap_angle_deg": args.facet_overlap_angle,
    }
    report = {
        "schema": "porsche-917-f50-private-gmsh-profile/v1",
        "native_BREP_sha256": input_sha,
        "profile": profile,
        "master_geometry_mutation_used": False,
        "OCC_heal_or_sew_used": False,
        "global_ellipse_used": False,
        "global_oval_used": False,
        "global_box_used": False,
        "status": "FAILED",
        "mesh": None,
        "failure_class": None,
    }
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.option.setNumber("General.NumThreads", 1)
        gmsh.option.setNumber("Geometry.Tolerance", args.geometry_tolerance)
        gmsh.option.setNumber("Mesh.Algorithm", args.surface_algorithm)
        gmsh.option.setNumber("Mesh.Algorithm3D", args.volume_algorithm)
        gmsh.option.setNumber("Mesh.MeshSizeMin", args.minimum)
        gmsh.option.setNumber("Mesh.MeshSizeMax", args.maximum)
        gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", args.curvature_points)
        gmsh.option.setNumber("Mesh.AngleToleranceFacetOverlap", args.facet_overlap_angle)
        gmsh.model.add("f50_native_brep_mesh")
        imported = gmsh.model.occ.importShapes(str(args.input_brep), highestDimOnly=True)
        gmsh.model.occ.synchronize()
        volumes = gmsh.model.getEntities(3)
        if len(imported) != 1 or len(volumes) != 1:
            raise RuntimeError(f"native_BREP_import_not_one_volume:{len(imported)}:{len(volumes)}")
        gmsh.model.mesh.generate(3)
        types, groups, _ = gmsh.model.mesh.getElements(3)
        tags = [int(tag) for group in groups for tag in group]
        qualities = sorted(float(v) for v in gmsh.model.mesh.getElementQualities(tags, "minSICN"))
        if not tags:
            raise RuntimeError("Gmsh_generated_no_volume_elements")
        gmsh.write(str(args.output_mesh))

        def quantile(fraction: float) -> float:
            return qualities[min(len(qualities) - 1, int(fraction * (len(qualities) - 1)))]

        report["status"] = "PASS"
        report["mesh"] = {
            "filename": args.output_mesh.name,
            "sha256": sha256(args.output_mesh),
            "bytes": args.output_mesh.stat().st_size,
            "element_types_3d": [int(value) for value in types],
            "volume_elements": len(tags),
            "minimum_minSICN": qualities[0],
            "p01_minSICN": quantile(0.01),
            "p05_minSICN": quantile(0.05),
            "count_le_0": sum(value <= 0.0 for value in qualities),
            "count_lt_0_1": sum(value < 0.1 for value in qualities),
        }
        report["mesh"]["strict_quality_accepted"] = (
            report["mesh"]["count_le_0"] == 0
            and report["mesh"]["count_lt_0_1"] == 0
        )
    except Exception as error:
        report["failure_class"] = classify_error(str(error))
        # Raw messages may contain private geometry coordinates.  Keep only a
        # redacted diagnostic classification in the persisted report.
        report["redacted_exception"] = re.sub(
            r"[-+]?\d+(?:\.\d*)?(?:[eE][-+]?\d+)?", "N", str(error)
        )[:500]
    finally:
        gmsh.finalize()

    args.output_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report["status"],
                "failure_class": report["failure_class"],
                "volume_elements": report["mesh"]["volume_elements"] if report["mesh"] else 0,
                "minimum_minSICN": report["mesh"]["minimum_minSICN"] if report["mesh"] else None,
                "count_le_0": report["mesh"]["count_le_0"] if report["mesh"] else None,
                "strict_quality_accepted": (
                    report["mesh"]["strict_quality_accepted"] if report["mesh"] else False
                ),
            },
            sort_keys=True,
        )
    )
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
