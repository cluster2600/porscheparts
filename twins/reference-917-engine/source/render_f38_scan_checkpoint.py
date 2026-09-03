#!/usr/bin/env python3
"""Rend un point de controle F38 uniquement depuis la peau F37 issue du scan.

Ce rendu n'invente aucune surface CAO. Il montre l'enveloppe triangulee retenue
et une coupe visuelle avec les noyaux gaz/huile existants afin de verifier la
direction avant toute reconstruction B-Rep.
"""

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


def load(path: Path) -> trimesh.Trimesh:
    mesh = trimesh.load(path, force="mesh", process=True)
    if not isinstance(mesh, trimesh.Trimesh) or not len(mesh.faces):
        raise RuntimeError(f"maillage absent: {path}")
    return mesh


def subset(mesh: trimesh.Trimesh, maximum_faces: int, mask: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    faces = np.arange(len(mesh.faces), dtype=np.int64)
    if mask is not None:
        faces = faces[np.asarray(mask, dtype=bool)]
    if len(faces) > maximum_faces:
        faces = faces[np.linspace(0, len(faces) - 1, maximum_faces, dtype=np.int64)]
    return mesh.vertices[mesh.faces[faces]], mesh.face_normals[faces]


def add_solid(
    axis: object,
    mesh: trimesh.Trimesh,
    colour: str,
    maximum_faces: int,
    *,
    alpha: float = 1.0,
    mask: np.ndarray | None = None,
) -> None:
    triangles, normals = subset(mesh, maximum_faces, mask)
    light = np.asarray([-0.45, -0.60, 0.90], dtype=float)
    light /= np.linalg.norm(light)
    intensity = np.clip(0.28 + 0.72 * np.abs(normals @ light), 0.20, 1.0)
    base = np.asarray(to_rgb(colour), dtype=float)
    rgba = np.column_stack((np.clip(base[None, :] * intensity[:, None], 0.0, 1.0), np.full(len(triangles), alpha)))
    collection = Poly3DCollection(triangles, linewidths=0.0, antialiased=False)
    collection.set_facecolor(rgba)
    collection.set_edgecolor("none")
    axis.add_collection3d(collection)


def frame(axis: object, mesh: trimesh.Trimesh, elev: float, azim: float) -> None:
    centre = mesh.bounds.mean(axis=0)
    radius = float(max(mesh.extents)) * 0.55
    axis.set_xlim(centre[0] - radius, centre[0] + radius)
    axis.set_ylim(centre[1] - radius, centre[1] + radius)
    axis.set_zlim(centre[2] - 0.48 * radius, centre[2] + 0.48 * radius)
    axis.set_box_aspect((1.0, 1.0, 0.78))
    axis.view_init(elev=elev, azim=azim)
    axis.set_axis_off()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--head", type=Path, required=True)
    parser.add_argument("--flow-core", type=Path, required=True)
    parser.add_argument("--oil-core", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    head = load(args.head)
    flow = load(args.flow_core)
    oil = load(args.oil_core)
    figure = plt.figure(figsize=(16, 9), facecolor="#07131c")
    figure.suptitle(
        "CULASSE PORSCHE 917 F38 — DIRECTION CORRIGEE SUR LA PEAU DU SCAN",
        color="white",
        fontsize=20,
        fontweight="bold",
        y=0.965,
    )

    exterior = figure.add_subplot(1, 2, 1, projection="3d", facecolor="#0c1b25")
    add_solid(exterior, head, "#c58a3b", 110_000)
    frame(exterior, head, 24.0, -52.0)
    exterior.set_title("Enveloppe retenue — maillage exact F37 issu du scan", color="white", fontsize=13, pad=12)

    section = figure.add_subplot(1, 2, 2, projection="3d", facecolor="#0c1b25")
    centres = head.triangles_center
    cut_mask = centres[:, 0] <= 4.0
    add_solid(section, head, "#c58a3b", 90_000, alpha=0.78, mask=cut_mask)
    add_solid(section, flow, "#56d7ef", 28_000, alpha=0.86)
    add_solid(section, oil, "#ef5757", 18_000, alpha=0.92)
    frame(section, head, 18.0, -18.0)
    section.set_title("Coupe visuelle — noyau gaz 4 soupapes + galeries d'huile", color="white", fontsize=13, pad=12)

    figure.text(
        0.5,
        0.055,
        "OR = peau scan conservee   •   CYAN = noyau admission/echappement/chambre   •   ROUGE = huile",
        ha="center",
        color="#a9dcec",
        fontsize=11,
        fontweight="bold",
    )
    figure.text(
        0.5,
        0.025,
        "POINT DE CONTROLE GEOMETRIQUE — ECHELLE ET INTERFACES 917 NON CERTIFIEES — IMPRESSION METAL INTERDITE",
        ha="center",
        color="#ff9b8c",
        fontsize=10,
        fontweight="bold",
    )
    figure.subplots_adjust(left=0.02, right=0.98, bottom=0.09, top=0.90, wspace=0.03)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=180, facecolor=figure.get_facecolor())
    plt.close(figure)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
