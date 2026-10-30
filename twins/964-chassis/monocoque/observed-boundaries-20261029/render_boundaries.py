#!/usr/bin/env python3
"""Overlay exact source edges on the retained USD; render local inspection media."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess

import numpy as np
import pyvista as pv
from pxr import Gf, Sdf, Usd, UsdGeom, Vt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
COLOURS = {0: (1.0, 0.40, 0.08), 1: (0.05, 0.48, 0.95), 2: (0.85, 0.08, 0.40)}
NAMES = {0: "SourceOpen", 1: "SelectionCut", 2: "SourceNonmanifold"}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def render(review, source_stage, vertices_path, faces_path, output):
    review, source_stage, output = Path(review).resolve(), Path(source_stage).resolve(), Path(output).resolve()
    if not output.is_relative_to(ROOT / "work") or output.exists():
        raise ValueError("Use a new private output directory")
    run = json.loads((review / "run.json").read_text())
    verification = json.loads((review / "verification.json").read_text())
    parent = json.loads((HERE.parent / "scan-coverage-20261029/run.json").read_text())
    if verification["status"] != "passed" or verification["run_sha256"] != digest(review / "run.json"):
        raise ValueError("A verified boundary inventory is required")
    if digest(source_stage) != parent["stage_sha256"]:
        raise ValueError("Retained source USD changed")
    for path, name in ((vertices_path, "verts_vehicle.npy"), (faces_path, "faces.npy")):
        if digest(path) != run["input_array_sha256"][name]:
            raise ValueError("Registered source array mismatch")
    vertices, faces = np.load(vertices_path, allow_pickle=False), np.load(faces_path, allow_pickle=False)
    output.mkdir(parents=True)
    target = output / "boundary-review.usdc"
    stage = Usd.Stage.CreateNew(str(target))
    root = UsdGeom.Xform.Define(stage, "/BoundaryReview").GetPrim()
    stage.SetDefaultPrim(root)
    UsdGeom.SetStageMetersPerUnit(stage, 0.001)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    root.CreateAttribute("review:classification", Sdf.ValueTypeNames.String).Set("Mesh boundary inspection; not a carbon cell or identified physical part")
    root.CreateAttribute("review:physicalSegmentationValidated", Sdf.ValueTypeNames.Bool).Set(False)
    root.CreateAttribute("review:geometryModified", Sdf.ValueTypeNames.Bool).Set(False)
    reference = UsdGeom.Xform.Define(stage, "/BoundaryReview/Scan").GetPrim()
    reference.GetReferences().AddReference(os.path.relpath(source_stage, output), "/ScanReview")
    for child in stage.GetPrimAtPath("/BoundaryReview/Scan/Observed").GetChildren():
        imageable = UsdGeom.Imageable(child)
        if child.GetName() not in run["regions"]:
            imageable.MakeInvisible()
        else:
            UsdGeom.Mesh(child).CreateDisplayColorAttr([Gf.Vec3f(0.64, 0.67, 0.70)])
    expected_curves = {}
    for name in run["regions"]:
        data_path = review / (name + ".npz")
        if digest(data_path) != run["private_outputs_sha256"][data_path.name]:
            raise ValueError("Boundary array changed")
        data = np.load(data_path, allow_pickle=False)
        for origin, label in NAMES.items():
            ids = data["source_vertex_ids"][data["boundary_origin"] == origin].astype(np.int32)
            if not len(ids):
                continue
            path = "/BoundaryReview/Edges/" + name + "/" + label
            curve = UsdGeom.BasisCurves.Define(stage, path)
            curve.CreateTypeAttr(UsdGeom.Tokens.linear)
            curve.CreateWrapAttr(UsdGeom.Tokens.nonperiodic)
            curve.CreateCurveVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(len(ids), 2, dtype=np.int32)))
            curve.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(vertices[ids.ravel()]))
            curve.CreateWidthsAttr([1.5])
            curve.SetWidthsInterpolation(UsdGeom.Tokens.constant)
            curve.CreateDisplayColorAttr([Gf.Vec3f(*COLOURS[origin])])
            curve.GetPrim().CreateAttribute("review:sourceVertexIds", Sdf.ValueTypeNames.IntArray).Set(Vt.IntArray.FromNumpy(ids.ravel()))
            curve.GetPrim().CreateAttribute("review:lineWidthMeaning", Sdf.ValueTypeNames.String).Set("Display only; not physical geometry or measurement uncertainty")
            expected_curves[path] = ids
    stage.GetRootLayer().Save()
    stage = None
    reopened = Usd.Stage.Open(str(target))
    if UsdGeom.GetStageMetersPerUnit(reopened) != 0.001 or UsdGeom.GetStageUpAxis(reopened) != "Z":
        raise ValueError("USD units or axis changed")
    meshes, lines = [], []
    checked_faces = checked_edges = 0
    for prim in reopened.Traverse():
        if prim.IsA(UsdGeom.Mesh) and UsdGeom.Imageable(prim).ComputeVisibility() != "invisible":
            mesh = UsdGeom.Mesh(prim)
            points = np.asarray(mesh.GetPointsAttr().Get())
            indices = np.asarray(mesh.GetFaceVertexIndicesAttr().Get()).reshape(-1, 3)
            ids = np.asarray(prim.GetAttribute("scan:sourceVertexIds").Get())
            source_faces = np.asarray(prim.GetAttribute("scan:sourceFaceIds").Get())
            if not np.array_equal(points, vertices[ids]) or not np.array_equal(ids[indices], faces[source_faces]):
                raise ValueError("Referenced mesh source correspondence failed")
            checked_faces += len(indices)
            meshes.append(pv.PolyData(points, np.column_stack((np.full(len(indices), 3), indices))))
        if prim.IsA(UsdGeom.BasisCurves):
            curve = UsdGeom.BasisCurves(prim)
            expected = expected_curves[str(prim.GetPath())]
            ids = np.asarray(prim.GetAttribute("review:sourceVertexIds").Get()).reshape(-1, 2)
            points = np.asarray(curve.GetPointsAttr().Get())
            counts = np.asarray(curve.GetCurveVertexCountsAttr().Get())
            if not np.array_equal(ids, expected) or not np.array_equal(points, vertices[expected.ravel()]) or not np.all(counts == 2):
                raise ValueError("Boundary curve source correspondence failed")
            checked_edges += len(ids)
            poly = pv.PolyData(points)
            poly.lines = np.column_stack((np.full(len(ids), 2), np.arange(len(points)).reshape(-1, 2)))
            lines.append((poly, tuple(curve.GetDisplayColorAttr().Get()[0])))
    if checked_edges != sum(r["boundary_edges"] for r in run["regions"].values()):
        raise ValueError("Incomplete curve export")
    check = subprocess.run(["usdchecker", "--strict", str(target)], text=True, capture_output=True)
    (output / "usdchecker.txt").write_text(check.stdout + check.stderr)
    if check.returncode:
        raise RuntimeError("Strict USD check failed")
    plot = pv.Plotter(off_screen=True, window_size=(1600, 1000))
    try:
        plot.set_background("#e8edf2")
        for mesh in meshes:
            plot.add_mesh(mesh, color="#a3abb3", opacity=0.65, smooth_shading=False)
        for line, colour in lines:
            plot.add_mesh(line, color=colour, line_width=3, lighting=False)
        plot.add_text("964 | OBSERVED FLOOR / COVER SEARCH REGIONS\nOrange: original open edges   Blue: selection cuts", position=(24, 915), font_size=16, color="#152335")
        plot.add_text("Topology inspection only | Physical seams are not identified\nSource coordinates unchanged | Local VTK view of reopened USD | Provisional mm", position=(24, 25), font_size=12, color="#152335")
        plot.enable_parallel_projection()
        images = {}
        views = {
            "boundary-underbody": ([(-1075, 0, -2300), (-1075, 0, 275), (1, 0, 0)], 850),
            "boundary-oblique": ([(-2100, -1800, -1400), (-1075, 0, 275), (0, 0, 1)], 850),
        }
        for name, (camera, scale) in views.items():
            plot.camera_position = camera
            plot.camera.parallel_scale = scale
            plot.render()
            plot.screenshot(output / (name + ".png"))
            images[name] = {"sha256": digest(output / (name + ".png")), "camera": camera, "parallel_scale_mm": scale}
        if len({row["sha256"] for row in images.values()}) != len(images):
            raise ValueError("Inspection views repeated")
        video = output / "boundary-orbit.mp4"
        command = ["ffmpeg", "-v", "error", "-f", "rawvideo", "-pixel_format", "rgb24", "-video_size", "1600x1000",
                   "-framerate", "24", "-i", "pipe:0", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23", "-movflags", "+faststart", str(video)]
        samples = {}
        with subprocess.Popen(command, stdin=subprocess.PIPE) as encoder:
            for frame_id in range(120):
                angle = 2 * math.pi * frame_id / 120
                plot.camera_position = [(-1075 + 1800 * math.cos(angle), 1800 * math.sin(angle), -1900), (-1075, 0, 275), (0, 0, 1)]
                plot.camera.parallel_scale = 850
                plot.render()
                pixels = np.ascontiguousarray(plot.screenshot(return_img=True)[:, :, :3])
                if frame_id in (0, 30, 60, 90):
                    samples[str(frame_id)] = hashlib.sha256(pixels.tobytes()).hexdigest()
                encoder.stdin.write(pixels.tobytes())
            encoder.stdin.close()
            if encoder.wait() != 0:
                raise RuntimeError("Video encoding failed")
        if len(set(samples.values())) != 4:
            raise ValueError("Quarter-orbit frames repeated")
    finally:
        plot.close()
    result = {"classification": "local_source_boundary_review_not_omniverse_or_product_geometry",
              "run_sha256": digest(review / "run.json"), "source_stage_sha256": digest(source_stage),
              "script_sha256": digest(__file__), "stage_sha256": digest(target), "reopened_source_faces_checked": checked_faces,
              "reopened_source_edges_checked": checked_edges, "strict_usdchecker_exit_code": check.returncode,
              "images": images, "video": {"sha256": digest(video), "frames": 120, "fps": 24, "quarter_frame_hashes": samples},
              "pyvista": pv.__version__, "vtk": str(pv.vtk_version_info),
              "geometry_changed": False, "physical_segmentation_validated": False}
    (output / "media.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("review", "source-stage", "vertices", "faces", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(render(args.review, args.source_stage, args.vertices, args.faces, args.output)))
