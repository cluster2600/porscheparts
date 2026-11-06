#!/usr/bin/env python3
"""Triage of factory-skeleton zones for a titanium candidate.

The titanium record screening covers 32 parts. The factory skeleton counts
12,864. The ratio is 0.25 %: saying no other part fits would therefore be false,
and saying it would be a fault.

This script does not fully fix the problem, because it cannot. The repository
does **not** hold the 12,864 designations: it keeps only counts and group
labels, so as not to copy a copyrighted catalogue. The available granularity is
therefore the illustration — 239 groups, 499 labels — not the part.

What follows is therefore a **keyword zone triage**, of low authority, meant to
direct attention. A retained zone becomes a candidate part only by opening the
matching PET line, which this repository will not do in place of its user.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

# Families where additive wins, transposed into catalogue vocabulary.
INTERNAL_PASSAGE = (
    "pipe", "line", "duct", "hose", "manifold", "distributor", "cooler",
    "air guide", "air-guide", "intake", "canister", "tank", "pump",
)
HOT_GAS = ("exhaust", "turbocharger", "turbocharging", "heat protection", "air injection")
CONSOLIDATION = ("bracket", "support", "carrier", "housing", "cowl", "console")

# Hard exclusions: presumed safety-critical in the SAFETY.md sense.
SAFETY_EXCLUDED = (
    "brake", "steering", "airbag", "wheel", "hub", "suspension", "wishbone",
    "stabiliser", "shock absorber", "coil spring", "drive shaft", "axle",
    "seat belt", "clutch", "pedal", "differential", "gear", "transmission",
    "crankshaft", "connecting rod", "piston", "camshaft", "valve control",
    "cylinder head", "crankcase", "tiptronic", "hydraulic",
)

# Exclusions by nature: nothing to print in titanium in these groups.
TRIVIAL_EXCLUDED = (
    "sticker", "grease", "mounting paste", "securing liquid", "tool", "paint",
    "maintenance set", "gasket set", "repair kit", "wiring", "harness", "radio",
    "loudspeaker", "telephone", "instrument", "speedometer", "lamp", "light",
    "wiper", "washer system", "glazing", "window", "seal", "battery", "switch",
    "control unit", "electrics", "sticker", "cruise control", "fanfare",
)


def matched(text: str, needles: tuple[str, ...]) -> list[str]:
    return sorted({n for n in needles if n in text})


def score_zone(system: dict[str, Any], illustration: dict[str, Any]) -> dict[str, Any]:
    labels = [label.lower() for label in illustration["labels"]]
    text = " ".join(labels + [system["name"].lower()])

    safety = matched(text, SAFETY_EXCLUDED)
    trivial = matched(text, TRIVIAL_EXCLUDED)
    passages = matched(text, INTERNAL_PASSAGE)
    hot = matched(text, HOT_GAS)
    consolidation = matched(text, CONSOLIDATION)

    excluded = bool(safety) or bool(trivial)
    score = 0 if excluded else 2 * len(hot) + 2 * len(passages) + len(consolidation)

    return {
        "system_id": system["system_id"],
        "system": system["name"],
        "illustration": illustration["illustration"],
        "reference_count": illustration["reference_count"],
        "labels": illustration["labels"],
        "score": score,
        "retained": not excluded and score > 0,
        "hot_gas_terms": hot,
        "internal_passage_terms": passages,
        "consolidation_terms": consolidation,
        "safety_exclusions": safety,
        "nature_exclusions": trivial,
    }


def run(skeleton_path: Path, screened_part_count: int) -> dict[str, Any]:
    skeleton = json.loads(skeleton_path.read_text(encoding="utf-8"))
    zones = [
        score_zone(system, illustration)
        for system in skeleton["systems"]
        for illustration in system["illustrations"]
    ]
    zones.sort(key=lambda zone: (zone["score"], zone["reference_count"]), reverse=True)

    retained = [zone for zone in zones if zone["retained"]]
    covered = sum(zone["reference_count"] for zone in retained)
    total = int(skeleton["reference_count"])

    return {
        "schema_version": "1.0.0",
        "screen_id": "PET-ZONE-TITANIUM-TRIAGE",
        "authority": "keyword_triage_of_group_labels_not_a_part_selection",
        "granularity": "illustration_group",
        "why_not_finer": (
            "Le squelette ne detient que des denombrements et des libelles de "
            "groupe. Les 12 864 designations restent chez leur detenteur : les "
            "recopier serait une copie de catalogue, ce que le depot refuse."
        ),
        "catalogue_reference_count": total,
        "catalogue_part_records_screened_so_far": screened_part_count,
        "part_record_coverage_percent": round(screened_part_count / total * 100.0, 3),
        "zones_screened": len(zones),
        "zones_retained": len(retained),
        "references_under_retained_zones": covered,
        "references_under_retained_zones_percent": round(covered / total * 100.0, 1),
        "next_step": (
            "Une zone retenue n'est pas une piece. Elle devient un candidat en "
            "ouvrant la ligne PET correspondante, en relevant designation, matiere "
            "et masse, et en la faisant passer par screen_titanium_candidates.py."
        ),
        "zones": zones,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skeleton",
        type=Path,
        default=ROOT / "catalog/reference/993-assembly-skeleton.json",
    )
    parser.add_argument("--catalog", type=Path, default=ROOT / "catalog/parts")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    screened = len(list(args.catalog.glob("*.json")))
    report = run(args.skeleton, screened)
    text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"

    if args.check:
        if not args.output.exists():
            raise SystemExit(f"absent:{args.output}")
        if args.output.read_text(encoding="utf-8") != text:
            raise SystemExit(f"perime:{args.output}")
        print(f"zone triage up to date: {report['zones_retained']} zones retained")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    print(
        f"{report['zones_screened']} zones triaged, {report['zones_retained']} retained, "
        f"covering {report['references_under_retained_zones']} references "
        f"({report['references_under_retained_zones_percent']} %)"
    )
    print(
        f"records already screened: {screened} of "
        f"{report['catalogue_reference_count']} references "
        f"({report['part_record_coverage_percent']} %)"
    )
    for zone in report["zones"][:12]:
        if zone["retained"]:
            print(
                f"  +{zone['score']:<2d} {zone['system_id']} {zone['illustration']:8s} "
                f"{zone['reference_count']:4d} refs  {', '.join(zone['labels'])[:60]}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
