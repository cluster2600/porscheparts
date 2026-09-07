#!/usr/bin/env python3
"""Couvercle thermique de turbo 993, concept IN625 F0 indépendant."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


PART_ID = "993-ENG-TURBO-HEAT-SHIELD-IN625-F0-0001"

# Enveloppe et masse publiées par FVD pour 993 123 113 51.
PUBLISHED_LENGTH_MM = 160.0
PUBLISHED_WIDTH_MM = 110.0
PUBLISHED_HEIGHT_MM = 105.0
PUBLISHED_MASS_G = 230.0

# Coque ouverte propre au projet ; aucune interface OEM n'est revendiquée.
WALL_MM = 0.8
OUTER_PROFILE = (
    (0.0, 0.0),
    (0.0, 70.0),
    (25.0, 105.0),
    (85.0, 105.0),
    (110.0, 70.0),
    (110.0, 0.0),
)
INNER_PROFILE = (
    (WALL_MM, 0.0),
    (WALL_MM, 69.6),
    (25.4, 105.0 - WALL_MM),
    (84.6, 105.0 - WALL_MM),
    (110.0 - WALL_MM, 69.6),
    (110.0 - WALL_MM, 0.0),
)
BOSS_X_MM = (25.0, 80.0, 135.0)
BOSS_CENTER_Z_MM = 20.0
BOSS_RADIUS_MM = 6.0
BOSS_DEPTH_MM = 6.0
MOUNT_BORE_DIAMETER_MM = 5.0

# Cas synthétiques de régression, sans autorité véhicule.
SCREEN_FORCE_N = 50.0
SCREEN_SPAN_MM = 60.0
SCREEN_STRIP_WIDTH_MM = 40.0
HOT_SURFACE_K = 900.0
SHIELD_SURFACE_K = 650.0
AMBIENT_K = 350.0
REFERENCE_K = 293.0
EMISSIVITY_HYPOTHESIS = 0.8
STEFAN_BOLTZMANN = 5.670374419e-8

# Carte de criblage EOS M 290 40 µm + propriétés physiques corroyées Special Metals.
DENSITY_G_CM3 = 8.44
ELASTIC_MODULUS_MPA = 204_000.0
COMPARISON_YIELD_STRENGTH_MPA = 640.0
THERMAL_EXPANSION_PER_K = 13.7e-6
THERMAL_CONDUCTIVITY_W_MK = 15.7
SPECIFIC_HEAT_J_KG_K = 511.0


def polygon_area_mm2(points: tuple[tuple[float, float], ...]) -> float:
    return abs(
        sum(
            u0 * v1 - u1 * v0
            for (u0, v0), (u1, v1) in zip(points, points[1:] + points[:1])
        )
    ) / 2.0


def analytic_volume_mm3() -> float:
    shell = (
        polygon_area_mm2(OUTER_PROFILE) - polygon_area_mm2(INNER_PROFILE)
    ) * PUBLISHED_LENGTH_MM
    bosses = len(BOSS_X_MM) * math.pi * BOSS_RADIUS_MM**2 * BOSS_DEPTH_MM
    bore_depth = WALL_MM + BOSS_DEPTH_MM
    bores = (
        len(BOSS_X_MM)
        * math.pi
        * (MOUNT_BORE_DIAMETER_MM / 2.0) ** 2
        * bore_depth
    )
    return shell + bosses - bores


def exposed_arch_area_m2() -> float:
    arch_length_mm = 70.0 + math.hypot(25.0, 35.0) + 60.0
    arch_length_mm += math.hypot(25.0, 35.0) + 70.0
    return arch_length_mm * PUBLISHED_LENGTH_MM / 1_000_000.0


def engineering_screen(force_n: float = SCREEN_FORCE_N) -> dict[str, object]:
    if force_n <= 0:
        raise ValueError("La force de criblage doit être positive.")

    area_mm2 = SCREEN_STRIP_WIDTH_MM * WALL_MM
    second_moment_mm4 = SCREEN_STRIP_WIDTH_MM * WALL_MM**3 / 12.0
    moment_n_mm = force_n * SCREEN_SPAN_MM / 4.0
    bending_stress_mpa = moment_n_mm * (WALL_MM / 2.0) / second_moment_mm4
    center_deflection_mm = force_n * SCREEN_SPAN_MM**3 / (
        48.0 * ELASTIC_MODULUS_MPA * second_moment_mm4
    )
    mount_reaction_n = force_n / len(BOSS_X_MM)
    mount_bearing_mpa = mount_reaction_n / (
        MOUNT_BORE_DIAMETER_MM * (WALL_MM + BOSS_DEPTH_MM)
    )

    delta_t_k = SHIELD_SURFACE_K - REFERENCE_K
    free_expansion_mm = (
        THERMAL_EXPANSION_PER_K * PUBLISHED_LENGTH_MM * delta_t_k
    )
    fully_constrained_stress_mpa = (
        ELASTIC_MODULUS_MPA * THERMAL_EXPANSION_PER_K * delta_t_k
    )
    area_m2 = exposed_arch_area_m2()
    incident_flux_w_m2 = (
        EMISSIVITY_HYPOTHESIS
        * STEFAN_BOLTZMANN
        * (HOT_SURFACE_K**4 - SHIELD_SURFACE_K**4)
    )
    rejected_flux_w_m2 = (
        EMISSIVITY_HYPOTHESIS
        * STEFAN_BOLTZMANN
        * (SHIELD_SURFACE_K**4 - AMBIENT_K**4)
    )
    through_thickness_resistance_m2_k_w = (
        WALL_MM / 1000.0 / THERMAL_CONDUCTIVITY_W_MK
    )

    volume_mm3 = analytic_volume_mm3()
    mass_g = volume_mm3 / 1000.0 * DENSITY_G_CM3
    heat_capacity_j_k = mass_g / 1000.0 * SPECIFIC_HEAT_J_KG_K

    return {
        "schema_version": "1.0.0",
        "part_id": PART_ID,
        "status": "f0_published_envelope_clean_sheet_math_screen_only",
        "geometry_authority": {
            "published": [
                "commercial product envelope 160 x 110 x 105 mm",
                "commercial product mass 230 g",
            ],
            "catalogue_identity": ["99312311351"],
            "hypotheses": [
                "open trapezoidal vault profile",
                "0.8 mm nominal shell",
                "three integrated mounting bosses",
                "mounting bore positions and diameters",
            ],
            "not_claimed": "No OEM or FVD surface, interface or fitment geometry is claimed.",
        },
        "synthetic_cases": {
            "local_center_force_n": force_n,
            "strip_span_mm": SCREEN_SPAN_MM,
            "hot_surface_k": HOT_SURFACE_K,
            "shield_surface_k": SHIELD_SURFACE_K,
            "ambient_k": AMBIENT_K,
            "emissivity": EMISSIVITY_HYPOTHESIS,
            "authority": "regression inputs only; turbo temperatures, view factors, convection and vehicle loads absent",
        },
        "material_screen": {
            "candidate": "EOS NickelAlloy IN625 on M 290 40 µm, study only",
            "density_g_cm3": DENSITY_G_CM3,
            "elastic_modulus_mpa": ELASTIC_MODULUS_MPA,
            "comparison_yield_strength_mpa": COMPARISON_YIELD_STRENGTH_MPA,
            "thermal_expansion_per_k": THERMAL_EXPANSION_PER_K,
            "thermal_conductivity_w_mk": THERMAL_CONDUCTIVITY_W_MK,
            "specific_heat_j_kg_k": SPECIFIC_HEAT_J_KG_K,
            "scope": "EOS process values and Special Metals wrought thermal values are screening inputs, not a hot-design allowable card",
        },
        "results": {
            "analytic_volume_mm3": volume_mm3,
            "screening_mass_g": mass_g,
            "published_commercial_mass_g": PUBLISHED_MASS_G,
            "mass_ratio": mass_g / PUBLISHED_MASS_G,
            "strip_area_mm2": area_mm2,
            "strip_second_moment_mm4": second_moment_mm4,
            "maximum_bending_moment_n_mm": moment_n_mm,
            "nominal_bending_stress_mpa": bending_stress_mpa,
            "ambient_yield_ratio": COMPARISON_YIELD_STRENGTH_MPA / bending_stress_mpa,
            "linear_elastic_center_deflection_mm": center_deflection_mm,
            "mount_reaction_each_n": mount_reaction_n,
            "mount_average_bearing_mpa": mount_bearing_mpa,
            "free_thermal_expansion_mm": free_expansion_mm,
            "fully_constrained_elastic_thermal_stress_mpa": fully_constrained_stress_mpa,
            "exposed_arch_area_m2": area_m2,
            "incident_radiative_flux_w_m2": incident_flux_w_m2,
            "incident_radiative_power_w": incident_flux_w_m2 * area_m2,
            "outward_radiative_flux_w_m2": rejected_flux_w_m2,
            "outward_radiative_power_w": rejected_flux_w_m2 * area_m2,
            "through_thickness_resistance_m2_k_w": through_thickness_resistance_m2_k_w,
            "lumped_heat_capacity_j_k": heat_capacity_j_k,
        },
        "equations": {
            "volume": "V=(A_outer-A_inner)*L+n*pi*R_boss^2*d_boss-n*pi*R_hole^2*d_hole",
            "mass": "m=rho*V",
            "strip_section": "A=b*t; I=b*t^3/12",
            "simply_supported_center_load": "Mmax=F*L/4; delta=F*L^3/(48*E*I)",
            "bending_stress": "sigma=M*c/I",
            "bearing": "p=R/(d*t_effective)",
            "free_thermal_expansion": "delta_L=alpha*L*delta_T",
            "fully_constrained_thermal_stress": "sigma_th=E*alpha*delta_T",
            "radiation": "q=epsilon*sigma_SB*A*(T1^4-T2^4), view factor assumed 1",
            "thermal_resistance": "R_double_prime=t/k",
            "heat_capacity": "C=m*c_p",
        },
        "dfam_screen": {
            "part_consolidation": "vault and three local bosses in one BREP",
            "open_cavity": True,
            "trapped_powder_volume": False,
            "nominal_wall_mm": WALL_MM,
            "minimum_bore_diameter_mm": MOUNT_BORE_DIAMETER_MM,
            "machining_allowance_defined": False,
            "orientation_selected": False,
            "process_comparison_required": ["stamped or fabricated sheet", "LPBF IN625"],
        },
        "interpretation": {
            "mechanics": "flat-strip screen only; shell curvature, embossing, local modes and stress concentrations are absent",
            "thermal": "radiation-only scenario with assumed temperatures, emissivity and view factor; no convection or conjugate heat transfer",
            "constraint": "fully constrained stress is an upper-bound warning that demands compliant mounts, not a predicted vehicle stress",
            "mass": "the FVD material is unknown, so matching or exceeding its mass cannot validate the concept",
            "physicsnemo": "deferred until correlated thermal/structural CAE or test samples exist",
            "simready": "deferred until measured interfaces and qualified hot material properties exist",
        },
        "release_blockers": [
            "No measured cover, hot-side surface, mounting datums, hole pattern, clearances or tolerances.",
            "The published 160 x 110 x 105 mm values are only a commercial envelope.",
            "No measured turbo skin temperature, emissivity, view factor, airflow or protected-component limit.",
            "No vibration spectrum, fastener preload, service load, thermal cycle or fatigue target.",
            "No qualified hot LPBF material card, orientation, support strategy or minimum-wall capability.",
            "No oxidation, creep, thermal-fatigue, distortion or coating assessment.",
            "No nonlinear shell/contact FEA, modal analysis or conjugate heat-transfer solution.",
            "No dimensional inspection, thermal bench, shaker, endurance or vehicle fit test.",
            "No professional engineering review for an engine-bay thermal component.",
        ],
        "release_authorized": False,
    }


def build_solid():
    from build123d import Align, Cylinder, Plane, Polygon, Pos, Rot, extrude

    outer = extrude(Plane.YZ * Polygon(*OUTER_PROFILE), amount=PUBLISHED_LENGTH_MM)
    inner = extrude(Plane.YZ * Polygon(*INNER_PROFILE), amount=PUBLISHED_LENGTH_MM)
    solid = Pos(PUBLISHED_LENGTH_MM, 0.0, 0.0) * (outer - inner)

    centered = (Align.CENTER, Align.CENTER, Align.CENTER)
    for x_pos in BOSS_X_MM:
        boss_center_y = WALL_MM + BOSS_DEPTH_MM / 2.0
        boss = (
            Pos(x_pos, boss_center_y, BOSS_CENTER_Z_MM)
            * Rot(90.0, 0.0, 0.0)
            * Cylinder(BOSS_RADIUS_MM, BOSS_DEPTH_MM, align=centered)
        )
        solid = solid + boss
        bore_depth = WALL_MM + BOSS_DEPTH_MM
        bore = (
            Pos(x_pos, bore_depth / 2.0, BOSS_CENTER_Z_MM)
            * Rot(90.0, 0.0, 0.0)
            * Cylinder(MOUNT_BORE_DIAMETER_MM / 2.0, bore_depth, align=centered)
        )
        solid = solid - bore
    return solid


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--force-n", type=float, default=SCREEN_FORCE_N)
    args = parser.parse_args()

    report = engineering_screen(args.force_n)
    if args.out:
        from build123d import export_step, import_step

        solid = build_solid()
        expected_volume = analytic_volume_mm3()
        if not solid.is_valid or len(solid.solids()) != 1:
            raise SystemExit("Le concept OCCT n'est pas un solide BREP unique valide.")
        if abs(solid.volume - expected_volume) > 0.05:
            raise SystemExit(
                f"Volume incohérent: OCCT={solid.volume}, analytique={expected_volume}"
            )
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
        if (
            not roundtrip.is_valid
            or len(roundtrip.solids()) != 1
            or abs(roundtrip.volume - expected_volume) > 0.05
        ):
            raise SystemExit("Le STEP relu ne reproduit pas le solide attendu.")
        report["step_roundtrip"] = {
            "status": "passed",
            "valid_brep": True,
            "solid_count": 1,
            "volume_mm3": roundtrip.volume,
            "envelope_mm": list(envelope),
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
