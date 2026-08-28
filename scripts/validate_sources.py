#!/usr/bin/env python3
"""Validate public-source registry records without external dependencies."""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "catalog" / "sources"
SOURCE_ID_PATTERN = re.compile(r"^SRC-[A-Z0-9][A-Z0-9._-]{2,63}$")

SOURCE_TYPES = {"official", "manufacturer", "measured", "community", "marketplace", "dataset", "academic", "estimated"}
CONTENT_TYPES = {"technical_data", "parts_catalogue", "manual", "drawing", "photograph", "scan", "cad", "mesh", "measurement", "simulation", "material_data"}
ACCESS_STATUSES = {"available", "access_blocked", "robots_excluded", "paywalled", "purchase_required", "unavailable", "not_checked"}
ACCESS_METHODS = {"direct_download", "browser_page_read", "manual_reference", "not_accessed"}
REDISTRIBUTION = {"allowed", "attribution_required", "noncommercial_only", "prohibited", "unknown"}

REQUIRED_KEYS = {"schema_version", "source_id", "title", "url", "publisher", "source_type", "content_types", "coverage", "access", "rights", "quality", "notes"}


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _strings(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _date(value: Any) -> bool:
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def validate_source(record: Any) -> list[str]:
    if not isinstance(record, dict):
        return ["root: expected an object"]
    errors: list[str] = []
    missing = REQUIRED_KEYS - record.keys()
    extra = record.keys() - REQUIRED_KEYS
    if missing:
        errors.append(f"root: missing fields: {', '.join(sorted(missing))}")
    if extra:
        errors.append(f"root: unknown fields: {', '.join(sorted(extra))}")

    if record.get("schema_version") != "1.0.0":
        errors.append("schema_version: expected 1.0.0")
    if not isinstance(record.get("source_id"), str) or not SOURCE_ID_PATTERN.fullmatch(record["source_id"]):
        errors.append("source_id: expected SRC- followed by an uppercase stable identifier")
    for field in ("title", "publisher"):
        if not _text(record.get(field)):
            errors.append(f"{field}: expected a non-empty string")
    if not _url(record.get("url")):
        errors.append("url: expected an http(s) URL")
    if record.get("source_type") not in SOURCE_TYPES:
        errors.append(f"source_type: expected one of {sorted(SOURCE_TYPES)}")
    content_types = record.get("content_types")
    if not isinstance(content_types, list) or not content_types:
        errors.append("content_types: expected at least one value")
    elif any(value not in CONTENT_TYPES for value in content_types):
        errors.append(f"content_types: expected values from {sorted(CONTENT_TYPES)}")

    coverage = record.get("coverage")
    if not isinstance(coverage, dict):
        errors.append("coverage: expected an object")
    else:
        if coverage.get("generation") not in {"993", "generic_automotive", "other_porsche"}:
            errors.append("coverage.generation: expected 993, generic_automotive, or other_porsche")
        for field in ("variants", "parts"):
            if not _strings(coverage.get(field)):
                errors.append(f"coverage.{field}: expected a string array")

    access = record.get("access")
    if not isinstance(access, dict):
        errors.append("access: expected an object")
    else:
        status = access.get("status")
        method = access.get("method")
        accessed_on = access.get("accessed_on")
        if status not in ACCESS_STATUSES:
            errors.append(f"access.status: expected one of {sorted(ACCESS_STATUSES)}")
        if method not in ACCESS_METHODS:
            errors.append(f"access.method: expected one of {sorted(ACCESS_METHODS)}")
        if not _date(accessed_on):
            errors.append("access.accessed_on: expected null or YYYY-MM-DD")
        if status == "not_checked" and method != "not_accessed":
            errors.append("access.method: not_checked requires not_accessed")
        if status == "available" and method == "not_accessed":
            errors.append("access.method: available requires an observed access method")
        if method != "not_accessed" and accessed_on is None:
            errors.append("access.accessed_on: required when the source was accessed")

    rights = record.get("rights")
    if not isinstance(rights, dict):
        errors.append("rights: expected an object")
    else:
        if not _text(rights.get("license")):
            errors.append("rights.license: expected a non-empty string")
        if rights.get("redistribution") not in REDISTRIBUTION:
            errors.append(f"rights.redistribution: expected one of {sorted(REDISTRIBUTION)}")
        if rights.get("redistribution") == "attribution_required" and not _text(rights.get("attribution")):
            errors.append("rights.attribution: required when attribution is required")

    quality = record.get("quality")
    if not isinstance(quality, dict):
        errors.append("quality: expected an object")
    else:
        if quality.get("evidence_level") not in {"A", "B", "C", "D", "E", "unrated"}:
            errors.append("quality.evidence_level: expected A-E or unrated")
        if quality.get("dimensional_accuracy") not in {"measured", "declared", "visual_only", "unknown"}:
            errors.append("quality.dimensional_accuracy: unknown value")
        if not _strings(quality.get("verified_against")):
            errors.append("quality.verified_against: expected a string array")

    return errors


def load_and_validate(path: Path) -> list[str]:
    try:
        return validate_source(json.loads(path.read_text(encoding="utf-8")))
    except json.JSONDecodeError as exc:
        return [f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"]


def main(arguments: list[str] | None = None) -> int:
    args = sys.argv[1:] if arguments is None else arguments
    paths = [Path(value).resolve() for value in args] if args else sorted(REGISTRY.glob("*.json"))
    if not paths:
        print("sources: no source records yet (allowed during Phase 0)")
        return 0

    failures = 0
    for path in paths:
        errors = load_and_validate(path)
        label = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        if errors:
            failures += 1
            print(f"FAIL {label}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"OK   {label}")
    if failures:
        print(f"sources: {failures} invalid record(s)")
        return 1
    print(f"sources: {len(paths)} valid record(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
