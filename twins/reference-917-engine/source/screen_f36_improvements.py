#!/usr/bin/env python3
"""Compare les ameliorations F36 sur des metriques et seuils communs.

Le programme consolide des sorties de calcul deja executees. Il ne transforme
pas une hypothese materiau ou un modele numerique en validation physique.
"""

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
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def labelled(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("format attendu: id=chemin")
    label, raw_path = value.split("=", 1)
    if not label or not raw_path:
        raise argparse.ArgumentTypeError("id et chemin sont requis")
    return label, Path(raw_path)


def spring_rate(candidate: dict, member: str) -> float:
    data = candidate[member]
    return 79_000.0 * data["wire_mm"] ** 4 / (
        8.0 * data["mean_diameter_mm"] ** 3 * data["active_coils"]
    )


def spring_shear(force_n: float, member: dict) -> float:
    wire = member["wire_mm"]
    diameter = member["mean_diameter_mm"]
    index = diameter / wire
    wahl = (4.0 * index - 1.0) / (4.0 * index - 4.0) + 0.615 / index
    return wahl * 8.0 * force_n * diameter / (math.pi * wire**3)


def valve_volume_mm3(head_diameter: float, stem_diameter: float) -> float:
    return math.pi * (head_diameter / 2.0) ** 2 * 2.5 + math.pi * (stem_diameter / 2.0) ** 2 * 96.0


def evaluate_spring(candidate: dict, valve_report: dict, objectives: dict) -> dict:
    lift = 12.0
    installed_tolerance = objectives["spring_installed_height_tolerance_mm"]
    k_outer = spring_rate(candidate, "outer")
    k_inner = spring_rate(candidate, "inner")
    k_total = k_outer + k_inner
    seat = candidate["seat_load_n"]
    open_load = seat + k_total * lift
    mid_load = seat + 0.5 * k_total * lift
    worst_open_load = open_load + k_total * installed_tolerance
    worst_mid_load = mid_load - k_total * installed_tolerance
    outer_force = worst_open_load * k_outer / k_total
    inner_force = worst_open_load * k_inner / k_total
    bind = {
        name: candidate["installed_height_mm"]
        - lift
        - (candidate[name]["active_coils"] + 1.5) * candidate[name]["wire_mm"]
        for name in ("outer", "inner")
    }
    acceleration = valve_report["valves"]["intake"]["maximum_harmonic_acceleration_m_s2"]
    dynamic = {
        family: worst_mid_load / (data["screen_moving_mass_kg"] * acceleration)
        for family, data in valve_report["valves"].items()
    }
    shear = {
        "outer": spring_shear(outer_force, candidate["outer"]),
        "inner": spring_shear(inner_force, candidate["inner"]),
    }
    gates = {
        "coil_bind_nominal": min(bind.values()) >= objectives["spring_coil_bind_margin_min_mm"],
        "coil_bind_worst_installed_height": min(bind.values()) - installed_tolerance
        >= objectives["spring_worst_case_coil_bind_margin_min_mm"],
        "dynamic_margin": min(dynamic.values()) >= objectives["spring_dynamic_force_margin_min"],
        "wahl_shear": max(shear.values()) <= objectives["spring_wahl_shear_max_mpa"],
    }
    return {
        "id": candidate["id"],
        "combined_rate_n_mm": k_total,
        "seat_load_n": seat,
        "open_load_n": open_load,
        "worst_open_load_n": worst_open_load,
        "installed_height_tolerance_mm": installed_tolerance,
        "coil_bind_margin_mm": bind,
        "worst_case_coil_bind_margin_mm": min(bind.values()) - installed_tolerance,
        "dynamic_force_margin": dynamic,
        "wahl_shear_mpa": shear,
        "gates": gates,
        "passed": all(gates.values()),
    }


def evaluate_valves(campaign: dict, geometry: dict, valve_report: dict) -> list[dict]:
    acceleration = valve_report["valves"]["intake"]["maximum_harmonic_acceleration_m_s2"]
    spring_mid_load = valve_report["spring"]["seat_load_n"] + 0.5 * valve_report["spring"]["combined_rate_n_per_mm"] * 12.0
    result = []
    for candidate in campaign["valve_material_candidates"]:
        family = candidate["family"]
        data = geometry["geometry"]["architecture"][family]
        mass = valve_volume_mm3(data["head_diameter_mm"], data["stem_diameter_mm"]) * candidate["density_kg_m3"] * 1.0e-9
        additional_mass = 0.040 if family == "intake" else 0.044
        dynamic = spring_mid_load / ((mass + additional_mass) * acceleration)
        evidence_classification = candidate["temperature_evidence_classification"]
        mechanical_temperature = candidate.get("mechanical_properties_temperature_c")
        temperature_ok = bool(
            mechanical_temperature is not None
            and mechanical_temperature >= candidate["reference_temperature_c"]
            and "not_service_rating" not in evidence_classification
        )
        result.append(
            {
                **candidate,
                "calculated_valve_mass_kg": mass,
                "baseline_spring_dynamic_margin": dynamic,
                "temperature_screen_passed": temperature_ok,
                "dynamic_screen_passed": dynamic >= 1.2,
                "passed": temperature_ok and dynamic >= 1.2,
            }
        )
    return result


def render(report: dict, output: Path) -> None:
    figure, axes = plt.subplots(2, 3, figsize=(21, 10), facecolor="#0b1118")
    figure.suptitle("F36 — matrice réelle des améliorations calculées", color="white", fontsize=21, fontweight="bold")
    for axis in axes.flat:
        axis.set_facecolor("#101b24")
        axis.tick_params(colors="#d4dde4")
        for spine in axis.spines.values():
            spine.set_color("#41505b")

    geometry = report["geometry_candidates"]
    ax = axes[0, 0]
    ax.bar([item["id"] for item in geometry], [item["mass_kg"] for item in geometry], color="#d69b42")
    ax.axhline(report["objectives"]["bare_head_mass_max_kg"], color="#ef6b5a", linestyle="--", label="cible 2,83 kg")
    ax.set_title("Allègement géométrique", color="white", fontweight="bold")
    ax.set_ylabel("masse nue calculée (kg)", color="#d4dde4")
    ax.legend(facecolor="#101b24", labelcolor="white")
    ax.tick_params(axis="x", rotation=25)

    springs = report["spring_candidates"]
    ax = axes[0, 1]
    colors = ["#4bbf8a" if item["passed"] else "#ef6b5a" for item in springs]
    ax.bar([item["id"] for item in springs], [min(item["dynamic_force_margin"].values()) for item in springs], color=colors)
    ax.axhline(report["objectives"]["spring_dynamic_force_margin_min"], color="#f0bd58", linestyle="--")
    ax.set_title("Marge dynamique des ressorts", color="white", fontweight="bold")
    ax.set_ylabel("marge minimale", color="#d4dde4")
    ax.tick_params(axis="x", rotation=25)

    cooling = report["cooling_candidates"]
    ax = axes[0, 2]
    for item in cooling:
        color = "#4bbf8a" if item["passed"] else "#ef6b5a"
        ax.scatter(item["pressure_drop_pa"] / 1000.0, item["effective_h_w_m2k"], color=color, s=65)
        ax.annotate(item["id"].replace("shroud-", ""), (item["pressure_drop_pa"] / 1000.0, item["effective_h_w_m2k"]), color="#d4dde4", fontsize=8, xytext=(4, 3), textcoords="offset points")
    ax.axhline(report["objectives"]["external_air_h_required_w_m2k"], color="#f0bd58", linestyle="--")
    ax.axvline(report["objectives"]["external_air_pressure_drop_max_pa"] / 1000.0, color="#f0bd58", linestyle="--")
    ax.set_title("Carénage : échange contre pompage", color="white", fontweight="bold")
    ax.set_xlabel("perte de charge (kPa)", color="#d4dde4")
    ax.set_ylabel("h effectif (W/m²K)", color="#d4dde4")

    thermal = report["thermal_candidates"]
    ax = axes[1, 0]
    if thermal:
        colors = ["#4bbf8a" if item["maximum_below_service_screen"] else "#ef6b5a" for item in thermal]
        ax.bar([item["id"] for item in thermal], [item["maximum_temperature_c"] for item in thermal], color=colors)
        ax.axhline(report["objectives"]["head_service_temperature_max_c"], color="#f0bd58", linestyle="--")
        ax.tick_params(axis="x", rotation=25)
    ax.set_title("Refroidissement / charge thermique", color="white", fontweight="bold")
    ax.set_ylabel("température maximale (°C)", color="#d4dde4")

    structural = report["structural_candidates"]
    ax = axes[1, 1]
    if structural:
        labels = [item["id"] for item in structural]
        positions = list(range(len(labels)))
        ax.bar(positions, [item["p99_mpa"] for item in structural], color="#4d9bd6", label="p99")
        ax.scatter(positions, [item["maximum_mpa"] for item in structural], color="#ef6b5a", marker="x", s=55, label="maximum local")
        ax.axhline(216.0, color="#f0bd58", linestyle="--", label="Rp0,2 écran chaud")
        ax.set_xticks(positions, labels, rotation=25)
        ax.legend(facecolor="#101b24", labelcolor="white", fontsize=8)
    ax.set_title("Structure : champ et pic local", color="white", fontweight="bold")
    ax.set_ylabel("Von Mises (MPa)", color="#d4dde4")

    ax = axes[1, 2]
    rows = [
        ("Matériau culasse retenu", report["selection"]["head_material"]),
        ("Soupape admission", report["selection"]["intake_valve"]),
        ("Soupape échappement", report["selection"]["exhaust_valve"]),
        ("Ressort virtuel", report["selection"]["spring"]),
        ("Carénage", report["selection"]["cooling"]),
        ("Géométrie", report["selection"]["geometry"]),
        ("Libération impression", "NON"),
        ("Autorisation démarrage", "NON"),
    ]
    ax.axis("off")
    y = 0.90
    for label, value in rows:
        ax.text(0.02, y, label, color="#9fb0bd", fontsize=11)
        ax.text(0.47, y, value, color="white", fontsize=11, fontweight="bold")
        y -= 0.105
    ax.set_title("Sélection sous contraintes", color="white", fontweight="bold")
    figure.text(0.5, 0.02, "Chaque barre provient d'un rapport numérique traçable. Échelle, cartes à chaud, CT/CND, spintron, banc de flux et banc moteur restent non corrélés.", color="#d4dde4", ha="center", fontsize=10)
    figure.subplots_adjust(left=0.07, right=0.98, bottom=0.13, top=0.90, hspace=0.42, wspace=0.24)
    figure.savefig(output, dpi=180, facecolor=figure.get_facecolor())
    plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--geometry", action="append", type=labelled, required=True)
    parser.add_argument("--valvetrain", type=Path, required=True)
    parser.add_argument("--thermal", action="append", type=labelled, default=[])
    parser.add_argument("--structural", action="append", type=labelled, default=[])
    parser.add_argument("--cooling", action="append", type=labelled, default=[])
    parser.add_argument("--lpbf", type=Path)
    parser.add_argument("--lpbf-locked", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    campaign = load(args.campaign)
    objectives = campaign["objectives"]
    geometry_reports = [(label, path, load(path)) for label, path in args.geometry]
    final_geometry = geometry_reports[-1][2]
    valve_report = load(args.valvetrain)

    geometry = []
    for label, path, payload in geometry_reports:
        geometry_payload = payload["geometry"]
        mass = geometry_payload.get("candidate_mass_kg_if_obj_unit_is_mm_and_density_2670")
        if mass is None:
            # F36-009 predates the explicit mass field; recompute the same
            # quantity from its recorded closed volume instead of dropping the
            # first point of the geometry DOE.
            mass = geometry_payload["volume_cubic_obj_units"] * 2670.0e-9
        geometry.append(
            {
                "id": label,
                "path": str(path),
                "sha256": sha256(path),
                "mass_kg": mass,
                "mass_gate": mass <= objectives["bare_head_mass_max_kg"],
                "watertight": payload["geometry"]["watertight"],
                "scan_p95_obj_units": payload["geometry"]["scan_surface_conformance"]["p95_obj_units"],
                "minimum_wall_screen_obj_units": payload["geometry"]["internal_wall_screen"]["minimum_obj_units"],
            }
        )

    materials = []
    volume = final_geometry["geometry"]["volume_cubic_obj_units"]
    for candidate in campaign["head_material_candidates"]:
        density = candidate["density_kg_m3"]
        additive = candidate["route"].startswith("LPBF")
        service = candidate["service_temperature_screen_c"]
        materials.append(
            {
                **candidate,
                "mass_kg_if_scale_is_mm": volume * density * 1.0e-9 if density is not None else None,
                "additive_route_screen_passed": additive,
                "service_temperature_screen_passed": service is not None and service >= objectives["head_service_temperature_max_c"],
                "hot_yield_card_available": candidate["yield_mpa_at_250c"] is not None,
                "passed": additive and service is not None and service >= objectives["head_service_temperature_max_c"] and candidate["yield_mpa_at_250c"] is not None,
            }
        )

    thermal = []
    for label, path in args.thermal:
        payload = load(path)
        maximum = payload["results"]["maximum_temperature_c"]
        thermal.append(
            {
                "id": label,
                "path": str(path),
                "sha256": sha256(path),
                "analysis_type": payload["boundary_conditions"]["analysis_type"],
                "duration_s": payload["boundary_conditions"].get("transient_duration_s"),
                "p95_temperature_c": payload["results"]["p95_temperature_c"],
                "maximum_temperature_c": maximum,
                "maximum_below_service_screen": maximum < objectives["head_service_temperature_max_c"],
            }
        )

    structural = []
    for label, path in args.structural:
        payload = load(path)
        structural.append(
            {
                "id": label,
                "path": str(path),
                "sha256": sha256(path),
                "pitch_mm": payload["mesh"]["pitch_mm_if_obj_unit_is_mm"],
                "p95_mpa": payload["results"]["von_mises_p95_mpa"],
                "p99_mpa": payload["results"]["von_mises_p99_mpa"],
                "maximum_mpa": payload["results"]["von_mises_max_mpa"],
                "p99_hot_yield_margin": payload["results"]["p99_hot_yield_margin"],
                "p99_gate": payload["results"]["p99_hot_yield_margin"] >= objectives["structural_p99_hot_yield_margin_min"],
            }
        )

    cooling = []
    for label, path in args.cooling:
        payload = load(path)
        pressure_drop = payload["pressure_drop_from_drag_pa"]
        effective_h = payload["effective_h_w_m2k"]
        mass_flow = payload["mass_flow_kg_s"]
        stable = bool(payload.get("numerically_stable") and payload.get("converged"))
        h_gate = effective_h >= objectives["external_air_h_required_w_m2k"]
        pressure_gate = pressure_drop <= objectives["external_air_pressure_drop_max_pa"]
        cooling.append(
            {
                "id": label,
                "path": str(path),
                "sha256": sha256(path),
                "grid": payload["grid"],
                "mass_flow_kg_s": mass_flow,
                "heat_rejection_w": payload["heat_rejection_w"],
                "effective_h_w_m2k": effective_h,
                "pressure_drop_pa": pressure_drop,
                "ideal_hydraulic_power_w": pressure_drop * mass_flow / 1.06,
                "stable_and_converged": stable,
                "h_gate": h_gate,
                "pressure_gate": pressure_gate,
                "passed": stable and h_gate and pressure_gate,
            }
        )

    lpbf = load(args.lpbf) if args.lpbf else None
    springs = [evaluate_spring(item, valve_report, objectives) for item in campaign["spring_candidates"]]
    valves = evaluate_valves(campaign, final_geometry, valve_report)
    valid_geometry = [item for item in geometry if item["mass_gate"] and item["watertight"]]
    valid_materials = [item for item in materials if item["passed"]]
    valid_springs = [item for item in springs if item["passed"]]
    intake_valves = [item for item in valves if item["family"] == "intake" and item["passed"]]
    exhaust_valves = [item for item in valves if item["family"] == "exhaust" and item["passed"]]
    valid_cooling = [item for item in cooling if item["passed"]]
    preferred_thermal = next(
        (
            item
            for item in thermal
            if item["id"] == "turbo_q0.45_h1600_p2.5" and item["maximum_below_service_screen"]
        ),
        None,
    )
    selection = {
        "geometry": min(valid_geometry, key=lambda item: item["mass_kg"])["id"] if valid_geometry else "none_passed",
        "head_material": min(valid_materials, key=lambda item: item["mass_kg_if_scale_is_mm"])["id"] if valid_materials else "none_passed",
        "intake_valve": min(intake_valves, key=lambda item: item["calculated_valve_mass_kg"])["id"] if intake_valves else "none_passed",
        "exhaust_valve": min(exhaust_valves, key=lambda item: item["calculated_valve_mass_kg"])["id"] if exhaust_valves else "none_passed",
        "spring": max(valid_springs, key=lambda item: min(item["dynamic_force_margin"].values()))["id"] if valid_springs else "none_passed",
        "cooling": min(valid_cooling, key=lambda item: item["ideal_hydraulic_power_w"])["id"] if valid_cooling else "none_passed",
        "thermal_case": preferred_thermal["id"] if preferred_thermal else min((item for item in thermal if item["maximum_below_service_screen"]), key=lambda item: item["maximum_temperature_c"], default={"id": "none_passed"})["id"],
    }
    report = {
        "schema_version": "1.0.0",
        "phase": "F36",
        "status": "bounded_improvement_doe_complete_physical_release_blocked",
        "classification": "traceable_virtual_screen_not_exhaustive_and_not_physical_validation",
        "objectives": objectives,
        "geometry_candidates": geometry,
        "head_material_candidates": materials,
        "valve_material_candidates": valves,
        "spring_candidates": springs,
        "thermal_candidates": thermal,
        "structural_candidates": structural,
        "cooling_candidates": cooling,
        "lpbf": {
            "path": str(args.lpbf),
            "sha256": sha256(args.lpbf),
            "selected_orientation": lpbf["selected_orientation"],
            "unsupported_fraction": lpbf["voxel_audit"]["unsupported_fraction"],
            "unsupported_gate": lpbf["voxel_audit"]["unsupported_fraction"] <= objectives["lpbf_unsupported_fraction_max"],
        } if lpbf else None,
        "lpbf_locked_plate": {
            "path": str(args.lpbf_locked),
            "sha256": sha256(args.lpbf_locked),
            "classification": load(args.lpbf_locked)["classification"],
            "results": load(args.lpbf_locked)["results"],
        } if args.lpbf_locked else None,
        "selection": selection,
        "release_gates": {
            "scale_confirmed": False,
            "temperature_dependent_material_cards_from_printed_coupons": False,
            "ct_ndt_complete": False,
            "flowbench_correlated": False,
            "spintron_correlated": False,
            "dyno_correlated": False,
            "metal_print_authorized": False,
            "engine_start_authorized": False,
        }
    }
    args.output.mkdir(parents=True, exist_ok=False)
    report_path = args.output / "improvement-doe-report.json"
    image_path = args.output / "917-head-f36-improvement-doe.png"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    render(report, image_path)
    print(json.dumps({"status": report["status"], "report": str(report_path), "image": str(image_path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
