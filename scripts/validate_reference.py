#!/usr/bin/env python3
"""Validate declared reference data: masses, envelopes and materials.

These values are read from third parties, not measured here. The point of this
file is therefore not the number but its attachment: every entry must name the
source record it came from, and that record must exist in the registry. A mass
without a traceable source is a rumour, and this validator refuses it.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "catalog" / "reference"
SOURCES = ROOT / "catalog" / "sources"

CONFIDENCE = {"declared", "inferred", "weighed_by_third_party"}
UNITS_MM = re.compile(r"^\d+(\.\d+)?$")

REQUIRED = {"entry_id", "name", "generation", "confidence", "source_id", "notes"}
OPTIONAL = {"oem_reference", "mass_kg", "dimensions_mm", "material", "variant", "caveat", "quantity_per_car"}


def known_source_ids() -> set[str]:
    ids: set[str] = set()
    for path in SOURCES.glob("*.json"):
        try:
            ids.add(json.loads(path.read_text(encoding="utf-8"))["source_id"])
        except Exception:
            continue
    return ids


def validate_entry(entry: Any, label: str, sources: set[str]) -> list[str]:
    errors: list[str] = []
    if not isinstance(entry, dict):
        return [f"{label}: expected an object"]

    missing = REQUIRED - entry.keys()
    unknown = entry.keys() - (REQUIRED | OPTIONAL)
    if missing:
        errors.append(f"{label}: missing fields: {', '.join(sorted(missing))}")
    if unknown:
        errors.append(f"{label}: unknown fields: {', '.join(sorted(unknown))}")

    if not isinstance(entry.get("name"), str) or not entry.get("name", "").strip():
        errors.append(f"{label}.name: expected a non-empty string")
    if entry.get("generation") not in {"993", "964", "generic"}:
        errors.append(f"{label}.generation: expected 993, 964 or generic")
    if entry.get("confidence") not in CONFIDENCE:
        errors.append(f"{label}.confidence: expected one of {sorted(CONFIDENCE)}")

    source_id = entry.get("source_id")
    if not isinstance(source_id, str):
        errors.append(f"{label}.source_id: expected a string")
    elif source_id not in sources:
        errors.append(f"{label}.source_id: {source_id} is not a registered source")

    mass = entry.get("mass_kg")
    if mass is not None and (not isinstance(mass, (int, float)) or isinstance(mass, bool) or mass <= 0):
        errors.append(f"{label}.mass_kg: expected a positive number")

    dims = entry.get("dimensions_mm")
    if dims is not None:
        if not isinstance(dims, list) or len(dims) != 3 or not all(
            isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0 for v in dims
        ):
            errors.append(f"{label}.dimensions_mm: expected three positive numbers")

    # An entry that carries no fact at all is noise.
    if mass is None and entry.get("dimensions_mm") is None and not entry.get("material"):
        errors.append(f"{label}: entry carries neither mass, dimensions nor material")

    quantity = entry.get("quantity_per_car")
    if quantity is not None and (not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1):
        errors.append(f"{label}.quantity_per_car: expected a positive integer")

    if not isinstance(entry.get("notes"), str):
        errors.append(f"{label}.notes: expected a string")
    return errors


def validate_skeleton(payload: Any) -> list[str]:
    """An assembly skeleton is an aggregate, and must stay one.

    The catalogue it is derived from belongs to someone else. Counting parts is a
    fact; reproducing their reference lines is a copy. The check below refuses the
    second, so the rule cannot quietly erode.
    """
    errors: list[str] = []
    systems = payload.get("systems")
    if not isinstance(systems, list) or not systems:
        return ["systems: expected a non-empty array"]

    total = 0
    for index, system in enumerate(systems):
        label = f"systems[{index}]"
        if not isinstance(system, dict):
            errors.append(f"{label}: expected an object")
            continue
        for field in ("system_id", "name"):
            if not isinstance(system.get(field), str) or not system[field].strip():
                errors.append(f"{label}.{field}: expected a non-empty string")
        count = system.get("reference_count")
        if not isinstance(count, int) or count < 1:
            errors.append(f"{label}.reference_count: expected a positive integer")
        else:
            total += count
        illustrations = system.get("illustrations")
        if not isinstance(illustrations, list) or not illustrations:
            errors.append(f"{label}.illustrations: expected a non-empty array")
            continue
        for position, item in enumerate(illustrations):
            if not isinstance(item, dict):
                errors.append(f"{label}.illustrations[{position}]: expected an object")
                continue
            leaked = item.keys() - {"illustration", "reference_count", "labels"}
            if leaked:
                errors.append(
                    f"{label}.illustrations[{position}]: aggregate must not carry "
                    f"catalogue detail: {', '.join(sorted(leaked))}"
                )

    declared = payload.get("reference_count")
    if isinstance(declared, int) and declared != total:
        errors.append(f"reference_count: {declared} does not match the sum of systems ({total})")
    return errors


def validate_file(payload: Any, sources: set[str]) -> list[str]:
    if isinstance(payload, dict) and "systems" in payload:
        return validate_skeleton(payload)
    if not isinstance(payload, dict) or "entries" not in payload:
        return ["root: expected an object with an entries or systems array"]
    entries = payload["entries"]
    if not isinstance(entries, list) or not entries:
        return ["entries: expected a non-empty array"]

    errors: list[str] = []
    seen: set[str] = set()
    for index, entry in enumerate(entries):
        errors.extend(validate_entry(entry, f"entries[{index}]", sources))
        if isinstance(entry, dict):
            identifier = entry.get("entry_id")
            if isinstance(identifier, str):
                if identifier in seen:
                    errors.append(f"entries[{index}].entry_id: duplicate {identifier}")
                seen.add(identifier)
    return errors


def main(arguments: list[str] | None = None) -> int:
    args = sys.argv[1:] if arguments is None else arguments
    paths = [Path(value).resolve() for value in args] if args else sorted(REFERENCE.glob("*.json"))
    if not paths:
        print("reference: no reference data yet")
        return 0

    sources = known_source_ids()
    failures = 0
    total = 0
    for path in paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"FAIL {path.name}\n  - invalid JSON at line {exc.lineno}: {exc.msg}")
            failures += 1
            continue
        errors = validate_file(payload, sources)
        label = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        if errors:
            failures += 1
            print(f"FAIL {label}")
            for error in errors:
                print(f"  - {error}")
        else:
            if "systems" in payload:
                count = payload.get("reference_count", 0)
                print(f"OK   {label} (squelette, {len(payload['systems'])} systemes, {count} references agregees)")
            else:
                count = len(payload["entries"])
                total += count
                print(f"OK   {label} ({count} entries)")
    if failures:
        print(f"reference: {failures} invalid file(s)")
        return 1
    print(f"reference: {total} declared value(s), all traced to a registered source")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
