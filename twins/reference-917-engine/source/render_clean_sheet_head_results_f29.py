#!/usr/bin/env python3
"""Produit des figures techniques F29 sans les presenter comme CFD, FEA ou Omniverse."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np


VARIANTS = (
    ("type_912_5_0_na_2v", "5,0 l atmospherique - 2V", "#d78b35"),
    ("type_912_5_0_na_4v", "5,0 l atmospherique - 4V", "#38a6b8"),
    ("917_30_1973_turbo_5374_2v", "5,374 l turbo - 2V", "#d78b35"),
    ("917_30_1973_turbo_5374_4v", "5,374 l turbo - 4V", "#38a6b8"),
)


def load_binary_stl(path: Path) -> np.ndarray:
    payload = path.read_bytes()
    if len(payload) < 84:
        raise ValueError(f"stl_too_short:{path}")
    triangle_count = struct.unpack_from("<I", payload, 80)[0]
    expected_size = 84 + triangle_count * 50
    if len(payload) != expected_size:
        raise ValueError(f"stl_size_mismatch:{path}:{len(payload)}:{expected_size}")
    record_dtype = np.dtype(
        [
            ("normal", "<f4", (3,)),
            ("vertices", "<f4", (3, 3)),
            ("attribute", "<u2"),
        ]
    )
    records = np.frombuffer(payload, dtype=record_dtype, count=triangle_count, offset=84)
    vertices = np.asarray(records["vertices"], dtype=np.float64)
    if not np.isfinite(vertices).all():
        raise ValueError(f"stl_non_finite_vertices:{path}")
    return vertices


def equalize_axes(axis, vertices: np.ndarray) -> None:
    minimum = vertices.reshape(-1, 3).min(axis=0)
    maximum = vertices.reshape(-1, 3).max(axis=0)
    center = (minimum + maximum) / 2.0
    radius = float((maximum - minimum).max() / 2.0)
    axis.set_xlim(center[0] - radius, center[0] + radius)
    axis.set_ylim(center[1] - radius, center[1] + radius)
    axis.set_zlim(center[2] - radius, center[2] + radius)
    axis.set_box_aspect((1.0, 1.0, 0.72))


def visible_triangles_and_colors(triangles: np.ndarray, base_color: str) -> tuple[np.ndarray, np.ndarray]:
    elevation = np.deg2rad(28.0)
    azimuth = np.deg2rad(-48.0)
    camera_vector = np.asarray(
        [
            np.cos(elevation) * np.cos(azimuth),
            np.cos(elevation) * np.sin(azimuth),
            np.sin(elevation),
        ]
    )
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    lengths = np.linalg.norm(normals, axis=1)
    valid = lengths > 1.0e-12
    normals[valid] /= lengths[valid, None]
    facing = valid & ((normals @ camera_vector) > 0.0)
    visible = triangles[facing]
    visible_normals = normals[facing]
    light_vector = np.asarray([0.35, -0.45, 0.82])
    light_vector /= np.linalg.norm(light_vector)
    intensity = np.clip(0.48 + 0.52 * (visible_normals @ light_vector), 0.25, 1.0)
    rgb = np.asarray(matplotlib.colors.to_rgb(base_color))
    colors = np.clip(intensity[:, None] * rgb[None, :], 0.0, 1.0)
    return visible, colors


def render_cad_comparison(evidence_root: Path, output_path: Path) -> None:
    figure = plt.figure(figsize=(14, 10), facecolor="#0c1117")
    figure.suptitle(
        "Porsche 917 - culasses conceptuelles F29 : comparaison 2V / 4V",
        color="white",
        fontsize=18,
        fontweight="bold",
        y=0.975,
    )
    figure.text(
        0.5,
        0.94,
        "APERCU CAD CONCEPTUEL - PAS UN RESULTAT CFD, FEA OU OMNIVERSE",
        color="#f0c36a",
        fontsize=11,
        ha="center",
        fontweight="bold",
    )
    for index, (identifier, label, color) in enumerate(VARIANTS, start=1):
        axis = figure.add_subplot(2, 2, index, projection="3d", facecolor="#101820")
        triangles = load_binary_stl(evidence_root / "cad" / f"{identifier}.stl")
        triangles, face_colors = visible_triangles_and_colors(triangles, color)
        if len(triangles) > 16000:
            selection = np.linspace(0, len(triangles) - 1, 16000, dtype=int)
            triangles = triangles[selection]
            face_colors = face_colors[selection]
        mesh = Poly3DCollection(
            triangles,
            facecolor=face_colors,
            edgecolor="none",
            linewidth=0.0,
            alpha=1.0,
        )
        axis.add_collection3d(mesh)
        equalize_axes(axis, triangles)
        axis.view_init(elev=28, azim=-48)
        axis.set_title(label, color="white", fontsize=13, fontweight="bold", pad=12)
        axis.set_axis_off()
    figure.text(
        0.5,
        0.018,
        "Solides STEP rouverts dans OCCT; STL derives pour visualisation. Ajustement moteur et fabrication non autorises.",
        color="#c8d0d8",
        fontsize=9.5,
        ha="center",
    )
    figure.subplots_adjust(left=0.015, right=0.985, bottom=0.055, top=0.91, wspace=0.02, hspace=0.08)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=180, facecolor=figure.get_facecolor(), bbox_inches="tight")
    plt.close(figure)


def render_trade_study(study_path: Path, output_path: Path) -> None:
    study = json.loads(study_path.read_text(encoding="utf-8"))
    comparisons = study["comparisons"]
    metrics = (
        ("combined_mean_effective_area", "Aire effective\nmoyenne", "#36b37e"),
        ("estimated_total_valve_mass", "Masse totale\ndes soupapes", "#f0b44d"),
        ("pressure_stress_proxy", "Contrainte\nproxy", "#e05d5d"),
        ("deck_temperature_rise_proxy", "Elevation thermique\nproxy", "#ad6bd6"),
    )
    labels = ["5,0 l atmospherique", "5,374 l turbo"]
    values = np.asarray(
        [
            [item["four_valve_change_percent"][key] for key, _, _ in metrics]
            for item in comparisons
        ],
        dtype=float,
    )
    figure, axis = plt.subplots(figsize=(13, 7.4), facecolor="#0c1117")
    axis.set_facecolor("#101820")
    x_positions = np.arange(len(labels), dtype=float)
    width = 0.18
    offsets = (np.arange(len(metrics)) - (len(metrics) - 1) / 2.0) * width
    for metric_index, (_, label, color) in enumerate(metrics):
        bars = axis.bar(
            x_positions + offsets[metric_index],
            values[:, metric_index],
            width=width * 0.9,
            label=label.replace("\n", " "),
            color=color,
        )
        axis.bar_label(bars, labels=[f"+{value:.1f}%" for value in values[:, metric_index]], color="white", padding=3)
    axis.set_title(
        "F29 - variation du concept 4V par rapport au 2V",
        color="white",
        fontsize=18,
        fontweight="bold",
        pad=22,
    )
    axis.text(
        0.5,
        1.01,
        "Criblage analytique simplifie : les hausses de masse, contrainte et temperature sont des penalites",
        transform=axis.transAxes,
        color="#f0c36a",
        fontsize=10.5,
        ha="center",
    )
    axis.set_ylabel("Variation 4V vs 2V (%)", color="white", fontsize=11)
    axis.set_xticks(x_positions, labels, color="white", fontsize=11)
    axis.tick_params(axis="y", colors="white")
    axis.grid(axis="y", color="#52606d", alpha=0.32, linewidth=0.8)
    for spine in axis.spines.values():
        spine.set_color("#52606d")
    legend = axis.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=4, frameon=False)
    for text in legend.get_texts():
        text.set_color("white")
    figure.text(
        0.5,
        0.018,
        "Indicateurs de sensibilite, pas rendement moteur; aucune correlation banc, CFD ou FEA.",
        color="#c8d0d8",
        fontsize=10,
        ha="center",
    )
    figure.subplots_adjust(left=0.09, right=0.98, top=0.86, bottom=0.2)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=180, facecolor=figure.get_facecolor(), bbox_inches="tight")
    plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    evidence_root = args.evidence_root.resolve()
    output_dir = args.output_dir.resolve()
    render_cad_comparison(evidence_root, output_dir / "cad-comparison-2v-4v.png")
    render_trade_study(evidence_root / "design-study.json", output_dir / "trade-study-4v-vs-2v.png")
    print(json.dumps({"status": "generated", "output_dir": str(output_dir)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
