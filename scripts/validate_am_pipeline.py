#!/usr/bin/env python3
"""Valide le suivi obligatoire des pièces candidates LPBF/DMLS."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "catalog/manufacturing/am-validation-policy.json"
PARTS = ROOT / "catalog/parts"


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def am_parts() -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for path in sorted(PARTS.glob("*.json")):
        record = load(path)
        processes = set(record.get("manufacturing", {}).get("candidate_processes", []))
        if processes & {"LPBF", "DMLS"}:
            records[record["part_id"]] = record
    return records


def validate(policy: dict[str, Any] | None = None) -> list[str]:
    policy = load(POLICY_PATH) if policy is None else policy
    errors: list[str] = []
    records = am_parts()
    tracked = policy.get("tracked_part_ids")
    if not isinstance(tracked, list) or any(not isinstance(item, str) for item in tracked):
        return ["tracked_part_ids: expected string array"]
    if len(tracked) != len(set(tracked)):
        errors.append("tracked_part_ids: duplicates")
    if set(tracked) != set(records):
        missing = sorted(set(records) - set(tracked))
        stale = sorted(set(tracked) - set(records))
        if missing:
            errors.append(f"untracked_am_parts:{','.join(missing)}")
        if stale:
            errors.append(f"stale_tracked_parts:{','.join(stale)}")

    definitions = policy.get("stage_definitions")
    if not isinstance(definitions, list) or not definitions:
        return errors + ["stage_definitions: expected non-empty array"]
    stage_ids = [item.get("stage_id") for item in definitions if isinstance(item, dict)]
    if len(stage_ids) != len(definitions) or any(not isinstance(item, str) for item in stage_ids):
        errors.append("stage_definitions: every stage needs a string stage_id")
        return errors
    if len(stage_ids) != len(set(stage_ids)):
        errors.append("stage_definitions: duplicate stage_id")
    required = {
        item["stage_id"] for item in definitions if item.get("required_for_release") is True
    }
    defaults = policy.get("default_stage_statuses")
    if not isinstance(defaults, dict) or set(defaults) != set(stage_ids):
        errors.append("default_stage_statuses: must cover every stage exactly")
        defaults = {}
    allowed = set(policy.get("allowed_stage_statuses", []))
    if not allowed or any(value not in allowed for value in defaults.values()):
        errors.append("default_stage_statuses: unknown status")

    overrides = policy.get("part_overrides")
    if not isinstance(overrides, dict):
        errors.append("part_overrides: expected object")
        overrides = {}
    unknown_overrides = set(overrides) - set(records)
    if unknown_overrides:
        errors.append(f"part_overrides: unknown parts:{','.join(sorted(unknown_overrides))}")

    for part_id, record in records.items():
        stages = dict(defaults)
        detail = overrides.get(part_id, {})
        stage_overrides = detail.get("stages", {}) if isinstance(detail, dict) else {}
        if not isinstance(stage_overrides, dict):
            errors.append(f"{part_id}: stages must be an object")
            continue
        if set(stage_overrides) - set(stage_ids):
            errors.append(f"{part_id}: unknown stage override")
        evidence_by_stage: dict[str, list[str]] = {}
        for stage_id, value in stage_overrides.items():
            if not isinstance(value, dict):
                errors.append(f"{part_id}:{stage_id}: expected object")
                continue
            status = value.get("status")
            if status not in allowed:
                errors.append(f"{part_id}:{stage_id}: unknown status")
                continue
            stages[stage_id] = status
            evidence = value.get("evidence")
            if not isinstance(evidence, list) or any(not isinstance(item, str) for item in evidence):
                errors.append(f"{part_id}:{stage_id}: evidence must be a string array")
                evidence = []
            evidence_by_stage[stage_id] = evidence
            if status in {"passed", "completed_screening"} and not evidence:
                errors.append(f"{part_id}:{stage_id}: completed stage needs evidence")
            if status == "blocked_missing_input" and not str(value.get("blocker", "")).strip():
                errors.append(f"{part_id}:{stage_id}: blocked stage needs blocker")
            for item in evidence:
                path = (ROOT / item).resolve()
                try:
                    path.relative_to(ROOT)
                except ValueError:
                    errors.append(f"{part_id}:{stage_id}: evidence escapes repository")
                    continue
                if not path.is_file():
                    errors.append(f"{part_id}:{stage_id}: missing evidence:{item}")

        release_passed = all(stages.get(stage_id) == "passed" for stage_id in required)
        if stages.get("11_engineering_release") == "passed" and not release_passed:
            errors.append(f"{part_id}: engineering release precedes required stages")
        if record.get("validation", {}).get("status") == "released" and not release_passed:
            errors.append(f"{part_id}: catalog release without complete AM pipeline")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"FAIL am-pipeline: {error}")
        return 1
    print(f"OK   am-pipeline: {len(am_parts())} LPBF/DMLS candidate parts tracked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
