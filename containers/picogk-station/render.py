"""Render an authored USD RenderProduct using the isolated OVRTX 0.3 runtime.

Lifecycle follows NVIDIA content-agents 36dbf3f274f8e256637230a05a085853f65cc175
world_understanding/functions/graphics/render_ovrtx.py (_WORKER_SCRIPT).
"""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scene", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--render-product", default="/Render/Station")
    parser.add_argument("--steps", type=int, default=64)
    args = parser.parse_args()
    if not args.scene.is_file() or not 1 <= args.steps <= 1024:
        parser.error("Existing USD and 1..1024 accumulation steps required")
    if not args.render_product.startswith("/") or args.output.exists():
        parser.error("Absolute USD prim path and new output filename required")
    import numpy as np
    import ovrtx
    from PIL import Image

    # Fail closed if this native build lacks explicit device selection.
    config = ovrtx.RendererConfig(active_cuda_gpus="0")
    renderer = ovrtx.Renderer(config=config)
    try:
        renderer.open_usd(str(args.scene.resolve()))
        products = None
        for _ in range(args.steps):
            products = renderer.step(render_products={args.render_product}, delta_time=0.0)
        if not products or args.render_product not in products:
            raise RuntimeError("Renderer did not return the requested RenderProduct")
        frames = products[args.render_product].frames
        if not frames or "LdrColor" not in frames[-1].render_vars:
            raise RuntimeError("Renderer returned no LdrColor frame")
        with frames[-1].render_vars["LdrColor"].map(device=ovrtx.Device.CPU) as mapped:
            pixels = np.from_dlpack(mapped).copy()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(pixels).save(args.output)
        print(json.dumps({"status": "PASS", "gpu_physical_index": 3,
                          "render_product": args.render_product,
                          "steps": args.steps, "output": str(args.output),
                          "manufacturing_validated": False}))
    finally:
        mapped = frames = None
        products = None
        del renderer


if __name__ == "__main__":
    main()
