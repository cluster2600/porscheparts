#!/usr/bin/env python3
"""Review scene of the head for an RTX capture: the CAD-body stage with cameras, lights and render products.

The scene references the private CAD-body stage unchanged (body and studs, grey where the scan
supports the surface and orange where it is inferred) and adds, in a layer of its own:

  cameras   three still views and one orbit of 120 frames at 24 per second, all looking at the
            centre of the body;
  lights    a dome light and one distant key light;
  floor     a disc under the lowest point, for contact shadows only, in a second scene file that the
            view from below does not use;
  products  one render product per camera, 1600 x 1000, colour only.

Nothing is added to the geometry and no material property is authored: the pictures show the twin's
own display colours. The scene is private, like the stage it references.

Usage: build_review_usd.py CAD_STAGE.usdc OUT_DIR
"""

from __future__ import annotations

import hashlib
import json
import math
import shutil
import sys
from pathlib import Path

from pxr import Gf, Usd, UsdGeom, UsdLux, UsdRender

FRAMES, FPS = 120, 24
RESOLUTION = (1600, 1000)
FOCAL_MM, APERTURE_MM = 50.0, 20.955


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def look_at(eye, target, up=(0.0, 0.0, 1.0)) -> Gf.Matrix4d:
    return Gf.Matrix4d().SetLookAt(Gf.Vec3d(*eye), Gf.Vec3d(*target), Gf.Vec3d(*up)).GetInverse()


def main(cad_stage, out_dir) -> None:
    cad_stage, out = Path(cad_stage), Path(out_dir)
    out.mkdir(parents=True, exist_ok=False)
    shutil.copy2(cad_stage, out / "head.usdc")
    source = Usd.Stage.Open(str(out / "head.usdc"))
    assert UsdGeom.GetStageUpAxis(source) == "Z" and abs(UsdGeom.GetStageMetersPerUnit(source) - 0.001) < 1e-12
    root = source.GetDefaultPrim()
    box = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_]).ComputeWorldBound(root).ComputeAlignedRange()
    lo, hi = box.GetMin(), box.GetMax()
    centre = tuple(0.5 * (lo[k] + hi[k]) for k in range(3))
    radius = 0.5 * math.sqrt(sum((hi[k] - lo[k]) ** 2 for k in range(3)))
    # The bounding sphere of the box is 1.25 times the frame's smaller field of view: the body, which
    # is far from filling that sphere, then takes about three quarters of the frame's height and
    # stays inside the frame's width through the whole orbit.
    fov = 2.0 * math.atan(0.5 * APERTURE_MM * RESOLUTION[1] / RESOLUTION[0] / FOCAL_MM)
    distance = radius / math.sin(0.5 * fov) / 1.25

    stage = Usd.Stage.CreateNew(str(out / "review.usda"))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 0.001)
    stage.SetStartTimeCode(0)
    stage.SetEndTimeCode(FRAMES - 1)
    stage.SetTimeCodesPerSecond(FPS)
    scene = UsdGeom.Xform.Define(stage, "/Review")
    stage.SetDefaultPrim(scene.GetPrim())
    head = stage.DefinePrim("/Review/Head")
    head.GetReferences().AddReference("./head.usdc")

    def eye(azimuth_deg, elevation_deg):
        a, e = math.radians(azimuth_deg), math.radians(elevation_deg)
        return (centre[0] + distance * math.cos(e) * math.cos(a), centre[1] + distance * math.cos(e) * math.sin(a),
                centre[2] + distance * math.sin(e))

    views = {"CamSide": (-58.0, 24.0), "PortSide": (122.0, 18.0), "Chamber": (-40.0, -42.0), "Orbit": (-58.0, 24.0)}
    for name, (azimuth, elevation) in views.items():
        camera = UsdGeom.Camera.Define(stage, f"/Review/Cameras/{name}")
        camera.CreateClippingRangeAttr(Gf.Vec2f(1.0, 20000.0))
        camera.CreateFocalLengthAttr(FOCAL_MM)
        camera.CreateHorizontalApertureAttr(APERTURE_MM)
        camera.CreateVerticalApertureAttr(APERTURE_MM * RESOLUTION[1] / RESOLUTION[0])
        op = camera.AddTransformOp()
        op.Set(look_at(eye(azimuth, elevation), centre))
        if name == "Orbit":
            for frame in range(FRAMES):
                op.Set(look_at(eye(azimuth + 360.0 * frame / FRAMES, elevation), centre), frame)
        product = UsdRender.Product.Define(stage, f"/Render/{name}")
        product.CreateCameraRel().SetTargets([camera.GetPath()])
        product.CreateResolutionAttr(Gf.Vec2i(*RESOLUTION))
        var = UsdRender.Var.Define(stage, f"/Render/{name}/LdrColor")
        var.CreateSourceNameAttr("LdrColor")
        var.CreateDataTypeAttr("color4f")
        product.CreateOrderedVarsRel().SetTargets([var.GetPath()])

    dome = UsdLux.DomeLight.Define(stage, "/Review/Lights/Studio")
    dome.CreateIntensityAttr(650)
    key = UsdLux.DistantLight.Define(stage, "/Review/Lights/Key")
    key.CreateIntensityAttr(2200)
    key.CreateAngleAttr(12)
    key.AddRotateXYZOp().Set(Gf.Vec3f(-38, -28, 25))
    stage.GetRootLayer().Save()

    # A second scene adds a floor just under the lowest point, for contact shadows. The view from
    # below uses the scene without it.
    with_floor = Usd.Stage.CreateNew(str(out / "review-floor.usda"))
    with_floor.GetRootLayer().subLayerPaths.append("./review.usda")
    UsdGeom.SetStageUpAxis(with_floor, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(with_floor, 0.001)
    with_floor.SetStartTimeCode(0)
    with_floor.SetEndTimeCode(FRAMES - 1)
    with_floor.SetTimeCodesPerSecond(FPS)
    with_floor.SetDefaultPrim(with_floor.GetPrimAtPath("/Review"))
    floor = UsdGeom.Mesh.Define(with_floor, "/Review/Floor")
    r, z = 6.0 * radius, lo[2] - 0.5
    ring = [(centre[0] + r * math.cos(2 * math.pi * k / 64), centre[1] + r * math.sin(2 * math.pi * k / 64), z) for k in range(64)]
    floor.CreatePointsAttr([Gf.Vec3f(*p) for p in ring])
    floor.CreateFaceVertexCountsAttr([64])
    floor.CreateFaceVertexIndicesAttr(list(range(64)))
    floor.CreateDisplayColorAttr([Gf.Vec3f(0.78, 0.79, 0.80)])
    with_floor.GetRootLayer().Save()

    reopened = Usd.Stage.Open(str(out / "review.usda"), Usd.Stage.LoadAll)
    assert reopened.GetPrimAtPath("/Review/Head/BareHead").IsA(UsdGeom.Mesh), "the reference did not resolve"
    manifest = {
        "schema": "935-cad-twin-review-scene/1",
        "claims": "review scene of a study twin: display colours only, no material, no physics, not a product picture",
        "cad_stage_sha256": sha256(cad_stage), "files_sha256": {n: sha256(out / n) for n in ("head.usdc", "review.usda", "review-floor.usda")},
        "units": "mm, Z up", "extent_mm": {"min": [round(v, 2) for v in lo], "max": [round(v, 2) for v in hi]},
        "camera": {"focal_mm": FOCAL_MM, "horizontal_aperture_mm": APERTURE_MM, "distance_mm": round(distance, 1),
                   "views_azimuth_elevation_deg": views},
        "render_products": [f"/Render/{name}" for name in views], "resolution": list(RESOLUTION),
        "scene_of_a_product": {f"/Render/{name}": ("review.usda" if name == "Chamber" else "review-floor.usda") for name in views},
        "orbit": {"frames": FRAMES, "frames_per_second": FPS},
    }
    (out / "scene.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(json.dumps({"distance_mm": manifest["camera"]["distance_mm"], "extent_mm": manifest["extent_mm"]}))


if __name__ == "__main__":
    main(*sys.argv[1:])
