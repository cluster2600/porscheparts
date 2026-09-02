#!/usr/bin/env python3
"""Reconstruit localement une culasse 4V conforme a l'enveloppe du scan.

Le maillage achete et tous les derives geometriques restent hors Git. Le script
verifie l'empreinte du scan, reconstruit une peau etanche par Poisson, bouche le
coeur 2V visible puis soustrait un concept 4V explicite. Le resultat est un
prototype d'architecture pour revue, jamais une definition de fabrication.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import tempfile

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.colors import to_rgb
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import pymeshlab
import trimesh


EXPECTED_SCAN_SHA256 = "4623d5d3b73fe3d03ca988a47543a8dd1be7834d3040e6f7efd1e1e95c766486"
PHASE = "F36"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def keep_largest(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    parts = mesh.split(only_watertight=False)
    if not parts:
        raise RuntimeError("la reconstruction Poisson ne contient aucun composant")
    return max(parts, key=lambda part: abs(float(part.volume)))


def reconstruct_stock(envelope: Path, temporary: Path, target_faces: int) -> trimesh.Trimesh:
    poisson = temporary / "poisson.ply"
    largest = temporary / "poisson-largest.ply"
    reduced = temporary / "poisson-reduced.ply"

    mesh_set = pymeshlab.MeshSet()
    mesh_set.load_new_mesh(str(envelope))
    mesh_set.apply_filter("compute_normal_per_vertex")
    mesh_set.apply_filter(
        "generate_surface_reconstruction_screened_poisson",
        depth=8,
        fulldepth=5,
        scale=1.05,
        samplespernode=2.0,
        pointweight=4.0,
        iters=8,
        preclean=True,
        # Le plugin Poisson de pymeshlab peut echouer de facon non deterministe
        # lors de la fermeture d'octree en multi-thread sur cette peau ouverte.
        # Un seul thread privilegie la reproductibilite a la vitesse.
        threads=1,
    )
    mesh_set.save_current_mesh(str(poisson))
    reconstructed = keep_largest(trimesh.load_mesh(poisson, process=True))
    reconstructed.export(largest)

    mesh_set = pymeshlab.MeshSet()
    mesh_set.load_new_mesh(str(largest))
    mesh_set.apply_filter(
        "meshing_decimation_quadric_edge_collapse",
        targetfacenum=target_faces,
        preservetopology=True,
        preservenormal=True,
        optimalplacement=True,
    )
    mesh_set.save_current_mesh(str(reduced))
    stock = trimesh.load_mesh(reduced, process=True)
    if not stock.is_watertight or not stock.is_winding_consistent:
        raise RuntimeError("la peau scan-conforme reconstruite n'est pas etanche")
    return stock


def scan_conformance(envelope_path: Path, reconstructed: trimesh.Trimesh) -> dict[str, float | int | bool]:
    envelope = trimesh.load_mesh(envelope_path, process=False)
    points, _ = trimesh.sample.sample_surface(envelope, 50_000, seed=936)
    _, distances, _ = trimesh.proximity.closest_point(reconstructed, points)
    finite = np.asarray(distances, dtype=float)[np.isfinite(distances)]
    if len(finite) != len(distances):
        raise RuntimeError("la carte d'ecart scan contient des valeurs non finies")
    return {
        "sample_count": int(len(finite)),
        "median_obj_units": float(np.median(finite)),
        "p95_obj_units": float(np.quantile(finite, 0.95)),
        "p99_obj_units": float(np.quantile(finite, 0.99)),
        "maximum_obj_units": float(finite.max()),
        "p95_screen_threshold_obj_units": 1.5,
        "p95_screen_passed": bool(np.quantile(finite, 0.95) <= 1.5),
    }


def wall_screen(stock: trimesh.Trimesh, flow: trimesh.Trimesh) -> dict[str, float | int | bool]:
    points, _ = trimesh.sample.sample_surface(flow, 20_000, seed=937)
    # Exclut les bouches fonctionnelles, la face de chambre et les futurs
    # volumes de porte-arbres. La metrique porte sur les conduits internes.
    selected = points[
        (points[:, 2] > 3.0)
        & (points[:, 2] < 60.0)
        & (points[:, 1] > -75.0)
        & (points[:, 1] < 100.0)
    ]
    _, distances, _ = trimesh.proximity.closest_point(stock, selected)
    target = 4.0
    return {
        "method": "sampled_nearest_distance_to_filled_scan_skin_not_CT_thickness",
        "sample_count": int(len(selected)),
        "minimum_obj_units": float(distances.min()),
        "p01_obj_units": float(np.quantile(distances, 0.01)),
        "p05_obj_units": float(np.quantile(distances, 0.05)),
        "median_obj_units": float(np.median(distances)),
        "screen_target_obj_units": target,
        "sampled_screen_passed": bool(distances.min() >= target),
        "ct_or_metrology_validation": False,
    }


def local_transform(interfaces: dict) -> np.ndarray:
    frame = np.asarray(interfaces["frame_rows_A_B_C"], dtype=float)
    chamber = interfaces["combustion_interface"]["chamber_step"]
    centre_a, centre_b = (float(value) for value in chamber["center"])
    plane_c = float(chamber["plane_C"])
    transform = np.eye(4)
    transform[:3, :3] = np.diag([1.0, 1.0, -1.0]) @ frame
    transform[:3, 3] = np.asarray([-centre_a, -centre_b, plane_c])
    return transform


def cylinder_between(start: np.ndarray, end: np.ndarray, radius: float, sections: int = 48) -> trimesh.Trimesh:
    return trimesh.creation.cylinder(
        radius=float(radius),
        segment=np.vstack((np.asarray(start, dtype=float), np.asarray(end, dtype=float))),
        sections=sections,
    )


def path_tube(points: list[tuple[float, float, float]], radii: list[float]) -> list[trimesh.Trimesh]:
    if len(points) != len(radii):
        raise ValueError("points et rayons doivent avoir la meme longueur")
    meshes: list[trimesh.Trimesh] = []
    vectors = [np.asarray(point, dtype=float) for point in points]
    for index, point in enumerate(vectors):
        sphere = trimesh.creation.icosphere(subdivisions=2, radius=float(radii[index]))
        sphere.apply_translation(point)
        meshes.append(sphere)
    for index in range(len(vectors) - 1):
        meshes.append(cylinder_between(vectors[index], vectors[index + 1], min(radii[index], radii[index + 1])))
    return meshes


def union(meshes: list[trimesh.Trimesh]) -> trimesh.Trimesh:
    result = trimesh.boolean.union(meshes, engine="manifold", check_volume=False)
    if not isinstance(result, trimesh.Trimesh):
        raise RuntimeError("l'union booleenne n'a pas produit un maillage")
    return result


def _subtract_voxel_mesh(matrix: np.ndarray, grid_transform: np.ndarray, cutter: trimesh.Trimesh, pitch: float) -> None:
    cutter_grid = cutter.voxelized(pitch=pitch, method="subdivide").fill(method="holes")
    points = cutter_grid.points
    inverse = np.linalg.inv(grid_transform)
    indices = np.rint(trimesh.transform_points(points, inverse)).astype(np.int64)
    valid = np.all((indices >= 0) & (indices < np.asarray(matrix.shape)[None, :]), axis=1)
    indices = indices[valid]
    matrix[indices[:, 0], indices[:, 1], indices[:, 2]] = False


def voxel_boolean_head(
    stock: trimesh.Trimesh,
    cutters: list[trimesh.Trimesh],
    pitch: float = 0.75,
) -> tuple[trimesh.Trimesh, trimesh.Trimesh]:
    """Bouche l'ancien coeur en voxels puis soustrait l'architecture 4V.

    La peau Poisson du scan contient encore les tunnels fonctionnels 2V. Une
    union B-Rep sur cette topologie de genre eleve est instable. La booleenne
    voxel garde la surface externe, remplit seulement les volumes de coeur
    mesures, puis remaillage le solide de facon deterministe.
    """

    grid = stock.voxelized(pitch=pitch, method="subdivide").fill(method="holes")
    matrix = np.asarray(grid.matrix, dtype=bool).copy()
    transform = np.asarray(grid.transform, dtype=float)
    x = transform[0, 0] * np.arange(matrix.shape[0]) + transform[0, 3]
    y = transform[1, 1] * np.arange(matrix.shape[1]) + transform[1, 3]
    z = transform[2, 2] * np.arange(matrix.shape[2]) + transform[2, 3]
    xx = x[:, None, None]
    yy = y[None, :, None]
    zz = z[None, None, :]

    # Le coeur est rebouche seulement jusqu'au toit des conduits. Le volume
    # superieur du scan reste ouvert pour recevoir un vrai porte-arbres et un
    # couvre-culasse 4V; prolonger ce cylindre jusqu'en haut creerait la fausse
    # paroi ronde visible sur le prototype precedent.
    core_fill = (xx * xx + yy * yy <= 51.5**2) & (zz >= -3.5) & (zz <= 60.0)
    intake_fill = (xx * xx + (zz - 31.0) ** 2 <= 22.5**2) & (yy >= -89.0) & (yy <= -34.0)
    exhaust_fill = (xx * xx + (zz - 42.0) ** 2 <= 21.0**2) & (yy >= 36.0) & (yy <= 116.0)
    matrix |= core_fill | intake_fill | exhaust_fill
    stock_matrix = matrix.copy()

    # Chambre spherique analytique: evite de voxeliser une sphere complete de
    # 160 mm alors que seule sa calotte coupe le plan de combustion.
    chamber_mask = xx * xx + yy * yy + (zz + 66.0) ** 2 <= 80.0**2
    matrix &= ~chamber_mask
    for cutter in cutters:
        _subtract_voxel_mesh(matrix, transform, cutter, pitch)

    filled_grid = trimesh.voxel.VoxelGrid(
        trimesh.voxel.encoding.DenseEncoding(matrix),
        transform=transform,
    )
    head = filled_grid.marching_cubes
    head.apply_transform(transform)
    head = keep_largest(head)
    head.remove_unreferenced_vertices()

    # Avant soustraction, le stock rebouche sert de peau thermique et de
    # reference pour les epaisseurs. Il est genere avec la meme grille.
    stock_grid = trimesh.voxel.VoxelGrid(
        trimesh.voxel.encoding.DenseEncoding(stock_matrix),
        transform=transform,
    )
    filled_stock = stock_grid.marching_cubes
    filled_stock.apply_transform(transform)
    filled_stock = keep_largest(filled_stock)
    filled_stock.remove_unreferenced_vertices()
    return head, filled_stock


def architecture() -> dict:
    return {
        "chamber_diameter_mm": 90.81248542471897,
        "register_diameter_mm": 113.52636742684192,
        "stud_pattern_mm": [86.74276999873194, 85.91583774915038],
        "stud_hole_diameter_mm": 10.740243181981537,
        "included_valve_angle_deg": 36.0,
        "intake": {
            "count": 2,
            "head_diameter_mm": 31.5,
            "stem_diameter_mm": 7.0,
            "centres_mm": [[-18.0, -17.0, 0.0], [18.0, -17.0, 0.0]],
            "tilt_y_deg": -18.0,
            "candidate_material": "Ti-6Al-4V forged or wrought; not LPBF release",
        },
        "exhaust": {
            "count": 2,
            "head_diameter_mm": 26.0,
            "stem_diameter_mm": 7.0,
            "centres_mm": [[-18.0, 17.0, 0.0], [18.0, 17.0, 0.0]],
            "tilt_y_deg": 18.0,
            "candidate_material": "INCONEL alloy 751 wrought; not printed",
        },
        "spark_plug": {
            "count": 2,
            "pilot_diameter_mm": 8.5,
            "nominal_thread_candidate": "M10x1.0",
            "electrode_centres_mm": [[-37.0, 0.0, 0.0], [37.0, 0.0, 0.0]],
            "architecture": "twin_ignition_lateral_canted",
        },
        "spring_candidate": "dual Cr-Si wire spring package; rate and installed load not released",
    }


def valve_axis(centre: list[float], tilt_y_deg: float, z_end: float = 84.0) -> tuple[np.ndarray, np.ndarray]:
    start = np.asarray(centre, dtype=float)
    angle = math.radians(float(tilt_y_deg))
    end = start + np.asarray([0.0, math.tan(angle) * z_end, z_end])
    return start, end


def build_geometry(
    stock_scan: trimesh.Trimesh,
    cfg: dict,
    interfaces: dict,
) -> tuple[trimesh.Trimesh, trimesh.Trimesh, trimesh.Trimesh, dict]:
    print("F36: preparation du repere scan local", flush=True)
    transform = local_transform(interfaces)
    stock_scan = stock_scan.copy()
    stock_scan.apply_transform(transform)
    if stock_scan.volume < 0.0:
        stock_scan.invert()

    # Le Poisson ferme deja les ouvertures du scan. Une union additionnelle
    # entre la peau a fort genre topologique et des bouchons analytiques rend
    # Manifold instable et, surtout, masquerait les volumes reellement observes.
    stock = stock_scan

    print("F36: construction analytique des volumes internes", flush=True)
    cutters: list[trimesh.Trimesh] = []
    flow_parts: list[trimesh.Trimesh] = []

    # Chambre peu profonde bornee par le registre mesure. La sphere produit un
    # toit continu; les bols de sieges et conduits viennent ensuite le rejoindre.
    chamber_radius = 80.0
    chamber_sphere = trimesh.creation.icosphere(subdivisions=4, radius=chamber_radius)
    # R=80 et centre z=-66 donnent une intersection de 45,3 mm au plan z=0,
    # pratiquement egale au rayon de chambre mesure (45,406 mm), sans face
    # coplanaire artificielle dans la booleenne.
    chamber_sphere.apply_translation([0.0, 0.0, -66.0])
    chamber = chamber_sphere
    flow_parts.append(chamber)

    intake_paths = [
        [(-18.0, -17.0, 2.0), (-18.0, -26.0, 16.0), (-14.0, -42.0, 28.0), (-8.0, -57.0, 32.0), (0.0, -70.0, 31.0)],
        [(18.0, -17.0, 2.0), (18.0, -26.0, 16.0), (14.0, -42.0, 28.0), (8.0, -57.0, 32.0), (0.0, -70.0, 31.0)],
    ]
    exhaust_paths = [
        [(-18.0, 17.0, 2.0), (-18.0, 27.0, 18.0), (-14.0, 44.0, 31.0), (-8.0, 62.0, 40.0), (0.0, 78.0, 42.0)],
        [(18.0, 17.0, 2.0), (18.0, 27.0, 18.0), (14.0, 44.0, 31.0), (8.0, 62.0, 40.0), (0.0, 78.0, 42.0)],
    ]
    for path in intake_paths:
        flow_parts.extend(path_tube(path, [12.8, 12.4, 12.0, 13.0, 16.0]))
    flow_parts.extend(path_tube([(0.0, -68.0, 31.0), (0.0, -88.0, 31.0)], [18.5, 21.5]))
    for path in exhaust_paths:
        flow_parts.extend(path_tube(path, [10.7, 10.5, 10.8, 12.0, 15.0]))
    flow_parts.extend(path_tube([(0.0, 76.0, 42.0), (0.0, 116.0, 42.0)], [16.0, 19.5]))

    # Les conduits sont fusionnes en un unique noyau pour eviter des parois
    # artificielles aux jonctions en Y.
    print("F36: fusion du noyau fluide 4V", flush=True)
    flow_core = union(flow_parts)
    cutters.append(flow_core)

    for family in ("intake", "exhaust"):
        data = cfg[family]
        for centre in data["centres_mm"]:
            start, end = valve_axis(centre, data["tilt_y_deg"], 88.0)
            guide = cylinder_between(start - np.asarray([0.0, 0.0, 3.0]), end, data["stem_diameter_mm"] / 2.0 + 0.35, 48)
            cutters.append(guide)
            # Sur-epaisseur de siege usinee: le diametre de poche est distingue
            # du diametre de tete de soupape.
            seat_radius = data["head_diameter_mm"] / 2.0 + 1.6
            seat_end = start + (end - start) / np.linalg.norm(end - start) * 7.0
            cutters.append(cylinder_between(start - (seat_end - start) * 0.2, seat_end, seat_radius, 64))

    for centre in cfg["spark_plug"]["electrode_centres_mm"]:
        outward = math.copysign(13.0, centre[0])
        cutters.append(
            cylinder_between(
                np.asarray(centre, dtype=float) - np.asarray([0.0, 0.0, 5.0]),
                np.asarray([centre[0] + outward, centre[1], 82.0]),
                cfg["spark_plug"]["pilot_diameter_mm"] / 2.0,
                48,
            )
        )

    stud_points: list[list[float]] = []
    for item in interfaces["head_stud_holes_at_C_minus_91"]:
        x = float(item["center_A_B"][0]) - float(interfaces["combustion_interface"]["chamber_step"]["center"][0])
        y = float(item["center_A_B"][1]) - float(interfaces["combustion_interface"]["chamber_step"]["center"][1])
        radius = float(item["diameter_obj_units"]) / 2.0
        cutters.append(cylinder_between(np.asarray([x, y, -7.0]), np.asarray([x, y, 92.0]), radius, 48))
        stud_points.append([x, y])

    print("F36: booleenne voxel du noyau 4V dans la peau scan-conforme", flush=True)
    head, filled_stock = voxel_boolean_head(stock, cutters, pitch=0.75)
    head.remove_unreferenced_vertices()
    if not head.is_watertight or not head.is_winding_consistent:
        raise RuntimeError("le concept 4V apres booleens n'est pas etanche")

    # Controles de packaging analytiques sur les tetes et poches de sieges.
    intake = cfg["intake"]
    exhaust = cfg["exhaust"]
    intake_pair_gap = 2.0 * abs(intake["centres_mm"][0][0]) - intake["head_diameter_mm"]
    exhaust_pair_gap = 2.0 * abs(exhaust["centres_mm"][0][0]) - exhaust["head_diameter_mm"]
    bank_gap = abs(exhaust["centres_mm"][0][1] - intake["centres_mm"][0][1]) - 0.5 * (intake["head_diameter_mm"] + exhaust["head_diameter_mm"])
    chamber_clearance = min(
        cfg["chamber_diameter_mm"] / 2.0 - math.hypot(*centre[:2]) - data["head_diameter_mm"] / 2.0
        for data in (intake, exhaust)
        for centre in data["centres_mm"]
    )
    seat_pocket_clearance = min(
        cfg["chamber_diameter_mm"] / 2.0
        - math.hypot(*centre[:2])
        - (data["head_diameter_mm"] / 2.0 + 1.6)
        for data in (intake, exhaust)
        for centre in data["centres_mm"]
    )
    plug_to_seat_pocket_clearance = min(
        math.dist(centre[:2], plug[:2])
        - (data["head_diameter_mm"] / 2.0 + 1.6)
        - cfg["spark_plug"]["pilot_diameter_mm"] / 2.0
        for data in (intake, exhaust)
        for centre in data["centres_mm"]
        for plug in cfg["spark_plug"]["electrode_centres_mm"]
    )
    checks = {
        "intake_head_pair_gap_mm": intake_pair_gap,
        "exhaust_head_pair_gap_mm": exhaust_pair_gap,
        "same_column_intake_exhaust_head_gap_mm": bank_gap,
        "minimum_head_to_chamber_edge_gap_mm": chamber_clearance,
        "minimum_seat_pocket_to_chamber_edge_gap_mm": seat_pocket_clearance,
        "minimum_plug_pilot_to_seat_pocket_gap_mm": plug_to_seat_pocket_clearance,
        "stud_centres_local_mm": stud_points,
    }
    return head, filled_stock, flow_core, checks


def decimated(mesh: trimesh.Trimesh, target_faces: int, temporary: Path, name: str) -> trimesh.Trimesh:
    source = temporary / f"{name}-source.ply"
    output = temporary / f"{name}-reduced.ply"
    mesh.export(source)
    mesh_set = pymeshlab.MeshSet()
    mesh_set.load_new_mesh(str(source))
    mesh_set.apply_filter(
        "meshing_decimation_quadric_edge_collapse",
        targetfacenum=min(target_faces, len(mesh.faces)),
        preservetopology=True,
        preservenormal=True,
        optimalplacement=True,
    )
    mesh_set.save_current_mesh(str(output))
    return trimesh.load_mesh(output, process=True)


def add_mesh(axis, mesh: trimesh.Trimesh, color: str, alpha: float = 1.0, maximum_faces: int = 30_000) -> None:
    faces = mesh.faces
    normals = mesh.face_normals
    if len(faces) > maximum_faces:
        selection = np.linspace(0, len(faces) - 1, maximum_faces, dtype=int)
        faces = faces[selection]
        normals = normals[selection]
    triangles = mesh.vertices[faces]
    light = np.asarray([0.35, -0.48, 0.80], dtype=float)
    light /= np.linalg.norm(light)
    intensity = np.clip(0.28 + 0.72 * np.maximum(normals @ light, 0.0), 0.20, 1.0)
    base = np.asarray(to_rgb(color), dtype=float)
    facecolors = np.column_stack((intensity[:, None] * base[None, :], np.full(len(intensity), alpha)))
    collection = Poly3DCollection(triangles, facecolors=facecolors, edgecolor="none", linewidth=0.0)
    axis.add_collection3d(collection)


def set_view(axis, bounds: np.ndarray, elevation: float, azimuth: float, title: str) -> None:
    centre = bounds.mean(axis=0)
    span = np.ptp(bounds, axis=0)
    radius = 0.55 * max(span)
    axis.set_xlim(centre[0] - radius, centre[0] + radius)
    axis.set_ylim(centre[1] - radius, centre[1] + radius)
    axis.set_zlim(centre[2] - 0.45 * radius, centre[2] + 0.55 * radius)
    axis.set_box_aspect((1.0, 1.15, 0.75))
    axis.view_init(elev=elevation, azim=azimuth)
    axis.set_axis_off()
    axis.set_title(title, color="white", fontsize=12, fontweight="bold", pad=7)


def render(
    head: trimesh.Trimesh,
    stock: trimesh.Trimesh,
    flow: trimesh.Trimesh,
    cfg: dict,
    checks: dict,
    conformance: dict,
    wall: dict,
    output: Path,
) -> None:
    bounds = head.bounds
    figure = plt.figure(figsize=(16, 10), facecolor="#090f15")
    figure.suptitle(
        "F36 — reconstruction 4 soupapes contrainte par le scan 935",
        color="white",
        fontsize=21,
        fontweight="bold",
        y=0.975,
    )
    figure.text(
        0.5,
        0.94,
        "ENVELOPPE DU SCAN CONSERVEE · COEUR 4V NOUVEAU · PROTOTYPE D'ARCHITECTURE, PAS UNE DEFINITION MOTEUR",
        color="#ffca63",
        fontsize=10.5,
        ha="center",
        fontweight="bold",
    )

    external = figure.add_subplot(2, 2, 1, projection="3d", facecolor="#101b24")
    add_mesh(external, head, "#c3933e", 1.0, 40_000)
    set_view(external, bounds, 24.0, -52.0, "Reconstruction externe: ailettes et bossages du scan")

    overlay = figure.add_subplot(2, 2, 2, projection="3d", facecolor="#101b24")
    vertex_selection = np.linspace(0, len(stock.vertices) - 1, min(12_000, len(stock.vertices)), dtype=int)
    overlay.scatter(
        stock.vertices[vertex_selection, 0],
        stock.vertices[vertex_selection, 1],
        stock.vertices[vertex_selection, 2],
        s=0.25,
        color="#aeb8c1",
        alpha=0.32,
        depthshade=False,
    )
    add_mesh(overlay, head, "#d19a3d", 0.92, 40_000)
    set_view(overlay, bounds, 18.0, 132.0, "Superposition: peau reconstruite / concept usine")

    cutaway = figure.add_subplot(2, 2, 3, projection="3d", facecolor="#101b24")
    half = head.submesh([np.where(head.triangles_center[:, 0] <= 1.0)[0]], append=True, repair=False)
    add_mesh(cutaway, half, "#a87b35", 0.25, 40_000)
    flow_visible = trimesh.intersections.slice_mesh_plane(
        flow,
        plane_normal=np.asarray([0.0, 0.0, 1.0]),
        plane_origin=np.asarray([0.0, 0.0, -4.0]),
        cap=False,
    )
    intake_faces = np.where(flow_visible.triangles_center[:, 1] <= 0.0)[0]
    exhaust_faces = np.where(flow_visible.triangles_center[:, 1] > 0.0)[0]
    intake_visible = flow_visible.submesh([intake_faces], append=True, repair=False)
    exhaust_visible = flow_visible.submesh([exhaust_faces], append=True, repair=False)
    add_mesh(cutaway, intake_visible, "#3ea7d8", 0.68, 40_000)
    add_mesh(cutaway, exhaust_visible, "#ed7848", 0.68, 40_000)
    for family, colour in (("intake", "#67c9ff"), ("exhaust", "#ff8f5a")):
        data = cfg[family]
        for centre in data["centres_mm"]:
            start, end = valve_axis(centre, data["tilt_y_deg"], 80.0)
            direction = end - start
            direction /= np.linalg.norm(direction)
            basis_x = np.asarray([1.0, 0.0, 0.0])
            basis_side = np.cross(direction, basis_x)
            basis_side /= np.linalg.norm(basis_side)
            cutaway.plot([start[0], end[0]], [start[1], end[1]], [start[2], end[2]], color=colour, linewidth=2.2)
            theta = np.linspace(0.0, 2.0 * np.pi, 80)
            head_circle = (
                start[None, :]
                + 0.5 * data["head_diameter_mm"] * np.cos(theta)[:, None] * basis_x[None, :]
                + 0.5 * data["head_diameter_mm"] * np.sin(theta)[:, None] * basis_side[None, :]
            )
            cutaway.plot(head_circle[:, 0], head_circle[:, 1], head_circle[:, 2], color=colour, linewidth=1.4)
            turns = 7.5
            spring_t = np.linspace(0.0, 1.0, 260)
            spring_axis = start[None, :] + direction[None, :] * (52.0 + 27.0 * spring_t[:, None])
            spring_radius = 12.5 if family == "intake" else 11.5
            phase = 2.0 * np.pi * turns * spring_t
            spring = (
                spring_axis
                + spring_radius * np.cos(phase)[:, None] * basis_x[None, :]
                + spring_radius * np.sin(phase)[:, None] * basis_side[None, :]
            )
            cutaway.plot(spring[:, 0], spring[:, 1], spring[:, 2], color=colour, linewidth=0.9, alpha=0.9)
    for plug in cfg["spark_plug"]["electrode_centres_mm"]:
        outward = math.copysign(13.0, plug[0])
        cutaway.plot(
            [plug[0], plug[0] + outward],
            [plug[1], plug[1]],
            [-4.0, 82.0],
            color="#f3e6a4",
            linewidth=2.2,
        )
    set_view(cutaway, bounds, 5.0, 0.0, "Coupe Y/Z: conduits, axes de soupapes et ressorts")

    face = figure.add_subplot(2, 2, 4, projection="3d", facecolor="#101b24")
    chamber = plt.Circle((0, 0), cfg["chamber_diameter_mm"] / 2.0, fill=False, color="#d7dde3", linewidth=1.8)
    face.add_patch(chamber)
    from mpl_toolkits.mplot3d import art3d

    art3d.pathpatch_2d_to_3d(chamber, z=0.0, zdir="z")
    for family, colour in (("intake", "#67c9ff"), ("exhaust", "#ff8f5a")):
        data = cfg[family]
        for centre in data["centres_mm"]:
            theta = np.linspace(0.0, 2.0 * np.pi, 100)
            radius = data["head_diameter_mm"] / 2.0
            face.plot(centre[0] + radius * np.cos(theta), centre[1] + radius * np.sin(theta), np.zeros_like(theta), color=colour, linewidth=2.5)
    for x, y in checks["stud_centres_local_mm"]:
        face.scatter([x], [y], [0], s=70, facecolors="none", edgecolors="#e4d6b4", linewidths=1.5)
    for plug in cfg["spark_plug"]["electrode_centres_mm"]:
        face.scatter([plug[0]], [plug[1]], [0], s=45, color="#f3e6a4")
    set_view(face, np.asarray([[-55.0, -55.0, -5.0], [55.0, 55.0, 5.0]]), 90.0, -90.0, "Face de combustion: quatre soupapes dans le registre mesure")

    legend = [
        Line2D([0], [0], color="#67c9ff", lw=4, label="admission 31,5 mm"),
        Line2D([0], [0], color="#ff8f5a", lw=4, label="echappement 26,0 mm"),
        Line2D([0], [0], color="#f3e6a4", lw=4, label="double allumage M10"),
    ]
    figure.legend(handles=legend, loc="lower center", ncol=3, frameon=False, labelcolor="white", bbox_to_anchor=(0.5, 0.045))
    figure.text(
        0.5,
        0.020,
        f"registre {cfg['register_diameter_mm']:.2f} · chambre {cfg['chamber_diameter_mm']:.2f} · goujons {cfg['stud_pattern_mm'][0]:.2f} x {cfg['stud_pattern_mm'][1]:.2f} · ecart peau p95 {conformance['p95_obj_units']:.3f} · paroi echantillonnee min {wall['minimum_obj_units']:.2f} unites OBJ; echelle physique non confirmee",
        color="#d0d8df",
        fontsize=9.5,
        ha="center",
    )
    figure.subplots_adjust(left=0.02, right=0.98, bottom=0.085, top=0.91, wspace=0.02, hspace=0.04)
    figure.savefig(output, dpi=180, facecolor=figure.get_facecolor())
    plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scan", type=Path, required=True)
    parser.add_argument("--envelope", type=Path, required=True)
    parser.add_argument("--interfaces", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target-faces", type=int, default=150_000)
    args = parser.parse_args()

    if sha256(args.scan) != EXPECTED_SCAN_SHA256:
        raise SystemExit("l'empreinte du scan 935 ne correspond pas a la source attendue")
    interfaces = json.loads(args.interfaces.read_text(encoding="utf-8"))
    args.output.mkdir(parents=True, exist_ok=False)
    cfg = architecture()

    with tempfile.TemporaryDirectory(prefix="f36-scan-") as temporary_name:
        temporary = Path(temporary_name)
        print("F36: reconstruction Poisson de la peau scannee", flush=True)
        stock_scan = reconstruct_stock(args.envelope, temporary, args.target_faces)
        print(
            f"F36: peau reconstruite {len(stock_scan.faces)} triangles, "
            f"etanche={stock_scan.is_watertight}",
            flush=True,
        )
        conformance = scan_conformance(args.envelope, stock_scan)
        print(
            f"F36: ecart scan / peau reconstruite p95={conformance['p95_obj_units']:.4f} "
            f"unites OBJ",
            flush=True,
        )
        head, filled_stock, flow, checks = build_geometry(stock_scan, cfg, interfaces)
        wall = wall_screen(filled_stock, flow)
        print(
            f"F36: ecran paroi interne minimum echantillonne={wall['minimum_obj_units']:.3f} "
            "unites OBJ",
            flush=True,
        )
        head_preview = decimated(head, 30_000, temporary, "head-preview")
        stock_preview = decimated(filled_stock, 30_000, temporary, "stock-preview")
        flow_preview = decimated(flow, 12_000, temporary, "flow-preview")

        head_path = args.output / "917-head-scan-conforming-4v-f36.local.stl"
        stock_path = args.output / "917-head-scan-stock-f36.local.stl"
        flow_path = args.output / "917-head-4v-flow-core-f36.local.stl"
        image_path = args.output / "917-head-scan-conforming-4v-f36.png"
        head.export(head_path)
        filled_stock.export(stock_path)
        flow.export(flow_path)
        render(head_preview, stock_preview, flow_preview, cfg, checks, conformance, wall, image_path)

    report = {
        "schema_version": "1.0.0",
        "phase": PHASE,
        "status": "scan_conforming_four_valve_architecture_prototype_not_engine_release",
        "source": {
            "scan_sha256": EXPECTED_SCAN_SHA256,
            "raw_scan_committed": False,
            "derived_geometry_committed": False,
            "scale_confirmed": False,
        },
        "geometry": {
            "watertight": bool(head.is_watertight),
            "winding_consistent": bool(head.is_winding_consistent),
            "body_count": int(head.body_count),
            "vertices": int(len(head.vertices)),
            "triangles": int(len(head.faces)),
            "volume_cubic_obj_units": float(head.volume),
            "surface_area_square_obj_units": float(head.area),
            "bounds_local_obj_units": head.bounds.tolist(),
            "architecture": cfg,
            "packaging_checks": checks,
            "scan_surface_conformance": conformance,
            "internal_wall_screen": wall,
        },
        "files_local_only": {
            path.name: {"bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in (head_path, stock_path, flow_path, image_path)
        },
        "engineering_gates": {
            "automated_surface_conformance": bool(conformance["p95_screen_passed"]),
            "human_morphology_review": False,
            "morphology_review": False,
            "absolute_scale": False,
            "porsche_917_interfaces": False,
            "oil_galleries": False,
            "valvetrain_kinematics": False,
            "minimum_wall_ct_verified": False,
            "cht_converged": False,
            "thermomechanical_fatigue": False,
            "metal_print_authorized": False,
            "engine_start_authorized": False,
        },
    }
    report_path = args.output / "geometry-report.json"
    save_json(report_path, report)
    print(json.dumps({"status": report["status"], "report": str(report_path), "image": str(image_path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
