#!/usr/bin/env python3
"""Évalue l'imprimabilité LPBF géométrique F36 et choisit une orientation.

Le test couvre enveloppe machine, surplombs, continuité couche par couche,
épaisseur échantillonnée, poudre potentiellement piégée et retrait libre. Il ne
remplace ni une simulation thermo-mécanique calibrée machine, ni un build test.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
from scipy import ndimage
import trimesh


BUILD_ENVELOPE_MM = np.asarray([250.0, 250.0, 325.0])
LAYER_HEIGHT_MM = 0.05
CRITICAL_OVERHANG_FROM_HORIZONTAL_DEG = 45.0
VOXEL_AUDIT_PITCH_MM = 2.0
WINDING_CHUNK_TRIANGLES = 32768
THICKNESS_GRID_CELL_MM = 4.0
THICKNESS_MAX_INDEX_REFERENCES = 12_000_000
ASSUMED_DENSITY_KG_M3 = 2670.0


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def rotations() -> dict[str, np.ndarray]:
    candidates = {
        "scan_z_up": np.eye(4),
        "scan_z_down": trimesh.transformations.rotation_matrix(math.pi, [1.0, 0.0, 0.0]),
        "scan_x_up": trimesh.transformations.rotation_matrix(math.pi / 2.0, [0.0, 1.0, 0.0]),
        "scan_x_down": trimesh.transformations.rotation_matrix(-math.pi / 2.0, [0.0, 1.0, 0.0]),
        "scan_y_up": trimesh.transformations.rotation_matrix(-math.pi / 2.0, [1.0, 0.0, 0.0]),
        "scan_y_down": trimesh.transformations.rotation_matrix(math.pi / 2.0, [1.0, 0.0, 0.0]),
    }
    base = candidates["scan_y_down"]
    for axis_name, axis in (("x", [1.0, 0.0, 0.0]), ("y", [0.0, 1.0, 0.0])):
        for angle_deg in (-45, -30, -15, 15, 30, 45):
            tilt = trimesh.transformations.rotation_matrix(math.radians(angle_deg), axis)
            candidates[f"scan_y_down_tilt_{axis_name}_{angle_deg:+d}"] = tilt @ base
    for x_angle in (-30, -15, 15, 30):
        for y_angle in (-30, -15, 15, 30):
            tilt_x = trimesh.transformations.rotation_matrix(math.radians(x_angle), [1.0, 0.0, 0.0])
            tilt_y = trimesh.transformations.rotation_matrix(math.radians(y_angle), [0.0, 1.0, 0.0])
            candidates[f"scan_y_down_tilt_xy_{x_angle:+d}_{y_angle:+d}"] = tilt_y @ tilt_x @ base
    return candidates


def oriented(mesh: trimesh.Trimesh, transform: np.ndarray) -> trimesh.Trimesh:
    candidate = mesh.copy()
    candidate.apply_transform(transform)
    candidate.apply_translation([0.0, 0.0, -candidate.bounds[0, 2]])
    return candidate


def orientation_metrics(name: str, mesh: trimesh.Trimesh, transform: np.ndarray) -> dict:
    candidate = oriented(mesh, transform)
    extents = candidate.extents
    normals = candidate.face_normals
    downward = normals[:, 2] < -math.cos(math.radians(CRITICAL_OVERHANG_FROM_HORIZONTAL_DEG))
    overhang_area = float(candidate.area_faces[downward].sum())
    projected_area = float(np.sum(candidate.area_faces[downward] * -normals[downward, 2]))
    height_weighted_proxy = float(
        np.sum(candidate.area_faces[downward] * -normals[downward, 2] * candidate.triangles_center[downward, 2])
    )
    fits = bool(np.all(extents <= BUILD_ENVELOPE_MM))
    return {
        "id": name,
        "transform": np.asarray(transform, dtype=float).tolist(),
        "extents_mm_if_scale_is_mm": extents.tolist(),
        "layer_count_at_50_um": int(math.ceil(extents[2] / LAYER_HEIGHT_MM)),
        "fits_250x250x325_mm": fits,
        "downward_overhang_area_mm2": overhang_area,
        "projected_support_area_mm2": projected_area,
        "column_support_volume_proxy_mm3": height_weighted_proxy,
        "score": height_weighted_proxy + 50.0 * projected_area + (0.0 if fits else 1.0e12),
    }


def winding_number_at_point(mesh: trimesh.Trimesh, point: np.ndarray) -> float:
    """Calcule le nombre d'enroulement signé sans construire de R-tree.

    La somme d'angles solides est parcourue par blocs de triangles afin que la
    mémoire dépende de ``WINDING_CHUNK_TRIANGLES`` et non du produit entre le
    nombre de requêtes et le nombre de faces.
    """

    point = np.asarray(point, dtype=np.float64).reshape(1, 3)
    total_angle = 0.0
    for start in range(0, len(mesh.faces), WINDING_CHUNK_TRIANGLES):
        faces = mesh.faces[start : start + WINDING_CHUNK_TRIANGLES]
        triangles = np.asarray(mesh.vertices[faces], dtype=np.float64)
        a = triangles[:, 0, :] - point
        b = triangles[:, 1, :] - point
        c = triangles[:, 2, :] - point
        a_norm = np.linalg.norm(a, axis=1)
        b_norm = np.linalg.norm(b, axis=1)
        c_norm = np.linalg.norm(c, axis=1)
        numerator = np.einsum("ij,ij->i", a, np.cross(b, c))
        denominator = (
            a_norm * b_norm * c_norm
            + np.einsum("ij,ij->i", a, b) * c_norm
            + np.einsum("ij,ij->i", b, c) * a_norm
            + np.einsum("ij,ij->i", c, a) * b_norm
        )
        total_angle += float(np.sum(2.0 * np.arctan2(numerator, denominator)))
    return total_angle / (4.0 * math.pi)


def classify_component_by_winding(
    mesh: trimesh.Trimesh,
    grid: trimesh.voxel.VoxelGrid,
    component_indices_padded: np.ndarray,
) -> tuple[bool, list[dict[str, object]]]:
    """Classe une composante fermée avec trois sondes déterministes.

    Une composante numérique qui donne des classes contradictoires est refusée
    plutôt que transformée en fausse preuve de dépoudrage.
    """

    count = len(component_indices_padded)
    sample_offsets = sorted({count // 4, count // 2, (3 * count) // 4})
    grid_indices = component_indices_padded[sample_offsets] - 1
    points = np.asarray(grid.indices_to_points(grid_indices), dtype=np.float64)
    samples: list[dict[str, object]] = []
    classifications: list[bool] = []
    for point in points:
        winding = winding_number_at_point(mesh, point)
        if not math.isfinite(winding):
            raise RuntimeError("nombre d'enroulement non fini dans l'audit voxel")
        absolute_winding = abs(winding)
        if 0.25 < absolute_winding < 0.75:
            raise RuntimeError("classification voxel ambiguë près d'une surface")
        is_material = absolute_winding >= 0.75
        classifications.append(is_material)
        samples.append(
            {
                "point_mm": point.tolist(),
                "signed_winding_number": winding,
                "classification": "solid_material" if is_material else "trapped_void",
            }
        )
    if len(set(classifications)) != 1:
        raise RuntimeError("classification voxel incohérente dans une même composante")
    return classifications[0], samples


def voxel_audit(mesh: trimesh.Trimesh, pitch_mm: float = VOXEL_AUDIT_PITCH_MM) -> dict:
    # Conserver d'abord uniquement les voxels de surface. ``fill(holes)`` est
    # volontairement interdit ici: il remplirait aussi les cavités réellement
    # fermées et rendrait le contrôle de poudre piégée aveugle. Les composantes
    # fermées du complément sont classées par nombre d'enroulement signé. La
    # somme d'angles solides par blocs évite le R-tree de ``mesh.contains``, qui
    # dépassait la mémoire de la machine x86 de 15 Gio sur le maillage F37.
    if not math.isfinite(pitch_mm) or pitch_mm <= 0.0:
        raise ValueError("le pas voxel doit être strictement positif")
    grid = mesh.voxelized(pitch=pitch_mm, method="subdivide")
    surface = np.pad(np.asarray(grid.matrix, dtype=bool), 1, constant_values=False)
    void = ~surface
    connectivity = ndimage.generate_binary_structure(3, 1)
    labels, component_count = ndimage.label(void, structure=connectivity)
    boundary_labels = np.unique(
        np.concatenate(
            (
                labels[0, :, :].ravel(),
                labels[-1, :, :].ravel(),
                labels[:, 0, :].ravel(),
                labels[:, -1, :].ravel(),
                labels[:, :, 0].ravel(),
                labels[:, :, -1].ravel(),
            )
        )
    )
    exterior_labels = {int(value) for value in boundary_labels if int(value) != 0}
    occupied = surface.copy()
    trapped = np.zeros_like(surface)
    enclosed_components: list[dict[str, object]] = []
    for component in range(1, component_count + 1):
        if component in exterior_labels:
            continue
        component_mask = labels == component
        component_indices = np.argwhere(component_mask)
        is_material, winding_samples = classify_component_by_winding(
            mesh, grid, component_indices
        )
        if is_material:
            occupied[component_mask] = True
        else:
            trapped[component_mask] = True
        enclosed_components.append(
            {
                "label": component,
                "voxel_count": int(len(component_indices)),
                "winding_samples": winding_samples,
                "classification": "solid_material" if is_material else "trapped_void",
            }
        )

    unsupported = 0
    occupied_above_plate = 0
    structure = np.ones((3, 3), dtype=bool)
    occupied_layers = np.flatnonzero(np.any(occupied, axis=(0, 1)))
    first_occupied_layer = int(occupied_layers.min()) if len(occupied_layers) else 0
    for layer in range(first_occupied_layer + 1, occupied.shape[2]):
        previous_support = ndimage.binary_dilation(occupied[:, :, layer - 1], structure=structure)
        current = occupied[:, :, layer]
        unsupported += int(np.count_nonzero(current & ~previous_support))
        occupied_above_plate += int(np.count_nonzero(current))
    trapped_voxels = int(np.count_nonzero(trapped))
    return {
        "pitch_mm": pitch_mm,
        "grid_shape": list(occupied.shape),
        "occupied_voxels": int(np.count_nonzero(occupied)),
        "occupied_voxels_above_plate": occupied_above_plate,
        "unsupported_voxels_above_plate": unsupported,
        "unsupported_fraction": unsupported / max(1, occupied_above_plate),
        "trapped_void_voxels": trapped_voxels,
        "trapped_void_volume_mm3": trapped_voxels * pitch_mm**3,
        "enclosed_component_classification": enclosed_components,
        "method": "surface_voxel_components_plus_chunked_winding_number_without_fill_holes",
        "winding_chunk_triangles": WINDING_CHUNK_TRIANGLES,
        "classification": "coarse_voxel_screen_not_machine_build_processor_or_CT",
    }


def _linear_bin_ids(low: np.ndarray, high: np.ndarray, shape: np.ndarray) -> list[int]:
    ids: list[int] = []
    for x_index in range(int(low[0]), int(high[0]) + 1):
        for y_index in range(int(low[1]), int(high[1]) + 1):
            base = (x_index * int(shape[1]) + y_index) * int(shape[2])
            ids.extend(base + z_index for z_index in range(int(low[2]), int(high[2]) + 1))
    return ids


def build_triangle_grid_index(
    mesh: trimesh.Trimesh,
    cell_size_mm: float = THICKNESS_GRID_CELL_MM,
) -> dict[str, object]:
    """Construit un index AABB compressé avec une limite dure de références."""

    if not math.isfinite(cell_size_mm) or cell_size_mm <= 0.0:
        raise ValueError("la cellule d'index d'épaisseur doit être positive")
    margin = max(1.0e-6, cell_size_mm * 1.0e-9)
    origin = np.asarray(mesh.bounds[0], dtype=np.float64) - margin
    upper = np.asarray(mesh.bounds[1], dtype=np.float64) + margin
    shape = np.maximum(1, np.ceil((upper - origin) / cell_size_mm).astype(np.int64))
    triangles = np.asarray(mesh.vertices[mesh.faces], dtype=np.float64)
    low = np.floor((triangles.min(axis=1) - origin) / cell_size_mm).astype(np.int64)
    high = np.floor((triangles.max(axis=1) - origin) / cell_size_mm).astype(np.int64)
    low = np.clip(low, 0, shape - 1)
    high = np.clip(high, 0, shape - 1)
    references_per_face = np.prod(high - low + 1, axis=1)
    reference_count = int(np.sum(references_per_face, dtype=np.int64))
    if reference_count > THICKNESS_MAX_INDEX_REFERENCES:
        raise RuntimeError(
            "index d'épaisseur trop grand: "
            f"{reference_count} références > {THICKNESS_MAX_INDEX_REFERENCES}"
        )

    single = references_per_face == 1
    single_faces = np.flatnonzero(single).astype(np.int32)
    single_low = low[single]
    single_bins = (
        (single_low[:, 0] * shape[1] + single_low[:, 1]) * shape[2] + single_low[:, 2]
    ).astype(np.int32)
    bin_chunks = [single_bins]
    face_chunks = [single_faces]
    pending_bins: list[int] = []
    pending_faces: list[int] = []
    for face_id in np.flatnonzero(~single):
        ids = _linear_bin_ids(low[face_id], high[face_id], shape)
        pending_bins.extend(ids)
        pending_faces.extend([int(face_id)] * len(ids))
        if len(pending_bins) >= 100_000:
            bin_chunks.append(np.asarray(pending_bins, dtype=np.int32))
            face_chunks.append(np.asarray(pending_faces, dtype=np.int32))
            pending_bins.clear()
            pending_faces.clear()
    if pending_bins:
        bin_chunks.append(np.asarray(pending_bins, dtype=np.int32))
        face_chunks.append(np.asarray(pending_faces, dtype=np.int32))

    bin_ids = np.concatenate(bin_chunks)
    face_ids = np.concatenate(face_chunks)
    if len(bin_ids) != reference_count:
        raise RuntimeError("comptage incohérent dans l'index spatial d'épaisseur")
    order = np.argsort(bin_ids, kind="stable")
    sorted_bins = bin_ids[order]
    sorted_faces = face_ids[order]
    bin_count = int(np.prod(shape, dtype=np.int64))
    counts = np.bincount(sorted_bins, minlength=bin_count)
    offsets = np.empty(bin_count + 1, dtype=np.int64)
    offsets[0] = 0
    np.cumsum(counts, out=offsets[1:])
    return {
        "origin": origin,
        "shape": shape,
        "cell_size_mm": float(cell_size_mm),
        "offsets": offsets,
        "face_ids": sorted_faces,
        "reference_count": reference_count,
        "bin_count": bin_count,
    }


def _ray_triangle_distances(
    mesh: trimesh.Trimesh,
    face_ids: np.ndarray,
    origin: np.ndarray,
    direction: np.ndarray,
    minimum_distance: float,
) -> np.ndarray:
    if len(face_ids) == 0:
        return np.empty(0, dtype=np.float64)
    triangles = np.asarray(mesh.vertices[mesh.faces[face_ids]], dtype=np.float64)
    edge_1 = triangles[:, 1] - triangles[:, 0]
    edge_2 = triangles[:, 2] - triangles[:, 0]
    h = np.cross(np.broadcast_to(direction, edge_2.shape), edge_2)
    determinant = np.einsum("ij,ij->i", edge_1, h)
    valid = np.abs(determinant) > 1.0e-12
    inverse = np.zeros_like(determinant)
    inverse[valid] = 1.0 / determinant[valid]
    s = origin - triangles[:, 0]
    u = inverse * np.einsum("ij,ij->i", s, h)
    valid &= (u >= -1.0e-10) & (u <= 1.0 + 1.0e-10)
    q = np.cross(s, edge_1)
    v = inverse * np.einsum("ij,j->i", q, direction)
    valid &= (v >= -1.0e-10) & (u + v <= 1.0 + 1.0e-10)
    distance = inverse * np.einsum("ij,ij->i", edge_2, q)
    return distance[valid & (distance > minimum_distance)]


def ray_first_intersection(
    mesh: trimesh.Trimesh,
    index: dict[str, object],
    surface_point: np.ndarray,
    inward_direction: np.ndarray,
) -> float:
    """Retourne la première intersection positive via parcours DDA des cellules."""

    direction = np.asarray(inward_direction, dtype=np.float64)
    direction /= np.linalg.norm(direction)
    cell_size = float(index["cell_size_mm"])
    epsilon = max(1.0e-6, cell_size * 1.0e-6)
    origin = np.asarray(surface_point, dtype=np.float64) + epsilon * direction
    grid_origin = np.asarray(index["origin"], dtype=np.float64)
    shape = np.asarray(index["shape"], dtype=np.int64)
    cell = np.floor((origin - grid_origin) / cell_size).astype(np.int64)
    cell = np.clip(cell, 0, shape - 1)
    step = np.sign(direction).astype(np.int64)
    t_delta = np.full(3, np.inf, dtype=np.float64)
    nonzero = np.abs(direction) > 1.0e-15
    t_delta[nonzero] = cell_size / np.abs(direction[nonzero])
    next_boundary = grid_origin + np.where(step > 0, cell + 1, cell) * cell_size
    t_max = np.full(3, np.inf, dtype=np.float64)
    t_max[nonzero] = (next_boundary[nonzero] - origin[nonzero]) / direction[nonzero]

    offsets = np.asarray(index["offsets"])
    indexed_faces = np.asarray(index["face_ids"])
    visited: set[int] = set()
    best = math.inf
    max_steps = int(np.sum(shape)) + 3
    for _ in range(max_steps):
        linear = int((cell[0] * shape[1] + cell[1]) * shape[2] + cell[2])
        candidates = indexed_faces[offsets[linear] : offsets[linear + 1]]
        fresh = np.asarray([int(face) for face in candidates if int(face) not in visited], dtype=np.int64)
        visited.update(int(face) for face in candidates)
        distances = _ray_triangle_distances(
            mesh, fresh, origin, direction, minimum_distance=10.0 * epsilon
        )
        if len(distances):
            best = min(best, float(np.min(distances)))
        next_t = float(np.min(t_max))
        if best <= next_t + 1.0e-10:
            return best + epsilon
        crossed = np.flatnonzero(np.isclose(t_max, next_t, rtol=0.0, atol=1.0e-12))
        if len(crossed) == 0:
            raise RuntimeError("parcours DDA sans frontière suivante")
        for axis in crossed:
            cell[axis] += step[axis]
            t_max[axis] += t_delta[axis]
        if np.any(cell < 0) or np.any(cell >= shape):
            break
    return math.inf


def thickness_audit(mesh: trimesh.Trimesh, sample_count: int = 4000) -> dict:
    points, face_ids = trimesh.sample.sample_surface(mesh, sample_count, seed=1936)
    normals = mesh.face_normals[face_ids]
    index = build_triangle_grid_index(mesh)
    thickness = np.asarray(
        [ray_first_intersection(mesh, index, point, -normal) for point, normal in zip(points, normals)],
        dtype=np.float64,
    )
    finite = thickness[np.isfinite(thickness) & (thickness > 0.0)]
    minimum_resolved = math.ceil(0.95 * sample_count)
    if len(finite) < minimum_resolved:
        raise RuntimeError(
            f"échantillonnage d'épaisseur insuffisant: {len(finite)}/{sample_count} < {minimum_resolved}"
        )
    return {
        "method": "sampled_inward_normal_ray_uniform_grid_exact_triangle_intersection",
        "requested_sample_count": sample_count,
        "sample_count": int(len(finite)),
        "unresolved_sample_count": int(sample_count - len(finite)),
        "minimum_resolved_fraction": 0.95,
        "spatial_index_cell_mm": index["cell_size_mm"],
        "spatial_index_bins": index["bin_count"],
        "spatial_index_triangle_references": index["reference_count"],
        "spatial_index_reference_limit": THICKNESS_MAX_INDEX_REFERENCES,
        "minimum_mm_if_scale_is_mm": float(np.min(finite)),
        "p01_mm_if_scale_is_mm": float(np.quantile(finite, 0.01)),
        "p05_mm_if_scale_is_mm": float(np.quantile(finite, 0.05)),
        "median_mm_if_scale_is_mm": float(np.median(finite)),
        "ct_verified": False,
    }


def render(mesh: trimesh.Trimesh, metrics: dict, output: Path) -> None:
    normals = mesh.face_normals
    overhang = normals[:, 2] < -math.cos(math.radians(CRITICAL_OVERHANG_FROM_HORIZONTAL_DEG))
    keep = np.linspace(0, len(mesh.faces) - 1, min(65000, len(mesh.faces)), dtype=int)
    triangles = mesh.vertices[mesh.faces[keep]]
    selected_overhang = overhang[keep]
    base = np.asarray(to_rgb("#c28d39"))
    red = np.asarray(to_rgb("#ed5d4f"))
    colors = np.where(selected_overhang[:, None], red[None, :], base[None, :])

    figure = plt.figure(figsize=(14, 8), facecolor="#0a1118")
    figure.suptitle(
        f"{metrics['phase']} — test virtuel d'orientation LPBF",
        color="white",
        fontsize=20,
        fontweight="bold",
        y=0.97,
    )
    axis = figure.add_subplot(1, 2, 1, projection="3d", facecolor="#101b24")
    axis.add_collection3d(Poly3DCollection(triangles, facecolors=np.column_stack((colors, np.ones(len(colors)))), edgecolor="none"))
    centre = mesh.bounds.mean(axis=0)
    radius = 0.58 * float(max(mesh.extents))
    axis.set_xlim(centre[0] - radius, centre[0] + radius)
    axis.set_ylim(centre[1] - radius, centre[1] + radius)
    axis.set_zlim(0.0, 2.0 * radius)
    axis.set_box_aspect((1.0, 1.0, 1.1))
    axis.view_init(elev=22.0, azim=-48.0)
    axis.set_axis_off()
    axis.set_title(f"Orientation retenue: {metrics['selected_orientation']}", color="white", fontweight="bold")

    table_axis = figure.add_subplot(1, 2, 2, facecolor="#101b24")
    table_axis.axis("off")
    selected = metrics["selected"]
    voxel = metrics["voxel_audit"]
    thickness = metrics["thickness_audit"]
    rows = [
        ("Enveloppe", " × ".join(f"{v:.1f}" for v in selected["extents_mm_if_scale_is_mm"]) + " mm"),
        ("Couches 50 µm", f"{selected['layer_count_at_50_um']:,}".replace(",", " ")),
        ("Surplomb descendant", f"{selected['downward_overhang_area_mm2'] / 100.0:.1f} cm²"),
        ("Voxels sans appui", f"{100.0 * voxel['unsupported_fraction']:.3f} %"),
        ("Volume fermé détecté", f"{voxel['trapped_void_volume_mm3'] / 1000.0:.1f} cm³"),
        ("Épaisseur p01", f"{thickness['p01_mm_if_scale_is_mm']:.2f} mm"),
        ("Retrait libre 280 K", " / ".join(f"{v:.2f}" for v in metrics["free_contraction_mm_280k"]) + " mm"),
        ("Masse nue", f"{metrics['head_mass_kg']:.3f} kg"),
        ("Décision", "NON LIBÉRÉE POUR FABRICATION"),
    ]
    y = 0.90
    for label, value in rows:
        table_axis.text(0.03, y, label, color="#9fb0bd", fontsize=11, transform=table_axis.transAxes)
        table_axis.text(0.47, y, value, color="white", fontsize=11, fontweight="bold", transform=table_axis.transAxes)
        y -= 0.085
    table_axis.text(0.03, 0.05, "Rouge = faces exigeant support selon le critère 45°. Le volume de support reste un proxy, pas un slicing machine.", color="#f0bd58", fontsize=9.5, wrap=True, transform=table_axis.transAxes)
    figure.subplots_adjust(left=0.02, right=0.98, bottom=0.04, top=0.90, wspace=0.04)
    figure.savefig(output, dpi=180, facecolor=figure.get_facecolor())
    plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--head", type=Path, required=True)
    parser.add_argument("--geometry-report", type=Path, required=True)
    parser.add_argument("--phase", default="F36", choices=("F36", "F37"))
    parser.add_argument(
        "--voxel-pitch-mm",
        type=float,
        default=VOXEL_AUDIT_PITCH_MM,
        help="pas du criblage voxel grossier; augmenter réduit la mémoire et la résolution",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)

    head = trimesh.load_mesh(args.head, process=True)
    if not isinstance(head, trimesh.Trimesh) or not head.is_watertight or not head.is_winding_consistent:
        raise SystemExit("la géométrie LPBF candidate doit être étanche et orientée")
    geometry_report = json.loads(args.geometry_report.read_text(encoding="utf-8"))
    orientation_results = [orientation_metrics(name, head, transform) for name, transform in rotations().items()]
    eligible = [item for item in orientation_results if item["fits_250x250x325_mm"]]
    if not eligible:
        raise SystemExit("aucune orientation ne tient dans le volume LPBF")
    selected = min(eligible, key=lambda item: item["score"])
    selected_mesh = oriented(head, np.asarray(selected["transform"], dtype=float))
    voxel = voxel_audit(selected_mesh, pitch_mm=args.voxel_pitch_mm)
    thickness = thickness_audit(head)
    free_contraction = (selected_mesh.extents * 23.0e-6 * 280.0).tolist()
    head_mass = float(head.volume) * ASSUMED_DENSITY_KG_M3 * 1.0e-9

    report = {
        "schema_version": "1.0.0",
        "phase": args.phase,
        "status": "lpbf_geometric_virtual_build_screen_complete_release_blocked",
        "classification": "virtual_printability_screen_not_calibrated_process_simulation",
        "inputs": {
            "head_sha256": sha256(args.head),
            "geometry_report_sha256": sha256(args.geometry_report),
            "scale_confirmed": bool(geometry_report["source"]["scale_confirmed"]),
        },
        "machine_screen": {
            "process": "LPBF_aluminium_candidate",
            "build_envelope_mm": BUILD_ENVELOPE_MM.tolist(),
            "layer_height_mm": LAYER_HEIGHT_MM,
            "critical_overhang_from_horizontal_deg": CRITICAL_OVERHANG_FROM_HORIZONTAL_DEG,
            "machine_and_parameter_set_qualified": False,
        },
        "orientations": orientation_results,
        "selected_orientation": selected["id"],
        "selected": selected,
        "voxel_audit": voxel,
        "thickness_audit": thickness,
        "free_contraction_mm_280k": free_contraction,
        "head_mass_kg": head_mass,
        "assumed_density_kg_m3": ASSUMED_DENSITY_KG_M3,
        "estimated_build_hours_at_60_cm3_per_hour": float(head.volume / 1000.0 / 60.0),
        "gates": {
            "watertight_single_body": bool(head.is_watertight and head.body_count == 1),
            "fits_build_envelope": bool(selected["fits_250x250x325_mm"]),
            "sampled_p01_thickness_at_least_1_5_mm": thickness["p01_mm_if_scale_is_mm"] >= 1.5,
            "coarse_trapped_void_volume_zero": voxel["trapped_void_voxels"] == 0,
            "coarse_layer_support_fraction_below_0_5_percent": voxel["unsupported_fraction"] <= 0.005,
            "absolute_scale_confirmed": bool(geometry_report["source"]["scale_confirmed"]),
            "calibrated_thermomechanical_build_simulation": False,
            "machining_allowances_validated": False,
            "powder_removal_physically_validated": False,
            "metal_print_authorized": False,
            "engine_start_authorized": False,
        },
    }
    phase_slug = args.phase.lower()
    stl_path = args.output / f"917-head-{phase_slug}-lpbf-oriented.local.stl"
    image_path = args.output / f"917-head-{phase_slug}-lpbf-printability.png"
    report_path = args.output / "lpbf-printability-report.json"
    selected_mesh.export(stl_path)
    render(selected_mesh, report, image_path)
    report["local_files"] = {
        stl_path.name: {"sha256": sha256(stl_path), "bytes": stl_path.stat().st_size},
        image_path.name: {"sha256": sha256(image_path), "bytes": image_path.stat().st_size},
    }
    save_json(report_path, report)
    print(json.dumps({"status": report["status"], "report": str(report_path), "image": str(image_path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
