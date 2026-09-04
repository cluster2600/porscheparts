#!/usr/bin/env python3
"""Construit une preuve locale de maillage F37 à partir du solide F36.

Le script soustrait le noyau des galeries d'huile et ajoute quatre bossages
d'appui solidaires autour des goujons mesurés. Le STL résultant est une preuve
topologique locale : il ne constitue ni une CAO de production, ni une
autorisation LPBF.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import trimesh


HEAD_DENSITY_KG_M3 = 2670.0
BOOLEAN_ENGINE = "manifold"
ACCESS_PATH_SAMPLES = 241
PLANAR_FACE_Z_TOLERANCE_MM = 0.08
FLOW_DEBRIS_VOLUME_TOLERANCE_MM3 = 1.0e-9


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_mesh(path: Path, identifier: str) -> trimesh.Trimesh:
    loaded = trimesh.load(path, force="mesh", process=True)
    if not isinstance(loaded, trimesh.Trimesh) or len(loaded.faces) == 0:
        raise SystemExit(f"{identifier}: maillage absent ou vide")
    if not loaded.is_watertight or not loaded.is_winding_consistent:
        raise SystemExit(f"{identifier}: maillage non étanche ou orientation incohérente")
    if loaded.volume <= 0.0:
        loaded.invert()
    if loaded.volume <= 0.0:
        raise SystemExit(f"{identifier}: volume orienté non positif")
    return loaded


def load_flow_mesh(path: Path) -> tuple[trimesh.Trimesh, dict[str, Any]]:
    """Retire uniquement les composantes dégénérées d'aire/volume nuls.

    Le STL F36 connu contient deux triangles dégénérés séparés du domaine gaz.
    Le composant principal est fermé; le conserver est traçable et évite de
    rendre faussement la collision huile-gaz indécidable.
    """

    loaded = trimesh.load(path, force="mesh", process=True)
    if not isinstance(loaded, trimesh.Trimesh) or len(loaded.faces) == 0:
        raise SystemExit("flow_core: maillage absent ou vide")
    components = loaded.split(only_watertight=False)
    ordered = sorted(components, key=lambda item: abs(float(item.volume)), reverse=True)
    if not ordered or abs(float(ordered[0].volume)) <= 0.0:
        raise SystemExit("flow_core: aucune composante volumique")
    retained = ordered[0]
    if retained.volume <= 0.0:
        retained.invert()
    if not retained.is_watertight or not retained.is_winding_consistent or retained.volume <= 0.0:
        raise SystemExit("flow_core: composante volumique principale non étanche")
    discarded = ordered[1:]
    discarded_absolute_volume = float(sum(abs(float(item.volume)) for item in discarded))
    if discarded_absolute_volume > FLOW_DEBRIS_VOLUME_TOLERANCE_MM3:
        raise SystemExit(
            "flow_core: composante secondaire volumique refusée: "
            f"{discarded_absolute_volume:.12g} mm3"
        )
    return retained, {
        "method": "retain_largest_positive_watertight_component_discard_only_zero_volume_debris",
        "source_triangle_count": int(len(loaded.faces)),
        "retained_triangle_count": int(len(retained.faces)),
        "discarded_component_count": int(len(discarded)),
        "discarded_triangle_count": int(sum(len(item.faces) for item in discarded)),
        "discarded_absolute_volume_mm3": discarded_absolute_volume,
        "discarded_absolute_volume_tolerance_mm3": FLOW_DEBRIS_VOLUME_TOLERANCE_MM3,
    }


def require_single_mesh(result: Any, identifier: str) -> trimesh.Trimesh:
    if isinstance(result, trimesh.Scene):
        geometries = [geometry for geometry in result.geometry.values() if isinstance(geometry, trimesh.Trimesh)]
        result = trimesh.util.concatenate(geometries) if geometries else None
    if not isinstance(result, trimesh.Trimesh) or len(result.faces) == 0:
        raise RuntimeError(f"{identifier}: l'opération booléenne n'a pas produit de maillage")
    result.remove_unreferenced_vertices()
    result.merge_vertices()
    return result


def boolean_difference(subject: trimesh.Trimesh, cutters: list[trimesh.Trimesh], identifier: str) -> trimesh.Trimesh:
    result = trimesh.boolean.difference([subject, *cutters], engine=BOOLEAN_ENGINE, check_volume=True)
    return require_single_mesh(result, identifier)


def boolean_union(meshes: list[trimesh.Trimesh], identifier: str) -> trimesh.Trimesh:
    result = trimesh.boolean.union(meshes, engine=BOOLEAN_ENGINE, check_volume=True)
    return require_single_mesh(result, identifier)


def intersection_volume(first: trimesh.Trimesh, second: trimesh.Trimesh) -> tuple[float, str, dict[str, Any] | None]:
    """Retourne le volume commun, sans transformer une panne de calcul en succès."""

    try:
        result = trimesh.boolean.intersection([first, second], engine=BOOLEAN_ENGINE, check_volume=True)
    except Exception as exc:  # pragma: no cover - dépend de la géométrie d'entrée
        return math.nan, f"boolean_failed:{type(exc).__name__}", None
    if result is None or (isinstance(result, trimesh.Trimesh) and len(result.faces) == 0):
        return 0.0, "exact_manifold_boolean", None
    if isinstance(result, trimesh.Scene) and not result.geometry:
        return 0.0, "exact_manifold_boolean", None
    mesh = require_single_mesh(result, "intersection")
    return (
        abs(float(mesh.volume)),
        "exact_manifold_boolean",
        {
            "bounds_mm_if_scale_is_mm": np.asarray(mesh.bounds, dtype=float).tolist(),
            "centroid_mm_if_scale_is_mm": np.asarray(mesh.centroid, dtype=float).tolist(),
            "triangle_count": int(len(mesh.faces)),
        },
    )


def topology(mesh: trimesh.Trimesh) -> dict[str, Any]:
    components = mesh.split(only_watertight=False)
    return {
        "vertices": int(len(mesh.vertices)),
        "triangles": int(len(mesh.faces)),
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "body_count": int(len(components)),
        "euler_number": int(mesh.euler_number),
        "volume_mm3_if_scale_is_mm": abs(float(mesh.volume)),
        "surface_area_mm2_if_scale_is_mm": float(mesh.area),
        "bounds_mm_if_scale_is_mm": np.asarray(mesh.bounds, dtype=float).tolist(),
    }


def strict_vertex_manifold_audit(mesh: trimesh.Trimesh) -> dict[str, Any]:
    """Vérifie que le lien de chaque sommet est un unique cycle fermé.

    Deux nappes peuvent se toucher en un sommet tout en gardant deux faces par
    arête. Le test watertight classique ne détecte pas ce sommet « bow-tie »;
    le lien de faces incidentes, lui, possède alors plusieurs composantes.
    """

    faces = np.asarray(mesh.faces, dtype=np.int64)
    vertex_ids = faces.reshape(-1)
    face_ids = np.repeat(np.arange(len(faces), dtype=np.int64), 3)
    order = np.argsort(vertex_ids, kind="stable")
    sorted_vertices = vertex_ids[order]
    sorted_faces = face_ids[order]
    counts = np.bincount(sorted_vertices, minlength=len(mesh.vertices))
    offsets = np.concatenate(([0], np.cumsum(counts)))
    non_manifold: list[dict[str, Any]] = []
    non_manifold_count = 0
    maximum_fan_count = 1

    for vertex in np.flatnonzero(counts):
        incident = sorted_faces[offsets[vertex] : offsets[vertex + 1]]
        link: dict[int, set[int]] = {}
        for face_id in incident:
            other = faces[face_id][faces[face_id] != vertex]
            if len(other) != 2 or other[0] == other[1]:
                link = {}
                break
            first, second = int(other[0]), int(other[1])
            link.setdefault(first, set()).add(second)
            link.setdefault(second, set()).add(first)

        degree_two = bool(link) and all(len(neighbours) == 2 for neighbours in link.values())
        unseen = set(link)
        fan_count = 0
        while unseen:
            fan_count += 1
            stack = [unseen.pop()]
            while stack:
                current = stack.pop()
                for neighbour in link[current]:
                    if neighbour in unseen:
                        unseen.remove(neighbour)
                        stack.append(neighbour)
        manifold = bool(degree_two and fan_count == 1 and len(link) == len(incident))
        if not manifold:
            non_manifold_count += 1
            maximum_fan_count = max(maximum_fan_count, fan_count)
            if len(non_manifold) < 32:
                non_manifold.append(
                    {
                        "vertex_index": int(vertex),
                        "coordinate_mm_if_scale_is_mm": np.asarray(mesh.vertices[vertex], dtype=float).tolist(),
                        "incident_face_count": int(len(incident)),
                        "link_vertex_count": int(len(link)),
                        "link_fan_count": int(fan_count),
                        "all_link_degrees_two": degree_two,
                    }
                )

    return {
        "method": "closed_vertex_link_must_be_one_connected_cycle",
        "vertex_count": int(len(mesh.vertices)),
        "strict_vertex_manifold": non_manifold_count == 0,
        "non_manifold_vertex_count": int(non_manifold_count),
        "maximum_link_fan_count": int(maximum_fan_count),
        "sample_non_manifold_vertices": non_manifold,
    }


def nvidia_asset_validator_observation(
    output_stl: Path, non_manifold_vertex_count: int | None, evidence: Path | None
) -> dict[str, Any]:
    """Consigne un résultat VG.007 externe sans le confondre avec l'audit local.

    Les deux outils n'emploient manifestement pas la même définition ou le
    même prétraitement des sommets. En cas d'absence de preuve NVIDIA, ce gate
    reste fermé; en cas de divergence, le verdict le plus conservateur gagne.
    """

    observation: dict[str, Any] = {
        "tool": "NVIDIA Asset Validator",
        "rule": "VG.007",
        "exact_stl_sha256": sha256(output_stl),
        "status": "not_run",
        "non_manifold_vertex_count": None,
        "vg007_clear": False,
        "evidence": None,
    }
    if non_manifold_vertex_count is None:
        observation["interpretation"] = "Validation NVIDIA absente; gate fermé par défaut."
        return observation
    if non_manifold_vertex_count < 0:
        raise SystemExit("le nombre de sommets VG.007 ne peut pas être négatif")
    observation["status"] = "pass" if non_manifold_vertex_count == 0 else "warning"
    observation["non_manifold_vertex_count"] = int(non_manifold_vertex_count)
    observation["vg007_clear"] = non_manifold_vertex_count == 0
    if evidence is not None:
        if not evidence.is_file():
            raise SystemExit(f"preuve NVIDIA absente: {evidence}")
        observation["evidence"] = {
            "path": evidence.as_posix(),
            "bytes": evidence.stat().st_size,
            "sha256": sha256(evidence),
        }
    observation["interpretation"] = (
        "Aucun avertissement VG.007 sur le STL exact."
        if non_manifold_vertex_count == 0
        else "VG.007 signale des sommets non-manifold; impression bloquée malgré l'audit local."
    )
    return observation


def create_head_pads(
    geometry_report: dict[str, Any], contract: dict[str, Any], head: trimesh.Trimesh
) -> tuple[list[trimesh.Trimesh], list[trimesh.Trimesh], list[list[float]], float, float, float]:
    centres = geometry_report["geometry"]["packaging_checks"]["stud_centres_local_mm"]
    carrier = contract["rocker_carrier"]
    radius = float(carrier["head_mount_pad_outer_diameter_mm"]) / 2.0
    plane_z = float(carrier["mount_interface_z_mm"])
    foundation_z = float(carrier["head_mount_pad_foundation_z_mm"])
    height = plane_z - foundation_z
    bore_radius = float(carrier["mount_final_clearance_diameter_mm"]) / 2.0
    pads: list[trimesh.Trimesh] = []
    bores: list[trimesh.Trimesh] = []
    for x, y in centres:
        pad = trimesh.creation.cylinder(radius=radius, height=height, sections=96)
        pad.apply_translation([float(x), float(y), foundation_z + height / 2.0])
        pads.append(pad)
        bore = trimesh.creation.cylinder(radius=bore_radius, height=height + 4.0, sections=96)
        bore.apply_translation([float(x), float(y), foundation_z - 2.0 + (height + 4.0) / 2.0])
        bores.append(bore)
    return pads, bores, [[float(x), float(y)] for x, y in centres], radius, plane_z, foundation_z


def access_paths(contract: dict[str, Any]) -> list[dict[str, Any]]:
    oil = contract["oil_system"]
    feed = oil["head_feed_lateral"]
    header = oil["head_header"]
    drains = oil["return_drains"]
    paths = [
        {
            "id": "feed_from_intake_fin_side",
            "start_mm": [feed["x_mm"], feed["y_range_mm"][0], feed["z_mm"]],
            "end_mm": [feed["x_mm"], feed["y_range_mm"][1], feed["z_mm"]],
            "diameter_mm": feed["diameter_mm"],
            "required_outside_end": "start",
        },
        {
            "id": "header_left_plug",
            "start_mm": [header["x_range_mm"][0], header["y_mm"], header["z_mm"]],
            "end_mm": [0.0, header["y_mm"], header["z_mm"]],
            "diameter_mm": header["diameter_mm"],
            "required_outside_end": "start",
        },
        {
            "id": "header_right_plug",
            "start_mm": [header["x_range_mm"][1], header["y_mm"], header["z_mm"]],
            "end_mm": [0.0, header["y_mm"], header["z_mm"]],
            "diameter_mm": header["diameter_mm"],
            "required_outside_end": "start",
        },
    ]
    for index, x in enumerate(drains["x_mm"], start=1):
        paths.append(
            {
                "id": f"return_drain_{index}_lateral_outlet",
                "start_mm": [x, drains["lateral_outlet_y_range_mm"][0], drains["lateral_outlet_z_mm"]],
                "end_mm": [x, drains["lateral_outlet_y_range_mm"][1], drains["lateral_outlet_z_mm"]],
                "diameter_mm": drains["diameter_mm"],
                "required_outside_end": "start",
            }
        )
    return paths


def audit_access_path(head: trimesh.Trimesh, path: dict[str, Any]) -> dict[str, Any]:
    start = np.asarray(path["start_mm"], dtype=float)
    end = np.asarray(path["end_mm"], dtype=float)
    parameters = np.linspace(0.0, 1.0, ACCESS_PATH_SAMPLES)
    points = start[None, :] + parameters[:, None] * (end - start)[None, :]
    inside = np.asarray(head.contains(points), dtype=bool)
    transitions = np.flatnonzero(inside[1:] != inside[:-1]) + 1
    transition_points = points[transitions]
    outside_start = not bool(inside[0])
    outside_end = not bool(inside[-1])
    intersects_parent_material = bool(np.any(inside))
    required_outside = outside_start if path["required_outside_end"] == "start" else outside_end
    # Un accès est prouvé seulement si son axe part de l'extérieur, entre dans
    # le métal parent et franchit donc au moins une fois la peau avant usinage.
    skin_opening_proved = bool(required_outside and intersects_parent_material and len(transitions) >= 1)
    return {
        **path,
        "method": "sampled_parent_solid_contains_along_declared_straight_axis",
        "sample_count": ACCESS_PATH_SAMPLES,
        "outside_at_start": outside_start,
        "outside_at_end": outside_end,
        "inside_sample_count": int(np.count_nonzero(inside)),
        "parent_skin_transition_count": int(len(transitions)),
        "first_transition_mm": transition_points[0].tolist() if len(transition_points) else None,
        "last_transition_mm": transition_points[-1].tolist() if len(transition_points) else None,
        "skin_opening_proved": skin_opening_proved,
        "limitations": "axe central échantillonné; ne remplace pas contrôle CMM/CT ni tolérance réelle du perçage",
    }


def audit_planar_pads(
    mesh: trimesh.Trimesh, centres: list[list[float]], radius: float, plane_z: float
) -> list[dict[str, Any]]:
    centres_faces = np.asarray(mesh.triangles_center, dtype=float)
    normals = np.asarray(mesh.face_normals, dtype=float)
    areas = np.asarray(mesh.area_faces, dtype=float)
    reports: list[dict[str, Any]] = []
    for index, (x, y) in enumerate(centres, start=1):
        radial = np.hypot(centres_faces[:, 0] - x, centres_faces[:, 1] - y)
        mask = (
            (np.abs(centres_faces[:, 2] - plane_z) <= PLANAR_FACE_Z_TOLERANCE_MM)
            & (normals[:, 2] >= 0.98)
            & (radial <= radius + 0.2)
        )
        area = float(areas[mask].sum())
        reports.append(
            {
                "id": f"stud_pad_{index}",
                "centre_xy_mm": [x, y],
                "target_plane_z_mm": plane_z,
                "cutter_radius_mm": radius,
                "detected_upward_planar_area_mm2": area,
                "planar_face_count": int(np.count_nonzero(mask)),
                "planar_surface_detected": area >= 10.0,
            }
        )
    return reports


def sampled_oil_to_gas_clearance(
    flow: trimesh.Trimesh, oil: trimesh.Trimesh, sample_count: int = 4000
) -> dict[str, Any]:
    """Écran de distance entre noyaux, distinct d'une épaisseur de paroi CT."""

    points, _ = trimesh.sample.sample_surface(oil, sample_count, seed=1937)
    _, distances, _ = trimesh.proximity.closest_point(flow, points)
    distances = np.asarray(distances, dtype=float)
    finite = distances[np.isfinite(distances)]
    if len(finite) == 0:
        return {
            "method": "sampled_nearest_surface_distance_oil_core_to_gas_flow_core",
            "sample_count": 0,
            "minimum_mm_if_scale_is_mm": None,
            "p01_mm_if_scale_is_mm": None,
            "ct_verified": False,
            "valid_for_release": False,
        }
    return {
        "method": "sampled_nearest_surface_distance_oil_core_to_gas_flow_core_not_true_wall_thickness",
        "sample_count": int(len(finite)),
        "minimum_mm_if_scale_is_mm": float(np.min(finite)),
        "p01_mm_if_scale_is_mm": float(np.quantile(finite, 0.01)),
        "p05_mm_if_scale_is_mm": float(np.quantile(finite, 0.05)),
        "median_mm_if_scale_is_mm": float(np.median(finite)),
        "ct_verified": False,
        "valid_for_release": False,
        "limitations": "distance euclidienne entre noyaux, incluant leurs portions hors solide; ne mesure pas l'épaisseur locale du métal",
    }


def add_mesh(
    axis: Any,
    mesh: trimesh.Trimesh,
    color: str,
    alpha: float,
    maximum_faces: int,
) -> None:
    if len(mesh.faces) > maximum_faces:
        keep = np.linspace(0, len(mesh.faces) - 1, maximum_faces, dtype=int)
    else:
        keep = np.arange(len(mesh.faces), dtype=int)
    triangles = mesh.vertices[mesh.faces[keep]]
    rgba = (*to_rgb(color), alpha)
    axis.add_collection3d(Poly3DCollection(triangles, facecolor=rgba, edgecolor="none"))


def render(
    final_head: trimesh.Trimesh,
    oil: trimesh.Trimesh,
    head_pads: list[trimesh.Trimesh],
    report: dict[str, Any],
    output: Path,
) -> None:
    figure = plt.figure(figsize=(16, 9), facecolor="#081018")
    figure.suptitle(
        "F37 — preuve locale du maillage de culasse avec huile et plans d'appui",
        color="white",
        fontsize=18,
        fontweight="bold",
        y=0.975,
    )
    views = ((23.0, -52.0, "Solide résultant + noyau huile"), (74.0, -90.0, "Vue supérieure des quatre appuis"))
    for position, (elev, azim, title) in enumerate(views, start=1):
        axis = figure.add_subplot(1, 3, position, projection="3d", facecolor="#101c25")
        add_mesh(axis, final_head, "#b88943", 0.86, 70000)
        add_mesh(axis, oil, "#f04f54", 0.50, 24000)
        for pad in head_pads:
            add_mesh(axis, pad, "#53d8d1", 0.35, 1500)
        centre = final_head.bounds.mean(axis=0)
        radius = float(max(final_head.extents)) * 0.57
        axis.set_xlim(centre[0] - radius, centre[0] + radius)
        axis.set_ylim(centre[1] - radius, centre[1] + radius)
        axis.set_zlim(centre[2] - 0.55 * radius, centre[2] + 0.55 * radius)
        axis.set_box_aspect((1.0, 1.0, 0.8))
        axis.view_init(elev=elev, azim=azim)
        axis.set_axis_off()
        axis.set_title(title, color="white", fontsize=11, fontweight="bold")

    table = figure.add_subplot(1, 3, 3, facecolor="#101c25")
    table.axis("off")
    topo = report["result"]
    collision = report["oil_to_gas_flow_collision"]
    gates = report["gates"]
    access_passes = sum(item["skin_opening_proved"] for item in report["oil_access_openings"])
    pad_passes = sum(item["planar_surface_detected"] for item in report["mount_pad_planes"])
    rows = [
        ("Triangles", f"{topo['triangles']:,}".replace(",", " ")),
        ("Étanche / corps", f"{topo['watertight']} / {topo['body_count']}"),
        ("Volume final", f"{topo['volume_mm3_if_scale_is_mm'] / 1000.0:.2f} cm³"),
        ("Masse candidate", f"{report['candidate_mass_kg_if_scale_is_mm']:.3f} kg"),
        ("Huile retirée", f"{report['volume_change']['oil_removed_mm3'] / 1000.0:.2f} cm³"),
        ("Pads ajoutés", f"{report['volume_change']['net_four_integral_mount_pads_added_mm3'] / 1000.0:.2f} cm³"),
        ("Huile ↔ gaz", f"{collision['volume_mm3']:.4f} mm³" if collision["calculation_succeeded"] else "calcul échoué"),
        ("Débouchés prouvés", f"{access_passes}/{len(report['oil_access_openings'])}"),
        ("Plans d'appui", f"{pad_passes}/{len(report['mount_pad_planes'])}"),
        ("Audit local non-manifold", str(report["strict_vertex_manifold_audit"]["non_manifold_vertex_count"])),
        (
            "NVIDIA VG.007",
            (
                str(report["nvidia_asset_validator_observation"]["non_manifold_vertex_count"])
                if report["nvidia_asset_validator_observation"]["non_manifold_vertex_count"] is not None
                else "NON EXÉCUTÉ"
            ),
        ),
        ("Consensus validateurs", str(gates["independent_topology_validators_agree"])),
        ("Étanche mono-corps", str(gates["watertight_single_body_topology_only"])),
        ("Redessin requis", str(gates["geometry_redesign_required"])),
        ("Impression métal", "NON AUTORISÉE"),
    ]
    y = 0.95
    for label, value in rows:
        table.text(0.04, y, label, color="#9db0bc", fontsize=10.5, transform=table.transAxes)
        table.text(0.53, y, value, color="white", fontsize=10.5, fontweight="bold", transform=table.transAxes)
        y -= 0.048
    table.text(
        0.04,
        0.015,
        "Or = maillage F37  •  Rouge = volume des galeries  •  Cyan = bossages d'appui\n"
        "La topologie calculée ne valide ni l'échelle, ni la matière à chaud, ni le procédé LPBF.\n"
        "Une divergence locale/NVIDIA bloque explicitement l'impression.",
        color="#f2c465",
        fontsize=9.2,
        wrap=True,
        transform=table.transAxes,
    )
    figure.subplots_adjust(left=0.012, right=0.988, bottom=0.04, top=0.91, wspace=0.025)
    figure.savefig(output, dpi=180, facecolor=figure.get_facecolor())
    plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--head", type=Path, required=True)
    parser.add_argument("--flow-core", type=Path, required=True)
    parser.add_argument("--oil-core", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--geometry-report", type=Path, required=True)
    parser.add_argument("--cad-report", type=Path, required=True)
    parser.add_argument(
        "--nvidia-vg007-non-manifold-vertices",
        type=int,
        help="Nombre VG.007 mesuré par NVIDIA Asset Validator sur le STL final exact.",
    )
    parser.add_argument(
        "--nvidia-validation-evidence",
        type=Path,
        help="Rapport ou journal NVIDIA optionnel dont le SHA-256 sera consigné.",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=False)
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    geometry_report = json.loads(args.geometry_report.read_text(encoding="utf-8"))
    cad_report = json.loads(args.cad_report.read_text(encoding="utf-8"))

    head_hash = sha256(args.head)
    if head_hash != contract["parent"]["head_sha256"]:
        raise SystemExit("le hash du solide F36 ne correspond pas au contrat F37")
    if head_hash != cad_report["inputs"]["parent_head_sha256"]:
        raise SystemExit("le rapport CAO ne référence pas le solide F36 fourni")
    if sha256(args.contract) != cad_report["inputs"]["contract_sha256"]:
        raise SystemExit("le rapport CAO ne référence pas le contrat F37 fourni")
    if sha256(args.geometry_report) != cad_report["inputs"]["geometry_report_sha256"]:
        raise SystemExit("le rapport CAO ne référence pas le rapport géométrique fourni")
    expected_flow = geometry_report["files_local_only"][
        "917-head-4v-flow-core-f36.local.stl"
    ]
    if sha256(args.flow_core) != expected_flow["sha256"]:
        raise SystemExit("le noyau gaz ne correspond pas au rapport géométrique F36")
    if args.flow_core.stat().st_size != int(expected_flow["bytes"]):
        raise SystemExit("la taille du noyau gaz ne correspond pas au rapport géométrique F36")
    oil_artifact = next(item for item in cad_report["artifacts"] if item["id"] == "oil-gallery-core")
    if sha256(args.oil_core) != oil_artifact["stl"]["sha256"]:
        raise SystemExit("le noyau huile ne correspond pas au rapport CAO F37")

    head = load_mesh(args.head, "head")
    flow, flow_input_processing = load_flow_mesh(args.flow_core)
    oil = load_mesh(args.oil_core, "oil_core")
    head_pads, stud_bores, stud_centres, pad_radius, pad_plane_z, pad_foundation_z = create_head_pads(
        geometry_report, contract, head
    )

    oil_flow_volume, oil_flow_method, oil_flow_location = intersection_volume(oil, flow)
    head_with_pads = boolean_union([head, *head_pads], "union bossages d'appui")
    head_with_pads_and_bores = boolean_difference(head_with_pads, stud_bores, "rétablissement alésages goujons")
    final_head = boolean_difference(head_with_pads_and_bores, [oil], "soustraction huile")
    initial_topology = topology(head)
    pad_topology = topology(head_with_pads_and_bores)
    final_topology = topology(final_head)

    net_pad_added = max(0.0, pad_topology["volume_mm3_if_scale_is_mm"] - initial_topology["volume_mm3_if_scale_is_mm"])
    oil_removed = max(0.0, pad_topology["volume_mm3_if_scale_is_mm"] - final_topology["volume_mm3_if_scale_is_mm"])
    openings = [audit_access_path(head, path) for path in access_paths(contract)]
    pads = audit_planar_pads(final_head, stud_centres, pad_radius, pad_plane_z)
    wall_screen = sampled_oil_to_gas_clearance(flow, oil)

    flow_collision_succeeded = math.isfinite(oil_flow_volume)
    all_openings = all(item["skin_opening_proved"] for item in openings)
    all_pads = all(item["planar_surface_detected"] for item in pads)
    no_oil_gas_collision = bool(flow_collision_succeeded and oil_flow_volume <= 0.01)

    output_stl = args.output / "917-head-f37-printable-proof.local.stl"
    output_report = args.output / "f37-printable-head-mesh-report.json"
    output_png = args.output / "917-head-f37-printable-proof.png"
    final_head.export(output_stl)
    exported_head = load_mesh(output_stl, "exported_head")
    final_topology = topology(exported_head)
    topology_printable = bool(
        final_topology["watertight"]
        and final_topology["winding_consistent"]
        and final_topology["body_count"] == 1
        and final_topology["volume_mm3_if_scale_is_mm"] > 0.0
    )
    vertex_manifold = strict_vertex_manifold_audit(exported_head)
    local_vertex_ok = bool(vertex_manifold["strict_vertex_manifold"])
    nvidia_validator = nvidia_asset_validator_observation(
        output_stl,
        args.nvidia_vg007_non_manifold_vertices,
        args.nvidia_validation_evidence,
    )
    independent_validators_agree = bool(local_vertex_ok and nvidia_validator["vg007_clear"])

    report: dict[str, Any] = {
        "schema_version": "1.0.0",
        "phase": "F37",
        "status": "local_mesh_boolean_proof_complete_physical_and_manufacturing_release_blocked",
        "classification": "scan_derived_triangle_mesh_with_oil_and_integral_mount_pads_not_production_brep",
        "inputs": {
            "head": {"path": args.head.name, "sha256": head_hash},
            "flow_core": {"path": args.flow_core.name, "sha256": sha256(args.flow_core)},
            "oil_core": {"path": args.oil_core.name, "sha256": sha256(args.oil_core)},
            "contract_sha256": sha256(args.contract),
            "geometry_report_sha256": sha256(args.geometry_report),
            "cad_report_sha256": sha256(args.cad_report),
            "scale_confirmed": bool(geometry_report["source"]["scale_confirmed"]),
        },
        "method": {
            "boolean_engine": BOOLEAN_ENGINE,
            "oil_operation": "exact triangle boolean difference",
            "mount_operation": "union of four integral cylindrical head pads followed by restoration of measured stud bores",
            "mount_interface_z_mm_if_scale_is_mm": pad_plane_z,
            "mount_pad_foundation_z_mm_if_scale_is_mm": pad_foundation_z,
            "mount_pad_radius_mm_if_scale_is_mm": pad_radius,
            "mount_centres_mm_if_scale_is_mm": stud_centres,
            "flow_input_processing": flow_input_processing,
        },
        "parent": initial_topology,
        "head_with_integral_mount_pads_and_stud_bores": pad_topology,
        "result": final_topology,
        "strict_vertex_manifold_audit": vertex_manifold,
        "nvidia_asset_validator_observation": nvidia_validator,
        "volume_change": {"net_four_integral_mount_pads_added_mm3": net_pad_added, "oil_removed_mm3": oil_removed},
        "candidate_mass_kg_if_scale_is_mm": final_topology["volume_mm3_if_scale_is_mm"] * HEAD_DENSITY_KG_M3 * 1.0e-9,
        "oil_to_gas_flow_collision": {
            "method": oil_flow_method,
            "calculation_succeeded": flow_collision_succeeded,
            "volume_mm3": oil_flow_volume if flow_collision_succeeded else None,
            "screen_limit_mm3": 0.01,
            "screen_passed": no_oil_gas_collision,
            "intersection_location": oil_flow_location,
        },
        "oil_access_openings": openings,
        "mount_pad_planes": pads,
        "oil_to_gas_clearance_screen": wall_screen,
        "gates": {
            "watertight_single_body_topology_only": topology_printable,
            "strict_vertex_manifold_local_algorithm_only": local_vertex_ok,
            "nvidia_asset_validator_vg007_clear": bool(nvidia_validator["vg007_clear"]),
            "independent_topology_validators_agree": independent_validators_agree,
            "geometry_redesign_required": not (
                all_openings and all_pads and no_oil_gas_collision and independent_validators_agree
            ),
            "metal_printability_demonstrated": False,
            "oil_boolean_removed_parent_material": oil_removed > 1.0,
            "all_declared_accesses_cross_parent_skin": all_openings,
            "all_four_mount_planes_detected": all_pads,
            "oil_to_gas_flow_collision_absent": no_oil_gas_collision,
            "absolute_scale_confirmed": False,
            "whole_head_production_brep": False,
            "minimum_wall_ct_verified": False,
            "machining_setup_and_tolerances_validated": False,
            "lpbf_machine_parameter_set_qualified": False,
            "metal_print_authorized": False,
            "engine_start_authorized": False,
        },
        "limitations": [
            "Le parent est un maillage triangulé dérivé d'un scan dont l'échelle absolue n'est pas confirmée.",
            "La soustraction exacte prouve la topologie du maillage, pas une reconstruction NURBS/B-Rep de production.",
            "Le contrôle de paroi près de l'huile est une distance de peau échantillonnée, pas une mesure CT d'épaisseur.",
            "Les plans d'appui, axes de perçage et débouchés exigent encore CMM/CT, gamme d'usinage et contrôle physique.",
            "Aucune carte matière LPBF à chaud, aucun jeu de paramètres machine ni essai coupon n'est qualifié.",
            "L'audit local du lien de sommet et NVIDIA Asset Validator VG.007 divergent; le résultat NVIDIA conservateur bloque l'impression jusqu'au remaillage et à une contre-validation convergente.",
        ],
        "local_only_artifacts": {
            output_stl.name: {"bytes": output_stl.stat().st_size, "sha256": sha256(output_stl)},
            output_png.name: None,
        },
    }
    save_json(output_report, report)
    render(exported_head, oil, head_pads, report, output_png)
    report["local_only_artifacts"][output_png.name] = {"bytes": output_png.stat().st_size, "sha256": sha256(output_png)}
    save_json(output_report, report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
