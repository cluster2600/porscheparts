#!/usr/bin/env python3
"""Generate a nominal bead-seat cylinder for a documented Fuchs wheel.

This is an interface proxy, not a reproduction of the spokes or flange profile.
It uses the nominal rim diameter and width and, when sourced, cuts the centre
bore. A documented pitch circle is metadata only until the seat diameter and
shape of the fasteners are also known.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parameters(record: dict) -> tuple[float, float, float | None]:
    values = {
        item["parameter_id"]: (float(item["value"]), item["unit"])
        for item in record["physical"]["size_parameters"]
    }
    diameter, diameter_unit = values["RIM_DIAMETER"]
    width, width_unit = values["RIM_WIDTH"]
    if diameter_unit != "in" or width_unit != "in":
        raise SystemExit("RIM_DIAMETER and RIM_WIDTH must be expressed in inches")
    centre_bore = values.get("CENTER_BORE")
    if centre_bore is not None and centre_bore[1] != "mm":
        raise SystemExit("CENTER_BORE must be expressed in millimetres")
    return diameter * 25.4, width * 25.4, centre_bore[0] if centre_bore else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--component", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    record = json.loads(args.component.read_text(encoding="utf-8"))
    diameter_mm, width_mm, centre_bore_mm = parameters(record)

    from build123d import Align, Cylinder, export_step

    proxy = Cylinder(
        radius=diameter_mm / 2,
        height=width_mm,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )
    if centre_bore_mm is not None:
        proxy -= Cylinder(
            radius=centre_bore_mm / 2,
            height=width_mm * 2,
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
        )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    export_step(proxy, str(args.out))
    bore = f", centre bore {centre_bore_mm} mm" if centre_bore_mm is not None else ""
    print(f"wrote nominal interface proxy {args.out}: {diameter_mm} x {width_mm} mm{bore}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
