#!/usr/bin/env python3
"""Dimensionnement analytique croisé du porte-axes, axes et culbuteurs F37."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--kinematics", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    kinematics = json.loads(args.kinematics.read_text(encoding="utf-8"))
    rocker = contract["rocker_carrier"]
    material = contract["component_material_and_load_screen"]
    pivot_screen = contract["rocker_pivot_reaction_screen"]
    spring_load = float(material["worst_open_spring_load_per_valve_n"])
    dynamic_factor = float(material["dynamic_load_factor"])
    spring_design_load = spring_load * dynamic_factor
    cam_to_valve_ratio = float(pivot_screen["cam_to_valve_force_ratio"])
    pivot_envelope_factor = float(pivot_screen["collinear_upper_envelope_factor"])
    cam_design_load = spring_design_load * cam_to_valve_ratio
    pivot_envelope_load = spring_design_load * pivot_envelope_factor
    if not math.isclose(pivot_envelope_factor, 1.0 + cam_to_valve_ratio, rel_tol=0.0, abs_tol=1.0e-12):
        raise RuntimeError("rocker_pivot_collinear_envelope_factor_mismatch")
    if pivot_screen["actual_resultant_direction_complete"] is not False:
        raise RuntimeError("rocker_pivot_resultant_direction_must_remain_fail_closed")
    if contract["release_gates"]["rocker_pivot_resultant_load_complete"] is not False:
        raise RuntimeError("rocker_pivot_resultant_gate_must_remain_fail_closed")

    support_span = float(rocker["screen_support_span_mm"])
    load_x = 18.0
    load_distance_from_support = support_span / 2.0 - load_x
    rail_width = float(rocker["rail_size_xyz_mm"][1])
    rail_bottom = float(rocker["rail_centre_z_mm"]) - float(rocker["rail_size_xyz_mm"][2]) / 2.0
    window_bottom = float(rocker["intake_axis_yz_mm"][1]) - 10.5
    chord_height = window_bottom - rail_bottom
    inertia = rail_width * chord_height**3 / 12.0
    section_modulus = rail_width * chord_height**2 / 6.0
    maximum_moment = pivot_envelope_load * load_distance_from_support
    rail_stress = maximum_moment / section_modulus
    rail_yield = float(material["rocker_carrier"]["screen_yield_mpa_at_200c"])

    elastic_modulus = 65_000.0
    x = np.linspace(0.0, support_span, 4001)
    moment = pivot_envelope_load * x
    moment -= pivot_envelope_load * np.maximum(x - load_distance_from_support, 0.0)
    moment -= pivot_envelope_load * np.maximum(x - (support_span - load_distance_from_support), 0.0)
    curvature = moment / (elastic_modulus * inertia)
    dx = x[1] - x[0]
    slope = np.concatenate(([0.0], np.cumsum(0.5 * (curvature[1:] + curvature[:-1]) * dx)))
    deflection_raw = np.concatenate(([0.0], np.cumsum(0.5 * (slope[1:] + slope[:-1]) * dx)))
    deflection_numerical = deflection_raw - deflection_raw[-1] * x / support_span
    maximum_deflection_numerical = abs(float(deflection_numerical.min()))
    maximum_deflection_closed_form = (
        pivot_envelope_load
        * load_distance_from_support
        * (3.0 * support_span**2 - 4.0 * load_distance_from_support**2)
        / (24.0 * elastic_modulus * inertia)
    )
    deflection_difference = abs(maximum_deflection_closed_form - maximum_deflection_numerical) / maximum_deflection_closed_form

    first_kinematic = kinematics["cases"][0]
    effective_lever = float(first_kinematic["effective_tangential_lever_mm"])
    rocker_width, rocker_height = map(float, rocker["rocker_arm_section_xz_mm"])
    rocker_section_modulus = rocker_width * rocker_height**2 / 6.0
    rocker_stress = spring_design_load * effective_lever / rocker_section_modulus
    rocker_yield = float(material["rockers"]["screen_yield_mpa"])

    shaft_diameter = float(rocker["shaft_final_diameter_mm"])
    shaft_window_span = 15.0
    shaft_moment = pivot_envelope_load * shaft_window_span / 4.0
    shaft_section_modulus = math.pi * shaft_diameter**3 / 32.0
    shaft_stress = shaft_moment / shaft_section_modulus
    shaft_yield = float(material["rocker_shafts"]["screen_yield_mpa"])

    # Le cisaillement est porté par le goujon, non par le diamètre fini de son
    # passage dans le porte-axes. Garder les deux dimensions distinctes évite
    # de surévaluer artificiellement la section résistante.
    stud_diameter = float(rocker["shared_head_stud_nominal_diameter_mm"])
    stud_shear = pivot_envelope_load / (math.pi * stud_diameter**2 / 4.0)
    bolt_shear_allowable = 400.0
    bearing_pressure = pivot_envelope_load / (shaft_diameter * 15.0)
    factors = {
        "carrier_hot_yield": rail_yield / rail_stress,
        "rocker_yield": rocker_yield / rocker_stress,
        "shaft_yield": shaft_yield / shaft_stress,
        "shared_head_stud_shear": bolt_shear_allowable / stud_shear,
    }
    minimum_fos = float(material["minimum_screen_factor_of_safety"])
    gates = {
        "carrier_factor_of_safety_at_least_2": factors["carrier_hot_yield"] >= minimum_fos,
        "rocker_factor_of_safety_at_least_2": factors["rocker_yield"] >= minimum_fos,
        "shaft_factor_of_safety_at_least_3": factors["shaft_yield"] >= 3.0,
        "shared_head_stud_shear_factor_at_least_3": factors["shared_head_stud_shear"] >= 3.0,
        "carrier_midspan_deflection_below_0_15_mm": maximum_deflection_numerical <= 0.15,
        "two_deflection_methods_agree_within_0_1_percent": deflection_difference <= 0.001,
        "pivot_reaction_magnitude_upper_envelope_applied": True,
        "actual_resultant_direction_complete": False,
        "rocker_pivot_resultant_load_complete": False,
        "nonlinear_contact_fea_complete": False,
        "material_cards_qualified": bool(material["material_cards_qualified"]),
        "fatigue_rig_correlated": False,
    }
    report = {
        "schema_version": "1.0.0",
        "phase": "F37",
        "status": "carrier_rocker_shaft_envelope_screen_complete_actual_pivot_direction_and_fea_pending",
        "inputs": {"contract_sha256": sha256(args.contract), "kinematics_sha256": sha256(args.kinematics)},
        "loads": {
            "spring_open_n": spring_load,
            "dynamic_factor": dynamic_factor,
            "spring_only_design_load_per_valve_n": spring_design_load,
            "cam_side_design_load_per_valve_n": cam_design_load,
            "cam_to_valve_force_ratio": cam_to_valve_ratio,
            "pivot_reaction_collinear_upper_envelope_factor": pivot_envelope_factor,
            "pivot_reaction_upper_envelope_per_valve_n": pivot_envelope_load,
            "carrier_shaft_and_mount_load_case": "pivot_reaction_magnitude_upper_envelope_applied_along_valve_axis_screen_direction",
            "actual_resultant_direction_complete": False,
        },
        "carrier": {
            "support_span_mm": support_span,
            "two_load_positions_from_left_support_mm": [load_distance_from_support, support_span - load_distance_from_support],
            "minimum_lower_chord_height_mm": chord_height,
            "second_moment_mm4": inertia,
            "section_modulus_mm3": section_modulus,
            "maximum_bending_moment_n_mm": maximum_moment,
            "bending_stress_mpa": rail_stress,
            "midspan_deflection_numerical_mm": maximum_deflection_numerical,
            "midspan_deflection_closed_form_mm": maximum_deflection_closed_form,
            "two_method_relative_difference": deflection_difference,
            "spring_only_scaled_midspan_deflection_mm": maximum_deflection_numerical / pivot_envelope_factor,
            "spring_only_scaled_bending_stress_mpa": rail_stress / pivot_envelope_factor,
            "shaft_bearing_pressure_mpa": bearing_pressure,
        },
        "rocker": {
            "load_case": "spring_side_design_load",
            "arm_section_xz_mm": [rocker_width, rocker_height],
            "bending_stress_mpa": rocker_stress,
            "section_modulus_mm3": rocker_section_modulus,
        },
        "shaft": {"bending_stress_mpa": shaft_stress, "section_modulus_mm3": shaft_section_modulus},
        "mount": {
            "shared_head_stud_nominal_diameter_mm": stud_diameter,
            "carrier_finished_clearance_diameter_mm": float(rocker["mount_final_clearance_diameter_mm"]),
            "shared_head_stud_nominal_screen_shear_stress_mpa": stud_shear,
            "screen_shear_allowable_mpa": bolt_shear_allowable,
            "clamp_stack_released": False,
        },
        "factors_of_safety": factors,
        "gates": gates,
        "limitations": [
            "Euler-Bernoulli linear elastic beam screen",
            "pivot reaction uses a collinear magnitude upper envelope applied in the valve-axis screen direction; actual cam/valve force directions are unavailable",
            "no shaft-carrier-rocker contact",
            "no bolt preload",
            "no thermal distortion",
            "no fatigue correlation",
        ],
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "f37-carrier-strength-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), facecolor="#eef1f3")
    axes[0].plot(x - support_span / 2.0, moment / 1000.0, color="#2f7196", linewidth=3)
    axes[0].fill_between(x - support_span / 2.0, 0.0, moment / 1000.0, color="#76a8c3", alpha=0.45)
    axes[0].set_xlabel("X le long du rail [mm]")
    axes[0].set_ylabel("Moment fléchissant [N·m]")
    axes[0].set_title("Deux charges dynamiques par rail", weight="bold")
    axes[0].grid(alpha=0.25)
    labels = ["porte-axes chaud", "culbuteur", "axe", "goujon partage"]
    fos_values = [factors["carrier_hot_yield"], factors["rocker_yield"], factors["shaft_yield"], factors["shared_head_stud_shear"]]
    bars = axes[1].bar(labels, fos_values, color=["#3d8c71", "#547c9a", "#747982", "#a4763c"])
    axes[1].axhline(2.0, color="#a2312c", linewidth=2, label="minimum écran = 2")
    axes[1].bar_label(bars, fmt="%.2f", padding=3)
    axes[1].tick_params(axis="x", rotation=20)
    axes[1].set_ylabel("Facteur de sécurité sur limite écran")
    axes[1].set_title("Résistance analytique des composants", weight="bold")
    axes[1].grid(axis="y", alpha=0.25)
    axes[1].legend(frameon=False)
    fig.suptitle("F37 — pré-dimensionnement du porte-axes et des culbuteurs", fontsize=15, weight="bold")
    fig.text(0.5, 0.01, "Pivot: enveloppe 2,15× la charge ressort dynamique; direction réelle, contact et fatigue non validés", ha="center", color="#9e2f2a", weight="bold")
    fig.tight_layout(rect=(0, 0.05, 1, 0.93))
    fig.savefig(args.output / "917-head-f37-carrier-strength-screen.png", dpi=180)
    plt.close(fig)
    print(json.dumps({"status": report["status"], "factors_of_safety": factors, "gates": gates}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
