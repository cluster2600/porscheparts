#!/usr/bin/env python3
"""Rend les maillages fluides F48 a partir des MSH analytiques locaux."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import gmsh
import matplotlib.pyplot as plt
from matplotlib import cm, colors
from matplotlib.lines import Line2D
from mpl_toolkits.mplot3d.art3d import Line3DCollection, Poly3DCollection
import numpy as np


BACKGROUND = "#08131b"
PATCH_COLORS = {
    "intake": "#20c77a",
    "exhaust": "#ff4b35",
    "valve": "#ffd43b",
    "chamber": "#f49b21",
    "deck": "#36c4d8",
    "bore": "#4277f5",
    "walls": "#a8b0b5",
    "oil_x_minus": "#1b8ef2",
    "oil_x_plus": "#1b8ef2",
    "oil_cleanout": "#58c7ff",
    "oil_walls": "#729fbd",
}


@dataclass
class Mesh:
    nodes: np.ndarray
    surface_triangles: np.ndarray
    surface_patch: list[str]
    tetrahedra: np.ndarray
    quality: np.ndarray


def element_connectivity(element_type: int, node_tags: np.ndarray, tag_to_index: dict[int, int]) -> np.ndarray:
    _, dimension, _, count, _, _ = gmsh.model.mesh.getElementProperties(element_type)
    if dimension not in (2, 3):
        return np.empty((0, 0), dtype=int)
    reshaped = np.asarray(node_tags, dtype=np.int64).reshape(-1, count)
    return np.asarray([[tag_to_index[int(tag)] for tag in row] for row in reshaped], dtype=int)


def load_mesh(path: Path) -> Mesh:
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.open(str(path))
        node_tags, coordinates, _ = gmsh.model.mesh.getNodes()
        nodes = np.asarray(coordinates, dtype=float).reshape(-1, 3)
        tag_to_index = {int(tag): index for index, tag in enumerate(node_tags)}
        triangles: list[np.ndarray] = []
        patches: list[str] = []
        for dimension, physical_tag in gmsh.model.getPhysicalGroups(2):
            name = gmsh.model.getPhysicalName(dimension, physical_tag)
            for entity in gmsh.model.getEntitiesForPhysicalGroup(dimension, physical_tag):
                types, _, node_tags_by_type = gmsh.model.mesh.getElements(2, int(entity))
                for element_type, element_nodes in zip(types, node_tags_by_type):
                    connectivity = element_connectivity(int(element_type), element_nodes, tag_to_index)
                    if connectivity.shape[1] < 3:
                        continue
                    triangles.append(connectivity[:, :3])
                    patches.extend([name] * len(connectivity))
        tet_connectivity: list[np.ndarray] = []
        tet_tags: list[int] = []
        types, tags_by_type, node_tags_by_type = gmsh.model.mesh.getElements(3)
        for element_type, element_tags, element_nodes in zip(types, tags_by_type, node_tags_by_type):
            properties = gmsh.model.mesh.getElementProperties(int(element_type))
            if not properties[0].startswith("Tetrahedron"):
                continue
            connectivity = element_connectivity(int(element_type), element_nodes, tag_to_index)
            tet_connectivity.append(connectivity[:, :4])
            tet_tags.extend(int(tag) for tag in element_tags)
        tetrahedra = np.concatenate(tet_connectivity)
        quality = np.asarray(gmsh.model.mesh.getElementQualities(tet_tags, "minSICN"), dtype=float)
        return Mesh(
            nodes=nodes,
            surface_triangles=np.concatenate(triangles),
            surface_patch=patches,
            tetrahedra=tetrahedra,
            quality=quality,
        )
    finally:
        gmsh.finalize()


def frame(axis, nodes: np.ndarray, elev: float, azim: float) -> None:
    minimum = nodes.min(axis=0)
    maximum = nodes.max(axis=0)
    centre = 0.5 * (minimum + maximum)
    span = maximum - minimum
    half = 0.54 * max(span)
    axis.set_xlim(centre[0] - half, centre[0] + half)
    axis.set_ylim(centre[1] - half, centre[1] + half)
    axis.set_zlim(centre[2] - 0.44 * max(span), centre[2] + 0.44 * max(span))
    axis.set_box_aspect((1.0, 1.0, 0.80))
    axis.view_init(elev=elev, azim=azim)
    axis.set_axis_off()


def add_surface(axis, mesh: Mesh, alpha: float = 0.92, maximum: int = 80000) -> None:
    triangles = mesh.nodes[mesh.surface_triangles]
    stride = max(1, int(np.ceil(len(triangles) / maximum)))
    shown = triangles[::stride]
    patch_colors = np.asarray([colors.to_rgba(PATCH_COLORS.get(name, "#cccccc"), alpha) for name in mesh.surface_patch])[::stride]
    axis.add_collection3d(
        Poly3DCollection(shown, facecolors=patch_colors, edgecolors="none", linewidths=0.0)
    )


def section_polygons(mesh: Mesh, x_plane: float) -> tuple[list[np.ndarray], np.ndarray]:
    edges = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))
    polygons: list[np.ndarray] = []
    qualities: list[float] = []
    for connectivity, quality in zip(mesh.tetrahedra, mesh.quality):
        vertices = mesh.nodes[connectivity]
        signed = vertices[:, 0] - x_plane
        if signed.min() > 0.0 or signed.max() < 0.0:
            continue
        points: list[np.ndarray] = []
        for first, second in edges:
            da, db = signed[first], signed[second]
            if da == 0.0:
                points.append(vertices[first])
            if da * db < 0.0:
                ratio = -da / (db - da)
                points.append(vertices[first] + ratio * (vertices[second] - vertices[first]))
        unique: list[np.ndarray] = []
        for point in points:
            if not any(np.linalg.norm(point - other) < 1.0e-8 for other in unique):
                unique.append(point)
        if len(unique) < 3:
            continue
        polygon = np.asarray(unique)
        centre = polygon.mean(axis=0)
        angles = np.arctan2(polygon[:, 2] - centre[2], polygon[:, 1] - centre[1])
        polygons.append(polygon[np.argsort(angles)])
        qualities.append(float(quality))
    return polygons, np.asarray(qualities)


def add_section(axis, mesh: Mesh, x_plane: float) -> None:
    polygons, quality = section_polygons(mesh, x_plane)
    normalizer = colors.Normalize(vmin=0.2, vmax=1.0, clip=True)
    collection = Poly3DCollection(
        polygons,
        facecolors=cm.viridis(normalizer(quality)),
        edgecolors=(0.02, 0.06, 0.08, 0.42),
        linewidths=0.22,
    )
    axis.add_collection3d(collection)
    boundary = mesh.nodes[mesh.surface_triangles]
    kept = boundary[np.mean(boundary[:, :, 0], axis=1) <= x_plane]
    stride = max(1, int(np.ceil(len(kept) / 50000)))
    axis.add_collection3d(
        Poly3DCollection(
            kept[::stride],
            facecolors=(0.60, 0.66, 0.70, 0.16),
            edgecolors=(0.82, 0.88, 0.91, 0.08),
            linewidths=0.08,
        )
    )


def render_overview(two: Mesh, four: Mesh, output: Path) -> None:
    figure = plt.figure(figsize=(16, 10), facecolor=BACKGROUND)
    panels = ((two, "2V — admission / échappement", 19, -62), (two, "2V — deck / chambre", -68, -90), (four, "4V — admission / échappement", 19, -62), (four, "4V — deck / chambre", -68, -90))
    for index, (mesh, title, elev, azim) in enumerate(panels, start=1):
        axis = figure.add_subplot(2, 2, index, projection="3d", facecolor=BACKGROUND)
        add_surface(axis, mesh)
        frame(axis, mesh.nodes, elev, azim)
        axis.set_title(title, color="white", fontsize=14, fontweight="bold")
    handles = [Line2D([0], [0], marker="s", color="none", markerfacecolor=color, markersize=11, label=name) for name, color in PATCH_COLORS.items() if not name.startswith("oil")]
    figure.legend(handles=handles, loc="lower center", ncol=7, frameon=False, labelcolor="white", fontsize=10)
    figure.suptitle("F48 — DOMAINES FLUIDES NATIFS, PATCHES CFD NOMMÉS", color="white", fontsize=21, fontweight="bold")
    figure.text(0.5, 0.055, "Cylindres circulaires fonctionnels uniquement · aucune peau de scan, enveloppe solide ou proxy", ha="center", color="#dbe5eb", fontsize=12)
    figure.subplots_adjust(left=0.01, right=0.99, bottom=0.12, top=0.91, hspace=0.03, wspace=0.01)
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=160, facecolor=figure.get_facecolor())
    plt.close(figure)


def render_sections(two: Mesh, four: Mesh, oil: Mesh, output: Path) -> None:
    figure = plt.figure(figsize=(18, 8), facecolor=BACKGROUND)
    panels = ((two, "2V — coupe maillage x=0", 0.0), (four, "4V — coupe maillage x=-19,5", -19.5))
    for index, (mesh, title, plane) in enumerate(panels, start=1):
        axis = figure.add_subplot(1, 3, index, projection="3d", facecolor=BACKGROUND)
        add_section(axis, mesh, plane)
        frame(axis, mesh.nodes, 11, -57)
        axis.set_title(title, color="white", fontsize=14, fontweight="bold")
    oil_axis = figure.add_subplot(1, 3, 3, projection="3d", facecolor=BACKGROUND)
    add_surface(oil_axis, oil)
    frame(oil_axis, oil.nodes, 18, -48)
    oil_axis.set_title("Huile — domaine lubrification séparé", color="white", fontsize=14, fontweight="bold")
    figure.suptitle("F48 — COUPES minSICN ET DOMAINE HUILE NON-REFROIDISSANT", color="white", fontsize=20, fontweight="bold")
    scalar = cm.ScalarMappable(norm=colors.Normalize(vmin=0.2, vmax=1.0), cmap=cm.viridis)
    bar = figure.colorbar(scalar, ax=figure.axes[:2], fraction=0.018, pad=0.015, shrink=0.68)
    bar.set_label("minSICN des tétraèdres coupés", color="white")
    bar.ax.tick_params(colors="white")
    figure.text(0.5, 0.04, "Maillages medium · 0 tétraèdre inversé · géométrie CFD de recherche, sans preuve de fitment/CHT/fabrication", ha="center", color="#dbe5eb", fontsize=11)
    figure.subplots_adjust(left=0.01, right=0.96, bottom=0.10, top=0.88, wspace=0.02)
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=160, facecolor=figure.get_facecolor())
    plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--two-valve", type=Path, required=True)
    parser.add_argument("--four-valve", type=Path, required=True)
    parser.add_argument("--oil", type=Path, required=True)
    parser.add_argument("--overview", type=Path, required=True)
    parser.add_argument("--sections", type=Path, required=True)
    args = parser.parse_args()
    two = load_mesh(args.two_valve)
    four = load_mesh(args.four_valve)
    oil = load_mesh(args.oil)
    render_overview(two, four, args.overview)
    render_sections(two, four, oil, args.sections)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
