#!/usr/bin/env python3
"""Présélection thermique de fabrication de la cellule CFRP 964/993.

Le calcul est un modèle thermique concentré à deux nœuds avec cinétique de
cuisson générique. Il compare des hypothèses et ne remplace ni PAM-COMPOSITES,
ni une simulation de drapage, ni des mesures DSC/DEA/thermocouples.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
TWIN_ROOT = ROOT / "twins" / "993-carbon-safety-cell"
DEFAULT_CONFIG = TWIN_ROOT / "manufacturing-simulation.json"
DEFAULT_OUTPUT = TWIN_ROOT / "derived" / "manufacturing-process-screening.json"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: objet JSON attendu")
    return value


def canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _duration_s(segment: dict[str, Any], start_C: float) -> float:
    if segment["kind"] == "hold":
        return float(segment["duration_min"]) * 60.0
    rate = float(segment["rate_C_per_min"])
    delta = float(segment["target_C"]) - start_C
    if rate == 0.0 or delta * rate <= 0.0:
        raise ValueError(f"rampe incohérente: départ {start_C}, segment {segment}")
    return abs(delta / rate) * 60.0


def build_air_schedule(route: dict[str, Any], dt_s: float, ambient_C: float = 25.0) -> list[float]:
    values = [ambient_C]
    current = ambient_C
    for segment in route["segments"]:
        duration_s = _duration_s(segment, current)
        steps = max(1, int(round(duration_s / dt_s)))
        if segment["kind"] == "hold":
            values.extend([current] * steps)
        elif segment["kind"] == "ramp":
            target = float(segment["target_C"])
            start = current
            values.extend(start + (target - start) * index / steps for index in range(1, steps + 1))
            current = target
        else:
            raise ValueError(f"segment inconnu: {segment['kind']}")
    return values


def simulate_case(config: dict[str, Any], route: dict[str, Any], thickness_mm: float) -> dict[str, Any]:
    thermal = config["thermal_model"]
    kinetics = config["resin_kinetics_hypothesis"]
    thresholds = config["screening_thresholds"]
    dt_s = float(thermal["time_step_s"])
    air = build_air_schedule(route, dt_s)
    tool_C = air[0]
    part_C = air[0]
    degree = float(kinetics["initial_degree_of_cure"])
    tau_tool = float(thermal["tool_time_constant_s"])
    tau_part = float(thermal["part_time_constant_s_at_4mm"]) * (
        thickness_mm / 4.0
    ) ** float(thermal["part_time_constant_thickness_exponent"])
    gas_constant = 8.314462618
    maximum_lag = 0.0
    maximum_overshoot = 0.0
    maximum_part_C = part_C
    maximum_cure_rate = 0.0

    for air_C in air[1:]:
        tool_C += (air_C - tool_C) * dt_s / tau_tool
        kelvin = max(part_C + 273.15, 1.0)
        rate = (
            float(kinetics["pre_exponential_1_s"])
            * math.exp(-float(kinetics["activation_energy_J_mol"]) / (gas_constant * kelvin))
            * max(1.0 - degree, 0.0) ** float(kinetics["reaction_order"])
        )
        increment = min(max(rate * dt_s, 0.0), 1.0 - degree)
        part_C += (tool_C - part_C) * dt_s / tau_part
        part_C += float(kinetics["adiabatic_temperature_rise_C"]) * increment
        degree += increment
        maximum_lag = max(maximum_lag, abs(tool_C - part_C))
        maximum_overshoot = max(maximum_overshoot, part_C - air_C)
        maximum_part_C = max(maximum_part_C, part_C)
        maximum_cure_rate = max(maximum_cure_rate, rate)

    checks = {
        "final_degree_of_cure": degree >= float(thresholds["minimum_final_degree_of_cure"]),
        "tool_part_lag": maximum_lag <= float(thresholds["maximum_tool_part_lag_C"]),
        "part_overshoot": maximum_overshoot <= float(thresholds["maximum_part_overshoot_above_air_C"]),
    }
    return {
        "route_id": route["route_id"],
        "coupon_thickness_mm": thickness_mm,
        "cycle_duration_min": round((len(air) - 1) * dt_s / 60.0, 2),
        "pressure_bar_absolute": float(route["pressure_bar_absolute"]),
        "vacuum_bar_gauge": float(route["vacuum_bar_gauge"]),
        "maximum_part_temperature_C": round(maximum_part_C, 3),
        "maximum_tool_part_lag_C": round(maximum_lag, 3),
        "maximum_part_overshoot_above_air_C": round(maximum_overshoot, 3),
        "maximum_cure_rate_1_s": round(maximum_cure_rate, 9),
        "final_degree_of_cure": round(degree, 6),
        "provisional_checks": checks,
        "passes_hypothesis_screening": all(checks.values()),
    }


def build_report(config: dict[str, Any]) -> dict[str, Any]:
    cases = [
        simulate_case(config, route, float(thickness))
        for route in config["process_routes"]
        for thickness in config["geometry_scope"]["coupon_thicknesses_mm"]
    ]
    delta_T = max(
        float(segment.get("target_C", 25.0))
        for route in config["process_routes"]
        for segment in route["segments"]
    ) - 25.0
    length_mm = float(config["geometry_scope"]["heated_length_mm"])
    part_cte = float(config["part_in_plane_cte_um_mK"])
    cte_cases = []
    threshold = float(config["screening_thresholds"]["maximum_free_cte_mismatch_mm"])
    for material in config["tool_material_hypotheses"]:
        mismatch = length_mm * (float(material["cte_um_mK"]) - part_cte) * 1.0e-6 * delta_T
        cte_cases.append({
            "material_id": material["material_id"],
            "free_expansion_mismatch_mm_over_heated_length": round(mismatch, 4),
            "within_provisional_mismatch_threshold": abs(mismatch) <= threshold,
        })

    return {
        "schema_version": "1.0.0",
        "simulation_id": config["simulation_id"],
        "status": "manufacturing_hypothesis_screening_complete_not_correlated",
        "method": config["thermal_model"]["model"],
        "kinetics_status": config["resin_kinetics_hypothesis"]["status"],
        "thermal_cure_cases": cases,
        "tool_cte_sensitivity": cte_cases,
        "decision": {
            "manufacturing_route_selected": False,
            "tool_material_selected": False,
            "reason": "Les résultats dépendent d'une cinétique résine et de constantes thermiques hypothétiques; le drapage, la porosité, la pression et les déformations résiduelles ne sont pas résolus.",
        },
        "required_next_evidence": [
            "fiche fournisseur du préimprégné et cycle qualifié",
            "DSC/DEA pour identifier la cinétique et la vitrification",
            "modèle de drapage sur surfaces F2 avec angles de cisaillement mesurés",
            "thermocouples sur panneau témoin et corrélation thermique",
            "mesure de porosité, fraction volumique et épaisseur après cuisson",
            "modèle pression/vide et vérification mécanique de l'outillage",
            "mesure de retrait, spring-in et compensation du moule"
        ],
        "not_simulated": config["thermal_model"]["not_modelled"],
        "release_gates": config["release_gates"],
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Présélection de fabrication CFRP F1",
        "",
        f"Statut : `{report['status']}`.",
        "",
        "| Route | Épaisseur témoin | Durée | Tmax pièce | Retard outil/pièce | Surtempérature | Cuisson finale | Filtre hypothétique |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for item in report["thermal_cure_cases"]:
        lines.append(
            f"| {item['route_id']} | {item['coupon_thickness_mm']:.1f} mm | "
            f"{item['cycle_duration_min']:.1f} min | {item['maximum_part_temperature_C']:.1f} °C | "
            f"{item['maximum_tool_part_lag_C']:.1f} °C | {item['maximum_part_overshoot_above_air_C']:.1f} °C | "
            f"{item['final_degree_of_cure']:.3f} | {'oui' if item['passes_hypothesis_screening'] else 'non'} |"
        )
    lines.extend([
        "",
        "Ce calcul ne sélectionne ni résine, ni cycle, ni outillage. Les seuils sont des filtres de sensibilité et ne donnent aucun crédit de fabrication.",
        "",
        "## Sensibilité de dilatation libre de l'outillage",
        "",
        "| Hypothèse outil | Écart libre sur 2 272 mm | Sous le seuil provisoire |",
        "|---|---:|---|",
    ])
    for item in report["tool_cte_sensitivity"]:
        lines.append(
            f"| {item['material_id']} | {item['free_expansion_mismatch_mm_over_heated_length']:.3f} mm | "
            f"{'oui' if item['within_provisional_mismatch_threshold'] else 'non'} |"
        )
    lines.extend(["", "Toutes les portes de libération restent fermées.", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write == args.check:
        parser.error("choisir exactement --write ou --check")

    report = build_report(load_json(args.config))
    rendered = canonical_json(report)
    markdown = render_markdown(report)
    markdown_path = args.output.with_suffix(".md")
    if args.write:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        markdown_path.write_text(markdown, encoding="utf-8")
        return 0
    if not args.output.exists() or args.output.read_text(encoding="utf-8") != rendered:
        print(f"{args.output}: sortie absente ou obsolète")
        return 1
    if not markdown_path.exists() or markdown_path.read_text(encoding="utf-8") != markdown:
        print(f"{markdown_path}: sortie absente ou obsolète")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
