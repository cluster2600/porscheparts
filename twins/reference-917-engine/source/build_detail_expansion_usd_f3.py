#!/usr/bin/env python3
"""Compose F3 detail proxies as a non-destructive layer over a validated F2 USD."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from pxr import Gf, Sdf, Usd, UsdGeom


def relative(layer: Path, asset: Path) -> str:
    return os.path.relpath(asset.resolve(), layer.parent.resolve()).replace(os.sep, "/")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_stage", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--parts-report", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    parts = json.loads(args.parts_report.read_text(encoding="utf-8"))
    confidence = {item["id"]: item["confidence"] for item in config["families"]}
    source = Usd.Stage.Open(str(args.input_stage.resolve()), load=Usd.Stage.LoadAll)
    if not source:
        raise RuntimeError(f"could not open F2 input stage: {args.input_stage}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    layer = Sdf.Layer.CreateNew(str(args.output.resolve()))
    layer.subLayerPaths.append(relative(args.output, args.input_stage))
    stage = Usd.Stage.Open(layer, load=Usd.Stage.LoadAll)
    stage.SetEditTarget(layer)
    world = stage.GetPrimAtPath("/World")
    if not world:
        raise RuntimeError("F2 input has no /World")
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
    world.SetCustomDataByKey("3dprinting993:detailExpansionSourceIdsJson", json.dumps(config["source_ids"]))

    added = []
    turbo = []
    for placement in parts["placements"]:
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
        prim.SetCustomDataByKey("3dprinting993:variant", placement["variant"])
        xform.AddTranslateOp().Set(Gf.Vec3d(*placement["translation_mm"]))
        xform.AddRotateXYZOp().Set(Gf.Vec3f(*placement["rotation_xyz_deg"]))
        added.append(str(prim.GetPath()))
        if placement["variant"] == "917_30_only":
            turbo.append(prim)

    variants = world.GetVariantSets().GetVariantSet("engineVariant")
    required_variants = set(config["acceptance"]["required_variants"])
    if set(variants.GetVariantNames()) != required_variants:
        raise RuntimeError(f"F2 engine variants do not match F3 contract: {variants.GetVariantNames()}")
    previous_selection = variants.GetVariantSelection()
    for name, active in (("type_912_4_5_na", False), ("917_30_turbo", True)):
        variants.SetVariantSelection(name)
        with variants.GetVariantEditContext():
            for prim in turbo:
                prim.SetActive(active)
    variants.SetVariantSelection(previous_selection or "type_912_4_5_na")
    stage.GetRootLayer().Save()

    report = {
        "schema_version": "1.0.0",
        "status": "passed",
        "input_stage": str(args.input_stage.resolve()),
        "output_stage": str(args.output.resolve()),
        "added_family_count": len({item["family"] for item in parts["placements"]}),
        "added_instance_count": len(added),
        "turbo_variant_instance_count": len(turbo),
        "variants": variants.GetVariantNames(),
        "default_variant": variants.GetVariantSelection(),
        "prohibited_use": config["prohibited_use"],
    }
    report_path = args.output.with_suffix(".assembly-report.json")
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
