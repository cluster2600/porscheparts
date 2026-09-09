#!/usr/bin/env python3
"""Maître paramétrique F1 de la bague aluminium EQ850101.

Les quatre cotes viennent de la fiche fournisseur archivée dans le catalogue.
Le profil intérieur est interprété comme un cône linéaire : cette hypothèse est
visible, testée et bloque toute libération tant qu'un exemplaire n'est pas mesuré.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


PART_ID = "993-INT-SWITCH-TRIM-RING-F1-0001"
OUTER_DIAMETER_MM = 30.5
DEPTH_MM = 10.5
FRONT_INNER_DIAMETER_MM = 23.0
REAR_INNER_DIAMETER_MM = 28.0

# Hypothèse de comparaison seulement, pas une identification de l'alliage original.
SCREENING_DENSITY_G_CM3 = 2.67


def geometry_screen() -> dict[str, object]:
    outer_radius = OUTER_DIAMETER_MM / 2.0
    front_radius = FRONT_INNER_DIAMETER_MM / 2.0
    rear_radius = REAR_INNER_DIAMETER_MM / 2.0
    if not 0 < front_radius <= rear_radius < outer_radius:
        raise ValueError("Les diamètres doivent définir un anneau positif.")

    outer_volume = math.pi * outer_radius**2 * DEPTH_MM
    bore_volume = (
        math.pi
        * DEPTH_MM
        * (front_radius**2 + front_radius * rear_radius + rear_radius**2)
        / 3.0
    )
    volume_mm3 = outer_volume - bore_volume
    mass_g = volume_mm3 / 1000.0 * SCREENING_DENSITY_G_CM3
    taper_half_angle_deg = math.degrees(
        math.atan((rear_radius - front_radius) / DEPTH_MM)
    )

    return {
        "schema_version": "1.0.0",
        "part_id": PART_ID,
        "status": "geometry_math_screen_only",
        "source_dimensions_mm": {
            "outer_diameter": OUTER_DIAMETER_MM,
            "depth": DEPTH_MM,
            "front_inner_diameter": FRONT_INNER_DIAMETER_MM,
            "rear_inner_diameter": REAR_INNER_DIAMETER_MM,
        },
        "explicit_assumptions": [
            "Le diamètre extérieur est cylindrique sur toute la profondeur.",
            "L'alésage évolue linéairement de 23 à 28 mm sur 10,5 mm.",
            "2,67 g/cm3 est une densité de criblage AlSi10Mg, pas la matière identifiée du produit.",
        ],
        "results": {
            "front_radial_wall_mm": outer_radius - front_radius,
            "rear_radial_wall_mm": outer_radius - rear_radius,
            "bore_taper_half_angle_deg": taper_half_angle_deg,
            "analytic_volume_mm3": volume_mm3,
            "screening_mass_g": mass_g,
        },
        "equations": {
            "frustum_bore_volume": "pi*h*(r1^2+r1*r2+r2^2)/3",
            "ring_volume": "pi*R^2*h-frustum_bore_volume",
            "mass": "ring_volume*density",
            "thermal_radial_growth_pending": "delta_r=alpha*r*delta_T",
            "interference_pressure_pending": "requires OEM opening, tolerances, E and nu",
        },
        "release_blockers": [
            "Tolérances fournisseur absentes.",
            "Profil axial réel et rayons d'arête non mesurés.",
            "Ouverture OEM, jeu ou serrage cible non mesurés.",
            "Alliage et état métallurgique du produit original non identifiés.",
            "Aucun montage véhicule ni contrôle sur échantillon.",
        ],
        "manufacturing_decision": {
            "lpbf": "géométriquement plausible, non qualifié",
            "cnc": "référence économique probable pour cette géométrie axisymétrique",
            "decision": "undecided_pending_sample_and_cost_comparison",
        },
    }


def build_solid():
    from build123d import Align, BuildPart, Cone, Cylinder, Mode

    with BuildPart() as model:
        Cylinder(
            OUTER_DIAMETER_MM / 2.0,
            DEPTH_MM,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )
        Cone(
            FRONT_INNER_DIAMETER_MM / 2.0,
            REAR_INNER_DIAMETER_MM / 2.0,
            DEPTH_MM,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
            mode=Mode.SUBTRACT,
        )
    return model.part


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    # Surface d'analyse pour le criblage LPBF aval. Le maillage n'est pas le
    # master : il en derive avec une tolerance declaree, et c'est cette
    # tolerance qui borne ce que le criblage peut affirmer.
    parser.add_argument("--surface", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    report = geometry_screen()
    if args.out or args.surface:
        from build123d import export_step, export_stl, import_step

        solid = build_solid()
        expected = float(report["results"]["analytic_volume_mm3"])
        if not solid.is_valid or abs(solid.volume - expected) > 0.01:
            raise SystemExit(
                f"BREP invalide ou volume incohérent: OCCT={solid.volume}, analytique={expected}"
            )
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            export_step(solid, str(args.out))
            roundtrip = import_step(str(args.out))
            if (
                not roundtrip.is_valid
                or len(roundtrip.solids()) != 1
                or abs(roundtrip.volume - expected) > 0.01
            ):
                raise SystemExit("Le STEP relu par OCCT ne reproduit pas le solide attendu.")
            report["step_roundtrip"] = {
                "status": "passed",
                "valid_brep": True,
                "solid_count": len(roundtrip.solids()),
                "volume_mm3": roundtrip.volume,
                "maximum_volume_delta_mm3": 0.01,
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
                "tolerance_mm": 0.03,
                "angular_tolerance_rad": 0.08,
                "sha256": sha256(args.surface),
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
