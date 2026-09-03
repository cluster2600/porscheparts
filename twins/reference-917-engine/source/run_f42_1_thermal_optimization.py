#!/usr/bin/env python3
"""Prépare et consolide l'optimisation thermique F42.1.

Les points de sensibilité thermique proviennent de CalculiX sur le maillage
voxel F41 exact déjà publié. La seconde méthode est un réseau conservatif
chambre-pont-ailettes alimenté par Gnielinski/Darcy. Ce n'est pas une CHT.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def parse_dat(path: Path) -> dict:
    values: list[float] = []
    active = False
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if "temperatures for set NALL" in line:
            active = True
            values = []
            continue
        if not active or not line:
            continue
        fields = line.split()
        if len(fields) == 2 and fields[0].isdigit():
            values.append(float(fields[1]))
        elif values:
            active = False
    if not values:
        raise ValueError(f"aucune température NALL dans {path}")
    return {
        "temperature_samples": len(values),
        "minimum_temperature_c": min(values),
        "median_temperature_c": percentile(values, 0.5),
        "p95_temperature_c": percentile(values, 0.95),
        "maximum_temperature_c": max(values),
    }


def case_id(h: float, conductivity_scale: float) -> str:
    h_tag = f"{h:07.2f}".replace(".", "p")
    k_tag = f"{conductivity_scale:.2f}".replace(".", "p")
    return f"h{h_tag}-k{k_tag}"


def prepare_cases(contract: dict, base_input: Path, run_root: Path) -> list[dict]:
    expected = contract["inheritance"]["base_input_sha256"]
    if sha256(base_input) != expected:
        raise ValueError("le deck CalculiX de base ne correspond pas au SHA F42 publié")
    baseline_h = float(contract["inheritance"]["base_external_h_w_m2k"])
    baseline_k = float(contract["inheritance"]["base_conductivity_scale"])
    cases = [(float(h), baseline_k) for h in contract["calculix_sweep"]["external_h_w_m2k"]]
    cases += [(baseline_h, float(k)) for k in contract["calculix_sweep"]["conductivity_scale_at_base_h"]]
    source = base_input.read_text(encoding="utf-8")
    film_token = f",35,{baseline_h / 1.0e6:.8f}"
    expected_faces = int(contract["calculix_sweep"]["external_film_face_count"])
    if source.count(film_token) != expected_faces:
        raise ValueError("nombre de faces FILM externes inattendu")
    prepared = []
    for h, k_scale in cases:
        cid = case_id(h, k_scale)
        directory = run_root / cid
        directory.mkdir(parents=True, exist_ok=True)
        text = source.replace(film_token, f",35,{h / 1.0e6:.8f}")
        for value, temperature in ((0.15, 20), (0.135, 200), (0.12, 300)):
            token = f"{value},{temperature}."
            replacement = f"{value * k_scale:.9g},{temperature}."
            if text.count(token) != 1:
                raise ValueError(f"ligne conductivité absente ou dupliquée: {token}")
            text = text.replace(token, replacement)
        input_path = directory / "head-f42-1-thermal.inp"
        input_path.write_text(text, encoding="utf-8")
        manifest = {
            "case_id": cid,
            "classification": "exact_F41_voxel_sequential_conduction_sensitivity_not_CHT",
            "external_h_w_m2k": h,
            "conductivity_scale": k_scale,
            "external_film_face_count": expected_faces,
            "input_sha256": sha256(input_path),
            "base_input_sha256": expected,
            "exact_F41_solid_stl_sha256": contract["inheritance"]["exact_F41_solid_stl_sha256"],
            "solver_completed": False,
            "release_claim": False,
        }
        (directory / "case.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        prepared.append({**manifest, "directory": str(directory)})
    (run_root / "prepared-cases.json").write_text(json.dumps(prepared, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return prepared


def analytical_case(f42: dict, mass_flow: float, capture: float) -> dict:
    bc = f42["boundary_conditions"]
    model = f42["method_b_analytical"]
    levels = [float(v) for v in model["fin_levels_mm_if_scan_unit_is_mm"]]
    thickness = float(model["fin_thickness_mm_if_scan_unit_is_mm"])
    gap = sum(b - a - thickness for a, b in zip(levels, levels[1:])) / (len(levels) - 1) * 1e-3
    length = float(model["mean_flow_length_mm_if_scan_unit_is_mm"]) * 1e-3
    span = float(model["mean_fin_profile_area_mm2_if_scan_unit_is_mm"]) / float(model["mean_flow_length_mm_if_scan_unit_is_mm"]) * 1e-3
    passages = 26
    dh = 2 * gap * span / (gap + span)
    open_area = passages * gap * span
    rho = float(bc["air_density_kg_m3"])
    mu = float(bc["air_dynamic_viscosity_pa_s"])
    velocity = mass_flow * capture / (rho * open_area)
    speed_of_sound = math.sqrt(1.4 * 287.05 * float(bc["air_inlet_temperature_k"]))
    mach = velocity / speed_of_sound
    reynolds = rho * velocity * dh / mu
    friction = (0.79 * math.log(reynolds) - 1.64) ** -2
    pr = float(bc["air_prandtl"])
    nusselt = (friction / 8) * (reynolds - 1000) * pr / (1 + 12.7 * math.sqrt(friction / 8) * (pr ** (2 / 3) - 1))
    h = nusselt * float(bc["air_thermal_conductivity_w_mk"]) / dh
    dp = friction * length / dh * 0.5 * rho * velocity**2
    return {
        "mass_flow_kg_s_per_head": mass_flow,
        "capture_fraction": capture,
        "velocity_m_s": velocity,
        "mach_at_inlet_temperature": mach,
        "reynolds": reynolds,
        "effective_h_w_m2k": h,
        "straight_channel_pressure_drop_pa": dp,
        "reynolds_correlation_in_range": reynolds >= 3000,
        "incompressible_screen_below_mach_0p3": mach < 0.3,
        "correlation_use_accepted": reynolds >= 3000 and mach < 0.3,
    }


def conductivity(f42: dict, temperature_c: float, scale: float) -> float:
    points = f42["sequential_solid_conduction"]["temperature_dependent_conductivity_w_mk"]
    if temperature_c <= points[0][0]:
        return float(points[0][1]) * scale
    if temperature_c >= points[-1][0]:
        return float(points[-1][1]) * scale
    for (t0, k0), (t1, k1) in zip(points, points[1:]):
        if t0 <= temperature_c <= t1:
            return (float(k0) + (temperature_c - t0) / (t1 - t0) * (float(k1) - float(k0))) * scale
    raise AssertionError("intervalle thermique absent")


def bridge_network(f42: dict, h: float, area_multiplier: float, k_scale: float) -> dict:
    bc = f42["boundary_conditions"]
    heat = float(bc["nominal_head_heat_load_w"])
    area = float(f42["geometry"]["surface_area_mm2_if_scan_unit_is_mm"]) * 1e-6 * area_multiplier
    root_c = float(bc["air_inlet_temperature_k"]) - 273.15 + heat / (h * area)
    required_integral = heat * 0.008 / 0.0012
    low, high = root_c, root_c + 1000
    for _ in range(100):
        middle = (low + high) / 2
        steps = 500
        width = (middle - root_c) / steps
        integral = sum((0.5 if i in (0, steps) else 1) * conductivity(f42, root_c + i * width, k_scale) for i in range(steps + 1)) * width
        if integral < required_integral:
            low = middle
        else:
            high = middle
    return {
        "classification": "independent_two_resistance_lower_bound_not_3D_CHT",
        "effective_h_w_m2k": h,
        "wetted_area_multiplier": area_multiplier,
        "conductivity_scale": k_scale,
        "fin_root_temperature_c": root_c,
        "bridge_temperature_c": (low + high) / 2,
    }


def power_fit(points: list[tuple[float, float]]) -> dict:
    best = None
    for i in range(10, 401):
        exponent = i / 200
        xs = [h ** (-exponent) for h, _ in points]
        ys = [t for _, t in points]
        xm = sum(xs) / len(xs)
        ym = sum(ys) / len(ys)
        denom = sum((x - xm) ** 2 for x in xs)
        slope = sum((x - xm) * (y - ym) for x, y in zip(xs, ys)) / denom
        intercept = ym - slope * xm
        residuals = [y - (intercept + slope * x) for x, y in zip(xs, ys)]
        rmse = math.sqrt(sum(r * r for r in residuals) / len(residuals))
        candidate = (rmse, exponent, intercept, slope)
        if slope > 0 and (best is None or candidate < best):
            best = candidate
    if best is None:
        raise ValueError("ajustement monotone impossible")
    rmse, exponent, intercept, slope = best
    return {"model": "T=a+b*h^-n", "a": intercept, "b": slope, "n": exponent, "rmse_c": rmse}


def predict(fit: dict, h: float) -> float:
    return fit["a"] + fit["b"] * h ** (-fit["n"])


def solve_required_h(function, target: float) -> float | None:
    low, high = 1.0, 1.0e7
    if function(high) > target:
        return None
    for _ in range(100):
        middle = math.sqrt(low * high)
        if function(middle) > target:
            low = middle
        else:
            high = middle
    return high


def airflow_for_h(f42: dict, required_h: float | None) -> dict | None:
    if required_h is None:
        return None
    low, high = 0.01, 40.0
    if analytical_case(f42, high, 1.0)["effective_h_w_m2k"] < required_h:
        return None
    for _ in range(100):
        middle = (low + high) / 2
        if analytical_case(f42, middle, 1.0)["effective_h_w_m2k"] < required_h:
            low = middle
        else:
            high = middle
    return analytical_case(f42, high, 1.0)


def load_completed_cases(run_root: Path, contract: dict, baseline_report: Path) -> list[dict]:
    baseline = json.loads(baseline_report.read_text(encoding="utf-8"))
    items = [{
        "case_id": "F42-published-baseline",
        "external_h_w_m2k": float(contract["inheritance"]["base_external_h_w_m2k"]),
        "conductivity_scale": 1.0,
        "results": baseline["results"],
        "solver_completed": baseline["status"] == "completed_screening",
        "input_sha256": baseline["input_sha256"],
        "dat_sha256": None,
        "source": "published_F42_actual_CalculiX",
    }]
    for manifest_path in sorted(run_root.glob("*/case.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        dat = manifest_path.parent / "head-f42-1-thermal.dat"
        log = manifest_path.parent / "log.ccx"
        if not dat.is_file() or not log.is_file() or "Job finished" not in log.read_text(encoding="utf-8", errors="replace"):
            continue
        items.append({
            **manifest,
            "solver_completed": True,
            "results": parse_dat(dat),
            "dat_sha256": sha256(dat),
            "log_sha256": sha256(log),
            "source": "F42_1_actual_CalculiX",
        })
    return items


def render(report: dict, output: Path) -> list[Path]:
    import matplotlib.pyplot as plt

    actual = sorted((c for c in report["method_a_calculix"]["actual_cases"] if c["conductivity_scale"] == 1), key=lambda c: c["external_h_w_m2k"])
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    hs = [c["external_h_w_m2k"] for c in actual]
    axes[0].plot(hs, [c["results"]["maximum_temperature_c"] for c in actual], "o-", label="Tmax CalculiX réel")
    axes[0].plot(hs, [c["results"]["p95_temperature_c"] for c in actual], "s-", label="p95 CalculiX réel")
    axes[0].axhline(260, color="crimson", ls="--", label="objectif 260 °C")
    axes[0].set_xscale("log"); axes[0].grid(True, alpha=.3); axes[0].set_xlabel("h externe (W/m²K)"); axes[0].set_ylabel("Température (°C)"); axes[0].legend()
    analytic = report["method_b_analytical"]["sweep"]
    for capture in sorted({c["capture_fraction"] for c in analytic}):
        subset = [c for c in analytic if c["capture_fraction"] == capture]
        axes[1].plot([c["mass_flow_kg_s_per_head"] for c in subset], [c["effective_h_w_m2k"] for c in subset], marker="o", label=f"capture {capture:.0%}")
    axes[1].axhline(report["requirements"]["network_required_h_w_m2k"], color="crimson", ls="--", label="h requis réseau")
    axes[1].grid(True, alpha=.3); axes[1].set_xlabel("Débit par tête (kg/s)"); axes[1].set_ylabel("h Gnielinski (W/m²K)"); axes[1].legend()
    fig.suptitle("F42.1 — sensibilité réelle CalculiX et corrélation indépendante (pas CHT)")
    fig.tight_layout()
    sensitivity = output / "917-head-f42-1-thermal-sensitivity.png"
    fig.savefig(sensitivity, dpi=180); plt.close(fig)

    pareto = report["options"]
    fig, ax = plt.subplots(figsize=(9, 6))
    for item in pareto:
        ax.scatter(item["pressure_drop_lower_bound_pa"] / 1000, item["network_bridge_temperature_c"], s=85, marker="D" if item["pareto_nondominated"] else "o")
        ax.annotate(item["id"], (item["pressure_drop_lower_bound_pa"] / 1000, item["network_bridge_temperature_c"]), xytext=(5, 5), textcoords="offset points", fontsize=8)
    ax.axhline(260, color="crimson", ls="--"); ax.axvline(6.7, color="crimson", ls=":")
    ax.set_xlabel("Δp canal droite, borne basse (kPa)"); ax.set_ylabel("T pont réseau conservatif (°C)"); ax.grid(True, alpha=.3)
    ax.set_title("F42.1 — options dans l'enveloppe (CAO/CHT non validées)")
    fig.tight_layout()
    pareto_path = output / "917-head-f42-1-pareto.png"
    fig.savefig(pareto_path, dpi=180); plt.close(fig)
    return [sensitivity, pareto_path]


def summarize(contract_path: Path, f42_path: Path, run_root: Path, baseline_report: Path, output: Path) -> dict:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    f42 = json.loads(f42_path.read_text(encoding="utf-8"))
    inherited_f42_report_path = Path(contract["inheritance"]["f42_report"])
    inherited_f42_report = json.loads(inherited_f42_report_path.read_text(encoding="utf-8"))
    actual = load_completed_cases(run_root, contract, baseline_report)
    expected_actual = 1 + len(contract["calculix_sweep"]["external_h_w_m2k"]) + len(contract["calculix_sweep"]["conductivity_scale_at_base_h"])
    h_cases = sorted((c for c in actual if c["conductivity_scale"] == 1), key=lambda c: c["external_h_w_m2k"])
    if len(actual) != expected_actual:
        raise ValueError(f"{len(actual)}/{expected_actual} cas CalculiX terminés")
    fit_max = power_fit([(c["external_h_w_m2k"], c["results"]["maximum_temperature_c"]) for c in h_cases])
    fit_p95 = power_fit([(c["external_h_w_m2k"], c["results"]["p95_temperature_c"]) for c in h_cases])
    base_h = float(contract["inheritance"]["base_external_h_w_m2k"])
    k_cases = sorted((c for c in actual if c["external_h_w_m2k"] == base_h), key=lambda c: c["conductivity_scale"])
    def k_sensitivity(metric: str) -> float:
        xs = [1 / c["conductivity_scale"] - 1 for c in k_cases]
        ys = [c["results"][metric] - predict(fit_max if metric == "maximum_temperature_c" else fit_p95, base_h) for c in k_cases]
        return sum(x * y for x, y in zip(xs, ys)) / sum(x * x for x in xs)
    beta_max = k_sensitivity("maximum_temperature_c")
    beta_p95 = k_sensitivity("p95_temperature_c")
    sweep = [analytical_case(f42, float(flow), float(capture)) for capture in contract["analytical_sweep"]["capture_fraction"] for flow in contract["analytical_sweep"]["mass_flow_kg_s_per_head"]]
    for item in sweep:
        item["network_bridge_temperature_c"] = bridge_network(f42, item["effective_h_w_m2k"], 1.0, 1.0)["bridge_temperature_c"]
        item["calculix_surrogate_maximum_temperature_c"] = predict(fit_max, item["effective_h_w_m2k"])
        item["calculix_surrogate_p95_temperature_c"] = predict(fit_p95, item["effective_h_w_m2k"])
        item["temperature_values_are_models_not_executed_airflow_cases"] = True
    area = float(f42["geometry"]["surface_area_mm2_if_scan_unit_is_mm"]) * 1e-6
    required_network_h = solve_required_h(lambda h: bridge_network(f42, h, 1, 1)["bridge_temperature_c"], 260)
    required_fea_h = solve_required_h(lambda h: predict(fit_max, h), 260)
    required_fea_p95_h = solve_required_h(lambda h: predict(fit_p95, h), 260)
    required_area_multiplier = required_network_h / base_h if required_network_h else None
    required_air = airflow_for_h(f42, required_network_h)
    required_fea_air = airflow_for_h(f42, required_fea_h)
    options = []
    for option in contract["options"]:
        air = analytical_case(f42, float(option["mass_flow_kg_s_per_head"]), float(option["capture_fraction"]))
        h_equiv = air["effective_h_w_m2k"] * float(option["internal_area_multiplier"])
        network = bridge_network(f42, air["effective_h_w_m2k"], float(option["internal_area_multiplier"]), float(option["conductivity_scale"]))
        pred_max = predict(fit_max, h_equiv) + beta_max * (1 / float(option["conductivity_scale"]) - 1)
        pred_p95 = predict(fit_p95, h_equiv) + beta_p95 * (1 / float(option["conductivity_scale"]) - 1)
        options.append({
            **option,
            "gnielinski_h_w_m2k": air["effective_h_w_m2k"],
            "equivalent_h_area_w_m2k": h_equiv,
            "pressure_drop_lower_bound_pa": air["straight_channel_pressure_drop_pa"],
            "pressure_drop_excludes_baffle_and_added_fin_losses": True,
            "network_bridge_temperature_c": network["bridge_temperature_c"],
            "calculix_surrogate_maximum_temperature_c": pred_max,
            "calculix_surrogate_p95_temperature_c": pred_p95,
            "surrogate_is_not_executed_modified_geometry": True,
            "target_260_and_dp_screen": network["bridge_temperature_c"] <= 260 and pred_max <= 260 and air["straight_channel_pressure_drop_pa"] <= 6700,
        })
    for item in options:
        item["pareto_nondominated"] = not any(
            other is not item and other["network_bridge_temperature_c"] <= item["network_bridge_temperature_c"] and other["pressure_drop_lower_bound_pa"] <= item["pressure_drop_lower_bound_pa"] and (
                other["network_bridge_temperature_c"] < item["network_bridge_temperature_c"] or other["pressure_drop_lower_bound_pa"] < item["pressure_drop_lower_bound_pa"]
            ) for other in options
        )
    report = {
        "schema_version": "1.0.0",
        "id": "917-head-f42-1-thermal-optimization-results",
        "classification": contract["classification"],
        "inputs": {
            "contract": {"path": str(contract_path), "sha256": sha256(contract_path)},
            "f42_contract": {"path": str(f42_path), "sha256": sha256(f42_path)},
            "f42_report": {"path": str(inherited_f42_report_path), "sha256": sha256(inherited_f42_report_path)},
            "baseline_report": {"path": str(baseline_report), "sha256": sha256(baseline_report)},
            "geometry_sha256": contract["inheritance"]["exact_F41_solid_stl_sha256"],
            "external_envelope_modified": False,
        },
        "method_a_calculix": {
            "classification": "actual_exact_F41_voxel_sequential_conduction_parametric_films_not_CHT",
            "actual_case_count": len(actual),
            "actual_cases": actual,
            "maximum_fit": fit_max,
            "p95_fit": fit_p95,
            "conductivity_sensitivity_max_c": beta_max,
            "conductivity_sensitivity_p95_c": beta_p95,
            "fit_predictions_are_validation": False,
        },
        "method_b_analytical": {
            "classification": "independent_Gnielinski_Darcy_plus_two_resistance_lower_bound",
            "sweep": sweep,
            "uses_total_scan_surface_as_optimistic_wetted_area_m2": area,
        },
        "inherited_cross_method_gate": {
            **inherited_f42_report["cross_method"],
            "classification": "F42_Gnielinski_vs_converged_F38_channel_proxy_not_exact_F41_whole_head",
            "recomputed_in_F42_1": False,
        },
        "requirements": {
            "network_required_h_w_m2k": required_network_h,
            "network_required_area_multiplier_at_baseline_h": required_area_multiplier,
            "network_required_wetted_area_m2_at_baseline_h": area * required_area_multiplier if required_area_multiplier else None,
            "network_required_airflow_at_capture_100": required_air,
            "calculix_fit_required_h_w_m2k": required_fea_h,
            "calculix_fit_required_airflow_at_capture_100": required_fea_air,
            "calculix_fit_p95_required_h_w_m2k": required_fea_p95_h,
            "calculix_fit_requirement_is_extrapolation": required_fea_h is None or required_fea_h > max(c["external_h_w_m2k"] for c in h_cases),
            "required_airflow_pressure_estimates_accepted": bool(required_air and required_fea_air and required_air["correlation_use_accepted"] and required_fea_air["correlation_use_accepted"]),
            "pressure_estimates_warning": "Les débits requis dépassent Mach 0,3; Darcy incompressible n'est alors qu'un indicateur d'impossibilité, pas une prédiction de conception.",
        },
        "options": options,
        "decision": {
            "any_option_passes_260c_and_6p7kpa": any(o["target_260_and_dp_screen"] for o in options),
            "external_envelope_modified": False,
            "exact_F41_whole_head_CHT_complete": False,
            "exact_F41_OpenFOAM_case_accepted": False,
            "material_card_qualified": False,
            "physical_validation_complete": False,
            "metal_print_authorized": False,
            "engine_start_authorized": False,
        },
        "release_gates": contract["release_gates"],
    }
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "f42-1-thermal-optimization-report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    csv_path = output / "f42-1-thermal-pareto.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["option", "h_W_m2K", "h_area_equiv_W_m2K", "dp_lower_bound_Pa", "network_Tbridge_C", "CalculiX_surrogate_Tmax_C", "CalculiX_surrogate_p95_C", "Pareto", "screen_pass"])
        for o in options:
            writer.writerow([o["id"], o["gnielinski_h_w_m2k"], o["equivalent_h_area_w_m2k"], o["pressure_drop_lower_bound_pa"], o["network_bridge_temperature_c"], o["calculix_surrogate_maximum_temperature_c"], o["calculix_surrogate_p95_temperature_c"], o["pareto_nondominated"], o["target_260_and_dp_screen"]])
    images = render(report, output)
    manifest = {
        "report": {"path": str(report_path), "sha256": sha256(report_path)},
        "pareto_csv": {"path": str(csv_path), "sha256": sha256(csv_path)},
        "images": [{"path": str(path), "sha256": sha256(path)} for path in images],
        "release_claim": False,
    }
    (output / "publication-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, default=Path("twins/reference-917-engine/f42-1-thermal-optimization.json"))
    parser.add_argument("--f42-contract", type=Path, default=Path("twins/reference-917-engine/f42-cooling-cht-contract.json"))
    parser.add_argument("--base-input", type=Path, default=Path("work/917-f42-cooling-cht/run/f42-calculix-p2p5-analytic-h/head-f36-thermal.inp"))
    parser.add_argument("--baseline-report", type=Path, default=Path("work/917-f42-cooling-cht/run/f42-calculix-p2p5-analytic-h/report.json"))
    parser.add_argument("--run-root", type=Path, default=Path("work/917-f42-1-thermal-optimization"))
    parser.add_argument("--output", type=Path, default=Path("twins/reference-917-engine/evidence/f42-1-thermal-optimization"))
    parser.add_argument("command", choices=("prepare", "summarize"))
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    if args.command == "prepare":
        prepared = prepare_cases(contract, args.base_input, args.run_root)
        print(json.dumps({"prepared": len(prepared), "run_root": str(args.run_root)}, sort_keys=True))
    else:
        report = summarize(args.contract, args.f42_contract, args.run_root, args.baseline_report, args.output)
        print(json.dumps({"actual_cases": report["method_a_calculix"]["actual_case_count"], "output": str(args.output)}, sort_keys=True))


if __name__ == "__main__":
    main()
