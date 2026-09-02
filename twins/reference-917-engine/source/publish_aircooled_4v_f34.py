#!/usr/bin/env python3
"""Publie les preuves F34 calculées sans publier les géométries lourdes."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
from pathlib import Path


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative_difference(a: float, b: float) -> float:
    return abs(a - b) / max(abs(a), abs(b), 1.0e-30)


def last_rows(root: Path, pattern: str) -> list[list[str]]:
    candidates = sorted(
        root.glob(pattern),
        key=lambda path: float(path.parent.name) if path.parent.name.replace(".", "", 1).isdigit() else -1.0,
    )
    rows_by_time: dict[float, list[str]] = {}
    for path in candidates:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip() and not line.lstrip().startswith("#"):
                row = line.split()
                rows_by_time[float(row[0])] = row
    return [rows_by_time[time] for time in sorted(rows_by_time)]


def parse_openfoam(case: Path, geometry: dict) -> dict:
    metadata = load(case / "case-metadata.json")
    mesh_log = (case / "log.checkMesh-default").read_text(encoding="utf-8", errors="replace")
    strict_log = (case / "log.checkMesh-strict").read_text(encoding="utf-8", errors="replace")
    solver_logs = sorted(case.glob("log.fluid*"))
    combined_solver_log = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in solver_logs)
    cells_match = re.findall(r"^\s*cells:\s+([0-9]+)", mesh_log, flags=re.MULTILINE)
    concave_match = re.search(r"Concave cells .* number of cells:\s*([0-9]+)", strict_log)
    weight_match = re.search(r"small interpolation weight .* number of faces:\s*([0-9]+)", strict_log)
    heat_rows = last_rows(case / "postProcessing/headHeatFlux", "*/wallHeatFlux.dat")
    mass_rows = last_rows(case / "postProcessing/outletMassFlow", "*/surfaceFieldValue.dat")
    weighted_outlet_rows = last_rows(case / "postProcessing/weightedOutletTemperature", "*/surfaceFieldValue.dat")
    total_energy_rows = last_rows(case / "postProcessing/outletTotalEnergyTerms", "*/surfaceFieldValue.dat")
    outlet_rows = last_rows(case / "postProcessing/outletTemperature", "*/surfaceFieldValue.dat")
    inlet_pressure_rows = last_rows(case / "postProcessing/inletPressure", "*/surfaceFieldValue.dat")
    residual_rows = last_rows(case / "postProcessing/residuals", "*/residuals.dat")
    if not heat_rows or not mass_rows or not outlet_rows:
        raise ValueError("résultats OpenFOAM incomplets")
    heat = heat_rows[-1]
    mass = mass_rows[-1]
    outlet = outlet_rows[-1]
    q_w = abs(float(heat[4]))
    mass_flow = float(mass[1])
    outlet_temperature = (
        float(total_energy_rows[-1][1])
        if total_energy_rows
        else float(weighted_outlet_rows[-1][1])
        if weighted_outlet_rows
        else float(outlet[1])
    )
    outlet_enthalpy_gain_w = mass_flow * 1007.0 * (outlet_temperature - 308.15)
    outlet_velocity_squared = float(total_energy_rows[-1][2]) if total_energy_rows else None
    inlet_velocity_squared = float(metadata["velocity_m_s"]) ** 2
    outlet_total_energy_gain_w = (
        outlet_enthalpy_gain_w
        + 0.5 * mass_flow * (outlet_velocity_squared - inlet_velocity_squared)
        if outlet_velocity_squared is not None
        else outlet_enthalpy_gain_w
    )
    energy_imbalance = relative_difference(q_w, outlet_total_energy_gain_w)
    area = geometry["geometry"]["external_cooling_envelope"]["surface_area_m2"]
    delta_t = 533.15 - 308.15
    heat_change = (
        relative_difference(abs(float(heat_rows[-2][4])), q_w)
        if len(heat_rows) > 1
        else None
    )
    latest_residuals = residual_rows[-1] if residual_rows else []
    return {
        "classification": "actual_full_external_head_steady_compressible_RANS_FVM_fixed_wall_temperature",
        "solver": "OpenFOAM_14_fluid_kOmegaSST",
        "mesh": {
            "cells": int(cells_match[-1]) if cells_match else None,
            "standard_check_mesh_passed": "Mesh OK." in mesh_log,
            "strict_check_mesh_passed": "Failed 0 mesh checks" in strict_log,
            "strict_advisories": {
                "concave_cells": int(concave_match.group(1)) if concave_match else None,
                "small_interpolation_weight_faces": int(weight_match.group(1)) if weight_match else None,
            },
        },
        "results": {
            "latest_iteration": float(heat[0]),
            "wall_heat_rejection_w": q_w,
            "outlet_enthalpy_gain_w": outlet_enthalpy_gain_w,
            "outlet_kinetic_energy_gain_w": outlet_total_energy_gain_w - outlet_enthalpy_gain_w,
            "outlet_total_energy_gain_w": outlet_total_energy_gain_w,
            "relative_energy_imbalance": energy_imbalance,
            "effective_h_w_m2k": q_w / (area * delta_t),
            "outlet_mass_flow_kg_s": mass_flow,
            "outlet_temperature_k": outlet_temperature,
            "outlet_temperature_averaging": "mass_flux_weighted" if total_energy_rows or weighted_outlet_rows else "area_average",
            "outlet_velocity_squared_m2_s2": outlet_velocity_squared,
            "inlet_velocity_squared_m2_s2": inlet_velocity_squared,
            "outlet_pressure_pa": float(outlet[2]),
            "inlet_pressure_pa": float(inlet_pressure_rows[-1][1]) if inlet_pressure_rows else None,
            "pressure_drop_pa": (
                float(inlet_pressure_rows[-1][1]) - float(outlet[2])
                if inlet_pressure_rows
                else None
            ),
            "relative_heat_rejection_change_last_sample": heat_change,
            "latest_initial_residual_row": latest_residuals,
        },
        "solver_completed": combined_solver_log.rstrip().endswith("End"),
        "mesh_independence_demonstrated": False,
        "converged_for_cross_method_screen": bool(
            combined_solver_log.rstrip().endswith("End")
            and heat_change is not None
            and heat_change <= 0.02
            and energy_imbalance <= 0.05
        ),
        "release_claim": False,
    }


def sanitize(value):
    if isinstance(value, dict):
        return {key: sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, str):
        value = re.sub(r"/(?:private/)?tmp/[^\s\"']+", "<local-path>", value)
        value = re.sub(r"/Users/[^\s\"']+", "<local-path>", value)
    return value


def compare_calculix(paths: list[Path]) -> dict:
    reports = [load(path) for path in paths]
    rows = [
        {
            "maximum_size_mm": item["mesh"]["maximum_size_mm"],
            "linear_tetrahedra": item["mesh"]["linear_tetrahedra"],
            **item["results"],
        }
        for item in reports
    ]
    a, b = rows[-2], rows[-1]
    differences = {
        "p95_stress": relative_difference(a["von_mises_p95_mpa"], b["von_mises_p95_mpa"]),
        "maximum_stress": relative_difference(a["von_mises_max_mpa"], b["von_mises_max_mpa"]),
        "maximum_displacement": relative_difference(a["maximum_displacement_mm"], b["maximum_displacement_mm"]),
    }
    return {
        "classification": "actual_F34_CAD_linear_elastic_combined_pressure_thermal_mesh_sequence",
        "solver": "CalculiX_2.21",
        "rows": rows,
        "finest_pair_relative_differences": differences,
        "stress_mesh_independence_limit_fraction": 0.10,
        "stress_mesh_independence_passed": max(differences["p95_stress"], differences["maximum_stress"]) <= 0.10,
        "displacement_mesh_independence_passed": differences["maximum_displacement"] <= 0.02,
        "finest_mesh_maximum_hot_yield_margin": 216.0 / rows[-1]["von_mises_max_mpa"],
        "finest_mesh_maximum_below_hot_yield": rows[-1]["von_mises_max_mpa"] < 216.0,
        "nonlinear_contact_creep_fatigue_tmf_included": False,
        "hot_material_card_qualified": False,
        "release_claim": False,
    }


def compare_fluidx(paths: list[Path]) -> dict:
    reports = [load(path) for path in paths]
    rows = [
        {
            "grid": item["grid"],
            "cell_size_mm": item["cell_size_mm"],
            "actual_steps": item["actual_steps"],
            "converged": item["converged"],
            "mass_flow_kg_s": item["mass_flow_kg_s"],
            "heat_rejection_w": item["heat_rejection_w"],
            "effective_h_w_m2k": item["effective_h_w_m2k"],
            "pressure_drop_from_drag_pa": item["pressure_drop_from_drag_pa"],
            "thermal_closure": item["thermal_closure"],
        }
        for item in reports
    ]
    a, b = rows[-2], rows[-1]
    differences = {
        "heat_rejection": relative_difference(a["heat_rejection_w"], b["heat_rejection_w"]),
        "effective_h": relative_difference(a["effective_h_w_m2k"], b["effective_h_w_m2k"]),
        "pressure_drop": relative_difference(a["pressure_drop_from_drag_pa"], b["pressure_drop_from_drag_pa"]),
    }
    return {
        "classification": "independent_LBM_external_cooling_constant_eddy_diffusivity_sensitivity",
        "solver": "FluidX3D_D3Q19_TRT_FP32",
        "rows": rows,
        "finest_pair_relative_differences": differences,
        "mesh_independence_limit_fraction": 0.10,
        "mesh_independence_passed": all(item <= 0.10 for item in differences.values()),
        "all_runs_statistically_converged": all(item["converged"] for item in rows),
        "reacting_or_compressible_combustion_model": False,
        "release_claim": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--geometry", type=Path, required=True)
    parser.add_argument("--preliminary", type=Path, required=True)
    parser.add_argument("--f33-reference", type=Path, required=True)
    parser.add_argument("--openfoam-case", type=Path, required=True)
    parser.add_argument("--calculix", type=Path, nargs=3, required=True)
    parser.add_argument("--fluidx3d", type=Path, nargs=3, required=True)
    parser.add_argument("--omniverse", type=Path, required=True)
    parser.add_argument("--toolchain-audit", type=Path, required=True)
    parser.add_argument("--step", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    contract = load(args.contract)
    geometry = load(args.geometry)
    preliminary = load(args.preliminary)
    f33 = load(args.f33_reference)
    expected_f33_sha = preliminary["upstream_sha256"]["twins/reference-917-engine/evidence/f33/report.json"]
    if sha256(args.f33_reference) != expected_f33_sha:
        raise ValueError("le rapport F33 2V/4V ne correspond pas au SHA-256 attendu")
    openfoam = parse_openfoam(args.openfoam_case, geometry)
    calculix = compare_calculix(args.calculix)
    fluidx = compare_fluidx(args.fluidx3d)
    openfoam_h = openfoam["results"]["effective_h_w_m2k"]
    fluidx_h = fluidx["rows"][-1]["effective_h_w_m2k"]
    cross_difference = relative_difference(openfoam_h, fluidx_h)
    cross_limit = contract["cross_verification"]["external_cooling"]["maximum_total_heat_rejection_difference_fraction"]
    pressure_difference = relative_difference(
        openfoam["results"]["pressure_drop_pa"],
        fluidx["rows"][-1]["pressure_drop_from_drag_pa"],
    )
    pressure_limit = contract["cross_verification"]["external_cooling"]["maximum_pressure_drop_difference_fraction"]
    design_mass_flow = preliminary["external_cooling"]["selected_setpoints"]["burst_air_mass_flow_kg_s_per_head"]
    openfoam_mass_flow = openfoam["results"]["outlet_mass_flow_kg_s"]
    fluidx_mass_flow = fluidx["rows"][-1]["mass_flow_kg_s"]
    openfoam_setpoint_difference = relative_difference(openfoam_mass_flow, design_mass_flow)
    fluidx_setpoint_difference = relative_difference(fluidx_mass_flow, design_mass_flow)
    external = {
        "classification": "same_77_m_s_external_domain_numerical_cross_check_not_design_mass_flow_validation",
        "method_a": openfoam,
        "method_b": fluidx,
        "design_burst_mass_flow_kg_s_per_head": design_mass_flow,
        "openfoam_mass_flow_to_design_ratio": openfoam_mass_flow / design_mass_flow,
        "fluidx3d_mass_flow_to_design_ratio": fluidx_mass_flow / design_mass_flow,
        "boundary_mass_flow_matches_design": bool(
            openfoam_setpoint_difference <= 0.10 and fluidx_setpoint_difference <= 0.10
        ),
        "relative_effective_h_difference": cross_difference,
        "cross_method_limit_fraction": cross_limit,
        "relative_pressure_drop_difference": pressure_difference,
        "pressure_drop_cross_method_limit_fraction": pressure_limit,
        "cross_method_passed": bool(
            openfoam["converged_for_cross_method_screen"]
            and fluidx["mesh_independence_passed"]
            and cross_difference <= cross_limit
            and pressure_difference <= pressure_limit
            and openfoam_setpoint_difference <= 0.10
            and fluidx_setpoint_difference <= 0.10
        ),
    }
    report = {
        "schema_version": "1.0.0",
        "phase": "F34",
        "status": "virtual_campaign_executed_release_blocked",
        "source_geometry": preliminary["source_geometry"],
        "geometry": preliminary["geometry"],
        "material_selection": preliminary["material_selection"],
        "cycle_cross_verification": preliminary["cycle_cross_verification"],
        "reduced_cooling": preliminary["external_cooling"],
        "external_cooling_3d_cross_verification": external,
        "thermomechanical_fea": calculix,
        "valvetrain": preliminary["valvetrain"],
        "two_vs_four_valve_reference": {
            "source": "F33 integrated virtual report",
            "report_sha256": expected_f33_sha,
            "new_F34_full_external_head_is_four_valve_only": True,
            "equivalent_port_2v_4v_comparison_available": True,
            "equivalent_port_cfd_classification": f33["equivalent_port_cfd"]["classification"],
            "fine_mesh_mass_flow_kg_s": {
                "two_valve": f33["equivalent_port_cfd"]["architectures"]["2v"][-1]["mass_flow_kg_s"],
                "four_valve": f33["equivalent_port_cfd"]["architectures"]["4v"][-1]["mass_flow_kg_s"],
            },
            "four_valve_fine_mass_flow_gain_percent": f33["equivalent_port_cfd"]["four_valve_fine_mass_flow_change_percent"],
            "quasi_steady_virtual_flowbench_gain_percent": f33["virtual_flowbench"]["four_valve_peak_flow_gain_percent"],
            "full_scan_seeded_2v_4v_cross_validation_complete": False,
        },
        "physicsnemo": preliminary["physicsnemo"],
        "toolchain": {
            **contract["toolchain"],
            "execution_audit": sanitize(load(args.toolchain_audit)),
            "aate_icengines_execution": {
                "compiled_in_cae_container": True,
                "moving_piston_valve_case_executed": False,
                "reason": "le scan ne fournit pas les volumes internes étanches ni la culasse 917 nécessaires",
            },
            "cantera_execution": {
                "executed_in_upstream_F33_cycle_report": True,
                "version": "3.2.0",
                "reused_with_digest_verification": True,
            },
        },
        "omniverse": {
            "status": load(args.omniverse)["status"],
            "simready_conversion_executed": False,
            "simready_validation_executed": False,
            "authorized": False,
        },
        "blocking_findings": [
            "l'échelle absolue et l'identité dimensionnelle 917 des scans ne sont pas confirmées",
            "la pression de pointe Cantera et le modèle Wiebe diffèrent au-delà du seuil F34",
            "la carte élastique, fatigue, fluage et conductivité à chaud du procédé imprimé n'est pas qualifiée",
            "le maximum de contrainte CalculiX du maillage le plus fin dépasse la limite à chaud et reste dépendant du maillage",
            "l'indépendance de maillage CFD et FEA doit être satisfaite avant CHT/TMF",
            "le second solveur EF Elmer prévu au contrat n'a pas été exécuté",
            "le cas AATE ICengines à piston et soupapes mobiles n'a pas été exécuté faute de volumes internes étanches mesurés",
            "Omniverse SimReady est bloqué au prévol officiel et aucune conversion USD n'est revendiquée",
            "aucun CT/CND, banc de flux, spintron ou banc moteur physique corrélé n'existe",
        ]
        + ([] if openfoam["converged_for_cross_method_screen"] else [
            "le calcul OpenFOAM externe ne satisfait pas encore le critère de convergence et de bilan énergétique"
        ])
        + ([] if fluidx["mesh_independence_passed"] else [
            "la séquence à trois mailles FluidX3D ne satisfait pas le seuil d'indépendance de maillage"
        ])
        + ([] if external["cross_method_passed"] else [
            "la comparaison 3D OpenFOAM/FluidX3D ne ferme pas la barrière de validation croisée"
        ])
        + ([] if external["boundary_mass_flow_matches_design"] else [
            "le domaine externe à 77 m/s traite environ dix fois le débit massique de calcul par culasse et reste une sensibilité numérique"
        ]),
        "release_gates": contract["release_gates"],
        "claims": {
            "editable_step_process_prototype_generated": True,
            "product_image_generated": True,
            "metal_print_authorized": False,
            "engine_start_authorized": False,
            "physical_validation_complete": False,
        },
    }
    if any(value is not False for value in report["release_gates"].values()):
        raise ValueError("une barrière F34 n'est pas fermée")

    args.output.mkdir(parents=True, exist_ok=False)
    dump(args.output / "report.json", report)
    dump(args.output / "geometry-report.json", geometry)
    dump(args.output / "calculix-mesh-study.json", calculix)
    dump(args.output / "fluidx3d-mesh-study.json", fluidx)
    dump(args.output / "openfoam-external-cooling.json", openfoam)
    dump(args.output / "omniverse-preflight.json", sanitize(load(args.omniverse)))
    dump(args.output / "toolchain-audit.json", sanitize(load(args.toolchain_audit)))
    shutil.copyfile(args.step, args.output / "917-head-aircooled-4v-f34-process-prototype.step")
    shutil.copyfile(args.image, args.output / "product-aircooled-4v-f34.png")
    (args.output / "README.md").write_text(
        "# Preuves F34 — culasse 4V refroidie par air\n\n"
        "Ce dossier contient le rapport consolidé, les études de maillage, "
        "l'audit des conteneurs x86, le prévol Omniverse, l'image du produit "
        "et le STEP du prototype de procédé. Le script paramétrique maître "
        "reste dans `../../source/build_aircooled_4v_head_f34.py`.\n\n"
        "Le STEP n'est ni une CAO de fabrication libérée, ni une preuve "
        "d'ajustement Porsche 917. Aucune impression métallique et aucun "
        "démarrage moteur ne sont autorisés par ces fichiers.\n",
        encoding="utf-8",
    )

    files = {
        str(path.relative_to(args.output)): sha256(path)
        for path in sorted(args.output.rglob("*"))
        if path.is_file() and path.name != "publication.json"
    }
    publication = {
        "schema_version": "1.0.0",
        "phase": "F34",
        "status": "published_virtual_evidence_not_manufacturing_or_engine_release",
        "files": files,
        "release_gates": contract["release_gates"],
    }
    dump(args.output / "publication.json", publication)
    print(json.dumps({"status": publication["status"], "file_count": len(files)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
