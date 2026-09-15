#!/usr/bin/env python3
"""Concepts F0 des pieces 993 qui n'avaient aucun maitre STEP.

Chaque concept est un solide volontairement simple. Les rares cotes publiees
sont marquees `published` avec leur source ; toutes les autres sont des
**variables de conception** marquees `hypothesis`. Aucun concept ne pretend
reproduire la piece d'origine, et aucun n'autorise une fabrication.

Chaque piece produit `parts/<slug>/derived/<nom>_concept_f0.step` et
`parts/<slug>/evidence/concept-f0.json`. Le STEP est relu et son enveloppe
comparee a celle declaree : un ecart fait echouer le script.

  python3 scripts/build_993_concept_f0.py            # dans l'image cadsim
  python3 scripts/build_993_concept_f0.py --only 993-int-door-pull-0001
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def p(value: float, source: str) -> dict:
    return {"value_mm": value, "authority": "published", "source": source}


def h(value: float, why: str) -> dict:
    return {"value_mm": value, "authority": "hypothesis", "rationale": why}


CONCEPTS = {
    "993-body-front-lid-0001": {
        "stem": "front_lid",
        "shape": "curved_shell",
        "dims": {
            "length": h(1100.0, "longueur de capot supposee, inferieure au porte-a-faux avant"),
            "width": h(1250.0, "largeur supposee, bornee par la largeur caisse publiee"),
            "crown_radius": h(3000.0, "bombe transversal suppose"),
            "skin": h(2.0, "peau composite supposee ; la tole d'origine est estimee a 0,6 mm"),
            "vehicle_width_bound": p(1735.0, "SRC-ASTRA-993-TYPE-APPROVAL-DIMENSIONS"),
        },
    },
    "993-int-dashboard-trim-0001": {
        "stem": "dashboard_trim",
        "shape": "u_channel",
        "dims": {
            "length": h(1350.0, "portee supposee entre montants, bornee par la largeur caisse"),
            "width": h(120.0, "profondeur d'habillage supposee"),
            "height": h(60.0, "hauteur d'habillage supposee"),
            "wall": h(3.0, "paroi composite supposee"),
            "vehicle_width_bound": p(1735.0, "SRC-ASTRA-993-TYPE-APPROVAL-DIMENSIONS"),
        },
    },
    "993-int-door-pull-0001": {
        "stem": "door_pull",
        "shape": "grip_on_posts",
        "dims": {
            "length": h(160.0, "entraxe de prise suppose"),
            "grip_width": h(22.0, "largeur de prise supposee"),
            "grip_thickness": h(18.0, "epaisseur de prise supposee"),
            "post_height": h(35.0, "passage de main suppose"),
        },
    },
    "993-int-seat-rail-cover-0001": {
        "stem": "seat_rail_cover",
        "shape": "u_channel",
        "dims": {
            "length": h(420.0, "longueur de glissiere supposee"),
            "width": h(40.0, "largeur supposee"),
            "height": h(30.0, "hauteur supposee"),
            "wall": h(2.5, "paroi polymere supposee"),
        },
    },
    "993-int-switch-blank-0001": {
        "stem": "switch_blank",
        "shape": "clip_plate",
        "dims": {
            "width": h(21.0, "ouverture declaree d'environ 19 mm, plus 1 mm de recouvrement par cote"),
            "height": h(33.0, "ouverture declaree d'environ 31 mm, plus 1 mm de recouvrement par cote"),
            "face": h(2.5, "epaisseur de face supposee"),
            "tab_length": h(10.0, "longueur de patte supposee"),
            "tab_thickness": h(1.2, "epaisseur de patte supposee"),
            "declared_opening_width": p(19.0, "SRC-RENNLIST-993-DASHBOARD-LIGHTING-DIMENSIONS, valeur declaree de niveau C"),
            "declared_opening_height": p(31.0, "SRC-RENNLIST-993-DASHBOARD-LIGHTING-DIMENSIONS, valeur declaree de niveau C"),
        },
    },
    "993-eng-carrier-0001": {
        "stem": "engine_carrier",
        "shape": "t_blade",
        "dims": {
            "length": h(580.0, "longueur supposee sous le majorant colis"),
            "width": h(45.0, "semelle supposee sous le majorant colis"),
            "height": h(45.0, "hauteur d'ame supposee sous le majorant colis"),
            "wall": h(6.0, "epaisseur supposee ; aucun cas de charge rempli"),
            "envelope_bound": p(600.0, "enveloppe vendeur 600 x 50 x 50 mm, lue comme dimensions de colis"),
        },
    },
    "993-eng-chain-case-0001": {
        "stem": "chain_case",
        "shape": "open_box",
        "dims": {
            "length": h(180.0, "longueur supposee"),
            "width": h(120.0, "largeur supposee"),
            "height": h(60.0, "profondeur supposee"),
            "wall": h(4.0, "paroi de fonderie supposee"),
            "lid_bolt_span": h(100.0, "reprise de la variable de conception du couvercle Ti F0"),
        },
    },
    "993-turbocharger-k16-pair-0001": {
        "stem": "k16_pair",
        "shape": "turbo_pair",
        "dims": {
            "length": p(280.0, "SRC-FVD-993-K16-OEM-DIMENSIONS, encombrement produit par turbo"),
            "width": p(190.0, "SRC-FVD-993-K16-OEM-DIMENSIONS, encombrement produit par turbo"),
            "height": p(210.0, "SRC-FVD-993-K16-OEM-DIMENSIONS, encombrement produit par turbo"),
            "pair_spacing": h(700.0, "entraxe gauche-droite suppose"),
        },
    },
}


def v(concept: dict, key: str) -> float:
    return concept["dims"][key]["value_mm"]


def build(concept: dict):
    from build123d import Align, Box, Cylinder, Pos, Rot

    base = (Align.CENTER, Align.CENTER, Align.MIN)
    shape = concept["shape"]
    if shape == "curved_shell":
        radius, skin = v(concept, "crown_radius"), v(concept, "skin")
        length, width = v(concept, "length"), v(concept, "width")
        ring = Rot(90, 0, 0) * (
            Cylinder(radius + skin, length, align=(Align.CENTER, Align.CENTER, Align.CENTER))
            - Cylinder(radius, length, align=(Align.CENTER, Align.CENTER, Align.CENTER))
        )
        # la corde du bombe a la base de la fenetre vaut exactement la largeur
        base_z = (radius**2 - (width / 2) ** 2) ** 0.5
        crown = radius + skin - base_z
        window = Pos(0, 0, base_z) * Box(width, length, crown, align=base)
        solid = ring & window
        return solid, (width, length, crown)
    if shape == "u_channel":
        length, width, height, wall = (v(concept, k) for k in ("length", "width", "height", "wall"))
        solid = Box(length, width, height, align=base) - Pos(0, 0, -wall) * Box(
            length + 2, width - 2 * wall, height, align=base
        )
        return solid, (length, width, height)
    if shape == "grip_on_posts":
        length, grip_w, grip_t, post = (v(concept, k) for k in ("length", "grip_width", "grip_thickness", "post_height"))
        solid = Pos(0, 0, post) * Box(length, grip_w, grip_t, align=base)
        for side in (-1, 1):
            solid = solid + Pos(side * (length - grip_w) / 2, 0, 0) * Box(grip_w, grip_w, post, align=base)
        return solid, (length, grip_w, post + grip_t)
    if shape == "clip_plate":
        width, height, face = v(concept, "width"), v(concept, "height"), v(concept, "face")
        tab_l, tab_t = v(concept, "tab_length"), v(concept, "tab_thickness")
        solid = Box(width, height, face, align=base)
        for side in (-1, 1):
            solid = solid + Pos(side * (width / 2 - 1.5 - tab_t / 2), 0, face) * Box(tab_t, height * 0.6, tab_l, align=base)
        return solid, (width, height, face + tab_l)
    if shape == "t_blade":
        length, width, height, wall = (v(concept, k) for k in ("length", "width", "height", "wall"))
        solid = Box(length, width, wall, align=base) + Box(length, wall, height, align=base)
        return solid, (length, width, height)
    if shape == "open_box":
        length, width, height, wall = (v(concept, k) for k in ("length", "width", "height", "wall"))
        solid = Box(length, width, height, align=base) - Pos(0, 0, wall) * Box(
            length - 2 * wall, width - 2 * wall, height, align=base
        )
        return solid, (length, width, height)
    if shape == "turbo_pair":
        length, width, height = v(concept, "length"), v(concept, "width"), v(concept, "height")
        spacing = v(concept, "pair_spacing")
        axial = (Align.CENTER, Align.CENTER, Align.MIN)
        radius = width / 2

        def turbo():
            compressor = Rot(0, 90, 0) * Cylinder(radius, 120.0, align=axial)
            core = Pos(120.0, 0, 0) * Rot(0, 90, 0) * Cylinder(40.0, 60.0, align=axial)
            turbine = Pos(180.0, 0, 0) * Rot(0, 90, 0) * Cylinder(85.0, length - 180.0, align=axial)
            wastegate = Pos(230.0, 0, radius) * Box(40.0, 40.0, height - width, align=base)
            return compressor + core + turbine + wastegate

        solid = Pos(-length / 2, -spacing / 2, 0) * turbo() + Pos(-length / 2, spacing / 2, 0) * turbo()
        return solid, (length, spacing + width, height)
    raise ValueError(shape)


def generate(slug: str, concept: dict) -> dict:
    from build123d import export_step, import_step

    solid, expected = build(concept)
    if not solid.is_valid:
        raise SystemExit(f"{slug}: BREP invalide")
    box = solid.bounding_box()
    envelope = [round(box.size.X, 4), round(box.size.Y, 4), round(box.size.Z, 4)]
    if expected and any(abs(a - b) > 0.01 for a, b in zip(envelope, expected)):
        raise SystemExit(f"{slug}: enveloppe {envelope} differente de {list(expected)}")
    step = ROOT / f"parts/{slug}/derived/{concept['stem']}_concept_f0.step"
    step.parent.mkdir(parents=True, exist_ok=True)
    export_step(solid, str(step))
    back = import_step(str(step))
    if not back.is_valid or abs(back.volume - solid.volume) > 1e-3 * solid.volume:
        raise SystemExit(f"{slug}: le STEP relu ne reproduit pas le solide")
    report = {
        "schema_version": "1.0.0",
        "slug": slug,
        "status": "f0_concept_geometry_hypotheses_not_dimensional",
        "shape": concept["shape"],
        "dimensions": concept["dims"],
        "step": {
            "path": str(step.relative_to(ROOT)),
            "sha256": hashlib.sha256(step.read_bytes()).hexdigest(),
            "solid_count": len(back.solids()),
            "volume_mm3": round(back.volume, 3),
            "envelope_mm": envelope,
        },
        "not_claimed": "Aucune forme, interface, fixation, datum ni tolerance d'origine n'est reproduite.",
        "dimensionally_accurate": False,
        "release_authorized": False,
    }
    evidence = ROOT / f"parts/{slug}/evidence/concept-f0.json"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", nargs="*")
    args = parser.parse_args()
    for slug, concept in CONCEPTS.items():
        if args.only and slug not in args.only:
            continue
        report = generate(slug, concept)
        print(slug, report["step"]["envelope_mm"], report["step"]["volume_mm3"], "mm3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
