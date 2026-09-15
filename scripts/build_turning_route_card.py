#!/usr/bin/env python3
"""Route tournage d'une piece de revolution, fail-closed.

Pendant de `build_process_route_card.py` pour une piece qui n'a aucune raison
d'etre imprimee. Les portes changent avec le procede : ce qui compte ici n'est
ni l'ilot ni le depoudrage, mais la barre disponible, la prise de piece, l'arete
cassee, et surtout la **cote d'ajustement** — celle qui decide si la bague tient
dans son logement, et que le depot ne mesure pas.

Le dossier ecrit est une demande de devis. Il n'autorise aucun montage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

# Diametres de barre courants au-dessus de 30,5 mm, en millimetres.
STOCK_BAR_DIAMETERS_MM = (32.0, 35.0, 36.0, 40.0)

# Surepaisseur radiale minimale pour un tournage de finition propre sur la peau
# de barre. Valeur d'atelier, volontairement conservatrice, a confirmer.
RADIAL_CLEANUP_MM = 0.5


class RouteError(RuntimeError):
    """Erreur controlee de la construction de route."""


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RouteError(f"expected_object:{path.name}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def gate(name: str, ok: bool, statement: str, blocker: str = "") -> dict[str, Any]:
    entry: dict[str, Any] = {"gate": name, "pass": bool(ok), "statement": statement}
    if not ok:
        entry["blocker"] = blocker or statement
    return entry


def smallest_bar(required_mm: float) -> float | None:
    for diameter in STOCK_BAR_DIAMETERS_MM:
        if diameter >= required_mm:
            return diameter
    return None


def build_route(
    part: dict[str, Any],
    screen: dict[str, Any],
    process: dict[str, Any],
) -> dict[str, Any]:
    dimensions = screen["source_dimensions_mm"]
    results = screen["results"]

    outer_diameter = float(dimensions["outer_diameter"])
    depth = float(dimensions["depth"])
    thinnest_wall = min(
        float(results["front_radial_wall_mm"]), float(results["rear_radial_wall_mm"])
    )
    part_volume = float(results["analytic_volume_mm3"])

    required_bar = outer_diameter + 2.0 * RADIAL_CLEANUP_MM
    bar = smallest_bar(required_bar)
    slug_volume = (
        math.pi * (bar / 2.0) ** 2 * (depth + 2.0) if bar else float("nan")
    )

    finish = process["surface_and_finish"]
    anodising_range = finish["anodising_thickness_um_typical_range"]

    gates = [
        gate(
            "bar_stock_covers_outer_diameter",
            bar is not None,
            f"Une barre de {bar:.0f} mm couvre le diametre exterieur de "
            f"{outer_diameter:.1f} mm avec {RADIAL_CLEANUP_MM:.1f} mm de "
            "surepaisseur radiale de reprise de peau."
            if bar
            else "",
            "Aucun diametre de barre courant ne couvre la piece.",
        ),
        gate(
            "bore_accessible_to_boring_bar",
            depth / float(dimensions["front_inner_diameter"]) < 3.0,
            f"L'alesage a un elancement de {depth / float(dimensions['front_inner_diameter']):.2f}, "
            "sans difficulte de porte-a-faux.",
        ),
        gate(
            "alloy_selected_against_governing_requirement",
            process["selection_rationale"]["governing_requirement"] == "appearance",
            "La nuance est choisie sur le critere qui gouverne la piece, l'aspect, "
            "et non sur la matiere la mieux documentee du depot.",
        ),
        gate(
            "visible_surface_finish_specified",
            "machined_ra_um_target_on_visible_faces" in finish,
            f"Un Ra cible de {finish.get('machined_ra_um_target_on_visible_faces')} um "
            "est fixe sur les faces visibles avant anodisation.",
        ),
        gate(
            "thin_wall_workholding_reviewed",
            False,
            "La prise de piece est revue.",
            f"La paroi la plus mince vaut {thinnest_wall:.2f} mm, soit "
            f"{thinnest_wall / outer_diameter * 100.0:.1f} % du diametre exterieur. "
            "Un serrage en mors durs sur cette bague peut l'ovaliser, et la "
            "tronconnage final la liberer deformee. Mors doux, bague de serrage "
            "ou reprise sur mandrin expansible sont a arbitrer par le tourneur.",
        ),
        gate(
            "edge_break_specified",
            False,
            "Les arêtes sont definies.",
            "Le maitre parametrique a des arêtes vives. Une bague decorative se "
            "juge d'abord sur son arête avant, et une arête vive s'anodise mal et "
            "coupe au montage. Chanfrein ou rayon avant, arriere et d'alesage "
            "restent a decider puis a porter au modele.",
        ),
        gate(
            "fit_dimension_toleranced",
            False,
            "La cote d'ajustement porte une tolerance.",
            f"Le diametre exterieur de {outer_diameter:.1f} mm est la cote qui "
            "decide du maintien dans le tableau de bord, et il n'a aucune "
            "tolerance. Il vient d'une page de vente d'une bague adaptable, pas "
            "d'une mesure du logement. Sans ouverture mesuree, aucune tolerance "
            "ne peut etre prescrite honnetement.",
        ),
        gate(
            "anodising_growth_subtracted_from_fit",
            False,
            "La croissance d'anodisation est retranchee de la cote usinee.",
            f"Une couche de {anodising_range[0]:.0f} a {anodising_range[1]:.0f} um "
            "croit pour moitie vers l'exterieur, soit environ "
            f"{anodising_range[0] / 1000.0:.3f} a {anodising_range[1] / 1000.0:.3f} mm "
            "sur le diametre. C'est du meme ordre que le jeu recherche : la "
            "correction ne peut etre appliquee qu'une fois la porte precedente "
            "ouverte.",
        ),
        gate(
            "material_certificate_contracted",
            False,
            "Le certificat matiere est engage.",
            "Ni nuance certifiee, ni etat metallurgique verifie ne sont engages "
            "avec un tourneur.",
        ),
    ]

    blocking = [entry for entry in gates if not entry["pass"]]

    derived: dict[str, Any] = {
        "outer_diameter_mm": outer_diameter,
        "depth_mm": depth,
        "thinnest_radial_wall_mm": thinnest_wall,
        "thinnest_wall_fraction_of_outer_diameter": thinnest_wall / outer_diameter,
        "required_bar_diameter_mm": required_bar,
        "selected_bar_diameter_mm": bar,
        "part_volume_mm3": part_volume,
    }
    if bar:
        derived["slug_volume_mm3"] = slug_volume
        derived["material_removed_fraction"] = 1.0 - part_volume / slug_volume
        derived["removal_scope"] = (
            "un tournage part d'un lopin et enleve la difference ; le chiffre est "
            "donne parce qu'il est l'argument habituel en faveur de l'additif, et "
            "qu'il ne suffit pas a le justifier sur une piece de 6 g"
        )

    return {
        "schema_version": "1.0.0",
        "part_id": screen["part_id"],
        "stage_id": "04_material_machine_process_card",
        "route_family": "cnc_turning",
        "status": "passed" if not blocking else "blocked_missing_input",
        "classification": "turning_route_screen_not_a_qualified_manufacturing_route",
        "safety_class": part["classification"]["safety_class"],
        "route": {
            "technology": process["technology"],
            "material": process["material"],
            "material_designations": process["material_designations"],
            "governing_requirement": process["selection_rationale"][
                "governing_requirement"
            ],
            "machining_notes": process["machining_notes"],
            "finishing_route": finish["finishing_route"],
            "anodising": finish["anodising"],
        },
        "derived": derived,
        "gates": gates,
        "blocking_gate_count": len(blocking),
        "fit_strategy": {
            "problem": (
                "L'ouverture du tableau de bord n'est pas mesuree, et le diametre "
                "exterieur est repris d'une page de vente."
            ),
            "proposal": (
                "Sur une piece tournee, la deuxieme et la troisieme coutent une "
                "fraction de la premiere. Commander trois bagues nues, non "
                "anodisees, a trois diametres exterieurs echelonnes, essayer, "
                "puis n'anodiser que la bonne — en retranchant alors la "
                "croissance de couche."
            ),
            "candidate_outer_diameters_mm": [30.40, 30.50, 30.60],
            "why_not_simply_measure": (
                "Mesurer le logement reste preferable et reste a faire. La serie "
                "de trois est ce qui permet d'avancer sans metrologie du "
                "vehicule, pas ce qui la remplace."
            ),
        },
        "vehicle_fitment_authorized": False,
        "authorization_note": (
            "Cette carte fixe une nuance et une intention de finition. Elle ne "
            "contient ni gamme d'usinage, ni capabilite mesuree, ni certificat, "
            "et n'autorise aucun montage."
        ),
    }


def render_rfq(card: dict[str, Any], part: dict[str, Any], inputs: dict[str, Any]) -> str:
    route = card["route"]
    derived = card["derived"]
    fit = card["fit_strategy"]
    lines = [
        f"# Demande de devis, tournage — {card['part_id']}",
        "",
        f"**{part['name']}**",
        "",
        "Demande de devis et de faisabilite, pas un ordre de fabrication. La piece",
        f"est classee `{card['safety_class']}`. Le fournisseur est invite a contredire",
        "ce qui suit, en particulier le choix de nuance.",
        "",
        "## 1. Ce qui est fourni",
        "",
        "| fichier | role | SHA-256 |",
        "|---|---|---|",
    ]
    for name, (role, digest) in inputs.items():
        lines.append(f"| `{name}` | {role} | `{digest}` |")
    lines += [
        "",
        "Le STEP est le maitre. **Il porte des arêtes vives et aucune tolerance** :",
        "les deux points sont ouverts ci-dessous et font partie de la question posee.",
        "",
        "## 2. Route demandee",
        "",
        "| poste | valeur |",
        "|---|---|",
        f"| procede | {route['technology']} |",
        f"| nuance | **{route['material']}** |",
        f"| designations | {', '.join(route['material_designations'])} |",
        f"| barre | Ø{derived['selected_bar_diameter_mm']:.0f} mm |",
        f"| diametre exterieur | {derived['outer_diameter_mm']:.1f} mm |",
        f"| profondeur | {derived['depth_mm']:.1f} mm |",
        f"| paroi la plus mince | {derived['thinnest_radial_wall_mm']:.2f} mm |",
        f"| finition | {route['finishing_route']} |",
        f"| anodisation | {route['anodising']} |",
        "",
        "**Pourquoi le 6063 et pas le 6061.** La piece est visible et ne porte rien :",
        "le critere qui gouverne est l'aspect. Le 6063 est la nuance de reference de",
        "l'anodisation brillante. Nous savons que c'est le moins agreable des deux a",
        "tourner :",
        "",
    ]
    lines += [f"- {note}" for note in route["machining_notes"]]
    lines += [
        "",
        "Si votre atelier juge le 6063 deraisonnable pour cette piece, dites-le et",
        "chiffrez le 6061 T6 en regard, en indiquant ce que l'aspect y perd.",
        "",
        "## 3. Questions ouvertes",
        "",
    ]
    for entry in card["gates"]:
        if not entry["pass"]:
            lines.append(f"- **{entry['gate']}** — {entry['blocker']}")
    lines += [
        "",
        "## 4. La cote d'ajustement, et ce que nous proposons",
        "",
        fit["problem"],
        "",
        fit["proposal"],
        "",
        "Diametres demandes : "
        + ", ".join(f"**{d:.2f} mm**" for d in fit["candidate_outer_diameters_mm"])
        + ", trois pieces nues, non anodisees.",
        "",
        f"_{fit['why_not_simply_measure']}_",
        "",
        "## 5. Livrables attendus avec le devis",
        "",
        "- prix des trois bagues nues, puis prix de l'anodisation d'une seule ;",
        "- prix de la meme piece en 6061 T6, pour comparaison ;",
        "- chanfreins ou rayons d'arête que vous recommandez, et pourquoi ;",
        "- tolerance que votre tour tient reellement sur le diametre exterieur ;",
        "- epaisseur d'anodisation obtenue et sa dispersion ;",
        "- certificat matiere de la barre ;",
        "- delai.",
        "",
        "## 6. Reserve",
        "",
        "Les cotes proviennent d'une fiche commerciale d'une bague adaptable, pas",
        "d'un plan d'origine ni d'une mesure. Aucune piece issue de ce devis ne doit",
        "etre consideree comme conforme a l'origine.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog-part", type=Path, required=True)
    parser.add_argument("--part-screen", type=Path, required=True)
    parser.add_argument("--process-card", type=Path, required=True)
    parser.add_argument("--master", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    part = load_json(args.catalog_part)
    screen = load_json(args.part_screen)
    process = load_json(args.process_card)

    published = screen.get("step_roundtrip", {}).get("sha256")
    if published and published != sha256(args.master):
        raise SystemExit(
            f"empreinte_divergente:{args.master.name}: le criblage ne decrit pas ce fichier."
        )

    card = build_route(part, screen, process)
    rfq = render_rfq(
        card,
        part,
        {args.master.name: ("maitre STEP", sha256(args.master))},
    )

    slug = card["part_id"].lower()
    card_path = args.output / f"{slug}-turning-route-card.json"
    rfq_path = args.output / f"{slug}-turning-rfq.md"
    card_text = json.dumps(card, indent=2, ensure_ascii=False) + "\n"

    if args.check:
        for path, expected in ((card_path, card_text), (rfq_path, rfq)):
            if not path.exists():
                raise SystemExit(f"absent:{path}")
            if path.read_text(encoding="utf-8") != expected:
                raise SystemExit(f"perime:{path}")
        print(f"route tournage a jour: {card['part_id']} status={card['status']}")
        return 0

    args.output.mkdir(parents=True, exist_ok=True)
    card_path.write_text(card_text, encoding="utf-8")
    rfq_path.write_text(rfq, encoding="utf-8")
    print(
        f"{card['part_id']}: status={card['status']} "
        f"portes bloquantes={card['blocking_gate_count']}"
    )
    print(f"  {card_path}")
    print(f"  {rfq_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
