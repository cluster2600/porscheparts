#!/usr/bin/env python3
"""Rend le champ Von Mises F36 depuis les sorties texte CalculiX."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def parse_mesh(path: Path) -> tuple[dict[int, tuple[float, float, float]], dict[int, tuple[int, ...]]]:
    nodes: dict[int, tuple[float, float, float]] = {}
    elements: dict[int, tuple[int, ...]] = {}
    mode = ""
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("*"):
            keyword = line.split(",", 1)[0].upper()
            mode = "node" if keyword == "*NODE" else "element" if keyword == "*ELEMENT" else ""
            continue
        fields = [field.strip() for field in line.split(",")]
        if mode == "node" and len(fields) >= 4:
            nodes[int(fields[0])] = tuple(float(value) for value in fields[1:4])
        elif mode == "element" and len(fields) >= 9:
            elements[int(fields[0])] = tuple(int(value) for value in fields[1:9])
    return nodes, elements


def parse_element_stress(path: Path) -> dict[int, float]:
    result: dict[int, float] = {}
    active = False
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        lower = raw.lower()
        if "stresses" in lower and "sxx" in lower:
            active = True
            continue
        if active and ("displacements" in lower or raw.startswith(" stresses")):
            if "displacements" in lower:
                break
        fields = raw.split()
        if not active or len(fields) < 8:
            continue
        try:
            tag = int(fields[0])
            int(fields[1])
            sxx, syy, szz, sxy, sxz, syz = map(float, fields[2:8])
        except ValueError:
            continue
        von_mises = math.sqrt(
            0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
            + 3.0 * (sxy * sxy + sxz * sxz + syz * syz)
        )
        result[tag] = max(result.get(tag, 0.0), von_mises)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inp", type=Path, required=True)
    parser.add_argument("--dat", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    nodes, elements = parse_mesh(args.inp)
    stresses = parse_element_stress(args.dat)
    tags = sorted(set(elements) & set(stresses))
    centres = np.asarray(
        [np.mean(np.asarray([nodes[node] for node in elements[tag]]), axis=0) for tag in tags]
    )
    values = np.asarray([stresses[tag] for tag in tags])
    report = json.loads(args.report.read_text(encoding="utf-8"))
    p99 = report["results"]["von_mises_p99_mpa"]
    clipped = np.minimum(values, p99)
    peak = np.argmax(values)

    figure, axes = plt.subplots(1, 2, figsize=(16, 7), facecolor="#0b1118")
    figure.suptitle("F36-013 — champ structural CalculiX, charge turbo", color="white", fontsize=21, fontweight="bold")
    views = ((0, 1, "Vue deck", "X", "Y"), (1, 2, "Vue latérale", "Y", "Z"))
    plot = None
    for view_index, (axis, (a, b, title, xlabel, ylabel)) in enumerate(zip(axes, views)):
        axis.set_facecolor("#101b24")
        plot = axis.scatter(centres[:, a], centres[:, b], c=clipped, s=2.0, cmap="inferno", vmin=0.0, vmax=p99, rasterized=True)
        axis.scatter(
            centres[peak, a], centres[peak, b], marker="x", s=90,
            color="#5de0ff", linewidths=2,
            label="pic local à l'appui" if view_index == 0 else None,
        )
        axis.set_aspect("equal", adjustable="box")
        axis.set_title(title, color="white", fontweight="bold")
        axis.set_xlabel(f"{xlabel} (unité OBJ; mm supposé)", color="#d4dde4")
        axis.set_ylabel(f"{ylabel} (unité OBJ; mm supposé)", color="#d4dde4")
        axis.tick_params(colors="#d4dde4")
        if view_index == 0:
            axis.legend(facecolor="#101b24", labelcolor="white", fontsize=9, loc="upper right")
    colorbar = figure.colorbar(plot, ax=axes, fraction=0.025, pad=0.025)
    colorbar.set_label("Von Mises écrêté au p99 (MPa)", color="#d4dde4")
    colorbar.ax.tick_params(colors="#d4dde4")
    results = report["results"]
    figure.text(
        0.5,
        0.025,
        f"p95 {results['von_mises_p95_mpa']:.1f} MPa · p99 {p99:.1f} MPa · "
        f"pic {results['von_mises_max_mpa']:.1f} MPa · déplacement {results['maximum_displacement_mm']:.3f} mm · "
        "pic non libéré: contact/précharge/congé non modélisés",
        color="#d4dde4",
        ha="center",
        fontsize=10,
    )
    figure.subplots_adjust(left=0.06, right=0.91, bottom=0.13, top=0.88, wspace=0.18)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=180, facecolor=figure.get_facecolor())
    plt.close(figure)
    print(json.dumps({"status": "rendered", "elements": len(tags), "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
