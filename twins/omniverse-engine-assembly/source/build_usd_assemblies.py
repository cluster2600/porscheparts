#!/usr/bin/env python3
"""Compose lightweight F0 Omniverse research assemblies from existing USD assets."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


MATERIALS = {
    "SteelPlaceholder": {
        "display_name": "Generic valve steel placeholder",
        "color": (0.34, 0.37, 0.40),
        "metallic": 0.85,
        "roughness": 0.24,
        "classification": "density_baseline_only",
    },
    "Ti64Study": {
        "display_name": "Ti-6Al-4V Grade 5 intake study",
        "color": (0.39, 0.44, 0.49),
        "metallic": 0.80,
        "roughness": 0.30,
        "classification": "intake_comparison_not_engine_release",
    },
    "Ti64Challenge": {
        "display_name": "Ti-6Al-4V exhaust challenge case",
        "color": (0.34, 0.45, 0.53),
        "metallic": 0.80,
        "roughness": 0.32,
        "classification": "deliberately_challenged_not_selected",
    },
    "Inconel751Study": {
        "display_name": "INCONEL 751 exhaust study",
        "color": (0.45, 0.42, 0.34),
        "metallic": 0.90,
        "roughness": 0.28,
        "classification": "bar_material_reference_not_lpbf_qualification",
    },
}


def load_and_validate_config(path: Path, project_root: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    errors: list[str] = []
    if data.get("status") != "F0_research_assembly":
        errors.append("status must be F0_research_assembly")
    if data.get("units") != "mm" or data.get("up_axis") != "Z":
        errors.append("the assembly contract requires millimetres and Z-up")
    for name, asset in data.get("assets", {}).items():
        source = project_root / asset.get("source", "")
        if not source.is_file():
            errors.append(f"missing source asset {name}: {source}")
    for valve in data.get("valves", []):
        source = project_root / valve.get("source", "")
        if not source.is_file():
            errors.append(f"missing valve USD {valve.get('id')}: {source}")
        unknown = set(valve.get("allowed_materials", [])) - MATERIALS.keys()
        if unknown:
            errors.append(f"unknown materials for {valve.get('id')}: {sorted(unknown)}")
        if valve.get("default_material") not in valve.get("allowed_materials", []):
            errors.append(f"default material is not allowed for {valve.get('id')}")
    for component in data.get("research_components", []):
        source = project_root / component.get("source", "")
        if not source.is_file():
            errors.append(f"missing research component {component.get('id')}: {source}")
        if component.get("count", 0) < 1:
            errors.append(f"invalid count for {component.get('id')}")
    if not data.get("limitations"):
        errors.append("limitations must be explicit")
    if errors:
        raise ValueError("; ".join(errors))
    return data


def relative_asset_path(layer_path: Path, asset_path: Path) -> str:
    return os.path.relpath(asset_path.resolve(), layer_path.parent.resolve()).replace(os.sep, "/")


def _stage(path: Path):
    from pxr import Usd, UsdGeom

    path.parent.mkdir(parents=True, exist_ok=True)
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageMetersPerUnit(stage, 0.001)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    world = UsdGeom.Xform.Define(stage, "/World").GetPrim()
    stage.SetDefaultPrim(world)
    world.SetMetadata("kind", "assembly")
    return stage, world


def _set_contract(prim, classification: str, note: str) -> None:
    prim.SetCustomDataByKey("3dprinting993:status", "F0_research_only")
    prim.SetCustomDataByKey("3dprinting993:classification", classification)
    prim.SetCustomDataByKey("3dprinting993:fitment", note)


def _define_materials(stage) -> dict[str, Any]:
    from pxr import Gf, Sdf, UsdGeom, UsdShade

    looks = UsdGeom.Scope.Define(stage, "/World/Looks")
    looks.GetPrim().SetMetadata("kind", "group")
    result = {}
    for name, spec in MATERIALS.items():
        material = UsdShade.Material.Define(stage, f"/World/Looks/{name}")
        shader = UsdShade.Shader.Define(stage, f"/World/Looks/{name}/PreviewSurface")
        shader.CreateIdAttr("UsdPreviewSurface")
        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*spec["color"]))
        shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(spec["metallic"])
        shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(spec["roughness"])
        material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
        material.GetPrim().SetCustomDataByKey("3dprinting993:displayName", spec["display_name"])
        material.GetPrim().SetCustomDataByKey("3dprinting993:classification", spec["classification"])
        result[name] = material
    return result


def build_engine_stage(config: dict[str, Any], project_root: Path, output: Path) -> Path:
    from pxr import UsdGeom

    path = output / "917-engine-assembly-f0.usda"
    stage, world = _stage(path)
    engine_spec = config["assets"]["engine_917"]
    engine = UsdGeom.Xform.Define(stage, "/World/Engine917Reference").GetPrim()
    engine.GetPayloads().AddPayload(
        relative_asset_path(path, project_root / engine_spec["source"])
    )
    engine.SetMetadata("kind", "component")
    _set_contract(engine, engine_spec["classification"], engine_spec["fitment"])
    world.SetCustomDataByKey("3dprinting993:assemblyPurpose", "917 exterior reference decomposition")
    world.SetCustomDataByKey("3dprinting993:limitationsJson", json.dumps(config["limitations"]))
    stage.GetRootLayer().Save()
    return path


def _add_valve(stage, stage_path: Path, valve: dict[str, Any], project_root: Path, materials, lifts):
    from pxr import Gf, UsdGeom, UsdShade

    xform = UsdGeom.Xform.Define(stage, f"/World/Valves/{valve['id']}")
    prim = xform.GetPrim()
    prim.GetReferences().AddReference(relative_asset_path(stage_path, project_root / valve["source"]))
    prim.SetInstanceable(True)
    prim.SetMetadata("kind", "component")
    _set_contract(prim, "F1_valve_proxy", "exploded_layout_not_measured_seat_axis")
    translate = xform.AddTranslateOp()
    base = valve["base_translation_mm"]
    lift_set = prim.GetVariantSets().AddVariantSet("liftStudy")
    for lift in lifts:
        name = f"lift_{str(lift).replace('.', '_')}mm"
        lift_set.AddVariant(name)
        lift_set.SetVariantSelection(name)
        with lift_set.GetVariantEditContext():
            translate.Set(Gf.Vec3d(base[0], base[1], base[2] + lift))
            prim.SetCustomDataByKey("3dprinting993:valveLiftMm", lift)
    lift_set.SetVariantSelection("lift_0_0mm")

    material_set = prim.GetVariantSets().AddVariantSet("materialStudy")
    for material_name in valve["allowed_materials"]:
        material_set.AddVariant(material_name)
        material_set.SetVariantSelection(material_name)
        with material_set.GetVariantEditContext():
            UsdShade.MaterialBindingAPI.Apply(prim).Bind(materials[material_name])
            prim.SetCustomDataByKey("3dprinting993:materialStudy", material_name)
    material_set.SetVariantSelection(valve["default_material"])
    return prim


def build_valvetrain_stage(config: dict[str, Any], project_root: Path, output: Path) -> Path:
    from pxr import UsdGeom

    path = output / "993-935-valvetrain-test-rig-f0.usda"
    stage, world = _stage(path)
    materials = _define_materials(stage)
    head_spec = config["assets"]["head_935"]
    head = UsdGeom.Xform.Define(stage, "/World/Head935Reference").GetPrim()
    head.GetPayloads().AddPayload(relative_asset_path(path, project_root / head_spec["source"]))
    head.SetMetadata("kind", "component")
    _set_contract(head, head_spec["classification"], head_spec["fitment"])
    valves = UsdGeom.Scope.Define(stage, "/World/Valves").GetPrim()
    valves.SetMetadata("kind", "group")
    for valve in config["valves"]:
        _add_valve(stage, path, valve, project_root, materials, config["lift_variants_mm"])
    world.SetCustomDataByKey("3dprinting993:assemblyPurpose", "935 reference head and 993 valve research rig")
    world.SetCustomDataByKey("3dprinting993:limitationsJson", json.dumps(config["limitations"]))
    stage.GetRootLayer().Save()
    return path


def build_overview_stage(config: dict[str, Any], output: Path, engine: Path, rig: Path) -> Path:
    from pxr import Gf, UsdGeom

    path = output / "engine-research-overview-f0.usda"
    stage, world = _stage(path)
    component_stage = output / "993-engine-components-exploded-f1.usda"
    for name, source, key in (
        ("Engine917", engine, "engine_917"),
        ("ValvetrainResearchRig", rig, "valvetrain_rig"),
        ("EngineComponents", component_stage, "engine_components"),
    ):
        xform = UsdGeom.Xform.Define(stage, f"/World/{name}")
        xform.GetPrim().GetReferences().AddReference(relative_asset_path(path, source))
        xform.AddTranslateOp().Set(Gf.Vec3d(*config["overview_offsets_mm"][key]))
        xform.GetPrim().SetMetadata("kind", "component")
    world.SetCustomDataByKey("3dprinting993:assemblyPurpose", "side-by-side research overview; not one engine")
    world.SetCustomDataByKey("3dprinting993:limitationsJson", json.dumps(config["limitations"]))
    stage.GetRootLayer().Save()
    return path


def build_component_stage(config: dict[str, Any], project_root: Path, output: Path) -> Path:
    from pxr import Gf, UsdGeom

    path = output / "993-engine-components-exploded-f1.usda"
    stage, world = _stage(path)
    group = UsdGeom.Scope.Define(stage, "/World/Components").GetPrim()
    group.SetMetadata("kind", "group")
    for component in config["research_components"]:
        origin = component["origin_mm"]
        step = component["step_mm"]
        for index in range(component["count"]):
            xform = UsdGeom.Xform.Define(stage, f"/World/Components/{component['id']}_{index + 1:02d}")
            prim = xform.GetPrim()
            prim.GetReferences().AddReference(relative_asset_path(path, project_root / component["source"]))
            prim.SetInstanceable(True)
            prim.SetMetadata("kind", "component")
            _set_contract(prim, component["classification"], "exploded_layout_not_measured_engine_position")
            xform.AddTranslateOp().Set(Gf.Vec3d(*(origin[axis] + index * step[axis] for axis in range(3))))
    world.SetCustomDataByKey("3dprinting993:assemblyPurpose", "993 internals and twin K16 exploded research proxies")
    world.SetCustomDataByKey("3dprinting993:limitationsJson", json.dumps(config["limitations"]))
    stage.GetRootLayer().Save()
    return path


def summarize(path: Path) -> dict[str, Any]:
    from pxr import Usd, UsdGeom

    stage = Usd.Stage.Open(str(path), load=Usd.Stage.LoadNone)
    return {
        "path": str(path.resolve()),
        "default_prim": str(stage.GetDefaultPrim().GetPath()) if stage.GetDefaultPrim() else None,
        "meters_per_unit": UsdGeom.GetStageMetersPerUnit(stage),
        "up_axis": UsdGeom.GetStageUpAxis(stage),
        "prim_count_unloaded": sum(1 for _ in stage.Traverse()),
        "used_layers_unloaded": [layer.identifier for layer in stage.GetUsedLayers()],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    project_root = args.project_root.resolve()
    output = args.output.resolve()
    config = load_and_validate_config(args.config.resolve(), project_root)
    output.mkdir(parents=True, exist_ok=True)
    engine = build_engine_stage(config, project_root, output)
    rig = build_valvetrain_stage(config, project_root, output)
    components = build_component_stage(config, project_root, output)
    overview = build_overview_stage(config, output, engine, rig)
    report = {
        "status": "passed",
        "property_assignment_intent": "skip",
        "profile": "F0_research_assembly",
        "stages": [summarize(path) for path in (engine, rig, components, overview)],
        "limitations": config["limitations"],
        "next_step": "validate loaded composition, render, then measure component datums",
    }
    (output / "assembly-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
