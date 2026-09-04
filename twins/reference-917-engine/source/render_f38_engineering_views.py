#!/usr/bin/env python3
"""Rend les vues d'ingénierie F38 depuis les maillages réellement exportés."""

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
    ("rocker-carrier-f38-rounded-reinforced.stl", "#d8a847", "Porte-axes renforcé"),
    ("two-rocker-shafts-f38.stl", "#d8e3e8", "2 axes"),
    ("four-rockers-f38.stl", "#9cb2bd", "4 culbuteurs"),
    ("two-intake-valves-f38.stl", "#48c9f0", "2 soupapes admission"),
    ("two-exhaust-valves-f38.stl", "#ff7659", "2 soupapes échappement"),
    ("four-valve-guides-f38.stl", "#b7c5cb", "4 guides"),
    ("four-valve-seats-f38.stl", "#eeae55", "4 sièges"),
    ("eight-valve-springs-f38.render.stl", "#a7e36d", "8 ressorts"),
)


def load(path: Path) -> trimesh.Trimesh:
    mesh = trimesh.load(path, force="mesh", process=True)
    if not isinstance(mesh, trimesh.Trimesh) or not len(mesh.faces):
        raise RuntimeError(f"maillage absent: {path}")
    return mesh


def add_mesh(
    axis: object,
    mesh: trimesh.Trimesh,
    colour: str,
    *,
    alpha: float = 1.0,
    face_mask: np.ndarray | None = None,
) -> None:
    face_ids = np.arange(len(mesh.faces), dtype=np.int64)
    if face_mask is not None:
        face_ids = face_ids[np.asarray(face_mask, dtype=bool)]
    triangles = mesh.vertices[mesh.faces[face_ids]]
    normals = mesh.face_normals[face_ids]
    light = np.asarray([-0.45, -0.70, 0.85], dtype=float)
    light /= np.linalg.norm(light)
    diffuse = np.clip(0.32 + 0.68 * np.maximum(0.0, normals @ light), 0.24, 1.0)
    base = np.asarray(to_rgb(colour), dtype=float)
    rgba = np.column_stack((np.clip(base[None, :] * diffuse[:, None], 0.0, 1.0), np.full(len(face_ids), alpha)))
    collection = Poly3DCollection(triangles, linewidths=0.0, antialiased=False, zsort="average")
    collection.set_facecolor(rgba)
    collection.set_edgecolor("none")
    axis.add_collection3d(collection)


def frame(axis: object, head: trimesh.Trimesh, elev: float, azim: float) -> None:
    centre = head.bounds.mean(axis=0)
    radius = float(max(head.extents)) * 0.51
    axis.set_xlim(centre[0] - radius, centre[0] + radius)
    axis.set_ylim(centre[1] - radius, centre[1] + radius)
    axis.set_zlim(centre[2] - 0.46 * radius, centre[2] + 0.46 * radius)
    axis.set_box_aspect((1.0, 1.0, 0.78))
    axis.view_init(elev=elev, azim=azim)
    axis.set_axis_off()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--head", type=Path, required=True)
    parser.add_argument("--parts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    head = load(args.head)
    components = [(load(args.parts / name), colour, label) for name, colour, label in PARTS]

    figure = plt.figure(figsize=(16, 9), facecolor="#07131c")
    figure.suptitle(
        "CULASSE PORSCHE 917 F38 — PEAU DU SCAN + DISTRIBUTION 4 SOUPAPES",
        color="white",
        fontsize=20,
        fontweight="bold",
        y=0.965,
    )

    exterior = figure.add_subplot(1, 2, 1, projection="3d", facecolor="#0d1c25")
    add_mesh(exterior, head, "#c48b42")
    frame(exterior, head, 25.0, -52.0)
    exterior.set_title("Corps de culasse — morphologie scan préservée", color="white", fontsize=13, pad=10)

    section = figure.add_subplot(1, 2, 2, projection="3d", facecolor="#0d1c25")
    cut = head.triangles_center[:, 0] <= 3.0
    add_mesh(section, head, "#c48b42", alpha=0.34, face_mask=cut)
    for index, (mesh, colour, _) in enumerate(components):
        add_mesh(section, mesh, colour, alpha=0.58 if index == 0 else 0.96)
    frame(section, head, 17.0, -20.0)
    section.set_title("Demi-coupe — distribution provisoire 4 soupapes / 8 ressorts", color="white", fontsize=13, pad=10)

    figure.text(
        0.5,
        0.055,
        "F38 OFFSET SCAN +0,45 mm  •  B-REP FACETTE  •  COMPOSANTS ANALYTIQUES SEPARES",
        ha="center",
        color="#a9dcec",
        fontsize=11,
        fontweight="bold",
    )
    figure.text(
        0.5,
        0.025,
        "CONVERSION STEP NON MAILLABLE CAE A CE STADE — ECHELLE/INTERFACES/MATIERE NON QUALIFIEES — IMPRESSION INTERDITE",
        ha="center",
        color="#ff9b8c",
        fontsize=10,
        fontweight="bold",
    )
    figure.subplots_adjust(left=0.015, right=0.985, bottom=0.09, top=0.90, wspace=0.02)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=180, facecolor=figure.get_facecolor())
    plt.close(figure)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
