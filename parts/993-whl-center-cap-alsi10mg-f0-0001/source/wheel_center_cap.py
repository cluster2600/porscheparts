#!/usr/bin/env python3
"""Cache-moyeu 993 AlSi10Mg F0, sans blason ni géométrie commerciale copiée."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


PART_ID = "993-WHL-CENTER-CAP-ALSI10MG-F0-0001"

# Dimensions et matière du produit d'origine déclarées par partworks.
PUBLISHED_OUTER_DIAMETER_MM = 76.0
PUBLISHED_INNER_DIAMETER_MM = 60.0
PUBLISHED_HEIGHT_MM = 46.0
PUBLISHED_ORIGINAL_MATERIAL = "plastic"

# Topologie métallique indépendante, entièrement paramétrique.
FACE_THICKNESS_MM = 2.0
FACE_Z_MM = PUBLISHED_HEIGHT_MM - FACE_THICKNESS_MM
OUTER_SKIRT_INNER_DIAMETER_MM = 73.0
OUTER_SKIRT_HEIGHT_MM = 12.0
OUTER_SKIRT_Z_MM = FACE_Z_MM - OUTER_SKIRT_HEIGHT_MM
CENTERING_RING_OUTER_DIAMETER_MM = 63.0
CENTERING_RING_HEIGHT_MM = FACE_Z_MM
TAB_COUNT = 4
TAB_RADIAL_THICKNESS_MM = 2.0
TAB_TANGENTIAL_WIDTH_MM = 8.0
TAB_LENGTH_MM = 30.0
TAB_Z_MM = FACE_Z_MM - TAB_LENGTH_MM
TAB_CENTER_RADIUS_MM = 27.0
BEAD_RADIAL_THICKNESS_MM = 2.0
BEAD_TANGENTIAL_WIDTH_MM = 8.0
BEAD_HEIGHT_MM = 4.0
BEAD_Z_MM = 11.0
BEAD_CENTER_RADIUS_MM = 28.5
TAB_BEAD_RADIAL_OVERLAP_MM = 0.5
TAB_BEAD_AXIAL_OVERLAP_MM = 1.0

# Cas de régression, pas exigences Porsche.
INSERTION_DEFLECTION_MM = 0.4
FRICTION_COEFFICIENT = 0.30
VEHICLE_SPEED_KMH = 250.0
TIRE_ROLLING_RADIUS_MM = 315.0
AXIAL_ACCELERATION_G = 20.0
GRAVITY_M_S2 = 9.80665
THERMAL_DELTA_T_K = 120.0
STEEL_WHEEL_EXPANSION_PER_K = 12.0e-6

# Carte générique ambiante AlSi10Mg de criblage uniquement.
DENSITY_G_CM3 = 2.67
ELASTIC_MODULUS_MPA = 70_000.0
POISSON_RATIO = 0.33
COMPARISON_YIELD_STRENGTH_MPA = 245.0
THERMAL_EXPANSION_PER_K = 21.0e-6


def analytic_volume_mm3() -> float:
    outer_radius = PUBLISHED_OUTER_DIAMETER_MM / 2.0
    skirt_inner_radius = OUTER_SKIRT_INNER_DIAMETER_MM / 2.0
    centering_outer_radius = CENTERING_RING_OUTER_DIAMETER_MM / 2.0
    centering_inner_radius = PUBLISHED_INNER_DIAMETER_MM / 2.0

    face = math.pi * outer_radius**2 * FACE_THICKNESS_MM
    skirt = math.pi * (
        outer_radius**2 - skirt_inner_radius**2
    ) * OUTER_SKIRT_HEIGHT_MM
    centering_ring = math.pi * (
        centering_outer_radius**2 - centering_inner_radius**2
    ) * CENTERING_RING_HEIGHT_MM
    tabs = (
        TAB_COUNT
        * TAB_RADIAL_THICKNESS_MM
        * TAB_TANGENTIAL_WIDTH_MM
        * TAB_LENGTH_MM
    )
    beads = (
        TAB_COUNT
        * BEAD_RADIAL_THICKNESS_MM
        * BEAD_TANGENTIAL_WIDTH_MM
        * BEAD_HEIGHT_MM
    )
    overlaps = (
        TAB_COUNT
        * TAB_BEAD_RADIAL_OVERLAP_MM
        * TAB_TANGENTIAL_WIDTH_MM
        * TAB_BEAD_AXIAL_OVERLAP_MM
    )
    return face + skirt + centering_ring + tabs + beads - overlaps


def tab_component_volume_mm3() -> float:
    tab = TAB_RADIAL_THICKNESS_MM * TAB_TANGENTIAL_WIDTH_MM * TAB_LENGTH_MM
    bead = BEAD_RADIAL_THICKNESS_MM * BEAD_TANGENTIAL_WIDTH_MM * BEAD_HEIGHT_MM
    overlap = (
        TAB_BEAD_RADIAL_OVERLAP_MM
        * TAB_TANGENTIAL_WIDTH_MM
        * TAB_BEAD_AXIAL_OVERLAP_MM
    )
    return tab + bead - overlap


def engineering_screen(insertion_deflection_mm: float = INSERTION_DEFLECTION_MM) -> dict[str, object]:
    if insertion_deflection_mm <= 0:
        raise ValueError("La flèche de clipsage doit être positive.")

    area_mm2 = TAB_TANGENTIAL_WIDTH_MM * TAB_RADIAL_THICKNESS_MM
    inertia_mm4 = (
        TAB_TANGENTIAL_WIDTH_MM * TAB_RADIAL_THICKNESS_MM**3 / 12.0
    )
    insertion_force_each_n = (
        3.0
        * ELASTIC_MODULUS_MPA
        * inertia_mm4
        * insertion_deflection_mm
        / TAB_LENGTH_MM**3
    )
    insertion_root_stress_mpa = (
        insertion_force_each_n
        * TAB_LENGTH_MM
        * (TAB_RADIAL_THICKNESS_MM / 2.0)
        / inertia_mm4
    )
    friction_retention_n = (
        TAB_COUNT * insertion_force_each_n * FRICTION_COEFFICIENT
    )

    volume_mm3 = analytic_volume_mm3()
    mass_g = volume_mm3 / 1000.0 * DENSITY_G_CM3
    axial_inertial_demand_n = (
        mass_g / 1000.0 * AXIAL_ACCELERATION_G * GRAVITY_M_S2
    )

    vehicle_speed_m_s = VEHICLE_SPEED_KMH / 3.6
    wheel_omega_rad_s = vehicle_speed_m_s / (TIRE_ROLLING_RADIUS_MM / 1000.0)
    tab_mass_kg = tab_component_volume_mm3() / 1_000_000.0 * DENSITY_G_CM3
    tab_effective_radius_m = TAB_CENTER_RADIUS_MM / 1000.0
    tab_centrifugal_force_n = (
        tab_mass_kg * wheel_omega_rad_s**2 * tab_effective_radius_m
    )
    distributed_load_n_mm = tab_centrifugal_force_n / TAB_LENGTH_MM
    centrifugal_root_moment_n_mm = (
        distributed_load_n_mm * TAB_LENGTH_MM**2 / 2.0
    )
    centrifugal_root_stress_mpa = (
        centrifugal_root_moment_n_mm
        * (TAB_RADIAL_THICKNESS_MM / 2.0)
        / inertia_mm4
    )
    centrifugal_tip_deflection_mm = (
        distributed_load_n_mm
        * TAB_LENGTH_MM**4
        / (8.0 * ELASTIC_MODULUS_MPA * inertia_mm4)
    )
    centering_mean_radius_m = (
        (CENTERING_RING_OUTER_DIAMETER_MM + PUBLISHED_INNER_DIAMETER_MM)
        / 4.0
        / 1000.0
    )
    ring_hoop_stress_mpa = (
        DENSITY_G_CM3
        * 1000.0
        * wheel_omega_rad_s**2
        * centering_mean_radius_m**2
        / 1_000_000.0
    )

    differential_growth_mm = (
        (THERMAL_EXPANSION_PER_K - STEEL_WHEEL_EXPANSION_PER_K)
        * PUBLISHED_INNER_DIAMETER_MM
        * THERMAL_DELTA_T_K
    )

    return {
        "schema_version": "1.0.0",
        "part_id": PART_ID,
        "status": "f0_published_envelope_clean_sheet_math_screen_only",
        "geometry_authority": {
            "published": [
                "commercial outer diameter 76 mm",
                "commercial inner diameter 60 mm",
                "commercial overall height 46 mm",
                "commercial original material plastic",
            ],
            "catalogue_identity": ["99336130307"],
            "hypotheses": [
                "blank 2 mm front face without Porsche marks",
                "outer skirt and separate centering ring",
                "four integral cantilever tabs and retention beads",
                "tab position, interference and wheel interface",
            ],
            "not_claimed": "No OEM face, emblem, clip or wheel-fit geometry is claimed.",
        },
        "synthetic_cases": {
            "insertion_deflection_mm": insertion_deflection_mm,
            "friction_coefficient": FRICTION_COEFFICIENT,
            "vehicle_speed_kmh": VEHICLE_SPEED_KMH,
            "tire_rolling_radius_mm": TIRE_ROLLING_RADIUS_MM,
            "axial_acceleration_g": AXIAL_ACCELERATION_G,
            "thermal_delta_t_k": THERMAL_DELTA_T_K,
            "authority": "regression inputs only; wheel bore, interference, friction, speed and road shock are not measured requirements",
        },
        "material_screen": {
            "candidate": "AlSi10Mg LPBF, room-temperature comparison only",
            "commercial_part_material": PUBLISHED_ORIGINAL_MATERIAL,
            "density_g_cm3": DENSITY_G_CM3,
            "elastic_modulus_mpa": ELASTIC_MODULUS_MPA,
            "poisson_ratio": POISSON_RATIO,
            "comparison_yield_strength_mpa": COMPARISON_YIELD_STRENGTH_MPA,
            "thermal_expansion_per_k": THERMAL_EXPANSION_PER_K,
            "scope": "generic screening values; the change from plastic to metal is not an equivalence claim",
        },
        "results": {
            "analytic_volume_mm3": volume_mm3,
            "screening_mass_each_g": mass_g,
            "screening_mass_set_of_four_g": 4.0 * mass_g,
            "tab_section_area_mm2": area_mm2,
            "tab_second_moment_mm4": inertia_mm4,
            "insertion_force_each_tab_n": insertion_force_each_n,
            "insertion_root_stress_mpa": insertion_root_stress_mpa,
            "ambient_yield_ratio": COMPARISON_YIELD_STRENGTH_MPA / insertion_root_stress_mpa,
            "friction_retention_capacity_n": friction_retention_n,
            "synthetic_axial_inertial_demand_n": axial_inertial_demand_n,
            "friction_retention_ratio": friction_retention_n / axial_inertial_demand_n,
            "wheel_angular_speed_rad_s": wheel_omega_rad_s,
            "tab_centrifugal_force_each_n": tab_centrifugal_force_n,
            "tab_centrifugal_root_stress_mpa": centrifugal_root_stress_mpa,
            "tab_centrifugal_tip_deflection_mm": centrifugal_tip_deflection_mm,
            "centering_ring_hoop_stress_mpa": ring_hoop_stress_mpa,
            "aluminium_minus_steel_diametral_growth_mm": differential_growth_mm,
        },
        "equations": {
            "volume": "sum of annular cylinders and rectangular tabs/beads minus explicit overlaps",
            "mass": "m=rho*V",
            "tab_section": "A=b*t; I=b*t^3/12",
            "cantilever_insertion": "F=3*E*I*delta/L^3; sigma=F*L*c/I",
            "friction_retention": "F_ret=n*mu*F_tab",
            "axial_inertia": "F=m*a_g*g",
            "wheel_speed": "omega=v/R_tire",
            "tab_centrifugal_force": "F=m_tab*omega^2*r_tab",
            "distributed_cantilever": "M_root=w*L^2/2; delta_tip=w*L^4/(8*E*I)",
            "rotating_thin_ring": "sigma_theta=rho*omega^2*r_mean^2",
            "differential_expansion": "delta_D=(alpha_Al-alpha_steel)*D*delta_T",
        },
        "dfam_screen": {
            "part_consolidation": "face, skirt, centering ring and four undercut retention tabs in one BREP",
            "open_internal_volume": True,
            "trapped_powder_volume": False,
            "minimum_nominal_wall_mm": min(FACE_THICKNESS_MM, TAB_RADIAL_THICKNESS_MM),
            "machining_allowance_defined": False,
            "orientation_selected": False,
            "process_comparison_required": ["MJF or SLS polymer", "injection molding", "LPBF AlSi10Mg", "CNC plus separate clips"],
        },
        "interpretation": {
            "retention": "linear four-tab friction screen only; real insertion curve, relaxation, wear and wheel geometry are absent",
            "rotation": "centrifugal screen covers tab and centering-ring expansion, not imbalance or axial ejection",
            "thermal": "uniform differential expansion versus hypothetical steel only; wheel alloy and gradients are unknown",
            "material_change": "metal may be heavier and less compliant than the declared plastic original; polymer AM may remain preferable",
            "physicsnemo": "deferred until spin, insertion and thermal datasets exist",
            "simready": "deferred until the wheel interface and retention law are measured",
        },
        "release_blockers": [
            "No measured wheel bore, cap section, clips, insertion direction, datums or tolerances.",
            "The published dimensions are commercial envelope values, not a production drawing.",
            "PorscheFanatics records historical PET status, not present fitment or availability.",
            "No measured insertion force, pull-off force, friction, relaxation, wear or corrosion stack.",
            "No qualified LPBF machine, orientation, heat treatment, surface state or fatigue curve.",
            "No wheel-speed, road-shock, imbalance, thermal-cycle or environmental requirement.",
            "No trademarked crest or Porsche face geometry is included or licensed.",
            "No dimensional inspection, spin bench, pull-off, impact, thermal-cycle or road test.",
            "No professional review of retention and external-object risk.",
        ],
        "release_authorized": False,
    }


def build_solid():
    from build123d import Align, Box, Cylinder, Pos, Rot

    axial = (Align.CENTER, Align.CENTER, Align.MIN)
    face = Pos(0.0, 0.0, FACE_Z_MM) * Cylinder(
        PUBLISHED_OUTER_DIAMETER_MM / 2.0,
        FACE_THICKNESS_MM,
        align=axial,
    )
    skirt = Pos(0.0, 0.0, OUTER_SKIRT_Z_MM) * (
        Cylinder(PUBLISHED_OUTER_DIAMETER_MM / 2.0, OUTER_SKIRT_HEIGHT_MM, align=axial)
        - Cylinder(OUTER_SKIRT_INNER_DIAMETER_MM / 2.0, OUTER_SKIRT_HEIGHT_MM, align=axial)
    )
    ring = Cylinder(
        CENTERING_RING_OUTER_DIAMETER_MM / 2.0,
        CENTERING_RING_HEIGHT_MM,
        align=axial,
    ) - Cylinder(
        PUBLISHED_INNER_DIAMETER_MM / 2.0,
        CENTERING_RING_HEIGHT_MM,
        align=axial,
    )
    solid = face + skirt + ring

    box_align = (Align.CENTER, Align.CENTER, Align.MIN)
    for index in range(TAB_COUNT):
        angle = index * 360.0 / TAB_COUNT
        tab = (
            Rot(0.0, 0.0, angle)
            * Pos(TAB_CENTER_RADIUS_MM, 0.0, TAB_Z_MM)
            * Box(
                TAB_RADIAL_THICKNESS_MM,
                TAB_TANGENTIAL_WIDTH_MM,
                TAB_LENGTH_MM,
                align=box_align,
            )
        )
        bead = (
            Rot(0.0, 0.0, angle)
            * Pos(BEAD_CENTER_RADIUS_MM, 0.0, BEAD_Z_MM)
            * Box(
                BEAD_RADIAL_THICKNESS_MM,
                BEAD_TANGENTIAL_WIDTH_MM,
                BEAD_HEIGHT_MM,
                align=box_align,
            )
        )
        solid = solid + tab + bead
    return solid


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--insertion-deflection-mm", type=float, default=INSERTION_DEFLECTION_MM)
    args = parser.parse_args()

    report = engineering_screen(args.insertion_deflection_mm)
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
            PUBLISHED_OUTER_DIAMETER_MM,
            PUBLISHED_OUTER_DIAMETER_MM,
            PUBLISHED_HEIGHT_MM,
        )
        if any(abs(a - b) > 0.01 for a, b in zip(envelope, expected_envelope)):
            raise SystemExit(
                f"Enveloppe incohérente: OCCT={envelope}, attendue={expected_envelope}"
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
