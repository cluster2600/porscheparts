#!/usr/bin/env python3
"""Build editable F3 proxy parts for sourced 917 subsystems missing from F1."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def tube(outer_radius, inner_radius, height):
    from build123d import Align, Cylinder

    outer = Cylinder(outer_radius, height, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    inner = Cylinder(inner_radius, height * 1.2, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    return outer - inner


def impeller(radius, width, blade_count):
    from build123d import Align, Box, Cylinder, Pos, Rot

    shape = Cylinder(radius * 0.22, width, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    for angle in range(0, 360, 360 // blade_count):
        blade = Rot(0, 0, angle) * Pos(radius * 0.58, 0, 0) * Box(
            radius * 0.82,
            max(2.0, radius * 0.08),
            width,
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
        )
        shape = shape + blade
    return shape


def build_shapes():
    from build123d import Align, Box, Cone, Cylinder, Pos

    cooler = Box(150, 42, 95, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    for offset in range(-65, 66, 13):
        cooler = cooler + Pos(offset, 0, 0) * Box(3, 52, 105, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    return {
        "cooling_blower_drive_shaft": Cylinder(10, 180, align=(Align.CENTER, Align.CENTER, Align.CENTER)),
        "cooling_blower_bevel_gear": Cone(36, 16, 24, align=(Align.CENTER, Align.CENTER, Align.CENTER)),
        "twelve_plunger_injection_pump": Box(155, 72, 68, align=(Align.CENTER, Align.CENTER, Align.CENTER)),
        "injection_line": tube(2.4, 1.5, 210),
        "oil_filter": Cylinder(38, 105, align=(Align.CENTER, Align.CENTER, Align.CENTER)),
        "oil_thermostat": Cylinder(32, 55, align=(Align.CENTER, Align.CENTER, Align.CENTER)),
        "oil_cooler": cooler,
        "cam_drive_intermediate_shaft": Cylinder(12, 220, align=(Align.CENTER, Align.CENTER, Align.CENTER)),
        "turbo_turbine_wheel": impeller(47, 18, 10),
        "turbo_compressor_wheel": impeller(52, 20, 12),
        "turbo_shaft": Cylinder(8, 112, align=(Align.CENTER, Align.CENTER, Align.CENTER)),
        "wastegate": Cylinder(35, 82, align=(Align.CENTER, Align.CENTER, Align.CENTER))
        + Pos(0, 0, 48) * Cylinder(18, 28, align=(Align.CENTER, Align.CENTER, Align.CENTER)),
        "wastegate_bypass_pipe": tube(23, 19, 170),
    }


def placements():
    regular_pitch = 118.0
    central_pitch = 173.0
    xs = [
        -(central_pitch / 2 + 2 * regular_pitch),
        -(central_pitch / 2 + regular_pitch),
        -central_pitch / 2,
        central_pitch / 2,
        central_pitch / 2 + regular_pitch,
        central_pitch / 2 + 2 * regular_pitch,
    ]
    result = []

    def add(family, translation, rotation=(0, 0, 0), variant="all"):
        index = 1 + sum(item["family"] == family for item in result)
        result.append(
            {
                "instance_id": f"{family}_{index:02d}",
                "family": family,
                "translation_mm": list(translation),
                "rotation_xyz_deg": list(rotation),
                "variant": variant,
                "placement_status": "layout_hypothesis",
            }
        )

    add("cooling_blower_drive_shaft", (0, 0, 210))
    add("cooling_blower_bevel_gear", (0, 0, 126))
    add("cooling_blower_bevel_gear", (0, 0, 190), (90, 0, 0))
    add("twelve_plunger_injection_pump", (0, -120, 145), (0, 90, 0))
    for bank in (-1, 1):
        for x in xs:
            add("injection_line", (x, bank * 178, 92), (90, 0, 0))
    add("oil_filter", (275, -105, -145), (0, 90, 0))
    add("oil_thermostat", (220, -112, -95), (0, 90, 0))
    add("oil_cooler", (292, 0, -85), (0, 90, 0))
    add("cam_drive_intermediate_shaft", (0, 0, 82), (0, 90, 0))

    for bank in (-1, 1):
        turbo_center = (bank * 245, bank * 370, -180)
        add("turbo_turbine_wheel", (turbo_center[0] - 48, turbo_center[1], turbo_center[2]), (0, 90, 0), "917_30_only")
        add("turbo_compressor_wheel", (turbo_center[0] + 48, turbo_center[1], turbo_center[2]), (0, 90, 0), "917_30_only")
        add("turbo_shaft", turbo_center, (0, 90, 0), "917_30_only")
        add("wastegate", (bank * 105, bank * 390, -225), (0, 90, 0), "917_30_only")
        add("wastegate_bypass_pipe", (bank * 165, bank * 350, -230), (0, 90, 0), "917_30_only")
    return result


def main():
    from build123d import export_step, export_stl

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    requested = {item["id"] for item in config["families"]}
    shapes = build_shapes()
    if requested != set(shapes):
        raise RuntimeError(f"family mismatch: config={sorted(requested)} shapes={sorted(shapes)}")

    prototypes = []
    for family, shape in shapes.items():
        step = args.output / "step" / f"{family}.step"
        stl = args.output / "stl" / f"{family}-display-only.stl"
        step.parent.mkdir(parents=True, exist_ok=True)
        stl.parent.mkdir(parents=True, exist_ok=True)
        export_step(shape, step)
        export_stl(shape, stl, tolerance=0.12, angular_tolerance=0.16)
        prototypes.append({"family": family, "step": str(step.resolve()), "stl": str(stl.resolve())})

    layout = placements()
    expected = config["acceptance"]
    if len(prototypes) != expected["added_family_count"] or len(layout) != expected["added_instance_count"]:
        raise RuntimeError("generated F3 counts do not match the acceptance contract")
    report = {
        "schema_version": "1.0.0",
        "status": config["status"],
        "prototype_count": len(prototypes),
        "instance_count": len(layout),
        "prototypes": prototypes,
        "placements": layout,
        "prohibited_use": config["prohibited_use"],
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "detail-expansion-f3-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": report["status"], "prototype_count": len(prototypes), "instance_count": len(layout)}, indent=2))


if __name__ == "__main__":
    main()
