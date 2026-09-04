#!/usr/bin/env python3
"""Audit LPBF F50 sur les maitres prives 2V/4V, sans publier la geometrie.

Le calcul applique uniquement des rotations/translations rigides. Il tranche
chaque couche a 50 um, construit une enveloppe conservative de supports et
effectue deux criblages independants: epaisseur locale par rayons et volume
ferme par voxelisation/flood-fill. Les sorties publiques ne contiennent ni
triangle, ni contour, ni coordonnee de la peau issue du scan.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


MACHINE = {
    "manufacturer": "Velo3D",
    "model": "Sapphire standard",
    "build_cylinder_diameter_mm": 315.0,
    "build_height_mm": 400.0,
    "laser_configuration": "2 x 1 kW",
    "recoater": "non-contact recoater",
    "source": "https://velo3d.com/solution/sapphire/",
}
LAYER_MM = 0.05
OVERHANG_DEG = 45.0
SUPPORT_RASTER_MM = 0.50


class AuditError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def private_expected_bounds(path: Path, variant: str, master_sha256: str) -> np.ndarray:
    """Charge un verrou de bbox privé sans publier les coordonnées du scan."""
    if not path.is_file():
        raise AuditError(f"missing_private_input:{path.name}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        bounds = np.asarray(payload["bounds"], dtype=float)
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise AuditError("invalid_private_bounds_lock") from exc
    if payload.get("variant") != variant or payload.get("master_sha256") != master_sha256:
        raise AuditError("private_bounds_lock_identity_mismatch")
    if bounds.shape != (2, 3) or not np.isfinite(bounds).all() or np.any(bounds[1] <= bounds[0]):
        raise AuditError("invalid_private_bounds_lock")
    return bounds


def geometry_components(geometry: Any) -> list[Any]:
    if geometry is None or geometry.is_empty:
        return []
    if geometry.geom_type == "Polygon":
        return [geometry]
    if geometry.geom_type == "MultiPolygon":
        return list(geometry.geoms)
    return [item for item in geometry.geoms if item.geom_type == "Polygon"]


def sanitize_polygonal(geometry: Any) -> Any:
    from shapely import make_valid
    from shapely.geometry import GeometryCollection
    from shapely.ops import unary_union

    if geometry is None or geometry.is_empty:
        return GeometryCollection()
    candidate = make_valid(geometry) if not geometry.is_valid else geometry
    polygons = geometry_components(candidate)
    if not polygons:
        return GeometryCollection()
    result = unary_union(polygons)
    if not result.is_valid:
        result = make_valid(result)
    if not result.is_valid:
        raise AuditError("invalid_slice_polygon")
    return result


def path_to_polygon(path: Any) -> Any:
    from shapely.geometry import GeometryCollection
    from shapely.ops import unary_union

    if path is None:
        return GeometryCollection()
    try:
        polygons = list(path.polygons_full)
    except Exception as exc:
        raise AuditError(f"slice_polygonization_failed:{type(exc).__name__}") from exc
    return sanitize_polygonal(unary_union(polygons)) if polygons else GeometryCollection()


def transform_matrix(name: str) -> np.ndarray:
    matrix = np.eye(4)
    if name.startswith("roll_y_"):
        angle = math.radians(float(name.rsplit("_", 1)[1]))
        matrix[:3, :3] = np.asarray(
            [
                [math.cos(angle), 0.0, math.sin(angle)],
                [0.0, 1.0, 0.0],
                [-math.sin(angle), 0.0, math.cos(angle)],
            ]
        )
    elif name == "build_x":
        matrix[:3, :3] = np.asarray([[0, 0, 1], [0, 1, 0], [-1, 0, 0]])
    elif name == "build_y":
        matrix[:3, :3] = np.asarray([[1, 0, 0], [0, 0, 1], [0, -1, 0]])
    elif name == "build_z":
        pass
    else:
        raise AuditError(f"unsupported_orientation:{name}")
    return matrix


def orient(mesh: Any, name: str) -> Any:
    candidate = mesh.copy()
    candidate.apply_transform(transform_matrix(name))
    candidate.apply_translation([0.0, 0.0, -float(candidate.bounds[0, 2])])
    return candidate


def machine_fit(extents: np.ndarray) -> dict[str, Any]:
    conservative_diameter = float(math.hypot(float(extents[0]), float(extents[1])))
    return {
        "part_extents_mm": [float(value) for value in extents],
        "conservative_required_diameter_mm": conservative_diameter,
        "diametral_margin_mm": MACHINE["build_cylinder_diameter_mm"] - conservative_diameter,
        "height_margin_mm": MACHINE["build_height_mm"] - float(extents[2]),
        "bare_part_nominal_fit": bool(
            conservative_diameter <= MACHINE["build_cylinder_diameter_mm"]
            and float(extents[2]) <= MACHINE["build_height_mm"]
        ),
    }


def orientation_screen(mesh: Any) -> list[dict[str, Any]]:
    cosine = math.cos(math.radians(OVERHANG_DEG))
    rows = []
    for name in ("build_x", "build_y", "build_z", "roll_y_25", "roll_y_35", "roll_y_45"):
        candidate = orient(mesh, name)
        normals = np.asarray(candidate.face_normals, dtype=float)
        areas = np.asarray(candidate.area_faces, dtype=float)
        downward = normals[:, 2] < -cosine
        projected = float(np.sum(areas[downward] * -normals[downward, 2]))
        rows.append(
            {
                "orientation": name,
                **machine_fit(np.asarray(candidate.extents, dtype=float)),
                "downward_surface_area_mm2": float(np.sum(areas[downward])),
                "downward_projected_area_mm2": projected,
                "downward_surface_fraction": float(np.sum(areas[downward]) / candidate.area),
            }
        )
    return rows


def deterministic_area_points(mesh: Any, count: int) -> tuple[np.ndarray, np.ndarray]:
    areas = np.asarray(mesh.area_faces, dtype=float)
    cumulative = np.cumsum(areas)
    targets = (np.arange(count, dtype=float) + 0.5) * cumulative[-1] / count
    indices = np.searchsorted(cumulative, targets, side="left")
    return np.asarray(mesh.triangles_center[indices], dtype=float), indices


def thickness_screen(mesh: Any, count: int) -> dict[str, Any]:
    from trimesh.proximity import thickness

    probe = mesh.copy()
    normals_repaired = not bool(probe.is_winding_consistent)
    if normals_repaired:
        probe.fix_normals()
    points, _ = deterministic_area_points(probe, count)
    values = np.asarray(thickness(probe, points, method="max_sphere"), dtype=float)
    finite = values[np.isfinite(values) & (values >= 0.0)]
    if len(finite) != count:
        raise AuditError(f"thickness_nonfinite:{len(finite)}/{count}")
    quantiles = np.quantile(finite, [0.0, 0.01, 0.05, 0.50, 0.95])
    return {
        "method": "trimesh max_sphere local thickness on deterministic area-weighted face-centre probes",
        "sample_count": count,
        "analysis_normals_repaired_without_vertex_motion": normals_repaired,
        "minimum_mm": float(quantiles[0]),
        "p01_mm": float(quantiles[1]),
        "p05_mm": float(quantiles[2]),
        "median_mm": float(quantiles[3]),
        "p95_mm": float(quantiles[4]),
        "sample_fraction_below_1p5_mm": float(np.mean(finite < 1.5)),
        "classification": "screening_only_not_a_certified_minimum_wall_map",
    }


def trapped_void_screen(mesh: Any, pitch_mm: float) -> dict[str, Any]:
    from scipy import ndimage

    voxels = mesh.voxelized(pitch_mm).fill()
    occupied = np.asarray(voxels.matrix, dtype=bool)
    padded_void = np.pad(~occupied, 1, mode="constant", constant_values=True)
    labels, count = ndimage.label(padded_void, structure=ndimage.generate_binary_structure(3, 1))
    outside = int(labels[0, 0, 0])
    trapped = (labels != 0) & (labels != outside)
    trapped_count = int(np.count_nonzero(trapped))
    return {
        "method": "surface voxelisation, solid fill and 6-connected exterior flood-fill",
        "pitch_mm": pitch_mm,
        "voxel_grid_shape": [int(value) for value in occupied.shape],
        "connected_void_labels_including_outside": int(count),
        "trapped_void_voxel_count": trapped_count,
        "trapped_void_volume_mm3": trapped_count * pitch_mm**3,
        "no_trapped_volume_detected_at_screen_resolution": trapped_count == 0,
        "classification": "resolution-limited depowdering screen; CT and endoscopy still required",
    }


def rasterize(geometry: Any, bounds_xy: np.ndarray, pitch_mm: float) -> np.ndarray:
    from PIL import Image, ImageDraw

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


def binary_perimeter(mask: np.ndarray, pitch_mm: float) -> float:
    transitions = int(np.count_nonzero(mask[1:, :] != mask[:-1, :]))
    transitions += int(np.count_nonzero(mask[:, 1:] != mask[:, :-1]))
    transitions += int(np.count_nonzero(mask[0, :]) + np.count_nonzero(mask[-1, :]))
    transitions += int(np.count_nonzero(mask[:, 0]) + np.count_nonzero(mask[:, -1]))
    return float(transitions * pitch_mm)


def slice_build(mesh: Any, orientation: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    from shapely.geometry import GeometryCollection

    candidate = orient(mesh, orientation)
    height = float(candidate.extents[2])
    count = int(math.ceil(height / LAYER_MM - 1.0e-12))
    bottoms = np.arange(count, dtype=float) * LAYER_MM
    tops = np.minimum(bottoms + LAYER_MM, height)
    heights = 0.5 * (bottoms + tops)
    paths = candidate.section_multiplane(
        plane_origin=np.zeros(3), plane_normal=np.asarray([0.0, 0.0, 1.0]), heights=heights
    )
    if len(paths) != count:
        raise AuditError("wrong_slice_count")
    slices = [path_to_polygon(path) for path in paths]
    empty = [index for index, item in enumerate(slices) if item.is_empty]
    if empty:
        raise AuditError(f"empty_layers:{len(empty)}")

    allowance = LAYER_MM / math.tan(math.radians(OVERHANG_DEG))
    unsupported: list[Any] = [GeometryCollection()]
    rows: list[dict[str, Any]] = []
    for index, current in enumerate(slices):
        if index == 0:
            region = GeometryCollection()
            islands = 0
        else:
            supported = slices[index - 1].buffer(allowance)
            region = sanitize_polygonal(current.difference(supported))
            region = sanitize_polygonal(
                __import__("shapely.ops", fromlist=["unary_union"]).unary_union(
                    [part for part in geometry_components(region) if part.area >= 0.01]
                )
            )
            islands = sum(
                int(component.intersection(supported).area < 0.01)
                for component in geometry_components(current)
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
                "support_area_mm2": 0.0,
                "support_perimeter_mm": 0.0,
            }
        )

    bounds_xy = np.asarray(candidate.bounds[:, :2], dtype=float)
    probe = rasterize(GeometryCollection(), bounds_xy, SUPPORT_RASTER_MM)
    columns = np.zeros_like(probe)
    support_volume = 0.0
    support_side = 0.0
    for index in range(count - 1, -1, -1):
        if index + 1 < count and not unsupported[index + 1].is_empty:
            columns |= rasterize(unsupported[index + 1], bounds_xy, SUPPORT_RASTER_MM)
        part = rasterize(slices[index], bounds_xy, SUPPORT_RASTER_MM)
        support = columns & ~part
        columns = support
        area = float(np.count_nonzero(support) * SUPPORT_RASTER_MM**2)
        perimeter = binary_perimeter(support, SUPPORT_RASTER_MM)
        rows[index]["support_area_mm2"] = round(area, 8)
        rows[index]["support_perimeter_mm"] = round(perimeter, 8)
        support_volume += area * LAYER_MM
        support_side += perimeter * LAYER_MM

    summary = {
        "orientation": orientation,
        "rigid_transform_only": True,
        "layer_thickness_mm": LAYER_MM,
        "layer_count": count,
        "build_height_mm": height,
        "empty_internal_layers": 0,
        "new_island_count": int(sum(row["new_island_count"] for row in rows)),
        "layers_with_new_islands": int(sum(row["new_island_count"] > 0 for row in rows)),
        "layers_with_unsupported_area": int(sum(row["unsupported_area_mm2"] > 0 for row in rows)),
        "maximum_unsupported_area_mm2": float(max(row["unsupported_area_mm2"] for row in rows)),
        "support_proxy_volume_mm3": support_volume,
        "support_proxy_volume_cm3": support_volume / 1000.0,
        "support_proxy_side_area_mm2": support_side,
        "support_raster_pitch_mm": SUPPORT_RASTER_MM,
        "support_classification": "conservative vertical-column proxy; no supplier support topology",
        **machine_fit(np.asarray(candidate.extents, dtype=float)),
    }
    return rows, summary


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def render(path: Path, variant: str, rows: list[dict[str, Any]], report: dict[str, Any]) -> None:
    layers = np.asarray([row["layer_index"] for row in rows])
    z = np.asarray([row["z_mm"] for row in rows])
    part = np.asarray([row["part_area_mm2"] for row in rows])
    support = np.asarray([row["support_area_mm2"] for row in rows])
    unsupported = np.asarray([row["unsupported_area_mm2"] for row in rows])
    figure, axes = plt.subplots(2, 2, figsize=(14, 9), facecolor="#08131d")
    figure.suptitle(f"F50 {variant.upper()} — AUDIT LPBF PLEINE PIECE — SAPPHIRE", color="white", fontsize=18, weight="bold")
    series = [
        (axes[0, 0], z, part, "Section de piece par couche", "mm2", "#4cc9f0"),
        (axes[0, 1], z, unsupported, "Zone nouvellement non soutenue", "mm2", "#f77f00"),
        (axes[1, 0], z, support, "Enveloppe conservative de supports", "mm2", "#90be6d"),
    ]
    for axis, x, y, title, unit, color in series:
        axis.set_facecolor("#10212d")
        axis.plot(x, y, color=color, linewidth=1.1)
        axis.set_title(title, color="white", weight="bold")
        axis.set_xlabel("Hauteur de construction (mm)", color="#d7e4ec")
        axis.set_ylabel(unit, color="#d7e4ec")
        axis.tick_params(colors="#d7e4ec")
        axis.grid(alpha=0.18)
    axis = axes[1, 1]
    axis.set_facecolor("#10212d")
    axis.axis("off")
    thickness = report["thickness_screen"]
    powder = report["powder_escape_screen"]
    slice_summary = report["full_build_slicing"]
    text = (
        f"Maitre F50: {report['master']['sha256'][:16]}...\n"
        f"Couches reelles: {len(layers):,} x 50 um\n"
        f"Hauteur: {slice_summary['build_height_mm']:.3f} mm\n"
        f"Support proxy: {slice_summary['support_proxy_volume_cm3']:.1f} cm3\n"
        f"Epaisseur p01: {thickness['p01_mm']:.3f} mm\n"
        f"Echantillons < 1.5 mm: {100*thickness['sample_fraction_below_1p5_mm']:.2f}%\n"
        f"Volume ferme detecte: {powder['trapped_void_volume_mm3']:.1f} mm3\n\n"
        "PEAU DU SCAN INCHANGEE\n"
        "AUCUN SCALING DIRECTIONNEL\n"
        "IMPRESSION: NON AUTORISEE"
    )
    axis.text(0.05, 0.95, text, transform=axis.transAxes, va="top", color="white", fontsize=12, linespacing=1.5)
    figure.text(
        0.5,
        0.02,
        "Audit geometrique et support proxy seulement — pas un fichier machine, pas une validation recoater ni une qualification matiere.",
        ha="center",
        color="#ffb4a2",
        fontsize=10,
    )
    figure.tight_layout(rect=(0.02, 0.05, 0.98, 0.94))
    figure.savefig(path, dpi=170, facecolor=figure.get_facecolor())
    plt.close(figure)


def run(args: argparse.Namespace) -> dict[str, Any]:
    import trimesh

    for path in (args.master, args.surface):
        if not path.is_file():
            raise AuditError(f"missing_private_input:{path.name}")
    if sha256(args.master) != args.master_sha256:
        raise AuditError("master_hash_mismatch")
    if sha256(args.surface) != args.surface_sha256:
        raise AuditError("surface_hash_mismatch")
    mesh = trimesh.load_mesh(args.surface, process=True)
    if not isinstance(mesh, trimesh.Trimesh) or not mesh.is_watertight:
        raise AuditError("surface_mesh_not_watertight")
    if len(mesh.split(only_watertight=False)) != 1:
        raise AuditError("surface_mesh_not_single_component")
    expected_bounds = private_expected_bounds(args.expected_bounds_lock, args.variant, args.master_sha256)
    if not np.allclose(mesh.bounds, expected_bounds, rtol=0.0, atol=2.0e-6):
        raise AuditError("scan_skin_bbox_changed")

    args.output.mkdir(parents=True, exist_ok=True)
    orientations = orientation_screen(mesh)
    fitting = [item for item in orientations if item["bare_part_nominal_fit"]]
    if not fitting:
        raise AuditError("no_orientation_fits_bare_machine_envelope")
    selected = min(fitting, key=lambda item: item["downward_projected_area_mm2"])[
        "orientation"
    ]
    rows, slicing = slice_build(mesh, selected)
    thickness = thickness_screen(mesh, args.thickness_samples)
    powder = trapped_void_screen(mesh, args.voxel_pitch_mm)
    csv_path = args.output / f"917-head-f50-{args.variant}-layer-metrics.csv"
    write_rows(csv_path, rows)
    report = {
        "schema_version": "1.0.0",
        "phase": "F50",
        "classification": "scan-derived-private-master-virtual-lpbf-screen",
        "variant": args.variant,
        "master": {"role": "immutable private native OCCT BREP", "sha256": args.master_sha256, "published": False},
        "analysis_surface": {"role": "private tessellation of the same master", "sha256": args.surface_sha256, "published": False},
        "geometry_invariants": {
            "source_bbox_contract_verified": True,
            "source_bbox_coordinates_published": False,
            "absolute_scale_certified": False,
            "units_interpreted_as_mm_for_candidate_screen_only": True,
            "scan_skin_modified": False,
            "envelope_proxy_used": False,
            "anisotropic_scaling_used": False,
            "elliptic_or_oval_exterior_used": False,
            "analysis_transform": "rigid rotation and translation only",
        },
        "machine": MACHINE,
        "orientation_screen": orientations,
        "selected_candidate_orientation": selected,
        "orientation_selection_rule": "minimum downward projected area among bare-part envelope-fitting candidates",
        "full_build_slicing": slicing,
        "thickness_screen": thickness,
        "powder_escape_screen": powder,
        "recoater_screen": {
            "nominal_bare_part_inside_build_envelope": slicing["bare_part_nominal_fit"],
            "collision_simulation_executed": False,
            "blade_clearance_and_compliance_known": False,
            "distortion_field_available": False,
            "pass": False,
        },
        "closed_volume_gate": {
            "screen_pass_at_voxel_resolution": powder["no_trapped_volume_detected_at_screen_resolution"],
            "ct_or_endoscope_confirmed": False,
            "final_pass": False,
        },
        "machining_and_support_gate": {
            "machining_allowances_in_master": False,
            "supplier_support_geometry_available": False,
            "support_contacts_on_functional_surfaces_checked": False,
            "support_removal_access_proved": False,
            "pass": False,
        },
        "publication": {
            "contains_private_geometry": False,
            "contains_triangle_or_slice_coordinates": False,
            "layer_metrics_csv": csv_path.name,
            "layer_metrics_sha256": sha256(csv_path),
        },
        "gates": {
            "immutable_master_hash_verified": True,
            "scan_skin_bbox_verified": True,
            "single_watertight_surface_mesh": True,
            "full_piece_50um_macro_slicing_completed": True,
            "bare_part_machine_envelope_fit": slicing["bare_part_nominal_fit"],
            "minimum_wall_1p5mm_everywhere": False,
            "powder_removal_physically_validated": False,
            "supplier_supports_validated": False,
            "recoater_clearance_validated": False,
            "supplier_machine_file_signed": False,
            "physical_coupon_qualified": False,
            "metal_print_authorized": False,
            "engine_start_authorized": False,
        },
        "verdict": "geometric_screen_completed_but_print_and_start_prohibited",
    }
    report_path = args.output / f"917-head-f50-{args.variant}-lpbf-geometry-report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    image_path = args.output / f"917-head-f50-{args.variant}-lpbf-geometry-audit.png"
    render(image_path, args.variant, rows, report)
    manifest = {
        "report": {"path": report_path.name, "sha256": sha256(report_path)},
        "layer_metrics": {"path": csv_path.name, "sha256": sha256(csv_path)},
        "image": {"path": image_path.name, "sha256": sha256(image_path)},
    }
    manifest_path = args.output / f"917-head-f50-{args.variant}-lpbf-geometry-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=("2v", "4v"), required=True)
    parser.add_argument("--master", type=Path, required=True)
    parser.add_argument("--master-sha256", required=True)
    parser.add_argument("--surface", type=Path, required=True)
    parser.add_argument("--surface-sha256", required=True)
    parser.add_argument("--expected-bounds-lock", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--thickness-samples", type=int, default=2000)
    parser.add_argument("--voxel-pitch-mm", type=float, default=1.5)
    return parser.parse_args()


if __name__ == "__main__":
    try:
        result = run(parse_args())
    except AuditError as exc:
        raise SystemExit(f"F50 LPBF FAIL-CLOSED: {exc}") from exc
    print(json.dumps({"variant": result["variant"], "gates": result["gates"]}, sort_keys=True))
