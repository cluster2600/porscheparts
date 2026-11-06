#!/usr/bin/env python3
"""Replay titanium selection/zone snapshots against their retained 44-part inventory."""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog/parts"
INPUTS = ROOT / "catalog/manufacturing/titanium-am-screen-inputs.json"
SELECTION = ROOT / "twins/993-exhaust-tip-ti-f0/evidence/selection/titanium-candidate-screen.json"
SCREEN = ROOT / "scripts/screen_titanium_candidates.py"
ZONE_SCREEN = ROOT / "scripts/screen_pet_zones_for_titanium.py"
ZONE_OUTPUT = SELECTION.with_name("pet-zone-titanium-triage.json")


def historical_records(catalog: Path) -> dict[str, Path]:
    inputs = json.loads(INPUTS.read_text(encoding="utf-8"))
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    ranked = [entry["part_id"] for entry in selection["ranking"]]
    if len(ranked) != 44 or len(set(ranked)) != len(ranked):
        raise ValueError("Historical ranking must contain 44 unique part IDs.")
    if selection["parts_screened"] != len(ranked) or set(ranked) != set(inputs["parts"]):
        raise ValueError("Historical ranking and retained judgement inventory differ.")

    # Filtering is explicit and local to this historical replay. The unchanged
    # live screening command still rejects every new unjudged catalogue part.
    wanted = set(ranked)
    records = {}
    for path in sorted(catalog.glob("*.json")):
        part_id = json.loads(path.read_text(encoding="utf-8"))["part_id"]
        if part_id not in wanted:
            continue
        if part_id in records:
            raise ValueError(f"Duplicate historical catalogue part: {part_id}")
        records[part_id] = path
    missing = wanted - records.keys()
    if missing:
        raise ValueError("Missing historical catalogue parts: " + ", ".join(sorted(missing)))
    return records


def check_snapshot(catalog: Path, mode: str = "selection") -> int:
    records = historical_records(catalog)
    with tempfile.TemporaryDirectory(prefix="titanium-screen-snapshot-") as temp:
        staged = Path(temp)
        for part_id, path in records.items():
            shutil.copyfile(path, staged / (part_id.lower() + ".json"))
        if mode == "selection":
            command = [sys.executable, str(SCREEN), "--inputs", str(INPUTS)]
            output = SELECTION
        else:
            command = [sys.executable, str(ZONE_SCREEN)]
            output = ZONE_OUTPUT
        result = subprocess.run(command + [
            "--catalog", str(staged), "--output", str(output), "--check",
        ])
    if result.returncode == 0:
        print(f"Historical titanium {mode} snapshot verified: 44 retained judgements; live catalogue not screened.")
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    parser.add_argument("--mode", choices=("selection", "pet-zone-triage"), default="selection")
    args = parser.parse_args()
    try:
        return check_snapshot(args.catalog, args.mode)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"Historical titanium snapshot check failed: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
