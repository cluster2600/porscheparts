#!/usr/bin/env python3
"""Layer F3 visual details onto one explicit F10 variant stage."""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path

from pxr import Gf, Sdf, Usd, UsdGeom


def relative(layer: Path, asset: Path) -> str:
    return os.path.relpath(asset.resolve(), layer.parent.resolve()).replace(os.sep, "/")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_stage", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--parts-report", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    parts = json.loads(args.parts_report.read_text(encoding="utf-8"))
    variant = config.get("f10_variant", {})
    variant_id = variant.get("variant_id")
    allowed_tags = set(variant.get("allowed_placement_tags", []))
    if not variant_id or not allowed_tags:
        raise RuntimeError("F10 detail config must declare variant and placement tags")
    source = Usd.Stage.Open(str(args.input_stage.resolve()), load=Usd.Stage.LoadAll)
    if not source:
        raise RuntimeError(f"could not open F10 kinematic input stage: {args.input_stage}")
    source_world = source.GetPrimAtPath("/World")
    if source_world.GetCustomDataByKey("3dprinting993:variantId") != variant_id:
        raise RuntimeError("F10 detail config and input stage variant IDs must match")
    confidence = {item["id"]: item["confidence"] for item in config["families"]}
    selected = [
        placement for placement in parts["placements"]
        if placement["variant"] in allowed_tags and placement["family"] in confidence
    ]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    layer = Sdf.Layer.CreateNew(str(args.output.resolve()))
    layer.subLayerPaths.append(relative(args.output, args.input_stage))
    stage = Usd.Stage.Open(layer, load=Usd.Stage.LoadAll)
    stage.SetEditTarget(layer)
    world = stage.GetPrimAtPath("/World")
    source_default = source.GetDefaultPrim()
    if source_default:
        stage.SetDefaultPrim(stage.GetPrimAtPath(source_default.GetPath()))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.GetStageUpAxis(source))
    UsdGeom.SetStageMetersPerUnit(stage, UsdGeom.GetStageMetersPerUnit(source))
    stage.SetStartTimeCode(source.GetStartTimeCode())
    stage.SetEndTimeCode(source.GetEndTimeCode())
    stage.SetTimeCodesPerSecond(source.GetTimeCodesPerSecond())
    stage.SetFramesPerSecond(source.GetFramesPerSecond())
    world.SetCustomDataByKey("3dprinting993:detailExpansionStatus", config["status"])
    world.SetCustomDataByKey("3dprinting993:detailExpansionVariantId", variant_id)
    world.SetCustomDataByKey(
        "3dprinting993:detailExpansionSourceIdsJson", json.dumps(config["source_ids"])
    )

    counts: Counter[str] = Counter()
    for placement in selected:
        family = placement["family"]
        scope = UsdGeom.Scope.Define(stage, f"/World/Components/{family}").GetPrim()
        scope.SetMetadata("kind", "group")
        path = f"/World/Components/{family}/{placement['instance_id']}"
        xform = UsdGeom.Xform.Define(stage, path)
        prim = xform.GetPrim()
        asset = args.assets / f"{family}.usdc"
        if not asset.is_file():
            raise FileNotFoundError(asset)
        prim.GetReferences().AddReference(relative(args.output, asset))
        prim.SetInstanceable(True)
        prim.SetMetadata("kind", "component")
        prim.SetCustomDataByKey("3dprinting993:family", family)
        prim.SetCustomDataByKey("3dprinting993:confidence", confidence[family])
        prim.SetCustomDataByKey("3dprinting993:placementStatus", placement["placement_status"])
        prim.SetCustomDataByKey("3dprinting993:releaseStatus", "research_only")
        prim.SetCustomDataByKey("3dprinting993:variantId", variant_id)
        prim.SetCustomDataByKey("3dprinting993:sourcePlacementTag", placement["variant"])
        xform.AddTranslateOp().Set(Gf.Vec3d(*placement["translation_mm"]))
        xform.AddRotateXYZOp().Set(Gf.Vec3f(*placement["rotation_xyz_deg"]))
        counts[family] += 1

    expected = Counter({item["id"]: item["count"] for item in config["families"]})
    if counts != expected:
        raise RuntimeError(f"F10 detail count mismatch: actual={dict(counts)} expected={dict(expected)}")
    stage.GetRootLayer().Save()
    report = {
        "schema_version": "1.0.0",
        "phase": "F10",
        "status": "passed",
        "variant_id": variant_id,
        "input_stage": str(args.input_stage.resolve()),
        "output_stage": str(args.output.resolve()),
        "stage_mode": "separate_stage_without_engine_variant_set",
        "added_family_count": len(counts),
        "added_instance_count": sum(counts.values()),
        "family_counts": dict(sorted(counts.items())),
        "manufacturing_geometry_ready": False,
        "prohibited_use": config["prohibited_use"],
    }
    args.output.with_suffix(".assembly-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
