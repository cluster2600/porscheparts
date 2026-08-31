#!/usr/bin/env python3
"""Build an editable twelve-cylinder F1 assembly proxy from detected openings."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from build123d import Align, Box, Compound, Cylinder, Pos, export_step, export_stl


def ring(radius_outer: float, radius_inner: float, length: float, direction: int):
    rotation = (-90.0 * direction, 0.0, 0.0)
    outer = Cylinder(
        radius_outer,
        length,
        rotation=rotation,
        align=(Align.CENTER, Align.CENTER, Align.MIN if direction > 0 else Align.MAX),
    )
    inner = Cylinder(
        radius_inner,
        length + 2.0,
        rotation=rotation,
        align=(Align.CENTER, Align.CENTER, Align.MIN if direction > 0 else Align.MAX),
    )
    return outer - inner


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("interfaces", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    data = json.loads(args.interfaces.read_text())
    args.output.mkdir(parents=True, exist_ok=True)

    all_openings = data["banks"]["positive"] + data["banks"]["negative"]
    bore_radius = float(np.mean([item["diameter_obj_units"] for item in all_openings])) / 2.0
    outer_radius = bore_radius + 22.0
    core_half_width = 115.0
    core_height = 170.0
    longitudinal = [item["center_longitudinal_vertical"][0] for item in all_openings]
    case_length = max(longitudinal) - min(longitudinal) + 160.0
    case_centre = (max(longitudinal) + min(longitudinal)) / 2.0
    bodies = [
        Pos(case_centre, 0.0, -10.0)
        * Box(case_length, 2.0 * core_half_width, core_height, align=Align.CENTER)
    ]

    for label, direction in (("positive", 1), ("negative", -1)):
        bank_depth = float(
            np.median([item["rim_outward_depth_mode_obj_units"] for item in data["banks"][label]])
        )
        length = max(25.0, bank_depth - core_half_width)
        for opening in data["banks"][label]:
            x, z = opening["center_longitudinal_vertical"]
            bodies.append(Pos(x, direction * core_half_width, z) * ring(outer_radius, bore_radius, length, direction))

    assembly = Compound(children=bodies, label="Porsche 917 F1 exterior interface proxy")
    step_path = args.output / "917-engine-interface-proxy-f1.step"
    stl_path = args.output / "917-engine-interface-proxy-fit-check-only.stl"
    export_step(assembly, step_path)
    export_stl(assembly, stl_path, tolerance=0.2, angular_tolerance=0.25)
    report = {
        "status": "F1_exterior_interface_proxy",
        "master": str(Path(__file__).resolve()),
        "step": str(step_path.resolve()),
        "stl": str(stl_path.resolve()),
        "coordinate_system": "local X=longitudinal, Y=opposed cylinder axis, Z=vertical",
        "units": data["units"],
        "cylinder_count": 12,
        "visible_opening_diameter_obj_units": 2.0 * bore_radius,
        "proxy_outer_cylinder_diameter_obj_units": 2.0 * outer_radius,
        "print_classification": "nonfunctional_fit_and_layout_check_only",
        "limitations": [
            "The STEP is an editable layout proxy, not a surface reconstruction of the engine.",
            "The crankcase is a box envelope and the finned cylinders are simplified rings.",
            "Internal components, fasteners, oil circuits, combustion geometry and tolerances are absent.",
            "Do not use this proxy for a functional engine or metal production part.",
        ],
    }
    (args.output / "interface-proxy.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
