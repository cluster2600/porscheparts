#!/usr/bin/env python3
"""Roue de compresseur K16, iteration Al2139 AM a pales effilees F1."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


PART_ID = "993-ENG-K16-COMPRESSOR-WHEEL-AL2139-F1-0001"
F0_PART_ID = "993-ENG-K16-COMPRESSOR-WHEEL-ALSI10MG-F0-0001"

# Donnees publiees pour le K16 droit, identiques au F0.
PUBLISHED_INDUCER_DIAMETER_MM = 40.6
PUBLISHED_EXDUCER_DIAMETER_MM = 60.5
PUBLISHED_MAIN_BLADE_COUNT = 6
PUBLISHED_SPLITTER_BLADE_COUNT = 6
PUBLISHED_WHEEL_REFERENCE = "53241232006"
PUBLISHED_TURBO_REFERENCE = "53169886735"

# Geometrie F1 independante ; seules les epaisseurs varient depuis le F0.
BACKPLATE_THICKNESS_MM = 3.0
TOTAL_HEIGHT_MM = 18.0
BORE_DIAMETER_MM = 6.0
HUB_BOTTOM_RADIUS_MM = 8.0
HUB_TOP_RADIUS_MM = 4.0
BLADE_BASE_Z_MM = 2.5
MAIN_INNER_RADIUS_MM = 7.0
MAIN_HEIGHT_MM = 11.0
MAIN_ROOT_THICKNESS_MM = 3.0
MAIN_TIP_THICKNESS_MM = 0.8
SPLITTER_INNER_RADIUS_MM = 16.0
SPLITTER_HEIGHT_MM = 7.0
SPLITTER_ROOT_THICKNESS_MM = 2.4
SPLITTER_TIP_THICKNESS_MM = 0.8
CAD_TAPER_SEGMENT_COUNT = 4
CAD_SEGMENT_OVERLAP_MM = 0.4
INDUCER_HUB_DIAMETER_MM = 12.0

# EOS Al2139 AM M290 60 um, T4 : valeurs publiees a l'ambiante.
DENSITY_KG_M3 = 2840.0
COMPARISON_YIELD_STRENGTH_PA = 460.0e6
COMPARISON_ULTIMATE_STRENGTH_PA = 520.0e6
COMPARISON_ELONGATION_RATIO = 0.04
PUBLISHED_AVERAGE_DEFECT_FRACTION_RANGE = [0.002, 0.003]
PUBLISHED_MINIMUM_WALL_MM = 0.4
PUBLISHED_PROCESS_TRL = 3

# Parametres physiques provisoires non publies par la fiche de procede retenue.
ELASTIC_MODULUS_PA_PROVISIONAL = 70.0e9
POISSON_RATIO_PROVISIONAL = 0.33
THERMAL_EXPANSION_PER_K_PROVISIONAL = 23.0e-6
SPECIFIC_HEAT_J_KG_K_PROVISIONAL = 900.0

# Valeurs F0 AlSi10Mg recalculees pour la comparaison de boucle.
F0_DENSITY_KG_M3 = 2670.0
F0_YIELD_STRENGTH_PA = 245.0e6
F0_UNIFORM_BLADE_THICKNESS_MM = 1.2

# Point de regression identique au F0.
AIR_GAMMA = 1.4
AIR_GAS_CONSTANT_J_KG_K = 287.05
AIR_CP_J_KG_K = 1005.0
AIR_DYNAMIC_VISCOSITY_PA_S = 1.9e-5
INLET_TEMPERATURE_K = 330.0
INLET_ABSOLUTE_PRESSURE_PA = 180_000.0
TARGET_TIP_MACH = 0.90
PRESSURE_RATIO = 1.80
ISENTROPIC_EFFICIENCY = 0.72
ENGINE_DISPLACEMENT_L = 3.6
ENGINE_SPEED_RPM = 5750.0
ENGINE_VOLUMETRIC_EFFICIENCY = 0.95
STRESS_CONCENTRATION_FACTOR = 2.0
OVERSPEED_FACTOR = 1.20
THERMAL_DELTA_T_K = 150.0
RESIDUAL_UNBALANCE_MG_MM = 10.0
SCREEN_DUTY_HOURS = 100.0
MINIMUM_SCREEN_RATIO = 1.5


def tapered_blade_screen(
    inner_radius_mm: float,
    height_mm: float,
    root_thickness_mm: float,
    tip_thickness_mm: float,
    density_kg_m3: float,
    angular_speed_rad_s: float,
) -> dict[str, float]:
    outer_radius_m = PUBLISHED_EXDUCER_DIAMETER_MM / 2000.0
    inner_radius_m = inner_radius_mm / 1000.0
    length_m = outer_radius_m - inner_radius_m
    height_m = height_mm / 1000.0
    root_thickness_m = root_thickness_mm / 1000.0
    tip_thickness_m = tip_thickness_mm / 1000.0
    thickness_delta_m = tip_thickness_m - root_thickness_m

    area_plan_m2 = length_m * (root_thickness_m + tip_thickness_m) / 2.0
    volume_m3 = area_plan_m2 * height_m
    mass_kg = density_kg_m3 * volume_m3
    first_radial_moment_m3 = length_m * (
        root_thickness_m * (inner_radius_m + length_m / 2.0)
        + thickness_delta_m * (inner_radius_m / 2.0 + length_m / 3.0)
    )
    mean_radius_m = first_radial_moment_m3 / area_plan_m2
    centrifugal_force_n = mass_kg * angular_speed_rad_s**2 * mean_radius_m
    root_area_m2 = root_thickness_m * height_m
    root_stress_pa = (
        STRESS_CONCENTRATION_FACTOR * centrifugal_force_n / root_area_m2
    )
    return {
        "volume_mm3": volume_m3 * 1.0e9,
        "mass_g": mass_kg * 1000.0,
        "mean_radius_mm": mean_radius_m * 1000.0,
        "centrifugal_force_n": centrifugal_force_n,
        "root_area_mm2": root_area_m2 * 1.0e6,
        "root_stress_mpa": root_stress_pa / 1.0e6,
        "overspeed_root_stress_mpa": root_stress_pa * OVERSPEED_FACTOR**2 / 1.0e6,
    }


def engineering_screen(cad_volume_mm3: float | None = None) -> dict[str, object]:
    radius_m = PUBLISHED_EXDUCER_DIAMETER_MM / 2000.0
    sound_speed_m_s = math.sqrt(AIR_GAMMA * AIR_GAS_CONSTANT_J_KG_K * INLET_TEMPERATURE_K)
    tip_speed_m_s = TARGET_TIP_MACH * sound_speed_m_s
    angular_speed_rad_s = tip_speed_m_s / radius_m
    shaft_speed_rpm = angular_speed_rad_s * 60.0 / (2.0 * math.pi)
    shaft_frequency_hz = shaft_speed_rpm / 60.0

    cad_mass_kg = (
        cad_volume_mm3 / 1.0e9 * DENSITY_KG_M3
        if cad_volume_mm3 is not None
        else None
    )
    load_mass_kg = cad_mass_kg if cad_mass_kg is not None else 0.042
    cylindrical_stock_volume_mm3 = math.pi * (radius_m * 1000.0) ** 2 * TOTAL_HEIGHT_MM
    cylindrical_stock_mass_kg = cylindrical_stock_volume_mm3 / 1.0e9 * DENSITY_KG_M3

    main = tapered_blade_screen(
        MAIN_INNER_RADIUS_MM,
        MAIN_HEIGHT_MM,
        MAIN_ROOT_THICKNESS_MM,
        MAIN_TIP_THICKNESS_MM,
        DENSITY_KG_M3,
        angular_speed_rad_s,
    )
    splitter = tapered_blade_screen(
        SPLITTER_INNER_RADIUS_MM,
        SPLITTER_HEIGHT_MM,
        SPLITTER_ROOT_THICKNESS_MM,
        SPLITTER_TIP_THICKNESS_MM,
        DENSITY_KG_M3,
        angular_speed_rad_s,
    )
    f0_main = tapered_blade_screen(
        MAIN_INNER_RADIUS_MM,
        MAIN_HEIGHT_MM,
        F0_UNIFORM_BLADE_THICKNESS_MM,
        F0_UNIFORM_BLADE_THICKNESS_MM,
        F0_DENSITY_KG_M3,
        angular_speed_rad_s,
    )
    f0_splitter = tapered_blade_screen(
        SPLITTER_INNER_RADIUS_MM,
        SPLITTER_HEIGHT_MM,
        F0_UNIFORM_BLADE_THICKNESS_MM,
        F0_UNIFORM_BLADE_THICKNESS_MM,
        F0_DENSITY_KG_M3,
        angular_speed_rad_s,
    )

    governing_root_stress_mpa = max(
        main["overspeed_root_stress_mpa"], splitter["overspeed_root_stress_mpa"]
    )
    f0_governing_root_stress_mpa = max(
        f0_main["overspeed_root_stress_mpa"],
        f0_splitter["overspeed_root_stress_mpa"],
    )
    root_screen_ratio = (
        COMPARISON_YIELD_STRENGTH_PA / 1.0e6 / governing_root_stress_mpa
    )
    f0_root_screen_ratio = (
        F0_YIELD_STRENGTH_PA / 1.0e6 / f0_governing_root_stress_mpa
    )

    disk_stress_pa = (
        (3.0 + POISSON_RATIO_PROVISIONAL)
        / 8.0
        * DENSITY_KG_M3
        * angular_speed_rad_s**2
        * radius_m**2
    )
    overspeed_disk_stress_pa = disk_stress_pa * OVERSPEED_FACTOR**2
    disk_screen_ratio = COMPARISON_YIELD_STRENGTH_PA / overspeed_disk_stress_pa
    fully_constrained_thermal_stress_pa = (
        ELASTIC_MODULUS_PA_PROVISIONAL
        * THERMAL_EXPANSION_PER_K_PROVISIONAL
        * THERMAL_DELTA_T_K
    )
    thermal_screen_ratio = (
        COMPARISON_YIELD_STRENGTH_PA / fully_constrained_thermal_stress_pa
    )
    ambient_analytical_screen_pass = (
        root_screen_ratio >= MINIMUM_SCREEN_RATIO
        and disk_screen_ratio >= MINIMUM_SCREEN_RATIO
        and thermal_screen_ratio >= MINIMUM_SCREEN_RATIO
    )

    density_air_kg_m3 = INLET_ABSOLUTE_PRESSURE_PA / (
        AIR_GAS_CONSTANT_J_KG_K * INLET_TEMPERATURE_K
    )
    total_engine_flow_m3_s = (
        ENGINE_DISPLACEMENT_L
        / 1000.0
        * ENGINE_SPEED_RPM
        / (2.0 * 60.0)
        * ENGINE_VOLUMETRIC_EFFICIENCY
    )
    bank_flow_m3_s = total_engine_flow_m3_s / 2.0
    inducer_area_m2 = math.pi / 4.0 * (
        (PUBLISHED_INDUCER_DIAMETER_MM / 1000.0) ** 2
        - (INDUCER_HUB_DIAMETER_MM / 1000.0) ** 2
    )
    axial_velocity_m_s = bank_flow_m3_s / inducer_area_m2
    inducer_reynolds = (
        density_air_kg_m3
        * axial_velocity_m_s
        * (PUBLISHED_INDUCER_DIAMETER_MM / 1000.0)
        / AIR_DYNAMIC_VISCOSITY_PA_S
    )
    isentropic_outlet_temperature_k = INLET_TEMPERATURE_K * PRESSURE_RATIO ** (
        (AIR_GAMMA - 1.0) / AIR_GAMMA
    )
    adjusted_outlet_temperature_k = INLET_TEMPERATURE_K + (
        isentropic_outlet_temperature_k - INLET_TEMPERATURE_K
    ) / ISENTROPIC_EFFICIENCY
    specific_work_j_kg = AIR_CP_J_KG_K * (
        adjusted_outlet_temperature_k - INLET_TEMPERATURE_K
    )
    bank_mass_flow_kg_s = density_air_kg_m3 * bank_flow_m3_s
    compressor_power_w = bank_mass_flow_kg_s * specific_work_j_kg

    elastic_radius_growth_mm = (
        disk_stress_pa / ELASTIC_MODULUS_PA_PROVISIONAL * radius_m * 1000.0
    )
    thermal_radius_growth_mm = (
        THERMAL_EXPANSION_PER_K_PROVISIONAL
        * radius_m
        * THERMAL_DELTA_T_K
        * 1000.0
    )
    approximate_polar_inertia_kg_m2 = 0.5 * load_mass_kg * radius_m**2
    approximate_rotational_energy_j = (
        0.5 * approximate_polar_inertia_kg_m2 * angular_speed_rad_s**2
    )
    residual_unbalance_force_n = (
        RESIDUAL_UNBALANCE_MG_MM * 1.0e-9 * angular_speed_rad_s**2
    )
    revolutions_at_duty = shaft_frequency_hz * SCREEN_DUTY_HOURS * 3600.0

    return {
        "schema_version": "1.0.0",
        "part_id": PART_ID,
        "status": "f1_material_and_taper_iteration_ambient_analytical_screen_only",
        "predecessor": {
            "part_id": F0_PART_ID,
            "reason": "F0 AlSi10Mg straight main blades failed the ambient 1.2x overspeed root screen",
            "f0_governing_overspeed_root_stress_mpa": f0_governing_root_stress_mpa,
            "f0_ambient_yield_mpa": F0_YIELD_STRENGTH_PA / 1.0e6,
            "f0_screen_ratio": f0_root_screen_ratio,
        },
        "geometry_authority": {
            "published": {
                "wheel_reference": PUBLISHED_WHEEL_REFERENCE,
                "right_turbo_reference": PUBLISHED_TURBO_REFERENCE,
                "inducer_diameter_mm": PUBLISHED_INDUCER_DIAMETER_MM,
                "exducer_diameter_mm": PUBLISHED_EXDUCER_DIAMETER_MM,
                "main_blade_count": PUBLISHED_MAIN_BLADE_COUNT,
                "splitter_blade_count": PUBLISHED_SPLITTER_BLADE_COUNT,
            },
            "interpretations": [
                "published diameters and 6+6 count retain exactly the F0 scope",
                "Al2139 AM is a separate candidate selected because the AlSi10Mg F0 failed its ambient overspeed screen",
                "the EOS heat-treated room-temperature values are comparisons, not K16 rotor allowables",
            ],
            "hypotheses": [
                "main blades taper analytically from 3.0 to 0.8 mm",
                "splitters taper analytically from 2.4 to 0.8 mm",
                "CAD represents each continuous taper by four overlapping radial thickness steps",
                "backplate, 18 mm height, 6 mm bore, hub and all axial blade heights remain F0 hypotheses",
                "no camber, three-dimensional twist, fillet, nut, shaft fit, balance cut or tip clearance",
            ],
            "not_claimed": "No Porsche, BorgWarner, K16 or production compressor surface, map, material, balance, fit, fatigue or burst capability is claimed.",
        },
        "synthetic_operating_case": {
            "target_tip_mach": TARGET_TIP_MACH,
            "inlet_temperature_k": INLET_TEMPERATURE_K,
            "inlet_absolute_pressure_pa": INLET_ABSOLUTE_PRESSURE_PA,
            "pressure_ratio": PRESSURE_RATIO,
            "isentropic_efficiency": ISENTROPIC_EFFICIENCY,
            "engine_displacement_l": ENGINE_DISPLACEMENT_L,
            "engine_speed_rpm": ENGINE_SPEED_RPM,
            "engine_volumetric_efficiency": ENGINE_VOLUMETRIC_EFFICIENCY,
            "overspeed_factor": OVERSPEED_FACTOR,
            "thermal_delta_t_k": THERMAL_DELTA_T_K,
            "minimum_screen_ratio": MINIMUM_SCREEN_RATIO,
            "authority": "same regression point as F0; no K16 map, shaft-speed trace, temperature, balance, clearance or duty was measured",
        },
        "material_screen": {
            "candidate": "EOS Aluminium Al2139 AM, M290 60 micrometre, heat-treated comparison",
            "process_trl": PUBLISHED_PROCESS_TRL,
            "density_kg_m3": DENSITY_KG_M3,
            "comparison_yield_strength_pa": COMPARISON_YIELD_STRENGTH_PA,
            "comparison_ultimate_strength_pa": COMPARISON_ULTIMATE_STRENGTH_PA,
            "comparison_elongation_ratio": COMPARISON_ELONGATION_RATIO,
            "published_average_defect_fraction_range": PUBLISHED_AVERAGE_DEFECT_FRACTION_RANGE,
            "published_minimum_wall_mm": PUBLISHED_MINIMUM_WALL_MM,
            "provisional_elastic_modulus_pa": ELASTIC_MODULUS_PA_PROVISIONAL,
            "provisional_poisson_ratio": POISSON_RATIO_PROVISIONAL,
            "provisional_thermal_expansion_per_k": THERMAL_EXPANSION_PER_K_PROVISIONAL,
            "scope": "density and room-temperature tensile values are process-specific EOS data; thermal constants are placeholders and no hot HCF, fracture, defect or burst allowable exists",
        },
        "results": {
            "cad_volume_mm3": cad_volume_mm3,
            "cad_mass_g": cad_mass_kg * 1000.0 if cad_mass_kg is not None else None,
            "cylindrical_stock_mass_g": cylindrical_stock_mass_kg * 1000.0,
            "cylindrical_stock_to_cad_mass_ratio": (
                cylindrical_stock_mass_kg / cad_mass_kg if cad_mass_kg else None
            ),
            "sound_speed_m_s": sound_speed_m_s,
            "tip_speed_m_s": tip_speed_m_s,
            "derived_shaft_speed_rpm": shaft_speed_rpm,
            "shaft_frequency_hz": shaft_frequency_hz,
            "bank_volume_flow_m3_s": bank_flow_m3_s,
            "bank_mass_flow_kg_s": bank_mass_flow_kg_s,
            "inducer_annulus_area_m2": inducer_area_m2,
            "inducer_axial_velocity_m_s": axial_velocity_m_s,
            "inducer_axial_mach": axial_velocity_m_s / sound_speed_m_s,
            "flow_coefficient": axial_velocity_m_s / tip_speed_m_s,
            "inducer_reynolds": inducer_reynolds,
            "efficiency_adjusted_outlet_temperature_k": adjusted_outlet_temperature_k,
            "specific_compressor_work_j_kg": specific_work_j_kg,
            "screening_compressor_power_w": compressor_power_w,
            "screening_compressor_torque_nm": compressor_power_w / angular_speed_rad_s,
            "main_blade": main,
            "splitter_blade": splitter,
            "f1_governing_overspeed_root_stress_mpa": governing_root_stress_mpa,
            "f1_ambient_yield_to_overspeed_root_stress_ratio": root_screen_ratio,
            "f0_governing_overspeed_root_stress_mpa_recomputed": f0_governing_root_stress_mpa,
            "f0_ambient_yield_to_overspeed_root_stress_ratio_recomputed": f0_root_screen_ratio,
            "root_stress_reduction_ratio_vs_f0": 1.0 - governing_root_stress_mpa / f0_governing_root_stress_mpa,
            "overspeed_rotating_disk_stress_mpa": overspeed_disk_stress_pa / 1.0e6,
            "f1_ambient_yield_to_overspeed_disk_stress_ratio": disk_screen_ratio,
            "fully_constrained_thermal_stress_mpa": fully_constrained_thermal_stress_pa / 1.0e6,
            "f1_ambient_yield_to_constrained_thermal_ratio": thermal_screen_ratio,
            "minimum_required_screen_ratio": MINIMUM_SCREEN_RATIO,
            "ambient_analytical_screen_pass": ambient_analytical_screen_pass,
            "elastic_disk_radius_growth_mm": elastic_radius_growth_mm,
            "free_thermal_radius_growth_mm": thermal_radius_growth_mm,
            "screening_combined_radius_growth_mm": elastic_radius_growth_mm + thermal_radius_growth_mm,
            "approximate_rotational_energy_j": approximate_rotational_energy_j,
            "residual_unbalance_force_n": residual_unbalance_force_n,
            "main_blade_pass_frequency_hz": PUBLISHED_MAIN_BLADE_COUNT * shaft_frequency_hz,
            "all_blade_pass_frequency_hz": (PUBLISHED_MAIN_BLADE_COUNT + PUBLISHED_SPLITTER_BLADE_COUNT) * shaft_frequency_hz,
            "revolutions_at_duty": revolutions_at_duty,
        },
        "equations": {
            "linear_taper_area": "Aplan=L*(troot+ttip)/2",
            "linear_taper_radial_moment": "int(r*t(r)dr)=L*[troot*(r0+L/2)+(ttip-troot)*(r0/2+L/3)]",
            "blade_force": "F=rho*h*Aplan*omega^2*rmean",
            "blade_root_stress": "sigma=Kt*F/(troot*h); sigma_over=sigma*factor^2",
            "rotating_disk": "sigma=(3+nu)/8*rho*omega^2*r^2",
            "speed_and_flow": "a=sqrt(gamma*R*T); U=M*a; omega=U/r; Qbank=Vd*N*VE/(240)",
            "compressor_power": "T2=T1+(T1*PR^((gamma-1)/gamma)-T1)/eta; P=mdot*cp*(T2-T1)",
            "elastic_growth": "delta_r=sigma/E*r",
            "thermal_growth": "delta_r=alpha*r*delta_T",
            "fully_constrained_thermal": "sigma=E*alpha*delta_T",
            "rotational_energy": "Erot=0.5*(0.5*m*r^2)*omega^2",
            "unbalance": "F=Ures*omega^2",
            "revolutions": "n=N/60*t_seconds",
        },
        "dfam_screen": {
            "additive_value": "load-driven root-to-tip blade thickness can be printed without casting tooling and iterated from analysis",
            "open_blade_topology": True,
            "trapped_powder_volume": False,
            "minimum_tip_thickness_mm": min(MAIN_TIP_THICKNESS_MM, SPLITTER_TIP_THICKNESS_MM),
            "published_process_minimum_wall_mm": PUBLISHED_MINIMUM_WALL_MM,
            "orientation_selected": False,
            "support_strategy_defined": False,
            "bore_backface_profiles_and_balance_features_require_machining": True,
            "process_comparison_required": [
                "qualified cast aluminium compressor wheel",
                "five-axis machined billet aluminium wheel",
                "LPBF Al2139 AM wheel with complete aerodynamic and burst qualification",
            ],
        },
        "interpretation": {
            "iteration": "F1 clears three separate ambient algebraic ratios; this is a useful redesign screen, not a valid rotor",
            "geometry": "four-step radial CAD blades approximate the continuous analytical taper and remain topology markers, not compressor profiles",
            "material": "460 MPa is a room-temperature heat-treated coupon value and cannot be used as a hot fatigue or burst allowable",
            "aerodynamics": "unchanged one-point thermodynamics cannot prove that the thickness-profiled F1 blades compress air",
            "mechanics": "taper integrals and disk equations omit 3D fillets, bore fit, preload, defects, modes, HCF and containment",
            "physicsnemo": "deferred until correlated CFD, thermal-structure, rotor-dynamic and burst cases define train, holdout and OOD sets",
            "simready": "deferred until the full measured rotating assembly and compressor housing exist",
        },
        "release_blockers": [
            "No measured K16 wheel, profile, camber, twist, fillet, hub, bore, backface, balance or mass distribution.",
            "The F1 thickness law and four-step CAD approximation are synthetic and have no aerodynamic optimization or manufacturing tolerance study.",
            "No evidence that wheel 53241232006 uses Al2139 AM, LPBF or the assumed interfaces.",
            "EOS marks the M290 60 micrometre process TRL 3 and reports 0.2-0.3 percent average defects.",
            "The 460 MPa comparison is ambient heat-treated coupon data, not a rotor allowable at temperature or after finishing.",
            "No measured K16 map, shaft-speed trace, surge/choke, pressure, efficiency, temperature, transient or duty.",
            "No shaft, nut, bore fit, backplate, diffuser, compressor housing, bearing system, clearance or balance datum.",
            "No rotating 3D CFD, FSI, mesh convergence or proof that F1 blades produce the target pressure ratio.",
            "No nonlinear rotating FEA, contact/preload, Campbell diagram, rotor dynamics, HCF, fracture or probabilistic burst analysis.",
            "No Al2139 AM hot HCF/LCF, crack growth, notch, surface, corrosion and defect allowables for the exact route.",
            "No qualified orientation, supports, distortion compensation, heat treatment, HIP decision, machining stock or polishing process.",
            "No CT, metallography, dimensional inspection, balance, spin proof, overspeed, burst or containment test.",
            "No compatibility evidence for the left K16, housings, charge circuit, controls or engine calibration.",
            "No professional turbomachinery review, approved validation plan, dyno authorization or vehicle release.",
        ],
        "manufacturing_authorized": False,
        "turbo_operation_authorized": False,
        "engine_operation_authorized": False,
        "release_authorized": False,
    }


def _blade_solid(
    inner_radius_mm: float,
    height_mm: float,
    root_thickness_mm: float,
    tip_thickness_mm: float,
):
    from build123d import Align, Box, Pos

    outer_radius_mm = PUBLISHED_EXDUCER_DIAMETER_MM / 2.0
    radial_length_mm = outer_radius_mm - inner_radius_mm
    segment_length_mm = radial_length_mm / CAD_TAPER_SEGMENT_COUNT
    blade = None
    for segment_index in range(CAD_TAPER_SEGMENT_COUNT):
        start_mm = inner_radius_mm + segment_index * segment_length_mm
        end_mm = start_mm + segment_length_mm
        fraction = (segment_index + 0.5) / CAD_TAPER_SEGMENT_COUNT
        thickness_mm = root_thickness_mm + fraction * (
            tip_thickness_mm - root_thickness_mm
        )
        segment = Pos(
            (start_mm + end_mm) / 2.0,
            0.0,
            BLADE_BASE_Z_MM + height_mm / 2.0,
        ) * Box(
            segment_length_mm + CAD_SEGMENT_OVERLAP_MM,
            thickness_mm,
            height_mm,
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
        )
        blade = segment if blade is None else blade + segment
    return blade


def build_geometry():
    from build123d import Align, Cone, Cylinder, Pos, Rot

    outer_radius_mm = PUBLISHED_EXDUCER_DIAMETER_MM / 2.0
    backplate = Cylinder(
        outer_radius_mm,
        BACKPLATE_THICKNESS_MM,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    hub = Pos(0.0, 0.0, BACKPLATE_THICKNESS_MM - 0.5) * Cone(
        HUB_BOTTOM_RADIUS_MM,
        HUB_TOP_RADIUS_MM,
        TOTAL_HEIGHT_MM - BACKPLATE_THICKNESS_MM + 0.5,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    blade_clip = Pos(0.0, 0.0, BLADE_BASE_Z_MM) * Cylinder(
        outer_radius_mm,
        max(MAIN_HEIGHT_MM, SPLITTER_HEIGHT_MM),
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    body = backplate + hub
    for index in range(PUBLISHED_MAIN_BLADE_COUNT):
        blade = Rot(0.0, 0.0, index * 360.0 / PUBLISHED_MAIN_BLADE_COUNT) * _blade_solid(
            MAIN_INNER_RADIUS_MM,
            MAIN_HEIGHT_MM,
            MAIN_ROOT_THICKNESS_MM,
            MAIN_TIP_THICKNESS_MM,
        )
        if not hasattr(blade, "is_valid"):
            blade = blade[0]
        body = body + (blade & blade_clip)
    for index in range(PUBLISHED_SPLITTER_BLADE_COUNT):
        angle_deg = index * 360.0 / PUBLISHED_SPLITTER_BLADE_COUNT + 180.0 / PUBLISHED_SPLITTER_BLADE_COUNT
        blade = Rot(0.0, 0.0, angle_deg) * _blade_solid(
            SPLITTER_INNER_RADIUS_MM,
            SPLITTER_HEIGHT_MM,
            SPLITTER_ROOT_THICKNESS_MM,
            SPLITTER_TIP_THICKNESS_MM,
        )
        if not hasattr(blade, "is_valid"):
            blade = blade[0]
        body = body + (blade & blade_clip)
    bore = Pos(0.0, 0.0, -1.0) * Cylinder(
        BORE_DIAMETER_MM / 2.0,
        TOTAL_HEIGHT_MM + 2.0,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    return body - bore


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
            raise SystemExit("Le F1 doit contenir exactement un solide BREP valide.")
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
            "semantic_solids": ["clean_sheet_k16_al2139_four_step_taper_blade_f1"],
            "volume_mm3": cad_volume_mm3,
            "envelope_mm": envelope,
            "main_blade_count": PUBLISHED_MAIN_BLADE_COUNT,
            "splitter_blade_count": PUBLISHED_SPLITTER_BLADE_COUNT,
            "minimum_tip_thickness_mm": min(MAIN_TIP_THICKNESS_MM, SPLITTER_TIP_THICKNESS_MM),
            "cad_taper_segment_count_per_blade": CAD_TAPER_SEGMENT_COUNT,
            "through_bore_count": 1,
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
