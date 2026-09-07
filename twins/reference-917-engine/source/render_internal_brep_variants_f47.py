#!/usr/bin/env python3
"""Rend les candidats internes F47 depuis les STEP prives, sans les publier.

Les images produites sont les seules sorties publiables de ce script. La peau
externe vient du STEP F43 verrouille; les noyaux gaz/huile et les composants
restent des geometries analytiques candidates et sont identifies comme tels.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from OCP.BRep import BRep_Tool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.TopAbs import TopAbs_FACE
from OCP.TopExp import TopExp
from OCP.TopLoc import TopLoc_Location
from OCP.TopTools import TopTools_IndexedMapOfShape
from OCP.TopoDS import TopoDS


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "twins/reference-917-engine/source"
sys.path.insert(0, str(SOURCE))

from audit_brep_f42 import read_step  # noqa: E402


BACKGROUND = "#0c151b"
HEAD = np.asarray([0.70, 0.73, 0.72])
GAS = np.asarray([0.96, 0.32, 0.12])
OIL = np.asarray([0.10, 0.55, 0.95])
COMPONENT = np.asarray([0.94, 0.72, 0.18])


def triangles_from_step(path: Path, deflection: float = 0.8) -> np.ndarray:
    shape, _ = read_step(path)
    mesher = BRepMesh_IncrementalMesh(shape, deflection, False, 0.45, True)
    mesher.Perform()
    faces = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(shape, TopAbs_FACE, faces)
    triangles: list[np.ndarray] = []
    for face_index in range(1, faces.Extent() + 1):
        face = TopoDS.Face_s(faces.FindKey(face_index))
        location = TopLoc_Location()
        mesh = BRep_Tool.Triangulation_s(face, location)
        if mesh is None:
            continue
        transform = location.Transformation()
        for triangle_index in range(1, mesh.NbTriangles() + 1):
            nodes = mesh.Triangle(triangle_index).Get()
            triangles.append(
                np.asarray(
                    [mesh.Node(node).Transformed(transform).Coord() for node in nodes],
                    dtype=float,
                )
            )
    if not triangles:
        raise RuntimeError(f"aucun_triangle:{path}")
    return np.asarray(triangles)


def bounds_of(*triangle_sets: np.ndarray) -> list[float]:
    points = np.concatenate([triangles.reshape(-1, 3) for triangles in triangle_sets])
    return [
        float(points[:, 0].min()),
        float(points[:, 1].min()),
        float(points[:, 2].min()),
        float(points[:, 0].max()),
        float(points[:, 1].max()),
        float(points[:, 2].max()),
    ]


def frame(axis, bounds: list[float], elev: float, azim: float) -> None:
    sizes = [bounds[index + 3] - bounds[index] for index in range(3)]
    longest = max(sizes)
    centres = [(bounds[index] + bounds[index + 3]) * 0.5 for index in range(3)]
    half = 0.54 * longest
    axis.set_xlim(centres[0] - half, centres[0] + half)
    axis.set_ylim(centres[1] - half, centres[1] + half)
    axis.set_zlim(max(-8.0, bounds[2] - 4.0), min(90.0, bounds[5] + 4.0))
    axis.set_box_aspect((1.0, 1.0, 0.68))
    axis.view_init(elev=elev, azim=azim)
    axis.set_axis_off()


def shaded_colors(triangles: np.ndarray, base: np.ndarray, alpha: float) -> np.ndarray:
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    lengths = np.linalg.norm(normals, axis=1)
    normals[lengths > 0] /= lengths[lengths > 0, None]
    light = np.asarray([0.35, -0.48, 0.80])
    light /= np.linalg.norm(light)
    intensity = 0.44 + 0.56 * np.abs(normals @ light)
    rgb = np.clip(base[None, :] * intensity[:, None], 0.0, 1.0)
    return np.column_stack((rgb, np.full(len(rgb), alpha)))


def add_mesh(axis, triangles: np.ndarray, base: np.ndarray, alpha: float = 1.0, maximum: int = 160000) -> None:
    stride = max(1, int(np.ceil(len(triangles) / maximum)))
    shown = triangles[::stride]
    axis.add_collection3d(
        Poly3DCollection(
            shown,
            facecolors=shaded_colors(shown, base, alpha),
            edgecolors="none",
            linewidths=0.0,
            alpha=alpha,
        )
    )


def clipped(triangles: np.ndarray, x_limit: float) -> np.ndarray:
    return triangles[np.mean(triangles[:, :, 0], axis=1) <= x_limit]


def render_four_views(data: dict[str, dict[str, np.ndarray]], output: Path) -> None:
    figure = plt.figure(figsize=(16, 11), facecolor=BACKGROUND)
    panels = (
        ("2V", "Face admission — ouvertures candidates", 18, -90),
        ("2V", "Face chambre/deck — 2 soupapes", -74, -90),
        ("4V", "Face admission — ouvertures candidates", 18, -90),
        ("4V", "Face chambre/deck — 4 soupapes", -74, -90),
    )
    for index, (variant, title, elev, azim) in enumerate(panels, start=1):
        axis = figure.add_subplot(2, 2, index, projection="3d", facecolor=BACKGROUND)
        head = data[variant]["head"]
        add_mesh(axis, head, HEAD)
        frame(axis, bounds_of(head), elev, azim)
        axis.set_title(title, color="white", fontsize=14, pad=5, fontweight="bold")
    figure.suptitle(
        "F47 — MEME PEAU F43 NON OVALE · CANDIDATS INTERNES 2V / 4V",
        color="white",
        fontsize=21,
        fontweight="bold",
        y=0.98,
    )
    figure.text(
        0.5,
        0.025,
        "Peau externe issue des 44 contours du scan, inchangée · géométries internes hypothétiques · impression et démarrage interdits",
        color="#e5ebef",
        fontsize=12,
        ha="center",
    )
    figure.subplots_adjust(left=0.01, right=0.99, bottom=0.06, top=0.92, hspace=0.05, wspace=0.01)
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=160, facecolor=figure.get_facecolor())
    plt.close(figure)


def render_sections(data: dict[str, dict[str, np.ndarray]], output: Path) -> None:
    figure = plt.figure(figsize=(16, 9), facecolor=BACKGROUND)
    for index, (variant, cut_x) in enumerate((("2V", 0.0), ("4V", -19.5)), start=1):
        axis = figure.add_subplot(1, 2, index, projection="3d", facecolor=BACKGROUND)
        head = clipped(data[variant]["head"], cut_x)
        gas = clipped(data[variant]["gas"], cut_x + 0.20)
        oil = clipped(data[variant]["oil"], cut_x + 0.20)
        components = clipped(data[variant]["components"], cut_x + 0.20)
        add_mesh(axis, head, HEAD, alpha=0.88)
        add_mesh(axis, gas, GAS, alpha=0.74, maximum=70000)
        add_mesh(axis, oil, OIL, alpha=0.88, maximum=30000)
        add_mesh(axis, components, COMPONENT, alpha=0.86, maximum=40000)
        frame(axis, bounds_of(data[variant]["head"]), 14, -52)
        axis.set_title(
            f"{variant} — demi-coupe x ≤ {cut_x:g} unité scan",
            color="white",
            fontsize=15,
            fontweight="bold",
        )
    legend = [
        Line2D([0], [0], marker="s", color="none", markerfacecolor=HEAD, markersize=12, label="culasse F43 évidée"),
        Line2D([0], [0], marker="s", color="none", markerfacecolor=GAS, markersize=12, label="noyau gaz fermé (caps = frontières ouvertes)"),
        Line2D([0], [0], marker="s", color="none", markerfacecolor=OIL, markersize=12, label="noyau huile séparé"),
        Line2D([0], [0], marker="s", color="none", markerfacecolor=COMPONENT, markersize=12, label="sièges / guides / soupapes séparés"),
    ]
    figure.legend(handles=legend, loc="lower center", ncol=4, frameon=False, labelcolor="white", fontsize=11)
    figure.suptitle(
        "F47 — COUPES CANDIDATES, PAS UNE PREUVE DE FABRICATION",
        color="white",
        fontsize=21,
        fontweight="bold",
        y=0.97,
    )
    figure.text(
        0.5,
        0.075,
        "Conduits circulaires droits et galeries = hypothèses F47 · interfaces Porsche, épaisseur, drainage et poudre non validés",
        color="#e5ebef",
        fontsize=11,
        ha="center",
    )
    figure.subplots_adjust(left=0.01, right=0.99, bottom=0.14, top=0.91, wspace=0.01)
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=160, facecolor=figure.get_facecolor())
    plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--four-views", type=Path, required=True)
    parser.add_argument("--sections", type=Path, required=True)
    args = parser.parse_args()
    data: dict[str, dict[str, np.ndarray]] = {}
    for variant in ("2V", "4V"):
        slug = variant.lower()
        prefix = args.private_dir / f"917-head-{slug}-f47"
        data[variant] = {
            "head": triangles_from_step(prefix.with_name(prefix.name + "-head.step")),
            "gas": triangles_from_step(prefix.with_name(prefix.name + "-gas-core.step"), 0.45),
            "oil": triangles_from_step(prefix.with_name(prefix.name + "-oil-core.step"), 0.35),
            "components": triangles_from_step(prefix.with_name(prefix.name + "-components.step"), 0.35),
        }
    render_four_views(data, args.four_views)
    render_sections(data, args.sections)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
