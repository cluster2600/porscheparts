#!/usr/bin/env python3
"""Place the 917 research assembly on a proxy Omniverse engine test bench."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics


def relative(layer: Path, asset: Path) -> str:
    return os.path.relpath(asset.resolve(), layer.parent.resolve()).replace(os.sep, "/")


def cube(stage: Usd.Stage, path: str, center: Gf.Vec3d, size: Gf.Vec3d, color: Gf.Vec3f):
    shape = UsdGeom.Cube.Define(stage, path)
    shape.CreateSizeAttr(1.0)
    shape.AddTranslateOp().Set(center)
    shape.AddScaleOp().Set(size)
    shape.CreateDisplayColorAttr([color])
    UsdPhysics.CollisionAPI.Apply(shape.GetPrim())
    return shape.GetPrim()


def cylinder(stage: Usd.Stage, path: str, center: Gf.Vec3d, radius: float, length: float, color: Gf.Vec3f):
    shape = UsdGeom.Cylinder.Define(stage, path)
    shape.CreateRadiusAttr(radius)
    shape.CreateHeightAttr(length)
    shape.CreateAxisAttr(UsdGeom.Tokens.x)
    shape.AddTranslateOp().Set(center)
    shape.CreateDisplayColorAttr([color])
    UsdPhysics.CollisionAPI.Apply(shape.GetPrim())
    return shape.GetPrim()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_stage", type=Path)
    parser.add_argument("--bench", type=Path, required=True)
    parser.add_argument("--systems", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    bench = json.loads(args.bench.read_text(encoding="utf-8"))
    systems = json.loads(args.systems.read_text(encoding="utf-8"))
    source = Usd.Stage.Open(str(args.input_stage.resolve()), load=Usd.Stage.LoadAll)
    if not source or not source.GetPrimAtPath("/World"):
        raise RuntimeError("validated F3 stage with /World is required")

    bounds = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_]).ComputeWorldBound(
        source.GetPrimAtPath("/World")
    ).ComputeAlignedRange()
    lower = bounds.GetMin()
    upper = bounds.GetMax()
    extent = upper - lower
    center = (lower + upper) * 0.5
    deck_z = lower[2] - 120.0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    layer = Sdf.Layer.CreateNew(str(args.output.resolve()))
    layer.subLayerPaths.append(relative(args.output, args.input_stage))
    stage = Usd.Stage.Open(layer, load=Usd.Stage.LoadAll)
    stage.SetEditTarget(layer)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.GetStageUpAxis(source))
    UsdGeom.SetStageMetersPerUnit(stage, UsdGeom.GetStageMetersPerUnit(source))
    stage.SetStartTimeCode(source.GetStartTimeCode())
    stage.SetEndTimeCode(source.GetEndTimeCode())
    stage.SetTimeCodesPerSecond(source.GetTimeCodesPerSecond())
    stage.SetFramesPerSecond(source.GetFramesPerSecond())
    stage.SetDefaultPrim(stage.GetPrimAtPath("/World"))

    world = stage.GetPrimAtPath("/World")
    world.SetCustomDataByKey("3dprinting993:testBenchStatus", bench["status"])
    world.SetCustomDataByKey("3dprinting993:maximumAuthorizedStage", bench["acceptance"]["maximum_authorized_stage"])
    world.SetCustomDataByKey("3dprinting993:firedRunAuthorized", False)
    world.SetCustomDataByKey("3dprinting993:fluidDomainsJson", json.dumps([item["id"] for item in systems["fluid_domains"]]))

    root = UsdGeom.Xform.Define(stage, "/World/TestBench").GetPrim()
    root.SetMetadata("kind", "assembly")
    root.SetCustomDataByKey("3dprinting993:releaseStatus", "research_only")
    gray = Gf.Vec3f(0.18, 0.20, 0.22)
    yellow = Gf.Vec3f(0.85, 0.55, 0.05)
    red = Gf.Vec3f(0.65, 0.04, 0.03)
    blue = Gf.Vec3f(0.06, 0.18, 0.55)

    deck_size = Gf.Vec3d(max(extent[0] + 700.0, 1500.0), max(extent[1] + 600.0, 1200.0), 80.0)
    cube(stage, "/World/TestBench/Bedplate", Gf.Vec3d(center[0], center[1], deck_z), deck_size, gray)
    mount_dx = max(extent[0] * 0.32, 260.0)
    mount_dy = max(extent[1] * 0.30, 220.0)
    for index, (sx, sy) in enumerate(((-1, -1), (-1, 1), (1, -1), (1, 1)), start=1):
        prim = cube(
            stage,
            f"/World/TestBench/EngineMount_{index:02d}",
            Gf.Vec3d(center[0] + sx * mount_dx, center[1] + sy * mount_dy, deck_z + 80.0),
            Gf.Vec3d(90.0, 90.0, 120.0),
            yellow,
        )
        prim.SetCustomDataByKey("3dprinting993:interfaceStatus", "position_and_load_limit_unmeasured")

    dyno_x = upper[0] + 320.0
    dyno = cylinder(stage, "/World/TestBench/Dynamometer", Gf.Vec3d(dyno_x, center[1], center[2]), 210.0, 420.0, blue)
    dyno.SetCustomDataByKey("3dprinting993:loadStatus", "disabled")
    coupling = cylinder(stage, "/World/TestBench/DynoCoupling", Gf.Vec3d(upper[0] + 80.0, center[1], center[2]), 55.0, 160.0, yellow)
    coupling.SetCustomDataByKey("3dprinting993:alignmentStatus", "interface_unmeasured")
    UsdPhysics.RigidBodyAPI.Apply(coupling).CreateKinematicEnabledAttr(True)

    cube(stage, "/World/TestBench/Battery", Gf.Vec3d(lower[0], upper[1] + 180.0, deck_z + 120.0), Gf.Vec3d(260.0, 160.0, 180.0), red)
    cylinder(stage, "/World/TestBench/OilReservoir", Gf.Vec3d(center[0], lower[1] - 240.0, deck_z + 220.0), 150.0, 360.0, gray)
    cube(stage, "/World/TestBench/FuelSupply", Gf.Vec3d(lower[0] + 320.0, lower[1] - 220.0, deck_z + 160.0), Gf.Vec3d(280.0, 220.0, 260.0), red)
    cube(stage, "/World/TestBench/EmergencyStop", Gf.Vec3d(upper[0] + 180.0, upper[1] + 180.0, deck_z + 160.0), Gf.Vec3d(100.0, 100.0, 180.0), red)

    instruments = UsdGeom.Scope.Define(stage, "/World/TestBench/Instrumentation").GetPrim()
    instruments.SetCustomDataByKey("3dprinting993:channelsJson", json.dumps(bench["instrumentation"]))
    instruments.SetCustomDataByKey("3dprinting993:channelCount", bench["acceptance"]["instrument_channel_count"])
    stage.GetRootLayer().Save()

    report = {
        "schema_version": "1.0.0",
        "status": "passed_visual_bench_layer_not_physical_start",
        "input_stage": str(args.input_stage.resolve()),
        "output_stage": str(args.output.resolve()),
        "engine_bounds_mm": [list(lower), list(upper)],
        "bench_component_instance_count": bench["acceptance"]["bench_component_instance_count"],
        "instrument_channel_count": bench["acceptance"]["instrument_channel_count"],
        "fired_run_authorized": False,
        "critical_blockers": bench["critical_blockers"],
    }
    args.output.with_suffix(".assembly-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
