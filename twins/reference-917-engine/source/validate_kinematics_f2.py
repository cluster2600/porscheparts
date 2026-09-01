#!/usr/bin/env python3
"""Validate the 917 F2 timeline, crank-slider travel and kinematic safety."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pxr import Usd, UsdGeom, UsdPhysics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    stage = Usd.Stage.Open(str(args.stage), load=Usd.Stage.LoadAll)
    checks = []

    def check(name: str, passed: bool, **details) -> None:
        checks.append({"name": name, "passed": bool(passed), **details})

    world = stage.GetPrimAtPath("/World")
    check("stage_opens", bool(stage))
    check("default_prim", stage.GetDefaultPrim() == world)
    check("z_up", UsdGeom.GetStageUpAxis(stage) == UsdGeom.Tokens.z)
    check("millimetres", UsdGeom.GetStageMetersPerUnit(stage) == 0.001)
    check("timeline_start", stage.GetStartTimeCode() == config["timeline"]["start_time_code"])
    check("timeline_end", stage.GetEndTimeCode() == config["timeline"]["end_time_code"])
    check("timeline_rate", stage.GetTimeCodesPerSecond() == config["timeline"]["time_codes_per_second"])
    check("property_assignment_intent", world.GetCustomDataByKey("3dprinting993:propertyAssignmentIntent") == "run")
    check("combustion_disabled", world.GetCustomDataByKey("3dprinting993:combustion") == "disabled")
    variants = world.GetVariantSets().GetVariantSet("engineVariant")
    check("engine_variants", set(variants.GetVariantNames()) == set(config["acceptance"]["required_variants"]))

    animated = []
    unsafe_dynamic = []
    for prim in stage.TraverseAll():
        samples = []
        for attribute in prim.GetAttributes():
            samples.extend(attribute.GetTimeSamples())
        if samples:
            animated.append(str(prim.GetPath()))
            if prim.HasAPI(UsdPhysics.RigidBodyAPI):
                kinematic = UsdPhysics.RigidBodyAPI(prim).GetKinematicEnabledAttr().Get()
                if kinematic is not True:
                    unsafe_dynamic.append(str(prim.GetPath()))
    check(
        "animated_prim_count",
        len(animated) >= config["acceptance"]["minimum_animated_prim_count"],
        expected_minimum=config["acceptance"]["minimum_animated_prim_count"],
        actual=len(animated),
    )
    check("all_animated_rigid_bodies_kinematic", not unsafe_dynamic, unsafe_dynamic=unsafe_dynamic)

    stroke = config["crank_slider"]["stroke_mm"]
    tolerance = config["acceptance"]["piston_travel_tolerance_mm"]
    piston_travel = {}
    for prim in stage.GetPrimAtPath("/World/Components/piston").GetChildren():
        op = next(
            item for item in UsdGeom.Xformable(prim).GetOrderedXformOps()
            if item.GetOpName() == "xformOp:translate"
        )
        values = [op.Get(Usd.TimeCode(time))[1] for time in op.GetAttr().GetTimeSamples()]
        travel = max(values) - min(values)
        piston_travel[str(prim.GetPath())] = travel
        check(f"stroke_{prim.GetName()}", abs(travel - stroke) <= tolerance, expected=stroke, actual=travel)

    physics_scene = UsdPhysics.Scene.Get(stage, "/World/PhysicsScene")
    check("physics_scene", bool(physics_scene))
    check("zero_gravity_test_bench", physics_scene.GetGravityMagnitudeAttr().Get() == 0.0)

    report = {
        "schema_version": "1.0.0",
        "status": "passed" if all(item["passed"] for item in checks) else "failed",
        "stage": str(args.stage.resolve()),
        "checks": checks,
        "animated_prim_count": len(animated),
        "piston_travel_mm": piston_travel,
        "unsafe_dynamic_bodies": unsafe_dynamic,
        "combustion": "disabled",
        "classification": config["status"],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "checks": len(checks), "animated_prims": len(animated)}, indent=2))
    raise SystemExit(0 if report["status"] == "passed" else 1)


if __name__ == "__main__":
    main()
