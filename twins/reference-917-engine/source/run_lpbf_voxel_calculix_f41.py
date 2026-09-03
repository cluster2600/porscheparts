#!/usr/bin/env python3
"""Ecran de distorsion LPBF F41 par elements hexa voxel et CalculiX."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess

import numpy as np
import trimesh


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    return float(np.quantile(np.asarray(values), fraction))


def write_ids(stream, keyword: str, name: str, values: list[int]) -> None:
    stream.write(f"*{keyword},{keyword}={name}\n")
    for start in range(0, len(values), 16):
        stream.write(",".join(str(value) for value in values[start : start + 16]) + "\n")


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
            stresses.append(
                math.sqrt(
                    0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
                    + 3.0 * (sxy * sxy + sxz * sxz + syz * syz)
                )
            )
        elif mode == "displacement" and len(fields) >= 4:
            try:
                int(fields[0]); vector = list(map(float, fields[1:4]))
            except ValueError:
                continue
            displacements.append(math.sqrt(sum(value * value for value in vector)))
    return stresses, displacements


def transform_y_down(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    transformed = mesh.copy()
    transformed.apply_transform(
        np.asarray(
            [
                [1.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, -1.0, 0.0],
                [0.0, 1.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ]
        )
    )
    transformed.apply_translation(-transformed.bounds[0])
    return transformed


def build_case(head: Path, output: Path, pitch: float, inherent_shrinkage: float) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    mesh = trimesh.load_mesh(head, process=True)
    if not isinstance(mesh, trimesh.Trimesh) or not mesh.is_watertight:
        raise RuntimeError("maillage_non_etanche")
    voxels = transform_y_down(mesh).voxelized(pitch).fill()
    occupancy = np.asarray(voxels.matrix, dtype=bool)
    origin = np.asarray(voxels.transform[:3, 3], dtype=float)
    node_map: dict[tuple[int, int, int], int] = {}
    node_coordinates: list[tuple[float, float, float]] = []
    elements: list[tuple[int, ...]] = []
    corner_order = ((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1))
    for index in np.argwhere(occupancy):
        i, j, k = (int(value) for value in index)
        tags = []
        for di, dj, dk in corner_order:
            key = (i + di, j + dj, k + dk)
            tag = node_map.get(key)
            if tag is None:
                tag = len(node_coordinates) + 1
                node_map[key] = tag
                point = origin + (np.asarray(key, dtype=float) - 0.5) * pitch
                node_coordinates.append(tuple(float(value) for value in point))
            tags.append(tag)
        elements.append(tuple(tags))
    base_nodes = sorted(tag for (i, j, k), tag in node_map.items() if k == 0)
    all_nodes = list(range(1, len(node_coordinates) + 1))
    if len(elements) < 1000 or len(base_nodes) < 20:
        raise RuntimeError("maillage_voxel_insuffisant")

    elastic_mpa = 70000.0
    poisson = 0.33
    expansion = 21.5e-6
    equivalent_delta_k = -inherent_shrinkage / expansion
    job = output / "f41-lpbf-distortion.inp"
    with job.open("w", encoding="utf-8") as stream:
        stream.write("*HEADING\nF41 locked-plate isotropic inherent-strain screen\n*NODE\n")
        for tag, point in enumerate(node_coordinates, start=1):
            stream.write(f"{tag},{point[0]:.8g},{point[1]:.8g},{point[2]:.8g}\n")
        stream.write("*ELEMENT,TYPE=C3D8,ELSET=HEAD\n")
        for tag, nodes in enumerate(elements, start=1):
            stream.write(f"{tag}," + ",".join(str(value) for value in nodes) + "\n")
        write_ids(stream, "NSET", "NALL", all_nodes)
        write_ids(stream, "NSET", "BUILD_PLATE", base_nodes)
        stream.write(
            "*MATERIAL,NAME=ALSI10MG_SCREEN_NOT_COUPON_QUALIFIED\n"
            f"*ELASTIC\n{elastic_mpa},{poisson}\n"
            f"*EXPANSION\n{expansion}\n"
            "*SOLID SECTION,ELSET=HEAD,MATERIAL=ALSI10MG_SCREEN_NOT_COUPON_QUALIFIED\n"
            "*INITIAL CONDITIONS,TYPE=TEMPERATURE\nNALL,0.\n"
            "*STEP\n*STATIC\n"
            "*BOUNDARY\nBUILD_PLATE,1,3,0.\n"
            f"*TEMPERATURE\nNALL,{equivalent_delta_k:.9g}\n"
            "*EL PRINT,ELSET=HEAD\nS\n"
            "*NODE PRINT,NSET=NALL\nU\n"
            "*EL FILE,ELSET=HEAD\nS,E\n"
            "*NODE FILE,NSET=NALL\nU,RF\n"
            "*END STEP\n"
        )
    completed = subprocess.run(
        ["ccx", "-i", job.stem],
        cwd=output,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    (output / "calculix.log").write_text(completed.stdout, encoding="utf-8")
    data = output / "f41-lpbf-distortion.dat"
    stresses, displacements = parse_dat(data) if data.is_file() else ([], [])
    results = {
        "von_mises_p95_mpa": percentile(stresses, 0.95),
        "von_mises_p99_mpa": percentile(stresses, 0.99),
        "von_mises_maximum_mpa": max(stresses) if stresses else None,
        "maximum_displacement_mm": max(displacements) if displacements else None,
    }
    return {
        "pitch_mm": pitch,
        "status": "completed" if completed.returncode == 0 and stresses and displacements else "failed",
        "solver": "CalculiX_ccx",
        "mesh": {"shape": list(occupancy.shape), "elements_C3D8": len(elements), "nodes": len(node_coordinates), "base_nodes": len(base_nodes)},
        "inherent_strain_assumption": {
            "isotropic_shrinkage": inherent_shrinkage,
            "equivalent_delta_temperature_k": equivalent_delta_k,
            "calibrated_to_machine_and_scan_strategy": False,
        },
        "material_assumption": {
            "elastic_modulus_mpa": elastic_mpa,
            "poisson": poisson,
            "thermal_expansion_1_k": expansion,
            "temperature_dependent": False,
            "coupon_qualified": False,
        },
        "boundary": "all_build_plate_nodes_fixed_1_to_3_locked_plate_screen",
        "results": results,
        "files": {"input": job.name, "log": "calculix.log", "dat": data.name if data.is_file() else None},
    }


def relative(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    return abs(a - b) / max(abs(a), abs(b), 1.0e-30)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--head", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pitches-mm", type=float, nargs="+", default=[5.0, 4.0, 3.0])
    parser.add_argument("--inherent-shrinkage", type=float, default=0.0025)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.mkdir(parents=True)
    cases = [
        build_case(args.head, args.output / f"pitch-{pitch:g}mm", pitch, args.inherent_shrinkage)
        for pitch in args.pitches_mm
    ]
    pair = cases[-2:]
    convergence = {
        "p95_stress_relative_difference": relative(pair[0]["results"]["von_mises_p95_mpa"], pair[1]["results"]["von_mises_p95_mpa"]),
        "maximum_displacement_relative_difference": relative(pair[0]["results"]["maximum_displacement_mm"], pair[1]["results"]["maximum_displacement_mm"]),
    }
    report = {
        "schema_version": "1.0.0",
        "phase": "F41",
        "status": "calculix_locked_plate_inherent_strain_screen_complete" if all(case["status"] == "completed" for case in cases) else "calculix_screen_failed",
        "classification": "voxel_locked_plate_linear_elastic_inherent_strain_sensitivity_not_calibrated_distortion_prediction",
        "input": {"path": args.head.name, "sha256": sha256(args.head)},
        "cases": cases,
        "finest_pair_convergence": convergence,
        "gates": {
            "all_cases_completed": all(case["status"] == "completed" for case in cases),
            "p95_stress_mesh_difference_below_10_percent": convergence["p95_stress_relative_difference"] is not None and convergence["p95_stress_relative_difference"] <= 0.10,
            "displacement_mesh_difference_below_5_percent": convergence["maximum_displacement_relative_difference"] is not None and convergence["maximum_displacement_relative_difference"] <= 0.05,
            "machine_inherent_strain_calibrated": False,
            "temperature_dependent_coupon_card_used": False,
            "support_contact_and_release_simulated": False,
            "lpbf_process_released": False,
        },
    }
    path = args.output / "917-head-lpbf-calculix-f41-report.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(path), "status": report["status"], "convergence": convergence, "finest": cases[-1]["results"]}, sort_keys=True))
    return 0 if report["gates"]["all_cases_completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
