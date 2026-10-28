#!/usr/bin/env python3
"""Capture the validated review bundle with the existing pinned OVRTX 0.3 image."""
import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_inputs(bundle):
    report = json.loads((bundle / "validation.json").read_text())
    if report.get("status") != "passed_portable_usd_review_only" or report.get("manufacturing_authorized") is not False:
        raise ValueError("A validated, unreleased review bundle is required")
    required = {"monocoque.usda", "interior.usda", "geometry.usdc", "display.usda", "results.usda", "presentation.usda"}
    if not required <= set(report.get("outputs_sha256", {})):
        raise ValueError("Incomplete bundle hash manifest")
    for name, expected in report["outputs_sha256"].items():
        path = bundle / name
        if Path(name).name != name or path.is_symlink() or digest(path) != expected:
            raise ValueError(f"Bundle file identity mismatch: {name}")
    return report


def capture(bundle, output):
    import numpy as np
    import ovrtx
    from PIL import Image
    report = verify_inputs(bundle)
    if ovrtx.__version__ != "0.3.0":
        raise RuntimeError("This adapter targets the qualified OVRTX 0.3.0 image")
    gpu = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version,uuid", "--format=csv,noheader"],
                         check=True, capture_output=True, text=True).stdout.strip()
    output.mkdir(parents=True, exist_ok=False)
    renderer = ovrtx.Renderer(config=ovrtx.RendererConfig(active_cuda_gpus="0", sync_mode=True))
    try:
        def frame(product, time, steps, path):
            renderer.update_from_usd_time(time)
            for _ in range(steps):
                products = renderer.step(render_products={product}, delta_time=0.)
            frames = products[product].frames
            with frames[-1].render_vars["LdrColor"].map(device=ovrtx.Device.CPU) as mapped:
                pixels = np.from_dlpack(mapped).copy()
            if pixels.shape != (1000, 1600, 4) or pixels.dtype != np.uint8 or np.std(pixels[:, :, :3]) < 5:
                raise RuntimeError("Invalid or empty RTX frame")
            Image.fromarray(pixels).save(path)

        renderer.open_usd(str(bundle / "monocoque.usda"))
        for name in ("Front", "Rear"):
            frame("/Render/" + name, 0., 64, output / (name.lower() + ".png"))
        with tempfile.TemporaryDirectory(prefix="964-rtx-frames-") as temp:
            for index in range(120):
                frame("/Render/Orbit", float(index), 16, Path(temp) / f"{index:04d}.png")
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-n", "-framerate", "24",
                            "-i", str(Path(temp) / "%04d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                            "-crf", "21", "-movflags", "+faststart", str(output / "turntable.mp4")], check=True)
        renderer.reset_stage()
        renderer.open_usd(str(bundle / "interior.usda"))
        frame("/Render/Interior", 0., 64, output / "interior.png")
    finally:
        del renderer
    report.update({"renderer": "NVIDIA Omniverse OVRTX", "ovrtx_version": ovrtx.__version__,
                   "rtx_execution_verified": True, "gpu": gpu, "video_frames": 120, "video_fps": 24,
                   "adapter_sha256": digest(Path(__file__)),
                   "bundle_validation_sha256": digest(bundle / "validation.json"),
                   "media_sha256": {p.name: digest(p) for p in output.iterdir() if p.is_file()}})
    (output / "capture.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    capture(args.bundle.resolve(), args.output.resolve())
