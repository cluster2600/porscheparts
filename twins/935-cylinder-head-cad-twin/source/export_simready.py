#!/usr/bin/env python3
"""Package the CAD-body stage as a simulation-ready OpenUSD asset.

The stage written by ``export_usd.py`` is geometry with evidence colours. A
physics or rendering application also expects a collider, a bound material
and one file to load. This script adds them without touching the geometry:

    part.usda       root layer, text: stage metadata, the display material and
                    its bindings, the collision schemas; it sublayers the two
                    binary layers below
    geometry.usdc   the CAD-body stage, copied byte for byte
    collider.usdc   a coarser closed surface of the same body, for collision
    part.usdz       the three layers in one package

Hierarchy under the default prim ``/Head935`` (millimetres, Z-up):

    BareHead                 render mesh, bound to Looks/EvidenceDisplay
    Hardware/Stud_NN         the fitted studs
    Datums                   frame and datums as customData
    Collision/BareHead       guide-purpose mesh with UsdPhysics collision
    Looks/EvidenceDisplay    UsdPreviewSurface reading the evidence colours

What is deliberately not authored: no mass, density or rigid body, because the
alloy is unknown, and no physical material. The display material shows the
observed and inferred classes; it is not a material of the part. The asset is
a study twin and inherits every limit of the body it packages.

Usage: export_simready.py CAD_STAGE.usdc COLLIDER.stl OUT_DIR SUMMARY.json
OUT_DIR must be a new private (git-ignored) directory.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

import numpy as np

ROOT = "/Head935"
SCHEMA = "935-cad-twin-simready-asset/1"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def signed_volume(v: np.ndarray, f: np.ndarray) -> float:
    t = v[f].astype(np.float64)
    return float(np.einsum("ij,ij->i", t[:, 0], np.cross(t[:, 1], t[:, 2])).sum() / 6.0)


def write_collider(path: Path, v: np.ndarray, f: np.ndarray) -> None:
    """A layer holding only the collider mesh, as overs up to the default prim."""

    from pxr import Gf, Usd, UsdGeom, Vt

    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 0.001)
    stage.OverridePrim(ROOT)
    UsdGeom.Scope.Define(stage, f"{ROOT}/Collision")
    m = UsdGeom.Mesh.Define(stage, f"{ROOT}/Collision/BareHead")
    m.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(v.astype(np.float32)))
    m.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(len(f), 3, dtype=np.int32)))
    m.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(f.astype(np.int32).ravel()))
    m.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    m.CreateExtentAttr([Gf.Vec3f(*v.min(axis=0)), Gf.Vec3f(*v.max(axis=0))])
    t = v[f]
    cross = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    norm = np.linalg.norm(cross, axis=1)
    flat = norm < 1.0e-12
    normals = np.where(flat[:, None], np.array([0.0, 0.0, 1.0]), cross / np.where(flat, 1.0, norm)[:, None])
    m.CreateNormalsAttr(Vt.Vec3fArray.FromNumpy(normals.astype(np.float32)))
    m.SetNormalsInterpolation(UsdGeom.Tokens.uniform)
    # A collider is not drawn: the render mesh is BareHead.
    m.CreatePurposeAttr(UsdGeom.Tokens.guide)
    stage.GetRootLayer().Save()


def write_root(path: Path, source_customdata: dict) -> None:
    """The text root layer: metadata, material, bindings and collision schemas."""

    from pxr import Sdf, Usd, UsdGeom, UsdPhysics, UsdShade

    stage = Usd.Stage.CreateNew(str(path))
    stage.GetRootLayer().subLayerPaths = ["./collider.usdc", "./geometry.usdc"]
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 0.001)
    UsdPhysics.SetStageKilogramsPerUnit(stage, 1.0)
    root = stage.GetPrimAtPath(ROOT)
    stage.SetDefaultPrim(root)
    for key, value in source_customdata.items():
        root.SetCustomDataByKey(key, value)

    UsdGeom.Scope.Define(stage, f"{ROOT}/Looks")
    material = UsdShade.Material.Define(stage, f"{ROOT}/Looks/EvidenceDisplay")
    material.GetPrim().SetCustomDataByKey(
        "porscheparts:claims", "display only: shows observed and inferred surface classes; not a material of the part")
    reader = UsdShade.Shader.Define(stage, f"{ROOT}/Looks/EvidenceDisplay/EvidenceColour")
    reader.CreateIdAttr("UsdPrimvarReader_float3")
    reader.CreateInput("varname", Sdf.ValueTypeNames.String).Set("displayColor")
    reader.CreateInput("fallback", Sdf.ValueTypeNames.Float3).Set((0.72, 0.72, 0.74))
    surface = UsdShade.Shader.Define(stage, f"{ROOT}/Looks/EvidenceDisplay/Surface")
    surface.CreateIdAttr("UsdPreviewSurface")
    surface.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(
        reader.CreateOutput("result", Sdf.ValueTypeNames.Float3))
    surface.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.6)
    surface.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
    material.CreateSurfaceOutput().ConnectToSource(surface.CreateOutput("surface", Sdf.ValueTypeNames.Token))
    for prim in Usd.PrimRange(root):
        if prim.IsA(UsdGeom.Gprim) and UsdGeom.Imageable(prim).ComputePurpose() != UsdGeom.Tokens.guide:
            UsdShade.MaterialBindingAPI.Apply(prim).Bind(material)

    collider = stage.GetPrimAtPath(f"{ROOT}/Collision/BareHead")
    UsdPhysics.CollisionAPI.Apply(collider)
    # A finned body is far from convex: ask the physics engine for a convex decomposition.
    UsdPhysics.MeshCollisionAPI.Apply(collider).CreateApproximationAttr(UsdPhysics.Tokens.convexDecomposition)
    stage.GetRootLayer().Save()


def findings(stage) -> dict:
    """Every registered OpenUSD validator on a stage, counted by severity."""

    from pxr import UsdValidation

    validators = UsdValidation.ValidationRegistry().GetOrLoadAllValidators()
    by_type: dict = {}
    for error in UsdValidation.ValidationContext(validators).Validate(stage):
        by_type.setdefault(str(error.GetType()).split(".")[-1], []).append(error.GetName())
    return {"validators_run": len(validators),
            "findings_by_type": {k: sorted(set(v))[:20] for k, v in by_type.items()},
            "error_count": len(by_type.get("Error", []))}


def describe(stage) -> dict:
    """What a consumer finds in a stage, read back through composition."""

    from pxr import Usd, UsdGeom, UsdPhysics, UsdShade

    root = stage.GetDefaultPrim()
    render = UsdGeom.Mesh(stage.GetPrimAtPath(f"{ROOT}/BareHead"))
    collider = stage.GetPrimAtPath(f"{ROOT}/Collision/BareHead")
    cv = np.asarray(UsdGeom.Mesh(collider).GetPointsAttr().Get(), dtype=np.float64)
    cf = np.asarray(UsdGeom.Mesh(collider).GetFaceVertexIndicesAttr().Get()).reshape(-1, 3)
    bound = [str(p.GetPath()) for p in Usd.PrimRange(root, Usd.TraverseInstanceProxies())
             if p.IsA(UsdGeom.Gprim) and UsdShade.MaterialBindingAPI(p).ComputeBoundMaterial()[0]]
    extent = render.GetExtentAttr().Get()
    return {
        "default_prim": str(root.GetPath()),
        "kind": Usd.ModelAPI(root).GetKind(),
        "up_axis": str(UsdGeom.GetStageUpAxis(stage)),
        "meters_per_unit": UsdGeom.GetStageMetersPerUnit(stage),
        "kilograms_per_unit": UsdPhysics.GetStageKilogramsPerUnit(stage),
        "render_triangles": len(render.GetFaceVertexCountsAttr().Get()),
        "render_normals": str(render.GetNormalsInterpolation()),
        "render_extent_mm": [[round(float(x), 3) for x in corner] for corner in extent],
        "gprims_with_bound_material": len(bound),
        "collider_triangles": int(len(cf)),
        "collider_volume_mm3": round(signed_volume(cv, cf), 1),
        "collider_purpose": str(UsdGeom.Imageable(collider).ComputePurpose()),
        "collider_has_collision_api": collider.HasAPI(UsdPhysics.CollisionAPI),
        "collider_approximation": str(UsdPhysics.MeshCollisionAPI(collider).GetApproximationAttr().Get()),
        "rigid_body_or_mass_authored": any(p.HasAPI(UsdPhysics.RigidBodyAPI) or p.HasAPI(UsdPhysics.MassAPI)
                                           for p in Usd.PrimRange(root)),
    }


def main(cad_stage, collider_stl, out_dir, summary) -> None:
    import trimesh
    from pxr import Usd, UsdUtils

    cad_stage, collider_stl, out_dir = Path(cad_stage), Path(collider_stl), Path(out_dir)
    if out_dir.exists():
        raise SystemExit(f"{out_dir} exists: give a new private directory")
    out_dir.mkdir(parents=True)
    shutil.copyfile(cad_stage, out_dir / "geometry.usdc")

    mesh = trimesh.load(collider_stl, process=False, force="mesh")
    mesh.merge_vertices()
    if not (mesh.is_watertight and mesh.is_winding_consistent):
        raise SystemExit("collider surface is not a closed, consistently wound solid")
    v, f = np.asarray(mesh.vertices), np.asarray(mesh.faces)
    write_collider(out_dir / "collider.usdc", v, f)

    source = Usd.Stage.Open(str(cad_stage))
    custom = dict(source.GetDefaultPrim().GetCustomData())
    render_volume = None
    write_root(out_dir / "part.usda", custom)

    stage = Usd.Stage.Open(str(out_dir / "part.usda"))
    layers = describe(stage)
    layer_findings = findings(stage)
    if not UsdUtils.CreateNewUsdzPackage(str(out_dir / "part.usda"), str(out_dir / "part.usdz")):
        raise SystemExit("usdz packaging failed")
    package = Usd.Stage.Open(str(out_dir / "part.usdz"))
    packaged = describe(package)

    rv = np.asarray(source.GetPrimAtPath(f"{ROOT}/BareHead").GetAttribute("points").Get(), dtype=np.float64)
    rf = np.asarray(source.GetPrimAtPath(f"{ROOT}/BareHead").GetAttribute("faceVertexIndices").Get()).reshape(-1, 3)
    render_volume = signed_volume(rv, rf)
    Path(summary).write_text(json.dumps({
        "schema": SCHEMA,
        "usd_version": ".".join(str(x) for x in Usd.GetVersion()),
        "source_stage_sha256": sha256(cad_stage),
        "geometry_layer_is_source_stage": sha256(out_dir / "geometry.usdc") == sha256(cad_stage),
        "collider_source": collider_stl.name,
        "collider_source_sha256": sha256(collider_stl),
        "collider_volume_over_render_volume": round(layers["collider_volume_mm3"] / render_volume, 5),
        "files": {name: {"bytes": (out_dir / name).stat().st_size, "sha256": sha256(out_dir / name)}
                  for name in ("part.usda", "geometry.usdc", "collider.usdc", "part.usdz")},
        "stage": layers,
        "package_reads_back_identically": packaged == layers,
        "openusd_validation": {"part.usda": layer_findings, "part.usdz": findings(package)},
        "not_authored": ["mass, density or rigid body: the alloy is unknown",
                         "a physical material: the bound material only displays the evidence classes"],
        "claims": "a well-formed study asset; no physics was run on it, and it inherits every limit of the v2 body",
    }, indent=2) + "\n")


if __name__ == "__main__":
    main(*sys.argv[1:5])
