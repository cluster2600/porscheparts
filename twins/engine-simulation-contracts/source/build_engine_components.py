#!/usr/bin/env python3
"""Build F1 assembly proxies for 993 pistons, rods, camshafts and K16 turbos."""

import argparse
import json
from pathlib import Path


def build_piston(spec):
    from build123d import Align, Cylinder
    return Cylinder(
        spec["nominal_bore_envelope_diameter_mm"] / 2,
        spec["proxy_body_height_mm"],
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )


def build_rod(spec):
    from build123d import Align, Box, Cylinder, Pos
    width = max(spec["small_end_width_mm"], spec["big_end_width_mm"])
    big_outer = spec["big_end_bore_mm"] / 2 + spec["proxy_outer_margin_mm"]
    small_outer = spec["small_end_bore_mm"] / 2 + spec["proxy_outer_margin_mm"]
    length = spec["center_distance_mm"]
    big = Cylinder(big_outer, width, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    small = Pos(length, 0, 0) * Cylinder(small_outer, width, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    bridge = Pos(length / 2, 0, 0) * Box(length, small_outer * 1.25, width, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    big_bore = Cylinder(spec["big_end_bore_mm"] / 2, width * 2, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    small_bore = Pos(length, 0, 0) * Cylinder(spec["small_end_bore_mm"] / 2, width * 2, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    return (big + small + bridge) - big_bore - small_bore


def build_camshaft(spec):
    from build123d import Align, Cylinder, Pos
    length = spec["proxy_length_mm"]
    shape = Cylinder(spec["proxy_journal_diameter_mm"] / 2, length, align=(Align.CENTER, Align.CENTER, Align.MIN))
    spacing = length / (spec["proxy_lobe_count"] + 1)
    for index in range(spec["proxy_lobe_count"]):
        z = spacing * (index + 1)
        lobe = Pos(spec["proxy_lobe_eccentricity_mm"], 0, z) * Cylinder(
            spec["proxy_lobe_major_diameter_mm"] / 2,
            spec["proxy_lobe_width_mm"],
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
        )
        shape = shape + lobe
    return shape


def build_turbo(spec, mirror=False):
    from build123d import Align, Cylinder, Pos, Sphere
    compressor_r = min(spec["envelope_mm"][1], spec["envelope_mm"][2]) * 0.38
    turbine_r = compressor_r * 0.92
    direction = -1 if mirror else 1
    compressor = Pos(direction * 62, 0, 0) * Sphere(compressor_r)
    turbine = Pos(direction * -62, 0, 0) * Sphere(turbine_r)
    chra = Cylinder(32, 124, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    comp_wheel = Pos(direction * 62, 0, 0) * Cylinder(
        spec["compressor_exducer_mm"] / 2, 10, align=(Align.CENTER, Align.CENTER, Align.CENTER)
    )
    turbine_wheel = Pos(direction * -62, 0, 0) * Cylinder(
        spec["turbine_inducer_mm"] / 2, 10, align=(Align.CENTER, Align.CENTER, Align.CENTER)
    )
    return compressor + turbine + chra + comp_wheel + turbine_wheel


def main():
    from build123d import export_step, export_stl
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--config", type=Path, default=Path(__file__).parents[1] / "engine-components-f1.json")
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    args.output.mkdir(parents=True, exist_ok=True)
    families = config["families"]
    shapes = {
        "993-piston-envelope-f1": build_piston(families["piston_993_turbo"]),
        "993-pauter-connecting-rod-f1": build_rod(families["connecting_rod_993_pauter"]),
        "993-camshaft-layout-f1": build_camshaft(families["camshaft_993_layout"]),
        "993-k16-left-envelope-f1": build_turbo(families["turbocharger_k16_pair"]),
        "993-k16-right-envelope-f1": build_turbo(families["turbocharger_k16_pair"], mirror=True),
    }
    outputs = []
    for name, shape in shapes.items():
        step = args.output / f"{name}.step"
        stl = args.output / f"{name}-display-only.stl"
        export_step(shape, step)
        export_stl(shape, stl, tolerance=0.08, angular_tolerance=0.12)
        outputs.append({"id": name, "step": str(step.resolve()), "stl": str(stl.resolve())})
    report = {
        "status": "F1_parametric_envelope_proxies_not_manufacturing_geometry",
        "outputs": outputs,
        "prohibited_use": config["prohibited_use"],
        "missing_before_simulation": [
            "measured piston crown, skirt, ring lands, pin bosses and clearances",
            "measured rod outer contour, fillets, bolt and bearing definitions",
            "measured cam journals, lobe profiles, phasing and oil passages",
            "measured turbo housings, interfaces, aero surfaces, bearings and operating maps"
        ]
    }
    (args.output / "engine-components-f1-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
