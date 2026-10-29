#!/usr/bin/env python3
"""Compose the retained 964 study geometry into a portable OpenUSD review bundle."""
import argparse
import hashlib
import json
import math
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdRender, UsdShade, UsdUtils, Vt

HERE = Path(__file__).resolve().parent
MONOCOQUE = HERE.parent
GROUPS = ("OuterSkin", "ClosedSections", "SandwichPanels", "WheelTubs")
COLOURS = ((.54, .57, .62), (.94, .48, .25), (.31, .60, .66), (.91, .71, .30))
FLAGS = ("manufacturingAuthorized", "strengthValidated", "fitment964Validated", "fitment993Validated")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def new_stage(path):
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, .001)
    root = UsdGeom.Xform.Define(stage, "/Monocoque").GetPrim()
    stage.SetDefaultPrim(root)
    root.SetCustomData({"classification": "prohibited_pending_engineering",
                        "fidelity": "documentary_design_envelope", **dict.fromkeys(FLAGS, False)})
    return stage


def checked_arrays(points, faces):
    points, faces = np.asarray(points), np.asarray(faces)
    if points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all():
        raise ValueError("Finite XYZ points required")
    if faces.ndim != 2 or faces.shape[1] != 3 or not np.issubdtype(faces.dtype, np.integer):
        raise ValueError("Integer triangle indices required")
    if not len(faces) or faces.min() < 0 or faces.max() >= len(points):
        raise ValueError("Triangle indices outside the point array")
    return points.astype(np.float32), faces.astype(np.int32)


def author_geometry(output):
    import pyvista as pv
    source = MONOCOQUE / "derived/zesad-monocoque.vtp"
    surface = pv.read(source)
    if not surface.is_all_triangles or set(np.unique(surface.cell_data["group"])) != set(range(4)):
        raise ValueError("Expected the four retained triangular display groups")
    points, faces = checked_arrays(surface.points, surface.faces.reshape(-1, 4)[:, 1:])
    stage = new_stage(output / "geometry.usdc")
    counts = {}
    for i, name in enumerate(GROUPS):
        selected = faces[np.asarray(surface.cell_data["group"]) == i]
        indices, inverse = np.unique(selected, return_inverse=True)
        local = points[indices]
        mesh = UsdGeom.Mesh.Define(stage, f"/Monocoque/Geometry/{name}")
        mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(local))
        mesh.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(len(selected), 3, np.int32)))
        mesh.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(inverse.astype(np.int32)))
        mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
        mesh.CreateDoubleSidedAttr(True)
        mesh.CreateExtentAttr([Gf.Vec3f(*local.min(axis=0).tolist()), Gf.Vec3f(*local.max(axis=0).tolist())])
        mesh.GetPrim().SetCustomData({"sourceSha256": sha(source), "sourceGroup": i,
                                      "role": "decimated_visual_mesh_not_analysis_mesh"})
        counts[name] = {"points": len(local), "triangles": len(selected)}
    stage.GetRootLayer().Save()
    return counts


def author_materials(output):
    stage = new_stage(output / "display.usda")
    for name, colour in zip(GROUPS, COLOURS):
        material = UsdShade.Material.Define(stage, f"/Monocoque/Materials/{name}")
        shader = UsdShade.Shader.Define(stage, str(material.GetPath()) + "/Surface")
        shader.CreateIdAttr("UsdPreviewSurface")
        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*colour))
        shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(.38)
        material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
        material.GetPrim().SetCustomData({"purpose": "display_group_colour_not_qualified_material"})
        prim = stage.OverridePrim(f"/Monocoque/Geometry/{name}")
        UsdShade.MaterialBindingAPI.Apply(prim).Bind(material)
    stage.GetRootLayer().Save()


def author_results(output):
    stage = new_stage(output / "results.usda")
    root = UsdGeom.Scope.Define(stage, "/Monocoque/Analysis").GetPrim()
    root.SetCustomData({"status": "historical_S6_screen_not_vehicle_validation",
                        "fieldMapping": "none_visual_and_analysis_geometries_differ",
                        "vehicleMassKgAssumed": 1200, "vehicleMassAppliedAsLoad": False})
    for label, filename, unit in (("Torsion", "torsion-monocoque.json", "N.m/deg"),
                                  ("Bending", "bending.json", "N/mm")):
        source = MONOCOQUE / "derived" / filename
        report = json.loads(source.read_text())
        case = report["cases"]["monocoque, CFRP layup"]
        prim = UsdGeom.Scope.Define(stage, f"/Monocoque/Analysis/{label}").GetPrim()
        prim.SetCustomData({"sourceSha256": sha(source), "sourceReport": filename,
                            "loadCase": json.dumps(report["load_case"], sort_keys=True),
                            "material": "assumed_equivalent_isotropic_CFRP_not_layered_failure_model"})
        prim.CreateAttribute("study:stiffness", Sdf.ValueTypeNames.DoubleArray).Set(case["K"])
        prim.CreateAttribute("study:units", Sdf.ValueTypeNames.String).Set(unit)
        prim.CreateAttribute("study:meshConverged", Sdf.ValueTypeNames.Bool).Set(False)
    stage.GetRootLayer().Save()


def camera_matrix(eye):
    return Gf.Matrix4d().SetLookAt(Gf.Vec3d(*eye), Gf.Vec3d(-1100, 0, 600), Gf.Vec3d(0, 0, 1)).GetInverse()


def author_presentation(output):
    stage = new_stage(output / "presentation.usda")
    views = {"Front": (4300, -4300, 2700), "Rear": (-6300, 4300, 2600),
             "Interior": (0, -3400, 2700), "Orbit": (4300, -4300, 2700)}
    for name, eye in views.items():
        camera = UsdGeom.Camera.Define(stage, f"/Monocoque/Presentation/{name}")
        camera.CreateClippingRangeAttr(Gf.Vec2f(10, 50000))
        camera.CreateFocalLengthAttr(50)
        transform = camera.AddTransformOp()
        transform.Set(camera_matrix(eye))
        if name == "Orbit":
            for frame in range(120):
                angle = 2 * math.pi * frame / 120
                transform.Set(camera_matrix((-1100 + 6400 * math.cos(angle), 6400 * math.sin(angle), 2700)), frame)
        product = UsdRender.Product.Define(stage, f"/Render/{name}")
        product.CreateCameraRel().SetTargets([camera.GetPath()])
        product.CreateResolutionAttr(Gf.Vec2i(1600, 1000))
        var = UsdRender.Var.Define(stage, f"/Render/{name}/LdrColor")
        var.CreateSourceNameAttr("LdrColor")
        var.CreateDataTypeAttr("color4f")
        product.CreateOrderedVarsRel().SetTargets([var.GetPath()])
    dome = UsdLux.DomeLight.Define(stage, "/Monocoque/Presentation/Studio")
    dome.CreateIntensityAttr(700)
    light = UsdLux.DistantLight.Define(stage, "/Monocoque/Presentation/Key")
    light.CreateIntensityAttr(1700)
    light.CreateAngleAttr(15)
    light.AddRotateXYZOp().Set(Gf.Vec3f(-30, -35, 20))
    stage.GetRootLayer().Save()


def validate(directory):
    """Reopen the relocated composition, reject missing assets and unsafe claims."""
    stage_path = directory / "monocoque.usda"
    stage = Usd.Stage.Open(str(stage_path), Usd.Stage.LoadAll)
    if not stage or str(stage.GetDefaultPrim().GetPath()) != "/Monocoque":
        raise ValueError("Missing default monocoque prim")
    if UsdGeom.GetStageUpAxis(stage) != "Z" or UsdGeom.GetStageMetersPerUnit(stage) != .001:
        raise ValueError("Expected millimetres and Z-up")
    data = stage.GetDefaultPrim().GetCustomData()
    if data.get("classification") != "prohibited_pending_engineering" or any(data.get(k) is not False for k in FLAGS):
        raise ValueError("Missing or altered engineering gates")
    layers, assets, unresolved = UsdUtils.ComputeAllDependencies(str(stage_path))
    if unresolved:
        raise ValueError(f"Unresolved dependencies: {unresolved}")
    for path in [Path(layer.realPath) for layer in layers] + [Path(p) for p in assets]:
        if not path.resolve().is_relative_to(directory.resolve()):
            raise ValueError("Bundle depends on a file outside its directory")
    counts = {}
    for name in GROUPS:
        mesh = UsdGeom.Mesh.Get(stage, f"/Monocoque/Geometry/{name}")
        if not mesh or set(mesh.GetFaceVertexCountsAttr().Get()) != {3}:
            raise ValueError(f"Missing triangular group {name}")
        p, f = checked_arrays(mesh.GetPointsAttr().Get(), np.asarray(mesh.GetFaceVertexIndicesAttr().Get()).reshape(-1, 3))
        counts[name] = {"points": len(p), "triangles": len(f)}
    # The usd-core wheel lacks shader resources; use the installed complete USD validator.
    check = subprocess.run(["usdchecker", "--strict", str(stage_path)],
                           check=True, capture_output=True, text=True)
    return {"usdchecker_stdout": check.stdout.strip(), "status": "passed_portable_usd_review_only", "groups": counts,
            "usd_version": list(Usd.GetVersion()), "strict_compliance_issues": [],
            "relocated_dependencies": len(layers) + len(assets), "rtx_execution_verified": False,
            "physical_validation": False, "manufacturing_authorized": False}


def build(output):
    if output.exists():
        raise FileExistsError("Use a new bundle directory; retained results are immutable")
    output.mkdir(parents=True)
    counts = author_geometry(output)
    author_materials(output)
    author_results(output)
    author_presentation(output)
    stage = new_stage(output / "monocoque.usda")
    stage.GetRootLayer().subLayerPaths = ["presentation.usda", "results.usda", "display.usda", "geometry.usdc"]
    stage.SetStartTimeCode(0)
    stage.SetEndTimeCode(119)
    stage.SetTimeCodesPerSecond(24)
    stage.SetFramesPerSecond(24)
    stage.GetRootLayer().documentation = "964 architecture study. No validated 964/993 fitment, laminate, strength or manufacturing process. Display mesh only."
    stage.GetRootLayer().Save()
    interior = new_stage(output / "interior.usda")
    interior.GetRootLayer().subLayerPaths = ["monocoque.usda"]
    UsdGeom.Imageable(interior.OverridePrim("/Monocoque/Geometry/OuterSkin")).CreateVisibilityAttr("invisible")
    interior.GetRootLayer().Save()
    for filename in ("torsion-monocoque.json", "bending.json", "zesad-monocoque.report.json"):
        shutil.copy2(MONOCOQUE / "derived" / filename, output / filename)
    with tempfile.TemporaryDirectory(prefix="964-usd-relocation-") as temp:
        relocated = Path(temp) / "bundle"
        shutil.copytree(output, relocated)
        report = validate(relocated)
    if report["groups"] != counts:
        raise ValueError("Relocated component counts differ from the source")
    report["inputs_sha256"] = {str(p.relative_to(MONOCOQUE)): sha(p) for p in
                               [MONOCOQUE / "derived/zesad-monocoque.vtp", HERE / "build_twin.py"]}
    report["outputs_sha256"] = {p.name: sha(p) for p in sorted(output.iterdir()) if p.is_file()}
    (output / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.output.resolve()), indent=2))
