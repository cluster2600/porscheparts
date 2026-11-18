#!/usr/bin/env python3
"""RTX stills and a turntable of the head's review scene with OVRTX 0.3.0.

Runs inside the pinned SimReady image on a machine with an RTX GPU (the image the repository has
already used for native captures). Follows the monocoque's capture script: every still is
accumulated over 64 steps, every orbit frame over 16, and the frames are encoded with ffmpeg.

On a rented machine the image's default Vulkan entry (libGLX_nvidia) may find no driver. The EGL
entry works headless: write a JSON naming libEGL_nvidia.so.0 and point VK_ICD_FILENAMES and
VK_DRIVER_FILES at it (seen on 2026-11-15, driver 580.178, RTX 3090). ffmpeg is not in the image.

Usage: capture_rtx.py SCENE_DIR OUT_DIR
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def capture(scene: Path, output: Path) -> None:
    import numpy as np
    import ovrtx
    from PIL import Image

    manifest = json.loads((scene / "scene.json").read_text())
    for name, expected in manifest["files_sha256"].items():
        if sha256(scene / name) != expected:
            raise ValueError(f"scene file changed since it was built: {name}")
    if ovrtx.__version__ != "0.3.0":
        raise RuntimeError("this adapter targets the qualified OVRTX 0.3.0 image")
    gpu = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"],
                         check=True, capture_output=True, text=True).stdout.strip()
    width, height = manifest["resolution"]
    output.mkdir(parents=True, exist_ok=False)
    renderer = ovrtx.Renderer(config=ovrtx.RendererConfig(active_cuda_gpus="0", sync_mode=True))
    try:
        def frame(product, time, steps, path):
            renderer.update_from_usd_time(time)
            for _ in range(steps):
                products = renderer.step(render_products={product}, delta_time=0.0)
            frames = products[product].frames
            with frames[-1].render_vars["LdrColor"].map(device=ovrtx.Device.CPU) as mapped:
                pixels = np.from_dlpack(mapped).copy()
            if pixels.shape != (height, width, 4) or pixels.dtype != np.uint8 or np.std(pixels[:, :, :3]) < 5:
                raise RuntimeError(f"invalid or empty RTX frame for {product}")
            Image.fromarray(pixels).save(path)

        stills = [p.rsplit("/", 1)[1] for p in manifest["render_products"] if not p.endswith("/Orbit")]
        scene_of = manifest["scene_of_a_product"]
        opened = None

        def use(product):
            nonlocal opened
            if scene_of[product] != opened:
                if opened is not None:
                    renderer.reset_stage()
                renderer.open_usd(str(scene / scene_of[product]))
                opened = scene_of[product]

        for name in stills:
            use("/Render/" + name)
            frame("/Render/" + name, 0.0, 64, output / (name.lower() + ".png"))
        frames, fps = manifest["orbit"]["frames"], manifest["orbit"]["frames_per_second"]
        use("/Render/Orbit")
        with tempfile.TemporaryDirectory(prefix="935-rtx-frames-") as temp:
            for index in range(frames):
                frame("/Render/Orbit", index / fps, 16, Path(temp) / f"{index:04d}.png")
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-n", "-framerate", str(fps),
                            "-i", str(Path(temp) / "%04d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                            "-crf", "21", "-movflags", "+faststart", str(output / "turntable.mp4")], check=True)
            # every tenth orbit frame is kept as a PNG, so that a GIF can be made without the video
            for index in range(0, frames, 10):
                (output / f"orbit-{index:03d}.png").write_bytes((Path(temp) / f"{index:04d}.png").read_bytes())
    finally:
        del renderer
    receipt = {
        "schema": "935-cad-twin-rtx-capture/1", "renderer": "NVIDIA Omniverse OVRTX", "ovrtx_version": ovrtx.__version__,
        "gpu": gpu, "scene_sha256": manifest["files_sha256"], "cad_stage_sha256": manifest["cad_stage_sha256"],
        "stills": stills, "video_frames": frames, "video_fps": fps, "accumulation_steps": {"still": 64, "orbit_frame": 16},
        "adapter_sha256": sha256(Path(__file__)),
        "media_sha256": {p.name: sha256(p) for p in sorted(output.iterdir()) if p.is_file()},
        "claims": manifest["claims"],
    }
    (output / "capture.json").write_text(json.dumps(receipt, indent=1) + "\n")
    print(json.dumps({"stills": stills, "frames": frames, "gpu": gpu}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scene", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    capture(args.scene.resolve(), args.output.resolve())
