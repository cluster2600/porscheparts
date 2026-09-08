#!/usr/bin/env python3
"""Compose les deux USD F0 sans ajouter de propriétés physiques non justifiées."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative_asset_path(layer: Path, asset: Path) -> str:
    return Path(os.path.relpath(asset.resolve(), layer.resolve().parent)).as_posix()


def _bounds(Usd: Any, UsdGeom: Any, stage: Any) -> dict[str, list[float]]:
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_])
    aligned = cache.ComputeWorldBound(stage.GetDefaultPrim()).ComputeAlignedRange()
    minimum = [float(value) for value in aligned.GetMin()]
    maximum = [float(value) for value in aligned.GetMax()]
    return {
        "min": minimum,
        "max": maximum,
        "size": [high - low for low, high in zip(minimum, maximum)],
    }


def build_assembly(housing: Path, impeller: Path, output: Path) -> dict[str, Any]:
    from pxr import Kind, Usd, UsdGeom, UsdPhysics

    housing = housing.resolve()
    impeller = impeller.resolve()
    output = output.resolve()
    for source in (housing, impeller):
        if not source.is_file():
            raise FileNotFoundError(source)

    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Usd.Stage.CreateNew(str(output))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 0.001)
    root = UsdGeom.Xform.Define(stage, "/EngineCoolingFanSystemF0").GetPrim()
    stage.SetDefaultPrim(root)
    root.SetMetadata("kind", Kind.Tokens.assembly)
    root.SetCustomData(
        {
            "digitalTwinId": "TWIN-993-ENGINE-COOLING-FAN-SYSTEM-F0",
            "fidelity": "F1_envelope",
            "integrationStatus": "failed_clearance",
            "coldRadialClearanceMm": -14.0,
            "hotRadialClearanceMm": -14.03822,
            "alignmentAuthority": "synthetic_coaxial_shared_front_plane",
            "manufacturingAuthorized": False,
            "engineOperationAuthorized": False,
            "releaseAuthorized": False,
        }
    )

    components = (
        ("FanHousingF0", housing, "host_stationary"),
        ("CoolingImpellerF0", impeller, "candidate_rotating_not_authorized"),
    )
    for name, source, role in components:
        prim = UsdGeom.Xform.Define(stage, f"/EngineCoolingFanSystemF0/{name}").GetPrim()
        prim.SetMetadata("kind", Kind.Tokens.component)
        prim.SetCustomData({"role": role, "sourceSha256": _sha256(source)})
        prim.GetReferences().AddReference(relative_asset_path(output, source))

    stage.GetRootLayer().documentation = (
        "Assemblage F0 synthétique en échec de jeu. Aucun PhysX, aucune attribution "
        "matériau SimReady et aucune autorisation de fabrication ou de rotation."
    )
    stage.GetRootLayer().Save()

    reopened = Usd.Stage.Open(str(output), Usd.Stage.LoadAll)
    if reopened is None:
        raise RuntimeError("the authored assembly cannot be reopened")
    prims = list(reopened.TraverseAll())
    default_prim = reopened.GetDefaultPrim()
    mesh_count = sum(1 for prim in prims if prim.IsA(UsdGeom.Mesh))
    rigid_body_count = sum(1 for prim in prims if prim.HasAPI(UsdPhysics.RigidBodyAPI))
    collider_count = sum(1 for prim in prims if prim.HasAPI(UsdPhysics.CollisionAPI))
    joint_count = sum(1 for prim in prims if prim.IsA(UsdPhysics.Joint))
    report = {
        "schema_version": "1.0.0",
        "status": "passed_minimum_composition_not_simready",
        "output_usd": str(output),
        "output_sha256": _sha256(output),
        "default_prim_path": str(default_prim.GetPath()) if default_prim else None,
        "up_axis": str(UsdGeom.GetStageUpAxis(reopened)),
        "meters_per_unit": float(UsdGeom.GetStageMetersPerUnit(reopened)),
        "authored_reference_count": len(components),
        "mesh_count": mesh_count,
        "bounds_stage_units": _bounds(Usd, UsdGeom, reopened),
        "rigid_body_count": rigid_body_count,
        "collider_count": collider_count,
        "joint_count": joint_count,
        "property_assignment_status": "skipped",
        "simready_claimed": False,
        "simulation_validated": False,
        "manufacturing_authorized": False,
        "engine_operation_authorized": False,
        "release_authorized": False,
    }
    if not default_prim or str(default_prim.GetPath()) != "/EngineCoolingFanSystemF0":
        raise RuntimeError("unexpected default prim")
    if mesh_count < 2:
        raise RuntimeError("the composed assembly does not expose both component meshes")
    if any((rigid_body_count, collider_count, joint_count)):
        raise RuntimeError("unreviewed physics schemas were authored")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--housing", type=Path, required=True)
    parser.add_argument("--impeller", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = build_assembly(args.housing, args.impeller, args.output)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
