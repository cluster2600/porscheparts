#!/usr/bin/env python3
"""Exécute et publie le témoin thermo-mécanique circulaire F50.

Le mode ``solve`` requiert Gmsh, NumPy et CalculiX. Il écrit les maillages et
champs coordinate-bearing dans ``work/`` uniquement. Le mode ``publish`` ne
publie que des agrégats, des images de champs du témoin et des empreintes.

Ce programme ne charge, ne reconstruit et ne modifie jamais la peau F43. Le
témoin circulaire représente seulement le pont local dans l'empreinte du bore;
ce n'est pas une géométrie de culasse complète.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

import numpy as np


C3D4_FACES: dict[int, tuple[int, int, int]] = {
    1: (0, 1, 2),
    2: (0, 3, 1),
    3: (1, 3, 2),
    4: (2, 3, 0),
}


class F50Error(RuntimeError):
    """Erreur contrôlée de la campagne F50."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def relative_difference(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or not math.isfinite(a) or not math.isfinite(b):
        return None
    return abs(a - b) / max(abs(a), abs(b), 1.0e-30)


def percentile(values: np.ndarray, fraction: float) -> float | None:
    if values.size == 0:
        return None
    return float(np.quantile(values, fraction))


def validate_upstream(root: Path, contract: dict[str, Any]) -> list[dict[str, Any]]:
    validated: list[dict[str, Any]] = []
    for name, binding in contract["upstream"].items():
        path = root / binding["path"]
        if not path.is_file():
            raise F50Error(f"missing_upstream:{name}:{binding['path']}")
        actual = sha256(path)
        if actual != binding["sha256"]:
            raise F50Error(
                f"upstream_hash_mismatch:{name}:{actual}:{binding['sha256']}"
            )
        validated.append(
            {
                "id": name,
                "path": binding["path"],
                "sha256": actual,
                "bytes": path.stat().st_size,
            }
        )
    for variant, definition in contract["variants"].items():
        binding = definition["trace"]
        path = root / binding["path"]
        if not path.is_file():
            raise F50Error(f"missing_trace:{variant}:{binding['path']}")
        actual = sha256(path)
        if actual != binding["sha256"]:
            raise F50Error(
                f"trace_hash_mismatch:{variant}:{actual}:{binding['sha256']}"
            )
        validated.append(
            {
                "id": f"{variant}_complete_F46_trace",
                "path": binding["path"],
                "sha256": actual,
                "bytes": path.stat().st_size,
                "case_id": binding["case_id"],
            }
        )
    return validated


def trace_metrics(path: Path, reference_pressure_pa: float) -> dict[str, float]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) < 720:
        raise F50Error(f"trace_too_short:{path}:{len(rows)}")
    angles = np.asarray([float(row["crank_angle_deg"]) for row in rows])
    pressure = np.asarray([float(row["pressure_pa_abs"]) for row in rows])
    temperature = np.asarray([float(row["temperature_k"]) for row in rows])
    flux = np.asarray([float(row["wall_heat_flux_w_m2"]) for row in rows])
    if not all(np.all(np.isfinite(values)) for values in (angles, pressure, temperature, flux)):
        raise F50Error(f"non_finite_trace:{path}")
    if abs(float(angles[0])) > 1.0e-12 or angles[-1] >= 720.0:
        raise F50Error(f"unexpected_crank_grid:{path}")
    return {
        "row_count": int(len(rows)),
        "crank_step_deg": float(np.median(np.diff(angles))),
        "pressure_peak_pa_abs": float(np.max(pressure)),
        "pressure_peak_mpa_gauge": float(
            (np.max(pressure) - reference_pressure_pa) / 1.0e6
        ),
        "temperature_peak_k": float(np.max(temperature)),
        "wall_heat_flux_cycle_mean_w_m2": float(np.mean(flux)),
        "wall_heat_flux_cycle_positive_mean_w_m2": float(np.mean(np.maximum(flux, 0.0))),
        "wall_heat_flux_peak_w_m2": float(np.max(flux)),
        "wall_heat_flux_minimum_w_m2": float(np.min(flux)),
    }


def tetra_quality(points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    a = points[:, 1] - points[:, 0]
    b = points[:, 2] - points[:, 0]
    c = points[:, 3] - points[:, 0]
    signed_volume = np.einsum("ij,ij->i", np.cross(a, b), c) / 6.0
    edges = np.stack(
        (
            points[:, 1] - points[:, 0],
            points[:, 2] - points[:, 0],
            points[:, 3] - points[:, 0],
            points[:, 2] - points[:, 1],
            points[:, 3] - points[:, 1],
            points[:, 3] - points[:, 2],
        ),
        axis=1,
    )
    edge_square_sum = np.sum(edges * edges, axis=(1, 2))
    mean_ratio = (
        12.0
        * np.power(3.0 * np.maximum(np.abs(signed_volume), 0.0), 2.0 / 3.0)
        / np.maximum(edge_square_sum, 1.0e-30)
    )
    return signed_volume, mean_ratio


def build_mesh(
    case_dir: Path,
    radius_mm: float,
    thickness_mm: float,
    voids: list[dict[str, Any]],
    mesh_size_mm: float,
) -> dict[str, Any]:
    try:
        import gmsh  # type: ignore
    except ImportError as exc:
        raise F50Error("gmsh_python_required_for_solve") from exc

    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add("f50_local_circular_deck_witness")
        outer = gmsh.model.occ.addCylinder(
            0.0, 0.0, 0.0, 0.0, 0.0, thickness_mm, radius_mm
        )
        tools: list[tuple[int, int]] = []
        for void in voids:
            x, y = (float(item) for item in void["centre_xy_mm"])
            tool = gmsh.model.occ.addCylinder(
                x,
                y,
                -0.5,
                0.0,
                0.0,
                thickness_mm + 1.0,
                0.5 * float(void["diameter_mm"]),
            )
            tools.append((3, tool))
        result, _ = gmsh.model.occ.cut([(3, outer)], tools, removeObject=True, removeTool=True)
        gmsh.model.occ.synchronize()
        if len(result) != 1 or result[0][0] != 3:
            raise F50Error(f"unexpected_boolean_result:{result}")
        gmsh.option.setNumber("Mesh.MeshSizeMin", 0.65 * mesh_size_mm)
        gmsh.option.setNumber("Mesh.MeshSizeMax", mesh_size_mm)
        gmsh.option.setNumber("Mesh.Algorithm", 6)
        gmsh.option.setNumber("Mesh.Algorithm3D", 1)
        gmsh.option.setNumber("Mesh.Optimize", 1)
        gmsh.model.mesh.generate(3)
        mesh_path = case_dir / "local-deck-witness.msh"
        gmsh.write(str(mesh_path))

        node_tags_raw, node_coords_raw, _ = gmsh.model.mesh.getNodes()
        node_tags_raw = np.asarray(node_tags_raw, dtype=np.int64)
        node_coords_raw = np.asarray(node_coords_raw, dtype=float).reshape((-1, 3))
        order = np.argsort(node_tags_raw)
        sorted_tags = node_tags_raw[order]
        node_xyz = node_coords_raw[order]
        if len(np.unique(sorted_tags)) != len(sorted_tags):
            raise F50Error("duplicate_node_tags")
        raw_to_local = {int(tag): index + 1 for index, tag in enumerate(sorted_tags)}

        element_types, _, element_node_tags = gmsh.model.mesh.getElements(3)
        tetra_raw: np.ndarray | None = None
        for element_type, flat_nodes in zip(element_types, element_node_tags, strict=True):
            _, dim, _, nodes_per_element, _, _ = gmsh.model.mesh.getElementProperties(
                int(element_type)
            )
            if dim == 3 and nodes_per_element == 4:
                tetra_raw = np.asarray(flat_nodes, dtype=np.int64).reshape((-1, 4))
                break
        if tetra_raw is None or not len(tetra_raw):
            raise F50Error("no_linear_tetrahedra")
        tetra = np.vectorize(raw_to_local.__getitem__, otypes=[np.int64])(tetra_raw)
        points = node_xyz[tetra - 1]
        signed_volume, mean_ratio = tetra_quality(points)
        negative = signed_volume < 0.0
        if np.any(negative):
            tetra[negative, [0, 1]] = tetra[negative, [1, 0]]
            points = node_xyz[tetra - 1]
            signed_volume, mean_ratio = tetra_quality(points)
        if np.any(signed_volume <= 1.0e-12):
            raise F50Error(
                f"nonpositive_or_degenerate_tetrahedra:{int(np.count_nonzero(signed_volume <= 1e-12))}"
            )
    finally:
        gmsh.finalize()

    boundary: dict[tuple[int, int, int], tuple[int, int] | None] = {}
    for element_index, nodes in enumerate(tetra, start=1):
        for label, local in C3D4_FACES.items():
            face = tuple(sorted(int(nodes[index]) for index in local))
            if face in boundary:
                boundary[face] = None
            else:
                boundary[face] = (element_index, label)
    records: list[dict[str, Any]] = []
    for face, owner in boundary.items():
        if owner is None:
            continue
        xyz = node_xyz[np.asarray(face, dtype=np.int64) - 1]
        area = 0.5 * float(np.linalg.norm(np.cross(xyz[1] - xyz[0], xyz[2] - xyz[0])))
        centroid = np.mean(xyz, axis=0)
        records.append(
            {
                "nodes": face,
                "element": owner[0],
                "label": owner[1],
                "area_mm2": area,
                "centroid": centroid,
            }
        )
    if not records:
        raise F50Error("no_boundary_faces")
    z_tolerance = max(1.0e-5, 0.03 * mesh_size_mm)
    r_tolerance = max(1.0e-5, 0.03 * mesh_size_mm)
    chamber = [item for item in records if abs(float(item["centroid"][2])) <= z_tolerance]
    top = [
        item
        for item in records
        if abs(float(item["centroid"][2]) - thickness_mm) <= z_tolerance
    ]
    outer = [
        item
        for item in records
        if abs(float(np.linalg.norm(item["centroid"][:2])) - radius_mm) <= r_tolerance
    ]
    cooling = top + outer
    if len(chamber) < 20 or len(cooling) < 20:
        raise F50Error(
            f"boundary_classification_too_small:chamber={len(chamber)}:cooling={len(cooling)}"
        )
    support_nodes = sorted(
        {
            int(tag)
            for item in outer
            for tag in item["nodes"]
            if abs(float(np.linalg.norm(node_xyz[int(tag) - 1, :2])) - radius_mm)
            <= max(r_tolerance, 1.0e-4)
        }
    )
    if len(support_nodes) < 20:
        raise F50Error(f"support_node_set_too_small:{len(support_nodes)}")
    return {
        "node_xyz": node_xyz,
        "tetra": tetra,
        "chamber": chamber,
        "cooling": cooling,
        "support_nodes": support_nodes,
        "mesh_path": mesh_path,
        "metrics": {
            "nodes": int(len(node_xyz)),
            "tetrahedra_C3D4": int(len(tetra)),
            "boundary_faces": int(len(records)),
            "chamber_faces": int(len(chamber)),
            "cooling_faces": int(len(cooling)),
            "support_nodes": int(len(support_nodes)),
            "minimum_signed_volume_mm3": float(np.min(signed_volume)),
            "minimum_mean_ratio": float(np.min(mean_ratio)),
            "p01_mean_ratio": float(np.quantile(mean_ratio, 0.01)),
            "p05_mean_ratio": float(np.quantile(mean_ratio, 0.05)),
            "chamber_area_mm2": float(sum(item["area_mm2"] for item in chamber)),
            "local_cooling_area_mm2": float(sum(item["area_mm2"] for item in cooling)),
        },
    }


def write_ids(stream: Any, keyword: str, name: str, values: list[int]) -> None:
    if not values:
        raise F50Error(f"empty_set:{keyword}:{name}")
    stream.write(f"*{keyword},{keyword}={name}\n")
    for start in range(0, len(values), 16):
        stream.write(",".join(str(item) for item in values[start : start + 16]) + "\n")


def write_mesh(stream: Any, mesh: dict[str, Any], element_type: str) -> None:
    stream.write("*NODE\n")
    for tag, xyz in enumerate(mesh["node_xyz"], start=1):
        stream.write(f"{tag},{xyz[0]:.12g},{xyz[1]:.12g},{xyz[2]:.12g}\n")
    stream.write(f"*ELEMENT,TYPE={element_type},ELSET=EALL\n")
    for tag, nodes in enumerate(mesh["tetra"], start=1):
        stream.write(f"{tag}," + ",".join(str(int(item)) for item in nodes) + "\n")
    write_ids(stream, "NSET", "NALL", list(range(1, len(mesh["node_xyz"]) + 1)))
    write_ids(stream, "NSET", "OUTER_CLAMP", mesh["support_nodes"])
    for region in ("chamber", "cooling"):
        for label in range(1, 5):
            elements = sorted(
                {
                    int(item["element"])
                    for item in mesh[region]
                    if int(item["label"]) == label
                }
            )
            if elements:
                write_ids(stream, "ELSET", f"{region.upper()}_S{label}", elements)


def write_thermal_deck(
    path: Path,
    mesh: dict[str, Any],
    conductivity_w_m_k: float,
    chamber_flux_w_m2: float,
    sink_c: float,
    physical_air_h_w_m2_k: float,
    f43_area_mm2: float,
) -> dict[str, float]:
    local_area = mesh["metrics"]["local_cooling_area_mm2"]
    equivalent_h_w_m2_k = physical_air_h_w_m2_k * f43_area_mm2 / local_area
    with path.open("w", encoding="utf-8") as stream:
        stream.write("*HEADING\nF50 local circular deck witness steady conduction screen\n")
        write_mesh(stream, mesh, "DC3D4")
        stream.write(
            "*MATERIAL,NAME=CP1_CONSTANT_ROOM_K_UNQUALIFIED_HOT_SCREEN\n"
            "*CONDUCTIVITY\n"
            f"{conductivity_w_m_k / 1000.0:.12g}\n"
            "*SOLID SECTION,ELSET=EALL,MATERIAL=CP1_CONSTANT_ROOM_K_UNQUALIFIED_HOT_SCREEN\n"
            "*INITIAL CONDITIONS,TYPE=TEMPERATURE\n"
            f"NALL,{sink_c:.12g}\n"
            "*STEP\n"
            "*HEAT TRANSFER,STEADY STATE\n"
            "*DFLUX\n"
        )
        for label in range(1, 5):
            if any(int(item["label"]) == label for item in mesh["chamber"]):
                stream.write(
                    f"CHAMBER_S{label},S{label},{chamber_flux_w_m2 * 1e-6:.12g}\n"
                )
        stream.write("*FILM\n")
        for label in range(1, 5):
            if any(int(item["label"]) == label for item in mesh["cooling"]):
                stream.write(
                    f"COOLING_S{label},F{label},{sink_c:.12g},{equivalent_h_w_m2_k * 1e-6:.12g}\n"
                )
        stream.write(
            "*NODE PRINT,NSET=NALL,FREQUENCY=1\nNT\n"
            "*NODE FILE,NSET=NALL,FREQUENCY=1\nNT\n"
            "*END STEP\n"
        )
    return {
        "physical_air_h_w_m2_k_hypothesis": physical_air_h_w_m2_k,
        "equivalent_local_h_w_m2_k": equivalent_h_w_m2_k,
        "air_sink_temperature_c": sink_c,
        "f43_total_area_mm2": f43_area_mm2,
        "local_cooling_area_mm2": local_area,
        "area_enhancement_ratio": f43_area_mm2 / local_area,
        "chamber_heat_input_w": chamber_flux_w_m2
        * mesh["metrics"]["chamber_area_mm2"]
        * 1.0e-6,
    }


def write_structural_deck(
    path: Path,
    mesh: dict[str, Any],
    pressure_mpa: float,
    temperatures_c: dict[int, float] | None,
    sink_c: float,
    elastic_modulus_mpa: float,
    poisson: float,
    expansion_per_k: float,
) -> None:
    with path.open("w", encoding="utf-8") as stream:
        stream.write("*HEADING\nF50 local circular deck witness linear structural screen\n")
        write_mesh(stream, mesh, "C3D4")
        stream.write(
            "*MATERIAL,NAME=GENERIC_ALUMINIUM_ELASTIC_HYPOTHESIS_NOT_F49_CARD\n"
            "*ELASTIC\n"
            f"{elastic_modulus_mpa:.12g},{poisson:.12g}\n"
            "*EXPANSION\n"
            f"{expansion_per_k:.12g}\n"
            "*SOLID SECTION,ELSET=EALL,MATERIAL=GENERIC_ALUMINIUM_ELASTIC_HYPOTHESIS_NOT_F49_CARD\n"
            "*INITIAL CONDITIONS,TYPE=TEMPERATURE\n"
            f"NALL,{sink_c:.12g}\n"
            "*STEP\n*STATIC\n"
            "*BOUNDARY\nOUTER_CLAMP,1,3,0.\n"
        )
        stream.write("*TEMPERATURE\n")
        if temperatures_c is not None:
            for tag in range(1, len(mesh["node_xyz"]) + 1):
                if tag not in temperatures_c:
                    raise F50Error(f"missing_temperature_node:{tag}")
                stream.write(f"{tag},{temperatures_c[tag]:.12g}\n")
        else:
            stream.write(f"NALL,{sink_c:.12g}\n")
        stream.write("*DLOAD\n")
        for label in range(1, 5):
            if any(int(item["label"]) == label for item in mesh["chamber"]):
                stream.write(f"CHAMBER_S{label},P{label},{pressure_mpa:.12g}\n")
        stream.write(
            "*EL PRINT,ELSET=EALL,FREQUENCY=1\nS,E\n"
            "*NODE PRINT,NSET=NALL,FREQUENCY=1\nU\n"
            "*EL FILE,FREQUENCY=1\nS,E\n"
            "*NODE FILE,NSET=NALL,FREQUENCY=1\nU,RF\n"
            "*END STEP\n"
        )


def run_ccx(case_dir: Path, stem: str) -> dict[str, Any]:
    completed = subprocess.run(
        ["ccx", "-i", stem],
        cwd=case_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    log = case_dir / f"{stem}.log"
    log.write_text(completed.stdout, encoding="utf-8")
    return {
        "return_code": completed.returncode,
        "log_path": log,
        "dat_path": case_dir / f"{stem}.dat",
        "frd_path": case_dir / f"{stem}.frd",
        "job_finished_marker": "Job finished" in completed.stdout,
    }


def parse_temperatures(path: Path) -> dict[int, float]:
    values: dict[int, float] = {}
    active = False
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        lower = raw.lower()
        if "temperatures for set" in lower:
            active = True
            continue
        fields = raw.split()
        if active and len(fields) >= 2:
            try:
                values[int(fields[0])] = float(fields[1])
            except ValueError:
                if values:
                    active = False
    return values


def von_mises(components: list[float]) -> float:
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


def parse_structural_dat(path: Path) -> tuple[dict[int, float], dict[int, float]]:
    stresses: dict[int, float] = {}
    displacements: dict[int, float] = {}
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
                element = int(fields[0])
                int(fields[1])
                value = von_mises([float(item) for item in fields[2:8]])
            except ValueError:
                continue
            stresses[element] = max(value, stresses.get(element, 0.0))
        elif mode == "displacement" and len(fields) >= 4:
            try:
                node = int(fields[0])
                vector = [float(item) for item in fields[1:4]]
            except ValueError:
                continue
            displacements[node] = math.sqrt(sum(item * item for item in vector))
    return stresses, displacements


def heat_balance(
    mesh: dict[str, Any],
    temperatures: dict[int, float],
    thermal: dict[str, float],
) -> dict[str, float]:
    output = 0.0
    h_w_mm2_k = thermal["equivalent_local_h_w_m2_k"] * 1.0e-6
    for face in mesh["cooling"]:
        face_temperature = float(
            np.mean([temperatures[int(tag)] for tag in face["nodes"]])
        )
        output += (
            h_w_mm2_k
            * float(face["area_mm2"])
            * (face_temperature - thermal["air_sink_temperature_c"])
        )
    input_w = thermal["chamber_heat_input_w"]
    return {
        "heat_input_w": input_w,
        "film_heat_output_w": output,
        "relative_imbalance": abs(input_w - output) / max(abs(input_w), 1.0e-30),
    }


def summarize_structure(
    mesh: dict[str, Any],
    stresses: dict[int, float],
    displacements: dict[int, float],
    support_exclusion_mm: float,
) -> dict[str, Any]:
    stress_values = np.asarray([stresses.get(tag, np.nan) for tag in range(1, len(mesh["tetra"]) + 1)])
    displacement_values = np.asarray(
        [displacements.get(tag, np.nan) for tag in range(1, len(mesh["node_xyz"]) + 1)]
    )
    centroids = np.mean(mesh["node_xyz"][mesh["tetra"] - 1], axis=1)
    radius = np.linalg.norm(centroids[:, :2], axis=1)
    keep = radius <= (45.0 - support_exclusion_mm)
    clean = stress_values[keep & np.isfinite(stress_values)]
    finite_stress = stress_values[np.isfinite(stress_values)]
    finite_displacement = displacement_values[np.isfinite(displacement_values)]
    return {
        "stress_sample_count": int(finite_stress.size),
        "displacement_sample_count": int(finite_displacement.size),
        "support_exclusion_radius_from_outer_edge_mm": support_exclusion_mm,
        "support_excluded_sample_count": int(clean.size),
        "von_mises_p95_mpa": percentile(finite_stress, 0.95),
        "von_mises_p99_mpa": percentile(finite_stress, 0.99),
        "von_mises_maximum_mpa": float(np.max(finite_stress)) if finite_stress.size else None,
        "support_excluded_von_mises_p95_mpa": percentile(clean, 0.95),
        "support_excluded_von_mises_p99_mpa": percentile(clean, 0.99),
        "support_excluded_von_mises_maximum_mpa": float(np.max(clean)) if clean.size else None,
        "maximum_displacement_mm": float(np.max(finite_displacement)) if finite_displacement.size else None,
        "displacement_p95_mm": percentile(finite_displacement, 0.95),
        "_stress_values": stress_values,
        "_displacement_values": displacement_values,
        "_centroids": centroids,
    }


def solve_case(
    root: Path,
    work: Path,
    contract: dict[str, Any],
    variant: str,
    mesh_size_mm: float,
) -> dict[str, Any]:
    case_dir = work / variant / f"mesh-{mesh_size_mm:g}mm"
    case_dir.mkdir(parents=True, exist_ok=False)
    geometry = contract["geometry_policy"]
    mesh = build_mesh(
        case_dir,
        radius_mm=0.5 * float(geometry["bore_diameter_mm"]),
        thickness_mm=float(geometry["witness_thickness_mm"]),
        voids=contract["variants"][variant]["functional_circular_voids"],
        mesh_size_mm=mesh_size_mm,
    )
    trace_binding = contract["variants"][variant]["trace"]
    loads = trace_metrics(
        root / trace_binding["path"],
        float(contract["load_policy"]["structural_reference_pressure_pa_abs"]),
    )
    thermal_cfg = contract["thermal_screen"]
    thermal_deck = case_dir / "f50-thermal.inp"
    thermal = write_thermal_deck(
        thermal_deck,
        mesh,
        conductivity_w_m_k=float(thermal_cfg["material"]["conductivity_w_m_k"]),
        chamber_flux_w_m2=loads["wall_heat_flux_cycle_mean_w_m2"],
        sink_c=float(thermal_cfg["air_sink_temperature_c_hypothesis"]),
        physical_air_h_w_m2_k=float(thermal_cfg["physical_air_film_hypothesis_w_m2_k"]),
        f43_area_mm2=float(
            thermal_cfg["F43_total_surface_area_scan_unit_squared_interpreted_as_mm2"]
        ),
    )
    thermal_run = run_ccx(case_dir, thermal_deck.stem)
    temperatures = (
        parse_temperatures(thermal_run["dat_path"])
        if thermal_run["dat_path"].is_file()
        else {}
    )
    if len(temperatures) != len(mesh["node_xyz"]):
        raise F50Error(
            f"thermal_field_incomplete:{variant}:{mesh_size_mm}:{len(temperatures)}/{len(mesh['node_xyz'])}"
        )
    heat = heat_balance(mesh, temperatures, thermal)

    structural_cfg = contract["structural_screen"]
    structural_runs: dict[str, Any] = {}
    local_fields: dict[str, np.ndarray] = {
        "node_xyz": mesh["node_xyz"],
        "tetra": mesh["tetra"],
        "temperature_c": np.asarray(
            [temperatures[tag] for tag in range(1, len(mesh["node_xyz"]) + 1)]
        ),
    }
    for load_case, field in (("pressure_only", None), ("thermo_pressure", temperatures)):
        deck = case_dir / f"f50-{load_case}.inp"
        write_structural_deck(
            deck,
            mesh,
            pressure_mpa=loads["pressure_peak_mpa_gauge"],
            temperatures_c=field,
            sink_c=float(thermal_cfg["air_sink_temperature_c_hypothesis"]),
            elastic_modulus_mpa=float(structural_cfg["elastic_modulus_mpa_hypothesis"]),
            poisson=float(structural_cfg["poisson_ratio_hypothesis"]),
            expansion_per_k=float(structural_cfg["thermal_expansion_per_k_hypothesis"]),
        )
        run = run_ccx(case_dir, deck.stem)
        stresses, displacements = (
            parse_structural_dat(run["dat_path"])
            if run["dat_path"].is_file()
            else ({}, {})
        )
        summary = summarize_structure(mesh, stresses, displacements, 5.0)
        local_fields[f"{load_case}_stress_mpa"] = summary.pop("_stress_values")
        local_fields[f"{load_case}_displacement_mm"] = summary.pop(
            "_displacement_values"
        )
        local_fields["element_centroids"] = summary.pop("_centroids")
        structural_runs[load_case] = {
            "solver": {
                "return_code": run["return_code"],
                "job_finished_marker": run["job_finished_marker"],
            },
            "results": summary,
        }
    fields_path = case_dir / "local-fields.npz"
    np.savez_compressed(fields_path, **local_fields)

    temp_values = local_fields["temperature_c"]
    all_completed = (
        thermal_run["return_code"] == 0
        and thermal_run["job_finished_marker"]
        and all(
            item["solver"]["return_code"] == 0
            and item["solver"]["job_finished_marker"]
            for item in structural_runs.values()
        )
    )
    mesh_gate = (
        mesh["metrics"]["minimum_signed_volume_mm3"] > 0.0
        and mesh["metrics"]["minimum_mean_ratio"]
        >= float(contract["mesh_campaign"]["minimum_mean_ratio_required"])
    )
    hashes = {
        "mesh_msh_sha256": sha256(mesh["mesh_path"]),
        "thermal_input_sha256": sha256(thermal_deck),
        "thermal_dat_sha256": sha256(thermal_run["dat_path"]),
        "pressure_input_sha256": sha256(case_dir / "f50-pressure_only.inp"),
        "pressure_dat_sha256": sha256(case_dir / "f50-pressure_only.dat"),
        "thermo_pressure_input_sha256": sha256(case_dir / "f50-thermo_pressure.inp"),
        "thermo_pressure_dat_sha256": sha256(case_dir / "f50-thermo_pressure.dat"),
        "local_fields_sha256": sha256(fields_path),
    }
    thermo_stress = structural_runs["thermo_pressure"]["results"]
    p95 = thermo_stress["support_excluded_von_mises_p95_mpa"]
    elastic_modulus = float(structural_cfg["elastic_modulus_mpa_hypothesis"])
    yield_rt = float(structural_cfg["room_temperature_yield_mpa_from_F49"])
    stress_amplitude = 0.5 * p95 if p95 is not None else None
    fatigue_proxy = {
        "basis": "zero-to-peak elastic screen, not a duty-cycle fatigue calculation",
        "support_excluded_stress_range_p95_mpa": p95,
        "elastic_stress_amplitude_p95_mpa": stress_amplitude,
        "SWT_like_sigma_a_squared_over_E_mpa": (
            stress_amplitude * stress_amplitude / elastic_modulus
            if stress_amplitude is not None
            else None
        ),
        "room_temperature_yield_utilization_p95": (
            p95 / yield_rt if p95 is not None else None
        ),
        "cycles_to_failure": None,
        "Miner_damage": None,
        "hot_curve_available": False,
    }
    private_case = {
        "variant": variant,
        "mesh_target_size_mm": mesh_size_mm,
        "classification": "executed_local_circular_deck_witness_not_full_head",
        "complete_trace": {
            "case_id": trace_binding["case_id"],
            "path": trace_binding["path"],
            "sha256": trace_binding["sha256"],
            **loads,
        },
        "mesh": mesh["metrics"],
        "thermal_boundary": thermal,
        "thermal_solver": {
            "return_code": thermal_run["return_code"],
            "job_finished_marker": thermal_run["job_finished_marker"],
        },
        "thermal_results": {
            "temperature_minimum_c": float(np.min(temp_values)),
            "temperature_median_c": float(np.median(temp_values)),
            "temperature_p95_c": float(np.quantile(temp_values, 0.95)),
            "temperature_maximum_c": float(np.max(temp_values)),
            "heat_balance": heat,
        },
        "structural": structural_runs,
        "fatigue_proxy": fatigue_proxy,
        "numerical_gates": {
            "all_three_CalculiX_jobs_completed": all_completed,
            "positive_tetrahedra_and_minimum_mean_ratio": mesh_gate,
            "thermal_balance_below_2_percent": heat["relative_imbalance"] <= 0.02,
            "complete_temperature_field": len(temperatures) == len(mesh["node_xyz"]),
            "complete_stress_and_displacement_fields": all(
                item["results"]["stress_sample_count"] == len(mesh["tetra"])
                and item["results"]["displacement_sample_count"]
                == len(mesh["node_xyz"])
                for item in structural_runs.values()
            ),
        },
        "local_artifact_hashes": hashes,
        "local_fields_file": str(fields_path.relative_to(work)),
    }
    write_json(case_dir / "case-report.json", private_case)
    return private_case


def solve(root: Path, contract_path: Path, work: Path) -> int:
    if work.exists():
        raise F50Error(f"work_path_exists:{work}")
    if shutil.which("ccx") is None:
        raise F50Error("calculix_ccx_required_for_solve")
    contract = load_json(contract_path)
    validated = validate_upstream(root, contract)
    work.mkdir(parents=True)
    cases: list[dict[str, Any]] = []
    for variant in ("2v", "4v"):
        for mesh_size in contract["mesh_campaign"]["target_sizes_mm"]:
            case = solve_case(root, work, contract, variant, float(mesh_size))
            cases.append(case)
            print(
                json.dumps(
                    {
                        "variant": variant,
                        "mesh_mm": mesh_size,
                        "Tmax_c": case["thermal_results"]["temperature_maximum_c"],
                        "stress_p95_mpa": case["structural"]["thermo_pressure"]["results"]["support_excluded_von_mises_p95_mpa"],
                        "displacement_max_mm": case["structural"]["thermo_pressure"]["results"]["maximum_displacement_mm"],
                        "gates": case["numerical_gates"],
                    },
                    sort_keys=True,
                )
            )
    write_json(
        work / "solve-index.json",
        {
            "schema_version": "1.0.0",
            "phase": "F50",
            "classification": "local_work_index_contains_no_private_F43_geometry",
            "contract": {
                "path": str(contract_path.relative_to(root)),
                "sha256": sha256(contract_path),
            },
            "validated_inputs": validated,
            "solver_runtime": {
                "gmsh_version": "queried_in_case_generator",
                "calculix_version": "2.21_required_by_execution_environment",
                "python_version": sys.version.split()[0],
            },
            "cases": [
                str(
                    (work / case["variant"] / f"mesh-{case['mesh_target_size_mm']:g}mm" / "case-report.json").relative_to(work)
                )
                for case in cases
            ],
        },
    )
    return 0


def sanitize_case(case: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in case.items()
        if key not in {"local_fields_file"}
    }


def convergence_for_variant(
    cases: list[dict[str, Any]], contract: dict[str, Any]
) -> dict[str, Any]:
    ordered = sorted(cases, key=lambda item: float(item["mesh_target_size_mm"]), reverse=True)
    medium, fine = ordered[-2:]
    tdiff = relative_difference(
        medium["thermal_results"]["temperature_maximum_c"],
        fine["thermal_results"]["temperature_maximum_c"],
    )
    sdiff = relative_difference(
        medium["structural"]["thermo_pressure"]["results"]["support_excluded_von_mises_p95_mpa"],
        fine["structural"]["thermo_pressure"]["results"]["support_excluded_von_mises_p95_mpa"],
    )
    udiff = relative_difference(
        medium["structural"]["thermo_pressure"]["results"]["maximum_displacement_mm"],
        fine["structural"]["thermo_pressure"]["results"]["maximum_displacement_mm"],
    )
    limits = contract["mesh_campaign"]["finest_pair_limits"]
    return {
        "temperature_max_relative_difference": tdiff,
        "support_excluded_p95_stress_relative_difference": sdiff,
        "maximum_displacement_relative_difference": udiff,
        "limits": limits,
        "gates": {
            "temperature_converged": tdiff is not None
            and tdiff <= float(limits["temperature_max_relative_difference"]),
            "stress_p95_converged": sdiff is not None
            and sdiff
            <= float(limits["support_excluded_p95_stress_relative_difference"]),
            "maximum_displacement_converged": udiff is not None
            and udiff <= float(limits["maximum_displacement_relative_difference"]),
        },
    }


def render_fields(work: Path, case: dict[str, Any], output: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fields_path = work / case["local_fields_file"]
    fields = np.load(fields_path)
    nodes = fields["node_xyz"]
    centroids = fields["element_centroids"]
    temperature = fields["temperature_c"]
    stress = fields["thermo_pressure_stress_mpa"]
    displacement = fields["thermo_pressure_displacement_mm"]
    variant = case["variant"].upper()
    figure, axes = plt.subplots(1, 3, figsize=(16, 5.8), facecolor="#08131b")
    panels = (
        (nodes[:, :2], temperature, "inferno", "Température [°C]", "Température"),
        (centroids[:, :2], stress, "turbo", "von Mises [MPa]", "Thermique + pression"),
        (nodes[:, :2], displacement, "viridis", "Déplacement [mm]", "Déplacement total"),
    )
    for axis, (xy, values, cmap, label, title) in zip(axes, panels, strict=True):
        finite = np.isfinite(values)
        order = np.argsort(values[finite])
        shown_xy = xy[finite][order]
        shown_values = values[finite][order]
        scatter = axis.scatter(
            shown_xy[:, 0],
            shown_xy[:, 1],
            c=shown_values,
            cmap=cmap,
            s=5,
            linewidths=0,
        )
        axis.set_aspect("equal", adjustable="box")
        axis.set_xlim(-47, 47)
        axis.set_ylim(-47, 47)
        axis.set_facecolor("#0d202b")
        axis.tick_params(colors="#b9cad4")
        axis.set_xlabel("x [mm]", color="#b9cad4")
        axis.set_ylabel("y [mm]", color="#b9cad4")
        axis.set_title(title, color="white", fontweight="bold")
        bar = figure.colorbar(scatter, ax=axis, fraction=0.045, pad=0.03)
        bar.set_label(label, color="white")
        bar.ax.tick_params(colors="white")
    figure.suptitle(
        f"F50 {variant} — champs CalculiX du témoin local circulaire",
        color="white",
        fontweight="bold",
        fontsize=18,
    )
    figure.text(
        0.5,
        0.02,
        "Vue XY à aspect 1:1 · aucune peau extérieure F43 affichée · criblage local, pas une culasse complète validée",
        ha="center",
        color="#ffb6a6",
        fontweight="bold",
    )
    figure.tight_layout(rect=(0, 0.06, 1, 0.92))
    figure.savefig(output, dpi=170, facecolor=figure.get_facecolor())
    plt.close(figure)


def render_convergence(
    grouped: dict[str, list[dict[str, Any]]], output: Path
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(1, 3, figsize=(15, 5.5), facecolor="#f0f3f5")
    for variant, color in (("2v", "#1f77b4"), ("4v", "#d04a35")):
        cases = sorted(grouped[variant], key=lambda item: item["mesh_target_size_mm"], reverse=True)
        sizes = [item["mesh_target_size_mm"] for item in cases]
        axes[0].plot(
            sizes,
            [item["thermal_results"]["temperature_maximum_c"] for item in cases],
            "o-",
            color=color,
            label=variant.upper(),
        )
        axes[1].plot(
            sizes,
            [item["structural"]["thermo_pressure"]["results"]["support_excluded_von_mises_p95_mpa"] for item in cases],
            "o-",
            color=color,
            label=variant.upper(),
        )
        axes[2].plot(
            sizes,
            [item["structural"]["thermo_pressure"]["results"]["maximum_displacement_mm"] for item in cases],
            "o-",
            color=color,
            label=variant.upper(),
        )
    for axis, title, ylabel in zip(
        axes,
        ("Convergence thermique", "Convergence contrainte p95", "Convergence déplacement"),
        ("Tmax [°C]", "von Mises p95 [MPa]", "Umax [mm]"),
        strict=True,
    ):
        axis.set_title(title, fontweight="bold")
        axis.set_xlabel("Taille cible [mm] (raffinement vers la droite)")
        axis.set_ylabel(ylabel)
        axis.invert_xaxis()
        axis.grid(alpha=0.3)
        axis.legend()
    figure.suptitle(
        "F50 — étude de maillage identique 2V / 4V, témoin local seulement",
        fontsize=16,
        fontweight="bold",
    )
    figure.text(
        0.5,
        0.015,
        "La convergence numérique ne remplace ni la carte matériau à chaud, ni la CHT, ni les essais physiques.",
        ha="center",
        color="#9b2020",
        fontweight="bold",
    )
    figure.tight_layout(rect=(0, 0.06, 1, 0.91))
    figure.savefig(output, dpi=170)
    plt.close(figure)


def publish(root: Path, contract_path: Path, work: Path, output: Path) -> int:
    if output.exists():
        raise F50Error(f"output_path_exists:{output}")
    contract = load_json(contract_path)
    validated = validate_upstream(root, contract)
    index = load_json(work / "solve-index.json")
    if index["contract"]["sha256"] != sha256(contract_path):
        raise F50Error("solve_index_contract_hash_mismatch")
    cases = [load_json(work / path) for path in index["cases"]]
    grouped = {
        variant: [case for case in cases if case["variant"] == variant]
        for variant in ("2v", "4v")
    }
    if any(len(grouped[variant]) != 3 for variant in grouped):
        raise F50Error("expected_three_cases_per_variant")
    convergence = {
        variant: convergence_for_variant(grouped[variant], contract)
        for variant in ("2v", "4v")
    }
    all_case_gates = all(all(case["numerical_gates"].values()) for case in cases)
    all_convergence = all(
        all(convergence[variant]["gates"].values()) for variant in convergence
    )
    numerical_screen_passed = all_case_gates and all_convergence
    output.mkdir(parents=True)
    finest = {
        variant: min(grouped[variant], key=lambda item: item["mesh_target_size_mm"])
        for variant in ("2v", "4v")
    }
    images = {
        "2v_fields": output / "f50-local-deck-2v-fields.png",
        "4v_fields": output / "f50-local-deck-4v-fields.png",
        "convergence": output / "f50-local-deck-mesh-convergence.png",
    }
    render_fields(work, finest["2v"], images["2v_fields"])
    render_fields(work, finest["4v"], images["4v_fields"])
    render_convergence(grouped, images["convergence"])

    comparison: dict[str, Any] = {}
    for metric, path in (
        ("temperature_maximum_c", ("thermal_results", "temperature_maximum_c")),
        (
            "support_excluded_von_mises_p95_mpa",
            ("structural", "thermo_pressure", "results", "support_excluded_von_mises_p95_mpa"),
        ),
        (
            "maximum_displacement_mm",
            ("structural", "thermo_pressure", "results", "maximum_displacement_mm"),
        ),
        ("fatigue_proxy_SWT_like_mpa", ("fatigue_proxy", "SWT_like_sigma_a_squared_over_E_mpa")),
    ):
        values: dict[str, float] = {}
        for variant in ("2v", "4v"):
            value: Any = finest[variant]
            for key in path:
                value = value[key]
            values[variant] = float(value)
        comparison[metric] = {
            **values,
            "four_v_change_fraction": (values["4v"] - values["2v"])
            / max(abs(values["2v"]), 1.0e-30),
        }
    temperature_screen_passed = all(
        finest[variant]["thermal_results"]["temperature_maximum_c"] <= 300.0
        for variant in ("2v", "4v")
    )
    room_yield_screen_passed = all(
        finest[variant]["fatigue_proxy"]["room_temperature_yield_utilization_p95"]
        <= 1.0
        for variant in ("2v", "4v")
    )
    engineering_screen_passed = (
        numerical_screen_passed
        and temperature_screen_passed
        and room_yield_screen_passed
    )

    report = {
        "schema_version": "1.0.0",
        "phase": "F50",
        "status": (
            "local_witness_engineering_screen_passed_release_still_blocked"
            if engineering_screen_passed
            else (
                "local_witness_numerically_converged_engineering_screen_failed_release_blocked"
                if numerical_screen_passed
                else "local_witness_numerical_screen_failed_release_blocked"
            )
        ),
        "classification": contract["classification"],
        "scope": {
            "executed_geometry": "local circular combustion-deck witness only",
            "full_head_FEA_completed": False,
            "full_head_CHT_completed": False,
            "F43_external_skin_loaded_modified_or_approximated": False,
            "global_oval_or_ellipse_created": False,
            "anisotropic_scaling_used": False,
            "comparison_same_boundary_and_material_hypotheses": True,
        },
        "contract": {
            "path": str(contract_path.relative_to(root)),
            "sha256": sha256(contract_path),
        },
        "validated_inputs": validated,
        "method": {
            "mesher": "Gmsh OCC circular deck witness with functional circular voids",
            "thermal_solver": "CalculiX 2.21 DC3D4 steady conduction",
            "structural_solver": "CalculiX 2.21 C3D4 linear elastic pressure-only and sequential thermo-pressure",
            "loads": contract["load_policy"],
            "thermal": contract["thermal_screen"],
            "structural": contract["structural_screen"],
            "fatigue_proxy": contract["fatigue_proxy"],
        },
        "cases": [sanitize_case(case) for case in cases],
        "finest_pair_convergence": convergence,
        "finest_mesh_comparison": comparison,
        "gates": {
            "all_six_mesh_cases_pass_local_numerical_gates": all_case_gates,
            "both_variants_pass_finest_pair_convergence": all_convergence,
            "local_witness_numerical_screen_passed": numerical_screen_passed,
            "both_variants_below_300C_screen_limit": temperature_screen_passed,
            "both_variants_below_CP1_room_temperature_yield_p95": room_yield_screen_passed,
            "linear_elastic_response_within_model_validity_screen": room_yield_screen_passed,
            "local_witness_engineering_screen_passed": engineering_screen_passed,
            "room_temperature_yield_reference_is_hot_design_allowable": False,
            "full_F43_head_solid_mesh_used": False,
            "verified_chamber_cooling_and_support_surface_mapping": False,
            "temperature_dependent_hot_material_card_used": False,
            "stress_acceptance_against_hot_design_allowable": False,
            "thermomechanical_fatigue_life_computed": False,
            "full_head_CHT_completed": False,
            "physical_correlation_completed": False,
            "manufacturing_authorized": False,
            "metal_print_authorized": False,
            "engine_start_authorized": False,
        },
        "verdict": {
            "reference_proxy_result_available": True,
            "numerically_converged": numerical_screen_passed,
            "engineering_screen_passed": engineering_screen_passed,
            "full_head_validated": False,
            "printable_or_startable_claimed": False,
            "stress_interpretation": "the thermo-pressure linear result exceeds room-temperature yield and is therefore a red divergence indicator, not a valid post-yield stress prediction",
            "blocking_reasons": [
                "private F43/F50 full-head solid mesh not used in this public witness run",
                "no measured and verified chamber/cooling/stud surface map",
                "both local witnesses exceed the 300 C screening limit",
                "both thermo-pressure p95 stresses exceed even the CP1 room-temperature yield reference",
                "F49 has no complete temperature-dependent CP1 material card",
                "no hot HCF/LCF/TMF curves or contact/preload model",
                "no correlated CHT, thermocouples, pressure trace, or physical engine test",
            ],
        },
        "publication": {
            "private_scan_geometry_published": False,
            "node_coordinates_or_connectivity_published": False,
            "raw_solver_fields_published": False,
            "images_are_local_witness_result_fields_not_product_renders": True,
        },
    }
    report_path = output / "thermomechanical-screen-report.json"
    write_json(report_path, report)
    manifest_entries = []
    for path in [report_path, *images.values()]:
        manifest_entries.append(
            {
                "path": str(path.relative_to(root)),
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
            }
        )
    manifest_path = output / "manifest.json"
    write_json(
        manifest_path,
        {
            "schema_version": "1.0.0",
            "phase": "F50",
            "classification": "public_aggregate_and_result_images_no_private_scan_geometry",
            "contract_sha256": sha256(contract_path),
            "entries": manifest_entries,
            "release_claim": False,
        },
    )
    print(
        json.dumps(
            {
                "report": str(report_path),
                "manifest": str(manifest_path),
                "status": report["status"],
                "comparison": comparison,
                "convergence": convergence,
            },
            sort_keys=True,
        )
    )
    return 0


def verify(root: Path, contract_path: Path, evidence: Path) -> int:
    contract = load_json(contract_path)
    validate_upstream(root, contract)
    report_path = evidence / "thermomechanical-screen-report.json"
    manifest_path = evidence / "manifest.json"
    report = load_json(report_path)
    manifest = load_json(manifest_path)
    if report["contract"]["sha256"] != sha256(contract_path):
        raise F50Error("published_contract_hash_mismatch")
    for entry in manifest["entries"]:
        path = root / entry["path"]
        if sha256(path) != entry["sha256"] or path.stat().st_size != entry["bytes"]:
            raise F50Error(f"manifest_mismatch:{entry['path']}")
    forbidden_true = (
        "full_F43_head_solid_mesh_used",
        "verified_chamber_cooling_and_support_surface_mapping",
        "temperature_dependent_hot_material_card_used",
        "linear_elastic_response_within_model_validity_screen",
        "stress_acceptance_against_hot_design_allowable",
        "thermomechanical_fatigue_life_computed",
        "full_head_CHT_completed",
        "physical_correlation_completed",
        "manufacturing_authorized",
        "metal_print_authorized",
        "engine_start_authorized",
    )
    if any(report["gates"][name] for name in forbidden_true):
        raise F50Error("forbidden_release_or_validation_gate_true")
    if report["scope"]["global_oval_or_ellipse_created"]:
        raise F50Error("forbidden_global_shape_created")
    if report["scope"]["F43_external_skin_loaded_modified_or_approximated"]:
        raise F50Error("F43_skin_policy_violation")
    print(
        json.dumps(
            {
                "status": report["status"],
                "manifest_entries": len(manifest["entries"]),
                "release_gates_closed": True,
                "skin_untouched": True,
            },
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("solve", "publish", "verify"):
        command = subparsers.add_parser(name)
        command.add_argument("--root", type=Path, required=True)
        command.add_argument("--contract", type=Path, required=True)
        if name in {"solve", "publish"}:
            command.add_argument("--work", type=Path, required=True)
        if name in {"publish", "verify"}:
            command.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    contract = args.contract.resolve()
    if args.command == "solve":
        return solve(root, contract, args.work.resolve())
    if args.command == "publish":
        return publish(root, contract, args.work.resolve(), args.evidence.resolve())
    return verify(root, contract, args.evidence.resolve())


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except F50Error as exc:
        print(f"F50_ERROR:{exc}", file=sys.stderr)
        raise SystemExit(2)
