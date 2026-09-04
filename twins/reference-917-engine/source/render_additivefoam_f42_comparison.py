#!/usr/bin/env python3
"""Render a fail-closed cross-host AdditiveFOAM F42 comparison."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


METRIC_LABELS = {
    "temperature_max_k": "Tmax",
    "temperature_p99_k": "T99",
    "molten_volume_mm3": "volume fondu",
    "melt_pool_length_mm": "longueur bain",
    "melt_pool_width_mm": "largeur bain",
    "melt_pool_depth_mm": "profondeur bain",
    "maximum_courant_number": "Courant max",
}


def validate(report: dict) -> list[dict]:
    if report.get("phase") != "F42.2":
        raise ValueError("phase_F42_2_requise")
    comparisons = report.get("comparisons")
    if not isinstance(comparisons, list) or len(comparisons) != 33:
        raise ValueError("33_comparaisons_requises")
    for item in comparisons:
        if item.get("present_on_both_hosts") is not True:
            raise ValueError("cas_absent_sur_un_hote")
        metrics = item.get("metrics")
        if not isinstance(metrics, dict) or set(metrics) != set(METRIC_LABELS):
            raise ValueError("jeu_de_metriques_invalide")
        for metric in metrics.values():
            for name in ("left", "right", "relative_difference"):
                if not np.isfinite(float(metric[name])):
                    raise ValueError(f"metrique_non_finie:{name}")
    return comparisons


def render(report: dict, output: Path) -> None:
    comparisons = validate(report)
    hosts = report.get("hosts", {})
    gates = report.get("gates", {})
    left_label = str(hosts.get("left", "hote-a"))
    right_label = str(hosts.get("right", "hote-b"))

    t99_left = np.array(
        [float(item["metrics"]["temperature_p99_k"]["left"]) for item in comparisons]
    )
    t99_right = np.array(
        [float(item["metrics"]["temperature_p99_k"]["right"]) for item in comparisons]
    )
    maximum_relative = {
        name: max(float(item["metrics"][name]["relative_difference"]) for item in comparisons)
        for name in METRIC_LABELS
    }

    plt.style.use("dark_background")
    figure, axes = plt.subplots(2, 2, figsize=(14, 10))
    figure.patch.set_facecolor("#07141e")
    figure.subplots_adjust(left=0.08, right=0.96, bottom=0.09, top=0.88, wspace=0.28, hspace=0.32)

    scatter = axes[0, 0]
    scatter.scatter(t99_left, t99_right, color="#55c8e8", edgecolor="white", alpha=0.85)
    low = min(float(t99_left.min()), float(t99_right.min()))
    high = max(float(t99_left.max()), float(t99_right.max()))
    scatter.plot([low, high], [low, high], color="#ffbf55", linestyle="--", linewidth=1.5)
    scatter.set_title("Reproductibilite T99 — 33 executions")
    scatter.set_xlabel(f"{left_label} (K)")
    scatter.set_ylabel(f"{right_label} (K)")
    scatter.grid(alpha=0.2)

    bars = axes[0, 1]
    names = list(METRIC_LABELS)
    values = np.array([maximum_relative[name] * 100.0 for name in names])
    colors = ["#8de090" if value <= 1.0 else "#ffbf55" for value in values]
    bars.barh(range(len(names)), values, color=colors)
    bars.set_yticks(range(len(names)), [METRIC_LABELS[name] for name in names])
    bars.invert_yaxis()
    bars.set_xlabel("ecart relatif maximal (%)")
    bars.set_title("Ecart maximal par metrique")
    bars.grid(axis="x", alpha=0.2)

    nominal = [item for item in comparisons if item.get("resolution") == "nominal"]
    nominal.sort(key=lambda item: str(item.get("case_id")))
    heatmap = axes[1, 0]
    differences = np.array(
        [[float(item["metrics"][name]["relative_difference"]) * 100.0 for name in names] for item in nominal]
    )
    image = heatmap.imshow(differences.T, aspect="auto", cmap="magma")
    heatmap.set_yticks(range(len(names)), [METRIC_LABELS[name] for name in names])
    heatmap.set_xticks(range(0, len(nominal), 3), [str(nominal[index]["case_id"]) for index in range(0, len(nominal), 3)], rotation=45, ha="right")
    heatmap.set_title("Ecarts relatifs — 27 cas nominaux (%)")
    figure.colorbar(image, ax=heatmap, fraction=0.046, pad=0.04)

    status = axes[1, 1]
    status.axis("off")
    reproduced = gates.get("all_33_runs_reproduced_within_tolerance") is True
    failed_cases = sum(item.get("passes") is not True for item in comparisons)
    status.text(0, 1.0, "Verdict croise", fontsize=18, weight="bold", color="#55c8e8", va="top")
    status.text(
        0,
        0.82,
        f"Jeu identique : {'OUI' if report.get('case_set_identical') else 'NON'}\n"
        f"Comparaisons : {len(comparisons)}/33\n"
        f"Cas hors tolerance : {failed_cases}\n"
        f"Reproductibilite numerique : {'PASSE' if reproduced else 'ECHOUE'}",
        fontsize=14,
        linespacing=1.55,
        color="#8de090" if reproduced else "#ffbf55",
        va="top",
    )
    status.text(
        0,
        0.33,
        "DEUXIEME MODELE PHYSIQUE : NON\n"
        "AUTORISATION D'IMPRESSION : NON\n"
        "AUTORISATION DEMARRAGE : NON",
        fontsize=14,
        weight="bold",
        color="#ff5964",
        linespacing=1.55,
        va="top",
    )

    figure.suptitle("F42.2 — comparaison AdditiveFOAM inter-hotes", fontsize=21, weight="bold")
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=170, facecolor=figure.get_facecolor())
    plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--comparison", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.comparison.read_text(encoding="utf-8"))
    render(report, args.output)
    print(json.dumps({"output": str(args.output), "bytes": args.output.stat().st_size}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
