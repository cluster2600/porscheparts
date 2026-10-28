#!/usr/bin/env python3
"""Capture local VTK previews of the reopened USD; these are not RTX receipts."""
import argparse
import json
import math
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pyvista as pv
from PIL import Image
from pxr import Gf, Usd, UsdGeom

from build_twin import COLOURS, GROUPS, sha, validate


def capture(bundle, output):
    report = validate(bundle)
    output.mkdir(parents=True, exist_ok=False)
    stage = Usd.Stage.Open(str(bundle / "monocoque.usda"))
    plotter = pv.Plotter(off_screen=True, window_size=(1600, 1000), lighting="three lights")
    plotter.set_background("#101720")
    actors = {}
    try:
        for name, colour in zip(GROUPS, COLOURS):
            mesh = UsdGeom.Mesh.Get(stage, f"/Monocoque/Geometry/{name}")
            triangles = np.asarray(mesh.GetFaceVertexIndicesAttr().Get()).reshape(-1, 3)
            cells = np.column_stack((np.full(len(triangles), 3), triangles))
            surface = pv.PolyData(np.asarray(mesh.GetPointsAttr().Get()), cells.ravel())
            actors[name] = plotter.add_mesh(surface, color=colour, smooth_shading=True)
        plotter.add_text("964 MONOCOQUE | ARCHITECTURE STUDY", position="upper_left", font_size=19, color="white")
        plotter.add_text("LOCAL OpenUSD / VTK PREVIEW - NOT OMNIVERSE RTX\nUnvalidated interfaces and laminate | No manufacturing approval",
                         position="lower_left", font_size=13, color="white")

        def frame(name, time, path):
            camera = UsdGeom.Camera.Get(stage, f"/Monocoque/Presentation/{name}").GetCamera(Usd.TimeCode(time))
            matrix = camera.transform
            eye = matrix.ExtractTranslation()
            plotter.camera_position = (tuple(eye), tuple(eye + matrix.TransformDir(Gf.Vec3d(0, 0, -1))),
                                       tuple(matrix.TransformDir(Gf.Vec3d(0, 1, 0))))
            plotter.camera.view_angle = math.degrees(2 * math.atan(camera.verticalAperture / (2 * camera.focalLength)))
            plotter.camera.clipping_range = (10, 50000)
            plotter.render()
            plotter.screenshot(str(path))
            pixels = np.asarray(Image.open(path))[:, :, :3]
            if np.std(pixels) < 5 or np.count_nonzero(np.ptp(pixels.astype(int), axis=2) > 30) < 10000:
                raise RuntimeError("Empty or missing-colour preview")

        plotter.show(auto_close=False, interactive=False)
        for name in ("Front", "Rear", "Interior"):
            actors["OuterSkin"].visibility = name != "Interior"
            frame(name, 0, output / (name.lower() + ".png"))
        actors["OuterSkin"].visibility = True
        with tempfile.TemporaryDirectory(prefix="964-preview-frames-") as temp:
            for index in range(120):
                frame("Orbit", index, Path(temp) / f"{index:04d}.png")
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-n", "-framerate", "24",
                            "-i", str(Path(temp) / "%04d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                            "-crf", "21", "-movflags", "+faststart", str(output / "turntable.mp4")], check=True)
    finally:
        plotter.close()
    report.update({"renderer": "VTK local preview", "rtx_execution_verified": False,
                   "video_frames": 120, "video_fps": 24,
                   "source_sha256": sha(Path(__file__)),
                   "bundle_sha256": {p.name: sha(p) for p in bundle.iterdir() if p.suffix in (".usda", ".usdc")},
                   "media_sha256": {p.name: sha(p) for p in output.iterdir() if p.is_file()}})
    (output / "capture.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    capture(args.bundle.resolve(), args.output.resolve())
