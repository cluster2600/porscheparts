#!/usr/bin/env python3
"""Rendu de la carte des faces F42.1 sans exporter la geometrie privee."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from OCP.BRep import BRep_Tool
from OCP.BRepGProp import BRepGProp
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.GProp import GProp_GProps
from OCP.TopAbs import TopAbs_FACE
from OCP.TopExp import TopExp
from OCP.TopLoc import TopLoc_Location
from OCP.TopTools import TopTools_IndexedMapOfShape
from OCP.TopoDS import TopoDS

from audit_brep_f42 import bbox, read_step


def mapped_faces(shape):
    result = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(shape, TopAbs_FACE, result)
    return result


def mesh_with_face_ids(shape) -> tuple[np.ndarray, np.ndarray]:
    BRepMesh_IncrementalMesh(shape, 0.8, False, 0.45, True).Perform()
    faces = mapped_faces(shape)
    triangles: list[np.ndarray] = []
    face_ids: list[int] = []
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
            face_ids.append(face_index)
    return np.asarray(triangles), np.asarray(face_ids, dtype=int)


def colors(triangles: np.ndarray, face_ids: np.ndarray, records: dict[int, dict]) -> np.ndarray:
    bases = np.tile(np.asarray([0.49, 0.55, 0.58]), (len(triangles), 1))
    for face_id, record in records.items():
        mask = face_ids == face_id
        if record["BOP_self_intersect"]:
            bases[mask] = [0.95, 0.18, 0.12]
        elif record["BOP_invalid_curve_on_surface"]:
            bases[mask] = [1.00, 0.58, 0.08]
        else:
            bases[mask] = [0.15, 0.58, 0.95]
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    lengths = np.linalg.norm(normals, axis=1)
    normals[lengths > 0.0] /= lengths[lengths > 0.0, None]
    light = np.asarray([0.32, -0.45, 0.83])
    light /= np.linalg.norm(light)
    intensity = 0.48 + 0.52 * np.abs(normals @ light)
    return np.clip(bases * intensity[:, None], 0.0, 1.0)


def frame(axis, bounds: list[float], elev: float, azim: float) -> None:
    sizes = [bounds[index + 3] - bounds[index] for index in range(3)]
    margins = [size * 0.035 for size in sizes]
    axis.set_xlim(bounds[0] - margins[0], bounds[3] + margins[0])
    axis.set_ylim(bounds[1] - margins[1], bounds[4] + margins[1])
    axis.set_zlim(bounds[2] - margins[2], bounds[5] + margins[2])
    axis.set_box_aspect(sizes)
    axis.view_init(elev=elev, azim=azim)
    axis.set_axis_off()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", type=Path, required=True)
    parser.add_argument("--face-map", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    face_map = json.loads(args.face_map.read_text(encoding="utf-8"))
    records = {record["gmsh_surface_tag"]: record for record in face_map["faces"]}
    shape, _ = read_step(args.step)
    triangles, face_ids = mesh_with_face_ids(shape)
    face_colors = colors(triangles, face_ids, records)
    bounds = bbox(shape)
    faces = mapped_faces(shape)

    figure = plt.figure(figsize=(16, 9), facecolor="#10161a")
    axes = [
        figure.add_subplot(1, 2, 1, projection="3d", facecolor="#10161a"),
        figure.add_subplot(1, 2, 2, projection="3d", facecolor="#10161a"),
    ]
    for axis, (elev, azim) in zip(axes, ((19, -58), (56, -88))):
        axis.add_collection3d(
            Poly3DCollection(triangles, facecolor=face_colors, edgecolor="none", alpha=1.0)
        )
        frame(axis, bounds, elev, azim)
    axes[0].set_title("Vue isométrique", color="white", fontsize=15)
    axes[1].set_title("Vue haute — identifiants provisoires", color="white", fontsize=15)
    for face_id in sorted(records):
        face = TopoDS.Face_s(faces.FindKey(face_id))
        props = GProp_GProps()
        BRepGProp.SurfaceProperties_s(face, props)
        center = props.CentreOfMass()
        axes[1].text(center.X(), center.Y(), center.Z(), str(face_id), color="white", fontsize=7)
    figure.legend(
        handles=[
            Patch(color="#7d8c94", label="face non ciblée"),
            Patch(color="#ff9414", label="Gmsh + p-courbe BOP invalide"),
            Patch(color="#f22e1f", label="Gmsh + auto-intersection BOP"),
            Patch(color="#2694f2", label="Gmsh seul dans le rapprochement provisoire"),
        ],
        loc="lower center",
        ncol=4,
        facecolor="#182126",
        edgecolor="#34434b",
        labelcolor="white",
        bbox_to_anchor=(0.5, 0.075),
    )
    figure.suptitle(
        "F42.1 — 25 FACES B-SPLINE À RECONSTRUIRE, CANDIDAT REJETÉ",
        color="white",
        fontsize=20,
        fontweight="bold",
        y=0.97,
    )
    figure.text(
        0.5,
        0.035,
        "8/25 également auto-intersectées · 23/25 également p-courbes invalides · mapping de tags non persistant à confirmer",
        color="#f0f3f5",
        fontsize=12,
        ha="center",
    )
    figure.subplots_adjust(left=0.01, right=0.99, bottom=0.13, top=0.91, wspace=0.01)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=160, facecolor=figure.get_facecolor())
    plt.close(figure)
    print(json.dumps({"output": str(args.output), "triangle_count": int(len(triangles))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
