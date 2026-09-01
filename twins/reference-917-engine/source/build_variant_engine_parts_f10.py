#!/usr/bin/env python3
"""Build separate F10 visual CAD proxies for one explicitly selected 917 variant."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from build_complete_engine_parts import build_shapes, placements
from prepare_variant_configs_f10 import calculated_displacement_cm3


def main() -> None:
    from build123d import export_step, export_stl

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    variant = config.get("f10_variant")
    if not isinstance(variant, dict) or not variant.get("variant_id"):
        raise RuntimeError("F10 variant metadata is required")
    variant_id = variant["variant_id"]
    requested = {item["id"] for item in config["component_families"]}
    shapes = build_shapes(config)
    unknown = requested - set(shapes)
    if unknown:
        raise RuntimeError(f"F10 config requests unknown families: {sorted(unknown)}")

    args.output.mkdir(parents=True, exist_ok=True)
    prototypes = []
    for family in sorted(requested):
        shape = shapes[family]
        step = args.output / "step" / f"{family}.step"
        stl = args.output / "stl" / f"{family}-display-only.stl"
        step.parent.mkdir(parents=True, exist_ok=True)
        stl.parent.mkdir(parents=True, exist_ok=True)
        export_step(shape, step)
        export_stl(shape, stl, tolerance=0.12, angular_tolerance=0.16)
        prototypes.append(
            {
                "family": family,
                "step": str(step.resolve()),
                "stl": str(stl.resolve()),
                "release_status": "visual_proxy_only",
            }
        )

    layout = [item for item in placements(config) if item["family"] in requested]
    placement_families = {item["family"] for item in layout}
    if placement_families != requested:
        raise RuntimeError(
            f"F10 placement/config family mismatch: placements={sorted(placement_families)} "
            f"config={sorted(requested)}"
        )
    dimensions = config["declared_dimensions"]
    report = {
        "schema_version": "1.0.0",
        "phase": "F10",
        "status": "passed",
        "classification": config["status"],
        "variant_id": variant_id,
        "property_assignment_intent": "skip",
        "bore_mm": dimensions["bore_mm"],
        "stroke_mm": dimensions["stroke_mm"],
        "calculated_displacement_cm3": calculated_displacement_cm3(
            12, dimensions["bore_mm"], dimensions["stroke_mm"]
        ),
        "prototype_count": len(prototypes),
        "instance_count": len(layout),
        "prototypes": prototypes,
        "placements": layout,
        "source_ids": config["source_ids"],
        "variant_change_scope": variant["variant_change_scope"],
        "manufacturing_geometry_ready": False,
        "prohibited_use": config["prohibited_use"],
    }
    (args.output / "variant-engine-parts-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "variant_id": variant_id,
                "prototype_count": len(prototypes),
                "instance_count": len(layout),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
