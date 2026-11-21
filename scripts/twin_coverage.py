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
  python3 scripts/twin_coverage.py --transmission tiptronic --kerb-weight <kg>
  python3 scripts/twin_coverage.py --variant Turbo --kerb-weight <kg>

The default curb weight is the manual's single Carrera curb weight (PDF p. 19,
MNL-TECH-0037). It names no transmission, so it is used only for the base
configuration, the Carrera with manual transmission. No measurement record gives
a Tiptronic or a Turbo curb weight, so those runs require --kerb-weight and stop
otherwise rather than reuse the Carrera figure. (A Porsche brochure gives the
Turbo's kerb weight as 1,500 kg, SRC-PORSCHE-993-TURBO-BROCHURE-UK-1995-PUBSTACK,
without its weighing standard; it is not yet a measurement value.)

Each counted part entry names the variants it belongs to (field "variants" in
catalog/reference). An entry is counted for the requested variant when it names
it, or when it is "unspecified" because its source names no variant. Entries
of other variants are listed as excluded, never silently added.

The engine is counted as one assembly mass read from the workshop manual's
measurement record. The manual has no Turbo volume and no registered source
gives a Turbo engine mass, so the Turbo variant counts no engine at all (the
M64/60 bill of materials, twins/m64-engine-system/bom/m64-bom-v1.json, keeps it
unresolved). For the Carrera, every run states the scope of the counted figure:

- Dry, ready for fitting, without gearbox. The PDF p. 15 technical-data sheet
  heads both values "Engine weight (dry, ready for fitting)". MEAS-MANUAL-993-ALL
  keeps only the row labels ("Manual transmission: 232 (511)", "Tiptronic:
  224 (494)"), so the heading is carried by the page-checked record
  ENGINE_SCOPE_RECORD, read on the page image in two copies on 2026-11-20
  (#434). The Porsche 993 technical specification booklet
  (SRC-PORSCHE-993-SPEC-BOOKLET-PUBSTACK, printed p. 18) gives the same figures
  as "Engine Weight" and lists "Transmission Weight with Oil" separately
  (pp. 22-23: 66 kg G50/21, 105 kg Tiptronic), so 232 kg is not engine plus
  gearbox.
- Open: which ancillaries "ready for fitting" includes; the sheet does not list
  them. The Tiptronic figure being 8 kg lower fits a figure that includes the
  manual gearbox's flywheel and clutch, by inference only.
- The values themselves are structured_derived. A manual value whose extraction
  status is not structured_derived or manually_checked is refused, and the
  engine is then reported as not counted. If no page-checked row agrees with
  the counted value, the run says its scope is unchecked instead of stating it.
- A registered community weighing (SRC-PELICAN-TIMMINS-993-ENGINE-WEIGHTS)
  gives 186.9 kg for a 1995 Carrera engine in a conversion configuration: light
  flywheel, headers and mufflers, no air conditioning, fluid state unknown
  (docs/research/993-engine-mass-scope-20261107.md). The configurations differ,
  so the 45.1 kg gap is not a like-for-like disagreement; it stays unallocated.
  The weighing is printed for comparison only and never counted.
"""

from __future__ import annotations

import argparse
import json
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "catalog" / "reference"
MANUAL_SOURCE = "SRC-PORSCHE-WORKSHOP-MANUAL-993"
MANUAL_RECORD = ROOT / "catalog" / "measurements" / "MEAS-MANUAL-993-ALL.json"
# A manual value is used only when its transcription is not raw OCR.
ADMISSIBLE_EXTRACTION = {"structured_derived", "manually_checked"}

# Engine masses, each read from a value of the manual's measurement record (p. 15),
# never typed here. None means no registered source gives the value: the engine is
# then reported as not counted, never guessed.
ENGINE_MASS = {
    ("Carrera", "manual"): ("MNL-TECH-0020", "p. 15 engine weight, manual transmission"),
    ("Carrera", "tiptronic"): ("MNL-TECH-0021", "p. 15 engine weight, Tiptronic"),
    ("Turbo", "manual"): None,
    ("Turbo", "tiptronic"): None,
}
# The p. 15 sheet heading, read on the page image; the measurement record drops it.
ENGINE_SCOPE_RECORD = ROOT / "catalog" / "manual" / "page-checked" / "993-workshop-manual-group0-engine-weight.json"
# Single Carrera curb weight of the manual, p. 19; it names no transmission.
CARRERA_CURB_WEIGHT = "MNL-TECH-0037"
# Registered community weighing of a 1995 Carrera engine in a conversion
# configuration (light flywheel, headers and mufflers, no air conditioning, fluid
# state unknown), scoped in COMMUNITY_WEIGHING_RECORD. Printed for comparison only,
# never counted.
COMMUNITY_WEIGHING_KG = 186.9
COMMUNITY_WEIGHING_SOURCE = "SRC-PELICAN-TIMMINS-993-ENGINE-WEIGHTS"
COMMUNITY_WEIGHING_RECORD = "docs/research/993-engine-mass-scope-20261107.md"
# Second Porsche document giving the same engine figures and the gearbox separately.
SCOPE_CROSS_CHECK = "SRC-PORSCHE-993-SPEC-BOOKLET-PUBSTACK"
UNSPECIFIED = "unspecified"


def applies_to(entry: dict, variant: str) -> bool:
    """Count an entry for a variant it names, or for every variant when unspecified."""
    variants = entry.get("variants")
    if not isinstance(variants, list) or not variants:
        raise ValueError(f"{entry.get('entry_id')}: counted entry carries no variants")
    return variant in variants or UNSPECIFIED in variants


def manual_value(value_id: str) -> dict:
    """Return an admissible mass value in kg of the manual's measurement record; fail closed otherwise."""
    record = json.loads(MANUAL_RECORD.read_text(encoding="utf-8"))
    for value in record.get("declared_values", []):
        if value.get("value_id") != value_id:
            continue
        if value.get("source_id") != MANUAL_SOURCE or not str(value.get("unit", "")).startswith("kg"):
            raise ValueError(f"{value_id} is not a mass in kg from {MANUAL_SOURCE}")
        if value.get("extraction_status") not in ADMISSIBLE_EXTRACTION:
            raise ValueError(f"{value_id} has extraction status {value.get('extraction_status')}, which is not admissible")
        return value
    raise ValueError(f"{value_id} is missing from {MANUAL_RECORD.name}")


def manual_mass_kg(value_id: str) -> float:
    """Read a mass in kg from the manual's measurement record; fail closed otherwise."""
    return float(manual_value(value_id)["numeric_values"][0])


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
    try:
        mass = manual_mass_kg(value_id)
    except ValueError as exc:
        return 0.0, f"not counted, {exc}"
    return mass, f"{label}, {MANUAL_SOURCE} ({MANUAL_RECORD.stem}:{value_id})"


def checked_heading(value_id: str, mass: float) -> str | None:
    """Return the page-checked sheet heading of a manual engine-weight value, or None if no checked row agrees."""
    try:
        record = json.loads(ENGINE_SCOPE_RECORD.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    for row in record.get("records", []):
        if row.get("measurement_value_id") != value_id:
            continue
        checked = row.get("status") == "page_checked" and isinstance(row.get("value"), (int, float))
        if checked and float(row["value"]) == mass and record.get("heading"):
            return str(record["heading"])
        return None
    return None


def engine_scope_note(variant: str, transmission: str, engine: float, kerb_weight: float) -> list[str]:
    """State the scope of the counted engine mass, what is still open, and the weighing it differs from."""
    entry = ENGINE_MASS[(variant, transmission)]
    if entry is None or engine <= 0:
        return []
    value = manual_value(entry[0])
    gap = engine - COMMUNITY_WEIGHING_KG
    heading = checked_heading(entry[0], engine)
    shown = ENGINE_SCOPE_RECORD.relative_to(ROOT) if ENGINE_SCOPE_RECORD.is_relative_to(ROOT) else ENGINE_SCOPE_RECORD
    if heading:
        scope = (
            f"Scope: \"{heading}\", the p. 15 sheet heading, page-checked in "
            f"{shown}. Gearbox excluded: {SCOPE_CROSS_CHECK} "
            f"(printed p. 18) gives the same figure as \"Engine Weight\" and the transmission "
            f"weight separately (pp. 22-23). Open: which ancillaries \"ready for fitting\" includes."
        )
    else:
        scope = (
            f"Scope unchecked: no page-checked row of {shown} agrees "
            f"with {entry[0]}. Gearbox excluded per {SCOPE_CROSS_CHECK}; fluids and ancillaries open."
        )
    text = (
        f"{scope} The measurement record labels this value \"{value.get('description')}\" "
        f"(kg, lbs) and is {value.get('extraction_status')}. A registered community weighing "
        f"({COMMUNITY_WEIGHING_SOURCE}) gives {COMMUNITY_WEIGHING_KG:.1f} kg for a 1995 Carrera "
        f"engine in a conversion configuration (light flywheel, headers and mufflers, no air "
        f"conditioning, fluid state unknown), {gap:.1f} kg ({gap / kerb_weight * 100:.1f} points "
        f"of coverage) below the counted figure; the configurations differ and the gap stays "
        f"unallocated ({COMMUNITY_WEIGHING_RECORD})."
    )
    return textwrap.wrap(text, width=80, break_on_hyphens=False, break_long_words=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--kerb-weight",
        type=float,
        default=None,
        help=(
            f"reference curb weight in kg (default for the manual-transmission Carrera only: "
            f"{MANUAL_RECORD.stem}:{CARRERA_CURB_WEIGHT}; required for Tiptronic and Turbo)"
        ),
    )
    parser.add_argument("--variant", default="Carrera", choices=["Carrera", "Turbo"])
    parser.add_argument("--transmission", default="manual", choices=["manual", "tiptronic"])
    args = parser.parse_args(argv)
    if args.kerb_weight is None:
        if (args.variant, args.transmission) != ("Carrera", "manual"):
            parser.error(
                f"no measurement record gives a curb weight for the {args.variant} with {args.transmission} "
                f"transmission; {CARRERA_CURB_WEIGHT} is the manual's single Carrera curb weight, names no "
                "transmission and is the default for the manual-transmission Carrera only; pass --kerb-weight"
            )
        args.kerb_weight = manual_mass_kg(CARRERA_CURB_WEIGHT)
    if args.kerb_weight <= 0:
        parser.error("--kerb-weight must be positive")

    entries = load_entries()
    counted: list[tuple[str, float, int, float, bool]] = []
    excluded: list[tuple[str, float, list[str]]] = []
    for entry in entries:
        mass = entry.get("mass_kg")
        quantity = entry.get("quantity_per_car")
        if mass is None or quantity is None:
            continue
        if entry.get("generation") not in {"993", "generic"}:
            continue
        if not applies_to(entry, args.variant):
            excluded.append((entry["name"], mass * quantity, entry["variants"]))
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
    for line in engine_scope_note(args.variant, args.transmission, engine, args.kerb_weight):
        print(line)
    print()
    share = documented / args.kerb_weight * 100
    if excluded:
        print(f"Excluded, other variants: {sum(row[1] for row in excluded):.2f} kg")
        for name, total, variants in sorted(excluded, key=lambda r: -r[1]):
            print(f"  {name[:38]:38s} {total:8.2f}  ({', '.join(variants)})")
        print()
    print(f"Coverage: {documented:.1f} kg of {args.kerb_weight:.0f} kg, i.e. {share:.1f} %")
    print(f"Left to document: {args.kerb_weight - documented:.1f} kg")
    print()
    print("Lines marked ! carry a caveat: the matching lightweight version is not an")
    print("equivalent replacement. The original mass itself remains valid.")
    print()
    print("Known limits: entries whose source names no variant are counted for every")
    print("variant. catalog/components are not added: they are aftermarket fitments")
    print("(wheels) or parts already inside the engine mass (connecting rods).")
    print()
    print("What this coverage does not say: where the material is. A mass without a")
    print("position gives no center of gravity, no distribution and no inertia.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
