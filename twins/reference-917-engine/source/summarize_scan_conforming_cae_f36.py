#!/usr/bin/env python3
"""Consolide les recalculs F36 sans promouvoir un ecran numerique en validation."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path


AIR_GAS_CONSTANT_J_KG_K = 287.05
AIR_CP_J_KG_K = 1007.0


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def last_data_row(path: Path) -> list[str] | None:
    if not path.is_file():
        return None
    rows = [line.split() for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line and not line.startswith("#")]
    return rows[-1] if rows else None


def previous_data_row(path: Path) -> list[str] | None:
    if not path.is_file():
        return None
    rows = [line.split() for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line and not line.startswith("#")]
    return rows[-2] if len(rows) >= 2 else None


def relative_change(a: float, b: float) -> float:
    return abs(a - b) / max(abs(b), 1.0e-12)


def resolve_case_path(cases_path: Path, item: dict) -> Path:
    recorded = Path(item["path"])
    if recorded.is_dir():
        return recorded
    portable = cases_path.parent / item["mesh_id"]
    return portable


def openfoam_case(case: Path, target_mass_flow: float, inlet_temperature: float, outlet_pressure: float, inlet_area: float) -> dict:
    fluid_log = case / "log.fluid"
    check_default = case / "log.checkMesh-default"
    check_strict = case / "log.checkMesh-strict"
    fluid_text = fluid_log.read_text(encoding="utf-8", errors="replace") if fluid_log.is_file() else ""
    default_text = check_default.read_text(encoding="utf-8", errors="replace") if check_default.is_file() else ""
    strict_text = check_strict.read_text(encoding="utf-8", errors="replace") if check_strict.is_file() else ""
    cell_match = re.search(r"^\s*cells:\s+(\d+)", default_text, re.MULTILINE)
    failed_match = re.search(r"Failed\s+(\d+)\s+mesh checks", strict_text)

    root = case / "postProcessing"
    mass_row = last_data_row(root / "outletMassFlow/0/surfaceFieldValue.dat")
    temperature_row = last_data_row(root / "weightedOutletTemperature/0/surfaceFieldValue.dat")
    pressure_row = last_data_row(root / "inletPressure/0/surfaceFieldValue.dat")
    total_row = last_data_row(root / "outletTotalEnergyTerms/0/surfaceFieldValue.dat")
    heat_path = root / "headHeatFlux/0/wallHeatFlux.dat"
    heat_row = last_data_row(heat_path)
    heat_previous_row = previous_data_row(heat_path)
    if not all((mass_row, temperature_row, pressure_row, total_row, heat_row)):
        run_status_path = case / "run-status.json"
        run_status = (
            json.loads(run_status_path.read_text(encoding="utf-8"))
            if run_status_path.is_file()
            else None
        )
        return {
            "mesh_id": case.name,
            "status": run_status.get("status", "incomplete") if run_status else "incomplete",
            "reason": run_status.get("reason") if run_status else None,
            "solver_completed": "\nEnd\n" in f"\n{fluid_text}\n",
            "standard_mesh_check_passed": "Mesh OK." in default_text,
            "strict_mesh_check_passed": bool(strict_text) and failed_match is None and "Mesh OK." in strict_text,
        }

    mass_flow = abs(float(mass_row[1]))
    outlet_temperature = float(temperature_row[1])
    inlet_pressure = float(pressure_row[1])
    outlet_velocity_squared = float(total_row[2])
    heat_rejection = float(heat_row[4])
    mean_heat_flux = float(heat_row[5])
    rho_inlet = inlet_pressure / (AIR_GAS_CONSTANT_J_KG_K * inlet_temperature)
    inlet_velocity = mass_flow / (rho_inlet * inlet_area)
    outlet_energy_gain = mass_flow * (
        AIR_CP_J_KG_K * (outlet_temperature - inlet_temperature)
        + 0.5 * (outlet_velocity_squared - inlet_velocity * inlet_velocity)
    )
    energy_error = abs(outlet_energy_gain - heat_rejection) / max(abs(heat_rejection), 1.0e-12)
    heat_change = (
        relative_change(heat_rejection, float(heat_previous_row[4]))
        if heat_previous_row is not None
        else None
    )
    solver_completed = "\nEnd\n" in f"\n{fluid_text}\n"
    standard_mesh = "Mesh OK." in default_text
    strict_mesh = bool(strict_text) and failed_match is None and "Mesh OK." in strict_text
    checks = {
        "solver_completed": solver_completed,
        "standard_mesh_check_passed": standard_mesh,
        "strict_mesh_check_passed": strict_mesh,
        "mass_flow_within_0p5_percent": relative_change(mass_flow, target_mass_flow) <= 0.005,
        "energy_balance_within_5_percent": energy_error <= 0.05,
        "last_heat_change_within_2_percent": heat_change is not None and heat_change <= 0.02,
        "outlet_temperature_bounded": inlet_temperature <= outlet_temperature <= 533.15,
    }
    return {
        "mesh_id": case.name,
        "status": "passed_reference_screen" if all(value for key, value in checks.items() if key != "strict_mesh_check_passed") else "failed",
        "cells": int(cell_match.group(1)) if cell_match else None,
        "strict_failed_mesh_checks": int(failed_match.group(1)) if failed_match else 0,
        "results": {
            "mass_flow_kg_s": mass_flow,
            "outlet_temperature_k": outlet_temperature,
            "wall_heat_rejection_w": heat_rejection,
            "mean_wall_heat_flux_w_m2": mean_heat_flux,
            "inlet_static_pressure_pa": inlet_pressure,
            "pressure_drop_pa": inlet_pressure - outlet_pressure,
            "inlet_velocity_from_mass_and_ideal_gas_m_s": inlet_velocity,
            "outlet_mass_weighted_velocity_squared_m2_s2": outlet_velocity_squared,
            "outlet_total_energy_gain_w": outlet_energy_gain,
            "relative_energy_balance_error": energy_error,
            "last_heat_relative_change": heat_change,
        },
        "checks": checks,
        "log_sha256": sha256(fluid_log) if fluid_log.is_file() else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--calculix", type=Path, nargs="+", required=True)
    parser.add_argument("--fluidx3d", type=Path, nargs="+", required=True)
    parser.add_argument("--fluidx3d-sensitivity", type=Path, nargs="*", default=[])
    parser.add_argument("--cycle", type=Path)
    parser.add_argument("--two-four-valve-report", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    boundary = cases["boundary_condition"]
    openfoam = [
        openfoam_case(
            resolve_case_path(args.cases, item),
            float(boundary["target_mass_flow_kg_s"]),
            float(boundary["inlet_temperature_k"]),
            float(boundary["outlet_static_pressure_pa"]),
            float(cases["cases"][0].get("inlet_cross_section_m2", 0.03)) if "inlet_cross_section_m2" in cases["cases"][0] else 0.03,
        )
        for item in cases["cases"]
    ]
    completed_openfoam = [item for item in openfoam if "results" in item]
    openfoam_grid = None
    if len(completed_openfoam) >= 2:
        previous, current = completed_openfoam[-2:]
        openfoam_grid = {
            "last_two_heat_relative_change": relative_change(
                current["results"]["wall_heat_rejection_w"], previous["results"]["wall_heat_rejection_w"]
            ),
            "last_two_pressure_drop_relative_change": relative_change(
                current["results"]["pressure_drop_pa"], previous["results"]["pressure_drop_pa"]
            ),
        }

    calculix = [json.loads(path.read_text(encoding="utf-8")) for path in args.calculix]
    calculix.sort(key=lambda item: item["mesh"]["pitch_mm_if_obj_unit_is_mm"], reverse=True)
    calculix_grid = None
    if len(calculix) >= 2:
        previous, current = calculix[-2:]
        calculix_grid = {
            "last_two_p95_stress_relative_change": relative_change(
                current["results"]["von_mises_p95_mpa"], previous["results"]["von_mises_p95_mpa"]
            ),
            "last_two_maximum_displacement_relative_change": relative_change(
                current["results"]["maximum_displacement_mm"], previous["results"]["maximum_displacement_mm"]
            ),
            "maximum_stress_below_hot_yield_all_meshes": all(
                item["results"]["von_mises_max_mpa"] <= item["material"]["hot_yield_mpa_at_250c"] for item in calculix
            ),
        }

    fluidx = [json.loads(path.read_text(encoding="utf-8")) for path in args.fluidx3d]
    fluidx.sort(key=lambda item: item["cell_size_mm"], reverse=True)
    fluidx_sensitivity = [
        {
            "path": str(path),
            "sha256": sha256(path),
            **json.loads(path.read_text(encoding="utf-8")),
        }
        for path in args.fluidx3d_sensitivity
    ]
    fluidx_sensitivity.sort(key=lambda item: item["effective_thermal_diffusivity_m2_s"])
    fluidx_grid = None
    if len(fluidx) >= 2:
        previous, current = fluidx[-2:]
        fluidx_grid = {
            "last_two_heat_relative_change": relative_change(current["heat_rejection_w"], previous["heat_rejection_w"]),
            "last_two_drag_pressure_relative_change": relative_change(
                current["pressure_drop_from_drag_pa"], previous["pressure_drop_from_drag_pa"]
            ),
        }

    stable_fluidx = [item for item in fluidx if item.get("numerically_stable") and item.get("converged")]
    cross_solver = None
    if completed_openfoam and stable_fluidx:
        openfoam_reference = completed_openfoam[-1]
        fluidx_reference = stable_fluidx[-1]
        openfoam_heat = openfoam_reference["results"]["wall_heat_rejection_w"]
        openfoam_pressure = openfoam_reference["results"]["pressure_drop_pa"]
        cross_solver = {
            "openfoam_mesh_id": openfoam_reference["mesh_id"],
            "fluidx3d_grid": fluidx_reference["grid"],
            "heat_relative_difference_from_openfoam": relative_change(
                fluidx_reference["heat_rejection_w"], openfoam_heat
            ),
            "pressure_relative_difference_from_openfoam": relative_change(
                fluidx_reference["pressure_drop_from_drag_pa"], openfoam_pressure
            ),
            "classification": "nominal_boundary_cross_check_with_different_turbulence_and_pressure_estimators",
        }

    cycle = None
    if args.cycle is not None:
        cycle_payload = json.loads(args.cycle.read_text(encoding="utf-8"))
        cycle = {
            "path": str(args.cycle),
            "sha256": sha256(args.cycle),
            "status": cycle_payload.get("status"),
            "classification": "F33_geometry_independent_zero_dimensional_load_screen_not_F36_flow_validation",
            "forward_predictions": [
                {
                    "variant_id": item["variant_id"],
                    "configuration": item["configuration"],
                    "peak_pressure_pa_abs": item["forward_prediction"]["idealized_states"]["constant_volume_equilibrium_end"]["pressure_pa_abs"],
                    "forward_predicted_mechanical_hp": item["forward_prediction"]["work_and_power"]["forward_predicted_mechanical_hp"],
                }
                for item in cycle_payload["forward_predictions"]
            ],
        }

    valve_comparison = None
    if args.two_four_valve_report is not None:
        comparison = json.loads(args.two_four_valve_report.read_text(encoding="utf-8"))
        valve_comparison = {
            "path": str(args.two_four_valve_report),
            "sha256": sha256(args.two_four_valve_report),
            "status": comparison.get("status"),
            "classification": "reexecuted_F33_equivalent_ports_and_zero_dimensional_proxy_not_scan_conforming_F36_internal_flow",
            "openfoam_fine_mass_flow_gain_4v_percent": comparison["equivalent_port_cfd"]["four_valve_fine_mass_flow_change_percent"],
            "virtual_flowbench_peak_gain_4v_percent": comparison["virtual_flowbench"]["four_valve_peak_flow_gain_percent"],
            "zero_dimensional_power_gain_4v_at_9000rpm_percent": comparison["zero_dimensional_engine_dyno"]["four_valve_power_change_at_9000rpm_percent"],
            "physical_correlation_used": False,
        }

    campaign_complete = len(completed_openfoam) == len(cases["cases"]) and len(fluidx) >= 2
    report = {
        "schema_version": "1.0.0",
        "phase": "F36",
        "status": (
            "recalculated_screening_complete_release_blocked"
            if campaign_complete
            else "recalculation_in_progress_release_blocked"
        ),
        "classification": "scan_conforming_multisolver_virtual_screen_not_physical_validation",
        "openfoam_external_air": {
            "classification": "steady_RANS_fixed_wall_temperature_not_CHT",
            "cases": openfoam,
            "grid_comparison": openfoam_grid,
        },
        "fluidx3d_external_air": {
            "classification": "independent_LBM_fixed_wall_temperature_cross_check_not_CHT",
            "cases": fluidx,
            "grid_comparison": fluidx_grid,
            "thermal_diffusivity_sensitivity": fluidx_sensitivity,
        },
        "external_air_cross_solver_comparison": cross_solver,
        "calculix_thermomechanical": {
            "classification": "linear_elastic_prescribed_temperature_pressure_screen_not_TMF",
            "cases": calculix,
            "grid_comparison": calculix_grid,
        },
        "cycle_load_reference": cycle,
        "two_vs_four_valve_proxy": valve_comparison,
        "release_gates": {
            "absolute_scale_confirmed": False,
            "openfoam_strict_mesh_all_passed": bool(openfoam) and all(item.get("checks", {}).get("strict_mesh_check_passed", False) for item in openfoam),
            "openfoam_grid_independence": bool(openfoam_grid) and max(openfoam_grid.values()) <= 0.05,
            "fluidx3d_all_stable_and_converged": bool(fluidx) and all(item.get("numerically_stable") and item.get("converged") for item in fluidx),
            "fluidx3d_grid_independence": bool(fluidx_grid) and max(fluidx_grid.values()) <= 0.05,
            "openfoam_fluidx3d_heat_agreement_within_10_percent": bool(cross_solver)
            and cross_solver["heat_relative_difference_from_openfoam"] <= 0.10,
            "openfoam_fluidx3d_pressure_agreement_within_20_percent": bool(cross_solver)
            and cross_solver["pressure_relative_difference_from_openfoam"] <= 0.20,
            "calculix_p95_and_displacement_grid_independence": bool(calculix_grid)
            and calculix_grid["last_two_p95_stress_relative_change"] <= 0.05
            and calculix_grid["last_two_maximum_displacement_relative_change"] <= 0.05,
            "calculix_peak_stress_below_hot_yield": bool(calculix_grid) and calculix_grid["maximum_stress_below_hot_yield_all_meshes"],
            "full_3d_conjugate_heat_transfer": False,
            "temperature_dependent_material_card_from_printed_coupons": False,
            "nonlinear_contact_creep_fatigue_tmf": False,
            "closed_internal_flow_domains_2v_and_4v": False,
            "physical_flowbench_correlation": False,
            "ct_ndt": False,
            "engine_dyno_correlation": False,
            "metal_print_authorized": False,
            "engine_start_authorized": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
