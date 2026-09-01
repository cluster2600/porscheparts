#!/usr/bin/env python3
"""Ecrit un rapport de phase atomique sans inclure de secret."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", required=True)
    parser.add_argument(
        "--status",
        required=True,
        choices=("passed", "failed", "blocked", "needs_rerun"),
    )
    parser.add_argument("--exit-code", required=True, type=int)
    parser.add_argument("--started-at", required=True)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--log", type=Path)
    parser.add_argument("--input", action="append", default=[])
    parser.add_argument("--output", action="append", default=[])
    parser.add_argument("--child-report", action="append", default=[])
    parser.add_argument("--note")
    parser.add_argument("--control", type=Path)
    args = parser.parse_args()

    control_summary = None
    if args.control and args.control.is_file():
        control = json.loads(args.control.read_text(encoding="utf-8"))
        control_summary = {
            "job_id": control.get("job_id"),
            "instance_id": control.get("instance_id"),
            "expected_image": control.get("expected_image"),
            "max_dph": control.get("max_dph"),
            "deadline_epoch": control.get("deadline_epoch"),
        }

    payload = {
        "schema_version": "1.0.0",
        "phase": args.phase,
        "status": args.status,
        "passed": args.status == "passed",
        "exit_code": args.exit_code,
        "started_at": args.started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "input_paths": [str(Path(value).resolve()) for value in args.input],
        "output_paths": [str(Path(value).resolve()) for value in args.output],
        "child_reports": [str(Path(value).resolve()) for value in args.child_report],
        "log_path": str(args.log.resolve()) if args.log else None,
        "note": args.note,
        "control": control_summary,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{args.report.name}.", suffix=".tmp", dir=args.report.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, args.report)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
