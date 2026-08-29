#!/usr/bin/env python3
"""Generate a nominal bead-seat cylinder for a documented Fuchs wheel.

This is an interface proxy, not a reproduction of the spokes, flange profile,
centre bore or bolt pattern. It uses only the nominal rim diameter and width
declared in the component record.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parameters(record: dict) -> tuple[float, float]:
    values = {
        item["parameter_id"]: (float(item["value"]), item["unit"])
        for item in record["physical"]["size_parameters"]
    }
    diameter, diameter_unit = values["RIM_DIAMETER"]
    width, width_unit = values["RIM_WIDTH"]
    if diameter_unit != "in" or width_unit != "in":
        raise SystemExit("RIM_DIAMETER and RIM_WIDTH must be expressed in inches")
    return diameter * 25.4, width * 25.4


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--component", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    record = json.loads(args.component.read_text(encoding="utf-8"))
    diameter_mm, width_mm = parameters(record)

    from build123d import Align, Cylinder, export_step

    proxy = Cylinder(
        radius=diameter_mm / 2,
        height=width_mm,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    export_step(proxy, str(args.out))
    print(f"wrote nominal interface proxy {args.out}: {diameter_mm} x {width_mm} mm")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

