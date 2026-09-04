#!/usr/bin/env python3
"""Render measured F42 AdditiveFOAM results without promoting release gates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


CASE_PATTERN = re.compile(r"^P(\d+)-V(\d+)-H(\d+)$")


def parse_case_id(value: str) -> tuple[int, int, float]:
    match = CASE_PATTERN.fullmatch(value)
    if match is None:
        raise ValueError(f"identifiant_cas_invalide:{value}")
    return int(match.group(1)), int(match.group(2)), int(match.group(3)) / 1000.0


def validate_results(report: dict) -> list[dict]:
    if report.get("phase") != "F42":
        raise ValueError("phase_F42_requise")
    measurements = report.get("measurements")
    if not isinstance(measurements, list):
        raise ValueError("mesures_absentes")
    nominal = [item for item in measurements if item.get("resolution") == "nominal"]
    if len(nominal) != 27:
        raise ValueError(f"27_mesures_nominales_requises:{len(nominal)}")
    keys = [item.get("case_id") for item in nominal]
    if len(set(keys)) != 27:
        raise ValueError("cas_nominaux_dupliques")
    for item in nominal:
        parse_case_id(str(item.get("case_id")))
        for name in (
            "temperature_max_k",
            "temperature_p99_k",
            "melt_pool_length_mm",
            "melt_pool_width_mm",
            "melt_pool_depth_mm",
        ):
            value = float(item[name])
            if not np.isfinite(value):
                raise ValueError(f"metrique_non_finie:{item['case_id']}:{name}")
    return nominal


def render(report: dict, output: Path, label: str) -> None:
    nominal = validate_results(report)
    powers = sorted({parse_case_id(item["case_id"])[0] for item in nominal})
    speeds = sorted({parse_case_id(item["case_id"])[1] for item in nominal})
    hatches = sorted({parse_case_id(item["case_id"])[2] for item in nominal})
    if len(powers) != 3 or len(speeds) != 3 or len(hatches) != 3:
        raise ValueError("matrice_3x3x3_requise")

    lookup = {}
    for item in nominal:
        lookup[parse_case_id(item["case_id"])] = item
    temperature_values = np.array([float(item["temperature_p99_k"]) for item in nominal])
    vmin = float(temperature_values.min())
    vmax = float(temperature_values.max())

    plt.style.use("dark_background")
    figure, axes = plt.subplots(2, 2, figsize=(14, 10))
    figure.patch.set_facecolor("#07141e")
    figure.subplots_adjust(left=0.07, right=0.92, bottom=0.09, top=0.88, wspace=0.28, hspace=0.31)
    image = None
    for axis, power in zip((axes[0, 0], axes[0, 1], axes[1, 0]), powers):
        values = np.zeros((3, 3))
        for iy, hatch in enumerate(hatches):
            for ix, speed in enumerate(speeds):
                values[iy, ix] = float(lookup[(power, speed, hatch)]["temperature_p99_k"])
        image = axis.imshow(values, cmap="inferno", vmin=vmin, vmax=vmax)
        axis.set_title(f"{power} W — T99 (K)")
        axis.set_xticks(range(3), speeds)
        axis.set_yticks(range(3), [f"{value:.2f}" for value in hatches])
        axis.set_xlabel("vitesse (mm/s)")
        axis.set_ylabel("hatch (mm)")
        for iy in range(3):
            for ix in range(3):
                axis.text(ix, iy, f"{values[iy, ix]:.0f}", ha="center", va="center", fontsize=10)
    assert image is not None
    color_axis = figure.add_axes([0.945, 0.53, 0.015, 0.30])
    figure.colorbar(image, cax=color_axis, label="T99 mesurée (K)")

    status = axes[1, 1]
    status.axis("off")
    policy = report.get("temperature_limit_policy", {})
    gates = report.get("gates", {})
    cap_count = int(policy.get("cap_hit_count", 0))
    convergence = report.get("convergence", {})
    convergence_count = sum(
        bool(item.get("nominal_to_fine", {}).get("passes"))
        for item in convergence.values()
    )
    depths = [float(item["melt_pool_depth_mm"]) for item in nominal]
    widths = [float(item["melt_pool_width_mm"]) for item in nominal]
    lengths = [float(item["melt_pool_length_mm"]) for item in nominal]
    status.text(0, 1.0, "Mesures du solveur", fontsize=18, weight="bold", color="#55c8e8", va="top")
    status.text(
        0,
        0.84,
        f"27 cas nominaux\n"
        f"T99 : {vmin:.1f}–{vmax:.1f} K\n"
        f"bain L/l/p : {min(lengths):.3f}–{max(lengths):.3f} / "
        f"{min(widths):.3f}–{max(widths):.3f} / {min(depths):.3f}–{max(depths):.3f} mm",
        fontsize=13,
        linespacing=1.5,
        va="top",
    )
    status.text(
        0,
        0.52,
        f"Saturations >= 3 299 K : {cap_count}\n"
        f"Convergences nominal/fin : {convergence_count}/3\n"
        f"Classement DOE permis : {'OUI' if gates.get('doe_response_ranking_permitted') else 'NON'}",
        fontsize=14,
        linespacing=1.6,
        color="#8de090" if gates.get("doe_response_ranking_permitted") else "#ffbf55",
        va="top",
    )
    status.text(
        0,
        0.16,
        "AUTORISATION D’IMPRESSION : NON\nAUTORISATION DÉMARRAGE : NON",
        fontsize=15,
        weight="bold",
        color="#ff5964",
        linespacing=1.5,
        va="top",
    )
    figure.suptitle(f"F42.2 — AdditiveFOAM mesuré — {label}", fontsize=21, weight="bold")
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=170, facecolor=figure.get_facecolor())
    plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    report = json.loads(args.results.read_text(encoding="utf-8"))
    render(report, args.output, args.label)
    print(json.dumps({"output": str(args.output), "bytes": args.output.stat().st_size}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
