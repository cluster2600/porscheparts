#!/usr/bin/env python3
"""Double calcul hydraulique du circuit d'huile F37 et sensibilité des gicleurs."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def hagen_poiseuille(mu: float, length: float, flow: float, diameter: float) -> float:
    return 128.0 * mu * length * flow / (math.pi * diameter**4)


def darcy_weisbach_laminar(mu: float, rho: float, length: float, flow: float, diameter: float) -> tuple[float, float, float]:
    area = math.pi * diameter**2 / 4.0
    velocity = flow / area
    reynolds = rho * velocity * diameter / mu
    friction = 64.0 / reynolds
    pressure = friction * length / diameter * 0.5 * rho * velocity**2
    return pressure, reynolds, velocity


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cfg = json.loads(args.contract.read_text(encoding="utf-8"))
    screen = cfg["oil_hydraulic_screen"]
    oil = cfg["oil_system"]
    rho = float(screen["oil_density_kg_m3"])
    q_total = float(screen["target_total_flow_l_min"]) / 60_000.0
    q_rocker = float(screen["target_flow_per_rocker_l_min"]) / 60_000.0
    lengths = screen["worst_path_lengths_mm"]
    segments = [
        ("lateral_feed_d6", lengths["lateral_feed_d6"] / 1000.0, oil["head_feed_lateral"]["diameter_mm"] / 1000.0, q_total),
        ("header_d6", lengths["header_d6"] / 1000.0, oil["head_header"]["diameter_mm"] / 1000.0, q_total),
        ("metering_branch_d3", lengths["metering_branch_d3"] / 1000.0, oil["four_metering_branches_diameter_mm"] / 1000.0, q_rocker),
        ("carrier_gallery_d5", lengths["carrier_gallery_d5"] / 1000.0, oil["carrier_gallery_diameter_mm"] / 1000.0, q_rocker),
    ]
    cases = []
    for label, viscosity in (
        ("hot_110c", float(screen["dynamic_viscosity_pa_s_hot_110c"])),
        ("cold_screen", float(screen["dynamic_viscosity_pa_s_cold_screen"])),
    ):
        rows = []
        hp_total = 0.0
        dw_total = 0.0
        for name, length, diameter, flow in segments:
            hp = hagen_poiseuille(viscosity, length, flow, diameter)
            dw, reynolds, velocity = darcy_weisbach_laminar(viscosity, rho, length, flow, diameter)
            hp_total += hp
            dw_total += dw
            rows.append({
                "segment": name,
                "diameter_mm": diameter * 1000.0,
                "length_mm": length * 1000.0,
                "flow_l_min": flow * 60_000.0,
                "velocity_m_s": velocity,
                "reynolds": reynolds,
                "hagen_poiseuille_pa": hp,
                "darcy_weisbach_pa": dw,
            })
        branch = next(item for item in rows if item["segment"] == "metering_branch_d3")
        minor = float(screen["minor_loss_coefficient_worst_path"]) * 0.5 * rho * branch["velocity_m_s"] ** 2
        hp_total += minor
        dw_total += minor
        difference = abs(hp_total - dw_total) / max(hp_total, 1.0e-12)
        cases.append({
            "id": label,
            "dynamic_viscosity_pa_s": viscosity,
            "segments": rows,
            "minor_loss_pa": minor,
            "hagen_poiseuille_total_kpa": hp_total / 1000.0,
            "darcy_weisbach_total_kpa": dw_total / 1000.0,
            "two_method_relative_difference": difference,
            "all_segments_laminar_re_below_2300": all(item["reynolds"] < 2300.0 for item in rows),
        })

    diameter = float(oil["four_metering_branches_diameter_mm"])
    radius_tolerance = float(screen["metering_bore_radius_tolerance_mm"])
    diameter_low = diameter - 2.0 * radius_tolerance
    diameter_high = diameter + 2.0 * radius_tolerance
    flow_low = diameter_low**4
    flow_high = diameter_high**4
    imbalance = (flow_high - flow_low) / ((flow_high + flow_low) / 2.0) * 100.0
    hot = next(item for item in cases if item["id"] == "hot_110c")
    cold = next(item for item in cases if item["id"] == "cold_screen")
    gates = {
        "two_methods_agree_within_1e_9": max(item["two_method_relative_difference"] for item in cases) <= 1.0e-9,
        "laminar_assumption_valid": all(item["all_segments_laminar_re_below_2300"] for item in cases),
        "hot_pressure_drop_below_limit": hot["darcy_weisbach_total_kpa"] <= float(screen["maximum_hot_pressure_drop_kpa"]),
        "cold_pressure_drop_below_limit": cold["darcy_weisbach_total_kpa"] <= float(screen["maximum_cold_pressure_drop_kpa"]),
        "parallel_flow_imbalance_below_limit": imbalance <= float(screen["maximum_parallel_flow_imbalance_percent"]),
        "physical_oil_rig_correlated": False,
    }
    report = {
        "schema_version": "1.0.0",
        "phase": "F37",
        "status": "oil_network_analytical_double_check_complete_physical_correlation_pending",
        "inputs": {"contract_sha256": sha256(args.contract)},
        "equations": {
            "method_1": "Hagen-Poiseuille: delta_p=128*mu*L*Q/(pi*D^4)",
            "method_2": "Darcy-Weisbach: delta_p=f*(L/D)*rho*v^2/2 with f=64/Re",
            "minor_losses": "delta_p=K*rho*v^2/2",
            "parallel_bore_sensitivity": "Q proportional to D^4 at equal pressure drop",
        },
        "cases": cases,
        "metering_bore_sensitivity": {
            "nominal_diameter_mm": diameter,
            "diameter_range_mm": [diameter_low, diameter_high],
            "parallel_flow_imbalance_percent": imbalance,
        },
        "gates": gates,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "f37-oil-hydraulic-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), facecolor="#eef1f3")
    labels = [item["id"] for item in cases]
    values = [item["darcy_weisbach_total_kpa"] for item in cases]
    limits = [float(screen["maximum_hot_pressure_drop_kpa"]), float(screen["maximum_cold_pressure_drop_kpa"])]
    utilization = [100.0 * value / limit for value, limit in zip(values, limits)]
    bars = axes[0].bar(labels, utilization, color=["#2d8a72", "#c97b35"])
    axes[0].axhline(100.0, color="#9e2f2a", linewidth=3, label="limite écran")
    axes[0].bar_label(bars, labels=[f"{value:.2f} kPa" for value in values], padding=3)
    axes[0].set_ylabel("Utilisation de la limite de perte de charge [%]")
    axes[0].set_title("Réseau d’huile — chaud et démarrage à froid", weight="bold")
    axes[0].grid(axis="y", alpha=0.25)
    axes[0].legend(frameon=False)
    branch_hot = next(item for item in hot["segments"] if item["segment"] == "metering_branch_d3")
    validity = [100.0 * branch_hot["reynolds"] / 2300.0, 100.0 * imbalance / float(screen["maximum_parallel_flow_imbalance_percent"])]
    right_bars = axes[1].bar(["Re / 2300", "déséquilibre / limite"], validity, color=["#3479a8", "#a34c8a"])
    axes[1].bar_label(right_bars, labels=[f"Re {branch_hot['reynolds']:.0f}", f"{imbalance:.1f} %"], padding=3)
    axes[1].axhline(100.0, color="#555", linestyle=":", label="limite = 100 %")
    axes[1].set_ylabel("Utilisation de la limite [%]")
    axes[1].set_title("Validité du modèle et tolérance D⁴", weight="bold")
    axes[1].grid(axis="y", alpha=0.25)
    axes[1].legend(frameon=False)
    fig.suptitle("F37 — double calcul analytique des galeries d’huile", fontsize=15, weight="bold")
    fig.text(0.5, 0.01, "Écran virtuel; banc huile et mesure des quatre débits encore requis", ha="center", color="#9e2f2a", weight="bold")
    fig.tight_layout(rect=(0, 0.05, 1, 0.93))
    fig.savefig(args.output / "917-head-f37-oil-hydraulic-screen.png", dpi=180)
    plt.close(fig)
    print(json.dumps({"status": report["status"], "gates": gates}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
