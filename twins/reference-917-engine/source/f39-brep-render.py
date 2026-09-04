#!/usr/bin/env python3
"""Genere les vues F39 depuis le STL analytique local et le scan local."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.path import Path as MplPath
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import trimesh


BACKGROUND = "#08131b"
PANEL = "#10232d"
ALUMINIUM = np.asarray([0.74, 0.77, 0.78])
GOLD = "#f4b942"
CYAN = "#52d3ff"


def load_mesh(path: Path) -> trimesh.Trimesh:
    mesh = trimesh.load(path, force="mesh", process=True)
    if not isinstance(mesh, trimesh.Trimesh) or len(mesh.faces) == 0:
        raise RuntimeError(f"maillage absent: {path}")
    return mesh


def triangles_and_colours(mesh: trimesh.Trimesh, maximum_faces: int) -> tuple[np.ndarray, np.ndarray]:
    if len(mesh.faces) <= maximum_faces:
        keep = np.arange(len(mesh.faces))
    else:
        keep = np.linspace(0, len(mesh.faces) - 1, maximum_faces, dtype=int)
    triangles = mesh.vertices[mesh.faces[keep]]
    normals = mesh.face_normals[keep]
    light = np.asarray([0.35, -0.45, 0.82])
    light /= np.linalg.norm(light)
    intensity = np.clip(0.35 + 0.65 * np.abs(normals @ light), 0.25, 1.0)
    colours = np.clip(ALUMINIUM[None, :] * intensity[:, None], 0.0, 1.0)
    return triangles, colours


def frame(axis, meshes: list[trimesh.Trimesh], elev: float, azim: float) -> None:
    minimum = np.min(np.vstack([mesh.bounds[0] for mesh in meshes]), axis=0)
    maximum = np.max(np.vstack([mesh.bounds[1] for mesh in meshes]), axis=0)
    centre = 0.5 * (minimum + maximum)
    radius = 0.55 * float(np.max(maximum - minimum))
    axis.set_xlim(centre[0] - radius, centre[0] + radius)
    axis.set_ylim(centre[1] - radius, centre[1] + radius)
    axis.set_zlim(centre[2] - 0.58 * radius, centre[2] + 0.58 * radius)
    axis.set_box_aspect((1.0, 1.0, 0.72))
    axis.view_init(elev=elev, azim=azim)
    axis.set_axis_off()


def exterior(mesh: trimesh.Trimesh, report: dict, output: Path) -> None:
    figure = plt.figure(figsize=(14, 9), facecolor=BACKGROUND)
    axis = figure.add_subplot(111, projection="3d", facecolor=BACKGROUND)
    triangles, colours = triangles_and_colours(mesh, 90000)
    axis.add_collection3d(Poly3DCollection(triangles, facecolors=colours, edgecolor="none", linewidth=0.0))
    frame(axis, [mesh], elev=23.0, azim=-52.0)
    figure.suptitle("Porsche 917 — culasse F39 scan-only", color="white", fontsize=23, fontweight="bold", y=0.965)
    figure.text(0.5, 0.915, "B-Rep analytique OCCT · 4 soupapes · 12 ailettes · vue extérieure", ha="center", color="#c9d8df", fontsize=13)
    geometry = report["geometry"]
    quality = report["volume_mesh"]
    note = (
        f"1 solide STEP réimporté  |  peau {geometry['boundary_shell_components']} composante  |  "
        f"Gmsh {quality['volume_elements']:,} tétraèdres\n"
        "Convention: 1 unité scan = 1 mm · ajustement OEM et impression métal NON autorisés"
    )
    figure.text(0.5, 0.045, note, ha="center", va="bottom", color="#dce7eb", fontsize=11,
                bbox={"facecolor": PANEL, "edgecolor": "#2c4b58", "boxstyle": "round,pad=0.7"})
    figure.savefig(output, dpi=180, facecolor=figure.get_facecolor(), bbox_inches="tight")
    plt.close(figure)


def section(mesh: trimesh.Trimesh, output: Path) -> None:
    x_cut = -18.0
    y_min, z_min = mesh.bounds[0, 1], mesh.bounds[0, 2]
    y_max, z_max = mesh.bounds[1, 1], mesh.bounds[1, 2]
    y = np.linspace(y_min - 3.0, y_max + 3.0, 600)
    z = np.linspace(z_min - 3.0, z_max + 3.0, 330)
    yy, zz = np.meshgrid(y, z)
    cut = mesh.section(plane_origin=[x_cut, 0.0, 0.0], plane_normal=[1.0, 0.0, 0.0])
    if cut is None:
        raise RuntimeError("coupe_X_moins_18_absente")
    query = np.column_stack((yy.ravel(), zz.ravel()))
    material = np.zeros(len(query), dtype=bool)
    loops: list[np.ndarray] = []
    for polyline in cut.discrete:
        yz = np.asarray(polyline, dtype=float)[:, [1, 2]]
        if len(yz) >= 4 and np.linalg.norm(yz[0] - yz[-1]) < 1.0e-3:
            loops.append(yz)
            material ^= MplPath(yz, closed=True).contains_points(query)
    material = material.reshape(yy.shape)

    figure, axis = plt.subplots(figsize=(15, 8), facecolor=BACKGROUND)
    axis.set_facecolor(BACKGROUND)
    cmap = LinearSegmentedColormap.from_list("f39_section", [BACKGROUND, "#9ca9ad"])
    axis.imshow(
        material.astype(float),
        origin="lower",
        extent=[y[0], y[-1], z[0], z[-1]],
        cmap=cmap,
        vmin=0.0,
        vmax=1.0,
        interpolation="nearest",
        aspect="equal",
    )
    axis.contour(y, z, material.astype(float), levels=[0.5], colors=["#ecf6f8"], linewidths=0.65)
    for loop in loops:
        axis.plot(loop[:, 0], loop[:, 1], color="#ecf6f8", linewidth=0.5, alpha=0.9)
    axis.axvline(0.0, color="#345666", linewidth=0.7, linestyle="--", alpha=0.6)
    axis.scatter([-17.0, 17.0], [1.0, 1.0], s=45, facecolors="none", edgecolors=[CYAN, "#ff7961"], linewidths=1.5)
    axis.annotate("admission", xy=(-42, 18), xytext=(-79, 48), color=CYAN,
                  arrowprops={"arrowstyle": "->", "color": CYAN}, fontsize=11)
    axis.annotate("échappement", xy=(47, 21), xytext=(70, 51), color="#ff7961",
                  arrowprops={"arrowstyle": "->", "color": "#ff7961"}, fontsize=11)
    axis.annotate("chambre ouverte au deck", xy=(0, 4), xytext=(-3, -6), ha="center", color=GOLD,
                  arrowprops={"arrowstyle": "->", "color": GOLD}, fontsize=11)
    axis.annotate("galerie d'huile", xy=(8, 45), xytext=(28, 68), color="#9ae66e",
                  arrowprops={"arrowstyle": "->", "color": "#9ae66e"}, fontsize=11)
    axis.set_xlim(y[0], y[-1])
    axis.set_ylim(z[0], z[-1])
    axis.set_xlabel("Y — convention scan (mm)", color="#bed0d8")
    axis.set_ylabel("Z — convention scan (mm)", color="#bed0d8")
    axis.tick_params(colors="#8ea5af")
    for spine in axis.spines.values():
        spine.set_color("#2c4b58")
    axis.set_title("F39 — coupe X = −18 mm : chambre, deux axes de soupape et conduits", color="white", fontsize=18, fontweight="bold", pad=16)
    figure.text(0.5, 0.025, "Coupe calculée depuis le STL dérivé du STEP · vide noir, matière aluminium grise · dimensions conditionnelles à l’unité du scan",
                ha="center", color="#c9d8df", fontsize=10)
    figure.savefig(output, dpi=180, facecolor=figure.get_facecolor(), bbox_inches="tight")
    plt.close(figure)


def overlay(model: trimesh.Trimesh, scan: trimesh.Trimesh, output: Path) -> None:
    figure = plt.figure(figsize=(14, 9), facecolor=BACKGROUND)
    axis = figure.add_subplot(111, projection="3d", facecolor=BACKGROUND)
    scan_triangles, _ = triangles_and_colours(scan, 45000)
    model_triangles, _ = triangles_and_colours(model, 65000)
    axis.add_collection3d(Poly3DCollection(scan_triangles, facecolor=(0.22, 0.78, 1.0, 0.18), edgecolor="none"))
    axis.add_collection3d(Poly3DCollection(model_triangles, facecolor=(0.96, 0.64, 0.18, 0.53), edgecolor="none"))
    frame(axis, [model, scan], elev=23.0, azim=-52.0)
    figure.suptitle("F39 — contrôle visuel scan / reconstruction analytique", color="white", fontsize=21, fontweight="bold", y=0.965)
    figure.text(0.5, 0.91, "cyan = référence locale issue du scan · ambre = B-Rep F39", ha="center", color="#dce7eb", fontsize=13)
    figure.text(0.5, 0.045, "L'image du scan est une preuve visuelle seulement; le scan brut n'est pas publié. L'ajustement OEM reste non certifié.",
                ha="center", color="#dce7eb", fontsize=10,
                bbox={"facecolor": PANEL, "edgecolor": "#2c4b58", "boxstyle": "round,pad=0.6"})
    figure.savefig(output, dpi=180, facecolor=figure.get_facecolor(), bbox_inches="tight")
    plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--head-stl-local", type=Path, required=True)
    parser.add_argument("--f37-scan-local", type=Path, required=True)
    parser.add_argument("--build-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    head = load_mesh(args.head_stl_local)
    scan = load_mesh(args.f37_scan_local)
    report = json.loads(args.build_report.read_text(encoding="utf-8"))
    exterior(head, report, args.output / "f39-brep-exterior.png")
    section(head, args.output / "f39-brep-section.png")
    overlay(head, scan, args.output / "f39-brep-scan-overlay.png")
    print(json.dumps({"status": "rendered", "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
