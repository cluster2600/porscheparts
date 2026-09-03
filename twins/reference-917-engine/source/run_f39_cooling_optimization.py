#!/usr/bin/env python3
"""Optimisation paramétrique scan-only du refroidissement 917 F39."""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def conductivity_at_c(contract: dict, temperature_c: float) -> float:
    points = contract["provisional_material_cp1"]["conductivity_w_mk_by_temperature_c"]
    if temperature_c <= points[0][0]:
        return float(points[0][1])
    if temperature_c >= points[-1][0]:
        return float(points[-1][1])
    for (t0, k0), (t1, k1) in zip(points, points[1:]):
        if t0 <= temperature_c <= t1:
            fraction = (temperature_c - t0) / (t1 - t0)
            return float(k0) + fraction * (float(k1) - float(k0))
    raise AssertionError("intervalle de conductivité absent")


def conductivity_integral(contract: dict, low_c: float, high_c: float) -> float:
    """Integrate the piecewise-linear provisional k(T) law exactly."""
    if high_c <= low_c:
        return 0.0
    material_points = contract["provisional_material_cp1"]["conductivity_w_mk_by_temperature_c"]
    nodes = [low_c]
    nodes.extend(float(temperature) for temperature, _ in material_points if low_c < float(temperature) < high_c)
    nodes.append(high_c)
    return sum(
        0.5 * (conductivity_at_c(contract, start) + conductivity_at_c(contract, end)) * (end - start)
        for start, end in zip(nodes, nodes[1:])
    )


def solve_bridge_temperature(contract: dict, root_c: float, heat_w: float, root_radius_mm: float) -> float:
    network = contract["bridge_network"]
    length = float(network["conduction_length_mm"]) * 1e-3
    area_gain = 1.0 + float(network["root_area_gain_per_added_radius_mm"]) * (root_radius_mm - 2.0)
    area = float(network["baseline_effective_cross_section_mm2"]) * area_gain * 1e-6
    required = heat_w * length / area
    low, high = root_c, root_c + 900.0
    for _ in range(90):
        middle = 0.5 * (low + high)
        if conductivity_integral(contract, root_c, middle) < required:
            low = middle
        else:
            high = middle
    return 0.5 * (low + high)


def fin_efficiency(h: float, thickness_m: float, height_m: float, solid_k: float = 135.0) -> float:
    parameter = math.sqrt(2.0 * h / (solid_k * thickness_m)) * height_m
    return math.tanh(parameter) / parameter


def candidate_geometry(contract: dict, levels: int, thickness_mm: float, gap_mm: float, span_mm: float, length_mm: float) -> dict:
    passages = 2 * (levels - 1)
    stack_height = levels * thickness_mm + (levels - 1) * gap_mm
    open_area = passages * gap_mm * span_mm * 1e-6
    anchor = contract["scan_surface_anchor"]
    area = (
        float(anchor["area_m2_if_scale_is_mm"])
        * levels / float(anchor["baseline_fin_levels"])
        * span_mm / float(anchor["baseline_span_mm"])
        * length_mm / float(anchor["baseline_flow_length_mm"])
    )
    return {
        "passage_count_equivalent": passages,
        "stack_height_mm": stack_height,
        "open_area_m2": open_area,
        "wetted_area_proxy_m2": area,
        "fits_scan_envelope_screen": stack_height <= float(contract["search_space"]["maximum_fin_stack_height_mm"]),
    }


def method_a(contract: dict, geometry: dict, thickness_mm: float, gap_mm: float, span_mm: float, length_mm: float, duct: dict, mass_flow: float) -> dict:
    bc = contract["fixed_boundaries"]
    model = contract["method_a_openfoam_anchored"]
    rho = float(bc["air_density_kg_m3"])
    velocity = mass_flow * float(duct["capture_fraction"]) / (rho * geometry["open_area_m2"])
    gap = gap_mm * 1e-3
    span = span_mm * 1e-3
    hydraulic_diameter = 2.0 * gap * span / (gap + span)
    h_isothermal = (
        float(model["reference_h_w_m2k"])
        * (velocity / float(model["reference_velocity_m_s"])) ** float(model["heat_velocity_exponent"])
        * (hydraulic_diameter / float(model["reference_hydraulic_diameter_m"])) ** float(model["heat_hydraulic_diameter_exponent"])
    )
    eta = fin_efficiency(h_isothermal, thickness_mm * 1e-3, 0.019)
    baseline_eta = fin_efficiency(float(model["reference_h_w_m2k"]), 0.002, 0.019)
    h_effective = h_isothermal * eta / baseline_eta
    straight_dp = (
        float(model["reference_pressure_drop_pa"])
        * (velocity / float(model["reference_velocity_m_s"])) ** float(model["pressure_velocity_exponent"])
        * (hydraulic_diameter / float(model["reference_hydraulic_diameter_m"])) ** float(model["pressure_hydraulic_diameter_exponent"])
        * (length_mm * 1e-3 / float(model["reference_length_m"]))
    )
    dynamic_pressure = 0.5 * rho * velocity**2
    return {
        "method": "OpenFOAM_F38_anchored_reduced_order_scaling",
        "velocity_m_s": velocity,
        "hydraulic_diameter_m": hydraulic_diameter,
        "fin_efficiency": eta,
        "effective_h_w_m2k": h_effective,
        "straight_pressure_drop_pa": straight_dp,
        "total_pressure_drop_pa": straight_dp + float(duct["minor_loss_k"]) * dynamic_pressure,
        "new_CFD_executed_for_candidate": False,
    }


def method_b(contract: dict, geometry: dict, thickness_mm: float, gap_mm: float, span_mm: float, length_mm: float, duct: dict, mass_flow: float) -> dict:
    bc = contract["fixed_boundaries"]
    rho = float(bc["air_density_kg_m3"])
    velocity = mass_flow * float(duct["capture_fraction"]) / (rho * geometry["open_area_m2"])
    gap = gap_mm * 1e-3
    span = span_mm * 1e-3
    length = length_mm * 1e-3
    hydraulic_diameter = 2.0 * gap * span / (gap + span)
    reynolds = rho * velocity * hydraulic_diameter / float(bc["air_dynamic_viscosity_pa_s"])
    friction = (0.79 * math.log(reynolds) - 1.64) ** -2
    prandtl = float(bc["air_prandtl"])
    nusselt = (
        (friction / 8.0) * (reynolds - 1000.0) * prandtl
        / (1.0 + 12.7 * math.sqrt(friction / 8.0) * (prandtl ** (2.0 / 3.0) - 1.0))
    )
    h_isothermal = nusselt * float(bc["air_thermal_conductivity_w_mk"]) / hydraulic_diameter
    eta = fin_efficiency(h_isothermal, thickness_mm * 1e-3, 0.019)
    dynamic_pressure = 0.5 * rho * velocity**2
    straight_dp = friction * length / hydraulic_diameter * dynamic_pressure
    return {
        "method": "Gnielinski_Darcy_Weisbach_closed_form",
        "velocity_m_s": velocity,
        "hydraulic_diameter_m": hydraulic_diameter,
        "reynolds": reynolds,
        "darcy_friction_factor": friction,
        "nusselt": nusselt,
        "fin_efficiency": eta,
        "effective_h_w_m2k": h_isothermal * eta,
        "straight_pressure_drop_pa": straight_dp,
        "total_pressure_drop_pa": straight_dp + float(duct["minor_loss_k"]) * dynamic_pressure,
    }


def thermal_result(contract: dict, geometry: dict, convection: dict, root_radius_mm: float, total_heat_w: float, oil_heat_w: float) -> dict:
    bc = contract["fixed_boundaries"]
    air_heat = total_heat_w - oil_heat_w
    inlet_c = float(bc["air_inlet_temperature_k"]) - 273.15
    root_c = inlet_c + air_heat / (float(convection["effective_h_w_m2k"]) * geometry["wetted_area_proxy_m2"])
    bridge_c = solve_bridge_temperature(contract, root_c, air_heat, root_radius_mm)
    return {
        "total_heat_w": total_heat_w,
        "local_oil_heat_removal_w": oil_heat_w,
        "air_heat_w": air_heat,
        "fin_root_temperature_c": root_c,
        "bridge_temperature_c": bridge_c,
        "within_CP1_interpolation_range": bridge_c <= float(contract["provisional_material_cp1"]["maximum_interpolation_temperature_c"]),
        "oil_mass_flow_kg_s_at_25k": oil_heat_w / (float(bc["oil_specific_heat_j_kgk"]) * float(bc["oil_design_temperature_rise_k"])),
    }


def evaluate(contract: dict, parameters: dict, mass_flow: float | None = None, total_heat_w: float | None = None) -> dict:
    bc = contract["fixed_boundaries"]
    objectives = contract["objectives"]
    mass_flow = float(bc["nominal_air_mass_flow_kg_s_per_head"] if mass_flow is None else mass_flow)
    total_heat_w = float(bc["nominal_chamber_heat_load_w_per_head"] if total_heat_w is None else total_heat_w)
    geometry = candidate_geometry(
        contract,
        parameters["fin_levels"],
        parameters["fin_thickness_mm"],
        parameters["clear_gap_mm"],
        parameters["mean_span_mm"],
        parameters["mean_flow_length_mm"],
    )
    a = method_a(contract, geometry, parameters["fin_thickness_mm"], parameters["clear_gap_mm"], parameters["mean_span_mm"], parameters["mean_flow_length_mm"], parameters["duct"], mass_flow)
    b = method_b(contract, geometry, parameters["fin_thickness_mm"], parameters["clear_gap_mm"], parameters["mean_span_mm"], parameters["mean_flow_length_mm"], parameters["duct"], mass_flow)
    thermal_a = thermal_result(contract, geometry, a, parameters["root_radius_mm"], total_heat_w, parameters["local_oil_heat_removal_w"])
    thermal_b = thermal_result(contract, geometry, b, parameters["root_radius_mm"], total_heat_w, parameters["local_oil_heat_removal_w"])
    h_difference = abs(a["effective_h_w_m2k"] - b["effective_h_w_m2k"]) / b["effective_h_w_m2k"]
    pressure_difference = abs(a["total_pressure_drop_pa"] - b["total_pressure_drop_pa"]) / b["total_pressure_drop_pa"]
    maximum_temperature = max(thermal_a["bridge_temperature_c"], thermal_b["bridge_temperature_c"])
    maximum_pressure = max(a["total_pressure_drop_pa"], b["total_pressure_drop_pa"])
    screen = {
        "geometry_fits": geometry["fits_scan_envelope_screen"],
        "wall_at_least_1p8mm": parameters["fin_thickness_mm"] >= float(contract["search_space"]["minimum_printed_wall_mm"]),
        "temperature_both_methods_at_most_260c": maximum_temperature <= float(objectives["maximum_bridge_temperature_c"]),
        "pressure_both_methods_at_most_6p7kpa": maximum_pressure <= float(objectives["maximum_air_pressure_drop_pa"]),
        "h_cross_method_difference_below_20percent": h_difference <= float(objectives["maximum_cross_method_h_relative_difference"]),
        "mass_flow_not_above_supported_0p85": mass_flow <= float(objectives["maximum_supported_air_mass_flow_kg_s_per_head"]),
        "oil_heat_not_above_1200w": parameters["local_oil_heat_removal_w"] <= float(objectives["maximum_local_oil_heat_removal_w"]),
    }
    screen["numerical_screen_passed"] = all(screen.values())
    normalized_constraint_violation = (
        max(0.0, maximum_temperature / float(objectives["maximum_bridge_temperature_c"]) - 1.0)
        + max(0.0, maximum_pressure / float(objectives["maximum_air_pressure_drop_pa"]) - 1.0)
        + max(0.0, h_difference / float(objectives["maximum_cross_method_h_relative_difference"]) - 1.0)
    )
    return {
        "parameters": {**parameters, "duct": parameters["duct"]["id"]},
        "operating_point": {"air_mass_flow_kg_s": mass_flow, "chamber_heat_load_w": total_heat_w},
        "geometry": geometry,
        "method_a": a,
        "method_b": b,
        "thermal_a": thermal_a,
        "thermal_b": thermal_b,
        "h_cross_method_relative_difference": h_difference,
        "pressure_drop_cross_method_relative_difference": pressure_difference,
        "maximum_bridge_temperature_c": maximum_temperature,
        "maximum_pressure_drop_pa": maximum_pressure,
        "normalized_constraint_violation": normalized_constraint_violation,
        "screen": screen,
    }


def parameter_grid(contract: dict):
    space = contract["search_space"]
    for values in itertools.product(
        space["fin_levels"],
        space["fin_thickness_mm"],
        space["clear_gap_mm"],
        space["root_radius_mm"],
        space["mean_span_mm"],
        space["mean_flow_length_mm"],
        space["duct_variants"],
        space["local_oil_heat_removal_w"],
    ):
        yield dict(zip(
            ("fin_levels", "fin_thickness_mm", "clear_gap_mm", "root_radius_mm", "mean_span_mm", "mean_flow_length_mm", "duct", "local_oil_heat_removal_w"),
            values,
        ))


def rank_key(item: dict) -> tuple:
    return (
        not item["screen"]["numerical_screen_passed"],
        0.0 if item["screen"]["numerical_screen_passed"] else item["normalized_constraint_violation"],
        item["parameters"]["local_oil_heat_removal_w"] if item["screen"]["numerical_screen_passed"] else 0.0,
        item["maximum_bridge_temperature_c"],
        item["maximum_pressure_drop_pa"],
        item["h_cross_method_relative_difference"],
    )


def render(report: dict, output: Path) -> None:
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, FancyArrowPatch, Rectangle

    all_points = report["optimization"]["compact_points"]
    selected = report["optimization"]["selected_candidate"]
    fig = plt.figure(figsize=(16, 9), facecolor="#eef2f4")
    grid = fig.add_gridspec(2, 2, hspace=0.28, wspace=0.22)

    ax_cut = fig.add_subplot(grid[:, 0])
    ax_cut.add_patch(Rectangle((0, 0), 1, 1, color="#091b24", zorder=-10))
    for index in range(selected["parameters"]["fin_levels"]):
        y = 0.10 + index * 0.76 / max(selected["parameters"]["fin_levels"] - 1, 1)
        ax_cut.add_patch(Rectangle((0.17, y), 0.66, 0.018, color="#e2a236", ec="#ffd06b"))
    ax_cut.add_patch(Circle((0.50, 0.48), 0.12, fc="#37474f", ec="#cfd8dc", lw=2))
    ax_cut.add_patch(Circle((0.50, 0.48), 0.065, fc="#d95f4f", ec="#ffab91", lw=2))
    ax_cut.plot([0.29, 0.44], [0.88, 0.58], color="#66c8ed", lw=6)
    ax_cut.plot([0.71, 0.56], [0.88, 0.58], color="#66c8ed", lw=6)
    for y in (0.18, 0.30, 0.42, 0.54, 0.66, 0.78):
        ax_cut.add_patch(FancyArrowPatch((0.02, y), (0.96, y), arrowstyle="-|>", mutation_scale=14, color="#48b8f0", lw=2))
    ax_cut.plot([0.35, 0.50, 0.65], [0.35, 0.28, 0.35], color="#f7cf5c", lw=8, solid_capstyle="round")
    ax_cut.text(0.04, 0.96, "Coupe fonctionnelle candidate", color="white", fontsize=17, weight="bold", va="top")
    ax_cut.text(0.04, 0.025, "Air forcé + déflecteurs (bleu) · huile locale (jaune) · pont chaud (rouge)", color="#d9edf7", fontsize=10)
    ax_cut.set_xlim(0, 1); ax_cut.set_ylim(0, 1); ax_cut.axis("off")

    ax_scatter = fig.add_subplot(grid[0, 1])
    passed = [point for point in all_points if point["pass"]]
    failed = [point for point in all_points if not point["pass"]]
    ax_scatter.scatter([p["dp"] / 1000 for p in failed], [p["temperature"] for p in failed], s=9, alpha=0.22, color="#a4aeb4", label="rejetés")
    if passed:
        ax_scatter.scatter([p["dp"] / 1000 for p in passed], [p["temperature"] for p in passed], s=22, alpha=0.8, color="#2b9b67", label="écran numérique passé")
    ax_scatter.scatter([selected["maximum_pressure_drop_pa"] / 1000], [selected["maximum_bridge_temperature_c"]], marker="*", s=220, color="#f1a12b", ec="black", label="sélection")
    ax_scatter.axvline(6.7, ls="--", color="#333"); ax_scatter.axhline(260, ls="--", color="#b52626")
    ax_scatter.set_xlabel("Δp maximale des deux méthodes [kPa]"); ax_scatter.set_ylabel("T pont maximale [°C]")
    ax_scatter.set_title("Espace de conception F39"); ax_scatter.legend(fontsize=8)

    ax_bar = fig.add_subplot(grid[1, 1])
    labels = ["T méthode A", "T méthode B", "limite"]
    values = [selected["thermal_a"]["bridge_temperature_c"], selected["thermal_b"]["bridge_temperature_c"], 260.0]
    colors = ["#2777b4", "#e89b2d", "#555"]
    bars = ax_bar.bar(labels, values, color=colors)
    ax_bar.set_ylabel("Température [°C]"); ax_bar.set_title("Candidat nominal sélectionné")
    ax_bar.set_ylim(0, 340)
    for bar, value in zip(bars, values):
        ax_bar.text(bar.get_x() + bar.get_width() / 2, value, f"{value:.1f}", ha="center", va="bottom", weight="bold")
    ax_bar.text(0.02, 0.97, f"hA/hB: {selected['method_a']['effective_h_w_m2k']:.1f}/{selected['method_b']['effective_h_w_m2k']:.1f} W/m²K\nΔh: {100*selected['h_cross_method_relative_difference']:.1f}% · Δp max: {selected['maximum_pressure_drop_pa']/1000:.2f} kPa\nhuile locale: {selected['parameters']['local_oil_heat_removal_w']:.0f} W", transform=ax_bar.transAxes, va="top", fontsize=9)

    fig.suptitle("Porsche 917 — optimisation thermique scan-only F39", fontsize=22, weight="bold")
    fig.text(0.5, 0.012, "PASS numérique ≠ validation : B-Rep, CHT culasse, carte matière, huile et banc restent non qualifiés", ha="center", color="#a42121", weight="bold")
    fig.savefig(output, dpi=170, bbox_inches="tight")
    plt.close(fig)


def render_sensitivity(report: dict, output: Path) -> None:
    import matplotlib.pyplot as plt

    points = report["off_design_sensitivity"]
    flows = sorted({item["operating_point"]["air_mass_flow_kg_s"] for item in points})
    loads = sorted({item["operating_point"]["chamber_heat_load_w"] for item in points})
    lookup = {
        (item["operating_point"]["air_mass_flow_kg_s"], item["operating_point"]["chamber_heat_load_w"]): item
        for item in points
    }
    temperatures = [[lookup[(flow, load)]["maximum_bridge_temperature_c"] for load in loads] for flow in flows]

    fig, (ax_map, ax_oil) = plt.subplots(1, 2, figsize=(15, 6.8), facecolor="#eef2f4")
    image = ax_map.imshow(temperatures, cmap="inferno", vmin=min(map(min, temperatures)), vmax=max(map(max, temperatures)), aspect="auto")
    for row, flow in enumerate(flows):
        for column, load in enumerate(loads):
            item = lookup[(flow, load)]
            verdict = "PASS" if item["screen"]["numerical_screen_passed"] else "FAIL"
            ax_map.text(
                column,
                row,
                f"{item['maximum_bridge_temperature_c']:.1f} °C\n{item['maximum_pressure_drop_pa']/1000:.2f} kPa\n{verdict}",
                ha="center",
                va="center",
                color="black" if item["maximum_bridge_temperature_c"] > 275 else "white",
                fontsize=10,
                weight="bold",
            )
    ax_map.set_xticks(range(len(loads)), [f"{load/1000:.1f}" for load in loads])
    ax_map.set_yticks(range(len(flows)), [f"{flow:.2f}" for flow in flows])
    ax_map.set_xlabel("Charge chambre [kW/tête]")
    ax_map.set_ylabel("Débit air disponible [kg/s/tête]")
    ax_map.set_title("Enveloppe hors-calage du candidat")
    fig.colorbar(image, ax=ax_map, label="T pont [°C]", fraction=0.047, pad=0.025)

    oil_cases = report["optimization"]["best_by_oil_under_air_constraints"]
    oils = sorted(float(value) for value in oil_cases)
    temperatures_oil = [oil_cases[str(oil)]["maximum_bridge_temperature_c"] for oil in oils]
    bars = ax_oil.bar([f"{oil/1000:.1f}" for oil in oils], temperatures_oil, color=["#b94e48", "#da8c34", "#3a9d68"])
    ax_oil.axhline(260.0, color="#202020", linestyle="--", linewidth=2, label="limite 260 °C")
    for bar, value in zip(bars, temperatures_oil):
        ax_oil.text(bar.get_x() + bar.get_width()/2, value + 2, f"{value:.1f} °C", ha="center", weight="bold")
    ax_oil.set_ylim(0, max(temperatures_oil) + 55)
    ax_oil.set_xlabel("Extraction locale par l'huile [kW]")
    ax_oil.set_ylabel("T pont minimale sous contraintes air [°C]", labelpad=8)
    ax_oil.set_title("Dépendance au refroidissement d'huile non qualifié")
    ax_oil.legend()
    ax_oil.text(
        0.5,
        0.05,
        "0 et 0,6 kW : aucune solution nominale\n1,2 kW : 35 solutions nominales",
        transform=ax_oil.transAxes,
        ha="center",
        va="bottom",
        fontsize=11,
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.85},
    )

    fig.suptitle("Porsche 917 F39 — sensibilité thermique et aérodynamique", fontsize=20, weight="bold")
    fig.subplots_adjust(wspace=0.34, top=0.82, bottom=0.15)
    fig.text(0.5, 0.015, "Écran paramétrique scan-only · aucune CHT culasse ni validation physique", ha="center", color="#a42121", weight="bold")
    fig.savefig(output, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    args.output.mkdir(parents=True, exist_ok=True)
    evaluated = [evaluate(contract, parameters) for parameters in parameter_grid(contract)]
    feasible_geometry = [item for item in evaluated if item["geometry"]["fits_scan_envelope_screen"]]
    ranked = sorted(feasible_geometry, key=rank_key)
    selected = ranked[0]
    passing = [item for item in feasible_geometry if item["screen"]["numerical_screen_passed"]]
    passing_by_oil = {
        str(float(oil)): sum(
            item["screen"]["numerical_screen_passed"]
            for item in feasible_geometry
            if item["parameters"]["local_oil_heat_removal_w"] == float(oil)
        )
        for oil in contract["search_space"]["local_oil_heat_removal_w"]
    }
    best_by_oil_under_air_constraints = {}
    for oil in contract["search_space"]["local_oil_heat_removal_w"]:
        air_feasible = [
            item for item in feasible_geometry
            if item["parameters"]["local_oil_heat_removal_w"] == float(oil)
            and item["maximum_pressure_drop_pa"] <= float(contract["objectives"]["maximum_air_pressure_drop_pa"])
            and item["h_cross_method_relative_difference"] <= float(contract["objectives"]["maximum_cross_method_h_relative_difference"])
        ]
        if air_feasible:
            best = min(air_feasible, key=lambda item: item["maximum_bridge_temperature_c"])
            best_by_oil_under_air_constraints[str(float(oil))] = {
                "parameters": best["parameters"],
                "maximum_bridge_temperature_c": best["maximum_bridge_temperature_c"],
                "maximum_pressure_drop_pa": best["maximum_pressure_drop_pa"],
                "h_cross_method_relative_difference": best["h_cross_method_relative_difference"],
                "temperature_objective_passed": best["screen"]["temperature_both_methods_at_most_260c"],
            }
    sensitivity = []
    selected_parameters = dict(selected["parameters"])
    duct_id = selected_parameters.pop("duct")
    selected_parameters["duct"] = next(item for item in contract["search_space"]["duct_variants"] if item["id"] == duct_id)
    for mass_flow, heat in itertools.product(
        contract["off_design_matrix"]["air_mass_flow_kg_s_per_head"],
        contract["off_design_matrix"]["chamber_heat_load_w_per_head"],
    ):
        sensitivity.append(evaluate(contract, selected_parameters, float(mass_flow), float(heat)))
    compact_points = [
        {
            "temperature": item["maximum_bridge_temperature_c"],
            "dp": item["maximum_pressure_drop_pa"],
            "h_delta": item["h_cross_method_relative_difference"],
            "pass": item["screen"]["numerical_screen_passed"],
        }
        for item in feasible_geometry
    ]
    report = {
        "schema_version": "1.0",
        "id": "917-head-f39-cooling-optimization-report",
        "classification": contract["classification"],
        "inputs": {
            "contract": {"path": str(args.contract), "sha256": sha256(args.contract)},
            "f38_cooling_report": {"path": contract["inputs"]["f38_cooling_report"], "sha256": sha256(Path(contract["inputs"]["f38_cooling_report"]))},
            "f37_surface_report": {"path": contract["inputs"]["f37_scan_conforming_surface_report"], "sha256": sha256(Path(contract["inputs"]["f37_scan_conforming_surface_report"]))},
        },
        "objectives": contract["objectives"],
        "methods": {
            "method_a": contract["method_a_openfoam_anchored"],
            "method_b": contract["method_b_correlation"],
            "independent_in_primary_equations": True,
            "shared_inputs": ["geometry_parameters", "air_properties", "mass_flow", "heat_load"],
            "physical_validation": False,
        },
        "optimization": {
            "combinations_evaluated": len(evaluated),
            "geometry_feasible_combinations": len(feasible_geometry),
            "numerical_screen_passing_combinations": len(passing),
            "method_b_reynolds_range": [
                min(item["method_b"]["reynolds"] for item in feasible_geometry),
                max(item["method_b"]["reynolds"] for item in feasible_geometry),
            ],
            "gnielinski_all_geometry_feasible_cases_above_re_3000": all(
                item["method_b"]["reynolds"] > 3000.0 for item in feasible_geometry
            ),
            "passing_combinations_by_local_oil_heat_w": passing_by_oil,
            "best_by_oil_under_air_constraints": best_by_oil_under_air_constraints,
            "selected_candidate": selected,
            "top_five": ranked[:5],
            "compact_points": compact_points,
            "selection_rule": "if_any_pass_then_minimize_unqualified_oil_heat_then_temperature_pressure_h_delta_else_minimize_normalized_constraint_violation",
        },
        "off_design_sensitivity": sensitivity,
        "decision": {
            "numerical_candidate_found": bool(passing),
            "selected_for_next_full_head_CHT": bool(passing),
            "accepted_F39_BRep_and_wetted_area_available": False,
            "full_head_CHT_complete": False,
            "oil_gallery_geometry_and_heat_transfer_validated": False,
            "hot_material_coupon_card_qualified": False,
            "fan_map_and_duct_leakage_measured": False,
            "physical_correlation_complete": False,
            "metal_print_authorized": False,
            "engine_start_authorized": False,
        },
    }
    report_path = args.output / "f39-cooling-optimization-report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    csv_path = args.output / "f39-cooling-candidates.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["fin_levels", "thickness_mm", "gap_mm", "root_radius_mm", "span_mm", "duct", "oil_w", "h_a", "h_b", "h_delta", "dp_max_pa", "dp_delta", "t_max_c", "pass"])
        for item in ranked:
            p = item["parameters"]
            writer.writerow([p["fin_levels"], p["fin_thickness_mm"], p["clear_gap_mm"], p["root_radius_mm"], p["mean_span_mm"], p["duct"], p["local_oil_heat_removal_w"], item["method_a"]["effective_h_w_m2k"], item["method_b"]["effective_h_w_m2k"], item["h_cross_method_relative_difference"], item["maximum_pressure_drop_pa"], item["pressure_drop_cross_method_relative_difference"], item["maximum_bridge_temperature_c"], item["screen"]["numerical_screen_passed"]])
    image_path = args.output / "917-head-f39-cooling-optimization.png"
    render(report, image_path)
    sensitivity_image_path = args.output / "917-head-f39-cooling-envelope.png"
    render_sensitivity(report, sensitivity_image_path)
    print(json.dumps({"report": str(report_path), "csv": str(csv_path), "images": [str(image_path), str(sensitivity_image_path)], "passing": len(passing), "evaluated": len(evaluated)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
