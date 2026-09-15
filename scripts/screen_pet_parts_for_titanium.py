#!/usr/bin/env python3
"""Triage titane de tout le catalogue d'usine 993, au niveau de la piece.

Le criblage des fiches porte sur une trentaine de pieces. Le catalogue d'usine
en compte pres de six mille. Conclure quoi que ce soit sur « tout le catalogue »
a partir des fiches etait donc indefendable, et ce script existe pour reparer
cela.

Il lit le releve de designations **hors du depot**, par `--listing`, comme le
fait deja `twin_structure.py` : les lignes de catalogue restent chez leur
detenteur. Seuls le classement agrege et une liste courte de candidats sont
publies.

Ce qu'il produit reste un triage lexical. Une designation de trois mots ne dit
ni la matiere, ni la masse, ni la temperature, ni la fonction exacte. Un candidat
retenu ici n'est pas une piece choisie : c'est une piece qu'il faut aller
regarder.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

# Rien a imprimer en titane : visserie, etancheite, souplesse, electricite.
COMMODITY = (
    "screw", "bolt", "nut", "washer", "shim", "clip", "clamp", "rivet", "stud",
    "circlip", "sticker", "label", "gasket", "o-ring", "sealing ring", "seal",
    "rubber", "hose", "cable", "wire", "harness", "lamp", "bulb", "glass",
    "carpet", "mat", "liner", "tool", "grease", "paint", "filter", "bearing",
    "bush", "sleeve", "spring", "grommet", "plug", "switch", "sensor", "relay",
    "fuse", "socket", "connector", "transmitter", "solenoid", "motor", "pump",
    "trim", "moulding", "emblem", "badge", "cap", "knob", "handle", "mirror",
    "wiper", "belt", "bag", "foam", "felt", "fabric", "leather",
)

# Presomption de criticite au sens de SAFETY.md, sur la designation ou le groupe.
SAFETY = (
    "brake", "steering", "airbag", "seat belt", "wheel", "hub", "suspension",
    "wishbone", "stabiliser", "shock absorber", "coil spring", "drive shaft",
    "axle", "clutch", "pedal", "differential", "gear", "transmission",
    "crankshaft", "connecting rod", "piston", "camshaft", "cylinder head",
    "crankcase", "tiptronic", "hydraulic", "valve tappet", "valve guide",
    "valve seat", "valve spring", "intake valve", "exhaust valve", "fuel tank",
)

# Chaud : la ou le titane a un interet et une limite en meme temps.
HOT = (
    "exhaust", "turbocharger", "turbo", "hot-air", "heat exchanger",
    "heat protection", "heat shield", "air injection", "tail pipe",
    "heat control", "heat dissipator", "thermostat",
)

# Passages internes : la premiere famille ou l'additif gagne.
PASSAGE = (
    "pipe", "line", "tube", "duct", "manifold", "distributor", "elbow",
    "nozzle", "cooler", "exchanger", "trumpet", "breather", "vent",
)

# Consolidation : la troisieme famille.
CONSOLIDATION = ("manifold", "distributor", "housing", "cowl", "exchanger", "console", "carrier", "guide")


def hits(text: str, needles: tuple[str, ...]) -> list[str]:
    return sorted({n for n in needles if n in text})


def score_reference(entry: dict[str, Any]) -> dict[str, Any]:
    description = entry["description"]
    groups = sorted(entry["groups"])

    commodity = hits(description, COMMODITY)
    # La designation prime. Le groupe n'exclut que s'il accuse **toutes** les
    # illustrations : une meme designation traverse le catalogue, et une
    # conduite d'huile qui apparait une fois sur une planche de carter n'est pas
    # pour autant un organe de carter. La regle brutale faisait disparaitre
    # `oil pipe`, qui est justement un des meilleurs candidats du lot.
    safety = hits(description, SAFETY)
    group_safety = [group for group in groups if hits(group, SAFETY)]
    group_excluded = bool(groups) and len(group_safety) == len(groups)
    if group_excluded:
        safety = sorted(set(safety) | {f"toutes les planches: {', '.join(groups[:3])}"})
    hot = hits(description, HOT)
    passage = hits(description, PASSAGE)
    consolidation = hits(description, CONSOLIDATION)

    excluded = bool(commodity) or bool(safety)
    score = 0 if excluded else 2 * len(hot) + 2 * len(passage) + len(consolidation)

    return {
        "description": description,
        "reference_count": entry["reference_count"],
        "groups": groups[:6],
        "safety_flagged_groups": group_safety[:6],
        "illustrations": sorted(entry["illustrations"])[:6],
        "score": score,
        "retained": not excluded and score > 0,
        "hot_terms": hot,
        "passage_terms": passage,
        "consolidation_terms": consolidation,
        "commodity_exclusions": commodity,
        "safety_exclusions": safety,
    }


def aggregate(listing_path: Path, generation: str) -> dict[str, dict[str, Any]]:
    payload = json.loads(listing_path.read_text(encoding="utf-8"))
    rows = payload["listings"] if isinstance(payload, dict) else payload

    by_description: dict[str, dict[str, Any]] = {}
    seen_references: set[tuple[str, str]] = set()
    for row in rows:
        if row.get("generationId") != generation:
            continue
        description = (row.get("description") or "").strip().lower()
        reference = (row.get("oemReference") or "").strip()
        if not description or not reference:
            continue
        key = (description, reference)
        entry = by_description.setdefault(
            description,
            {
                "description": description,
                "reference_count": 0,
                "illustrations": set(),
                "groups": set(),
            },
        )
        if key not in seen_references:
            seen_references.add(key)
            entry["reference_count"] += 1
        if row.get("petIllustration"):
            entry["illustrations"].add(row["petIllustration"])
        if row.get("petGroup"):
            entry["groups"].add(row["petGroup"].strip().lower())
    return by_description


def run(listing_path: Path, generation: str, catalog: Path, shortlist: int) -> dict[str, Any]:
    by_description = aggregate(listing_path, generation)
    scored = [score_reference(entry) for entry in by_description.values()]
    scored.sort(key=lambda item: (item["score"], item["reference_count"]), reverse=True)

    retained = [item for item in scored if item["retained"]]
    distinct_references = sum(item["reference_count"] for item in scored)
    screened_records = len(list(catalog.glob("*.json")))

    return {
        "schema_version": "1.0.0",
        "screen_id": "PET-PART-TITANIUM-TRIAGE",
        "authority": "lexical_triage_of_factory_descriptions_not_a_part_selection",
        "generation": generation,
        "listing_source": (
            "releve de designations tenu hors du depot ; seules les conclusions "
            "agregees et la liste courte sont publiees ici"
        ),
        "distinct_descriptions": len(scored),
        "distinct_references": distinct_references,
        "catalogue_part_records": screened_records,
        "part_record_coverage_percent": round(
            screened_records / distinct_references * 100.0, 2
        ),
        "descriptions_retained": len(retained),
        "references_under_retained_descriptions": sum(
            item["reference_count"] for item in retained
        ),
        "limits": [
            "Une designation de trois mots ne dit ni la matiere, ni la masse, ni la temperature.",
            "Le triage est lexical : il retient des mots, pas des fonctions.",
            "Une piece retenue n'est pas choisie, elle est a regarder.",
        ],
        "shortlist": retained[:shortlist],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--listing", type=Path, required=True)
    parser.add_argument("--generation", default="993")
    parser.add_argument("--catalog", type=Path, default=ROOT / "catalog/parts")
    parser.add_argument("--shortlist", type=int, default=40)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = run(args.listing, args.generation, args.catalog, args.shortlist)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        f"{report['distinct_descriptions']} designations distinctes, "
        f"{report['distinct_references']} references"
    )
    print(
        f"fiches du depot: {report['catalogue_part_records']} soit "
        f"{report['part_record_coverage_percent']} % des references"
    )
    print(f"retenues: {report['descriptions_retained']} designations")
    for item in report["shortlist"][:20]:
        print(
            f"  +{item['score']:<2d} {item['reference_count']:3d}x  {item['description']:28s} "
            f"{','.join(item['illustrations'][:3])}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
