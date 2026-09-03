#!/usr/bin/env python3
"""Audit geometrique pleine pile LPBF F42.2, sans publier la geometrie privee.

Le programme coupe effectivement le maillage a chaque plan median de couche.
Il ne remplace ni un trancheur fournisseur, ni AdditiveFOAM, ni une simulation
de deformation/recoater. Les contours et l'enveloppe de supports restent dans
le repertoire prive d'execution; seuls des agregats sans coordonnees sortent.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np


LAYER_THICKNESS_MM = 0.05
EXPECTED_LAYER_COUNT = 4122
OVERHANG_LIMIT_DEG = 45.0
MIN_FEATURE_AREA_MM2 = 0.01
SUPPORT_RASTER_PITCH_MM = 0.25
BLT_S310_BUILD_MM = (250.0, 250.0, 400.0)
LOCKED_ORIENTATION = "scan_y_down"
SUPPORTED_ORIENTATIONS = ("scan_y_down", "scan_y_up")


class F422Error(RuntimeError):
    """Erreur controlee de la chaine F42.2."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def required_layer_count(height_mm: float, layer_thickness_mm: float) -> int:
    if not math.isfinite(height_mm) or height_mm <= 0.0:
        raise F422Error("invalid_build_height")
    if not math.isfinite(layer_thickness_mm) or layer_thickness_mm <= 0.0:
        raise F422Error("invalid_layer_thickness")
    return int(math.ceil(height_mm / layer_thickness_mm - 1.0e-12))


def locked_transform(vertices: np.ndarray) -> np.ndarray:
    """Transforme le repere scan vers x, -z, +y puis pose z=0."""

    transformed = np.column_stack((vertices[:, 0], -vertices[:, 2], vertices[:, 1]))
    transformed[:, 2] -= float(np.min(transformed[:, 2]))
    return transformed


def orientation_transform(vertices: np.ndarray, orientation: str) -> np.ndarray:
    if orientation == "scan_y_down":
        return locked_transform(vertices)
    if orientation == "scan_y_up":
        transformed = np.column_stack((vertices[:, 0], vertices[:, 2], -vertices[:, 1]))
        transformed[:, 2] -= float(np.min(transformed[:, 2]))
        return transformed
    raise F422Error(f"unsupported_orientation:{orientation}")


def geometry_components(geometry: Any) -> list[Any]:
    if geometry is None or geometry.is_empty:
        return []
    if geometry.geom_type == "Polygon":
        return [geometry]
    if geometry.geom_type == "MultiPolygon":
        return list(geometry.geoms)
    return [part for part in geometry.geoms if part.geom_type == "Polygon"]


def sanitize_polygonal(geometry: Any) -> Any:
    from shapely import make_valid
    from shapely.geometry import GeometryCollection
    from shapely.ops import unary_union

    if geometry is None or geometry.is_empty:
        return GeometryCollection()
    valid = make_valid(geometry) if not geometry.is_valid else geometry
    polygons = geometry_components(valid)
    if not polygons:
        return GeometryCollection()
    result = unary_union(polygons)
    if not result.is_valid:
        result = make_valid(result)
    if not result.is_valid:
        raise F422Error("invalid_polygon_after_repair")
    return result


def path_to_polygon(path: Any) -> Any:
    from shapely.geometry import GeometryCollection
    from shapely.ops import unary_union

    if path is None:
        return GeometryCollection()
    try:
        polygons = list(path.polygons_full)
    except Exception as exc:  # pragma: no cover - depends on trimesh backend
        raise F422Error(f"section_polygonization_failed:{type(exc).__name__}") from exc
    return sanitize_polygonal(unary_union(polygons)) if polygons else GeometryCollection()


def unsupported_regions(
    previous: Any,
    current: Any,
    horizontal_allowance_mm: float,
    minimum_area_mm2: float = MIN_FEATURE_AREA_MM2,
) -> tuple[Any, int, int]:
    """Retourne l'aire non soutenue et deux comptes geometriques.

    ``new_islands`` compte les composantes courantes sans intersection surfacique
    significative avec la couche precedente dilatee. ``unsupported_components``
    compte toutes les zones d'overhang filtrees, meme sur une composante reliee.
    """

    from shapely.ops import unary_union

    if current is None or current.is_empty:
        return sanitize_polygonal(None), 0, 0
    supported = previous.buffer(horizontal_allowance_mm) if previous is not None else None
    raw = current if supported is None or supported.is_empty else current.difference(supported)
    kept = [part for part in geometry_components(sanitize_polygonal(raw)) if part.area >= minimum_area_mm2]
    unsupported = sanitize_polygonal(unary_union(kept)) if kept else sanitize_polygonal(None)
    new_islands = 0
    for component in geometry_components(current):
        overlap = 0.0 if supported is None else component.intersection(supported).area
        if overlap < minimum_area_mm2:
            new_islands += 1
    return unsupported, new_islands, len(kept)


def cardinal_orientation_audit(mesh: Any, overhang_limit_deg: float) -> list[dict[str, Any]]:
    vectors = {
        "+X": np.asarray([1.0, 0.0, 0.0]),
        "-X": np.asarray([-1.0, 0.0, 0.0]),
        "+Y_locked": np.asarray([0.0, 1.0, 0.0]),
        "-Y": np.asarray([0.0, -1.0, 0.0]),
        "+Z": np.asarray([0.0, 0.0, 1.0]),
        "-Z": np.asarray([0.0, 0.0, -1.0]),
    }
    original_extents = np.asarray(mesh.extents, dtype=float)
    normals = np.asarray(mesh.face_normals, dtype=float)
    areas = np.asarray(mesh.area_faces, dtype=float)
    cosine = math.cos(math.radians(overhang_limit_deg))
    results: list[dict[str, Any]] = []
    for name, build_vector in vectors.items():
        axis = int(np.argmax(np.abs(build_vector)))
        planar = [index for index in range(3) if index != axis]
        dots = normals @ build_vector
        overhang = dots < -cosine
        plate = [float(original_extents[index]) for index in planar]
        height = float(original_extents[axis])
        results.append(
            {
                "orientation": name,
                "plate_extents_mm": plate,
                "height_mm": height,
                "blt_s310_nominal_envelope_fit": bool(
                    max(plate) <= BLT_S310_BUILD_MM[0]
                    and min(plate) <= BLT_S310_BUILD_MM[1]
                    and height <= BLT_S310_BUILD_MM[2]
                ),
                "downward_overhang_surface_mm2": float(np.sum(areas[overhang])),
                "downward_projected_area_mm2": float(np.sum(areas[overhang] * -dots[overhang])),
            }
        )
    return results


def write_layer_csv(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    fieldnames = [
        "layer_index",
        "z_mm",
        "part_area_mm2",
        "part_perimeter_mm",
        "part_component_count",
        "new_island_count",
        "unsupported_area_mm2",
        "unsupported_component_count",
        "support_cross_section_area_mm2",
        "support_cross_section_perimeter_mm",
    ]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def validate_public_rows(rows: list[dict[str, Any]], thickness_mm: float) -> None:
    if len(rows) != EXPECTED_LAYER_COUNT:
        raise F422Error(f"unexpected_layer_count:{len(rows)}")
    for expected, row in enumerate(rows):
        if int(row["layer_index"]) != expected:
            raise F422Error("non_contiguous_layer_indices")
        values = [float(row[key]) for key in row if key not in {"layer_index"}]
        if not all(math.isfinite(value) and value >= 0.0 for value in values):
            raise F422Error(f"invalid_public_metric_at_layer:{expected}")
        expected_z = (expected + 0.5) * thickness_mm
        if abs(float(row["z_mm"]) - expected_z) > 1.0e-8:
            raise F422Error(f"unexpected_layer_z:{expected}")


def rasterize_polygonal(geometry: Any, bounds_xy: np.ndarray, pitch_mm: float) -> np.ndarray:
    """Rasterise une geometrie polygonale dans une grille privee bornee."""

    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:  # pragma: no cover - remote runtime dependency
        raise F422Error("pillow_required_for_private_support_raster") from exc
    if pitch_mm <= 0.0 or not math.isfinite(pitch_mm):
        raise F422Error("invalid_support_raster_pitch")
    minimum, maximum = bounds_xy
    width = int(math.ceil((maximum[0] - minimum[0]) / pitch_mm)) + 1
    height = int(math.ceil((maximum[1] - minimum[1]) / pitch_mm)) + 1
    image = Image.new("1", (width, height), 0)
    if geometry is None or geometry.is_empty:
        return np.zeros((height, width), dtype=bool)
    draw = ImageDraw.Draw(image)

    def pixels(coordinates: Any) -> list[tuple[float, float]]:
        return [
            ((float(x) - minimum[0]) / pitch_mm, (float(y) - minimum[1]) / pitch_mm)
            for x, y in coordinates
        ]

    for polygon in geometry_components(geometry):
        draw.polygon(pixels(polygon.exterior.coords), fill=1)
        for interior in polygon.interiors:
            draw.polygon(pixels(interior.coords), fill=0)
    return np.asarray(image, dtype=bool)


def binary_perimeter_mm(mask: np.ndarray, pitch_mm: float) -> float:
    vertical = int(np.count_nonzero(mask[1:, :] != mask[:-1, :]))
    horizontal = int(np.count_nonzero(mask[:, 1:] != mask[:, :-1]))
    boundary = int(np.count_nonzero(mask[0, :]) + np.count_nonzero(mask[-1, :]))
    boundary += int(np.count_nonzero(mask[:, 0]) + np.count_nonzero(mask[:, -1]))
    return float((vertical + horizontal + boundary) * pitch_mm)


def run(args: argparse.Namespace) -> dict[str, Any]:
    try:
        import trimesh
        from shapely.geometry import GeometryCollection
        from shapely.ops import unary_union
    except ImportError as exc:
        raise F422Error("trimesh_shapely_rtree_required") from exc

    private_input = args.head.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    loaded = trimesh.load_mesh(private_input, process=True)
    if not isinstance(loaded, trimesh.Trimesh):
        raise F422Error("input_is_not_one_triangle_mesh")
    components = loaded.split(only_watertight=False)
    if not loaded.is_watertight or len(components) != 1:
        raise F422Error(
            f"input_not_single_watertight_component:watertight={loaded.is_watertight}:components={len(components)}"
        )
    source_hash = sha256(private_input)
    orientations = cardinal_orientation_audit(loaded, args.overhang_limit_deg)

    mesh = loaded.copy()
    mesh.vertices = orientation_transform(np.asarray(mesh.vertices, dtype=float), args.orientation)
    bounds = np.asarray(mesh.bounds, dtype=float)
    extents = np.asarray(mesh.extents, dtype=float)
    height = float(bounds[1, 2] - bounds[0, 2])
    layer_count = required_layer_count(height, args.layer_thickness_mm)
    if layer_count != args.expected_layer_count:
        raise F422Error(f"locked_geometry_requires_{layer_count}_layers_not_{args.expected_layer_count}")
    heights = (np.arange(layer_count, dtype=float) + 0.5) * args.layer_thickness_mm
    if heights[-1] >= height:
        raise F422Error("last_midplane_not_inside_build_height")
    paths = mesh.section_multiplane(
        plane_origin=np.asarray([0.0, 0.0, 0.0]),
        plane_normal=np.asarray([0.0, 0.0, 1.0]),
        heights=heights,
    )
    if len(paths) != layer_count:
        raise F422Error("section_backend_returned_wrong_count")
    slices = [path_to_polygon(path) for path in paths]
    empty_layers = [index for index, item in enumerate(slices) if item.is_empty]
    if empty_layers:
        raise F422Error(f"empty_internal_layers:{len(empty_layers)}")

    horizontal_allowance = args.layer_thickness_mm / math.tan(
        math.radians(args.overhang_limit_deg)
    )
    unsupported: list[Any] = [GeometryCollection()]
    rows: list[dict[str, Any]] = []
    for index, current in enumerate(slices):
        if index == 0:
            region, islands, unsupported_count = GeometryCollection(), 0, 0
        else:
            region, islands, unsupported_count = unsupported_regions(
                slices[index - 1], current, horizontal_allowance, args.minimum_area_mm2
            )
        unsupported.append(region) if index > 0 else None
        rows.append(
            {
                "layer_index": index,
                "z_mm": round(float(heights[index]), 8),
                "part_area_mm2": round(float(current.area), 8),
                "part_perimeter_mm": round(float(current.length), 8),
                "part_component_count": len(geometry_components(current)),
                "new_island_count": islands,
                "unsupported_area_mm2": round(float(region.area), 8),
                "unsupported_component_count": unsupported_count,
                "support_cross_section_area_mm2": 0.0,
                "support_cross_section_perimeter_mm": 0.0,
            }
        )
    if len(unsupported) != layer_count:
        raise F422Error("unsupported_stack_length_error")

    # Enveloppe volontairement conservative: chaque zone non soutenue est
    # projetee verticalement vers le plateau. Une grille privee explicite et
    # reproductible borne le cout, sans pretendre aux supports du slicer BLT.
    bounds_xy = np.asarray(mesh.bounds[:, :2], dtype=float)
    probe = rasterize_polygonal(GeometryCollection(), bounds_xy, args.support_raster_pitch_mm)
    packed_width = int(math.ceil(probe.shape[1] / 8.0))
    packed_supports = np.zeros((layer_count, probe.shape[0], packed_width), dtype=np.uint8)
    columns = np.zeros_like(probe)
    support_volume = 0.0
    support_side_area = 0.0
    support_nonempty_layers = 0
    for index in range(layer_count - 1, -1, -1):
        if index + 1 < layer_count and not unsupported[index + 1].is_empty:
            columns |= rasterize_polygonal(
                unsupported[index + 1], bounds_xy, args.support_raster_pitch_mm
            )
        part_mask = rasterize_polygonal(slices[index], bounds_xy, args.support_raster_pitch_mm)
        support = columns & ~part_mask
        columns = support
        area = float(np.count_nonzero(support) * args.support_raster_pitch_mm**2)
        perimeter = binary_perimeter_mm(support, args.support_raster_pitch_mm)
        rows[index]["support_cross_section_area_mm2"] = round(area, 8)
        rows[index]["support_cross_section_perimeter_mm"] = round(perimeter, 8)
        support_volume += area * args.layer_thickness_mm
        support_side_area += perimeter * args.layer_thickness_mm
        support_nonempty_layers += int(area >= args.minimum_area_mm2)
        packed_supports[index] = np.packbits(support, axis=1)
    private_support = output / "private-support-slice-stack.npz"
    np.savez_compressed(
        private_support,
        packed_supports=packed_supports,
        original_grid_width=np.asarray([probe.shape[1]], dtype=np.int64),
        grid_height=np.asarray([probe.shape[0]], dtype=np.int64),
        pitch_mm=np.asarray([args.support_raster_pitch_mm], dtype=float),
        bounds_xy_mm=bounds_xy,
        layer_thickness_mm=np.asarray([args.layer_thickness_mm], dtype=float),
    )
    validate_public_rows(rows, args.layer_thickness_mm)
    csv_path = output / "917-head-f42-2-layer-metrics.csv"
    write_layer_csv(csv_path, rows)

    cardinal_orientation = "+Y_locked" if args.orientation == "scan_y_down" else "-Y"
    evaluated_orientation = next(
        item for item in orientations if item["orientation"] == cardinal_orientation
    )
    candidate = min(orientations, key=lambda item: item["downward_projected_area_mm2"])
    unsupported_area_integral = sum(float(row["unsupported_area_mm2"]) for row in rows)
    report: dict[str, Any] = {
        "schema_version": "1.0.0",
        "phase": "F42.2",
        "title": "Full-build 50 um geometric slicing and conservative support audit",
        "private_input": {
            "role": "private welded scan-conforming head surface",
            "sha256": source_hash,
            "byte_size": private_input.stat().st_size,
            "published": False,
        },
        "machine_envelope": {
            "machine": "BLT-S310",
            "nominal_build_envelope_mm": list(BLT_S310_BUILD_MM),
            "locked_orientation": LOCKED_ORIENTATION,
            "evaluated_orientation": args.orientation,
            "part_extents_in_locked_build_frame_mm": [float(value) for value in extents],
            "nominal_envelope_fit": bool(evaluated_orientation["blt_s310_nominal_envelope_fit"]),
            "source_of_machine_dimensions": "documented machine specification; no supplier project review",
        },
        "geometric_slicing": {
            "executed": True,
            "method": "exact triangle-plane intersections at every layer midplane; Shapely polygonization",
            "layer_thickness_mm": args.layer_thickness_mm,
            "build_height_mm": height,
            "required_layer_count": layer_count,
            "first_midplane_z_mm": float(heights[0]),
            "last_midplane_z_mm": float(heights[-1]),
            "empty_internal_layers": 0,
            "all_layer_indices_contiguous": True,
        },
        "overhang_and_islands": {
            "overhang_limit_deg_from_horizontal": args.overhang_limit_deg,
            "horizontal_carry_per_layer_mm": horizontal_allowance,
            "minimum_reported_feature_area_mm2": args.minimum_area_mm2,
            "layers_with_new_islands": sum(int(row["new_island_count"] > 0) for row in rows),
            "new_island_count_total": sum(int(row["new_island_count"]) for row in rows),
            "layers_with_unsupported_regions": sum(
                int(row["unsupported_component_count"] > 0) for row in rows
            ),
            "unsupported_area_layer_integral_mm2_layers": unsupported_area_integral,
            "maximum_unsupported_area_on_one_layer_mm2": max(
                float(row["unsupported_area_mm2"]) for row in rows
            ),
        },
        "support_proxy": {
            "method": "vertical solid-column envelope propagated downward on a private binary grid from exact-slice unsupported regions",
            "status": "conservative geometric proxy; not optimized or supplier-ready supports",
            "private_raster_pitch_mm": args.support_raster_pitch_mm,
            "raster_shape_yx": [int(probe.shape[0]), int(probe.shape[1])],
            "private_layer_resolved_geometry_generated": True,
            "private_geometry_sha256": sha256(private_support),
            "private_geometry_byte_size": private_support.stat().st_size,
            "published": False,
            "nonempty_support_layers": support_nonempty_layers,
            "volume_mm3": support_volume,
            "volume_cm3": support_volume / 1000.0,
            "approximate_vertical_side_surface_mm2": support_side_area,
            "surface_limit": "horizontal interfaces and support strut topology are not represented",
        },
        "orientation_screen": {
            "method": "six cardinal orientations; triangle normal 45 deg downward-face proxy",
            "locked_orientation": "+Y_locked",
            "evaluated_orientation": cardinal_orientation,
            "lowest_projected_overhang_cardinal_candidate": candidate["orientation"],
            "candidate_requires_independent_full_slice": candidate["orientation"] != "+Y_locked",
            "results": orientations,
        },
        "recoater": {
            "nominal_z_schedule_inside_envelope": True,
            "collision_clearance_verified": False,
            "risk_unresolved": True,
            "missing_inputs": [
                "distortion field from a calibrated thermo-mechanical LPBF simulation",
                "recoater blade clearance, compliance and sweep direction",
                "optimized supplier support geometry",
                "supplier slicer project and machine file review",
            ],
        },
        "thermal_process": {
            "additivefoam_executed_in_this_phase": False,
            "thermal_or_melt_pool_field_produced": False,
            "statement": "F42.2 is a geometric slicer audit only; AdditiveFOAM is a separate thermal-process workflow.",
        },
        "publication": {
            "contains_private_geometry": False,
            "contains_coordinates_or_contours": False,
            "public_layer_metrics_csv": csv_path.name,
            "public_layer_metrics_sha256": sha256(csv_path),
        },
        "gates": {
            "actual_full_layer_slicing_completed": True,
            "exact_4122_layers_at_50_um": layer_count == EXPECTED_LAYER_COUNT,
            "all_layers_finite_and_contiguous": True,
            "support_proxy_computed": True,
            "private_support_stack_generated": True,
            "blt_s310_nominal_envelope_fit": bool(
                evaluated_orientation["blt_s310_nominal_envelope_fit"]
            ),
            "supplier_slicer_project_reviewed": False,
            "recoater_collision_clearance_verified": False,
            "machine_file_generated_and_signed": False,
            "process_thermal_model_correlated": False,
            "manufacturing_release": False,
        },
        "verdict": {
            "geometric_full_build_audit_completed": True,
            "part_authorized_for_print": False,
            "reason": "supplier slicer, calibrated thermal-distortion model, recoater clearance and signed machine file are missing",
        },
    }
    report_path = output / "917-head-f42-2-full-build-report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--head", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--layer-thickness-mm", type=float, default=LAYER_THICKNESS_MM)
    parser.add_argument("--expected-layer-count", type=int, default=EXPECTED_LAYER_COUNT)
    parser.add_argument("--overhang-limit-deg", type=float, default=OVERHANG_LIMIT_DEG)
    parser.add_argument("--minimum-area-mm2", type=float, default=MIN_FEATURE_AREA_MM2)
    parser.add_argument("--support-raster-pitch-mm", type=float, default=SUPPORT_RASTER_PITCH_MM)
    parser.add_argument("--orientation", choices=SUPPORTED_ORIENTATIONS, default=LOCKED_ORIENTATION)
    return parser.parse_args()


if __name__ == "__main__":
    try:
        result = run(parse_args())
    except F422Error as exc:
        raise SystemExit(f"F42.2 FAIL-CLOSED: {exc}") from exc
    print(json.dumps({"phase": result["phase"], "gates": result["gates"]}, sort_keys=True))
