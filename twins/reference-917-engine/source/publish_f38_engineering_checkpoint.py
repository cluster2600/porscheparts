#!/usr/bin/env python3
"""Publie le checkpoint F38 sans transformer ses écrans en autorisation."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def bind(path: Path) -> dict:
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": digest(path),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--engineering-view", type=Path, required=True)
    parser.add_argument("--contact-sheet", type=Path, required=True)
    parser.add_argument("--coupon-plan", type=Path, required=True)
    parser.add_argument("--coupon-image", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "twins/reference-917-engine/evidence/f38-engineering-checkpoint",
    )
    args = parser.parse_args()

    brep_path = ROOT / "twins/reference-917-engine/evidence/f38-brep-lpbf/f38-brep-lpbf-report.json"
    cooling_path = ROOT / "twins/reference-917-engine/evidence/f38-cooling-redesign/f38-cooling-cross-check.json"
    carrier_path = ROOT / "twins/reference-917-engine/f38-rocker-carrier-redesign.json"
    valvetrain_path = ROOT / "twins/reference-917-engine/evidence/f38-valvetrain-package/f38-valvetrain-package-report.json"
    material_path = ROOT / "twins/reference-917-engine/f38-material-coupon-qualification.json"
    ice_path = ROOT / "twins/reference-917-engine/evidence/f37-ice-engine-foam/report.json"
    cantera_path = ROOT / "twins/reference-917-engine/evidence/f33/cycle-thermal-report.json"

    brep = load(brep_path)
    cooling = load(cooling_path)
    carrier = load(carrier_path)
    valvetrain = load(valvetrain_path)
    coupon_plan = load(args.coupon_plan)
    ice = load(ice_path)

    if brep["release_gates"]["metal_print_authorized"]:
        raise RuntimeError("brep_print_gate_must_remain_false")
    if cooling["decision"]["metal_print_authorized"]:
        raise RuntimeError("cooling_print_gate_must_remain_false")
    if carrier["release_gates"]["engine_start_authorized"]:
        raise RuntimeError("carrier_start_gate_must_remain_false")
    if coupon_plan["result"]["campaign_executed"]:
        raise RuntimeError("coupon_campaign_was_not_executed")

    args.output.mkdir(parents=True, exist_ok=True)
    copies = {
        "917-head-f38-engineering-views.png": args.engineering_view,
        "917-head-f38-functional-contact-sheet.png": args.contact_sheet,
        "917-head-f38-functional.mp4": args.video,
        "917-head-f38-hot-coupon-matrix.png": args.coupon_image,
        "f38-hot-coupon-qualification-plan.json": args.coupon_plan,
    }
    artifacts = {}
    for name, source in copies.items():
        target = args.output / name
        shutil.copy2(source, target)
        artifacts[name] = {
            "bytes": target.stat().st_size,
            "sha256": digest(target),
        }

    openfoam_cases = cooling["openfoam"]["cases"]
    report = {
        "schema_version": "1.0.0",
        "phase": "F38",
        "status": "scan_conforming_engineering_checkpoint_release_blocked",
        "classification": "virtual_evidence_bundle_not_production_cad_not_manufacturing_release",
        "source_reports": {
            "geometry_and_lpbf": bind(brep_path),
            "cooling": bind(cooling_path),
            "rocker_carrier_contract": bind(carrier_path),
            "valvetrain_package": bind(valvetrain_path),
            "material_contract": bind(material_path),
            "ice_engine_reference": bind(ice_path),
            "cantera_reference": bind(cantera_path),
        },
        "geometry": {
            "scan_morphology_preserved": True,
            "boxy_prototype_rejected": True,
            "constructed_offset_mm_if_scan_unit_is_mm": 0.45,
            "authoritative_local_mesh_sha256": brep["geometry_hierarchy"]["authoritative_surface_master"]["sha256"],
            "production_brep_complete": brep["release_gates"]["whole_head_production_brep"],
            "minimum_wall_mm": brep["independent_screens"]["minimum_wall_sample"]["minimum_mm"],
            "minimum_wall_requirement_mm": brep["independent_screens"]["minimum_wall_sample"]["requirement_mm"],
            "trapped_void_volume_mm3_at_1_mm": brep["independent_screens"]["trapped_void_voxel_resolution_study"]["results"][-1]["trapped_volume_mm3"],
            "void_study_converged": brep["independent_screens"]["trapped_void_voxel_resolution_study"]["resolution_converged"],
            "support_area_fraction": brep["independent_screens"]["lpbf_overhang_screen"]["support_area_fraction"],
            "gmsh_volume_mesh_success": brep["independent_screens"]["gmsh_volume_mesh"]["success"],
        },
        "valvetrain": {
            "valves": 4,
            "guides": 4,
            "seats": 4,
            "springs": 8,
            "rockers": 4,
            "rocker_shafts": 2,
            "total_separate_solids": valvetrain["architecture"]["total_separate_solids"],
            "components_are_separate_analytic_parts": True,
            "integrated_dimensional_fit_proved": False,
            "cam_profile_measured": carrier["release_gates"]["cam_profile_measured"],
            "nonlinear_contact_complete": carrier["release_gates"]["nonlinear_contact_complete"],
            "fatigue_and_thermal_cycle_complete": carrier["release_gates"]["fatigue_and_thermal_cycle_complete"],
            "structural_proof": valvetrain["release_gates"]["structural_proof"],
        },
        "structure": valvetrain["structural_status"],
        "cooling": {
            "openfoam_cell_counts": [item["cell_count"] for item in openfoam_cases],
            "openfoam_effective_h_w_m2k": [item["effective_h_w_m2k"] for item in openfoam_cases],
            "openfoam_fine_energy_balance_relative": openfoam_cases[-1]["energy_balance_relative"],
            "independent_gnielinski_effective_h_w_m2k": cooling["analytical_method"]["effective_h_w_m2k"],
            "h_relative_difference": cooling["cross_method"]["h_relative_difference"],
            "pressure_drop_relative_difference": cooling["cross_method"]["pressure_drop_relative_difference"],
            "projected_bridge_temperature_range_c": [
                cooling["thermal_projection"]["from_openfoam"]["bridge_temperature_c"],
                cooling["thermal_projection"]["from_analytical"]["bridge_temperature_c"],
            ],
            "whole_head_cht_complete": cooling["decision"]["whole_head_CHT_complete"],
            "temperature_screen_passed": cooling["decision"]["temperature_screen_passed"],
        },
        "material": {
            "candidate_only": brep["material_status"]["candidate_only"],
            "coupon_count_planned": coupon_plan["coupon_count_total"],
            "coupon_count_executed": 0,
            "hot_material_card_qualified": coupon_plan["result"]["material_card_qualified"],
        },
        "engine_solver_boundary": {
            "exact_ice_engine_foam_executable_executed": ice["gates"]["exact_iceEngineFoam_executable_executed"],
            "generic_xifluid_tutorial_executed": True,
            "generic_tutorial_valve_count": ice["executed_reference_case"]["valve_count"],
            "f38_geometry_coupled": False,
            "cantera_0d_reference_executed": True,
            "cantera_coupled_to_f38_cfd": False,
            "pressure_cross_method_passed": ice["cantera_load_boundary"]["pressure_cross_method_passed"],
        },
        "artifacts": artifacts,
        "release_gates": {
            "absolute_scale_confirmed": False,
            "porsche_917_interfaces_measured": False,
            "production_brep_complete": False,
            "full_head_cht_complete": False,
            "thermomechanical_fatigue_complete": False,
            "virtual_lpbf_process_simulation_complete": False,
            "hot_material_card_qualified": False,
            "physical_ct_ndt_complete": False,
            "physical_flow_bench_correlated": False,
            "physical_engine_bench_correlated": False,
            "metal_print_authorized": False,
            "engine_start_authorized": False,
        },
        "verdict": "F38 corrige la morphologie extérieure, mais échoue les portes géométrie, maillage, refroidissement et qualification matière. Impression métal et démarrage moteur interdits.",
    }
    (args.output / "f38-engineering-checkpoint.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
