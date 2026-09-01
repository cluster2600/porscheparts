#!/usr/bin/env python3
"""Construit un proxy statique F10 avec un représentant par famille.

Ce stage sert uniquement à réduire le travail du Material Agent. Il ne remplace
jamais l'assemblage F10 complet et ne doit pas entrer dans la chaîne Physics.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(layer: Path, asset: Path) -> str:
    return os.path.relpath(asset.resolve(), layer.parent.resolve()).replace(os.sep, "/")


def family_plan(geometry_config: dict[str, Any], detail_config: dict[str, Any]) -> list[dict[str, Any]]:
    geometry = {item["id"]: item for item in geometry_config["component_families"]}
    detail = {item["id"]: item for item in detail_config["families"]}
    overlap = sorted(set(geometry) & set(detail))
    if overlap:
        raise RuntimeError(f"familles F10 présentes dans les deux contrats: {overlap}")
    result = []
    for origin, values in (("geometry", geometry), ("detail", detail)):
        for family, item in sorted(values.items()):
            count = item.get("count")
            if type(count) is not int or count <= 0:
                raise RuntimeError(f"compte de famille invalide: {family}")
            result.append(
                {
                    "family": family,
                    "origin": origin,
                    "full_instance_count": count,
                    "confidence": item.get("confidence"),
                }
            )
    if not result:
        raise RuntimeError("aucune famille F10 à présenter au Material Agent")
    return result


def main() -> int:
    from pxr import Gf, Usd, UsdGeom, UsdPhysics

    parser = argparse.ArgumentParser()
    parser.add_argument("--source-asset", required=True, type=Path)
    parser.add_argument("--geometry-config", required=True, type=Path)
    parser.add_argument("--detail-config", required=True, type=Path)
    parser.add_argument("--variant-assets", required=True, type=Path)
    parser.add_argument("--detail-assets", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()

    source_asset = args.source_asset.resolve(strict=True)
    geometry_config = json.loads(args.geometry_config.read_text(encoding="utf-8"))
    detail_config = json.loads(args.detail_config.read_text(encoding="utf-8"))
    geometry_variant = geometry_config.get("f10_variant", {}).get("variant_id")
    detail_variant = detail_config.get("f10_variant", {}).get("variant_id")
    if not geometry_variant or geometry_variant != detail_variant:
        raise RuntimeError("identité de variante F10 absente ou incohérente")

    source = Usd.Stage.Open(str(source_asset), load=Usd.Stage.LoadAll)
    if not source:
        raise RuntimeError(f"stage F10 illisible: {source_asset}")
    source_world = source.GetDefaultPrim()
    if not source_world or source_world.GetPath() != "/World":
        raise RuntimeError("le stage F10 doit avoir /World comme defaultPrim")
    if source_world.GetCustomDataByKey("3dprinting993:variantId") != geometry_variant:
        raise RuntimeError("le stage et les configurations désignent des variantes différentes")

    plan = family_plan(geometry_config, detail_config)
    expected = {item["family"]: item["full_instance_count"] for item in plan}
    actual: dict[str, list[str]] = {}
    components = source.GetPrimAtPath("/World/Components")
    if not components:
        raise RuntimeError("scope /World/Components absent du stage F10")
    for scope in components.GetChildren():
        for prim in scope.GetChildren():
            family = prim.GetCustomDataByKey("3dprinting993:family")
            if isinstance(family, str):
                actual.setdefault(family, []).append(str(prim.GetPath()))
    if {key: len(value) for key, value in actual.items()} != expected:
        raise RuntimeError(
            "comptage famille/stage différent des configurations: "
            f"stage={{{', '.join(f'{key!r}: {len(value)}' for key, value in sorted(actual.items()))}}} "
            f"config={dict(sorted(expected.items()))}"
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    stage = Usd.Stage.CreateNew(str(args.output.resolve()))
    UsdGeom.SetStageMetersPerUnit(stage, 0.001)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    stage.SetStartTimeCode(0)
    stage.SetEndTimeCode(0)
    stage.SetTimeCodesPerSecond(24)
    stage.SetFramesPerSecond(24)
    world = UsdGeom.Xform.Define(stage, "/World").GetPrim()
    stage.SetDefaultPrim(world)
    world.SetMetadata("kind", "assembly")
    for key in (
        "3dprinting993:architecture",
        "3dprinting993:boreMm",
        "3dprinting993:strokeMm",
        "3dprinting993:documentedDisplacementCm3",
        "3dprinting993:calculatedDisplacementCm3",
        "3dprinting993:fieldEvidenceJson",
        "3dprinting993:sourceIdsJson",
        "3dprinting993:prohibitedUseJson",
        "3dprinting993:variantChangeScopeJson",
    ):
        value = source_world.GetCustomDataByKey(key)
        if value is not None:
            world.SetCustomDataByKey(key, value)
    world.SetCustomDataByKey("3dprinting993:phase", "F10-material-proxy")
    world.SetCustomDataByKey("3dprinting993:variantId", geometry_variant)
    world.SetCustomDataByKey("3dprinting993:propertyAssignmentIntent", "run")
    world.SetCustomDataByKey("3dprinting993:materialProxy", True)
    world.SetCustomDataByKey("3dprinting993:materialProxyMustNotEnterPhysics", True)
    world.SetCustomDataByKey("3dprinting993:manufacturingGeometryReady", False)
    world.SetCustomDataByKey("3dprinting993:physicalKinematicsReady", False)
    components_out = UsdGeom.Scope.Define(stage, "/World/Components").GetPrim()
    components_out.SetMetadata("kind", "group")

    mappings = []
    columns = 7
    spacing_mm = 1000.0
    for index, item in enumerate(plan):
        family = item["family"]
        paths = sorted(actual[family])
        canonical = f"/World/Components/{family}/{family}_01"
        if paths[0] != canonical or canonical not in paths:
            raise RuntimeError(f"représentant canonique absent ou non déterministe: {canonical}")
        asset_root = args.variant_assets if item["origin"] == "geometry" else args.detail_assets
        asset = (asset_root / f"{family}.usdc").resolve(strict=True)
        scope = UsdGeom.Scope.Define(stage, f"/World/Components/{family}").GetPrim()
        scope.SetMetadata("kind", "group")
        xform = UsdGeom.Xform.Define(stage, canonical)
        prim = xform.GetPrim()
        prim.GetReferences().AddReference(relative(args.output, asset))
        prim.SetInstanceable(False)
        prim.SetMetadata("kind", "component")
        prim.SetCustomDataByKey("3dprinting993:family", family)
        prim.SetCustomDataByKey("3dprinting993:assignmentProxyFamily", family)
        prim.SetCustomDataByKey("3dprinting993:confidence", item["confidence"] or "unknown")
        prim.SetCustomDataByKey("3dprinting993:releaseStatus", "research_only")
        prim.SetCustomDataByKey("3dprinting993:variantId", geometry_variant)
        xform.AddTranslateOp().Set(
            Gf.Vec3d((index % columns) * spacing_mm, (index // columns) * spacing_mm, 0.0)
        )
        mappings.append(
            {
                "family": family,
                "origin": item["origin"],
                "representative_prim_path": canonical,
                "full_instance_prim_paths": paths,
                "asset_path": str(asset),
                "asset_sha256": sha256(asset),
            }
        )

    stage.GetRootLayer().Save()
    proxy = Usd.Stage.Open(str(args.output.resolve()), load=Usd.Stage.LoadAll)
    if not proxy:
        raise RuntimeError("le proxy matériel sauvegardé ne se rouvre pas")
    time_sampled = sorted(
        str(attr.GetPath())
        for prim in proxy.TraverseAll()
        for attr in prim.GetAttributes()
        if attr.GetNumTimeSamples() > 0
    )
    instanceable = sorted(str(prim.GetPath()) for prim in proxy.TraverseAll() if prim.IsInstance())
    rigid_bodies = sorted(
        str(prim.GetPath()) for prim in proxy.TraverseAll() if prim.HasAPI(UsdPhysics.RigidBodyAPI)
    )
    physics_scenes = sorted(
        str(prim.GetPath()) for prim in proxy.TraverseAll() if prim.GetTypeName() == "PhysicsScene"
    )
    mesh_count = sum(1 for prim in proxy.TraverseAll() if prim.IsA(UsdGeom.Mesh))
    if time_sampled or instanceable or rigid_bodies or physics_scenes or mesh_count != len(mappings):
        raise RuntimeError(
            "proxy matériel non statique ou non unitaire: "
            f"time_samples={time_sampled} instances={instanceable} rigid_bodies={rigid_bodies} "
            f"physics_scenes={physics_scenes} mesh_count={mesh_count} représentants={len(mappings)}"
        )

    output = args.output.resolve(strict=True)
    report = {
        "schema_version": "1.0.0",
        "status": "passed",
        "passed": True,
        "phase": "f10-material-proxy",
        "variant_id": geometry_variant,
        "source_asset_path": str(source_asset),
        "source_asset_sha256": sha256(source_asset),
        "output_usd_path": str(output),
        "output_paths": [str(output)],
        "output_sha256": sha256(output),
        "claim_scope": "visual_material_assignment_proxy_only",
        "material_proxy_must_not_enter_physics": True,
        "manufacturing_geometry_ready": False,
        "physical_simulation_validated": False,
        "representative_count": len(mappings),
        "renderable_mesh_count": mesh_count,
        "full_instance_count": sum(len(item["full_instance_prim_paths"]) for item in mappings),
        "timeline": {"start_time_code": 0, "end_time_code": 0, "time_sample_count": 0},
        "mappings": mappings,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
