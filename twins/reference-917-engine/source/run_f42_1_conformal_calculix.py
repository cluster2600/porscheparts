#!/usr/bin/env python3
"""Maillage tetra conforme et ecran thermo-mecanique CalculiX F42.1.

Le STL d'entree reste prive. Le rapport public ne contient que des agregats,
des empreintes cryptographiques et des portes de validation fail-closed.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
from typing import Any

import numpy as np


CHAMBER_CENTER_MM = np.asarray([0.6807746887, -13.5726814270, -107.0])
CHAMBER_RADIUS_MM = 80.0
STUD_AXES_XY_MM = np.asarray(
    [
        [-42.66824085, 29.33066475],
        [-42.16637457, -56.35998334],
        [43.78105643, 29.55585441],
        [44.07452915, -56.01732087],
    ]
)
STUD_BORE_RADIUS_MM = 5.05
CHAMBER_RADIAL_TOLERANCE_MM = 1.0
CHAMBER_NORMAL_ALIGNMENT_MINIMUM = 0.80
STUD_RADIAL_TOLERANCE_MM = 0.50
STUD_NORMAL_ALIGNMENT_MINIMUM = 0.60
SUPPORT_SINGULARITY_EXCLUSION_RADIUS_MM = 15.0

# CalculiX/Abaqus C3D4 face labels. Indices refer to the local node order.
C3D4_FACE_NODE_INDICES: dict[int, tuple[int, int, int]] = {
    1: (0, 1, 2),
    2: (0, 3, 1),
    3: (1, 3, 2),
    4: (2, 3, 0),
}


class F421Error(RuntimeError):
    """Erreur controlee de la chaine F42.1."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_ids(stream: Any, kind: str, name: str, values: Iterable[int]) -> None:
    values = sorted(set(int(value) for value in values))
    if not values:
        raise F421Error(f"empty_{kind.lower()}:{name}")
    stream.write(f"*{kind},{kind}={name}\n")
    for start in range(0, len(values), 16):
        stream.write(",".join(str(value) for value in values[start : start + 16]) + "\n")


def relative_difference(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or not math.isfinite(a) or not math.isfinite(b):
        return None
    return abs(a - b) / max(abs(a), abs(b), 1.0e-30)


def von_mises(components: Iterable[float]) -> float:
    sxx, syy, szz, sxy, sxz, syz = components
    return math.sqrt(
        0.5
        * (
            (sxx - syy) ** 2
            + (syy - szz) ** 2
            + (szz - sxx) ** 2
            + 6.0 * (sxy * sxy + sxz * sxz + syz * syz)
        )
    )


def c3d4_boundary_faces(
    tetra_node_tags: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, int]]:
    """Retourne faces frontiere, index proprietaire et label C3D4.

    Le tri vectorise evite un dictionnaire Python de plusieurs millions de
    faces. Une face interieure doit appartenir a exactement deux tetraedres.
    """

    if tetra_node_tags.ndim != 2 or tetra_node_tags.shape[1] != 4:
        raise F421Error("invalid_c3d4_connectivity_shape")
    count = tetra_node_tags.shape[0]
    raw_faces = np.concatenate(
        [tetra_node_tags[:, C3D4_FACE_NODE_INDICES[label]] for label in range(1, 5)],
        axis=0,
    )
    sorted_faces = np.sort(raw_faces, axis=1)
    owners = np.tile(np.arange(count, dtype=np.int64), 4)
    labels = np.repeat(np.arange(1, 5, dtype=np.int8), count)
    order = np.lexsort((sorted_faces[:, 2], sorted_faces[:, 1], sorted_faces[:, 0]))
    ordered = sorted_faces[order]
    run_start = np.concatenate(
        ([0], np.flatnonzero(np.any(ordered[1:] != ordered[:-1], axis=1)) + 1)
    )
    run_end = np.concatenate((run_start[1:], [len(ordered)]))
    multiplicity = run_end - run_start
    nonmanifold = int(np.count_nonzero(multiplicity > 2))
    if nonmanifold:
        raise F421Error(f"nonmanifold_tetra_faces:{nonmanifold}")
    boundary_positions = run_start[multiplicity == 1]
    raw_positions = order[boundary_positions]
    metrics = {
        "boundary_faces": int(len(boundary_positions)),
        "interior_faces": int(np.count_nonzero(multiplicity == 2)),
        "nonmanifold_faces": nonmanifold,
    }
    return (
        sorted_faces[raw_positions],
        owners[raw_positions],
        labels[raw_positions],
        metrics,
    )


def outward_face_geometry(
    node_tags: np.ndarray,
    node_xyz: np.ndarray,
    tetra_node_tags: np.ndarray,
    faces: np.ndarray,
    owners: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    positions = np.searchsorted(node_tags, faces)
    if np.any(node_tags[positions] != faces):
        raise F421Error("boundary_face_references_unknown_node")
    points = node_xyz[positions]
    centroids = np.mean(points, axis=1)
    normals = np.cross(points[:, 1] - points[:, 0], points[:, 2] - points[:, 0])
    magnitudes = np.linalg.norm(normals, axis=1)
    if np.any(magnitudes <= 1.0e-14):
        raise F421Error("zero_area_boundary_face")
    normals /= magnitudes[:, None]
    owner_positions = np.searchsorted(node_tags, tetra_node_tags[owners])
    tetra_centroids = np.mean(node_xyz[owner_positions], axis=1)
    points_to_interior = np.einsum("ij,ij->i", normals, tetra_centroids - centroids)
    normals[points_to_interior > 0.0] *= -1.0
    areas = 0.5 * magnitudes
    return centroids, normals, areas


def classify_boundary_faces(
    centroids: np.ndarray,
    normals: np.ndarray,
) -> tuple[np.ndarray, list[np.ndarray]]:
    chamber_vector = CHAMBER_CENTER_MM - centroids
    chamber_distance = np.linalg.norm(chamber_vector, axis=1)
    chamber_direction = chamber_vector / np.maximum(chamber_distance[:, None], 1.0e-30)
    chamber_alignment = np.einsum("ij,ij->i", normals, chamber_direction)
    chamber = (
        (np.abs(chamber_distance - CHAMBER_RADIUS_MM) <= CHAMBER_RADIAL_TOLERANCE_MM)
        & (chamber_alignment >= CHAMBER_NORMAL_ALIGNMENT_MINIMUM)
    )
    studs: list[np.ndarray] = []
    for axis in STUD_AXES_XY_MM:
        radial = axis - centroids[:, :2]
        distance = np.linalg.norm(radial, axis=1)
        direction = np.zeros_like(centroids)
        direction[:, :2] = radial / np.maximum(distance[:, None], 1.0e-30)
        alignment = np.einsum("ij,ij->i", normals, direction)
        studs.append(
            (np.abs(distance - STUD_BORE_RADIUS_MM) <= STUD_RADIAL_TOLERANCE_MM)
            & (alignment >= STUD_NORMAL_ALIGNMENT_MINIMUM)
        )
    return chamber, studs


def support_exclusion_mask(element_centroids: np.ndarray) -> np.ndarray:
    """Vrai hors d'un cylindre fixe de 15 mm autour de chaque appui."""

    distances = np.linalg.norm(
        element_centroids[:, None, :2] - STUD_AXES_XY_MM[None, :, :], axis=2
    )
    return np.min(distances, axis=1) > SUPPORT_SINGULARITY_EXCLUSION_RADIUS_MM


def percentile(values: np.ndarray, quantile: float) -> float | None:
    if values.size == 0:
        return None
    return float(np.quantile(values, quantile))


def parse_calculix_dat(path: Path) -> tuple[dict[int, float], dict[int, float]]:
    stresses: dict[int, float] = {}
    displacements: dict[int, float] = {}
    mode = ""
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        lower = raw.lower()
        if "stresses" in lower and "sxx" in lower:
            mode = "stress"
            continue
        if "displacements" in lower and ("vx" in lower or "dx" in lower):
            mode = "displacement"
            continue
        fields = raw.split()
        if mode == "stress" and len(fields) >= 8:
            try:
                element = int(fields[0])
                int(fields[1])
                value = von_mises(float(item) for item in fields[2:8])
            except ValueError:
                continue
            stresses[element] = max(value, stresses.get(element, 0.0))
        elif mode == "displacement" and len(fields) >= 4:
            try:
                node = int(fields[0])
                vector = [float(item) for item in fields[1:4]]
            except ValueError:
                continue
            displacements[node] = math.sqrt(sum(value * value for value in vector))
    return stresses, displacements


def prepare_private_surface(path: Path, repaired_path: Path) -> dict[str, Any]:
    try:
        import trimesh
    except ImportError as exc:
        raise F421Error("trimesh_required") from exc
    loaded = trimesh.load_mesh(path, process=True)
    if not isinstance(loaded, trimesh.Trimesh):
        raise F421Error("input_is_not_one_triangle_mesh")
    components = loaded.split(only_watertight=False)
    if not loaded.is_watertight or len(components) != 1:
        raise F421Error(
            f"private_surface_not_closed:watertight={loaded.is_watertight}:components={len(components)}"
        )
    original_volume = float(loaded.volume)
    original_area = float(loaded.area)
    try:
        import pymeshlab
        import pymeshfix
    except ImportError as exc:
        raise F421Error("pymeshlab_and_pymeshfix_required_for_private_repair") from exc
    meshset = pymeshlab.MeshSet()
    meshset.add_mesh(
        pymeshlab.Mesh(
            vertex_matrix=np.asarray(loaded.vertices),
            face_matrix=np.asarray(loaded.faces),
        )
    )
    for filter_name in (
        "meshing_remove_duplicate_faces",
        "meshing_remove_duplicate_vertices",
        "meshing_remove_folded_faces",
        "meshing_repair_non_manifold_edges",
        "meshing_repair_non_manifold_vertices",
    ):
        meshset.apply_filter(filter_name)
    meshset.apply_filter("compute_selection_by_self_intersections_per_face")
    self_intersecting_faces = int(
        np.count_nonzero(meshset.current_mesh().face_selection_array())
    )
    if self_intersecting_faces:
        meshset.apply_filter("meshing_remove_selected_faces")
        meshset.apply_filter("meshing_close_holes", maxholesize=10000)
    intermediate = meshset.current_mesh()
    meshfix = pymeshfix.MeshFix(
        np.asarray(intermediate.vertex_matrix()),
        np.asarray(intermediate.face_matrix()),
    )
    meshfix.repair(joincomp=False, remove_smallest_components=False)
    repaired = trimesh.Trimesh(
        np.asarray(meshfix.points), np.asarray(meshfix.faces), process=True
    )
    repaired_components = repaired.split(only_watertight=False)
    if not repaired.is_watertight or len(repaired_components) != 1:
        raise F421Error(
            f"private_repair_failed:watertight={repaired.is_watertight}:components={len(repaired_components)}"
        )
    repaired.export(repaired_path)
    volume_difference = abs(float(repaired.volume) - original_volume) / abs(original_volume)
    area_difference = abs(float(repaired.area) - original_area) / abs(original_area)
    if volume_difference > 0.005 or area_difference > 0.005:
        raise F421Error(
            f"private_repair_exceeds_aggregate_tolerance:volume={volume_difference}:area={area_difference}"
        )
    return {
        "sha256": sha256(path),
        "size_bytes": path.stat().st_size,
        "source_triangle_count": int(len(loaded.faces)),
        "watertight_after_exact_vertex_weld": True,
        "connected_components_after_exact_vertex_weld": 1,
        "self_intersecting_faces_removed_before_hole_repair": self_intersecting_faces,
        "private_repair_pipeline": "PyMeshLab_self_intersection_removal_then_MeshFix_hole_repair",
        "repaired_triangle_count": int(len(repaired.faces)),
        "relative_volume_change_after_private_repair": volume_difference,
        "relative_surface_area_change_after_private_repair": area_difference,
        "aggregate_repair_change_below_0_5_percent": (
            volume_difference <= 0.005 and area_difference <= 0.005
        ),
    }


def tetgen_tetrahedralize(
    repaired_surface: Path,
    mesh_size_mm: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    try:
        import tetgen
        import trimesh
    except ImportError as exc:
        raise F421Error("tetgen_and_trimesh_required") from exc
    surface = trimesh.load_mesh(repaired_surface, process=True)
    tetrahedralizer = tetgen.TetGen(
        np.asarray(surface.vertices), np.asarray(surface.faces)
    )
    target_maximum_volume = mesh_size_mm**3 / (6.0 * math.sqrt(2.0))
    try:
        node_xyz, zero_based_tetra, _, _ = tetrahedralizer.tetrahedralize(
            plc=True,
            nobisect=True,
            quality=True,
            mindihedral=2.0,
            minratio=2.0,
            fixedvolume=True,
            maxvolume=target_maximum_volume,
            steinerleft=500000,
            quiet=True,
        )
    except RuntimeError as exc:
        raise F421Error(f"tetgen_failed:{exc}") from exc
    node_xyz = np.asarray(node_xyz, dtype=float)
    tetra_node_tags = np.asarray(zero_based_tetra, dtype=np.int64) + 1
    node_tags = np.arange(1, len(node_xyz) + 1, dtype=np.int64)
    element_tags = np.arange(1, len(tetra_node_tags) + 1, dtype=np.int64)
    if len(element_tags) < 1000 or len(node_tags) < 500:
        raise F421Error("tetgen_tetra_mesh_too_small")
    tetra_xyz = node_xyz[tetra_node_tags - 1]
    signed_six_volume = np.einsum(
        "ij,ij->i",
        tetra_xyz[:, 1] - tetra_xyz[:, 0],
        np.cross(
            tetra_xyz[:, 2] - tetra_xyz[:, 0],
            tetra_xyz[:, 3] - tetra_xyz[:, 0],
        ),
    )
    volume = np.abs(signed_six_volume) / 6.0
    if np.any(volume <= 1.0e-12):
        raise F421Error("zero_volume_tetrahedron")
    edge_pairs = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))
    edge_square_sum = sum(
        np.sum((tetra_xyz[:, first] - tetra_xyz[:, second]) ** 2, axis=1)
        for first, second in edge_pairs
    )
    quality = 12.0 * np.power(3.0 * volume, 2.0 / 3.0) / edge_square_sum
    metrics = {
        "nodes": int(len(node_tags)),
        "elements_C3D4": int(len(element_tags)),
        "volume_mm3": float(np.sum(volume)),
        "target_maximum_tetrahedron_volume_mm3": target_maximum_volume,
        "observed_maximum_tetrahedron_volume_mm3": float(np.max(volume)),
        "minimum_tetrahedron_volume_mm3": float(np.min(volume)),
        "minimum_mean_ratio_quality": float(np.min(quality)),
        "p01_mean_ratio_quality": float(np.quantile(quality, 0.01)),
        "tetgen_input_surface_bisection_disabled": True,
    }
    return node_tags, node_xyz, element_tags, tetra_node_tags, metrics


def element_centroids(
    node_tags: np.ndarray, node_xyz: np.ndarray, tetra_node_tags: np.ndarray
) -> np.ndarray:
    positions = np.searchsorted(node_tags, tetra_node_tags)
    return np.mean(node_xyz[positions], axis=1)


def write_calculix_deck(
    path: Path,
    node_tags: np.ndarray,
    node_xyz: np.ndarray,
    element_tags: np.ndarray,
    tetra_node_tags: np.ndarray,
    chamber_faces: np.ndarray,
    chamber_owners: np.ndarray,
    chamber_labels: np.ndarray,
    stud_faces: list[np.ndarray],
    *,
    pressure_mpa: float,
    ambient_temperature_c: float,
    chamber_temperature_c: float,
    thermal_decay_mm: float,
) -> dict[str, Any]:
    all_nodes = node_tags.tolist()
    stud_nodes = [np.unique(faces).tolist() for faces in stud_faces]
    if any(len(values) < 20 for values in stud_nodes):
        raise F421Error(f"insufficient_stud_support_nodes:{[len(v) for v in stud_nodes]}")
    if len(chamber_faces) < 50:
        raise F421Error(f"insufficient_chamber_pressure_faces:{len(chamber_faces)}")

    distance_from_chamber = np.maximum(
        np.linalg.norm(node_xyz - CHAMBER_CENTER_MM, axis=1) - CHAMBER_RADIUS_MM,
        0.0,
    )
    temperatures = ambient_temperature_c + (
        chamber_temperature_c - ambient_temperature_c
    ) * np.exp(-distance_from_chamber / thermal_decay_mm)

    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write("*HEADING\nF42.1 conformal tetra thermo-mechanical screening\n*NODE\n")
        for tag, point in zip(node_tags, node_xyz, strict=True):
            stream.write(f"{tag},{point[0]:.10g},{point[1]:.10g},{point[2]:.10g}\n")
        stream.write("*ELEMENT,TYPE=C3D4,ELSET=HEAD\n")
        for tag, nodes in zip(element_tags, tetra_node_tags, strict=True):
            stream.write(f"{tag}," + ",".join(str(value) for value in nodes) + "\n")
        write_ids(stream, "NSET", "NALL", all_nodes)
        for index, values in enumerate(stud_nodes, start=1):
            write_ids(stream, "NSET", f"STUD_{index}", values)
        for label in range(1, 5):
            selected = chamber_owners[chamber_labels == label]
            if selected.size:
                write_ids(stream, "ELSET", f"CHAMBER_S{label}", element_tags[selected])
        stream.write(
            "*MATERIAL,NAME=ALSI10MG_PROVISIONAL_ROOM_TEMPERATURE_SCREEN\n"
            "*ELASTIC\n70000.,0.33\n"
            "*EXPANSION\n2.15E-5\n"
            "*SOLID SECTION,ELSET=HEAD,MATERIAL=ALSI10MG_PROVISIONAL_ROOM_TEMPERATURE_SCREEN\n"
            f"*INITIAL CONDITIONS,TYPE=TEMPERATURE\nNALL,{ambient_temperature_c:.9g}\n"
            "*STEP\n*STATIC\n"
            "*BOUNDARY\n"
            "STUD_1,1,3,0.\n"
            "STUD_2,2,3,0.\n"
            "STUD_3,3,3,0.\n"
            "STUD_4,3,3,0.\n"
            "*TEMPERATURE\n"
        )
        for tag, temperature in zip(node_tags, temperatures, strict=True):
            stream.write(f"{tag},{temperature:.9g}\n")
        stream.write("*DLOAD\n")
        for label in range(1, 5):
            if np.any(chamber_labels == label):
                stream.write(f"CHAMBER_S{label},P{label},{pressure_mpa:.9g}\n")
        stream.write(
            "*EL PRINT,ELSET=HEAD\nS\n"
            "*NODE PRINT,NSET=NALL\nU\n"
            "*END STEP\n"
        )
    return {
        "support_nodes_per_stud": [len(values) for values in stud_nodes],
        "temperature_minimum_c": float(np.min(temperatures)),
        "temperature_maximum_c": float(np.max(temperatures)),
    }


def solve_one_case(
    repaired_head: Path,
    input_metadata: dict[str, Any],
    output: Path,
    mesh_size_mm: float,
    settings: dict[str, float],
) -> dict[str, Any]:
    case_dir = output / f"mesh-{mesh_size_mm:g}mm"
    case_dir.mkdir(parents=True, exist_ok=False)
    node_tags, node_xyz, element_tags, tetra_node_tags, mesh = tetgen_tetrahedralize(
        repaired_head, mesh_size_mm
    )
    faces, owners, labels, face_metrics = c3d4_boundary_faces(tetra_node_tags)
    centroids, normals, areas = outward_face_geometry(
        node_tags, node_xyz, tetra_node_tags, faces, owners
    )
    chamber_mask, stud_masks = classify_boundary_faces(centroids, normals)
    if any(np.count_nonzero(mask) < 10 for mask in stud_masks):
        raise F421Error(
            f"stable_stud_surface_group_missing:{[int(np.count_nonzero(m)) for m in stud_masks]}"
        )
    chamber_faces = faces[chamber_mask]
    stud_faces = [faces[mask] for mask in stud_masks]
    deck = case_dir / "f42-1-conformal.inp"
    load_metrics = write_calculix_deck(
        deck,
        node_tags,
        node_xyz,
        element_tags,
        tetra_node_tags,
        chamber_faces,
        owners[chamber_mask],
        labels[chamber_mask],
        stud_faces,
        pressure_mpa=settings["pressure_mpa"],
        ambient_temperature_c=settings["ambient_temperature_c"],
        chamber_temperature_c=settings["chamber_temperature_c"],
        thermal_decay_mm=settings["thermal_decay_mm"],
    )
    completed = subprocess.run(
        ["ccx", "-i", deck.stem],
        cwd=case_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    (case_dir / "calculix.log").write_text(completed.stdout, encoding="utf-8")
    dat = case_dir / f"{deck.stem}.dat"
    stresses, displacements = parse_calculix_dat(dat) if dat.is_file() else ({}, {})
    tag_to_element_index = {int(tag): index for index, tag in enumerate(element_tags)}
    common_stress_tags = sorted(set(stresses) & set(tag_to_element_index))
    stress_values = np.asarray([stresses[tag] for tag in common_stress_tags], dtype=float)
    all_centroids = element_centroids(node_tags, node_xyz, tetra_node_tags)
    stress_centroids = np.asarray(
        [all_centroids[tag_to_element_index[tag]] for tag in common_stress_tags]
    )
    keep = support_exclusion_mask(stress_centroids) if len(stress_centroids) else np.asarray([], dtype=bool)
    cleaned = stress_values[keep]
    displacement_values = np.asarray(list(displacements.values()), dtype=float)
    completed_ok = (
        completed.returncode == 0
        and stress_values.size == len(element_tags)
        and displacement_values.size == len(node_tags)
        and cleaned.size >= int(0.50 * len(element_tags))
    )
    result = {
        "mesh_target_size_mm": mesh_size_mm,
        "status": "completed" if completed_ok else "failed",
        "solver": "CalculiX_ccx_linear_static_C3D4",
        "input": input_metadata,
        "mesh": {
            **mesh,
            **face_metrics,
            "all_tetrahedra_have_positive_absolute_volume": mesh[
                "minimum_tetrahedron_volume_mm3"
            ]
            > 0.0,
        },
        "surface_groups": {
            "chamber_pressure_faces": int(np.count_nonzero(chamber_mask)),
            "chamber_pressure_area_mm2": float(np.sum(areas[chamber_mask])),
            "stud_support_faces_per_stud": [
                int(np.count_nonzero(mask)) for mask in stud_masks
            ],
            "stud_support_area_mm2_per_stud": [
                float(np.sum(areas[mask])) for mask in stud_masks
            ],
            **load_metrics,
        },
        "results": {
            "maximum_displacement_mm": (
                float(np.max(displacement_values)) if displacement_values.size else None
            ),
            "stress_sample_count": int(stress_values.size),
            "raw_von_mises_p95_mpa": percentile(stress_values, 0.95),
            "raw_von_mises_p99_mpa": percentile(stress_values, 0.99),
            "raw_von_mises_maximum_mpa": (
                float(np.max(stress_values)) if stress_values.size else None
            ),
            "support_excluded_sample_count": int(cleaned.size),
            "support_excluded_fraction": (
                float(cleaned.size / stress_values.size) if stress_values.size else 0.0
            ),
            "support_excluded_von_mises_p95_mpa": percentile(cleaned, 0.95),
            "support_excluded_von_mises_p99_mpa": percentile(cleaned, 0.99),
            "support_excluded_von_mises_maximum_mpa": (
                float(np.max(cleaned)) if cleaned.size else None
            ),
        },
        "solver_return_code": completed.returncode,
    }
    return result


def build_public_report(
    private_head: Path,
    cases: list[dict[str, Any]],
    settings: dict[str, float],
) -> dict[str, Any]:
    finest_pair = cases[-2:]
    stress_difference = relative_difference(
        finest_pair[0]["results"]["support_excluded_von_mises_p95_mpa"],
        finest_pair[1]["results"]["support_excluded_von_mises_p95_mpa"],
    )
    displacement_difference = relative_difference(
        finest_pair[0]["results"]["maximum_displacement_mm"],
        finest_pair[1]["results"]["maximum_displacement_mm"],
    )
    all_completed = all(case["status"] == "completed" for case in cases)
    conformal_meshes = all(
        case["mesh"]["nonmanifold_faces"] == 0
        and case["mesh"]["all_tetrahedra_have_positive_absolute_volume"]
        for case in cases
    )
    mesh_quality_and_size_control = all(
        case["mesh"]["p01_mean_ratio_quality"] >= 0.05
        and case["mesh"]["observed_maximum_tetrahedron_volume_mm3"]
        <= 1.05 * case["mesh"]["target_maximum_tetrahedron_volume_mm3"]
        for case in cases
    )
    stable_groups = all(
        case["surface_groups"]["chamber_pressure_faces"] >= 50
        and min(case["surface_groups"]["stud_support_faces_per_stud"]) >= 10
        for case in cases
    )
    stress_converged = stress_difference is not None and stress_difference <= 0.10
    displacement_converged = (
        displacement_difference is not None and displacement_difference <= 0.05
    )
    gates = {
        "all_three_calculix_cases_completed": all_completed and len(cases) == 3,
        "tetra_meshes_conformal_and_positive": conformal_meshes,
        "mesh_quality_and_size_control_adequate": mesh_quality_and_size_control,
        "geometrically_stable_surface_groups_present": stable_groups,
        "support_excluded_p95_finest_pair_difference_below_10_percent": stress_converged,
        "maximum_displacement_finest_pair_difference_below_5_percent": displacement_converged,
        "temperature_dependent_hot_material_card_available": False,
        "loads_correlated_to_instrumented_engine": False,
        "physical_test_correlation_available": False,
        "manufacturing_release": False,
    }
    numerical_screen_passed = all(
        gates[key]
        for key in (
            "all_three_calculix_cases_completed",
            "tetra_meshes_conformal_and_positive",
            "mesh_quality_and_size_control_adequate",
            "geometrically_stable_surface_groups_present",
            "support_excluded_p95_finest_pair_difference_below_10_percent",
            "maximum_displacement_finest_pair_difference_below_5_percent",
        )
    )
    return {
        "schema_version": "1.0.0",
        "phase": "F42.1",
        "status": (
            "numerical_screen_converged_but_not_released"
            if numerical_screen_passed
            else "numerical_screen_not_converged_and_not_released"
        ),
        "classification": "private_scan_conformal_tetra_linear_thermo_mechanical_screen_not_design_release",
        "private_input": {
            "role": "private_F41_welded_head_surface",
            "sha256": sha256(private_head),
            "size_bytes": private_head.stat().st_size,
            "geometry_published": False,
        },
        "method": {
            "surface_repair": "private exact vertex weld, PyMeshLab self-intersection removal, then MeshFix hole repair; aggregate change bounded to 0.5 percent",
            "volume_mesher": "TetGen_PLC_C3D4_with_input_surface_bisection_disabled",
            "rejected_mesher_path": "Gmsh discrete STL createGeometry rejected wrong boundary parametrization topology",
            "surface_grouping": "fixed_public_F41_analytic_chamber_sphere_and_four_stud_bore_axes",
            "support_boundary_condition": "distributed_stud_bore_nodes; stud_1_U1_U2_U3, stud_2_U2_U3, studs_3_4_U3",
            "pressure_loading": "CalculiX_DLOAD_on_selected_tetra_boundary_faces",
            "thermal_loading": "analytic_exponential_temperature_field_from_chamber_surface",
            "support_singularity_rule": {
                "definition": "exclude_element_centroids_inside_any_stud_axis_cylinder",
                "radius_mm": SUPPORT_SINGULARITY_EXCLUSION_RADIUS_MM,
                "fixed_across_all_meshes": True,
                "primary_stress_metric": "support_excluded_von_mises_p95_mpa",
                "raw_metrics_retained": True,
            },
        },
        "screening_inputs": {
            **settings,
            "youngs_modulus_mpa": 70000.0,
            "poisson_ratio": 0.33,
            "thermal_expansion_per_k": 2.15e-5,
            "temperature_dependent_material": False,
            "coupon_qualified_hot_material": False,
        },
        "cases": cases,
        "finest_pair_convergence": {
            "support_excluded_p95_stress_relative_difference": stress_difference,
            "maximum_displacement_relative_difference": displacement_difference,
            "stress_limit_fraction": 0.10,
            "displacement_limit_fraction": 0.05,
        },
        "gates": gates,
        "verdict": {
            "numerical_screen_passed": numerical_screen_passed,
            "part_authorized_for_print": False,
            "part_authorized_for_engine_operation": False,
            "reason": (
                "mesh_quality_or_size_control_inadequate; temperature_dependent_"
                "hot_material_card_and_physical_correlation_missing"
            ),
        },
        "publication": {
            "contains_private_geometry": False,
            "contains_node_coordinates": False,
            "contains_element_connectivity": False,
            "contains_solver_field_files": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--head", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mesh-sizes-mm", type=float, nargs=3, default=[7.0, 5.0, 3.0])
    parser.add_argument("--pressure-mpa", type=float, default=10.0)
    parser.add_argument("--ambient-temperature-c", type=float, default=120.0)
    parser.add_argument("--chamber-temperature-c", type=float, default=260.0)
    parser.add_argument("--thermal-decay-mm", type=float, default=12.0)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    if not args.head.is_file():
        raise FileNotFoundError(args.head)
    sizes = list(args.mesh_sizes_mm)
    if any(value <= 0.0 for value in sizes) or not all(
        sizes[index] > sizes[index + 1] for index in range(2)
    ):
        raise F421Error("mesh_sizes_must_be_three_positive_strictly_descending_values")
    if shutil.which("ccx") is None:
        raise F421Error("calculix_ccx_required")
    settings = {
        "pressure_mpa": args.pressure_mpa,
        "ambient_temperature_c": args.ambient_temperature_c,
        "chamber_temperature_c": args.chamber_temperature_c,
        "thermal_decay_mm": args.thermal_decay_mm,
    }
    args.output.mkdir(parents=True)
    repaired_head = args.output / "private-repaired-input.stl"
    input_metadata = prepare_private_surface(args.head, repaired_head)
    cases = [
        solve_one_case(repaired_head, input_metadata, args.output, size, settings)
        for size in sizes
    ]
    report = build_public_report(args.head, cases, settings)
    report_path = args.output / "917-head-f42-1-conformal-mechanics-public-report.json"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "report": str(report_path),
                "status": report["status"],
                "gates": report["gates"],
            },
            sort_keys=True,
        )
    )
    return 0 if report["gates"]["all_three_calculix_cases_completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
