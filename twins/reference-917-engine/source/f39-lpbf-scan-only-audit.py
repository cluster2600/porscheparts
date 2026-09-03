#!/usr/bin/env python3
"""Audit LPBF/structure F39 sur la seule peau de scan F37.

La carte d'épaisseur couvre chaque triangle du maillage, mais reste une carte de
cordes suivant les normales de facettes. Elle ne remplace ni une reconstruction
CAO, ni un CT. Aucune cote de pièce n'est ajoutée par ce script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import shutil
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import colors
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
from scipy import ndimage
import vtk
from vtk.util.numpy_support import vtk_to_numpy


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_stl(path: Path) -> tuple[vtk.vtkPolyData, np.ndarray, np.ndarray]:
    reader = vtk.vtkSTLReader()
    reader.SetFileName(str(path))
    reader.MergingOn()
    reader.Update()
    poly = reader.GetOutput()
    require(poly.GetNumberOfPoints() > 0 and poly.GetNumberOfCells() > 0, "empty_scan_mesh")
    require(poly.GetPolys().GetNumberOfCells() == poly.GetNumberOfCells(), "scan_mesh_not_triangles")
    connectivity = vtk_to_numpy(poly.GetPolys().GetConnectivityArray())
    require(len(connectivity) == 3 * poly.GetNumberOfCells(), "non_triangle_connectivity")
    points = np.asarray(vtk_to_numpy(poly.GetPoints().GetData()), dtype=np.float64)
    faces = np.asarray(connectivity.reshape(-1, 3), dtype=np.int64)
    return poly, points, faces


def topology(poly: vtk.vtkPolyData) -> dict:
    edges = vtk.vtkFeatureEdges()
    edges.SetInputData(poly)
    edges.BoundaryEdgesOn()
    edges.NonManifoldEdgesOn()
    edges.FeatureEdgesOff()
    edges.ManifoldEdgesOff()
    edges.Update()
    connectivity = vtk.vtkPolyDataConnectivityFilter()
    connectivity.SetInputData(poly)
    connectivity.SetExtractionModeToAllRegions()
    connectivity.ColorRegionsOn()
    connectivity.Update()
    return {
        "vertices": int(poly.GetNumberOfPoints()),
        "triangles": int(poly.GetNumberOfCells()),
        "boundary_or_nonmanifold_edges": int(edges.GetOutput().GetNumberOfCells()),
        "connected_surface_regions": int(connectivity.GetNumberOfExtractedRegions()),
        "watertight_manifold_screen": edges.GetOutput().GetNumberOfCells() == 0,
    }


def triangle_geometry(points: np.ndarray, faces: np.ndarray) -> tuple[np.ndarray, ...]:
    triangles = points[faces]
    cross = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    double_area = np.linalg.norm(cross, axis=1)
    require(bool(np.all(double_area > 0.0)), "degenerate_triangle_in_scan")
    normals = cross / double_area[:, None]
    signed_volume = float(
        np.sum(np.einsum("ij,ij->i", triangles[:, 0], np.cross(triangles[:, 1], triangles[:, 2]))) / 6.0
    )
    # Les normales issues du produit vectoriel sont extérieures pour un volume
    # signé positif. Le signe global rend la direction robuste à un STL inversé.
    outward = normals if signed_volume > 0.0 else -normals
    centroids = triangles.mean(axis=1)
    return triangles, centroids, outward, 0.5 * double_area, signed_volume


def exhaustive_normal_chords(
    poly: vtk.vtkPolyData,
    centroids: np.ndarray,
    outward_normals: np.ndarray,
    diagonal_mm: float,
) -> np.ndarray:
    locator = vtk.vtkStaticCellLocator()
    locator.SetDataSet(poly)
    locator.BuildLocator()
    hits = vtk.vtkPoints()
    hit_ids = vtk.vtkIdList()
    epsilon = max(1.0e-5, diagonal_mm * 1.0e-7)
    thickness = np.full(len(centroids), np.nan, dtype=np.float64)
    for index, (centre, outward) in enumerate(zip(centroids, outward_normals)):
        inward = -outward
        start = centre + epsilon * inward
        end = start + (diagonal_mm + 2.0 * epsilon) * inward
        hits.Reset()
        hit_ids.Reset()
        locator.IntersectWithLine(start, end, 1.0e-8, hits, hit_ids)
        best = math.inf
        for hit_index in range(hits.GetNumberOfPoints()):
            point = np.asarray(hits.GetPoint(hit_index), dtype=np.float64)
            distance = float(np.dot(point - start, inward))
            if distance > 5.0 * epsilon:
                best = min(best, distance + epsilon)
        if math.isfinite(best):
            thickness[index] = best
    return thickness


def thickness_summary(thickness: np.ndarray, areas: np.ndarray, inherited_requirement: float) -> dict:
    valid = np.isfinite(thickness) & (thickness > 0.0)
    values = thickness[valid]
    require(len(values) > 0, "no_resolved_thickness_chords")
    resolved_area = float(np.sum(areas[valid]))
    below_area = float(np.sum(areas[valid & (thickness < inherited_requirement)]))
    return {
        "method": "exhaustive_triangle_centroid_inward_normal_first_opposite_surface_chord_VTK",
        "domain": "all_triangles_of_exact_F37_scan_mesh",
        "triangle_count": int(len(thickness)),
        "evaluated_triangle_count": int(len(thickness)),
        "resolved_triangle_count": int(np.count_nonzero(valid)),
        "unresolved_triangle_count": int(np.count_nonzero(~valid)),
        "resolved_fraction": float(np.count_nonzero(valid) / len(valid)),
        "minimum_mm_if_scale_is_mm": float(np.min(values)),
        "p01_mm_if_scale_is_mm": float(np.quantile(values, 0.01)),
        "p05_mm_if_scale_is_mm": float(np.quantile(values, 0.05)),
        "median_mm_if_scale_is_mm": float(np.median(values)),
        "p95_mm_if_scale_is_mm": float(np.quantile(values, 0.95)),
        "maximum_mm_if_scale_is_mm": float(np.max(values)),
        "inherited_screen_requirement_mm_if_scale_is_mm": inherited_requirement,
        "resolved_area_below_inherited_requirement_fraction": below_area / max(resolved_area, 1.0e-15),
        "all_resolved_chords_meet_inherited_requirement": bool(np.all(values >= inherited_requirement)),
        "continuous_surface_proof": False,
        "ct_verified": False,
        "limitation": "face_normal_chord_on_faceted_scan_not_medial_thickness_or_production_CAD_wall_map",
    }


def trapped_void_screen(poly: vtk.vtkPolyData, bounds: np.ndarray, pitch: float) -> dict:
    origin = [float(bounds[axis, 0] - pitch) for axis in range(3)]
    shape = tuple(int(math.ceil((bounds[axis, 1] - bounds[axis, 0]) / pitch)) + 3 for axis in range(3))
    image = vtk.vtkImageData()
    image.SetSpacing(pitch, pitch, pitch)
    image.SetOrigin(*origin)
    image.SetDimensions(*shape)
    image.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 1)
    vtk_to_numpy(image.GetPointData().GetScalars()).fill(1)
    stencil = vtk.vtkPolyDataToImageStencil()
    stencil.SetInputData(poly)
    stencil.SetOutputOrigin(*origin)
    stencil.SetOutputSpacing(pitch, pitch, pitch)
    stencil.SetOutputWholeExtent(image.GetExtent())
    stencil.Update()
    apply_stencil = vtk.vtkImageStencil()
    apply_stencil.SetInputData(image)
    apply_stencil.SetStencilConnection(stencil.GetOutputPort())
    apply_stencil.ReverseStencilOff()
    apply_stencil.SetBackgroundValue(0)
    apply_stencil.Update()
    # VTK stocke x comme indice variant le plus vite; order='F' restitue
    # explicitement le tableau [x, y, z]. Le stencil est déterministe, à
    # l'inverse du rayon aléatoire interne de vtkSelectEnclosedPoints.
    inside = np.asarray(
        vtk_to_numpy(apply_stencil.GetOutput().GetPointData().GetScalars()), dtype=bool
    ).reshape(shape, order="F")
    void = ~inside
    labels, component_count = ndimage.label(void, structure=ndimage.generate_binary_structure(3, 1))
    boundary = np.unique(
        np.concatenate(
            [
                labels[0, :, :].ravel(),
                labels[-1, :, :].ravel(),
                labels[:, 0, :].ravel(),
                labels[:, -1, :].ravel(),
                labels[:, :, 0].ravel(),
                labels[:, :, -1].ravel(),
            ]
        )
    )
    exterior = np.zeros(component_count + 1, dtype=bool)
    exterior[boundary.astype(np.int64)] = True
    trapped = void & ~exterior[labels]
    counts = np.bincount(labels.ravel(), minlength=component_count + 1)
    trapped_ids = np.flatnonzero((~exterior) & (np.arange(component_count + 1) > 0) & (counts > 0))
    objects = ndimage.find_objects(labels)
    components = []
    for label in trapped_ids:
        voxel_count = int(counts[label])
        slices = objects[int(label) - 1]
        require(slices is not None, "missing_component_slice")
        local = labels[slices] == label
        local_indices = np.argwhere(local)
        starts = np.asarray([item.start for item in slices], dtype=np.float64)
        mean_index = local_indices.mean(axis=0) + starts
        centroid = [float(origin[axis] + pitch * mean_index[axis]) for axis in range(3)]
        volume = voxel_count * pitch**3
        components.append(
            {
                "label": int(label),
                "voxel_count": voxel_count,
                "volume_mm3_if_scale_is_mm": float(volume),
                "equivalent_sphere_diameter_mm_if_scale_is_mm": float((6.0 * volume / math.pi) ** (1.0 / 3.0)),
                "centroid_mm_if_scale_is_mm": centroid,
                "connected_to_exterior": False,
            }
        )
    components.sort(key=lambda item: (-item["voxel_count"], item["label"]))
    trapped_voxels = int(np.count_nonzero(trapped))
    return {
        "pitch_mm_if_scale_is_mm": pitch,
        "grid_shape": list(shape),
        "grid_point_count": int(np.prod(shape, dtype=np.int64)),
        "solid_grid_points": int(np.count_nonzero(inside)),
        "method": "deterministic_VTK_polydata_to_image_stencil_plus_6_connected_exterior_flood_fill",
        "trapped_component_count": int(len(components)),
        "trapped_voxel_count": trapped_voxels,
        "trapped_volume_mm3_if_scale_is_mm": float(trapped_voxels * pitch**3),
        "largest_components": components[:50],
        "all_detected_void_connected_to_exterior": len(components) == 0,
        "physical_powder_removal_verified": False,
        "classification": "voxel_resolution_screen_not_CT_or_powder_flow_test",
    }


def rotation_matrix(axis: str, degrees: float) -> np.ndarray:
    angle = math.radians(degrees)
    cosine, sine = math.cos(angle), math.sin(angle)
    if axis == "x":
        return np.asarray([[1, 0, 0], [0, cosine, -sine], [0, sine, cosine]], dtype=float)
    if axis == "y":
        return np.asarray([[cosine, 0, sine], [0, 1, 0], [-sine, 0, cosine]], dtype=float)
    return np.asarray([[cosine, -sine, 0], [sine, cosine, 0], [0, 0, 1]], dtype=float)


def candidate_rotations() -> dict[str, np.ndarray]:
    candidates = {
        "scan_z_up": np.eye(3),
        "scan_z_down": rotation_matrix("x", 180),
        "scan_x_up": rotation_matrix("y", -90),
        "scan_x_down": rotation_matrix("y", 90),
        "scan_y_up": rotation_matrix("x", -90),
        "scan_y_down": rotation_matrix("x", 90),
    }
    base = candidates["scan_y_down"]
    for axis in ("x", "y"):
        for angle in (-45, -30, -15, 15, 30, 45):
            candidates[f"scan_y_down_tilt_{axis}_{angle:+d}"] = rotation_matrix(axis, angle) @ base
    return candidates


def orientation_screen(
    points: np.ndarray,
    centroids: np.ndarray,
    normals: np.ndarray,
    areas: np.ndarray,
    envelope: np.ndarray,
    critical_angle: float,
) -> tuple[list[dict], dict]:
    results = []
    cosine = math.cos(math.radians(critical_angle))
    total_area = float(np.sum(areas))
    for name, transform in candidate_rotations().items():
        rotated_points = points @ transform.T
        rotated_centres = centroids @ transform.T
        rotated_normals = normals @ transform.T
        lower = rotated_points.min(axis=0)
        extents = rotated_points.max(axis=0) - lower
        height = rotated_centres[:, 2] - lower[2]
        downward = rotated_normals[:, 2] < -cosine
        support_area = float(np.sum(areas[downward]))
        projected_area = float(np.sum(areas[downward] * -rotated_normals[downward, 2]))
        column_proxy = float(np.sum(areas[downward] * -rotated_normals[downward, 2] * height[downward]))
        fits = bool(np.all(extents <= envelope))
        results.append(
            {
                "id": name,
                "transform": transform.tolist(),
                "extents_mm_if_scale_is_mm": extents.tolist(),
                "fits_inherited_250x250x325_envelope_if_scale_is_mm": fits,
                "downward_face_area_mm2_if_scale_is_mm": support_area,
                "downward_face_area_fraction": support_area / total_area,
                "projected_support_area_mm2_if_scale_is_mm": projected_area,
                "column_support_volume_proxy_mm3_if_scale_is_mm": column_proxy,
                "score": column_proxy + 50.0 * projected_area + (0.0 if fits else 1.0e12),
            }
        )
    eligible = [item for item in results if item["fits_inherited_250x250x325_envelope_if_scale_is_mm"]]
    require(bool(eligible), "no_orientation_fits_inherited_envelope")
    selected = min(eligible, key=lambda item: (item["score"], item["id"]))
    return results, selected


def solver_inventory() -> dict:
    commands = [
        "AdditiveFOAM",
        "amphyon",
        "simufact",
        "ansys-additive",
        "abaqus",
        "code_aster",
        "ElmerSolver",
        "ccx",
    ]
    found = {command: shutil.which(command) for command in commands}
    dedicated = ["AdditiveFOAM", "amphyon", "simufact", "ansys-additive"]
    return {
        "commands_checked": found,
        "dedicated_additive_layer_activation_solver_available": any(found[name] for name in dedicated),
        "calibrated_machine_scan_strategy_and_inherent_strain_parameters_available": False,
        "simulation_executed": False,
        "uniform_locked_plate_or_free_shrink_promoted_to_process_simulation": False,
        "reason": "no_dedicated_solver_and_no_calibrated_machine_material_scan_strategy_parameter_set",
    }


def render(
    triangles: np.ndarray,
    thickness: np.ndarray,
    report: dict,
    destination: Path,
) -> None:
    valid = np.isfinite(thickness) & (thickness > 0.0)
    values = thickness[valid]
    base = np.linspace(0, len(triangles) - 1, min(26000, len(triangles)), dtype=np.int64)
    thin = np.argsort(np.where(valid, thickness, np.inf))[: min(6000, int(np.count_nonzero(valid)))]
    keep = np.unique(np.concatenate((base, thin)))
    selected = report["orientation_and_support_screen"]["selected"]
    transform = np.asarray(selected["transform"], dtype=float)
    shown = triangles[keep] @ transform.T
    shown[:, :, 2] -= float(shown[:, :, 2].min())
    shown_thickness = thickness[keep]
    vmin = max(0.02, float(np.quantile(values, 0.005)))
    vmax = max(vmin * 1.01, min(20.0, float(np.quantile(values, 0.90))))
    normalization = colors.LogNorm(vmin=vmin, vmax=vmax, clip=True)
    colormap = plt.get_cmap("turbo_r")
    facecolors = colormap(normalization(np.where(np.isfinite(shown_thickness), shown_thickness, vmax)))

    figure = plt.figure(figsize=(16, 9), facecolor="#091119")
    figure.suptitle("PORSCHE 917 F39 — AUDIT LPBF / STRUCTURE SCAN-ONLY", color="white", fontsize=19, fontweight="bold")
    axis = figure.add_subplot(2, 2, 1, projection="3d", facecolor="#101c25")
    axis.add_collection3d(Poly3DCollection(shown, facecolors=facecolors, edgecolor="none"))
    lower = shown.reshape(-1, 3).min(axis=0)
    upper = shown.reshape(-1, 3).max(axis=0)
    centre = (lower + upper) / 2.0
    radius = 0.55 * float(np.max(upper - lower))
    axis.set_xlim(centre[0] - radius, centre[0] + radius)
    axis.set_ylim(centre[1] - radius, centre[1] + radius)
    axis.set_zlim(max(0.0, centre[2] - radius), centre[2] + radius)
    axis.set_box_aspect((1, 1, 1))
    axis.view_init(elev=24, azim=-52)
    axis.set_axis_off()
    axis.set_title("Cordes normales — chaque triangle calculé", color="white", fontweight="bold")
    scalar = plt.cm.ScalarMappable(norm=normalization, cmap=colormap)
    bar = figure.colorbar(scalar, ax=axis, fraction=0.035, pad=0.02)
    bar.set_label("mm si 1 unité scan = 1 mm", color="white")
    bar.ax.tick_params(colors="white")

    histogram = figure.add_subplot(2, 2, 2, facecolor="#101c25")
    cap = float(np.quantile(values, 0.99))
    histogram.hist(np.clip(values, 0.0, cap), bins=70, color="#57b5d9", alpha=0.9)
    requirement = report["exhaustive_thickness_map"]["inherited_screen_requirement_mm_if_scale_is_mm"]
    histogram.axvline(requirement, color="#ff7058", linestyle="--", linewidth=2, label="seuil-écran F38 hérité")
    histogram.set_title("Distribution exhaustive des cordes résolues", color="white", fontweight="bold")
    histogram.set_xlabel("épaisseur-corde tronquée au p99 (mm conditionnels)", color="#c5d2da")
    histogram.set_ylabel("triangles", color="#c5d2da")
    histogram.tick_params(colors="#c5d2da")
    histogram.legend(facecolor="#101c25", labelcolor="white")
    for spine in histogram.spines.values():
        spine.set_color("#31434f")

    orientations = sorted(report["orientation_and_support_screen"]["candidates"], key=lambda item: item["score"])
    chart = figure.add_subplot(2, 2, 3, facecolor="#101c25")
    shown_orientations = orientations[:8]
    chart.barh(
        [item["id"].replace("scan_y_down_", "") for item in shown_orientations][::-1],
        [100.0 * item["downward_face_area_fraction"] for item in shown_orientations][::-1],
        color="#d3a14b",
    )
    chart.set_xlabel("aire de faces descendantes (%) — proxy, pas supports tranchés", color="#c5d2da")
    chart.set_title("8 meilleures orientations au score proxy", color="white", fontweight="bold")
    chart.tick_params(colors="#c5d2da", labelsize=8)
    for spine in chart.spines.values():
        spine.set_color("#31434f")

    panel = figure.add_subplot(2, 2, 4, facecolor="#101c25")
    panel.axis("off")
    thickness_report = report["exhaustive_thickness_map"]
    finest_void = report["closed_void_and_powder_escape"]["resolutions"][-1]
    carrier = report["carrier_distributed_contact_correction_plan"]["f38_baseline"]
    lines = [
        ("Maillage exact", f"{thickness_report['triangle_count']:,} triangles"),
        ("Couverture cordes", f"{100.0 * thickness_report['resolved_fraction']:.4f} %"),
        ("p01 corde", f"{thickness_report['p01_mm_if_scale_is_mm']:.3f} mm conditionnels"),
        ("Vides fermés @ maille fine", f"{finest_void['trapped_component_count']} / {finest_void['trapped_volume_mm3_if_scale_is_mm']:.1f} mm³"),
        ("Orientation candidate", selected["id"]),
        ("Simulation inherent-strain", "NON EXÉCUTÉE — outil/paramètres absents"),
        ("Porte-axes F38 max", f"{carrier['finest_raw_maximum_mpa']:.03f} MPa"),
        ("Convergence max F38", f"{100.0 * carrier['raw_maximum_relative_change']:.2f} % — ÉCHEC"),
        ("Décision", "NON IMPRIMABLE / NON AUTORISÉ"),
    ]
    y = 0.92
    for label, value in lines:
        panel.text(0.03, y, label, color="#91a5b2", fontsize=10, transform=panel.transAxes)
        panel.text(0.45, y, value, color="white" if label != "Décision" else "#ff7058", fontsize=10, fontweight="bold", transform=panel.transAxes)
        y -= 0.09
    panel.text(
        0.03,
        0.04,
        "Carte exhaustive sur le domaine discret des facettes, pas preuve continue ni CT. Aucune cote ajoutée. Les surépaisseurs restent indéfinies.",
        color="#f2c66d",
        fontsize=9,
        wrap=True,
        transform=panel.transAxes,
    )
    figure.tight_layout(rect=(0.01, 0.02, 0.99, 0.95))
    figure.savefig(destination, dpi=175, facecolor=figure.get_facecolor())
    plt.close(figure)


def validate_inputs(args: argparse.Namespace, contract: dict, f37: dict, f38: dict, cad: dict, carrier: dict) -> None:
    require(contract.get("phase") == "F39", "contract_phase_not_F39")
    require(contract.get("source_constraints", {}).get("additional_part_dimensions_introduced") is False, "F39_must_not_add_dimensions")
    require(sha256(args.head) == contract["source_constraints"]["exact_f37_head_mesh_sha256"], "head_sha256_mismatch")
    expected = contract["parent_evidence"]
    require(sha256(args.f37_lpbf_report) == expected["f37_exact_lpbf_report_sha256"], "f37_lpbf_report_sha256_mismatch")
    require(sha256(args.f38_lpbf_report) == expected["f38_brep_lpbf_report_sha256"], "f38_lpbf_report_sha256_mismatch")
    require(sha256(args.f38_carrier_cad_report) == expected["f38_carrier_cad_report_sha256"], "f38_carrier_cad_sha256_mismatch")
    require(sha256(args.f38_carrier_report) == expected["f38_carrier_calculix_report_sha256"], "f38_carrier_report_sha256_mismatch")
    require(f37["inputs"]["head_sha256"] == sha256(args.head), "f37_report_not_bound_to_exact_head")
    require(f37["inputs"]["scale_confirmed"] is False, "unexpected_confirmed_scale")
    require(f37["gates"]["metal_print_authorized"] is False, "f37_print_gate_must_be_false")
    require(f38["release_gates"]["metal_print_authorized"] is False, "f38_print_gate_must_be_false")
    require(f38["release_gates"]["engine_start_authorized"] is False, "f38_start_gate_must_be_false")
    require(cad["release_gates"]["metal_print_authorized"] is False, "f38_carrier_cad_print_gate_must_be_false")
    require(carrier["gates"]["raw_maximum_grid_change_below_10_percent"] is False, "f38_raw_max_convergence_expected_false")
    require(carrier["gates"]["qualified_material_card"] is False, "f38_material_gate_must_be_false")
    require(all(value is False for value in contract["release_gates"].values()), "contract_release_gates_must_all_be_false")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--head", type=Path, required=True)
    parser.add_argument("--f37-lpbf-report", type=Path, required=True)
    parser.add_argument("--f38-lpbf-report", type=Path, required=True)
    parser.add_argument("--f38-carrier-cad-report", type=Path, required=True)
    parser.add_argument("--f38-carrier-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--publish-dir", type=Path, required=True)
    args = parser.parse_args()

    contract = load_json(args.contract)
    f37 = load_json(args.f37_lpbf_report)
    f38 = load_json(args.f38_lpbf_report)
    carrier_cad = load_json(args.f38_carrier_cad_report)
    carrier = load_json(args.f38_carrier_report)
    validate_inputs(args, contract, f37, f38, carrier_cad, carrier)
    args.output.mkdir(parents=True, exist_ok=False)
    args.publish_dir.mkdir(parents=True, exist_ok=True)

    poly, points, faces = load_stl(args.head)
    mesh_topology = topology(poly)
    require(mesh_topology["watertight_manifold_screen"], "scan_mesh_not_watertight_manifold")
    triangles, centroids, normals, areas, signed_volume = triangle_geometry(points, faces)
    bounds = np.column_stack((points.min(axis=0), points.max(axis=0)))
    diagonal = float(np.linalg.norm(bounds[:, 1] - bounds[:, 0]))
    thickness = exhaustive_normal_chords(poly, centroids, normals, diagonal)
    inherited_requirement = float(contract["audit_definition"]["thickness"]["inherited_screen_requirement_mm_if_scale_is_mm"])
    thickness_report = thickness_summary(thickness, areas, inherited_requirement)
    map_path = args.output / "f39-lpbf-exhaustive-triangle-thickness-map.npz"
    np.savez_compressed(
        map_path,
        triangle_id=np.arange(len(faces), dtype=np.int32),
        centroid_mm_if_scale_is_mm=centroids.astype(np.float32),
        face_area_mm2_if_scale_is_mm=areas.astype(np.float32),
        normal=normals.astype(np.float32),
        thickness_chord_mm_if_scale_is_mm=thickness.astype(np.float32),
    )
    thickness_report["local_map"] = {
        "path": f"local-only://{map_path.name}",
        "sha256": sha256(map_path),
        "bytes": map_path.stat().st_size,
        "repository_policy": "local_only_derived_scan_data",
    }

    void_resolutions = [
        trapped_void_screen(poly, bounds, float(pitch))
        for pitch in contract["audit_definition"]["closed_voids"]["voxel_pitches_mm_if_scale_is_mm"]
    ]
    finest, previous = void_resolutions[-1], void_resolutions[-2]
    void_relative_change = abs(finest["trapped_volume_mm3_if_scale_is_mm"] - previous["trapped_volume_mm3_if_scale_is_mm"]) / max(
        finest["trapped_volume_mm3_if_scale_is_mm"], 1.0e-12
    )
    envelope = np.asarray(contract["audit_definition"]["orientation"]["machine_envelope_mm_if_scale_is_mm"], dtype=float)
    critical_angle = float(contract["audit_definition"]["orientation"]["critical_downward_normal_angle_from_vertical_deg"])
    orientations, selected = orientation_screen(points, centroids, normals, areas, envelope, critical_angle)
    tools = solver_inventory()

    f38_baseline = carrier["cases"][-1]
    carrier_plan = {
        "status": "plan_defined_not_executed_missing_measured_contacts_clearances_and_resultants",
        "f38_baseline": {
            "carrier_cad_report_sha256": sha256(args.f38_carrier_cad_report),
            "calculix_report_sha256": sha256(args.f38_carrier_report),
            "finest_mesh_size_mm": f38_baseline["mesh"]["mesh_size_mm"],
            "finest_raw_maximum_mpa": f38_baseline["von_mises_mpa"]["maximum"],
            "finest_p99_mpa": f38_baseline["von_mises_mpa"]["p99"],
            "finest_maximum_displacement_mm": f38_baseline["maximum_displacement_mm"],
            "raw_maximum_relative_change": carrier["fine_vs_previous"]["raw_maximum_relative_change"],
            "p99_relative_change": carrier["fine_vs_previous"]["p99_relative_change"],
            "raw_maximum_converged_below_10_percent": carrier["gates"]["raw_maximum_grid_change_below_10_percent"],
            "qualified_material_card": carrier["gates"]["qualified_material_card"],
            "nonlinear_contact_complete": carrier["gates"]["nonlinear_contact_complete"],
        },
        "model_scope": contract["carrier_correction_plan"]["required_model"],
        "implementation_sequence": [
            "replace_nodal_ring_loads_with_resultant_preserving_distributed_tractions_on_measured_bearing_contact_patches",
            "model_two_shafts_four_rockers_carrier_and_head_interface_as_separate_bodies",
            "add_surface_to_surface_contact_and_measured_clearances_without_penalty_stiffness_tuning_to_force_convergence",
            "apply_measured_fastener_pretension_and_head_interface_contact_instead_of_fully_fixed_mount_nodes",
            "refine_contact_edges_and_curved_load_transitions_with_three_independent_meshes",
            "track_raw_maximum_p99_displacement_strain_energy_and_contact_pressure_p99",
            "if_raw_maximum_remains_mesh_singular_modify_the_physical_fillet_or_load_transfer_geometry_then_repeat_all_grids",
        ],
        "load_resultants_n": None,
        "contact_clearances_mm": None,
        "fastener_pretension_n": None,
        "geometry_corrections_mm": None,
        "missing_evidence": [
            "measured_rocker_to_shaft_and_shaft_to_carrier_clearances",
            "measured_fastener_pretension_and_head_interface_compliance",
            "measured_cam_resultants_and_directions_over_cycle",
            "qualified_temperature_dependent_material_and_contact_cards",
        ],
        "target_relative_change": contract["carrier_correction_plan"]["target_relative_change"],
        "executed": False,
    }
    machining = {
        "numeric_allowances_defined": False,
        "reason": contract["audit_definition"]["machining_allowances"]["reason"],
        "zones": [
            {"id": name, "additional_allowance_mm": None, "datum_defined": False}
            for name in (
                "cylinder_sealing_deck",
                "valve_seat_pockets",
                "valve_guide_bores",
                "spark_plug_seat_and_thread",
                "rocker_shaft_bores_and_carrier_mounts",
                "intake_and_exhaust_flange_faces",
                "stud_threads_and_counterbores",
            )
        ],
        "correction_rule": "reconstruct_and_measure_each_functional_surface_then_assign_process_specific_allowance_in_a_tolerance_stack",
    }
    gates = {
        "exact_scan_sha256_verified": True,
        "all_scan_triangles_evaluated_for_normal_chord": thickness_report["evaluated_triangle_count"] == mesh_topology["triangles"],
        "all_triangle_chords_resolved": thickness_report["unresolved_triangle_count"] == 0,
        "all_resolved_chords_meet_inherited_1_5_mm_screen": thickness_report["all_resolved_chords_meet_inherited_requirement"],
        "continuous_wall_thickness_proved": False,
        "closed_void_zero_at_all_voxel_resolutions": all(item["trapped_component_count"] == 0 for item in void_resolutions),
        "powder_escape_physically_demonstrated": False,
        "orientation_fits_inherited_envelope_conditionally": bool(selected["fits_inherited_250x250x325_envelope_if_scale_is_mm"]),
        "support_topology_sliced_and_reviewed": False,
        "machining_allowances_dimensioned": False,
        "calibrated_inherent_strain_simulation_complete": False,
        "carrier_distributed_contact_model_complete": False,
        "carrier_raw_maximum_converged_below_10_percent": False,
        "absolute_scale_confirmed": False,
        "qualified_hot_material_card": False,
        "ct_cmm_fpi_pressure_test_complete": False,
        "professional_engineering_review_complete": False,
        "metal_print_authorized": False,
        "engine_start_authorized": False,
    }
    report = {
        "schema_version": "1.0.0",
        "phase": "F39",
        "status": "scan_only_lpbf_and_structural_audit_complete_release_blocked",
        "classification": "exhaustive_discrete_scan_screen_and_correction_plan_not_production_CAD_process_simulation_or_release",
        "inputs": {
            "contract": {"path": "../../f39-lpbf-scan-only-contract.json", "sha256": sha256(args.contract)},
            "exact_f37_head": {"path": "local-only://917-head-f37-printable-proof.local.stl", "sha256": sha256(args.head)},
            "f37_exact_lpbf_report": {"path": "local-only://f37-lpbf-exact/lpbf-printability-report.json", "sha256": sha256(args.f37_lpbf_report)},
            "f38_brep_lpbf_report": {"path": "../f38-brep-lpbf/f38-brep-lpbf-report.json", "sha256": sha256(args.f38_lpbf_report)},
            "f38_carrier_cad_report": {"path": "local-only://f38-rocker-carrier-cad-report.json", "sha256": sha256(args.f38_carrier_cad_report)},
            "f38_carrier_calculix_report": {"path": "local-only://f38-carrier-calculix-report.json", "sha256": sha256(args.f38_carrier_report)},
        },
        "source_constraints": {
            "scan_only": True,
            "additional_part_dimensions_introduced": False,
            "absolute_scale_confirmed": False,
            "production_brep_available": False,
            "F38_evidence_reused_without_promotion": True,
        },
        "toolchain": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "vtk": vtk.vtkVersion.GetVTKVersion(),
            "scipy": __import__("scipy").__version__,
            "matplotlib": matplotlib.__version__,
            "generator_sha256": sha256(Path(__file__)),
        },
        "scan_mesh": {
            **mesh_topology,
            "bounds_mm_if_scale_is_mm": bounds.tolist(),
            "signed_volume_mm3_if_scale_is_mm": signed_volume,
            "surface_area_mm2_if_scale_is_mm": float(np.sum(areas)),
        },
        "exhaustive_thickness_map": thickness_report,
        "closed_void_and_powder_escape": {
            "resolutions": void_resolutions,
            "fine_vs_previous_trapped_volume_relative_change": void_relative_change,
            "resolution_converged_below_10_percent": void_relative_change < 0.1,
            "minimum_escape_diameter_mm": None,
            "minimum_escape_diameter_missing_reason": contract["audit_definition"]["closed_voids"]["minimum_escape_diameter_missing_reason"],
            "correction_plan": "connect_each_persistent_closed_component_to_an_exterior_service_opening_then_repeat_resolution_study_and_physical_powder_removal_test",
        },
        "orientation_and_support_screen": {
            "method": "all_triangle_downward_normal_area_and_vertical_column_proxy",
            "critical_angle_deg": critical_angle,
            "candidate_count": len(orientations),
            "candidates": orientations,
            "selected": selected,
            "supports_generated": False,
            "machine_sliced": False,
            "distortion_simulated": False,
        },
        "machining_allowances": machining,
        "inherent_strain_simulation": tools,
        "carrier_distributed_contact_correction_plan": carrier_plan,
        "gates": gates,
        "verdict": "NON IMPRIMABLE / NON AUTORISE. La peau de scan fournit une carte discrete exhaustive, mais pas une CAO de production; parois, cavites, supports, surépaisseurs, procédé calibré et contact du porte-axes restent non libérés.",
    }
    image_path = args.publish_dir / "f39-lpbf-scan-only-audit.png"
    render(triangles, thickness, report, image_path)
    report["published_image"] = {
        "path": image_path.name,
        "sha256": sha256(image_path),
        "bytes": image_path.stat().st_size,
    }
    report_path = args.publish_dir / "f39-lpbf-scan-only-report.json"
    write_json(report_path, report)
    write_json(args.output / report_path.name, report)
    shutil.copy2(image_path, args.output / image_path.name)
    print(
        json.dumps(
            {
                "status": report["status"],
                "report": str(report_path),
                "image": str(image_path),
                "thickness_resolved": thickness_report["resolved_triangle_count"],
                "thickness_total": thickness_report["triangle_count"],
                "finest_trapped_volume_mm3": finest["trapped_volume_mm3_if_scale_is_mm"],
                "gates": gates,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
