#!/usr/bin/env python3
"""Consolide les preuves F42 de refroidissement sans promouvoir un écran en CHT."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative_difference(a: float, b: float) -> float:
    return abs(a - b) / max(abs(b), 1.0e-12)


def data_rows(path: Path) -> list[list[str]]:
    if not path.is_file():
        return []
    return [
        line.replace("(", " ").replace(")", " ").split()
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def post_file(case: Path, function: str, filename: str) -> Path | None:
    matches = sorted((case / "postProcessing" / function).glob(f"*/{filename}"))
    return matches[-1] if matches else None


def parse_openfoam_case(case: Path, contract: dict) -> dict:
    metadata_path = case / "case-metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    log_path = case / "log.fluid"
    log_text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.is_file() else ""
    default_mesh_path = case / "log.checkMesh-default"
    strict_mesh_path = case / "log.checkMesh-strict"
    default_mesh = default_mesh_path.read_text(encoding="utf-8", errors="replace") if default_mesh_path.is_file() else ""
    strict_mesh = strict_mesh_path.read_text(encoding="utf-8", errors="replace") if strict_mesh_path.is_file() else ""
    required = {
        "mass": post_file(case, "outletMassFlow", "surfaceFieldValue.dat"),
        "temperature": post_file(case, "weightedOutletTemperature", "surfaceFieldValue.dat"),
        "pressure": post_file(case, "inletPressure", "surfaceFieldValue.dat"),
        "energy": post_file(case, "outletTotalEnergyTerms", "surfaceFieldValue.dat"),
        "heat": post_file(case, "headHeatFlux", "wallHeatFlux.dat"),
    }
    rows = {name: data_rows(path) if path is not None else [] for name, path in required.items()}
    diverged = bool(re.search(r"(^|\s)(nan|-nan)(\s|$)", log_text, re.IGNORECASE))
    solver_completed = "\nEnd\n" in f"\n{log_text}\n" and not diverged
    if not all(rows.values()) or not solver_completed:
        return {
            "case_id": case.name,
            "status": "failed_or_incomplete",
            "classification": metadata["classification"],
            "solver_completed": solver_completed,
            "numerical_divergence_detected": diverged,
            "standard_mesh_check_passed": "Mesh OK." in default_mesh,
            "strict_mesh_check_passed": "Mesh OK." in strict_mesh and "Failed " not in strict_mesh,
            "metadata_sha256": sha256(metadata_path),
            "solver_log_sha256": sha256(log_path) if log_path.is_file() else None,
            "release_claim": False,
        }

    mass = abs(float(rows["mass"][-1][1]))
    tout = float(rows["temperature"][-1][1])
    pin = float(rows["pressure"][-1][1])
    u2out = float(rows["energy"][-1][2])
    heat = abs(float(rows["heat"][-1][4]))
    mean_heat_flux = abs(float(rows["heat"][-1][5]))
    previous_heat = abs(float(rows["heat"][-2][4])) if len(rows["heat"]) > 1 else None
    wall_area = heat / mean_heat_flux
    bc = contract["boundary_conditions"]
    tin = float(bc["air_inlet_temperature_k"])
    twall = float(bc["isothermal_wall_temperature_k"])
    delta_in = twall - tin
    delta_out = twall - tout
    lmtd = delta_in if tout <= tin or delta_out <= 0 else (delta_in - delta_out) / math.log(delta_in / delta_out)
    effective_h = heat / (wall_area * lmtd)
    rho_in = pin / (287.05 * tin)
    area_in = float(metadata["inlet_cross_section_m2"])
    vin = mass / (rho_in * area_in)
    energy_gain = mass * (float(bc["air_specific_heat_j_kgk"]) * (tout - tin) + 0.5 * (u2out - vin * vin))
    energy_error = relative_difference(energy_gain, heat)
    mass_error = relative_difference(mass, float(bc["air_mass_flow_kg_s_per_head"]))
    heat_change = relative_difference(heat, previous_heat) if previous_heat is not None else None
    cell_match = re.search(r"^\s*cells:\s+(\d+)", default_mesh, re.MULTILINE)
    strict_failed = re.search(r"Failed\s+(\d+)\s+mesh checks", strict_mesh)
    checks = {
        "solver_completed_without_nan": solver_completed,
        "standard_mesh_check_passed": "Mesh OK." in default_mesh,
        "strict_mesh_check_passed": "Mesh OK." in strict_mesh and strict_failed is None,
        "mass_balance_within_0p5_percent": mass_error <= float(contract["method_a_openfoam"]["required_mass_balance_relative"]),
        "energy_balance_within_5_percent": energy_error <= float(contract["method_a_openfoam"]["required_energy_balance_relative"]),
        "last_heat_change_within_2_percent": heat_change is not None and heat_change <= float(contract["method_a_openfoam"]["required_last_heat_change_relative"]),
        "pressure_drop_below_6p7kpa": pin - float(bc["outlet_static_pressure_pa"]) <= float(bc["maximum_pressure_drop_pa"]),
    }
    return {
        "case_id": case.name,
        "status": "passed_numerical_screen" if all(value for key, value in checks.items() if key != "strict_mesh_check_passed") else "failed_numerical_screen",
        "classification": metadata["classification"],
        "cells": int(cell_match.group(1)) if cell_match else None,
        "strict_failed_mesh_checks": int(strict_failed.group(1)) if strict_failed else 0,
        "results": {
            "mass_flow_kg_s": mass,
            "outlet_temperature_k": tout,
            "wall_heat_rejection_w": heat,
            "wall_area_resolved_m2": wall_area,
            "effective_h_w_m2k": effective_h,
            "pressure_drop_pa": pin - float(bc["outlet_static_pressure_pa"]),
            "relative_mass_balance_error": mass_error,
            "relative_energy_balance_error": energy_error,
            "last_heat_relative_change": heat_change,
            "air_total_energy_gain_w": energy_gain,
        },
        "checks": checks,
        "metadata_sha256": sha256(metadata_path),
        "solver_log_sha256": sha256(log_path),
        "source_stl_sha256": metadata["source_stl_sha256"],
        "engine_interfaces_capped": metadata.get("engine_interfaces_capped", False),
        "release_claim": False,
    }


def analytical_cases(contract: dict) -> list[dict]:
    bc = contract["boundary_conditions"]
    model = contract["method_b_analytical"]
    levels = [float(value) for value in model["fin_levels_mm_if_scan_unit_is_mm"]]
    thickness_mm = float(model["fin_thickness_mm_if_scan_unit_is_mm"])
    gaps_mm = [b - a - thickness_mm for a, b in zip(levels, levels[1:])]
    gap = (sum(gaps_mm) / len(gaps_mm)) * 1.0e-3
    length = float(model["mean_flow_length_mm_if_scan_unit_is_mm"]) * 1.0e-3
    span = float(model["mean_fin_profile_area_mm2_if_scan_unit_is_mm"]) / float(model["mean_flow_length_mm_if_scan_unit_is_mm"]) * 1.0e-3
    dh = 2.0 * gap * span / (gap + span)
    rho = float(bc["air_density_kg_m3"])
    mu = float(bc["air_dynamic_viscosity_pa_s"])
    conductivity = float(bc["air_thermal_conductivity_w_mk"])
    pr = float(bc["air_prandtl"])
    results = []
    for passages in model["passage_count_bounds"]:
        for capture in model["capture_fraction_cases"]:
            open_area = float(passages) * gap * span
            velocity = float(bc["air_mass_flow_kg_s_per_head"]) * float(capture) / (rho * open_area)
            reynolds = rho * velocity * dh / mu
            friction = (0.79 * math.log(reynolds) - 1.64) ** -2
            nusselt = (friction / 8.0) * (reynolds - 1000.0) * pr / (
                1.0 + 12.7 * math.sqrt(friction / 8.0) * (pr ** (2.0 / 3.0) - 1.0)
            )
            h = nusselt * conductivity / dh
            dp = friction * (length / dh) * 0.5 * rho * velocity**2
            results.append({
                "case_id": f"p{passages}-capture{float(capture):.2f}",
                "passage_count_equivalent": int(passages),
                "capture_fraction": float(capture),
                "mean_clear_gap_mm": gap * 1000.0,
                "effective_span_mm": span * 1000.0,
                "open_area_m2": open_area,
                "hydraulic_diameter_m": dh,
                "velocity_m_s": velocity,
                "reynolds": reynolds,
                "darcy_friction_factor": friction,
                "nusselt": nusselt,
                "effective_h_w_m2k": h,
                "straight_pressure_drop_pa": dp,
                "pressure_drop_below_6p7kpa": dp <= float(bc["maximum_pressure_drop_pa"]),
                "correlation_in_reynolds_range": reynolds >= 3000.0,
            })
    return results


def conductivity_at_c(contract: dict, temperature_c: float) -> float:
    points = contract["sequential_solid_conduction"]["temperature_dependent_conductivity_w_mk"]
    if temperature_c <= points[0][0]:
        return float(points[0][1])
    if temperature_c >= points[-1][0]:
        return float(points[-1][1])
    for (t0, k0), (t1, k1) in zip(points, points[1:]):
        if t0 <= temperature_c <= t1:
            fraction = (temperature_c - t0) / (t1 - t0)
            return float(k0) + fraction * (float(k1) - float(k0))
    raise AssertionError("intervalle thermique absent")


def bridge_temperature(contract: dict, h: float, area_m2: float) -> dict:
    bc = contract["boundary_conditions"]
    heat = float(bc["nominal_head_heat_load_w"])
    root_c = float(bc["air_inlet_temperature_k"]) - 273.15 + heat / (h * area_m2)
    length_m = 0.008
    bridge_area_m2 = 0.0012
    required_integral = heat * length_m / bridge_area_m2
    low, high = root_c, root_c + 800.0
    for _ in range(100):
        middle = 0.5 * (low + high)
        steps = 600
        width = (middle - root_c) / steps
        integral = sum(
            (0.5 if i in (0, steps) else 1.0) * conductivity_at_c(contract, root_c + i * width)
            for i in range(steps + 1)
        ) * width
        if integral < required_integral:
            low = middle
        else:
            high = middle
    bridge_c = 0.5 * (low + high)
    return {
        "classification": "two_resistance_lower_bound_using_resolved_wetted_area_and_F38_bridge_proxy_not_3D_CHT",
        "heat_load_w": heat,
        "wetted_area_m2": area_m2,
        "external_h_w_m2k": h,
        "fin_root_temperature_c": root_c,
        "bridge_temperature_c": bridge_c,
        "maximum_below_260_c": bridge_c <= float(bc["maximum_bridge_temperature_c"]),
        "within_qualified_interpolation_range_to_300c": bridge_c <= 300.0,
        "above_300c_conductivity_treatment": "120_W_mK_constant_unqualified_extrapolation" if bridge_c > 300.0 else None,
        "bridge_length_mm_proxy": 8.0,
        "bridge_area_mm2_proxy": 1200.0,
    }


def load_calculix_report(path: Path | None) -> dict | None:
    if path is None or not path.is_file():
        return None
    report = json.loads(path.read_text(encoding="utf-8"))
    return {"path": str(path), "sha256": sha256(path), **report}


def load_inherited_openfoam_reference(contract: dict) -> dict:
    source = contract["inherited_openfoam_reference"]
    path = Path(source["path"])
    payload = json.loads(path.read_text(encoding="utf-8"))
    case = next(item for item in payload["openfoam"]["cases"] if item["case_id"] == source["case_id"])
    return {
        "source_path": str(path),
        "source_sha256": sha256(path),
        "case_id": case["case_id"],
        "classification": "inherited_converged_F38_canonical_channel_proxy_not_F41_whole_head",
        "geometry": source["geometry"],
        "cell_count": case["cell_count"],
        "effective_h_w_m2k": case["effective_h_w_m2k"],
        "pressure_drop_pa": case["pressure_drop_pa"],
        "relative_energy_balance_error": case["energy_balance_relative"],
        "relative_mass_balance_error": case["mass_balance_relative"],
        "two_grid_h_change_relative": payload["openfoam"]["fine_grid_h_change_relative"],
        "accepted_as_proxy": (
            payload["openfoam"]["two_grid_h_agreement_below_5_percent"]
            and payload["openfoam"]["fine_energy_balance_below_5_percent"]
            and payload["openfoam"]["fine_mass_balance_below_1_percent"]
        ),
        "accepted_as_F41_whole_head": False,
    }


def render_calculix_field(case: Path, output: Path) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    nodes: dict[int, tuple[float, float, float]] = {}
    active = False
    for raw in (case / "head-f36-thermal.inp").read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if line.upper() == "*NODE":
            active = True
            continue
        if active and line.startswith("*"):
            break
        if active and line:
            fields = [field.strip() for field in line.split(",")]
            nodes[int(fields[0])] = tuple(float(value) for value in fields[1:4])
    temperatures: dict[int, float] = {}
    for raw in (case / "head-f36-thermal.dat").read_text(encoding="utf-8", errors="replace").splitlines():
        fields = raw.split()
        if len(fields) == 2:
            try:
                temperatures[int(fields[0])] = float(fields[1])
            except ValueError:
                continue
    all_tags = np.asarray(sorted(set(nodes).intersection(temperatures)), dtype=int)
    all_values = np.asarray([temperatures[int(tag)] for tag in all_tags])
    tags = all_tags
    if len(tags) > 45000:
        tags = tags[np.linspace(0, len(tags) - 1, 45000, dtype=int)]
    points = np.asarray([nodes[int(tag)] for tag in tags])
    values = np.asarray([temperatures[int(tag)] for tag in tags])
    figure = plt.figure(figsize=(14, 7), facecolor="#0b1118")
    figure.suptitle("F42 — champ thermique CalculiX sur le solide F41 exact", color="white", fontsize=18, fontweight="bold")
    for panel, (elev, azim, title) in enumerate(((20.0, -55.0, "Vue admission"), (12.0, 35.0, "Vue échappement")), start=1):
        axis = figure.add_subplot(1, 2, panel, projection="3d", facecolor="#101b24")
        scatter = axis.scatter(points[:, 0], points[:, 1], points[:, 2], c=values, cmap="inferno", s=2.0, linewidths=0)
        centre = points.mean(axis=0)
        radius = 0.55 * float(np.ptp(points, axis=0).max())
        axis.set_xlim(centre[0] - radius, centre[0] + radius)
        axis.set_ylim(centre[1] - radius, centre[1] + radius)
        axis.set_zlim(centre[2] - 0.45 * radius, centre[2] + 0.55 * radius)
        axis.set_box_aspect((1.0, 1.15, 0.75))
        axis.view_init(elev=elev, azim=azim)
        axis.set_axis_off()
        axis.set_title(title, color="white", fontsize=12)
    colourbar = figure.colorbar(scatter, ax=figure.axes, fraction=0.025, pad=0.02)
    colourbar.set_label("Température °C", color="white")
    colourbar.ax.tick_params(colors="white")
    figure.text(
        0.5,
        0.025,
        f"min {all_values.min():.1f} °C · médiane {np.median(all_values):.1f} °C · p95 {np.percentile(all_values, 95):.1f} °C · max {all_values.max():.1f} °C · conduction séquentielle, pas CHT",
        color="#d6dde3",
        ha="center",
    )
    figure.subplots_adjust(left=0.01, right=0.91, bottom=0.08, top=0.89, wspace=0.02)
    figure.savefig(output, dpi=180, facecolor=figure.get_facecolor())
    plt.close(figure)


def render(report: dict, output: Path) -> None:
    import matplotlib.pyplot as plt

    completed = [case for case in report["method_a_openfoam"]["cases"] if "results" in case]
    inherited = report["method_a_openfoam"]["inherited_converged_reference"]
    analytical = report["method_b_analytical"]["cases"]
    selected = report["method_b_analytical"]["selected_cross_check"]
    fig, axes = plt.subplots(1, 3, figsize=(16, 6), facecolor="#f2f5f7")
    labels = [case["case_id"] for case in completed] + ["F38 canal proxy", selected["case_id"]]
    h_values = [case["results"]["effective_h_w_m2k"] for case in completed] + [inherited["effective_h_w_m2k"], selected["effective_h_w_m2k"]]
    axes[0].bar(labels, h_values, color=["#2878b5"] * len(completed) + ["#586f7c", "#e59322"])
    axes[0].set_title("h issu des calculs exécutés")
    axes[0].set_ylabel("W/m²K")
    axes[0].tick_params(axis="x", rotation=18)
    dp_labels = [case["case_id"] for case in completed] + ["F38 canal proxy"] + [item["case_id"] for item in analytical]
    dp_values = [case["results"]["pressure_drop_pa"] for case in completed] + [inherited["pressure_drop_pa"]] + [item["straight_pressure_drop_pa"] for item in analytical]
    axes[1].bar(dp_labels, dp_values, color=["#2878b5"] * len(completed) + ["#586f7c"] + ["#e59322"] * len(analytical))
    axes[1].axhline(6700.0, color="#b22222", linestyle="--", label="porte 6,7 kPa")
    axes[1].set_title("Perte de charge")
    axes[1].set_ylabel("Pa")
    axes[1].tick_params(axis="x", rotation=45, labelsize=8)
    axes[1].legend()
    thermal = report["thermal_screens"]
    t_labels = list(thermal)
    t_values = [thermal[name]["bridge_temperature_c"] for name in t_labels]
    axes[2].bar(t_labels, t_values, color=["#2a9d6f" if value <= 260 else "#c84343" for value in t_values])
    axes[2].axhline(260.0, color="#111", linestyle="--", label="porte 260 °C")
    axes[2].axhline(300.0, color="#9b6c00", linestyle=":", label="limite carte CP1")
    axes[2].set_title("Réseau thermique conservatif")
    axes[2].set_ylabel("°C")
    axes[2].tick_params(axis="x", rotation=18)
    axes[2].legend()
    fig.suptitle("F42 — refroidissement F41 exact: résultats numériques, pas une CHT complète", fontweight="bold", fontsize=16)
    fig.text(0.5, 0.01, "Interfaces moteur ouvertes, échelle et carte matière non qualifiées — impression et démarrage interdits", ha="center", color="#a02020", fontweight="bold")
    fig.tight_layout(rect=(0, 0.05, 1, 0.93))
    fig.savefig(output, dpi=180)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--openfoam-case", type=Path, action="append", default=[])
    parser.add_argument("--calculix-report", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    cases = [parse_openfoam_case(path, contract) for path in args.openfoam_case]
    analytical = analytical_cases(contract)
    inherited_openfoam = load_inherited_openfoam_reference(contract)
    selected_cfg = contract["method_b_analytical"]["selected_cross_check"]
    selected = next(
        item for item in analytical
        if item["passage_count_equivalent"] == int(selected_cfg["passage_count"])
        and item["capture_fraction"] == float(selected_cfg["capture_fraction"])
    )
    completed = [case for case in cases if case.get("status") == "passed_numerical_screen"]
    exact_reference = completed[-1] if completed else None
    reference_h = exact_reference["results"]["effective_h_w_m2k"] if exact_reference else inherited_openfoam["effective_h_w_m2k"]
    reference_dp = exact_reference["results"]["pressure_drop_pa"] if exact_reference else inherited_openfoam["pressure_drop_pa"]
    reference_kind = "exact_F41_external_air" if exact_reference else "inherited_F38_channel_proxy"
    h_cross = relative_difference(reference_h, selected["effective_h_w_m2k"])
    dp_cross = relative_difference(reference_dp, selected["straight_pressure_drop_pa"])
    thermal_screens = {
        "Gnielinski_p26_c70": bridge_temperature(contract, selected["effective_h_w_m2k"], float(contract["geometry"]["surface_area_mm2_if_scan_unit_is_mm"]) * 1e-6)
    }
    if exact_reference:
        thermal_screens["OpenFOAM_F41_exact"] = bridge_temperature(
            contract,
            exact_reference["results"]["effective_h_w_m2k"],
            exact_reference["results"]["wall_area_resolved_m2"],
        )
    else:
        thermal_screens["OpenFOAM_F38_channel_proxy"] = bridge_temperature(
            contract,
            inherited_openfoam["effective_h_w_m2k"],
            float(contract["geometry"]["surface_area_mm2_if_scan_unit_is_mm"]) * 1e-6,
        )
    calculix = load_calculix_report(args.calculix_report)
    calculix_pass = bool(calculix and calculix.get("results", {}).get("maximum_temperature_c", math.inf) <= 260.0)
    report = {
        "schema_version": "1.0.0",
        "id": "917-head-f42-cooling-cht-cross-check",
        "classification": contract["classification"],
        "inputs": {
            "contract": {"path": str(args.contract), "sha256": sha256(args.contract)},
            "geometry": contract["geometry"],
        },
        "boundary_conditions": contract["boundary_conditions"],
        "method_a_openfoam": {
            "solver": contract["method_a_openfoam"]["solver"],
            "cases": cases,
            "accepted_completed_case_count": len(completed),
            "inherited_converged_reference": inherited_openfoam,
            "full_head_CHT": False,
        },
        "method_b_analytical": {
            "method": contract["method_b_analytical"]["method"],
            "cases": analytical,
            "selected_cross_check": selected,
        },
        "cross_method": {
            "h_relative_difference": h_cross,
            "pressure_drop_relative_difference": dp_cross,
            "reference_kind": reference_kind,
            "h_agreement_below_20_percent": h_cross <= float(contract["method_b_analytical"]["maximum_cross_method_h_relative_difference"]),
            "pressure_agreement_below_20_percent": dp_cross <= 0.20,
            "agreement_is_physical_validation": False,
        },
        "thermal_screens": thermal_screens,
        "sequential_solid_conduction": calculix,
        "decision": {
            "exact_F41_openfoam_numerical_case_accepted": bool(completed),
            "inherited_F38_channel_proxy_accepted": inherited_openfoam["accepted_as_proxy"],
            "cross_method_h_gate_passed": h_cross <= 0.20,
            "cross_method_pressure_gate_passed": dp_cross <= 0.20,
            "all_pressure_screens_below_6p7kpa": inherited_openfoam["pressure_drop_pa"] <= float(contract["boundary_conditions"]["maximum_pressure_drop_pa"]) and all(item["pressure_drop_below_6p7kpa"] for item in analytical),
            "all_thermal_screens_below_260c": bool(thermal_screens) and all(item["maximum_below_260_c"] for item in thermal_screens.values()) and (calculix_pass if calculix else False),
            "full_head_CHT_complete": False,
            "reason_full_CHT_false": "OpenFOAM impose une paroi isotherme; CalculiX, si présent, reçoit un h moyen séquentiel; les interfaces moteur ne sont pas obturées.",
            **contract["release_gates"],
        },
    }
    args.output.mkdir(parents=True, exist_ok=True)
    report_path = args.output / "f42-cooling-cht-cross-check.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    image_path = args.output / "917-head-f42-cooling-results.png"
    render(report, image_path)
    field_image = None
    if args.calculix_report is not None:
        calculix_case = args.calculix_report.parent
        if (calculix_case / "head-f36-thermal.inp").is_file() and (calculix_case / "head-f36-thermal.dat").is_file():
            field_image = args.output / "917-head-f42-calculix-temperature-field.png"
            render_calculix_field(calculix_case, field_image)
    print(json.dumps({"report": str(report_path), "image": str(image_path), "field_image": str(field_image) if field_image else None, "accepted_openfoam_cases": len(completed)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
