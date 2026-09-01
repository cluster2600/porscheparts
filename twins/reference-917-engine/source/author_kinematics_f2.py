#!/usr/bin/env python3
"""Author a conservative, time-sampled 917 F2 kinematic layer for Omniverse."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path

from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics


def relative(layer: Path, asset: Path) -> str:
    return os.path.relpath(asset.resolve(), layer.parent.resolve()).replace(os.sep, "/")


def cylinder_phase_deg(cylinder: int, firing_order: list[int]) -> float:
    return float(firing_order.index(cylinder) * 60)


def slider_delta_mm(angle_deg: float, crank_radius: float, rod_length: float) -> float:
    angle = math.radians(angle_deg)
    current = crank_radius * math.cos(angle) + math.sqrt(
        rod_length**2 - (crank_radius * math.sin(angle)) ** 2
    )
    return current - (crank_radius + rod_length)


def rod_tilt_deg(angle_deg: float, crank_radius: float, rod_length: float) -> float:
    return math.degrees(math.asin(crank_radius * math.sin(math.radians(angle_deg)) / rod_length))


def periodic_lift_mm(angle_deg: float, center_deg: float, duration_deg: float, maximum_lift: float) -> float:
    delta = (angle_deg - center_deg + 360.0) % 720.0 - 360.0
    half = duration_deg / 2.0
    if abs(delta) >= half:
        return 0.0
    return maximum_lift * 0.5 * (1.0 + math.cos(math.pi * delta / half))


def family_prims(stage: Usd.Stage, family: str) -> list[Usd.Prim]:
    scope = stage.GetPrimAtPath(f"/World/Components/{family}")
    return list(scope.GetChildren()) if scope else []


def base_translate(prim: Usd.Prim) -> tuple[UsdGeom.XformOp, Gf.Vec3d]:
    for op in UsdGeom.Xformable(prim).GetOrderedXformOps():
        if op.GetOpType() == UsdGeom.XformOp.TypeTranslate and op.GetOpName() == "xformOp:translate":
            value = op.Get()
            return op, Gf.Vec3d(value[0], value[1], value[2])
    raise RuntimeError(f"missing base translate op: {prim.GetPath()}")


def base_rotate_xyz(prim: Usd.Prim) -> tuple[UsdGeom.XformOp, Gf.Vec3f]:
    for op in UsdGeom.Xformable(prim).GetOrderedXformOps():
        if op.GetOpType() == UsdGeom.XformOp.TypeRotateXYZ and op.GetOpName() == "xformOp:rotateXYZ":
            value = op.Get()
            return op, Gf.Vec3f(value[0], value[1], value[2])
    raise RuntimeError(f"missing base rotateXYZ op: {prim.GetPath()}")


def make_kinematic(prim: Usd.Prim) -> None:
    body = UsdPhysics.RigidBodyAPI.Apply(prim)
    body.CreateKinematicEnabledAttr(True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_stage", type=Path)
    parser.add_argument("output_stage", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    source_stage = Usd.Stage.Open(str(args.input_stage.resolve()), load=Usd.Stage.LoadAll)
    if not source_stage:
        raise RuntimeError(f"could not open input stage: {args.input_stage}")
    source_default_prim = source_stage.GetDefaultPrim()
    source_up_axis = UsdGeom.GetStageUpAxis(source_stage)
    source_meters_per_unit = UsdGeom.GetStageMetersPerUnit(source_stage)
    args.output_stage.parent.mkdir(parents=True, exist_ok=True)
    layer = Sdf.Layer.CreateNew(str(args.output_stage.resolve()))
    layer.subLayerPaths.append(relative(args.output_stage, args.input_stage))
    stage = Usd.Stage.Open(layer, load=Usd.Stage.LoadAll)
    stage.SetEditTarget(layer)
    world = stage.GetPrimAtPath("/World")
    if not world:
        raise RuntimeError("input stage has no /World prim")
    if source_default_prim:
        composed_default = stage.GetPrimAtPath(source_default_prim.GetPath())
        if composed_default:
            stage.SetDefaultPrim(composed_default)
    UsdGeom.SetStageUpAxis(stage, source_up_axis)
    UsdGeom.SetStageMetersPerUnit(stage, source_meters_per_unit)

    timeline = config["timeline"]
    start = timeline["start_time_code"]
    end = timeline["end_time_code"]
    stage.SetStartTimeCode(start)
    stage.SetEndTimeCode(end)
    stage.SetTimeCodesPerSecond(timeline["time_codes_per_second"])
    stage.SetFramesPerSecond(timeline["time_codes_per_second"])
    world.SetCustomDataByKey("3dprinting993:kinematicsStatus", config["status"])
    world.SetCustomDataByKey("3dprinting993:propertyAssignmentIntent", "run")
    world.SetCustomDataByKey("3dprinting993:combustion", "disabled")
    world.SetCustomDataByKey("3dprinting993:prohibitedUseJson", json.dumps(config["prohibited_use"]))

    scene = UsdPhysics.Scene.Define(stage, "/World/PhysicsScene")
    scene.CreateGravityMagnitudeAttr(config["physics_policy"]["gravity_m_s2"])
    scene.CreateGravityDirectionAttr(Gf.Vec3f(0.0, 0.0, -1.0))

    order = config["firing_order"]["sequence"]
    numbering = {}
    for bank_name, cylinders in config["cylinder_numbering_hypothesis"].items():
        if not bank_name.startswith("bank_"):
            continue
        for cylinder in cylinders:
            numbering[cylinder] = -1 if bank_name == "bank_negative_y" else 1
    moving = set()

    crank = family_prims(stage, "crankshaft")[0]
    crank_op, crank_base = base_rotate_xyz(crank)
    make_kinematic(crank)
    moving.add(str(crank.GetPath()))

    cam_prims = family_prims(stage, "camshaft")
    cam_ops = [(prim, *base_rotate_xyz(prim)) for prim in cam_prims]
    for prim, _, _ in cam_ops:
        make_kinematic(prim)
        moving.add(str(prim.GetPath()))

    piston_families = ("piston", "piston_pin")
    piston_prims = {family: family_prims(stage, family) for family in piston_families}
    ring_prims = family_prims(stage, "piston_ring")
    rod_prims = family_prims(stage, "connecting_rod")
    valve_prims = {
        "intake_valve": family_prims(stage, "intake_valve"),
        "exhaust_valve": family_prims(stage, "exhaust_valve"),
    }
    tappets = family_prims(stage, "bucket_tappet")
    springs = family_prims(stage, "valve_spring")

    translate_data = {}
    for family, prims in piston_prims.items():
        translate_data[family] = [(prim, *base_translate(prim)) for prim in prims]
    translate_data["piston_ring"] = [(prim, *base_translate(prim)) for prim in ring_prims]
    translate_data["intake_valve"] = [(prim, *base_translate(prim)) for prim in valve_prims["intake_valve"]]
    translate_data["exhaust_valve"] = [(prim, *base_translate(prim)) for prim in valve_prims["exhaust_valve"]]
    translate_data["bucket_tappet"] = [(prim, *base_translate(prim)) for prim in tappets]
    translate_data["valve_spring"] = [(prim, *base_translate(prim)) for prim in springs]
    rod_data = [(prim, *base_rotate_xyz(prim)) for prim in rod_prims]

    for family in translate_data:
        for prim, _, _ in translate_data[family]:
            make_kinematic(prim)
            moving.add(str(prim.GetPath()))
    for prim, _, _ in rod_data:
        make_kinematic(prim)
        moving.add(str(prim.GetPath()))

    crank_radius = config["crank_slider"]["stroke_mm"] / 2.0
    rod_length = config["crank_slider"]["connecting_rod_center_distance_mm"]
    valve_cfg = config["valve_motion_hypothesis"]
    frame_count = end - start
    for frame in range(start, end + 1):
        fraction = (frame - start) / frame_count
        crank_angle = fraction * timeline["crank_revolutions"] * 360.0
        cycle_angle = fraction * timeline["crank_revolutions"] * 360.0
        time = Usd.TimeCode(frame)
        crank_op.Set(Gf.Vec3f(crank_angle, crank_base[1], crank_base[2]), time)
        for _, cam_op, cam_base in cam_ops:
            cam_op.Set(Gf.Vec3f(crank_angle / 2.0, cam_base[1], cam_base[2]), time)

        for cylinder in range(1, 13):
            index = cylinder - 1
            bank = numbering[cylinder]
            local_angle = crank_angle + cylinder_phase_deg(cylinder, order)
            delta = slider_delta_mm(local_angle, crank_radius, rod_length)
            tilt = rod_tilt_deg(local_angle, crank_radius, rod_length)
            for family in piston_families:
                _, op, base = translate_data[family][index]
                op.Set(Gf.Vec3d(base[0], base[1] + bank * delta, base[2]), time)
            for ring_index in range(index * 3, index * 3 + 3):
                _, op, base = translate_data["piston_ring"][ring_index]
                op.Set(Gf.Vec3d(base[0], base[1] + bank * delta, base[2]), time)
            _, rod_op, rod_base = rod_data[index]
            rod_op.Set(Gf.Vec3f(rod_base[0], rod_base[1], rod_base[2] + bank * tilt), time)

            cylinder_cycle = (cycle_angle + cylinder_phase_deg(cylinder, order) * 2.0) % 720.0
            intake_lift = periodic_lift_mm(
                cylinder_cycle,
                valve_cfg["intake_center_cycle_deg"],
                valve_cfg["intake_duration_deg"],
                valve_cfg["maximum_lift_mm"],
            )
            exhaust_lift = periodic_lift_mm(
                cylinder_cycle,
                valve_cfg["exhaust_center_cycle_deg"],
                valve_cfg["exhaust_duration_deg"],
                valve_cfg["maximum_lift_mm"],
            )
            _, intake_op, intake_base = translate_data["intake_valve"][index]
            _, exhaust_op, exhaust_base = translate_data["exhaust_valve"][index]
            intake_op.Set(Gf.Vec3d(intake_base[0], intake_base[1], intake_base[2] - intake_lift), time)
            exhaust_op.Set(Gf.Vec3d(exhaust_base[0], exhaust_base[1], exhaust_base[2] + exhaust_lift), time)
            for offset, lift in ((index * 2, intake_lift), (index * 2 + 1, exhaust_lift)):
                for family in ("bucket_tappet", "valve_spring"):
                    _, op, base = translate_data[family][offset]
                    direction = -1.0 if offset % 2 == 0 else 1.0
                    op.Set(Gf.Vec3d(base[0], base[1], base[2] + direction * lift), time)

    stage.GetRootLayer().Save()
    report = {
        "schema_version": "1.0.0",
        "status": "passed",
        "input_stage": str(args.input_stage.resolve()),
        "output_stage": str(args.output_stage.resolve()),
        "animated_prim_count": len(moving),
        "time_sample_count": end - start + 1,
        "crank_revolutions": timeline["crank_revolutions"],
        "property_assignment_intent": "run",
        "combustion": "disabled",
        "limitations": config["prohibited_use"],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
