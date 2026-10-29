#!/usr/bin/env python3
"""Refuse newly tracked files above the size threshold unless the register admits them.

Git keeps every byte it is ever given, so a large payload committed by mistake
cannot be removed later: deleting the file leaves the blob in history. The only
cheap moment to refuse one is before it is pushed.

The repository already tracks several hundred large payloads that predate this
gate, so the check is a ratchet rather than a blanket limit: the register
catalog/registers/large-files.json lists the paths allowed to exceed the
threshold, and anything else above it fails. Admitting a new payload therefore
means adding a register entry with a reason, which is a visible decision in the
diff instead of a silent one.

The gate is presence-based: it does not bound how much an admitted payload may
grow, because several of them are regenerated artifacts whose size moves
legitimately. It answers one question only - is this large file here on purpose.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "catalog" / "registers" / "large-files.json"


def tracked_sizes() -> dict[str, int]:
    """Size every path git tracks, reading the index rather than the work tree."""
    out = subprocess.run(
        ["git", "ls-tree", "-r", "-l", "-z", "HEAD"],
        cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout
    sizes: dict[str, int] = {}
    for record in out.split("\0"):
        if not record:
            continue
        meta, _, path = record.partition("\t")
        fields = meta.split()
        if len(fields) != 4 or fields[1] != "blob":
            continue
        if fields[3] == "-":  # submodule or otherwise unsized
            continue
        sizes[path] = int(fields[3])
    return sizes


def load_register() -> tuple[int, dict[str, str]]:
    data = json.loads(REGISTER.read_text(encoding="utf-8"))
    threshold = data["threshold_bytes"]
    admitted: dict[str, str] = {}
    for entry in data["entries"]:
        admitted[entry["path"]] = entry["reason"]
    return threshold, admitted


def main() -> int:
    threshold, admitted = load_register()
    sizes = tracked_sizes()

    unadmitted = sorted(
        (path, size) for path, size in sizes.items()
        if size >= threshold and path not in admitted
    )
    blank = sorted(path for path, reason in admitted.items() if not reason.strip())
    stale = sorted(path for path in admitted if path not in sizes)

    for path, size in unadmitted:
        print(f"FAIL {path}")
        print(f"  - {size / 1048576:.1f} MiB exceeds the {threshold / 1048576:.0f} MiB "
              f"threshold and is not in {REGISTER.relative_to(ROOT)}")
    for path in blank:
        print(f"FAIL {path}")
        print("  - register entry carries no reason")

    if stale:
        # Not a failure: removing a payload is the outcome this gate wants.
        print(f"note: {len(stale)} register entry(ies) no longer tracked and can be pruned")
        for path in stale[:10]:
            print(f"  - {path}")

    failures = len(unadmitted) + len(blank)
    if failures:
        print(f"file sizes: {failures} path(s) refused")
        print("  admit a payload on purpose by adding it to "
              f"{REGISTER.relative_to(ROOT)} with a reason, or keep the bytes in the "
              "evidence release and commit only hashes and results")
        return 1
    print(f"file sizes: {len(sizes)} tracked path(s), {len(admitted)} admitted above "
          f"{threshold / 1048576:.0f} MiB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
