#!/usr/bin/env python3
"""Fail closed when the generated F1 and CFD artefacts are inconsistent."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import meshio
import trimesh
from build123d import import_step


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pipeline", type=Path)
    args = parser.parse_args()
    root = args.pipeline
    checks: list[dict[str, object]] = []

    step = root / "cad/935-head-interface-proxy-f1.step"
    shape = import_step(step)
    checks.append({"name": "step_shape", "passed": bool(shape.is_valid)})

    fit_stl = root / "cad/935-head-interface-proxy-fit-check-only.stl"
    fit_mesh = trimesh.load_mesh(fit_stl, process=True)
    checks.append(
        {
            "name": "fit_check_stl",
            "passed": bool(fit_mesh.is_watertight and fit_mesh.volume > 0),
            "watertight": bool(fit_mesh.is_watertight),
            "triangles": int(len(fit_mesh.faces)),
        }
    )

    for name in ("low_B", "high_B"):
        surface = trimesh.load_mesh(root / f"cfd/{name}/fluid-domain.stl", process=True)
        volume_mesh = meshio.read(root / f"cfd/{name}/fluid-domain.msh")
        tetrahedra = sum(len(block.data) for block in volume_mesh.cells if block.type == "tetra")
        checks.append(
            {
                "name": f"cfd_{name}",
                "passed": bool(surface.is_watertight and abs(surface.volume) > 0 and tetrahedra > 0),
                "watertight": bool(surface.is_watertight),
                "tetrahedra": int(tetrahedra),
            }
        )

    report = {
        "status": "passed" if all(item["passed"] for item in checks) else "failed",
        "checks": checks,
        "scope": "geometric integrity only; no fit, material, CFD solution or engine validation",
    }
    output = root / "reports/output-verification.json"
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
