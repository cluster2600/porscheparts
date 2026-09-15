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
# La piece d'origine est en MAGNESIUM coule, pas en aluminium. Plusieurs
# sources independantes le donnent, et la raison d'etre du marche du billet est
# justement que ces couvercles se corrodent, se piquent et finissent par ne plus
# etancher. C'est la matiere d'origine, donc la reference de toute comparaison.
MAGNESIUM = {
    "name": "magnesium coule, nuance d'origine non identifiee",
    "density_g_cm3": 1.81,
    "expansion_per_k": 26.0e-6,
    "elastic_modulus_gpa": 45.0,
    "yield_strength_mpa": 160.0,
    "properties_scope": "valeurs de criblage pour un alliage de magnesium coule courant",
    "known_failure_mode": (
        "corrosion : le couvercle se pique sur sa portee, et aucun joint "
        "n'etanche contre une portee piquee"
    ),
}

# L'aluminium billet est la reponse du marche, pas la matiere d'origine.
ALUMINIUM = {
    "name": "aluminium 6061 billet, reponse du marche de la rechange",
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


# Le magnesium de 1995 et celui d'aujourd'hui ne sont pas le meme materiau. La
# difference n'est pas le revetement, c'est la **purete** : le fer, le nickel et
# le cuivre forment des sites cathodiques qui corrodent l'alliage de l'interieur.
# Les limites ASTM de l'AZ91D les plafonnent a 0,004 %, 0,001 % et 0,015 %, et la
# haute purete est donnee jusqu'a cent fois plus resistante que le standard.
MAGNESIUM_MODERN = {
    "name": "magnesium moderne : alliage haute purete, PEO",
    "density_g_cm3": 1.81,
    "expansion_per_k": 26.0e-6,
    "elastic_modulus_gpa": 45.0,
    "yield_strength_mpa": 160.0,
    "impurity_limits_astm_az91d_percent": {"Fe": 0.004, "Ni": 0.001, "Cu": 0.015},
    "corrosion_gain_versus_standard_purity": "jusqu'a 100x, ASTM B117",
    "surface_treatment": (
        "oxydation par plasma electrolytique, aussi dite PEO ou MAO : couche "
        "ceramique, sans chrome hexavalent, conforme REACH"
    ),
    "what_it_replaced": (
        "la chromatation au chrome hexavalent, technologie de reference en 1995, "
        "aujourd'hui sous autorisation REACH"
    ),
}


def index_pair(card: dict) -> dict[str, float]:
    return {
        "stiffness_limited_E13_over_rho": card["elastic_modulus_gpa"] ** (1 / 3)
        / card["density_g_cm3"],
        "strength_limited_sqrt_sigma_over_rho": card["yield_strength_mpa"] ** 0.5
        / card["density_g_cm3"],
    }


def against_the_real_incumbent() -> dict[str, object]:
    """Le titane compare a la matiere d'origine, qui est le magnesium.

    Tout le raisonnement de masse mene jusqu'ici opposait le titane a de
    l'aluminium. C'etait comparer au produit de rechange, pas a la piece
    d'origine. Contre du magnesium a 1,81 g/cm3, le titane perd les deux
    arbitrages, y compris celui de la resistance.
    """
    mg = index_pair(MAGNESIUM)
    al = index_pair(ALUMINIUM)
    ti = index_pair(TITANIUM)
    return {
        "incumbent": MAGNESIUM["name"],
        "incumbent_failure_mode": MAGNESIUM["known_failure_mode"],
        "density_penalty_vs_magnesium": TITANIUM["density_g_cm3"]
        / MAGNESIUM["density_g_cm3"],
        "indices": {"magnesium": mg, "aluminium_billet": al, "titanium": ti},
        "titanium_beats_magnesium_on_stiffness": ti[
            "stiffness_limited_E13_over_rho"
        ]
        > mg["stiffness_limited_E13_over_rho"],
        "titanium_beats_magnesium_on_strength": ti[
            "strength_limited_sqrt_sigma_over_rho"
        ]
        > mg["strength_limited_sqrt_sigma_over_rho"],
        "verdict_on_mass": (
            "Le titane est 2,45 fois plus dense que le magnesium d'origine. Il "
            "perd l'arbitrage de raideur tres largement, et il perd aussi celui "
            "de resistance, de peu. L'argument « plus resistant donc moins "
            "epais donc plus leger », valable contre l'aluminium, ne tient pas "
            "contre le magnesium : sa densite est trop basse pour etre "
            "rattrapee."
        ),
        "what_titanium_does_win": (
            "La corrosion. Le mode de defaillance de la piece d'origine est "
            "que sa portee se pique et cesse d'etancher. Un couvercle titane ne "
            "se pique pas. C'est le deuxieme critere de TITANIUM.md, "
            "« corrosion problematique avec la matiere d'origine », et il est "
            "ici au coeur du sujet — pas la masse."
        ),
        "the_1995_versus_today_reframing": {
            "question": (
                "La piece d'origine ne se corrode pas parce qu'elle est en "
                "magnesium. Elle se corrode parce qu'elle est en magnesium **de "
                "1995** : purete standard, chromatation au chrome hexavalent."
            ),
            "what_changed": {
                "alliage": (
                    "purete standard -> haute purete, fer, nickel et cuivre "
                    "plafonnes ; jusqu'a 100x de gain au brouillard salin"
                ),
                "traitement": (
                    "chromatation hexavalente -> PEO/MAO, couche ceramique "
                    "conforme REACH"
                ),
                "mecanisme": "barriere passive -> revetements actifs, sol-gel",
            },
            "consequence": (
                "Un couvercle en magnesium moderne bat le titane et l'aluminium "
                "sur les deux indices de flexion de plaque, supprime totalement "
                "le couple galvanique puisqu'il est de meme nature que le carter, "
                "annule la dilatation differentielle, et traite le mode de "
                "defaillance a sa racine au lieu de le contourner. C'est la "
                "matiere d'origine, faite correctement."
            ),
            "the_real_obstacles": [
                "L'usinage du magnesium demande un atelier equipe : les copeaux fins sont inflammables, et tous les tourneurs ne le prennent pas.",
                "Le PEO depose 5 a 40 um : sur un plan de joint cela se masque ou se reprend apres traitement.",
                "La plaque corroyee courante est en AZ31B, pas en AZ91E de fonderie : l'alliage disponible n'est pas celui d'origine.",
                "Aucune de ces trois questions n'est instruite ici.",
            ],
        },
        "the_catch": (
            "Le couvercle se boulonne sur un carter lui aussi en magnesium. Le "
            "magnesium est le plus anodique des metaux de structure et le "
            "titane l'un des plus cathodiques : c'est le couple galvanique le "
            "plus defavorable de la liste, et TITANIUM.md nomme explicitement "
            "le magnesium. Le joint isole les portees, pas la visserie ni les "
            "chemins d'humidite. Un couvercle titane pourrait donc proteger "
            "sa propre portee tout en aggravant l'attaque du carter en face."
        ),
    }


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

    # Indices de performance d'une plaque en flexion, formulation d'Ashby. Pour
    # une plaque de contour impose dont on ajuste l'epaisseur, le meilleur
    # materiau maximise :
    #   - raideur imposee   : E^(1/3) / rho
    #   - resistance imposee: sigma^(1/2) / rho
    # Les deux exposants different, et c'est toute l'affaire : l'aluminium gagne
    # le premier, le titane gagne le second.
    index_stiffness_al = ALUMINIUM["elastic_modulus_gpa"] ** (1 / 3) / ALUMINIUM["density_g_cm3"]
    index_stiffness_ti = TITANIUM["elastic_modulus_gpa"] ** (1 / 3) / TITANIUM["density_g_cm3"]
    index_strength_al = ALUMINIUM["yield_strength_mpa"] ** 0.5 / ALUMINIUM["density_g_cm3"]
    index_strength_ti = TITANIUM["yield_strength_mpa"] ** 0.5 / TITANIUM["density_g_cm3"]

    return {
        "performance_indices_plate_in_bending": {
            "method": "indices d'Ashby pour une plaque de contour impose, epaisseur libre",
            "stiffness_limited": {
                "index": "E^(1/3) / rho",
                "aluminium": index_stiffness_al,
                "titanium": index_stiffness_ti,
                "titanium_over_aluminium": index_stiffness_ti / index_stiffness_al,
                "winner": "aluminium",
            },
            "strength_limited": {
                "index": "sigma_y^(1/2) / rho",
                "aluminium": index_strength_al,
                "titanium": index_strength_ti,
                "titanium_over_aluminium": index_strength_ti / index_strength_al,
                "winner": "titane",
            },
            "why_it_flips": (
                "La raideur d'une plaque varie en t^3 et la resistance en t^2. "
                "Un materiau plus rigide se rattrape donc a la puissance un "
                "tiers, un materiau plus resistant a la puissance un demi. Le "
                "titane n'est que 1,63 fois plus rigide que l'aluminium mais "
                "environ 4,6 fois plus resistant : il perd le premier "
                "arbitrage et gagne largement le second. Dire « le titane est "
                "plus resistant donc moins epais » est exact — a condition que "
                "ce soit la resistance qui dimensionne."
            ),
            "specific_stiffness_note": (
                "A raideur en traction, E/rho vaut 25,9 pour l'aluminium et "
                "25,7 pour le titane : ils sont equivalents. Ce n'est qu'en "
                "flexion de plaque, ou l'exposant est un tiers, que "
                "l'aluminium prend l'avantage."
            ),
        },
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
        "against_the_real_incumbent": against_the_real_incumbent(),
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
