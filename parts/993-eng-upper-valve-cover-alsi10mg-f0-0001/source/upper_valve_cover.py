#!/usr/bin/env python3
"""Couvre-culasse supérieur 993 AlSi10Mg, concept F0 avec tours COP."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


PART_ID = "993-ENG-UPPER-VALVE-COVER-ALSI10MG-F0-0001"

# Faits de catalogue ; dimensions et masse concernent le kit complet.
PUBLISHED_KIT_ENVELOPE_MM = [400.0, 150.0, 200.0]
PUBLISHED_KIT_MASS_KG = 3.32
PUBLISHED_COMMERCIAL_MATERIAL = "high_strength_billet_aluminium_unspecified_grade"
PUBLISHED_ALTERNATIVE_MATERIAL = "6061-T6_billet_aluminium"
OCR_UNVERIFIED_VALVE_COVER_TORQUE_NM = 9.7
OCR_UNVERIFIED_FASTENER_THREAD = "M6"

# Géométrie indépendante d'un seul cache supérieur.
LENGTH_MM = 220.0
WIDTH_MM = 95.0
SHELL_HEIGHT_MM = 25.0
ROOF_THICKNESS_MM = 3.0
SIDE_FLANGE_WIDTH_MM = 6.0
COP_TOWER_HEIGHT_MM = 20.0
COP_TOWER_OUTER_DIAMETER_MM = 24.0
COP_TOWER_BORE_DIAMETER_MM = 14.0
COP_TOWER_X_MM = (-70.0, 0.0, 70.0)
BOLT_BOSS_OUTER_DIAMETER_MM = 12.0
BOLT_BORE_DIAMETER_MM = 6.6
BOLT_X_MM = (-95.0, -47.5, 0.0, 47.5, 95.0)
BOLT_Y_MM = (-41.5, 41.5)
FIN_COUNT = 6
FIN_LENGTH_MM = 190.0
FIN_THICKNESS_MM = 2.5
FIN_HEIGHT_MM = 8.0
FIN_Y_MM = (-30.0, -18.0, -6.0, 6.0, 18.0, 30.0)

# EOS AlSi10Mg de criblage, valeurs génériques déjà bornées dans le projet.
DENSITY_KG_M3 = 2670.0
ELASTIC_MODULUS_PA = 70.0e9
POISSON_RATIO = 0.33
COMPARISON_YIELD_STRENGTH_PA = 245.0e6
THERMAL_EXPANSION_PER_K = 21.0e-6
SPECIFIC_HEAT_J_KG_K = 900.0
PUBLISHED_PROCESS_MINIMUM_WALL_MM = 0.4

# Cas synthétiques sans autorité véhicule.
CRANKCASE_PRESSURE_DIFFERENTIAL_PA = 20_000.0
UNSUPPORTED_ROOF_SPAN_MM = 45.0
NUT_FACTOR = 0.20
FASTENER_NOMINAL_DIAMETER_M = 0.006
SYNTHETIC_BOLT_COUNT = 10
LOCAL_GASKET_LEVER_ARM_MM = 6.0
LOCAL_FLANGE_EFFECTIVE_WIDTH_MM = 30.0
LOCAL_FLANGE_THICKNESS_MM = 6.0
OPERATING_COVER_TEMPERATURE_C = 200.0
REFERENCE_TEMPERATURE_C = 20.0
THROUGH_THICKNESS_GRADIENT_K = 50.0
MAXIMUM_SEAL_BOW_MM = 0.10
CONVECTION_COEFFICIENT_W_M2_K = 30.0
ENGINE_BAY_AIR_TEMPERATURE_C = 80.0
TARGET_REJECTED_HEAT_W = 300.0
MINIMUM_SCREEN_RATIO = 1.5


def engineering_screen(cad_volume_mm3: float | None = None) -> dict[str, object]:
    pressure_n_mm2 = CRANKCASE_PRESSURE_DIFFERENTIAL_PA / 1.0e6
    plate_stress_mpa = (
        0.75
        * pressure_n_mm2
        * UNSUPPORTED_ROOF_SPAN_MM**2
        / ROOF_THICKNESS_MM**2
    )
    plate_deflection_mm = (
        5.0
        * pressure_n_mm2
        * UNSUPPORTED_ROOF_SPAN_MM**4
        / (32.0 * (ELASTIC_MODULUS_PA / 1.0e6) * ROOF_THICKNESS_MM**3)
    )
    pressure_yield_ratio = COMPARISON_YIELD_STRENGTH_PA / 1.0e6 / plate_stress_mpa

    per_bolt_preload_n = OCR_UNVERIFIED_VALVE_COVER_TORQUE_NM / (
        NUT_FACTOR * FASTENER_NOMINAL_DIAMETER_M
    )
    total_preload_n = per_bolt_preload_n * SYNTHETIC_BOLT_COUNT
    inner_length_mm = LENGTH_MM - 2.0 * SIDE_FLANGE_WIDTH_MM
    inner_width_mm = WIDTH_MM - 2.0 * SIDE_FLANGE_WIDTH_MM
    gasket_band_area_mm2 = LENGTH_MM * WIDTH_MM - inner_length_mm * inner_width_mm
    average_gasket_pressure_mpa = total_preload_n / gasket_band_area_mm2
    gasket_band_yield_ratio = (
        COMPARISON_YIELD_STRENGTH_PA / 1.0e6 / average_gasket_pressure_mpa
    )
    local_moment_n_mm = per_bolt_preload_n * LOCAL_GASKET_LEVER_ARM_MM / 2.0
    local_second_moment_mm4 = (
        LOCAL_FLANGE_EFFECTIVE_WIDTH_MM * LOCAL_FLANGE_THICKNESS_MM**3 / 12.0
    )
    local_flange_stress_mpa = (
        local_moment_n_mm
        * (LOCAL_FLANGE_THICKNESS_MM / 2.0)
        / local_second_moment_mm4
    )
    local_flange_yield_ratio = (
        COMPARISON_YIELD_STRENGTH_PA / 1.0e6 / local_flange_stress_mpa
    )

    delta_temperature_k = OPERATING_COVER_TEMPERATURE_C - REFERENCE_TEMPERATURE_C
    free_thermal_growth_mm = THERMAL_EXPANSION_PER_K * LENGTH_MM * delta_temperature_k
    constrained_thermal_stress_pa = (
        ELASTIC_MODULUS_PA * THERMAL_EXPANSION_PER_K * delta_temperature_k
    )
    constrained_thermal_ratio = (
        COMPARISON_YIELD_STRENGTH_PA / constrained_thermal_stress_pa
    )
    thermal_curvature_per_m = (
        THERMAL_EXPANSION_PER_K
        * THROUGH_THICKNESS_GRADIENT_K
        / (ROOF_THICKNESS_MM / 1000.0)
    )
    thermal_bow_mm = (
        thermal_curvature_per_m * (LENGTH_MM / 1000.0) ** 2 / 8.0 * 1000.0
    )
    seal_bow_ratio = MAXIMUM_SEAL_BOW_MM / thermal_bow_mm

    projected_area_m2 = LENGTH_MM * WIDTH_MM / 1.0e6
    fin_area_m2 = 2.0 * FIN_LENGTH_MM * FIN_HEIGHT_MM * FIN_COUNT / 1.0e6
    tower_area_m2 = (
        len(COP_TOWER_X_MM)
        * math.pi
        * COP_TOWER_OUTER_DIAMETER_MM
        * COP_TOWER_HEIGHT_MM
        / 1.0e6
    )
    approximate_external_area_m2 = projected_area_m2 + fin_area_m2 + tower_area_m2
    convection_capacity_w = (
        CONVECTION_COEFFICIENT_W_M2_K
        * approximate_external_area_m2
        * (OPERATING_COVER_TEMPERATURE_C - ENGINE_BAY_AIR_TEMPERATURE_C)
    )
    heat_rejection_ratio = convection_capacity_w / TARGET_REJECTED_HEAT_W

    cad_mass_kg = (
        cad_volume_mm3 / 1.0e9 * DENSITY_KG_M3
        if cad_volume_mm3 is not None
        else None
    )
    billet_box_volume_mm3 = LENGTH_MM * WIDTH_MM * (
        SHELL_HEIGHT_MM + COP_TOWER_HEIGHT_MM
    )
    billet_box_mass_kg = billet_box_volume_mm3 / 1.0e9 * DENSITY_KG_M3
    projected_four_cover_mass_kg = cad_mass_kg * 4.0 if cad_mass_kg is not None else None
    lumped_heat_capacity_j_k = (
        cad_mass_kg * SPECIFIC_HEAT_J_KG_K if cad_mass_kg is not None else None
    )

    pressure_screen_pass = pressure_yield_ratio >= MINIMUM_SCREEN_RATIO
    clamp_screen_pass = (
        gasket_band_yield_ratio >= MINIMUM_SCREEN_RATIO
        and local_flange_yield_ratio >= MINIMUM_SCREEN_RATIO
    )
    thermal_screen_pass = (
        constrained_thermal_ratio >= MINIMUM_SCREEN_RATIO
        and seal_bow_ratio >= 1.0
        and heat_rejection_ratio >= 1.0
    )
    preliminary_screen_pass = (
        pressure_screen_pass and clamp_screen_pass and thermal_screen_pass
    )

    return {
        "schema_version": "1.0.0",
        "part_id": PART_ID,
        "status": "f0_clean_sheet_integrated_cop_cover_analytical_screen_failed",
        "geometry_authority": {
            "published": {
                "fvd_complete_kit_envelope_mm": PUBLISHED_KIT_ENVELOPE_MM,
                "fvd_complete_kit_mass_kg": PUBLISHED_KIT_MASS_KG,
                "fvd_material": PUBLISHED_COMMERCIAL_MATERIAL,
                "protomotive_alternative_material": PUBLISHED_ALTERNATIVE_MATERIAL,
                "torque_nm_ocr_unverified": OCR_UNVERIFIED_VALVE_COVER_TORQUE_NM,
                "fastener_thread_ocr_unverified": OCR_UNVERIFIED_FASTENER_THREAD,
            },
            "hypotheses": [
                "one 220 x 95 x 25 mm upper cover with open underside",
                "3 mm roof, 6 mm side flange and synthetic ten-bolt pattern",
                "three 24 mm OD coil-on-plug towers with 14 mm bores",
                "six external 190 x 2.5 x 8 mm fins",
                "no gasket surface, head interface, breather, oil baffle, wire route, seal or tolerance",
            ],
            "not_claimed": "The 400 x 150 x 200 mm and 3.32 kg describe a complete commercial kit, not this cover; no Porsche, FVD, Protomotive or BBi surface or fit is claimed.",
        },
        "synthetic_cases": {
            "crankcase_pressure_differential_pa": CRANKCASE_PRESSURE_DIFFERENTIAL_PA,
            "unsupported_roof_span_mm": UNSUPPORTED_ROOF_SPAN_MM,
            "nut_factor": NUT_FACTOR,
            "synthetic_bolt_count": SYNTHETIC_BOLT_COUNT,
            "operating_cover_temperature_c": OPERATING_COVER_TEMPERATURE_C,
            "through_thickness_gradient_k": THROUGH_THICKNESS_GRADIENT_K,
            "maximum_seal_bow_mm": MAXIMUM_SEAL_BOW_MM,
            "convection_coefficient_w_m2_k": CONVECTION_COEFFICIENT_W_M2_K,
            "target_rejected_heat_w": TARGET_REJECTED_HEAT_W,
            "minimum_screen_ratio": MINIMUM_SCREEN_RATIO,
            "authority": "regression inputs only; no measured crankcase pressure, surface temperature, gasket law, bolt preload, heat rejection, vibration or duty",
        },
        "material_screen": {
            "candidate": "EOS Aluminium AlSi10Mg LPBF T6 comparison",
            "density_kg_m3": DENSITY_KG_M3,
            "elastic_modulus_pa": ELASTIC_MODULUS_PA,
            "poisson_ratio": POISSON_RATIO,
            "comparison_yield_strength_pa": COMPARISON_YIELD_STRENGTH_PA,
            "thermal_expansion_per_k": THERMAL_EXPANSION_PER_K,
            "specific_heat_j_kg_k": SPECIFIC_HEAT_J_KG_K,
            "published_process_minimum_wall_mm": PUBLISHED_PROCESS_MINIMUM_WALL_MM,
            "scope": "generic project comparison values plus verified EOS T6 route; no hot gasket-flange fatigue, creep, porosity, oil, seal or flatness allowable",
        },
        "results": {
            "cad_volume_mm3": cad_volume_mm3,
            "cad_mass_g": cad_mass_kg * 1000.0 if cad_mass_kg is not None else None,
            "billet_box_mass_g": billet_box_mass_kg * 1000.0,
            "billet_box_to_cad_mass_ratio": billet_box_mass_kg / cad_mass_kg if cad_mass_kg else None,
            "projected_four_cover_mass_kg": projected_four_cover_mass_kg,
            "published_complete_kit_mass_kg": PUBLISHED_KIT_MASS_KG,
            "lumped_heat_capacity_j_k": lumped_heat_capacity_j_k,
            "roof_plate_stress_mpa": plate_stress_mpa,
            "roof_plate_deflection_mm": plate_deflection_mm,
            "ambient_yield_to_roof_pressure_ratio": pressure_yield_ratio,
            "per_bolt_preload_n_from_unverified_torque": per_bolt_preload_n,
            "total_preload_n_synthetic_pattern": total_preload_n,
            "gasket_band_area_mm2": gasket_band_area_mm2,
            "average_gasket_pressure_mpa": average_gasket_pressure_mpa,
            "ambient_yield_to_average_gasket_pressure_ratio": gasket_band_yield_ratio,
            "local_flange_stress_mpa": local_flange_stress_mpa,
            "ambient_yield_to_local_flange_stress_ratio": local_flange_yield_ratio,
            "free_thermal_growth_mm": free_thermal_growth_mm,
            "fully_constrained_thermal_stress_mpa": constrained_thermal_stress_pa / 1.0e6,
            "ambient_yield_to_constrained_thermal_ratio": constrained_thermal_ratio,
            "thermal_gradient_curvature_per_m": thermal_curvature_per_m,
            "thermal_bow_mm": thermal_bow_mm,
            "seal_bow_allowance_to_prediction_ratio": seal_bow_ratio,
            "approximate_external_area_m2": approximate_external_area_m2,
            "convection_capacity_w": convection_capacity_w,
            "convection_capacity_to_target_ratio": heat_rejection_ratio,
            "pressure_screen_pass": pressure_screen_pass,
            "clamp_screen_pass": clamp_screen_pass,
            "thermal_screen_pass": thermal_screen_pass,
            "preliminary_screen_pass": preliminary_screen_pass,
            "fatigue_and_seal_life_status": "not_computable_without_hot_material_gasket_preload_flatness_vibration_and_cycle_data",
        },
        "equations": {
            "roof_strip_stress": "sigma=0.75*p*a^2/t^2",
            "roof_strip_deflection": "w=5*p*a^4/(32*E*t^3)",
            "bolt_preload": "F=T/(K*d), OCR torque and K are not production inputs",
            "gasket_pressure": "p_gasket=sum(Fbolt)/A_band",
            "local_flange_bending": "M=Fbolt*e/2; I=b*t^3/12; sigma=M*(t/2)/I",
            "thermal_growth": "delta_L=alpha*L*delta_T",
            "constrained_thermal": "sigma=E*alpha*delta_T",
            "thermal_bow": "kappa=alpha*delta_T_through/t; w=kappa*L^2/8",
            "convection": "Q=h*A*(Tcover-Tair)",
            "mass_and_heat_capacity": "m=rho*V; C=m*cp",
        },
        "dfam_screen": {
            "additive_value": "open shell, external fins and three coil-on-plug towers consolidated without billet stock removal",
            "open_oil_side": True,
            "trapped_powder_volume": False,
            "integrated_cop_tower_count": len(COP_TOWER_X_MM),
            "integrated_fin_count": FIN_COUNT,
            "nominal_roof_mm": ROOF_THICKNESS_MM,
            "published_process_minimum_wall_mm": PUBLISHED_PROCESS_MINIMUM_WALL_MM,
            "roof_to_process_minimum_ratio": ROOF_THICKNESS_MM / PUBLISHED_PROCESS_MINIMUM_WALL_MM,
            "orientation_selected": False,
            "support_strategy_defined": False,
            "all_sealing_and_fastener_surfaces_require_machining": True,
            "process_comparison_required": [
                "qualified injection-moulded production cover",
                "CNC 6061-T6 billet cover",
                "cast aluminium cover",
                "LPBF AlSi10Mg integrated COP cover",
            ],
        },
        "interpretation": {
            "result": "pressure and clamp algebra pass; constrained growth, thermal bow and heat-rejection screens fail",
            "mass": "projecting one synthetic cover to four cannot validate the 3.32 kg commercial kit, which includes different parts, gaskets and hardware",
            "sealing": "flat-strip and average-contact algebra cannot predict gasket leakage or machined face distortion",
            "thermal": "uniform and gradient bounds omit oil splash, head conduction, radiation and vehicle airflow",
            "physicsnemo": "deferred until correlated CHT, structural, seal and durability datasets exist",
            "simready": "deferred until both upper/lower measured covers, heads, gaskets, coils, harnesses and clearances exist",
        },
        "release_blockers": [
            "No measured 993 upper cover, gasket contour, head datum, bolt pattern, sealing width, coil interface, breather or clearance.",
            "The published envelope and mass describe a four-cover kit with gaskets and hardware, not one cover.",
            "The F0 220 x 95 mm shell, ten bolts, fins and COP towers are entirely synthetic.",
            "No evidence that a production or commercial 993 cover uses AlSi10Mg or LPBF.",
            "The 9.7 Nm value is an unverified OCR transcription and the preload model assumes an arbitrary nut factor.",
            "No measured crankcase pressure, gasket law, clamp relaxation, fastener preload or leakage threshold.",
            "No measured cover/head/oil/air temperature, heat flux, radiation, convection or oil coking limit.",
            "The constrained thermal, bow and convection screens fail their regression criteria.",
            "No hot LPBF AlSi10Mg fatigue, creep, porosity, oil compatibility, corrosion or flatness allowables.",
            "No modal, vibration, engine-motion, thermal-cycle, seal-life or fastener-loosening model.",
            "No CHT, nonlinear contact/gasket FEA, mesh convergence or measured boundary correlation.",
            "No qualified orientation, supports, distortion compensation, T6, quench control, machining stock or anodizing route.",
            "No CT, FPI, metallurgy, dimensional inspection, flatness, pressure, leak, thermal-cycle, shaker or endurance test.",
            "No lower-cover, left/right, turbo-clearance, coil, harness, plug-wire or head integration evidence.",
            "No professional engine review, approved validation plan, dyno authorization or vehicle release.",
        ],
        "manufacturing_authorized": False,
        "engine_operation_authorized": False,
        "release_authorized": False,
    }


def build_geometry():
    from build123d import Align, Box, Cylinder, Pos

    centered_min = (Align.CENTER, Align.CENTER, Align.MIN)
    outer = Box(LENGTH_MM, WIDTH_MM, SHELL_HEIGHT_MM, align=centered_min)
    inner_length_mm = LENGTH_MM - 2.0 * SIDE_FLANGE_WIDTH_MM
    inner_width_mm = WIDTH_MM - 2.0 * SIDE_FLANGE_WIDTH_MM
    inner = Pos(0.0, 0.0, -1.0) * Box(
        inner_length_mm,
        inner_width_mm,
        SHELL_HEIGHT_MM - ROOF_THICKNESS_MM + 1.0,
        align=centered_min,
    )
    body = outer - inner

    for x_mm in BOLT_X_MM:
        for y_mm in BOLT_Y_MM:
            boss = Pos(x_mm, y_mm, 0.0) * Cylinder(
                BOLT_BOSS_OUTER_DIAMETER_MM / 2.0,
                8.0,
                align=centered_min,
            )
            body = body + boss
            bore = Pos(x_mm, y_mm, -1.0) * Cylinder(
                BOLT_BORE_DIAMETER_MM / 2.0,
                10.0,
                align=centered_min,
            )
            body = body - bore

    for y_mm in FIN_Y_MM:
        fin = Pos(0.0, y_mm, SHELL_HEIGHT_MM - 0.5) * Box(
            FIN_LENGTH_MM,
            FIN_THICKNESS_MM,
            FIN_HEIGHT_MM + 0.5,
            align=centered_min,
        )
        body = body + fin

    for x_mm in COP_TOWER_X_MM:
        tower = Pos(x_mm, 0.0, SHELL_HEIGHT_MM - 0.5) * Cylinder(
            COP_TOWER_OUTER_DIAMETER_MM / 2.0,
            COP_TOWER_HEIGHT_MM + 0.5,
            align=centered_min,
        )
        body = body + tower
        tower_bore = Pos(x_mm, 0.0, SHELL_HEIGHT_MM - ROOF_THICKNESS_MM - 1.0) * Cylinder(
            COP_TOWER_BORE_DIAMETER_MM / 2.0,
            COP_TOWER_HEIGHT_MM + ROOF_THICKNESS_MM + 2.0,
            align=centered_min,
        )
        body = body - tower_bore
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
            raise SystemExit("Le couvre-culasse F0 doit être un solide BREP unique valide.")
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
            "semantic_solids": ["clean_sheet_upper_valve_cover_integrated_cop_f0"],
            "volume_mm3": cad_volume_mm3,
            "envelope_mm": envelope,
            "open_oil_side_count": 1,
            "bolt_bore_count": len(BOLT_X_MM) * len(BOLT_Y_MM),
            "cop_tower_count": len(COP_TOWER_X_MM),
            "cop_through_bore_count": len(COP_TOWER_X_MM),
            "external_fin_count": FIN_COUNT,
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
