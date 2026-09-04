#!/usr/bin/env python3
"""Index an already welded binary STL into a minimum-valid USD stage.

This converter does not smooth, repair, scale or move the source coordinates.
It rejects open, non-manifold and degenerate triangle topology before writing
the private USD used by the F42 Omniverse diagnostic.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import struct

from pxr import Gf, Usd, UsdGeom


TRIANGLE_RECORD = struct.Struct("<12fH")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_stl", type=Path)
    parser.add_argument("output_usd", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    payload = args.input_stl.read_bytes()
    if len(payload) < 84:
        raise SystemExit("binary STL is too short")
    triangle_count = struct.unpack_from("<I", payload, 80)[0]
    expected_size = 84 + triangle_count * TRIANGLE_RECORD.size
    if len(payload) != expected_size:
        raise SystemExit(
            f"binary STL size mismatch: expected {expected_size}, got {len(payload)}"
        )

    points: list[tuple[float, float, float]] = []
    point_index: dict[tuple[float, float, float], int] = {}
    indices: list[int] = []
    normals: list[tuple[float, float, float]] = []
    edges: Counter[tuple[int, int]] = Counter()
    offset = 84
    for _ in range(triangle_count):
        record = TRIANGLE_RECORD.unpack_from(payload, offset)
        offset += TRIANGLE_RECORD.size
        face: list[int] = []
        for vertex_offset in (3, 6, 9):
            point = tuple(
                float(value) for value in record[vertex_offset : vertex_offset + 3]
            )
            if not all(math.isfinite(value) for value in point):
                raise SystemExit("non-finite STL coordinate")
            index = point_index.get(point)
            if index is None:
                index = len(points)
                point_index[point] = index
                points.append(point)
            face.append(index)
        if len(set(face)) != 3:
            raise SystemExit("degenerate triangle after exact vertex indexing")
        indices.extend(face)
        a, b, c = (points[index] for index in face)
        ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        ac = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
        normal = (
            ab[1] * ac[2] - ab[2] * ac[1],
            ab[2] * ac[0] - ab[0] * ac[2],
            ab[0] * ac[1] - ab[1] * ac[0],
        )
        normal_length = math.sqrt(sum(value * value for value in normal))
        if not math.isfinite(normal_length) or normal_length == 0.0:
            raise SystemExit("zero-area triangle after exact vertex indexing")
        unit_normal = tuple(value / normal_length for value in normal)
        normals.extend((unit_normal, unit_normal, unit_normal))
        for a_index, b_index in (
            (face[0], face[1]),
            (face[1], face[2]),
            (face[2], face[0]),
        ):
            edges[tuple(sorted((a_index, b_index)))] += 1

    boundary_edges = sum(incidence == 1 for incidence in edges.values())
    nonmanifold_edges = sum(incidence > 2 for incidence in edges.values())
    if boundary_edges or nonmanifold_edges:
        raise SystemExit(
            f"topology rejected: boundary_edges={boundary_edges}, "
            f"nonmanifold_edges={nonmanifold_edges}"
        )

    minimum = tuple(min(point[axis] for point in points) for axis in range(3))
    maximum = tuple(max(point[axis] for point in points) for axis in range(3))
    args.output_usd.parent.mkdir(parents=True, exist_ok=True)
    stage = Usd.Stage.CreateNew(str(args.output_usd))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 0.001)
    root = UsdGeom.Xform.Define(stage, "/HeadF41Baseline")
    UsdGeom.Scope.Define(stage, "/HeadF41Baseline/HeadSolid")
    mesh = UsdGeom.Mesh.Define(stage, "/HeadF41Baseline/HeadSolid/Mesh")
    mesh.CreatePointsAttr(points)
    mesh.CreateFaceVertexCountsAttr([3] * triangle_count)
    mesh.CreateFaceVertexIndicesAttr(indices)
    mesh.CreateNormalsAttr(normals)
    mesh.SetNormalsInterpolation(UsdGeom.Tokens.faceVarying)
    mesh.CreateExtentAttr([Gf.Vec3f(*minimum), Gf.Vec3f(*maximum)])
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    mesh.CreateOrientationAttr(UsdGeom.Tokens.rightHanded)
    stage.SetDefaultPrim(root.GetPrim())
    stage.GetRootLayer().Save()

    report = {
        "schema_version": "1.0.0",
        "conversion_scope": (
            "exact binary STL coordinates; no smoothing or geometry repair"
        ),
        "triangle_count": triangle_count,
        "point_count": len(points),
        "unique_edge_count": len(edges),
        "boundary_edge_count": boundary_edges,
        "nonmanifold_edge_count": nonmanifold_edges,
        "coordinate_displacement": 0.0,
        "authored_normals": "faceVarying geometric triangle normals",
        "authored_extent": [list(minimum), list(maximum)],
        "meters_per_unit": 0.001,
        "up_axis": "Z",
        "default_prim": "/HeadF41Baseline",
        "passed": True,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
