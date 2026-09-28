#!/usr/bin/env python3
"""Calcule le premier screening mécanique reproductible de la 911–917 F9."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
TWIN_ROOT = ROOT / "twins" / "vehicle-911-917"
CONFIG_PATH = TWIN_ROOT / "mechanical-engineering-basis-f9.json"
WORK_ROOT = ROOT / "work" / "911-917-engineering-f9"
REPORT_PATH = WORK_ROOT / "mechanical-engineering-report-f9.json"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: objet JSON attendu")
    return value


def torque_nm(power_value: float, watts_per_unit: float, speed_rpm: float) -> float:
    if power_value <= 0.0 or watts_per_unit <= 0.0 or speed_rpm <= 0.0:
        raise ValueError("puissance, conversion et régime doivent être strictement positifs")
    return power_value * watts_per_unit / (2.0 * math.pi * speed_rpm / 60.0)


def build_report(config: dict[str, Any]) -> dict[str, Any]:
    load_basis = config["powertrain_load_basis"]
    power = load_basis["target_power"]
    power_value = float(power["value"])
    watts_per_unit = float(power["watts_per_unit"])
    service_factor = float(load_basis["preliminary_service_factor"]["value"])
    speeds = [float(value) for value in load_basis["equivalent_power_speeds_rpm"]]

    torque_table = []
    for speed in speeds:
        input_torque = torque_nm(power_value, watts_per_unit, speed)
        torque_table.append(
            {
                "speed_rpm": speed,
                "equivalent_input_torque_nm": round(input_torque, 1),
                "preliminary_design_input_torque_nm": round(input_torque * service_factor, 1),
            }
        )

    required_raw = max(row["equivalent_input_torque_nm"] for row in torque_table)
    required_design = max(row["preliminary_design_input_torque_nm"] for row in torque_table)
    comparisons = []
    for candidate in config["transaxle_candidates"]:
        best_rating = max(float(item["maximum_input_torque_nm"]) for item in candidate["ratings"])
        comparisons.append(
            {
                "candidate_id": candidate["candidate_id"],
                "best_published_rating_nm": best_rating,
                "margin_to_max_raw_equivalent_nm": round(best_rating - required_raw, 1),
                "margin_to_preliminary_design_requirement_nm": round(best_rating - required_design, 1),
                "passes_all_raw_equivalent_points": best_rating >= required_raw,
                "passes_preliminary_service_screen": best_rating >= required_design,
                "public_GA_available": candidate["public_overall_dimensions_mm"] is not None,
                "selected": False,
            }
        )

    required_inputs = config["required_input_register"]
    missing_inputs = [item["input_id"] for item in required_inputs if item["value"] is None]
    blocked_load_cases = [
        item["load_case_id"] for item in config["load_cases"] if item["status"].startswith("blocked_")
    ]

    return {
        "schema_version": config["schema_version"],
        "phase": config["phase"],
        "engineering_basis_id": config["engineering_basis_id"],
        "status": config["status"],
        "calculation_basis": {
            "target_power": power,
            "preliminary_service_factor": load_basis["preliminary_service_factor"],
            "formula": load_basis["formula"],
            "warning": load_basis["warning"],
        },
        "torque_table": torque_table,
        "requirements": {
            "maximum_raw_equivalent_input_torque_nm": required_raw,
            "minimum_preliminary_design_input_torque_nm": required_design,
            "governing_speed_rpm": min(speeds),
        },
        "candidate_comparisons": comparisons,
        "decision": {
            "selected_transaxle": None,
            "all_public_candidates_fail_preliminary_service_screen": not any(
                item["passes_preliminary_service_screen"] for item in comparisons
            ),
            "public_candidates_with_complete_GA": [
                item["candidate_id"] for item in comparisons if item["public_GA_available"]
            ],
            "current_direction": config["architecture_decision"]["current_direction"],
            "reason": (
                "Aucun candidat public ne satisfait le couple de calcul préliminaire; "
                "aucun plan général public ne permet en outre de valider le packaging."
            ),
        },
        "readiness": {
            "required_input_count": len(required_inputs),
            "missing_required_input_count": len(missing_inputs),
            "missing_required_input_ids": missing_inputs,
            "blocked_load_case_ids": blocked_load_cases,
            "mass_distribution_computable": False,
            "mount_reactions_computable": False,
            "thermal_sizing_computable": False,
        },
        "release_gates": config["release_gates"],
    }


def validate(config: dict[str, Any], report: dict[str, Any]) -> None:
    upstream = config["upstream"]
    if upstream["latest_artistic_brief"]["authority"] != "visual_brief_only_no_dimensional_or_engineering_authority":
        raise ValueError("le rendu artistique ne doit avoir aucune autorité géométrique")
    if config["architecture_decision"]["compactness_is_requirement"]:
        raise ValueError("la compacité ne peut pas primer sur la capacité mécanique")
    if config["architecture_decision"]["selected_transaxle"] is not None:
        raise ValueError("aucune boîte ne peut être sélectionnée à ce stade")
    if any(candidate["public_overall_dimensions_mm"] is not None for candidate in config["transaxle_candidates"]):
        raise ValueError("une enveloppe publique non prouvée a été renseignée")
    if not report["decision"]["all_public_candidates_fail_preliminary_service_screen"]:
        raise ValueError("le screening F9 attend que tous les candidats publics échouent")
    if report["decision"]["public_candidates_with_complete_GA"]:
        raise ValueError("aucun plan général public complet n'est disponible")
    if report["requirements"]["minimum_preliminary_design_input_torque_nm"] <= 2000.0:
        raise ValueError("le cas 1600 hp à 7000 tr/min avec facteur 1,3 doit dépasser 2000 Nm")
    if report["readiness"]["missing_required_input_count"] != report["readiness"]["required_input_count"]:
        raise ValueError("les entrées physiques F9 doivent rester explicitement non acquises")
    if any(config["release_gates"].values()) or any(report["release_gates"].values()):
        raise ValueError("tous les gates F9 doivent rester fermés")


def write_report(report: dict[str, Any]) -> None:
    WORK_ROOT.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("build", "check"), default="build")
    args = parser.parse_args()

    config = load_json(CONFIG_PATH)
    report = build_report(config)
    validate(config, report)
    if args.mode == "build":
        write_report(report)
        print(REPORT_PATH)
    else:
        print("911-917 mechanical engineering F9: PASS (preliminary screening, all release gates closed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
