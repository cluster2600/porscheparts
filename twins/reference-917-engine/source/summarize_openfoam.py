#!/usr/bin/env python3
"""Convert the OpenFOAM checkMesh log into a machine-readable safety gate."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def number(pattern: str, text: str, cast=float):
    match = re.search(pattern, text)
    return cast(match.group(1)) if match else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("log", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    text = args.log.read_text(errors="replace")
    failed = number(r"Failed\s+(\d+)\s+mesh checks", text, int)
    if failed is None:
        failed = 0 if "Mesh OK." in text else -1
    report = {
        "status": "solver_mesh_ready" if failed == 0 else "blocked_mesh_quality",
        "solver_allowed": failed == 0,
        "failed_mesh_checks": failed,
        "cells": number(r"cells:\s+(\d+)", text, int),
        "duplicate_faces": number(r"duplicate \(not baffle\) faces found:\s*(\d+)", text, int),
        "non_consecutive_shared_point_faces": number(
            r"faces with non-consecutive shared points:\s*(\d+)", text, int
        ),
        "max_non_orthogonality_degrees": number(
            r"(?:Mesh non-orthogonality|Non-orthogonality) Max:\s*([0-9.eE+-]+)", text
        ),
        "highly_skew_faces": number(r"(\d+) highly skew faces", text, int),
        "concave_cells": number(r"Concave cells .* number of cells:\s*(\d+)", text, int),
        "scope": "external geometry mesh only; no boundary conditions or flow solution",
        "next_action": "repair duplicated/shared surface features and retune local snappy refinement before any solver run",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report["solver_allowed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
