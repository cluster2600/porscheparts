#!/usr/bin/env python3
"""Collecteur d'admission trois conduits 993, concept AlSi10Mg F0."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


PART_ID = "993-ENG-THREE-RUNNER-INTAKE-ALSI10MG-F0-0001"

# Chaîne dimensionnelle publiée dans le titre PMO, interprétée seulement au F0.
PUBLISHED_TOP_DIAMETER_MM = 46.0
PUBLISHED_BOTTOM_DIAMETER_MM = 42.0
PUBLISHED_HEIGHT_MM = 100.0
PUBLISHED_PIECES_PER_SET = 2

# Topologie propre au projet. Aucune interface ou position de boulon n'est publiée.
RUNNER_WALL_MM = 2.0
LOWER_CENTERS_X_MM = (-55.0, 0.0, 55.0)
UPPER_CENTERS_X_MM = (-65.0, 0.0, 65.0)
LOWER_CENTER_Y_MM = 0.0
UPPER_CENTER_Y_MM = 5.0
FLANGE_X_MM = 180.0
FLANGE_Y_MM = 70.0
FLANGE_THICKNESS_MM = 6.0

# Cas de débit synthétique, sans autorité moteur.
ENGINE_DISPLACEMENT_L = 3.6
ENGINE_SPEED_RPM = 6800.0
VOLUMETRIC_EFFICIENCY = 0.95
RUNNER_COUNT_ENGINE = 6
AIR_TEMPERATURE_K = 320.0
AIR_DENSITY_KG_M3 = 1.16
AIR_DYNAMIC_VISCOSITY_PA_S = 1.9e-5
HEAT_CAPACITY_RATIO = 1.4
AIR_GAS_CONSTANT_J_KG_K = 287.0
CONTRACTION_LOSS_COEFFICIENT = 0.05
SCREEN_GAUGE_PRESSURE_PA = 10_000.0
SCREEN_DELTA_T_K = 100.0

# Carte générique de criblage AlSi10Mg.
DENSITY_G_CM3 = 2.67
ELASTIC_MODULUS_MPA = 70_000.0
COMPARISON_YIELD_STRENGTH_MPA = 245.0
THERMAL_EXPANSION_PER_K = 21.0e-6
THERMAL_CONDUCTIVITY_W_MK = 155.0
SPECIFIC_HEAT_J_KG_K = 900.0


def radius_at_z(radius_bottom_mm: float, radius_top_mm: float, z_mm: float) -> float:
    return radius_bottom_mm + (
        radius_top_mm - radius_bottom_mm
    ) * z_mm / PUBLISHED_HEIGHT_MM


def frustum_segment_volume_mm3(
    radius_bottom_mm: float,
    radius_top_mm: float,
    z0_mm: float,
    z1_mm: float,
) -> float:
    r0 = radius_at_z(radius_bottom_mm, radius_top_mm, z0_mm)
    r1 = radius_at_z(radius_bottom_mm, radius_top_mm, z1_mm)
    length = z1_mm - z0_mm
    return math.pi * length / 3.0 * (r0**2 + r0 * r1 + r1**2)


def analytic_volume_mm3() -> float:
    inner_bottom = PUBLISHED_BOTTOM_DIAMETER_MM / 2.0
    inner_top = PUBLISHED_TOP_DIAMETER_MM / 2.0
    outer_bottom = inner_bottom + RUNNER_WALL_MM
    outer_top = inner_top + RUNNER_WALL_MM
    middle_z0 = FLANGE_THICKNESS_MM
    middle_z1 = PUBLISHED_HEIGHT_MM - FLANGE_THICKNESS_MM

    middle_shell_each = frustum_segment_volume_mm3(
        outer_bottom, outer_top, middle_z0, middle_z1
    ) - frustum_segment_volume_mm3(
        inner_bottom, inner_top, middle_z0, middle_z1
    )
    flange_volume = 2.0 * FLANGE_X_MM * FLANGE_Y_MM * FLANGE_THICKNESS_MM
    flange_flow_voids = len(LOWER_CENTERS_X_MM) * (
        frustum_segment_volume_mm3(
            inner_bottom, inner_top, 0.0, FLANGE_THICKNESS_MM
        )
        + frustum_segment_volume_mm3(
            inner_bottom,
            inner_top,
            PUBLISHED_HEIGHT_MM - FLANGE_THICKNESS_MM,
            PUBLISHED_HEIGHT_MM,
        )
    )
    return len(LOWER_CENTERS_X_MM) * middle_shell_each + flange_volume - flange_flow_voids


def engineering_screen(cad_volume_mm3: float | None = None) -> dict[str, object]:
    top_radius_m = PUBLISHED_TOP_DIAMETER_MM / 2000.0
    bottom_radius_m = PUBLISHED_BOTTOM_DIAMETER_MM / 2000.0
    top_area_m2 = math.pi * top_radius_m**2
    bottom_area_m2 = math.pi * bottom_radius_m**2
    total_volume_flow_m3_s = (
        ENGINE_DISPLACEMENT_L
        / 1000.0
        * ENGINE_SPEED_RPM
        / (2.0 * 60.0)
        * VOLUMETRIC_EFFICIENCY
    )
    runner_volume_flow_m3_s = total_volume_flow_m3_s / RUNNER_COUNT_ENGINE
    top_velocity_m_s = runner_volume_flow_m3_s / top_area_m2
    bottom_velocity_m_s = runner_volume_flow_m3_s / bottom_area_m2
    speed_of_sound_m_s = math.sqrt(
        HEAT_CAPACITY_RATIO * AIR_GAS_CONSTANT_J_KG_K * AIR_TEMPERATURE_K
    )
    reynolds_bottom = (
        AIR_DENSITY_KG_M3
        * bottom_velocity_m_s
        * (2.0 * bottom_radius_m)
        / AIR_DYNAMIC_VISCOSITY_PA_S
    )
    ideal_kinetic_pressure_change_pa = 0.5 * AIR_DENSITY_KG_M3 * (
        bottom_velocity_m_s**2 - top_velocity_m_s**2
    )
    contraction_loss_pa = (
        CONTRACTION_LOSS_COEFFICIENT
        * 0.5
        * AIR_DENSITY_KG_M3
        * bottom_velocity_m_s**2
    )

    firing_frequency_hz = ENGINE_SPEED_RPM / 60.0 * RUNNER_COUNT_ENGINE / 2.0
    runner_quarter_wave_hz = speed_of_sound_m_s / (
        4.0 * PUBLISHED_HEIGHT_MM / 1000.0
    )
    first_order_quarter_wave_length_mm = (
        speed_of_sound_m_s / (4.0 * firing_frequency_hz) * 1000.0
    )
    side_runner_splay_deg = math.degrees(
        math.atan2(
            abs(UPPER_CENTERS_X_MM[0] - LOWER_CENTERS_X_MM[0]),
            PUBLISHED_HEIGHT_MM,
        )
    )

    mean_radius_m = (top_radius_m + bottom_radius_m) / 2.0
    hoop_stress_mpa = (
        SCREEN_GAUGE_PRESSURE_PA
        * mean_radius_m
        / (RUNNER_WALL_MM / 1000.0)
        / 1_000_000.0
    )
    free_expansion_mm = (
        THERMAL_EXPANSION_PER_K * PUBLISHED_HEIGHT_MM * SCREEN_DELTA_T_K
    )
    fully_constrained_stress_mpa = (
        ELASTIC_MODULUS_MPA * THERMAL_EXPANSION_PER_K * SCREEN_DELTA_T_K
    )

    analytic_mm3 = analytic_volume_mm3()
    volume_mm3 = cad_volume_mm3 if cad_volume_mm3 is not None else analytic_mm3
    mass_g = volume_mm3 / 1000.0 * DENSITY_G_CM3

    return {
        "schema_version": "1.0.0",
        "part_id": PART_ID,
        "status": "f0_published_dimensional_string_clean_sheet_flow_screen_only",
        "geometry_authority": {
            "published": [
                "commercial title string 46 mm x 42 mm x 100 mm",
                "three-bolt manifold set with two pieces",
                "raw aluminium finish, alloy not disclosed",
            ],
            "catalogue_identity": ["FUE PMO 9150", "PM-O915-0", "PMO9150"],
            "hypotheses": [
                "46 mm interpreted as upper flow diameter",
                "42 mm interpreted as lower flow diameter",
                "100 mm interpreted as axial runner height",
                "three runners per bank on synthetic center positions",
                "2 mm walls and two 6 mm common flanges",
                "side runners splayed 10 mm outward and 5 mm laterally",
                "three-bolt pattern intentionally omitted",
            ],
            "not_claimed": "No PMO or Porsche surface, port spacing, bolt pattern, flange, fitment or flow performance is claimed.",
        },
        "synthetic_cases": {
            "engine_displacement_l": ENGINE_DISPLACEMENT_L,
            "engine_speed_rpm": ENGINE_SPEED_RPM,
            "volumetric_efficiency": VOLUMETRIC_EFFICIENCY,
            "runner_count_engine": RUNNER_COUNT_ENGINE,
            "air_temperature_k": AIR_TEMPERATURE_K,
            "screen_gauge_pressure_pa": SCREEN_GAUGE_PRESSURE_PA,
            "contraction_loss_coefficient": CONTRACTION_LOSS_COEFFICIENT,
            "authority": "regression inputs only; no measured M64 volumetric efficiency, pulse, temperature, port field or complete intake tract",
        },
        "material_screen": {
            "candidate": "generic LPBF AlSi10Mg, study only",
            "density_g_cm3": DENSITY_G_CM3,
            "elastic_modulus_mpa": ELASTIC_MODULUS_MPA,
            "comparison_yield_strength_mpa": COMPARISON_YIELD_STRENGTH_MPA,
            "thermal_expansion_per_k": THERMAL_EXPANSION_PER_K,
            "thermal_conductivity_w_mk": THERMAL_CONDUCTIVITY_W_MK,
            "specific_heat_j_kg_k": SPECIFIC_HEAT_J_KG_K,
            "scope": "generic ambient screening values; no qualified intake-manifold LPBF material card",
        },
        "results": {
            "analytic_volume_mm3": analytic_mm3,
            "cad_volume_mm3": volume_mm3,
            "cad_minus_analytic_volume_mm3": volume_mm3 - analytic_mm3,
            "screening_mass_each_bank_g": mass_g,
            "screening_mass_pair_g": 2.0 * mass_g,
            "top_flow_area_each_m2": top_area_m2,
            "bottom_flow_area_each_m2": bottom_area_m2,
            "total_cold_volume_flow_m3_s": total_volume_flow_m3_s,
            "runner_volume_flow_m3_s": runner_volume_flow_m3_s,
            "top_velocity_m_s": top_velocity_m_s,
            "bottom_velocity_m_s": bottom_velocity_m_s,
            "bottom_reynolds": reynolds_bottom,
            "bottom_mach": bottom_velocity_m_s / speed_of_sound_m_s,
            "ideal_kinetic_pressure_change_pa": ideal_kinetic_pressure_change_pa,
            "screening_contraction_loss_pa": contraction_loss_pa,
            "screening_flow_power_engine_w": contraction_loss_pa
            * total_volume_flow_m3_s,
            "engine_firing_frequency_hz": firing_frequency_hz,
            "runner_quarter_wave_hz": runner_quarter_wave_hz,
            "quarter_wave_to_firing_frequency_ratio": runner_quarter_wave_hz
            / firing_frequency_hz,
            "first_order_quarter_wave_length_mm": first_order_quarter_wave_length_mm,
            "side_runner_splay_deg": side_runner_splay_deg,
            "thin_wall_hoop_stress_mpa": hoop_stress_mpa,
            "ambient_yield_ratio": COMPARISON_YIELD_STRENGTH_MPA / hoop_stress_mpa,
            "free_thermal_expansion_mm": free_expansion_mm,
            "fully_constrained_elastic_thermal_stress_mpa": fully_constrained_stress_mpa,
            "lumped_heat_capacity_each_bank_j_k": mass_g
            / 1000.0
            * SPECIFIC_HEAT_J_KG_K,
        },
        "equations": {
            "frustum": "V=pi*L*(r0^2+r0*r1+r1^2)/3",
            "mass": "m=rho*V",
            "four_stroke_flow": "Q=Vd*N*eta_v/(2*60); Qrunner=Q/6",
            "continuity": "u=Q/A",
            "reynolds": "Re=rho*u*D/mu",
            "mach": "M=u/sqrt(gamma*R*T)",
            "kinetic_pressure": "delta_p_kin=rho*(u2^2-u1^2)/2",
            "minor_loss_screen": "delta_p_loss=K*rho*u2^2/2; P=delta_p_loss*Q",
            "firing_frequency": "f_fire=N/60*n_cyl/2",
            "quarter_wave": "f1=a/(4*L); L1=a/(4*f_fire)",
            "thin_wall_pressure": "sigma_hoop=p*r/t",
            "free_thermal_expansion": "delta_L=alpha*L*delta_T",
            "fully_constrained_thermal_stress": "sigma_th=E*alpha*delta_T",
            "heat_capacity": "C=m*cp",
        },
        "dfam_screen": {
            "part_consolidation": "three splayed tapered runners and two common flanges in one BREP",
            "open_flow_channels": 3,
            "trapped_powder_volume": False,
            "nominal_runner_wall_mm": RUNNER_WALL_MM,
            "mounting_holes_intentionally_absent": True,
            "machining_allowance_defined": False,
            "orientation_selected": False,
            "process_comparison_required": [
                "cast or CNC/fabricated aluminium manifold",
                "LPBF AlSi10Mg personalized runner manifold",
            ],
        },
        "interpretation": {
            "flow": "one-dimensional steady screen only; port pulsation, runner interaction, boundary layers, roughness and full plenum are absent",
            "acoustic": "100 mm quarter-wave result is not intake tuning because the complete runner, valve timing and reflection boundaries are absent",
            "mechanics": "thin-wall pressure only; flange bending, bolt preload, vibration, fatigue and backfire are absent",
            "thermal": "uniform delta-T screen only; head conduction, fuel film and transient heat soak are absent",
            "mass": "no commercial mass is published, so the calculated pair mass cannot validate the concept",
            "physicsnemo": "deferred until correlated CFD/CHT and structural cases with uncertainty and OOD gates exist",
            "simready": "deferred until ports, bolt pattern, installed environment and qualified material card are measured",
        },
        "release_blockers": [
            "No measured PMO part, cylinder-head ports, throttle interface, spacings, bolt pattern, gaskets, clearances or tolerances.",
            "The 46 x 42 x 100 mm string has no public drawing defining its datums or meaning.",
            "No commercial mass, aluminium grade, heat treatment, process or wall distribution.",
            "No measured M64 airflow, volumetric-efficiency map, valve timing, pressure pulses, temperature or acoustic boundary conditions.",
            "No qualified LPBF material card, surface condition, leak criterion or fuel compatibility assessment.",
            "No build orientation, supports, recoater check, machining stock or distortion compensation.",
            "No transient compressible CFD, conjugate heat transfer, modal, fatigue or backfire load case.",
            "No dimensional inspection, CT, pressure/leak bench, flow bench, thermal cycle, shaker or engine dyno test.",
            "No professional engine engineering review or approved validation plan.",
        ],
        "manufacturing_authorized": False,
        "engine_operation_authorized": False,
        "release_authorized": False,
    }


def _lofted_runner(
    bottom_radius_mm: float,
    top_radius_mm: float,
    lower_x_mm: float,
    upper_x_mm: float,
):
    from build123d import BuildSketch, Circle, Locations, Plane, loft

    with BuildSketch(Plane.XY) as lower:
        with Locations((lower_x_mm, LOWER_CENTER_Y_MM)):
            Circle(bottom_radius_mm)
    with BuildSketch(Plane.XY.offset(PUBLISHED_HEIGHT_MM)) as upper:
        with Locations((upper_x_mm, UPPER_CENTER_Y_MM)):
            Circle(top_radius_mm)
    return loft([lower.sketch, upper.sketch])


def build_solid():
    from build123d import Align, Box, Pos

    align_bottom = (Align.CENTER, Align.CENTER, Align.MIN)
    lower_flange = Box(
        FLANGE_X_MM, FLANGE_Y_MM, FLANGE_THICKNESS_MM, align=align_bottom
    )
    upper_flange = Pos(
        0.0, 0.0, PUBLISHED_HEIGHT_MM - FLANGE_THICKNESS_MM
    ) * Box(FLANGE_X_MM, FLANGE_Y_MM, FLANGE_THICKNESS_MM, align=align_bottom)
    solid = lower_flange + upper_flange
    inner_voids = []
    for lower_x, upper_x in zip(LOWER_CENTERS_X_MM, UPPER_CENTERS_X_MM):
        outer = _lofted_runner(
            PUBLISHED_BOTTOM_DIAMETER_MM / 2.0 + RUNNER_WALL_MM,
            PUBLISHED_TOP_DIAMETER_MM / 2.0 + RUNNER_WALL_MM,
            lower_x,
            upper_x,
        )
        inner = _lofted_runner(
            PUBLISHED_BOTTOM_DIAMETER_MM / 2.0,
            PUBLISHED_TOP_DIAMETER_MM / 2.0,
            lower_x,
            upper_x,
        )
        solid = solid + (outer - inner)
        inner_voids.append(inner)
    for inner in inner_voids:
        solid = solid - inner
    return solid


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    cad_volume_mm3 = None
    solid = None
    if args.out:
        from build123d import export_step, import_step

        solid = build_solid()
        if not solid.is_valid or len(solid.solids()) != 1:
            raise SystemExit("Le concept OCCT n'est pas un solide BREP unique valide.")
        bbox = solid.bounding_box()
        envelope = (bbox.size.X, bbox.size.Y, bbox.size.Z)
        expected_envelope = (FLANGE_X_MM, FLANGE_Y_MM, PUBLISHED_HEIGHT_MM)
        if any(
            abs(actual - target) > 0.01
            for actual, target in zip(envelope, expected_envelope)
        ):
            raise SystemExit(
                f"Enveloppe incohérente: OCCT={envelope}, cible F0={expected_envelope}"
            )

        args.out.parent.mkdir(parents=True, exist_ok=True)
        export_step(solid, str(args.out))
        roundtrip = import_step(str(args.out))
        if not roundtrip.is_valid or len(roundtrip.solids()) != 1:
            raise SystemExit("Le STEP relu n'est pas un solide BREP unique valide.")
        if abs(roundtrip.volume - solid.volume) > 0.05:
            raise SystemExit("Le STEP relu ne reproduit pas le volume OCCT attendu.")
        cad_volume_mm3 = roundtrip.volume

    report = engineering_screen(cad_volume_mm3)
    if solid is not None:
        report["step_roundtrip"] = {
            "status": "passed",
            "valid_brep": True,
            "solid_count": 1,
            "volume_mm3": cad_volume_mm3,
            "envelope_mm": [FLANGE_X_MM, FLANGE_Y_MM, PUBLISHED_HEIGHT_MM],
            "maximum_volume_delta_mm3": 0.05,
            "maximum_envelope_delta_mm": 0.01,
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
