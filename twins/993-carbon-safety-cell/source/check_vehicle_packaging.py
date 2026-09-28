#!/usr/bin/env python3
"""Vérifie la cohérence interne des enveloppes de packaging C2/C4."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
TWIN_ROOT = HERE.parent
ROOT = TWIN_ROOT.parents[1]
CONFIG = TWIN_ROOT / "design-space.json"
CONTRACT = TWIN_ROOT / "vehicle-packaging-contract.json"
CAD_REPORT = TWIN_ROOT / "derived" / "cad-generation-report.json"
OUTPUT = TWIN_ROOT / "derived" / "packaging-clearance-check.json"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: objet JSON attendu")
    return value


def build_report() -> dict[str, Any]:
    config = load_json(CONFIG)
    contract = load_json(CONTRACT)
    cad = load_json(CAD_REPORT)
    geometry = config["screening_geometry_mm"]
    package = config["vehicle_packaging_mm"]
    common = package["common_cell"]
    c2 = package["c2_package"]
    c4 = package["c4_package"]
    services = package["protected_service_channels"]

    floor_z = float(geometry["floor_z"])
    tunnel_inner_half_width = (float(common["tunnel_outer_width"]) - 2.0 * 26.0) / 2.0
    tunnel_inner_top_z = floor_z + float(common["tunnel_outer_height"]) - float(common["service_cover_thickness"]) / 2.0
    c2_radius = float(c2["external_shift_rod_diameter"]) / 2.0
    c4_outer_radius = float(c4["central_tube_outer_diameter"]) / 2.0
    c4_shift_radius = float(c4["shift_guide_diameter"]) / 2.0
    c4_center_z = float(c4["central_tube_center_z"])
    c4_shift_center_z = c4_center_z + 82.0
    service_radius = float(services["service_tube_diameter"]) / 2.0
    service_y_values = [abs(float(services[key])) for key in (
        "brake_fuel_left_center_y",
        "wiring_right_center_y",
        "parking_brake_left_center_y",
        "parking_brake_right_center_y",
    )]
    minimum_service_separation = min(service_y_values) - service_radius - c4_outer_radius

    checks = [
        {
            "check_id": "C2_SHIFT_ROD_INSIDE_TUNNEL",
            "passed": abs(float(c2["external_shift_rod_center_y"])) + c2_radius < tunnel_inner_half_width and floor_z < float(c2["external_shift_rod_center_z"]) - c2_radius and float(c2["external_shift_rod_center_z"]) + c2_radius < tunnel_inner_top_z,
            "margin_y_mm": tunnel_inner_half_width - abs(float(c2["external_shift_rod_center_y"])) - c2_radius,
            "status": "hypothesis_check_only",
        },
        {
            "check_id": "C4_CENTRAL_TUBE_INSIDE_TUNNEL",
            "passed": c4_outer_radius < tunnel_inner_half_width and floor_z < c4_center_z - c4_outer_radius and c4_center_z + c4_outer_radius < tunnel_inner_top_z,
            "margin_y_mm": tunnel_inner_half_width - c4_outer_radius,
            "margin_top_z_mm": tunnel_inner_top_z - c4_center_z - c4_outer_radius,
            "status": "hypothesis_check_only",
        },
        {
            "check_id": "C4_SHIFT_GUIDE_INSIDE_TUNNEL",
            "passed": abs(float(c4["shift_guide_center_y"])) + c4_shift_radius < tunnel_inner_half_width and c4_shift_center_z + c4_shift_radius < tunnel_inner_top_z,
            "margin_y_mm": tunnel_inner_half_width - abs(float(c4["shift_guide_center_y"])) - c4_shift_radius,
            "margin_top_z_mm": tunnel_inner_top_z - c4_shift_center_z - c4_shift_radius,
            "status": "hypothesis_check_only",
        },
        {
            "check_id": "FIXED_SERVICES_OUTSIDE_C4_ROTATION_ENVELOPE",
            "passed": minimum_service_separation >= 100.0,
            "minimum_radial_separation_mm": minimum_service_separation,
            "provisional_required_separation_mm": 100.0,
            "status": "hypothesis_check_only",
        },
        {
            "check_id": "ALL_FOUR_VARIANTS_EXPORTED",
            "passed": set(cad["driveline_packages"]) == set(contract["variant_matrix"]),
            "variants": sorted(cad["driveline_packages"]),
            "status": "file_contract_check",
        },
        {
            "check_id": "C4_FRONT_DRIVE_FEATURES_PRESENT",
            "passed": all({"central_tube_clearance", "propeller_shaft_clearance", "front_final_drive_clearance", "front_halfshaft_clearance"}.issubset(set(cad["driveline_packages"][variant]["feature_ids"])) for variant in ("964_C4", "993_C4")),
            "status": "file_contract_check",
        },
    ]
    passed = all(item["passed"] for item in checks)
    return {
        "schema_version": "1.0.0",
        "status": "concept_checks_passed_not_measured" if passed else "concept_checks_failed",
        "passed": passed,
        "checks": checks,
        "inputs": {
            "design_space": str(CONFIG.relative_to(ROOT)),
            "packaging_contract": str(CONTRACT.relative_to(ROOT)),
            "cad_report": str(CAD_REPORT.relative_to(ROOT)),
        },
        "claim_limits": [
            "Les marges sont calculées entre enveloppes hypothétiques; elles ne valident pas une pièce Porsche réelle.",
            "Les mouvements de joints, fouettement d'arbre, tolérances, déformations et dilatations thermiques ne sont pas modélisés.",
            "La réussite ne donne aucun crédit de rigidité, fatigue, crash, feu, fabrication, route, circuit ou TÜV.",
        ],
        "release_gates": {
            "measured_vehicle_clearance": False,
            "dynamic_driveline_clearance": False,
            "manufacturing_authorized": False,
            "road_or_track_use_authorized": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = build_report()
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.write:
        OUTPUT.write_text(rendered, encoding="utf-8")
    elif not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != rendered:
        print(f"stale: {OUTPUT.relative_to(ROOT)}")
        return 1
    print(f"packaging C2/C4: {len(report['checks'])} checks, passed={str(report['passed']).lower()}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
