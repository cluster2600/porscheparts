#!/usr/bin/env python3
"""Support d'intercooler 993 Turbo/GT2, concept Ti F0 indépendant.

FVD publie uniquement l'enveloppe et la masse de son support renforcé. Le PET
indexé par PorscheFanatics fournit les identités de pièces. Les rails ouverts,
les alésages et le plot central ci-dessous sont des hypothèses propres au projet
et ne constituent ni une reconstruction OEM, ni une géométrie montable.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


PART_ID = "993-ENG-INTERCOOLER-BRACKET-TI-F0-0001"

# Données publiées par FVD pour son produit commercial FVD11011050.
PUBLISHED_LENGTH_MM = 255.0
PUBLISHED_WIDTH_MM = 80.0
PUBLISHED_HEIGHT_MM = 23.0
PUBLISHED_MASS_G = 200.0

# Topologie ouverte, propre au concept F0.
BASE_THICKNESS_MM = 6.0
OUTER_POINTS = (
    (0.0, 10.0),
    (15.0, 0.0),
    (55.0, 4.0),
    (105.0, 16.0),
    (145.0, 25.0),
    (195.0, 40.0),
    (240.0, 45.0),
    (255.0, 54.0),
    (252.0, 70.0),
    (225.0, 72.0),
    (180.0, 68.0),
    (140.0, 62.0),
    (100.0, 52.0),
    (55.0, 41.0),
    (15.0, 40.0),
    (0.0, 30.0),
)
CUTOUTS = (
    (
        (25.0, 12.0),
        (55.0, 10.0),
        (95.0, 20.0),
        (95.0, 39.0),
        (58.0, 31.0),
        (25.0, 29.0),
    ),
    (
        (110.0, 27.0),
        (145.0, 34.0),
        (195.0, 47.0),
        (225.0, 51.0),
        (223.0, 62.0),
        (188.0, 59.0),
        (143.0, 51.0),
        (110.0, 44.0),
    ),
)
END_BORES = ((15.0, 20.0, 6.0), (241.0, 58.0, 5.0))
PEDESTAL_X_MM = 120.0
PEDESTAL_Y_MM = 56.0
PEDESTAL_LENGTH_MM = 25.0
PEDESTAL_WIDTH_MM = 24.0
PEDESTAL_HEIGHT_MM = PUBLISHED_HEIGHT_MM - BASE_THICKNESS_MM
PEDESTAL_BORE_DIAMETER_MM = 6.0

# Cas de régression synthétique, sans autorité véhicule.
SCREEN_FORCE_N = 400.0
SCREEN_SPAN_MM = 220.0
SCREEN_DELTA_T_K = 120.0
RAIL_COUNT = 2.0
RAIL_EFFECTIVE_WIDTH_MM = 8.0

# Carte mixte provisoire : physique TIMET corroyée + procédé EOS LPBF.
DENSITY_G_CM3 = 4.42
ELASTIC_MODULUS_MPA = 110_000.0
POISSON_RATIO = 0.31
COMPARISON_PROOF_STRENGTH_MPA = 828.0
THERMAL_EXPANSION_PER_K = 9.0e-6


def polygon_area_mm2(points: tuple[tuple[float, float], ...]) -> float:
    """Aire signée absolue d'un polygone simple par la formule du lacet."""

    return abs(
        sum(
            x0 * y1 - x1 * y0
            for (x0, y0), (x1, y1) in zip(points, points[1:] + points[:1])
        )
    ) / 2.0


def analytic_volume_mm3() -> float:
    """Volume net exact de la géométrie F0 sans dépendance CAO."""

    base_area = polygon_area_mm2(OUTER_POINTS)
    base_area -= sum(polygon_area_mm2(cutout) for cutout in CUTOUTS)
    base_area -= sum(math.pi * radius**2 for _, _, radius in END_BORES)
    base_volume = base_area * BASE_THICKNESS_MM
    pedestal_volume = (
        PEDESTAL_LENGTH_MM * PEDESTAL_WIDTH_MM * PEDESTAL_HEIGHT_MM
    )
    pedestal_bore = (
        math.pi
        * (PEDESTAL_BORE_DIAMETER_MM / 2.0) ** 2
        * PEDESTAL_HEIGHT_MM
    )
    return base_volume + pedestal_volume - pedestal_bore


def engineering_screen(force_n: float = SCREEN_FORCE_N) -> dict[str, object]:
    """Criblage poutre/liaisons/thermique, volontairement conservateur et simple."""

    if force_n <= 0:
        raise ValueError("La force de criblage doit être positive.")

    effective_width = RAIL_COUNT * RAIL_EFFECTIVE_WIDTH_MM
    area = effective_width * BASE_THICKNESS_MM
    second_moment = effective_width * BASE_THICKNESS_MM**3 / 12.0
    reaction = force_n / 2.0
    maximum_moment = force_n * SCREEN_SPAN_MM / 4.0
    bending_stress = maximum_moment * (BASE_THICKNESS_MM / 2.0) / second_moment
    maximum_shear = 1.5 * force_n / area
    von_mises = math.sqrt(bending_stress**2 + 3.0 * maximum_shear**2)
    center_deflection = force_n * SCREEN_SPAN_MM**3 / (
        48.0 * ELASTIC_MODULUS_MPA * second_moment
    )
    end_bearing = [
        reaction / (2.0 * radius * BASE_THICKNESS_MM)
        for _, _, radius in END_BORES
    ]
    pedestal_bearing = force_n / (
        PEDESTAL_BORE_DIAMETER_MM * PEDESTAL_HEIGHT_MM
    )
    thermal_growth = (
        THERMAL_EXPANSION_PER_K * SCREEN_SPAN_MM * SCREEN_DELTA_T_K
    )
    volume = analytic_volume_mm3()
    mass = volume / 1000.0 * DENSITY_G_CM3

    return {
        "schema_version": "1.0.0",
        "part_id": PART_ID,
        "status": "f0_published_envelope_clean_sheet_math_screen_only",
        "geometry_authority": {
            "published": [
                "commercial product envelope 255 x 80 x 23 mm",
                "commercial product mass 200 g",
            ],
            "catalogue_identity": ["99311011050", "99311011052"],
            "hypotheses": [
                "open two-rail polygonal load path",
                "end-bore diameters and positions",
                "central pedestal and bore",
                "effective rail section and 220 mm support span",
            ],
            "not_claimed": "No OEM or FVD fitment geometry is claimed.",
        },
        "synthetic_load_case": {
            "center_force_n": force_n,
            "span_mm": SCREEN_SPAN_MM,
            "delta_t_k": SCREEN_DELTA_T_K,
            "authority": "regression input only; vehicle loads, vibration spectrum and temperature field absent",
        },
        "material_screen": {
            "candidate": "Ti-6Al-4V Grade 5 LPBF study only",
            "density_g_cm3": DENSITY_G_CM3,
            "elastic_modulus_mpa": ELASTIC_MODULUS_MPA,
            "poisson_ratio": POISSON_RATIO,
            "comparison_proof_strength_mpa": COMPARISON_PROOF_STRENGTH_MPA,
            "thermal_expansion_per_k": THERMAL_EXPANSION_PER_K,
            "scope": "TIMET wrought physical/minimum plate references are not LPBF allowables; EOS process qualification remains supplier-specific",
        },
        "results": {
            "analytic_volume_mm3": volume,
            "screening_mass_g": mass,
            "published_commercial_mass_g": PUBLISHED_MASS_G,
            "mass_delta_g": mass - PUBLISHED_MASS_G,
            "mass_ratio": mass / PUBLISHED_MASS_G,
            "effective_rail_area_mm2": area,
            "effective_second_moment_mm4": second_moment,
            "support_reaction_each_n": reaction,
            "maximum_bending_moment_n_mm": maximum_moment,
            "nominal_bending_stress_mpa": bending_stress,
            "maximum_transverse_shear_mpa": maximum_shear,
            "von_mises_screen_mpa": von_mises,
            "wrought_reference_proof_ratio": COMPARISON_PROOF_STRENGTH_MPA / von_mises,
            "linear_elastic_center_deflection_mm": center_deflection,
            "end_bore_average_bearing_mpa": end_bearing,
            "pedestal_average_bearing_mpa": pedestal_bearing,
            "thermal_growth_over_screen_span_mm": thermal_growth,
        },
        "equations": {
            "polygon_area": "A=abs(sum(x_i*y_i+1-x_i+1*y_i))/2",
            "mass": "m=rho*V",
            "beam_section": "A=n*b*t; I=n*b*t^3/12",
            "simply_supported_center_load": "Mmax=F*L/4; delta=F*L^3/(48*E*I)",
            "bending_stress": "sigma=M*c/I",
            "rectangular_shear": "tau_max=1.5*F/A",
            "von_mises": "sqrt(sigma^2+3*tau^2)",
            "bearing": "p=R/(d*t)",
            "thermal_growth": "delta_L=alpha*L*delta_T",
        },
        "dfam_screen": {
            "part_consolidation": "open frame, two end eyes and central pedestal in one BREP",
            "open_cutouts": len(CUTOUTS),
            "trapped_powder_volume": False,
            "minimum_nominal_wall_mm": BASE_THICKNESS_MM,
            "minimum_bore_diameter_mm": min(2.0 * item[2] for item in END_BORES),
            "machining_allowance_defined": False,
            "orientation_selected": False,
            "process_comparison_required": ["5-axis CNC", "fabricated sheet/forging", "LPBF titanium"],
        },
        "interpretation": {
            "mechanics": "nominal beam screen only; curved-frame stress concentrations, contact, bolt preload and local modes are absent",
            "mass": "the mass delta does not validate the model because the FVD material and exact topology are unknown",
            "fatigue": "not calculated; no vibration spectrum, surface state, defect population or qualified S-N curve",
            "thermal": "uniform free expansion only; engine-bay gradients and constrained expansion are absent",
            "physicsnemo": "deferred until correlated CAE or test samples exist; no surrogate model can replace missing boundary conditions",
            "simready": "deferred until measured interfaces and qualified material assignment exist",
        },
        "release_blockers": [
            "No measured OEM or FVD bracket, mounting datums, hole spacing, tolerances or mating surfaces.",
            "The published 255 x 80 x 23 mm values are only a commercial packaging envelope.",
            "No measured intercooler mass, acceleration load, boost-hose reaction or fastener preload.",
            "No engine-bay temperature field, vibration PSD, duty cycle or fatigue target.",
            "No qualified LPBF machine, parameter set, orientation, heat treatment, HIP decision or fatigue card.",
            "No machining allowance, bushing, fastener, surface finish or galvanic-isolation stack selected.",
            "No nonlinear/contact FEA, modal analysis, thermal-stress analysis or correlated surrogate dataset.",
            "No dimensional inspection, proof load, vibration bench, thermal cycle, leak check or vehicle fit test.",
            "No professional engineering review for a loaded engine-bay support.",
        ],
        "release_authorized": False,
    }


def build_solid():
    """Construit le BREP F0 ; build123d est importé dans l'image CAO."""

    from build123d import Align, Box, Cylinder, Polygon, Pos, extrude

    solid = extrude(Polygon(*OUTER_POINTS), amount=BASE_THICKNESS_MM)
    for cutout in CUTOUTS:
        solid = solid - extrude(Polygon(*cutout), amount=BASE_THICKNESS_MM)
    for x_pos, y_pos, radius in END_BORES:
        solid = solid - Pos(x_pos, y_pos, 0.0) * Cylinder(
            radius,
            BASE_THICKNESS_MM,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )

    pedestal = Pos(PEDESTAL_X_MM, PEDESTAL_Y_MM, BASE_THICKNESS_MM) * Box(
        PEDESTAL_LENGTH_MM,
        PEDESTAL_WIDTH_MM,
        PEDESTAL_HEIGHT_MM,
        align=(Align.MIN, Align.MIN, Align.MIN),
    )
    solid = solid + pedestal
    pedestal_bore = Pos(
        PEDESTAL_X_MM + PEDESTAL_LENGTH_MM / 2.0,
        PEDESTAL_Y_MM + PEDESTAL_WIDTH_MM / 2.0,
        BASE_THICKNESS_MM,
    ) * Cylinder(
        PEDESTAL_BORE_DIAMETER_MM / 2.0,
        PEDESTAL_HEIGHT_MM,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    return solid - pedestal_bore


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
        expected = analytic_volume_mm3()
        if not solid.is_valid or len(solid.solids()) != 1:
            raise SystemExit("Le concept OCCT n'est pas un solide BREP unique valide.")
        if abs(solid.volume - expected) > 0.05:
            raise SystemExit(
                f"Volume incohérent: OCCT={solid.volume}, analytique={expected}"
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
            or abs(roundtrip.volume - expected) > 0.05
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
