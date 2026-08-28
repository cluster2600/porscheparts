#!/usr/bin/env python3
"""Validate catalogue records with project-specific, dependency-free rules."""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog" / "parts"
PART_ID_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9._-]{2,63}$")

SAFETY_CLASSES = {
    "non_critical",
    "functional",
    "safety_critical",
    "prohibited_pending_engineering",
}
STATUSES = {
    "concept",
    "dimensionally_reviewed",
    "prototype_fitted",
    "functionally_tested",
    "engineering_reviewed",
    "released",
}
SOURCE_TYPES = {
    "official",
    "manufacturer",
    "measured",
    "community",
    "public_model",
    "estimated",
}
GEOMETRY_SOURCE_TYPES = {
    "measured",
    "scan",
    "reverse_engineered",
    "public_model",
    "estimated",
    "mixed",
}
PROCESSES = {"FFF", "SLA", "SLS", "MJF", "LPBF", "DMLS", "CNC", "sheet_metal", "casting"}

TOP_LEVEL_KEYS = {
    "schema_version",
    "part_id",
    "name",
    "description",
    "vehicle",
    "classification",
    "geometry",
    "provenance",
    "manufacturing",
    "titanium",
    "validation",
}


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _is_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _is_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _section(record: dict[str, Any], name: str, errors: list[str]) -> dict[str, Any]:
    value = record.get(name)
    if not isinstance(value, dict):
        errors.append(f"{name}: expected an object")
        return {}
    return value


def _validate_file_reference(value: str, field: str, errors: list[str]) -> None:
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


def validate_record(record: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(record, dict):
        return ["root: expected an object"]

    missing = TOP_LEVEL_KEYS - record.keys()
    extra = record.keys() - TOP_LEVEL_KEYS
    if missing:
        errors.append(f"root: missing fields: {', '.join(sorted(missing))}")
    if extra:
        errors.append(f"root: unknown fields: {', '.join(sorted(extra))}")

    if record.get("schema_version") != "1.0.0":
        errors.append("schema_version: expected 1.0.0")
    part_id = record.get("part_id")
    if not isinstance(part_id, str) or not PART_ID_PATTERN.fullmatch(part_id):
        errors.append("part_id: expected 3-64 uppercase letters, digits, dots, underscores, or hyphens")
    if not _is_non_empty_string(record.get("name")):
        errors.append("name: expected a non-empty string")
    if not _is_non_empty_string(record.get("description")):
        errors.append("description: expected a non-empty string")

    vehicle = _section(record, "vehicle", errors)
    if vehicle.get("generation") != "993":
        errors.append("vehicle.generation: expected 993")
    variants = vehicle.get("variants")
    if not _is_string_list(variants) or not variants:
        errors.append("vehicle.variants: expected at least one string")
    years = vehicle.get("model_years")
    if not isinstance(years, dict):
        errors.append("vehicle.model_years: expected an object")
    else:
        year_from = years.get("from")
        year_to = years.get("to")
        if not isinstance(year_from, int) or not 1993 <= year_from <= 1998:
            errors.append("vehicle.model_years.from: expected an integer from 1993 to 1998")
        if not isinstance(year_to, int) or not 1993 <= year_to <= 1998:
            errors.append("vehicle.model_years.to: expected an integer from 1993 to 1998")
        if isinstance(year_from, int) and isinstance(year_to, int) and year_from > year_to:
            errors.append("vehicle.model_years: from must be less than or equal to to")
    if not _is_string_list(vehicle.get("porsche_part_numbers")):
        errors.append("vehicle.porsche_part_numbers: expected a string array")

    classification = _section(record, "classification", errors)
    safety_class = classification.get("safety_class")
    if safety_class not in SAFETY_CLASSES:
        errors.append(f"classification.safety_class: expected one of {sorted(SAFETY_CLASSES)}")
    if not _is_non_empty_string(classification.get("category")):
        errors.append("classification.category: expected a non-empty string")
    if not _is_non_empty_string(classification.get("intended_use")):
        errors.append("classification.intended_use: expected a non-empty string")

    geometry = _section(record, "geometry", errors)
    if geometry.get("source_type") not in GEOMETRY_SOURCE_TYPES:
        errors.append(f"geometry.source_type: expected one of {sorted(GEOMETRY_SOURCE_TYPES)}")
    if geometry.get("master_format") not in {"FCStd", "OpenSCAD", "STEP", "none"}:
        errors.append("geometry.master_format: expected FCStd, OpenSCAD, STEP, or none")
    if geometry.get("units") != "mm":
        errors.append("geometry.units: expected mm")
    accuracy = geometry.get("accuracy_mm")
    if accuracy is not None and (not isinstance(accuracy, (int, float)) or accuracy <= 0):
        errors.append("geometry.accuracy_mm: expected null or a positive number")
    master_file = geometry.get("master_file")
    if not isinstance(master_file, str):
        errors.append("geometry.master_file: expected a string")
    else:
        _validate_file_reference(master_file, "geometry.master_file", errors)
    derived_files = geometry.get("derived_files")
    if not _is_string_list(derived_files):
        errors.append("geometry.derived_files: expected a string array")
    else:
        for index, filename in enumerate(derived_files):
            _validate_file_reference(filename, f"geometry.derived_files[{index}]", errors)

    provenance = _section(record, "provenance", errors)
    if not _is_non_empty_string(provenance.get("record_license")):
        errors.append("provenance.record_license: expected a non-empty string")
    sources = provenance.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append("provenance.sources: expected at least one source")
    else:
        for index, source in enumerate(sources):
            prefix = f"provenance.sources[{index}]"
            if not isinstance(source, dict):
                errors.append(f"{prefix}: expected an object")
                continue
            if not _is_non_empty_string(source.get("title")):
                errors.append(f"{prefix}.title: expected a non-empty string")
            if not _is_url(source.get("url")):
                errors.append(f"{prefix}.url: expected an http(s) URL")
            if source.get("source_type") not in SOURCE_TYPES:
                errors.append(f"{prefix}.source_type: expected one of {sorted(SOURCE_TYPES)}")
            if not _is_non_empty_string(source.get("license")):
                errors.append(f"{prefix}.license: expected a non-empty string")
            if not _is_date(source.get("accessed_on")):
                errors.append(f"{prefix}.accessed_on: expected YYYY-MM-DD")

    manufacturing = _section(record, "manufacturing", errors)
    candidate_processes = manufacturing.get("candidate_processes")
    if not isinstance(candidate_processes, list) or not candidate_processes:
        errors.append("manufacturing.candidate_processes: expected at least one process")
    elif any(process not in PROCESSES for process in candidate_processes):
        errors.append(f"manufacturing.candidate_processes: expected values from {sorted(PROCESSES)}")
    preferred_process = manufacturing.get("preferred_process")
    if preferred_process not in PROCESSES | {"undecided"}:
        errors.append("manufacturing.preferred_process: unknown process")
    if not isinstance(manufacturing.get("material"), dict):
        errors.append("manufacturing.material: expected an object")
    if not _is_string_list(manufacturing.get("post_processing")):
        errors.append("manufacturing.post_processing: expected a string array")
    supplier_requirements = manufacturing.get("supplier_requirements")
    if not _is_string_list(supplier_requirements):
        errors.append("manufacturing.supplier_requirements: expected a string array")

    titanium = _section(record, "titanium", errors)
    applicable = titanium.get("applicable")
    if not isinstance(applicable, bool):
        errors.append("titanium.applicable: expected a boolean")
    if titanium.get("hip_required") not in {"yes", "no", "to_be_determined", "not_applicable"}:
        errors.append("titanium.hip_required: unknown value")
    if not _is_string_list(titanium.get("machined_surfaces")):
        errors.append("titanium.machined_surfaces: expected a string array")
    if not _is_string_list(titanium.get("inspection")):
        errors.append("titanium.inspection: expected a string array")
    if applicable is True:
        for field in ("alloy", "heat_treatment", "galvanic_isolation"):
            if not _is_non_empty_string(titanium.get(field)):
                errors.append(f"titanium.{field}: required when titanium is applicable")
        if not titanium.get("inspection"):
            errors.append("titanium.inspection: at least one inspection is required")
        if not supplier_requirements:
            errors.append("manufacturing.supplier_requirements: required for titanium")
        if preferred_process not in {"LPBF", "DMLS", "CNC", "sheet_metal", "casting"}:
            errors.append("manufacturing.preferred_process: incompatible with a titanium final part")

    validation = _section(record, "validation", errors)
    status = validation.get("status")
    if status not in STATUSES:
        errors.append(f"validation.status: expected one of {sorted(STATUSES)}")
    for field in ("vehicle_tested", "evidence", "known_limits"):
        if not _is_string_list(validation.get(field)):
            errors.append(f"validation.{field}: expected a string array")
    reviewed_on = validation.get("reviewed_on")
    if reviewed_on is not None and not _is_date(reviewed_on):
        errors.append("validation.reviewed_on: expected null or YYYY-MM-DD")

    if status == "released" and safety_class in {"safety_critical", "prohibited_pending_engineering"}:
        if not _is_non_empty_string(validation.get("reviewed_by")):
            errors.append("validation.reviewed_by: required to release a critical part")
        if not validation.get("evidence"):
            errors.append("validation.evidence: required to release a critical part")
        if not manufacturing.get("supplier_requirements"):
            errors.append("manufacturing.supplier_requirements: required to release a critical part")
        if not titanium.get("inspection") and applicable is True:
            errors.append("titanium.inspection: required to release a critical titanium part")
    if status == "released" and safety_class == "prohibited_pending_engineering":
        errors.append("validation.status: a prohibited part cannot be released")

    return errors


def load_and_validate(path: Path) -> list[str]:
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"]
    return validate_record(record)


def catalogue_paths(arguments: list[str]) -> list[Path]:
    if arguments:
        return [Path(argument).resolve() for argument in arguments]
    return sorted(CATALOG.glob("*.json"))


def main(arguments: list[str] | None = None) -> int:
    paths = catalogue_paths(sys.argv[1:] if arguments is None else arguments)
    if not paths:
        print("catalogue: no part records yet (allowed during Phase 0)")
        return 0

    failures = 0
    for path in paths:
        errors = load_and_validate(path)
        if errors:
            failures += 1
            print(f"FAIL {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"OK   {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}")

    if failures:
        print(f"catalogue: {failures} invalid record(s)")
        return 1
    print(f"catalogue: {len(paths)} valid record(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
