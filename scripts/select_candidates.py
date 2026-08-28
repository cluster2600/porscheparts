#!/usr/bin/env python3
"""Shortlist reproducible parts from a factory part listing.

Buying every part to find out which ones are worth reproducing does not scale.
Reading the catalogue does. This narrows a full generation down to a handful of
candidates a human can then judge, using three filters:

  excluded    domains SAFETY.md presumes critical - never a shortlist candidate
  commodity   standard hardware bought off the shelf, not reproduced
  candidate   trim and non-structural parts a polymer print can plausibly serve

The output is a shortlist for human review, not a decision. Keyword matching on
a catalogue description cannot know whether a part is loaded, sealed, heated or
merely decorative. Every candidate still needs its own record, measurement plan
and safety class.

Input is a listing exported from a parts atlas, one object per catalogue line
with at least: oemReference, description, petGroup, petIllustration, petPage,
generationId. The file stays outside this repository.

  python3 scripts/select_candidates.py --listing ../atlas/oem-listed.json \\
      --generation 993 --limit 40
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

# Domains SAFETY.md presumes critical. A match here ends the discussion.
EXCLUDED = (
    "brake", "bremse", "steering", "lenk", "suspension", "shock", "damper", "strut",
    "spring", "wheel", "rim", "tire", "tyre", "hub", "axle", "drive shaft", "cv joint",
    "seat belt", "belt buckle", "airbag", "restraint", "fuel", "petrol", "tank",
    "injector", "piston", "crankshaft", "connecting rod", "cylinder head", "valve",
    "camshaft", "turbo", "engine carrier", "engine mount", "engine suspension",
    "jack", "lifting", "tow", "roll bar", "anti-roll",
)

# Standard hardware: sourced, not reproduced.
COMMODITY = (
    "screw", "bolt", "nut", "washer", "rivet", "clamp", "hose", "pipe", "line",
    "gasket", "sealing ring", "o-ring", "bearing", "circlip", "split pin", "stud",
    "wiring", "harness", "cable", "fuse", "relay", "bulb", "lamp", "battery",
    "spark plug", "filter", "oil", "grease", "adhesive", "paint", "sealant",
    "spring washer", "hexagon", "pan-head", "tapping", "combination",
)

# Shapes a polymer print can plausibly serve.
CANDIDATE = (
    "cover", "cap", "trim", "clip", "holder", "knob", "grille", "grid", "louvre",
    "panel", "escutcheon", "moulding", "molding", "badge", "emblem", "plug",
    "guide", "retainer", "bezel", "surround", "handle", "lever", "button",
    "housing", "shroud", "duct", "deflector", "spacer", "bush", "insert",
    "end piece", "blind", "blanking", "rosette", "strip",
)


def classify(text: str) -> str:
    lowered = text.lower()
    for word in EXCLUDED:
        if word in lowered:
            return "excluded"
    for word in COMMODITY:
        if re.search(rf"\b{re.escape(word)}", lowered):
            return "commodity"
    for word in CANDIDATE:
        if word in lowered:
            return "candidate"
    return "unclassified"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--listing", required=True, type=Path, help="factory listing JSON, kept outside this repository")
    parser.add_argument("--generation", default="993")
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--json-out", type=Path, help="write the shortlist as JSON")
    args = parser.parse_args(argv)

    payload = json.loads(args.listing.read_text(encoding="utf-8"))
    rows = payload["listings"] if isinstance(payload, dict) and "listings" in payload else payload
    rows = [r for r in rows if r.get("generationId") == args.generation]
    if not rows:
        print(f"no listing for generation {args.generation}", file=sys.stderr)
        return 1

    verdicts = Counter()
    candidates: list[dict] = []
    for row in rows:
        text = f"{row.get('description') or ''} {row.get('petGroup') or ''}"
        verdict = classify(text)
        verdicts[verdict] += 1
        if verdict == "candidate":
            candidates.append(row)

    print(f"generation {args.generation}: {len(rows)} catalogue lines")
    for verdict in ("excluded", "commodity", "candidate", "unclassified"):
        share = verdicts[verdict] / len(rows) * 100
        print(f"  {verdict:13s} {verdicts[verdict]:6d}  {share:5.1f}%")

    # Group identical descriptions: one shape, however many references carry it.
    grouped: dict[str, dict] = {}
    for row in candidates:
        key = (row.get("description") or "").strip().lower()
        entry = grouped.setdefault(key, {"description": row.get("description"), "references": [], "groups": set()})
        entry["references"].append(row.get("oemReference"))
        if row.get("petGroup"):
            entry["groups"].add(row["petGroup"])

    ranked = sorted(grouped.values(), key=lambda e: len(e["references"]), reverse=True)
    print(f"\n{len(grouped)} distinct candidate descriptions; top {min(args.limit, len(ranked))}:\n")
    print(f"{'refs':>4}  {'description':<38}  groups")
    for entry in ranked[:args.limit]:
        groups = ", ".join(sorted(entry["groups"]))[:44]
        print(f"{len(entry['references']):>4}  {(entry['description'] or '')[:38]:<38}  {groups}")

    if args.json_out:
        out = [
            {
                "description": e["description"],
                "references": e["references"],
                "pet_groups": sorted(e["groups"]),
            }
            for e in ranked
        ]
        args.json_out.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"\nshortlist written to {args.json_out}")

    print("\nThis is a shortlist, not a decision: a catalogue description cannot say")
    print("whether a part is loaded, sealed, heated or merely decorative.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
