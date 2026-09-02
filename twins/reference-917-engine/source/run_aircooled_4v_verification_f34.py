#!/usr/bin/env python3
"""Ecrans physiques F34 et matrice de verification croisee de la culasse 4V."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def verify_contract(contract: dict, root: Path) -> dict:
    errors: list[str] = []
    observed: dict[str, str] = {}
    if contract.get("phase") != "F34":
        errors.append("phase must be F34")
    if any(value is not False for value in contract.get("release_gates", {}).values()):
        errors.append("all F34 release gates must remain literal false")
    if contract.get("toolchain", {}).get("physicsnemo", {}).get("training_authorized") is not False:
        errors.append("PhysicsNeMo training must remain blocked")
    for item in contract.get("upstream", []):
        path = root / item["path"]
        if not path.is_file():
            errors.append(f"missing upstream: {item['path']}")
            continue
        digest = sha256(path)
        observed[item["path"]] = digest
        if digest != item["sha256"]:
            errors.append(f"upstream digest mismatch: {item['path']}")
    if errors:
        raise ValueError("; ".join(errors))
    return observed


def distance(a: list[float], b: list[float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def geometry_clearances(contract: dict, geometry: dict) -> dict:
    cfg = contract["cad"]
    intake = cfg["valves"]["intake"]
    exhaust = cfg["valves"]["exhaust"]
    spark_insert_radius_mm = 6.0
    intake_radius = intake["head_diameter_mm"] / 2.0
    exhaust_radius = exhaust["head_diameter_mm"] / 2.0
    intake_pair = distance(*intake["positions_xy_mm"]) - 2.0 * intake_radius
    exhaust_pair = distance(*exhaust["positions_xy_mm"]) - 2.0 * exhaust_radius
    cross_pairs = [
        distance(i, e) - intake_radius - exhaust_radius
        for i in intake["positions_xy_mm"]
        for e in exhaust["positions_xy_mm"]
    ]
    spark_pairs = [
        math.hypot(*position) - radius - spark_insert_radius_mm
        for positions, radius in (
            (intake["positions_xy_mm"], intake_radius),
            (exhaust["positions_xy_mm"], exhaust_radius),
        )
        for position in positions
    ]
    minimum_seat_gap = min(intake_pair, exhaust_pair, *cross_pairs)
    minimum_spark_gap = min(spark_pairs)
    target = cfg["minimum_wall_targets_mm"]
    area = geometry["geometry"]["external_and_internal_surface_area_m2"]
    return {
        "classification": "nominal_2d_clearance_screen_not_tolerance_stack_or_hot_distortion",
        "intake_seat_gap_mm": intake_pair,
        "exhaust_seat_gap_mm": exhaust_pair,
        "minimum_intake_to_exhaust_seat_gap_mm": min(cross_pairs),
        "minimum_seat_gap_mm": minimum_seat_gap,
        "minimum_seat_to_spark_insert_gap_mm": minimum_spark_gap,
        "target_between_valve_seats_mm": target["between_valve_seats"],
        "target_seat_to_spark_insert_mm": target["seat_to_spark_insert"],
        "surface_area_m2": area,
        "single_watertight_brep_solid": geometry["geometry"]["solid_count"] == 1,
        "surface_area_target_passed": area >= contract["acceptance"]["minimum_external_surface_area_m2"],
        "clearance_targets_passed": (
            minimum_seat_gap >= target["between_valve_seats"]
            and minimum_spark_gap >= target["seat_to_spark_insert"]
        ),
    }


def cycle_cross_check(contract: dict, root: Path) -> dict:
    cantera_report = load_json(root / "twins/reference-917-engine/evidence/f33/cycle-thermal-report.json")
    wiebe_report = load_json(root / "twins/reference-917-engine/evidence/f33/report.json")
    cantera = next(
        row["forward_prediction"]
        for row in cantera_report["forward_predictions"]
        if row["configuration"] == "twin_turbo"
    )
    wiebe = wiebe_report["zero_dimensional_engine_dyno"]["curves"]["4v"][-1]
    power_a = cantera["work_and_power"]["forward_predicted_mechanical_hp"]
    power_b = wiebe["brake_power_mechanical_hp"]
    pressure_a = cantera["idealized_states"]["constant_volume_equilibrium_end"]["pressure_pa_abs"]
    pressure_b = wiebe["peak_cylinder_pressure_mpa"] * 1e6
    power_delta = abs(power_a - power_b) / max(power_a, power_b)
    pressure_delta = abs(pressure_a - pressure_b) / max(pressure_a, pressure_b)
    criteria = contract["cross_verification"]["cycle"]
    return {
        "classification": "two_executed_non_correlated_0d_models_not_dyno_or_combustion_validation",
        "method_a": {
            "id": criteria["method_a"],
            "power_mechanical_hp": power_a,
            "peak_pressure_mpa": pressure_a / 1e6,
            "source_report_sha256": sha256(root / "twins/reference-917-engine/evidence/f33/cycle-thermal-report.json"),
        },
        "method_b": {
            "id": criteria["method_b"],
            "power_mechanical_hp": power_b,
            "peak_pressure_mpa": pressure_b / 1e6,
            "source_report_sha256": sha256(root / "twins/reference-917-engine/evidence/f33/report.json"),
        },
        "relative_power_difference": power_delta,
        "relative_peak_pressure_difference": pressure_delta,
        "power_cross_check_passed": power_delta <= criteria["maximum_power_difference_fraction"],
        "peak_pressure_cross_check_passed": pressure_delta <= criteria["maximum_peak_pressure_difference_fraction"],
        "conservative_pressure_load_mpa": max(pressure_a, pressure_b) / 1e6,
        "target_power_proven": False,
    }


def air_properties() -> dict:
    return {
        "density_kg_m3": 1.06,
        "dynamic_viscosity_pa_s": 2.05e-5,
        "conductivity_w_mk": 0.0305,
        "prandtl": 0.70,
        "heat_capacity_j_kgk": 1007.0,
    }


def fin_efficiency(h: float, conductivity: float, thickness_m: float, length_m: float) -> float:
    ml = math.sqrt(2.0 * h / (conductivity * thickness_m)) * length_m
    return math.tanh(ml) / ml


def cooling_cross_check(contract: dict) -> dict:
    cad = contract["cad"]
    cooling = contract["cooling_design"]
    fin = cad["fin"]
    props = air_properties()
    gap_m = (fin["pitch_mm"] - fin["thickness_mm"]) / 1000.0
    channel_count = fin["count"] - 1
    width_m = fin["maximum_width_mm"] / 1000.0
    depth_m = fin["maximum_depth_mm"] / 1000.0
    free_area = width_m * gap_m * channel_count
    hydraulic_diameter = 2.0 * gap_m
    fin_length = (fin["maximum_width_mm"] - cad["body_width_mm"]) / 2000.0
    conductivity = next(
        item["screening_conductivity_w_mk"]
        for item in contract["materials"]["head_candidates"]
        if item["id"] == contract["materials"]["selected_virtual_candidate"]
    )
    effective_area = cooling["fin_area_target_m2_per_head"]
    base_area = 0.08
    rows = []
    for mass_flow in cooling["air_mass_flow_points_kg_s_per_head"]:
        velocity = mass_flow / (props["density_kg_m3"] * free_area)
        reynolds = (
            props["density_kg_m3"]
            * velocity
            * hydraulic_diameter
            / props["dynamic_viscosity_pa_s"]
        )
        darcy_a = (0.79 * math.log(reynolds) - 1.64) ** -2
        nusselt_a = (
            (darcy_a / 8.0)
            * (reynolds - 1000.0)
            * props["prandtl"]
            / (
                1.0
                + 12.7
                * math.sqrt(darcy_a / 8.0)
                * (props["prandtl"] ** (2.0 / 3.0) - 1.0)
            )
        )
        h_a = nusselt_a * props["conductivity_w_mk"] / hydraulic_diameter
        j_colburn = 0.023 * reynolds**-0.2
        h_b = (
            j_colburn
            * (mass_flow / free_area)
            * props["heat_capacity_j_kgk"]
            / props["prandtl"] ** (2.0 / 3.0)
        )
        eta_a = fin_efficiency(h_a, conductivity, fin["thickness_mm"] / 1000.0, fin_length)
        eta_b = fin_efficiency(h_b, conductivity, fin["thickness_mm"] / 1000.0, fin_length)
        ua_a = h_a * (base_area + eta_a * (effective_area - base_area))
        ua_b = h_b * (base_area + eta_b * (effective_area - base_area))
        dynamic_pressure = 0.5 * props["density_kg_m3"] * velocity**2
        pressure_a = (darcy_a * depth_m / hydraulic_diameter + 1.2) * dynamic_pressure
        darcy_b = 0.3164 / reynolds**0.25
        pressure_b = (darcy_b * depth_m / hydraulic_diameter + 1.0) * dynamic_pressure
        rows.append(
            {
                "air_mass_flow_kg_s_per_head": mass_flow,
                "mean_channel_velocity_m_s": velocity,
                "reynolds_number": reynolds,
                "method_a": {
                    "correlation": "Gnielinski_plus_Darcy_Weisbach",
                    "h_w_m2k": h_a,
                    "fin_efficiency": eta_a,
                    "ua_w_k": ua_a,
                    "pressure_drop_pa": pressure_a,
                },
                "method_b": {
                    "correlation": "Colburn_j_plus_Blasius",
                    "h_w_m2k": h_b,
                    "fin_efficiency": eta_b,
                    "ua_w_k": ua_b,
                    "pressure_drop_pa": pressure_b,
                },
                "relative_ua_difference": abs(ua_a - ua_b) / max(ua_a, ua_b),
                "relative_pressure_drop_difference": abs(pressure_a - pressure_b) / max(pressure_a, pressure_b),
            }
        )

    continuous_row = rows[-2]
    burst_row = rows[-1]

    def temperature(method: str, row: dict, load: dict, initial_c: float | None = None) -> dict:
        ua = row[method]["ua_w_k"]
        ambient = load["ambient_air_c"]
        steady = ambient + load["head_heat_per_cylinder_w"] / ua
        result = {"steady_metal_temperature_c": steady, "ua_w_k": ua}
        if initial_c is not None:
            duration = load["duration_s"]
            capacity = cooling["head_lumped_mass_kg"] * cooling["head_heat_capacity_j_kgk"]
            transient = steady + (initial_c - steady) * math.exp(-ua * duration / capacity)
            result["temperature_after_duration_c"] = transient
            result["duration_s"] = duration
        return result

    thermal = {}
    for method in ("method_a", "method_b"):
        continuous = temperature(method, continuous_row, contract["load_cases"]["continuous_1100_ps"])
        burst = temperature(
            method,
            burst_row,
            contract["load_cases"]["burst_1600_hp"],
            initial_c=continuous["steady_metal_temperature_c"],
        )
        thermal[method] = {
            "continuous": continuous,
            "burst": burst,
            "continuous_screen_passed": continuous["steady_metal_temperature_c"] <= cooling["maximum_continuous_chamber_bridge_c"],
            "burst_screen_passed": burst["temperature_after_duration_c"] <= cooling["maximum_burst_chamber_bridge_c"],
        }

    total_mass_continuous = continuous_row["air_mass_flow_kg_s_per_head"] * contract["program"]["cylinder_count"]
    total_mass_burst = burst_row["air_mass_flow_kg_s_per_head"] * contract["program"]["cylinder_count"]
    blower = {
        "continuous_air_mass_flow_kg_s": total_mass_continuous,
        "burst_air_mass_flow_kg_s": total_mass_burst,
        "continuous_shaft_power_kw": (
            total_mass_continuous
            / props["density_kg_m3"]
            * cooling["blower_total_pressure_pa"]
            / cooling["blower_efficiency"]
            / 1000.0
        ),
        "burst_shaft_power_kw": (
            total_mass_burst
            / props["density_kg_m3"]
            * cooling["blower_total_pressure_pa"]
            / cooling["blower_efficiency"]
            / 1000.0
        ),
        "pressure_available_pa": cooling["blower_total_pressure_pa"],
        "continuous_pressure_screen_passed": all(
            continuous_row[method]["pressure_drop_pa"] <= cooling["blower_total_pressure_pa"]
            for method in ("method_a", "method_b")
        ),
        "burst_pressure_screen_passed": all(
            burst_row[method]["pressure_drop_pa"] <= cooling["blower_total_pressure_pa"]
            for method in ("method_a", "method_b")
        ),
    }
    criteria = contract["cross_verification"]["external_cooling"]
    return {
        "classification": "two_independent_forced_convection_correlations_before_3d_FVM_LBM_cross_check",
        "air_properties": props,
        "effective_cooling_area_m2_per_head": effective_area,
        "free_flow_area_m2_per_head": free_area,
        "hydraulic_diameter_m": hydraulic_diameter,
        "rows": rows,
        "selected_setpoints": {
            "continuous_air_mass_flow_kg_s_per_head": continuous_row["air_mass_flow_kg_s_per_head"],
            "burst_air_mass_flow_kg_s_per_head": burst_row["air_mass_flow_kg_s_per_head"],
        },
        "thermal_screen": thermal,
        "blower_screen": blower,
        "reduced_method_cross_check_passed": all(
            row["relative_ua_difference"] <= criteria["maximum_total_heat_rejection_difference_fraction"]
            and row["relative_pressure_drop_difference"] <= criteria["maximum_pressure_drop_difference_fraction"]
            for row in rows
        ),
        "openfoam_3d_executed": False,
        "fluidx3d_3d_executed": False,
        "full_3d_cross_validation_complete": False,
    }


def stress_screen(contract: dict, cycle: dict, cooling: dict) -> dict:
    pressure_mpa = cycle["conservative_pressure_load_mpa"]
    radius_mm = contract["program"]["bore_mm"] / 2.0
    ligament_mm = 10.5
    hot_yield_mpa = 216.0
    hot_temperature_c = max(
        cooling["thermal_screen"][method]["burst"]["temperature_after_duration_c"]
        for method in ("method_a", "method_b")
    )
    membrane = pressure_mpa * radius_mm / (2.0 * ligament_mm)
    pressure_a = 1.60 * membrane
    pressure_b = 0.22 * pressure_mpa * (radius_mm / ligament_mm) ** 2
    thermal_a = 52.0 * hot_temperature_c / 260.0
    thermal_b = 49.0 * hot_temperature_c / 260.0
    residual = 30.0
    combined_a = math.sqrt(pressure_a**2 + thermal_a**2 + residual**2)
    combined_b = math.sqrt(pressure_b**2 + thermal_b**2 + residual**2)
    difference = abs(combined_a - combined_b) / max(combined_a, combined_b)
    criterion = contract["cross_verification"]["solid_thermal_stress"]["maximum_p95_von_mises_difference_fraction"]
    return {
        "classification": "two_analytical_hotspot_screens_not_CalculiX_Elmer_FEA_or_TMF_validation",
        "conservative_pressure_load_mpa": pressure_mpa,
        "screening_hot_temperature_c": hot_temperature_c,
        "screening_hot_yield_mpa": hot_yield_mpa,
        "method_a": {
            "id": "spherical_membrane_with_stress_concentration",
            "combined_stress_mpa": combined_a,
            "hot_yield_margin": hot_yield_mpa / combined_a,
        },
        "method_b": {
            "id": "clamped_circular_plate_energy_screen",
            "combined_stress_mpa": combined_b,
            "hot_yield_margin": hot_yield_mpa / combined_b,
        },
        "relative_combined_stress_difference": difference,
        "analytical_cross_check_passed": difference <= criterion,
        "minimum_hot_yield_margin_passed": min(hot_yield_mpa / combined_a, hot_yield_mpa / combined_b) >= contract["acceptance"]["minimum_hot_yield_margin"],
        "calculix_executed": False,
        "elmer_executed": False,
        "nonlinear_contact_creep_and_tmf_included": False,
    }


def valvetrain_screen(contract: dict) -> dict:
    rpm = contract["program"]["qualifying_burst"]["speed_rpm"]
    spring = contract["materials"]["spring"]
    rows = []
    assumptions = {
        "intake": {"event_duration_crank_deg": 260.0, "effective_mass_kg": 0.090},
        "exhaust": {"event_duration_crank_deg": 250.0, "effective_mass_kg": 0.095},
    }
    for kind in ("intake", "exhaust"):
        valve = contract["cad"]["valves"][kind]
        event_time = assumptions[kind]["event_duration_crank_deg"] / 360.0 * 60.0 / rpm
        acceleration = 2.0 * math.pi**2 * (valve["maximum_lift_mm"] / 1000.0) / event_time**2
        inertia = acceleration * assumptions[kind]["effective_mass_kg"]
        spring_nose = spring["seat_force_n"] + spring["combined_rate_n_mm"] * valve["maximum_lift_mm"]
        required = 1.25 * inertia
        rows.append(
            {
                "kind": kind,
                "maximum_lift_mm": valve["maximum_lift_mm"],
                "effective_mass_kg": assumptions[kind]["effective_mass_kg"],
                "maximum_cosine_acceleration_m_s2": acceleration,
                "inertia_force_n": inertia,
                "spring_nose_force_n": spring_nose,
                "required_force_with_dynamic_factor_n": required,
                "positive_force_margin_n": spring_nose - required,
                "screen_passed": spring_nose >= required,
            }
        )
    return {
        "classification": "cosine_lift_dynamic_screen_not_spintron_or_cam_contact_validation",
        "speed_rpm": rpm,
        "spring": spring,
        "valves": rows,
        "all_force_screens_passed": all(row["screen_passed"] for row in rows),
        "spring_surge_spintron_and_fatigue_validated": False,
    }


def dataset_plan(contract: dict) -> dict:
    cases = []
    case_id = 0
    for scale in contract["source_geometry"]["scale_sensitivity"]:
        for mass_flow in contract["cooling_design"]["air_mass_flow_points_kg_s_per_head"]:
            for lift_mm in (1.0, 3.0, 5.0, 7.0, 9.0, 10.5):
                for rpm in (5000, 7800, 9000):
                    case_id += 1
                    cases.append(
                        {
                            "case_id": f"F34-DOE-{case_id:03d}",
                            "scale_factor": scale,
                            "air_mass_flow_kg_s_per_head": mass_flow,
                            "valve_lift_mm": lift_mm,
                            "rpm": rpm,
                            "classical_solution_available": False,
                        }
                    )
    minimum = contract["toolchain"]["physicsnemo"]["minimum_converged_classical_cases_before_training"]
    return {
        "schema_version": "1.0.0",
        "phase": "F34",
        "status": "doe_defined_classical_solutions_pending",
        "case_count": len(cases),
        "minimum_before_training": minimum,
        "cases": cases,
        "converged_case_count": 0,
        "training_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--geometry-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--doe-output", type=Path)
    args = parser.parse_args()

    contract = load_json(args.contract)
    geometry = load_json(args.geometry_report)
    observed = verify_contract(contract, ROOT)
    clearances = geometry_clearances(contract, geometry)
    cycle = cycle_cross_check(contract, ROOT)
    cooling = cooling_cross_check(contract)
    stress = stress_screen(contract, cycle, cooling)
    valvetrain = valvetrain_screen(contract)
    doe = dataset_plan(contract)
    if args.doe_output:
        write_json(args.doe_output, doe)

    preliminary_checks = {
        "geometry_clearances": clearances["clearance_targets_passed"],
        "geometry_surface_area": clearances["surface_area_target_passed"],
        "cycle_power_cross_check": cycle["power_cross_check_passed"],
        "cycle_peak_pressure_cross_check": cycle["peak_pressure_cross_check_passed"],
        "cooling_reduced_cross_check": cooling["reduced_method_cross_check_passed"],
        "cooling_continuous": all(
            cooling["thermal_screen"][method]["continuous_screen_passed"]
            for method in ("method_a", "method_b")
        ),
        "cooling_burst": all(
            cooling["thermal_screen"][method]["burst_screen_passed"]
            for method in ("method_a", "method_b")
        ),
        "blower_pressure": (
            cooling["blower_screen"]["continuous_pressure_screen_passed"]
            and cooling["blower_screen"]["burst_pressure_screen_passed"]
        ),
        "stress_analytical_cross_check": stress["analytical_cross_check_passed"],
        "stress_hot_yield_margin": stress["minimum_hot_yield_margin_passed"],
        "valvetrain_force": valvetrain["all_force_screens_passed"],
    }
    report = {
        "schema_version": "1.0.0",
        "phase": "F34",
        "status": "scan_bounded_design_preliminary_screens_complete_high_fidelity_cross_validation_pending",
        "contract_sha256": sha256(args.contract),
        "geometry_report_sha256": sha256(args.geometry_report),
        "upstream_sha256": observed,
        "source_geometry": contract["source_geometry"],
        "geometry": clearances,
        "material_selection": {
            "selected_virtual_candidate": contract["materials"]["selected_virtual_candidate"],
            "selection_scope": contract["materials"]["selection_scope"],
            "head_candidates": contract["materials"]["head_candidates"],
            "hot_material_card_qualified": False,
        },
        "cycle_cross_verification": cycle,
        "external_cooling": cooling,
        "hot_stress": stress,
        "valvetrain": valvetrain,
        "toolchain": contract["toolchain"],
        "physicsnemo": {
            "dataset_plan_case_count": doe["case_count"],
            "converged_classical_cases": 0,
            "training_authorized": False,
            "training_executed": False,
            "surrogate_available": False,
        },
        "preliminary_checks": preliminary_checks,
        "preliminary_all_passed": all(preliminary_checks.values()),
        "blocking_findings": [
            "Cantera and Wiebe peak cylinder pressures differ beyond the F34 cross-method limit",
            "OpenFOAM and FluidX3D 3D head cases are not yet executed",
            "CalculiX and Elmer 3D thermal-stress cases are not yet executed",
            "scan scale and Porsche 917 head identity are not confirmed",
            "no hot coupons, CT, flow bench, spintron or engine dyno correlation exists",
        ],
        "claims": {
            "step_and_watertight_stl_process_prototype_available": True,
            "engine_release_cad_available": False,
            "metal_print_authorized": False,
            "engine_start_authorized": False,
            "physical_validation_complete": False,
        },
        "release_gates": contract["release_gates"],
    }
    write_json(args.output, report)
    print(json.dumps({"status": report["status"], "preliminary_checks": preliminary_checks}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
