#!/usr/bin/env python3
"""Author exterior and cutaway camera layers for the 917 motion video."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from pxr import Gf, Sdf, Usd, UsdGeom


def relative(layer: Path, asset: Path) -> str:
    return os.path.relpath(asset.resolve(), layer.parent.resolve()).replace(os.sep, "/")


def author_stage(source_path: Path, output: Path, config: dict, cutaway: bool) -> None:
    source = Usd.Stage.Open(str(source_path.resolve()), load=Usd.Stage.LoadAll)
    if not source or not source.GetPrimAtPath("/World/TestBench/StartSupportF5"):
        raise RuntimeError("validated F5 stage is required")
    output.parent.mkdir(parents=True, exist_ok=True)
    layer = Sdf.Layer.CreateNew(str(output.resolve()))
    layer.subLayerPaths.append(relative(output, source_path))
    stage = Usd.Stage.Open(layer, load=Usd.Stage.LoadAll)
    stage.SetEditTarget(layer)
    stage.SetDefaultPrim(stage.GetPrimAtPath("/World"))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.GetStageUpAxis(source))
    UsdGeom.SetStageMetersPerUnit(stage, UsdGeom.GetStageMetersPerUnit(source))
    stage.SetStartTimeCode(source.GetStartTimeCode())
    stage.SetEndTimeCode(source.GetEndTimeCode())
    stage.SetTimeCodesPerSecond(source.GetTimeCodesPerSecond())
    stage.SetFramesPerSecond(source.GetFramesPerSecond())

    components = stage.GetPrimAtPath("/World/Components")
    bounds = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_]).ComputeWorldBound(components).ComputeAlignedRange()
    center = (bounds.GetMin() + bounds.GetMax()) * 0.5
    extent = bounds.GetMax() - bounds.GetMin()
    radius = max(extent[0], extent[1], extent[2])
    eye = center + Gf.Vec3d(radius * 1.45, -radius * 1.75, radius * 1.05)

    UsdGeom.Scope.Define(stage, "/World/Cameras")
    camera = UsdGeom.Camera.Define(stage, config["render"]["camera_path"])
    camera.CreateFocalLengthAttr(52.0)
    camera.CreateClippingRangeAttr(Gf.Vec2f(1.0, 100000.0))
    transform = Gf.Matrix4d().SetLookAt(eye, center, Gf.Vec3d(0.0, 0.0, 1.0)).GetInverse()
    camera.AddTransformOp().Set(transform)
    camera.GetPrim().SetCustomDataByKey("3dprinting993:view", "cutaway" if cutaway else "exterior")
    camera.GetPrim().SetCustomDataByKey("3dprinting993:disclosure", config["disclosure"])

    if cutaway:
        for family in config["cutaway_hidden_families"]:
            scope = stage.GetPrimAtPath(f"/World/Components/{family}")
            if not scope:
                raise RuntimeError(f"missing cutaway family: {family}")
            for prim in scope.GetChildren():
                UsdGeom.Imageable(prim).MakeInvisible()
    stage.GetPrimAtPath("/World").SetCustomDataByKey("3dprinting993:videoSimulationClaimAuthorized", False)
    stage.GetRootLayer().Save()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_stage", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    outputs = []
    for shot in config["shots"]:
        output = args.output_dir / shot["stage"]
        author_stage(args.input_stage, output, config, shot["id"] == "cutaway")
        outputs.append(str(output.resolve()))
    report = {
        "schema_version": "1.0.0",
        "status": "passed_camera_layers_authored_render_pending",
        "outputs": outputs,
        "expected_frame_count": config["acceptance"]["expected_frame_count"],
        "video_rendered": False,
        "disclosure": config["disclosure"],
    }
    (args.output_dir / "motion-video-f7-stage-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
