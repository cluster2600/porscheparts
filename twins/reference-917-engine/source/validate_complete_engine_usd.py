#!/usr/bin/env python3
"""Validate hierarchy, counts, composition and safety gates of the F1 assembly."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from pxr import Usd, UsdGeom, UsdPhysics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    stage = Usd.Stage.Open(str(args.stage), load=Usd.Stage.LoadAll)
    world = stage.GetPrimAtPath("/World")
    checks = []

    def check(name, passed, **details):
        checks.append({"name": name, "passed": bool(passed), **details})

    check("stage_opens", bool(stage))
    check("default_prim", stage.GetDefaultPrim() == world)
    check("millimetres", UsdGeom.GetStageMetersPerUnit(stage) == 0.001)
    check("z_up", UsdGeom.GetStageUpAxis(stage) == UsdGeom.Tokens.z)
    variant = world.GetVariantSets().GetVariantSet("engineVariant")
    check("engine_variants", set(variant.GetVariantNames()) == {"type_912_4_5_na", "917_30_turbo"}, values=variant.GetVariantNames())
    check("default_variant", variant.GetVariantSelection() == "type_912_4_5_na")

    expected = {item["id"]: item["count"] for item in config["component_families"]}
    variant_only = {item["id"] for item in config["component_families"] if item.get("variant") == "917_30_only"}

    def count_families(selection):
        variant.SetVariantSelection(selection)
        counts = Counter()
        prims = []
        for family_prim in stage.GetPrimAtPath("/World/Components").GetAllChildren():
            for child in family_prim.GetChildren():
                prims.append(child)
                counts[child.GetCustomDataByKey("3dprinting993:family")] += 1
        return counts, prims

    na_counts, _ = count_families("type_912_4_5_na")
    expected_na = {family: count for family, count in expected.items() if family not in variant_only}
    check("na_family_counts", dict(na_counts) == expected_na, expected=expected_na, actual=dict(na_counts))

    family_counts, component_prims = count_families("917_30_turbo")
    for child in component_prims:
        check(f"metadata_{child.GetPath()}", bool(child.GetCustomDataByKey("3dprinting993:confidence")))
    for family, count in expected.items():
        check(f"count_{family}", family_counts[family] == count, expected=count, actual=family_counts[family])
    check("instance_count", sum(family_counts.values()) == 275, actual=sum(family_counts.values()))

    meshes = [prim for prim in stage.TraverseAll() if prim.IsA(UsdGeom.Mesh)]
    prototype_meshes = [prim for prototype in stage.GetPrototypes() for prim in Usd.PrimRange(prototype) if prim.IsA(UsdGeom.Mesh)]
    check("prototype_meshes", len(meshes) + len(prototype_meshes) >= 31, count=len(meshes) + len(prototype_meshes))
    rigid = [str(prim.GetPath()) for prim in stage.TraverseAll() if prim.HasAPI(UsdPhysics.RigidBodyAPI)]
    check("no_unreviewed_rigid_bodies", not rigid, rigid_bodies=rigid)
    check("property_assignment_skipped", world.GetCustomDataByKey("3dprinting993:propertyAssignmentIntent") == "skip")
    variant.SetVariantSelection("type_912_4_5_na")

    report = {
        "schema_version": "1.0.0",
        "status": "passed" if all(item["passed"] for item in checks) else "failed",
        "classification": config["status"],
        "checks": checks,
        "family_counts": dict(sorted(family_counts.items())),
        "physics_assignment": "intentionally_absent",
        "next_gate": "measure missing interfaces before physics or manufacturing release"
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "checks": len(checks), "families": len(family_counts)}, indent=2))
    raise SystemExit(0 if report["status"] == "passed" else 1)


if __name__ == "__main__":
    main()
