#!/usr/bin/env python3
"""Validate complete physical components and their sourced assemblies."""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = ROOT / "catalog" / "components"
ASSEMBLIES = ROOT / "catalog" / "assemblies"
COMPONENT_ID = re.compile(r"^COMP-[A-Z0-9][A-Z0-9._-]{2,79}$")
ASSEMBLY_ID = re.compile(r"^ASM-[A-Z0-9][A-Z0-9._-]{2,79}$")


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _file(value: str, field: str, errors: list[str]) -> None:
    if not value:
        return
    candidate = (ROOT / value).resolve()
    try:
        candidate.relative_to(ROOT)
    except ValueError:
        errors.append(f"{field}: path escapes repository")
        return
    if not candidate.is_file():
        errors.append(f"{field}: referenced file does not exist: {value}")


def validate_component(record: Any) -> list[str]:
    if not isinstance(record, dict):
        return ["root: expected an object"]
    errors: list[str] = []
    expected = {"schema_version", "component_id", "name", "kind", "vehicle", "identifiers", "physical", "geometry", "sources", "eligibility"}
    if expected - record.keys():
        errors.append(f"root: missing fields: {', '.join(sorted(expected - record.keys()))}")
    if record.keys() - expected:
        errors.append(f"root: unknown fields: {', '.join(sorted(record.keys() - expected))}")
    if record.get("schema_version") != "1.0.0":
        errors.append("schema_version: expected 1.0.0")
    identifier = record.get("component_id")
    if not isinstance(identifier, str) or not COMPONENT_ID.fullmatch(identifier):
        errors.append("component_id: invalid")
    if not _text(record.get("name")):
        errors.append("name: expected a non-empty string")
    if record.get("kind") not in {"oem", "aftermarket", "standard", "measured_original"}:
        errors.append("kind: unknown")

    sources = record.get("sources")
    source_ids: set[str] = set()
    if not isinstance(sources, list) or not sources:
        errors.append("sources: expected at least one source")
        sources = []
    for index, source in enumerate(sources):
        label = f"sources[{index}]"
        if not isinstance(source, dict):
            errors.append(f"{label}: expected an object")
            continue
        source_id = source.get("source_id")
        if not _text(source_id):
            errors.append(f"{label}.source_id: expected text")
        elif source_id in source_ids:
            errors.append(f"{label}.source_id: duplicate")
        else:
            source_ids.add(source_id)
        if not _url(source.get("url")):
            errors.append(f"{label}.url: expected http(s) URL")
        if not _date(source.get("accessed_on")):
            errors.append(f"{label}.accessed_on: expected YYYY-MM-DD")
        if not _text(source.get("license")):
            errors.append(f"{label}.license: expected text")
        if not isinstance(source.get("supports"), list) or not source.get("supports"):
            errors.append(f"{label}.supports: expected claims")

    physical = record.get("physical")
    if not isinstance(physical, dict):
        errors.append("physical: expected an object")
        physical = {}
    sizes = physical.get("size_parameters")
    if not isinstance(sizes, list) or not sizes:
        errors.append("physical.size_parameters: expected at least one parameter")
        sizes = []
    for index, parameter in enumerate(sizes):
        if not isinstance(parameter, dict) or not isinstance(parameter.get("value"), (int, float)):
            errors.append(f"physical.size_parameters[{index}]: invalid")
        elif parameter.get("source_id") not in source_ids:
            errors.append(f"physical.size_parameters[{index}].source_id: unknown source")
    mass = physical.get("mass")
    if not isinstance(mass, dict) or not isinstance(mass.get("value_g"), (int, float)) or mass.get("value_g", 0) <= 0:
        errors.append("physical.mass.value_g: expected a positive number")
    elif mass.get("source_id") not in source_ids:
        errors.append("physical.mass.source_id: unknown source")
    material = physical.get("material")
    if not isinstance(material, dict) or not _text(material.get("family")) or not _text(material.get("process")):
        errors.append("physical.material: family and process are required")
    elif material.get("source_id") not in source_ids:
        errors.append("physical.material.source_id: unknown source")

    geometry = record.get("geometry")
    if not isinstance(geometry, dict):
        errors.append("geometry: expected an object")
        geometry = {}
    master_file = geometry.get("master_file")
    if not isinstance(master_file, str):
        errors.append("geometry.master_file: expected a string")
    else:
        _file(master_file, "geometry.master_file", errors)
    if geometry.get("representation") not in {"interface_proxy", "envelope", "detailed_solid", "scan"}:
        errors.append("geometry.representation: unknown")
    if not isinstance(geometry.get("limitations"), list) or not geometry.get("limitations"):
        errors.append("geometry.limitations: expected at least one limitation")

    eligibility = record.get("eligibility")
    if not isinstance(eligibility, dict):
        errors.append("eligibility: expected an object")
    elif eligibility.get("complete_physical_record") is True:
        if errors:
            errors.append("eligibility.complete_physical_record: cannot be true while the record is invalid")
        if eligibility.get("spatial_check") is True and geometry.get("interface_accuracy_mm") is None:
            errors.append("eligibility.spatial_check: requires known interface accuracy")
    return errors


def validate_assembly(record: Any, known_components: dict[str, dict]) -> list[str]:
    if not isinstance(record, dict):
        return ["root: expected an object"]
    errors: list[str] = []
    if record.get("schema_version") != "1.0.0":
        errors.append("schema_version: expected 1.0.0")
    identifier = record.get("assembly_id")
    if not isinstance(identifier, str) or not ASSEMBLY_ID.fullmatch(identifier):
        errors.append("assembly_id: invalid")
    status = record.get("status")
    if status not in {"logical", "positioned", "interface_checked"}:
        errors.append("status: unknown")
    sources = record.get("relationship_sources")
    source_ids = {source.get("source_id") for source in sources if isinstance(source, dict)} if isinstance(sources, list) else set()
    if not sources:
        errors.append("relationship_sources: expected at least one source")
    instances = record.get("instances")
    calculated_mass = 0.0
    if not isinstance(instances, list) or len(instances) < 2:
        errors.append("instances: expected at least two instances")
        instances = []
    for index, instance in enumerate(instances):
        label = f"instances[{index}]"
        if not isinstance(instance, dict):
            errors.append(f"{label}: expected an object")
            continue
        component = known_components.get(instance.get("component_id"))
        if component is None:
            errors.append(f"{label}.component_id: unknown component")
        else:
            quantity = instance.get("quantity")
            if not isinstance(quantity, int) or quantity < 1:
                errors.append(f"{label}.quantity: expected a positive integer")
            else:
                calculated_mass += component["physical"]["mass"]["value_g"] * quantity
        if instance.get("relationship_source_id") not in source_ids:
            errors.append(f"{label}.relationship_source_id: unknown source")
        transform = instance.get("transform")
        if transform is not None and (not isinstance(transform, list) or len(transform) != 16):
            errors.append(f"{label}.transform: expected null or 16 values")
        if status in {"positioned", "interface_checked"} and transform is None:
            errors.append(f"{label}.transform: required for {status}")
    summary = record.get("physical_summary")
    if not isinstance(summary, dict) or not isinstance(summary.get("mass_g"), (int, float)):
        errors.append("physical_summary.mass_g: expected a number")
    elif abs(float(summary["mass_g"]) - calculated_mass) > 0.001:
        errors.append(
            f"physical_summary.mass_g: {summary['mass_g']} does not match component sum {calculated_mass}"
        )
    if isinstance(summary, dict) and summary.get("basis") != "sum_of_component_records":
        errors.append("physical_summary.basis: expected sum_of_component_records")
    return errors


def main() -> int:
    failed = False
    known: dict[str, dict] = {}
    component_files = sorted(COMPONENTS.glob("*.json"))
    if not component_files:
        print("components: no records found", file=sys.stderr)
        return 1
    for path in component_files:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            errors = validate_component(record)
        except (OSError, json.JSONDecodeError) as exc:
            errors = [f"cannot load JSON: {exc}"]
            record = {}
        if errors:
            failed = True
            for error in errors:
                print(f"{path.relative_to(ROOT)}: {error}", file=sys.stderr)
        else:
            known[record["component_id"]] = record
            print(f"valid {path.relative_to(ROOT)}")
    assembly_files = sorted(ASSEMBLIES.glob("*.json"))
    for path in assembly_files:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            errors = validate_assembly(record, known)
        except (OSError, json.JSONDecodeError) as exc:
            errors = [f"cannot load JSON: {exc}"]
        if errors:
            failed = True
            for error in errors:
                print(f"{path.relative_to(ROOT)}: {error}", file=sys.stderr)
        else:
            print(f"valid {path.relative_to(ROOT)}")
    print(f"components: {len(known)} valid, assemblies: {len(assembly_files)} checked")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
