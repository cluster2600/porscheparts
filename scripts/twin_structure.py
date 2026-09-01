#!/usr/bin/env python3
"""Build the assembly skeleton of the twin from a factory part listing.

The catalogue holds no mass and no material, but it holds something the twin
needs just as much: where every part sits. Each reference carries an illustration
number, and those numbers form the vehicle's assembly tree.

This emits an aggregate only - systems, illustrations and counts - never the
catalogue lines themselves, which stay in their own repository under their own
rights. The detail is regenerated on demand from the external listing.

  python3 scripts/twin_structure.py --listing <atlas>/oem-listed.json \\
      --generation 993 --out catalog/reference/993-assembly-skeleton.json
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Libelles derives des groupes les plus frequents de chaque famille, pas devines.
SYSTEMS = {
    "0": "Consommables, adhesifs et documentation",
    "1": "Moteur",
    "2": "Carburant, echappement et suralimentation",
    "3": "Boite de vitesses",
    "4": "Direction, traverse et train avant",
    "5": "Train arriere, amortisseurs et transmission",
    "6": "Freinage et hydraulique",
    "7": "Commandes, pedalier et embrayage",
    "8": "Carrosserie et habillage",
    "9": "Electricite, eclairage et equipements",
}


def build(rows: list[dict], generation: str) -> dict:
    rows = [r for r in rows if r.get("generationId") == generation and r.get("petIllustration")]
    systems: dict[str, dict] = {}
    for row in rows:
        illustration = row["petIllustration"]
        key = illustration[0]
        system = systems.setdefault(
            key,
            {"system_id": f"{key}xx", "name": SYSTEMS.get(key, "Non classe"),
             "reference_count": 0, "illustrations": {}},
        )
        system["reference_count"] += 1
        entry = system["illustrations"].setdefault(
            illustration, {"illustration": illustration, "reference_count": 0, "labels": Counter()},
        )
        entry["reference_count"] += 1
        label = (row.get("petGroup") or "").strip()
        if label:
            entry["labels"][label.lower()] += 1

    out = []
    for key in sorted(systems):
        system = systems[key]
        illustrations = []
        for illustration in sorted(system["illustrations"]):
            item = system["illustrations"][illustration]
            common = [name for name, _ in item["labels"].most_common(3)]
            illustrations.append(
                {"illustration": illustration, "reference_count": item["reference_count"], "labels": common}
            )
        out.append(
            {
                "system_id": system["system_id"],
                "name": system["name"],
                "reference_count": system["reference_count"],
                "illustration_count": len(illustrations),
                "illustrations": illustrations,
            }
        )
    return {
        "$comment": (
            "Squelette d'assemblage agrege depuis un catalogue d'usine externe. Contient des "
            "denombrements et des libelles de groupe, jamais les lignes du catalogue, qui restent "
            "chez leur detenteur sous leurs propres droits. Regenerable par scripts/twin_structure.py."
        ),
        "generation": generation,
        "reference_count": sum(s["reference_count"] for s in out),
        "systems": out,
    }


def coverage(skeleton: dict) -> None:
    """Report how much of each system carries documented mass."""
    reference = ROOT / "catalog" / "reference" / "993-declared-part-data.json"
    documented = 0
    if reference.exists():
        entries = json.loads(reference.read_text(encoding="utf-8"))["entries"]
        documented = sum(1 for e in entries if e.get("mass_kg") is not None)

    print(f"{'systeme':46s} {'refs':>6} {'illus':>6}")
    for system in skeleton["systems"]:
        print(f"{system['system_id'] + '  ' + system['name']:46s} "
              f"{system['reference_count']:6d} {system['illustration_count']:6d}")
    total = skeleton["reference_count"]
    print(f"{'-' * 60}")
    print(f"{'TOTAL':46s} {total:6d} "
          f"{sum(s['illustration_count'] for s in skeleton['systems']):6d}")
    print()
    print(f"Pieces portant une masse documentee : {documented} sur {total} references, "
          f"soit {documented / total * 100:.2f} %.")
    print("La couverture massique, elle, se lit avec scripts/twin_coverage.py :")
    print("une poignee de grosses pieces represente une part de masse sans rapport")
    print("avec sa part de references.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--listing", required=True, type=Path)
    parser.add_argument("--generation", default="993")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    payload = json.loads(args.listing.read_text(encoding="utf-8"))
    rows = payload["listings"] if isinstance(payload, dict) and "listings" in payload else payload
    skeleton = build(rows, args.generation)
    coverage(skeleton)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(skeleton, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"\nsquelette ecrit dans {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
