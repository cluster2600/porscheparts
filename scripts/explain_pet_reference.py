#!/usr/bin/env python3
"""What does the screening say about one specific factory-catalogue reference?

Screenings publish what they retain. They cannot answer the question most often
asked of them: "and what about this part?". A discarded designation disappears
silently from the ranking, and its rejection reason is written nowhere.

This script answers reference by reference. It reads the listing **outside the
repository**, via `--listing`, and replays the triage and judgement rules on the
single requested designation. It writes nothing: it is a reading tool.
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
        raise SystemExit(f"reference missing from the {args.generation} listing: {wanted}")

    description = (sightings[0].get("description") or "").strip().lower()
    plates = sorted({row.get("petIllustration") or "" for row in sightings})
    groups = sorted({(row.get("petGroup") or "").strip().lower() for row in sightings})
    positions = sorted({row.get("position") for row in sightings if row.get("position")})

    print(f"reference   {wanted}")
    print(f"designation {description}")
    print(f"plates      {', '.join(p for p in plates if p)}")
    print(f"groups      {', '.join(g for g in groups if g)}")
    print(f"positions   {', '.join(str(p) for p in positions)}")
    print(f"occurrences {len(sightings)} in the listing")

    # Replay the lexical triage on this single designation.
    aggregate = triage.aggregate(args.listing, args.generation)
    entry = aggregate.get(description)
    if entry is None:
        raise SystemExit("designation not found in the triage aggregate")
    scored = triage.score_reference(entry)

    print()
    print(f"--- lexical triage: {'retained' if scored['retained'] else 'discarded'}, score {scored['score']}")
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
        print("--- judgement: none")
        print("    This designation was not retained by the triage, so it was")
        print("    never examined. The absence of a judgement is not a verdict:")
        print("    it is the admission that nobody has looked at it.")
        return 0

    verdict, blockers = verdicts.derive(judgement)
    print(f"--- judgement: {verdict}")
    print(f"    presumed original material  {judgement['incumbent_material']}")
    print(f"    titanium improves on it     {judgement['titanium_improves_on_it']}")
    print(f"    presumed class              {judgement['presumed_safety_class']}")
    print(f"    additive families           {', '.join(judgement['additive_families']) or 'none'}")
    for blocker in blockers:
        print(f"    BLOCKED {blocker}")
    print(f"    {judgement['reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
