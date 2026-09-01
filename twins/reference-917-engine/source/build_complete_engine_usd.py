#!/usr/bin/env python3
"""Compose the complete F1 917 engine proxy assembly from converted prototypes."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from pxr import Gf, Usd, UsdGeom


def relative(layer: Path, asset: Path) -> str:
    return os.path.relpath(asset.resolve(), layer.parent.resolve()).replace(os.sep, "/")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--parts-report", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    parts = json.loads(args.parts_report.read_text(encoding="utf-8"))
    confidence = {item["id"]: item["confidence"] for item in config["component_families"]}

    args.output.parent.mkdir(parents=True, exist_ok=True)
    stage = Usd.Stage.CreateNew(str(args.output))
    UsdGeom.SetStageMetersPerUnit(stage, 0.001)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    world = UsdGeom.Xform.Define(stage, "/World").GetPrim()
    stage.SetDefaultPrim(world)
    world.SetMetadata("kind", "assembly")
    world.SetCustomDataByKey("3dprinting993:status", config["status"])
    world.SetCustomDataByKey("3dprinting993:propertyAssignmentIntent", "skip")
    world.SetCustomDataByKey("3dprinting993:baseVariant", config["base_variant"])
    world.SetCustomDataByKey("3dprinting993:sourceIdsJson", json.dumps(config["source_ids"]))
    world.SetCustomDataByKey("3dprinting993:prohibitedUseJson", json.dumps(config["prohibited_use"]))

    components = UsdGeom.Scope.Define(stage, "/World/Components").GetPrim()
    components.SetMetadata("kind", "group")
    family_scopes = {}
    turbo_prims = []
    for placement in parts["placements"]:
        family = placement["family"]
        if family not in family_scopes:
            scope = UsdGeom.Scope.Define(stage, f"/World/Components/{family}").GetPrim()
            scope.SetMetadata("kind", "group")
            family_scopes[family] = scope
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
        prim.SetCustomDataByKey("3dprinting993:releaseStatus", "research_only")
        prim.SetCustomDataByKey("3dprinting993:variant", placement["variant"])
        xform.AddTranslateOp().Set(Gf.Vec3d(*placement["translation_mm"]))
        xform.AddRotateXYZOp().Set(Gf.Vec3f(*placement["rotation_xyz_deg"]))
        if placement["variant"] == "917_30_only":
            turbo_prims.append(prim)

    variants = world.GetVariantSets().AddVariantSet("engineVariant")
    for name, turbo_active in (("type_912_4_5_na", False), ("917_30_turbo", True)):
        variants.AddVariant(name)
        variants.SetVariantSelection(name)
        with variants.GetVariantEditContext():
            for prim in turbo_prims:
                prim.SetActive(turbo_active)
            world.SetCustomDataByKey("3dprinting993:selectedArchitecture", name)
    variants.SetVariantSelection("type_912_4_5_na")

    stage.GetRootLayer().Save()
    report = {
        "schema_version": "1.0.0",
        "status": "passed",
        "stage": str(args.output.resolve()),
        "property_assignment_intent": "skip",
        "prototype_count": parts["prototype_count"],
        "instance_count": parts["instance_count"],
        "family_count": len(family_scopes),
        "variants": variants.GetVariantNames(),
        "default_variant": variants.GetVariantSelection(),
        "physics_assignment": "intentionally_absent_pending_measured_interfaces_and_materials"
    }
    report_path = args.output.with_suffix(".assembly-report.json")
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
