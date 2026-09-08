#!/usr/bin/env python3
"""Carter fixe de ventilateur moteur 993, concept AlSi10Mg F0."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


PART_ID = "993-ENG-FAN-HOUSING-ALSI10MG-F0-0001"

# Données commerciales publiées. Elles bornent le produit, pas ses interfaces.
PUBLISHED_PART_NUMBERS = ["99310666703", "99310666701"]
PUBLISHED_ENVELOPE_MM = [300.0, 300.0, 170.0]
PUBLISHED_FVD_MASS_KG = 1.9
PUBLISHED_PORSCHE_ROISSY_MASS_KG = 1.86
PUBLISHED_RESELLER_MATERIAL = "aluminium_unspecified_grade_and_process"

# F0 indépendant. Seuls OD et profondeur reprennent l'enveloppe commerciale.
OUTER_DIAMETER_MM = 300.0
DEPTH_MM = 170.0
SHELL_THICKNESS_MM = 3.0
SYNTHETIC_THROAT_DIAMETER_MM = 252.0
FRONT_FLANGE_THICKNESS_MM = 4.0
SYNTHETIC_HUB_OUTER_DIAMETER_MM = 90.0
SYNTHETIC_HUB_BORE_DIAMETER_MM = 70.0
SYNTHETIC_HUB_DEPTH_MM = 20.0
SPOKE_COUNT = 6
SPOKE_RADIAL_LENGTH_MM = 81.0
SPOKE_WIDTH_MM = 12.0
SPOKE_THICKNESS_MM = 12.0
SYNTHETIC_MOUNT_BORE_DIAMETER_MM = 6.6
SYNTHETIC_MOUNT_RADIUS_MM = 136.0

# Comparaison AlSi10Mg générique, pas carte admissible de carter chaud.
DENSITY_KG_M3 = 2670.0
ELASTIC_MODULUS_PA = 70.0e9
COMPARISON_YIELD_STRENGTH_PA = 245.0e6
THERMAL_EXPANSION_PER_K = 21.0e-6
SPECIFIC_HEAT_J_KG_K = 900.0
PUBLISHED_PROCESS_MINIMUM_WALL_MM = 0.4

# Cas de régression synthétiques, sans autorité véhicule.
SYNTHETIC_AIRFLOW_M3_S = 1.25
SYNTHETIC_HUB_DIAMETER_MM = 90.0
AIR_DENSITY_KG_M3 = 1.05
SYNTHETIC_FLOW_LOSS_K = 0.80
MAXIMUM_SYNTHETIC_PRESSURE_LOSS_PA = 500.0
SYNTHETIC_RADIAL_LOAD_N = 2000.0
SPOKE_EFFECTIVE_LENGTH_MM = 81.0
MAXIMUM_STATIC_DEFLECTION_MM = 0.50
SYNTHETIC_FAN_SPEED_RPM = 6000.0
SYNTHETIC_BLADE_COUNT = 11
MINIMUM_MODAL_SEPARATION_RATIO = 0.20
OPERATING_HOUSING_TEMPERATURE_C = 150.0
REFERENCE_TEMPERATURE_C = 20.0
MINIMUM_SCREEN_RATIO = 1.5


def engineering_screen(cad_volume_mm3: float | None = None) -> dict[str, object]:
    throat_m = SYNTHETIC_THROAT_DIAMETER_MM / 1000.0
    hub_m = SYNTHETIC_HUB_DIAMETER_MM / 1000.0
    flow_area_m2 = math.pi / 4.0 * (throat_m**2 - hub_m**2)
    mean_velocity_m_s = SYNTHETIC_AIRFLOW_M3_S / flow_area_m2
    dynamic_pressure_pa = 0.5 * AIR_DENSITY_KG_M3 * mean_velocity_m_s**2
    pressure_loss_pa = SYNTHETIC_FLOW_LOSS_K * dynamic_pressure_pa
    air_power_w = pressure_loss_pa * SYNTHETIC_AIRFLOW_M3_S
    flow_loss_ratio = MAXIMUM_SYNTHETIC_PRESSURE_LOSS_PA / pressure_loss_pa
    flow_screen_pass = flow_loss_ratio >= 1.0

    per_spoke_load_n = SYNTHETIC_RADIAL_LOAD_N / SPOKE_COUNT
    second_moment_mm4 = SPOKE_WIDTH_MM * SPOKE_THICKNESS_MM**3 / 12.0
    spoke_stress_mpa = (
        per_spoke_load_n
        * SPOKE_EFFECTIVE_LENGTH_MM
        * (SPOKE_THICKNESS_MM / 2.0)
        / second_moment_mm4
    )
    spoke_deflection_mm = (
        per_spoke_load_n
        * SPOKE_EFFECTIVE_LENGTH_MM**3
        / (3.0 * (ELASTIC_MODULUS_PA / 1.0e6) * second_moment_mm4)
    )
    spoke_yield_ratio = COMPARISON_YIELD_STRENGTH_PA / 1.0e6 / spoke_stress_mpa
    static_screen_pass = (
        spoke_yield_ratio >= MINIMUM_SCREEN_RATIO
        and spoke_deflection_mm <= MAXIMUM_STATIC_DEFLECTION_MM
    )

    area_m2 = SPOKE_WIDTH_MM * SPOKE_THICKNESS_MM / 1.0e6
    second_moment_m4 = second_moment_mm4 / 1.0e12
    length_m = SPOKE_EFFECTIVE_LENGTH_MM / 1000.0
    first_spoke_mode_hz = (
        1.875104068711961**2
        / (2.0 * math.pi)
        * math.sqrt(
            ELASTIC_MODULUS_PA
            * second_moment_m4
            / (DENSITY_KG_M3 * area_m2 * length_m**4)
        )
    )
    blade_pass_frequency_hz = (
        SYNTHETIC_FAN_SPEED_RPM / 60.0 * SYNTHETIC_BLADE_COUNT
    )
    modal_separation_ratio = abs(first_spoke_mode_hz - blade_pass_frequency_hz) / blade_pass_frequency_hz
    modal_screen_pass = modal_separation_ratio >= MINIMUM_MODAL_SEPARATION_RATIO

    delta_temperature_k = OPERATING_HOUSING_TEMPERATURE_C - REFERENCE_TEMPERATURE_C
    free_diametral_growth_mm = (
        THERMAL_EXPANSION_PER_K * SYNTHETIC_THROAT_DIAMETER_MM * delta_temperature_k
    )
    fully_constrained_thermal_stress_pa = (
        ELASTIC_MODULUS_PA * THERMAL_EXPANSION_PER_K * delta_temperature_k
    )
    thermal_yield_ratio = COMPARISON_YIELD_STRENGTH_PA / fully_constrained_thermal_stress_pa
    thermal_screen_pass = thermal_yield_ratio >= MINIMUM_SCREEN_RATIO

    cad_mass_kg = (
        cad_volume_mm3 / 1.0e9 * DENSITY_KG_M3
        if cad_volume_mm3 is not None
        else None
    )
    billet_box_volume_mm3 = OUTER_DIAMETER_MM**2 * DEPTH_MM
    billet_box_mass_kg = billet_box_volume_mm3 / 1.0e9 * DENSITY_KG_M3
    lumped_heat_capacity_j_k = (
        cad_mass_kg * SPECIFIC_HEAT_J_KG_K if cad_mass_kg is not None else None
    )
    mass_delta_to_roissy_percent = (
        (cad_mass_kg - PUBLISHED_PORSCHE_ROISSY_MASS_KG)
        / PUBLISHED_PORSCHE_ROISSY_MASS_KG
        * 100.0
        if cad_mass_kg is not None
        else None
    )

    preliminary_screen_pass = (
        flow_screen_pass
        and static_screen_pass
        and modal_screen_pass
        and thermal_screen_pass
    )

    return {
        "schema_version": "1.0.0",
        "part_id": PART_ID,
        "status": "f0_clean_sheet_stationary_fan_housing_analytical_screen_failed",
        "geometry_authority": {
            "published": {
                "part_numbers": PUBLISHED_PART_NUMBERS,
                "fvd_commercial_envelope_mm": PUBLISHED_ENVELOPE_MM,
                "fvd_commercial_mass_kg": PUBLISHED_FVD_MASS_KG,
                "porsche_roissy_commercial_mass_kg": PUBLISHED_PORSCHE_ROISSY_MASS_KG,
                "reseller_material": PUBLISHED_RESELLER_MATERIAL,
            },
            "hypotheses": [
                "300 mm F0 outer diameter and 170 mm depth reuse only the published bounding envelope",
                "252 mm throat, 3 mm shell and 4 mm front flange",
                "90/70 mm annular alternator hub and six 81 x 12 x 12 mm radial spokes",
                "six synthetic 6.6 mm mounting bores on a 136 mm radius",
                "no measured fan tip, alternator, belt, shroud, tinware, vane, seal or engine interface",
            ],
            "not_claimed": "The FVD dimensions are a commercial envelope and the reseller aluminium label has no grade/process certificate; neither defines this clean-sheet surface or fit.",
        },
        "synthetic_cases": {
            "airflow_m3_s": SYNTHETIC_AIRFLOW_M3_S,
            "air_density_kg_m3": AIR_DENSITY_KG_M3,
            "flow_loss_k": SYNTHETIC_FLOW_LOSS_K,
            "maximum_pressure_loss_pa": MAXIMUM_SYNTHETIC_PRESSURE_LOSS_PA,
            "radial_load_n": SYNTHETIC_RADIAL_LOAD_N,
            "fan_speed_rpm": SYNTHETIC_FAN_SPEED_RPM,
            "blade_count": SYNTHETIC_BLADE_COUNT,
            "operating_housing_temperature_c": OPERATING_HOUSING_TEMPERATURE_C,
            "minimum_screen_ratio": MINIMUM_SCREEN_RATIO,
            "authority": "regression inputs only; no measured 993 airflow map, pressure field, fan diameter, blade count, speed, belt load, thermal field, modal boundary or duty",
        },
        "material_screen": {
            "candidate": "EOS Aluminium AlSi10Mg LPBF T6 comparison",
            "oem_replacement_material_evidence": PUBLISHED_RESELLER_MATERIAL,
            "density_kg_m3": DENSITY_KG_M3,
            "elastic_modulus_pa": ELASTIC_MODULUS_PA,
            "comparison_yield_strength_pa": COMPARISON_YIELD_STRENGTH_PA,
            "thermal_expansion_per_k": THERMAL_EXPANSION_PER_K,
            "specific_heat_j_kg_k": SPECIFIC_HEAT_J_KG_K,
            "published_process_minimum_wall_mm": PUBLISHED_PROCESS_MINIMUM_WALL_MM,
            "scope": "generic ambient comparison only; no hot fatigue, casting-equivalence, porosity, belt-load, corrosion or fan-containment allowable",
        },
        "results": {
            "cad_volume_mm3": cad_volume_mm3,
            "cad_mass_g": cad_mass_kg * 1000.0 if cad_mass_kg is not None else None,
            "published_mass_range_kg": [PUBLISHED_PORSCHE_ROISSY_MASS_KG, PUBLISHED_FVD_MASS_KG],
            "mass_delta_to_roissy_percent": mass_delta_to_roissy_percent,
            "billet_box_mass_g": billet_box_mass_kg * 1000.0,
            "billet_box_to_cad_mass_ratio": billet_box_mass_kg / cad_mass_kg if cad_mass_kg else None,
            "lumped_heat_capacity_j_k": lumped_heat_capacity_j_k,
            "annular_flow_area_m2": flow_area_m2,
            "mean_air_velocity_m_s": mean_velocity_m_s,
            "dynamic_pressure_pa": dynamic_pressure_pa,
            "synthetic_pressure_loss_pa": pressure_loss_pa,
            "air_power_w": air_power_w,
            "pressure_loss_allowance_ratio": flow_loss_ratio,
            "per_spoke_load_n": per_spoke_load_n,
            "spoke_second_moment_mm4": second_moment_mm4,
            "spoke_bending_stress_mpa": spoke_stress_mpa,
            "ambient_yield_to_spoke_stress_ratio": spoke_yield_ratio,
            "spoke_tip_deflection_mm": spoke_deflection_mm,
            "first_spoke_mode_hz": first_spoke_mode_hz,
            "synthetic_blade_pass_frequency_hz": blade_pass_frequency_hz,
            "modal_separation_ratio": modal_separation_ratio,
            "free_throat_diametral_growth_mm": free_diametral_growth_mm,
            "fully_constrained_thermal_stress_mpa": fully_constrained_thermal_stress_pa / 1.0e6,
            "ambient_yield_to_constrained_thermal_ratio": thermal_yield_ratio,
            "flow_screen_pass": flow_screen_pass,
            "static_screen_pass": static_screen_pass,
            "modal_screen_pass": modal_screen_pass,
            "thermal_screen_pass": thermal_screen_pass,
            "preliminary_screen_pass": preliminary_screen_pass,
            "fatigue_containment_and_cooling_status": "not_computable_without_measured_interfaces_loads_air_map_hot_material_and_duty",
        },
        "equations": {
            "annular_flow": "A=pi*(D_throat^2-D_hub^2)/4; v=Q/A",
            "minor_loss": "delta_p=K*rho*v^2/2; P_air=delta_p*Q",
            "spoke_bending": "I=b*t^3/12; sigma=F*L*(t/2)/I; delta=F*L^3/(3*E*I)",
            "cantilever_mode": "f1=1.875104^2/(2*pi)*sqrt(E*I/(rho*A*L^4))",
            "blade_pass": "f_bpf=N_blades*rpm/60",
            "thermal_growth": "delta_D=alpha*D*delta_T",
            "constrained_thermal": "sigma=E*alpha*delta_T",
            "mass_and_heat_capacity": "m=rho*V; C=m*cp",
        },
        "dfam_screen": {
            "additive_value": "low-volume annular housing consolidating thin shell, front flange, alternator hub and six radial supports with little billet removal",
            "stationary_part": True,
            "rotating_impeller_included": False,
            "open_air_path": True,
            "trapped_powder_volume": False,
            "integrated_spoke_count": SPOKE_COUNT,
            "nominal_shell_mm": SHELL_THICKNESS_MM,
            "shell_to_process_minimum_ratio": SHELL_THICKNESS_MM / PUBLISHED_PROCESS_MINIMUM_WALL_MM,
            "build_envelope_mm": PUBLISHED_ENVELOPE_MM,
            "orientation_selected": False,
            "support_strategy_defined": False,
            "all_fan_alternator_mounting_and_sealing_interfaces_require_machining": True,
            "process_comparison_required": [
                "qualified magnesium or aluminium production casting",
                "fabricated and machined aluminium assembly",
                "large-billet CNC aluminium housing",
                "LPBF AlSi10Mg integrated housing",
            ],
        },
        "interpretation": {
            "result": "synthetic airflow, static and modal algebra pass; fully constrained thermal screen fails",
            "mass": "similarity to the retailer mass range is not validation because the internal F0 geometry is synthetic",
            "airflow": "an annular area and lumped loss coefficient cannot predict fan operating point or cylinder-head distribution",
            "structure": "six isolated cantilever spokes do not model the cast shell, alternator bearings, belt, bolts or fan containment",
            "physicsnemo": "deferred until correlated CFD, CHT, structural and modal datasets exist",
            "simready": "deferred until measured fan, hub, alternator, engine, tinware and sealed air-domain interfaces exist",
        },
        "release_blockers": [
            "No measured housing, fan tip, alternator, hub, bearing, belt, tinware, shroud or engine interface.",
            "Only the 300 x 300 x 170 mm commercial envelope and two retailer masses are published.",
            "The 252 mm throat, shell, flange, hub, six spokes and bolt pattern are entirely synthetic.",
            "The aluminium material statement has no alloy, process, heat treatment or certificate.",
            "No evidence that the production housing uses AlSi10Mg or LPBF.",
            "Airflow, density, loss coefficient and pressure allowance are arbitrary regression inputs.",
            "No measured fan curve, system curve, cooling distribution, leakage or hot-cylinder margin.",
            "Radial load, load sharing, blade count, speed and boundary conditions are synthetic.",
            "The beam and modal equations omit ring coupling, joint compliance, gyroscopic excitation and harmonics.",
            "No fan fragment or overspeed containment analysis is present.",
            "The fully constrained thermal screen fails and no actual temperature field is known.",
            "No hot LPBF AlSi10Mg fatigue, creep, porosity, corrosion or surface allowables.",
            "No CFD, CHT, converged FEA, modal survey, fatigue or measured correlation.",
            "No qualified build orientation, supports, stress relief, T6, HIP, distortion compensation or machining route.",
            "No CT, FPI, metallurgy, dimensional inspection, balance-clearance, airflow, vibration or endurance test.",
            "No professional engine review, approved validation plan, dyno authorization or vehicle release.",
        ],
        "manufacturing_authorized": False,
        "engine_operation_authorized": False,
        "release_authorized": False,
    }


def build_geometry():
    from build123d import Align, Box, Cylinder, Pos, Rot

    centered_min = (Align.CENTER, Align.CENTER, Align.MIN)
    outer = Cylinder(OUTER_DIAMETER_MM / 2.0, DEPTH_MM, align=centered_min)
    inner = Pos(0.0, 0.0, -1.0) * Cylinder(
        OUTER_DIAMETER_MM / 2.0 - SHELL_THICKNESS_MM,
        DEPTH_MM + 2.0,
        align=centered_min,
    )
    body = outer - inner

    flange_outer = Cylinder(
        OUTER_DIAMETER_MM / 2.0 - SHELL_THICKNESS_MM,
        FRONT_FLANGE_THICKNESS_MM,
        align=centered_min,
    )
    flange_inner = Pos(0.0, 0.0, -1.0) * Cylinder(
        SYNTHETIC_THROAT_DIAMETER_MM / 2.0,
        FRONT_FLANGE_THICKNESS_MM + 2.0,
        align=centered_min,
    )
    body = body + (flange_outer - flange_inner)

    hub_outer = Cylinder(
        SYNTHETIC_HUB_OUTER_DIAMETER_MM / 2.0,
        SYNTHETIC_HUB_DEPTH_MM,
        align=centered_min,
    )
    hub_inner = Pos(0.0, 0.0, -1.0) * Cylinder(
        SYNTHETIC_HUB_BORE_DIAMETER_MM / 2.0,
        SYNTHETIC_HUB_DEPTH_MM + 2.0,
        align=centered_min,
    )
    body = body + (hub_outer - hub_inner)

    spoke_center_radius_mm = (
        SYNTHETIC_HUB_OUTER_DIAMETER_MM / 2.0 + SPOKE_RADIAL_LENGTH_MM / 2.0
    )
    for index in range(SPOKE_COUNT):
        angle_deg = index * 360.0 / SPOKE_COUNT
        spoke = (
            Rot(0.0, 0.0, angle_deg)
            * Pos(spoke_center_radius_mm, 0.0, 0.0)
            * Box(
                SPOKE_RADIAL_LENGTH_MM + 2.0,
                SPOKE_WIDTH_MM,
                SPOKE_THICKNESS_MM,
                align=centered_min,
            )
        )
        body = body + spoke

    for index in range(SPOKE_COUNT):
        angle_rad = math.radians(index * 360.0 / SPOKE_COUNT + 30.0)
        x_mm = SYNTHETIC_MOUNT_RADIUS_MM * math.cos(angle_rad)
        y_mm = SYNTHETIC_MOUNT_RADIUS_MM * math.sin(angle_rad)
        bore = Pos(x_mm, y_mm, -1.0) * Cylinder(
            SYNTHETIC_MOUNT_BORE_DIAMETER_MM / 2.0,
            FRONT_FLANGE_THICKNESS_MM + 2.0,
            align=centered_min,
        )
        body = body - bore
    return body


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    cad_volume_mm3 = None
    envelope = None
    if args.out:
        from build123d import export_step, import_step

        shape = build_geometry()
        if not shape.is_valid or len(shape.solids()) != 1:
            raise SystemExit("Le carter F0 doit être un solide BREP unique valide.")
        bbox = shape.bounding_box()
        envelope = [bbox.size.X, bbox.size.Y, bbox.size.Z]
        args.out.parent.mkdir(parents=True, exist_ok=True)
        export_step(shape, str(args.out))
        roundtrip = import_step(str(args.out))
        if not roundtrip.is_valid or len(roundtrip.solids()) != 1:
            raise SystemExit("Le STEP relu ne conserve pas le solide valide.")
        if abs(roundtrip.volume - shape.volume) > 0.05:
            raise SystemExit("Le STEP relu ne reproduit pas le volume OCCT attendu.")
        cad_volume_mm3 = roundtrip.volume

    report = engineering_screen(cad_volume_mm3)
    if args.out and envelope is not None:
        report["step_roundtrip"] = {
            "status": "passed",
            "valid_brep": True,
            "solid_count": 1,
            "semantic_solids": ["clean_sheet_stationary_fan_housing_f0"],
            "volume_mm3": cad_volume_mm3,
            "envelope_mm": envelope,
            "open_air_path_count": 1,
            "stationary_spoke_count": SPOKE_COUNT,
            "mount_bore_count": SPOKE_COUNT,
            "rotating_impeller_count": 0,
            "maximum_volume_delta_mm3": 0.05,
        }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
