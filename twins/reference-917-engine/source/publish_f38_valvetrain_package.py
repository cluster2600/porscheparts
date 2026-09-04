#!/usr/bin/env python3
"""Publie les STEP analytiques séparés de la distribution F38, fail-closed."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

from build123d import import_step


COMPONENTS = (
    ("rocker-carrier-f38-rounded-reinforced", 1, "porte_axes"),
    ("two-rocker-shafts-f38", 2, "axes"),
    ("four-rockers-f38", 4, "culbuteurs"),
    ("two-intake-valves-f38", 2, "soupapes_admission"),
    ("two-exhaust-valves-f38", 2, "soupapes_echappement"),
    ("four-valve-guides-f38", 4, "guides"),
    ("four-valve-seats-f38", 4, "sieges"),
    ("eight-valve-springs-f38", 8, "ressorts_concentriques"),
    ("four-lower-spring-cups-f38", 4, "coupelles_inferieures"),
    ("four-upper-spring-retainers-f38", 4, "coupelles_superieures"),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--source-report", type=Path, required=True)
    parser.add_argument("--cad", type=Path, required=True)
    parser.add_argument("--f38-calculix-report", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    source_report = json.loads(args.source_report.read_text(encoding="utf-8"))
    calculix_report = json.loads(args.f38_calculix_report.read_text(encoding="utf-8"))
    require(spec["phase"] == "F38", "spec_phase_not_F38")
    require(source_report["phase"] == "F38", "source_report_phase_not_F38")
    require(calculix_report["phase"] == "F38", "calculix_report_phase_not_F38")
    require(calculix_report["gates"]["three_meshes_complete"], "calculix_three_meshes_incomplete")
    by_id = {item["id"]: item for item in source_report["artifacts"]}
    args.output.mkdir(parents=True, exist_ok=True)
    cad_output = args.output / "cad"
    cad_output.mkdir(parents=True, exist_ok=True)

    artifacts = []
    for identifier, expected_solids, role in COMPONENTS:
        source = args.cad / f"{identifier}.step"
        require(source.is_file(), f"missing_STEP:{source}")
        require(identifier in by_id, f"missing_source_report_item:{identifier}")
        require(sha256(source) == by_id[identifier]["step"]["sha256"], f"source_report_hash_mismatch:{identifier}")
        shape = import_step(source)
        solids = list(shape.solids())
        require(len(solids) == expected_solids, f"solid_count_mismatch:{identifier}")
        require(bool(shape.is_valid) and bool(shape.is_manifold), f"invalid_STEP:{identifier}")
        require(all(solid.is_valid and solid.is_manifold for solid in solids), f"invalid_solid:{identifier}")
        destination = cad_output / source.name
        shutil.copy2(source, destination)
        artifacts.append({
            "id": identifier,
            "role": role,
            "component_count": expected_solids,
            "step": {
                "path": f"cad/{destination.name}",
                "bytes": destination.stat().st_size,
                "sha256": sha256(destination),
            },
            "independent_reimport": {
                "solid_count": len(solids),
                "valid": True,
                "manifold": True,
                "all_solids_closed": True,
                "volume_mm3_if_scale_is_mm": round(sum(solid.volume for solid in solids), 6),
            },
        })

    image_destination = args.output / "917-f38-valvetrain-package.png"
    shutil.copy2(args.image, image_destination)
    report = {
        "schema_version": "1.0.0",
        "phase": "F38",
        "status": "analytic_valvetrain_component_package_published_release_blocked",
        "classification": "conditional_analytic_OCCT_components_not_fitted_or_dynamically_validated",
        "inputs": {
            "spec": {"path": str(args.spec), "sha256": sha256(args.spec)},
            "source_cad_report": {"path": str(args.source_report), "sha256": sha256(args.source_report)},
            "f38_calculix_report": {"path": str(args.f38_calculix_report), "sha256": sha256(args.f38_calculix_report)},
            "builder": {"path": "twins/reference-917-engine/source/build_f38_rocker_carrier.py", "sha256": sha256(Path(__file__).with_name("build_f38_rocker_carrier.py"))},
            "publisher": {"path": "twins/reference-917-engine/source/publish_f38_valvetrain_package.py", "sha256": sha256(Path(__file__))},
            "renderer": {"path": "twins/reference-917-engine/source/render_f38_valvetrain_package.py", "sha256": sha256(Path(__file__).with_name("render_f38_valvetrain_package.py"))},
        },
        "architecture": {
            "separate_step_files": True,
            "published_monolithic_assembly": False,
            "total_separate_solids": sum(item[1] for item in COMPONENTS),
            "valves": 4,
            "guides": 4,
            "seats": 4,
            "springs": 8,
            "rocker_shafts": 2,
            "rockers": 4,
            "lower_spring_cups": 4,
            "upper_spring_retainers": 4,
        },
        "artifacts": artifacts,
        "image": {
            "path": image_destination.name,
            "bytes": image_destination.stat().st_size,
            "sha256": sha256(image_destination),
            "classification": "analytic_multi_body_assembly_and_half_section_visualization",
            "contains_scan_geometry": False,
        },
        "structural_status": {
            "f38_calculix_three_grid_screen_present": True,
            "classification": calculix_report["classification"],
            "mesh_sizes_mm": [case["mesh"]["mesh_size_mm"] for case in calculix_report["cases"]],
            "finest_raw_maximum_mpa": calculix_report["cases"][-1]["von_mises_mpa"]["maximum"],
            "finest_p99_mpa": calculix_report["cases"][-1]["von_mises_mpa"]["p99"],
            "finest_maximum_displacement_mm": calculix_report["cases"][-1]["maximum_displacement_mm"],
            "p99_grid_change_below_10_percent": calculix_report["gates"]["p99_grid_change_below_10_percent"],
            "raw_maximum_grid_change_below_10_percent": calculix_report["gates"]["raw_maximum_grid_change_below_10_percent"],
            "actual_resultant_direction_complete": calculix_report["gates"]["actual_resultant_direction_complete"],
            "nonlinear_contact_complete": calculix_report["gates"]["nonlinear_contact_complete"],
            "qualified_material_card": calculix_report["gates"]["qualified_material_card"],
            "fatigue_and_thermal_cycle_complete": calculix_report["gates"]["fatigue_and_thermal_cycle_complete"],
            "f37_parent_linear_screen_transfer_allowed": False,
            "structural_proof": False,
            "reason": "le calcul lineaire trois maillages est un ecran; maximum brut non converge, chargements, contacts, matiere et fatigue non valides",
        },
        "release_gates": {
            "all_published_step_roundtrips_valid_closed": True,
            "component_counts_verified": True,
            "absolute_scale_confirmed": False,
            "porsche_917_mating_interfaces_confirmed": False,
            "cam_profile_measured": False,
            "kinematic_clearances_validated": False,
            "dynamic_valvetrain_correlated": False,
            "nonlinear_contacts_validated": False,
            "spring_surge_and_coil_bind_validated": False,
            "fatigue_and_thermal_cycles_validated": False,
            "qualified_material_cards": False,
            "structural_proof": False,
            "metal_print_authorized": False,
            "engine_start_authorized": False,
        },
        "verdict": "GEOMETRIE ANALYTIQUE MULTI-CORPS SEULEMENT. Interfaces, jeux, cinematique, contacts, lubrification, ressorts, fatigue et tenue thermique restent a valider avant fabrication.",
    }
    (args.output / "f38-valvetrain-package-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": report["status"], "step_files": len(artifacts), "solids": report["architecture"]["total_separate_solids"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
