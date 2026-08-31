#!/usr/bin/env python3
"""Create an editable F1 interface proxy and a non-functional fit-check STL."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from build123d import Align, Box, Cylinder, Pos, export_step, export_stl


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("interfaces", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    data = json.loads(args.interfaces.read_text())
    args.output.mkdir(parents=True, exist_ok=True)

    outer = data["combustion_interface"]["outer_register"]
    chamber = data["combustion_interface"]["chamber_step"]
    holes = data["head_stud_holes_at_C_minus_91"]
    origin_a, origin_b = outer["center"]

    # Deliberately simple F1 envelope: editable datum geometry, not a reverse-
    # engineered functional cylinder head.
    body = Pos(0, 12.0, 0) * Box(118.0, 190.0, 87.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body -= Cylinder(outer["diameter_obj_units"] / 2.0, 3.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body -= Pos(0, 0, 3.0) * Cylinder(
        chamber["diameter_obj_units"] / 2.0, 9.0, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )
    for hole in holes:
        a, b = hole["center_A_B"]
        body -= Pos(a - origin_a, b - origin_b, -1.0) * Cylinder(
            hole["diameter_obj_units"] / 2.0, 89.0, align=(Align.CENTER, Align.CENTER, Align.MIN)
        )

    step_path = args.output / "935-head-interface-proxy-f1.step"
    stl_path = args.output / "935-head-interface-proxy-fit-check-only.stl"
    export_step(body, step_path)
    export_stl(body, stl_path, tolerance=0.15, angular_tolerance=0.2)
    report = {
        "status": "F1_interface_proxy",
        "master": str(Path(__file__).resolve()),
        "step": str(step_path.resolve()),
        "stl": str(stl_path.resolve()),
        "coordinate_system": "local X=A, Y=B; origin at fitted outer-register centre; local Z enters head",
        "units": data["units"],
        "print_classification": "non_functional_fit_check_only",
        "limitations": [
            "The body is a simplified envelope and not the original finned geometry.",
            "Oil galleries, valve seats, guides, threads, port cores and machining stock are absent.",
            "Do not install this proxy in an engine or use it for a functional metal build.",
            "Scale must be confirmed physically before even a fit-check print is trusted.",
        ],
    }
    (args.output / "interface-proxy.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
