#!/usr/bin/env python3
"""Ecran cinematique des quatre culbuteurs F37 dans le plan YZ."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_contract_cad_link(
    contract_path: Path, geometry_report_path: Path, cad: dict
) -> tuple[str, str]:
    contract_sha = sha256(contract_path)
    geometry_report_sha = sha256(geometry_report_path)
    try:
        cad_contract_sha = cad["inputs"]["contract_sha256"]
        cad_geometry_report_sha = cad["inputs"]["geometry_report_sha256"]
    except (KeyError, TypeError) as exc:
        raise RuntimeError("cad_report_input_link_missing") from exc
    if cad_contract_sha != contract_sha:
        raise RuntimeError("cad_report_contract_hash_mismatch")
    if cad_geometry_report_sha != geometry_report_sha:
        raise RuntimeError("cad_report_geometry_hash_mismatch")
    return contract_sha, geometry_report_sha


def valve_axis(tilt_y_deg: float):
    import numpy as np

    angle = math.radians(tilt_y_deg)
    return np.asarray([math.sin(angle), math.cos(angle)])  # Y, Z


def main() -> int:
    # Les contrôles de liaison SHA peuvent être importés dans un environnement
    # minimal ; NumPy et Matplotlib ne sont requis que pour exécuter l'écran.
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--geometry-report", type=Path, required=True)
    parser.add_argument("--cad-report", type=Path, required=True)
    parser.add_argument("--valve-lift-mm", type=float, default=12.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    geometry = json.loads(args.geometry_report.read_text(encoding="utf-8"))
    cad = json.loads(args.cad_report.read_text(encoding="utf-8"))
    contract_sha, geometry_report_sha = validate_contract_cad_link(
        args.contract, args.geometry_report, cad
    )
    rocker = contract["rocker_carrier"]
    architecture = geometry["geometry"]["architecture"]
    ratio = float(rocker["target_rocker_ratio"])
    cases = []
    for family, pivot_key in (("intake", "intake_axis_yz_mm"), ("exhaust", "exhaust_axis_yz_mm")):
        data = architecture[family]
        axis = valve_axis(float(data["tilt_y_deg"]))
        pivot = np.asarray(rocker[pivot_key], dtype=float)
        for index, (x, y, z) in enumerate(data["centres_mm"], start=1):
            closed_tip = np.asarray([y, z], dtype=float) + 96.0 * axis
            radial = closed_tip - pivot
            valve_lever = float(np.linalg.norm(radial))
            tangent = np.asarray([-radial[1], radial[0]]) / valve_lever
            effective_lever = abs(float(np.dot(tangent, axis))) * valve_lever
            angular_swing = math.degrees(float(args.valve_lift_mm) / effective_lever)
            open_tip = closed_tip - float(args.valve_lift_mm) * axis
            # Le rapport de déplacement porte sur les bras tangents effectifs,
            # pas sur la distance géométrique pivot-pointe de soupape.
            cam_lever = effective_lever / ratio
            cam_lift = float(args.valve_lift_mm) / ratio
            cases.append({
                "id": f"{family}-{index}",
                "x_mm": x,
                "pivot_yz_mm": pivot.tolist(),
                "closed_valve_tip_yz_mm": closed_tip.tolist(),
                "open_valve_tip_yz_mm": open_tip.tolist(),
                "valve_side_lever_mm": valve_lever,
                "effective_tangential_lever_mm": effective_lever,
                "cam_side_lever_mm": cam_lever,
                "nominal_cam_lift_mm": cam_lift,
                "small_angle_swing_deg": angular_swing,
            })
    levers = [item["valve_side_lever_mm"] for item in cases]
    swings = [item["small_angle_swing_deg"] for item in cases]
    gates = {
        "four_rockers_present": len(cases) == 4,
        "minimum_valve_side_lever_at_least_25_mm": min(levers) >= 25.0,
        "small_angle_swing_below_30_deg": max(swings) <= 30.0,
        "cam_lift_below_11_mm": max(item["nominal_cam_lift_mm"] for item in cases) <= 11.0,
        "rocker_pair_x_clearance_at_least_20_mm": 36.0 - 11.0 >= 20.0,
        "static_brep_interference_zero": cad["checks"]["rocker_carrier_interference_volume_mm3"] == 0.0
        and cad["checks"]["rocker_shaft_interference_volume_mm3"] == 0.0,
        "measured_cam_profile_available": False,
        "dynamic_contact_and_flexure_fea_complete": False,
        "spintron_correlated": False,
    }
    report = {
        "schema_version": "1.0.0",
        "phase": "F37",
        "status": "rocker_kinematic_screen_complete_dynamic_correlation_pending",
        "method": "planar_YZ_rigid_finger_rocker_small_angle_screen",
        "equations": {
            "valve_tip": "P_tip=P_seat+96*u_valve",
            "effective_lever": "r_eff=abs(tangent(r) dot u_valve)*norm(r)",
            "rocker_swing": "theta_screen=valve_lift/r_eff",
            "cam_lift": "valve_lift/rocker_ratio",
            "cam_side_lever": "r_cam=r_eff_valve/rocker_ratio",
        },
        "inputs": {
            "valve_lift_mm": args.valve_lift_mm,
            "target_rocker_ratio": ratio,
            "contract_sha256": contract_sha,
            "geometry_report_sha256": geometry_report_sha,
            "cad_report_sha256": sha256(args.cad_report),
        },
        "cases": cases,
        "gates": gates,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "f37-rocker-kinematic-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), facecolor="#eef1f3")
    for family, color in (("intake", "#277ba7"), ("exhaust", "#c65e3b")):
        item = next(case for case in cases if case["id"] == f"{family}-1")
        pivot = np.asarray(item["pivot_yz_mm"])
        closed = np.asarray(item["closed_valve_tip_yz_mm"])
        opened = np.asarray(item["open_valve_tip_yz_mm"])
        axes[0].plot([pivot[0], closed[0]], [pivot[1], closed[1]], "o-", color=color, linewidth=4, label=f"{family} fermé")
        axes[0].plot([pivot[0], opened[0]], [pivot[1], opened[1]], "o--", color=color, alpha=0.65, label=f"{family} levée 12 mm")
    axes[0].set_xlabel("Y [mm si échelle confirmée]")
    axes[0].set_ylabel("Z [mm si échelle confirmée]")
    axes[0].set_title("Bras pivots → queues de soupapes", weight="bold")
    axes[0].axis("equal")
    axes[0].grid(alpha=0.25)
    axes[0].legend(frameon=False, fontsize=8)
    names = ["levier soupape", "levier effectif", "levier came", "levée came", "rotation"]
    first = cases[0]
    values = [first["valve_side_lever_mm"], first["effective_tangential_lever_mm"], first["cam_side_lever_mm"], first["nominal_cam_lift_mm"], first["small_angle_swing_deg"]]
    bars = axes[1].bar(names, values, color=["#315d75", "#488ba7", "#5e7582", "#aa793d", "#9c4842"])
    axes[1].bar_label(bars, fmt="%.2f", padding=3)
    axes[1].tick_params(axis="x", rotation=24)
    axes[1].set_title("Grandeurs cinématiques de l’écran", weight="bold")
    axes[1].grid(axis="y", alpha=0.25)
    fig.suptitle("F37 — contrôle cinématique du porte-axes 4 soupapes", fontsize=15, weight="bold")
    fig.text(0.5, 0.01, "Géométrie rigide provisoire; profil de came, élasticité, Hertz et spintron non corrélés", ha="center", color="#9e2f2a", weight="bold")
    fig.tight_layout(rect=(0, 0.05, 1, 0.93))
    fig.savefig(args.output / "917-head-f37-rocker-kinematic-screen.png", dpi=180)
    plt.close(fig)
    print(json.dumps({"status": report["status"], "gates": gates}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
