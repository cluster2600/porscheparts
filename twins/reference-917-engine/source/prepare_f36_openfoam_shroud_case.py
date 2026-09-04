#!/usr/bin/env python3
"""Dérive un cas OpenFOAM F36 avec carénage rectangulaire adiabatique no-slip."""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
from pathlib import Path

import trimesh


RHO_INITIAL_KG_M3 = 100000.0 / (287.05 * 308.15)
DOMAIN_X_HALF_M = 0.18
BASE_CELL_M = 0.0075
C_MU = 0.09


def replace_exact(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"motif absent dans {path}: {old}")
    path.write_text(text.replace(old, new), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--gap-mm", type=float, required=True)
    parser.add_argument("--mass-flow-kg-s", type=float, default=0.85)
    parser.add_argument("--base-cell-mm", type=float, default=BASE_CELL_M * 1000.0)
    parser.add_argument("--domain-x-half-m", type=float, default=DOMAIN_X_HALF_M)
    parser.add_argument("--turbulence-model", choices=("kOmegaSST", "kEpsilon", "laminar"), default="kOmegaSST")
    parser.add_argument("--turbulence-intensity", type=float, default=0.05)
    parser.add_argument("--turbulence-length-mm", type=float, default=5.0)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"output exists: {args.output}")
    if min(args.gap_mm, args.mass_flow_kg_s, args.base_cell_mm, args.domain_x_half_m, args.turbulence_intensity, args.turbulence_length_mm) <= 0.0:
        raise SystemExit("gap, flow, mesh and turbulence inputs must be positive")

    shutil.copytree(
        args.template,
        args.output,
        ignore=shutil.ignore_patterns(
            "processor*",
            "postProcessing",
            "[1-9]*",
            "log.*",
            "driver*.log",
            ".recovered*",
        ),
    )
    shutil.rmtree(args.output / "constant/polyMesh", ignore_errors=True)
    stl = args.output / "constant/triSurface/head.stl"
    mesh = trimesh.load_mesh(stl, process=False)
    if not isinstance(mesh, trimesh.Trimesh):
        raise SystemExit("head STL is not a single mesh")
    y_half_m = (max(abs(mesh.bounds[0, 1]), abs(mesh.bounds[1, 1])) + args.gap_mm) * 1.0e-3
    z_half_m = (max(abs(mesh.bounds[0, 2]), abs(mesh.bounds[1, 2])) + args.gap_mm) * 1.0e-3
    base_cell_m = args.base_cell_mm * 1.0e-3
    ny = math.ceil((2.0 * y_half_m) / base_cell_m)
    nz = math.ceil((2.0 * z_half_m) / base_cell_m)
    nx = math.ceil((2.0 * args.domain_x_half_m) / base_cell_m)
    area = 4.0 * y_half_m * z_half_m
    velocity = args.mass_flow_kg_s / (RHO_INITIAL_KG_M3 * area)
    turbulent_k = 1.5 * (args.turbulence_intensity * velocity) ** 2
    turbulent_length_m = args.turbulence_length_mm * 1.0e-3
    turbulent_omega = math.sqrt(turbulent_k) / (C_MU ** 0.25 * turbulent_length_m)
    turbulent_epsilon = C_MU ** 0.75 * turbulent_k ** 1.5 / turbulent_length_m

    block = f"""FoamFile
{{
    format ascii;
    class dictionary;
    object blockMeshDict;
}}

convertToMeters 1;
vertices
(
    (-{args.domain_x_half_m} -{y_half_m:.10f} -{z_half_m:.10f})
    ( {args.domain_x_half_m} -{y_half_m:.10f} -{z_half_m:.10f})
    ( {args.domain_x_half_m}  {y_half_m:.10f} -{z_half_m:.10f})
    (-{args.domain_x_half_m}  {y_half_m:.10f} -{z_half_m:.10f})
    (-{args.domain_x_half_m} -{y_half_m:.10f}  {z_half_m:.10f})
    ( {args.domain_x_half_m} -{y_half_m:.10f}  {z_half_m:.10f})
    ( {args.domain_x_half_m}  {y_half_m:.10f}  {z_half_m:.10f})
    (-{args.domain_x_half_m}  {y_half_m:.10f}  {z_half_m:.10f})
);
blocks (hex (0 1 2 3 4 5 6 7) ({nx} {ny} {nz}) simpleGrading (1 1 1));
edges ();
boundary
(
    inlet {{ type patch; faces ((0 3 7 4)); }}
    outlet {{ type patch; faces ((1 2 6 5)); }}
    shroudYmin {{ type wall; faces ((0 1 5 4)); }}
    shroudYmax {{ type wall; faces ((3 2 6 7)); }}
    shroudZmin {{ type wall; faces ((0 1 2 3)); }}
    shroudZmax {{ type wall; faces ((4 5 6 7)); }}
);
"""
    (args.output / "system/blockMeshDict").write_text(block, encoding="utf-8")

    snappy = args.output / "system/snappyHexMeshDict"
    snappy_text = snappy.read_text(encoding="utf-8")
    snappy_text = re.sub(r"minRefinementCells\s+\d+;", "minRefinementCells 10;", snappy_text)
    snappy_text = re.sub(
        r"locationInMesh\s*\([^;]+;",
        "locationInMesh (-0.165 0 0);",
        snappy_text,
    )
    snappy.write_text(snappy_text, encoding="utf-8")

    def shroud_patches(condition: str) -> str:
        return "\n".join(f"{name} {{ {condition} }}" for name in ("shroudYmin", "shroudYmax", "shroudZmin", "shroudZmax"))

    replace_exact(args.output / "0/U", "farfield { type slip; }", shroud_patches("type noSlip;"))
    for scalar_name in ("T", "p"):
        replace_exact(
            args.output / "0" / scalar_name,
            "farfield { type zeroGradient; }",
            shroud_patches("type zeroGradient;"),
        )
    replace_exact(
        args.output / "0/k",
        "farfield { type zeroGradient; }",
        shroud_patches("type kqRWallFunction; value uniform 1e-10;"),
    )
    replace_exact(
        args.output / "0/omega",
        "farfield { type zeroGradient; }",
        shroud_patches("type omegaWallFunction; value uniform 900;"),
    )
    replace_exact(
        args.output / "0/nut",
        "farfield { type calculated; value uniform 0; }",
        shroud_patches("type nutkWallFunction; value uniform 0;"),
    )
    replace_exact(
        args.output / "0/alphat",
        "farfield { type calculated; value uniform 1e-3; }",
        shroud_patches("type compressible::alphatWallFunction; value uniform 1e-3;"),
    )
    u_path = args.output / "0/U"
    u_text = u_path.read_text(encoding="utf-8")
    u_text = re.sub(r"internalField uniform \([^;]+;", f"internalField uniform ({velocity:.10f} 0 0);", u_text)
    u_text = re.sub(r"massFlowRate\s+[0-9.eE+-]+;", f"massFlowRate {args.mass_flow_kg_s};", u_text)
    u_text = re.sub(r"value uniform \([^;]+;", f"value uniform ({velocity:.10f} 0 0);", u_text, count=2)
    u_path.write_text(u_text, encoding="utf-8")

    k_path = args.output / "0/k"
    k_text = k_path.read_text(encoding="utf-8").replace("uniform 4.0", f"uniform {turbulent_k:.10g}")
    k_path.write_text(k_text, encoding="utf-8")
    omega_path = args.output / "0/omega"
    omega_text = omega_path.read_text(encoding="utf-8").replace("uniform 900", f"uniform {turbulent_omega:.10g}")
    omega_path.write_text(omega_text, encoding="utf-8")

    if args.turbulence_model == "kEpsilon":
        momentum = args.output / "constant/momentumTransport"
        replace_exact(momentum, "model kOmegaSST;", "model kEpsilon;")
        epsilon_text = omega_path.read_text(encoding="utf-8")
        epsilon_text = epsilon_text.replace("object omega;", "object epsilon;")
        epsilon_text = epsilon_text.replace("dimensions [0 0 -1 0 0 0 0];", "dimensions [0 2 -3 0 0 0 0];")
        epsilon_text = epsilon_text.replace(f"uniform {turbulent_omega:.10g}", f"uniform {turbulent_epsilon:.10g}")
        epsilon_text = epsilon_text.replace("omegaWallFunction", "epsilonWallFunction")
        epsilon_path = args.output / "0/epsilon"
        epsilon_path.write_text(epsilon_text, encoding="utf-8")
        omega_path.unlink()
        for relative in ("system/fvSchemes", "system/fvSolution", "system/controlDict"):
            path = args.output / relative
            path.write_text(path.read_text(encoding="utf-8").replace("omega", "epsilon"), encoding="utf-8")
    elif args.turbulence_model == "laminar":
        momentum = args.output / "constant/momentumTransport"
        replace_exact(momentum, "simulationType RAS;", "simulationType laminar;")

    solution = args.output / "system/fvSolution"
    solution_text = solution.read_text(encoding="utf-8")
    prefix, marker, relaxation_text = solution_text.partition("relaxationFactors")
    if not marker:
        raise SystemExit("fvSolution has no relaxationFactors block")
    for pattern, value in (
        (r"(\bp\s+)[0-9.eE+-]+;", "0.1"),
        (r"(\brho\s+)[0-9.eE+-]+;", "0.002"),
        (r"(\bU\s+)[0-9.eE+-]+;", "0.1"),
        (r"(\bh\s+)[0-9.eE+-]+;", "0.01"),
        (r'("\(k\|(?:omega|epsilon)\)"\s+)[0-9.eE+-]+;', "0.1"),
    ):
        relaxation_text, replaced = re.subn(pattern, rf"\g<1>{value};", relaxation_text, count=1)
        if replaced != 1:
            raise SystemExit(f"fvSolution relaxation entry not found: {pattern}")
    solution_text = prefix + marker + relaxation_text
    solution.write_text(solution_text, encoding="utf-8")
    schemes = args.output / "system/fvSchemes"
    schemes_text = schemes.read_text(encoding="utf-8")
    schemes_text = schemes_text.replace(
        "laplacianSchemes { default Gauss linear corrected; }",
        "laplacianSchemes { default Gauss linear limited 0.33; }",
    )
    schemes_text = schemes_text.replace(
        "snGradSchemes { default corrected; }",
        "snGradSchemes { default limited 0.33; }",
    )
    schemes.write_text(schemes_text, encoding="utf-8")

    metadata_path = args.output / "case-metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata.update(
        {
            "mesh_id": f"shroud-gap{args.gap_mm:g}-nonslip-{args.turbulence_model}-base{args.base_cell_mm:g}mm",
            "classification": "scan_conforming_external_airflow_with_rectangular_adiabatic_noslip_shroud_not_CHT",
            "cells": [nx, ny, nz],
            "domain_m": [2.0 * args.domain_x_half_m, 2.0 * y_half_m, 2.0 * z_half_m],
            "domain_x_half_m": args.domain_x_half_m,
            "target_mass_flow_kg_s": args.mass_flow_kg_s,
            "initial_velocity_m_s": velocity,
            "velocity_m_s": velocity,
            "inlet_cross_section_m2": area,
            "shroud_gap_mm": args.gap_mm,
            "shroud_cross_section_m2": area,
            "base_cell_mm": args.base_cell_mm,
            "turbulence_model": args.turbulence_model,
            "reynolds_classification": "laminar_lower_bound_only_Re_is_turbulent"
            if args.turbulence_model == "laminar"
            else "RANS_screen",
            "turbulence_intensity": args.turbulence_intensity,
            "turbulence_length_mm": args.turbulence_length_mm,
            "inlet_turbulent_k_m2_s2": turbulent_k,
            "inlet_turbulent_omega_s-1": turbulent_omega if args.turbulence_model == "kOmegaSST" else None,
            "inlet_turbulent_epsilon_m2_s3": turbulent_epsilon if args.turbulence_model == "kEpsilon" else None,
            "stabilization": {
                "p_relaxation": 0.1,
                "rho_relaxation": 0.002,
                "U_relaxation": 0.1,
                "h_relaxation": 0.01,
                "turbulence_relaxation": 0.1,
                "laplacian_limiter": 0.33,
                "snGrad_limiter": 0.33,
            },
            "shroud_wall_velocity_condition": "noSlip",
            "shroud_wall_thermal_condition": "adiabatic_zeroGradient",
            "shroud_wall_patches": ["shroudYmin", "shroudYmax", "shroudZmin", "shroudZmax"],
            "release_claim": False,
        }
    )
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "cells": [nx, ny, nz], "area_m2": area, "velocity_m_s": velocity, "turbulence_model": args.turbulence_model}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
