#!/usr/bin/env python3
"""Prépare et résume un écran de conduction solide CalculiX pour F36.

La géométrie est voxelisée en hexaèdres thermiques. Les faces de chambre
reçoivent un flux moyen, les conduits admission/échappement un film gaz et les
autres faces un film d'air forcé. Ce modèle est un écran de sensibilité CHT
séquentiel; il ne remplace ni une CHT transitoire corrélée ni une carte matière
qualifiée à chaud.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import deque
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh


CHAMBER_CENTRE = np.asarray([0.0, 0.0, -66.0])
CHAMBER_RADIUS = 80.0
CHAMBER_PLAN_RADIUS = 90.81248542471897 / 2.0

FACE_DEFINITIONS = (
    ((-1, 0, 0), (0, 3, 7, 4), "S6"),
    ((1, 0, 0), (1, 2, 6, 5), "S4"),
    ((0, -1, 0), (0, 1, 5, 4), "S3"),
    ((0, 1, 0), (3, 2, 6, 7), "S5"),
    ((0, 0, -1), (0, 1, 2, 3), "S1"),
    ((0, 0, 1), (4, 5, 6, 7), "S2"),
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def chunks(values: list[int], size: int = 16) -> list[list[int]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def write_set(stream, keyword: str, name: str, values: list[int]) -> None:
    stream.write(f"*{keyword},{keyword}={name}\n")
    for row in chunks(values):
        stream.write(",".join(str(value) for value in row) + "\n")


def largest_face_connected_component(occupied: set[tuple[int, int, int]]) -> tuple[set[tuple[int, int, int]], int]:
    remaining = set(occupied)
    largest: set[tuple[int, int, int]] = set()
    directions = tuple(item[0] for item in FACE_DEFINITIONS)
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


def parse_temperatures(path: Path) -> dict[int, float]:
    temperatures: dict[int, float] = {}
    active = False
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        lower = raw.lower()
        if "temperatures for set" in lower:
            active = True
            continue
        fields = raw.split()
        if active and len(fields) >= 2:
            try:
                temperatures[int(fields[0])] = float(fields[1])
            except ValueError:
                if temperatures:
                    active = False
    return temperatures


def parse_nodes(path: Path) -> dict[int, tuple[float, float, float]]:
    nodes: dict[int, tuple[float, float, float]] = {}
    active = False
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if line.upper() == "*NODE":
            active = True
            continue
        if line.startswith("*") and active:
            break
        if active and line:
            fields = [field.strip() for field in line.split(",")]
            nodes[int(fields[0])] = tuple(float(value) for value in fields[1:4])
    return nodes


def render_temperature(output: Path, temperatures: dict[int, float]) -> Path:
    nodes = parse_nodes(output / "head-f36-thermal.inp")
    tags = np.asarray(sorted(set(nodes).intersection(temperatures)), dtype=int)
    if not len(tags):
        raise RuntimeError("aucun noeud thermique commun à rendre")
    if len(tags) > 45000:
        tags = tags[np.linspace(0, len(tags) - 1, 45000, dtype=int)]
    points = np.asarray([nodes[int(tag)] for tag in tags])
    values = np.asarray([temperatures[int(tag)] for tag in tags])
    vmin = float(np.percentile(values, 1.0))
    vmax = float(np.percentile(values, 99.0))
    figure = plt.figure(figsize=(15, 8), facecolor="#0b1118")
    figure.suptitle("F36 — conduction solide / carte nodale CalculiX", color="white", fontsize=20, fontweight="bold")
    for panel, (elev, azim, title) in enumerate(((20.0, -55.0, "Vue admission/latérale"), (12.0, 35.0, "Vue échappement")), start=1):
        axis = figure.add_subplot(1, 2, panel, projection="3d", facecolor="#101b24")
        scatter = axis.scatter(
            points[:, 0],
            points[:, 1],
            points[:, 2],
            c=values,
            cmap="inferno",
            vmin=vmin,
            vmax=vmax,
            s=2.2,
            linewidths=0,
            alpha=0.92,
        )
        centre = points.mean(axis=0)
        radius = 0.55 * float(np.ptp(points, axis=0).max())
        axis.set_xlim(centre[0] - radius, centre[0] + radius)
        axis.set_ylim(centre[1] - radius, centre[1] + radius)
        axis.set_zlim(centre[2] - 0.45 * radius, centre[2] + 0.55 * radius)
        axis.set_box_aspect((1.0, 1.15, 0.75))
        axis.view_init(elev=elev, azim=azim)
        axis.set_axis_off()
        axis.set_title(title, color="white", fontsize=12, fontweight="bold")
    colourbar = figure.colorbar(scatter, ax=figure.axes, fraction=0.022, pad=0.02)
    colourbar.set_label("Température °C", color="white")
    colourbar.ax.tick_params(colors="white")
    figure.text(
        0.5,
        0.035,
        f"min {values.min():.1f} °C · médiane {np.median(values):.1f} °C · p95 {np.percentile(values, 95):.1f} °C · max {values.max():.1f} °C · points = noeuds FEA",
        color="#d6dde3",
        ha="center",
        fontsize=10,
    )
    figure.subplots_adjust(left=0.01, right=0.91, bottom=0.08, top=0.90, wspace=0.02)
    image_path = output / "917-head-f36-thermal-map.png"
    figure.savefig(image_path, dpi=180, facecolor=figure.get_facecolor())
    plt.close(figure)
    return image_path


def prepare(
    stl: Path,
    flow_core_stl: Path,
    output: Path,
    pitch: float,
    chamber_flux_w_mm2: float,
    ambient_c: float,
    external_h_w_mm2k: float,
    intake_gas_c: float,
    intake_h_w_mm2k: float,
    exhaust_gas_c: float,
    exhaust_h_w_mm2k: float,
    transient_duration_s: float | None,
    initial_temperature_c: float,
    conductivity_scale: float,
) -> dict:
    if output.exists():
        raise ValueError(f"output exists: {output}")
    if conductivity_scale <= 0.0:
        raise ValueError("conductivity_scale doit etre strictement positif")
    output.mkdir(parents=True)
    mesh = trimesh.load_mesh(stl, process=True)
    flow = trimesh.load_mesh(flow_core_stl, process=True)
    if not isinstance(mesh, trimesh.Trimesh) or not mesh.is_watertight:
        raise ValueError("la géométrie de culasse F36 doit être étanche")
    if not isinstance(flow, trimesh.Trimesh):
        raise ValueError("le noyau fluide F36 est invalide")

    grid = mesh.voxelized(pitch=pitch, method="subdivide").fill(method="holes")
    raw_occupied = {tuple(int(value) for value in row) for row in grid.sparse_indices}
    occupied, component_count = largest_face_connected_component(raw_occupied)
    transform = np.asarray(grid.transform, dtype=float)

    node_ids: dict[tuple[int, int, int], int] = {}
    node_coordinates: dict[int, tuple[float, float, float]] = {}

    def node(corner: tuple[int, int, int]) -> int:
        if corner not in node_ids:
            tag = len(node_ids) + 1
            point = trimesh.transform_points((np.asarray(corner, dtype=float) - 0.5)[None, :], transform)[0]
            node_ids[corner] = tag
            node_coordinates[tag] = tuple(float(value) for value in point)
        return node_ids[corner]

    elements: list[tuple[int, tuple[int, int, int], tuple[int, ...]]] = []
    for element_id, index in enumerate(sorted(occupied), start=1):
        i, j, k = index
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
        elements.append((element_id, index, tuple(node(corner) for corner in corners)))

    boundary: list[dict] = []
    for element_id, index, element_nodes in elements:
        for direction, local_face, face_label in FACE_DEFINITIONS:
            neighbour = tuple(index[axis] + direction[axis] for axis in range(3))
            if neighbour in occupied:
                continue
            face_nodes = tuple(element_nodes[position] for position in local_face)
            centre = np.mean([node_coordinates[tag] for tag in face_nodes], axis=0)
            radius = float(np.linalg.norm(centre - CHAMBER_CENTRE))
            radial_xy = float(np.linalg.norm(centre[:2]))
            is_chamber = (
                radial_xy <= CHAMBER_PLAN_RADIUS + 0.5 * pitch
                and abs(radius - CHAMBER_RADIUS) <= 1.1 * pitch
                and centre[2] <= 18.0
            )
            boundary.append(
                {
                    "element": element_id,
                    "face": face_label,
                    "nodes": face_nodes,
                    "centre": centre,
                    "is_chamber": is_chamber,
                }
            )

    non_chamber = [item for item in boundary if not item["is_chamber"]]
    if non_chamber:
        centres = np.asarray([item["centre"] for item in non_chamber])
        _, distances, _ = trimesh.proximity.closest_point(flow, centres)
        for item, distance in zip(non_chamber, distances, strict=True):
            if distance <= 1.35 * pitch:
                item["region"] = "exhaust_port" if item["centre"][1] > 0.0 else "intake_port"
            else:
                item["region"] = "external_air"
    for item in boundary:
        if item["is_chamber"]:
            item["region"] = "chamber"

    regions: dict[str, list[dict]] = {name: [] for name in ("chamber", "intake_port", "exhaust_port", "external_air")}
    for item in boundary:
        regions[item["region"]].append(item)
    if len(regions["chamber"]) < 20 or len(regions["external_air"]) < 100:
        raise RuntimeError("classification thermique des surfaces insuffisante")

    job = output / "head-f36-thermal.inp"
    with job.open("w", encoding="utf-8") as stream:
        stream.write("*HEADING\nF36 scan-conforming solid conduction sensitivity screen\n*NODE\n")
        for tag in sorted(node_coordinates):
            x, y, z = node_coordinates[tag]
            stream.write(f"{tag},{x:.9g},{y:.9g},{z:.9g}\n")
        stream.write("*ELEMENT,TYPE=DC3D8,ELSET=EALL\n")
        for element_id, _, tags in elements:
            stream.write(f"{element_id}," + ",".join(str(tag) for tag in tags) + "\n")
        write_set(stream, "NSET", "NALL", sorted(node_coordinates))
        conductivity = [150.0 * conductivity_scale, 135.0 * conductivity_scale, 120.0 * conductivity_scale]
        stream.write(
            "*MATERIAL,NAME=AHEADD_HT1_THERMAL_SCREEN\n"
            "*DENSITY\n"
            "2.67e-6\n"
            "*SPECIFIC HEAT\n"
            "900.\n"
            "*CONDUCTIVITY\n"
            f"{conductivity[0] / 1000.0:.9g},20.\n"
            f"{conductivity[1] / 1000.0:.9g},200.\n"
            f"{conductivity[2] / 1000.0:.9g},300.\n"
            "*SOLID SECTION,ELSET=EALL,MATERIAL=AHEADD_HT1_THERMAL_SCREEN\n"
            "*INITIAL CONDITIONS,TYPE=TEMPERATURE\n"
            f"NALL,{initial_temperature_c:.9g}\n"
            "*STEP\n"
        )
        if transient_duration_s is None:
            stream.write("*HEAT TRANSFER,STEADY STATE\n")
        else:
            initial_increment = min(0.25, max(0.01, transient_duration_s / 100.0))
            maximum_increment = min(1.0, max(0.05, transient_duration_s / 20.0))
            stream.write("*HEAT TRANSFER\n")
            stream.write(f"{initial_increment:.9g},{transient_duration_s:.9g},1e-6,{maximum_increment:.9g}\n")
        stream.write("*DFLUX\n")
        for item in regions["chamber"]:
            stream.write(f"{item['element']},{item['face']},{chamber_flux_w_mm2:.9g}\n")
        stream.write("*FILM\n")
        film_settings = {
            "external_air": (ambient_c, external_h_w_mm2k),
            "intake_port": (intake_gas_c, intake_h_w_mm2k),
            "exhaust_port": (exhaust_gas_c, exhaust_h_w_mm2k),
        }
        for region in ("external_air", "intake_port", "exhaust_port"):
            sink_c, coefficient = film_settings[region]
            for item in regions[region]:
                film_face = "F" + item["face"][1:]
                stream.write(f"{item['element']},{film_face},{sink_c:.9g},{coefficient:.9g}\n")
        stream.write("*NODE PRINT,NSET=NALL,FREQUENCY=1\nNT\n*NODE FILE,NSET=NALL,FREQUENCY=1\nNT\n*END STEP\n")

    face_area_mm2 = pitch * pitch
    preparation = {
        "schema_version": "1.0.0",
        "phase": "F36",
        "status": "thermal_input_prepared",
        "classification": "scan_conforming_voxel_solid_conduction_with_mean_flux_and_film_hypotheses",
        "mesh": {
            "pitch_mm_if_obj_unit_is_mm": pitch,
            "raw_occupied_voxels": len(raw_occupied),
            "face_connected_components": component_count,
            "discarded_non_primary_voxels": len(raw_occupied) - len(occupied),
            "nodes": len(node_coordinates),
            "hexahedra": len(elements),
        },
        "surface_regions": {
            region: {"faces": len(items), "voxel_area_mm2": len(items) * face_area_mm2}
            for region, items in regions.items()
        },
        "boundary_conditions": {
            "chamber_flux_w_mm2": chamber_flux_w_mm2,
            "external_air": {"sink_c": ambient_c, "h_w_mm2k": external_h_w_mm2k},
            "intake_port": {"sink_c": intake_gas_c, "h_w_mm2k": intake_h_w_mm2k},
            "exhaust_port": {"sink_c": exhaust_gas_c, "h_w_mm2k": exhaust_h_w_mm2k},
            "analysis_type": "transient" if transient_duration_s is not None else "steady_state",
            "transient_duration_s": transient_duration_s,
            "initial_temperature_c": initial_temperature_c,
        },
        "material": {
            "id": "Aheadd_HT1_candidate_unqualified_thermal_screen",
            "conductivity_scale": conductivity_scale,
            "conductivity_w_mk_by_temperature_c": [
                [20.0, conductivity[0]],
                [200.0, conductivity[1]],
                [300.0, conductivity[2]],
            ],
            "density_kg_mm3": 2.67e-6,
            "specific_heat_j_kgk": 900.0,
            "card_qualified": False,
        },
        "inputs": {"head_sha256": sha256(stl), "flow_core_sha256": sha256(flow_core_stl)},
        "input_sha256": sha256(job),
        "release_claim": False,
    }
    (output / "preparation.json").write_text(json.dumps(preparation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return preparation


def summarize(output: Path) -> dict:
    preparation = json.loads((output / "preparation.json").read_text(encoding="utf-8"))
    temperatures = parse_temperatures(output / "head-f36-thermal.dat")
    values = np.asarray(list(temperatures.values()), dtype=float)
    image_path = render_temperature(output, temperatures) if len(values) else None
    report = {
        **preparation,
        "status": "completed_screening" if len(values) else "failed",
        "solver": "CalculiX",
        "results": {
            "temperature_samples": int(len(values)),
            "minimum_temperature_c": float(values.min()) if len(values) else None,
            "median_temperature_c": float(np.median(values)) if len(values) else None,
            "p95_temperature_c": float(np.percentile(values, 95.0)) if len(values) else None,
            "maximum_temperature_c": float(values.max()) if len(values) else None,
        },
        "engineering_gates": {
            "maximum_below_260_c_service_screen": bool(len(values) and values.max() < 260.0),
            "temperature_field_from_conjugate_cfd": False,
            "thermal_material_card_qualified": False,
            "physical_thermocouple_correlation": False,
            "metal_print_authorized": False,
            "engine_start_authorized": False,
        },
        "local_files": {
            image_path.name: {"bytes": image_path.stat().st_size, "sha256": sha256(image_path)}
        }
        if image_path is not None
        else {},
    }
    (output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stl", type=Path)
    parser.add_argument("--flow-core", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pitch", type=float)
    parser.add_argument("--chamber-flux-w-mm2", type=float, default=0.85)
    parser.add_argument("--ambient-c", type=float, default=40.0)
    parser.add_argument("--external-h-w-mm2k", type=float, default=0.00018)
    parser.add_argument("--intake-gas-c", type=float, default=100.0)
    parser.add_argument("--intake-h-w-mm2k", type=float, default=0.00010)
    parser.add_argument("--exhaust-gas-c", type=float, default=900.0)
    parser.add_argument("--exhaust-h-w-mm2k", type=float, default=0.00035)
    parser.add_argument("--transient-duration-s", type=float)
    parser.add_argument("--initial-temperature-c", type=float, default=80.0)
    parser.add_argument("--conductivity-scale", type=float, default=1.0)
    parser.add_argument("--summarize", action="store_true")
    args = parser.parse_args()
    if args.summarize:
        report = summarize(args.output)
    else:
        if args.stl is None or args.flow_core is None or args.pitch is None:
            parser.error("--stl, --flow-core et --pitch sont requis en préparation")
        report = prepare(
            args.stl,
            args.flow_core,
            args.output,
            args.pitch,
            args.chamber_flux_w_mm2,
            args.ambient_c,
            args.external_h_w_mm2k,
            args.intake_gas_c,
            args.intake_h_w_mm2k,
            args.exhaust_gas_c,
            args.exhaust_h_w_mm2k,
            args.transient_duration_s,
            args.initial_temperature_c,
            args.conductivity_scale,
        )
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] in {"thermal_input_prepared", "completed_screening"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
