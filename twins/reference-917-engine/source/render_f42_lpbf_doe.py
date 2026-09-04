#!/usr/bin/env python3
"""Render the F42 BLT-S310 DOE and its fail-closed status."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from prepare_additivefoam_f42_doe import build_matrix


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--spec",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "f42-lpbf-doe.json",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    matrix = build_matrix(spec)
    powers = spec["published_process_window"]["laser_power_w"]
    speeds = spec["published_process_window"]["scan_speed_mm_s"]
    hatches = spec["published_process_window"]["hatch_spacing_mm"]

    plt.style.use("dark_background")
    figure, axes = plt.subplots(2, 2, figsize=(14, 10), constrained_layout=False)
    figure.patch.set_facecolor("#07141e")
    figure.subplots_adjust(left=0.07, right=0.87, bottom=0.08, top=0.88, wspace=0.34, hspace=0.30)
    heat_axes = [axes[0, 0], axes[0, 1], axes[1, 0]]
    images = []
    for axis, power in zip(heat_axes, powers):
        values = np.zeros((len(hatches), len(speeds)))
        for iy, hatch in enumerate(hatches):
            for ix, speed in enumerate(speeds):
                row = next(
                    item
                    for item in matrix
                    if item["laser_power_w"] == power
                    and item["scan_speed_mm_s"] == speed
                    and item["hatch_spacing_mm"] == hatch
                )
                values[iy, ix] = row["volumetric_energy_density_j_mm3"]
        image = axis.imshow(values, cmap="viridis", vmin=30.0, vmax=51.28205128205128)
        images.append(image)
        axis.set_title(f"{power} W")
        axis.set_xticks(range(len(speeds)), speeds)
        axis.set_yticks(range(len(hatches)), [f"{value:.2f}" for value in hatches])
        axis.set_xlabel("vitesse (mm/s)")
        axis.set_ylabel("hatch (mm)")
        for iy in range(len(hatches)):
            for ix in range(len(speeds)):
                axis.text(ix, iy, f"{values[iy, ix]:.1f}", ha="center", va="center", fontsize=10)
    colorbar_axis = figure.add_axes([0.91, 0.17, 0.018, 0.64])
    colorbar = figure.colorbar(images[-1], cax=colorbar_axis)
    colorbar.set_label("VED indicative P/(v·h·t), J/mm³")

    status = axes[1, 1]
    status.axis("off")
    status.text(0.0, 0.98, "Contrat de validation", fontsize=17, weight="bold", color="#55c8e8", va="top")
    status.text(
        0.0,
        0.82,
        "27 cas nominaux\n+ 3 cas extrêmes × 3 maillages\n= 33 exécutions uniques",
        fontsize=14,
        linespacing=1.5,
        va="top",
    )
    status.text(
        0.0,
        0.54,
        "Culasse orientée : 119,1 × 82,0 × 206,1 mm\n"
        "BLT-S310 : 250 × 250 × 400 mm\n"
        "4 122 couches à 50 µm",
        fontsize=13,
        linespacing=1.5,
        va="top",
    )
    status.text(
        0.0,
        0.33,
        "Tmax = 3 300 K conservé\n"
        "≥ 3 299 K = donnée censurée, DOE refusé\n"
        "Supports et fichier machine : NON GÉNÉRÉS",
        fontsize=13,
        color="#ffbf55",
        linespacing=1.5,
        va="top",
    )
    status.text(
        0.0,
        0.0,
        "AUCUNE AUTORISATION D’IMPRESSION",
        fontsize=14,
        weight="bold",
        color="#ff5964",
        va="bottom",
    )
    figure.suptitle(
        "F42 — DOE AdditiveFOAM / BLT-S310 / AlSi10Mg",
        fontsize=21,
        weight="bold",
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=170, facecolor=figure.get_facecolor())
    plt.close(figure)
    report_path = args.output.with_suffix(".json")
    report_path.write_text(
        json.dumps(
            {
                "phase": "F42",
                "classification": "doe_visualization_not_solver_result",
                "specification_sha256": sha256(args.spec),
                "image": {
                    "path": args.output.name,
                    "sha256": sha256(args.output),
                    "bytes": args.output.stat().st_size,
                },
                "metal_print_authorized": False,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"image": str(args.output), "sha256": sha256(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
