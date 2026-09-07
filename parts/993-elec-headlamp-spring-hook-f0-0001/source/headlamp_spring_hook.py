#!/usr/bin/env python3
"""Concept F0 indépendant d'un crochet de réparation de phare 993.

La source commerciale démontre le besoin et l'intérêt de l'impression métal,
mais ne publie aucune cote. Les valeurs ci-dessous sont donc des variables de
conception explicites, jamais des mesures de la pièce Roadster-Fashion ou OEM.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


PART_ID = "993-ELEC-HEADLAMP-SPRING-HOOK-F0-0001"

# Géométrie propre au concept F0, en mm.
SOCKET_LENGTH = 10.0
SOCKET_WIDTH = 8.0
SOCKET_HEIGHT = 7.0
CAVITY_LENGTH = 7.5
CAVITY_WIDTH = 4.5
CAVITY_HEIGHT = 4.0
CAVITY_FLOOR = 1.5
NECK_LENGTH = 3.0
NECK_HEIGHT = 8.0
ARM_LENGTH = 9.0
ARM_THICKNESS = 3.0
TIP_LENGTH = 3.0
TIP_HEIGHT = 5.0

# Cas synthétique destiné à éprouver les équations, pas la pièce du véhicule.
SCREEN_FORCE_N = 30.0
SCREEN_DELTA_T_K = 100.0

# Carte ambiante de criblage AlSi10Mg. Elle ne qualifie ni poudre ni procédé.
DENSITY_G_CM3 = 2.67
ELASTIC_MODULUS_MPA = 70_000.0
YIELD_STRENGTH_MPA = 245.0
THERMAL_EXPANSION_PER_K = 21.0e-6


def analytic_volume_mm3() -> float:
    socket = SOCKET_LENGTH * SOCKET_WIDTH * SOCKET_HEIGHT
    cavity = CAVITY_LENGTH * CAVITY_WIDTH * CAVITY_HEIGHT
    neck = NECK_LENGTH * SOCKET_WIDTH * NECK_HEIGHT
    arm = ARM_LENGTH * SOCKET_WIDTH * ARM_THICKNESS
    neck_arm_overlap = NECK_LENGTH * SOCKET_WIDTH * ARM_THICKNESS
    tip = TIP_LENGTH * SOCKET_WIDTH * TIP_HEIGHT
    return socket - cavity + neck + arm - neck_arm_overlap + tip


def engineering_screen(force_n: float = SCREEN_FORCE_N) -> dict[str, object]:
    if force_n <= 0:
        raise ValueError("La force de criblage doit être positive.")

    free_span = ARM_LENGTH - NECK_LENGTH
    width = SOCKET_WIDTH
    thickness = ARM_THICKNESS
    area = width * thickness
    second_moment = width * thickness**3 / 12.0
    bending_moment = force_n * free_span
    bending_stress = bending_moment * (thickness / 2.0) / second_moment
    max_shear = 1.5 * force_n / area
    von_mises = math.sqrt(bending_stress**2 + 3.0 * max_shear**2)
    deflection = force_n * free_span**3 / (
        3.0 * ELASTIC_MODULUS_MPA * second_moment
    )
    bond_area = 2.0 * (CAVITY_WIDTH + CAVITY_HEIGHT) * CAVITY_LENGTH
    bond_average_shear = force_n / bond_area
    envelope_length = SOCKET_LENGTH + (ARM_LENGTH - NECK_LENGTH)
    thermal_growth = THERMAL_EXPANSION_PER_K * envelope_length * SCREEN_DELTA_T_K
    volume = analytic_volume_mm3()

    return {
        "schema_version": "1.0.0",
        "part_id": PART_ID,
        "status": "f0_clean_sheet_math_screen_only",
        "geometry_authority": "design_hypothesis_not_observed_dimensions",
        "synthetic_load_case": {
            "force_n": force_n,
            "delta_t_k": SCREEN_DELTA_T_K,
            "authority": "regression input only; real spring load and temperature absent",
        },
        "material_screen": {
            "candidate": "AlSi10Mg LPBF, room-temperature reference only",
            "density_g_cm3": DENSITY_G_CM3,
            "elastic_modulus_mpa": ELASTIC_MODULUS_MPA,
            "yield_strength_mpa": YIELD_STRENGTH_MPA,
            "thermal_expansion_per_k": THERMAL_EXPANSION_PER_K,
        },
        "results": {
            "analytic_volume_mm3": volume,
            "screening_mass_g": volume / 1000.0 * DENSITY_G_CM3,
            "minimum_socket_wall_mm": min(
                (SOCKET_WIDTH - CAVITY_WIDTH) / 2.0,
                CAVITY_FLOOR,
                SOCKET_HEIGHT - CAVITY_FLOOR - CAVITY_HEIGHT,
            ),
            "arm_free_span_mm": free_span,
            "arm_section_area_mm2": area,
            "arm_second_moment_mm4": second_moment,
            "bending_stress_mpa": bending_stress,
            "maximum_transverse_shear_mpa": max_shear,
            "von_mises_screen_mpa": von_mises,
            "room_temperature_yield_ratio": YIELD_STRENGTH_MPA / von_mises,
            "tip_deflection_mm": deflection,
            "bond_area_mm2": bond_area,
            "bond_average_shear_mpa": bond_average_shear,
            "thermal_growth_over_envelope_mm": thermal_growth,
        },
        "equations": {
            "second_moment": "I=b*t^3/12",
            "bending_stress": "sigma=M*c/I with M=F*L",
            "rectangular_shear": "tau_max=1.5*F/(b*t)",
            "von_mises": "sqrt(sigma^2+3*tau^2)",
            "cantilever_deflection": "delta=F*L^3/(3*E*I)",
            "bond_average_shear": "tau_bond=F/A_bond",
            "thermal_growth": "delta_L=alpha*L*delta_T",
        },
        "interpretation": {
            "solid_mechanics": "numerical screen only; synthetic force and ambient yield card",
            "bond": "reported only; no adhesive allowables or temperature curve",
            "thermal": "free expansion only; lamp radiation and constraints not modelled",
            "lpbf": "open cavity avoids trapped powder; orientation and supports remain unqualified",
        },
        "release_blockers": [
            "No published dimensions, datum or tolerance for the commercial or OEM hook.",
            "No measured spring force, direction or repeated lamp-change duty cycle.",
            "No lamp-side temperature or radiative heat-flux map.",
            "No qualified AlSi10Mg hot material card for the selected machine/orientation.",
            "No adhesive system, bond-line geometry or hot lap-shear allowables selected.",
            "No headlamp fit check, beam-alignment check or road vibration test.",
        ],
        "release_authorized": False,
    }


def build_solid():
    from build123d import Align, Box, Pos

    align = (Align.MIN, Align.CENTER, Align.MIN)
    outer = Box(SOCKET_LENGTH, SOCKET_WIDTH, SOCKET_HEIGHT, align=align)
    cavity = Pos(-0.1, 0, CAVITY_FLOOR) * Box(
        CAVITY_LENGTH + 0.1, CAVITY_WIDTH, CAVITY_HEIGHT, align=align
    )
    socket = outer - cavity
    neck = Pos(SOCKET_LENGTH - NECK_LENGTH, 0, SOCKET_HEIGHT) * Box(
        NECK_LENGTH, SOCKET_WIDTH, NECK_HEIGHT, align=align
    )
    arm = Pos(SOCKET_LENGTH - NECK_LENGTH, 0, SOCKET_HEIGHT + NECK_HEIGHT - ARM_THICKNESS) * Box(
        ARM_LENGTH, SOCKET_WIDTH, ARM_THICKNESS, align=align
    )
    tip = Pos(SOCKET_LENGTH + ARM_LENGTH - NECK_LENGTH - TIP_LENGTH, 0, SOCKET_HEIGHT) * Box(
        TIP_LENGTH, SOCKET_WIDTH, TIP_HEIGHT, align=align
    )
    return socket + neck + arm + tip


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
        if abs(solid.volume - expected) > 0.01:
            raise SystemExit(
                f"Volume incohérent: OCCT={solid.volume}, analytique={expected}"
            )
        args.out.parent.mkdir(parents=True, exist_ok=True)
        export_step(solid, str(args.out))
        roundtrip = import_step(str(args.out))
        if (
            not roundtrip.is_valid
            or len(roundtrip.solids()) != 1
            or abs(roundtrip.volume - expected) > 0.01
        ):
            raise SystemExit("Le STEP relu ne reproduit pas le solide attendu.")
        report["step_roundtrip"] = {
            "status": "passed",
            "valid_brep": True,
            "solid_count": 1,
            "volume_mm3": roundtrip.volume,
            "maximum_volume_delta_mm3": 0.01,
        }

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
