#!/usr/bin/env python3
"""Author and round-trip audit a private USD from an F51 surface archive.

The operation is deliberately geometry preserving: points keep their numeric
millimetre coordinates, stage units are explicit, and no Xform, proxy,
material or physics schema is authored.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from pxr import Gf, Kind, Usd, UsdGeom, Vt


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def topology(points: np.ndarray, triangles: np.ndarray) -> dict[str, object]:
    edge_incidence: Counter[tuple[int, int]] = Counter()
    edge_orientation: Counter[tuple[int, int]] = Counter()
    triangle_points = points[triangles]
    cross = np.cross(
        triangle_points[:, 1] - triangle_points[:, 0],
        triangle_points[:, 2] - triangle_points[:, 0],
    )
    double_areas = np.linalg.norm(cross, axis=1)
    for triangle in triangles:
        for first, second in (
            (int(triangle[0]), int(triangle[1])),
            (int(triangle[1]), int(triangle[2])),
            (int(triangle[2]), int(triangle[0])),
        ):
            key = (min(first, second), max(first, second))
            edge_incidence[key] += 1
            edge_orientation[key] += 1 if first < second else -1
    signed_volume = float(
        np.einsum(
            "ij,ij->i",
            triangle_points[:, 0],
            np.cross(triangle_points[:, 1], triangle_points[:, 2]),
        ).sum()
        / 6.0
    )
    return {
        "unique_edge_count": len(edge_incidence),
        "boundary_edge_count": sum(value == 1 for value in edge_incidence.values()),
        "nonmanifold_edge_count": sum(value > 2 for value in edge_incidence.values()),
        "winding_conflict_edge_count": sum(
            edge_incidence[key] == 2 and edge_orientation[key] != 0
            for key in edge_incidence
        ),
        "degenerate_triangle_count": int(np.count_nonzero(double_areas <= 1.0e-12)),
        "signed_volume_scan_units_cubed": signed_volume,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-archive", type=Path, required=True)
    parser.add_argument("--expected-archive-sha256", required=True)
    parser.add_argument("--expected-brep-sha256", required=True)
    parser.add_argument("--variant", choices=("2V", "4V"), required=True)
    parser.add_argument("--output-usd", type=Path, required=True)
    parser.add_argument("--output-report", type=Path, required=True)
    args = parser.parse_args()

    if args.output_usd.exists():
        raise RuntimeError("refusing_to_overwrite_private_USD")
    archive_sha = sha256(args.input_archive)
    if archive_sha != args.expected_archive_sha256:
        raise RuntimeError("surface_archive_SHA256_mismatch")
    with np.load(args.input_archive, allow_pickle=False) as payload:
        points64 = np.asarray(payload["points"], dtype=np.float64)
        triangles = np.asarray(payload["triangles"], dtype=np.int64)
        source_normals = np.asarray(payload["normals"], dtype=np.float64)
        metadata = json.loads(str(payload["metadata_json"].item()))
    if metadata["variant"] != args.variant:
        raise RuntimeError("surface_archive_variant_mismatch")
    if metadata["native_BREP_sha256"] != args.expected_brep_sha256:
        raise RuntimeError("surface_archive_BREP_SHA256_mismatch")
    if points64.ndim != 2 or points64.shape[1] != 3:
        raise RuntimeError("surface_archive_points_shape_invalid")
    if triangles.ndim != 2 or triangles.shape[1] != 3:
        raise RuntimeError("surface_archive_triangles_shape_invalid")
    if source_normals.shape != (len(triangles), 3):
        raise RuntimeError("surface_archive_normals_shape_invalid")
    if triangles.min(initial=0) < 0 or triangles.max(initial=0) >= len(points64):
        raise RuntimeError("surface_archive_index_out_of_range")

    points32 = np.ascontiguousarray(points64, dtype=np.float32)
    triangles32 = np.ascontiguousarray(triangles, dtype=np.int32)
    triangle_points = points32[triangles32].astype(np.float64)
    cross = np.cross(
        triangle_points[:, 1] - triangle_points[:, 0],
        triangle_points[:, 2] - triangle_points[:, 0],
    )
    lengths = np.linalg.norm(cross, axis=1)
    if np.any(lengths <= 1.0e-12):
        raise RuntimeError("float32_USD_quantization_created_degenerate_triangle")
    normals32 = np.ascontiguousarray(cross / lengths[:, None], dtype=np.float32)
    minimum = points32.min(axis=0)
    maximum = points32.max(axis=0)

    args.output_usd.parent.mkdir(parents=True, exist_ok=True)
    args.output_report.parent.mkdir(parents=True, exist_ok=True)
    stage = Usd.Stage.CreateNew(str(args.output_usd))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 0.001)
    root_name = f"Porsche917Head{args.variant}F51"
    root_path = f"/{root_name}"
    root = UsdGeom.Xform.Define(stage, root_path)
    Usd.ModelAPI(root.GetPrim()).SetKind(Kind.Tokens.component)
    root.GetPrim().SetCustomDataByKey("nativeBREPSha256", args.expected_brep_sha256)
    root.GetPrim().SetCustomDataByKey("surfaceArchiveSha256", archive_sha)
    root.GetPrim().SetCustomDataByKey("variant", args.variant)
    geometry = UsdGeom.Scope.Define(stage, f"{root_path}/Geometry")
    mesh = UsdGeom.Mesh.Define(stage, f"{root_path}/Geometry/HeadSurface")
    mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(points32))
    mesh.CreateFaceVertexCountsAttr(
        Vt.IntArray.FromNumpy(np.full(len(triangles32), 3, dtype=np.int32))
    )
    mesh.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(triangles32.reshape(-1)))
    mesh.CreateNormalsAttr(Vt.Vec3fArray.FromNumpy(normals32))
    mesh.SetNormalsInterpolation(UsdGeom.Tokens.uniform)
    mesh.CreateExtentAttr(
        Vt.Vec3fArray([Gf.Vec3f(*minimum.tolist()), Gf.Vec3f(*maximum.tolist())])
    )
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    mesh.CreateOrientationAttr(UsdGeom.Tokens.rightHanded)
    mesh.CreateDoubleSidedAttr(False)
    stage.SetDefaultPrim(root.GetPrim())
    stage.GetRootLayer().Save()

    reopened = Usd.Stage.Open(str(args.output_usd))
    if reopened is None:
        raise RuntimeError("USD_roundtrip_open_failed")
    default_prim = reopened.GetDefaultPrim()
    meshes = [prim for prim in reopened.Traverse() if prim.IsA(UsdGeom.Mesh)]
    component_prims = [
        prim
        for prim in reopened.Traverse()
        if Usd.ModelAPI(prim).GetKind() == Kind.Tokens.component
    ]
    if len(meshes) != 1:
        raise RuntimeError(f"USD_roundtrip_mesh_count:{len(meshes)}")
    roundtrip_mesh = UsdGeom.Mesh(meshes[0])
    roundtrip_points = np.asarray(roundtrip_mesh.GetPointsAttr().Get(), dtype=np.float32)
    roundtrip_indices = np.asarray(
        roundtrip_mesh.GetFaceVertexIndicesAttr().Get(), dtype=np.int64
    ).reshape(-1, 3)
    roundtrip_counts = np.asarray(
        roundtrip_mesh.GetFaceVertexCountsAttr().Get(), dtype=np.int64
    )
    roundtrip_normals = np.asarray(roundtrip_mesh.GetNormalsAttr().Get(), dtype=np.float64)
    audited_topology = topology(roundtrip_points.astype(np.float64), roundtrip_indices)
    authored_bbox = np.concatenate((points32.min(axis=0), points32.max(axis=0))).astype(
        np.float64
    )
    roundtrip_bbox = np.concatenate(
        (roundtrip_points.min(axis=0), roundtrip_points.max(axis=0))
    ).astype(np.float64)
    normal_lengths = np.linalg.norm(roundtrip_normals, axis=1)
    geometric_normals = normals32.astype(np.float64)
    normal_alignment = np.einsum("ij,ij->i", roundtrip_normals, geometric_normals)
    xform_ops = UsdGeom.Xformable(default_prim).GetOrderedXformOps()
    applied_schemas = [schema for prim in reopened.Traverse() for schema in prim.GetAppliedSchemas()]
    maximum_float32_quantization = float(np.max(np.abs(points64 - points32.astype(np.float64))))
    accepted = (
        bool(default_prim)
        and default_prim.GetPath().pathString == root_path
        and UsdGeom.GetStageUpAxis(reopened) == UsdGeom.Tokens.z
        and math.isclose(UsdGeom.GetStageMetersPerUnit(reopened), 0.001, abs_tol=0.0)
        and len(component_prims) == 1
        and len(meshes) == 1
        and len(xform_ops) == 0
        and np.array_equal(roundtrip_counts, np.full(len(triangles), 3, dtype=np.int64))
        and np.array_equal(roundtrip_indices, triangles)
        and len(roundtrip_normals) == len(triangles)
        and roundtrip_mesh.GetNormalsInterpolation() == UsdGeom.Tokens.uniform
        and float(np.max(np.abs(normal_lengths - 1.0))) <= 1.0e-6
        and float(np.min(normal_alignment)) >= 1.0 - 1.0e-6
        and audited_topology["boundary_edge_count"] == 0
        and audited_topology["nonmanifold_edge_count"] == 0
        and audited_topology["winding_conflict_edge_count"] == 0
        and audited_topology["degenerate_triangle_count"] == 0
        and audited_topology["signed_volume_scan_units_cubed"] > 0.0
        and maximum_float32_quantization <= 5.0e-6
        and float(np.max(np.abs(authored_bbox - roundtrip_bbox))) == 0.0
        and not any("Physics" in schema or "MaterialBindingAPI" in schema for schema in applied_schemas)
    )
    report = {
        "schema": "porsche-917-f51-private-native-surface-usd/v1",
        "variant": args.variant,
        "source": {
            "native_BREP_sha256": args.expected_brep_sha256,
            "surface_archive_sha256": archive_sha,
        },
        "operations": {
            "point_scale_transform": [1.0, 1.0, 1.0],
            "xform_op_count": len(xform_ops),
            "proxy_used": False,
            "geometry_repair_used": False,
            "ellipse_or_oval_used": False,
            "material_assignment_used": False,
            "physics_authoring_used": False,
        },
        "USD": {
            "filename": args.output_usd.name,
            "sha256": sha256(args.output_usd),
            "bytes": args.output_usd.stat().st_size,
            "format": args.output_usd.suffix.lower(),
            "stage_roundtrip_opened": True,
            "default_prim": default_prim.GetPath().pathString,
            "up_axis": str(UsdGeom.GetStageUpAxis(reopened)),
            "meters_per_unit": UsdGeom.GetStageMetersPerUnit(reopened),
            "mesh_count": len(meshes),
            "component_count": len(component_prims),
            "point_count": len(roundtrip_points),
            "triangle_count": len(roundtrip_indices),
            "normal_count": len(roundtrip_normals),
            "normal_interpolation": str(roundtrip_mesh.GetNormalsInterpolation()),
            "normal_length_maximum_error": float(np.max(np.abs(normal_lengths - 1.0))),
            "normal_alignment_minimum": float(np.min(normal_alignment)),
            "maximum_float32_coordinate_quantization_scan_units": maximum_float32_quantization,
            "authored_bbox_scan_units_private": authored_bbox.tolist(),
            "roundtrip_bbox_scan_units_private": roundtrip_bbox.tolist(),
            "roundtrip_bbox_maximum_delta_scan_units": float(
                np.max(np.abs(authored_bbox - roundtrip_bbox))
            ),
            "topology": audited_topology,
            "applied_schemas": applied_schemas,
        },
        "accepted_for_external_USD_validators": accepted,
        "release": {
            "simready_validated": False,
            "manufacturing_authorized": False,
            "engine_start_authorized": False,
        },
    }
    args.output_report.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "variant": args.variant,
                "accepted_for_external_USD_validators": accepted,
                "USD_sha256": report["USD"]["sha256"],
                "mesh_count": len(meshes),
                "component_count": len(component_prims),
                "point_count": len(roundtrip_points),
                "triangle_count": len(roundtrip_indices),
                "boundary_edge_count": audited_topology["boundary_edge_count"],
                "nonmanifold_edge_count": audited_topology["nonmanifold_edge_count"],
                "winding_conflict_edge_count": audited_topology[
                    "winding_conflict_edge_count"
                ],
                "meters_per_unit": report["USD"]["meters_per_unit"],
                "xform_op_count": len(xform_ops),
            },
            sort_keys=True,
        )
    )
    return 0 if accepted else 2


if __name__ == "__main__":
    raise SystemExit(main())
