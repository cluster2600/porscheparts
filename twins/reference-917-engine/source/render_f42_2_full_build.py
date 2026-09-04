#!/usr/bin/env python3
"""Rendu public assaini des agregats de tranchage F42.2."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_metrics(path: Path) -> dict[str, np.ndarray]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 4122:
        raise ValueError(f"expected_4122_rows:{len(rows)}")
    numeric: dict[str, np.ndarray] = {}
    for key in rows[0]:
        numeric[key] = np.asarray([float(row[key]) for row in rows], dtype=float)
    return numeric


def style_figure(figure: plt.Figure) -> None:
    figure.patch.set_facecolor("#08131c")
    for axis in figure.axes:
        axis.set_facecolor("#0d1d29")
        axis.tick_params(colors="#d6e3eb", labelsize=8)
        axis.xaxis.label.set_color("#d6e3eb")
        axis.yaxis.label.set_color("#d6e3eb")
        axis.title.set_color("#f4f7f8")
        for spine in axis.spines.values():
            spine.set_color("#3c5362")
        axis.grid(color="#314955", linewidth=0.5, alpha=0.45)


def render_dashboard(report: dict, metrics: dict[str, np.ndarray], output: Path) -> None:
    z = metrics["z_mm"]
    figure, axes = plt.subplots(2, 2, figsize=(14, 8))
    figure.subplots_adjust(left=0.07, right=0.98, bottom=0.14, top=0.87, hspace=0.40, wspace=0.26)
    style_figure(figure)
    figure.suptitle(
        "F42.2 — tranche géométrique pleine pièce, 4 122 couches × 50 µm",
        color="white",
        fontsize=17,
        fontweight="bold",
    )
    axes[0, 0].plot(z, metrics["part_area_mm2"], color="#72d6ff", linewidth=1.0)
    axes[0, 0].set(title="Section de matière", xlabel="Hauteur Z (mm)", ylabel="Aire (mm²)")
    axes[0, 1].fill_between(
        z, metrics["unsupported_area_mm2"], color="#ffb347", alpha=0.85, linewidth=0
    )
    axes[0, 1].set(
        title="Zones non soutenues — critère géométrique 45°",
        xlabel="Hauteur Z (mm)",
        ylabel="Aire/couche (mm²)",
    )
    axes[1, 0].plot(
        z, metrics["support_cross_section_area_mm2"], color="#c58cff", linewidth=1.0
    )
    axes[1, 0].set(
        title="Enveloppe conservative de supports",
        xlabel="Hauteur Z (mm)",
        ylabel="Section support (mm²)",
    )
    orientation = report["orientation_screen"]["results"]
    labels = [item["orientation"] for item in orientation]
    projected = [item["downward_projected_area_mm2"] for item in orientation]
    colors = ["#ffb347" if label == "+Y_locked" else "#5aa9cf" for label in labels]
    axes[1, 1].bar(labels, projected, color=colors)
    axes[1, 1].set(
        title="Écran cardinal d'orientation (proxy surfacique)",
        xlabel="Direction de construction",
        ylabel="Projection descendante (mm²)",
    )
    axes[1, 1].tick_params(axis="x", rotation=20)
    support = report["support_proxy"]
    footer = (
        f"Support proxy: {support['volume_cm3']:.2f} cm³  |  "
        f"îlots nouveaux: {report['overhang_and_islands']['new_island_count_total']}  |  "
        "AdditiveFOAM: NON EXÉCUTÉ  |  recoater: NON VALIDÉ  |  impression: NON AUTORISÉE"
    )
    figure.text(0.5, 0.025, footer, ha="center", color="#ff8f8f", fontsize=9.5)
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=180, facecolor=figure.get_facecolor())
    plt.close(figure)


def render_video(metrics: dict[str, np.ndarray], output: Path, frames: int = 120) -> None:
    z = metrics["z_mm"]
    area = metrics["part_area_mm2"]
    unsupported = metrics["unsupported_area_mm2"]
    support = metrics["support_cross_section_area_mm2"]
    figure, axes = plt.subplots(3, 1, figsize=(12.8, 7.2), sharex=True, constrained_layout=True)
    style_figure(figure)
    figure.suptitle(
        "F42.2 — progression des 4 122 couches (agrégats publics, sans contours)",
        color="white",
        fontsize=15,
        fontweight="bold",
    )
    series = [area, unsupported, support]
    labels = ["Aire pièce (mm²)", "Aire non soutenue (mm²)", "Section support proxy (mm²)"]
    colors = ["#72d6ff", "#ffb347", "#c58cff"]
    lines = []
    markers = []
    for axis, values, label, color in zip(axes, series, labels, colors):
        axis.set_xlim(float(z[0]), float(z[-1]))
        axis.set_ylim(0.0, max(float(np.max(values)) * 1.08, 1.0))
        axis.set_ylabel(label)
        line, = axis.plot([], [], color=color, linewidth=1.3)
        marker = axis.axvline(float(z[0]), color="white", linewidth=0.8, alpha=0.8)
        lines.append(line)
        markers.append(marker)
    axes[-1].set_xlabel("Hauteur Z (mm)")
    status = figure.text(0.82, 0.94, "", ha="right", color="#d6e3eb", fontsize=10)

    endpoints = np.linspace(1, len(z), frames, dtype=int)

    def update(frame: int):
        end = int(endpoints[frame])
        for line, marker, values in zip(lines, markers, series):
            line.set_data(z[:end], values[:end])
            marker.set_xdata([z[end - 1], z[end - 1]])
        status.set_text(f"couche {end:,}/4 122 — Z {z[end - 1]:.3f} mm".replace(",", " "))
        return [*lines, *markers, status]

    movie = animation.FuncAnimation(figure, update, frames=frames, interval=50, blit=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    writer = animation.FFMpegWriter(fps=24, bitrate=2400, codec="libx264")
    movie.save(output, writer=writer, dpi=100)
    plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    metrics = load_metrics(args.metrics)
    render_dashboard(report, metrics, args.image)
    render_video(metrics, args.video)
    manifest = {
        "schema_version": "1.0.0",
        "phase": "F42.2",
        "privacy": "aggregate metrics only; no contours, coordinates or private geometry",
        "artifacts": {
            "report": {"file": args.report.name, "sha256": sha256(args.report)},
            "metrics": {"file": args.metrics.name, "sha256": sha256(args.metrics)},
            "image": {"file": args.image.name, "sha256": sha256(args.image)},
            "video": {"file": args.video.name, "sha256": sha256(args.video)},
        },
        "gates": {
            "contains_private_geometry": False,
            "supplier_slicer_reviewed": False,
            "recoater_clearance_verified": False,
            "print_authorized": False,
        },
    }
    args.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
