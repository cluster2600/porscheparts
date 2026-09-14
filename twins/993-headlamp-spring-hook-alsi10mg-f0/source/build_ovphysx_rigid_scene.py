#!/usr/bin/env python3
"""Construit une scène USD de chute rigide synthétique sur le crochet F0.

Le crochet importé est un collisionneur statique. Une sphère témoin de 10 g
tombe sur sa surface supérieure. Ce montage contrôle CAD -> USD -> ovstage ->
ovphysx ; il ne représente ni le ressort, ni le phare, ni un essai fonctionnel.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from pxr import Gf, Kind, Usd, UsdGeom, UsdPhysics


PART_ID = "993-ELEC-HEADLAMP-SPRING-HOOK-F0-0001"
TWIN_ID = "TWIN-993-HEADLAMP-SPRING-HOOK-ALSI10MG-F0"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset", type=Path, required=True)
    parser.add_argument("--scene", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    asset = args.asset.resolve()
    scene = args.scene.resolve()
    scene.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)

    source = Usd.Stage.Open(str(asset))
    if source is None:
        raise SystemExit(f"Impossible d'ouvrir l'asset USD: {asset}")
    mesh_path = "/headlamp_spring_hook_f0/COMPOUND/Mesh"
    if not source.GetPrimAtPath(mesh_path).IsA(UsdGeom.Mesh):
        raise SystemExit(f"Maillage attendu absent: {mesh_path}")
    if UsdGeom.GetStageMetersPerUnit(source) != 0.001:
        raise SystemExit("L'asset doit rester en millimètres (metersPerUnit=0.001).")

    stage = Usd.Stage.CreateNew(str(scene))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 0.001)
    stage.SetTimeCodesPerSecond(240.0)
    stage.SetFramesPerSecond(240.0)
    world = UsdGeom.Xform.Define(stage, "/World")
    Usd.ModelAPI(world.GetPrim()).SetKind(Kind.Tokens.assembly)
    stage.SetDefaultPrim(world.GetPrim())

    physics_scene = UsdPhysics.Scene.Define(stage, "/World/PhysicsScene")
    physics_scene.CreateGravityDirectionAttr(Gf.Vec3f(0.0, 0.0, -1.0))
    physics_scene.CreateGravityMagnitudeAttr(9810.0)

    hook = UsdGeom.Xform.Define(stage, "/World/Hook")
    relative_asset = os.path.relpath(asset, scene.parent)
    hook.GetPrim().GetReferences().AddReference(relative_asset)
    hook_mesh = stage.OverridePrim("/World/Hook/COMPOUND/Mesh")
    UsdPhysics.CollisionAPI.Apply(hook_mesh)
    UsdPhysics.MeshCollisionAPI.Apply(hook_mesh).CreateApproximationAttr("none")

    witness = UsdGeom.Sphere.Define(stage, "/World/WitnessSphere")
    witness.CreateRadiusAttr(2.0)
    witness.AddTranslateOp().Set(Gf.Vec3d(8.0, 0.0, 22.0))
    UsdPhysics.CollisionAPI.Apply(witness.GetPrim())
    UsdPhysics.RigidBodyAPI.Apply(witness.GetPrim())
    mass = UsdPhysics.MassAPI.Apply(witness.GetPrim())
    mass.CreateMassAttr(0.010)

    guard = UsdGeom.Cube.Define(stage, "/World/FallGuard")
    guard.CreateSizeAttr(2.0)
    guard.AddTranslateOp().Set(Gf.Vec3d(8.0, 0.0, -3.0))
    guard.AddScaleOp().Set(Gf.Vec3f(20.0, 10.0, 1.0))
    UsdPhysics.CollisionAPI.Apply(guard.GetPrim())

    stage.GetRootLayer().customLayerData = {
        "authority": "synthetic software-integration screen only",
        "part_id": PART_ID,
        "twin_id": TWIN_ID,
        "release_authorized": False,
    }
    stage.GetRootLayer().Save()

    report = {
        "schema_version": "1.0.0",
        "part_id": PART_ID,
        "twin_id": TWIN_ID,
        "status": "scene_authored",
        "tool": {"name": "OpenUSD Python", "usd_version": list(Usd.GetVersion())},
        "asset": {
            "path": asset.name,
            "sha256": sha256(asset),
            "source_mesh_prim": mesh_path,
            "meters_per_unit": UsdGeom.GetStageMetersPerUnit(source),
        },
        "scene": {
            "path": scene.name,
            "sha256": sha256(scene),
            "up_axis": "Z",
            "meters_per_unit": 0.001,
            "static_hook_collider": "/World/Hook/COMPOUND/Mesh",
            "dynamic_witness": "/World/WitnessSphere",
            "fall_guard": "/World/FallGuard",
        },
        "synthetic_case": {
            "gravity_mm_s2": 9810.0,
            "witness_mass_kg": 0.010,
            "witness_radius_mm": 2.0,
            "initial_position_mm": [8.0, 0.0, 22.0],
        },
        "interpretation": "Test de branchement rigide seulement; aucune charge ou interface du phare n'est modélisée.",
        "engineering_validation": False,
        "manufacturing_release_authorized": False,
    }
    args.report.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
