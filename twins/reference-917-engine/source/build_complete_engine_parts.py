#!/usr/bin/env python3
"""Build non-functional F1 CAD prototypes for the complete 917 engine family."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def tube(outer_r, inner_r, height):
    from build123d import Align, Cylinder
    outer = Cylinder(outer_r, height, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    inner = Cylinder(inner_r, height * 1.2, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    return outer - inner


def valve(head_diameter):
    from build123d import Align, Cone, Cylinder, Pos
    head = Cylinder(head_diameter / 2, 4, align=(Align.CENTER, Align.CENTER, Align.MIN))
    neck = Pos(0, 0, 4) * Cone(head_diameter / 2, 4, 14, align=(Align.CENTER, Align.CENTER, Align.MIN))
    stem = Pos(0, 0, 4) * Cylinder(4, 105, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return head + neck + stem


def crankshaft(length):
    from build123d import Align, Cylinder, Pos
    shape = Cylinder(18, length, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    for index, z in enumerate((-295, -177, -59, 59, 177, 295)):
        offset = 12 if index % 2 == 0 else -12
        shape = shape + Pos(offset, 0, z) * Cylinder(25, 38, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    return shape


def camshaft(length):
    from build123d import Align, Cylinder, Pos
    shape = Cylinder(13, length, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    for index, z in enumerate((-295, -177, -59, 59, 177, 295)):
        offset = 5 if index % 2 == 0 else -5
        shape = shape + Pos(offset, 0, z) * Cylinder(24, 13, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    return shape


def connecting_rod(center_distance):
    from build123d import Align, Box, Cylinder, Pos
    width = 18
    big = Cylinder(34, width, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    small = Pos(center_distance, 0, 0) * Cylinder(18, width, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    beam = Pos(center_distance / 2, 0, 0) * Box(center_distance, 22, width, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    return (big + small + beam) - Cylinder(25, 30, align=(Align.CENTER, Align.CENTER, Align.CENTER)) - Pos(center_distance, 0, 0) * Cylinder(11, 30, align=(Align.CENTER, Align.CENTER, Align.CENTER))


def individual_cylinder(bore, height):
    from build123d import Align, Cylinder, Pos
    shape = tube(bore / 2 + 7, bore / 2, height)
    for z in range(-45, 46, 9):
        fin = Pos(0, 0, z) * tube(bore / 2 + 17, bore / 2 - 1, 3)
        shape = shape + fin
    return shape


def blower():
    from build123d import Align, Box, Cylinder, Pos, Rot
    shape = Cylinder(24, 28, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    for angle in range(0, 360, 30):
        blade = Rot(0, 0, angle) * Pos(57, 0, 0) * Box(70, 8, 22, align=(Align.CENTER, Align.CENTER, Align.CENTER))
        shape = shape + blade
    return shape


def turbo():
    from build123d import Align, Cylinder, Pos, Sphere
    return (
        Pos(-55, 0, 0) * Sphere(68)
        + Pos(55, 0, 0) * Sphere(62)
        + Cylinder(30, 110, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    )


def build_shapes(config):
    from build123d import Align, Box, Cone, Cylinder, Pos
    d = config["declared_dimensions"]
    h = config["layout_hypotheses"]
    bore = d["bore_mm"]
    shapes = {
        "crankcase_half": Box(710, 170, 92, align=(Align.CENTER, Align.CENTER, Align.CENTER)),
        "main_bearing": tube(32, 19, 18),
        "crankshaft": crankshaft(d["crankshaft_length_mm"]),
        "central_output_gear": Cylinder(72, 24, align=(Align.CENTER, Align.CENTER, Align.CENTER)),
        "output_shaft": Cylinder(18, 260, align=(Align.CENTER, Align.CENTER, Align.CENTER)),
        "connecting_rod": connecting_rod(h["connecting_rod_center_distance_mm"]),
        "piston": Cylinder(bore / 2 - 0.7, h["piston_height_mm"], align=(Align.CENTER, Align.CENTER, Align.CENTER)),
        "piston_pin": Cylinder(11, 68, align=(Align.CENTER, Align.CENTER, Align.CENTER)),
        "piston_ring": tube(bore / 2 - 0.5, bore / 2 - 2.2, 1.6),
        "individual_cylinder": individual_cylinder(bore, h["cylinder_length_mm"]),
        "individual_head": Cylinder(62, 50, align=(Align.CENTER, Align.CENTER, Align.CENTER)) + Pos(0, 0, 25) * Box(105, 88, 18, align=(Align.CENTER, Align.CENTER, Align.CENTER)),
        "intake_valve": valve(d["intake_valve_head_mm"]),
        "exhaust_valve": valve(d["exhaust_valve_head_mm"]),
        "valve_spring": tube(13, 9, 42),
        "bucket_tappet": Cylinder(15, 18, align=(Align.CENTER, Align.CENTER, Align.CENTER)),
        "camshaft": camshaft(h["camshaft_length_mm"]),
        "cam_carrier": Box(705, 52, 45, align=(Align.CENTER, Align.CENTER, Align.CENTER)),
        "cam_drive_gear": Cylinder(34, 14, align=(Align.CENTER, Align.CENTER, Align.CENTER)),
        "cooling_blower": blower(),
        "blower_shroud": tube(118, 104, 38),
        "intake_trumpet": Cone(21, 37, 110, align=(Align.CENTER, Align.CENTER, Align.MIN)) - Cone(17, 33, 112, align=(Align.CENTER, Align.CENTER, Align.MIN)),
        "injector": Cylinder(5, 48, align=(Align.CENTER, Align.CENTER, Align.CENTER)),
        "spark_plug": Cylinder(6, 55, align=(Align.CENTER, Align.CENTER, Align.CENTER)),
        "distributor": Cylinder(42, 70, align=(Align.CENTER, Align.CENTER, Align.CENTER)),
        "pressure_oil_pump": Box(75, 55, 45, align=(Align.CENTER, Align.CENTER, Align.CENTER)),
        "scavenge_oil_pump": Box(48, 38, 34, align=(Align.CENTER, Align.CENTER, Align.CENTER)),
        "exhaust_primary": tube(24, 20, 150),
        "exhaust_collector": tube(52, 47, 260),
        "alternator": Cylinder(45, 82, align=(Align.CENTER, Align.CENTER, Align.CENTER)),
        "turbocharger": turbo(),
        "charge_plenum": Box(360, 115, 100, align=(Align.CENTER, Align.CENTER, Align.CENTER)),
    }
    return shapes


def placements(config):
    d = config["declared_dimensions"]
    h = config["layout_hypotheses"]
    pitch = d["cylinder_regular_pitch_mm"]
    gap = d["central_pair_pitch_mm"]
    xs = [-(gap / 2 + 2 * pitch), -(gap / 2 + pitch), -gap / 2, gap / 2, gap / 2 + pitch, gap / 2 + 2 * pitch]
    result = []

    def add(family, translation, rotation=(0, 0, 0), variant="base"):
        index = 1 + sum(1 for item in result if item["family"] == family)
        result.append({"instance_id": f"{family}_{index:02d}", "family": family, "translation_mm": list(translation), "rotation_xyz_deg": list(rotation), "variant": variant})

    add("crankcase_half", (0, -48, 0))
    add("crankcase_half", (0, 48, 0))
    add("crankshaft", (0, 0, 0), (0, 90, 0))
    for x in (-350, -250, -150, -50, 50, 150, 250, 350):
        add("main_bearing", (x, 0, 0), (0, 90, 0))
    add("central_output_gear", (0, 0, 0), (90, 0, 0))
    add("output_shaft", (0, 0, -140))

    for bank in (-1, 1):
        for cylinder_index, x in enumerate(xs):
            add("connecting_rod", (x, bank * 42, 0), (0, 90, 90 if bank > 0 else -90))
            add("piston", (x, bank * 92, 0), (90, 0, 0))
            add("piston_pin", (x, bank * 92, 0), (0, 90, 0))
            for ring_offset in (-12, -8, -4):
                add("piston_ring", (x, bank * (92 + ring_offset), 0), (90, 0, 0))
            add("individual_cylinder", (x, bank * 150, 0), (90, 0, 0))
            add("individual_head", (x, bank * 225, 0), (90, 0, 0))
            add("intake_valve", (x, bank * 235, 24), (0, 0, 0))
            add("exhaust_valve", (x, bank * 235, -24), (180, 0, 0))
            add("valve_spring", (x, bank * 250, 48))
            add("valve_spring", (x, bank * 250, -48))
            add("bucket_tappet", (x, bank * 265, 48))
            add("bucket_tappet", (x, bank * 265, -48))
            add("spark_plug", (x - 14, bank * 242, 0), (90, 0, 0))
            add("spark_plug", (x + 14, bank * 242, 0), (90, 0, 0))
            add("intake_trumpet", (x, bank * 242, 95), (0, 0, 0))
            add("injector", (x + 22, bank * 246, 70), (15, 0, 0))
            add("exhaust_primary", (x, bank * 248, -115), (0, 0, 0))
        add("cam_carrier", (0, bank * 270, 0), (0, 90, 0))
        add("camshaft", (0, bank * 285, 48), (0, 90, 0))
        add("camshaft", (0, bank * 285, -48), (0, 90, 0))
        for gear_index in range(5):
            add("cam_drive_gear", ((gear_index - 2) * 38, bank * 112, (gear_index % 2) * 42 - 21), (90, 0, 0))
        add("exhaust_collector", (0, bank * 265, -205), (0, 90, 0))
        add("distributor", (bank * 310, bank * 85, 105))
        add("charge_plenum", (0, bank * 330, 125), variant="917_30_only")
        add("turbocharger", (bank * 245, bank * 370, -180), (0, 90, 0), variant="917_30_only")

    add("cooling_blower", (0, 0, 190))
    add("blower_shroud", (0, 0, 190))
    add("pressure_oil_pump", (0, -70, -110))
    for index, x in enumerate(xs):
        add("scavenge_oil_pump", (x, 70 if index % 2 else -70, -115))
    add("alternator", (0, 0, 285))
    return result


def main():
    from build123d import export_step, export_stl
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    args.output.mkdir(parents=True, exist_ok=True)
    shapes = build_shapes(config)
    prototypes = []
    for family, shape in shapes.items():
        step = args.output / "step" / f"{family}.step"
        stl = args.output / "stl" / f"{family}-display-only.stl"
        step.parent.mkdir(parents=True, exist_ok=True)
        stl.parent.mkdir(parents=True, exist_ok=True)
        export_step(shape, step)
        export_stl(shape, stl, tolerance=0.12, angular_tolerance=0.16)
        prototypes.append({"family": family, "step": str(step.resolve()), "stl": str(stl.resolve())})
    layout = placements(config)
    report = {
        "schema_version": "1.0.0",
        "status": config["status"],
        "property_assignment_intent": "skip",
        "prototype_count": len(prototypes),
        "instance_count": len(layout),
        "prototypes": prototypes,
        "placements": layout,
        "prohibited_use": config["prohibited_use"]
    }
    (args.output / "complete-engine-parts-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "prototype_count": len(prototypes), "instance_count": len(layout)}, indent=2))


if __name__ == "__main__":
    main()
