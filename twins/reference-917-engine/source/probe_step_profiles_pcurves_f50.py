#!/usr/bin/env python3
"""Private p-curve-only round-trip probe for F50 STEP profiles."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--helper-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.helper_dir))
    from audit_brep_f42 import read_step
    from repair_pcurves_f42_2 import pcurve_fault_map

    profiles = []
    for path in sorted(args.input_dir.glob("*.step")):
        shape, roots = read_step(path)
        result = pcurve_fault_map(shape)
        profiles.append(
            {
                "filename": path.name,
                "sha256": sha256(path),
                "roots": roots,
                "pcurve_fault_count": result["result_count"],
                "status_counts": result["status_counts"],
                "unique_face_count": result["unique_face_count"],
                "unique_edge_count": result["unique_edge_count"],
                "accepted_by_early_pcurve_gate": result["result_count"] == 0,
            }
        )
    report = {
        "schema": "porsche-917-f50-private-step-pcurve-profile-probe/v1",
        "authority": "early_pcurve_indicator_only_full_roundtrip_audit_required_for_acceptance",
        "geometry_edit_used": False,
        "profiles": profiles,
        "any_early_pcurve_pass": any(item["accepted_by_early_pcurve_gate"] for item in profiles),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            [
                {
                    "filename": item["filename"],
                    "pcurve_fault_count": item["pcurve_fault_count"],
                    "unique_face_count": item["unique_face_count"],
                    "unique_edge_count": item["unique_edge_count"],
                }
                for item in profiles
            ],
            sort_keys=True,
        )
    )
    return 0 if report["any_early_pcurve_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
