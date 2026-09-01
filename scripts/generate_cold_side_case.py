#!/usr/bin/env python3
"""Validate and render the small OpenFOAM cold-side regression case."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from textwrap import dedent
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PARAMETERS = ROOT / "simulation" / "993-k16-cold-side-baseline" / "parameters.json"
DEFAULT_CASE = DEFAULT_PARAMETERS.parent


def _positive(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def validate_parameters(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return ["root: expected an object"]

    errors: list[str] = []
    for key in ("schema_version", "case_id", "status", "units", "geometry_source", "geometry", "flow", "solver"):
        if key not in payload:
            errors.append(f"root: missing {key}")
    if payload.get("schema_version") != "1.0.0":
        errors.append("schema_version: expected 1.0.0")
    if not isinstance(payload.get("case_id"), str) or not payload["case_id"].strip():
        errors.append("case_id: expected a non-empty string")
    if payload.get("status") != "exploratory_reference":
        errors.append("status: expected exploratory_reference")
    if not isinstance(payload.get("geometry_source"), str) or not payload["geometry_source"].strip():
        errors.append("geometry_source: expected a non-empty repository path")

    geometry = payload.get("geometry")
    if not isinstance(geometry, dict):
        errors.append("geometry: expected an object")
    else:
        dimensions = ("inlet_diameter_mm", "outlet_diameter_mm", "diffuser_length_mm", "wall_thickness_mm")
        for key in dimensions:
            if not _positive(geometry.get(key)):
                errors.append(f"geometry.{key}: expected a positive number")
        if all(_positive(geometry.get(key)) for key in dimensions[:3]):
            if geometry["outlet_diameter_mm"] <= geometry["inlet_diameter_mm"]:
                errors.append("geometry.outlet_diameter_mm: must exceed inlet diameter")
        if _positive(geometry.get("inlet_diameter_mm")) and _positive(geometry.get("wall_thickness_mm")):
            if geometry["wall_thickness_mm"] >= geometry["inlet_diameter_mm"] / 2:
                errors.append("geometry.wall_thickness_mm: must leave an inlet passage")
        for key in ("mesh_cells_streamwise", "mesh_cells_across_inlet"):
            if not isinstance(geometry.get(key), int) or geometry[key] < 2:
                errors.append(f"geometry.{key}: expected an integer >= 2")

    flow = payload.get("flow")
    if not isinstance(flow, dict):
        errors.append("flow: expected an object")
    else:
        for key in ("air_density_kg_m3", "kinematic_viscosity_m2_s", "inlet_velocity_m_s"):
            if not _positive(flow.get(key)):
                errors.append(f"flow.{key}: expected a positive number")
        if not isinstance(flow.get("fluid"), str) or flow["fluid"] != "air":
            errors.append("flow.fluid: expected air")

    solver = payload.get("solver")
    if not isinstance(solver, dict):
        errors.append("solver: expected an object")
    else:
        if solver.get("application") != "simpleFoam":
            errors.append("solver.application: expected simpleFoam")
        if solver.get("openfoam_version") != "13":
            errors.append("solver.openfoam_version: expected 13")
        if solver.get("turbulence_model") != "kOmegaSST":
            errors.append("solver.turbulence_model: expected kOmegaSST")
        if not isinstance(solver.get("iterations"), int) or solver["iterations"] < 1:
            errors.append("solver.iterations: expected a positive integer")

    return errors


def _number(value: float) -> str:
    return f"{value:.9g}"


def render_block_mesh(payload: dict[str, Any]) -> str:
    geometry = payload["geometry"]
    length = geometry["diffuser_length_mm"] / 1000.0
    inlet = geometry["inlet_diameter_mm"] / 1000.0
    outlet = geometry["outlet_diameter_mm"] / 1000.0
    nx = geometry["mesh_cells_streamwise"]
    ny = geometry["mesh_cells_across_inlet"]
    nz = ny
    vertices = [
        (0.0, -inlet / 2, -inlet / 2),
        (length, -outlet / 2, -outlet / 2),
        (length, outlet / 2, -outlet / 2),
        (0.0, inlet / 2, -inlet / 2),
        (0.0, -inlet / 2, inlet / 2),
        (length, -outlet / 2, outlet / 2),
        (length, outlet / 2, outlet / 2),
        (0.0, inlet / 2, inlet / 2),
    ]
    vertex_lines = "\n".join(f"        ({_number(x)} {_number(y)} {_number(z)})" for x, y, z in vertices)
    generation_source = payload.get("generation_source", "simulation/993-k16-cold-side-baseline/parameters.json")
    variant_id = payload.get("variant_id")
    rendered = dedent(
        f"""\
        /*--------------------------------*- C++ -*----------------------------------*\\
          =========                 |
          \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox
           \\    /   O peration     | Version: 13
            \\  /    A nd          |
             \\/     M anipulation  |
        \\*---------------------------------------------------------------------------*/
        FoamFile
        {{
            format      ascii;
            class       dictionary;
            object      blockMeshDict;
        }}
        // Generated from {generation_source}.
        // The block is a rectangular equivalent diffuser, not K16 CAD.

        convertToMeters 1;

        vertices
        (
        {vertex_lines}
        );

        blocks
        (
            hex (0 1 2 3 4 5 6 7) ({nx} {ny} {nz}) simpleGrading (1 1 1)
        );

        edges
        (
        );

        boundary
        (
            inlet
            {{
                type patch;
                faces ((0 4 7 3));
            }}
            outlet
            {{
                type patch;
                faces ((1 2 6 5));
            }}
            walls
            {{
                type wall;
                faces
                (
                    (0 1 5 4)
                    (3 7 6 2)
                    (0 3 2 1)
                    (4 5 6 7)
                );
            }}
        );

        mergePatchPairs
        (
        );
        """
    )
    if variant_id:
        rendered = rendered.replace(
            "// The block is a rectangular equivalent diffuser, not K16 CAD.",
            f"// Variant: {variant_id}.\n// The block is a rectangular equivalent diffuser, not K16 CAD.",
        )
    return rendered


def load(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"cold-side: cannot read {path}: {exc}")
    errors = validate_parameters(payload)
    if errors:
        raise SystemExit("cold-side: invalid parameters\n" + "\n".join(f"  - {error}" for error in errors))
    return payload


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parameters", type=Path, default=DEFAULT_PARAMETERS)
    parser.add_argument("--output", type=Path, default=DEFAULT_CASE)
    parser.add_argument("--write", action="store_true", help="write the generated blockMeshDict")
    parser.add_argument("--check", action="store_true", help="validate parameters and checked-in generated file")
    args = parser.parse_args(arguments)

    payload = load(args.parameters)
    source = (ROOT / payload["geometry_source"]).resolve()
    if not source.is_file():
        raise SystemExit(f"cold-side: geometry source does not exist: {payload['geometry_source']}")
    rendered = render_block_mesh(payload)
    target = args.output / "system" / "blockMeshDict"

    if args.write:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
        print(f"generated {target.relative_to(ROOT)}")
    if args.check or not args.write:
        if not target.is_file():
            print(f"FAIL {target.relative_to(ROOT)}: generated file does not exist")
            return 1
        if target.read_text(encoding="utf-8") != rendered:
            print(f"FAIL {target.relative_to(ROOT)}: regenerate with --write")
            return 1
        print(f"OK   {args.parameters.relative_to(ROOT)} and {target.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
