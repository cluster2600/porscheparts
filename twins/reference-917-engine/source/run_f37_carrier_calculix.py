#!/usr/bin/env python3
"""Maille le porte-axes F37 avec Gmsh et exécute un écran CalculiX."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import shutil
import subprocess


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(fraction * (len(ordered) - 1)))]


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
            stresses.append(math.sqrt(0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2) + 3.0 * (sxy**2 + sxz**2 + syz**2)))
        elif mode == "displacement" and len(fields) >= 4:
            try:
                int(fields[0]); vector = list(map(float, fields[1:4]))
            except ValueError:
                continue
            displacements.append(math.sqrt(sum(value * value for value in vector)))
    if not stresses or not displacements:
        raise RuntimeError(f"missing_calculix_results:{path}")
    return stresses, displacements


def write_set(stream, kind: str, name: str, values: list[int]) -> None:
    stream.write(f"*{kind},{kind}={name}\n")
    for index in range(0, len(values), 16):
        stream.write(",".join(str(value) for value in values[index:index + 16]) + "\n")


def prepare_case(step: Path, contract: dict, geometry: dict, case: Path, size: float) -> dict:
    import gmsh

    case.mkdir(parents=True, exist_ok=False)
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 1)
        gmsh.model.add("f37_carrier")
        gmsh.merge(str(step))
        volumes = gmsh.model.getEntities(3)
        if len(volumes) != 1:
            raise RuntimeError(f"expected_one_volume_got:{len(volumes)}")
        gmsh.option.setNumber("Mesh.MeshSizeMin", size)
        gmsh.option.setNumber("Mesh.MeshSizeMax", size)
        gmsh.option.setNumber("Mesh.ElementOrder", 1)
        gmsh.option.setNumber("Mesh.Algorithm3D", 10)
        gmsh.model.mesh.generate(3)
        node_tags, coordinates, _ = gmsh.model.mesh.getNodes()
        points = {int(tag): tuple(float(value) for value in coordinates[3 * index:3 * index + 3]) for index, tag in enumerate(node_tags)}
        element_types, element_tags, element_nodes = gmsh.model.mesh.getElements(3)
        elements: list[tuple[int, tuple[int, int, int, int]]] = []
        for element_type, tags, nodes in zip(element_types, element_tags, element_nodes):
            if int(element_type) != 4:
                continue
            for index, tag in enumerate(tags):
                offset = 4 * index
                elements.append((int(tag), tuple(int(item) for item in nodes[offset:offset + 4])))
        gmsh.write(str(case / "carrier.msh"))
    finally:
        gmsh.finalize()
    if not elements:
        raise RuntimeError("no_linear_tetrahedra")

    rocker = contract["rocker_carrier"]
    axis_z = float(rocker["intake_axis_yz_mm"][1])
    y_axes = (float(rocker["intake_axis_yz_mm"][0]), float(rocker["exhaust_axis_yz_mm"][0]))
    mount_centres = [tuple(map(float, value)) for value in geometry["geometry"]["packaging_checks"]["stud_centres_local_mm"]]
    bottom = float(rocker["mount_interface_z_mm"])
    mount_radius = float(rocker["mount_boss_outer_diameter_mm"]) / 2.0
    support = [
        tag for tag, (x, y, z) in points.items()
        if z <= bottom + max(0.25, 0.2 * size)
        and any(math.hypot(x - mx, y - my) <= mount_radius for mx, my in mount_centres)
    ]
    architecture = geometry["geometry"]["architecture"]
    tilt_by_axis_y = {
        float(rocker["intake_axis_yz_mm"][0]): float(architecture["intake"]["tilt_y_deg"]),
        float(rocker["exhaust_axis_yz_mm"][0]): float(architecture["exhaust"]["tilt_y_deg"]),
    }
    load_zones: list[dict[str, object]] = []
    for load_x in (-18.0, 18.0):
        for axis_y in y_axes:
            zone = [
                tag for tag, (x, y, z) in points.items()
                if abs(x - load_x) <= 7.5
                and 6.2 <= math.hypot(y - axis_y, z - axis_z) <= 7.5
            ]
            load_zones.append({"nodes": zone, "tilt_y_deg": tilt_by_axis_y[axis_y]})
    if len(support) < 12 or any(len(zone["nodes"]) < 4 for zone in load_zones):
        raise RuntimeError(
            f"insufficient_node_selection:support={len(support)}:"
            f"loads={[len(zone['nodes']) for zone in load_zones]}"
        )

    load_cfg = contract["component_material_and_load_screen"]
    pivot_screen = contract["rocker_pivot_reaction_screen"]
    spring_design_load = float(load_cfg["worst_open_spring_load_per_valve_n"]) * float(load_cfg["dynamic_load_factor"])
    cam_to_valve_ratio = float(pivot_screen["cam_to_valve_force_ratio"])
    pivot_envelope_factor = float(pivot_screen["collinear_upper_envelope_factor"])
    if not math.isclose(pivot_envelope_factor, 1.0 + cam_to_valve_ratio, rel_tol=0.0, abs_tol=1.0e-12):
        raise RuntimeError("rocker_pivot_collinear_envelope_factor_mismatch")
    if pivot_screen["actual_resultant_direction_complete"] is not False:
        raise RuntimeError("rocker_pivot_resultant_direction_must_remain_fail_closed")
    if contract["release_gates"]["rocker_pivot_resultant_load_complete"] is not False:
        raise RuntimeError("rocker_pivot_resultant_gate_must_remain_fail_closed")
    design_load = spring_design_load * pivot_envelope_factor
    job = case / "carrier-f37.inp"
    with job.open("w", encoding="utf-8") as stream:
        stream.write("*HEADING\nF37 rocker carrier static hot-modulus screen\n*NODE\n")
        for tag in sorted(points):
            x, y, z = points[tag]
            stream.write(f"{tag},{x:.9g},{y:.9g},{z:.9g}\n")
        stream.write("*ELEMENT,TYPE=C3D4,ELSET=EALL\n")
        for tag, nodes in elements:
            stream.write(f"{tag}," + ",".join(str(node) for node in nodes) + "\n")
        write_set(stream, "NSET", "NALL", sorted(points))
        write_set(stream, "NSET", "SUPPORT", sorted(support))
        stream.write("*MATERIAL,NAME=2618A_SCREEN\n*ELASTIC\n65000.,0.33\n*SOLID SECTION,ELSET=EALL,MATERIAL=2618A_SCREEN\n*STEP\n*STATIC\n*BOUNDARY\nSUPPORT,1,3\n*CLOAD\n")
        for zone in load_zones:
            nodes = zone["nodes"]
            tilt_rad = math.radians(float(zone["tilt_y_deg"]))
            nodal_y = -design_load * math.sin(tilt_rad) / len(nodes)
            nodal_z = -design_load * math.cos(tilt_rad) / len(nodes)
            for tag in sorted(nodes):
                stream.write(f"{tag},2,{nodal_y:.9g}\n")
                stream.write(f"{tag},3,{nodal_z:.9g}\n")
        stream.write("*EL PRINT,ELSET=EALL\nS\n*NODE PRINT,NSET=NALL\nU\n*END STEP\n")
    return {
        "mesh_size_mm": size,
        "nodes": len(points),
        "elements": len(elements),
        "support_nodes": len(support),
        "load_nodes_per_zone": [len(zone["nodes"]) for zone in load_zones],
        "spring_only_design_load_per_zone_n": spring_design_load,
        "cam_side_design_load_per_zone_n": spring_design_load * cam_to_valve_ratio,
        "pivot_reaction_collinear_upper_envelope_factor": pivot_envelope_factor,
        "design_load_per_zone_n": design_load,
        "load_classification": "pivot_reaction_magnitude_upper_envelope_applied_along_valve_axis_screen_direction",
        "actual_resultant_direction_complete": False,
        "load_direction": "along_each_valve_axis_in_local_yz_plane_screen_direction_only",
        "load_vectors_yz_n": [
            [
                -design_load * math.sin(math.radians(float(zone["tilt_y_deg"]))),
                -design_load * math.cos(math.radians(float(zone["tilt_y_deg"]))),
            ]
            for zone in load_zones
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--step", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--geometry-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mesh-sizes", default="3.0,2.0,1.5")
    parser.add_argument("--ccx", default="ccx")
    parser.add_argument("--runtime-image-ref", default="not_recorded")
    parser.add_argument("--runtime-image-id", default="not_recorded")
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    geometry = json.loads(args.geometry_report.read_text(encoding="utf-8"))
    import gmsh

    ccx_resolved = shutil.which(args.ccx)
    if ccx_resolved is None:
        raise RuntimeError(f"calculix_executable_not_found:{args.ccx}")
    version_run = subprocess.run(
        [ccx_resolved, "-v"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    ccx_version = version_run.stdout.strip()
    args.output.mkdir(parents=True, exist_ok=True)
    results = []
    for size in (float(value) for value in args.mesh_sizes.split(",")):
        case = args.output / f"mesh-{str(size).replace('.', 'p')}"
        mesh = prepare_case(args.step, contract, geometry, case, size)
        completed = subprocess.run([ccx_resolved, "carrier-f37"], cwd=case, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        (case / "calculix.log").write_text(completed.stdout, encoding="utf-8")
        if completed.returncode != 0:
            raise RuntimeError(f"calculix_failed:{size}:{completed.returncode}")
        stresses, displacements = parse_dat(case / "carrier-f37.dat")
        artifacts = {
            path.name: {"bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in (
                case / "carrier.msh",
                case / "carrier-f37.inp",
                case / "carrier-f37.dat",
                case / "calculix.log",
            )
        }
        results.append({
            "mesh": mesh,
            "command": [ccx_resolved, "carrier-f37"],
            "artifacts": artifacts,
            "von_mises_mpa": {
                "p95": percentile(stresses, 0.95),
                "p99": percentile(stresses, 0.99),
                "maximum": max(stresses),
            },
            "maximum_displacement_mm": max(displacements),
        })
    finest = results[-1]
    previous = results[-2]
    p95_change = abs(finest["von_mises_mpa"]["p95"] - previous["von_mises_mpa"]["p95"]) / finest["von_mises_mpa"]["p95"]
    displacement_change = abs(finest["maximum_displacement_mm"] - previous["maximum_displacement_mm"]) / finest["maximum_displacement_mm"]
    yield_mpa = float(contract["component_material_and_load_screen"]["rocker_carrier"]["screen_yield_mpa_at_200c"])
    report = {
        "schema_version": "1.0.0",
        "phase": "F37",
        "status": "carrier_calculix_pivot_envelope_grid_screen_complete_actual_direction_contact_and_material_correlation_pending",
        "inputs": {
            "contract_sha256": sha256(args.contract),
            "geometry_report_sha256": sha256(args.geometry_report),
            "carrier_step_sha256": sha256(args.step),
        },
        "solver": "CalculiX linear static C3D4; Gmsh tetra mesh",
        "load_case": {
            "model": contract["rocker_pivot_reaction_screen"]["model"],
            "spring_only_design_load_per_zone_n": (
                float(contract["component_material_and_load_screen"]["worst_open_spring_load_per_valve_n"])
                * float(contract["component_material_and_load_screen"]["dynamic_load_factor"])
            ),
            "pivot_reaction_collinear_upper_envelope_factor": float(
                contract["rocker_pivot_reaction_screen"]["collinear_upper_envelope_factor"]
            ),
            "actual_resultant_direction_complete": False,
        },
        "toolchain": {
            "python": platform.python_version(),
            "gmsh_python": str(gmsh.__version__),
            "calculix_executable": ccx_resolved,
            "calculix_version_output": ccx_version,
            "runtime_image_ref": args.runtime_image_ref,
            "runtime_image_id": args.runtime_image_id,
            "runtime_reproducibility": "local_runtime_snapshot_not_portably_reproducible",
            "registry_digest_available": False,
        },
        "cases": results,
        "grid_comparison_fine_vs_previous": {"p95_relative_change": p95_change, "displacement_relative_change": displacement_change},
        "gates": {
            "p95_grid_change_below_5_percent": p95_change <= 0.05,
            "displacement_grid_change_below_5_percent": displacement_change <= 0.05,
            "finest_p99_below_200c_screen_yield": finest["von_mises_mpa"]["p99"] <= yield_mpa,
            "finest_maximum_below_200c_screen_yield": finest["von_mises_mpa"]["maximum"] <= yield_mpa,
            "finest_displacement_below_0_15_mm": finest["maximum_displacement_mm"] <= 0.15,
            "pivot_reaction_magnitude_upper_envelope_applied": True,
            "actual_resultant_direction_complete": False,
            "rocker_pivot_resultant_load_complete": False,
            "nonlinear_contact_complete": False,
            "qualified_material_card": False,
            "multiaxial_valve_axis_load_case_complete": True,
        },
    }
    (args.output / "f37-carrier-calculix-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "gates": report["gates"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
