#!/usr/bin/env python3
"""Render the private F42.2 diagnostic STEP without exporting its geometry."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from audit_brep_f42 import bbox, read_step
from repair_pcurves_f42_2 import TARGET_FACE_INDICES
from render_topology_map_f42_1 import frame, mapped_faces, mesh_with_face_ids


def shaded_colors(
    triangles: np.ndarray,
    face_ids: np.ndarray,
    target_faces: set[int],
    residual_faces: set[int],
) -> np.ndarray:
    bases = np.tile(np.asarray([0.47, 0.53, 0.56]), (len(triangles), 1))
    bases[np.isin(face_ids, sorted(target_faces))] = [0.96, 0.55, 0.07]
    bases[np.isin(face_ids, sorted(residual_faces))] = [0.92, 0.10, 0.18]
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    lengths = np.linalg.norm(normals, axis=1)
    normals[lengths > 0.0] /= lengths[lengths > 0.0, None]
    light = np.asarray([0.32, -0.45, 0.83])
    light /= np.linalg.norm(light)
    intensity = 0.48 + 0.52 * np.abs(normals @ light)
    return np.clip(bases * intensity[:, None], 0.0, 1.0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", type=Path, required=True)
    parser.add_argument("--private-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.private_report.read_text(encoding="utf-8"))
    shape, _ = read_step(args.step)
    triangles, face_ids = mesh_with_face_ids(shape)
    target_faces = set(TARGET_FACE_INDICES)
    residual_faces = {
        item["face_index_private"]
        for item in report["residual_pair_chord_deviation"]["pairs_private"]
    }
    colors = shaded_colors(triangles, face_ids, target_faces, residual_faces)
    bounds = bbox(shape)

    figure = plt.figure(figsize=(16, 9), facecolor="#10161a")
    axis = figure.add_subplot(1, 2, 1, projection="3d", facecolor="#10161a")
    axis.add_collection3d(
        Poly3DCollection(triangles, facecolor=colors, edgecolor="none", alpha=1.0)
    )
    frame(axis, bounds, 22, -58)
    axis.set_title("Candidat privé réouvert — diagnostic seulement", color="white", fontsize=14)

    chart = figure.add_subplot(1, 2, 2, facecolor="#10161a")
    labels = ["F42.1\nround-trip", "25 faces\navant export", "Extension\navant export", "F42.2\nround-trip"]
    values = [
        248,
        report["mapped_25_face_trial"]["residual_pcurve_faults"]["result_count"],
        report["pre_export_full_BOPAlgo"]["result_count"],
        report["roundtrip"]["full_BOPAlgo"]["result_count"],
    ]
    bars = chart.bar(labels, values, color=["#88949a", "#f08a13", "#d63b42", "#d63b42"])
    chart.set_ylabel("Défauts BOPAlgo", color="white")
    chart.tick_params(colors="white")
    chart.spines[["top", "right"]].set_visible(False)
    chart.spines[["left", "bottom"]].set_color("#718089")
    chart.grid(axis="y", color="#334047", linewidth=0.7, alpha=0.6)
    chart.set_axisbelow(True)
    for bar, value in zip(bars, values):
        chart.text(bar.get_x() + bar.get_width() / 2, value + 5, str(value), ha="center", color="white", fontsize=12)
    chart.text(
        0.02,
        0.93,
        "Écart courbe–surface résiduel max\n0,1169 unité > limite 0,02",
        transform=chart.transAxes,
        color="#ff6970",
        fontsize=14,
        va="top",
        fontweight="bold",
    )
    chart.set_ylim(0, max(values) * 1.22)

    figure.legend(
        handles=[
            Patch(color="#78888f", label="surface non ciblée"),
            Patch(color="#f58c12", label="faces de la carte F42.1"),
            Patch(color="#eb1a2d", label="faces des quatre couples résiduels avant export"),
        ],
        loc="lower center",
        ncol=3,
        facecolor="#182126",
        edgecolor="#34434b",
        labelcolor="white",
        bbox_to_anchor=(0.5, 0.07),
    )
    figure.suptitle(
        "F42.2 — REPROJECTION P-COURBES REJETÉE, PEAU 3D INCHANGÉE",
        color="white",
        fontsize=20,
        fontweight="bold",
        y=0.97,
    )
    figure.text(
        0.5,
        0.025,
        "BRepCheck seul reste valide, mais BOPAlgo et Gmsh ferment la porte CAE/fabrication",
        color="#f0f3f5",
        fontsize=12,
        ha="center",
    )
    figure.subplots_adjust(left=0.02, right=0.97, bottom=0.15, top=0.90, wspace=0.12)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=160, facecolor=figure.get_facecolor())
    plt.close(figure)
    print(json.dumps({"output": str(args.output), "triangle_count": int(len(triangles))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
