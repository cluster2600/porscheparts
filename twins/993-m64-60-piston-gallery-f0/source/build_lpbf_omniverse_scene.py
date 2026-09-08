#!/usr/bin/env python3
"""Construit la scène Omniverse du criblage LPBF sans simuler le procédé."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(layer: Path, asset: Path) -> str:
    return os.path.relpath(asset.resolve(), layer.resolve().parent).replace(os.sep, "/")


def aligned_bounds(Usd: Any, UsdGeom: Any, prim: Any) -> dict[str, list[float]]:
    cache = UsdGeom.BBoxCache(
        Usd.TimeCode.Default(),
        [UsdGeom.Tokens.default_, UsdGeom.Tokens.render],
    )
    value = cache.ComputeWorldBound(prim).ComputeAlignedRange()
    minimum = [float(item) for item in value.GetMin()]
    maximum = [float(item) for item in value.GetMax()]
    return {
        "min": minimum,
        "max": maximum,
        "size": [high - low for low, high in zip(minimum, maximum)],
    }


def cube(stage: Any, UsdGeom: Any, Gf: Any, path: str, center, size, color, opacity=1.0):
    item = UsdGeom.Cube.Define(stage, path)
    item.CreateSizeAttr(1.0)
    item.AddTranslateOp().Set(Gf.Vec3d(*center))
    item.AddScaleOp().Set(Gf.Vec3d(*size))
    item.CreateDisplayColorAttr([Gf.Vec3f(*color)])
    item.CreateDisplayOpacityAttr([float(opacity)])
    return item


def build(args: argparse.Namespace) -> dict[str, Any]:
    from pxr import Gf, Kind, Usd, UsdGeom

    source = args.input_usd.resolve()
    output = args.output_usd.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    source_stage = Usd.Stage.Open(str(source), Usd.Stage.LoadAll)
    if source_stage is None or not source_stage.GetDefaultPrim():
        raise RuntimeError("input_usd_has_no_default_prim")
    source_bounds = aligned_bounds(Usd, UsdGeom, source_stage.GetDefaultPrim())
    source_meters_per_unit = float(UsdGeom.GetStageMetersPerUnit(source_stage))
    mm_to_stage = 0.001 / source_meters_per_unit

    angle = math.radians(args.roll_y_deg)
    corners = []
    for x in (source_bounds["min"][0], source_bounds["max"][0]):
        for y in (source_bounds["min"][1], source_bounds["max"][1]):
            for z in (source_bounds["min"][2], source_bounds["max"][2]):
                corners.append(
                    (
                        math.cos(angle) * x + math.sin(angle) * z,
                        y,
                        -math.sin(angle) * x + math.cos(angle) * z,
                    )
                )
    ground_translation = -min(point[2] for point in corners)

    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Usd.Stage.CreateNew(str(output))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, source_meters_per_unit)
    stage.SetStartTimeCode(0.0)
    stage.SetEndTimeCode(1.0)
    stage.SetTimeCodesPerSecond(1.0)
    root = UsdGeom.Xform.Define(stage, "/LPBFBuildScreen").GetPrim()
    stage.SetDefaultPrim(root)
    root.SetMetadata("kind", Kind.Tokens.assembly)
    root.SetCustomData(
        {
            "partId": args.part_id,
            "classification": "geometric_lpbf_build_scene_not_process_simulation",
            "candidateOrientation": f"roll_y_{args.roll_y_deg:g}",
            "metalPrintAuthorized": False,
            "recoaterCollisionValidated": False,
        }
    )

    piston = UsdGeom.Xform.Define(stage, "/LPBFBuildScreen/PistonCandidate")
    piston.GetPrim().SetMetadata("kind", Kind.Tokens.group)
    common = UsdGeom.XformCommonAPI(piston)
    common.SetTranslate(Gf.Vec3d(0.0, 0.0, ground_translation))
    common.SetRotate(
        Gf.Vec3f(0.0, args.roll_y_deg, 0.0),
        UsdGeom.XformCommonAPI.RotationOrderXYZ,
    )
    asset = UsdGeom.Xform.Define(stage, "/LPBFBuildScreen/PistonCandidate/Asset")
    asset.GetPrim().SetMetadata("kind", Kind.Tokens.group)
    asset.GetPrim().GetReferences().AddReference(relative(output, source))
    asset.GetPrim().SetCustomData(
        {
            "sourceSha256": sha256(source),
            "orientationStatus": "candidate_not_engineering_reviewed",
        }
    )

    plate = cube(
        stage,
        UsdGeom,
        Gf,
        "/LPBFBuildScreen/BuildPlate",
        (0.0, 0.0, -5.0 * mm_to_stage),
        (
            args.machine_diameter_mm * mm_to_stage,
            args.machine_diameter_mm * mm_to_stage,
            10.0 * mm_to_stage,
        ),
        (0.12, 0.15, 0.18),
    )
    plate.GetPrim().SetCustomData({"role": "visual_build_plate_proxy"})

    envelope = UsdGeom.Cylinder.Define(stage, "/LPBFBuildScreen/MachineEnvelope")
    envelope.CreateAxisAttr(UsdGeom.Tokens.z)
    envelope.CreateRadiusAttr(args.machine_diameter_mm * mm_to_stage / 2.0)
    envelope.CreateHeightAttr(args.machine_height_mm * mm_to_stage)
    envelope.AddTranslateOp().Set(
        Gf.Vec3d(0.0, 0.0, args.machine_height_mm * mm_to_stage / 2.0)
    )
    envelope.CreateDisplayColorAttr([Gf.Vec3f(0.10, 0.40, 0.65)])
    envelope.CreateDisplayOpacityAttr([0.08])
    envelope.CreatePurposeAttr(UsdGeom.Tokens.guide)
    envelope.GetPrim().SetCustomData({"role": "nominal_machine_envelope_not_collision_geometry"})

    recoater = cube(
        stage,
        UsdGeom,
        Gf,
        "/LPBFBuildScreen/RecoaterGuide",
        (
            0.0,
            0.0,
            (args.nominal_build_height_mm + args.nominal_recoater_gap_mm) * mm_to_stage,
        ),
        (5.0 * mm_to_stage, args.machine_diameter_mm * mm_to_stage, 1.0 * mm_to_stage),
        (0.95, 0.35, 0.08),
        0.65,
    )
    translate = recoater.GetOrderedXformOps()[0]
    z = (args.nominal_build_height_mm + args.nominal_recoater_gap_mm) * mm_to_stage
    translate.Set(
        Gf.Vec3d(-args.machine_diameter_mm * mm_to_stage / 2.0, 0.0, z),
        Usd.TimeCode(0.0),
    )
    translate.Set(
        Gf.Vec3d(args.machine_diameter_mm * mm_to_stage / 2.0, 0.0, z),
        Usd.TimeCode(1.0),
    )
    recoater.CreatePurposeAttr(UsdGeom.Tokens.guide)
    recoater.GetPrim().SetCustomData(
        {
            "role": "visual_sweep_only",
            "collisionSimulationExecuted": False,
            "missingInput": "calibrated_distortion_field_and_blade_compliance",
        }
    )
    stage.GetRootLayer().documentation = (
        "Scène de revue Omniverse de l'orientation LPBF candidate. Le volume machine, "
        "la plaque et le recoater sont des guides; aucune physique procédé ni collision "
        "sur forme déformée n'est revendiquée."
    )
    stage.GetRootLayer().Save()

    reopened = Usd.Stage.Open(str(output), Usd.Stage.LoadAll)
    if reopened is None:
        raise RuntimeError("output_usd_cannot_reopen")
    piston_bounds = aligned_bounds(
        Usd, UsdGeom, reopened.GetPrimAtPath("/LPBFBuildScreen/PistonCandidate")
    )
    max_radius = max(
        math.hypot(x, y)
        for x in (piston_bounds["min"][0], piston_bounds["max"][0])
        for y in (piston_bounds["min"][1], piston_bounds["max"][1])
    )
    grounded = abs(piston_bounds["min"][2]) <= args.ground_tolerance_mm * mm_to_stage
    inside = (
        grounded
        and max_radius <= args.machine_diameter_mm * mm_to_stage / 2.0
        and piston_bounds["max"][2] <= args.machine_height_mm * mm_to_stage
    )
    if not inside:
        raise RuntimeError(f"candidate_outside_nominal_machine_envelope:{piston_bounds}")
    report = {
        "schema_version": "1.0.0",
        "part_id": args.part_id,
        "classification": "executed_omniverse_lpbf_build_setup_screen_not_recoater_or_process_validation",
        "input_usd_sha256": sha256(source),
        "output_usd_sha256": sha256(output),
        "orientation": f"roll_y_{args.roll_y_deg:g}",
        "piston_world_bounds_mm": {
            key: [value / mm_to_stage for value in values]
            for key, values in piston_bounds.items()
        },
        "conservative_bounding_radius_mm": max_radius / mm_to_stage,
        "machine": {
            "diameter_mm": args.machine_diameter_mm,
            "height_mm": args.machine_height_mm,
        },
        "recoater_guide": {
            "animated": True,
            "nominal_gap_above_geometric_build_mm": args.nominal_recoater_gap_mm,
            "collision_simulation_executed": False,
        },
        "gates": {
            "input_usd_hash_bound": True,
            "candidate_grounded_on_plate": grounded,
            "bare_part_inside_nominal_machine_envelope": inside,
            "candidate_orientation_engineering_reviewed": False,
            "distortion_field_applied": False,
            "recoater_collision_validated": False,
            "supplier_support_geometry_loaded": False,
            "metal_print_authorized": False,
        },
    }
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--part-id", required=True)
    parser.add_argument("--input-usd", type=Path, required=True)
    parser.add_argument("--output-usd", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--roll-y-deg", type=float, default=45.0)
    parser.add_argument("--machine-diameter-mm", type=float, default=315.0)
    parser.add_argument("--machine-height-mm", type=float, default=400.0)
    parser.add_argument("--nominal-build-height-mm", type=float, required=True)
    parser.add_argument("--nominal-recoater-gap-mm", type=float, default=1.0)
    parser.add_argument("--ground-tolerance-mm", type=float, default=0.01)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build(args)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
