#!/usr/bin/env python3
"""Validate and materialize the three exploratory 993 turbo variants."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.generate_cold_side_case import render_block_mesh, validate_parameters  # noqa: E402

MANIFEST = ROOT / "simulation" / "993-turbo-variants" / "variants.json"
BASELINE_CASE = ROOT / "simulation" / "993-k16-cold-side-baseline"
EXPECTED_VARIANTS = {"K16-OEM", "K16-24-HYBRID", "K24-REFERENCE"}
STATIC_CASE_FILES = (
    "0/k",
    "0/nut",
    "0/omega",
    "0/p",
    "constant/transportProperties",
    "constant/turbulenceProperties",
    "system/controlDict",
    "system/fvSchemes",
    "system/fvSolution",
)
VELOCITY_RE = re.compile(r"uniform \(40 0 0\)")


def _positive(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def _known_source_ids() -> set[str]:
    known: set[str] = set()
    for path in (ROOT / "catalog" / "sources").glob("*.json"):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(record, dict) and isinstance(record.get("source_id"), str):
            known.add(record["source_id"])
    return known


def _variant_payload(manifest: dict[str, Any], variant: dict[str, Any]) -> dict[str, Any]:
    comparison = manifest["comparison"]
    return {
        "schema_version": "1.0.0",
        "case_id": variant["case_id"],
        "status": "exploratory_reference",
        "units": "SI_for_solver_mm_for_geometry",
        "geometry_source": manifest["geometry_source"],
        "generation_source": "simulation/993-turbo-variants/variants.json",
        "variant_id": variant["variant_id"],
        "geometry": variant["geometry"],
        "flow": variant["flow"],
        "solver": manifest["solver"],
        "assumptions": variant["assumptions"],
        "validation": variant["validation"],
        "comparison": comparison,
    }


def validate_manifest(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return ["root: expected an object"]

    errors: list[str] = []
    required = {"schema_version", "manifest_id", "status", "geometry_source", "case_root", "comparison", "solver", "variants"}
    missing = required - payload.keys()
    if missing:
        errors.extend(f"root: missing {field}" for field in sorted(missing))
    if payload.get("schema_version") != "1.0.0":
        errors.append("schema_version: expected 1.0.0")
    if not isinstance(payload.get("manifest_id"), str) or not payload["manifest_id"].strip():
        errors.append("manifest_id: expected a non-empty string")
    if payload.get("status") != "exploratory_reference":
        errors.append("status: expected exploratory_reference")

    geometry_source = payload.get("geometry_source")
    if not isinstance(geometry_source, str) or not (ROOT / geometry_source).is_file():
        errors.append("geometry_source: referenced source file does not exist")

    comparison = payload.get("comparison")
    if not isinstance(comparison, dict):
        errors.append("comparison: expected an object")
    else:
        for field in ("mass_flow_per_case_kg_s", "air_density_kg_m3", "kinematic_viscosity_m2_s"):
            if not _positive(comparison.get(field)):
                errors.append(f"comparison.{field}: expected a positive number")
        if not isinstance(comparison.get("basis"), str) or not comparison["basis"].strip():
            errors.append("comparison.basis: expected a non-empty string")

    solver = payload.get("solver")
    if not isinstance(solver, dict):
        errors.append("solver: expected an object")

    variants = payload.get("variants")
    if not isinstance(variants, list) or not variants:
        errors.append("variants: expected a non-empty array")
        return errors

    ids: set[str] = set()
    known_sources = _known_source_ids()
    if isinstance(comparison, dict):
        common_mass_flow = comparison.get("mass_flow_per_case_kg_s")
        common_density = comparison.get("air_density_kg_m3")
        common_viscosity = comparison.get("kinematic_viscosity_m2_s")
    else:
        common_mass_flow = common_density = common_viscosity = None

    for index, variant in enumerate(variants):
        label = f"variants[{index}]"
        if not isinstance(variant, dict):
            errors.append(f"{label}: expected an object")
            continue
        for field in ("variant_id", "case_id", "name", "configuration", "geometry", "flow", "source_ids", "assumptions", "validation"):
            if field not in variant:
                errors.append(f"{label}: missing {field}")

        variant_id = variant.get("variant_id")
        if not isinstance(variant_id, str) or not variant_id.strip():
            errors.append(f"{label}.variant_id: expected a non-empty string")
        elif variant_id in ids:
            errors.append(f"{label}.variant_id: duplicate {variant_id}")
        else:
            ids.add(variant_id)

        source_ids = variant.get("source_ids")
        if not isinstance(source_ids, list) or not source_ids or not all(isinstance(value, str) for value in source_ids):
            errors.append(f"{label}.source_ids: expected a non-empty string array")
        else:
            for source_id in source_ids:
                if source_id not in known_sources:
                    errors.append(f"{label}.source_ids: {source_id} is not registered")

        geometry = variant.get("geometry")
        if not isinstance(geometry, dict):
            errors.append(f"{label}.geometry: expected an object")
        else:
            if geometry.get("evidence_level") != "hypothesis":
                errors.append(f"{label}.geometry.evidence_level: expected hypothesis")
            if not isinstance(geometry.get("design_basis"), str) or not geometry["design_basis"].strip():
                errors.append(f"{label}.geometry.design_basis: expected a non-empty string")

        flow = variant.get("flow")
        if not isinstance(flow, dict):
            errors.append(f"{label}.flow: expected an object")
        else:
            for field in ("mass_flow_per_case_kg_s", "air_density_kg_m3", "kinematic_viscosity_m2_s", "inlet_velocity_m_s"):
                if not _positive(flow.get(field)):
                    errors.append(f"{label}.flow.{field}: expected a positive number")
            if flow.get("fluid") != "air":
                errors.append(f"{label}.flow.fluid: expected air")
            if isinstance(common_mass_flow, (int, float)) and flow.get("mass_flow_per_case_kg_s") != common_mass_flow:
                errors.append(f"{label}.flow.mass_flow_per_case_kg_s: must match comparison case")
            if isinstance(common_density, (int, float)) and flow.get("air_density_kg_m3") != common_density:
                errors.append(f"{label}.flow.air_density_kg_m3: must match comparison case")
            if isinstance(common_viscosity, (int, float)) and flow.get("kinematic_viscosity_m2_s") != common_viscosity:
                errors.append(f"{label}.flow.kinematic_viscosity_m2_s: must match comparison case")
            if isinstance(geometry, dict) and all(_positive(geometry.get(field)) for field in ("inlet_diameter_mm",)):
                if _positive(flow.get("mass_flow_per_case_kg_s")) and _positive(flow.get("air_density_kg_m3")) and _positive(flow.get("inlet_velocity_m_s")):
                    area = math.pi * (geometry["inlet_diameter_mm"] / 1000.0) ** 2 / 4.0
                    expected_mass_flow = flow["air_density_kg_m3"] * area * flow["inlet_velocity_m_s"]
                    if not math.isclose(expected_mass_flow, flow["mass_flow_per_case_kg_s"], rel_tol=1e-9, abs_tol=1e-10):
                        errors.append(f"{label}.flow: velocity does not reproduce declared comparison mass flow")

        assumptions = variant.get("assumptions")
        if not isinstance(assumptions, list) or not assumptions or not all(isinstance(value, str) and value.strip() for value in assumptions):
            errors.append(f"{label}.assumptions: expected a non-empty string array")

        validation = variant.get("validation")
        if not isinstance(validation, dict):
            errors.append(f"{label}.validation: expected an object")
        else:
            for field in ("physical_fitment", "engine_tested", "release_allowed"):
                if validation.get(field) is not False:
                    errors.append(f"{label}.validation.{field}: must remain false")

        if not isinstance(variant.get("case_id"), str) or not variant["case_id"].strip():
            errors.append(f"{label}.case_id: expected a non-empty string")
        if isinstance(variant_id, str):
            child_errors = validate_parameters(_variant_payload(payload, variant))
            errors.extend(f"{label}.{error}" for error in child_errors)

    if ids != EXPECTED_VARIANTS:
        errors.append(f"variants: expected exactly {sorted(EXPECTED_VARIANTS)}, got {sorted(ids)}")
    return errors


def _render_velocity_field(variant: dict[str, Any]) -> str:
    source = BASELINE_CASE / "0" / "U"
    text = source.read_text(encoding="utf-8")
    velocity = f"{variant['flow']['inlet_velocity_m_s']:.12g}"
    rendered, count = VELOCITY_RE.subn(f"uniform ({velocity} 0 0)", text)
    if count != 2:
        raise ValueError(f"{source}: expected two baseline velocity values, found {count}")
    return rendered


def _target(root: Path, relative: str) -> Path:
    return root / relative


def materialize(manifest: dict[str, Any], write: bool) -> list[str]:
    case_root = ROOT / manifest["case_root"]
    failures: list[str] = []
    for variant in manifest["variants"]:
        case_dir = case_root / variant["variant_id"]
        payload = _variant_payload(manifest, variant)
        expected_files = {"system/blockMeshDict": render_block_mesh(payload), "0/U": _render_velocity_field(variant)}
        expected_files.update({relative: (BASELINE_CASE / relative).read_text(encoding="utf-8") for relative in STATIC_CASE_FILES})

        if write:
            for relative, content in expected_files.items():
                path = case_dir / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
        for relative, expected in expected_files.items():
            path = case_dir / relative
            if not path.is_file():
                failures.append(f"{path.relative_to(ROOT)}: generated file does not exist")
            elif path.read_text(encoding="utf-8") != expected:
                failures.append(f"{path.relative_to(ROOT)}: regenerate with --write")
    return failures


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--write", action="store_true", help="write the three generated OpenFOAM cases")
    parser.add_argument("--check", action="store_true", help="validate the manifest and generated files")
    args = parser.parse_args(arguments)

    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"turbo-variants: cannot read {args.manifest}: {exc}")
    errors = validate_manifest(manifest)
    if errors:
        raise SystemExit("turbo-variants: invalid manifest\n" + "\n".join(f"  - {error}" for error in errors))

    try:
        failures = materialize(manifest, write=args.write)
    except (OSError, ValueError) as exc:
        raise SystemExit(f"turbo-variants: {exc}")
    if failures:
        print("FAIL turbo variants")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    action = "generated" if args.write else "validated"
    print(f"OK   {args.manifest.relative_to(ROOT)} ({action} {len(manifest['variants'])} variants)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
