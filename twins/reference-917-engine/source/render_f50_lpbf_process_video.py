#!/usr/bin/env python3
"""Render a public F50 LPBF process video from aggregate metrics only.

No triangle, contour, coordinate, private path, scan or product silhouette is
read or emitted.  The animation is a process/qualification dashboard, not an
engine-operation video and not evidence of a successful physical print.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_layers(path: Path) -> dict[str, np.ndarray]:
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise SystemExit(f"empty_layer_metrics:{path.name}")
    fields = ("z_mm", "part_area_mm2", "unsupported_area_mm2", "support_area_mm2")
    return {field: np.asarray([float(row[field]) for row in rows]) for field in fields}


def load_cases(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 4:
        raise SystemExit(f"expected_four_coupon_cases:{len(rows)}")
    return rows


def style(axis: plt.Axes) -> None:
    axis.set_facecolor("#10212d")
    axis.tick_params(colors="#d7e4ec")
    for spine in axis.spines.values():
        spine.set_color("#476579")
    axis.grid(alpha=0.15)


def draw_frame(
    destination: Path,
    fraction: float,
    layers: dict[str, dict[str, np.ndarray]],
    cases: list[dict[str, str]],
) -> None:
    figure, axes = plt.subplots(2, 2, figsize=(16, 9), facecolor="#07131b")
    figure.suptitle(
        "F50 — QUALIFICATION VIRTUELLE DU PROCEDE LPBF",
        color="white",
        fontsize=22,
        weight="bold",
    )
    colors = {"2V": "#4cc9f0", "4V": "#f9c74f"}
    for variant, data in layers.items():
        count = max(2, min(len(data["z_mm"]), int(round(fraction * len(data["z_mm"])))))
        axes[0, 0].plot(
            data["z_mm"][:count], data["part_area_mm2"][:count],
            color=colors[variant], linewidth=1.5, label=variant,
        )
        axes[0, 1].plot(
            data["z_mm"][:count], data["unsupported_area_mm2"][:count],
            color=colors[variant], linewidth=1.5, label=variant,
        )
    axes[0, 0].set_title("Section pleine piece par couche", color="white", weight="bold")
    axes[0, 0].set_xlabel("Hauteur de fabrication (mm)", color="#d7e4ec")
    axes[0, 0].set_ylabel("Aire sectionnee (mm2)", color="#d7e4ec")
    axes[0, 1].set_title("Zone descendante sans support fournisseur", color="white", weight="bold")
    axes[0, 1].set_xlabel("Hauteur de fabrication (mm)", color="#d7e4ec")
    axes[0, 1].set_ylabel("Aire projetee (mm2)", color="#d7e4ec")
    for axis in axes[0]:
        style(axis)
        axis.legend(facecolor="#10212d", labelcolor="white")

    visible = max(1, min(len(cases), int(np.ceil(fraction * len(cases)))))
    shown = cases[:visible]
    labels = [row["case_id"].replace("published_witness", "witness").replace("low_ved_screen", "lowVED") for row in shown]
    x = np.arange(visible)
    axes[1, 0].bar(x, [float(row["temperature_p99_k"]) for row in shown], color="#ff7849")
    axes[1, 0].set_title("AdditiveFOAM — temperature P99 des coupons", color="white", weight="bold")
    axes[1, 0].set_ylabel("K", color="#d7e4ec")
    axes[1, 0].set_xticks(x, labels, rotation=28, ha="right", fontsize=7)
    style(axes[1, 0])

    axes[1, 1].bar(x - 0.22, [float(row["melt_pool_width_mm"]) for row in shown], width=0.22, color="#90be6d", label="largeur")
    axes[1, 1].bar(x, [float(row["melt_pool_depth_mm"]) for row in shown], width=0.22, color="#f9c74f", label="profondeur")
    axes[1, 1].bar(x + 0.22, [float(row["melt_pool_length_mm"]) for row in shown], width=0.22, color="#4cc9f0", label="longueur")
    axes[1, 1].set_title("AdditiveFOAM — bain fondu des coupons", color="white", weight="bold")
    axes[1, 1].set_ylabel("mm", color="#d7e4ec")
    axes[1, 1].set_xticks(x, labels, rotation=28, ha="right", fontsize=7)
    axes[1, 1].legend(facecolor="#10212d", labelcolor="white", fontsize=8)
    style(axes[1, 1])

    figure.text(
        0.5,
        0.016,
        "VIDEO DE PROCEDE — ni fonctionnement moteur, ni validation physique. Peau F50 non publiee et inchangee. Impression et demarrage interdits.",
        color="#ffb4a2",
        ha="center",
        fontsize=11,
        weight="bold",
    )
    figure.tight_layout(rect=(0.025, 0.06, 0.975, 0.94))
    figure.savefig(destination, dpi=100, facecolor=figure.get_facecolor())
    plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--layers-2v", type=Path, required=True)
    parser.add_argument("--layers-4v", type=Path, required=True)
    parser.add_argument("--coupons", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    args = parser.parse_args()
    layers = {"2V": load_layers(args.layers_2v), "4V": load_layers(args.layers_4v)}
    cases = load_cases(args.coupons)
    args.output.mkdir(parents=True, exist_ok=True)
    image_path = args.output / "917-head-f50-lpbf-process-dashboard.png"
    video_path = args.output / "917-head-f50-lpbf-process.mp4"
    with tempfile.TemporaryDirectory(prefix="f50-lpbf-frames-") as temporary:
        frame_dir = Path(temporary)
        frame_count = 90
        for index in range(frame_count):
            fraction = (index + 1) / frame_count
            draw_frame(frame_dir / f"frame-{index:04d}.png", fraction, layers, cases)
        draw_frame(image_path, 1.0, layers, cases)
        command = [
            args.ffmpeg, "-y", "-framerate", "15", "-i", str(frame_dir / "frame-%04d.png"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video_path),
        ]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            raise SystemExit(f"ffmpeg_failed:{completed.stderr[-1000:]}")
    manifest = {
        "classification": "aggregate_lpbf_process_dashboard_not_engine_operation_not_physical_print",
        "contains_private_geometry": False,
        "contains_triangle_or_slice_coordinates": False,
        "image": {"path": image_path.name, "sha256": sha256(image_path)},
        "video": {"path": video_path.name, "sha256": sha256(video_path)},
        "inputs": {
            "layers_2v_sha256": sha256(args.layers_2v),
            "layers_4v_sha256": sha256(args.layers_4v),
            "coupons_sha256": sha256(args.coupons),
        },
    }
    manifest_path = args.output / "917-head-f50-lpbf-process-media-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
