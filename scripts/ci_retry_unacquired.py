#!/usr/bin/env python3
"""Decide whether a failed CI run failed only because GitHub never gave some of its jobs a runner (#733).

GitHub's hosted macOS arm64 pool has been short of capacity since 2026-11-18. The two carrier jobs of
"Validate catalogue" are then never acquired: they are cancelled after 15 to 20 minutes with no runner and
no step, and the run shows as failed although nothing ran. ``.github/workflows/retry-unacquired.yml`` calls
this script on the jobs of a failed attempt and re-runs the failed jobs only when it answers yes.

Input: a file of job objects as the GitHub REST API returns them (``/actions/runs/{id}/attempts/{n}/jobs``),
one JSON object per line. Exit 0: every failed job was never acquired, re-run them. Exit 10: do not re-run.
Any other exit is an error. A job that ran and failed is never a reason to re-run.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RERUN, KEEP = 0, 10
FAILED = ("failure", "cancelled", "timed_out")


def never_acquired(job: dict) -> bool:
    """A job no runner picked up: no runner name and no step."""

    return not job.get("runner_name") and not job.get("steps")


def decide(jobs: list[dict]) -> tuple[bool, str]:
    failed = [job for job in jobs if job.get("conclusion") in FAILED]
    if not failed:
        return False, "no failed job"
    ran = [job["name"] for job in failed if not never_acquired(job)]
    if ran:
        return False, "a job that ran failed: " + ", ".join(ran)
    return True, "never given a runner: " + ", ".join(job["name"] for job in failed)


def read_jobs(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {Path(argv[0]).name} JOBS.jsonl", file=sys.stderr)
        return 2
    rerun, why = decide(read_jobs(Path(argv[1])))
    print(("re-run: " if rerun else "keep: ") + why)
    return RERUN if rerun else KEEP


if __name__ == "__main__":
    sys.exit(main(sys.argv))
