#!/usr/bin/env python3
"""Author measured-input placeholders for 917 starting and oil-prime support."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics


def relative(layer: Path, asset: Path) -> str:
    return os.path.relpath(asset.resolve(), layer.parent.resolve()).replace(os.sep, "/")


def center(stage: Usd.Stage, path: str) -> Gf.Vec3d:
    prim = stage.GetPrimAtPath(path)
    if not prim:
        raise RuntimeError(f"missing support endpoint: {path}")
    bounds = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_]).ComputeWorldBound(prim).ComputeAlignedRange()
    return (bounds.GetMin() + bounds.GetMax()) * 0.5


def family_path(stage: Usd.Stage, family: str) -> str:
    scope = stage.GetPrimAtPath(f"/World/Components/{family}")
    children = sorted(scope.GetAllChildren(), key=lambda prim: str(prim.GetPath())) if scope else []
    if not children:
        raise RuntimeError(f"missing component family: {family}")
    return str(children[0].GetPath())


def tag(prim: Usd.Prim, support_id: str, status: str) -> Usd.Prim:
    prim.SetCustomDataByKey("3dprinting993:supportId", support_id)
    prim.SetCustomDataByKey("3dprinting993:interfaceStatus", status)
    prim.SetCustomDataByKey("3dprinting993:simulationReady", False)
    return prim


def cylinder(stage: Usd.Stage, path: str, point: Gf.Vec3d, radius: float, height: float, color: Gf.Vec3f) -> Usd.Prim:
    shape = UsdGeom.Cylinder.Define(stage, path)
    shape.CreateAxisAttr(UsdGeom.Tokens.x)
    shape.CreateRadiusAttr(radius)
    shape.CreateHeightAttr(height)
    shape.AddTranslateOp().Set(point)
    shape.CreateDisplayColorAttr([color])
    UsdPhysics.CollisionAPI.Apply(shape.GetPrim())
    return shape.GetPrim()


def cube(stage: Usd.Stage, path: str, point: Gf.Vec3d, size: Gf.Vec3d, color: Gf.Vec3f, opacity: float = 1.0) -> Usd.Prim:
    shape = UsdGeom.Cube.Define(stage, path)
    shape.CreateSizeAttr(1.0)
    shape.AddTranslateOp().Set(point)
    shape.AddScaleOp().Set(size)
    shape.CreateDisplayColorAttr([color])
    shape.CreateDisplayOpacityAttr([opacity])
    UsdPhysics.CollisionAPI.Apply(shape.GetPrim())
    return shape.GetPrim()


def curve(stage: Usd.Stage, path: str, points: list[Gf.Vec3d], width: float, color: Gf.Vec3f) -> Usd.Prim:
    item = UsdGeom.BasisCurves.Define(stage, path)
    item.CreateTypeAttr(UsdGeom.Tokens.linear)
    item.CreateCurveVertexCountsAttr([len(points)])
    item.CreatePointsAttr(points)
    item.CreateWidthsAttr([width])
    item.SetWidthsInterpolation(UsdGeom.Tokens.constant)
    item.CreateDisplayColorAttr([color])
    return item.GetPrim()


def sensor(stage: Usd.Stage, path: str, point: Gf.Vec3d, color: Gf.Vec3f) -> Usd.Prim:
    item = UsdGeom.Sphere.Define(stage, path)
    item.CreateRadiusAttr(12.0)
    item.AddTranslateOp().Set(point)
    item.CreateDisplayColorAttr([color])
    return item.GetPrim()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_stage", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    source = Usd.Stage.Open(str(args.input_stage.resolve()), load=Usd.Stage.LoadAll)
    if not source or not source.GetPrimAtPath("/World/TestBench") or not source.GetPrimAtPath("/World/Simulation"):
        raise RuntimeError("validated F4 test-bench stage with system routes is required")

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
    world.SetCustomDataByKey("3dprinting993:startSupportStatus", config["status"])
    world.SetCustomDataByKey("3dprinting993:oilPrimeTopologyComplete", True)
    world.SetCustomDataByKey("3dprinting993:oilPrimeSolverReady", False)
    world.SetCustomDataByKey("3dprinting993:starterTorqueSimulationReady", False)
    root = UsdGeom.Xform.Define(stage, "/World/TestBench/StartSupportF5").GetPrim()
    root.SetMetadata("kind", "assembly")
    root.SetCustomDataByKey("3dprinting993:releaseStatus", "research_only")
    root.SetCustomDataByKey("3dprinting993:remainingInputsJson", json.dumps(config["remaining_release_inputs"]))

    crank_path = family_path(stage, "crankshaft")
    case_path = family_path(stage, "crankcase_half")
    pump_path = family_path(stage, "pressure_oil_pump")
    cooler_path = family_path(stage, "oil_cooler")
    crank_prim = stage.GetPrimAtPath(crank_path)
    crank_range = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_]).ComputeWorldBound(crank_prim).ComputeAlignedRange()
    crank_center = (crank_range.GetMin() + crank_range.GetMax()) * 0.5
    output_x = crank_range.GetMax()[0] + 24.0
    output_point = Gf.Vec3d(output_x, crank_center[1], crank_center[2])
    dyno_point = center(stage, "/World/TestBench/Dynamometer")
    coupling_point = center(stage, "/World/TestBench/DynoCoupling")
    starter_point = Gf.Vec3d(output_x - 45.0, crank_center[1] + 155.0, crank_center[2] - 95.0)
    pinion_point = Gf.Vec3d(output_x, crank_center[1] + 95.0, crank_center[2] - 60.0)

    dark = Gf.Vec3f(0.10, 0.11, 0.12)
    steel = Gf.Vec3f(0.45, 0.48, 0.52)
    yellow = Gf.Vec3f(0.90, 0.58, 0.05)
    red = Gf.Vec3f(0.75, 0.05, 0.03)
    brown = Gf.Vec3f(0.48, 0.26, 0.06)
    cyan = Gf.Vec3f(0.10, 0.75, 0.90)

    starter = cylinder(stage, f"{root.GetPath()}/StarterMotor", starter_point, 58.0, 190.0, dark)
    tag(starter, "starter_motor", "layout_proxy_mount_current_and_torque_unmeasured")
    pinion = cylinder(stage, f"{root.GetPath()}/StarterPinion", pinion_point, 28.0, 35.0, steel)
    tag(pinion, "starter_pinion", "tooth_geometry_mesh_and_backlash_unmeasured")
    ring = cylinder(stage, f"{root.GetPath()}/RingGear", output_point, 132.0, 22.0, steel)
    tag(ring, "ring_gear", "solid_envelope_proxy_not_tooth_geometry")
    flange = cylinder(stage, f"{root.GetPath()}/CrankOutputFlange", Gf.Vec3d(output_x + 25.0, crank_center[1], crank_center[2]), 88.0, 32.0, steel)
    tag(flange, "crank_output_flange", "register_bolt_pattern_runout_and_material_unmeasured")
    adapter_center = (output_point + coupling_point) * 0.5
    adapter = cylinder(stage, f"{root.GetPath()}/DynoAdapter", adapter_center, 68.0, abs(coupling_point[0] - output_point[0]), yellow)
    tag(adapter, "dyno_adapter", "layout_proxy_torque_and_misalignment_rating_unmeasured")
    guard = cube(stage, f"{root.GetPath()}/CouplingGuard", (output_point + dyno_point) * 0.5 + Gf.Vec3d(0.0, 0.0, 80.0), Gf.Vec3d(abs(dyno_point[0] - output_point[0]) + 160.0, 360.0, 330.0), yellow, 0.22)
    tag(guard, "coupling_guard", "visual_envelope_not_safety_certified")
    UsdPhysics.RigidBodyAPI.Apply(flange).CreateKinematicEnabledAttr(True)
    root.CreateRelationship("starterDriveTargets").SetTargets([Sdf.Path(str(pinion.GetPath())), Sdf.Path(str(ring.GetPath()))])
    root.CreateRelationship("dynoDriveTargets").SetTargets([Sdf.Path(crank_path), Sdf.Path(str(flange.GetPath())), Sdf.Path(str(adapter.GetPath()))])

    battery = center(stage, "/World/TestBench/Battery")
    case = center(stage, case_path)
    positive = curve(stage, f"{root.GetPath()}/BatteryPositiveCable", [battery, battery + Gf.Vec3d(0.0, 0.0, 90.0), starter_point], 9.0, red)
    tag(positive, "battery_positive_cable", "route_proxy_gauge_length_terminals_and_fuse_unmeasured")
    ground = curve(stage, f"{root.GetPath()}/EngineGroundStrap", [battery, battery + Gf.Vec3d(0.0, -80.0, 0.0), case], 11.0, dark)
    tag(ground, "engine_ground_strap", "route_proxy_resistance_and_bonding_points_unmeasured")

    reservoir = center(stage, "/World/TestBench/OilReservoir")
    pump = center(stage, pump_path)
    cooler = center(stage, cooler_path)
    supply_mid = (reservoir + pump) * 0.5 + Gf.Vec3d(0.0, 0.0, 100.0)
    supply = curve(stage, f"{root.GetPath()}/OilReservoirSupply", [reservoir, supply_mid, pump], 14.0, brown)
    tag(supply, "oil_reservoir_supply", "route_proxy_inside_diameter_length_and_pressure_drop_unmeasured")
    return_mid = (cooler + reservoir) * 0.5 + Gf.Vec3d(0.0, 0.0, 120.0)
    oil_return = curve(stage, f"{root.GetPath()}/OilCoolerReturn", [cooler, return_mid, reservoir], 14.0, brown)
    tag(oil_return, "oil_cooler_return", "route_proxy_inside_diameter_length_and_pressure_drop_unmeasured")

    for index, point in enumerate((pump, cooler), start=1):
        pressure = sensor(stage, f"{root.GetPath()}/OilPressureSensor_{index:02d}", point + Gf.Vec3d(0.0, 0.0, 28.0), cyan)
        tag(pressure, "oil_pressure_sensor", "position_proxy_range_calibration_and_trip_threshold_unmeasured")
        temperature = sensor(stage, f"{root.GetPath()}/OilTemperatureSensor_{index:02d}", point + Gf.Vec3d(0.0, 0.0, 55.0), red)
        tag(temperature, "oil_temperature_sensor", "position_proxy_range_calibration_and_trip_threshold_unmeasured")

    stage.GetRootLayer().Save()
    report = {
        "schema_version": "1.0.0",
        "status": "passed_topology_authoring_not_solver_ready",
        "input_stage": str(args.input_stage.resolve()),
        "output_stage": str(args.output.resolve()),
        "support_component_instance_count": config["acceptance"]["support_component_instance_count"],
        "oil_prime_topology_complete": True,
        "oil_prime_solver_ready": False,
        "starter_torque_simulation_ready": False,
        "remaining_release_inputs": config["remaining_release_inputs"],
        "prohibited_use": config["prohibited_use"],
    }
    args.output.with_suffix(".assembly-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
