#!/usr/bin/env python3
"""Calcul thermo-mécanique maillé F38, sans promouvoir une carte matière non qualifiée."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import subprocess

import gmsh

from run_aircooled_calculix_f34 import chunks, parse_dat, percentile, sha256


def chamber_pressure_direction(centroid: tuple[float, float, float], chamber_radius_mm: float) -> tuple[float, float, float] | None:
    x, y, z = centroid
    radial = math.hypot(x, y)
    if 0.0 <= z <= 10.2 and radial <= chamber_radius_mm - 0.2:
        return (0.0, 0.0, 1.0)
    if -9.6 <= z <= 10.2 and abs(radial - chamber_radius_mm) <= 0.55 and radial > 0.0:
        return (x / radial, y / radial, 0.0)
    return None


def triangle_area(points: list[tuple[float, float, float]]) -> float:
    a, b, c = points
    ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    ac = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    cross = (
        ab[1] * ac[2] - ab[2] * ac[1],
        ab[2] * ac[0] - ab[0] * ac[2],
        ab[0] * ac[1] - ab[1] * ac[0],
    )
    return 0.5 * math.sqrt(sum(value * value for value in cross))


def write_set(stream, keyword: str, name: str, values: list[int]) -> None:
    stream.write(f"*{keyword},{keyword}={name}\n")
    for row in chunks(values):
        stream.write(",".join(str(value) for value in row) + "\n")


def run_case(step: Path, output: Path, mesh_size_mm: float, pressure_mpa: float, chamber_diameter_mm: float) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 1)
        gmsh.option.setNumber("Geometry.OCCFixSmallEdges", 1)
        gmsh.option.setNumber("Geometry.OCCFixSmallFaces", 1)
        # Un STEP facetté issu d'un scan contient légitimement des triangles
        # presque coplanaires partageant une arête. La tolérance Gmsh par
        # défaut (0,1°) peut les classer à tort comme facettes superposées.
        # Une valeur stricte conserve le rejet des recouvrements réels tout en
        # permettant la tétraédrisation des plis très faibles du scan.
        gmsh.option.setNumber("Mesh.AngleToleranceFacetOverlap", 1.0e-4)
        gmsh.model.add("f38_head")
        gmsh.model.occ.importShapes(str(step))
        gmsh.model.occ.synchronize()
        gmsh.option.setNumber("Mesh.MeshSizeMin", 0.58 * mesh_size_mm)
        gmsh.option.setNumber("Mesh.MeshSizeMax", mesh_size_mm)
        gmsh.option.setNumber("Mesh.Algorithm3D", 1)
        gmsh.model.mesh.generate(3)
        gmsh.model.mesh.optimize("Relocate3D")
        node_tags, coordinates, _ = gmsh.model.mesh.getNodes()
        nodes = {
            int(tag): tuple(float(coordinates[3 * index + axis]) for axis in range(3))
            for index, tag in enumerate(node_tags)
        }
        tetrahedra = []
        next_element = 1
        for element_type, tags, connectivity in zip(*gmsh.model.mesh.getElements(3)):
            props = gmsh.model.mesh.getElementProperties(element_type)
            count = int(props[3])
            if count != 4:
                continue
            for index, _ in enumerate(tags):
                start = index * count
                tetrahedra.append((next_element, tuple(int(v) for v in connectivity[start:start + count])))
                next_element += 1
        forces: dict[int, list[float]] = defaultdict(lambda: [0.0, 0.0, 0.0])
        loaded_area = 0.0
        loaded_triangles = 0
        for element_type, _, connectivity in zip(*gmsh.model.mesh.getElements(2)):
            props = gmsh.model.mesh.getElementProperties(element_type)
            if int(props[3]) != 3:
                continue
            for start in range(0, len(connectivity), 3):
                tags = [int(v) for v in connectivity[start:start + 3]]
                points = [nodes[tag] for tag in tags]
                centroid = tuple(sum(point[axis] for point in points) / 3.0 for axis in range(3))
                direction = chamber_pressure_direction(centroid, chamber_diameter_mm / 2.0)
                if direction is None:
                    continue
                area = triangle_area(points)
                loaded_area += area
                loaded_triangles += 1
                for tag in tags:
                    for axis in range(3):
                        forces[tag][axis] += pressure_mpa * area * direction[axis] / 3.0
    finally:
        gmsh.finalize()

    min_z = min(point[2] for point in nodes.values())
    support = sorted(tag for tag, point in nodes.items() if point[2] <= min_z + 0.08 and math.hypot(point[0], point[1]) >= chamber_diameter_mm / 2.0 + 3.0)
    if len(support) < 20 or len(forces) < 20 or len(tetrahedra) < 100:
        raise RuntimeError("f38_head_selection_insufficient")
    anchor = min(support, key=lambda tag: nodes[tag][0] ** 2 + nodes[tag][1] ** 2)
    guide = max(support, key=lambda tag: nodes[tag][0])
    job = output / "head-f38.inp"
    with job.open("w", encoding="utf-8") as stream:
        stream.write("*HEADING\nF38 monoblock combined thermo-pressure screen\n*NODE\n")
        for tag in sorted(nodes):
            stream.write(f"{tag},{nodes[tag][0]:.9g},{nodes[tag][1]:.9g},{nodes[tag][2]:.9g}\n")
        stream.write("*ELEMENT,TYPE=C3D4,ELSET=EALL\n")
        for element, tags in tetrahedra:
            stream.write(f"{element}," + ",".join(str(tag) for tag in tags) + "\n")
        write_set(stream, "NSET", "NALL", sorted(nodes))
        write_set(stream, "NSET", "DECK_SUPPORT", support)
        write_set(stream, "NSET", "ANCHOR", [anchor])
        write_set(stream, "NSET", "GUIDE", [guide])
        stream.write(
            "*MATERIAL,NAME=CP1_PROVISIONAL_NOT_QUALIFIED\n*ELASTIC\n70000.,0.33\n"
            "*EXPANSION\n2.2e-5\n*SOLID SECTION,ELSET=EALL,MATERIAL=CP1_PROVISIONAL_NOT_QUALIFIED\n"
            "*INITIAL CONDITIONS,TYPE=TEMPERATURE\nNALL,20.\n*STEP\n*STATIC\n"
            "*BOUNDARY\nDECK_SUPPORT,3,3\nANCHOR,1,2\nGUIDE,2,2\n*TEMPERATURE\n"
        )
        maximum_z = max(point[2] for point in nodes.values())
        for tag in sorted(nodes):
            fraction = min(1.0, max(0.0, (nodes[tag][2] - 10.0) / max(maximum_z - 10.0, 1.0)))
            temperature = 260.0 - 140.0 * fraction
            stream.write(f"{tag},{temperature:.6g}\n")
        stream.write("*CLOAD\n")
        for tag in sorted(forces):
            for dof, value in enumerate(forces[tag], start=1):
                if abs(value) > 1e-12:
                    stream.write(f"{tag},{dof},{value:.9g}\n")
        stream.write("*EL PRINT,ELSET=EALL\nS\n*NODE PRINT,NSET=NALL\nU\n*END STEP\n")

    completed = subprocess.run(["ccx", "-i", job.stem], cwd=output, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    (output / "calculix.log").write_text(completed.stdout, encoding="utf-8")
    dat = output / "head-f38.dat"
    stresses, displacements = parse_dat(dat) if dat.is_file() else ([], [])
    report = {
        "mesh_size_mm": mesh_size_mm,
        "status": "completed" if completed.returncode == 0 and stresses else "failed",
        "mesh": {"nodes": len(nodes), "linear_tetrahedra": len(tetrahedra)},
        "load": {"pressure_mpa": pressure_mpa, "loaded_area_mm2": loaded_area, "loaded_triangles": loaded_triangles, "support_nodes": len(support), "temperature_degC": {"chamber": 260.0, "top": 120.0, "reference": 20.0}},
        "material": {"candidate": "EOS Aluminium Constellium CP1", "elastic_modulus_mpa_provisional": 70000.0, "poisson_provisional": 0.33, "cte_per_k_provisional": 2.2e-5, "hot_coupon_card_qualified": False},
        "results": {"von_mises_p95_mpa": percentile(stresses, .95) if stresses else None, "von_mises_p99_mpa": percentile(stresses, .99) if stresses else None, "von_mises_max_mpa": max(stresses) if stresses else None, "maximum_displacement_mm": max(displacements) if displacements else None},
        "release_claim": False,
    }
    (output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def relative_difference(a: float, b: float) -> float:
    return abs(a - b) / max(abs(a), abs(b), 1e-30)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mesh-sizes-mm", type=float, nargs="+", default=[4.0, 3.0, 2.5])
    parser.add_argument("--pressure-mpa", type=float, default=12.0)
    parser.add_argument("--chamber-diameter-mm", type=float, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    cases = [run_case(args.step.resolve(), args.output / f"mesh-{size:g}mm", size, args.pressure_mpa, args.chamber_diameter_mm) for size in args.mesh_sizes_mm]
    finest_a, finest_b = cases[-2:]
    convergence = {
        "p95_stress_relative_difference": relative_difference(finest_a["results"]["von_mises_p95_mpa"], finest_b["results"]["von_mises_p95_mpa"]),
        "displacement_relative_difference": relative_difference(finest_a["results"]["maximum_displacement_mm"], finest_b["results"]["maximum_displacement_mm"]),
    }
    summary = {
        "schema_version": "1.0.0", "phase": "F38", "status": "linear_thermomechanical_mesh_sequence_complete_release_blocked",
        "classification": "actual_F38_BRep_linear_elastic_combined_pressure_thermal_screen_not_TMF_or_release_FEA",
        "inputs": {"step_sha256": sha256(args.step), "pressure_mpa": args.pressure_mpa, "chamber_diameter_mm": args.chamber_diameter_mm},
        "cases": cases, "finest_pair_convergence": convergence,
        "gates": {"all_cases_completed": all(case["status"] == "completed" for case in cases), "p95_mesh_difference_below_10_percent": convergence["p95_stress_relative_difference"] <= .10, "displacement_mesh_difference_below_5_percent": convergence["displacement_relative_difference"] <= .05, "hot_coupon_material_card_qualified": False, "thermomechanical_fatigue_complete": False, "professional_review_complete": False, "metal_print_authorized": False, "engine_start_authorized": False},
    }
    (args.output / "f38-head-calculix-report.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": summary["status"], "convergence": convergence, "finest": cases[-1]["results"]}, sort_keys=True))
    return 0 if summary["gates"]["all_cases_completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
