#!/usr/bin/env python3
"""Support d'impact avant 993, concept AlSi10Mg F0 non libérable."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


PART_ID = "993-BODY-FRONT-IMPACT-SUPPORT-ALSI10MG-F0-0001"

# Déclarations commerciales FVD, sans dessin ni protocole indépendant.
PUBLISHED_LENGTH_MM = 139.0
PUBLISHED_WIDTH_MM = 100.0
PUBLISHED_HEIGHT_MM = 53.0
PUBLISHED_MASS_G = 145.0

# Topologie F0 indépendante. Les interfaces de montage sont volontairement absentes.
BASE_PLATE_MM = 3.0
BODY_LENGTH_MM = PUBLISHED_LENGTH_MM - BASE_PLATE_MM
OUTER_A_MM = 30.0
OUTER_B_MM = 19.0
SHELL_MM = 1.2
CORE_SEGMENT_THICKNESSES_MM = (1.4, 1.2, 1.0, 0.8)
CORE_SEGMENT_LENGTH_MM = BODY_LENGTH_MM / len(CORE_SEGMENT_THICKNESSES_MM)

# Cas d'énergie synthétique : ce n'est ni une exigence réglementaire ni un essai 993.
SCREEN_MEAN_CRUSH_FORCE_N = 15_000.0
SCREEN_CRUSH_STROKE_MM = 80.0
SUPPORT_COUNT = 2
SCREEN_VEHICLE_MASS_KG = 1450.0
SCREEN_DELTA_T_K = 100.0

# Carte générique de criblage AlSi10Mg, non admissible crash.
DENSITY_G_CM3 = 2.67
ELASTIC_MODULUS_MPA = 70_000.0
POISSON_RATIO = 0.33
COMPARISON_YIELD_STRENGTH_MPA = 245.0
THERMAL_EXPANSION_PER_K = 21.0e-6
SPECIFIC_HEAT_J_KG_K = 900.0


def ellipse_annulus_area_mm2() -> float:
    return math.pi * (
        OUTER_A_MM * OUTER_B_MM
        - (OUTER_A_MM - SHELL_MM) * (OUTER_B_MM - SHELL_MM)
    )


def core_area_mm2(thickness_mm: float) -> float:
    if thickness_mm <= 0:
        raise ValueError("L'épaisseur du cœur doit être positive.")
    inner_width = 2.0 * (OUTER_A_MM - SHELL_MM)
    inner_height = 2.0 * (OUTER_B_MM - SHELL_MM)
    return (
        inner_width * thickness_mm
        + inner_height * thickness_mm
        - thickness_mm**2
    )


def analytic_volume_mm3() -> float:
    base = BASE_PLATE_MM * PUBLISHED_WIDTH_MM * PUBLISHED_HEIGHT_MM
    shell = ellipse_annulus_area_mm2() * BODY_LENGTH_MM
    graded_core = sum(
        core_area_mm2(thickness) * CORE_SEGMENT_LENGTH_MM
        for thickness in CORE_SEGMENT_THICKNESSES_MM
    )
    return base + shell + graded_core


def weak_axis_shell_inertia_mm4() -> float:
    inner_a = OUTER_A_MM - SHELL_MM
    inner_b = OUTER_B_MM - SHELL_MM
    return math.pi / 4.0 * (
        OUTER_A_MM * OUTER_B_MM**3 - inner_a * inner_b**3
    )


def plate_buckling_stress_mpa(
    thickness_mm: float,
    panel_width_mm: float,
    buckling_coefficient: float = 4.0,
) -> float:
    return (
        buckling_coefficient
        * math.pi**2
        * ELASTIC_MODULUS_MPA
        / (12.0 * (1.0 - POISSON_RATIO**2))
        * (thickness_mm / panel_width_mm) ** 2
    )


def engineering_screen(cad_volume_mm3: float | None = None) -> dict[str, object]:
    analytic_mm3 = analytic_volume_mm3()
    volume_mm3 = cad_volume_mm3 if cad_volume_mm3 is not None else analytic_mm3
    mass_g = volume_mm3 / 1000.0 * DENSITY_G_CM3

    front_core_t = CORE_SEGMENT_THICKNESSES_MM[-1]
    minimum_section_area_mm2 = ellipse_annulus_area_mm2() + core_area_mm2(
        front_core_t
    )
    nominal_axial_stress_mpa = SCREEN_MEAN_CRUSH_FORCE_N / minimum_section_area_mm2
    yield_force_upper_bound_n = (
        minimum_section_area_mm2 * COMPARISON_YIELD_STRENGTH_MPA
    )

    shell_panel_width_mm = 2.0 * (OUTER_B_MM - SHELL_MM)
    web_panel_width_mm = OUTER_A_MM - SHELL_MM
    shell_plate_buckling_mpa = plate_buckling_stress_mpa(
        SHELL_MM, shell_panel_width_mm
    )
    front_web_buckling_mpa = plate_buckling_stress_mpa(
        front_core_t, web_panel_width_mm
    )

    inertia_mm4 = weak_axis_shell_inertia_mm4()
    euler_force_n = (
        math.pi**2
        * ELASTIC_MODULUS_MPA
        * inertia_mm4
        / BODY_LENGTH_MM**2
    )
    shell_and_front_core_area_m2 = minimum_section_area_mm2 / 1_000_000.0
    shell_inertia_m4 = inertia_mm4 / 1.0e12
    body_length_m = BODY_LENGTH_MM / 1000.0
    bending_mode_hz = (
        1.875104**2
        / (2.0 * math.pi)
        * math.sqrt(
            ELASTIC_MODULUS_MPA
            * 1_000_000.0
            * shell_inertia_m4
            / (
                DENSITY_G_CM3
                * 1000.0
                * shell_and_front_core_area_m2
                * body_length_m**4
            )
        )
    )

    energy_each_j = SCREEN_MEAN_CRUSH_FORCE_N * SCREEN_CRUSH_STROKE_MM / 1000.0
    total_energy_j = energy_each_j * SUPPORT_COUNT
    equivalent_speed_m_s = math.sqrt(
        2.0 * total_energy_j / SCREEN_VEHICLE_MASS_KG
    )
    specific_energy_absorption_kj_kg = energy_each_j / (mass_g / 1000.0) / 1000.0
    free_thermal_expansion_mm = (
        THERMAL_EXPANSION_PER_K * PUBLISHED_LENGTH_MM * SCREEN_DELTA_T_K
    )

    return {
        "schema_version": "1.0.0",
        "part_id": PART_ID,
        "status": "f0_published_envelope_mass_clean_sheet_crash_screen_only",
        "geometry_authority": {
            "published": [
                "commercial product envelope 139 x 100 x 53 mm",
                "commercial product mass 145 g",
                "commercial material family aluminium, alloy not disclosed",
            ],
            "catalogue_identity": ["FVD50501700"],
            "hypotheses": [
                "3 mm solid rear plate without mounting holes",
                "60 x 38 mm open elliptic crush shell",
                "1.2 mm constant shell wall",
                "four axial core segments of equal length",
                "cruciform core graded from 1.4 to 0.8 mm",
                "no OEM bumper or body interface",
            ],
            "not_claimed": "No Porsche or FVD surface, mounting pattern, load path, crash performance or fitment is claimed.",
        },
        "synthetic_cases": {
            "mean_crush_force_each_n": SCREEN_MEAN_CRUSH_FORCE_N,
            "crush_stroke_mm": SCREEN_CRUSH_STROKE_MM,
            "support_count": SUPPORT_COUNT,
            "vehicle_mass_kg": SCREEN_VEHICLE_MASS_KG,
            "delta_t_k": SCREEN_DELTA_T_K,
            "authority": "regression inputs only; not a Porsche requirement, regulatory pulse, vehicle model or validated crash case",
        },
        "material_screen": {
            "candidate": "generic LPBF AlSi10Mg, study only",
            "density_g_cm3": DENSITY_G_CM3,
            "elastic_modulus_mpa": ELASTIC_MODULUS_MPA,
            "poisson_ratio": POISSON_RATIO,
            "comparison_yield_strength_mpa": COMPARISON_YIELD_STRENGTH_MPA,
            "thermal_expansion_per_k": THERMAL_EXPANSION_PER_K,
            "specific_heat_j_kg_k": SPECIFIC_HEAT_J_KG_K,
            "scope": "generic ambient screening values; no strain-rate, heat-treatment, orientation, defect or crash allowable",
        },
        "results": {
            "analytic_unclipped_volume_mm3": analytic_mm3,
            "cad_volume_mm3": volume_mm3,
            "cad_minus_analytic_volume_mm3": volume_mm3 - analytic_mm3,
            "screening_mass_g": mass_g,
            "published_mass_g": PUBLISHED_MASS_G,
            "mass_ratio_to_published": mass_g / PUBLISHED_MASS_G,
            "shell_annulus_area_mm2": ellipse_annulus_area_mm2(),
            "front_core_area_mm2": core_area_mm2(front_core_t),
            "minimum_section_area_mm2": minimum_section_area_mm2,
            "nominal_axial_stress_mpa": nominal_axial_stress_mpa,
            "ambient_yield_ratio": COMPARISON_YIELD_STRENGTH_MPA / nominal_axial_stress_mpa,
            "yield_force_upper_bound_n": yield_force_upper_bound_n,
            "mean_crush_to_yield_force_ratio": SCREEN_MEAN_CRUSH_FORCE_N
            / yield_force_upper_bound_n,
            "shell_flat_plate_buckling_stress_mpa": shell_plate_buckling_mpa,
            "front_web_flat_plate_buckling_stress_mpa": front_web_buckling_mpa,
            "weak_axis_shell_inertia_mm4": inertia_mm4,
            "global_euler_force_n": euler_force_n,
            "cantilever_shell_first_bending_mode_hz": bending_mode_hz,
            "synthetic_energy_each_j": energy_each_j,
            "synthetic_energy_two_supports_j": total_energy_j,
            "synthetic_equivalent_vehicle_speed_km_h": equivalent_speed_m_s * 3.6,
            "synthetic_specific_energy_absorption_kj_kg": specific_energy_absorption_kj_kg,
            "free_thermal_expansion_mm": free_thermal_expansion_mm,
            "lumped_heat_capacity_j_k": mass_g / 1000.0 * SPECIFIC_HEAT_J_KG_K,
        },
        "equations": {
            "ellipse_shell_area": "A=pi*(a*b-(a-t)*(b-t))",
            "cruciform_core_area": "Acore=w*t+h*t-t^2",
            "volume": "V=Vbase+Ashell*L+sum(Acore_i*L_i)",
            "mass": "m=rho*V",
            "nominal_axial": "sigma=F/A; F_y_upper=A*Rp0.2",
            "flat_plate_buckling": "sigma_cr=k*pi^2*E/(12*(1-nu^2))*(t/b)^2",
            "ellipse_weak_axis_inertia": "I=pi/4*(a*b^3-ai*bi^3)",
            "euler": "Pcr=pi^2*E*I/(K*L)^2 with K=1",
            "crush_energy": "E=Fmean*s; v_eq=sqrt(2*n*E/m_vehicle)",
            "specific_energy_absorption": "SEA=E/m_part",
            "cantilever_first_mode": "f1=1.875104^2/(2*pi)*sqrt(E*I/(rho*A*L^4))",
            "free_thermal_expansion": "delta_L=alpha*L*delta_T",
            "heat_capacity": "C=m*cp",
        },
        "dfam_screen": {
            "part_consolidation": "rear plate, elliptic shell and four graded cruciform core segments in one BREP",
            "open_crush_channels": 4,
            "trapped_powder_volume": False,
            "nominal_shell_mm": SHELL_MM,
            "minimum_core_wall_mm": front_core_t,
            "mounting_holes_intentionally_absent": True,
            "machining_allowance_defined": False,
            "orientation_selected": False,
            "process_comparison_required": [
                "fabricated or extruded aluminium support",
                "LPBF AlSi10Mg graded open-cell support",
            ],
        },
        "interpretation": {
            "crash": "F*s is an energy target only; it does not predict the force-displacement curve, pulse, intrusion or occupant response",
            "strength": "nominal yield and Euler results are upper bounds; thin-wall local folding, imperfections and joints govern crush",
            "buckling": "flat-plate estimates do not represent the nonlinear progressive folding of the oval shell and graded core",
            "modal": "equivalent cantilever shell mode excludes bumper beam, body attachment, ribs, joints and vehicle excitation",
            "mass": "near agreement with 145 g is a scalar screen only and cannot validate geometry or crash behavior",
            "physicsnemo": "deferred until a validated nonlinear explicit crash dataset with uncertainty and OOD gates exists",
            "simready": "deferred until measured interfaces, material cards, contact definitions and a correlated solver case exist",
        },
        "release_blockers": [
            "No measured support, body rail, bumper beam, mounting datums, holes, fasteners, clearances or tolerances.",
            "The 139 x 100 x 53 mm and 145 g values are commercial declarations, not a drawing or inspection report.",
            "The commercial aluminium alloy, temper, process, wall distribution and heat treatment are unknown.",
            "No vehicle variant mass, impact pulse, load distribution, barrier, intrusion or occupant criterion is defined.",
            "No strain-rate-dependent LPBF material card, anisotropy, fracture locus or defect population.",
            "No nonlinear explicit shell/contact model, mesh convergence, imperfection study or force-displacement target.",
            "No bumper-beam, longitudinal, body, fastener or adjacent-component model.",
            "No build orientation, support strategy, recoater check, machining stock or distortion compensation.",
            "No corrosion, galvanic, thermal-cycle, fatigue or road-debris assessment.",
            "No dimensional inspection, CT, coupon, quasi-static crush, dynamic sled or full-vehicle crash test.",
            "No professional crash engineering review or approved validation and homologation plan.",
        ],
        "manufacturing_authorized": False,
        "release_authorized": False,
    }


def build_solid():
    from build123d import Align, Box, BuildSketch, Ellipse, Plane, Pos, extrude

    align_min_x = (Align.MIN, Align.CENTER, Align.CENTER)
    base = Box(
        BASE_PLATE_MM,
        PUBLISHED_WIDTH_MM,
        PUBLISHED_HEIGHT_MM,
        align=align_min_x,
    )
    with BuildSketch(Plane.YZ) as outer_sketch:
        Ellipse(OUTER_A_MM, OUTER_B_MM)
    with BuildSketch(Plane.YZ) as inner_sketch:
        Ellipse(OUTER_A_MM - SHELL_MM, OUTER_B_MM - SHELL_MM)
    outer_body = Pos(BASE_PLATE_MM, 0.0, 0.0) * extrude(
        outer_sketch.sketch, amount=BODY_LENGTH_MM
    )
    inner_void = Pos(BASE_PLATE_MM, 0.0, 0.0) * extrude(
        inner_sketch.sketch, amount=BODY_LENGTH_MM
    )
    solid = base + (outer_body - inner_void)

    for index, thickness in enumerate(CORE_SEGMENT_THICKNESSES_MM):
        start_x = BASE_PLATE_MM + index * CORE_SEGMENT_LENGTH_MM
        horizontal = Pos(start_x, 0.0, 0.0) * Box(
            CORE_SEGMENT_LENGTH_MM,
            2.0 * OUTER_A_MM,
            thickness,
            align=align_min_x,
        )
        vertical = Pos(start_x, 0.0, 0.0) * Box(
            CORE_SEGMENT_LENGTH_MM,
            thickness,
            2.0 * OUTER_B_MM,
            align=align_min_x,
        )
        # Le cœur est borné par l'ellipse extérieure et reste ouvert en bout.
        solid = solid + ((horizontal + vertical) & outer_body)
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
        expected_envelope = (
            PUBLISHED_LENGTH_MM,
            PUBLISHED_WIDTH_MM,
            PUBLISHED_HEIGHT_MM,
        )
        if any(
            abs(actual - target) > 0.01
            for actual, target in zip(envelope, expected_envelope)
        ):
            raise SystemExit(
                f"Enveloppe incohérente: OCCT={envelope}, publiée={expected_envelope}"
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
            "envelope_mm": [
                PUBLISHED_LENGTH_MM,
                PUBLISHED_WIDTH_MM,
                PUBLISHED_HEIGHT_MM,
            ],
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
