#!/usr/bin/env python3
"""Create and audit a private surface tessellation from an immutable B-Rep.

The tessellation is a hash-linked derivative for an independent tetrahedralizer
only.  It is not a CAD repair and can never replace the native B-Rep master.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

import gmsh


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-brep", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--output-stl", type=Path, required=True)
    parser.add_argument("--output-msh", type=Path, required=True)
    parser.add_argument("--output-report", type=Path, required=True)
    parser.add_argument("--minimum", type=float, default=1.0)
    parser.add_argument("--maximum", type=float, default=4.0)
    parser.add_argument("--curvature-points", type=int, default=60)
    args = parser.parse_args()
    source_sha = sha256(args.input_brep)
    if source_sha != args.expected_sha256:
        raise RuntimeError("native_BREP_SHA256_mismatch")
    for path in (args.output_stl, args.output_msh, args.output_report):
        path.parent.mkdir(parents=True, exist_ok=True)

    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.option.setNumber("General.NumThreads", 1)
        gmsh.option.setNumber("Mesh.Algorithm", 5)
        gmsh.option.setNumber("Mesh.MeshSizeMin", args.minimum)
        gmsh.option.setNumber("Mesh.MeshSizeMax", args.maximum)
        gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", args.curvature_points)
        gmsh.model.add("f50_native_brep_surface")
        imported = gmsh.model.occ.importShapes(str(args.input_brep), highestDimOnly=True)
        gmsh.model.occ.synchronize()
        if len(imported) != 1 or len(gmsh.model.getEntities(3)) != 1:
            raise RuntimeError("native_BREP_import_not_one_volume")
        gmsh.model.mesh.generate(2)

        node_tags, flat_coordinates, _ = gmsh.model.mesh.getNodes()
        points = {
            int(tag): (
                float(flat_coordinates[3 * index]),
                float(flat_coordinates[3 * index + 1]),
                float(flat_coordinates[3 * index + 2]),
            )
            for index, tag in enumerate(node_tags)
        }
        element_types, _, connectivity_groups = gmsh.model.mesh.getElements(2)
        triangles: list[tuple[int, int, int]] = []
        unsupported: list[int] = []
        for element_type, connectivity in zip(element_types, connectivity_groups):
            _, dimension, _, node_count, _, _ = gmsh.model.mesh.getElementProperties(int(element_type))
            if dimension != 2 or node_count != 3:
                unsupported.append(int(element_type))
                continue
            triangles.extend(
                tuple(int(connectivity[offset + local]) for local in range(3))
                for offset in range(0, len(connectivity), 3)
            )
        if unsupported or not triangles:
            raise RuntimeError(f"surface_not_linear_triangles:{unsupported}:{len(triangles)}")

        edge_use: Counter[tuple[int, int]] = Counter()
        signed_volume = 0.0
        bounds_min = [math.inf, math.inf, math.inf]
        bounds_max = [-math.inf, -math.inf, -math.inf]
        for a, b, c in triangles:
            edge_use.update(
                [tuple(sorted((a, b))), tuple(sorted((b, c))), tuple(sorted((c, a)))]
            )
            pa, pb, pc = points[a], points[b], points[c]
            signed_volume += (
                pa[0] * (pb[1] * pc[2] - pb[2] * pc[1])
                - pa[1] * (pb[0] * pc[2] - pb[2] * pc[0])
                + pa[2] * (pb[0] * pc[1] - pb[1] * pc[0])
            ) / 6.0
            for point in (pa, pb, pc):
                for axis in range(3):
                    bounds_min[axis] = min(bounds_min[axis], point[axis])
                    bounds_max[axis] = max(bounds_max[axis], point[axis])

        edge_histogram = Counter(edge_use.values())
        watertight = edge_histogram.get(1, 0) == 0 and sum(
            count for uses, count in edge_histogram.items() if uses != 2
        ) == 0
        gmsh.write(str(args.output_msh))
        gmsh.write(str(args.output_stl))
    finally:
        gmsh.finalize()

    report = {
        "schema": "porsche-917-f50-private-surface-tessellation/v1",
        "native_BREP": {"sha256": source_sha},
        "profile": {
            "surface_algorithm": 5,
            "minimum_mm": args.minimum,
            "maximum_mm": args.maximum,
            "curvature_points_per_2pi": args.curvature_points,
        },
        "master_geometry_mutation_used": False,
        "OCC_heal_or_sew_used": False,
        "tessellation": {
            "node_count": len(points),
            "triangle_count": len(triangles),
            "unique_edge_count": len(edge_use),
            "edge_use_histogram": {str(key): value for key, value in sorted(edge_histogram.items())},
            "watertight_by_triangle_edge_incidence": watertight,
            "signed_volume_mm3": signed_volume,
            "absolute_signed_volume_mm3": abs(signed_volume),
            "bbox_mm": bounds_min + bounds_max,
            "msh": {"filename": args.output_msh.name, "sha256": sha256(args.output_msh)},
            "stl": {"filename": args.output_stl.name, "sha256": sha256(args.output_stl)},
        },
        "independent_tetrahedralizer_allowed": watertight,
        "release": {"manufacturing_authorized": False, "engine_start_authorized": False},
    }
    args.output_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "watertight": watertight,
                "nodes": len(points),
                "triangles": len(triangles),
                "edge_use_histogram": report["tessellation"]["edge_use_histogram"],
                "absolute_signed_volume_mm3": abs(signed_volume),
                "bbox_mm": report["tessellation"]["bbox_mm"],
            },
            sort_keys=True,
        )
    )
    return 0 if watertight else 2


if __name__ == "__main__":
    raise SystemExit(main())
