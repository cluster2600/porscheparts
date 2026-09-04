#!/usr/bin/env python3
"""Rend uniquement les agregats publics de l'ecran mecanique F42.1."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    if report.get("publication", {}).get("contains_private_geometry") is not False:
        raise RuntimeError("public_report_geometry_gate_not_closed")
    cases = report["cases"]
    sizes = [case["mesh_target_size_mm"] for case in cases]
    cleaned_p95 = [
        case["results"]["support_excluded_von_mises_p95_mpa"] for case in cases
    ]
    raw_p95 = [case["results"]["raw_von_mises_p95_mpa"] for case in cases]
    displacement = [case["results"]["maximum_displacement_mm"] for case in cases]
    elements = [case["mesh"]["elements_C3D4"] for case in cases]
    quality = [case["mesh"]["p01_mean_ratio_quality"] for case in cases]

    figure, axes = plt.subplots(2, 2, figsize=(15, 9), facecolor="#07131b")
    figure.suptitle(
        "F42.1 — ECRAN THERMO-MECANIQUE TETRA CONFORME",
        color="white",
        fontsize=18,
        fontweight="bold",
    )
    for axis in axes.flat:
        axis.set_facecolor("#0d202b")
        axis.tick_params(colors="#dbe8ee")
        axis.grid(color="#34515f", alpha=0.35)
        for spine in axis.spines.values():
            spine.set_color("#456675")

    axes[0, 0].plot(sizes, cleaned_p95, "o-", color="#3dd6d0", label="p95 hors appuis")
    axes[0, 0].plot(sizes, raw_p95, "s--", color="#ffb347", label="p95 brut")
    axes[0, 0].set_title("Convergence de contrainte", color="white", fontweight="bold")
    axes[0, 0].set_ylabel("von Mises [MPa]", color="#dbe8ee")
    axes[0, 0].legend(facecolor="#0d202b", labelcolor="white")

    axes[0, 1].plot(sizes, displacement, "o-", color="#91d45b")
    axes[0, 1].set_title("Déplacement maximal", color="white", fontweight="bold")
    axes[0, 1].set_ylabel("|U|max [mm]", color="#dbe8ee")

    axes[1, 0].plot(sizes, elements, "o-", color="#8fb8ff")
    axes[1, 0].set_title("Raffinement volumique", color="white", fontweight="bold")
    axes[1, 0].set_ylabel("Éléments C3D4", color="#dbe8ee")

    axes[1, 1].plot(sizes, quality, "o-", color="#e889d0")
    axes[1, 1].set_title("Qualité tétra — percentile 1 %", color="white", fontweight="bold")
    axes[1, 1].set_ylabel("mean-ratio [0–1]", color="#dbe8ee")
    for axis in axes.flat:
        axis.set_xlabel("Taille cible [mm] — plus fin vers la droite", color="#dbe8ee")
        axis.invert_xaxis()

    convergence = report["finest_pair_convergence"]
    gate_text = (
        f"Écart fin p95 hors appuis : "
        f"{100.0 * convergence['support_excluded_p95_stress_relative_difference']:.2f} %  ·  "
        f"déplacement : {100.0 * convergence['maximum_displacement_relative_difference']:.2f} %\n"
        "EXCLUSION FIXE : cylindres R=15 mm autour des 4 axes de goujon  ·  "
        "QUALITÉ/TAILLE MAILLE REFUSÉE  ·  CARTE MATÉRIAU À CHAUD ABSENTE\n"
        "VERDICT FAIL-CLOSED — NI AUTORISATION D'IMPRIMER, NI AUTORISATION MOTEUR"
    )
    figure.text(
        0.5,
        0.015,
        gate_text,
        ha="center",
        va="bottom",
        color="#ffdb84",
        fontsize=10,
        fontweight="bold",
    )
    figure.tight_layout(rect=(0.02, 0.11, 0.98, 0.93))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=170, facecolor=figure.get_facecolor())
    plt.close(figure)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
