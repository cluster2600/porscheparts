#!/usr/bin/env python3
"""Roue de turbine K16 IN718 F0 : CAO propre et criblages fail-closed."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


PART_ID = "993-ENG-K16-TURBINE-WHEEL-IN718-F0-0001"
COMPANION_PART_ID = "993-ENG-K16-COMPRESSOR-WHEEL-AL2139-F1-0001"

# Donnees de catalogue fournisseur reliees au K16 droit 5316-988-6735.
PUBLISHED_TURBINE_WHEEL_REFERENCE = "5316-120-5000"
PUBLISHED_RIGHT_TURBO_REFERENCE = "5316-988-6735"
PUBLISHED_INDUCER_DIAMETER_MM = 54.96
PUBLISHED_EXDUCER_DIAMETER_MM = 48.97
PUBLISHED_BLADE_COUNT = 12
PUBLISHED_TIP_HEIGHT_MM = 9.4
PUBLISHED_SHAFT_DIAMETER_MM = 8.42

# Topologie F0 independante. Ces nombres ne sont pas des dimensions OEM.
SYNTHETIC_TOTAL_HEIGHT_MM = 20.0
SYNTHETIC_BACKFACE_THICKNESS_MM = 5.8
SYNTHETIC_HUB_ROOT_RADIUS_MM = 12.0
SYNTHETIC_BLADE_INNER_RADIUS_MM = 9.5
SYNTHETIC_BLADE_ROOT_THICKNESS_MM = 2.4
SYNTHETIC_BLADE_TIP_THICKNESS_MM = 0.8
CAD_TAPER_SEGMENT_COUNT = 4
CAD_SEGMENT_OVERLAP_MM = 0.35

# EOS NickelAlloy IN718 API, M 290, 40 um, traite thermiquement.
MATERIAL_DENSITY_KG_M3 = 8150.0
AMBIENT_YIELD_STRENGTH_PA = 865.0e6
AMBIENT_ULTIMATE_STRENGTH_PA = 1236.0e6
AMBIENT_ELONGATION_RATIO = 0.28
PUBLISHED_AVERAGE_DEFECT_FRACTION = 0.0003
PUBLISHED_MINIMUM_WALL_RANGE_MM = [0.3, 0.4]
PUBLISHED_PROCESS_TRL = 9
PUBLISHED_USE_TEMPERATURE_LIMIT_C = 700.0
PUBLISHED_CTE_AT_700C_PER_K = 15.5e-6

# Constantes provisoires : la fiche EOS retenue ne donne pas une carte rotor.
ELASTIC_MODULUS_PA_PROVISIONAL = 200.0e9
POISSON_RATIO_PROVISIONAL = 0.29
SPECIFIC_HEAT_J_KG_K_PROVISIONAL = 435.0

# Point commun au compresseur F1 ; aucune vitesse K16 n'a ete mesuree.
AIR_GAMMA = 1.4
AIR_GAS_CONSTANT_J_KG_K = 287.05
AIR_CP_J_KG_K = 1005.0
AIR_INLET_TEMPERATURE_K = 330.0
AIR_INLET_PRESSURE_PA = 180_000.0
COMPRESSOR_TARGET_TIP_MACH = 0.90
COMPRESSOR_EXDUCER_DIAMETER_MM = 60.5
COMPRESSOR_PRESSURE_RATIO = 1.80
COMPRESSOR_ISENTROPIC_EFFICIENCY = 0.72
ENGINE_DISPLACEMENT_L = 3.6
ENGINE_SPEED_RPM = 5750.0
ENGINE_VOLUMETRIC_EFFICIENCY = 0.95

# Cas chaud synthetique. T3 vient d'un contexte catalogue, pas d'une mesure K16.
TURBINE_INLET_TEMPERATURE_C = 950.0
TURBINE_OUTLET_PRESSURE_PA = 110_000.0
EXHAUST_GAMMA = 1.33
EXHAUST_GAS_CONSTANT_J_KG_K = 287.0
EXHAUST_CP_J_KG_K = 1150.0
EXHAUST_DYNAMIC_VISCOSITY_PA_S = 4.6e-5
AIR_FUEL_RATIO = 12.0
TURBINE_ISENTROPIC_EFFICIENCY = 0.70
MECHANICAL_EFFICIENCY = 0.95
RADIAL_METAL_GRADIENT_K = 350.0

OVERSPEED_FACTOR = 1.20
STRESS_CONCENTRATION_FACTOR = 2.5
MINIMUM_SCREEN_RATIO = 1.5
RESIDUAL_UNBALANCE_MG_MM = 10.0
SCREEN_DUTY_HOURS = 100.0


def tapered_blade_screen(angular_speed_rad_s: float) -> dict[str, float]:
    outer_radius_m = PUBLISHED_INDUCER_DIAMETER_MM / 2000.0
    inner_radius_m = SYNTHETIC_BLADE_INNER_RADIUS_MM / 1000.0
    length_m = outer_radius_m - inner_radius_m
    height_m = PUBLISHED_TIP_HEIGHT_MM / 1000.0
    root_thickness_m = SYNTHETIC_BLADE_ROOT_THICKNESS_MM / 1000.0
    tip_thickness_m = SYNTHETIC_BLADE_TIP_THICKNESS_MM / 1000.0
    thickness_delta_m = tip_thickness_m - root_thickness_m

    plan_area_m2 = length_m * (root_thickness_m + tip_thickness_m) / 2.0
    volume_m3 = plan_area_m2 * height_m
    mass_kg = MATERIAL_DENSITY_KG_M3 * volume_m3
    first_radial_moment_m3 = length_m * (
        root_thickness_m * (inner_radius_m + length_m / 2.0)
        + thickness_delta_m * (inner_radius_m / 2.0 + length_m / 3.0)
    )
    mean_radius_m = first_radial_moment_m3 / plan_area_m2
    centrifugal_force_n = mass_kg * angular_speed_rad_s**2 * mean_radius_m
    root_area_m2 = root_thickness_m * height_m
    root_stress_pa = (
        STRESS_CONCENTRATION_FACTOR * centrifugal_force_n / root_area_m2
    )
    return {
        "length_mm": length_m * 1000.0,
        "volume_mm3": volume_m3 * 1.0e9,
        "mass_g": mass_kg * 1000.0,
        "mean_radius_mm": mean_radius_m * 1000.0,
        "centrifugal_force_n": centrifugal_force_n,
        "root_area_mm2": root_area_m2 * 1.0e6,
        "nominal_root_stress_mpa": root_stress_pa / 1.0e6,
        "overspeed_root_stress_mpa": root_stress_pa * OVERSPEED_FACTOR**2 / 1.0e6,
    }


def engineering_screen(cad_volume_mm3: float | None = None) -> dict[str, object]:
    compressor_radius_m = COMPRESSOR_EXDUCER_DIAMETER_MM / 2000.0
    air_sound_speed_m_s = math.sqrt(
        AIR_GAMMA * AIR_GAS_CONSTANT_J_KG_K * AIR_INLET_TEMPERATURE_K
    )
    compressor_tip_speed_m_s = COMPRESSOR_TARGET_TIP_MACH * air_sound_speed_m_s
    angular_speed_rad_s = compressor_tip_speed_m_s / compressor_radius_m
    shaft_speed_rpm = angular_speed_rad_s * 60.0 / (2.0 * math.pi)
    shaft_frequency_hz = shaft_speed_rpm / 60.0

    turbine_radius_m = PUBLISHED_INDUCER_DIAMETER_MM / 2000.0
    turbine_tip_speed_m_s = angular_speed_rad_s * turbine_radius_m
    blade = tapered_blade_screen(angular_speed_rad_s)
    blade_root_ratio = (
        AMBIENT_YIELD_STRENGTH_PA / 1.0e6 / blade["overspeed_root_stress_mpa"]
    )
    disk_stress_pa = (
        (3.0 + POISSON_RATIO_PROVISIONAL)
        / 8.0
        * MATERIAL_DENSITY_KG_M3
        * angular_speed_rad_s**2
        * turbine_radius_m**2
    )
    overspeed_disk_stress_pa = disk_stress_pa * OVERSPEED_FACTOR**2
    disk_ratio = AMBIENT_YIELD_STRENGTH_PA / overspeed_disk_stress_pa

    thermal_stress_pa = (
        ELASTIC_MODULUS_PA_PROVISIONAL
        * PUBLISHED_CTE_AT_700C_PER_K
        * RADIAL_METAL_GRADIENT_K
        / (1.0 - POISSON_RATIO_PROVISIONAL)
    )
    thermal_ratio = AMBIENT_YIELD_STRENGTH_PA / thermal_stress_pa
    free_thermal_growth_mm = (
        PUBLISHED_CTE_AT_700C_PER_K
        * turbine_radius_m
        * (TURBINE_INLET_TEMPERATURE_C - 20.0)
        * 1000.0
    )
    elastic_growth_mm = (
        disk_stress_pa
        / ELASTIC_MODULUS_PA_PROVISIONAL
        * turbine_radius_m
        * 1000.0
    )

    air_density_kg_m3 = AIR_INLET_PRESSURE_PA / (
        AIR_GAS_CONSTANT_J_KG_K * AIR_INLET_TEMPERATURE_K
    )
    total_air_volume_flow_m3_s = (
        ENGINE_DISPLACEMENT_L
        / 1000.0
        * ENGINE_SPEED_RPM
        / (2.0 * 60.0)
        * ENGINE_VOLUMETRIC_EFFICIENCY
    )
    bank_air_volume_flow_m3_s = total_air_volume_flow_m3_s / 2.0
    bank_air_mass_flow_kg_s = air_density_kg_m3 * bank_air_volume_flow_m3_s
    compressor_t2s_k = AIR_INLET_TEMPERATURE_K * COMPRESSOR_PRESSURE_RATIO ** (
        (AIR_GAMMA - 1.0) / AIR_GAMMA
    )
    compressor_t2_k = AIR_INLET_TEMPERATURE_K + (
        compressor_t2s_k - AIR_INLET_TEMPERATURE_K
    ) / COMPRESSOR_ISENTROPIC_EFFICIENCY
    compressor_specific_work_j_kg = AIR_CP_J_KG_K * (
        compressor_t2_k - AIR_INLET_TEMPERATURE_K
    )
    compressor_power_w = bank_air_mass_flow_kg_s * compressor_specific_work_j_kg
    turbine_power_required_w = compressor_power_w / MECHANICAL_EFFICIENCY
    fuel_mass_flow_kg_s = bank_air_mass_flow_kg_s / AIR_FUEL_RATIO
    exhaust_mass_flow_kg_s = bank_air_mass_flow_kg_s + fuel_mass_flow_kg_s
    turbine_specific_work_j_kg = turbine_power_required_w / exhaust_mass_flow_kg_s
    turbine_inlet_temperature_k = TURBINE_INLET_TEMPERATURE_C + 273.15
    turbine_outlet_temperature_k = (
        turbine_inlet_temperature_k
        - turbine_specific_work_j_kg / EXHAUST_CP_J_KG_K
    )
    turbine_isentropic_outlet_temperature_k = (
        turbine_inlet_temperature_k
        - turbine_specific_work_j_kg
        / (TURBINE_ISENTROPIC_EFFICIENCY * EXHAUST_CP_J_KG_K)
    )
    expansion_ratio = (
        turbine_inlet_temperature_k / turbine_isentropic_outlet_temperature_k
    ) ** (EXHAUST_GAMMA / (EXHAUST_GAMMA - 1.0))
    turbine_inlet_pressure_pa = TURBINE_OUTLET_PRESSURE_PA * expansion_ratio
    exhaust_density_kg_m3 = turbine_inlet_pressure_pa / (
        EXHAUST_GAS_CONSTANT_J_KG_K * turbine_inlet_temperature_k
    )
    exhaust_sound_speed_m_s = math.sqrt(
        EXHAUST_GAMMA
        * EXHAUST_GAS_CONSTANT_J_KG_K
        * turbine_inlet_temperature_k
    )
    tip_reynolds = (
        exhaust_density_kg_m3
        * turbine_tip_speed_m_s
        * (PUBLISHED_INDUCER_DIAMETER_MM / 1000.0)
        / EXHAUST_DYNAMIC_VISCOSITY_PA_S
    )

    cad_mass_kg = (
        cad_volume_mm3 / 1.0e9 * MATERIAL_DENSITY_KG_M3
        if cad_volume_mm3 is not None
        else None
    )
    cylindrical_stock_volume_mm3 = (
        math.pi
        * (PUBLISHED_INDUCER_DIAMETER_MM / 2.0) ** 2
        * SYNTHETIC_TOTAL_HEIGHT_MM
    )
    cylindrical_stock_mass_kg = (
        cylindrical_stock_volume_mm3 / 1.0e9 * MATERIAL_DENSITY_KG_M3
    )
    load_mass_kg = cad_mass_kg if cad_mass_kg is not None else 0.10
    polar_inertia_kg_m2 = 0.5 * load_mass_kg * turbine_radius_m**2
    rotational_energy_j = 0.5 * polar_inertia_kg_m2 * angular_speed_rad_s**2
    unbalance_force_n = (
        RESIDUAL_UNBALANCE_MG_MM * 1.0e-9 * angular_speed_rad_s**2
    )
    revolutions_at_duty = shaft_frequency_hz * SCREEN_DUTY_HOURS * 3600.0

    temperature_envelope_pass = (
        TURBINE_INLET_TEMPERATURE_C <= PUBLISHED_USE_TEMPERATURE_LIMIT_C
    )
    ambient_mechanical_screen_pass = (
        blade_root_ratio >= MINIMUM_SCREEN_RATIO
        and disk_ratio >= MINIMUM_SCREEN_RATIO
        and thermal_ratio >= MINIMUM_SCREEN_RATIO
    )
    preliminary_screen_pass = (
        ambient_mechanical_screen_pass and temperature_envelope_pass
    )

    return {
        "schema_version": "1.0.0",
        "part_id": PART_ID,
        "status": "f0_clean_sheet_hot_rotor_analytical_screen_failed",
        "companion": {
            "part_id": COMPANION_PART_ID,
            "shared_shaft_speed_only": True,
            "coupled_rotor_geometry_available": False,
        },
        "geometry_authority": {
            "published": {
                "turbine_wheel_reference": PUBLISHED_TURBINE_WHEEL_REFERENCE,
                "right_turbo_reference": PUBLISHED_RIGHT_TURBO_REFERENCE,
                "inducer_diameter_mm": PUBLISHED_INDUCER_DIAMETER_MM,
                "exducer_diameter_mm": PUBLISHED_EXDUCER_DIAMETER_MM,
                "blade_count": PUBLISHED_BLADE_COUNT,
                "tip_height_mm": PUBLISHED_TIP_HEIGHT_MM,
                "shaft_diameter_mm": PUBLISHED_SHAFT_DIAMETER_MM,
            },
            "hypotheses": [
                "20 mm axial envelope, 5.8 mm backface and hub cone",
                "four-step straight radial blades approximate a 2.4 to 0.8 mm continuous taper",
                "9.5 mm analytical blade root radius and 2.5 stress concentration factor",
                "the shaft is excluded except for a short interface marker",
                "no camber, twist, scallop, fillet, balance cut, weld, seal or tip clearance",
            ],
            "not_claimed": "No Porsche, BorgWarner or production K16 surface, tolerance, material, balance, fit, weld, fatigue, creep or burst capability is claimed.",
        },
        "synthetic_operating_case": {
            "derived_shaft_speed_source": "same Mach 0.9 compressor F1 regression point; not measured",
            "overspeed_factor": OVERSPEED_FACTOR,
            "turbine_inlet_temperature_c": TURBINE_INLET_TEMPERATURE_C,
            "temperature_authority": "BorgWarner catalogue context T3 for the upgrade line; not K16 wheel metal temperature",
            "radial_metal_gradient_k": RADIAL_METAL_GRADIENT_K,
            "air_fuel_ratio": AIR_FUEL_RATIO,
            "turbine_isentropic_efficiency": TURBINE_ISENTROPIC_EFFICIENCY,
            "mechanical_efficiency": MECHANICAL_EFFICIENCY,
            "minimum_screen_ratio": MINIMUM_SCREEN_RATIO,
        },
        "material_screen": {
            "candidate": "EOS NickelAlloy IN718 API, M290 40 micrometre, heat-treated comparison",
            "process_trl": PUBLISHED_PROCESS_TRL,
            "density_kg_m3": MATERIAL_DENSITY_KG_M3,
            "ambient_vertical_yield_strength_pa": AMBIENT_YIELD_STRENGTH_PA,
            "ambient_vertical_ultimate_strength_pa": AMBIENT_ULTIMATE_STRENGTH_PA,
            "ambient_vertical_elongation_ratio": AMBIENT_ELONGATION_RATIO,
            "average_defect_fraction": PUBLISHED_AVERAGE_DEFECT_FRACTION,
            "minimum_wall_range_mm": PUBLISHED_MINIMUM_WALL_RANGE_MM,
            "published_use_temperature_limit_c": PUBLISHED_USE_TEMPERATURE_LIMIT_C,
            "published_cte_at_700c_per_k": PUBLISHED_CTE_AT_700C_PER_K,
            "provisional_elastic_modulus_pa": ELASTIC_MODULUS_PA_PROVISIONAL,
            "provisional_poisson_ratio": POISSON_RATIO_PROVISIONAL,
            "scope": "process-specific room-temperature coupons and a generic marketing temperature range; no K16 hot HCF, LCF, creep, crack-growth, oxidation or burst allowable",
        },
        "results": {
            "cad_volume_mm3": cad_volume_mm3,
            "cad_mass_g": cad_mass_kg * 1000.0 if cad_mass_kg is not None else None,
            "cylindrical_stock_mass_g": cylindrical_stock_mass_kg * 1000.0,
            "cylindrical_stock_to_cad_mass_ratio": (
                cylindrical_stock_mass_kg / cad_mass_kg if cad_mass_kg else None
            ),
            "derived_shaft_speed_rpm": shaft_speed_rpm,
            "shaft_frequency_hz": shaft_frequency_hz,
            "turbine_tip_speed_m_s": turbine_tip_speed_m_s,
            "turbine_tip_mach": turbine_tip_speed_m_s / exhaust_sound_speed_m_s,
            "turbine_tip_reynolds": tip_reynolds,
            "blade": blade,
            "ambient_yield_to_overspeed_blade_root_stress_ratio": blade_root_ratio,
            "overspeed_rotating_disk_stress_mpa": overspeed_disk_stress_pa / 1.0e6,
            "ambient_yield_to_overspeed_disk_stress_ratio": disk_ratio,
            "fully_constrained_gradient_stress_mpa": thermal_stress_pa / 1.0e6,
            "ambient_yield_to_constrained_gradient_ratio": thermal_ratio,
            "free_thermal_radius_growth_mm_extrapolated": free_thermal_growth_mm,
            "elastic_disk_radius_growth_mm": elastic_growth_mm,
            "gas_temperature_above_published_material_range_c": (
                TURBINE_INLET_TEMPERATURE_C - PUBLISHED_USE_TEMPERATURE_LIMIT_C
            ),
            "bank_air_mass_flow_kg_s": bank_air_mass_flow_kg_s,
            "bank_fuel_mass_flow_kg_s": fuel_mass_flow_kg_s,
            "bank_exhaust_mass_flow_kg_s": exhaust_mass_flow_kg_s,
            "compressor_power_w": compressor_power_w,
            "turbine_power_required_w": turbine_power_required_w,
            "turbine_specific_work_j_kg": turbine_specific_work_j_kg,
            "turbine_expansion_ratio_required": expansion_ratio,
            "turbine_inlet_pressure_pa_required": turbine_inlet_pressure_pa,
            "turbine_outlet_temperature_k": turbine_outlet_temperature_k,
            "turbine_isentropic_outlet_temperature_k": turbine_isentropic_outlet_temperature_k,
            "shaft_torque_nm": turbine_power_required_w / angular_speed_rad_s,
            "approximate_polar_inertia_kg_m2": polar_inertia_kg_m2,
            "approximate_rotational_energy_j": rotational_energy_j,
            "residual_unbalance_force_n": unbalance_force_n,
            "blade_pass_frequency_hz": PUBLISHED_BLADE_COUNT * shaft_frequency_hz,
            "revolutions_at_duty": revolutions_at_duty,
            "blade_events_at_duty": revolutions_at_duty * PUBLISHED_BLADE_COUNT,
            "minimum_required_screen_ratio": MINIMUM_SCREEN_RATIO,
            "temperature_envelope_pass": temperature_envelope_pass,
            "ambient_mechanical_screen_pass": ambient_mechanical_screen_pass,
            "preliminary_screen_pass": preliminary_screen_pass,
            "creep_screen_status": "not_computable_without_hot_stress_temperature_time_and_material_constants",
            "hcf_lcf_screen_status": "not_computable_without_hot_S_N_epsilon_N_notch_surface_and_defect_data",
        },
        "equations": {
            "shared_rotor_speed": "a=sqrt(gamma*R*T); U=M*a; omega=U/r_comp",
            "linear_taper_blade": "V=h*L*(troot+ttip)/2; F=rho*V*omega^2*rmean",
            "blade_root_stress": "sigma=Kt*F/(troot*h); sigma_over=sigma*factor^2",
            "rotating_disk": "sigma=(3+nu)/8*rho*omega^2*r^2",
            "thermal_gradient": "sigma=E*alpha*delta_T/(1-nu)",
            "thermal_growth": "delta_r=alpha*r*(Tgas-20C), extrapolated screen only",
            "compressor_power": "Pcomp=mdot_air*cp*(T2-T1)",
            "turbine_power": "Pturb=Pcomp/eta_mech; w=Pturb/mdot_exhaust",
            "expansion_ratio": "PR=(T3/T4s)^(gamma/(gamma-1))",
            "rotational_energy": "Erot=0.5*(0.5*m*r^2)*omega^2",
            "unbalance": "F=Ures*omega^2",
            "cycles": "Nrev=rpm/60*t; Nblade=Nrev*z",
        },
        "dfam_screen": {
            "additive_value": "tooling-free low-volume rotor topology and rapid iteration of a complex twelve-blade hot-side form",
            "open_blade_topology": True,
            "trapped_powder_volume": False,
            "minimum_tip_thickness_mm": SYNTHETIC_BLADE_TIP_THICKNESS_MM,
            "published_process_minimum_wall_range_mm": PUBLISHED_MINIMUM_WALL_RANGE_MM,
            "orientation_selected": False,
            "support_strategy_defined": False,
            "process_comparison_required": [
                "qualified investment-cast nickel turbine wheel joined to a steel shaft",
                "five-axis finish-machined conventional rotor route",
                "LPBF IN718 wheel with qualified shaft joining, finishing and contained burst validation",
            ],
        },
        "interpretation": {
            "result": "rejected: blade-root and thermal-gradient ratios miss 1.5 and the gas context exceeds the published material range",
            "geometry": "straight four-step blades are topology markers, not turbine profiles",
            "thermal": "gas T3 is not wheel metal temperature; the extrapolated growth and constrained gradient are bounding placeholders",
            "mechanics": "algebra omits 3D fillets, cast/AM defects, weld, contact, modes, creep, HCF, LCF and containment",
            "aerodynamics": "the one-point power balance is not a K16 turbine map or rotating CFD result",
            "physicsnemo": "deferred until correlated CFD, thermal-structure, rotor-dynamic and burst datasets exist",
            "simready": "deferred until the measured full rotor, housings, clearances and bearing assembly exist",
        },
        "release_blockers": [
            "No measured or CT-scanned 5316-120-5000 wheel, shaft or weld.",
            "No OEM blade camber, twist, thickness, fillet, scallop, hub, backface, balance cut or tolerance.",
            "The 20 mm envelope, hub, backface and four-step blade form are synthetic.",
            "No proof that the production K16 wheel uses IN718 or any additive route.",
            "The EOS API heat treatment and room-temperature coupons are not a turbine-rotor qualification.",
            "The 950 C value is catalogue gas context, not measured K16 wheel metal temperature.",
            "The gas context exceeds EOS's published generic 700 C material-use statement.",
            "No hot yield, creep, stress rupture, HCF, LCF, crack-growth, oxidation or coating allowables for the exact route.",
            "The blade-root and constrained-gradient algebraic ratios are below the 1.5 regression threshold.",
            "No K16 turbine map, shaft-speed trace, exhaust pulsation, pressure, efficiency, temperature or transient duty.",
            "No rotating CFD, conjugate heat transfer, FSI, mesh convergence or measured boundary correlation.",
            "No nonlinear rotating FEA, weld/contact model, Campbell diagram, rotor dynamics or probabilistic burst analysis.",
            "No qualified build orientation, supports, distortion compensation, heat treatment, HIP, machining, polishing or joining route.",
            "No CT, FPI, metallurgy, dimensional inspection, balance, spin proof, overspeed, burst or containment test.",
            "No bearing, seal, shaft, compressor, housing, clearance, oil/cooling or wastegate integration evidence.",
            "No professional turbomachinery review, approved validation plan, dyno authorization or vehicle release.",
        ],
        "manufacturing_authorized": False,
        "turbo_operation_authorized": False,
        "engine_operation_authorized": False,
        "release_authorized": False,
    }


def _blade_solid():
    from build123d import Align, Box, Pos

    outer_radius_mm = PUBLISHED_INDUCER_DIAMETER_MM / 2.0
    radial_length_mm = outer_radius_mm - SYNTHETIC_BLADE_INNER_RADIUS_MM
    segment_length_mm = radial_length_mm / CAD_TAPER_SEGMENT_COUNT
    blade = None
    for segment_index in range(CAD_TAPER_SEGMENT_COUNT):
        start_mm = SYNTHETIC_BLADE_INNER_RADIUS_MM + segment_index * segment_length_mm
        end_mm = start_mm + segment_length_mm
        fraction = (segment_index + 0.5) / CAD_TAPER_SEGMENT_COUNT
        thickness_mm = SYNTHETIC_BLADE_ROOT_THICKNESS_MM + fraction * (
            SYNTHETIC_BLADE_TIP_THICKNESS_MM
            - SYNTHETIC_BLADE_ROOT_THICKNESS_MM
        )
        segment = Pos(
            (start_mm + end_mm) / 2.0,
            0.0,
            SYNTHETIC_BACKFACE_THICKNESS_MM + PUBLISHED_TIP_HEIGHT_MM / 2.0 - 0.25,
        ) * Box(
            segment_length_mm + CAD_SEGMENT_OVERLAP_MM,
            thickness_mm,
            PUBLISHED_TIP_HEIGHT_MM,
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
        )
        blade = segment if blade is None else blade + segment
    return blade


def build_geometry():
    from build123d import Align, Cone, Cylinder, Pos, Rot

    outer_radius_mm = PUBLISHED_INDUCER_DIAMETER_MM / 2.0
    backface_radius_mm = PUBLISHED_EXDUCER_DIAMETER_MM / 2.0
    backface = Cylinder(
        backface_radius_mm,
        SYNTHETIC_BACKFACE_THICKNESS_MM,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    hub = Pos(0.0, 0.0, SYNTHETIC_BACKFACE_THICKNESS_MM - 0.4) * Cone(
        SYNTHETIC_HUB_ROOT_RADIUS_MM,
        PUBLISHED_SHAFT_DIAMETER_MM / 2.0,
        SYNTHETIC_TOTAL_HEIGHT_MM - SYNTHETIC_BACKFACE_THICKNESS_MM + 0.4,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    blade_clip = Pos(0.0, 0.0, SYNTHETIC_BACKFACE_THICKNESS_MM - 0.25) * Cylinder(
        outer_radius_mm,
        PUBLISHED_TIP_HEIGHT_MM,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    body = backface + hub
    for index in range(PUBLISHED_BLADE_COUNT):
        blade = Rot(0.0, 0.0, index * 360.0 / PUBLISHED_BLADE_COUNT) * _blade_solid()
        if not hasattr(blade, "is_valid"):
            blade = blade[0]
        body = body + (blade & blade_clip)
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
            raise SystemExit("Le F0 turbine doit contenir exactement un solide BREP valide.")
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
            "semantic_solids": ["clean_sheet_k16_in718_hot_rotor_f0"],
            "volume_mm3": cad_volume_mm3,
            "envelope_mm": envelope,
            "blade_count": PUBLISHED_BLADE_COUNT,
            "cad_taper_segment_count_per_blade": CAD_TAPER_SEGMENT_COUNT,
            "shaft_interface_marker_diameter_mm": PUBLISHED_SHAFT_DIAMETER_MM,
            "full_shaft_included": False,
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
