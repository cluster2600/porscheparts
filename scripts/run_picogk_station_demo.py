#!/usr/bin/env python3
"""Generate PicoGK witnesses, screen the EOS route and compose a millimetre USD.

Uses the existing LPBF geometry kernel. No printer commands or manufacturing
release are produced. Output must be new; incomplete jobs have no completion file.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def import_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_inputs(output, span, voxel):
    if output.exists() or output.is_symlink():
        raise ValueError("output must be new")
    if not math.isfinite(span) or not 20 <= span <= 80:
        raise ValueError("span must be between 20 and 80 mm")
    if not math.isfinite(voxel) or not 0.1 <= voxel <= 0.5:
        raise ValueError("voxel must be between 0.1 and 0.5 mm")


def write_usd(path, meshes):
    from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdRender, UsdShade
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageMetersPerUnit(stage, 0.001)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    world = UsdGeom.Xform.Define(stage, "/World").GetPrim()
    stage.SetDefaultPrim(world)
    world.SetCustomDataByKey("manufacturing_authorized", False)
    material = UsdShade.Material.Define(stage, "/World/Looks/AluminiumReference")
    shader = UsdShade.Shader.Define(stage, "/World/Looks/AluminiumReference/Surface")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.54, 0.62, 0.69))
    shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.65)
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.3)
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    for index, (name, mesh) in enumerate(meshes):
        part = UsdGeom.Xform.Define(stage, "/World/" + name.replace("-", "_"))
        part.AddTranslateOp().Set(Gf.Vec3d(0, index * 20, 0))
        geom = UsdGeom.Mesh.Define(stage, str(part.GetPath()) + "/Geometry")
        geom.CreatePointsAttr([Gf.Vec3f(*map(float, p)) for p in mesh.vertices])
        geom.CreateFaceVertexCountsAttr([3] * len(mesh.faces))
        geom.CreateFaceVertexIndicesAttr(mesh.faces.reshape(-1).tolist())
        geom.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
        UsdShade.MaterialBindingAPI.Apply(geom.GetPrim()).Bind(material)
    plate = UsdGeom.Cube.Define(stage, "/World/EOSM290NominalPlate")
    plate.CreateSizeAttr(1.0)
    plate.AddScaleOp().Set(Gf.Vec3f(250, 250, 1))
    plate.AddTranslateOp().Set(Gf.Vec3d(0, 0, -1))
    plate.CreateDisplayColorAttr([Gf.Vec3f(0.1, 0.12, 0.15)])
    plate.GetPrim().SetCustomDataByKey("nominal_envelope_only", True)
    UsdLux.DomeLight.Define(stage, "/World/Light").CreateIntensityAttr(700)
    camera = UsdGeom.Camera.Define(stage, "/World/Camera")
    matrix = Gf.Matrix4d().SetLookAt(Gf.Vec3d(105, -130, 100), Gf.Vec3d(0, 20, 5), Gf.Vec3d(0, 0, 1)).GetInverse()
    camera.AddTransformOp().Set(matrix)
    camera.CreateClippingRangeAttr(Gf.Vec2f(0.1, 10000))
    render_var = UsdRender.Var.Define(stage, "/Render/Vars/LdrColor")
    render_var.CreateSourceNameAttr("LdrColor")
    product = UsdRender.Product.Define(stage, "/Render/Station")
    product.CreateResolutionAttr(Gf.Vec2i(1280, 720))
    product.CreateCameraRel().SetTargets([camera.GetPath()])
    product.CreateOrderedVarsRel().SetTargets([render_var.GetPath()])
    stage.GetRootLayer().Save()
    reread = Usd.Stage.Open(str(path))
    if reread is None or UsdGeom.GetStageMetersPerUnit(reread) != 0.001:
        raise ValueError("USD roundtrip or units failed")
    if sum(p.IsA(UsdGeom.Mesh) for p in reread.Traverse()) != len(meshes):
        raise ValueError("USD mesh count mismatch")


def run(output, span=30.0, voxel=0.25, dll=Path("/opt/station-demo/bin/StationDemo.dll")):
    validate_inputs(output, span, voxel)
    import trimesh
    output.mkdir(parents=True)
    geometry = output / "geometry"
    with (output / "picogk.log").open("w") as log:
        subprocess.run(["station-picogk", str(dll), str(geometry), str(span), str(voxel)], stdout=log, stderr=subprocess.STDOUT, check=True, timeout=600)
    native = json.loads((geometry / "geometry.json").read_text())
    if native.get("status") != "software_witness_only" or len(native.get("parts", [])) != 3:
        raise ValueError("PicoGK witness report incomplete")
    screen = import_script("run_metal_am_geometry_screen")
    route = import_script("build_process_route_card")
    machine_path = ROOT / "catalog/manufacturing/machines/eos-m290.json"
    process_path = ROOT / "catalog/manufacturing/processes/eos-m290-alsi10mg-30um.json"
    source = ROOT / "twins/picogk-station-demo/Program.cs"
    machine, process = json.loads(machine_path.read_text()), json.loads(process_path.read_text())
    meshes = []
    for part in native["parts"]:
        surface = geometry / part["file"]
        if surface.parent != geometry or sha256(surface) != part["sha256"]:
            raise ValueError("native mesh hash or path mismatch")
        mesh = trimesh.load_mesh(surface, process=True)
        if not isinstance(mesh, trimesh.Trimesh) or not mesh.is_watertight or len(mesh.split()) != 1 or mesh.volume <= 0:
            raise ValueError("witness must have one closed positive-volume component")
        meshes.append((part["id"], mesh))
        args = argparse.Namespace(
            part_id="STATION-" + part["id"].upper(), master=source, master_sha256=sha256(source),
            surface=surface, surface_sha256=sha256(surface), machine_card=machine_path,
            material=process["material"], expected_envelope_mm=mesh.extents.tolist(), envelope_tolerance_mm=0.01,
            output=output / part["id"], layer_thickness_mm=0.03, overhang_deg=45.0,
            support_raster_mm=0.5, thickness_samples=500, voxel_pitch_mm=0.5,
        )
        report = screen.run(args)
        route_report = route.build_route({"id": args.part_id, "name": part["id"], "classification": {"safety_class": "software_witness_only"}}, report, machine, process, None)
        (args.output / "process-route.json").write_text(json.dumps(route_report, indent=2) + "\n")
    stage = output / "station-assembly.usda"
    write_usd(stage, meshes)
    # Completion is published last. Artifacts with FAILED.json or without this
    # receipt are never presented as a completed pipeline.
    result = {"status": "software_pipeline_completed", "manufacturing_authorized": False,
              "physical_coupon_tested": False, "source_sha256": sha256(source),
              "machine_card_sha256": sha256(machine_path), "process_card_sha256": sha256(process_path),
              "artifacts": {str(p.relative_to(output)): sha256(p) for p in sorted(output.rglob("*")) if p.is_file()}}
    (output / "completed.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--span-mm", type=float, default=30)
    parser.add_argument("--voxel-mm", type=float, default=0.25)
    parser.add_argument("--dll", type=Path, default=Path("/opt/station-demo/bin/StationDemo.dll"))
    args = parser.parse_args()
    run(args.output.resolve(), args.span_mm, args.voxel_mm, args.dll)
    print("STATION_PIPELINE_PASS (software witnesses; no print release)")
