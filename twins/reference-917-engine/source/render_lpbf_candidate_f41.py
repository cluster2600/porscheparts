#!/usr/bin/env python3
"""Produit les vues de controle du candidat de culasse F41.

Le rendu distingue explicitement la peau externe conservee, la face de
combustion et une demi-coupe. Il ne remplace pas une inspection CAO.
"""

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
import trimesh


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_mesh(path: Path) -> trimesh.Trimesh:
    mesh = trimesh.load_mesh(path, process=True)
    if not isinstance(mesh, trimesh.Trimesh):
        raise RuntimeError(f"maillage_invalide:{path}")
    return mesh


def sampled_triangles(mesh: trimesh.Trimesh, maximum: int, selector: np.ndarray | None = None) -> np.ndarray:
    triangles = mesh.triangles
    if selector is not None:
        triangles = triangles[selector]
    if len(triangles) > maximum:
        indices = np.linspace(0, len(triangles) - 1, maximum, dtype=np.int64)
        triangles = triangles[indices]
    return triangles


def light_colors(triangles: np.ndarray, base: tuple[float, float, float], alpha: float = 1.0) -> np.ndarray:
    vectors = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    lengths = np.maximum(np.linalg.norm(vectors, axis=1), 1.0e-12)
    normals = vectors / lengths[:, None]
    light = np.asarray([0.25, -0.35, 0.90])
    light /= np.linalg.norm(light)
    intensity = 0.38 + 0.62 * np.abs(normals @ light)
    rgb = np.asarray(base)[None, :] * intensity[:, None]
    return np.column_stack((np.clip(rgb, 0.0, 1.0), np.full(len(rgb), alpha)))


def add_mesh(axis, triangles: np.ndarray, base: tuple[float, float, float], alpha: float = 1.0) -> None:
    collection = Poly3DCollection(
        triangles,
        facecolors=light_colors(triangles, base, alpha),
        edgecolor=(0.08, 0.11, 0.13, min(alpha, 0.20)),
        linewidth=0.08,
    )
    axis.add_collection3d(collection)


def frame(axis, meshes: list[np.ndarray], elev: float, azim: float) -> None:
    points = np.concatenate([triangles.reshape(-1, 3) for triangles in meshes], axis=0)
    low = points.min(axis=0)
    high = points.max(axis=0)
    centre = (low + high) / 2.0
    radius = 0.56 * float(np.max(high - low))
    axis.set_xlim(centre[0] - radius, centre[0] + radius)
    axis.set_ylim(centre[1] - radius, centre[1] + radius)
    axis.set_zlim(centre[2] - radius, centre[2] + radius)
    axis.set_box_aspect((1.0, 1.0, 0.82))
    axis.view_init(elev=elev, azim=azim)
    axis.set_axis_off()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--head", type=Path, required=True)
    parser.add_argument("--gas-core", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    head = load_mesh(args.head)
    gas = load_mesh(args.gas_core) if args.gas_core else None
    report = json.loads(args.report.read_text(encoding="utf-8"))
    head_triangles = sampled_triangles(head, 70000)
    gas_triangles = sampled_triangles(gas, 28000) if gas is not None else None
    centres = head.triangles_center
    half_triangles = sampled_triangles(head, 70000, centres[:, 0] <= 0.0)

    figure = plt.figure(figsize=(18, 10), facecolor="#07131b")
    figure.suptitle(
        "CULASSE F41 — ENVELOPPE PORSCHE 935/917 CONSERVEE, 4 SOUPAPES",
        color="white",
        fontsize=21,
        fontweight="bold",
        y=0.97,
    )
    subtitle = "B-Rep monobloc scan-conforme · aucune ovalisation · brut LPBF AlSi10Mg candidat"
    figure.text(0.5, 0.925, subtitle, color="#80c8de", fontsize=12, ha="center")

    iso = figure.add_subplot(1, 3, 1, projection="3d", facecolor="#0d202b")
    add_mesh(iso, head_triangles, (0.93, 0.68, 0.30))
    frame(iso, [head_triangles], 24, -55)
    iso.set_title("Enveloppe exterieure conservee", color="white", fontweight="bold", pad=10)

    deck = figure.add_subplot(1, 3, 2, projection="3d", facecolor="#0d202b")
    add_mesh(deck, head_triangles, (0.84, 0.86, 0.87))
    frame(deck, [head_triangles], -82, -90)
    deck.set_title("Face combustion : 4 soupapes + 2 bougies", color="white", fontweight="bold", pad=10)

    cut = figure.add_subplot(1, 3, 3, projection="3d", facecolor="#0d202b")
    add_mesh(cut, half_triangles, (0.76, 0.78, 0.80), 0.90)
    if gas_triangles is not None:
        add_mesh(cut, gas_triangles, (0.98, 0.32, 0.12), 0.38)
    for x, y, color in (
        (-18.0, -17.0, "#61d6ff"),
        (18.0, -17.0, "#61d6ff"),
        (-18.0, 17.0, "#ff765d"),
        (18.0, 17.0, "#ff765d"),
    ):
        sign = -1.0 if y < 0.0 else 1.0
        cut.plot([x, x], [y, y + sign * 31.0], [0.0, 88.0], color=color, linewidth=2.1)
    frame(cut, [half_triangles] + ([gas_triangles] if gas_triangles is not None else []), 18, -42)
    cut.set_title("Demi-coupe : chambre et conduits", color="white", fontweight="bold", pad=10)

    mesh = report["mesh"]
    material = report["material_candidate"]
    facts = (
        f"1 solide ferme : {mesh['watertight']}   |   {mesh['triangles']:,} triangles   |   "
        f"masse brute conditionnelle : {material['mass_kg_if_obj_unit_is_mm']:.3f} kg\n"
        "Sieges, guides, filetages et galeries d'huile : usinage apres detensionnement. "
        "Validation physique et autorisation d'impression non acquises."
    )
    figure.text(0.5, 0.045, facts, color="#d7e0e5", fontsize=10.5, ha="center", va="center")
    figure.tight_layout(rect=(0.015, 0.08, 0.985, 0.90), w_pad=0.5)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=160, facecolor=figure.get_facecolor())
    plt.close(figure)
    print(json.dumps({"image": str(args.output), "sha256": sha256(args.output), "bytes": args.output.stat().st_size}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
