#!/usr/bin/env python3
"""Prépare et résume un écran CalculiX F36 sur une grille hexa voxelisée."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from collections import deque
from pathlib import Path

import numpy as np
import trimesh


STUD_CENTRES = (
    (-43.349015535011006, 42.903346179100126),
    (-42.84714926124019, -42.78730191374865),
    (43.100281745848605, 43.128535835401735),
    (43.39375446372094, -42.44463944735759),
)
CHAMBER_CENTRE = np.asarray([0.0, 0.0, -66.0])
CHAMBER_RADIUS = 80.0
CHAMBER_PLAN_RADIUS = 90.81248542471897 / 2.0


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def chunks(values: list[int], size: int = 16) -> list[list[int]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def write_set(stream, keyword: str, name: str, values: list[int]) -> None:
    stream.write(f"*{keyword},{keyword}={name}\n")
    for row in chunks(values):
        stream.write(",".join(str(value) for value in row) + "\n")


def parse_dat(path: Path) -> tuple[list[float], list[float], int | None]:
    stresses: list[float] = []
    displacements: list[float] = []
    peak_element_id: int | None = None
    peak_stress = -math.inf
    mode = ""
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        lower = raw.lower()
        if "stresses" in lower and "sxx" in lower:
            mode = "stress"
            continue
        if "displacements" in lower and ("dx" in lower or "vx" in lower):
            mode = "displacement"
            continue
        fields = raw.split()
        if mode == "stress" and len(fields) >= 8:
            try:
                int(fields[0]); int(fields[1])
                sxx, syy, szz, sxy, sxz, syz = map(float, fields[2:8])
            except ValueError:
                continue
            value = math.sqrt(
                    0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
                    + 3.0 * (sxy * sxy + sxz * sxz + syz * syz)
                )
            stresses.append(value)
            if value > peak_stress:
                peak_stress = value
                peak_element_id = int(fields[0])
        elif mode == "displacement" and len(fields) >= 4:
            try:
                int(fields[0])
                vector = list(map(float, fields[1:4]))
            except ValueError:
                continue
            displacements.append(math.sqrt(sum(value * value for value in vector)))
    return stresses, displacements, peak_element_id


def element_centroid_from_inp(path: Path, element_id: int | None) -> tuple[float, float, float] | None:
    if element_id is None:
        return None
    nodes: dict[int, tuple[float, float, float]] = {}
    selected_nodes: tuple[int, ...] | None = None
    mode = ""
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if line.startswith("*"):
            keyword = line.split(",", 1)[0].upper()
            mode = "node" if keyword == "*NODE" else "element" if keyword == "*ELEMENT" else ""
            continue
        if not line:
            continue
        fields = [field.strip() for field in line.split(",")]
        if mode == "node":
            nodes[int(fields[0])] = tuple(float(value) for value in fields[1:4])
        elif mode == "element" and int(fields[0]) == element_id:
            selected_nodes = tuple(int(value) for value in fields[1:])
    if selected_nodes is None or any(tag not in nodes for tag in selected_nodes):
        return None
    return tuple(sum(nodes[tag][axis] for tag in selected_nodes) / len(selected_nodes) for axis in range(3))


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(fraction * (len(ordered) - 1)))]


def largest_face_connected_component(occupied: set[tuple[int, int, int]]) -> tuple[set[tuple[int, int, int]], int]:
    remaining = set(occupied)
    largest: set[tuple[int, int, int]] = set()
    directions = ((-1, 0, 0), (1, 0, 0), (0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1))
    component_count = 0
    while remaining:
        component_count += 1
        seed = remaining.pop()
        component = {seed}
        queue = deque([seed])
        while queue:
            current = queue.popleft()
            for direction in directions:
                neighbour = tuple(current[axis] + direction[axis] for axis in range(3))
                if neighbour in remaining:
                    remaining.remove(neighbour)
                    component.add(neighbour)
                    queue.append(neighbour)
        if len(component) > len(largest):
            largest = component
    return largest, component_count


def prepare(
    stl: Path,
    output: Path,
    pitch: float,
    pressure_mpa: float,
    chamber_temperature_c: float,
    upper_temperature_c: float,
) -> dict:
    if output.exists():
        raise ValueError(f"output exists: {output}")
    output.mkdir(parents=True)
    mesh = trimesh.load_mesh(stl, process=True)
    if not isinstance(mesh, trimesh.Trimesh) or not mesh.is_watertight:
        raise ValueError("la géométrie F36 doit être étanche")
    grid = mesh.voxelized(pitch=pitch, method="subdivide").fill(method="holes")
    raw_occupied = {tuple(int(value) for value in row) for row in grid.sparse_indices}
    occupied, voxel_component_count = largest_face_connected_component(raw_occupied)
    transform = np.asarray(grid.transform, dtype=float)

    node_ids: dict[tuple[int, int, int], int] = {}
    node_coordinates: dict[int, tuple[float, float, float]] = {}

    def node(corner: tuple[int, int, int]) -> int:
        if corner not in node_ids:
            tag = len(node_ids) + 1
            centre_index = np.asarray(corner, dtype=float) - 0.5
            point = trimesh.transform_points(centre_index[None, :], transform)[0]
            node_ids[corner] = tag
            node_coordinates[tag] = tuple(float(value) for value in point)
        return node_ids[corner]

    elements: list[tuple[int, tuple[int, ...]]] = []
    for element_id, (i, j, k) in enumerate(sorted(occupied), start=1):
        corners = (
            (i, j, k),
            (i + 1, j, k),
            (i + 1, j + 1, k),
            (i, j + 1, k),
            (i, j, k + 1),
            (i + 1, j, k + 1),
            (i + 1, j + 1, k + 1),
            (i, j + 1, k + 1),
        )
        elements.append((element_id, tuple(node(corner) for corner in corners)))

    face_definitions = (
        ((-1, 0, 0), (0, 3, 7, 4)),
        ((1, 0, 0), (1, 2, 6, 5)),
        ((0, -1, 0), (0, 1, 5, 4)),
        ((0, 1, 0), (3, 2, 6, 7)),
        ((0, 0, -1), (0, 1, 2, 3)),
        ((0, 0, 1), (4, 5, 6, 7)),
    )
    forces: dict[int, np.ndarray] = defaultdict(lambda: np.zeros(3, dtype=float))
    loaded_faces = 0
    raw_projected_area_mm2 = 0.0
    selected_faces: list[tuple[list[int], np.ndarray]] = []
    for _, element_nodes in elements:
        points = np.asarray([node_coordinates[tag] for tag in element_nodes])
        index = tuple(int(round((value - transform[axis, 3]) / transform[axis, axis])) for axis, value in enumerate(points.mean(axis=0)))
        for direction, local_face in face_definitions:
            neighbour = tuple(index[axis] + direction[axis] for axis in range(3))
            if neighbour in occupied:
                continue
            face_nodes = [element_nodes[position] for position in local_face]
            centre = np.mean([node_coordinates[tag] for tag in face_nodes], axis=0)
            radius = float(np.linalg.norm(centre - CHAMBER_CENTRE))
            radial_xy = float(np.linalg.norm(centre[:2]))
            if radial_xy > CHAMBER_PLAN_RADIUS + 0.5 * pitch or abs(radius - CHAMBER_RADIUS) > 1.1 * pitch or centre[2] > 18.0:
                continue
            pressure_direction = (centre - CHAMBER_CENTRE) / max(radius, 1.0e-12)
            selected_faces.append((face_nodes, pressure_direction))
            raw_projected_area_mm2 += pitch * pitch * max(pressure_direction[2], 0.0)
            loaded_faces += 1

    # Les guides et sièges sont ouverts dans le prototype sans soupapes solides;
    # ils agrandissent artificiellement la peau exposée. Le chargement est donc
    # normalisé au résultat axial p*pi*r_chambre^2, comme si les quatre soupapes
    # et les deux bougies fermaient réellement la chambre.
    target_projected_area_mm2 = math.pi * CHAMBER_PLAN_RADIUS**2
    if raw_projected_area_mm2 <= 0.0:
        raise RuntimeError("aucune surface de chambre n'a été sélectionnée")
    pressure_area_scale = target_projected_area_mm2 / raw_projected_area_mm2
    for face_nodes, pressure_direction in selected_faces:
        force = pressure_mpa * pitch * pitch * pressure_area_scale * pressure_direction
        for tag in face_nodes:
            forces[tag] += force / 4.0

    minimum_z = min(point[2] for point in node_coordinates.values())
    support_groups: list[list[int]] = []
    for centre_x, centre_y in STUD_CENTRES:
        group = [
            tag
            for tag, point in node_coordinates.items()
            if point[2] <= minimum_z + 2.2 * pitch
            and math.hypot(point[0] - centre_x, point[1] - centre_y) <= 9.0
        ]
        support_groups.append(sorted(group))
    support = sorted({tag for group in support_groups for tag in group})
    if not elements or len(forces) < 20 or any(len(group) < 4 for group in support_groups):
        raise RuntimeError("sélection hexa insuffisante pour la chambre ou les appuis de goujons")

    anchor = [support_groups[0][0]]
    guide = [support_groups[1][0]]
    job = output / "head-f36.inp"
    with job.open("w", encoding="utf-8") as stream:
        stream.write("*HEADING\nF36 scan-conforming voxel hexa thermo-pressure screen\n*NODE\n")
        for tag in sorted(node_coordinates):
            x, y, z = node_coordinates[tag]
            stream.write(f"{tag},{x:.9g},{y:.9g},{z:.9g}\n")
        stream.write("*ELEMENT,TYPE=C3D8,ELSET=EALL\n")
        for element_id, tags in elements:
            stream.write(f"{element_id}," + ",".join(str(tag) for tag in tags) + "\n")
        write_set(stream, "NSET", "NALL", sorted(node_coordinates))
        write_set(stream, "NSET", "STUD_SUPPORT", support)
        write_set(stream, "NSET", "ANCHOR", anchor)
        write_set(stream, "NSET", "GUIDE", guide)
        stream.write(
            "*MATERIAL,NAME=AHEADD_HT1_SCREEN\n"
            "*ELASTIC\n66000.,0.33\n"
            "*EXPANSION\n2.3e-5\n"
            "*SOLID SECTION,ELSET=EALL,MATERIAL=AHEADD_HT1_SCREEN\n"
            "*INITIAL CONDITIONS,TYPE=TEMPERATURE\nNALL,20.\n"
            "*STEP\n*STATIC\n"
            # Le guide est séparé de l'ancrage principalement suivant Y.
            # Bloquer X à ce point supprime la rotation rigide autour de Z tout
            # en laissant la dilatation thermique suivant l'axe ancrage-guide.
            "*BOUNDARY\nSTUD_SUPPORT,3,3\nANCHOR,1,2\nGUIDE,1,1\n"
            "*TEMPERATURE\n"
        )
        for tag in sorted(node_coordinates):
            z = node_coordinates[tag][2]
            temperature_c = chamber_temperature_c - (chamber_temperature_c - upper_temperature_c) * min(
                1.0, max(0.0, (z - 5.0) / 75.0)
            )
            stream.write(f"{tag},{temperature_c:.8g}\n")
        stream.write("*CLOAD\n")
        for tag in sorted(forces):
            for degree, value in enumerate(forces[tag], start=1):
                if abs(value) > 1.0e-12:
                    stream.write(f"{tag},{degree},{value:.9g}\n")
        stream.write(
            "*EL PRINT,ELSET=EALL\nS\n"
            "*NODE PRINT,NSET=NALL\nU\n"
            "*EL FILE\nS,E\n"
            "*NODE FILE,NSET=NALL\nU,RF\n"
            "*END STEP\n"
        )

    preparation = {
        "schema_version": "1.0.0",
        "phase": "F36",
        "status": "calculix_input_prepared",
        "classification": "scan_conforming_structured_voxel_hexa_linear_elastic_thermal_pressure_screen",
        "mesh": {
            "pitch_mm_if_obj_unit_is_mm": pitch,
            "raw_occupied_voxels": len(raw_occupied),
            "face_connected_components": voxel_component_count,
            "discarded_non_primary_voxels": len(raw_occupied) - len(occupied),
            "nodes": len(node_coordinates),
            "hexahedra": len(elements),
            "loaded_chamber_faces": loaded_faces,
            "raw_open_head_projected_area_mm2": raw_projected_area_mm2,
            "target_closed_chamber_projected_area_mm2": target_projected_area_mm2,
            "pressure_area_scale": pressure_area_scale,
            "loaded_nodes": len(forces),
            "support_nodes": len(support),
            "support_nodes_per_stud": [len(group) for group in support_groups],
        },
        "load": {
            "pressure_mpa": pressure_mpa,
            "temperature_c": {
                "chamber": chamber_temperature_c,
                "upper_fins": upper_temperature_c,
                "reference": 20.0,
            },
        },
        "material": {
            "id": "Constellium_Aheadd_HT1_high_temperature_heat_treatment",
            "hot_yield_mpa_at_250c": 216.0,
            "elastic_modulus_mpa_hypothesis": 66000.0,
            "poisson_hypothesis": 0.33,
            "thermal_expansion_per_k_hypothesis": 2.3e-5,
            "hot_elastic_card_qualified": False,
        },
        "input_sha256": sha256(job),
        "release_claim": False,
    }
    (output / "preparation.json").write_text(json.dumps(preparation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return preparation


def summarize(output: Path) -> dict:
    preparation = json.loads((output / "preparation.json").read_text(encoding="utf-8"))
    dat = output / "head-f36.dat"
    stresses, displacements, peak_element_id = parse_dat(dat) if dat.is_file() else ([], [], None)
    peak_centroid = element_centroid_from_inp(output / "head-f36.inp", peak_element_id)
    nearest_stud_distance = (
        min(math.hypot(peak_centroid[0] - centre[0], peak_centroid[1] - centre[1]) for centre in STUD_CENTRES)
        if peak_centroid is not None
        else None
    )
    p95 = percentile(stresses, 0.95)
    p99 = percentile(stresses, 0.99)
    hot_yield_mpa = float(preparation["material"]["hot_yield_mpa_at_250c"])
    above_hot_yield = sum(value > hot_yield_mpa for value in stresses)
    report = {
        **preparation,
        "status": "completed_screening" if stresses and displacements else "failed",
        "solver": "CalculiX",
        "results": {
            "stress_samples": len(stresses),
            "von_mises_p95_mpa": p95,
            "von_mises_p99_mpa": p99,
            "von_mises_max_mpa": max(stresses) if stresses else None,
            "von_mises_max_element_id": peak_element_id,
            "von_mises_max_element_centroid_obj_units": list(peak_centroid) if peak_centroid is not None else None,
            "von_mises_max_nearest_stud_centre_distance_obj_units": nearest_stud_distance,
            "von_mises_max_at_stud_support_edge": bool(
                peak_centroid is not None
                and nearest_stud_distance is not None
                and nearest_stud_distance <= 15.0
                and peak_centroid[2] <= 0.0
            ),
            "maximum_displacement_mm": max(displacements) if displacements else None,
            "p95_hot_yield_margin": hot_yield_mpa / p95 if p95 else None,
            "p99_hot_yield_margin": hot_yield_mpa / p99 if p99 else None,
            "stress_samples_above_hot_yield": above_hot_yield,
            "stress_sample_fraction_above_hot_yield": above_hot_yield / len(stresses) if stresses else None,
        },
        "physical_limits": {
            "absolute_scale_confirmed": False,
            "temperature_field_from_CHT": False,
            "nonlinear_contact_creep_fatigue_tmf_included": False,
            "manufacturing_authorized": False,
        },
    }
    (output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stl", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pitch", type=float)
    parser.add_argument("--pressure-mpa", type=float, default=24.686)
    parser.add_argument("--chamber-temperature-c", type=float, default=260.0)
    parser.add_argument("--upper-temperature-c", type=float, default=120.0)
    parser.add_argument("--summarize", action="store_true")
    args = parser.parse_args()
    if args.summarize:
        report = summarize(args.output)
    else:
        if args.stl is None or args.pitch is None:
            parser.error("--stl et --pitch sont requis en préparation")
        report = prepare(
            args.stl,
            args.output,
            args.pitch,
            args.pressure_mpa,
            args.chamber_temperature_c,
            args.upper_temperature_c,
        )
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] in {"calculix_input_prepared", "completed_screening"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
