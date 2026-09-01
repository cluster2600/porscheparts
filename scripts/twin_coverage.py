#!/usr/bin/env python3
"""Measure how much of the vehicle the digital twin actually accounts for.

A digital twin of a car is not finished when it looks right, it is finished when
it accounts for what the car is made of. The most honest progress metric
available without touching a vehicle is therefore a mass budget: how many
kilograms of the kerb weight are described by parts whose mass is documented and
sourced.

Coverage is deliberately unflattering. It counts only what carries a mass, from a
registered source, with a quantity per car. Everything else is the work left.

  python3 scripts/twin_coverage.py
  python3 scripts/twin_coverage.py --kerb-weight 1500 --variant Turbo
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "catalog" / "reference"

# Masses d'ensembles etablies par ailleurs dans le dossier, hors catalogue de pieces.
ASSEMBLIES = {
    "Moteur complet, pret a tourner": {
        "Carrera": 186.9,
        "Turbo": 195.0,
        "source": "pesee au marbre, source communautaire nommee",
    },
}


def load_entries() -> list[dict]:
    entries: list[dict] = []
    for path in sorted(REFERENCE.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        entries.extend(payload.get("entries", []))
    return entries


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--kerb-weight", type=float, default=1370.0, help="masse a vide de reference, en kg")
    parser.add_argument("--variant", default="Carrera", choices=["Carrera", "Turbo"])
    args = parser.parse_args(argv)

    entries = load_entries()
    counted: list[tuple[str, float, int, float, bool]] = []
    for entry in entries:
        mass = entry.get("mass_kg")
        quantity = entry.get("quantity_per_car")
        if mass is None or quantity is None:
            continue
        if entry.get("generation") not in {"993", "generic"}:
            continue
        counted.append((entry["name"], mass, quantity, mass * quantity, "caveat" in entry))

    parts_total = sum(row[3] for row in counted)
    engine = ASSEMBLIES["Moteur complet, pret a tourner"][args.variant]
    documented = parts_total + engine

    print(f"Jumeau numerique, couverture massique — variante {args.variant}")
    print(f"Masse a vide de reference : {args.kerb_weight:.0f} kg\n")
    print(f"{'piece':38s} {'unite':>8} {'x':>3} {'total':>8}")
    for name, mass, quantity, total, flagged in sorted(counted, key=lambda r: -r[3]):
        mark = " !" if flagged else ""
        print(f"{name[:38]:38s} {mass:8.2f} {quantity:3d} {total:8.2f}{mark}")
    print(f"{'-' * 60}")
    print(f"{'Sous-total pieces documentees':38s} {'':8s} {'':3s} {parts_total:8.2f}")
    print(f"{'Moteur complet':38s} {'':8s} {'':3s} {engine:8.2f}")
    print(f"{'TOTAL DOCUMENTE':38s} {'':8s} {'':3s} {documented:8.2f}")
    print()
    share = documented / args.kerb_weight * 100
    print(f"Couverture : {documented:.1f} kg sur {args.kerb_weight:.0f} kg, soit {share:.1f} %")
    print(f"Reste a documenter : {args.kerb_weight - documented:.1f} kg")
    print()
    print("Les lignes marquees ! portent un caveat : la version allegee correspondante")
    print("n'est pas un remplacement equivalent. La masse d'origine, elle, reste valable.")
    print()
    print("Ce que cette couverture ne dit pas : ou se trouve la matiere. Une masse sans")
    print("position ne donne ni centre de gravite, ni repartition, ni inertie.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
