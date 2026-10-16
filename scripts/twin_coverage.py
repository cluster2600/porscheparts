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
configuration, the Carrera with manual transmission. No registered source gives
a Tiptronic or a Turbo curb weight, so those runs require --kerb-weight and stop
otherwise rather than reuse the Carrera figure.

The engine is counted as one assembly mass read from the workshop manual's
measurement record. The manual has no Turbo volume and no registered source
gives a Turbo engine mass, so the Turbo variant counts no engine at all. For the
Carrera, the scope of the counted figure is an open question, stated in every
run:

- MEAS-MANUAL-993-ALL transcribes the PDF p. 15 technical-data sheet with only
  the labels "Manual transmission: 232 (511)" and "Tiptronic: 224 (494)", in kg
  (lbs). "Dry, ready to install" is the sheet heading as recorded in
  docs/993/993_MANUAL_DATA_MAP.md; the transcription itself does not carry it.
  The Tiptronic figure being lower than the manual one fits an engine-only
  figure, but that is an inference, not a statement of the sheet.
- Both values are structured_derived, not manually_checked, and the upstream
  transcription (catalog/specifications/porschefanatics-993-technical-data.json)
  marks them ocr_transcription_unverified. A manual value whose extraction
  status is not structured_derived or manually_checked is refused, and the
  engine is then reported as not counted.
- An unregistered community weighing with a named weigher and a declared method
  gives 186.9 kg for a complete 1995 Carrera engine, ready to run, without
  gearbox. parts/993-eng-carrier-0001/evidence/load-cases.md records the 45.1 kg
  gap as an open contradiction (232 kg might be engine plus gearbox), and
  twins/m64-engine-system/bom/m64-bom-v1.json keeps the dry engine mass
  unresolved. The weighing is printed for comparison only and never counted.
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
    ("Carrera", "manual"): ("MNL-TECH-0020", "p. 15 value for the manual transmission, read as the engine (scope open)"),
    ("Carrera", "tiptronic"): ("MNL-TECH-0021", "p. 15 value for the Tiptronic, read as the engine (scope open)"),
    ("Turbo", "manual"): None,
    ("Turbo", "tiptronic"): None,
}
# Single Carrera curb weight of the manual, p. 19; it names no transmission.
CARRERA_CURB_WEIGHT = "MNL-TECH-0037"
# Unregistered community weighing (named weigher, declared method and scope:
# complete 1995 Carrera engine, ready to run, without gearbox), recorded in
# COMMUNITY_WEIGHING_RECORD. Printed for comparison only: it has no source record
# and is never counted.
COMMUNITY_WEIGHING_KG = 186.9
COMMUNITY_WEIGHING_RECORD = "parts/993-eng-carrier-0001/evidence/load-cases.md"


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


def engine_scope_note(variant: str, transmission: str, engine: float, kerb_weight: float) -> list[str]:
    """State why the scope of the counted engine mass is open, and the weighing it contradicts."""
    entry = ENGINE_MASS[(variant, transmission)]
    if entry is None or engine <= 0:
        return []
    value = manual_value(entry[0])
    gap = engine - COMMUNITY_WEIGHING_KG
    text = (
        f"Engine scope is open. The p. 15 sheet labels this value only "
        f"\"{value.get('description')}\" (kg, lbs); \"dry, ready to install\" is the "
        f"sheet heading as recorded in docs/993/993_MANUAL_DATA_MAP.md, not in the "
        f"transcription, which is {value.get('extraction_status')}, not manually checked. "
        f"Tiptronic lighter than manual fits an engine-only figure, by inference only. "
        f"An unregistered community weighing with a declared method gives "
        f"{COMMUNITY_WEIGHING_KG:.1f} kg for a complete 1995 Carrera engine without gearbox, "
        f"{gap:.1f} kg ({gap / kerb_weight * 100:.1f} points of coverage) below the counted "
        f"figure; the contradiction is open in {COMMUNITY_WEIGHING_RECORD}."
    )
    return textwrap.wrap(text, width=80)


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
                f"no registered source gives a curb weight for the {args.variant} with {args.transmission} "
                f"transmission; {CARRERA_CURB_WEIGHT} is the manual's single Carrera curb weight, names no "
                "transmission and is the default for the manual-transmission Carrera only; pass --kerb-weight"
            )
        args.kerb_weight = manual_mass_kg(CARRERA_CURB_WEIGHT)
    if args.kerb_weight <= 0:
        parser.error("--kerb-weight must be positive")

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
    for line in engine_scope_note(args.variant, args.transmission, engine, args.kerb_weight):
        print(line)
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
