#!/usr/bin/env python3
"""Embout d'échappement 993 IN625, concept double paroi F0 indépendant."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


# Une seule geometrie, plusieurs metaux. Le conduit, la coque et les huit
# nervures ne changent pas d'un alliage a l'autre : ce qui change est la carte
# matiere et, seule question qui decide vraiment ici, le plafond de service.
MATERIALS = {
    "in625": {
        "part_id": "993-EXH-OVAL-TIP-IN625-F0-0001",
        "candidate": "EOS NickelAlloy IN625 on M 290 40 µm, study only",
        "density_g_cm3": 8.44,
        "elastic_modulus_mpa": 204_000.0,
        "comparison_yield_strength_mpa": 640.0,
        "thermal_expansion_per_k": 13.7e-6,
        "thermal_conductivity_w_mk": 15.7,
        "specific_heat_j_kg_k": 511.0,
        "creep_limited_ceiling_c": 980.0,
        "ceiling_basis": "superalliage nickel, tres au-dela du domaine de cet embout",
        "commodity": True,
    },
    "ti64": {
        "part_id": "993-EXH-OVAL-TIP-TI-F1-0001",
        "candidate": "EOS Titanium Ti64 on M 290 30 µm, heat treated coupons",
        "density_g_cm3": 4.41,
        "elastic_modulus_mpa": 110_000.0,
        "comparison_yield_strength_mpa": 945.0,
        "thermal_expansion_per_k": 8.6e-6,
        "thermal_conductivity_w_mk": 7.0,
        "specific_heat_j_kg_k": 560.0,
        "creep_limited_ceiling_c": 400.0,
        "ceiling_basis": "plafond de fluage couramment donne a 350-400 °C",
        "commodity": True,
    },
    "ti6242": {
        "part_id": "993-EXH-OVAL-TIP-TI-F1-0001",
        "candidate": "Ti-6Al-2Sn-4Zr-2Mo LPBF, route de recherche sans fournisseur",
        "density_g_cm3": 4.54,
        "elastic_modulus_mpa": 115_000.0,
        "comparison_yield_strength_mpa": 860.0,
        "thermal_expansion_per_k": 7.7e-6,
        "thermal_conductivity_w_mk": 6.9,
        "specific_heat_j_kg_k": 460.0,
        "creep_limited_ceiling_c": 550.0,
        "ceiling_basis": "nuance quasi-alpha developpee pour le fluage",
        "commodity": False,
    },
}

MATERIAL_KEY = "in625"
PART_ID = MATERIALS[MATERIAL_KEY]["part_id"]

# Seule l'enveloppe de sortie est publiée par FVD.
PUBLISHED_OUTLET_WIDTH_MM = 120.0
PUBLISHED_OUTLET_HEIGHT_MM = 85.0

# Dimensions F0 de criblage, sans autorité d'interface ou de montage.
CONCEPT_LENGTH_MM = 120.0
OUTER_INLET_RADIUS_MM = 33.0
OUTER_OUTLET_A_MM = PUBLISHED_OUTLET_WIDTH_MM / 2.0
OUTER_OUTLET_B_MM = PUBLISHED_OUTLET_HEIGHT_MM / 2.0
OUTER_WALL_MM = 0.8
INNER_SHELL_INLET_RADIUS_MM = 29.5
INNER_SHELL_OUTLET_A_MM = 55.5
INNER_SHELL_OUTLET_B_MM = 38.0
INNER_WALL_MM = 0.8
RIB_THICKNESS_MM = 1.0
RIB_LENGTH_MM = 12.0

# Cas synthétique : moteur 3,8 L, deux sorties, sans autorité véhicule.
ENGINE_DISPLACEMENT_L = 3.8
ENGINE_SPEED_RPM = 6500.0
VOLUMETRIC_EFFICIENCY = 0.95
OUTLET_COUNT = 2
INTAKE_REFERENCE_K = 300.0
EXHAUST_GAS_K = 850.0
REFERENCE_AIR_DENSITY_KG_M3 = 1.18
EXHAUST_DYNAMIC_VISCOSITY_PA_S = 4.0e-5
SCREEN_GAUGE_PRESSURE_PA = 30_000.0

# Cas thermique et modal synthétique.
TIP_SURFACE_K = 700.0
AMBIENT_K = 350.0
REFERENCE_K = 293.0
EMISSIVITY_HYPOTHESIS = 0.8
STEFAN_BOLTZMANN = 5.670374419e-8
MODAL_STRIP_WIDTH_MM = 20.0

# Carte de criblage active, fixee par --material. Les references corroyées et
# ambiantes restent des entrées de criblage, pas des admissibles chauds.
DENSITY_G_CM3 = MATERIALS[MATERIAL_KEY]["density_g_cm3"]
ELASTIC_MODULUS_MPA = MATERIALS[MATERIAL_KEY]["elastic_modulus_mpa"]
COMPARISON_YIELD_STRENGTH_MPA = MATERIALS[MATERIAL_KEY]["comparison_yield_strength_mpa"]
THERMAL_EXPANSION_PER_K = MATERIALS[MATERIAL_KEY]["thermal_expansion_per_k"]
THERMAL_CONDUCTIVITY_W_MK = MATERIALS[MATERIAL_KEY]["thermal_conductivity_w_mk"]
SPECIFIC_HEAT_J_KG_K = MATERIALS[MATERIAL_KEY]["specific_heat_j_kg_k"]


def select_material(key: str) -> None:
    """Bascule la carte matiere active avant tout calcul."""
    global MATERIAL_KEY, PART_ID, DENSITY_G_CM3, ELASTIC_MODULUS_MPA
    global COMPARISON_YIELD_STRENGTH_MPA, THERMAL_EXPANSION_PER_K
    global THERMAL_CONDUCTIVITY_W_MK, SPECIFIC_HEAT_J_KG_K
    if key not in MATERIALS:
        raise SystemExit(f"materiau inconnu: {key}")
    card = MATERIALS[key]
    MATERIAL_KEY = key
    PART_ID = card["part_id"]
    DENSITY_G_CM3 = card["density_g_cm3"]
    ELASTIC_MODULUS_MPA = card["elastic_modulus_mpa"]
    COMPARISON_YIELD_STRENGTH_MPA = card["comparison_yield_strength_mpa"]
    THERMAL_EXPANSION_PER_K = card["thermal_expansion_per_k"]
    THERMAL_CONDUCTIVITY_W_MK = card["thermal_conductivity_w_mk"]
    SPECIFIC_HEAT_J_KG_K = card["specific_heat_j_kg_k"]


def linear_ellipse_loft_volume_mm3(
    length_mm: float,
    a0_mm: float,
    b0_mm: float,
    a1_mm: float,
    b1_mm: float,
) -> float:
    """Intégrale de pi*a(z)*b(z) pour des demi-axes linéaires."""
    da = a1_mm - a0_mm
    db = b1_mm - b0_mm
    return math.pi * length_mm * (
        a0_mm * b0_mm
        + (a0_mm * db + b0_mm * da) / 2.0
        + da * db / 3.0
    )


def unribbed_shell_volume_mm3() -> float:
    outer = linear_ellipse_loft_volume_mm3(
        CONCEPT_LENGTH_MM,
        OUTER_INLET_RADIUS_MM,
        OUTER_INLET_RADIUS_MM,
        OUTER_OUTLET_A_MM,
        OUTER_OUTLET_B_MM,
    )
    outer_void = linear_ellipse_loft_volume_mm3(
        CONCEPT_LENGTH_MM,
        OUTER_INLET_RADIUS_MM - OUTER_WALL_MM,
        OUTER_INLET_RADIUS_MM - OUTER_WALL_MM,
        OUTER_OUTLET_A_MM - OUTER_WALL_MM,
        OUTER_OUTLET_B_MM - OUTER_WALL_MM,
    )
    inner = linear_ellipse_loft_volume_mm3(
        CONCEPT_LENGTH_MM,
        INNER_SHELL_INLET_RADIUS_MM,
        INNER_SHELL_INLET_RADIUS_MM,
        INNER_SHELL_OUTLET_A_MM,
        INNER_SHELL_OUTLET_B_MM,
    )
    inner_void = linear_ellipse_loft_volume_mm3(
        CONCEPT_LENGTH_MM,
        INNER_SHELL_INLET_RADIUS_MM - INNER_WALL_MM,
        INNER_SHELL_INLET_RADIUS_MM - INNER_WALL_MM,
        INNER_SHELL_OUTLET_A_MM - INNER_WALL_MM,
        INNER_SHELL_OUTLET_B_MM - INNER_WALL_MM,
    )
    return outer - outer_void + inner - inner_void


def ellipse_area_m2(a_mm: float, b_mm: float) -> float:
    return math.pi * a_mm * b_mm / 1_000_000.0


def ellipse_perimeter_mm(a_mm: float, b_mm: float) -> float:
    # Approximation de Ramanujan II.
    h = ((a_mm - b_mm) / (a_mm + b_mm)) ** 2
    return math.pi * (a_mm + b_mm) * (
        1.0 + 3.0 * h / (10.0 + math.sqrt(4.0 - 3.0 * h))
    )


def engineering_screen(cad_volume_mm3: float | None = None) -> dict[str, object]:
    inlet_radius_m = (INNER_SHELL_INLET_RADIUS_MM - INNER_WALL_MM) / 1000.0
    outlet_a_m = (INNER_SHELL_OUTLET_A_MM - INNER_WALL_MM) / 1000.0
    outlet_b_m = (INNER_SHELL_OUTLET_B_MM - INNER_WALL_MM) / 1000.0
    inlet_area_m2 = math.pi * inlet_radius_m**2
    outlet_area_m2 = math.pi * outlet_a_m * outlet_b_m

    cold_volume_flow_m3_s = (
        ENGINE_DISPLACEMENT_L
        / 1000.0
        * ENGINE_SPEED_RPM
        / (2.0 * 60.0)
        * VOLUMETRIC_EFFICIENCY
        / OUTLET_COUNT
    )
    hot_volume_flow_m3_s = (
        cold_volume_flow_m3_s * EXHAUST_GAS_K / INTAKE_REFERENCE_K
    )
    inlet_velocity_m_s = hot_volume_flow_m3_s / inlet_area_m2
    outlet_velocity_m_s = hot_volume_flow_m3_s / outlet_area_m2
    hot_density_kg_m3 = (
        REFERENCE_AIR_DENSITY_KG_M3 * INTAKE_REFERENCE_K / EXHAUST_GAS_K
    )
    expansion_loss_coefficient = (1.0 - inlet_area_m2 / outlet_area_m2) ** 2
    expansion_pressure_loss_pa = (
        expansion_loss_coefficient
        * 0.5
        * hot_density_kg_m3
        * inlet_velocity_m_s**2
    )
    flow_power_w = expansion_pressure_loss_pa * hot_volume_flow_m3_s
    hydraulic_diameter_m = 2.0 * inlet_radius_m
    inlet_reynolds = (
        hot_density_kg_m3
        * inlet_velocity_m_s
        * hydraulic_diameter_m
        / EXHAUST_DYNAMIC_VISCOSITY_PA_S
    )

    effective_radius_m = OUTER_INLET_RADIUS_MM / 1000.0
    wall_m = OUTER_WALL_MM / 1000.0
    thin_wall_hoop_stress_mpa = (
        SCREEN_GAUGE_PRESSURE_PA * effective_radius_m / wall_m / 1_000_000.0
    )
    axial_pressure_force_n = SCREEN_GAUGE_PRESSURE_PA * inlet_area_m2

    delta_t_k = TIP_SURFACE_K - REFERENCE_K
    free_expansion_mm = (
        THERMAL_EXPANSION_PER_K * CONCEPT_LENGTH_MM * delta_t_k
    )
    fully_constrained_stress_mpa = (
        ELASTIC_MODULUS_MPA * THERMAL_EXPANSION_PER_K * delta_t_k
    )
    inlet_perimeter_mm = 2.0 * math.pi * OUTER_INLET_RADIUS_MM
    outlet_perimeter_mm = ellipse_perimeter_mm(
        OUTER_OUTLET_A_MM, OUTER_OUTLET_B_MM
    )
    lateral_area_m2 = (
        (inlet_perimeter_mm + outlet_perimeter_mm)
        / 2.0
        * CONCEPT_LENGTH_MM
        / 1_000_000.0
    )
    outward_radiative_flux_w_m2 = (
        EMISSIVITY_HYPOTHESIS
        * STEFAN_BOLTZMANN
        * (TIP_SURFACE_K**4 - AMBIENT_K**4)
    )

    strip_b_m = MODAL_STRIP_WIDTH_MM / 1000.0
    strip_t_m = OUTER_WALL_MM / 1000.0
    strip_area_m2 = strip_b_m * strip_t_m
    strip_i_m4 = strip_b_m * strip_t_m**3 / 12.0
    length_m = CONCEPT_LENGTH_MM / 1000.0
    first_mode_hz = (
        1.875104**2
        / (2.0 * math.pi)
        * math.sqrt(
            ELASTIC_MODULUS_MPA
            * 1_000_000.0
            * strip_i_m4
            / (DENSITY_G_CM3 * 1000.0 * strip_area_m2 * length_m**4)
        )
    )

    estimate_mm3 = unribbed_shell_volume_mm3()
    volume_mm3 = cad_volume_mm3 if cad_volume_mm3 is not None else estimate_mm3
    mass_g = volume_mm3 / 1000.0 * DENSITY_G_CM3

    return {
        "schema_version": "1.0.0",
        "part_id": PART_ID,
        "status": "f0_published_outlet_envelope_clean_sheet_math_screen_only",
        "geometry_authority": {
            "published": ["commercial outlet envelope 120 x 85 mm"],
            "catalogue_identity": ["FVD11199300"],
            "hypotheses": [
                "120 mm axial length",
                "66 mm round outer inlet",
                "56.6 mm round flow inlet",
                "0.8 mm outer and inner walls",
                "four inlet and four outlet radial ties",
                "linearly lofted round-to-oval profiles",
            ],
            "not_claimed": "No Porsche or FVD interface, surface, length, wall, tolerance or fitment geometry is claimed.",
        },
        "synthetic_cases": {
            "engine_displacement_l": ENGINE_DISPLACEMENT_L,
            "engine_speed_rpm": ENGINE_SPEED_RPM,
            "volumetric_efficiency": VOLUMETRIC_EFFICIENCY,
            "outlet_count": OUTLET_COUNT,
            "exhaust_gas_k": EXHAUST_GAS_K,
            "tip_surface_k": TIP_SURFACE_K,
            "screen_gauge_pressure_pa": SCREEN_GAUGE_PRESSURE_PA,
            "authority": "regression inputs only; no measured engine flow, pressure, temperature, pulse spectrum or vehicle duty cycle",
        },
        "material_screen": {
            "candidate": MATERIALS[MATERIAL_KEY]["candidate"],
            "density_g_cm3": DENSITY_G_CM3,
            "elastic_modulus_mpa": ELASTIC_MODULUS_MPA,
            "comparison_yield_strength_mpa": COMPARISON_YIELD_STRENGTH_MPA,
            "thermal_expansion_per_k": THERMAL_EXPANSION_PER_K,
            "thermal_conductivity_w_mk": THERMAL_CONDUCTIVITY_W_MK,
            "specific_heat_j_kg_k": SPECIFIC_HEAT_J_KG_K,
            "scope": "ambient and wrought references are screening inputs, not hot LPBF design allowables",
        },
        "temperature_screen": {
            "declared_tip_surface_c": TIP_SURFACE_K - 273.15,
            "declared_tip_surface_authority": "synthetic screening input, never measured on a vehicle",
            "alloy_creep_limited_ceiling_c": MATERIALS[MATERIAL_KEY]["creep_limited_ceiling_c"],
            "ceiling_basis": MATERIALS[MATERIAL_KEY]["ceiling_basis"],
            "margin_c": MATERIALS[MATERIAL_KEY]["creep_limited_ceiling_c"] - (TIP_SURFACE_K - 273.15),
            "alloy_adequate_at_declared_temperature": (
                MATERIALS[MATERIAL_KEY]["creep_limited_ceiling_c"] >= TIP_SURFACE_K - 273.15
            ),
            "commodity_supply": MATERIALS[MATERIAL_KEY]["commodity"],
            "interpretation": (
                "Le verdict depend entierement d'une temperature synthetique. "
                "Une mesure au thermometre infrarouge sur la sortie reelle, apres "
                "roulage, deplacerait la reponse plus surement que n'importe quel "
                "calcul de ce fichier."
            ),
        },
        "results": {
            "unribbed_linear_loft_volume_mm3": estimate_mm3,
            "cad_volume_mm3": volume_mm3,
            "cad_minus_unribbed_volume_mm3": volume_mm3 - estimate_mm3,
            "screening_mass_g": mass_g,
            "inlet_flow_area_m2": inlet_area_m2,
            "outlet_flow_area_m2": outlet_area_m2,
            "cold_volume_flow_each_m3_s": cold_volume_flow_m3_s,
            "hot_volume_flow_each_m3_s": hot_volume_flow_m3_s,
            "hot_density_kg_m3": hot_density_kg_m3,
            "inlet_velocity_m_s": inlet_velocity_m_s,
            "outlet_velocity_m_s": outlet_velocity_m_s,
            "inlet_reynolds": inlet_reynolds,
            "borda_carnot_loss_coefficient": expansion_loss_coefficient,
            "borda_carnot_pressure_loss_pa": expansion_pressure_loss_pa,
            "screening_flow_power_w": flow_power_w,
            "thin_wall_hoop_stress_mpa": thin_wall_hoop_stress_mpa,
            "axial_pressure_force_n": axial_pressure_force_n,
            "free_thermal_expansion_mm": free_expansion_mm,
            "fully_constrained_elastic_thermal_stress_mpa": fully_constrained_stress_mpa,
            "outer_lateral_area_m2": lateral_area_m2,
            "outward_radiative_flux_w_m2": outward_radiative_flux_w_m2,
            "outward_radiative_power_w": outward_radiative_flux_w_m2 * lateral_area_m2,
            "outer_wall_through_thickness_resistance_m2_k_w": wall_m / THERMAL_CONDUCTIVITY_W_MK,
            "lumped_heat_capacity_j_k": mass_g / 1000.0 * SPECIFIC_HEAT_J_KG_K,
            "cantilever_strip_first_mode_hz": first_mode_hz,
        },
        "equations": {
            "linear_ellipse_loft": "V=pi*L*(a0*b0+(a0*db+b0*da)/2+da*db/3)",
            "mass": "m=rho*V",
            "four_stroke_flow": "Qcold=Vd*N*eta_v/(2*60*n_out); Qhot=Qcold*Thot/Tref",
            "continuity": "u=Q/A",
            "hot_density": "rho_hot=rho_ref*Tref/Thot",
            "reynolds": "Re=rho*u*Dh/mu",
            "sudden_expansion_screen": "K=(1-A1/A2)^2; delta_p=K*rho*u1^2/2; P=delta_p*Q",
            "thin_wall_pressure": "sigma_hoop=p*r/t; Faxial=p*Ain",
            "free_thermal_expansion": "delta_L=alpha*L*delta_T",
            "fully_constrained_thermal_stress": "sigma_th=E*alpha*delta_T",
            "ellipse_perimeter": "Ramanujan II",
            "radiation": "q=epsilon*sigma_SB*A*(Ttip^4-Tamb^4)",
            "thermal_resistance": "R_double_prime=t/k",
            "cantilever_first_mode": "f1=1.875104^2/(2*pi)*sqrt(E*I/(rho*A*L^4))",
        },
        "dfam_screen": {
            "part_consolidation": "inner duct, outer shroud and eight radial ties in one BREP",
            "open_annular_channel": True,
            "trapped_powder_volume": False,
            "nominal_wall_mm": OUTER_WALL_MM,
            "minimum_open_gap_mm": 2.7,
            "machining_allowance_defined": False,
            "orientation_selected": False,
            "process_comparison_required": [
                "hydroformed or fabricated stainless tip",
                "LPBF IN625 double-wall concept",
            ],
        },
        "interpretation": {
            "flow": "steady ideal-gas and abrupt-expansion screen; pulses, bends, roughness, heat transfer and upstream exhaust are absent",
            "mechanics": "thin-wall membrane and equivalent-strip mode only; joints, oval-shell modes and fatigue are absent",
            "thermal": "uniform assumed surface temperature and radiation only; no convection, CHT, oxidation or thermal cycling",
            "constraint": "fully constrained stress is a warning that demands a sliding interface, not a predicted vehicle stress",
            "material": "PorscheFanatics shows IN625 precedent on 993 Turbo exhaust systems; it does not establish IN625 for this tip",
            "physicsnemo": "deferred until correlated CFD/CHT/structural cases or test samples exist",
            "simready": "deferred until inlet interface, installed clearances and qualified hot material properties are measured",
        },
        "release_blockers": [
            "No measured exhaust tip, inlet interface, insertion depth, clamp, installed length, angle, clearances or tolerances.",
            "Only the commercial 120 x 85 mm outlet envelope is published.",
            "No measured flow, pressure, temperature, exhaust pulse spectrum or duty cycle.",
            "The FVD product is stainless; IN625 is only a candidate selected from separate 993 exhaust precedent.",
            "No hot LPBF material card, oxidation limit, surface condition or fatigue allowable.",
            "No build orientation, supports, recoater check, machining stock or distortion compensation.",
            "No transient CFD/CHT, shell/contact FEA, modal correlation or fatigue calculation.",
            "No dimensional inspection, CT, leak, thermal-cycle, vibration, acoustic or vehicle fit test.",
            "No professional review of the exhaust installation and adjacent bumper temperature.",
        ],
        "release_authorized": False,
    }


def _lofted_ellipse(a0: float, b0: float, a1: float, b1: float):
    from build123d import BuildSketch, Ellipse, Plane, loft

    with BuildSketch(Plane.XY) as first:
        Ellipse(a0, b0)
    with BuildSketch(Plane.XY.offset(CONCEPT_LENGTH_MM)) as second:
        Ellipse(a1, b1)
    return loft([first.sketch, second.sketch])


def build_solid():
    from build123d import Align, Box, Pos

    outer_body = _lofted_ellipse(
        OUTER_INLET_RADIUS_MM,
        OUTER_INLET_RADIUS_MM,
        OUTER_OUTLET_A_MM,
        OUTER_OUTLET_B_MM,
    )
    outer_void = _lofted_ellipse(
        OUTER_INLET_RADIUS_MM - OUTER_WALL_MM,
        OUTER_INLET_RADIUS_MM - OUTER_WALL_MM,
        OUTER_OUTLET_A_MM - OUTER_WALL_MM,
        OUTER_OUTLET_B_MM - OUTER_WALL_MM,
    )
    inner_body = _lofted_ellipse(
        INNER_SHELL_INLET_RADIUS_MM,
        INNER_SHELL_INLET_RADIUS_MM,
        INNER_SHELL_OUTLET_A_MM,
        INNER_SHELL_OUTLET_B_MM,
    )
    inner_void = _lofted_ellipse(
        INNER_SHELL_INLET_RADIUS_MM - INNER_WALL_MM,
        INNER_SHELL_INLET_RADIUS_MM - INNER_WALL_MM,
        INNER_SHELL_OUTLET_A_MM - INNER_WALL_MM,
        INNER_SHELL_OUTLET_B_MM - INNER_WALL_MM,
    )
    solid = (outer_body - outer_void) + (inner_body - inner_void)

    align_min_z = (Align.CENTER, Align.CENTER, Align.MIN)
    inlet_x = Box(64.0, RIB_THICKNESS_MM, RIB_LENGTH_MM, align=align_min_z)
    inlet_y = Box(RIB_THICKNESS_MM, 64.0, RIB_LENGTH_MM, align=align_min_z)
    outlet_x = Pos(0.0, 0.0, CONCEPT_LENGTH_MM - RIB_LENGTH_MM) * Box(
        114.0, RIB_THICKNESS_MM, RIB_LENGTH_MM, align=align_min_z
    )
    outlet_y = Pos(0.0, 0.0, CONCEPT_LENGTH_MM - RIB_LENGTH_MM) * Box(
        RIB_THICKNESS_MM, 82.0, RIB_LENGTH_MM, align=align_min_z
    )
    solid = solid + inlet_x + inlet_y + outlet_x + outlet_y
    # Les nervures ne doivent jamais traverser le conduit de gaz.
    return solid - inner_void


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    parser.add_argument("--surface", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--material", default="in625", choices=sorted(MATERIALS))
    args = parser.parse_args()

    select_material(args.material)

    cad_volume_mm3 = None
    solid = None
    if args.out or args.surface:
        from build123d import export_step, export_stl, import_step

        solid = build_solid()
        if not solid.is_valid or len(solid.solids()) != 1:
            raise SystemExit("Le concept OCCT n'est pas un solide BREP unique valide.")
        bbox = solid.bounding_box()
        envelope = (bbox.size.X, bbox.size.Y, bbox.size.Z)
        expected_envelope = (
            PUBLISHED_OUTLET_WIDTH_MM,
            PUBLISHED_OUTLET_HEIGHT_MM,
            CONCEPT_LENGTH_MM,
        )
        if any(
            abs(actual - target) > 0.01
            for actual, target in zip(envelope, expected_envelope)
        ):
            raise SystemExit(
                f"Enveloppe incohérente: OCCT={envelope}, cible={expected_envelope}"
            )

        args.out.parent.mkdir(parents=True, exist_ok=True)
        export_step(solid, str(args.out))
        roundtrip = import_step(str(args.out))
        if not roundtrip.is_valid or len(roundtrip.solids()) != 1:
            raise SystemExit("Le STEP relu n'est pas un solide BREP unique valide.")
        if abs(roundtrip.volume - solid.volume) > 0.05:
            raise SystemExit("Le STEP relu ne reproduit pas le volume OCCT attendu.")
        cad_volume_mm3 = roundtrip.volume

    if args.surface and solid is not None:
        args.surface.parent.mkdir(parents=True, exist_ok=True)
        export_stl(solid, str(args.surface), tolerance=0.05, angular_tolerance=0.10)

    report = engineering_screen(cad_volume_mm3)
    report["material_key"] = MATERIAL_KEY
    if solid is not None:
        report["step_roundtrip"] = {
            "status": "passed",
            "valid_brep": True,
            "solid_count": 1,
            "volume_mm3": cad_volume_mm3,
            "envelope_mm": [
                PUBLISHED_OUTLET_WIDTH_MM,
                PUBLISHED_OUTLET_HEIGHT_MM,
                CONCEPT_LENGTH_MM,
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
