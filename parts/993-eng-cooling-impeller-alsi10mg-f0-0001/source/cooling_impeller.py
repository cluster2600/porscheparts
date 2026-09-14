#!/usr/bin/env python3
"""Turbine de refroidissement moteur 993, concept tournant AlSi10Mg F0."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


PART_ID = "993-ENG-COOLING-IMPELLER-ALSI10MG-F0-0001"

# Faits commerciaux, sans définition d'interface.
PUBLISHED_PART_NUMBER = "96410601531"
PUBLISHED_ENVELOPE_MM = [300.0, 300.0, 150.0]
PUBLISHED_FVD_MASS_KG = 0.94
PUBLISHED_POITIERS_MASS_KG = 0.948
PUBLISHED_RESELLER_MATERIAL = "aluminium_unspecified_grade_and_process"

# F0 indépendant. Tous les paramètres fonctionnels ci-dessous sont synthétiques.
OUTER_DIAMETER_MM = 280.0
AXIAL_DEPTH_MM = 30.0
OUTER_RIM_THICKNESS_MM = 3.0
HUB_OUTER_DIAMETER_MM = 80.0
HUB_BORE_DIAMETER_MM = 30.0
BLADE_COUNT = 12
BLADE_RADIAL_LENGTH_MM = 102.0
BLADE_CHORD_MM = 7.0
BLADE_AXIAL_HEIGHT_MM = 20.0
BLADE_Z_MM = 5.0
BLADE_CENTER_RADIUS_MM = 88.5
BLADE_SWEEP_DEG = 10.0

# Comparaison générique AlSi10Mg, pas carte admissible tournante ou chaude.
DENSITY_KG_M3 = 2670.0
ELASTIC_MODULUS_PA = 70.0e9
COMPARISON_YIELD_STRENGTH_PA = 245.0e6
THERMAL_EXPANSION_PER_K = 21.0e-6
SPECIFIC_HEAT_J_KG_K = 900.0
PUBLISHED_PROCESS_MINIMUM_WALL_MM = 0.4

# Cas analytiques synthétiques sans autorité 993.
SYNTHETIC_NOMINAL_SPEED_RPM = 10_000.0
SYNTHETIC_OVERSPEED_FACTOR = 1.20
SYNTHETIC_AIRFLOW_M3_S = 1.01
SYNTHETIC_PRESSURE_RISE_PA = 800.0
SYNTHETIC_AIR_TEMPERATURE_C = 80.0
AIR_GAMMA = 1.4
AIR_GAS_CONSTANT_J_KG_K = 287.05
OPERATING_IMPELLER_TEMPERATURE_C = 150.0
REFERENCE_TEMPERATURE_C = 20.0
MINIMUM_SCREEN_RATIO = 1.5
MINIMUM_MODAL_SEPARATION_RATIO = 0.20
UPSTREAM_HOUSING_PART_ID = "993-ENG-FAN-HOUSING-ALSI10MG-F0-0001"
UPSTREAM_HOUSING_SYNTHETIC_THROAT_MM = 252.0
MINIMUM_SYNTHETIC_RADIAL_CLEARANCE_MM = 2.0


def _angular_speed(speed_rpm: float) -> float:
    return speed_rpm * 2.0 * math.pi / 60.0


def engineering_screen(cad_volume_mm3: float | None = None) -> dict[str, object]:
    outer_radius_m = OUTER_DIAMETER_MM / 2000.0
    hub_radius_m = HUB_OUTER_DIAMETER_MM / 2000.0
    omega = _angular_speed(SYNTHETIC_NOMINAL_SPEED_RPM)
    overspeed_rpm = SYNTHETIC_NOMINAL_SPEED_RPM * SYNTHETIC_OVERSPEED_FACTOR
    overspeed_omega = _angular_speed(overspeed_rpm)

    nominal_tip_speed_m_s = omega * outer_radius_m
    overspeed_tip_speed_m_s = overspeed_omega * outer_radius_m
    speed_of_sound_m_s = math.sqrt(
        AIR_GAMMA * AIR_GAS_CONSTANT_J_KG_K * (SYNTHETIC_AIR_TEMPERATURE_C + 273.15)
    )
    overspeed_tip_mach = overspeed_tip_speed_m_s / speed_of_sound_m_s

    nominal_rim_hoop_stress_pa = DENSITY_KG_M3 * nominal_tip_speed_m_s**2
    overspeed_rim_hoop_stress_pa = DENSITY_KG_M3 * overspeed_tip_speed_m_s**2
    overspeed_yield_ratio = COMPARISON_YIELD_STRENGTH_PA / overspeed_rim_hoop_stress_pa
    overspeed_screen_pass = overspeed_yield_ratio >= MINIMUM_SCREEN_RATIO

    housing_diametral_clearance_mm = (
        UPSTREAM_HOUSING_SYNTHETIC_THROAT_MM - OUTER_DIAMETER_MM
    )
    housing_radial_clearance_mm = housing_diametral_clearance_mm / 2.0
    housing_fit_screen_pass = (
        housing_radial_clearance_mm >= MINIMUM_SYNTHETIC_RADIAL_CLEARANCE_MM
    )

    blade_volume_m3 = (
        BLADE_RADIAL_LENGTH_MM
        * BLADE_CHORD_MM
        * BLADE_AXIAL_HEIGHT_MM
        / 1.0e9
    )
    blade_mass_kg = blade_volume_m3 * DENSITY_KG_M3
    blade_center_radius_m = BLADE_CENTER_RADIUS_MM / 1000.0
    blade_centrifugal_force_n = blade_mass_kg * overspeed_omega**2 * blade_center_radius_m
    blade_root_area_mm2 = BLADE_CHORD_MM * BLADE_AXIAL_HEIGHT_MM
    blade_root_direct_stress_mpa = blade_centrifugal_force_n / blade_root_area_mm2
    blade_root_yield_ratio = (
        COMPARISON_YIELD_STRENGTH_PA / 1.0e6 / blade_root_direct_stress_mpa
    )
    blade_root_screen_pass = blade_root_yield_ratio >= MINIMUM_SCREEN_RATIO

    blade_second_moment_mm4 = (
        BLADE_AXIAL_HEIGHT_MM * BLADE_CHORD_MM**3 / 12.0
    )
    blade_second_moment_m4 = blade_second_moment_mm4 / 1.0e12
    blade_area_m2 = blade_root_area_mm2 / 1.0e6
    blade_length_m = BLADE_RADIAL_LENGTH_MM / 1000.0
    first_blade_mode_hz = (
        1.875104068711961**2
        / (2.0 * math.pi)
        * math.sqrt(
            ELASTIC_MODULUS_PA
            * blade_second_moment_m4
            / (DENSITY_KG_M3 * blade_area_m2 * blade_length_m**4)
        )
    )
    blade_pass_frequency_hz = BLADE_COUNT * SYNTHETIC_NOMINAL_SPEED_RPM / 60.0
    modal_separation_ratio = abs(first_blade_mode_hz - blade_pass_frequency_hz) / blade_pass_frequency_hz
    modal_screen_pass = modal_separation_ratio >= MINIMUM_MODAL_SEPARATION_RATIO

    annular_area_m2 = math.pi / 4.0 * (
        (OUTER_DIAMETER_MM / 1000.0) ** 2
        - (HUB_OUTER_DIAMETER_MM / 1000.0) ** 2
    )
    mean_axial_velocity_m_s = SYNTHETIC_AIRFLOW_M3_S / annular_area_m2
    synthetic_air_power_w = SYNTHETIC_AIRFLOW_M3_S * SYNTHETIC_PRESSURE_RISE_PA
    synthetic_shaft_torque_nm = synthetic_air_power_w / omega

    rim_outer_radius_m = OUTER_DIAMETER_MM / 2000.0
    rim_inner_radius_m = (OUTER_DIAMETER_MM / 2.0 - OUTER_RIM_THICKNESS_MM) / 1000.0
    rim_volume_m3 = math.pi * (rim_outer_radius_m**2 - rim_inner_radius_m**2) * (AXIAL_DEPTH_MM / 1000.0)
    hub_outer_radius_m = HUB_OUTER_DIAMETER_MM / 2000.0
    hub_bore_radius_m = HUB_BORE_DIAMETER_MM / 2000.0
    hub_volume_m3 = math.pi * (hub_outer_radius_m**2 - hub_bore_radius_m**2) * (AXIAL_DEPTH_MM / 1000.0)
    rim_mass_kg = rim_volume_m3 * DENSITY_KG_M3
    hub_mass_kg = hub_volume_m3 * DENSITY_KG_M3
    rim_inertia_kg_m2 = 0.5 * rim_mass_kg * (rim_outer_radius_m**2 + rim_inner_radius_m**2)
    hub_inertia_kg_m2 = 0.5 * hub_mass_kg * (hub_outer_radius_m**2 + hub_bore_radius_m**2)
    blade_inertia_kg_m2 = BLADE_COUNT * blade_mass_kg * (
        blade_center_radius_m**2 + blade_length_m**2 / 12.0
    )
    approximate_polar_inertia_kg_m2 = rim_inertia_kg_m2 + hub_inertia_kg_m2 + blade_inertia_kg_m2
    overspeed_kinetic_energy_j = 0.5 * approximate_polar_inertia_kg_m2 * overspeed_omega**2

    delta_temperature_k = OPERATING_IMPELLER_TEMPERATURE_C - REFERENCE_TEMPERATURE_C
    free_diametral_growth_mm = THERMAL_EXPANSION_PER_K * OUTER_DIAMETER_MM * delta_temperature_k
    fully_constrained_thermal_stress_pa = ELASTIC_MODULUS_PA * THERMAL_EXPANSION_PER_K * delta_temperature_k
    thermal_yield_ratio = COMPARISON_YIELD_STRENGTH_PA / fully_constrained_thermal_stress_pa
    thermal_screen_pass = thermal_yield_ratio >= MINIMUM_SCREEN_RATIO

    cad_mass_kg = cad_volume_mm3 / 1.0e9 * DENSITY_KG_M3 if cad_volume_mm3 is not None else None
    billet_box_volume_mm3 = OUTER_DIAMETER_MM**2 * AXIAL_DEPTH_MM
    billet_box_mass_kg = billet_box_volume_mm3 / 1.0e9 * DENSITY_KG_M3
    mass_delta_to_fvd_percent = (
        (cad_mass_kg - PUBLISHED_FVD_MASS_KG) / PUBLISHED_FVD_MASS_KG * 100.0
        if cad_mass_kg is not None else None
    )

    preliminary_screen_pass = (
        housing_fit_screen_pass
        and overspeed_screen_pass
        and blade_root_screen_pass
        and modal_screen_pass
        and thermal_screen_pass
    )
    return {
        "schema_version": "1.0.0",
        "part_id": PART_ID,
        "status": "f0_clean_sheet_rotating_cooling_impeller_analytical_screen_failed",
        "geometry_authority": {
            "published": {
                "part_number": PUBLISHED_PART_NUMBER,
                "fvd_commercial_envelope_mm": PUBLISHED_ENVELOPE_MM,
                "fvd_commercial_mass_kg": PUBLISHED_FVD_MASS_KG,
                "porsche_poitiers_commercial_mass_kg": PUBLISHED_POITIERS_MASS_KG,
                "reseller_material": PUBLISHED_RESELLER_MATERIAL,
            },
            "hypotheses": [
                "280 mm OD by 30 mm F0 rotating envelope inside the published product envelope",
                "80/30 mm annular hub and 3 mm outer rim",
                "twelve straight swept blades, each 102 x 7 x 20 mm at 10 degrees",
                "no copied Porsche, FVD, Partworks or product-photo surface",
                "no measured shaft, hub, pulley, shim, bearing, housing, blade, balance or tip-clearance interface",
            ],
            "not_claimed": "The 300 x 300 x 150 mm data are a commercial product envelope; the two masses and aluminium label do not define this F0 geometry, alloy, balance or fit.",
        },
        "upstream_f0_integration": {
            "housing_part_id": UPSTREAM_HOUSING_PART_ID,
            "housing_synthetic_throat_mm": UPSTREAM_HOUSING_SYNTHETIC_THROAT_MM,
            "impeller_synthetic_outer_diameter_mm": OUTER_DIAMETER_MM,
            "minimum_synthetic_radial_clearance_mm": MINIMUM_SYNTHETIC_RADIAL_CLEARANCE_MM,
            "authority": "comparison between two synthetic F0 values only; neither dimension is measured or a production interface",
        },
        "synthetic_cases": {
            "nominal_speed_rpm": SYNTHETIC_NOMINAL_SPEED_RPM,
            "overspeed_factor": SYNTHETIC_OVERSPEED_FACTOR,
            "airflow_m3_s": SYNTHETIC_AIRFLOW_M3_S,
            "pressure_rise_pa": SYNTHETIC_PRESSURE_RISE_PA,
            "air_temperature_c": SYNTHETIC_AIR_TEMPERATURE_C,
            "operating_impeller_temperature_c": OPERATING_IMPELLER_TEMPERATURE_C,
            "minimum_screen_ratio": MINIMUM_SCREEN_RATIO,
            "authority": "regression inputs only; no measured 993 speed, pulley ratio, fan map, pressure, temperature, blade count, geometry, imbalance, vibration or duty",
        },
        "material_screen": {
            "candidate": "EOS Aluminium AlSi10Mg LPBF T6 comparison",
            "commercial_material_evidence": PUBLISHED_RESELLER_MATERIAL,
            "density_kg_m3": DENSITY_KG_M3,
            "elastic_modulus_pa": ELASTIC_MODULUS_PA,
            "comparison_yield_strength_pa": COMPARISON_YIELD_STRENGTH_PA,
            "thermal_expansion_per_k": THERMAL_EXPANSION_PER_K,
            "specific_heat_j_kg_k": SPECIFIC_HEAT_J_KG_K,
            "published_process_minimum_wall_mm": PUBLISHED_PROCESS_MINIMUM_WALL_MM,
            "scope": "generic ambient comparison only; no rotating hot-fatigue, HCF, defect, notch, corrosion, balance, overspeed or fragment-containment allowable",
        },
        "results": {
            "cad_volume_mm3": cad_volume_mm3,
            "cad_mass_g": cad_mass_kg * 1000.0 if cad_mass_kg is not None else None,
            "published_mass_range_kg": [PUBLISHED_FVD_MASS_KG, PUBLISHED_POITIERS_MASS_KG],
            "mass_delta_to_fvd_percent": mass_delta_to_fvd_percent,
            "billet_box_mass_g": billet_box_mass_kg * 1000.0,
            "billet_box_to_cad_mass_ratio": billet_box_mass_kg / cad_mass_kg if cad_mass_kg else None,
            "nominal_tip_speed_m_s": nominal_tip_speed_m_s,
            "overspeed_rpm": overspeed_rpm,
            "overspeed_tip_speed_m_s": overspeed_tip_speed_m_s,
            "speed_of_sound_m_s": speed_of_sound_m_s,
            "overspeed_tip_mach": overspeed_tip_mach,
            "housing_diametral_clearance_mm": housing_diametral_clearance_mm,
            "housing_radial_clearance_mm": housing_radial_clearance_mm,
            "nominal_rim_hoop_stress_mpa": nominal_rim_hoop_stress_pa / 1.0e6,
            "overspeed_rim_hoop_stress_mpa": overspeed_rim_hoop_stress_pa / 1.0e6,
            "ambient_yield_to_overspeed_hoop_ratio": overspeed_yield_ratio,
            "single_blade_mass_g": blade_mass_kg * 1000.0,
            "single_blade_overspeed_centrifugal_force_n": blade_centrifugal_force_n,
            "blade_root_direct_stress_mpa": blade_root_direct_stress_mpa,
            "ambient_yield_to_blade_root_ratio": blade_root_yield_ratio,
            "first_blade_mode_hz": first_blade_mode_hz,
            "blade_pass_frequency_hz": blade_pass_frequency_hz,
            "modal_separation_ratio": modal_separation_ratio,
            "annular_flow_area_m2": annular_area_m2,
            "mean_axial_velocity_m_s": mean_axial_velocity_m_s,
            "synthetic_air_power_w": synthetic_air_power_w,
            "synthetic_shaft_torque_nm": synthetic_shaft_torque_nm,
            "approximate_polar_inertia_kg_m2": approximate_polar_inertia_kg_m2,
            "overspeed_kinetic_energy_j": overspeed_kinetic_energy_j,
            "free_outer_diametral_growth_mm": free_diametral_growth_mm,
            "fully_constrained_thermal_stress_mpa": fully_constrained_thermal_stress_pa / 1.0e6,
            "ambient_yield_to_constrained_thermal_ratio": thermal_yield_ratio,
            "overspeed_screen_pass": overspeed_screen_pass,
            "housing_fit_screen_pass": housing_fit_screen_pass,
            "blade_root_screen_pass": blade_root_screen_pass,
            "modal_screen_pass": modal_screen_pass,
            "thermal_screen_pass": thermal_screen_pass,
            "preliminary_screen_pass": preliminary_screen_pass,
            "hcf_balance_aeroacoustics_and_containment_status": "not_computable_without_measured_geometry_material_defects_balance_fan_map_boundaries_and_duty",
        },
        "equations": {
            "angular_speed_and_tip": "omega=2*pi*rpm/60; v_tip=omega*r",
            "housing_clearance": "c_radial=(D_housing_throat-D_impeller)/2",
            "thin_rim_hoop": "sigma_theta=rho*v_tip^2",
            "blade_centrifugal": "F=m*omega^2*r_c; sigma=F/A_root",
            "cantilever_mode": "f1=1.875104^2/(2*pi)*sqrt(E*I/(rho*A*L^4))",
            "blade_pass": "f_bpf=N_blades*rpm/60",
            "annular_flow_and_power": "A=pi*(D^2-d^2)/4; v=Q/A; P=Q*delta_p; torque=P/omega",
            "polar_energy": "E_k=I*omega^2/2 with ring, hub and blade centroid approximations",
            "thermal": "delta_D=alpha*D*delta_T; sigma=E*alpha*delta_T",
            "mass": "m=rho*V",
        },
        "dfam_screen": {
            "additive_value": "one-piece low-volume impeller consolidating hub, twelve swept blades and outer rim; topology and blade law could later be optimized from correlated CFD/FEA",
            "rotating_part": True,
            "blade_count": BLADE_COUNT,
            "trapped_powder_volume": False,
            "minimum_feature_mm": min(OUTER_RIM_THICKNESS_MM, BLADE_CHORD_MM),
            "minimum_feature_to_process_minimum_ratio": min(OUTER_RIM_THICKNESS_MM, BLADE_CHORD_MM) / PUBLISHED_PROCESS_MINIMUM_WALL_MM,
            "orientation_selected": False,
            "support_strategy_defined": False,
            "dynamic_balance_defined": False,
            "all_shaft_hub_pulley_and_tip_interfaces_require_measurement_and_machining": True,
            "process_comparison_required": [
                "qualified original casting",
                "five-axis CNC aluminium billet",
                "hybrid machined hub plus qualified composite blades",
                "LPBF AlSi10Mg one-piece impeller",
            ],
        },
        "interpretation": {
            "result": "thin-rim, direct blade-root and modal algebra pass; upstream housing fit and constrained thermal screens fail",
            "mass": "proximity to 0.94/0.948 kg is a scalar design check only, not shape or balance validation",
            "rotation": "thin-ring and direct-stress equations omit blade-root notch, bending, residual stress, defects and HCF",
            "cooling": "flow and pressure are targets only because no blade angles, fan curve or housing domain are measured",
            "containment": "the reported overspeed kinetic energy is a hazard indicator, not a containment proof",
            "integration": "the 280 mm impeller conflicts with the preceding housing F0's 252 mm throat; no synthetic dimension is silently changed",
            "physicsnemo": "deferred until correlated rotating CFD, structural, modal, HCF and balance datasets exist",
            "simready": "deferred until measured housing, fan, hub, alternator, belt, shims and engine interfaces exist",
        },
        "release_blockers": [
            "No measured fan OD, depth, hub, bore, pulley, shim, shaft, bearing, housing or tip clearance.",
            "Only a 300 x 300 x 150 mm product envelope and two retailer masses are published.",
            "The 280 mm OD, 80/30 mm hub, twelve swept blades and outer rim are synthetic.",
            "The preceding housing F0 throat is 252 mm, giving -14 mm radial clearance against this 280 mm impeller F0.",
            "The aluminium statement has no grade, process, heat treatment or certificate.",
            "No evidence that the production impeller uses AlSi10Mg or LPBF.",
            "Nominal speed, overspeed factor, airflow, pressure and temperatures are regression inputs.",
            "The rim equation is thin-ring algebra and the blade equation includes direct centrifugal stress only.",
            "No blade-root notch, bending, torsion, residual stress, porosity or anisotropy model.",
            "No actual fan map, efficiency, stall, recirculation, cylinder distribution or aeroacoustics model.",
            "No assembled modal/harmonic, Campbell diagram, bearing or belt excitation analysis.",
            "No imbalance tolerance, correction-plane definition or balancing method.",
            "No foreign-object impact, blade loss, overspeed burst or housing-containment proof.",
            "The fully constrained thermal screen fails and no actual thermal field is known.",
            "No hot HCF/S-N allowables for the exact LPBF route, defects, surface and mean stress.",
            "No qualified orientation, supports, stress relief, T6, HIP, machining or surface route.",
            "No CT, FPI, metallurgy, dimensional, balance, overspeed, vibration, airflow or endurance test.",
            "No professional rotating-equipment review, approved dyno cell plan or vehicle release.",
        ],
        "manufacturing_authorized": False,
        "engine_operation_authorized": False,
        "release_authorized": False,
    }


def build_geometry():
    from build123d import Align, Box, Cylinder, Pos, Rot

    centered_min = (Align.CENTER, Align.CENTER, Align.MIN)
    hub = Cylinder(HUB_OUTER_DIAMETER_MM / 2.0, AXIAL_DEPTH_MM, align=centered_min)
    hub_bore = Pos(0.0, 0.0, -1.0) * Cylinder(
        HUB_BORE_DIAMETER_MM / 2.0, AXIAL_DEPTH_MM + 2.0, align=centered_min
    )
    body = hub - hub_bore

    rim_outer = Cylinder(OUTER_DIAMETER_MM / 2.0, AXIAL_DEPTH_MM, align=centered_min)
    rim_inner = Pos(0.0, 0.0, -1.0) * Cylinder(
        OUTER_DIAMETER_MM / 2.0 - OUTER_RIM_THICKNESS_MM,
        AXIAL_DEPTH_MM + 2.0,
        align=centered_min,
    )
    body = body + (rim_outer - rim_inner)

    for index in range(BLADE_COUNT):
        angle_deg = index * 360.0 / BLADE_COUNT + BLADE_SWEEP_DEG
        blade = (
            Rot(0.0, 0.0, angle_deg)
            * Pos(BLADE_CENTER_RADIUS_MM, 0.0, BLADE_Z_MM)
            * Box(
                BLADE_RADIAL_LENGTH_MM,
                BLADE_CHORD_MM,
                BLADE_AXIAL_HEIGHT_MM,
                align=centered_min,
            )
        )
        body = body + blade
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
            raise SystemExit("La turbine F0 doit être un solide BREP unique valide.")
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
            "semantic_solids": ["clean_sheet_rotating_cooling_impeller_f0"],
            "volume_mm3": cad_volume_mm3,
            "envelope_mm": envelope,
            "hub_bore_count": 1,
            "synthetic_blade_count": BLADE_COUNT,
            "outer_rim_count": 1,
            "maximum_volume_delta_mm3": 0.05,
        }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
