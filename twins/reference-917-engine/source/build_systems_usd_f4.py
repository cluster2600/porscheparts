#!/usr/bin/env python3
"""Author provisional fluid and electrical routing layers over the 917 F3 stage."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from pxr import Gf, Sdf, Usd, UsdGeom


def relative(layer: Path, asset: Path) -> str:
    return os.path.relpath(asset.resolve(), layer.parent.resolve()).replace(os.sep, "/")


def center(stage: Usd.Stage, path: str) -> Gf.Vec3d:
    prim = stage.GetPrimAtPath(path)
    if not prim:
        raise RuntimeError(f"missing route endpoint: {path}")
    value = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_]).ComputeWorldBound(prim).ComputeAlignedRange()
    return (value.GetMin() + value.GetMax()) * 0.5


def family_paths(stage: Usd.Stage, family: str) -> list[str]:
    scope = stage.GetPrimAtPath(f"/World/Components/{family}")
    return sorted(str(child.GetPath()) for child in scope.GetAllChildren()) if scope else []


def route_pairs(sources: list[str], targets: list[str], count: int, target_group_size: int | None = None):
    if not sources or not targets:
        raise RuntimeError("a declared route references a missing component family")
    pairs = []
    for index in range(count):
        source = sources[min(index, len(sources) - 1)] if len(sources) > 1 else sources[0]
        if target_group_size:
            target = targets[min(index // target_group_size, len(targets) - 1)]
        else:
            target = targets[index % len(targets)]
        pairs.append((source, target))
    return pairs


def curve(stage: Usd.Stage, path: str, start: Gf.Vec3d, end: Gf.Vec3d, width: float, color: Gf.Vec3f):
    item = UsdGeom.BasisCurves.Define(stage, path)
    middle = (start + end) * 0.5 + Gf.Vec3d(0.0, 0.0, max(30.0, abs(end[1] - start[1]) * 0.12))
    item.CreateTypeAttr(UsdGeom.Tokens.linear)
    item.CreateCurveVertexCountsAttr([3])
    item.CreatePointsAttr([start, middle, end])
    item.CreateWidthsAttr([width])
    item.SetWidthsInterpolation(UsdGeom.Tokens.constant)
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
    if not source or not source.GetPrimAtPath("/World"):
        raise RuntimeError("validated F3 stage with /World is required")

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
    world.SetCustomDataByKey("3dprinting993:systemsStatus", config["status"])
    world.SetCustomDataByKey("3dprinting993:systemsSimulationReady", False)
    simulation = UsdGeom.Scope.Define(stage, "/World/Simulation").GetPrim()
    simulation.SetCustomDataByKey("3dprinting993:releaseStatus", "research_only")
    UsdGeom.Scope.Define(stage, "/World/Simulation/Fluids")
    fluid_colors = {
        "external_cooling_air": Gf.Vec3f(0.2, 0.65, 1.0),
        "intake_air": Gf.Vec3f(0.1, 0.8, 0.9),
        "exhaust_gas": Gf.Vec3f(1.0, 0.25, 0.05),
        "dry_sump_oil": Gf.Vec3f(0.55, 0.32, 0.08),
    }
    turbo_routes = []
    fluid_count = 0
    for spec in config["fluid_routes"]:
        UsdGeom.Scope.Define(stage, f"/World/Simulation/Fluids/{spec['domain']}")
        sources = family_paths(stage, spec["from_family"])
        targets = family_paths(stage, spec["to_family"])
        for index, (source_path, target_path) in enumerate(
            route_pairs(sources, targets, spec["count"], spec.get("target_group_size")), start=1
        ):
            path = f"/World/Simulation/Fluids/{spec['domain']}/{spec['id']}_{index:02d}"
            prim = curve(stage, path, center(stage, source_path), center(stage, target_path), 12.0, fluid_colors[spec["domain"]])
            prim.SetCustomDataByKey("3dprinting993:domain", spec["domain"])
            prim.SetCustomDataByKey("3dprinting993:sourceEndpoint", source_path)
            prim.SetCustomDataByKey("3dprinting993:targetEndpoint", target_path)
            prim.SetCustomDataByKey("3dprinting993:confidence", spec["confidence"])
            prim.SetCustomDataByKey("3dprinting993:simulationReady", False)
            fluid_count += 1
            if spec["variant"] == "917_30_only":
                turbo_routes.append(prim)

    electrical = UsdGeom.Scope.Define(stage, "/World/Simulation/Electrical").GetPrim()
    electrical.SetCustomDataByKey("3dprinting993:requiredInputsJson", json.dumps(config["electrical_system"]["required_inputs"]))
    bounds = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_]).ComputeWorldBound(world).ComputeAlignedRange()
    lower, upper = bounds.GetMin(), bounds.GetMax()
    external = {
        "external_battery_bus": Gf.Vec3d(lower[0], upper[1] + 120.0, lower[2]),
        "starter_motor": Gf.Vec3d(upper[0] + 80.0, lower[1], lower[2] + 80.0),
    }

    def electrical_endpoints(node: str) -> list[tuple[str, Gf.Vec3d]]:
        if node in external:
            return [(f"/World/Simulation/Electrical/External/{node}", external[node])]
        paths = family_paths(stage, node)
        return [(path, center(stage, path)) for path in paths]

    UsdGeom.Scope.Define(stage, "/World/Simulation/Electrical/External")
    for name, point in external.items():
        marker = UsdGeom.Sphere.Define(stage, f"/World/Simulation/Electrical/External/{name}")
        marker.CreateRadiusAttr(10.0)
        marker.AddTranslateOp().Set(point)
        marker.CreateDisplayColorAttr([Gf.Vec3f(1.0, 0.8, 0.0)])
        marker.GetPrim().SetCustomDataByKey("3dprinting993:interfaceStatus", "position_unmeasured")

    electrical_count = 0
    for spec in config["electrical_system"]["routes"]:
        sources = electrical_endpoints(spec["from"])
        targets = electrical_endpoints(spec["to"])
        for index in range(spec["count"]):
            group_size = spec.get("target_group_size")
            source_index = index // group_size if group_size and len(sources) > 1 else min(index, len(sources) - 1)
            source_path, start = sources[source_index]
            target_index = index
            target_path, end = targets[target_index % len(targets)]
            prim = curve(stage, f"/World/Simulation/Electrical/{spec['id']}_{index + 1:02d}", start, end, 3.0, Gf.Vec3f(1.0, 0.75, 0.05))
            prim.SetCustomDataByKey("3dprinting993:signal", spec["signal"])
            prim.SetCustomDataByKey("3dprinting993:sourceEndpoint", source_path)
            prim.SetCustomDataByKey("3dprinting993:targetEndpoint", target_path)
            prim.SetCustomDataByKey("3dprinting993:simulationReady", False)
            electrical_count += 1

    variants = world.GetVariantSets().GetVariantSet("engineVariant")
    previous = variants.GetVariantSelection()
    for name, active in (("type_912_4_5_na", False), ("917_30_turbo", True)):
        variants.SetVariantSelection(name)
        with variants.GetVariantEditContext():
            for prim in turbo_routes:
                prim.SetActive(active)
    variants.SetVariantSelection(previous or "type_912_4_5_na")
    stage.GetRootLayer().Save()
    report = {
        "schema_version": "1.0.0",
        "status": "passed_topology_visualization_not_solver_ready",
        "output_stage": str(args.output.resolve()),
        "fluid_route_instance_count": fluid_count,
        "electrical_route_instance_count": electrical_count,
        "simulation_ready": False,
        "prohibited_use": config["prohibited_use"],
    }
    args.output.with_suffix(".assembly-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
