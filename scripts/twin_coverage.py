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
  python3 scripts/twin_coverage.py --transmission tiptronic
  python3 scripts/twin_coverage.py --kerb-weight 1500 --variant Turbo

The engine is counted as one sourced assembly mass. The Carrera values are the
workshop manual's dry engine weights, ready to install (PDF p. 15). The manual
has no Turbo volume and no registered source gives a Turbo engine mass, so the
Turbo variant counts no engine at all rather than an unsourced figure.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "catalog" / "reference"
MANUAL_SOURCE = "SRC-PORSCHE-WORKSHOP-MANUAL-993"
MANUAL_RECORD = ROOT / "catalog" / "measurements" / "MEAS-MANUAL-993-ALL.json"

# Engine masses, each read from a value of the manual's measurement record (p. 15),
# never typed here. None means no registered source gives the value: the engine is
# then reported as not counted, never guessed.
ENGINE_MASS = {
    ("Carrera", "manual"): ("MNL-TECH-0020", "engine for manual transmission, dry, ready to install"),
    ("Carrera", "tiptronic"): ("MNL-TECH-0021", "engine for Tiptronic, dry, ready to install"),
    ("Turbo", "manual"): None,
    ("Turbo", "tiptronic"): None,
}
# DIN curb weight of the Carrera, manual p. 19.
CARRERA_CURB_WEIGHT = "MNL-TECH-0037"


def manual_mass_kg(value_id: str) -> float:
    """Read a mass in kg from the manual's measurement record; fail closed otherwise."""
    record = json.loads(MANUAL_RECORD.read_text(encoding="utf-8"))
    for value in record.get("declared_values", []):
        if value.get("value_id") != value_id:
            continue
        if value.get("source_id") != MANUAL_SOURCE or not str(value.get("unit", "")).startswith("kg"):
            raise ValueError(f"{value_id} is not a mass in kg from {MANUAL_SOURCE}")
        return float(value["numeric_values"][0])
    raise ValueError(f"{value_id} is missing from {MANUAL_RECORD.name}")


def load_entries() -> list[dict]:
    entries: list[dict] = []
    for path in sorted(REFERENCE.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        entries.extend(payload.get("entries", []))
    return entries


def engine_mass(variant: str, transmission: str) -> tuple[float, str]:
    """Return the sourced engine mass in kg and its citation, or 0 and the reason."""
    entry = ENGINE_MASS[(variant, transmission)]
    if entry is None:
        return 0.0, f"not counted, no registered source gives the {variant} engine mass"
    value_id, label = entry
    return manual_mass_kg(value_id), f"{label}, {MANUAL_SOURCE} ({MANUAL_RECORD.stem}:{value_id})"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--kerb-weight",
        type=float,
        default=None,
        help=f"reference curb weight in kg (default: Carrera DIN curb weight, {MANUAL_RECORD.stem}:{CARRERA_CURB_WEIGHT})",
    )
    parser.add_argument("--variant", default="Carrera", choices=["Carrera", "Turbo"])
    parser.add_argument("--transmission", default="manual", choices=["manual", "tiptronic"])
    args = parser.parse_args(argv)
    if args.kerb_weight is None:
        args.kerb_weight = manual_mass_kg(CARRERA_CURB_WEIGHT)

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
    engine, engine_citation = engine_mass(args.variant, args.transmission)
    documented = parts_total + engine

    print(f"Digital twin, mass coverage — variant {args.variant}, {args.transmission} transmission")
    print(f"Reference curb weight: {args.kerb_weight:.0f} kg\n")
    print(f"{'part':38s} {'unit':>8} {'x':>3} {'total':>8}")
    for name, mass, quantity, total, flagged in sorted(counted, key=lambda r: -r[3]):
        mark = " !" if flagged else ""
        print(f"{name[:38]:38s} {mass:8.2f} {quantity:3d} {total:8.2f}{mark}")
    print(f"{'-' * 60}")
    print(f"{'Subtotal, documented parts':38s} {'':8s} {'':3s} {parts_total:8.2f}")
    print(f"{'Complete engine':38s} {'':8s} {'':3s} {engine:8.2f}")
    print(f"{'DOCUMENTED TOTAL':38s} {'':8s} {'':3s} {documented:8.2f}")
    print(f"Engine: {engine_citation}")
    print()
    share = documented / args.kerb_weight * 100
    print(f"Coverage: {documented:.1f} kg of {args.kerb_weight:.0f} kg, i.e. {share:.1f} %")
    print(f"Left to document: {args.kerb_weight - documented:.1f} kg")
    print()
    print("Lines marked ! carry a caveat: the matching lightweight version is not an")
    print("equivalent replacement. The original mass itself remains valid.")
    print()
    print("Known limits: the part entries carry no variant, so Turbo-only parts are counted")
    print("for the Carrera too. catalog/components are not added: they are aftermarket")
    print("fitments (wheels) or parts already inside the engine mass (connecting rods).")
    print()
    print("What this coverage does not say: where the material is. A mass without a")
    print("position gives no center of gravity, no distribution and no inertia.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
