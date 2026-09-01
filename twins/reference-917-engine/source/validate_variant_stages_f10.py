#!/usr/bin/env python3
"""Fail-closed validation for one separate F10 geometry/kinematics/detail branch."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path

from pxr import Usd, UsdGeom, UsdPhysics
from kinematics_f2_math import (
    cylinder_cycle_deg,
    cylinder_phase_deg,
    periodic_lift_mm,
    rod_tilt_deg,
    slider_delta_mm,
)
from prepare_variant_configs_f10 import (
    EXPECTED_VARIANT_GEOMETRY,
    calculated_displacement_cm3,
    evaluate_stage_provenance,
    stage_provenance_payload,
)


def family_counts(stage: Usd.Stage) -> Counter[str]:
    counts: Counter[str] = Counter()
    components = stage.GetPrimAtPath("/World/Components")
    if not components:
        return counts
    for scope in components.GetChildren():
        for prim in scope.GetChildren():
            family = prim.GetCustomDataByKey("3dprinting993:family")
            if isinstance(family, str):
                counts[family] += 1
    return counts


def engine_variant_switches(stage: Usd.Stage) -> list[str]:
    switches = []
    for prim in stage.TraverseAll():
        if "engineVariant" in prim.GetVariantSets().GetNames():
            switches.append(str(prim.GetPath()))
    return switches


def xform_op(prim: Usd.Prim, name: str) -> UsdGeom.XformOp | None:
    return next((op for op in UsdGeom.Xformable(prim).GetOrderedXformOps() if op.GetOpName() == name), None)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--variant", required=True)
    parser.add_argument("--geometry-config", type=Path, required=True)
    parser.add_argument("--kinematics-config", type=Path, required=True)
    parser.add_argument("--detail-config", type=Path, required=True)
    parser.add_argument("--parts-report", type=Path, required=True)
    parser.add_argument("--geometry-stage", type=Path, required=True)
    parser.add_argument("--kinematic-stage", type=Path, required=True)
    parser.add_argument("--detail-stage", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    geometry_config = json.loads(args.geometry_config.read_text(encoding="utf-8"))
    kinematics_config = json.loads(args.kinematics_config.read_text(encoding="utf-8"))
    detail_config = json.loads(args.detail_config.read_text(encoding="utf-8"))
    parts_report = json.loads(args.parts_report.read_text(encoding="utf-8"))
    variants = {item["variant_id"]: item for item in manifest["variants"]}
    if args.variant not in variants:
        raise RuntimeError(f"unknown F10 variant: {args.variant}")
    variant = variants[args.variant]
    geometry = variant["geometry"]
    canonical_geometry = EXPECTED_VARIANT_GEOMETRY[args.variant]
    expected_provenance = stage_provenance_payload(
        args.variant,
        canonical_geometry["values"]["documented_displacement_cm3"],
        canonical_geometry["field_evidence"],
    )
    expected_calculated = calculated_displacement_cm3(
        canonical_geometry["values"]["cylinder_count"],
        canonical_geometry["values"]["bore_mm"],
        canonical_geometry["values"]["stroke_mm"],
    )

    stages = {
        "geometry": Usd.Stage.Open(str(args.geometry_stage.resolve()), load=Usd.Stage.LoadAll),
        "kinematic": Usd.Stage.Open(str(args.kinematic_stage.resolve()), load=Usd.Stage.LoadAll),
        "detail": Usd.Stage.Open(str(args.detail_stage.resolve()), load=Usd.Stage.LoadAll),
    }
    checks = []

    def check(name: str, passed: bool, **details) -> None:
        checks.append({"name": name, "passed": bool(passed), **details})

    check("stage_paths_distinct", len({args.geometry_stage.resolve(), args.kinematic_stage.resolve(), args.detail_stage.resolve()}) == 3)
    actual_stage_paths = {
        "geometry_stage": args.geometry_stage,
        "kinematic_stage": args.kinematic_stage,
        "detail_stage": args.detail_stage,
    }
    for key, actual in actual_stage_paths.items():
        expected_parts = Path(variant["outputs"][key]).parts
        check(
            f"{key}_matches_manifest",
            tuple(actual.resolve().parts[-len(expected_parts):]) == expected_parts,
            actual=str(actual.resolve()),
            expected=variant["outputs"][key],
        )
    for name, stage in stages.items():
        check(f"{name}_stage_opens", bool(stage))
        if not stage:
            continue
        world = stage.GetPrimAtPath("/World")
        check(f"{name}_default_prim", stage.GetDefaultPrim() == world)
        check(f"{name}_z_up", UsdGeom.GetStageUpAxis(stage) == UsdGeom.Tokens.z)
        check(f"{name}_millimetres", UsdGeom.GetStageMetersPerUnit(stage) == 0.001)
        check(
            f"{name}_variant_id",
            world.GetCustomDataByKey("3dprinting993:variantId") == args.variant,
            actual=world.GetCustomDataByKey("3dprinting993:variantId"),
        )
        check(
            f"{name}_no_engine_variant_switch",
            not engine_variant_switches(stage),
            engine_variant_switches=engine_variant_switches(stage),
        )
        check(
            f"{name}_not_manufacturing_geometry",
            world.GetCustomDataByKey("3dprinting993:manufacturingGeometryReady") is False,
        )
        check(
            f"{name}_not_physical_kinematics",
            world.GetCustomDataByKey("3dprinting993:physicalKinematicsReady") is False,
        )
        provenance_checks = evaluate_stage_provenance(
            expected_provenance,
            documented_displacement_cm3=world.GetCustomDataByKey(
                "3dprinting993:documentedDisplacementCm3"
            ),
            calculated_displacement_cm3=world.GetCustomDataByKey(
                "3dprinting993:calculatedDisplacementCm3"
            ),
            field_evidence_json=world.GetCustomDataByKey("3dprinting993:fieldEvidenceJson"),
            expected_calculated_displacement_cm3=expected_calculated,
        )
        for provenance_name, result in provenance_checks.items():
            check(f"{name}_{provenance_name}", result.pop("passed"), **result)

    geometry_stage = stages["geometry"]
    kinematic_stage = stages["kinematic"]
    detail_stage = stages["detail"]
    if geometry_stage:
        world = geometry_stage.GetPrimAtPath("/World")
        check("geometry_bore", world.GetCustomDataByKey("3dprinting993:boreMm") == geometry["bore_mm"])
        check("geometry_stroke", world.GetCustomDataByKey("3dprinting993:strokeMm") == geometry["stroke_mm"])
        counts = family_counts(geometry_stage)
        expected = Counter({item["id"]: item["count"] for item in geometry_config["component_families"]})
        check("geometry_family_counts", counts == expected, actual=dict(counts), expected=dict(expected))
        check(
            "geometry_turbocharger_count",
            counts["turbocharger"] == variant["assembly_filter"]["turbocharger_expected_count"],
            actual=counts["turbocharger"],
        )
        check(
            "geometry_charge_plenum_count",
            counts["charge_plenum"] == variant["assembly_filter"]["charge_plenum_expected_count"],
            actual=counts["charge_plenum"],
        )

    check("parts_report_variant", parts_report.get("variant_id") == args.variant)
    check("parts_report_bore", parts_report.get("bore_mm") == geometry["bore_mm"])
    check("parts_report_stroke", parts_report.get("stroke_mm") == geometry["stroke_mm"])
    check("parts_not_manufacturing_geometry", parts_report.get("manufacturing_geometry_ready") is False)
    prototype_roots = {Path(item["step"]).resolve().parents[1] for item in parts_report.get("prototypes", [])}
    check("variant_specific_prototype_root", len(prototype_roots) == 1, roots=sorted(map(str, prototype_roots)))

    if kinematic_stage:
        check("kinematic_timeline_start", kinematic_stage.GetStartTimeCode() == kinematics_config["timeline"]["start_time_code"])
        check("kinematic_timeline_end", kinematic_stage.GetEndTimeCode() == kinematics_config["timeline"]["end_time_code"])
        stroke = geometry["stroke_mm"]
        tolerance = kinematics_config["acceptance"]["piston_travel_tolerance_mm"]
        piston_travel = {}
        piston_scope = kinematic_stage.GetPrimAtPath("/World/Components/piston")
        pistons = list(piston_scope.GetChildren()) if piston_scope else []
        for prim in pistons:
            translate = xform_op(prim, "xformOp:translate")
            if translate is None:
                continue
            samples = translate.GetAttr().GetTimeSamples()
            values = [translate.Get(Usd.TimeCode(time))[1] for time in samples]
            if values:
                piston_travel[str(prim.GetPath())] = max(values) - min(values)
        check("kinematic_piston_count", len(piston_travel) == 12, actual=len(piston_travel))
        for path, travel in piston_travel.items():
            check(f"kinematic_stroke_{Path(path).name}", abs(travel - stroke) <= tolerance, actual=travel, expected=stroke)
        unsafe_dynamic = []
        for prim in kinematic_stage.TraverseAll():
            if not prim.HasAPI(UsdPhysics.RigidBodyAPI):
                continue
            samples = [time for attr in prim.GetAttributes() for time in attr.GetTimeSamples()]
            if samples and UsdPhysics.RigidBodyAPI(prim).GetKinematicEnabledAttr().Get() is not True:
                unsafe_dynamic.append(str(prim.GetPath()))
        check("kinematic_animated_bodies_are_kinematic", not unsafe_dynamic, unsafe_dynamic=unsafe_dynamic)

        order = kinematics_config["firing_order"]["sequence"]
        bank_by_cylinder = {}
        for bank_name, cylinders in kinematics_config["cylinder_numbering_hypothesis"].items():
            if bank_name == "bank_negative_y":
                bank_by_cylinder.update({cylinder: -1 for cylinder in cylinders})
            elif bank_name == "bank_positive_y":
                bank_by_cylinder.update({cylinder: 1 for cylinder in cylinders})
        crank_radius = stroke / 2.0
        rod_length = kinematics_config["crank_slider"]["connecting_rod_center_distance_mm"]
        crank_prims = list(kinematic_stage.GetPrimAtPath("/World/Components/crankshaft").GetChildren())
        cam_prims = list(kinematic_stage.GetPrimAtPath("/World/Components/camshaft").GetChildren())
        pin_prims = list(kinematic_stage.GetPrimAtPath("/World/Components/piston_pin").GetChildren())
        ring_prims = list(kinematic_stage.GetPrimAtPath("/World/Components/piston_ring").GetChildren())
        rod_prims = list(kinematic_stage.GetPrimAtPath("/World/Components/connecting_rod").GetChildren())
        crank_op = xform_op(crank_prims[0], "xformOp:rotateXYZ") if len(crank_prims) == 1 else None
        crank_times = crank_op.GetAttr().GetTimeSamples() if crank_op else []
        check("kinematic_crank_time_samples", len(crank_times) == kinematic_stage.GetEndTimeCode() - kinematic_stage.GetStartTimeCode() + 1, actual=len(crank_times))

        cam_ratio_error = 0.0
        for cam in cam_prims:
            cam_op = xform_op(cam, "xformOp:rotateXYZ")
            if cam_op and crank_op:
                for time in crank_times:
                    cam_ratio_error = max(
                        cam_ratio_error,
                        abs(float(cam_op.Get(Usd.TimeCode(time))[0]) * 2.0 - float(crank_op.Get(Usd.TimeCode(time))[0])),
                    )
            else:
                cam_ratio_error = math.inf
        check("kinematic_camshaft_half_speed_ratio", len(cam_prims) == 4 and cam_ratio_error <= 1e-4, maximum_error_deg=cam_ratio_error)

        piston_model_error = 0.0
        pin_comovement_error = 0.0
        ring_comovement_error = 0.0
        rod_model_error = 0.0
        complete_motion_families = (
            len(pistons) == 12 and len(pin_prims) == 12 and len(ring_prims) == 36 and len(rod_prims) == 12
        )
        if complete_motion_families and crank_op:
            for cylinder in range(1, 13):
                index = cylinder - 1
                phase = cylinder_phase_deg(cylinder, order)
                bank = bank_by_cylinder[cylinder]
                piston_op = xform_op(pistons[index], "xformOp:translate")
                pin_op = xform_op(pin_prims[index], "xformOp:translate")
                rod_op = xform_op(rod_prims[index], "xformOp:rotateXYZ")
                if not piston_op or not pin_op or not rod_op:
                    complete_motion_families = False
                    break
                piston_base = piston_op.Get(Usd.TimeCode.Default())
                pin_base = pin_op.Get(Usd.TimeCode.Default())
                rod_base = rod_op.Get(Usd.TimeCode.Default())
                cylinder_ring_ops = [xform_op(ring_prims[index * 3 + offset], "xformOp:translate") for offset in range(3)]
                if any(op is None for op in cylinder_ring_ops):
                    complete_motion_families = False
                    break
                ring_bases = [op.Get(Usd.TimeCode.Default()) for op in cylinder_ring_ops]
                for time in crank_times:
                    time_code = Usd.TimeCode(time)
                    crank_angle = float(crank_op.Get(time_code)[0])
                    expected_delta = bank * slider_delta_mm(crank_angle + phase, crank_radius, rod_length)
                    piston_delta = float(piston_op.Get(time_code)[1] - piston_base[1])
                    pin_delta = float(pin_op.Get(time_code)[1] - pin_base[1])
                    piston_model_error = max(piston_model_error, abs(piston_delta - expected_delta))
                    pin_comovement_error = max(pin_comovement_error, abs(pin_delta - piston_delta))
                    for ring_op, ring_base in zip(cylinder_ring_ops, ring_bases):
                        ring_delta = float(ring_op.Get(time_code)[1] - ring_base[1])
                        ring_comovement_error = max(ring_comovement_error, abs(ring_delta - piston_delta))
                    expected_tilt = bank * rod_tilt_deg(crank_angle + phase, crank_radius, rod_length)
                    actual_tilt = float(rod_op.Get(time_code)[2] - rod_base[2])
                    rod_model_error = max(rod_model_error, abs(actual_tilt - expected_tilt))
        check("kinematic_motion_family_counts", complete_motion_families)
        check("kinematic_piston_phase_model", complete_motion_families and piston_model_error <= tolerance, maximum_error_mm=piston_model_error)
        check("kinematic_pin_piston_comovement", complete_motion_families and pin_comovement_error <= 1e-6, maximum_error_mm=pin_comovement_error)
        check("kinematic_ring_piston_comovement", complete_motion_families and ring_comovement_error <= 1e-6, maximum_error_mm=ring_comovement_error)
        check("kinematic_rod_phase_model", complete_motion_families and rod_model_error <= 1e-4, maximum_error_deg=rod_model_error)

        intake_prims = list(kinematic_stage.GetPrimAtPath("/World/Components/intake_valve").GetChildren())
        exhaust_prims = list(kinematic_stage.GetPrimAtPath("/World/Components/exhaust_valve").GetChildren())
        tappet_prims = list(kinematic_stage.GetPrimAtPath("/World/Components/bucket_tappet").GetChildren())
        spring_prims = list(kinematic_stage.GetPrimAtPath("/World/Components/valve_spring").GetChildren())
        complete_valve_families = (
            len(intake_prims) == 12
            and len(exhaust_prims) == 12
            and len(tappet_prims) == 24
            and len(spring_prims) == 24
        )
        valve_cfg = kinematics_config["valve_motion_hypothesis"]
        valve_model_error = 0.0
        follower_comovement_error = 0.0
        if complete_valve_families and crank_op:
            for cylinder in range(1, 13):
                index = cylinder - 1
                intake_op = xform_op(intake_prims[index], "xformOp:translate")
                exhaust_op = xform_op(exhaust_prims[index], "xformOp:translate")
                follower_ops = [
                    xform_op(tappet_prims[index * 2], "xformOp:translate"),
                    xform_op(tappet_prims[index * 2 + 1], "xformOp:translate"),
                    xform_op(spring_prims[index * 2], "xformOp:translate"),
                    xform_op(spring_prims[index * 2 + 1], "xformOp:translate"),
                ]
                if not intake_op or not exhaust_op or any(op is None for op in follower_ops):
                    complete_valve_families = False
                    break
                intake_base = intake_op.Get(Usd.TimeCode.Default())
                exhaust_base = exhaust_op.Get(Usd.TimeCode.Default())
                follower_bases = [op.Get(Usd.TimeCode.Default()) for op in follower_ops]
                for time in crank_times:
                    time_code = Usd.TimeCode(time)
                    crank_angle = float(crank_op.Get(time_code)[0])
                    cylinder_cycle = cylinder_cycle_deg(crank_angle, cylinder, order)
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
                    intake_delta = float(intake_op.Get(time_code)[2] - intake_base[2])
                    exhaust_delta = float(exhaust_op.Get(time_code)[2] - exhaust_base[2])
                    valve_model_error = max(
                        valve_model_error,
                        abs(intake_delta + intake_lift),
                        abs(exhaust_delta - exhaust_lift),
                    )
                    expected_followers = (-intake_lift, exhaust_lift, -intake_lift, exhaust_lift)
                    for follower_op, follower_base, expected in zip(
                        follower_ops, follower_bases, expected_followers
                    ):
                        delta = float(follower_op.Get(time_code)[2] - follower_base[2])
                        follower_comovement_error = max(
                            follower_comovement_error, abs(delta - expected)
                        )
        expected_valve_phases = [cylinder_cycle_deg(0.0, cylinder, order) for cylinder in range(1, 13)]
        check("kinematic_twelve_unique_valve_phases", len(set(expected_valve_phases)) == 12, phases_deg=expected_valve_phases)
        check("kinematic_valve_family_counts", complete_valve_families)
        check("kinematic_valve_phase_model", complete_valve_families and valve_model_error <= 1e-4, maximum_error_mm=valve_model_error)
        check("kinematic_tappet_spring_comovement", complete_valve_families and follower_comovement_error <= 1e-4, maximum_error_mm=follower_comovement_error)

    if detail_stage:
        counts = family_counts(detail_stage)
        expected = Counter({item["id"]: item["count"] for item in geometry_config["component_families"]})
        expected.update({item["id"]: item["count"] for item in detail_config["families"]})
        check("detail_combined_family_counts", counts == expected, actual=dict(counts), expected=dict(expected))
        turbo_detail = {"turbo_turbine_wheel", "turbo_compressor_wheel", "turbo_shaft", "wastegate", "wastegate_bypass_pipe"}
        actual_turbo_detail = {family for family in turbo_detail if counts[family]}
        expected_turbo_detail = turbo_detail if args.variant == "917_30_turbo_5374" else set()
        check(
            "detail_turbo_family_filter",
            actual_turbo_detail == expected_turbo_detail,
            actual=sorted(actual_turbo_detail),
            expected=sorted(expected_turbo_detail),
        )

    report = {
        "schema_version": "1.0.0",
        "phase": "F10",
        "status": "passed" if all(item["passed"] for item in checks) else "failed",
        "variant_id": args.variant,
        "stage_mode": "separate_stage_without_engine_variant_set",
        "bore_mm": geometry["bore_mm"],
        "stroke_mm": geometry["stroke_mm"],
        "checks": checks,
        "manufacturing_geometry_ready": False,
        "physical_kinematics_ready": False,
        "missing_variant_inputs": manifest["missing_variant_inputs"][args.variant],
        "prohibited_use": manifest["prohibited_use"],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "variant_id": args.variant, "checks": len(checks)}, indent=2))
    raise SystemExit(0 if report["status"] == "passed" else 1)


if __name__ == "__main__":
    main()
