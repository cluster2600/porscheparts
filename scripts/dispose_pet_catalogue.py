#!/usr/bin/env python3
"""Disposition explicite de **toutes** les designations du catalogue d'usine.

Les criblages precedents publiaient ce qu'ils retenaient. Tout le reste tombait
sans motif : 956 designations sur 1 026 disparaissaient en silence, et c'est
ainsi que `oil pipe` puis `pulley` se sont perdus. Ce script ne retient rien : il
**dispose de tout**, et chaque designation repart avec une categorie et une
raison.

Il produit aussi le constat qui borne l'exercice. Une designation est une unite
de jugement utile quand elle nomme une fonction — `hot-air manifold` en est une.
Elle ne l'est pas quand elle nomme une forme : `support` couvre 142 references
qui n'ont rien a voir entre elles. Pour celles-la, la designation ne porte aucune
information, et le travail doit se faire reference par reference. Le script les
compte au lieu de faire semblant de les avoir jugees.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

# Designations qui ne decrivent pas une piece metallique a refabriquer.
NOT_A_METAL_PART = (
    "sticker", "label", "logo", "insignia", "emblem", "badge", "film", "foil",
    "carpet", "mat", "lining", "leather", "fabric", "felt", "foam", "textile",
    "sun visor", "loudspeaker", "speaker", "radio", "antenna", "aerial",
    "control unit", "speedometer", "tachometer", "instrument", "gauge",
    "switch", "sensor", "relay", "fuse", "lamp", "bulb", "light", "wiring",
    "harness", "cable", "lead", "battery", "glass", "window", "windscreen",
    "mirror", "wiper", "repair kit", "maintenance", "loctite", "adhesive",
    "grease", "paint", "sealant", "liquid", "sound absorber", "absorber pad",
    "desk pad", "package box", "glove compartment", "ashtray", "booster",
    "stone guard", "knee protection strip", "manual", "documentation",
    "tool", "jack", "warning", "first aid", "cover strip", "piping",
    "bellows", "buffer", "grommet", "rosette", "trim", "moulding",
)

# Designations qui nomment une forme, pas une fonction. La designation n'est
# alors pas l'unite de jugement : il faut descendre a la reference.
GENERIC_SHAPES = (
    "support", "cover", "lid", "bracket", "plate", "insert", "ring", "valve",
    "spacer", "stop", "stopper", "holder", "clip", "strip", "piece", "part",
    "housing", "frame", "guide", "rail", "cap", "plug", "bush", "sleeve",
    "disc", "shaft", "rod", "lever", "arm", "pin", "block", "body", "element",
    "unit", "set", "kit", "assembly", "mount", "mounting", "fitting",
    "connection piece", "connecting piece", "intermediate piece", "end piece",
    "distributing piece", "reinforcement", "member", "panel", "section",
)

CATEGORIES = {
    "commodity": "visserie, etancheite, matiere souple : rien a refabriquer",
    "not_a_metal_part": "ni metal, ni piece a refabriquer",
    "safety_domain": "domaine presume critique par SAFETY.md",
    "generic_designation": (
        "la designation nomme une forme et non une fonction : elle couvre des "
        "pieces sans rapport entre elles, et ne peut pas etre jugee telle quelle"
    ),
    "judged": "instruite, avec un verdict",
    "needs_a_human_call": "reste a instruire",
}


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def classify(
    description: str, scored: dict[str, Any], judged: set[str], generic_floor: int,
    reference_count: int,
) -> tuple[str, str]:
    if description in judged:
        return "judged", "instruite dans pet-candidate-judgements.json"
    if scored["commodity_exclusions"]:
        return "commodity", ", ".join(scored["commodity_exclusions"])
    if any(token in description for token in NOT_A_METAL_PART):
        hit = next(t for t in NOT_A_METAL_PART if t in description)
        return "not_a_metal_part", hit
    if scored["safety_exclusions"]:
        return "safety_domain", ", ".join(scored["safety_exclusions"])
    if reference_count >= generic_floor and any(
        token == description or token in description.split() for token in GENERIC_SHAPES
    ):
        return (
            "generic_designation",
            f"{reference_count} references partagent ce mot",
        )
    return "needs_a_human_call", ""


def run(listing: Path, generation: str, generic_floor: int) -> dict[str, Any]:
    triage = load_module("pet_triage", ROOT / "scripts/screen_pet_parts_for_titanium.py")
    judged = set(
        json.loads(
            (ROOT / "catalog/manufacturing/pet-candidate-judgements.json").read_text(
                encoding="utf-8"
            )
        )["parts"]
    )

    aggregate = triage.aggregate(listing, generation)
    rows = []
    for entry in aggregate.values():
        scored = triage.score_reference(entry)
        category, reason = classify(
            entry["description"], scored, judged, generic_floor, entry["reference_count"]
        )
        rows.append(
            {
                "description": entry["description"],
                "reference_count": entry["reference_count"],
                "category": category,
                "reason": reason,
            }
        )

    rows.sort(key=lambda row: (row["category"], -row["reference_count"]))
    counts: dict[str, dict[str, int]] = {}
    for row in rows:
        bucket = counts.setdefault(
            row["category"], {"designations": 0, "references": 0}
        )
        bucket["designations"] += 1
        bucket["references"] += row["reference_count"]

    remaining = [row for row in rows if row["category"] == "needs_a_human_call"]
    generic = [row for row in rows if row["category"] == "generic_designation"]

    return {
        "schema_version": "1.0.0",
        "screen_id": "PET-FULL-DISPOSITION",
        "authority": "mechanical_disposition_plus_declared_judgements",
        "generation": generation,
        "designations_total": len(rows),
        "references_total": sum(row["reference_count"] for row in rows),
        "categories": CATEGORIES,
        "counts": counts,
        "silently_dropped": 0,
        "what_this_does_not_do": (
            "Une designation generique nomme une forme, pas une fonction. Les "
            f"{len(generic)} designations ainsi classees couvrent "
            f"{sum(row['reference_count'] for row in generic)} references qui "
            "n'ont rien a voir entre elles. Les juger a ce niveau serait un "
            "faux : elles demandent un travail reference par reference, qui "
            "n'est pas fait et dont l'ampleur est ici mesuree, pas masquee."
        ),
        "remaining_to_judge": remaining,
        "generic_designations": generic,
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--listing", type=Path, required=True)
    parser.add_argument("--generation", default="993")
    parser.add_argument("--generic-floor", type=int, default=4)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = run(args.listing, args.generation, args.generic_floor)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"{report['designations_total']} designations, {report['references_total']} references")
    for name, bucket in sorted(
        report["counts"].items(), key=lambda item: -item[1]["designations"]
    ):
        print(
            f"  {bucket['designations']:5d} designations  {bucket['references']:5d} refs  {name}"
        )
    print(f"\nreste a instruire : {len(report['remaining_to_judge'])}")
    for row in report["remaining_to_judge"][:40]:
        print(f"  {row['reference_count']:3d}x  {row['description']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
