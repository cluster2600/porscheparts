#!/usr/bin/env python3
"""Build non-functional F1 valve proxies and mass-comparison reports."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def proxy_volume_mm3(variant: dict[str, Any], defaults: dict[str, Any]) -> float:
    """Return the volume of the deliberately simplified cylinder/cone proxy."""
    head_r = variant["head_diameter_mm"] / 2.0
    stem_r = variant["stem_diameter_mm"] / 2.0
    face_h = defaults["face_thickness_mm"]
    neck_h = defaults["neck_length_mm"]
    stem_h = variant["overall_length_mm"] - face_h
    if min(head_r, stem_r, face_h, neck_h, stem_h) <= 0 or neck_h > stem_h:
        raise ValueError(f"invalid dimensions for {variant['id']}")
    head = math.pi * head_r**2 * face_h
    frustum = math.pi * neck_h * (head_r**2 + head_r * stem_r + stem_r**2) / 3.0
    # The stem overlaps the frustum. Count only the straight part above it.
    stem = math.pi * stem_r**2 * (stem_h - neck_h)
    return head + frustum + stem


def mass_g(volume_mm3: float, density_g_cm3: float) -> float:
    return volume_mm3 / 1000.0 * density_g_cm3


def build_shape(variant: dict[str, Any], defaults: dict[str, Any]):
    from build123d import Align, Cone, Cylinder, Pos

    head_r = variant["head_diameter_mm"] / 2.0
    stem_r = variant["stem_diameter_mm"] / 2.0
    face_h = defaults["face_thickness_mm"]
    neck_h = defaults["neck_length_mm"]
    stem_h = variant["overall_length_mm"] - face_h
    head = Cylinder(head_r, face_h, align=(Align.CENTER, Align.CENTER, Align.MIN))
    neck = Pos(0, 0, face_h) * Cone(
        head_r, stem_r, neck_h, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )
    stem = Pos(0, 0, face_h) * Cylinder(
        stem_r, stem_h, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )
    return head + neck + stem


def generate(config_path: Path, output: Path) -> dict[str, Any]:
    from build123d import export_step, export_stl

    config = json.loads(config_path.read_text())
    output.mkdir(parents=True, exist_ok=True)
    defaults = config["geometry_defaults"]
    results = []
    for variant in config["variants"]:
        volume = proxy_volume_mm3(variant, defaults)
        shape = build_shape(variant, defaults)
        step = output / f"{variant['id']}.step"
        stl = output / f"{variant['id']}-fit-check-only.stl"
        export_step(shape, step)
        export_stl(shape, stl, tolerance=0.03, angular_tolerance=0.08)
        comparisons = []
        for material_id in variant["material_variants"]:
            material = config["materials"][material_id]
            comparisons.append(
                {
                    "material_id": material_id,
                    "name": material["name"],
                    "density_g_cm3": material["density_g_cm3"],
                    "proxy_mass_g": round(mass_g(volume, material["density_g_cm3"]), 3),
                    "role": material["role"],
                    "limitations": material["limits"],
                }
            )
        results.append(
            {
                **variant,
                "proxy_volume_mm3": round(volume, 3),
                "step": str(step.resolve()),
                "stl": str(stl.resolve()),
                "material_comparisons": comparisons,
            }
        )
    report = {
        "status": "F1_hypothesis_only",
        "master": str(Path(__file__).resolve()),
        "config": str(config_path.resolve()),
        "variants": results,
        "allowed_use": ["CAD review", "mass comparison", "collision setup", "polymer fit-check"],
        "prohibited_use": [
            "functional engine installation",
            "metal production release",
            "fatigue, thermal or valvetrain-dynamics sign-off",
        ],
        "missing_measurements": [
            "exact overall length for the intake valve",
            "keeper groove and tip geometry",
            "seat angle, seat width and margin",
            "neck fillet and underhead profile",
            "guide clearance, stem finish and coating",
            "cam profile, spring curves, installed height and moving masses",
        ],
    }
    (output / "valve-variants-f1.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).with_name("valve_variants_f1.json"),
    )
    args = parser.parse_args()
    report = generate(args.config, args.output)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
