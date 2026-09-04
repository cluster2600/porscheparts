#!/usr/bin/env python3
"""Rendu diagnostique F42 directement depuis le STEP prive, sans export mesh."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from OCP.BRep import BRep_Tool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.TopAbs import TopAbs_FACE
from OCP.TopExp import TopExp
from OCP.TopLoc import TopLoc_Location
from OCP.TopTools import TopTools_IndexedMapOfShape
from OCP.TopoDS import TopoDS

from audit_brep_f42 import read_step


def triangles_from_shape(shape, deflection: float) -> np.ndarray:
    BRepMesh_IncrementalMesh(shape, deflection, False, 0.45, True).Perform()
    faces = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(shape, TopAbs_FACE, faces)
    triangles: list[np.ndarray] = []
    for face_index in range(1, faces.Extent() + 1):
        face = TopoDS.Face_s(faces.FindKey(face_index))
        location = TopLoc_Location()
        mesh = BRep_Tool.Triangulation_s(face, location)
        if mesh is None:
            continue
        transformation = location.Transformation()
        for triangle_index in range(1, mesh.NbTriangles() + 1):
            nodes = mesh.Triangle(triangle_index).Get()
            triangles.append(
                np.asarray(
                    [mesh.Node(node).Transformed(transformation).Coord() for node in nodes],
                    dtype=float,
                )
            )
    return np.asarray(triangles)


def equal_axes(axis, bounds: list[float]) -> None:
    sizes = [bounds[i + 3] - bounds[i] for i in range(3)]
    margins = [size * 0.035 for size in sizes]
    axis.set_xlim(bounds[0] - margins[0], bounds[3] + margins[0])
    axis.set_ylim(bounds[1] - margins[1], bounds[4] + margins[1])
    axis.set_zlim(bounds[2] - margins[2], bounds[5] + margins[2])
    axis.set_box_aspect(sizes)


def add_geometry(axis, triangles: np.ndarray, bounds: list[float], cut: bool) -> None:
    shown = triangles
    if cut:
        shown = shown[np.mean(shown[:, :, 0], axis=1) <= 0.0]
    stride = max(1, int(np.ceil(len(shown) / 300000)))
    shown = shown[::stride]
    normals = np.cross(shown[:, 1] - shown[:, 0], shown[:, 2] - shown[:, 0])
    lengths = np.linalg.norm(normals, axis=1)
    normals[lengths > 0.0] /= lengths[lengths > 0.0, None]
    light = np.asarray([0.32, -0.45, 0.83])
    light /= np.linalg.norm(light)
    intensity = 0.42 + 0.58 * np.abs(normals @ light)
    base = np.asarray([0.68, 0.73, 0.76])
    colors = np.clip(intensity[:, None] * base[None, :], 0.0, 1.0)
    collection = Poly3DCollection(
        shown,
        facecolor=colors,
        edgecolor="none",
        alpha=1.0,
        lightsource=None,
    )
    axis.add_collection3d(collection)
    equal_axes(axis, bounds)
    axis.view_init(elev=19, azim=-58)
    axis.set_axis_off()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--deflection", type=float, default=0.8)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    shape, _ = read_step(args.input)
    triangles = triangles_from_shape(shape, args.deflection)
    bounds = report["exact_properties"]["bbox_scan_units"]
    thickness = report["exact_sampled_thickness"]

    figure = plt.figure(figsize=(16, 9), facecolor="#10161a")
    exterior = figure.add_subplot(1, 2, 1, projection="3d", facecolor="#10161a")
    section = figure.add_subplot(1, 2, 2, projection="3d", facecolor="#10161a")
    add_geometry(exterior, triangles, bounds, cut=False)
    add_geometry(section, triangles, bounds, cut=True)
    points = np.asarray(
        [item["point_scan_units"] for item in thickness["smallest_fifty_samples"]],
        dtype=float,
    )
    cut_points = points[points[:, 0] <= 0.0]
    section.scatter(
        cut_points[:, 0], cut_points[:, 1], cut_points[:, 2],
        s=22, c="#ff453a", depthshade=False,
    )
    exterior.set_title("STEP privé — enveloppe inchangée", color="white", fontsize=15, pad=8)
    section.set_title("Demi-coupe x ≤ 0 — 50 cordes les plus faibles", color="white", fontsize=15, pad=8)
    figure.suptitle(
        "F42 — AUDIT B-REP OCCT, VERDICT FAIL-CLOSED",
        color="white",
        fontsize=21,
        fontweight="bold",
        y=0.97,
    )
    figure.text(
        0.5,
        0.055,
        (
            f"1 solide / 1 coque · BRepCheck exact valide · BOPAlgo: 9 auto-intersections + "
            f"238 p-courbes invalides\n"
            f"épaisseur exacte échantillonnée: min {thickness['minimum_scan_units']:.4f}, "
            f"p01 {thickness['p01_scan_units']:.4f}, "
            f"{100.0 * thickness['resolved_area_weighted_fraction_below_threshold']:.2f}% "
            "de surface résolue sous 1,5 unité · aucune réparation / aucune autorisation d'imprimer"
        ),
        color="#f0f3f5",
        fontsize=12,
        ha="center",
        va="center",
    )
    figure.subplots_adjust(left=0.01, right=0.99, bottom=0.1, top=0.91, wspace=0.01)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=160, facecolor=figure.get_facecolor())
    plt.close(figure)
    print(json.dumps({"output": str(args.output), "triangles_read": int(len(triangles))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
