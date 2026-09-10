#!/usr/bin/env python3
"""Etape 04 du pipeline AM : carte matiere-machine-procede, fail-closed.

Les etapes 02 et 03 disent qu'une geometrie est tranchable. Elles ne disent pas
qu'il existe une **route** : un alliage, une poudre, une machine, une
orientation, une epaisseur de couche, des traitements et des proprietes
dependantes de la temperature qui appartiennent au meme procede qualifie.

Ce script ne fabrique pas cette route. Il confronte le rapport geometrique a la
carte machine et a la carte procede du catalogue, et il **echoue a porte fermee**
sur chaque incoherence ou chaque entree manquante. Le dossier fournisseur qu'il
ecrit est une demande de devis, pas une autorisation d'impression.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


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


GENERIC_MATERIAL_WORDS = {
    "eos",
    "aluminium",
    "aluminum",
    "alloy",
    "alliage",
    "candidate",
    "powder",
    "poudre",
}


def alloy_tokens(label: str) -> frozenset[str]:
    """Reduit un libelle matiere a ses jetons d'alliage significatifs.

    `EOS AlSi10Mg` et `EOS Aluminium AlSi10Mg` designent le meme alliage ; la
    comparaison litterale les separerait a tort. Les qualificatifs de route
    apres un `/` sont deja retires par l'appelant.
    """
    tokens = {
        token.strip(",;()").lower()
        for token in label.replace("-", " ").split()
    }
    return frozenset(token for token in tokens if token and token not in GENERIC_MATERIAL_WORDS)


def gate(name: str, ok: bool, statement: str, blocker: str = "") -> dict[str, Any]:
    entry: dict[str, Any] = {"gate": name, "pass": bool(ok), "statement": statement}
    if not ok:
        entry["blocker"] = blocker or statement
    return entry


def part_volume_mm3(screen: dict[str, Any] | None) -> float | None:
    """Volume du solide, pris au STEP relu et non au maillage facettise."""
    if not screen:
        return None
    roundtrip = screen.get("step_roundtrip", {})
    if "volume_mm3" in roundtrip:
        return float(roundtrip["volume_mm3"])
    results = screen.get("results", {})
    if "analytic_volume_mm3" in results:
        return float(results["analytic_volume_mm3"])
    return None


def build_route(
    part: dict[str, Any],
    geometry: dict[str, Any],
    machine: dict[str, Any],
    process: dict[str, Any],
    screen: dict[str, Any] | None,
) -> dict[str, Any]:
    slicing = geometry["full_build_slicing"]
    thickness = geometry["thickness_screen"]
    reference = process["process_reference"]
    coupons = process["published_as_manufactured_coupon_properties"]

    screened_layer_mm = float(slicing["layer_thickness_mm"])
    qualified_layer_mm = float(reference["layer_thickness_um"]) / 1000.0
    build_height_mm = float(slicing["build_height_mm"])
    minimum_wall_mm = float(reference["minimum_wall_thickness_mm"])
    solid_volume_mm3 = part_volume_mm3(screen)

    gates = [
        gate(
            "machine_identity_consistent",
            machine["model"] == geometry["machine_candidate"]["model"] == process["system"],
            "Le criblage geometrique, la carte machine et la carte procede nomment la meme machine.",
            "Le criblage geometrique et la carte procede ne portent pas sur la meme machine.",
        ),
        gate(
            "material_identity_consistent",
            alloy_tokens(geometry["process_physics"]["target_material_card"].split(" / ")[0])
            == alloy_tokens(process["material"]),
            "L'alliage cible du criblage est celui de la carte procede.",
            "L'alliage cible du criblage n'est pas celui de la carte procede.",
        ),
        gate(
            "layer_thickness_consistent",
            math.isclose(screened_layer_mm, qualified_layer_mm, abs_tol=1e-9),
            f"Le tranchage a {screened_layer_mm * 1000:.0f} um est celui de la route qualifiee.",
            f"Le tranchage a ete conduit a {screened_layer_mm * 1000:.0f} um alors que la seule "
            f"route publiee de cet alliage sur cette machine est a "
            f"{qualified_layer_mm * 1000:.0f} um. Le nombre de couches, la duree et les "
            "proprietes coupon ne se transposent pas d'une epaisseur a l'autre.",
        ),
        gate(
            "screened_wall_above_process_minimum",
            float(thickness["p01_mm"]) >= minimum_wall_mm,
            f"Le premier centile d'epaisseur locale, {float(thickness['p01_mm']):.3f} mm, "
            f"reste au-dessus du minimum procede de {minimum_wall_mm:.2f} mm.",
        ),
        gate(
            "bare_part_fits_machine_envelope",
            bool(slicing["bare_part_nominal_fit"]),
            "La piece nue tient dans l'enveloppe nominale de la machine.",
        ),
        gate(
            "orientation_engineering_reviewed",
            bool(geometry["gates"]["candidate_orientation_engineering_reviewed"]),
            "L'orientation retenue est revue par un ingenieur.",
            "L'orientation vient d'une regle de criblage automatique, pas d'une revue DfAM.",
        ),
        gate(
            "temperature_dependent_constitutive_card_available",
            bool(process["solver_readiness"]["complete_and_calibrated"]),
            "La carte matiere-procede est complete et calibree en temperature.",
            "La carte procede se declare elle-meme incomplete : "
            + " ; ".join(process["solver_readiness"]["missing_inputs"][:3])
            + ".",
        ),
        gate(
            "heat_treatment_route_defined",
            "heat_treatment" in reference,
            "Le traitement thermique appartient a la route publiee.",
            "La carte procede ne publie aucun traitement thermique : detente, revenu "
            "et etat metallurgique de livraison restent a contractualiser.",
        ),
        gate(
            "machining_stock_defined",
            "machining_stock_mm" in reference,
            "Les surepaisseurs d'usinage sont definies.",
            "Aucune surepaisseur d'usinage n'est definie, donc aucune surface "
            "fonctionnelle n'est garantie a la tolerance.",
        ),
        gate(
            "part_allowables_derived_from_coupons",
            False,
            "Des admissibles de piece existent.",
            "Les valeurs publiees sont des coupons EOS as-manufactured "
            f"(Rp0,2 vertical {coupons['vertical_yield_strength_mpa']:.0f} MPa, "
            f"fatigue {coupons['fatigue_strength_mpa']:.0f} MPa a "
            f"{coupons['fatigue_cycles'] / 1e6:.0f} millions de cycles) : ce ne sont "
            "pas des admissibles de cette piece, dans cette orientation, a cet etat "
            "de surface.",
        ),
        gate(
            "powder_lot_traceability_contracted",
            False,
            "La tracabilite du lot de poudre est contractualisee.",
            "Ni lot, ni nombre de reemplois, ni certificat matiere ne sont engages "
            "avec un fournisseur.",
        ),
    ]

    blocking = [entry for entry in gates if not entry["pass"]]
    status = "passed" if not blocking else "blocked_missing_input"

    derived: dict[str, Any] = {
        "screened_layer_thickness_mm": screened_layer_mm,
        "qualified_layer_thickness_mm": qualified_layer_mm,
        "layers_at_screened_thickness": int(slicing["layer_count"]),
        "layers_at_qualified_thickness": math.ceil(build_height_mm / qualified_layer_mm),
        "build_height_mm": build_height_mm,
        "orientation": slicing["orientation"],
        "support_proxy_volume_mm3": float(slicing["support_proxy_volume_mm3"]),
    }
    if solid_volume_mm3:
        deposited = solid_volume_mm3 + derived["support_proxy_volume_mm3"]
        rate = float(reference["volume_rate_mm3_s"])
        derived["deposited_volume_mm3"] = deposited
        derived["exposure_time_hours_at_published_rate"] = deposited / rate / 3600.0
        derived["exposure_time_scope"] = (
            "volume divise par le debit publie : ni recouvrement, ni chauffe, ni "
            "inertage, ni changement de plateau ne sont comptes"
        )
        derived["screening_mass_g"] = (
            solid_volume_mm3 / 1000.0 * float(coupons["density_g_cm3_minimum"])
        )

    return {
        "schema_version": "1.0.0",
        "part_id": geometry["part_id"],
        "stage_id": "04_material_machine_process_card",
        "status": status,
        "classification": (
            "confrontation_of_published_cards_not_a_qualified_process_route"
        ),
        "safety_class": part["classification"]["safety_class"],
        "route": {
            "material": process["material"],
            "material_designations": process["material_designations"],
            "machine": (
                machine["model"]
                if machine["model"].lower().startswith(machine["manufacturer"].lower())
                else f"{machine['manufacturer']} {machine['model']}"
            ),
            "material_set": reference.get("eos_material_set", ""),
            "inert_gas": reference["inert_gas"],
            "build_platform_temperature_c": reference["build_platform_temperature_c"],
            "minimum_wall_thickness_mm": minimum_wall_mm,
            "orientation": slicing["orientation"],
        },
        "derived": derived,
        "gates": gates,
        "blocking_gate_count": len(blocking),
        "metal_print_authorized": False,
        "authorization_note": (
            "Aucune porte de fabrication n'est ouverte par ce fichier. Une route "
            "coherente sur le papier ne remplace ni coupon, ni fichier machine "
            "signe, ni revue d'ingenierie."
        ),
    }


def render_rfq(card: dict[str, Any], part: dict[str, Any], inputs: dict[str, str]) -> str:
    route = card["route"]
    derived = card["derived"]
    lines = [
        f"# Demande de devis — {card['part_id']}",
        "",
        f"**{part['name']}**",
        "",
        "Ce document est une **demande de devis et de faisabilite**, pas un ordre de",
        "fabrication. La piece est classee "
        f"`{card['safety_class']}` et n'est autorisee ni au montage, ni a la vente.",
        "Le fournisseur est invite a contredire ce qui suit.",
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
        "Le STEP est le maitre. Le STL est une surface d'analyse derivee, a tolerance",
        "de corde declaree ; il ne fait pas foi sur la cote.",
        "",
        "## 2. Route candidate",
        "",
        "| poste | valeur |",
        "|---|---|",
        f"| alliage | {route['material']} |",
        f"| designations | {', '.join(route['material_designations'])} |",
        f"| machine | {route['machine']} |",
        f"| jeu de parametres | {route['material_set']} |",
        f"| gaz | {route['inert_gas']} |",
        f"| plateau | {route['build_platform_temperature_c']:.0f} °C |",
        f"| orientation de criblage | `{route['orientation']}` |",
        f"| hauteur de construction | {derived['build_height_mm']:.1f} mm |",
        f"| couches a {derived['qualified_layer_thickness_mm'] * 1000:.0f} µm | "
        f"{derived['layers_at_qualified_thickness']} |",
    ]
    if "screening_mass_g" in derived:
        lines.append(f"| masse de criblage | {derived['screening_mass_g']:.2f} g |")
    if "exposure_time_hours_at_published_rate" in derived:
        lines.append(
            "| temps d'exposition au debit publie | "
            f"{derived['exposure_time_hours_at_published_rate']:.2f} h |"
        )
    lines += [
        "",
        "## 3. Ce que le dossier ne contient pas — questions au fournisseur",
        "",
    ]
    for entry in card["gates"]:
        if not entry["pass"]:
            lines.append(f"- **{entry['gate']}** — {entry['blocker']}")
    lines += [
        "",
        "## 4. Livrables attendus avec le devis",
        "",
        "- procede et machine reellement employes, avec le jeu de parametres qualifie ;",
        "- epaisseur de couche proposee, et proprietes coupon **de cette epaisseur** ;",
        "- orientation et topologie de supports proposees, avec justification ;",
        "- traitement thermique, etat de livraison et HIP si juge necessaire ;",
        "- surepaisseurs d'usinage sur les surfaces fonctionnelles ;",
        "- certificat matiere, lot de poudre et nombre de reemplois ;",
        "- controle dimensionnel des quatre cotes et du profil axial ;",
        "- comparaison chiffree avec le tournage CNC de la meme geometrie.",
        "",
        "## 5. Reserve",
        "",
        "Les cotes du modele proviennent d'une fiche commerciale, pas d'un plan",
        "d'origine ni d'une mesure. Elles sont des variables de conception. Aucune",
        "piece issue de ce dossier ne doit etre montee sur un vehicule avant mesure",
        "d'un exemplaire et controle du logement.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog-part", type=Path, required=True)
    parser.add_argument("--geometry-report", type=Path, required=True)
    parser.add_argument("--machine-card", type=Path, required=True)
    parser.add_argument("--process-card", type=Path, required=True)
    parser.add_argument("--part-screen", type=Path, default=None)
    parser.add_argument("--master", type=Path, required=True)
    parser.add_argument("--surface", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Ne rien ecrire : echouer si les fichiers publies different.",
    )
    args = parser.parse_args()

    part = load_json(args.catalog_part)
    geometry = load_json(args.geometry_report)
    machine = load_json(args.machine_card)
    process = load_json(args.process_card)

    for path, key in ((args.master, "master"), (args.surface, "analysis_surface")):
        published = geometry[key].get("sha256")
        if published and published != sha256(path):
            raise SystemExit(
                f"empreinte_divergente:{path.name}: le rapport geometrique ne decrit "
                "pas ce fichier."
            )

    screen = load_json(args.part_screen) if args.part_screen else None
    card = build_route(part, geometry, machine, process, screen)
    rfq = render_rfq(
        card,
        part,
        {
            args.master.name: ("maitre STEP", sha256(args.master)),
            args.surface.name: ("surface d'analyse STL", sha256(args.surface)),
            args.geometry_report.name: (
                "criblage geometrique etape 03",
                sha256(args.geometry_report),
            ),
        },
    )

    slug = card["part_id"].lower()
    card_path = args.output / f"{slug}-process-route-card.json"
    rfq_path = args.output / f"{slug}-supplier-rfq.md"
    card_text = json.dumps(card, indent=2, ensure_ascii=False) + "\n"

    if args.check:
        for path, expected in ((card_path, card_text), (rfq_path, rfq)):
            if not path.exists():
                raise SystemExit(f"absent:{path}")
            if path.read_text(encoding="utf-8") != expected:
                raise SystemExit(f"perime:{path}")
        print(f"route a jour: {card['part_id']} status={card['status']}")
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
