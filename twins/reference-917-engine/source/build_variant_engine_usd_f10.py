#!/usr/bin/env python3
"""Compose one F10 917 geometry stage without a shared engineVariant switch."""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path

from pxr import Gf, Usd, UsdGeom

from prepare_variant_configs_f10 import stage_provenance_payload


def relative(layer: Path, asset: Path) -> str:
    return os.path.relpath(asset.resolve(), layer.parent.resolve()).replace(os.sep, "/")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--parts-report", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    parts = json.loads(args.parts_report.read_text(encoding="utf-8"))
    variant = config.get("f10_variant", {})
    variant_id = variant.get("variant_id")
    if not variant_id or parts.get("variant_id") != variant_id:
        raise RuntimeError("F10 config and parts report variant IDs must match")
    confidence = {item["id"]: item["confidence"] for item in config["component_families"]}

    args.output.parent.mkdir(parents=True, exist_ok=True)
    stage = Usd.Stage.CreateNew(str(args.output.resolve()))
    UsdGeom.SetStageMetersPerUnit(stage, 0.001)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    world = UsdGeom.Xform.Define(stage, "/World").GetPrim()
    stage.SetDefaultPrim(world)
    world.SetMetadata("kind", "assembly")
    dimensions = config["declared_dimensions"]
    provenance = stage_provenance_payload(
        variant_id,
        variant["documented_displacement_cm3"],
        variant["field_evidence"],
    )
    world.SetCustomDataByKey("3dprinting993:phase", "F10")
    world.SetCustomDataByKey("3dprinting993:status", config["status"])
    world.SetCustomDataByKey("3dprinting993:variantId", variant_id)
    world.SetCustomDataByKey("3dprinting993:architecture", variant["architecture"])
    world.SetCustomDataByKey("3dprinting993:boreMm", dimensions["bore_mm"])
    world.SetCustomDataByKey("3dprinting993:strokeMm", dimensions["stroke_mm"])
    world.SetCustomDataByKey(
        "3dprinting993:documentedDisplacementCm3", variant["documented_displacement_cm3"]
    )
    world.SetCustomDataByKey(
        "3dprinting993:calculatedDisplacementCm3", parts["calculated_displacement_cm3"]
    )
    world.SetCustomDataByKey(
        "3dprinting993:fieldEvidenceJson", json.dumps(provenance["field_evidence"], sort_keys=True)
    )
    world.SetCustomDataByKey("3dprinting993:propertyAssignmentIntent", "skip")
    world.SetCustomDataByKey("3dprinting993:propertyAssignmentStatus", "not_run")
    world.SetCustomDataByKey("3dprinting993:manufacturingGeometryReady", False)
    world.SetCustomDataByKey("3dprinting993:physicalKinematicsReady", False)
    world.SetCustomDataByKey(
        "3dprinting993:variantChangeScopeJson", json.dumps(variant["variant_change_scope"])
    )
    world.SetCustomDataByKey("3dprinting993:sourceIdsJson", json.dumps(config["source_ids"]))
    world.SetCustomDataByKey("3dprinting993:prohibitedUseJson", json.dumps(config["prohibited_use"]))

    components = UsdGeom.Scope.Define(stage, "/World/Components").GetPrim()
    components.SetMetadata("kind", "group")
    family_scopes: dict[str, Usd.Prim] = {}
    counts: Counter[str] = Counter()
    external_assets: set[str] = set()
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
        asset_path = relative(args.output, asset)
        prim.GetReferences().AddReference(asset_path)
        external_assets.add(asset_path)
        prim.SetInstanceable(True)
        prim.SetMetadata("kind", "component")
        prim.SetCustomDataByKey("3dprinting993:family", family)
        prim.SetCustomDataByKey("3dprinting993:confidence", confidence[family])
        prim.SetCustomDataByKey("3dprinting993:releaseStatus", "research_only")
        prim.SetCustomDataByKey("3dprinting993:variantId", variant_id)
        prim.SetCustomDataByKey("3dprinting993:sourcePlacementTag", placement["variant"])
        xform.AddTranslateOp().Set(Gf.Vec3d(*placement["translation_mm"]))
        xform.AddRotateXYZOp().Set(Gf.Vec3f(*placement["rotation_xyz_deg"]))
        counts[family] += 1

    expected = Counter({item["id"]: item["count"] for item in config["component_families"]})
    if counts != expected:
        raise RuntimeError(f"F10 stage count mismatch: actual={dict(counts)} expected={dict(expected)}")
    stage.GetRootLayer().Save()
    report = {
        "schema_version": "1.0.0",
        "phase": "F10",
        "status": "passed",
        "variant_id": variant_id,
        "stage": str(args.output.resolve()),
        "stage_mode": "separate_stage_without_engine_variant_set",
        "property_assignment_intent": "skip",
        "property_assignment_status": "not_run",
        "prototype_count": parts["prototype_count"],
        "instance_count": sum(counts.values()),
        "family_count": len(counts),
        "family_counts": dict(sorted(counts.items())),
        "external_assets": sorted(external_assets),
        "bore_mm": dimensions["bore_mm"],
        "stroke_mm": dimensions["stroke_mm"],
        "documented_displacement_cm3": provenance["documented_displacement_cm3"],
        "calculated_displacement_cm3": parts["calculated_displacement_cm3"],
        "field_evidence": provenance["field_evidence"],
        "variant_change_scope": variant["variant_change_scope"],
        "manufacturing_geometry_ready": False,
        "physics_assignment": "intentionally_absent_pending_measured_interfaces_and_materials",
    }
    report_path = args.output.with_suffix(".assembly-report.json")
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
