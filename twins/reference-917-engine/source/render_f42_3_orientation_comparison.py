#!/usr/bin/env python3
"""Rendu public de la comparaison d'orientation F42.3."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    orientations = report["orientations"]
    reference = orientations["reference_scan_y_down_plus_y"]
    candidate = orientations["candidate_scan_y_up_minus_y"]

    panels = [
        ("Nouveaux îlots", "new_island_count_total", "nombre"),
        (
            "Intégrale d'aire non soutenue",
            "unsupported_area_layer_integral_mm2_layers",
            "mm²·couches",
        ),
        ("Volume support conservatif", "support_volume_cm3", "cm³"),
        ("Matière dans le premier mm", "first_1mm_material_volume_mm3", "mm³"),
    ]
    figure, axes = plt.subplots(2, 2, figsize=(13.5, 8.2))
    figure.patch.set_facecolor("#08131c")
    figure.subplots_adjust(left=0.08, right=0.97, bottom=0.16, top=0.82, hspace=0.50, wspace=0.32)
    for axis, (title, key, unit) in zip(axes.flat, panels):
        axis.set_facecolor("#0d1d29")
        values = [float(reference[key]), float(candidate[key])]
        bars = axis.bar(["+Y référence", "-Y candidat"], values, color=["#ffb347", "#69b9df"])
        axis.set_title(title, color="white", fontsize=12)
        axis.set_ylabel(unit, color="#d6e3eb")
        axis.tick_params(colors="#d6e3eb")
        axis.grid(axis="y", color="#314955", alpha=0.45)
        for spine in axis.spines.values():
            spine.set_color("#3c5362")
        for bar, value in zip(bars, values):
            axis.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f"{value:,.2f}".replace(",", " "),
                ha="center",
                va="bottom",
                color="#f4f7f8",
                fontsize=9,
            )
    surface = report["cardinal_surface_proxy"]["candidate_change_percent"]
    figure.suptitle(
        "F42.3 — comparaison exhaustive +Y / -Y, 4 122 couches chacune",
        color="white",
        fontsize=17,
        fontweight="bold",
    )
    figure.text(
        0.5,
        0.875,
        f"Le proxy surfacique favorise -Y de {abs(surface):.2f} %, mais la pile complète décide.",
        ha="center",
        color="#d6e3eb",
        fontsize=11,
    )
    decision = report["decision"]
    footer = (
        f"DÉCISION : {decision['selected_orientation']} — changement NON AUTORISÉ  |  "
        "interfaces: NON QUALIFIÉES  |  recoater: NON VALIDÉ  |  impression: NON AUTORISÉE"
    )
    figure.text(0.5, 0.035, footer, ha="center", color="#ff8f8f", fontsize=9.5)
    args.image.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.image, dpi=180, facecolor=figure.get_facecolor())
    plt.close(figure)
    manifest = {
        "schema_version": "1.0.0",
        "phase": "F42.3",
        "artifacts": {
            "report": {"file": args.report.name, "sha256": sha256(args.report)},
            "image": {"file": args.image.name, "sha256": sha256(args.image)},
        },
        "gates": {
            "contains_private_geometry": False,
            "orientation_change_authorized": False,
            "manufacturing_release": False,
        },
    }
    args.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
