#!/usr/bin/env python3
"""Concept F0 indépendant d'un ouvre-porte intérieur Porsche 993.

FVD publie seulement l'enveloppe et la masse de sa paire commerciale. Le
catalogue PorscheFanatics fournit les identités PET gauche/droite. Les détails
de la chape, des alésages et des poches ci-dessous sont des variables de
conception propres au projet, jamais des cotes OEM ou Rennline/FVD.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re


PART_ID = "993-INT-DOOR-OPENER-LEVER-F0-0001"

# Enveloppe et masse publiées par FVD pour son produit commercial.
PUBLISHED_LENGTH_MM = 108.0
PUBLISHED_WIDTH_MM = 45.0
PUBLISHED_HEIGHT_MM = 27.0
PUBLISHED_PAIR_MASS_G = 180.0

# Topologie propre au concept F0, en mm.
PLATE_THICKNESS_MM = 5.0
TOP_SKIN_MM = 2.0
POCKET_DEPTH_MM = PLATE_THICKNESS_MM - TOP_SKIN_MM
POCKET_LENGTH_MM = 14.0
POCKET_WIDTH_MM = 35.0
POCKET_X_MM = (4.0, 24.0, 44.0, 64.0, 84.0)
BRIDGE_X_MM = 18.0
BRIDGE_LENGTH_MM = 34.0
BRIDGE_WIDTH_MM = 24.0
BRIDGE_HEIGHT_MM = 8.0
EAR_THICKNESS_MM = 4.0
EAR_HEIGHT_MM = 14.0
EAR_CENTER_Y_MM = 10.0
PIVOT_X_MM = 35.0
PIVOT_Z_MM = 7.0
PIVOT_DIAMETER_MM = 6.0
MOUNT_BORE_DIAMETER_MM = 5.0
MOUNT_BORE_DEPTH_MM = 6.0
MOUNT_BORE_X_MM = (26.0, 44.0)
LOAD_APPLICATION_X_MM = 92.0
HAND_CONTACT_LENGTH_MM = 30.0

# Cas synthétique de régression. Ce n'est pas une exigence Porsche/FVD.
SCREEN_FORCE_N = 150.0
SCREEN_DELTA_T_K = 60.0

# Carte ambiante de criblage AlSi10Mg, non qualifiée pour cette pièce.
DENSITY_G_CM3 = 2.67
ELASTIC_MODULUS_MPA = 70_000.0
YIELD_STRENGTH_MPA = 233.0
THERMAL_EXPANSION_PER_K = 22.0e-6


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_step_header(path: Path) -> None:
    """Retire l'horodatage OCCT afin que le STEP reste reproductible."""

    payload = path.read_text(encoding="utf-8")
    normalized, count = re.subn(
        r"(FILE_NAME\('Open CASCADE Shape Model',)'[^']+'",
        r"\1'1970-01-01T00:00:00'",
        payload,
        count=1,
    )
    if count != 1:
        raise SystemExit("En-tête STEP OCCT inattendu ; normalisation refusée.")
    path.write_text(normalized, encoding="utf-8")


def analytic_volume_mm3() -> float:
    """Volume net du BREP F0, calculé sans dépendance CAO."""

    plate = PUBLISHED_LENGTH_MM * PUBLISHED_WIDTH_MM * PLATE_THICKNESS_MM
    pockets = (
        len(POCKET_X_MM) * POCKET_LENGTH_MM * POCKET_WIDTH_MM * POCKET_DEPTH_MM
    )
    bridge = BRIDGE_LENGTH_MM * BRIDGE_WIDTH_MM * BRIDGE_HEIGHT_MM
    ears = 2.0 * BRIDGE_LENGTH_MM * EAR_THICKNESS_MM * EAR_HEIGHT_MM
    pivot_bores = math.pi * (PIVOT_DIAMETER_MM / 2.0) ** 2 * (
        2.0 * EAR_THICKNESS_MM
    )
    mount_bores = len(MOUNT_BORE_X_MM) * math.pi * (
        MOUNT_BORE_DIAMETER_MM / 2.0
    ) ** 2 * MOUNT_BORE_DEPTH_MM
    return plate - pockets + bridge + ears - pivot_bores - mount_bores


def engineering_screen(force_n: float = SCREEN_FORCE_N) -> dict[str, object]:
    """Criblage élastique du levier et de son pivot sous une charge hypothétique."""

    if force_n <= 0:
        raise ValueError("La force de criblage doit être positive.")

    lever_span = LOAD_APPLICATION_X_MM - PIVOT_X_MM
    section_area = PUBLISHED_WIDTH_MM * PLATE_THICKNESS_MM
    second_moment = (
        PUBLISHED_WIDTH_MM * PLATE_THICKNESS_MM**3 / 12.0
    )
    bending_moment = force_n * lever_span
    bending_stress = (
        bending_moment * (PLATE_THICKNESS_MM / 2.0) / second_moment
    )
    maximum_shear = 1.5 * force_n / section_area
    von_mises = math.sqrt(bending_stress**2 + 3.0 * maximum_shear**2)
    tip_deflection = force_n * lever_span**3 / (
        3.0 * ELASTIC_MODULUS_MPA * second_moment
    )

    pivot_bearing = force_n / (
        2.0 * PIVOT_DIAMETER_MM * EAR_THICKNESS_MM
    )
    pin_double_shear_area = 2.0 * math.pi * PIVOT_DIAMETER_MM**2 / 4.0
    pin_double_shear = force_n / pin_double_shear_area
    ear_net_area = 2.0 * EAR_THICKNESS_MM * (
        EAR_HEIGHT_MM - PIVOT_DIAMETER_MM
    )
    ear_net_tension = force_n / ear_net_area
    hand_contact_pressure = force_n / (
        HAND_CONTACT_LENGTH_MM * PUBLISHED_WIDTH_MM
    )

    thermal_growth = (
        THERMAL_EXPANSION_PER_K
        * PUBLISHED_LENGTH_MM
        * SCREEN_DELTA_T_K
    )
    volume = analytic_volume_mm3()
    mass = volume / 1000.0 * DENSITY_G_CM3
    model_pair_mass = 2.0 * mass

    return {
        "schema_version": "1.0.0",
        "part_id": PART_ID,
        "status": "f0_published_envelope_clean_sheet_math_screen_only",
        "geometry_authority": {
            "published": [
                "commercial product envelope 108 x 45 x 27 mm",
                "commercial pair mass 180 g",
            ],
            "hypotheses": [
                "plate thickness, pockets and skin",
                "integrated bridge and clevis geometry",
                "pivot and blind mounting bores",
                "load application point",
            ],
            "not_claimed": "No OEM or commercial-product fitment geometry is claimed.",
        },
        "synthetic_load_case": {
            "force_n": force_n,
            "delta_t_k": SCREEN_DELTA_T_K,
            "authority": "regression input only; real hand force, direction, stops and temperature absent",
        },
        "material_screen": {
            "candidate": "EOS Aluminium AlSi10Mg / EOS M 290 / 30 um, as-manufactured screening route",
            "commercial_product": "high-strength aluminium declared by FVD; grade unknown",
            "density_g_cm3": DENSITY_G_CM3,
            "elastic_modulus_mpa": ELASTIC_MODULUS_MPA,
            "yield_strength_mpa": YIELD_STRENGTH_MPA,
            "thermal_expansion_per_k": THERMAL_EXPANSION_PER_K,
        },
        "results": {
            "analytic_volume_mm3": volume,
            "screening_mass_each_g": mass,
            "screening_pair_mass_g": model_pair_mass,
            "published_pair_mass_g": PUBLISHED_PAIR_MASS_G,
            "pair_mass_delta_g": model_pair_mass - PUBLISHED_PAIR_MASS_G,
            "pair_mass_ratio": model_pair_mass / PUBLISHED_PAIR_MASS_G,
            "minimum_open_skin_mm": TOP_SKIN_MM,
            "lever_span_mm": lever_span,
            "lever_section_area_mm2": section_area,
            "lever_second_moment_mm4": second_moment,
            "bending_moment_n_mm": bending_moment,
            "bending_stress_mpa": bending_stress,
            "maximum_transverse_shear_mpa": maximum_shear,
            "von_mises_screen_mpa": von_mises,
            "room_temperature_yield_ratio": YIELD_STRENGTH_MPA / von_mises,
            "linear_elastic_tip_deflection_mm": tip_deflection,
            "pivot_average_bearing_stress_mpa": pivot_bearing,
            "candidate_pin_double_shear_mpa": pin_double_shear,
            "clevis_net_tension_mpa": ear_net_tension,
            "average_hand_contact_pressure_mpa": hand_contact_pressure,
            "thermal_growth_over_published_length_mm": thermal_growth,
        },
        "equations": {
            "section_area": "A=b*t",
            "second_moment": "I=b*t^3/12",
            "bending_stress": "sigma=M*c/I with M=F*L",
            "rectangular_shear": "tau_max=1.5*F/(b*t)",
            "von_mises": "sqrt(sigma^2+3*tau^2)",
            "cantilever_deflection": "delta=F*L^3/(3*E*I)",
            "pivot_bearing": "p=F/(2*d*t_ear)",
            "pin_double_shear": "tau=F/(2*pi*d^2/4)",
            "clevis_net_tension": "sigma_net=F/(2*t_ear*(h_ear-d))",
            "contact_pressure": "p_hand=F/A_contact",
            "mass": "m=rho*V",
            "thermal_growth": "delta_L=alpha*L*delta_T",
        },
        "dfam_screen": {
            "part_consolidation": "plate, bridge and clevis are one BREP solid",
            "open_relief_pockets": len(POCKET_X_MM),
            "trapped_powder_volume": False,
            "minimum_open_skin_mm": TOP_SKIN_MM,
            "minimum_bore_diameter_mm": min(
                PIVOT_DIAMETER_MM, MOUNT_BORE_DIAMETER_MM
            ),
            "machining_allowance_defined": False,
            "orientation_selected": False,
        },
        "interpretation": {
            "solid_mechanics": "nominal beam screen only; clevis fillets, stops, contact and stress concentrations absent",
            "mass": "comparison is not a validation because the published pair may include fasteners and a different topology",
            "fatigue": "not calculated; no duty cycle, surface state, defect population or qualified S-N curve",
            "lpbf": "consolidation and open pockets justify study; build orientation, supports and finish remain unqualified",
            "simready": "deferred until the NVIDIA preflight and property-assignment services are healthy",
        },
        "release_blockers": [
            "No measured OEM lever, pivot, stop, cable/rod interface, datum or tolerance.",
            "The published 108 x 45 x 27 mm values are only a commercial product envelope.",
            "No measured pull force, off-axis abuse case, duty cycle or impact case.",
            "No qualified LPBF machine/orientation material card or fatigue curve.",
            "No machining allowance, pivot fit, bushing, fastener preload or coating stack selected.",
            "No dimensional inspection, door fit check, emergency-egress test or cyclic bench test.",
            "No professional engineering review for a functional door-release component.",
        ],
        "release_authorized": False,
    }


def build_solid():
    """Construit le BREP F0 ; build123d est importé seulement dans l'image CAO."""

    from build123d import Align, Box, Cylinder, Pos, Rot

    box_align = (Align.MIN, Align.CENTER, Align.MIN)
    plate_z = PUBLISHED_HEIGHT_MM - PLATE_THICKNESS_MM
    bridge_z = plate_z - BRIDGE_HEIGHT_MM

    plate = Pos(0, 0, plate_z) * Box(
        PUBLISHED_LENGTH_MM,
        PUBLISHED_WIDTH_MM,
        PLATE_THICKNESS_MM,
        align=box_align,
    )
    for pocket_x in POCKET_X_MM:
        pocket = Pos(pocket_x, 0, plate_z) * Box(
            POCKET_LENGTH_MM,
            POCKET_WIDTH_MM,
            POCKET_DEPTH_MM,
            align=box_align,
        )
        plate = plate - pocket

    bridge = Pos(BRIDGE_X_MM, 0, bridge_z) * Box(
        BRIDGE_LENGTH_MM,
        BRIDGE_WIDTH_MM,
        BRIDGE_HEIGHT_MM,
        align=box_align,
    )
    left_ear = Pos(BRIDGE_X_MM, -EAR_CENTER_Y_MM, 0) * Box(
        BRIDGE_LENGTH_MM,
        EAR_THICKNESS_MM,
        EAR_HEIGHT_MM,
        align=box_align,
    )
    right_ear = Pos(BRIDGE_X_MM, EAR_CENTER_Y_MM, 0) * Box(
        BRIDGE_LENGTH_MM,
        EAR_THICKNESS_MM,
        EAR_HEIGHT_MM,
        align=box_align,
    )
    solid = plate + bridge + left_ear + right_ear

    centered = (Align.CENTER, Align.CENTER, Align.CENTER)
    pivot_bore = (
        Pos(PIVOT_X_MM, 0, PIVOT_Z_MM)
        * Rot(90, 0, 0)
        * Cylinder(
            PIVOT_DIAMETER_MM / 2.0,
            BRIDGE_WIDTH_MM + 2.0,
            align=centered,
        )
    )
    solid = solid - pivot_bore

    for bore_x in MOUNT_BORE_X_MM:
        mount_bore = Pos(bore_x, 0, bridge_z + MOUNT_BORE_DEPTH_MM / 2.0) * Cylinder(
            MOUNT_BORE_DIAMETER_MM / 2.0,
            MOUNT_BORE_DEPTH_MM,
            align=centered,
        )
        solid = solid - mount_bore
    return solid


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    parser.add_argument("--surface", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--force-n", type=float, default=SCREEN_FORCE_N)
    args = parser.parse_args()

    report = engineering_screen(args.force_n)
    if args.out or args.surface:
        from build123d import export_step, export_stl, import_step

        solid = build_solid()
        expected = analytic_volume_mm3()
        if not solid.is_valid or len(solid.solids()) != 1:
            raise SystemExit("Le concept OCCT n'est pas un solide BREP unique valide.")
        if abs(solid.volume - expected) > 0.02:
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
        if any(abs(actual - target) > 0.01 for actual, target in zip(envelope, expected_envelope)):
            raise SystemExit(
                f"Enveloppe incohérente: OCCT={envelope}, publiée={expected_envelope}"
            )

        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            export_step(solid, str(args.out))
            normalize_step_header(args.out)
            roundtrip = import_step(str(args.out))
            if (
                not roundtrip.is_valid
                or len(roundtrip.solids()) != 1
                or abs(roundtrip.volume - expected) > 0.02
            ):
                raise SystemExit("Le STEP relu ne reproduit pas le solide attendu.")
            report["step_roundtrip"] = {
                "status": "passed",
                "valid_brep": True,
                "solid_count": 1,
                "volume_mm3": roundtrip.volume,
                "envelope_mm": list(envelope),
                "maximum_volume_delta_mm3": 0.02,
                "maximum_envelope_delta_mm": 0.01,
                "sha256": sha256(args.out),
            }

        if args.surface:
            args.surface.parent.mkdir(parents=True, exist_ok=True)
            export_stl(
                solid,
                str(args.surface),
                tolerance=0.03,
                angular_tolerance=0.08,
            )
            report["analysis_surface"] = {
                "status": "exported_for_downstream_mesh_validation",
                "format": ".stl",
                "sha256": sha256(args.surface),
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
