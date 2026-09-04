#!/usr/bin/env python3
"""Watchdog distant sans acces fournisseur; borne les processus uid 9147."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import time


RUNTIME = Path("/workspace/f46-runtime")
STOP = Path("/workspace/F46_STOP")


def solver_pids() -> list[int]:
    found: list[int] = []
    for status in Path("/proc").glob("[0-9]*/status"):
        try:
            uid_line = next(line for line in status.read_text().splitlines() if line.startswith("Uid:"))
            real_uid = int(uid_line.split()[1])
            pid = int(status.parent.name)
        except (OSError, StopIteration, ValueError, IndexError):
            continue
        if real_uid == 9147:
            found.append(pid)
    return sorted(found)


def atomic(path: Path, payload: dict[str, object]) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--deadline-epoch", type=int, required=True)
    args = parser.parse_args()
    if os.getuid() != 0:
        raise RuntimeError("watchdog requires transport root")
    RUNTIME.mkdir(parents=True, exist_ok=True)
    atomic(RUNTIME / "watchdog-armed.json", {
        "schema_version": "1.0.0",
        "deadline_epoch": args.deadline_epoch,
        "watchdog_pid": os.getpid(),
        "solver_uid": 9147,
    })
    while int(time.time()) < args.deadline_epoch:
        time.sleep(min(15, max(1, args.deadline_epoch - int(time.time()))))
    STOP.touch(mode=0o444, exist_ok=True)
    for pid in solver_pids():
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    time.sleep(30)
    for pid in solver_pids():
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    atomic(RUNTIME / "watchdog-fired.json", {
        "schema_version": "1.0.0",
        "deadline_epoch": args.deadline_epoch,
        "fired_at_epoch": int(time.time()),
        "stop_file": str(STOP),
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
