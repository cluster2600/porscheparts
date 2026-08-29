#!/usr/bin/env python3
"""Validate digital-twin zone records without external dependencies."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "catalog" / "twins"
TWIN_ID = re.compile(r"^TWIN-[A-Z0-9][A-Z0-9._-]{2,63}$")
COMPONENT_ID = re.compile(r"^[A-Z][A-Z0-9._-]{1,63}$")
FIDELITIES = {"F0_reference", "F1_envelope", "F2_interface", "F3_engineering", "F4_correlated"}
PURPOSES = {"fit", "clearance", "motion", "structural", "thermal", "fluid"}
ROLES = {"host", "candidate", "context"}
KINDS = {"contact", "clearance", "fastener", "clip", "motion"}
INTERFACE_STATUSES = {"missing_data", "ready", "passed", "failed"}
VALIDATION_STATUSES = {"concept", "geometry_ready", "digitally_checked", "physically_correlated"}
TOP_LEVEL_KEYS = {
    "schema_version", "twin_id", "name", "vehicle", "scope", "fidelity",
    "coordinate_system", "components", "interfaces", "geometry", "validation",
}


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _file(value: str, field: str, errors: list[str]) -> None:
    if not value:
        return
    candidate = (ROOT / value).resolve()
    try:
        candidate.relative_to(ROOT)
    except ValueError:
        errors.append(f"{field}: path escapes the repository: {value}")
        return
    if not candidate.is_file():
        errors.append(f"{field}: referenced file does not exist: {value}")


def validate_twin(record: Any) -> list[str]:
    if not isinstance(record, dict):
        return ["root: expected an object"]
    errors: list[str] = []
    missing = TOP_LEVEL_KEYS - record.keys()
    extra = record.keys() - TOP_LEVEL_KEYS
    if missing:
        errors.append(f"root: missing fields: {', '.join(sorted(missing))}")
    if extra:
        errors.append(f"root: unknown fields: {', '.join(sorted(extra))}")

    if record.get("schema_version") != "1.0.0":
        errors.append("schema_version: expected 1.0.0")
    if not isinstance(record.get("twin_id"), str) or not TWIN_ID.fullmatch(record["twin_id"]):
        errors.append("twin_id: expected TWIN- followed by an uppercase stable identifier")
    if not _text(record.get("name")):
        errors.append("name: expected a non-empty string")

    vehicle = record.get("vehicle")
    if not isinstance(vehicle, dict):
        errors.append("vehicle: expected an object")
    else:
        if vehicle.get("generation") != "993":
            errors.append("vehicle.generation: expected 993")
        variants = vehicle.get("variants")
        if not isinstance(variants, list) or not variants or not all(_text(v) for v in variants):
            errors.append("vehicle.variants: expected at least one string")
        years = vehicle.get("model_years")
        if not isinstance(years, dict):
            errors.append("vehicle.model_years: expected an object")
        else:
            start, end = years.get("from"), years.get("to")
            if not isinstance(start, int) or not 1993 <= start <= 1998:
                errors.append("vehicle.model_years.from: expected 1993..1998")
            if not isinstance(end, int) or not 1993 <= end <= 1998:
                errors.append("vehicle.model_years.to: expected 1993..1998")
            if isinstance(start, int) and isinstance(end, int) and start > end:
                errors.append("vehicle.model_years: from must be <= to")

    scope = record.get("scope")
    if not isinstance(scope, dict):
        errors.append("scope: expected an object")
    else:
        if not _text(scope.get("zone")):
            errors.append("scope.zone: expected a non-empty string")
        purposes = scope.get("purposes")
        if not isinstance(purposes, list) or not purposes or any(item not in PURPOSES for item in purposes):
            errors.append(f"scope.purposes: expected values from {sorted(PURPOSES)}")
    if record.get("fidelity") not in FIDELITIES:
        errors.append(f"fidelity: expected one of {sorted(FIDELITIES)}")

    coordinates = record.get("coordinate_system")
    if not isinstance(coordinates, dict):
        errors.append("coordinate_system: expected an object")
    else:
        if coordinates.get("frame") not in {"local", "vehicle"}:
            errors.append("coordinate_system.frame: expected local or vehicle")
        if coordinates.get("units") != "mm":
            errors.append("coordinate_system.units: expected mm")
        for field in ("origin", "axes"):
            if not _text(coordinates.get(field)):
                errors.append(f"coordinate_system.{field}: expected a non-empty string")
        transform = coordinates.get("vehicle_transform")
        if transform is not None and (
            not isinstance(transform, list) or len(transform) != 16
            or not all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in transform)
        ):
            errors.append("coordinate_system.vehicle_transform: expected null or 16 numbers")

    components = record.get("components")
    known_components: set[str] = set()
    if not isinstance(components, list) or len(components) < 2:
        errors.append("components: expected at least two components")
        components = []
    for index, component in enumerate(components):
        label = f"components[{index}]"
        if not isinstance(component, dict):
            errors.append(f"{label}: expected an object")
            continue
        identifier = component.get("component_id")
        if not isinstance(identifier, str) or not COMPONENT_ID.fullmatch(identifier):
            errors.append(f"{label}.component_id: invalid identifier")
        elif identifier in known_components:
            errors.append(f"{label}.component_id: duplicate {identifier}")
        else:
            known_components.add(identifier)
        if component.get("role") not in ROLES:
            errors.append(f"{label}.role: expected one of {sorted(ROLES)}")
        geometry_file = component.get("geometry_file")
        if not isinstance(geometry_file, str):
            errors.append(f"{label}.geometry_file: expected a string")
        else:
            _file(geometry_file, f"{label}.geometry_file", errors)
        accuracy = component.get("accuracy_mm")
        if accuracy is not None and (not isinstance(accuracy, (int, float)) or isinstance(accuracy, bool) or accuracy <= 0):
            errors.append(f"{label}.accuracy_mm: expected null or a positive number")

    interfaces = record.get("interfaces")
    if not isinstance(interfaces, list) or not interfaces:
        errors.append("interfaces: expected at least one interface")
        interfaces = []
    for index, interface in enumerate(interfaces):
        label = f"interfaces[{index}]"
        if not isinstance(interface, dict):
            errors.append(f"{label}: expected an object")
            continue
        if interface.get("kind") not in KINDS:
            errors.append(f"{label}.kind: expected one of {sorted(KINDS)}")
        refs = interface.get("components")
        if not isinstance(refs, list) or len(refs) != 2:
            errors.append(f"{label}.components: expected exactly two component ids")
        elif any(ref not in known_components for ref in refs):
            errors.append(f"{label}.components: references an unknown component")
        required = interface.get("required_measurements")
        if not isinstance(required, list) or not required or not all(_text(item) for item in required):
            errors.append(f"{label}.required_measurements: expected at least one identifier")
        if not _text(interface.get("acceptance_rule")):
            errors.append(f"{label}.acceptance_rule: expected a non-empty rule")
        if interface.get("status") not in INTERFACE_STATUSES:
            errors.append(f"{label}.status: expected one of {sorted(INTERFACE_STATUSES)}")

    geometry = record.get("geometry")
    if not isinstance(geometry, dict):
        errors.append("geometry: expected an object")
    else:
        if geometry.get("master_format") not in {"build123d", "FCStd", "STEP", "none"}:
            errors.append("geometry.master_format: unknown format")
        master_file = geometry.get("master_file")
        if not isinstance(master_file, str):
            errors.append("geometry.master_file: expected a string")
        else:
            _file(master_file, "geometry.master_file", errors)
        derived = geometry.get("derived_files")
        if not isinstance(derived, list) or not all(isinstance(item, str) for item in derived):
            errors.append("geometry.derived_files: expected a string array")
        else:
            for index, item in enumerate(derived):
                _file(item, f"geometry.derived_files[{index}]", errors)

    validation = record.get("validation")
    if not isinstance(validation, dict):
        errors.append("validation: expected an object")
    else:
        status = validation.get("status")
        if status not in VALIDATION_STATUSES:
            errors.append(f"validation.status: expected one of {sorted(VALIDATION_STATUSES)}")
        evidence = validation.get("evidence")
        if not isinstance(evidence, list) or not all(isinstance(item, str) for item in evidence):
            errors.append("validation.evidence: expected a string array")
        limits = validation.get("known_limits")
        if not isinstance(limits, list) or not all(_text(item) for item in limits):
            errors.append("validation.known_limits: expected a string array")
        if status in {"digitally_checked", "physically_correlated"}:
            if record.get("fidelity") in {"F0_reference", "F1_envelope"}:
                errors.append("validation.status: digital checking requires at least F2_interface")
            if any(component.get("accuracy_mm") is None for component in components if isinstance(component, dict)):
                errors.append("validation.status: every component requires known accuracy")
            if not evidence:
                errors.append("validation.evidence: required for a checked twin")

    return errors


def load_and_validate(path: Path) -> list[str]:
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot load JSON: {exc}"]
    return validate_twin(record)


def main() -> int:
    files = sorted(REGISTRY.glob("*.json"))
    if not files:
        print("No twin records found", file=sys.stderr)
        return 1
    failed = False
    for path in files:
        errors = load_and_validate(path)
        if errors:
            failed = True
            for error in errors:
                print(f"{path.relative_to(ROOT)}: {error}", file=sys.stderr)
        else:
            print(f"valid {path.relative_to(ROOT)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

