#!/usr/bin/env python3
"""Rendu des contraintes CalculiX du maillage voxel LPBF F41."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import colors
import numpy as np


def parse_input(path: Path) -> tuple[dict[int, np.ndarray], dict[int, tuple[int, ...]]]:
    nodes: dict[int, np.ndarray] = {}
    elements: dict[int, tuple[int, ...]] = {}
    mode = ""
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        upper = line.upper()
        if upper.startswith("*NODE"):
            mode = "node"
            continue
        if upper.startswith("*ELEMENT"):
            mode = "element"
            continue
        if line.startswith("*"):
            mode = ""
            continue
        fields = line.split(",")
        try:
            if mode == "node" and len(fields) == 4:
                nodes[int(fields[0])] = np.asarray([float(value) for value in fields[1:4]])
            elif mode == "element" and len(fields) == 9:
                elements[int(fields[0])] = tuple(int(value) for value in fields[1:9])
        except ValueError:
            continue
    return nodes, elements


def parse_stress(path: Path) -> dict[int, float]:
    result: dict[int, float] = {}
    active = False
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        lower = raw.lower()
        if "stresses" in lower and "sxx" in lower:
            active = True
            continue
        if "displacements" in lower:
            active = False
        if not active:
            continue
        fields = raw.split()
        if len(fields) < 8:
            continue
        try:
            element = int(fields[0]); int(fields[1])
            sxx, syy, szz, sxy, sxz, syz = map(float, fields[2:8])
        except ValueError:
            continue
        von_mises = math.sqrt(
            0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
            + 3.0 * (sxy * sxy + sxz * sxz + syz * syz)
        )
        result[element] = max(von_mises, result.get(element, 0.0))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--dat", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    nodes, elements = parse_input(args.input)
    stress = parse_stress(args.dat)
    common = sorted(set(elements) & set(stress))
    centroids = np.asarray([np.mean([nodes[tag] for tag in elements[element]], axis=0) for element in common])
    values = np.asarray([stress[element] for element in common])
    p99 = float(np.quantile(values, 0.99))
    normalizer = colors.Normalize(vmin=0.0, vmax=max(p99, 1.0e-9), clip=True)
    color = plt.get_cmap("turbo")(normalizer(values))
    report = json.loads(args.report.read_text(encoding="utf-8"))

    figure = plt.figure(figsize=(16, 9), facecolor="#07131b")
    figure.suptitle("F41 — DISTORSION LPBF CALCULIX, ECRAN PLAQUE BLOQUEE", color="white", fontsize=19, fontweight="bold")
    for position, (elev, azim, title) in enumerate(((24, -55, "Contraintes de von Mises — isometrique"), (5, -90, "Contraintes — vue laterale")), start=1):
        axis = figure.add_subplot(1, 3, position, projection="3d", facecolor="#0d202b")
        axis.scatter(centroids[:, 0], centroids[:, 1], centroids[:, 2], c=color, s=2.0, marker="s", linewidths=0)
        axis.set_box_aspect(np.ptp(centroids, axis=0))
        axis.view_init(elev=elev, azim=azim)
        axis.set_axis_off()
        axis.set_title(title, color="white", fontweight="bold")
    scalar = plt.cm.ScalarMappable(norm=normalizer, cmap="turbo")
    bar = figure.colorbar(scalar, ax=figure.axes[:2], fraction=0.025, pad=0.01)
    bar.set_label("MPa, echelle tronquee au p99", color="white")
    bar.ax.tick_params(colors="white")

    chart = figure.add_subplot(1, 3, 3, facecolor="#0d202b")
    cases = report["cases"]
    labels = [f"{case['pitch_mm']:g} mm" for case in cases]
    p95 = [case["results"]["von_mises_p95_mpa"] for case in cases]
    displacement = [case["results"]["maximum_displacement_mm"] for case in cases]
    x = np.arange(len(cases))
    chart.bar(x - 0.18, p95, width=0.36, color="#f09a3e", label="contrainte p95 (MPa)")
    secondary = chart.twinx()
    secondary.bar(x + 0.18, displacement, width=0.36, color="#60bed8", label="deplacement max (mm)")
    chart.set_xticks(x, labels)
    chart.set_ylabel("MPa", color="#f09a3e")
    secondary.set_ylabel("mm", color="#60bed8")
    chart.tick_params(colors="#c9d5dc")
    secondary.tick_params(colors="#c9d5dc")
    chart.set_title("Etude de maillage 5 / 4 / 3 mm", color="white", fontweight="bold")
    chart.grid(axis="y", alpha=0.18)
    handles_a, labels_a = chart.get_legend_handles_labels()
    handles_b, labels_b = secondary.get_legend_handles_labels()
    chart.legend(handles_a + handles_b, labels_a + labels_b, loc="upper left", facecolor="#0d202b", labelcolor="white", fontsize=8)
    for axis in (chart, secondary):
        for spine in axis.spines.values():
            spine.set_color("#35505e")

    finest = cases[-1]["results"]
    figure.text(
        0.5,
        0.045,
        f"3 mm : p95 {finest['von_mises_p95_mpa']:.1f} MPa · p99 {finest['von_mises_p99_mpa']:.1f} MPa · déplacement max {finest['maximum_displacement_mm']:.3f} mm. "
        "Retrait isotrope 0,25 % supposé; carte matière et calibration machine absentes.",
        color="#efc36a",
        ha="center",
        fontsize=10,
    )
    figure.subplots_adjust(left=0.02, right=0.94, top=0.90, bottom=0.10, wspace=0.18)
    figure.savefig(args.output, dpi=170, facecolor=figure.get_facecolor())
    plt.close(figure)
    print(json.dumps({"image": str(args.output), "elements": len(common), "stress_p99_mpa": p99}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
