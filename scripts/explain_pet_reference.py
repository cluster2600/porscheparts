#!/usr/bin/env python3
"""Que dit le criblage d'une reference precise du catalogue d'usine ?

Les criblages publient ce qu'ils retiennent. Ils ne savent pas repondre a la
question qu'on leur pose le plus souvent : « et cette piece-la ? ». Une
designation ecartee disparait silencieusement du classement, et son motif de
rejet n'est ecrit nulle part.

Ce script repond reference par reference. Il lit le releve **hors depot**, via
`--listing`, et rejoue sur la seule designation demandee les regles du triage et
du jugement. Il n'ecrit rien : c'est un outil de lecture.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
JUDGEMENTS = ROOT / "catalog/manufacturing/pet-candidate-judgements.json"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--listing", type=Path, required=True)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--generation", default="993")
    args = parser.parse_args()

    triage = load_module("pet_triage", ROOT / "scripts/screen_pet_parts_for_titanium.py")
    verdicts = load_module("pet_verdict", ROOT / "scripts/screen_pet_candidates.py")

    wanted = args.reference.strip()
    payload = json.loads(args.listing.read_text(encoding="utf-8"))
    rows = payload["listings"] if isinstance(payload, dict) else payload
    sightings = [
        row
        for row in rows
        if (row.get("oemReference") or "").strip() == wanted
        and row.get("generationId") == args.generation
    ]
    if not sightings:
        raise SystemExit(f"reference absente du releve {args.generation}: {wanted}")

    description = (sightings[0].get("description") or "").strip().lower()
    plates = sorted({row.get("petIllustration") or "" for row in sightings})
    groups = sorted({(row.get("petGroup") or "").strip().lower() for row in sightings})
    positions = sorted({row.get("position") for row in sightings if row.get("position")})

    print(f"reference   {wanted}")
    print(f"designation {description}")
    print(f"planches    {', '.join(p for p in plates if p)}")
    print(f"groupes     {', '.join(g for g in groups if g)}")
    print(f"positions   {', '.join(str(p) for p in positions)}")
    print(f"occurrences {len(sightings)} dans le releve")

    # Rejouer le triage lexical sur cette seule designation.
    aggregate = triage.aggregate(args.listing, args.generation)
    entry = aggregate.get(description)
    if entry is None:
        raise SystemExit("designation introuvable dans l'agregat du triage")
    scored = triage.score_reference(entry)

    print()
    print(f"--- triage lexical : {'retenu' if scored['retained'] else 'ecarte'}, score {scored['score']}")
    for label, key in (
        ("chaud", "hot_terms"),
        ("passage interne", "passage_terms"),
        ("consolidation", "consolidation_terms"),
    ):
        if scored[key]:
            print(f"    {label:16s} {', '.join(scored[key])}")
    for label, key in (
        ("visserie/souple", "commodity_exclusions"),
        ("domaine critique", "safety_exclusions"),
    ):
        if scored[key]:
            print(f"    {label:16s} {', '.join(scored[key])}")

    judgement: dict[str, Any] | None = json.loads(
        JUDGEMENTS.read_text(encoding="utf-8")
    )["parts"].get(description)

    print()
    if judgement is None:
        print("--- jugement : aucun")
        print("    Cette designation n'a pas ete retenue par le triage, donc")
        print("    jamais instruite. L'absence de jugement n'est pas un verdict :")
        print("    c'est l'aveu que personne ne l'a regardee.")
        return 0

    verdict, blockers = verdicts.derive(judgement)
    print(f"--- jugement : {verdict}")
    print(f"    matiere d'origine presumee  {judgement['incumbent_material']}")
    print(f"    le titane l'ameliore        {judgement['titanium_improves_on_it']}")
    print(f"    classe presumee             {judgement['presumed_safety_class']}")
    print(f"    familles additives          {', '.join(judgement['additive_families']) or 'aucune'}")
    for blocker in blockers:
        print(f"    BLOQUE  {blocker}")
    print(f"    {judgement['reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
