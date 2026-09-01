#!/usr/bin/env python3
"""Render F7 frame ranges through local OVRTX and encode a disclosed MP4."""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import urllib.request
from pathlib import Path


def post_json(url: str, payload: dict) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=3600) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--stages-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--endpoint", default="http://127.0.0.1:8001")
    args = parser.parse_args()
    if not args.endpoint.startswith(("http://127.0.0.1:", "http://localhost:")):
        raise RuntimeError("OVRTX endpoint must remain loopback-local")
    config = json.loads(args.config.read_text(encoding="utf-8"))
    frames_dir = args.output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    render = config["render"]
    written = 0
    for shot in config["shots"]:
        stage = (args.stages_dir / shot["stage"]).resolve()
        if not stage.is_file():
            raise RuntimeError(f"missing authored video stage: {stage}")
        for start in range(shot["start"], shot["end"] + 1, render["chunk_size"]):
            end = min(start + render["chunk_size"] - 1, shot["end"])
            payload = {
                "url": stage.as_uri(),
                "force_render": True,
                "render_settings": {
                    "camera_paths": [render["camera_path"]],
                    "frame_range": {"start": start, "end": end},
                    "camera_parameters": {"width": render["width"], "height": render["height"]},
                    "sensors": ["rgb"],
                    "apply_background_mask": False,
                    "render_mode": render["render_mode"],
                    "num_sensor_updates": render["num_sensor_updates"],
                    "material_target": render["material_target"],
                },
            }
            result = post_json(f"{args.endpoint.rstrip('/')}/render", payload)
            if result.get("status") != "success":
                raise RuntimeError(f"OVRTX render failed: {result.get('error')}")
            for frame in range(start, end + 1):
                encoded = result["images"][str(frame)][render["camera_path"]]["rgb"]
                (frames_dir / f"frame_{frame:04d}.png").write_bytes(base64.b64decode(encoded))
                written += 1

    expected = config["acceptance"]["expected_frame_count"]
    if written != expected:
        raise RuntimeError(f"frame count mismatch: {written} != {expected}")
    output = args.output_dir / "917-engine-dry-crank-f7.mp4"
    disclosure = config["disclosure"].replace("'", "\\'").replace(":", "\\:")
    subprocess.run(
        [
            "ffmpeg", "-y", "-framerate", str(config["timeline"]["frames_per_second"]),
            "-i", str(frames_dir / "frame_%04d.png"),
            "-vf", f"drawbox=x=0:y=h-54:w=w:h=54:color=black@0.65:t=fill,drawtext=text='{disclosure}':fontcolor=white:fontsize=22:x=(w-text_w)/2:y=h-38",
            "-c:v", config["encode"]["video_codec"], "-crf", str(config["encode"]["constant_rate_factor"]),
            "-pix_fmt", config["encode"]["pixel_format"], "-movflags", "+faststart", str(output),
        ],
        check=True,
    )
    subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(output)], check=True)
    report = {
        "schema_version": "1.0.0",
        "status": "passed",
        "output_video": str(output.resolve()),
        "frame_count": written,
        "frames_per_second": config["timeline"]["frames_per_second"],
        "disclosure": config["disclosure"],
        "physical_simulation_claim_authorized": False,
    }
    (args.output_dir / "motion-video-f7-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
