#!/usr/bin/env python3
"""Tessellate an immutable F50 native B-Rep for private USD authoring.

The native ``.brep`` is imported directly by Gmsh's OCCT backend.  This stage
does not heal, sew, scale, transform or export CAD.  It emits a private NumPy
archive only after the surface is closed, consistently wound and tied to an
accepted F50 master hash.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import gmsh
import numpy as np
from OCP.BRep import BRep_Builder
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepGProp import BRepGProp
from OCP.BRepTools import BRepTools
from OCP.Bnd import Bnd_Box
from OCP.GProp import GProp_GProps
from OCP.TopoDS import TopoDS_Shape


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def quantile(values: np.ndarray, fraction: float) -> float:
    return float(np.quantile(values, fraction)) if values.size else math.inf


def component_count(triangles: np.ndarray, inverse: np.ndarray, counts: np.ndarray) -> int:
    parent = np.arange(len(triangles), dtype=np.int64)
    rank = np.zeros(len(triangles), dtype=np.uint8)

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = int(parent[index])
        return index

    def union(first: int, second: int) -> None:
        first_root = find(first)
        second_root = find(second)
        if first_root == second_root:
            return
        if rank[first_root] < rank[second_root]:
            first_root, second_root = second_root, first_root
        parent[second_root] = first_root
        if rank[first_root] == rank[second_root]:
            rank[first_root] += 1

    triangle_ids = np.tile(np.arange(len(triangles), dtype=np.int64), 3)
    ordering = np.argsort(inverse, kind="stable")
    grouped_triangles = triangle_ids[ordering]
    offsets = np.concatenate(([0], np.cumsum(counts, dtype=np.int64)))
    for edge_index in np.flatnonzero(counts == 2):
        start = int(offsets[edge_index])
        union(int(grouped_triangles[start]), int(grouped_triangles[start + 1]))
    return len({find(index) for index in range(len(triangles))})


def orient_triangles_consistently(triangles: np.ndarray, points: np.ndarray) -> tuple[np.ndarray, int, int]:
    """Normalize only index winding; vertex coordinates remain byte-identical."""

    directed_edges = np.vstack(
        (triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [2, 0]])
    )
    edge_signs = np.where(directed_edges[:, 0] < directed_edges[:, 1], 1, -1)
    canonical_edges = np.sort(directed_edges, axis=1)
    _, inverse, counts = np.unique(
        canonical_edges, axis=0, return_inverse=True, return_counts=True
    )
    orientation_sum = np.bincount(inverse, weights=edge_signs, minlength=len(counts))
    conflicts_before = int(np.count_nonzero((counts == 2) & (orientation_sum != 0)))
    if np.any(counts != 2):
        return triangles, 0, conflicts_before

    triangle_ids = np.tile(np.arange(len(triangles), dtype=np.int64), 3)
    ordering = np.argsort(inverse, kind="stable")
    grouped_triangles = triangle_ids[ordering]
    grouped_signs = edge_signs[ordering]
    offsets = np.concatenate(([0], np.cumsum(counts, dtype=np.int64)))
    adjacency: list[list[tuple[int, bool]]] = [[] for _ in range(len(triangles))]
    for edge_index in range(len(counts)):
        start = int(offsets[edge_index])
        first_triangle = int(grouped_triangles[start])
        second_triangle = int(grouped_triangles[start + 1])
        toggle = bool(grouped_signs[start] == grouped_signs[start + 1])
        adjacency[first_triangle].append((second_triangle, toggle))
        adjacency[second_triangle].append((first_triangle, toggle))

    flip = np.full(len(triangles), -1, dtype=np.int8)
    for start in range(len(triangles)):
        if flip[start] != -1:
            continue
        flip[start] = 0
        stack = [start]
        while stack:
            current = stack.pop()
            for neighbor, toggle in adjacency[current]:
                expected = int(flip[current]) ^ int(toggle)
                if flip[neighbor] == -1:
                    flip[neighbor] = expected
                    stack.append(neighbor)
                elif int(flip[neighbor]) != expected:
                    raise RuntimeError("surface_triangle_winding_is_nonorientable")

    result = triangles.copy()
    mask = flip == 1
    result[mask] = result[mask][:, [0, 2, 1]]
    triangle_points = points[result]
    signed_volume = float(
        np.einsum(
            "ij,ij->i",
            triangle_points[:, 0],
            np.cross(triangle_points[:, 1], triangle_points[:, 2]),
        ).sum()
        / 6.0
    )
    if signed_volume < 0.0:
        result = result[:, [0, 2, 1]]
        mask = ~mask
    return result, int(np.count_nonzero(mask)), conflicts_before


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-brep", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--variant", choices=("2V", "4V"), required=True)
    parser.add_argument("--f50-public-evidence", type=Path, required=True)
    parser.add_argument("--output-archive", type=Path, required=True)
    parser.add_argument("--output-report", type=Path, required=True)
    parser.add_argument("--minimum", type=float, default=1.0)
    parser.add_argument("--maximum", type=float, default=4.0)
    parser.add_argument("--curvature-points", type=int, default=60)
    args = parser.parse_args()

    if args.output_archive.exists():
        raise RuntimeError("refusing_to_overwrite_private_surface_archive")
    source_sha = sha256(args.input_brep)
    if source_sha != args.expected_sha256:
        raise RuntimeError("native_BREP_SHA256_mismatch")
    f50 = json.loads(args.f50_public_evidence.read_text(encoding="utf-8"))
    master = f50["native_OCCT_masters"][args.variant]
    if master["private_native_BREP_sha256"] != source_sha:
        raise RuntimeError("F50_public_authority_hash_mismatch")
    if not master["accepted_as_private_same_kernel_CAD_CAE_master"]:
        raise RuntimeError("F50_native_master_not_accepted")
    if master["roundtrip"]["bbox_maximum_coordinate_delta_scan_units"] != 0.0:
        raise RuntimeError("F50_native_master_not_F43_bbox_locked")

    native_shape = TopoDS_Shape()
    if not BRepTools.Read_s(native_shape, str(args.input_brep), BRep_Builder()):
        raise RuntimeError("native_BREP_read_failed")
    exact_check = BRepCheck_Analyzer(native_shape, True)
    exact_check.SetExactMethod(True)
    exact_check.SetParallel(True)
    if not exact_check.IsValid():
        raise RuntimeError("native_BREP_exact_BRepCheck_failed")
    bounds = Bnd_Box()
    BRepBndLib.AddOptimal_s(native_shape, bounds, True, False)
    brep_bbox = np.asarray(bounds.Get(), dtype=np.float64)
    volume_properties = GProp_GProps()
    BRepGProp.VolumeProperties_s(native_shape, volume_properties)
    brep_volume = float(volume_properties.Mass())

    args.output_archive.parent.mkdir(parents=True, exist_ok=True)
    args.output_report.parent.mkdir(parents=True, exist_ok=True)
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.option.setNumber("General.NumThreads", 1)
        gmsh.option.setNumber("Mesh.Algorithm", 5)
        gmsh.option.setNumber("Mesh.MeshSizeMin", args.minimum)
        gmsh.option.setNumber("Mesh.MeshSizeMax", args.maximum)
        gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", args.curvature_points)
        gmsh.model.add(f"f51_native_{args.variant.lower()}_surface")
        imported = gmsh.model.occ.importShapes(str(args.input_brep), highestDimOnly=True)
        gmsh.model.occ.synchronize()
        volumes = gmsh.model.getEntities(3)
        if len(imported) != 1 or len(volumes) != 1:
            raise RuntimeError(f"native_BREP_import_not_one_volume:{len(imported)}:{len(volumes)}")
        gmsh.model.mesh.generate(2)

        node_tags, coordinates, _ = gmsh.model.mesh.getNodes()
        points = np.asarray(coordinates, dtype=np.float64).reshape(-1, 3)
        node_tags = np.asarray(node_tags, dtype=np.int64)
        tag_order = np.argsort(node_tags)
        sorted_tags = node_tags[tag_order]
        element_types, _, connectivity_groups = gmsh.model.mesh.getElements(2)
        triangle_groups: list[np.ndarray] = []
        unsupported: list[int] = []
        for element_type, connectivity in zip(element_types, connectivity_groups):
            _, dimension, _, node_count, _, _ = gmsh.model.mesh.getElementProperties(
                int(element_type)
            )
            if dimension != 2 or node_count != 3:
                unsupported.append(int(element_type))
                continue
            node_connectivity = np.asarray(connectivity, dtype=np.int64)
            positions = np.searchsorted(sorted_tags, node_connectivity)
            if np.any(positions >= len(sorted_tags)) or not np.array_equal(
                sorted_tags[positions], node_connectivity
            ):
                raise RuntimeError("surface_connectivity_references_unknown_node")
            triangle_groups.append(tag_order[positions].reshape(-1, 3))
        if unsupported or not triangle_groups:
            raise RuntimeError(f"surface_not_linear_triangles:{unsupported}")
        triangles = np.vstack(triangle_groups).astype(np.int64, copy=False)
    finally:
        gmsh.finalize()

    triangles, reoriented_triangles, winding_conflicts_before = orient_triangles_consistently(
        triangles, points
    )
    triangle_points = points[triangles]
    cross = np.cross(
        triangle_points[:, 1] - triangle_points[:, 0],
        triangle_points[:, 2] - triangle_points[:, 0],
    )
    double_areas = np.linalg.norm(cross, axis=1)
    degenerate = int(np.count_nonzero(~np.isfinite(double_areas) | (double_areas <= 1.0e-15)))
    normals = np.zeros_like(cross, dtype=np.float32)
    valid = double_areas > 1.0e-15
    normals[valid] = (cross[valid] / double_areas[valid, None]).astype(np.float32)

    directed_edges = np.vstack(
        (triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [2, 0]])
    )
    edge_sign = np.where(directed_edges[:, 0] < directed_edges[:, 1], 1, -1)
    canonical_edges = np.sort(directed_edges, axis=1)
    unique_edges, inverse, edge_counts = np.unique(
        canonical_edges, axis=0, return_inverse=True, return_counts=True
    )
    orientation_sum = np.bincount(inverse, weights=edge_sign, minlength=len(unique_edges))
    boundary_edges = int(np.count_nonzero(edge_counts == 1))
    nonmanifold_edges = int(np.count_nonzero(edge_counts > 2))
    winding_conflicts = int(np.count_nonzero((edge_counts == 2) & (orientation_sum != 0)))
    components = component_count(triangles, inverse, edge_counts)

    signed_volume = float(
        np.einsum(
            "ij,ij->i",
            triangle_points[:, 0],
            np.cross(triangle_points[:, 1], triangle_points[:, 2]),
        ).sum()
        / 6.0
    )
    surface_bbox = np.concatenate((points.min(axis=0), points.max(axis=0)))
    maximum_bbox_delta = float(np.max(np.abs(surface_bbox - brep_bbox)))
    volume_relative_delta = abs(abs(signed_volume) - abs(brep_volume)) / abs(brep_volume)
    normal_lengths = np.linalg.norm(normals.astype(np.float64), axis=1)
    accepted = (
        degenerate == 0
        and boundary_edges == 0
        and nonmanifold_edges == 0
        and winding_conflicts == 0
        and components == 1
        and signed_volume > 0.0
        and maximum_bbox_delta <= 2.0e-6
        and volume_relative_delta <= 5.0e-4
        and float(np.max(np.abs(normal_lengths - 1.0))) <= 1.0e-6
    )

    report = {
        "schema": "porsche-917-f51-private-native-brep-tessellation/v1",
        "variant": args.variant,
        "source": {
            "native_BREP_sha256": source_sha,
            "F50_master_accepted": True,
            "native_BREP_exact_BRepCheck_valid": True,
            "F43_outer_skin_STEP_sha256": f50["authority"]["outer_skin"][
                "private_STEP_sha256"
            ],
            "F50_bbox_delta_from_F43_scan_units": master["roundtrip"][
                "bbox_maximum_coordinate_delta_scan_units"
            ],
        },
        "operations": {
            "direct_native_BREP_import": True,
            "OCC_heal_or_sew_used": False,
            "CAD_boolean_used": False,
            "geometry_transform_used": False,
            "scale_transform": [1.0, 1.0, 1.0],
            "proxy_used": False,
            "ellipse_or_oval_used": False,
            "triangle_winding_reorientation_used": reoriented_triangles > 0,
            "triangle_winding_reorientation_changes_coordinates": False,
        },
        "profile": {
            "surface_algorithm": 5,
            "minimum_scan_units": args.minimum,
            "maximum_scan_units": args.maximum,
            "curvature_points_per_2pi": args.curvature_points,
        },
        "tessellation": {
            "point_count": int(len(points)),
            "triangle_count": int(len(triangles)),
            "unique_edge_count": int(len(unique_edges)),
            "boundary_edge_count": boundary_edges,
            "nonmanifold_edge_count": nonmanifold_edges,
            "winding_conflict_edge_count": winding_conflicts,
            "winding_conflict_edge_count_before_reorientation": winding_conflicts_before,
            "triangle_winding_reoriented_count": reoriented_triangles,
            "connected_component_count": components,
            "degenerate_triangle_count": degenerate,
            "signed_volume_scan_units_cubed": signed_volume,
            "BRep_volume_scan_units_cubed": brep_volume,
            "absolute_volume_relative_delta_from_BRep": volume_relative_delta,
            "BRep_bbox_scan_units_private": brep_bbox.tolist(),
            "surface_bbox_scan_units_private": surface_bbox.tolist(),
            "maximum_bbox_delta_from_BRep_scan_units": maximum_bbox_delta,
            "normal_length_maximum_error": float(np.max(np.abs(normal_lengths - 1.0))),
            "triangle_area_scan_units_squared": {
                "minimum": float(np.min(double_areas) / 2.0),
                "p01": quantile(double_areas / 2.0, 0.01),
                "p50": quantile(double_areas / 2.0, 0.5),
            },
        },
        "accepted_for_private_USD_authoring": accepted,
        "release": {
            "simready_validated": False,
            "manufacturing_authorized": False,
            "engine_start_authorized": False,
        },
    }
    if accepted:
        archive_metadata = {
            "schema": "porsche-917-f51-private-surface-archive/v1",
            "variant": args.variant,
            "native_BREP_sha256": source_sha,
            "meters_per_unit": 0.001,
            "up_axis": "Z",
            "scale_transform": [1.0, 1.0, 1.0],
        }
        np.savez_compressed(
            args.output_archive,
            points=points,
            triangles=triangles.astype(np.int32),
            normals=normals,
            metadata_json=np.asarray(json.dumps(archive_metadata, sort_keys=True)),
        )
        report["private_archive"] = {
            "filename": args.output_archive.name,
            "sha256": sha256(args.output_archive),
            "bytes": args.output_archive.stat().st_size,
        }
    args.output_report.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "variant": args.variant,
                "accepted_for_private_USD_authoring": accepted,
                "point_count": len(points),
                "triangle_count": len(triangles),
                "boundary_edge_count": boundary_edges,
                "nonmanifold_edge_count": nonmanifold_edges,
                "winding_conflict_edge_count": winding_conflicts,
                "connected_component_count": components,
                "maximum_bbox_delta_from_BRep_scan_units": maximum_bbox_delta,
                "absolute_volume_relative_delta_from_BRep": volume_relative_delta,
            },
            sort_keys=True,
        )
    )
    return 0 if accepted else 2


if __name__ == "__main__":
    raise SystemExit(main())
