#!/usr/bin/env python3
"""Validate documentary specifications and their evidence boundary."""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "catalog" / "specifications"
SET_ID = re.compile(r"^SPEC-[A-Z0-9][A-Z0-9._-]{2,63}$")
RECORD_ID = re.compile(r"^[A-Z]{2}-[A-F0-9]{12}$")
KINDS = {"technical_data", "tightening_torque"}


def _number_or_none(value: Any) -> bool:
    return value is None or (isinstance(value, (int, float)) and not isinstance(value, bool))


def validate_specification_set(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return ["root: expected an object"]
    errors: list[str] = []
    required = {"schema_version", "specification_set_id", "title", "kind", "source", "records", "notes"}
    if set(value) != required:
        errors.append("root: fields do not match the documentary specification contract")
    if value.get("schema_version") != "1.0.0":
        errors.append("schema_version: expected 1.0.0")
    identifier = value.get("specification_set_id")
    if not isinstance(identifier, str) or not SET_ID.fullmatch(identifier):
        errors.append("specification_set_id: invalid stable identifier")
    kind = value.get("kind")
    if kind not in KINDS:
        errors.append(f"kind: expected one of {sorted(KINDS)}")

    source = value.get("source")
    if not isinstance(source, dict):
        errors.append("source: expected an object")
    else:
        if source.get("method") != "derived_facts_from_ocr_transcription":
            errors.append("source.method: documentary imports must retain their OCR provenance")
        for field in ("retrieved_on", "upstream_reviewed_on"):
            try:
                parsed = date.fromisoformat(source.get(field, ""))
                if parsed > date.today():
                    errors.append(f"source.{field}: date is in the future")
            except (TypeError, ValueError):
                errors.append(f"source.{field}: expected YYYY-MM-DD")

    records = value.get("records")
    if not isinstance(records, list) or not records:
        errors.append("records: expected at least one record")
        return errors
    seen: set[str] = set()
    for index, record in enumerate(records):
        label = f"records[{index}]"
        if not isinstance(record, dict):
            errors.append(f"{label}: expected an object")
            continue
        record_id = record.get("record_id")
        if not isinstance(record_id, str) or not RECORD_ID.fullmatch(record_id):
            errors.append(f"{label}.record_id: invalid identifier")
        elif record_id in seen:
            errors.append(f"{label}.record_id: duplicate identifier {record_id}")
        else:
            seen.add(record_id)
        if record.get("verification_status") != "ocr_transcription_unverified":
            errors.append(f"{label}.verification_status: OCR data cannot be promoted automatically")
        if not isinstance(record.get("page"), int) or record["page"] < 1:
            errors.append(f"{label}.page: expected a positive manual page")
        if kind == "technical_data":
            for field in ("subject", "label", "raw_value"):
                if not isinstance(record.get(field), str) or not record[field].strip():
                    errors.append(f"{label}.{field}: expected a non-empty string")
            if not isinstance(record.get("raw_values"), list):
                errors.append(f"{label}.raw_values: expected an array")
            if not isinstance(record.get("raw_variants"), list):
                errors.append(f"{label}.raw_variants: expected an array")
        elif kind == "tightening_torque":
            for field in ("torque_nm", "torque_nm_max", "tolerance_nm", "angle_degrees", "torque_ft_lb"):
                if not _number_or_none(record.get(field)):
                    errors.append(f"{label}.{field}: expected null or a number")
            if all(record.get(field) is None for field in ("torque_nm", "angle_degrees")):
                errors.append(f"{label}: expected a torque or an angle")
    return errors


def load_and_validate(path: Path) -> list[str]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot load JSON: {exc}"]
    return validate_specification_set(value)


def main() -> int:
    paths = sorted(REGISTRY.glob("*.json"))
    if not paths:
        print("specifications: no documentary records yet")
        return 0
    failed = False
    total = 0
    for path in paths:
        value = json.loads(path.read_text(encoding="utf-8"))
        errors = validate_specification_set(value)
        if errors:
            failed = True
            for error in errors:
                print(f"ERROR {path.relative_to(ROOT)}: {error}")
        else:
            count = len(value["records"])
            total += count
            print(f"OK   {path.relative_to(ROOT)} ({count} records)")
    if not failed:
        print(f"specifications: {total} documentary record(s)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
