#!/usr/bin/env python3
"""Validate raw-scan registry records (catalog/scans) without external dependencies."""

from __future__ import annotations

import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "catalog" / "scans"
SCAN_ID_PATTERN = re.compile(r"^SCAN-[A-Z0-9][A-Z0-9._-]{2,63}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
ISO_DATETIME_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:[+-]\d{2}:\d{2}|Z)$")

TRACKS = {"engine", "body", "interior", "chassis", "unknown"}
RESOLUTION_BASIS = {"filename", "vendor_page", "vendor_page_and_filename", "scan_report", "not_declared", "unknown"}
REDISTRIBUTION = {"allowed", "attribution_required", "noncommercial_only", "prohibited", "unknown"}

REQUIRED_KEYS = {
    "schema_version",
    "scan_id",
    "title",
    "path",
    "sha256",
    "bytes",
    "mtime",
    "recorded_on",
    "resolution",
    "subject_part",
    "track",
    "subsystems",
    "duplicate_of",
    "other_paths",
    "linked_source_ids",
    "linked_artifacts",
    "rights",
    "limitations",
    "notes",
}


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _strings(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _datetime(value: Any) -> bool:
    if not isinstance(value, str) or not ISO_DATETIME_PATTERN.fullmatch(value):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def validate_scan(record: Any) -> list[str]:
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
    scan_id = record.get("scan_id")
    if not isinstance(scan_id, str) or not SCAN_ID_PATTERN.fullmatch(scan_id):
        errors.append("scan_id: expected SCAN- followed by an uppercase stable identifier")
    for field in ("title", "path", "subject_part"):
        if not _text(record.get(field)):
            errors.append(f"{field}: expected a non-empty string")

    path = record.get("path")
    if _text(path) and not path.startswith("/"):
        errors.append("path: expected an absolute host path")

    sha = record.get("sha256")
    if not isinstance(sha, str) or not SHA256_PATTERN.fullmatch(sha):
        errors.append("sha256: expected 64 lowercase hex characters")
    size = record.get("bytes")
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        errors.append("bytes: expected a positive integer")
    if not _datetime(record.get("mtime")):
        errors.append("mtime: expected an ISO-8601 datetime with offset")
    if not _date(record.get("recorded_on")):
        errors.append("recorded_on: expected an ISO date")

    resolution = record.get("resolution")
    if not isinstance(resolution, dict):
        errors.append("resolution: expected an object")
    else:
        if not _text(resolution.get("declared")):
            errors.append("resolution.declared: expected a non-empty string (use 'unknown' honestly)")
        if resolution.get("basis") not in RESOLUTION_BASIS:
            errors.append(f"resolution.basis: expected one of {sorted(RESOLUTION_BASIS)}")
        if not isinstance(resolution.get("verified"), bool):
            errors.append("resolution.verified: expected a boolean")

    if record.get("track") not in TRACKS:
        errors.append(f"track: expected one of {sorted(TRACKS)}")
    if not _strings(record.get("subsystems")):
        errors.append("subsystems: expected a list of strings (possibly empty)")
    dup = record.get("duplicate_of")
    if dup is not None and (not isinstance(dup, str) or not SHA256_PATTERN.fullmatch(dup)):
        errors.append("duplicate_of: expected null or a 64-char lowercase sha256")
    if not _strings(record.get("other_paths")):
        errors.append("other_paths: expected a list of strings")
    if not _strings(record.get("linked_source_ids")):
        errors.append("linked_source_ids: expected a list of strings")
    if not _strings(record.get("linked_artifacts")):
        errors.append("linked_artifacts: expected a list of strings")
    if not _strings(record.get("limitations")) or not record["limitations"]:
        errors.append("limitations: expected at least one limitation")

    rights = record.get("rights")
    if not isinstance(rights, dict):
        errors.append("rights: expected an object")
    else:
        for field in ("license", "redistribution", "provenance"):
            if not _text(rights.get(field)):
                errors.append(f"rights.{field}: expected a non-empty string (use 'unknown' honestly)")
        if rights.get("redistribution") not in REDISTRIBUTION:
            errors.append(f"rights.redistribution: expected one of {sorted(REDISTRIBUTION)}")

    if not _text(record.get("notes")):
        errors.append("notes: expected a non-empty string")
    return errors


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    paths = [Path(value).resolve() for value in args] if args else sorted(REGISTRY.glob("*.json"))
    if not paths:
        print("scans: no scan records yet (allowed)")
        return 0

    seen_ids: dict[str, Path] = {}
    seen_hashes: dict[str, Path] = {}
    failures = 0
    for path in paths:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures += 1
            print(f"FAIL {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}")
            print(f"  - invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}")
            continue
        errors = validate_scan(record)
        sid = record.get("scan_id") if isinstance(record, dict) else None
        sha = record.get("sha256") if isinstance(record, dict) else None
        if isinstance(sid, str):
            if sid in seen_ids:
                errors.append(f"scan_id: duplicate id also in {seen_ids[sid].relative_to(ROOT)}")
            else:
                seen_ids[sid] = path
        if isinstance(sha, str) and SHA256_PATTERN.fullmatch(sha):
            canonical = {str(record.get("path")), *[str(p).split(" ")[0] for p in record.get("other_paths", []) if isinstance(p, str)]}
            if sha in seen_hashes and seen_hashes[sha][0] not in canonical:
                errors.append(f"sha256: same payload as {seen_hashes[sha][1].relative_to(ROOT)}; register as duplicate_of or other_paths")
            seen_hashes.setdefault(sha, (str(record.get("path")), path))
        rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        if errors:
            failures += 1
            print(f"FAIL {rel}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"OK   {rel}")
    if failures:
        print(f"scans: {failures} record(s) failed validation")
        return 1
    print(f"scans: {len(paths)} record(s) valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
