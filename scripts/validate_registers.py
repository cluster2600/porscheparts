#!/usr/bin/env python3
"""Validate the cross-record registers in catalog/registers.

Two registers live there:

- ``contradictions.json``: every documentary contradiction, with the values in
  conflict, the registered source of each value and what would resolve it;
- ``993-source-classification.json``: for each system of the 993 assembly
  skeleton, the qualified official or manufacturer sources that cover it, and,
  per source, model years and dated availability observations.

The checks are about attachment, not about truth: a cited source must exist, a
cited manual value must exist and belong to that source, a quoted year must be
present verbatim in the record it is quoted from, and absence from a vendor or
from the Parts Finder can never be recorded as a discontinuation.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
REGISTERS = ROOT / "catalog" / "registers"
SOURCES = ROOT / "catalog" / "sources"
SKELETON = ROOT / "catalog" / "reference" / "993-assembly-skeleton.json"
MANUAL_993 = ROOT / "catalog" / "measurements" / "MEAS-MANUAL-993-ALL.json"
CONTRADICTIONS = REGISTERS / "contradictions.json"
CLASSIFICATION = REGISTERS / "993-source-classification.json"

CONTRADICTION_ID = re.compile(r"^CTR-\d{4}$")
GENERATIONS = {"993", "964", "964_993", "generic"}
STATUSES = {"open", "resolved"}
QUALIFIED_TYPES = {"official", "manufacturer"}
QUALIFIED_LEVELS = {"A", "B"}
ROLES = {
    "assembly_breakdown",
    "service_specification",
    "declared_dimensions",
    "type_approval",
    "documentation_index",
}
YEAR_FIELDS = {"title", "coverage.variants", "notes"}
AVAILABILITY = {
    "listed_for_sale",
    "listed_on_request",
    "listed_out_of_stock",
    "not_listed_on_channel",
    "channel_unavailable",
    "channel_unreadable",
    "robots_excluded",
    "login_required",
    "discontinued_per_publisher",
}
BASES = {"record_text", "register_observation"}


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _repo_file(value: Any) -> bool:
    if not _text(value):
        return False
    candidate = (ROOT / value).resolve()
    return candidate.is_relative_to(ROOT) and candidate.is_file()


def load_sources() -> dict[str, dict]:
    records: dict[str, dict] = {}
    for path in SOURCES.glob("*.json"):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(record, dict) and isinstance(record.get("source_id"), str):
            records[record["source_id"]] = record
    return records


def load_manual_values() -> dict[str, str]:
    payload = json.loads(MANUAL_993.read_text(encoding="utf-8"))
    return {item["value_id"]: item["source_id"] for item in payload["declared_values"]}


def load_skeleton() -> dict[str, set[str]]:
    payload = json.loads(SKELETON.read_text(encoding="utf-8"))
    return {
        system["system_id"]: {item["illustration"] for item in system["illustrations"]}
        for system in payload["systems"]
    }


def validate_contradictions(payload: Any, sources: dict[str, dict]) -> list[str]:
    if not isinstance(payload, dict):
        return ["root: expected an object"]
    errors: list[str] = []
    if payload.get("schema_version") != "1.0.0":
        errors.append("schema_version: expected 1.0.0")
    if _date(payload.get("updated_on")) is None:
        errors.append("updated_on: expected YYYY-MM-DD")
    entries = payload.get("entries")
    if not isinstance(entries, list) or not entries:
        return errors + ["entries: expected a non-empty array"]
    seen: set[str] = set()
    for index, entry in enumerate(entries):
        label = f"entries[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{label}: expected an object")
            continue
        identifier = entry.get("contradiction_id")
        if not isinstance(identifier, str) or not CONTRADICTION_ID.fullmatch(identifier):
            errors.append(f"{label}.contradiction_id: expected CTR-NNNN")
        elif identifier in seen:
            errors.append(f"{label}.contradiction_id: duplicate {identifier}")
        else:
            seen.add(identifier)
            label = identifier
        if not _text(entry.get("subject")):
            errors.append(f"{label}.subject: expected a non-empty string")
        if entry.get("generation") not in GENERATIONS:
            errors.append(f"{label}.generation: expected one of {sorted(GENERATIONS)}")
        status = entry.get("status")
        if status not in STATUSES:
            errors.append(f"{label}.status: expected open or resolved")
        elif status == "open" and not _text(entry.get("next_step")):
            errors.append(f"{label}.next_step: required while the contradiction is open")
        elif status == "resolved" and not _text(entry.get("resolution")):
            errors.append(f"{label}.resolution: required once the contradiction is resolved")

        pointers = entry.get("register_pointer")
        if pointers is not None:
            if not isinstance(pointers, list) or not pointers:
                errors.append(f"{label}.register_pointer: expected a non-empty array of paths")
            else:
                for path in pointers:
                    if not _repo_file(path):
                        errors.append(f"{label}.register_pointer: file not found: {path}")
        values = entry.get("values")
        if not isinstance(values, list):
            errors.append(f"{label}.values: expected an array")
            values = []
        if len(values) < 2 and not pointers:
            errors.append(f"{label}.values: a contradiction needs two values or a register_pointer")
        for position, item in enumerate(values):
            where = f"{label}.values[{position}]"
            if not isinstance(item, dict):
                errors.append(f"{where}: expected an object")
                continue
            if not _text(item.get("value")):
                errors.append(f"{where}.value: expected a non-empty string")
            if not _text(item.get("location")):
                errors.append(f"{where}.location: expected a non-empty string")
            source_id = item.get("source_id")
            if source_id is None:
                if not _repo_file(item.get("repository_path")):
                    errors.append(f"{where}: a value without source_id needs an existing repository_path")
            elif source_id not in sources:
                errors.append(f"{where}.source_id: {source_id} is not a registered source")
            if "repository_path" in item and not _repo_file(item.get("repository_path")):
                errors.append(f"{where}.repository_path: file not found: {item.get('repository_path')}")
        flagged = entry.get("flagged_in")
        if not isinstance(flagged, list) or not flagged:
            errors.append(f"{label}.flagged_in: expected at least one repository path")
        else:
            for path in flagged:
                if not _repo_file(path):
                    errors.append(f"{label}.flagged_in: file not found: {path}")
    return errors


def _field_text(record: dict, field: str) -> list[str]:
    if field == "coverage.variants":
        variants = record.get("coverage", {}).get("variants", [])
        return [item for item in variants if isinstance(item, str)]
    value = record.get(field)
    return [value] if isinstance(value, str) else []


def _quoted(record: dict, field: Any, quote: Any) -> bool:
    if field not in YEAR_FIELDS or not _text(quote):
        return False
    return any(quote in text for text in _field_text(record, field))


def validate_family(
    family: Any,
    label: str,
    sources: dict[str, dict],
    manual_values: dict[str, str],
    skeleton: dict[str, set[str]],
) -> list[str]:
    if not isinstance(family, dict):
        return [f"{label}: expected an object"]
    errors: list[str] = []
    family_id = family.get("family_id")
    if family_id not in skeleton:
        errors.append(f"{label}.family_id: {family_id} is not a system of the assembly skeleton")
    if not _text(family.get("name")):
        errors.append(f"{label}.name: expected a non-empty string")
    if not _text(family.get("gaps")):
        errors.append(f"{label}.gaps: state what the qualified sources do not cover")
    qualified = family.get("qualified_sources")
    if not isinstance(qualified, list) or not qualified:
        return errors + [f"{label}.qualified_sources: expected at least one source"]
    for position, item in enumerate(qualified):
        where = f"{label}.qualified_sources[{position}]"
        if not isinstance(item, dict):
            errors.append(f"{where}: expected an object")
            continue
        source_id = item.get("source_id")
        record = sources.get(source_id)
        if record is None:
            errors.append(f"{where}.source_id: {source_id} is not a registered source")
            continue
        if record.get("source_type") not in QUALIFIED_TYPES:
            errors.append(f"{where}.source_id: {source_id} is {record.get('source_type')}, not official or manufacturer")
        if record.get("quality", {}).get("evidence_level") not in QUALIFIED_LEVELS:
            errors.append(f"{where}.source_id: {source_id} is not rated A or B")
        if item.get("role") not in ROLES:
            errors.append(f"{where}.role: expected one of {sorted(ROLES)}")
        if not _text(item.get("location")):
            errors.append(f"{where}.location: say where in the source the family is covered")
        for value_id in item.get("value_ids", []) or []:
            owner = manual_values.get(value_id)
            if owner is None:
                errors.append(f"{where}.value_ids: {value_id} is not in MEAS-MANUAL-993-ALL")
            elif owner != source_id:
                errors.append(f"{where}.value_ids: {value_id} belongs to {owner}, not {source_id}")
        illustrations = item.get("pet_illustrations")
        if illustrations is not None:
            known = skeleton.get(family_id, set())
            for end in ("first", "last"):
                value = illustrations.get(end) if isinstance(illustrations, dict) else None
                if value not in known:
                    errors.append(f"{where}.pet_illustrations.{end}: {value} is not an illustration of {family_id}")
    return errors


def validate_source_entry(entry: Any, label: str, sources: dict[str, dict], today: date) -> list[str]:
    if not isinstance(entry, dict):
        return [f"{label}: expected an object"]
    errors: list[str] = []
    source_id = entry.get("source_id")
    record = sources.get(source_id)
    if record is None:
        return [f"{label}.source_id: {source_id} is not a registered source"]
    if record.get("source_type") not in QUALIFIED_TYPES:
        errors.append(f"{label}.source_id: only official or manufacturer sources are classified here")
    if "model_years" not in entry and "availability" not in entry:
        errors.append(f"{label}: classify model_years, availability or both")

    years = entry.get("model_years")
    if years is not None:
        if not isinstance(years, dict):
            errors.append(f"{label}.model_years: expected an object")
        else:
            start, end, quote = years.get("from"), years.get("to"), years.get("quote")
            if not isinstance(start, int) or isinstance(start, bool) or not 1960 <= start <= 2030:
                errors.append(f"{label}.model_years.from: expected a four-digit year")
            if end is not None and (not isinstance(end, int) or isinstance(end, bool) or not 1960 <= end <= 2030):
                errors.append(f"{label}.model_years.to: expected a four-digit year or null")
            if isinstance(start, int) and isinstance(end, int) and end < start:
                errors.append(f"{label}.model_years: to precedes from")
            if not _quoted(record, years.get("stated_in"), quote):
                errors.append(f"{label}.model_years.quote: not found verbatim in {source_id} {years.get('stated_in')}")
            elif isinstance(start, int) and str(start) not in quote:
                errors.append(f"{label}.model_years.from: {start} does not appear in the quote")
            elif isinstance(end, int) and str(end) not in quote:
                errors.append(f"{label}.model_years.to: {end} does not appear in the quote")
            elif end is None and "onward" not in quote:
                errors.append(f"{label}.model_years.to: null is only allowed for an open-ended ('onward') statement")

    observations = entry.get("availability")
    if observations is not None:
        if not isinstance(observations, list) or not observations:
            errors.append(f"{label}.availability: expected a non-empty array")
            observations = []
        for position, item in enumerate(observations):
            where = f"{label}.availability[{position}]"
            if not isinstance(item, dict):
                errors.append(f"{where}: expected an object")
                continue
            observed = _date(item.get("observed_on"))
            if observed is None:
                errors.append(f"{where}.observed_on: expected YYYY-MM-DD")
            elif observed > today:
                errors.append(f"{where}.observed_on: in the future")
            status = item.get("status")
            if status not in AVAILABILITY:
                errors.append(f"{where}.status: expected one of {sorted(AVAILABILITY)}")
            if not _url(item.get("channel_url")):
                errors.append(f"{where}.channel_url: expected the http(s) page observed")
            basis = item.get("basis")
            if basis not in BASES:
                errors.append(f"{where}.basis: expected record_text or register_observation")
            elif basis == "record_text":
                if not _quoted(record, item.get("stated_in"), item.get("quote")):
                    errors.append(f"{where}.quote: not found verbatim in {source_id} {item.get('stated_in')}")
            elif not _text(item.get("quote")):
                errors.append(f"{where}.quote: an observation keeps the page wording it rests on")
            if status == "discontinued_per_publisher":
                if basis != "register_observation" or not _text(item.get("publisher_statement")):
                    errors.append(f"{where}: discontinued_per_publisher needs the publisher's own statement")
    return errors


def validate_classification(
    payload: Any,
    sources: dict[str, dict],
    manual_values: dict[str, str],
    skeleton: dict[str, set[str]],
    today: date | None = None,
) -> list[str]:
    if not isinstance(payload, dict):
        return ["root: expected an object"]
    today = today or date.today()
    errors: list[str] = []
    if payload.get("schema_version") != "1.0.0":
        errors.append("schema_version: expected 1.0.0")
    if payload.get("generation") != "993":
        errors.append("generation: expected 993")
    if not isinstance(payload.get("rules"), list) or not payload["rules"]:
        errors.append("rules: expected the classification rules")
    families = payload.get("families")
    if not isinstance(families, list):
        errors.append("families: expected an array")
        families = []
    covered: set[str] = set()
    for index, family in enumerate(families):
        errors.extend(validate_family(family, f"families[{index}]", sources, manual_values, skeleton))
        if isinstance(family, dict) and isinstance(family.get("family_id"), str):
            if family["family_id"] in covered:
                errors.append(f"families[{index}].family_id: duplicate {family['family_id']}")
            covered.add(family["family_id"])
    for missing in sorted(set(skeleton) - covered):
        errors.append(f"families: system {missing} of the assembly skeleton has no qualified source")
    entries = payload.get("sources")
    if not isinstance(entries, list):
        return errors + ["sources: expected an array"]
    seen: set[str] = set()
    for index, entry in enumerate(entries):
        errors.extend(validate_source_entry(entry, f"sources[{index}]", sources, today))
        if isinstance(entry, dict):
            source_id = entry.get("source_id")
            if source_id in seen:
                errors.append(f"sources[{index}].source_id: duplicate {source_id}")
            seen.add(source_id)
    return errors


def main(arguments: list[str] | None = None) -> int:
    del arguments
    sources = load_sources()
    failures = 0
    checks = (
        (CONTRADICTIONS, lambda payload: validate_contradictions(payload, sources)),
        (
            CLASSIFICATION,
            lambda payload: validate_classification(payload, sources, load_manual_values(), load_skeleton()),
        ),
    )
    for path, check in checks:
        label = path.relative_to(ROOT)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"FAIL {label}\n  - cannot load JSON: {exc}")
            failures += 1
            continue
        errors = check(payload)
        if errors:
            failures += 1
            print(f"FAIL {label}")
            for error in errors:
                print(f"  - {error}")
        elif path == CONTRADICTIONS:
            entries = payload["entries"]
            still_open = sum(1 for entry in entries if entry.get("status") == "open")
            print(f"OK   {label} ({len(entries)} contradictions, {still_open} open)")
        else:
            print(
                f"OK   {label} ({len(payload['families'])} families covered, "
                f"{len(payload['sources'])} sources classified)"
            )
    if failures:
        print(f"registers: {failures} invalid register(s)")
        return 1
    print("registers: every cited source, manual value and quoted year resolves")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
