#!/usr/bin/env python3
"""Rend le paquet analytique de distribution F38 sans géométrie de scan."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import trimesh


PARTS = (
    ("rocker-carrier-f38-rounded-reinforced.stl", "#d7a54a", "porte-axes", 0.42),
    ("two-rocker-shafts-f38.stl", "#dbe8ed", "2 axes", 1.0),
    ("four-rockers-f38.stl", "#8298a4", "4 culbuteurs", 1.0),
    ("two-intake-valves-f38.stl", "#36c9ef", "2 soupapes admission", 1.0),
    ("two-exhaust-valves-f38.stl", "#ff7659", "2 soupapes échappement", 1.0),
    ("four-valve-guides-f38.stl", "#cbd6db", "4 guides", 0.78),
    ("four-valve-seats-f38.stl", "#f4bf62", "4 sièges", 1.0),
    ("eight-valve-springs-f38.render.stl", "#9ee46d", "8 ressorts", 1.0),
    ("four-lower-spring-cups-f38.stl", "#e6c887", "4 coupelles inférieures", 1.0),
    ("four-upper-spring-retainers-f38.stl", "#f0dda7", "4 coupelles supérieures", 1.0),
)


def load(path: Path) -> trimesh.Trimesh:
    mesh = trimesh.load(path, force="mesh", process=True)
    if not isinstance(mesh, trimesh.Trimesh) or not len(mesh.faces):
        raise RuntimeError(f"maillage_absent:{path}")
    return mesh


def add_mesh(axis: object, mesh: trimesh.Trimesh, colour: str, alpha: float, *, section: bool) -> None:
    ids = np.arange(len(mesh.faces), dtype=np.int64)
    if section:
        ids = ids[mesh.triangles_center[:, 0] <= 0.0]
    triangles = mesh.vertices[mesh.faces[ids]]
    normals = mesh.face_normals[ids]
    light = np.asarray([-0.4, -0.7, 0.85], dtype=float)
    light /= np.linalg.norm(light)
    level = np.clip(0.26 + 0.74 * np.maximum(0.0, normals @ light), 0.20, 1.0)
    base = np.asarray(to_rgb(colour))
    rgba = np.column_stack((np.clip(base[None, :] * level[:, None], 0.0, 1.0), np.full(len(ids), alpha)))
    collection = Poly3DCollection(triangles, linewidths=0.0, antialiased=False, zsort="average")
    collection.set_facecolor(rgba)
    collection.set_edgecolor("none")
    axis.add_collection3d(collection)


def frame(axis: object, bounds: np.ndarray, elev: float, azim: float) -> None:
    centre = bounds.mean(axis=0)
    extents = bounds[1] - bounds[0]
    radius = float(max(extents)) * 0.57
    axis.set_xlim(centre[0] - radius, centre[0] + radius)
    axis.set_ylim(centre[1] - radius, centre[1] + radius)
    axis.set_zlim(centre[2] - 0.58 * radius, centre[2] + 0.58 * radius)
    axis.set_box_aspect((1.0, 1.0, 1.02))
    axis.view_init(elev=elev, azim=azim)
    axis.set_axis_off()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cad", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    components = [(load(args.cad / name), colour, label, alpha) for name, colour, label, alpha in PARTS]
    bounds = np.array([
        np.min([mesh.bounds[0] for mesh, _, _, _ in components], axis=0),
        np.max([mesh.bounds[1] for mesh, _, _, _ in components], axis=0),
    ])
    figure = plt.figure(figsize=(16, 9), facecolor="#07131c")
    figure.suptitle(
        "PORSCHE 917 F38 — DISTRIBUTION ANALYTIQUE 4 SOUPAPES",
        color="white",
        fontsize=21,
        fontweight="bold",
        y=0.965,
    )

    assembled = figure.add_subplot(1, 2, 1, projection="3d", facecolor="#0c1b25")
    for mesh, colour, _, alpha in components:
        add_mesh(assembled, mesh, colour, alpha, section=False)
    frame(assembled, bounds, 21.0, -47.0)
    assembled.set_title("Assemblage multi-corps — composants séparés", color="white", fontsize=13, pad=12)

    section = figure.add_subplot(1, 2, 2, projection="3d", facecolor="#0c1b25")
    for mesh, colour, _, alpha in components:
        add_mesh(section, mesh, colour, min(alpha + 0.15, 1.0), section=True)
    frame(section, bounds, 13.0, -8.0)
    section.set_title("Demi-coupe X ≤ 0 — axes, culbuteurs et empilage soupapes", color="white", fontsize=13, pad=12)

    figure.text(
        0.5,
        0.060,
        "1 PORTE-AXES  •  2 AXES  •  4 CULBUTEURS  •  4 SOUPAPES  •  4 GUIDES  •  4 SIÈGES  •  8 RESSORTS",
        ha="center",
        color="#b9e6f2",
        fontsize=11,
        fontweight="bold",
    )
    figure.text(
        0.5,
        0.026,
        "INTERFACES • CINÉMATIQUE • CONTACTS • FATIGUE NON VALIDÉS — PAS UNE PREUVE DE RÉSISTANCE NI UNE AUTORISATION DE FABRICATION",
        ha="center",
        color="#ff9b8c",
        fontsize=10,
        fontweight="bold",
    )
    figure.subplots_adjust(left=0.01, right=0.99, bottom=0.10, top=0.90, wspace=0.01)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=180, facecolor=figure.get_facecolor())
    plt.close(figure)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
