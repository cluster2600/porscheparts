#!/usr/bin/env python3
"""Rend la CAO F34 réelle sans la présenter comme une pièce libérée."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_ascii_stl(path: Path, triangle_count: int) -> np.ndarray:
    triangles = np.empty((triangle_count, 3, 3), dtype=np.float32)
    vertex_index = 0
    with path.open("r", encoding="ascii") as stream:
        for line in stream:
            tokens = line.split()
            if len(tokens) == 4 and tokens[0] == "vertex":
                triangles[vertex_index // 3, vertex_index % 3] = [
                    float(value) for value in tokens[1:]
                ]
                vertex_index += 1
    if vertex_index != triangle_count * 3:
        raise ValueError(
            f"ASCII STL incomplet: {vertex_index // 3} triangles, {triangle_count} attendus"
        )
    return triangles


def visible_mesh(
    triangles: np.ndarray,
    elevation_deg: float,
    azimuth_deg: float,
    base_rgb: np.ndarray,
    maximum_faces: int = 400_000,
) -> tuple[np.ndarray, np.ndarray]:
    elevation = np.deg2rad(elevation_deg)
    azimuth = np.deg2rad(azimuth_deg)
    camera = np.asarray(
        [
            np.cos(elevation) * np.cos(azimuth),
            np.cos(elevation) * np.sin(azimuth),
            np.sin(elevation),
        ],
        dtype=float,
    )
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    lengths = np.linalg.norm(normals, axis=1)
    valid = lengths > 1.0e-12
    normals[valid] /= lengths[valid, None]
    facing = valid & ((normals @ camera) > -0.02)
    visible = triangles[facing]
    visible_normals = normals[facing]
    if len(visible) > maximum_faces:
        selection = np.linspace(0, len(visible) - 1, maximum_faces, dtype=int)
        visible = visible[selection]
        visible_normals = visible_normals[selection]
    light = np.asarray([0.35, -0.45, 0.82], dtype=float)
    light /= np.linalg.norm(light)
    intensity = np.clip(0.42 + 0.58 * np.maximum(visible_normals @ light, 0.0), 0.25, 1.0)
    rgba = np.column_stack((intensity[:, None] * base_rgb[None, :], np.ones(len(intensity))))
    return visible, rgba


def equal_axes(axis, triangles: np.ndarray) -> None:
    lower = triangles.reshape(-1, 3).min(axis=0)
    upper = triangles.reshape(-1, 3).max(axis=0)
    centre = 0.5 * (lower + upper)
    span = np.maximum(upper - lower, 1.0)
    radius = 0.54 * float(span.max())
    axis.set_xlim(centre[0] - radius, centre[0] + radius)
    axis.set_ylim(centre[1] - radius, centre[1] + radius)
    axis.set_zlim(centre[2] - 0.45 * radius, centre[2] + 0.75 * radius)
    axis.set_box_aspect((1.0, 1.0, 0.70))


def add_view(axis, triangles: np.ndarray, elevation: float, azimuth: float, title: str) -> None:
    visible, colors = visible_mesh(
        triangles,
        elevation,
        azimuth,
        np.asarray([0.82, 0.61, 0.24]),
    )
    axis.add_collection3d(
        Poly3DCollection(visible, facecolors=colors, edgecolors="none", linewidths=0.0)
    )
    equal_axes(axis, triangles)
    axis.view_init(elev=elevation, azim=azimuth)
    axis.set_axis_off()
    axis.set_title(title, color="white", fontsize=12, fontweight="bold", pad=8)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stl", type=Path, required=True)
    parser.add_argument("--geometry-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads(args.geometry_report.read_text(encoding="utf-8"))
    expected_sha = report["files"]["stl"]["sha256"]
    if sha256(args.stl) != expected_sha:
        raise SystemExit("le STL ne correspond pas au rapport géométrique F34")
    triangles = load_ascii_stl(args.stl, report["geometry"]["surface_elements"])
    args.output.parent.mkdir(parents=True, exist_ok=True)

    figure = plt.figure(figsize=(14, 8.2), facecolor="#0b1118")
    figure.suptitle(
        "Culasse Porsche 917 F34 — concept 4 soupapes refroidi par air",
        color="white",
        fontsize=18,
        fontweight="bold",
        y=0.975,
    )
    figure.text(
        0.5,
        0.93,
        "RENDU DE LA CAO PARAMÉTRIQUE ÉTANCHE — PROTOTYPE DE PROCÉDÉ, FABRICATION MOTEUR INTERDITE",
        color="#ffcc66",
        fontsize=10.5,
        ha="center",
        fontweight="bold",
    )
    left = figure.add_subplot(1, 2, 1, projection="3d", facecolor="#111b25")
    right = figure.add_subplot(1, 2, 2, projection="3d", facecolor="#111b25")
    add_view(left, triangles, 24.0, -52.0, "Ailettes, conduits et deck supérieur")
    add_view(right, triangles, -66.0, 38.0, "Chambre, quatre sièges et bougie centrale")

    metrics = report["geometry"]
    figure.text(
        0.5,
        0.055,
        f"{metrics['fin_count']} ailettes · {metrics['valve_count']} soupapes · "
        f"surface totale {metrics['external_and_internal_surface_area_m2']:.3f} m² · "
        f"volume {metrics['volume_mm3'] / 1e6:.3f} l · un seul solide B-Rep",
        color="#d6dde5",
        fontsize=10.5,
        ha="center",
    )
    figure.text(
        0.5,
        0.022,
        "Échelle du scan non confirmée; ajustement 917, carte matière à chaud, CFD/CHT, fatigue, CT/CND et bancs physiques non validés.",
        color="#f19a9a",
        fontsize=9.2,
        ha="center",
    )
    figure.subplots_adjust(left=0.015, right=0.985, bottom=0.085, top=0.90, wspace=0.01)
    figure.savefig(args.output, dpi=180, facecolor=figure.get_facecolor())
    plt.close(figure)
    print(json.dumps({"status": "rendered", "output": str(args.output), "stl_sha256": expected_sha}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
