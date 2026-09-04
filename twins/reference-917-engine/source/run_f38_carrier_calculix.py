#!/usr/bin/env python3
"""Écran CalculiX trois mailles du porte-axes renforcé F38."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import platform
import shutil
import subprocess
import sys

from run_f37_carrier_calculix import parse_dat, percentile, sha256, write_set


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def prepare_case(step: Path, spec: dict, geometry: dict, case: Path, size: float) -> dict:
    import gmsh

    case.mkdir(parents=True, exist_ok=False)
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 1)
        gmsh.model.add("f38_rounded_reinforced_carrier")
        gmsh.merge(str(step))
        volumes = gmsh.model.getEntities(3)
        require(len(volumes) == 1, f"expected_one_volume_got:{len(volumes)}")
        gmsh.option.setNumber("Mesh.MeshSizeMin", size)
        gmsh.option.setNumber("Mesh.MeshSizeMax", size)
        gmsh.option.setNumber("Mesh.ElementOrder", 1)
        gmsh.option.setNumber("Mesh.Algorithm3D", 10)
        gmsh.model.mesh.generate(3)
        node_tags, coordinates, _ = gmsh.model.mesh.getNodes()
        points = {int(tag): tuple(float(value) for value in coordinates[3 * index:3 * index + 3]) for index, tag in enumerate(node_tags)}
        element_types, element_tags, element_nodes = gmsh.model.mesh.getElements(3)
        elements = []
        for element_type, tags, nodes in zip(element_types, element_tags, element_nodes):
            if int(element_type) != 4:
                continue
            for index, tag in enumerate(tags):
                elements.append((int(tag), tuple(int(item) for item in nodes[4 * index:4 * index + 4])))
        gmsh.write(str(case / "carrier-f38.msh"))
    finally:
        gmsh.finalize()
    require(bool(elements), "no_linear_tetrahedra")

    carrier = spec["carrier"]
    mount_z = float(carrier["mount_interface_z_mm"])
    mount_radius = float(carrier["mount_boss_outer_diameter_mm"]) / 2.0
    studs = [tuple(map(float, item)) for item in geometry["geometry"]["packaging_checks"]["stud_centres_local_mm"]]
    support = [
        tag for tag, (x, y, z) in points.items()
        if z <= mount_z + max(0.25, 0.2 * size)
        and any(math.hypot(x - sx, y - sy) <= mount_radius for sx, sy in studs)
    ]
    axis_z = float(carrier["intake_axis_yz_mm"][1])
    axes_y = (float(carrier["intake_axis_yz_mm"][0]), float(carrier["exhaust_axis_yz_mm"][0]))
    tilts = {axes_y[0]: -18.0, axes_y[1]: 18.0}
    zones = []
    for load_x in (-18.0, 18.0):
        for axis_y in axes_y:
            nodes = [
                tag for tag, (x, y, z) in points.items()
                if abs(x - load_x) <= 7.5 and 6.2 <= math.hypot(y - axis_y, z - axis_z) <= 7.5
            ]
            zones.append({"nodes": nodes, "tilt_y_deg": tilts[axis_y]})
    require(len(support) >= 12, f"insufficient_support_nodes:{len(support)}")
    require(all(len(zone["nodes"]) >= 4 for zone in zones), f"insufficient_load_nodes:{[len(zone['nodes']) for zone in zones]}")

    screen = spec["fea_screen"]
    spring = spec["valvetrain"]["spring"]
    spring_design = float(spring["worst_open_spring_load_per_valve_n"]) * float(screen["dynamic_load_factor"])
    design_load = spring_design * float(screen["pivot_reaction_collinear_upper_envelope_factor"])
    job = case / "carrier-f38.inp"
    with job.open("w", encoding="utf-8") as stream:
        stream.write("*HEADING\nF38 rounded reinforced rocker carrier linear hot-modulus screen\n*NODE\n")
        for tag in sorted(points):
            x, y, z = points[tag]
            stream.write(f"{tag},{x:.9g},{y:.9g},{z:.9g}\n")
        stream.write("*ELEMENT,TYPE=C3D4,ELSET=EALL\n")
        for tag, nodes in elements:
            stream.write(f"{tag}," + ",".join(str(node) for node in nodes) + "\n")
        write_set(stream, "NSET", "NALL", sorted(points))
        write_set(stream, "NSET", "SUPPORT", sorted(support))
        stream.write(
            "*MATERIAL,NAME=2618A_UNQUALIFIED_SCREEN\n*ELASTIC\n"
            f"{float(screen['elastic_modulus_mpa_at_200c_screen']):.9g},{float(screen['poisson_ratio']):.9g}\n"
            "*SOLID SECTION,ELSET=EALL,MATERIAL=2618A_UNQUALIFIED_SCREEN\n*STEP\n*STATIC\n"
            "*BOUNDARY\nSUPPORT,1,3\n*CLOAD\n"
        )
        for zone in zones:
            tilt = math.radians(float(zone["tilt_y_deg"]))
            fy = -design_load * math.sin(tilt) / len(zone["nodes"])
            fz = -design_load * math.cos(tilt) / len(zone["nodes"])
            for tag in sorted(zone["nodes"]):
                stream.write(f"{tag},2,{fy:.9g}\n{tag},3,{fz:.9g}\n")
        stream.write("*EL PRINT,ELSET=EALL\nS\n*NODE PRINT,NSET=NALL\nU\n*END STEP\n")
    return {
        "mesh_size_mm": size,
        "nodes": len(points),
        "elements": len(elements),
        "support_nodes": len(support),
        "load_nodes_per_zone": [len(zone["nodes"]) for zone in zones],
        "spring_only_design_load_per_zone_n": spring_design,
        "design_load_per_zone_n": design_load,
        "load_vectors_yz_n": [[-design_load * math.sin(math.radians(float(zone["tilt_y_deg"]))), -design_load * math.cos(math.radians(float(zone["tilt_y_deg"])))] for zone in zones],
        "actual_resultant_direction_complete": False,
    }


def relative_change(fine: float, previous: float) -> float:
    return abs(fine - previous) / max(abs(fine), 1.0e-12)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--step", type=Path, required=True)
    parser.add_argument("--cad-report", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--geometry-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mesh-sizes", default="2.0,1.5,1.25")
    parser.add_argument("--ccx", default="ccx")
    parser.add_argument("--runtime-image-ref", default="not_recorded")
    parser.add_argument("--runtime-image-id", default="not_recorded")
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    geometry = json.loads(args.geometry_report.read_text(encoding="utf-8"))
    cad = json.loads(args.cad_report.read_text(encoding="utf-8"))
    require(spec["phase"] == "F38" and cad["phase"] == "F38", "f38_phase_required")
    require(cad["inputs"]["spec_sha256"] == sha256(args.spec), "cad_spec_sha256_mismatch")
    carrier_artifact = next(item for item in cad["artifacts"] if item["id"] == "rocker-carrier-f38-rounded-reinforced")
    require(carrier_artifact["step"]["sha256"] == sha256(args.step), "carrier_step_sha256_mismatch")
    require(sha256(args.geometry_report) == spec["parent_evidence"]["f36_geometry_report"]["sha256"], "geometry_sha256_mismatch")
    ccx = shutil.which(args.ccx)
    require(ccx is not None, f"calculix_executable_not_found:{args.ccx}")
    version = subprocess.run([ccx, "-v"], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False).stdout.strip()
    args.output.mkdir(parents=True, exist_ok=True)
    results = []
    for size in [float(item) for item in args.mesh_sizes.split(",")]:
        case = args.output / f"mesh-{str(size).replace('.', 'p')}"
        mesh = prepare_case(args.step, spec, geometry, case, size)
        completed = subprocess.run([ccx, "carrier-f38"], cwd=case, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        (case / "calculix.log").write_text(completed.stdout, encoding="utf-8")
        require(completed.returncode == 0, f"calculix_failed:{size}:{completed.returncode}")
        stresses, displacements = parse_dat(case / "carrier-f38.dat")
        artifacts = {
            path.name: {"bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in (case / "carrier-f38.msh", case / "carrier-f38.inp", case / "carrier-f38.dat", case / "calculix.log")
        }
        results.append({
            "mesh": mesh,
            "command": [ccx, "carrier-f38"],
            "artifacts": artifacts,
            "von_mises_mpa": {"p95": percentile(stresses, 0.95), "p99": percentile(stresses, 0.99), "maximum": max(stresses)},
            "maximum_displacement_mm": max(displacements),
        })
    fine, previous = results[-1], results[-2]
    convergence = {
        "raw_maximum_relative_change": relative_change(fine["von_mises_mpa"]["maximum"], previous["von_mises_mpa"]["maximum"]),
        "p99_relative_change": relative_change(fine["von_mises_mpa"]["p99"], previous["von_mises_mpa"]["p99"]),
        "p95_relative_change": relative_change(fine["von_mises_mpa"]["p95"], previous["von_mises_mpa"]["p95"]),
        "displacement_relative_change": relative_change(fine["maximum_displacement_mm"], previous["maximum_displacement_mm"]),
    }
    target = float(spec["fea_screen"]["raw_maximum_convergence_target_fraction"])
    yield_mpa = float(spec["fea_screen"]["provisional_yield_mpa_at_200c"])
    parent_max = float(spec["parent_evidence"]["f37_calculix_report"]["finest_raw_maximum_mpa"])
    report = {
        "schema_version": "1.0.0",
        "phase": "F38",
        "status": "three_grid_linear_static_redesign_screen_complete_material_and_contact_release_blocked",
        "classification": "linear_elastic_hot_modulus_screen_not_fatigue_or_release_validation",
        "inputs": {"spec_sha256": sha256(args.spec), "cad_report_sha256": sha256(args.cad_report), "carrier_step_sha256": sha256(args.step), "geometry_report_sha256": sha256(args.geometry_report)},
        "solver": "CalculiX linear static C3D4; Gmsh tetra mesh",
        "toolchain": {"python": platform.python_version(), "calculix_executable": ccx, "calculix_version_output": version, "runtime_image_ref": args.runtime_image_ref, "runtime_image_id": args.runtime_image_id},
        "cases": results,
        "fine_vs_previous": convergence,
        "comparison_to_f37": {"f37_finest_raw_maximum_mpa": parent_max, "f38_finest_raw_maximum_mpa": fine["von_mises_mpa"]["maximum"], "raw_maximum_reduction_fraction": (parent_max - fine["von_mises_mpa"]["maximum"]) / parent_max},
        "gates": {
            "three_meshes_complete": len(results) == 3,
            "raw_maximum_grid_change_below_10_percent": convergence["raw_maximum_relative_change"] < target,
            "p99_grid_change_below_10_percent": convergence["p99_relative_change"] < float(spec["fea_screen"]["p99_convergence_target_fraction"]),
            "displacement_grid_change_below_10_percent": convergence["displacement_relative_change"] < float(spec["fea_screen"]["displacement_convergence_target_fraction"]),
            "finest_raw_maximum_below_provisional_200c_screen_yield": fine["von_mises_mpa"]["maximum"] < yield_mpa,
            "raw_maximum_reduced_from_f37": fine["von_mises_mpa"]["maximum"] < parent_max,
            "actual_resultant_direction_complete": False,
            "nonlinear_contact_complete": False,
            "qualified_material_card": False,
            "fatigue_and_thermal_cycle_complete": False,
            "metal_print_authorized": False,
            "engine_start_authorized": False,
        },
    }
    (args.output / "f38-carrier-calculix-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "fine_max_mpa": fine["von_mises_mpa"]["maximum"], "convergence": convergence, "gates": report["gates"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
