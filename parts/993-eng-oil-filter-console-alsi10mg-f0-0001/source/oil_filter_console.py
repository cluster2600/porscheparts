#!/usr/bin/env python3
"""Console de filtre à huile moteur 993 AlSi10Mg, concept F0 à galeries intégrées."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


PART_ID = "993-ENG-OIL-FILTER-CONSOLE-ALSI10MG-F0-0001"

# Faits publics. Les dimensions du filtre ne définissent pas la console.
PUBLISHED_CONSOLE_PART_NUMBERS = ["99310705700", "99310705701"]
PUBLISHED_CONSOLE_MASS_KG = 0.78
PUBLISHED_FILTER_PART_NUMBER = "99310720303"
PUBLISHED_FILTER_MODEL = "MAHLE_OC229"
PUBLISHED_FILTER_HEIGHT_MM = 101.0
PUBLISHED_FILTER_DIAMETER_MM = 76.0
PUBLISHED_FILTER_BASE_DIAMETER_MM = 72.0
PUBLISHED_FILTER_SEAL_DIAMETER_MM = 62.0
PUBLISHED_FILTER_THREAD = "M20x1.5"
PUBLISHED_FILTER_TORQUE_NM = 20.0
PUBLISHED_FILTER_MASS_G = 333.0
OCR_UNVERIFIED_OIL_PRESSURE_BAR = 6.5
OCR_UNVERIFIED_OIL_PRESSURE_RPM = 5000.0
OCR_UNVERIFIED_OIL_PRESSURE_TEMPERATURE_C = 90.0

# Géométrie propre et synthétique. Aucune surface commerciale ou Porsche.
BODY_LENGTH_MM = 130.0
BODY_WIDTH_MM = 90.0
BODY_HEIGHT_MM = 20.0
FILTER_PEDESTAL_CENTER_X_MM = 25.0
FILTER_PEDESTAL_OUTER_DIAMETER_MM = 82.0
FILTER_PEDESTAL_HEIGHT_MM = 20.0
FILTER_SEAL_LAND_OUTER_DIAMETER_MM = 72.0
FILTER_SEAL_LAND_INNER_DIAMETER_MM = 62.0
FILTER_SEAL_LAND_HEIGHT_MM = 1.0
FILTER_SPIGOT_OUTER_DIAMETER_MM = 20.0
FILTER_SPIGOT_BORE_DIAMETER_MM = 12.0
FILTER_SPIGOT_HEIGHT_MM = 10.0
EXTERNAL_PORT_BOSS_DIAMETER_MM = 26.0
EXTERNAL_PORT_BOSS_LENGTH_MM = 14.0
MAIN_GALLERY_DIAMETER_MM = 16.0
MAIN_GALLERY_TOTAL_LENGTH_MM = 165.0
SPIGOT_GALLERY_LENGTH_MM = 20.0
INLET_GALLERY_Y_MM = -22.0
OUTLET_GALLERY_Y_MM = 0.0
MOUNT_BORE_DIAMETER_MM = 8.5
MOUNT_X_MM = (-50.0, 50.0)
MOUNT_Y_MM = (-34.0, 34.0)

# Comparaison générique EOS AlSi10Mg du projet, pas carte admissible chaude.
DENSITY_KG_M3 = 2670.0
ELASTIC_MODULUS_PA = 70.0e9
COMPARISON_YIELD_STRENGTH_PA = 245.0e6
THERMAL_EXPANSION_PER_K = 21.0e-6
SPECIFIC_HEAT_J_KG_K = 900.0
PUBLISHED_PROCESS_MINIMUM_WALL_MM = 0.4

# Cas analytiques synthétiques et volontairement conservateurs.
SYNTHETIC_FLOW_L_MIN = 30.0
OIL_DENSITY_KG_M3 = 850.0
HOT_OIL_DYNAMIC_VISCOSITY_PA_S = 0.012
COLD_OIL_DYNAMIC_VISCOSITY_PA_S = 0.25
AS_BUILT_EFFECTIVE_ROUGHNESS_MM = 0.05
MAIN_GALLERY_LOCAL_LOSS_K = 5.5
SPIGOT_LOCAL_LOSS_K = 1.5
MAXIMUM_PRESSURE_LOSS_FRACTION = 0.05
SYNTHETIC_PROOF_PRESSURE_BAR = 12.0
MINIMUM_CHANNEL_WALL_MM = 4.0
NUT_FACTOR = 0.20
FILTER_THREAD_NOMINAL_DIAMETER_M = 0.020
SYNTHETIC_THREAD_ENGAGEMENT_MM = 12.0
SYNTHETIC_THREAD_SHEAR_FRACTION = 0.50
MAXIMUM_FILTER_SEAL_PRESSURE_MPA = 8.0
OPERATING_CONSOLE_TEMPERATURE_C = 150.0
REFERENCE_TEMPERATURE_C = 20.0
MINIMUM_SCREEN_RATIO = 1.5


def _friction_factor(reynolds: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        raise ValueError("Le nombre de Reynolds doit être positif.")
    if reynolds < 2300.0:
        return 64.0 / reynolds
    roughness_m = AS_BUILT_EFFECTIVE_ROUGHNESS_MM / 1000.0
    return (
        -1.8
        * math.log10(
            (roughness_m / (3.7 * diameter_m)) ** 1.11 + 6.9 / reynolds
        )
    ) ** -2


def _hydraulic_case(dynamic_viscosity_pa_s: float) -> dict[str, float]:
    flow_m3_s = SYNTHETIC_FLOW_L_MIN / 1000.0 / 60.0
    segments = (
        (MAIN_GALLERY_DIAMETER_MM / 1000.0, 0.095, 3.0),
        (FILTER_SPIGOT_BORE_DIAMETER_MM / 1000.0, 0.020, SPIGOT_LOCAL_LOSS_K),
        (MAIN_GALLERY_DIAMETER_MM / 1000.0, 0.070, 2.5),
    )
    total_pressure_loss_pa = 0.0
    segment_results: list[dict[str, float]] = []
    for diameter_m, length_m, local_loss_k in segments:
        area_m2 = math.pi * diameter_m**2 / 4.0
        velocity_m_s = flow_m3_s / area_m2
        reynolds = (
            OIL_DENSITY_KG_M3
            * velocity_m_s
            * diameter_m
            / dynamic_viscosity_pa_s
        )
        friction_factor = _friction_factor(reynolds, diameter_m)
        pressure_loss_pa = (
            (friction_factor * length_m / diameter_m + local_loss_k)
            * OIL_DENSITY_KG_M3
            * velocity_m_s**2
            / 2.0
        )
        total_pressure_loss_pa += pressure_loss_pa
        segment_results.append(
            {
                "diameter_mm": diameter_m * 1000.0,
                "length_mm": length_m * 1000.0,
                "local_loss_k": local_loss_k,
                "velocity_m_s": velocity_m_s,
                "reynolds": reynolds,
                "friction_factor": friction_factor,
                "pressure_loss_pa": pressure_loss_pa,
            }
        )
    return {
        "dynamic_viscosity_pa_s": dynamic_viscosity_pa_s,
        "flow_m3_s": flow_m3_s,
        "total_pressure_loss_pa": total_pressure_loss_pa,
        "hydraulic_power_w": total_pressure_loss_pa * flow_m3_s,
        "segments": segment_results,
    }


def engineering_screen(cad_volume_mm3: float | None = None) -> dict[str, object]:
    reference_pressure_pa = OCR_UNVERIFIED_OIL_PRESSURE_BAR * 100_000.0
    pressure_loss_limit_pa = reference_pressure_pa * MAXIMUM_PRESSURE_LOSS_FRACTION
    hot_case = _hydraulic_case(HOT_OIL_DYNAMIC_VISCOSITY_PA_S)
    cold_case = _hydraulic_case(COLD_OIL_DYNAMIC_VISCOSITY_PA_S)
    hot_pressure_ratio = pressure_loss_limit_pa / hot_case["total_pressure_loss_pa"]
    cold_pressure_ratio = pressure_loss_limit_pa / cold_case["total_pressure_loss_pa"]
    hot_hydraulic_pass = hot_pressure_ratio >= 1.0
    cold_hydraulic_pass = cold_pressure_ratio >= 1.0

    proof_pressure_pa = SYNTHETIC_PROOF_PRESSURE_BAR * 100_000.0
    channel_wall_stress_pa = (
        proof_pressure_pa
        * (MAIN_GALLERY_DIAMETER_MM / 1000.0)
        / (2.0 * MINIMUM_CHANNEL_WALL_MM / 1000.0)
    )
    channel_wall_yield_ratio = COMPARISON_YIELD_STRENGTH_PA / channel_wall_stress_pa

    filter_preload_n = PUBLISHED_FILTER_TORQUE_NM / (
        NUT_FACTOR * FILTER_THREAD_NOMINAL_DIAMETER_M
    )
    seal_area_mm2 = math.pi / 4.0 * (
        PUBLISHED_FILTER_BASE_DIAMETER_MM**2
        - PUBLISHED_FILTER_SEAL_DIAMETER_MM**2
    )
    filter_seal_pressure_mpa = filter_preload_n / seal_area_mm2
    thread_shear_area_mm2 = (
        math.pi
        * FILTER_THREAD_NOMINAL_DIAMETER_M
        * 1000.0
        * SYNTHETIC_THREAD_ENGAGEMENT_MM
        * SYNTHETIC_THREAD_SHEAR_FRACTION
    )
    thread_shear_stress_mpa = filter_preload_n / thread_shear_area_mm2
    thread_von_mises_mpa = math.sqrt(3.0) * thread_shear_stress_mpa
    thread_yield_ratio = (
        COMPARISON_YIELD_STRENGTH_PA / 1.0e6 / thread_von_mises_mpa
    )
    filter_interface_pass = (
        filter_seal_pressure_mpa <= MAXIMUM_FILTER_SEAL_PRESSURE_MPA
        and thread_yield_ratio >= MINIMUM_SCREEN_RATIO
    )

    delta_temperature_k = OPERATING_CONSOLE_TEMPERATURE_C - REFERENCE_TEMPERATURE_C
    synthetic_envelope_length_mm = BODY_LENGTH_MM + EXTERNAL_PORT_BOSS_LENGTH_MM
    free_thermal_growth_mm = (
        THERMAL_EXPANSION_PER_K * synthetic_envelope_length_mm * delta_temperature_k
    )
    fully_constrained_thermal_stress_pa = (
        ELASTIC_MODULUS_PA * THERMAL_EXPANSION_PER_K * delta_temperature_k
    )
    thermal_yield_ratio = (
        COMPARISON_YIELD_STRENGTH_PA / fully_constrained_thermal_stress_pa
    )
    thermal_screen_pass = thermal_yield_ratio >= MINIMUM_SCREEN_RATIO

    cad_mass_kg = (
        cad_volume_mm3 / 1.0e9 * DENSITY_KG_M3
        if cad_volume_mm3 is not None
        else None
    )
    billet_envelope_height_mm = (
        BODY_HEIGHT_MM + FILTER_PEDESTAL_HEIGHT_MM + FILTER_SPIGOT_HEIGHT_MM
    )
    billet_box_volume_mm3 = (
        synthetic_envelope_length_mm * BODY_WIDTH_MM * billet_envelope_height_mm
    )
    billet_box_mass_kg = billet_box_volume_mm3 / 1.0e9 * DENSITY_KG_M3
    lumped_heat_capacity_j_k = (
        cad_mass_kg * SPECIFIC_HEAT_J_KG_K if cad_mass_kg is not None else None
    )

    pressure_screen_pass = channel_wall_yield_ratio >= MINIMUM_SCREEN_RATIO
    preliminary_screen_pass = (
        hot_hydraulic_pass
        and cold_hydraulic_pass
        and pressure_screen_pass
        and filter_interface_pass
        and thermal_screen_pass
    )

    return {
        "schema_version": "1.0.0",
        "part_id": PART_ID,
        "status": "f0_clean_sheet_integrated_oil_console_analytical_screen_failed",
        "geometry_authority": {
            "published": {
                "console_part_numbers": PUBLISHED_CONSOLE_PART_NUMBERS,
                "console_commercial_mass_kg": PUBLISHED_CONSOLE_MASS_KG,
                "filter_part_number": PUBLISHED_FILTER_PART_NUMBER,
                "filter_model": PUBLISHED_FILTER_MODEL,
                "filter_height_mm": PUBLISHED_FILTER_HEIGHT_MM,
                "filter_diameter_mm": PUBLISHED_FILTER_DIAMETER_MM,
                "filter_base_diameter_mm": PUBLISHED_FILTER_BASE_DIAMETER_MM,
                "filter_seal_diameter_mm": PUBLISHED_FILTER_SEAL_DIAMETER_MM,
                "filter_thread": PUBLISHED_FILTER_THREAD,
                "filter_torque_nm": PUBLISHED_FILTER_TORQUE_NM,
                "filter_mass_g": PUBLISHED_FILTER_MASS_G,
                "oil_pressure_bar_ocr_unverified": OCR_UNVERIFIED_OIL_PRESSURE_BAR,
                "oil_pressure_rpm_ocr_unverified": OCR_UNVERIFIED_OIL_PRESSURE_RPM,
                "oil_pressure_temperature_c_ocr_unverified": OCR_UNVERIFIED_OIL_PRESSURE_TEMPERATURE_C,
            },
            "hypotheses": [
                "144 x 90 x 50 mm overall F0 envelope",
                "130 x 90 x 20 mm synthetic body and 82 mm filter pedestal",
                "four synthetic 8.5 mm mounting bores",
                "two synthetic non-collinear internal oil galleries",
                "16 mm main galleries and 12 mm unthreaded filter-spigot bore",
                "no OEM mounting surface, oil-port position, sensor boss, thread, seal groove or tolerance",
            ],
            "not_claimed": "The 0.78 kg is a retailer value for 993 107 057 01 and the filter dimensions describe MAHLE OC 229; neither defines this clean-sheet console geometry or proves fit.",
        },
        "synthetic_cases": {
            "flow_l_min": SYNTHETIC_FLOW_L_MIN,
            "oil_density_kg_m3": OIL_DENSITY_KG_M3,
            "hot_dynamic_viscosity_pa_s": HOT_OIL_DYNAMIC_VISCOSITY_PA_S,
            "cold_dynamic_viscosity_pa_s": COLD_OIL_DYNAMIC_VISCOSITY_PA_S,
            "effective_roughness_mm": AS_BUILT_EFFECTIVE_ROUGHNESS_MM,
            "maximum_pressure_loss_fraction_of_ocr_reference": MAXIMUM_PRESSURE_LOSS_FRACTION,
            "proof_pressure_bar": SYNTHETIC_PROOF_PRESSURE_BAR,
            "minimum_channel_wall_mm": MINIMUM_CHANNEL_WALL_MM,
            "nut_factor": NUT_FACTOR,
            "synthetic_thread_engagement_mm": SYNTHETIC_THREAD_ENGAGEMENT_MM,
            "operating_console_temperature_c": OPERATING_CONSOLE_TEMPERATURE_C,
            "minimum_screen_ratio": MINIMUM_SCREEN_RATIO,
            "authority": "regression inputs only; no measured 993 flow, viscosity, pressure waveform, roughness, local-loss coefficients, proof pressure, temperature field, thread or seal law",
        },
        "material_screen": {
            "candidate": "EOS Aluminium AlSi10Mg LPBF T6 comparison",
            "commercial_architecture_reference": "Islandworks integrated console in billet 6061-T6, not a 993 replacement",
            "oem_console_material": "not_published",
            "density_kg_m3": DENSITY_KG_M3,
            "elastic_modulus_pa": ELASTIC_MODULUS_PA,
            "comparison_yield_strength_pa": COMPARISON_YIELD_STRENGTH_PA,
            "thermal_expansion_per_k": THERMAL_EXPANSION_PER_K,
            "specific_heat_j_kg_k": SPECIFIC_HEAT_J_KG_K,
            "published_process_minimum_wall_mm": PUBLISHED_PROCESS_MINIMUM_WALL_MM,
            "scope": "generic ambient comparison only; no hot-oil fatigue, pressure, corrosion, thread, sealing, porosity or cleanliness allowables",
        },
        "results": {
            "cad_volume_mm3": cad_volume_mm3,
            "cad_mass_g": cad_mass_kg * 1000.0 if cad_mass_kg is not None else None,
            "published_console_mass_g": PUBLISHED_CONSOLE_MASS_KG * 1000.0,
            "cad_to_published_mass_ratio": cad_mass_kg / PUBLISHED_CONSOLE_MASS_KG if cad_mass_kg else None,
            "billet_box_mass_g": billet_box_mass_kg * 1000.0,
            "billet_box_to_cad_mass_ratio": billet_box_mass_kg / cad_mass_kg if cad_mass_kg else None,
            "lumped_heat_capacity_j_k": lumped_heat_capacity_j_k,
            "pressure_loss_limit_pa": pressure_loss_limit_pa,
            "hot_hydraulic": hot_case,
            "cold_hydraulic": cold_case,
            "hot_pressure_loss_allowance_ratio": hot_pressure_ratio,
            "cold_pressure_loss_allowance_ratio": cold_pressure_ratio,
            "hot_hydraulic_pass": hot_hydraulic_pass,
            "cold_hydraulic_pass": cold_hydraulic_pass,
            "channel_wall_stress_mpa_at_proof": channel_wall_stress_pa / 1.0e6,
            "ambient_yield_to_channel_wall_ratio": channel_wall_yield_ratio,
            "filter_preload_n_from_published_torque": filter_preload_n,
            "synthetic_filter_seal_area_mm2": seal_area_mm2,
            "synthetic_filter_seal_pressure_mpa": filter_seal_pressure_mpa,
            "thread_shear_area_mm2": thread_shear_area_mm2,
            "thread_shear_stress_mpa": thread_shear_stress_mpa,
            "thread_von_mises_mpa": thread_von_mises_mpa,
            "ambient_yield_to_thread_von_mises_ratio": thread_yield_ratio,
            "filter_interface_pass": filter_interface_pass,
            "free_thermal_growth_mm": free_thermal_growth_mm,
            "fully_constrained_thermal_stress_mpa": fully_constrained_thermal_stress_pa / 1.0e6,
            "ambient_yield_to_constrained_thermal_ratio": thermal_yield_ratio,
            "pressure_screen_pass": pressure_screen_pass,
            "thermal_screen_pass": thermal_screen_pass,
            "preliminary_screen_pass": preliminary_screen_pass,
            "fatigue_seal_and_cleanliness_status": "not_computable_without_correlated_hot_material_surface_pressure_cycle_seal_and_residual-contamination_data",
        },
        "equations": {
            "continuity": "v=Q/A; A=pi*d^2/4",
            "reynolds": "Re=rho*v*d/mu",
            "laminar_friction": "f=64/Re for Re<2300",
            "haaland_friction": "f=[-1.8*log10((epsilon/(3.7d))^1.11+6.9/Re)]^-2",
            "darcy_weisbach": "delta_p=sum[(f*L/d+K)*rho*v^2/2]",
            "hydraulic_power": "P=delta_p*Q",
            "channel_membrane": "sigma=p*d/(2*t), screening approximation",
            "filter_preload": "F=T/(K*d), K is synthetic and torque belongs to the filter",
            "seal_pressure": "p=F/[pi*(D_outer^2-D_inner^2)/4]",
            "thread_shear": "tau=F/[pi*d*Le*0.5]; sigma_vm=sqrt(3)*tau",
            "thermal_growth": "delta_L=alpha*L*delta_T",
            "constrained_thermal": "sigma=E*alpha*delta_T",
            "mass_and_heat_capacity": "m=rho*V; C=m*cp",
        },
        "dfam_screen": {
            "additive_value": "two non-collinear oil paths, filter pedestal, threaded-boss stock and external ports consolidated without cross-drill closure plugs",
            "integrated_gallery_count": 2,
            "gallery_opening_count": 4,
            "trapped_powder_volume": False,
            "powder_removal_validated": False,
            "minimum_channel_wall_mm": MINIMUM_CHANNEL_WALL_MM,
            "published_process_minimum_wall_mm": PUBLISHED_PROCESS_MINIMUM_WALL_MM,
            "wall_to_process_minimum_ratio": MINIMUM_CHANNEL_WALL_MM / PUBLISHED_PROCESS_MINIMUM_WALL_MM,
            "filter_spigot_is_unthreaded_machining_stock": True,
            "orientation_selected": False,
            "support_strategy_defined": False,
            "all_filter_mount_seal_sensor_and_port_surfaces_require_machining": True,
            "process_comparison_required": [
                "OEM casting plus machining",
                "CNC 6061-T6 with cross-drilled galleries and qualified closure plugs",
                "LPBF AlSi10Mg with integrated galleries",
            ],
        },
        "interpretation": {
            "result": "hot synthetic pressure loss, proof wall and filter algebra pass; cold pressure loss and fully constrained thermal screens fail",
            "hydraulics": "the filter element, bypass valve, real bends, ports, fittings and engine galleries are excluded, so the Darcy screen is not a system prediction",
            "mass": "closeness to the 0.78 kg retailer value cannot validate shape because the commercial weighing boundary and geometry are unknown",
            "filter_interface": "filter dimensions bound a mating component only; the console thread, seal land and installation stack remain unmeasured",
            "physicsnemo": "deferred until correlated CFD, conjugate-thermal, structural, leakage, contamination and durability datasets exist",
            "simready": "deferred until crankcase, console, filter, sensors, lines, seals and service clearances are measured",
        },
        "release_blockers": [
            "No measured 993 console, crankcase face, gallery centers, ports, bosses, sensors, filter spigot, seal land, datums or tolerances.",
            "PorscheFanatics supplies identity and assembly context only, not geometry or material.",
            "The 0.78 kg value is retailer-declared with an unknown weighing boundary and no protocol.",
            "The OC 229 dimensions describe the filter, not the mating console surface.",
            "The F0 envelope, mounting pattern, gallery topology, diameters, wall and machining stock are synthetic.",
            "No evidence that the OEM console uses AlSi10Mg, LPBF or the assumed heat treatment.",
            "No measured oil flow, hot/cold viscosity, pressure waveform, aeration, contamination, temperature or duty cycle.",
            "The 6.5 bar at 5000 rpm and 90 C value is an unverified OCR occurrence, not a released load case.",
            "The cold pressure-loss screen fails and excludes the filter element and its bypass valve.",
            "The fully constrained thermal screen fails the minimum ratio.",
            "The filter preload uses an arbitrary nut factor and does not establish thread or gasket contact.",
            "No CHT-CFD, cavitation, pressure pulsation, nonlinear contact, thread, modal, fatigue or crack-growth analysis.",
            "No qualified orientation, supports, distortion compensation, T6, HIP, machining stock, sealing or surface route.",
            "No CT, FPI, metallography, dimensional inspection, pressure proof, burst, leakage, flow, thermal-cycle or vibration test.",
            "No validated depowdering, flushing, particle extraction or engine-oil cleanliness acceptance criterion.",
            "No professional lubrication-system review, approved validation plan, dyno authorization or vehicle release.",
        ],
        "manufacturing_authorized": False,
        "engine_operation_authorized": False,
        "release_authorized": False,
    }


def _cylinder_x(radius_mm: float, length_mm: float, x_mm: float, y_mm: float, z_mm: float):
    from build123d import Align, Cylinder, Pos, Rot

    return (
        Pos(x_mm, y_mm, z_mm)
        * Rot(0.0, 90.0, 0.0)
        * Cylinder(radius_mm, length_mm, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    )


def _cylinder_between_xz(
    radius_mm: float,
    start: tuple[float, float],
    end: tuple[float, float],
    y_mm: float,
):
    from build123d import Align, Cylinder, Pos, Rot

    dx = end[0] - start[0]
    dz = end[1] - start[1]
    length_mm = math.hypot(dx, dz) + 1.0
    angle_y_deg = math.degrees(math.atan2(dx, dz))
    midpoint_x = (start[0] + end[0]) / 2.0
    midpoint_z = (start[1] + end[1]) / 2.0
    return (
        Pos(midpoint_x, y_mm, midpoint_z)
        * Rot(0.0, angle_y_deg, 0.0)
        * Cylinder(radius_mm, length_mm, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    )


def build_geometry():
    from build123d import Align, Box, Cylinder, Pos

    centered_min = (Align.CENTER, Align.CENTER, Align.MIN)
    body = Box(BODY_LENGTH_MM, BODY_WIDTH_MM, BODY_HEIGHT_MM, align=centered_min)

    pedestal = Pos(FILTER_PEDESTAL_CENTER_X_MM, 0.0, BODY_HEIGHT_MM - 0.5) * Cylinder(
        FILTER_PEDESTAL_OUTER_DIAMETER_MM / 2.0,
        FILTER_PEDESTAL_HEIGHT_MM + 0.5,
        align=centered_min,
    )
    body = body + pedestal

    seal_land = Pos(
        FILTER_PEDESTAL_CENTER_X_MM,
        0.0,
        BODY_HEIGHT_MM + FILTER_PEDESTAL_HEIGHT_MM - 0.5,
    ) * Cylinder(
        FILTER_SEAL_LAND_OUTER_DIAMETER_MM / 2.0,
        FILTER_SEAL_LAND_HEIGHT_MM + 0.5,
        align=centered_min,
    )
    seal_land_inner = Pos(
        FILTER_PEDESTAL_CENTER_X_MM,
        0.0,
        BODY_HEIGHT_MM + FILTER_PEDESTAL_HEIGHT_MM - 1.0,
    ) * Cylinder(
        FILTER_SEAL_LAND_INNER_DIAMETER_MM / 2.0,
        FILTER_SEAL_LAND_HEIGHT_MM + 2.0,
        align=centered_min,
    )
    body = body + (seal_land - seal_land_inner)

    spigot = Pos(
        FILTER_PEDESTAL_CENTER_X_MM,
        0.0,
        BODY_HEIGHT_MM + FILTER_PEDESTAL_HEIGHT_MM - 0.5,
    ) * Cylinder(
        FILTER_SPIGOT_OUTER_DIAMETER_MM / 2.0,
        FILTER_SPIGOT_HEIGHT_MM + 0.5,
        align=centered_min,
    )
    body = body + spigot

    inlet_boss = _cylinder_x(
        EXTERNAL_PORT_BOSS_DIAMETER_MM / 2.0,
        EXTERNAL_PORT_BOSS_LENGTH_MM,
        -BODY_LENGTH_MM / 2.0,
        INLET_GALLERY_Y_MM,
        13.0,
    )
    outlet_boss = _cylinder_x(
        EXTERNAL_PORT_BOSS_DIAMETER_MM / 2.0,
        EXTERNAL_PORT_BOSS_LENGTH_MM,
        BODY_LENGTH_MM / 2.0,
        OUTLET_GALLERY_Y_MM,
        15.0,
    )
    body = body + inlet_boss + outlet_boss

    for x_mm in MOUNT_X_MM:
        for y_mm in MOUNT_Y_MM:
            mount_bore = Pos(x_mm, y_mm, -1.0) * Cylinder(
                MOUNT_BORE_DIAMETER_MM / 2.0,
                BODY_HEIGHT_MM + 2.0,
                align=centered_min,
            )
            body = body - mount_bore

    inlet_channel = _cylinder_x(
        MAIN_GALLERY_DIAMETER_MM / 2.0,
        34.0,
        -56.0,
        INLET_GALLERY_Y_MM,
        13.0,
    )
    inlet_channel = inlet_channel + _cylinder_between_xz(
        MAIN_GALLERY_DIAMETER_MM / 2.0,
        (-41.0, 13.0),
        (FILTER_PEDESTAL_CENTER_X_MM, 30.0),
        INLET_GALLERY_Y_MM,
    )
    inlet_channel = inlet_channel + Pos(
        FILTER_PEDESTAL_CENTER_X_MM,
        INLET_GALLERY_Y_MM,
        27.0,
    ) * Cylinder(
        MAIN_GALLERY_DIAMETER_MM / 2.0,
        16.0,
        align=centered_min,
    )

    outlet_channel = Pos(
        FILTER_PEDESTAL_CENTER_X_MM,
        OUTLET_GALLERY_Y_MM,
        27.0,
    ) * Cylinder(
        FILTER_SPIGOT_BORE_DIAMETER_MM / 2.0,
        24.0,
        align=centered_min,
    )
    outlet_channel = outlet_channel + _cylinder_between_xz(
        MAIN_GALLERY_DIAMETER_MM / 2.0,
        (FILTER_PEDESTAL_CENTER_X_MM, 29.0),
        (48.0, 15.0),
        OUTLET_GALLERY_Y_MM,
    )
    outlet_channel = outlet_channel + _cylinder_x(
        MAIN_GALLERY_DIAMETER_MM / 2.0,
        35.0,
        56.5,
        OUTLET_GALLERY_Y_MM,
        15.0,
    )
    body = body - inlet_channel - outlet_channel
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
            raise SystemExit("La console d'huile F0 doit être un solide BREP unique valide.")
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
            "semantic_solids": ["clean_sheet_993_oil_filter_console_integrated_galleries_f0"],
            "volume_mm3": cad_volume_mm3,
            "envelope_mm": envelope,
            "mount_bore_count": len(MOUNT_X_MM) * len(MOUNT_Y_MM),
            "integrated_gallery_count": 2,
            "external_port_count": 2,
            "filter_opening_count": 2,
            "unthreaded_filter_spigot_count": 1,
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
