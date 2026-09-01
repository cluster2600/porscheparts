#!/usr/bin/env python3
"""Propage les matériaux du proxy F10 vers l'assemblage complet, sans géométrie.

Le raccordement est volontairement fermé : chaque famille doit fournir un et
un seul matériau effectif et chaque instance complète doit être attestée par le
rapport du proxy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from pxr import Sdf, Usd, UsdGeom, UsdShade


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(layer: Path, asset: Path) -> str:
    return os.path.relpath(asset.resolve(), layer.parent.resolve()).replace(os.sep, "/")


def load_report(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"rapport JSON objet attendu: {path}")
    return payload


def bound_material_paths(stage: Usd.Stage, root_path: str) -> list[str]:
    root = stage.GetPrimAtPath(root_path)
    if not root:
        raise RuntimeError(f"représentant absent de la sortie Material Agent: {root_path}")
    paths: set[str] = set()
    mesh_count = 0
    for prim in Usd.PrimRange(root):
        if not prim.IsA(UsdGeom.Mesh):
            continue
        mesh_count += 1
        material, _ = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()
        if material and material.GetPrim():
            paths.add(str(material.GetPath()))
    if mesh_count == 0:
        raise RuntimeError(f"aucun mesh traversable pour la famille: {root_path}")
    return sorted(paths)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-asset", required=True, type=Path)
    parser.add_argument("--proxy-report", required=True, type=Path)
    parser.add_argument("--material-usd", required=True, type=Path)
    parser.add_argument("--material-report", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()

    source_asset = args.source_asset.resolve(strict=True)
    proxy_report_path = args.proxy_report.resolve(strict=True)
    material_usd = args.material_usd.resolve(strict=True)
    material_report_path = args.material_report.resolve(strict=True)
    proxy_report = load_report(proxy_report_path)
    material_report = load_report(material_report_path)
    if (
        proxy_report.get("schema_version") != "1.0.0"
        or proxy_report.get("status") != "passed"
        or proxy_report.get("passed") is not True
        or proxy_report.get("claim_scope") != "visual_material_assignment_proxy_only"
        or proxy_report.get("material_proxy_must_not_enter_physics") is not True
    ):
        raise RuntimeError("rapport de proxy matériel non validé")
    if Path(str(proxy_report.get("source_asset_path", ""))).resolve() != source_asset:
        raise RuntimeError("le proxy matériel provient d'un autre assemblage F10")
    if proxy_report.get("source_asset_sha256") != sha256(source_asset):
        raise RuntimeError("le stage F10 a changé depuis la construction du proxy")
    proxy_path = Path(str(proxy_report.get("output_usd_path", ""))).resolve(strict=True)
    if proxy_report.get("output_paths") != [str(proxy_path)]:
        raise RuntimeError("sortie du rapport de proxy absente ou ambiguë")
    if proxy_report.get("output_sha256") != sha256(proxy_path):
        raise RuntimeError("le proxy matériel a changé depuis son attestation")
    if (
        material_report.get("passed") is not True
        or str(material_report.get("status", "")).lower() not in {"pass", "passed", "ready"}
        or Path(str(material_report.get("asset_path", ""))).resolve() != proxy_path
        or Path(str(material_report.get("output_usd_path", ""))).resolve() != material_usd
    ):
        raise RuntimeError("rapport Material Agent non validé ou rattaché à un autre proxy")

    source = Usd.Stage.Open(str(source_asset), load=Usd.Stage.LoadAll)
    material_stage = Usd.Stage.Open(str(material_usd), load=Usd.Stage.LoadAll)
    if not source or not material_stage:
        raise RuntimeError("stage F10 ou sortie Material Agent illisible")
    mappings = proxy_report.get("mappings")
    if not isinstance(mappings, list) or len(mappings) != proxy_report.get("representative_count"):
        raise RuntimeError("mapping famille/proxy absent ou incomplet")
    families = [item.get("family") for item in mappings if isinstance(item, dict)]
    if len(families) != len(mappings) or any(not isinstance(value, str) for value in families):
        raise RuntimeError("identifiant de famille invalide dans le mapping")
    if len(set(families)) != len(families):
        raise RuntimeError("famille dupliquée dans le mapping matériel")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    layer = Sdf.Layer.CreateNew(str(args.output.resolve()))
    layer.subLayerPaths.append(relative(args.output, source_asset))
    stage = Usd.Stage.Open(layer, load=Usd.Stage.LoadAll)
    stage.SetEditTarget(layer)
    source_default = source.GetDefaultPrim()
    if source_default:
        stage.SetDefaultPrim(stage.GetPrimAtPath(source_default.GetPath()))
    UsdGeom.SetStageMetersPerUnit(stage, UsdGeom.GetStageMetersPerUnit(source))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.GetStageUpAxis(source))
    stage.SetStartTimeCode(source.GetStartTimeCode())
    stage.SetEndTimeCode(source.GetEndTimeCode())
    stage.SetTimeCodesPerSecond(source.GetTimeCodesPerSecond())
    stage.SetFramesPerSecond(source.GetFramesPerSecond())
    looks = UsdGeom.Scope.Define(stage, "/World/Looks/MaterialAgent").GetPrim()
    looks.SetMetadata("kind", "group")

    bindings = []
    bound_instance_paths: set[str] = set()
    for item in sorted(mappings, key=lambda value: value["family"]):
        family = item["family"]
        representative_path = item.get("representative_prim_path")
        full_paths = item.get("full_instance_prim_paths")
        if not isinstance(representative_path, str) or not isinstance(full_paths, list) or not full_paths:
            raise RuntimeError(f"mapping incomplet pour la famille: {family}")
        material_paths = bound_material_paths(material_stage, representative_path)
        if len(material_paths) != 1:
            raise RuntimeError(
                f"la famille {family} doit avoir exactement un matériau effectif, obtenu={material_paths}"
            )
        source_material_path = material_paths[0]
        target_path = f"/World/Looks/MaterialAgent/{family}"
        target = UsdShade.Material.Define(stage, target_path)
        target.GetPrim().GetReferences().AddReference(
            relative(args.output, material_usd), Sdf.Path(source_material_path)
        )
        family_bindings = []
        for prim_path in full_paths:
            if not isinstance(prim_path, str) or prim_path in bound_instance_paths:
                raise RuntimeError(f"instance absente, invalide ou dupliquée: {prim_path}")
            prim = stage.GetPrimAtPath(prim_path)
            if not prim:
                raise RuntimeError(f"instance F10 absente pendant le raccordement: {prim_path}")
            if prim.GetCustomDataByKey("3dprinting993:family") != family:
                raise RuntimeError(f"instance rattachée à la mauvaise famille: {prim_path}")
            binding = UsdShade.MaterialBindingAPI.Apply(prim)
            if not binding.Bind(target, UsdShade.Tokens.strongerThanDescendants):
                raise RuntimeError(f"échec du binding matériel: {prim_path}")
            family_bindings.append(prim_path)
            bound_instance_paths.add(prim_path)
        bindings.append(
            {
                "family": family,
                "representative_prim_path": representative_path,
                "source_material_path": source_material_path,
                "target_material_path": target_path,
                "bound_instance_prim_paths": family_bindings,
            }
        )

    expected_full_count = proxy_report.get("full_instance_count")
    if type(expected_full_count) is not int or len(bound_instance_paths) != expected_full_count:
        raise RuntimeError("le raccordement ne couvre pas toutes les instances attestées")
    world = stage.GetPrimAtPath("/World")
    world.SetCustomDataByKey("3dprinting993:materialAssignmentStatus", "family_proxy_propagated")
    world.SetCustomDataByKey("3dprinting993:materialAssignmentProxyPath", str(proxy_path))
    world.SetCustomDataByKey("3dprinting993:materialAssignmentPhysicalValidation", False)
    stage.GetRootLayer().Save()

    output = args.output.resolve(strict=True)
    verification = Usd.Stage.Open(str(output), load=Usd.Stage.LoadAll)
    if not verification:
        raise RuntimeError("stage F10 matérialisé illisible après sauvegarde")
    if (
        verification.GetStartTimeCode() != source.GetStartTimeCode()
        or verification.GetEndTimeCode() != source.GetEndTimeCode()
    ):
        raise RuntimeError("la timeline F10 a changé pendant le raccordement")
    for item in bindings:
        expected_material = item["target_material_path"]
        for prim_path in item["bound_instance_prim_paths"]:
            material, relationship = UsdShade.MaterialBindingAPI(
                verification.GetPrimAtPath(prim_path)
            ).ComputeBoundMaterial()
            if not material or str(material.GetPath()) != expected_material or not relationship:
                raise RuntimeError(f"binding effectif différent du plan: {prim_path}")

    report = {
        "schema_version": "1.0.0",
        "status": "passed",
        "passed": True,
        "phase": "f10-family-material-propagation",
        "claim_scope": "visual_material_bindings_only",
        "source_asset_path": str(source_asset),
        "source_asset_sha256": sha256(source_asset),
        "proxy_report_path": str(proxy_report_path),
        "proxy_asset_path": str(proxy_path),
        "proxy_asset_sha256": sha256(proxy_path),
        "material_report_path": str(material_report_path),
        "material_usd_path": str(material_usd),
        "material_usd_sha256": sha256(material_usd),
        "output_usd_path": str(output),
        "output_paths": [str(output)],
        "output_sha256": sha256(output),
        "family_count": len(bindings),
        "bound_instance_count": len(bound_instance_paths),
        "timeline": {
            "start_time_code": verification.GetStartTimeCode(),
            "end_time_code": verification.GetEndTimeCode(),
        },
        "bindings": bindings,
        "manufacturing_geometry_ready": False,
        "physical_simulation_validated": False,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
