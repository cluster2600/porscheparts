#!/usr/bin/env python3
"""Retire les proprietes non sourcees d'un USD Content Agents."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-usd", required=True, type=Path)
    parser.add_argument("--output-usd", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--mass-kg", required=True, type=float)
    parser.add_argument("--density-kg-m3", required=True, type=float)
    args = parser.parse_args()

    from pxr import Sdf, Usd, UsdPhysics, UsdShade

    source = args.input_usd.resolve()
    output = args.output_usd.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, output)
    stage = Usd.Stage.Open(str(output), load=Usd.Stage.LoadAll)
    if stage is None or not stage.GetDefaultPrim():
        raise RuntimeError("input_usd_invalid")

    root = stage.GetDefaultPrim()
    old_visual = Sdf.Path(f"{root.GetPath()}/Looks/Stainless_Steel_Polished")
    visual = Sdf.Path(f"{root.GetPath()}/Looks/IN625_Visual_Proxy")
    if stage.GetPrimAtPath(old_visual):
        if stage.GetPrimAtPath(visual):
            stage.RemovePrim(visual)
        if not Sdf.CopySpec(stage.GetRootLayer(), old_visual, stage.GetRootLayer(), visual):
            raise RuntimeError("visual_material_copy_failed")
        for prim in stage.TraverseAll():
            for relationship in prim.GetRelationships():
                targets = relationship.GetTargets()
                replaced = [
                    visual.AppendPath(target.MakeRelativePath(old_visual))
                    if target.HasPrefix(old_visual)
                    else target
                    for target in targets
                ]
                if replaced != targets:
                    relationship.SetTargets(replaced)
        stage.RemovePrim(old_visual)

    visual_prim = stage.GetPrimAtPath(visual)
    if not visual_prim:
        raise RuntimeError("visual_material_missing")
    visual_prim.SetDisplayName("IN625 visual proxy - non calibrated")
    for name in (
        "omni:simready:nonvisual:attributes",
        "omni:simready:nonvisual:base",
        "omni:simready:nonvisual:coating",
    ):
        visual_prim.RemoveProperty(name)
    labels = visual_prim.GetAttribute("semantics:labels:material")
    if labels:
        labels.Set(["metal", "nickel", "alloy", "gray", "smooth", "reflective"])
    roughness = visual_prim.GetAttribute("inputs:specular_roughness")
    if roughness:
        roughness.Set(0.22)

    removed_prims: list[str] = []
    for suffix in ("PhysicsScene", "Looks/PhysMat_sf0_50_df0_75_r0_30"):
        path = Sdf.Path(f"{root.GetPath()}/{suffix}")
        if stage.GetPrimAtPath(path):
            stage.RemovePrim(path)
            removed_prims.append(str(path))

    for prim in stage.TraverseAll():
        binding = prim.GetRelationship("material:binding:physics")
        if binding:
            prim.RemoveProperty("material:binding:physics")

    rigid = UsdPhysics.RigidBodyAPI.Apply(root)
    rigid.CreateRigidBodyEnabledAttr(True)
    mass = UsdPhysics.MassAPI.Apply(root)
    mass.CreateMassAttr(args.mass_kg)
    mass.CreateDensityAttr(0.0)

    physics_material_path = Sdf.Path(f"{root.GetPath()}/Looks/IN625_Screening_Physics")
    physics_material = UsdShade.Material.Define(stage, physics_material_path)
    physical = UsdPhysics.MaterialAPI.Apply(physics_material.GetPrim())
    physical.CreateDensityAttr(args.density_kg_m3)
    physics_material.GetPrim().SetCustomData(
        {
            "classification": "density_only_screening_material",
            "frictionKnown": False,
            "restitutionKnown": False,
        }
    )

    collision_meshes = []
    for prim in stage.TraverseAll():
        if prim.HasAPI(UsdPhysics.CollisionAPI):
            collision_meshes.append(str(prim.GetPath()))
            mesh_mass = UsdPhysics.MassAPI.Apply(prim)
            mesh_mass.CreateDensityAttr(args.density_kg_m3)
            mesh_mass.CreateMassAttr(0.0)
            prim.CreateRelationship("material:binding:physics").SetTargets(
                [physics_material_path]
            )

    root.SetCustomData(
        {
            "classification": "isolated_simready_inspection_prop_not_installed_exhaust",
            "materialCandidate": "EOS NickelAlloy IN625 screening candidate",
            "massBasis": "analytic CAD volume times screening density",
            "metalPrintAuthorized": False,
            "vehicleInstallationAuthorized": False,
        }
    )
    stage.GetRootLayer().documentation = (
        "Asset SimReady isole. La masse et la densite sont des valeurs de criblage; "
        "aucun contact, appui, frottement, restitution, gravite ou chargement thermique "
        "installe n'est source."
    )
    stage.GetRootLayer().Save()

    forbidden = []
    reopened = Usd.Stage.Open(str(output), load=Usd.Stage.LoadAll)
    for prim in reopened.TraverseAll():
        if prim.IsA(UsdPhysics.Scene):
            forbidden.append(f"physics_scene:{prim.GetPath()}")
        for name in ("physics:staticFriction", "physics:dynamicFriction", "physics:restitution"):
            attribute = prim.GetAttribute(name)
            if attribute and attribute.HasAuthoredValueOpinion():
                forbidden.append(f"{name}:{prim.GetPath()}")
    if forbidden:
        raise RuntimeError(f"unverified_properties_remain:{forbidden}")

    report = {
        "schema_version": "1.0.0",
        "classification": "content_agents_output_sanitized_against_source_contract",
        "input_usd_sha256": sha256(source),
        "output_usd_sha256": sha256(output),
        "default_prim": str(reopened.GetDefaultPrim().GetPath()),
        "mass_kg": args.mass_kg,
        "density_kg_m3": args.density_kg_m3,
        "collision_meshes": collision_meshes,
        "visual_material": str(visual),
        "physics_material": str(physics_material_path),
        "physics_material_properties": {
            "density_kg_m3": args.density_kg_m3,
            "static_friction": None,
            "dynamic_friction": None,
            "restitution": None,
        },
        "removed_unverified_prims": removed_prims,
        "removed_unverified_properties": [
            "physics material binding",
            "static and dynamic friction",
            "restitution",
            "gravity scene",
            "stainless-steel semantic identity",
        ],
        "remaining_forbidden_properties": forbidden,
        "gates": {
            "agent_output_accepted_without_review": False,
            "source_contract_sanitized": True,
            "manufacturing_authorized": False,
            "vehicle_installation_authorized": False,
        },
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
