#!/usr/bin/env python3
"""Maillage et calcul thermo-mecanique CalculiX de la CAO F34 complete."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from collections import defaultdict
from pathlib import Path

import gmsh


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def chunks(values: list[int], size: int = 16) -> list[list[int]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def write_set(stream, keyword: str, name: str, values: list[int]) -> None:
    stream.write(f"*{keyword},{keyword}={name}\n")
    for row in chunks(values):
        stream.write(",".join(str(value) for value in row) + "\n")


def triangle_area_normal(points: list[tuple[float, float, float]]) -> tuple[float, tuple[float, float, float]]:
    a, b, c = points
    ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    ac = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    cross = (
        ab[1] * ac[2] - ab[2] * ac[1],
        ab[2] * ac[0] - ab[0] * ac[2],
        ab[0] * ac[1] - ab[1] * ac[0],
    )
    magnitude = math.sqrt(sum(value * value for value in cross))
    if magnitude == 0.0:
        return 0.0, (0.0, 0.0, 0.0)
    return 0.5 * magnitude, tuple(value / magnitude for value in cross)


def parse_dat(path: Path) -> tuple[list[float], list[float]]:
    stresses: list[float] = []
    displacements: list[float] = []
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
            von_mises = math.sqrt(
                0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
                + 3.0 * (sxy * sxy + sxz * sxz + syz * syz)
            )
            stresses.append(von_mises)
        elif mode == "displacement" and len(fields) >= 4:
            try:
                int(fields[0])
                values = list(map(float, fields[1:4]))
            except ValueError:
                continue
            displacements.append(math.sqrt(sum(value * value for value in values)))
    return stresses, displacements


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return math.nan
    return ordered[min(len(ordered) - 1, int(fraction * (len(ordered) - 1)))]


def run(step: Path, output: Path, mesh_size_mm: float, pressure_mpa: float) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 1)
        gmsh.option.setNumber("Geometry.OCCFixSmallEdges", 1)
        gmsh.option.setNumber("Geometry.OCCFixSmallFaces", 1)
        gmsh.model.add("f34_calculix")
        gmsh.model.occ.importShapes(str(step))
        gmsh.model.occ.synchronize()
        gmsh.option.setNumber("Mesh.MeshSizeMin", 0.55 * mesh_size_mm)
        gmsh.option.setNumber("Mesh.MeshSizeMax", mesh_size_mm)
        gmsh.option.setNumber("Mesh.Algorithm3D", 1)
        gmsh.model.mesh.generate(3)
        gmsh.model.mesh.optimize("Relocate3D")

        node_tags, coordinates, _ = gmsh.model.mesh.getNodes()
        nodes = {
            int(tag): tuple(float(coordinates[3 * index + axis]) for axis in range(3))
            for index, tag in enumerate(node_tags)
        }
        element_types, element_tags, element_nodes = gmsh.model.mesh.getElements(3)
        tetrahedra: list[tuple[int, tuple[int, int, int, int]]] = []
        next_element = 1
        for element_type, tags, connectivity in zip(element_types, element_tags, element_nodes):
            properties = gmsh.model.mesh.getElementProperties(element_type)
            nodes_per_element = int(properties[3])
            if nodes_per_element != 4:
                continue
            for index, _ in enumerate(tags):
                start = index * nodes_per_element
                tetrahedra.append((next_element, tuple(int(v) for v in connectivity[start : start + 4])))
                next_element += 1

        surface_types, _, surface_nodes = gmsh.model.mesh.getElements(2)
        chamber_depth_mm = 11.5
        chamber_center = (0.0, 0.0, -(57.0 - chamber_depth_mm))
        forces: dict[int, list[float]] = defaultdict(lambda: [0.0, 0.0, 0.0])
        chamber_area_mm2 = 0.0
        chamber_triangles = 0
        for element_type, connectivity in zip(surface_types, surface_nodes):
            properties = gmsh.model.mesh.getElementProperties(element_type)
            nodes_per_element = int(properties[3])
            if nodes_per_element != 3:
                continue
            for start in range(0, len(connectivity), 3):
                tags = [int(value) for value in connectivity[start : start + 3]]
                points = [nodes[tag] for tag in tags]
                centroid = tuple(sum(point[axis] for point in points) / 3.0 for axis in range(3))
                radius = math.sqrt(sum((centroid[axis] - chamber_center[axis]) ** 2 for axis in range(3)))
                radial = math.hypot(centroid[0], centroid[1])
                if not (abs(radius - 57.0) <= 0.35 and centroid[2] <= chamber_depth_mm + 0.1 and radial <= 57.2):
                    continue
                area, _ = triangle_area_normal(points)
                outward = tuple((centroid[axis] - chamber_center[axis]) / radius for axis in range(3))
                chamber_area_mm2 += area
                chamber_triangles += 1
                for tag in tags:
                    for axis in range(3):
                        forces[tag][axis] += pressure_mpa * area * outward[axis] / 3.0
    finally:
        gmsh.finalize()

    support = sorted(tag for tag, point in nodes.items() if point[2] <= 0.02 and 32.0 <= math.hypot(point[0], point[1]) <= 61.0)
    if len(support) < 20 or len(forces) < 20 or not tetrahedra:
        raise RuntimeError("selection CAE insuffisante: support, chambre ou tetraedres")
    anchor = min(support, key=lambda tag: (nodes[tag][0] + 43.0) ** 2 + (nodes[tag][1] + 43.0) ** 2)
    guide = min(support, key=lambda tag: (nodes[tag][0] - 43.0) ** 2 + (nodes[tag][1] + 43.0) ** 2)

    job = output / "head-f34.inp"
    with job.open("w", encoding="utf-8") as stream:
        stream.write("*HEADING\nF34 complete CAD combined thermo-pressure screening\n*NODE\n")
        for tag in sorted(nodes):
            x, y, z = nodes[tag]
            stream.write(f"{tag},{x:.9g},{y:.9g},{z:.9g}\n")
        stream.write("*ELEMENT,TYPE=C3D4,ELSET=EALL\n")
        for element, tags in tetrahedra:
            stream.write(f"{element}," + ",".join(str(tag) for tag in tags) + "\n")
        write_set(stream, "NSET", "NALL", sorted(nodes))
        write_set(stream, "NSET", "DECK_SUPPORT", support)
        write_set(stream, "NSET", "ANCHOR", [anchor])
        write_set(stream, "NSET", "GUIDE", [guide])
        stream.write(
            "*MATERIAL,NAME=AHEADD_HT1_SCREEN\n"
            "*ELASTIC\n66000.,0.33\n"
            "*EXPANSION\n2.3e-5\n"
            "*SOLID SECTION,ELSET=EALL,MATERIAL=AHEADD_HT1_SCREEN\n"
            "*INITIAL CONDITIONS,TYPE=TEMPERATURE\nNALL,20.\n"
            "*STEP\n*STATIC\n"
            "*BOUNDARY\nDECK_SUPPORT,3,3\nANCHOR,1,2\nGUIDE,2,2\n"
            "*TEMPERATURE\n"
        )
        for tag in sorted(nodes):
            temperature_c = min(260.0, max(120.0, 260.0 - 1.333333333 * nodes[tag][2]))
            stream.write(f"{tag},{temperature_c:.6g}\n")
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

    completed = subprocess.run(
        ["ccx", "-i", job.stem],
        cwd=output,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    (output / "calculix.log").write_text(completed.stdout, encoding="utf-8")
    dat = output / f"{job.stem}.dat"
    stresses, displacements = parse_dat(dat) if dat.is_file() else ([], [])
    hot_yield_mpa = 216.0
    p95 = percentile(stresses, 0.95)
    report = {
        "schema_version": "1.0.0",
        "phase": "F34",
        "status": "completed_screening" if completed.returncode == 0 and stresses else "failed",
        "classification": "actual_F34_CAD_linear_elastic_combined_thermal_pressure_screen_not_TMF_or_release_FEA",
        "solver": "CalculiX",
        "mesh": {
            "maximum_size_mm": mesh_size_mm,
            "nodes": len(nodes),
            "linear_tetrahedra": len(tetrahedra),
            "chamber_surface_triangles": chamber_triangles,
            "chamber_loaded_area_mm2": chamber_area_mm2,
        },
        "load": {
            "pressure_mpa": pressure_mpa,
            "temperature_c": {"deck": 260.0, "top": 120.0, "reference": 20.0},
            "load_nodes": len(forces),
            "support_nodes": len(support),
        },
        "material": {
            "id": "Constellium_Aheadd_HT1_high_temperature_heat_treatment",
            "hot_yield_mpa_at_250c": hot_yield_mpa,
            "elastic_modulus_mpa_hypothesis": 66000.0,
            "poisson_hypothesis": 0.33,
            "thermal_expansion_per_k_hypothesis": 2.3e-5,
            "hot_elastic_card_qualified": False,
        },
        "results": {
            "stress_samples": len(stresses),
            "von_mises_p95_mpa": p95 if stresses else None,
            "von_mises_max_mpa": max(stresses) if stresses else None,
            "maximum_displacement_mm": max(displacements) if displacements else None,
            "p95_hot_yield_margin": hot_yield_mpa / p95 if stresses and p95 > 0.0 else None,
        },
        "files": {"input_sha256": sha256(job)},
        "release_claim": False,
    }
    (output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True, allow_nan=False))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mesh-size-mm", type=float, required=True)
    parser.add_argument("--pressure-mpa", type=float, required=True)
    args = parser.parse_args()
    report = run(args.step.resolve(), args.output.resolve(), args.mesh_size_mm, args.pressure_mpa)
    return 0 if report["status"] == "completed_screening" else 1


if __name__ == "__main__":
    raise SystemExit(main())
