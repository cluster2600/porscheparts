#!/usr/bin/env python3
"""Maillage Gmsh et écran statique CalculiX du support d'intercooler F0.

Le STEP reste une géométrie indépendante limitée à l'enveloppe commerciale.
Les appuis, la charge et la carte Ti-6Al-4V sont des hypothèses de criblage :
ce calcul ne constitue ni une validation véhicule, ni une autorisation LPBF.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import shutil
import subprocess


PART_ID = "993-ENG-INTERCOOLER-BRACKET-TI-F0-0001"
TWIN_ID = "TWIN-993-INTERCOOLER-BRACKET-TI-F0"
LOAD_N = 400.0
ELASTIC_MODULUS_MPA = 110_000.0
POISSON_RATIO = 0.31
WROUGHT_REFERENCE_PROOF_MPA = 828.0
LEFT_BORE = (15.0, 20.0, 6.0)
RIGHT_BORE = (241.0, 58.0, 5.0)
PEDESTAL_BOUNDS = (120.0, 145.0, 56.0, 80.0, 23.0)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(fraction * (len(ordered) - 1)))
    return ordered[index]


def von_mises(components: list[float]) -> float:
    sxx, syy, szz, sxy, sxz, syz = components
    return math.sqrt(
        0.5
        * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
        + 3.0 * (sxy**2 + sxz**2 + syz**2)
    )


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
                int(fields[0])
                int(fields[1])
                components = [float(value) for value in fields[2:8]]
            except ValueError:
                continue
            stresses.append(von_mises(components))
        elif mode == "displacement" and len(fields) >= 4:
            try:
                int(fields[0])
                vector = [float(value) for value in fields[1:4]]
            except ValueError:
                continue
            displacements.append(math.sqrt(sum(value**2 for value in vector)))
    if not stresses or not displacements:
        raise RuntimeError(f"missing_calculix_results:{path.name}")
    return stresses, displacements


def write_set(stream, name: str, values: list[int]) -> None:
    stream.write(f"*NSET,NSET={name}\n")
    for index in range(0, len(values), 16):
        stream.write(",".join(str(value) for value in values[index : index + 16]) + "\n")


def bore_nodes(
    points: dict[int, tuple[float, float, float]],
    bore: tuple[float, float, float],
    tolerance_mm: float,
) -> list[int]:
    center_x, center_y, radius = bore
    return sorted(
        tag
        for tag, (x, y, z) in points.items()
        if -tolerance_mm <= z <= 6.0 + tolerance_mm
        and abs(math.hypot(x - center_x, y - center_y) - radius)
        <= tolerance_mm
    )


def prepare_case(step: Path, case: Path, mesh_size_mm: float) -> dict[str, object]:
    import gmsh

    case.mkdir(parents=True, exist_ok=False)
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add("993_intercooler_bracket_ti_f0")
        gmsh.merge(str(step))
        volumes = gmsh.model.getEntities(3)
        if len(volumes) != 1:
            raise RuntimeError(f"expected_one_volume_got:{len(volumes)}")
        gmsh.option.setNumber("Mesh.MeshSizeMin", mesh_size_mm)
        gmsh.option.setNumber("Mesh.MeshSizeMax", mesh_size_mm)
        gmsh.option.setNumber("Mesh.ElementOrder", 2)
        gmsh.option.setNumber("Mesh.Algorithm3D", 10)
        gmsh.model.mesh.generate(3)
        node_tags, coordinates, _ = gmsh.model.mesh.getNodes()
        points = {
            int(tag): tuple(
                float(value)
                for value in coordinates[3 * index : 3 * index + 3]
            )
            for index, tag in enumerate(node_tags)
        }
        element_types, element_tags, element_nodes = gmsh.model.mesh.getElements(3)
        elements: list[tuple[int, tuple[int, ...]]] = []
        for element_type, tags, nodes in zip(
            element_types, element_tags, element_nodes
        ):
            if int(element_type) != 11:
                continue
            for index, tag in enumerate(tags):
                offset = 10 * index
                gmsh_nodes = [
                    int(item) for item in nodes[offset : offset + 10]
                ]
                # Gmsh place les milieux des arêtes 4-3 puis 4-2, tandis que
                # CalculiX attend 2-4 puis 3-4 pour C3D10.
                calculix_nodes = tuple(
                    gmsh_nodes[:8] + [gmsh_nodes[9], gmsh_nodes[8]]
                )
                elements.append(
                    (
                        int(tag),
                        calculix_nodes,
                    )
                )
        gmsh.write(str(case / "bracket.msh"))
    finally:
        gmsh.finalize()

    if not elements:
        raise RuntimeError("no_quadratic_tetrahedra")
    tolerance = max(0.08, 0.04 * mesh_size_mm)
    left = bore_nodes(points, LEFT_BORE, tolerance)
    right = bore_nodes(points, RIGHT_BORE, tolerance)
    x_min, x_max, y_min, y_max, z_top = PEDESTAL_BOUNDS
    loaded = sorted(
        tag
        for tag, (x, y, z) in points.items()
        if x_min - tolerance <= x <= x_max + tolerance
        and y_min - tolerance <= y <= y_max + tolerance
        and abs(z - z_top) <= tolerance
    )
    if len(left) < 6 or len(right) < 6 or len(loaded) < 4:
        raise RuntimeError(
            "insufficient_boundary_nodes:"
            f"left={len(left)}:right={len(right)}:load={len(loaded)}"
        )

    deck = case / "bracket-static.inp"
    with deck.open("w", encoding="utf-8") as stream:
        stream.write("*HEADING\n993 intercooler bracket Ti64 F0 static screen\n")
        stream.write("*NODE\n")
        for tag in sorted(points):
            x, y, z = points[tag]
            stream.write(f"{tag},{x:.9g},{y:.9g},{z:.9g}\n")
        stream.write("*ELEMENT,TYPE=C3D10,ELSET=BODY\n")
        for tag, nodes in elements:
            stream.write(f"{tag}," + ",".join(str(node) for node in nodes) + "\n")
        write_set(stream, "NALL", sorted(points))
        write_set(stream, "LEFT_BORE", left)
        write_set(stream, "RIGHT_BORE", right)
        write_set(stream, "LOAD_PAD", loaded)
        stream.write(
            "*MATERIAL,NAME=TI64_SCREEN\n"
            f"*ELASTIC\n{ELASTIC_MODULUS_MPA:.9g},{POISSON_RATIO:.9g}\n"
            "*SOLID SECTION,ELSET=BODY,MATERIAL=TI64_SCREEN\n"
            "*STEP\n*STATIC\n"
            "*BOUNDARY\nLEFT_BORE,1,3\nRIGHT_BORE,2,3\n"
            "*CLOAD\n"
        )
        nodal_load = -LOAD_N / len(loaded)
        for tag in loaded:
            stream.write(f"{tag},3,{nodal_load:.12g}\n")
        stream.write(
            "*EL PRINT,ELSET=BODY\nS\n"
            "*NODE PRINT,NSET=NALL\nU\n"
            "*END STEP\n"
        )
    return {
        "mesh_size_mm": mesh_size_mm,
        "nodes": len(points),
        "quadratic_tetrahedra": len(elements),
        "left_bore_fixed_xyz_nodes": len(left),
        "right_bore_roller_yz_nodes": len(right),
        "loaded_pedestal_top_nodes": len(loaded),
        "distributed_load_n": LOAD_N,
        "load_direction": "negative_local_z",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--step", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--mesh-sizes", default="5.0,3.5,2.5")
    parser.add_argument("--ccx", default="ccx")
    parser.add_argument("--runtime-image-ref", default="not_recorded")
    parser.add_argument("--runtime-image-id", default="not_recorded")
    args = parser.parse_args()

    if not args.step.is_file():
        raise FileNotFoundError(args.step)
    ccx = shutil.which(args.ccx)
    if ccx is None:
        raise RuntimeError(f"calculix_executable_not_found:{args.ccx}")
    import gmsh

    version = subprocess.run(
        [ccx, "-v"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    ).stdout.strip()
    args.work_root.mkdir(parents=True, exist_ok=True)
    cases: list[dict[str, object]] = []
    for size in (float(value) for value in args.mesh_sizes.split(",")):
        case_dir = args.work_root / f"mesh-{str(size).replace('.', 'p')}"
        mesh = prepare_case(args.step, case_dir, size)
        completed = subprocess.run(
            [ccx, "bracket-static"],
            cwd=case_dir,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        log = case_dir / "calculix.log"
        log.write_text(completed.stdout, encoding="utf-8")
        if completed.returncode != 0:
            raise RuntimeError(f"calculix_failed:{size}:{completed.returncode}")
        dat = case_dir / "bracket-static.dat"
        stresses, displacements = parse_dat(dat)
        artifacts = {}
        for path in (
            case_dir / "bracket.msh",
            case_dir / "bracket-static.inp",
            dat,
            log,
        ):
            artifacts[path.name] = {
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        cases.append(
            {
                "mesh": mesh,
                "von_mises_mpa": {
                    "p95": percentile(stresses, 0.95),
                    "p99": percentile(stresses, 0.99),
                    "maximum": max(stresses),
                },
                "maximum_displacement_mm": max(displacements),
                "artifacts": artifacts,
            }
        )

    previous = cases[-2]
    finest = cases[-1]
    p95_change = abs(
        finest["von_mises_mpa"]["p95"]
        - previous["von_mises_mpa"]["p95"]
    ) / finest["von_mises_mpa"]["p95"]
    displacement_change = abs(
        finest["maximum_displacement_mm"]
        - previous["maximum_displacement_mm"]
    ) / finest["maximum_displacement_mm"]
    report = {
        "schema_version": "1.0.0",
        "part_id": PART_ID,
        "twin_id": TWIN_ID,
        "status": "synthetic_linear_static_calculix_screen_complete_not_vehicle_validation",
        "inputs": {
            "step_repository_path": "parts/993-eng-intercooler-bracket-ti-f0-0001/derived/intercooler_bracket_ti_f0.step",
            "step_sha256": sha256(args.step),
            "load_n": LOAD_N,
            "load_authority": "synthetic regression value; no measured 993 intercooler, hose, vibration or acceleration load",
            "boundary_condition_authority": "F0 bore locations and roller idealization; no measured vehicle interfaces or fastener preload",
        },
        "solver": {
            "analysis": "CalculiX linear static C3D10",
            "mesh": "Gmsh second-order tetrahedra from the exact committed STEP",
            "python": platform.python_version(),
            "gmsh_version": str(gmsh.__version__),
            "calculix_version_output": version,
            "runtime_image_ref": args.runtime_image_ref,
            "runtime_image_id": args.runtime_image_id,
            "runtime_reproducibility": "local immutable image ID recorded; no registry digest claimed",
        },
        "material": {
            "candidate": "Ti-6Al-4V Grade 5 screening card",
            "elastic_modulus_mpa": ELASTIC_MODULUS_MPA,
            "poisson_ratio": POISSON_RATIO,
            "wrought_reference_proof_mpa": WROUGHT_REFERENCE_PROOF_MPA,
            "qualified_lpbf_allowable_available": False,
        },
        "cases": cases,
        "grid_comparison_fine_vs_previous": {
            "p95_relative_change": p95_change,
            "displacement_relative_change": displacement_change,
            "screening_threshold": 0.10,
            "threshold_authority": "project regression threshold only; not a design acceptance criterion",
        },
        "numerical_gates": {
            "p95_grid_change_below_10_percent": p95_change <= 0.10,
            "displacement_grid_change_below_10_percent": displacement_change <= 0.10,
            "finest_p99_below_wrought_reference_proof": finest["von_mises_mpa"]["p99"]
            <= WROUGHT_REFERENCE_PROOF_MPA,
            "finest_maximum_below_wrought_reference_proof": finest["von_mises_mpa"]["maximum"]
            <= WROUGHT_REFERENCE_PROOF_MPA,
        },
        "dfam_assessment": {
            "favorable_features": [
                "single BREP consolidates the open frame, two end eyes and central pedestal",
                "two open cutouts and all bores provide direct powder evacuation",
                "low-volume replacement could avoid dedicated casting tooling",
            ],
            "unfavorable_features": [
                "current form is predominantly planar and accessible to profile cutting plus machining",
                "no measured load path exists to justify topology optimization or lattice features",
                "Ti-6Al-4V powder, qualification, supports and post-machining add cost and inspection burden",
            ],
            "current_route_decision": "conditional_candidate_requires_CNC_sheet_LPBF_cost_and_performance_comparison",
            "lpbf_preferred_for_current_geometry": False,
            "geometry_redesign_authorized": False,
        },
        "engineering_gates": {
            "measured_mounting_interfaces": False,
            "measured_vehicle_loads": False,
            "fastener_contact_and_preload": False,
            "thermal_stress_completed": False,
            "modal_and_vibration_completed": False,
            "fatigue_completed": False,
            "qualified_lpbf_material_card": False,
            "professional_review": False,
            "vehicle_fit_test": False,
        },
        "interpretation": {
            "scope": "The solve checks numerical behavior of the F0 clean-sheet BREP under one synthetic static load only.",
            "singularities": "Raw maxima at idealized supports and point-distributed load edges are reported but p95/p99 and mesh convergence carry more screening value.",
            "strength": "The 828 MPa value is a wrought comparison reference, never an LPBF design allowable.",
            "physicsnemo": "No training or inference: three uncorrelated mesh points are not an admissible surrogate dataset.",
            "manufacturing": "No geometry, numerical, or material result authorizes printing or vehicle installation.",
        },
        "release_authorized": False,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "numerical_gates": report["numerical_gates"],
                "engineering_gates": report["engineering_gates"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
