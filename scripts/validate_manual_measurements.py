#!/usr/bin/env python3
"""Validate the quantitative ledger derived from the 993 workshop manual."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from validate_reference import known_source_ids


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "catalog" / "manual"
REQUIRED_ROOT = {
    "$comment",
    "schema_version",
    "source_id",
    "source",
    "manual_pdf_pages",
    "generated_on",
    "extraction",
    "counts",
    "technical_data",
    "torque_specs",
    "measurement_occurrences",
}
RECORD_TYPES = {"technical_data", "torque_spec", "ocr_measurement_occurrence", "ocr_thread_size_occurrence"}
EXTRACTION_STATUSES = {"structured_derived", "ocr_unreviewed", "manually_checked"}


def text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_row(row: Any, label: str, page_limit: int, allowed_types: set[str]) -> list[str]:
    if not isinstance(row, dict):
        return [f"{label}: expected an object"]
    errors: list[str] = []
    if row.get("record_type") not in allowed_types:
        errors.append(f"{label}.record_type: unexpected value")
    page = row.get("pdf_page")
    if not isinstance(page, int) or isinstance(page, bool) or not 1 <= page <= page_limit:
        errors.append(f"{label}.pdf_page: expected an integer from 1 to {page_limit}")
    if not text(row.get("value_text")):
        errors.append(f"{label}.value_text: expected a non-empty string")
    if row.get("record_type") != "technical_data" and not text(row.get("unit")):
        errors.append(f"{label}.unit: expected a non-empty string")
    status = row.get("extraction_status")
    if status not in EXTRACTION_STATUSES:
        errors.append(f"{label}.extraction_status: unexpected value")
    for field in ("context", "page_header", "label", "subject", "thread", "stage", "section", "group", "model", "variant_context"):
        if field in row and not isinstance(row[field], str):
            errors.append(f"{label}.{field}: expected a string")
    return errors


def validate_file(path: Path) -> list[str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"]
    if not isinstance(payload, dict):
        return ["root: expected an object"]
    errors: list[str] = []
    missing = REQUIRED_ROOT - payload.keys()
    extra = payload.keys() - REQUIRED_ROOT
    if missing:
        errors.append(f"root: missing fields: {', '.join(sorted(missing))}")
    if extra:
        errors.append(f"root: unknown fields: {', '.join(sorted(extra))}")
    if payload.get("schema_version") != "1.0.0":
        errors.append("schema_version: expected 1.0.0")
    source_id = payload.get("source_id")
    if source_id not in known_source_ids():
        errors.append(f"source_id: {source_id} is not a registered source")
    page_limit = payload.get("manual_pdf_pages")
    if not isinstance(page_limit, int) or page_limit < 1:
        errors.append("manual_pdf_pages: expected a positive integer")
        page_limit = 1481
    if not text(payload.get("source")) or not text(payload.get("generated_on")):
        errors.append("source/generated_on: expected non-empty strings")
    counts = payload.get("counts")
    if not isinstance(counts, dict):
        errors.append("counts: expected an object")
    else:
        for field in ("technical_data", "torque_specs", "measurement_occurrences", "total_records"):
            if not isinstance(counts.get(field), int) or counts[field] < 0:
                errors.append(f"counts.{field}: expected a non-negative integer")

    specs = payload.get("technical_data")
    torques = payload.get("torque_specs")
    occurrences = payload.get("measurement_occurrences")
    for field, rows, types in (
        ("technical_data", specs, {"technical_data"}),
        ("torque_specs", torques, {"torque_spec"}),
        ("measurement_occurrences", occurrences, {"ocr_measurement_occurrence", "ocr_thread_size_occurrence"}),
    ):
        if not isinstance(rows, list):
            errors.append(f"{field}: expected an array")
            continue
        for index, row in enumerate(rows):
            errors.extend(validate_row(row, f"{field}[{index}]", page_limit, types))
        if isinstance(counts, dict) and counts.get(field) != len(rows):
            errors.append(f"counts.{field}: does not match the array length")

    if isinstance(counts, dict):
        total = sum(len(rows) for rows in (specs or [], torques or [], occurrences or []) if isinstance(rows, list))
        if counts.get("total_records") != total:
            errors.append(f"counts.total_records: {counts.get('total_records')} does not match {total}")

    identifiers: set[str] = set()
    for field, rows in (("technical_data", specs), ("torque_specs", torques), ("measurement_occurrences", occurrences)):
        if not isinstance(rows, list):
            continue
        for index, row in enumerate(rows):
            # The extraction arrays intentionally have no synthetic ID: their
            # stable identity is source section + page + index.
            if isinstance(row, dict) and "measurement_id" in row:
                identifier = row["measurement_id"]
                if not isinstance(identifier, str) or not identifier or identifier in identifiers:
                    errors.append(f"{field}[{index}].measurement_id: missing or duplicate")
                identifiers.add(identifier)
    return errors


def main(arguments: list[str] | None = None) -> int:
    paths = [Path(value).resolve() for value in (arguments if arguments is not None else sys.argv[1:])]
    if not paths:
        paths = sorted(REGISTRY.glob("*.json"))
    if not paths:
        print("manual measurements: no ledger yet")
        return 0
    failures = 0
    for path in paths:
        errors = validate_file(path)
        label = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        if errors:
            failures += 1
            print(f"FAIL {label}")
            for error in errors:
                print(f"  - {error}")
        else:
            payload = json.loads(path.read_text(encoding="utf-8"))
            print(f"OK   {label} ({payload['counts']['total_records']} records)")
    if failures:
        print(f"manual measurements: {failures} invalid file(s)")
        return 1
    print(f"manual measurements: {len(paths)} valid ledger(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
