#!/usr/bin/env python3
"""Conduite de retour d'huile turbo 993, concept IN625 F0 fail-closed."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


PART_ID = "993-ENG-TURBO-OIL-RETURN-LINE-IN625-F0-0001"

# La source publie seulement la fonction, le jeu gauche/droit et le fitment.
PUBLISHED_PRODUCT_REFERENCE = "TUR 993 107 338 53 PMS"
PUBLISHED_MODEL_YEARS = [1996, 1997]

# Géométrie propre au F0 ; aucune cote commerciale ou OEM n'est revendiquée.
TUBE_OUTER_DIAMETER_MM = 12.7
TUBE_WALL_MM = 1.2
TUBE_INNER_DIAMETER_MM = TUBE_OUTER_DIAMETER_MM - 2.0 * TUBE_WALL_MM
SYNTHETIC_CENTERLINE_LENGTH_MM = 175.0
SYNTHETIC_VERTICAL_RISE_MM = 90.0
FLANGE_DIAMETER_MM = 30.0
FLANGE_THICKNESS_MM = 4.0
FLANGE_BOLT_CENTERS_MM = 18.0
FLANGE_BORE_DIAMETER_MM = 6.0
CENTERLINE_CONTROL_POINTS = (
    (0.0, 0.0, 0.0),
    (0.0, 0.0, 24.0),
    (28.0, 0.0, 45.0),
    (72.0, 18.0, 47.0),
    (108.0, 30.0, 68.0),
    (110.0, 30.0, 90.0),
)

# Carte de comparaison EOS IN625 M290 40 um + référence thermique corroyée.
DENSITY_KG_M3 = 8440.0
ELASTIC_MODULUS_PA = 204.0e9
COMPARISON_YIELD_STRENGTH_PA = 640.0e6
THERMAL_EXPANSION_PER_K = 13.7e-6
THERMAL_CONDUCTIVITY_W_M_K = 15.7
SPECIFIC_HEAT_J_KG_K = 511.0
PUBLISHED_MINIMUM_WALL_MM = 0.4

# Cas hydrauliques, thermiques et mécaniques synthétiques de régression.
OIL_VOLUME_FLOW_L_MIN = 2.0
OIL_DENSITY_KG_M3 = 850.0
OIL_DYNAMIC_VISCOSITY_PA_S = 0.015
OIL_TEMPERATURE_C = 120.0
TUBE_EXTERNAL_TEMPERATURE_C = 600.0
REFERENCE_TEMPERATURE_C = 20.0
DESIGN_INTERNAL_PRESSURE_PA = 300_000.0
MINOR_LOSS_COEFFICIENT = 4.0
GRAVITY_M_S2 = 9.80665
MAX_SCREEN_PRESSURE_DROP_PA = 5000.0
TRANSVERSE_SCREEN_FORCE_N = 100.0
MOUNT_SPAN_MM = 120.0
MINIMUM_SCREEN_RATIO = 1.5


def hydraulic_screen() -> dict[str, float | str]:
    inner_diameter_m = TUBE_INNER_DIAMETER_MM / 1000.0
    length_m = SYNTHETIC_CENTERLINE_LENGTH_MM / 1000.0
    flow_m3_s = OIL_VOLUME_FLOW_L_MIN / 1000.0 / 60.0
    flow_area_m2 = math.pi * inner_diameter_m**2 / 4.0
    velocity_m_s = flow_m3_s / flow_area_m2
    reynolds = (
        OIL_DENSITY_KG_M3
        * velocity_m_s
        * inner_diameter_m
        / OIL_DYNAMIC_VISCOSITY_PA_S
    )
    regime = "laminar" if reynolds < 2300.0 else "non_laminar"
    darcy_factor = 64.0 / reynolds if regime == "laminar" else 0.3164 / reynolds**0.25
    dynamic_pressure_pa = OIL_DENSITY_KG_M3 * velocity_m_s**2 / 2.0
    straight_loss_pa = (
        darcy_factor * length_m / inner_diameter_m * dynamic_pressure_pa
    )
    minor_loss_pa = MINOR_LOSS_COEFFICIENT * dynamic_pressure_pa
    hydrostatic_head_pa = (
        OIL_DENSITY_KG_M3
        * GRAVITY_M_S2
        * SYNTHETIC_VERTICAL_RISE_MM
        / 1000.0
    )
    total_pressure_drop_pa = straight_loss_pa + minor_loss_pa + hydrostatic_head_pa
    return {
        "flow_m3_s": flow_m3_s,
        "flow_area_m2": flow_area_m2,
        "mean_velocity_m_s": velocity_m_s,
        "reynolds": reynolds,
        "flow_regime": regime,
        "darcy_friction_factor": darcy_factor,
        "dynamic_pressure_pa": dynamic_pressure_pa,
        "straight_friction_loss_pa": straight_loss_pa,
        "minor_loss_pa": minor_loss_pa,
        "hydrostatic_head_pa": hydrostatic_head_pa,
        "total_pressure_drop_pa": total_pressure_drop_pa,
        "pressure_drop_screen_ratio": MAX_SCREEN_PRESSURE_DROP_PA / total_pressure_drop_pa,
    }


def engineering_screen(cad_volume_mm3: float | None = None) -> dict[str, object]:
    hydraulic = hydraulic_screen()
    outer_diameter_m = TUBE_OUTER_DIAMETER_MM / 1000.0
    inner_diameter_m = TUBE_INNER_DIAMETER_MM / 1000.0
    wall_m = TUBE_WALL_MM / 1000.0

    hoop_stress_pa = DESIGN_INTERNAL_PRESSURE_PA * inner_diameter_m / (2.0 * wall_m)
    axial_stress_pa = DESIGN_INTERNAL_PRESSURE_PA * inner_diameter_m / (4.0 * wall_m)
    pressure_von_mises_pa = math.sqrt(
        hoop_stress_pa**2
        + axial_stress_pa**2
        - hoop_stress_pa * axial_stress_pa
    )
    pressure_ratio = COMPARISON_YIELD_STRENGTH_PA / pressure_von_mises_pa
    thin_wall_yield_burst_pressure_pa = (
        2.0 * TUBE_WALL_MM / TUBE_INNER_DIAMETER_MM * COMPARISON_YIELD_STRENGTH_PA
    )
    pressure_end_force_n = (
        DESIGN_INTERNAL_PRESSURE_PA * math.pi * inner_diameter_m**2 / 4.0
    )

    second_moment_mm4 = math.pi / 64.0 * (
        TUBE_OUTER_DIAMETER_MM**4 - TUBE_INNER_DIAMETER_MM**4
    )
    bending_moment_n_mm = TRANSVERSE_SCREEN_FORCE_N * MOUNT_SPAN_MM / 4.0
    bending_stress_mpa = (
        bending_moment_n_mm
        * (TUBE_OUTER_DIAMETER_MM / 2.0)
        / second_moment_mm4
    )
    combined_membrane_bending_mpa = pressure_von_mises_pa / 1.0e6 + bending_stress_mpa
    combined_ratio = (
        COMPARISON_YIELD_STRENGTH_PA / 1.0e6 / combined_membrane_bending_mpa
    )

    delta_temperature_k = TUBE_EXTERNAL_TEMPERATURE_C - REFERENCE_TEMPERATURE_C
    free_thermal_expansion_mm = (
        THERMAL_EXPANSION_PER_K
        * SYNTHETIC_CENTERLINE_LENGTH_MM
        * delta_temperature_k
    )
    fully_constrained_thermal_stress_pa = (
        ELASTIC_MODULUS_PA * THERMAL_EXPANSION_PER_K * delta_temperature_k
    )
    constrained_thermal_ratio = (
        COMPARISON_YIELD_STRENGTH_PA / fully_constrained_thermal_stress_pa
    )
    maximum_restraint_fraction_for_margin = (
        COMPARISON_YIELD_STRENGTH_PA
        / (MINIMUM_SCREEN_RATIO * fully_constrained_thermal_stress_pa)
    )

    conduction_resistance_k_w = math.log(
        outer_diameter_m / inner_diameter_m
    ) / (
        2.0
        * math.pi
        * THERMAL_CONDUCTIVITY_W_M_K
        * SYNTHETIC_CENTERLINE_LENGTH_MM
        / 1000.0
    )
    conduction_only_power_w = (
        TUBE_EXTERNAL_TEMPERATURE_C - OIL_TEMPERATURE_C
    ) / conduction_resistance_k_w

    cad_mass_kg = (
        cad_volume_mm3 / 1.0e9 * DENSITY_KG_M3
        if cad_volume_mm3 is not None
        else None
    )
    heat_capacity_j_k = (
        cad_mass_kg * SPECIFIC_HEAT_J_KG_K if cad_mass_kg is not None else None
    )
    hydraulic_pass = (
        hydraulic["pressure_drop_screen_ratio"] >= MINIMUM_SCREEN_RATIO
    )
    pressure_mechanical_pass = (
        pressure_ratio >= MINIMUM_SCREEN_RATIO
        and combined_ratio >= MINIMUM_SCREEN_RATIO
    )
    thermal_constraint_pass = constrained_thermal_ratio >= MINIMUM_SCREEN_RATIO
    preliminary_screen_pass = (
        hydraulic_pass and pressure_mechanical_pass and thermal_constraint_pass
    )

    return {
        "schema_version": "1.0.0",
        "part_id": PART_ID,
        "status": "f0_single_side_clean_sheet_analytical_screen_failed",
        "geometry_authority": {
            "published": {
                "product_reference": PUBLISHED_PRODUCT_REFERENCE,
                "model_years": PUBLISHED_MODEL_YEARS,
                "set_content": "left_and_right",
                "route": "oil_pump_to_reservoir",
                "functional_claim": "optimized_shape_against_oil_backflow",
                "installation_note": "engine_case_first_then_adjust_line_to_turbo",
            },
            "hypotheses": [
                "one-side 175 mm centerline with 90 mm rise and six spline control points",
                "12.7 mm OD, 1.2 mm wall and 10.3 mm ID",
                "two 30 x 4 mm circular flanges with synthetic two-bolt patterns",
                "the opposite side is neither mirrored nor claimed",
                "no vehicle route, sealing face, gasket, weld, clocking, clearance or tolerance",
            ],
            "not_claimed": "No Porsche or Patrick Motorsports surface, dimension, material, fit or hydraulic performance is claimed.",
        },
        "synthetic_cases": {
            "oil_volume_flow_l_min": OIL_VOLUME_FLOW_L_MIN,
            "oil_temperature_c": OIL_TEMPERATURE_C,
            "tube_external_temperature_c": TUBE_EXTERNAL_TEMPERATURE_C,
            "design_internal_pressure_pa": DESIGN_INTERNAL_PRESSURE_PA,
            "minor_loss_coefficient": MINOR_LOSS_COEFFICIENT,
            "maximum_screen_pressure_drop_pa": MAX_SCREEN_PRESSURE_DROP_PA,
            "transverse_center_force_n": TRANSVERSE_SCREEN_FORCE_N,
            "mount_span_mm": MOUNT_SPAN_MM,
            "minimum_screen_ratio": MINIMUM_SCREEN_RATIO,
            "authority": "regression inputs only; no measured K16 scavenge flow, pressure, oil state, temperature, vehicle route, loads or vibration",
        },
        "material_screen": {
            "candidate": "EOS NickelAlloy IN625 M290 40 micrometre comparison",
            "density_kg_m3": DENSITY_KG_M3,
            "comparison_yield_strength_pa": COMPARISON_YIELD_STRENGTH_PA,
            "elastic_modulus_pa": ELASTIC_MODULUS_PA,
            "thermal_expansion_per_k": THERMAL_EXPANSION_PER_K,
            "thermal_conductivity_w_m_k": THERMAL_CONDUCTIVITY_W_M_K,
            "specific_heat_j_kg_k": SPECIFIC_HEAT_J_KG_K,
            "published_minimum_wall_mm": PUBLISHED_MINIMUM_WALL_MM,
            "scope": "EOS process comparison plus wrought thermal properties; no hot thin-wall fatigue, oil compatibility, oxidation, weld or pressure allowable",
        },
        "results": {
            "cad_volume_mm3": cad_volume_mm3,
            "cad_mass_g": cad_mass_kg * 1000.0 if cad_mass_kg is not None else None,
            "lumped_heat_capacity_j_k": heat_capacity_j_k,
            "hydraulic": hydraulic,
            "hoop_stress_mpa": hoop_stress_pa / 1.0e6,
            "axial_stress_mpa": axial_stress_pa / 1.0e6,
            "pressure_von_mises_mpa": pressure_von_mises_pa / 1.0e6,
            "ambient_yield_to_pressure_ratio": pressure_ratio,
            "thin_wall_yield_burst_pressure_mpa": thin_wall_yield_burst_pressure_pa / 1.0e6,
            "pressure_end_force_n": pressure_end_force_n,
            "second_moment_mm4": second_moment_mm4,
            "bending_moment_n_mm": bending_moment_n_mm,
            "nominal_bending_stress_mpa": bending_stress_mpa,
            "combined_membrane_bending_mpa": combined_membrane_bending_mpa,
            "ambient_yield_to_combined_ratio": combined_ratio,
            "free_thermal_expansion_mm": free_thermal_expansion_mm,
            "fully_constrained_thermal_stress_mpa": fully_constrained_thermal_stress_pa / 1.0e6,
            "ambient_yield_to_constrained_thermal_ratio": constrained_thermal_ratio,
            "maximum_restraint_fraction_for_1p5_margin": maximum_restraint_fraction_for_margin,
            "wall_conduction_resistance_k_w": conduction_resistance_k_w,
            "conduction_only_power_w": conduction_only_power_w,
            "hydraulic_screen_pass": hydraulic_pass,
            "pressure_mechanical_screen_pass": pressure_mechanical_pass,
            "thermal_constraint_screen_pass": thermal_constraint_pass,
            "preliminary_screen_pass": preliminary_screen_pass,
            "fatigue_screen_status": "not_computable_without_pressure_temperature_vibration_cycles_and_hot_thin_wall_allowables",
        },
        "equations": {
            "continuity": "v=Q/A; A=pi*Di^2/4",
            "reynolds": "Re=rho*v*Di/mu",
            "darcy_laminar": "f=64/Re",
            "pressure_drop": "dp=f*L/Di*rho*v^2/2+K*rho*v^2/2+rho*g*dz",
            "thin_wall_pressure": "sigma_h=p*Di/(2t); sigma_a=p*Di/(4t)",
            "pressure_von_mises": "sigma_vm=sqrt(sigma_h^2+sigma_a^2-sigma_h*sigma_a)",
            "tube_bending": "I=pi*(Do^4-Di^4)/64; M=F*L/4; sigma=M*(Do/2)/I",
            "free_thermal_expansion": "delta_L=alpha*L*delta_T",
            "fully_constrained_thermal": "sigma_th=E*alpha*delta_T",
            "cylinder_conduction": "R=ln(Do/Di)/(2*pi*k*L); Qdot=delta_T/R",
            "heat_capacity": "C=m*cp",
        },
        "dfam_screen": {
            "additive_value": "single-piece curved thin-wall route with integrated flanges for low-volume obsolete fitment",
            "part_consolidation": "tube_and_two_flange_markers",
            "open_internal_channel": True,
            "trapped_powder_volume": False,
            "internal_supports_allowed": False,
            "nominal_wall_mm": TUBE_WALL_MM,
            "published_process_minimum_wall_mm": PUBLISHED_MINIMUM_WALL_MM,
            "wall_to_process_minimum_ratio": TUBE_WALL_MM / PUBLISHED_MINIMUM_WALL_MM,
            "minimum_internal_diameter_mm": TUBE_INNER_DIAMETER_MM,
            "orientation_selected": False,
            "support_strategy_defined": False,
            "installation_adjustability_conflict": "vendor requires final line adjustment; a rigid LPBF route needs measured datums or compliant interfaces",
            "process_comparison_required": [
                "bent and welded qualified stainless or nickel tube",
                "formed tube with brazed or welded flanges",
                "LPBF IN625 line with machined faces and verified powder removal",
            ],
        },
        "interpretation": {
            "result": "pressure and synthetic hydraulic screens pass, but full thermal restraint fails; the final-adjustment requirement also blocks a rigid printed route",
            "hydraulics": "one-phase laminar estimate; aerated oil, scavenge pump suction, pulsing and two-phase drainage are absent",
            "pressure": "thin-wall membrane and straight-tube bending omit elbows, flange roots, surface defects and residual stress",
            "thermal": "fully constrained stress and conduction-only power are bounds, not predicted vehicle values",
            "physicsnemo": "deferred until correlated two-phase CFD, thermal-structure and vibration datasets exist",
            "simready": "deferred until both measured routes, interfaces, surrounding geometry and clearances exist",
        },
        "release_blockers": [
            "No measured left or right line, flange datum, sealing face, bolt pattern, clocking, route, clearance or tolerance.",
            "The supplier explicitly requires final adjustment during installation; the rigid F0 cannot provide it.",
            "All tube and flange dimensions, the centerline and the 90 mm rise are synthetic.",
            "No evidence that the commercial line uses IN625, LPBF or an integrated tube-flange route.",
            "No measured oil flow, aeration, pressure, temperature, viscosity, drainage head, pump suction or pulsation.",
            "No two-phase oil-air CFD, bend-loss correlation, backflow model or scavenge-system integration.",
            "No measured turbo/exhaust temperature, heat flux, convection, radiation, shield or oil coking limit.",
            "The fully constrained thermal screen fails and the compliant support behavior is undefined.",
            "No vibration spectrum, engine motion, installation load, flange preload, thermal cycles or fatigue target.",
            "No hot thin-wall LPBF IN625 fatigue, oxidation, oil compatibility, roughness, defect or weld allowables.",
            "No qualified orientation, support, distortion compensation, heat treatment, HIP decision, machining or cleaning route.",
            "No proof that powder, supports and debris can be removed and verified from the complete internal passage.",
            "No CT, borescope, FPI, metallography, pressure proof, leak, burst, thermal-cycle, vibration or flow-bench test.",
            "No measured mirror/handed relationship or proof that one geometry covers both sides.",
            "No professional review, approved validation plan, engine-bench authorization or vehicle release.",
        ],
        "manufacturing_authorized": False,
        "turbo_operation_authorized": False,
        "engine_operation_authorized": False,
        "release_authorized": False,
    }


def _flange_at(x_mm: float, y_mm: float, z_mm: float):
    from build123d import Align, Cylinder, Pos

    flange = Pos(x_mm, y_mm, z_mm - FLANGE_THICKNESS_MM / 2.0) * Cylinder(
        FLANGE_DIAMETER_MM / 2.0,
        FLANGE_THICKNESS_MM,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    central_bore = Pos(x_mm, y_mm, z_mm - FLANGE_THICKNESS_MM) * Cylinder(
        TUBE_INNER_DIAMETER_MM / 2.0,
        2.0 * FLANGE_THICKNESS_MM,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    flange = flange - central_bore
    for offset_mm in (-FLANGE_BOLT_CENTERS_MM / 2.0, FLANGE_BOLT_CENTERS_MM / 2.0):
        bore = Pos(x_mm + offset_mm, y_mm, z_mm - FLANGE_THICKNESS_MM) * Cylinder(
            FLANGE_BORE_DIAMETER_MM / 2.0,
            2.0 * FLANGE_THICKNESS_MM,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )
        flange = flange - bore
    return flange


def build_geometry():
    from build123d import Circle, Spline, sweep

    path = Spline(
        *CENTERLINE_CONTROL_POINTS,
        tangents=((0.0, 0.0, 1.0), (0.0, 0.0, 1.0)),
        tangent_scalars=(1.2, 1.2),
    )
    outer = sweep((path ^ 0.0) * Circle(TUBE_OUTER_DIAMETER_MM / 2.0), path=path)
    inner = sweep((path ^ 0.0) * Circle(TUBE_INNER_DIAMETER_MM / 2.0), path=path)
    tube = outer - inner
    start = CENTERLINE_CONTROL_POINTS[0]
    end = CENTERLINE_CONTROL_POINTS[-1]
    return tube + _flange_at(*start) + _flange_at(*end)


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
            raise SystemExit("La conduite F0 doit contenir exactement un solide BREP valide.")
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
            "semantic_solids": ["clean_sheet_single_side_turbo_oil_return_line_in625_f0"],
            "volume_mm3": cad_volume_mm3,
            "envelope_mm": envelope,
            "tube_outer_diameter_mm": TUBE_OUTER_DIAMETER_MM,
            "tube_inner_diameter_mm": TUBE_INNER_DIAMETER_MM,
            "nominal_wall_mm": TUBE_WALL_MM,
            "flange_count": 2,
            "bolt_bore_count": 4,
            "continuous_internal_passage_count": 1,
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
