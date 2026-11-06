#!/usr/bin/env python3
"""Refuse solver output tracked under the git-ignored ``work/`` directory.

``work/`` is ignored because it holds local runs. A few case decks are tracked
there deliberately (dictionaries, initial conditions, scripts, run records and
metrics), but solver output is not: AGENTS.md keeps solver dumps out of Git and
records only their hashes, settings and numerical results. Output that was
tracked before this gate is listed, with its digest and a recovery commit, in
``catalog/registers/untracked-solver-output.json``.

A tracked path under ``work/`` is refused when it is:

- inside a numeric time directory other than ``0`` (``100/``, ``0.5/``, ...);
- inside ``postProcessing/``, ``processor*/`` or a ``polyMesh/`` directory;
- a solver or utility log (``*.log`` or ``log.*``).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "catalog" / "registers" / "untracked-solver-output.json"
TIME_DIR = re.compile(r"^\d+(\.\d+)?(e[+-]?\d+)?$")


def solver_output_reason(path: str) -> str | None:
    """Return why ``path`` counts as solver output, or None if it does not."""
    parts = path.split("/")
    if not parts or parts[0] != "work":
        return None
    for directory in parts[:-1]:
        if TIME_DIR.match(directory) and float(directory) != 0.0:
            return f"time directory {directory}/"
        if directory == "postProcessing":
            return "postProcessing/"
        if directory.startswith("processor"):
            return f"decomposition directory {directory}/"
        if directory == "polyMesh":
            return "generated mesh polyMesh/"
    name = parts[-1]
    if name.endswith(".log") or name.startswith("log."):
        return "solver or utility log"
    return None


def tracked_paths() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "-z", "--", "work"],
        cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout
    return [p for p in out.split("\0") if p]


def check_register() -> list[str]:
    errors: list[str] = []
    data = json.loads(REGISTER.read_text(encoding="utf-8"))
    commit = data.get("recovery_commit", "")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        errors.append("register: recovery_commit must be a full commit id")
    for entry in data.get("files", []):
        path = entry.get("path", "")
        if solver_output_reason(path) is None:
            errors.append(f"register: {path} is not solver output under work/")
        if not re.fullmatch(r"[0-9a-f]{64}", entry.get("sha256", "")):
            errors.append(f"register: {path} has no sha256")
        if not isinstance(entry.get("bytes"), int) or entry["bytes"] < 0:
            errors.append(f"register: {path} has no byte size")
    return errors


def main() -> int:
    errors = check_register()
    for path in tracked_paths():
        reason = solver_output_reason(path)
        if reason:
            errors.append(f"tracked solver output under work/ ({reason}): {path}")
    for error in errors:
        print(f"ERROR {error}")
    if errors:
        return 1
    print("work/ holds no tracked solver output")
    return 0


if __name__ == "__main__":
    sys.exit(main())
