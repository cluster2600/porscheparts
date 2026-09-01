#!/usr/bin/env python3
"""Validate F3 detail counts, variants and preservation of the F2 timeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pxr import Usd, UsdGeom


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    stage = Usd.Stage.Open(str(args.stage.resolve()), load=Usd.Stage.LoadAll)
    checks = []

    def check(name, passed, **details):
        checks.append({"name": name, "passed": bool(passed), **details})

    world = stage.GetPrimAtPath("/World") if stage else None
    check("stage_opens", bool(stage))
    check("default_prim", bool(world) and stage.GetDefaultPrim() == world)
    check("z_up", UsdGeom.GetStageUpAxis(stage) == UsdGeom.Tokens.z)
    check("timeline_preserved", stage.GetEndTimeCode() > stage.GetStartTimeCode())
    check("f3_status", world.GetCustomDataByKey("3dprinting993:detailExpansionStatus") == config["status"])

    family_ids = [item["id"] for item in config["families"]]
    paths = []
    for family in family_ids:
        scope = stage.GetPrimAtPath(f"/World/Components/{family}")
        children = list(scope.GetAllChildren()) if scope else []
        expected = next(item["count"] for item in config["families"] if item["id"] == family)
        check(f"count_{family}", len(children) == expected, expected=expected, actual=len(children))
        paths.extend(str(child.GetPath()) for child in children)
    check("added_family_count", len(family_ids) == config["acceptance"]["added_family_count"])
    check("added_instance_count", len(paths) == config["acceptance"]["added_instance_count"])

    variants = world.GetVariantSets().GetVariantSet("engineVariant")
    check("required_variants", set(variants.GetVariantNames()) == set(config["acceptance"]["required_variants"]))
    turbo_paths = [
        path
        for path in paths
        if stage.GetPrimAtPath(path).GetCustomDataByKey("3dprinting993:variant") == "917_30_only"
    ]
    previous = variants.GetVariantSelection()
    variants.SetVariantSelection("type_912_4_5_na")
    check("turbo_details_hidden_in_na", all(not stage.GetPrimAtPath(path).IsActive() for path in turbo_paths))
    variants.SetVariantSelection("917_30_turbo")
    check("turbo_details_active_in_917_30", all(stage.GetPrimAtPath(path).IsActive() for path in turbo_paths))
    variants.SetVariantSelection(previous)

    animated = {
        str(prim.GetPath())
        for prim in stage.TraverseAll()
        if any(attribute.GetNumTimeSamples() for attribute in prim.GetAttributes())
    }
    check("f2_animation_preserved", len(animated) >= 149, expected_minimum=149, actual=len(animated))
    report = {
        "schema_version": "1.0.0",
        "status": "passed" if all(item["passed"] for item in checks) else "failed",
        "stage": str(args.stage.resolve()),
        "checks": checks,
        "added_instance_count": len(paths),
        "animated_prim_count": len(animated),
        "prohibited_use": config["prohibited_use"],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "checks": len(checks), "instances": len(paths)}, indent=2))
    raise SystemExit(0 if report["status"] == "passed" else 1)


if __name__ == "__main__":
    main()
