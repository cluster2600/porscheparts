#!/usr/bin/env python3
"""Couvercle de carter de chaine en Ti-6Al-4V : ce qui se calcule sans la piece.

La piece n'est pas mesuree. Trois questions se tranchent quand meme, et ce sont
celles qui decident si le titane est viable ici :

1. **la masse** — le titane est plus dense que l'aluminium ; a geometrie egale il
   est plus lourd, et l'epaisseur d'un couvercle est fixee par la planeite
   d'etancheite, pas par la resistance, donc on ne peut pas l'amincir ;
2. **la dilatation differentielle** — un couvercle en titane sur un carter en
   aluminium ne bouge pas a la meme vitesse ; il faut savoir de combien, et si
   le jeu de percage l'absorbe ;
3. **le couple galvanique** — et la, le joint d'origine est deja l'isolant.

Toutes les cotes sont parametrees. Tant qu'un exemplaire n'est pas mesure, les
valeurs par defaut sont des hypotheses declarees, et le rapport le dit.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

PART_ID = "993-ENG-CHAIN-CASE-LID-TI-F0-0001"
OEM_REFERENCE = "964 105 107 01"

# Cartes matiere de criblage, valeurs ambiantes de reference.
ALUMINIUM = {
    "name": "aluminium de fonderie, nuance d'origine non identifiee",
    "density_g_cm3": 2.70,
    "expansion_per_k": 23.0e-6,
    "elastic_modulus_gpa": 70.0,
    "yield_strength_mpa": 180.0,
    "properties_scope": "valeurs de criblage pour un alliage de fonderie courant, la nuance d'origine n'etant pas identifiee",
}
TITANIUM = {
    "name": "Ti-6Al-4V Grade 5, plaque",
    "density_g_cm3": 4.43,
    "expansion_per_k": 8.6e-6,
    "elastic_modulus_gpa": 114.0,
    "yield_strength_mpa": 830.0,
    "properties_scope": "valeurs corroyees de reference pour plaque recuite",
}

# Hypotheses a remplacer par la mesure. Elles sont la pour que le calcul tourne,
# pas pour decrire la piece.
DEFAULT_BOLT_CIRCLE_MM = 100.0
DEFAULT_PLAN_AREA_CM2 = 90.0
DEFAULT_THICKNESS_MM = 5.0
DEFAULT_DELTA_T_K = 100.0
DEFAULT_BOLT_DIAMETER_MM = 8.0
DEFAULT_CLEARANCE_HOLE_MM = 8.4


def thickness_equivalence(thickness_mm: float) -> dict[str, object]:
    """A quelle epaisseur le titane egale-t-il l'aluminium, et sur quel critere ?

    Un couvercle boulonne n'est pas dimensionne par une seule chose, et la
    reponse change du tout au tout selon le critere retenu.

    - a **raideur en flexion egale**, D = E t^3 / 12(1-nu^2), donc
      t_ti / t_al = (E_al / E_ti)^(1/3) ;
    - a **resistance en flexion egale**, sigma = 6 M / t^2, donc
      t_ti / t_al = sqrt(sigma_al / sigma_ti) ;
    - a **masse egale**, t_ti / t_al = rho_al / rho_ti, et il reste a regarder
      ce qu'il reste de raideur a cette epaisseur-la.
    """
    e_ratio = ALUMINIUM["elastic_modulus_gpa"] / TITANIUM["elastic_modulus_gpa"]
    s_ratio = ALUMINIUM["yield_strength_mpa"] / TITANIUM["yield_strength_mpa"]
    rho_ratio = ALUMINIUM["density_g_cm3"] / TITANIUM["density_g_cm3"]

    equal_stiffness = e_ratio ** (1.0 / 3.0)
    equal_strength = s_ratio ** 0.5
    equal_mass = rho_ratio

    def mass_ratio(t_ratio: float) -> float:
        return t_ratio * TITANIUM["density_g_cm3"] / ALUMINIUM["density_g_cm3"]

    # Raideur relative a l'epaisseur d'egale masse : E t^3 compare a l'origine.
    stiffness_at_equal_mass = (1.0 / e_ratio) * equal_mass ** 3

    return {
        "criterion_matters": (
            "Le couvercle peut etre plus mince en titane. De combien depend "
            "entierement du critere qui le dimensionne, et les trois reponses "
            "ne vont pas dans le meme sens."
        ),
        "equal_bending_stiffness": {
            "thickness_ratio": equal_stiffness,
            "thickness_mm": thickness_mm * equal_stiffness,
            "mass_ratio_vs_aluminium": mass_ratio(equal_stiffness),
            "equation": "t_ti/t_al = (E_al/E_ti)^(1/3)",
            "verdict": "plus mince, mais encore plus lourd",
        },
        "equal_bending_strength": {
            "thickness_ratio": equal_strength,
            "thickness_mm": thickness_mm * equal_strength,
            "mass_ratio_vs_aluminium": mass_ratio(equal_strength),
            "equation": "t_ti/t_al = sqrt(sigma_al/sigma_ti)",
            "verdict": "nettement plus mince et plus leger",
        },
        "equal_mass": {
            "thickness_ratio": equal_mass,
            "thickness_mm": thickness_mm * equal_mass,
            "remaining_bending_stiffness_fraction": stiffness_at_equal_mass,
            "verdict": "a masse egale il ne reste qu'une fraction de la raideur d'origine",
        },
        "what_decides": (
            "Si le couvercle est dimensionne par sa raideur, donc par la tenue "
            "du plan de joint entre vis, le titane reste plus lourd. S'il est "
            "dimensionne par sa resistance, il devient plus leger d'un quart. "
            "Et il existe un troisieme cas, le plus probable sur une piece de "
            "fonderie : l'epaisseur d'origine n'est dictee ni par l'une ni par "
            "l'autre, mais par la fonderie elle-meme — paroi minimale, "
            "depouille, remplissage. Une piece fraisee n'a aucune de ces "
            "contraintes. Dans ce cas le titane peut etre plus mince que la "
            "fonte tout en restant plus raide qu'il ne faut."
        ),
        "how_to_settle_it": (
            "Mesurer l'epaisseur d'origine, D03, et regarder la piece : une "
            "epaisseur uniforme genereuse avec des conges larges trahit la "
            "fonderie ; des zones minces et des nervures trahissent un "
            "dimensionnement. Le calcul ne tranchera pas a la place de l'oeil."
        ),
        "material_cards": {"aluminium": ALUMINIUM, "titanium": TITANIUM},
    }


def screen(
    bolt_circle_mm: float,
    plan_area_cm2: float,
    thickness_mm: float,
    delta_t_k: float,
    bolt_diameter_mm: float,
    clearance_hole_mm: float,
    measured: bool,
) -> dict[str, object]:
    volume_cm3 = plan_area_cm2 * thickness_mm / 10.0

    mass_al_g = volume_cm3 * ALUMINIUM["density_g_cm3"]
    mass_ti_g = volume_cm3 * TITANIUM["density_g_cm3"]

    # Dilatation libre de chaque piece sur la distance entre percages extremes.
    growth_al_mm = ALUMINIUM["expansion_per_k"] * bolt_circle_mm * delta_t_k
    growth_ti_mm = TITANIUM["expansion_per_k"] * bolt_circle_mm * delta_t_k
    differential_mm = growth_al_mm - growth_ti_mm

    # Le jeu disponible est le demi-jeu au percage, puisque l'ecart se partage
    # de part et d'autre du cercle de percage.
    available_play_mm = (clearance_hole_mm - bolt_diameter_mm) / 2.0

    return {
        "schema_version": "1.0.0",
        "part_id": PART_ID,
        "oem_reference": OEM_REFERENCE,
        "status": "f0_parametric_screen_no_measured_geometry",
        "geometry_authority": (
            "mesure d'un exemplaire" if measured else "hypotheses declarees, aucune mesure"
        ),
        "inputs_mm": {
            "bolt_circle_or_extreme_hole_span": bolt_circle_mm,
            "plan_area_cm2": plan_area_cm2,
            "thickness": thickness_mm,
            "bolt_diameter": bolt_diameter_mm,
            "clearance_hole": clearance_hole_mm,
            "delta_t_k": delta_t_k,
        },
        "mass_comparison": {
            "aluminium_g": mass_al_g,
            "titanium_g": mass_ti_g,
            "titanium_penalty_g": mass_ti_g - mass_al_g,
            "titanium_penalty_percent": (mass_ti_g / mass_al_g - 1.0) * 100.0,
            "interpretation": (
                "A **geometrie egale** le titane est plus lourd de 64 %. Mais "
                "l'epaisseur n'a aucune raison de rester egale : voir "
                "thickness_equivalence, qui donne les trois epaisseurs "
                "equivalentes selon le critere retenu. La comparaison a "
                "geometrie egale est le point de depart, pas la conclusion."
            ),
        },
        "thickness_equivalence": thickness_equivalence(thickness_mm),
        "differential_expansion": {
            "aluminium_growth_mm": growth_al_mm,
            "titanium_growth_mm": growth_ti_mm,
            "differential_mm": differential_mm,
            "available_play_at_hole_mm": available_play_mm,
            "play_covers_differential": available_play_mm >= differential_mm,
            "margin_mm": available_play_mm - differential_mm,
            "equations": {
                "free_growth": "delta_L = alpha * L * delta_T",
                "available_play": "(clearance_hole - bolt_diameter) / 2",
            },
            "interpretation": (
                "Le carter en aluminium s'allonge plus que le couvercle en "
                "titane. L'ecart doit tenir dans le jeu de percage, sinon les vis "
                "travaillent en cisaillement et le plan de joint se deplace. Sur "
                "un petit couvercle l'ecart est faible ; c'est sur un carter "
                "entier qu'il devient redhibitoire."
            ),
        },
        "galvanic": {
            "couple": "Ti-6Al-4V cathodique vis-a-vis de l'aluminium du carter",
            "existing_isolation": (
                "Le joint d'origine, reference 964 105 181 01, separe deja les "
                "deux metaux sur tout le plan de joint : l'isolation est dans la "
                "nomenclature, pas a inventer."
            ),
            "remaining_paths": [
                "les vis, si elles sont en contact direct avec les deux pieces",
                "la face exterieure exposee a l'humidite et au sel de route",
            ],
            "mitigation": (
                "Rondelles ou douilles isolantes sous tete, pate anti-grippage, "
                "et anodisation du couvercle. Parades connues et verifiables."
            ),
            "resolved": False,
        },
        "release_blockers": [
            "Aucune cote mesuree : contour, epaisseur, entraxes, percages, portee de joint et centrage sont inconnus.",
            "Le jeu interieur au couvercle, vis-a-vis de la chaine et du tendeur, n'est pas releve.",
            "La planeite exigee du plan de joint et le couple de serrage ne sont pas etablis.",
            "La nuance de l'aluminium d'origine n'est pas identifiee ; 2,70 g/cm3 est une valeur de criblage.",
            "Aucun essai d'etancheite, de cyclage thermique ni de depose-repose repetee.",
        ],
        "manufacturing_decision": {
            "process": "fraisage dans une plaque Ti-6Al-4V",
            "why_not_additive": (
                "Couvercle plan boulonne : ni passage interne, ni sous-ensemble a "
                "consolider, ni noyau impossible. Aucune des trois familles ou "
                "l'additif gagne. Le fraisage est plus rapide, moins cher et plus "
                "precis sur le plan de joint."
            ),
            "critical_feature": "planeite et etat de surface du plan de joint",
        },
        "release_authorized": False,
        "vehicle_fitment_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bolt-circle-mm", type=float, default=DEFAULT_BOLT_CIRCLE_MM)
    parser.add_argument("--plan-area-cm2", type=float, default=DEFAULT_PLAN_AREA_CM2)
    parser.add_argument("--thickness-mm", type=float, default=DEFAULT_THICKNESS_MM)
    parser.add_argument("--delta-t-k", type=float, default=DEFAULT_DELTA_T_K)
    parser.add_argument("--bolt-diameter-mm", type=float, default=DEFAULT_BOLT_DIAMETER_MM)
    parser.add_argument("--clearance-hole-mm", type=float, default=DEFAULT_CLEARANCE_HOLE_MM)
    parser.add_argument(
        "--measured",
        action="store_true",
        help="Declarer que les cotes viennent d'une mesure et non d'une hypothese.",
    )
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    report = screen(
        args.bolt_circle_mm,
        args.plan_area_cm2,
        args.thickness_mm,
        args.delta_t_k,
        args.bolt_diameter_mm,
        args.clearance_hole_mm,
        args.measured,
    )
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
