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
DEFAULT_BOLT_SPAN_MM = 100.0
DEFAULT_PLAN_AREA_CM2 = 90.0
DEFAULT_THICKNESS_MM = 5.0
DEFAULT_DELTA_T_K = 100.0

# Le manuel d'atelier serre le couvercle de carter de chaine a 9,7 Nm, ce qui
# situe la visserie en M6. Percages de passage ISO 273 pour M6.
DEFAULT_BOLT_DIAMETER_MM = 6.0
CLEARANCE_HOLES_M6_MM = {"fin": 6.4, "moyen": 6.6, "large": 7.0}
DEFAULT_CLEARANCE_HOLE_MM = CLEARANCE_HOLES_M6_MM["moyen"]

# Origine de la dilatation relative. La planche 103-05 porte une douille de
# centrage, 993 105 175 00 : si elle existe sur ce couvercle, c'est elle le
# point fixe, et non le centre du semis de vis.
DATUM_CENTROID = "centroid"
DATUM_DOWEL = "dowel"


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
        "break_even_against_foundry_fat": {
            "question": (
                "La vraie question n'est pas « le titane est-il plus lourd que "
                "l'aluminium a epaisseur egale » — il l'est. C'est : de combien "
                "l'epaisseur coulee depasse-t-elle ce que la raideur exige ?"
            ),
            "required_thickness_ratio_for_titanium_to_win": (
                ALUMINIUM["density_g_cm3"]
                / (TITANIUM["density_g_cm3"] * equal_stiffness)
            ),
            "foundry_fat_needed_percent": (
                1.0
                / (
                    ALUMINIUM["density_g_cm3"]
                    / (TITANIUM["density_g_cm3"] * equal_stiffness)
                )
                - 1.0
            )
            * 100.0,
            "reading": (
                "Le titane usine a la raideur strictement necessaire est plus "
                "leger que la fonte des que celle-ci porte environ 40 % "
                "d'epaisseur de plus que sa propre exigence de raideur. Sur une "
                "piece de fonderie, paroi minimale coulable et depouille "
                "comprises, ce n'est pas une hypothese extravagante — c'est "
                "meme le cas courant."
            ),
            "how_to_test_it_cheaply": (
                "LN Engineering usine ce meme couvercle dans du 6061 massif, "
                "sans aucune contrainte de fonderie. Son epaisseur, comparee a "
                "celle de la piece d'origine, mesure directement le gras de "
                "fonderie. Deux cotes, et la question est tranchee."
            ),
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
    bolt_span_mm: float,
    plan_area_cm2: float,
    thickness_mm: float,
    delta_t_k: float,
    bolt_diameter_mm: float,
    clearance_hole_mm: float,
    datum: str,
    measured: bool,
) -> dict[str, object]:
    volume_cm3 = plan_area_cm2 * thickness_mm / 10.0

    mass_al_g = volume_cm3 * ALUMINIUM["density_g_cm3"]
    mass_ti_g = volume_cm3 * TITANIUM["density_g_cm3"]

    # Ce qui compte n'est pas la dilatation totale de la portee, c'est le
    # **deplacement relatif au percage le plus eloigne du point fixe**. Les deux
    # pieces se dilatent autour de ce point ; a un rayon r, l'ecart vaut
    # r * (alpha_al - alpha_ti) * delta_T. Comparer une dilatation de portee
    # entiere a un jeu radial, comme le faisait la premiere version de ce
    # criblage, surestimait le probleme d'un facteur deux.
    #
    # Le rayon retenu depend du point fixe. Sans centrage, l'assemblage se
    # centre de lui-meme et le pire rayon vaut la demi-portee. Avec une douille
    # de centrage en bord de piece, le point fixe est la douille et le pire
    # rayon vaut la portee entiere.
    worst_radius_mm = bolt_span_mm if datum == DATUM_DOWEL else bolt_span_mm / 2.0
    delta_alpha = ALUMINIUM["expansion_per_k"] - TITANIUM["expansion_per_k"]
    relative_shift_mm = worst_radius_mm * delta_alpha * delta_t_k

    growth_al_mm = ALUMINIUM["expansion_per_k"] * bolt_span_mm * delta_t_k
    growth_ti_mm = TITANIUM["expansion_per_k"] * bolt_span_mm * delta_t_k

    # Jeu radial au percage : le fut de vis peut s'ecarter de la moitie de la
    # difference des diametres avant de toucher.
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
            "extreme_hole_span": bolt_span_mm,
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
            "datum": datum,
            "worst_radius_mm": worst_radius_mm,
            "aluminium_free_growth_over_span_mm": growth_al_mm,
            "titanium_free_growth_over_span_mm": growth_ti_mm,
            "relative_shift_at_worst_hole_mm": relative_shift_mm,
            "available_play_at_hole_mm": available_play_mm,
            "play_covers_shift": available_play_mm >= relative_shift_mm,
            "margin_mm": available_play_mm - relative_shift_mm,
            "utilisation_of_play": (
                relative_shift_mm / available_play_mm if available_play_mm else None
            ),
            "clearance_holes_m6_mm": CLEARANCE_HOLES_M6_MM,
            "equations": {
                "relative_shift": "delta = r * (alpha_al - alpha_ti) * delta_T",
                "worst_radius_without_dowel": "r = span / 2",
                "worst_radius_with_dowel": "r = span",
                "available_play": "(clearance_hole - bolt_diameter) / 2",
            },
            "assembly_assumption": (
                "Les vis sont supposees centrees dans leurs percages au montage "
                "a froid. Une vis deja en appui du mauvais cote au montage "
                "n'aurait aucun jeu : la moitie de la marge affichee est une "
                "tolerance de montage, pas une reserve de calcul."
            ),
            "interpretation": (
                "Le carter en aluminium se dilate deux fois et demie plus que le "
                "couvercle en titane. Ce qui doit tenir dans le jeu de percage "
                "n'est pas leur dilatation, c'est leur **ecart au percage le plus "
                "eloigne du point fixe**. Sur un petit couvercle il est faible ; "
                "sur un carter entier, ou sur une piece centree par une douille "
                "en bord, il double et devient redhibitoire."
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
    parser.add_argument("--bolt-span-mm", type=float, default=DEFAULT_BOLT_SPAN_MM)
    parser.add_argument("--plan-area-cm2", type=float, default=DEFAULT_PLAN_AREA_CM2)
    parser.add_argument("--thickness-mm", type=float, default=DEFAULT_THICKNESS_MM)
    parser.add_argument("--delta-t-k", type=float, default=DEFAULT_DELTA_T_K)
    parser.add_argument("--bolt-diameter-mm", type=float, default=DEFAULT_BOLT_DIAMETER_MM)
    parser.add_argument("--clearance-hole-mm", type=float, default=DEFAULT_CLEARANCE_HOLE_MM)
    parser.add_argument("--datum", choices=(DATUM_CENTROID, DATUM_DOWEL), default=DATUM_CENTROID)
    parser.add_argument(
        "--measured",
        action="store_true",
        help="Declarer que les cotes viennent d'une mesure et non d'une hypothese.",
    )
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    report = screen(
        args.bolt_span_mm,
        args.plan_area_cm2,
        args.thickness_mm,
        args.delta_t_k,
        args.bolt_diameter_mm,
        args.clearance_hole_mm,
        args.datum,
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
