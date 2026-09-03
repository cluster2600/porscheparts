#!/usr/bin/env python3
"""Prépare des cas OpenFOAM F36 sur la peau extérieure issue du scan."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from prepare_aircooled_openfoam_f34 import header, prepare_case


EXPECTED_SCAN_SHA256 = "4623d5d3b73fe3d03ca988a47543a8dd1be7834d3040e6f7efd1e1e95c766486"
DOMAIN_X_M = 0.36
DOMAIN_Y_M = 0.20
DOMAIN_Z_M = 0.15
AIR_DENSITY_KG_M3 = 1.06
RHO_INLET_START_KG_M3 = 100000.0 / (287.05 * 308.15)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def align_for_airflow(source: Path, destination: Path) -> dict:
    """Centre la peau et transforme +Y→-Y du scan en écoulement +X."""

    mesh = trimesh.load_mesh(source, process=True)
    if not isinstance(mesh, trimesh.Trimesh) or not mesh.is_watertight:
        raise ValueError("la peau extérieure F36 doit être un maillage étanche")
    centre = mesh.bounds.mean(axis=0)
    mesh.apply_translation(-centre)
    rotation = np.asarray(
        [
            [0.0, -1.0, 0.0, 0.0],
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )
    mesh.apply_transform(rotation)
    mesh.export(destination)
    return {
        "watertight": bool(mesh.is_watertight),
        "body_count": int(mesh.body_count),
        "bounds_aligned_obj_units": mesh.bounds.tolist(),
        "surface_area_m2_if_obj_unit_is_mm": float(mesh.area * 1.0e-6),
        "transformation": "translate_to_bounds_centre_then_x_new_equals_minus_y_old",
        "physical_airflow_direction_in_scan_frame": "positive_y_to_negative_y",
    }


def replace_domain(case: Path) -> None:
    nx, ny, nz = json.loads((case / "case-metadata.json").read_text(encoding="utf-8"))["cells"]
    block = header("blockMeshDict") + f"""convertToMeters 1;
vertices
(
    (-0.18 -0.10 -0.075)
    ( 0.18 -0.10 -0.075)
    ( 0.18  0.10 -0.075)
    (-0.18  0.10 -0.075)
    (-0.18 -0.10  0.075)
    ( 0.18 -0.10  0.075)
    ( 0.18  0.10  0.075)
    (-0.18  0.10  0.075)
);
blocks (hex (0 1 2 3 4 5 6 7) ({nx} {ny} {nz}) simpleGrading (1 1 1));
edges ();
boundary
(
    inlet {{ type patch; faces ((0 3 7 4)); }}
    outlet {{ type patch; faces ((1 2 6 5)); }}
    farfield {{ type patch; faces ((0 1 5 4) (3 2 6 7) (0 1 2 3) (4 5 6 7)); }}
);
"""
    (case / "system/blockMeshDict").write_text(block, encoding="utf-8")
    snappy = (case / "system/snappyHexMeshDict").read_text(encoding="utf-8")
    snappy = snappy.replace("locationInMesh (-0.27 0 0.12);", "locationInMesh (-0.165 0 0.060);")
    (case / "system/snappyHexMeshDict").write_text(snappy, encoding="utf-8")


def replace_velocity_inlet_with_mass_flow(case: Path, mass_flow_kg_s: float, initial_velocity_m_s: float) -> None:
    path = case / "0/U"
    source = path.read_text(encoding="utf-8")
    old = f"    inlet {{ type fixedValue; value uniform ({initial_velocity_m_s} 0 0); }}"
    new = (
        "    inlet\n"
        "    {\n"
        "        type flowRateInletVelocity;\n"
        f"        massFlowRate {mass_flow_kg_s};\n"
        "        rho rho;\n"
        f"        rhoInlet {RHO_INLET_START_KG_M3};\n"
        f"        value uniform ({initial_velocity_m_s} 0 0);\n"
        "    }"
    )
    if old not in source:
        raise RuntimeError("condition de vitesse F34 inattendue dans 0/U")
    path.write_text(source.replace(old, new), encoding="utf-8")


def write_parallel_decomposition(case: Path, subdomains: int = 4) -> None:
    decomposition = header("decomposeParDict") + f"""numberOfSubdomains {subdomains};
method scotch;
"""
    (case / "system/decomposeParDict").write_text(decomposition, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--stl", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mass-flow-kg-s", type=float, default=0.85)
    parser.add_argument("--wall-temperature-k", type=float, default=533.15)
    args = parser.parse_args()

    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    if contract["source"]["sha256"] != EXPECTED_SCAN_SHA256:
        raise SystemExit("le contrat F36 ne référence pas le scan attendu")
    if args.output.exists():
        raise SystemExit(f"output exists: {args.output}")
    if args.mass_flow_kg_s <= 0.0:
        raise SystemExit("le débit massique doit être positif")
    args.output.mkdir(parents=True)

    aligned = args.output / "head-f36-external-aligned.local.stl"
    geometry = align_for_airflow(args.stl, aligned)
    cross_section_m2 = DOMAIN_Y_M * DOMAIN_Z_M
    velocity = args.mass_flow_kg_s / (AIR_DENSITY_KG_M3 * cross_section_m2)
    specs = {
        "coarse": ((48, 28, 24), (1, 2)),
        "medium": ((64, 36, 30), (1, 3)),
        "fine": ((80, 44, 38), (2, 3)),
    }
    cases = []
    for name, (cells, level) in specs.items():
        case = args.output / name
        prepare_case(case, aligned, cells, level, velocity, args.wall_temperature_k)
        replace_domain(case)
        replace_velocity_inlet_with_mass_flow(case, args.mass_flow_kg_s, velocity)
        write_parallel_decomposition(case)
        metadata_path = case / "case-metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata.update(
            {
                "phase": "F36",
                "classification": "scan_conforming_external_airflow_fixed_wall_temperature_not_CHT",
                "target_mass_flow_kg_s": args.mass_flow_kg_s,
                "inlet_cross_section_m2": cross_section_m2,
                "inlet_density_kg_m3": AIR_DENSITY_KG_M3,
                "rho_inlet_start_kg_m3": RHO_INLET_START_KG_M3,
                "velocity_boundary_type": "flowRateInletVelocity_massFlowRate",
                "domain_m": [DOMAIN_X_M, DOMAIN_Y_M, DOMAIN_Z_M],
                "external_surface_area_m2_if_obj_unit_is_mm": geometry["surface_area_m2_if_obj_unit_is_mm"],
                "source_stl_sha256": sha256(args.stl),
                "aligned_stl_sha256": sha256(case / "constant/triSurface/head.stl"),
            }
        )
        metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        cases.append({"mesh_id": name, "path": str(case), "cells": list(cells), "surface_refinement": list(level)})

    report = {
        "schema_version": "1.0.0",
        "phase": "F36",
        "status": "openfoam_cases_prepared",
        "boundary_condition": {
            "target_mass_flow_kg_s": args.mass_flow_kg_s,
            "uniform_inlet_velocity_m_s": velocity,
            "inlet_temperature_k": 308.15,
            "wall_temperature_k": args.wall_temperature_k,
            "outlet_static_pressure_pa": 100000.0,
        },
        "geometry": geometry,
        "case_count": len(cases),
        "cases": cases,
        "release_claim": False,
    }
    (args.output / "cases.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "velocity_m_s": velocity, "case_count": len(cases)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
