#!/usr/bin/env python3
"""Fail closed when the generated 917 F1 and display artefacts disagree."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import trimesh
from build123d import import_step


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pipeline", type=Path)
    args = parser.parse_args()
    root = args.pipeline
    checks: list[dict[str, object]] = []

    preparation = json.loads((root / "reports/mesh-preparation.json").read_text())
    p95 = preparation["simplification_deviation"]["light_600k"]["p95_obj_units"]
    checks.append({"name": "working_mesh_deviation", "passed": p95 <= 0.5, "p95_obj_units": p95})

    interfaces = json.loads((root / "reports/interfaces.json").read_text())
    count = sum(len(bank) for bank in interfaces["banks"].values())
    checks.append({"name": "twelve_detected_openings", "passed": count == 12, "count": count})

    step = root / "cad/917-engine-interface-proxy-f1.step"
    shape = import_step(step)
    checks.append({"name": "step_proxy", "passed": bool(shape.is_valid)})

    for denominator in (4, 8):
        path = root / f"print/917-engine-display-only-scale-1-{denominator}.stl"
        mesh = trimesh.load_mesh(path, process=True)
        passed = bool(mesh.is_volume and mesh.body_count == 1)
        checks.append(
            {
                "name": f"display_print_1_{denominator}",
                "passed": passed,
                "watertight": bool(mesh.is_watertight),
                "body_count": int(mesh.body_count),
                "triangles": int(len(mesh.faces)),
                "dimensions_candidate_mm": list(map(float, mesh.extents)),
            }
        )

    cfd = json.loads((root / "cfd/external-cooling/cfd-preparation.json").read_text())
    checks.append(
        {
            "name": "external_cfd_surface",
            "passed": bool(cfd["surface_watertight"] and cfd["surface_is_volume"]),
            "triangles": cfd["surface_triangles"],
        }
    )
    report = {
        "status": "passed" if all(item["passed"] for item in checks) else "failed",
        "checks": checks,
        "scope": "geometric F1 integrity only; identity, scale, fit, material, CFD solution and engine function remain unvalidated",
    }
    output = root / "reports/output-verification.json"
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
