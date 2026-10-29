#!/usr/bin/env python3
"""Validate the 935 rotor CFD admissibility verdict and keep it tied to its reports.

A mesh or solver study inherits every defect of the geometry it consumes. The
935 rotor wall carries facets that are not traceable to an acquired section, and
on 2026-10-28 eight parameter trials were run and rejected before that was
established. The verdict record exists so the next trial consults one authority
instead of rediscovering this, and so the trials already spent stay visible next
to it.

This validator does not recompute the geometry: the surface and the audit
outputs live in the private evidence release. It checks the things a committed
record can be held to - that the verdict is one of the declared values, that
every finding and every recorded rejection cites a report that exists in this
repository, that each cited digest actually appears in the report it names so
the record cannot drift away from its evidence, and that a blocking verdict
carries both the trials it refuses and the conditions that would clear it.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "twins" / "935-horizontal-cooling-system-f0" / "admissibility.json"
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

VERDICTS = {
    "admissible",
    "inadmissible_for_cfd_parameter_studies",
    "admissible_with_declared_reconstruction",
}
BLOCKING = VERDICTS - {"admissible"}

REQUIRED_KEYS = {
    "schema_version", "recorded_on", "subject", "verdict", "statement",
    "basis", "blocks", "does_not_block", "clears_when", "limitations",
}


def report_text(rel: str, cache: dict[str, str | None]) -> str | None:
    if rel not in cache:
        path = ROOT / rel
        cache[rel] = path.read_text(encoding="utf-8") if path.is_file() else None
    return cache[rel]


def validate(record: dict) -> list[str]:
    errors: list[str] = []
    missing = REQUIRED_KEYS - set(record)
    if missing:
        errors.append(f"missing key(s): {', '.join(sorted(missing))}")
        return errors

    if record["verdict"] not in VERDICTS:
        errors.append(f"verdict: {record['verdict']!r} is not one of {sorted(VERDICTS)}")
    if not str(record["statement"]).strip():
        errors.append("statement: empty; the verdict must say why in prose")

    cache: dict[str, str | None] = {}

    if not record["basis"]:
        errors.append("basis: a verdict with no measured basis is an opinion")
    for index, finding in enumerate(record["basis"]):
        where = f"basis[{index}]"
        for key in ("finding", "report", "evidence_sha256", "caveat"):
            if not str(finding.get(key, "")).strip():
                errors.append(f"{where}.{key}: empty")
        digest = str(finding.get("evidence_sha256", ""))
        if not SHA256_PATTERN.fullmatch(digest):
            errors.append(f"{where}.evidence_sha256: not a sha256 digest")
        text = report_text(str(finding.get("report", "")), cache)
        if text is None:
            errors.append(f"{where}.report: {finding.get('report')!r} is not a file in this repository")
        elif SHA256_PATTERN.fullmatch(digest) and digest not in text:
            errors.append(f"{where}: digest {digest[:12]} does not appear in {finding['report']}; "
                          "the record has drifted from its evidence")

    blocking = record["verdict"] in BLOCKING
    rejections = 0
    for index, family in enumerate(record["blocks"]):
        where = f"blocks[{index}]"
        if not str(family.get("family", "")).strip():
            errors.append(f"{where}.family: empty")
        if not family.get("recorded_rejections"):
            errors.append(f"{where}: a blocked family must list the trials already spent on it")
        for position, trial in enumerate(family.get("recorded_rejections", [])):
            rejections += 1
            spot = f"{where}.recorded_rejections[{position}]"
            if not str(trial.get("change", "")).strip():
                errors.append(f"{spot}.change: empty; name the single setting that was varied")
            if report_text(str(trial.get("report", "")), cache) is None:
                errors.append(f"{spot}.report: {trial.get('report')!r} is not a file in this repository")
            prs = trial.get("pull_requests")
            if not isinstance(prs, list) or not all(isinstance(n, int) for n in prs) or not prs:
                errors.append(f"{spot}.pull_requests: expected a non-empty list of integers")

    if blocking:
        if not record["blocks"]:
            errors.append("blocks: a blocking verdict must name what it refuses")
        if not record["clears_when"]:
            errors.append("clears_when: a blocking verdict must say what would lift it")
        if not record["does_not_block"]:
            errors.append("does_not_block: name the work that stays open, or the verdict reads as a halt")
    if not record["limitations"]:
        errors.append("limitations: empty")

    return errors + ([] if rejections else ["blocks: no recorded rejection anywhere"])


def main() -> int:
    if not RECORD.is_file():
        print(f"FAIL {RECORD.relative_to(ROOT)}")
        print("  - admissibility record missing")
        return 1
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    errors = validate(record)
    rel = RECORD.relative_to(ROOT)
    if errors:
        print(f"FAIL {rel}")
        for error in errors:
            print(f"  - {error}")
        print("935 admissibility: record refused")
        return 1
    families = len(record["blocks"])
    spent = sum(len(f["recorded_rejections"]) for f in record["blocks"])
    print(f"OK   {rel} ({record['verdict']}, {families} blocked family(ies), "
          f"{spent} recorded rejection(s))")
    print("935 admissibility: verdict cites its evidence and names what it refuses")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
