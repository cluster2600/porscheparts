#!/usr/bin/env python3
"""Construit les enveloppes de chargement CAE F47 depuis les traces F46.

Le programme ne lance aucun solveur CFD, CHT ou EF et ne charge aucune
geometrie. Il verifie les empreintes F46, extrait uniquement les echantillons
entiers deja presents dans chacune des 36 traces, puis publie des bornes et des
contrats de transfert fail-closed.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import html
import json
import math
import struct
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


CONTRACT_REL = Path("twins/reference-917-engine/cae-load-transfer-f47.json")
SOURCE_REL = Path("twins/reference-917-engine/source/build_cae_load_transfer_f47.py")
EVIDENCE_REL = Path("twins/reference-917-engine/evidence/f47-cae-loads")
REPORT_REL = EVIDENCE_REL / "load-report.json"
SUMMARY_REL = EVIDENCE_REL / "summary.json"
ENVELOPE_JSON_REL = EVIDENCE_REL / "envelopes/f47-load-envelopes.json"
OPENFOAM_MAP_REL = EVIDENCE_REL / "mappings/openfoam-aate-enginefoam-patches.json"
CALCULIX_MAP_REL = EVIDENCE_REL / "mappings/calculix-loads.json"
SVG_REL = EVIDENCE_REL / "figures/f47-cae-load-envelopes.svg"
PNG_REL = EVIDENCE_REL / "figures/f47-cae-load-envelopes.png"
MANIFEST_REL = EVIDENCE_REL / "manifest.json"

MODELS = ("cantera_finite_rate", "wiebe_counter_model")
ARCHITECTURES = ("2v", "4v")
VARIABLES = (
    "pressure_pa_abs",
    "pressure_gauge_pa",
    "temperature_k",
    "h_gas_w_m2_k",
    "wall_heat_flux_w_m2",
)
MODEL_SHORT = {
    "cantera_finite_rate": "cantera",
    "wiebe_counter_model": "wiebe",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    require(isinstance(value, dict), f"JSON racine invalide: {path}")
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def rounded(value: float, digits: int = 9) -> float:
    result = round(float(value), digits)
    return 0.0 if result == -0.0 else result


def finite_float(value: Any, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label}: valeur non numerique") from error
    require(math.isfinite(result), f"{label}: valeur non finie")
    return result


def validate_contract(contract: dict[str, Any]) -> None:
    require(contract.get("schema_version") == "1.0.0", "schema F47 inattendu")
    require(contract.get("phase") == "F47", "phase F47 absente")
    matrix = contract.get("source_matrix", {})
    require(matrix.get("architectures") == list(ARCHITECTURES), "architectures F47 invalides")
    require(matrix.get("combustion_models") == list(MODELS), "modeles F47 invalides")
    require(matrix.get("discharge_coefficients") == [0.62, 0.72, 0.82], "Cd F47 invalides")
    require(matrix.get("crank_steps_deg") == [1.0, 0.5, 0.25], "pas F47 invalides")
    require(matrix.get("expected_case_count") == 36, "F47 exige 36 cas")
    grid = contract.get("transfer_grid", {})
    require(
        (grid.get("start_deg"), grid.get("stop_exclusive_deg"), grid.get("step_deg"))
        == (0, 720, 1),
        "grille F47 invalide",
    )
    require(grid.get("interpolation_allowed") is False, "interpolation F47 interdite")
    geometry = contract.get("geometry_policy", {})
    for key in (
        "geometry_created",
        "cad_created",
        "mesh_created",
        "external_scan_contour_modified",
        "oval_or_ellipse_created",
    ):
        require(geometry.get(key) is False, f"politique geometrie fail-open: {key}")
    require(geometry.get("patches_are_unresolved_names_only") is True, "patches non bornes")
    gates = contract.get("release_gates", {})
    require(gates and all(value is False for value in gates.values()), "une gate F47 est ouverte")
    require(contract["envelope_policy"].get("joint_trajectory_claimed") is False, "fausse trajectoire")
    require(contract["solver_handoff"]["openfoam_family"].get("execution_claimed") is False, "fausse CFD")
    require(contract["solver_handoff"]["calculix"].get("execution_claimed") is False, "fausse FEA")


def verify_bound_json(project_root: Path, binding: dict[str, str], label: str) -> dict[str, Any]:
    path = project_root / binding["path"]
    require(path.is_file() and not path.is_symlink(), f"{label}: source absente ou lien")
    require(sha256_file(path) == binding["sha256"], f"{label}: SHA-256 divergent")
    return load_json(path)


def verify_upstream(project_root: Path, contract: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    upstream = contract["upstream"]
    f46_contract = verify_bound_json(project_root, upstream["f46_contract"], "contrat F46")
    report = verify_bound_json(project_root, upstream["f46_cycle_report"], "rapport F46")
    manifest = verify_bound_json(project_root, upstream["f46_manifest"], "manifeste F46")
    authority = verify_bound_json(project_root, upstream["solver_authority"], "autorite solveur")

    require(f46_contract.get("phase") == "F46", "contrat amont hors F46")
    require(report.get("phase") == "F46", "rapport amont hors F46")
    require(report.get("runtime", {}).get("case_count") == 36, "rapport F46 incomplet")
    require(
        report.get("common_conditions_identical_between_architectures")
        == f46_contract.get("common_operating_point"),
        "frontieres F46 non liees au contrat",
    )
    require(
        report.get("conclusion", {}).get("both_architectures_share_identical_non_geometry_boundaries")
        is True,
        "frontieres non comparables",
    )
    require(authority.get("phase") == "F46", "autorite solveur hors F46")
    require(authority["execution_gates"].get("cross_method_acceptance_passed") is False, "gate amont incoherente")
    geometry = f46_contract.get("geometry", {})
    require(geometry.get("external_head_geometry_used") is False, "geometrie externe F46 interdite")
    require(geometry.get("external_scan_contour_modified") is False, "peau scan modifiee")
    require(geometry.get("oval_or_ellipse_created") is False, "geometrie non circulaire interdite")

    artifact_map: dict[str, dict[str, Any]] = {}
    for item in manifest.get("artifacts", []):
        require(isinstance(item, dict), "entree manifeste F46 invalide")
        rel = item.get("path")
        require(isinstance(rel, str) and rel not in artifact_map, "artefact F46 duplique")
        artifact_map[rel] = item
        path = project_root / rel
        require(path.is_file() and not path.is_symlink(), f"artefact F46 absent: {rel}")
        require(path.stat().st_size == item.get("bytes"), f"taille F46 divergente: {rel}")
        require(sha256_file(path) == item.get("sha256"), f"empreinte F46 divergente: {rel}")
    return f46_contract, report, artifact_map


def wall_transfer_coefficient(pressure_pa: float, temperature_k: float, mean_piston_speed_m_s: float) -> float:
    return (
        130.0
        * (max(pressure_pa, 1.0e4) / 1.0e5) ** 0.8
        * (max(temperature_k, 200.0) / 300.0) ** -0.53
        * (max(mean_piston_speed_m_s, 1.0) / 10.0) ** 0.8
    )


def read_case_samples(
    project_root: Path,
    case: dict[str, Any],
    artifact_map: dict[str, dict[str, Any]],
    wall_temperature_k: float,
    mean_piston_speed_m_s: float,
) -> tuple[dict[int, dict[str, float]], float]:
    raw = case.get("raw_timeseries", {})
    rel = raw.get("path")
    require(isinstance(rel, str) and rel in artifact_map, f"trace non manifestee: {case.get('case_id')}")
    item = artifact_map[rel]
    require(raw.get("sha256") == item.get("sha256"), f"SHA trace/report divergent: {rel}")
    path = project_root / rel
    samples: dict[int, dict[str, float]] = {}
    worst_closure = 0.0
    row_count = 0
    with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"crank_angle_deg", "pressure_pa_abs", "temperature_k", "wall_heat_flux_w_m2"}
        require(required.issubset(set(reader.fieldnames or [])), f"colonnes trace absentes: {rel}")
        for row in reader:
            row_count += 1
            angle = finite_float(row["crank_angle_deg"], f"{rel}: angle")
            pressure = finite_float(row["pressure_pa_abs"], f"{rel}: pression")
            temperature = finite_float(row["temperature_k"], f"{rel}: temperature")
            flux = finite_float(row["wall_heat_flux_w_m2"], f"{rel}: flux")
            require(pressure > 0.0 and temperature > 0.0, f"etat non physique dans {rel}")
            h_gas = wall_transfer_coefficient(pressure, temperature, mean_piston_speed_m_s)
            closure = h_gas * (temperature - wall_temperature_k)
            relative = abs(closure - flux) / max(abs(flux), 1.0)
            worst_closure = max(worst_closure, relative)
            nearest = int(round(angle))
            if abs(angle - nearest) <= 1.0e-10 and 0 <= nearest < 720:
                require(nearest not in samples, f"angle entier duplique dans {rel}: {nearest}")
                samples[nearest] = {
                    "pressure_pa_abs": pressure,
                    "temperature_k": temperature,
                    "h_gas_w_m2_k": h_gas,
                    "wall_heat_flux_w_m2": flux,
                }
    require(row_count == raw.get("rows"), f"compte de lignes divergent: {rel}")
    require(set(samples) == set(range(720)), f"grille entiere incomplete: {rel}")
    return samples, worst_closure


def load_all_cases(
    project_root: Path,
    contract: dict[str, Any],
    f46_contract: dict[str, Any],
    report: dict[str, Any],
    artifact_map: dict[str, dict[str, Any]],
) -> tuple[dict[str, dict[int, dict[str, float]]], list[dict[str, Any]], float]:
    geometry = f46_contract["geometry"]
    common = f46_contract["common_operating_point"]
    speed = finite_float(common["speed_rpm"], "regime")
    stroke_m = finite_float(geometry["stroke_mm"], "course") * 1.0e-3
    mean_piston_speed = 2.0 * stroke_m * speed / 60.0
    wall_temperature = finite_float(contract["load_equations"]["wall_temperature_k"], "T paroi")
    reference_pressure = finite_float(
        contract["load_equations"]["structural_reference_pressure_pa_abs"], "pression reference"
    )

    cases = report.get("cases", [])
    require(isinstance(cases, list) and len(cases) == 36, "matrice F46 incomplete")
    identities: set[tuple[str, str, float, float]] = set()
    samples_by_case: dict[str, dict[int, dict[str, float]]] = {}
    index: list[dict[str, Any]] = []
    worst_closure = 0.0
    for case in cases:
        arch = case.get("architecture")
        model = case.get("model")
        cd = finite_float(case.get("Cd"), "Cd")
        step = finite_float(case.get("crank_step_deg"), "pas")
        identity = (arch, model, cd, step)
        require(arch in ARCHITECTURES and model in MODELS, f"identite cas invalide: {identity}")
        require(cd in (0.62, 0.72, 0.82) and step in (1.0, 0.5, 0.25), f"DOE invalide: {identity}")
        require(identity not in identities, f"cas duplique: {identity}")
        identities.add(identity)
        case_id = case.get("case_id")
        require(isinstance(case_id, str) and case_id not in samples_by_case, "case_id invalide")
        samples, closure = read_case_samples(
            project_root, case, artifact_map, wall_temperature, mean_piston_speed
        )
        for sample in samples.values():
            sample["pressure_gauge_pa"] = sample["pressure_pa_abs"] - reference_pressure
        samples_by_case[case_id] = samples
        worst_closure = max(worst_closure, closure)
        index.append(
            {
                "case_id": case_id,
                "architecture": arch,
                "combustion_model": model,
                "Cd": cd,
                "crank_step_deg": step,
                "raw_path": case["raw_timeseries"]["path"],
                "raw_sha256": case["raw_timeseries"]["sha256"],
                "integer_samples_used": 720,
            }
        )
    require(len(identities) == 36, "matrice de cas non unique")
    return samples_by_case, sorted(index, key=lambda item: item["case_id"]), worst_closure


def build_envelopes(
    contract: dict[str, Any],
    case_index: list[dict[str, Any]],
    samples_by_case: dict[str, dict[int, dict[str, float]]],
) -> dict[str, Any]:
    speed = finite_float(contract["transfer_grid"]["speed_rpm"], "regime transfert")
    groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    for case in case_index:
        groups[(case["architecture"], case["combustion_model"])].append(case["case_id"])
    for key, values in groups.items():
        require(len(values) == 9, f"nombre de contributeurs incorrect pour {key}")

    architectures: dict[str, Any] = {}
    for arch in ARCHITECTURES:
        rows: list[dict[str, Any]] = []
        for angle in range(720):
            row: dict[str, Any] = {
                "crank_angle_deg": angle,
                "cycle_time_s": rounded(angle / (6.0 * speed), 12),
            }
            for variable in VARIABLES:
                model_bounds: list[tuple[float, float]] = []
                for model in MODELS:
                    values = [
                        samples_by_case[case_id][angle][variable]
                        for case_id in groups[(arch, model)]
                    ]
                    lower = min(values)
                    upper = max(values)
                    short = MODEL_SHORT[model]
                    row[f"{short}_{variable}_min"] = rounded(lower)
                    row[f"{short}_{variable}_max"] = rounded(upper)
                    model_bounds.append((lower, upper))
                row[f"cross_model_{variable}_min"] = rounded(min(value[0] for value in model_bounds))
                row[f"cross_model_{variable}_max"] = rounded(max(value[1] for value in model_bounds))
            rows.append(row)
        architectures[arch] = {
            "variant_id": f"917_30_turbo_5374_{arch}_f45",
            "rows": rows,
            "rows_count": len(rows),
        }
    return {
        "schema_version": "1.0.0",
        "phase": "F47",
        "classification": contract["classification"],
        "grid": contract["transfer_grid"],
        "equations": contract["load_equations"],
        "envelope_policy": contract["envelope_policy"],
        "architectures": architectures,
    }


def envelope_csv_fields() -> list[str]:
    fields = ["crank_angle_deg", "cycle_time_s"]
    for variable in VARIABLES:
        for prefix in ("cantera", "wiebe", "cross_model"):
            fields.extend((f"{prefix}_{variable}_min", f"{prefix}_{variable}_max"))
    return fields


def write_envelope_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=envelope_csv_fields(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def global_bounds(rows: list[dict[str, Any]], prefix: str, variable: str) -> dict[str, Any]:
    lower_key = f"{prefix}_{variable}_min"
    upper_key = f"{prefix}_{variable}_max"
    minimum_row = min(rows, key=lambda row: row[lower_key])
    maximum_row = max(rows, key=lambda row: row[upper_key])
    return {
        "minimum": minimum_row[lower_key],
        "minimum_crank_angle_deg": minimum_row["crank_angle_deg"],
        "maximum": maximum_row[upper_key],
        "maximum_crank_angle_deg": maximum_row["crank_angle_deg"],
    }


def build_metrics(envelopes: dict[str, Any], worst_closure: float) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "wall_flux_equation_closure": {
            "worst_relative_error": rounded(worst_closure, 12),
            "pass": worst_closure <= 1.0e-6,
        },
        "architectures": {},
    }
    for arch in ARCHITECTURES:
        rows = envelopes["architectures"][arch]["rows"]
        arch_metrics: dict[str, Any] = {}
        for variable in VARIABLES:
            arch_metrics[variable] = {
                prefix: global_bounds(rows, prefix, variable)
                for prefix in ("cantera", "wiebe", "cross_model")
            }
            cantera_max = arch_metrics[variable]["cantera"]["maximum"]
            wiebe_max = arch_metrics[variable]["wiebe"]["maximum"]
            arch_metrics[variable]["model_peak_spread_fraction"] = rounded(
                abs(cantera_max - wiebe_max) / max(abs(cantera_max), abs(wiebe_max), 1.0e-30)
            )
        metrics["architectures"][arch] = arch_metrics
    metrics["outer_maximum_4v_change_fraction"] = {
        variable: rounded(
            (
                metrics["architectures"]["4v"][variable]["cross_model"]["maximum"]
                / metrics["architectures"]["2v"][variable]["cross_model"]["maximum"]
            )
            - 1.0
        )
        for variable in VARIABLES
    }
    return metrics


def build_openfoam_mapping(contract: dict[str, Any], case_index: list[dict[str, Any]]) -> dict[str, Any]:
    patch_names = (
        ("cylinder_gas_zone", "cell_zone", "p_and_T_comparison_target_only"),
        ("combustion_chamber_wall", "wall", "Robin_h_Tgas_or_direct_qwall"),
        ("piston_crown_wall", "moving_wall", "Robin_h_Tgas_or_direct_qwall"),
        ("intake_valve_faces", "moving_wall", "motion_and_thermal_mapping_pending"),
        ("exhaust_valve_faces", "moving_wall", "motion_and_thermal_mapping_pending"),
        ("intake_port_boundary", "patch", "plenum_boundary_from_F46_hypothesis_only"),
        ("exhaust_port_boundary", "patch", "plenum_boundary_from_F46_hypothesis_only"),
    )
    return {
        "schema_version": "1.0.0",
        "phase": "F47",
        "classification": "planned_field_and_patch_mapping_not_a_solver_deck_not_a_CFD_run",
        "solver_roles": contract["solver_handoff"]["openfoam_family"]["roles"],
        "solver_authority_binding": contract["upstream"]["solver_authority"],
        "execution_claimed": False,
        "geometry_loaded": False,
        "patch_templates": [
            {
                "semantic_name": name,
                "required_type": patch_type,
                "intended_use": use,
                "resolved_geometry_patch": None,
                "status": "blocked_no_sealed_variant_fluid_domain",
            }
            for name, patch_type, use in patch_names
        ],
        "field_mapping": {
            "pressure_pa_abs": {
                "destination": "volume_averaged_cylinder_pressure_comparison_target",
                "boundary_condition": False,
                "warning": "Imposer la pression 0D sur la chambre supprimerait la prediction CFD.",
            },
            "temperature_k": {
                "destination": "volume_averaged_cylinder_temperature_comparison_target",
                "boundary_condition": False,
            },
            "h_gas_w_m2_k_plus_temperature_k": {
                "destination": "future_conjugate_wall_Robin_condition",
                "equation": "q_into_solid=h_gas*(T_gas-T_solid_local)",
                "allowed_with_direct_flux": False,
            },
            "wall_heat_flux_w_m2": {
                "destination": "future_prescribed_wall_flux_sensitivity_only",
                "positive_direction": "gas_to_solid",
                "allowed_with_Robin_condition": False,
            },
        },
        "time_mapping": contract["transfer_grid"]["time_equation"],
        "source_case_policy": {
            "required": "choose_one_complete_F46_trace_and_preserve_case_id",
            "pointwise_envelope_as_solver_history_allowed": False,
            "available_case_count": len(case_index),
        },
        "load_tables": {
            arch: f"twins/reference-917-engine/evidence/f47-cae-loads/envelopes/f47-{arch}-load-envelope.csv"
            for arch in ARCHITECTURES
        },
        "release_gates": contract["release_gates"],
    }


def build_calculix_mapping(contract: dict[str, Any], case_index: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "phase": "F47",
        "classification": "planned_pressure_and_thermal_load_mapping_not_an_input_deck_not_a_FEA_run",
        "execution_claimed": False,
        "geometry_loaded": False,
        "units": {"length": "m", "pressure": "Pa", "temperature": "K", "heat_flux": "W/m2"},
        "required_surface_sets": [
            {
                "semantic_name": "combustion_chamber_surface",
                "resolved_element_face_set": None,
                "normal_orientation_reviewed": False,
                "status": "blocked_no_verified_solid_mesh",
            },
            {
                "semantic_name": "external_cooling_surface",
                "resolved_element_face_set": None,
                "normal_orientation_reviewed": False,
                "status": "blocked_no_verified_solid_mesh",
            },
            {
                "semantic_name": "deck_and_stud_constraints",
                "resolved_node_or_face_set": None,
                "contact_model_verified": False,
                "status": "blocked_no_interface_metrology",
            },
        ],
        "structural_pressure": {
            "source": "pressure_gauge_pa_from_one_complete_F46_trace",
            "equation": contract["load_equations"]["structural_gauge_pressure"],
            "reference_pressure_pa_abs": contract["load_equations"]["structural_reference_pressure_pa_abs"],
            "reference_pressure_classification": contract["load_equations"]["reference_pressure_classification"],
            "intended_keyword": "DLOAD_P_after_surface_normal_review",
            "dynamic_inertia_or_contact_included": False,
        },
        "thermal": {
            "recommended": {
                "source": "h_gas_w_m2_k_and_temperature_k_from_one_complete_F46_trace",
                "intended_keyword": "FILM_or_equivalent_time_dependent_Robin_load",
                "equation": "q_into_solid=h_gas*(T_gas-T_solid_local)",
            },
            "sensitivity_alternative": {
                "source": "wall_heat_flux_w_m2_from_same_complete_F46_trace",
                "intended_keyword": "DFLUX_after_sign_review",
            },
            "simultaneous_Robin_and_direct_flux_allowed": False,
            "material_card_at_temperature_available": False,
        },
        "time_mapping": contract["transfer_grid"]["time_equation"],
        "source_case_policy": {
            "required": "choose_one_complete_F46_trace_and_preserve_case_id",
            "pointwise_envelope_as_solver_history_allowed": False,
            "available_case_count": len(case_index),
        },
        "load_tables": {
            arch: f"twins/reference-917-engine/evidence/f47-cae-loads/envelopes/f47-{arch}-load-envelope.csv"
            for arch in ARCHITECTURES
        },
        "release_gates": contract["release_gates"],
    }


def plot_series(rows: list[dict[str, Any]], model: str, variable: str) -> tuple[list[float], list[float], list[float]]:
    short = MODEL_SHORT[model]
    lower = [float(row[f"{short}_{variable}_min"]) for row in rows]
    upper = [float(row[f"{short}_{variable}_max"]) for row in rows]
    middle = [(low + high) * 0.5 for low, high in zip(lower, upper)]
    return lower, upper, middle


def _plot_specs() -> list[tuple[str, str, float]]:
    return [
        ("pressure_pa_abs", "Pression absolue [bar]", 1.0e-5),
        ("temperature_k", "Temperature gaz [K]", 1.0),
        ("h_gas_w_m2_k", "h gaz global [W/m2/K]", 1.0),
        ("wall_heat_flux_w_m2", "Flux paroi gaz vers solide [MW/m2]", 1.0e-6),
    ]


def build_svg(envelopes: dict[str, Any]) -> str:
    width, height = 1920, 1080
    margin_x, top = 110, 155
    gap_x, gap_y = 90, 100
    panel_w = (width - 2 * margin_x - gap_x) / 2
    panel_h = (height - top - 100 - gap_y) / 2
    colors = {"2v": "#f5a623", "4v": "#43a9ff"}
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="1920" height="1080" fill="#07141d"/>',
        '<text x="110" y="65" fill="#f4f8fb" font-family="DejaVu Sans, sans-serif" font-size="38" font-weight="700">F47 — chargements 0D bornés pour futurs calculs CAE</text>',
        '<text x="110" y="108" fill="#9fc5d8" font-family="DejaVu Sans, sans-serif" font-size="22">36 traces F46 · bandes Cd/pas · traits Cantera/Wiebe · aucune CFD/CHT/FEA exécutée</text>',
    ]
    for idx, (variable, title, scale) in enumerate(_plot_specs()):
        col, row_index = idx % 2, idx // 2
        x0 = margin_x + col * (panel_w + gap_x)
        y0 = top + row_index * (panel_h + gap_y)
        plot_x0, plot_y0 = x0 + 80, y0 + 45
        plot_w, plot_h = panel_w - 105, panel_h - 80
        all_values: list[float] = []
        series: dict[tuple[str, str], tuple[list[float], list[float], list[float]]] = {}
        for arch in ARCHITECTURES:
            rows = envelopes["architectures"][arch]["rows"]
            for model in MODELS:
                low, high, mid = plot_series(rows, model, variable)
                low = [value * scale for value in low]
                high = [value * scale for value in high]
                mid = [value * scale for value in mid]
                series[(arch, model)] = (low, high, mid)
                all_values.extend(low)
                all_values.extend(high)
        ymin, ymax = min(all_values), max(all_values)
        pad = max((ymax - ymin) * 0.08, 1.0e-12)
        ymin = ymin - pad if variable == "wall_heat_flux_w_m2" else max(0.0, ymin - pad)
        ymax += pad
        parts.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{panel_w:.1f}" height="{panel_h:.1f}" rx="18" fill="#0d2230" stroke="#214354"/>')
        parts.append(f'<text x="{x0 + 28:.1f}" y="{y0 + 34:.1f}" fill="#f4f8fb" font-family="DejaVu Sans, sans-serif" font-size="22" font-weight="700">{html.escape(title)}</text>')
        for tick in range(5):
            yy = plot_y0 + plot_h * tick / 4
            value = ymax - (ymax - ymin) * tick / 4
            parts.append(f'<line x1="{plot_x0:.1f}" y1="{yy:.1f}" x2="{plot_x0 + plot_w:.1f}" y2="{yy:.1f}" stroke="#234452" stroke-width="1"/>')
            parts.append(f'<text x="{plot_x0 - 10:.1f}" y="{yy + 6:.1f}" text-anchor="end" fill="#8fb1c0" font-family="DejaVu Sans Mono, monospace" font-size="14">{value:.3g}</text>')
        for angle in (0, 180, 360, 540, 720):
            xx = plot_x0 + plot_w * angle / 720
            parts.append(f'<line x1="{xx:.1f}" y1="{plot_y0:.1f}" x2="{xx:.1f}" y2="{plot_y0 + plot_h:.1f}" stroke="#1d3946"/>')
            parts.append(f'<text x="{xx:.1f}" y="{plot_y0 + plot_h + 24:.1f}" text-anchor="middle" fill="#8fb1c0" font-family="DejaVu Sans Mono, monospace" font-size="14">{angle}</text>')
        for arch in ARCHITECTURES:
            for model in MODELS:
                low, high, mid = series[(arch, model)]
                upper_points = []
                lower_points = []
                line_points = []
                for angle, (lo, hi, center) in enumerate(zip(low, high, mid)):
                    xx = plot_x0 + plot_w * angle / 719
                    y_hi = plot_y0 + plot_h * (ymax - hi) / (ymax - ymin)
                    y_lo = plot_y0 + plot_h * (ymax - lo) / (ymax - ymin)
                    y_mid = plot_y0 + plot_h * (ymax - center) / (ymax - ymin)
                    upper_points.append(f"{xx:.2f},{y_hi:.2f}")
                    lower_points.append(f"{xx:.2f},{y_lo:.2f}")
                    line_points.append(f"{xx:.2f},{y_mid:.2f}")
                polygon = " ".join(upper_points + list(reversed(lower_points)))
                dash = "" if model == "cantera_finite_rate" else ' stroke-dasharray="9 7"'
                parts.append(f'<polygon points="{polygon}" fill="{colors[arch]}" opacity="0.07"/>')
                parts.append(f'<polyline points="{" ".join(line_points)}" fill="none" stroke="{colors[arch]}" stroke-width="2.2"{dash}/>')
    legend_y = 1035
    parts.extend(
        [
            f'<line x1="110" y1="{legend_y}" x2="160" y2="{legend_y}" stroke="#f5a623" stroke-width="5"/><text x="175" y="{legend_y + 7}" fill="#dcebf2" font-family="DejaVu Sans, sans-serif" font-size="18">2V</text>',
            f'<line x1="250" y1="{legend_y}" x2="300" y2="{legend_y}" stroke="#43a9ff" stroke-width="5"/><text x="315" y="{legend_y + 7}" fill="#dcebf2" font-family="DejaVu Sans, sans-serif" font-size="18">4V</text>',
            f'<line x1="390" y1="{legend_y}" x2="450" y2="{legend_y}" stroke="#dcebf2" stroke-width="3"/><text x="465" y="{legend_y + 7}" fill="#dcebf2" font-family="DejaVu Sans, sans-serif" font-size="18">Cantera</text>',
            f'<line x1="590" y1="{legend_y}" x2="650" y2="{legend_y}" stroke="#dcebf2" stroke-width="3" stroke-dasharray="9 7"/><text x="665" y="{legend_y + 7}" fill="#dcebf2" font-family="DejaVu Sans, sans-serif" font-size="18">Wiebe</text>',
            f'<text x="1810" y="{legend_y + 7}" text-anchor="end" fill="#ff9b91" font-family="DejaVu Sans, sans-serif" font-size="18">Bornes non corrélées — aucune autorisation physique</text>',
            "</svg>",
        ]
    )
    return "\n".join(parts) + "\n"


def render_png(envelopes: dict[str, Any], path: Path) -> str:
    try:
        from PIL import Image, ImageDraw, ImageFont, __version__ as pillow_version
    except ImportError as error:
        raise RuntimeError("Pillow est requis uniquement pour regenerer le PNG F47") from error

    width, height = 1920, 1080
    image = Image.new("RGB", (width, height), "#07141d")
    draw = ImageDraw.Draw(image, "RGBA")
    font = ImageFont.load_default(size=24)
    font_small = ImageFont.load_default(size=17)
    font_title = ImageFont.load_default(size=40)
    draw.text((110, 38), "F47 - chargements 0D bornes pour futurs calculs CAE", fill="#f4f8fb", font=font_title)
    draw.text((110, 95), "36 traces F46 | bandes Cd/pas | Cantera/Wiebe | aucune CFD/CHT/FEA executee", fill="#9fc5d8", font=font)
    margin_x, top = 110, 155
    gap_x, gap_y = 90, 100
    panel_w = (width - 2 * margin_x - gap_x) / 2
    panel_h = (height - top - 100 - gap_y) / 2
    colors = {"2v": (245, 166, 35), "4v": (67, 169, 255)}
    for idx, (variable, title, scale) in enumerate(_plot_specs()):
        col, row_index = idx % 2, idx // 2
        x0 = margin_x + col * (panel_w + gap_x)
        y0 = top + row_index * (panel_h + gap_y)
        plot_x0, plot_y0 = x0 + 80, y0 + 45
        plot_w, plot_h = panel_w - 105, panel_h - 80
        draw.rounded_rectangle((x0, y0, x0 + panel_w, y0 + panel_h), radius=18, fill="#0d2230", outline="#214354", width=2)
        draw.text((x0 + 28, y0 + 14), title, fill="#f4f8fb", font=font)
        all_values: list[float] = []
        series: dict[tuple[str, str], tuple[list[float], list[float], list[float]]] = {}
        for arch in ARCHITECTURES:
            rows = envelopes["architectures"][arch]["rows"]
            for model in MODELS:
                low, high, mid = plot_series(rows, model, variable)
                low = [value * scale for value in low]
                high = [value * scale for value in high]
                mid = [value * scale for value in mid]
                series[(arch, model)] = (low, high, mid)
                all_values.extend(low + high)
        ymin, ymax = min(all_values), max(all_values)
        pad = max((ymax - ymin) * 0.08, 1.0e-12)
        ymin = ymin - pad if variable == "wall_heat_flux_w_m2" else max(0.0, ymin - pad)
        ymax += pad
        def point(angle: int, value: float) -> tuple[float, float]:
            return (
                plot_x0 + plot_w * angle / 719,
                plot_y0 + plot_h * (ymax - value) / (ymax - ymin),
            )
        for tick in range(5):
            yy = plot_y0 + plot_h * tick / 4
            value = ymax - (ymax - ymin) * tick / 4
            draw.line((plot_x0, yy, plot_x0 + plot_w, yy), fill="#234452", width=1)
            draw.text((plot_x0 - 72, yy - 8), f"{value:.3g}", fill="#8fb1c0", font=font_small)
        for angle in (0, 180, 360, 540, 719):
            xx = plot_x0 + plot_w * angle / 719
            draw.line((xx, plot_y0, xx, plot_y0 + plot_h), fill="#1d3946", width=1)
            draw.text((xx - 15, plot_y0 + plot_h + 8), "720" if angle == 719 else str(angle), fill="#8fb1c0", font=font_small)
        for arch in ARCHITECTURES:
            for model in MODELS:
                low, high, mid = series[(arch, model)]
                polygon = [point(i, value) for i, value in enumerate(high)] + [
                    point(i, value) for i, value in reversed(list(enumerate(low)))
                ]
                draw.polygon(polygon, fill=colors[arch] + (18,))
                points = [point(i, value) for i, value in enumerate(mid)]
                if model == "cantera_finite_rate":
                    draw.line(points, fill=colors[arch] + (255,), width=3, joint="curve")
                else:
                    for start in range(0, len(points) - 1, 14):
                        draw.line(points[start : min(start + 8, len(points))], fill=colors[arch] + (255,), width=3)
    draw.line((110, 1035, 160, 1035), fill=colors["2v"] + (255,), width=6)
    draw.text((175, 1023), "2V", fill="#dcebf2", font=font_small)
    draw.line((250, 1035, 300, 1035), fill=colors["4v"] + (255,), width=6)
    draw.text((315, 1023), "4V", fill="#dcebf2", font=font_small)
    draw.line((390, 1035, 450, 1035), fill="#dcebf2", width=3)
    draw.text((465, 1023), "Cantera", fill="#dcebf2", font=font_small)
    for x_start in range(590, 650, 15):
        draw.line((x_start, 1035, min(x_start + 9, 650), 1035), fill="#dcebf2", width=3)
    draw.text((665, 1023), "Wiebe", fill="#dcebf2", font=font_small)
    warning = "Bornes non correlees - aucune autorisation physique"
    warning_box = draw.textbbox((0, 0), warning, font=font_small)
    draw.text((1810 - (warning_box[2] - warning_box[0]), 1023), warning, fill="#ff9b91", font=font_small)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", compress_level=9, optimize=False)
    return pillow_version


def png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()[:24]
    require(data[:8] == b"\x89PNG\r\n\x1a\n", "signature PNG invalide")
    return struct.unpack(">II", data[16:24])


def artifact_record(project_root: Path, rel: Path) -> dict[str, Any]:
    path = project_root / rel
    return {"path": rel.as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def build(project_root: Path) -> None:
    contract_path = project_root / CONTRACT_REL
    require(contract_path.is_file() and not contract_path.is_symlink(), "contrat F47 absent")
    contract = load_json(contract_path)
    validate_contract(contract)
    f46_contract, f46_report, artifact_map = verify_upstream(project_root, contract)
    samples_by_case, case_index, worst_closure = load_all_cases(
        project_root, contract, f46_contract, f46_report, artifact_map
    )
    limit = finite_float(contract["quality_limits"]["relative_wall_flux_closure_limit"], "limite flux")
    require(worst_closure <= limit, f"fermeture h/T/q depassee: {worst_closure}")
    envelopes = build_envelopes(contract, case_index, samples_by_case)
    metrics = build_metrics(envelopes, worst_closure)

    evidence = project_root / EVIDENCE_REL
    evidence.mkdir(parents=True, exist_ok=True)
    envelope_csv_paths: dict[str, str] = {}
    for arch in ARCHITECTURES:
        rel = EVIDENCE_REL / f"envelopes/f47-{arch}-load-envelope.csv"
        write_envelope_csv(project_root / rel, envelopes["architectures"][arch]["rows"])
        envelope_csv_paths[arch] = rel.as_posix()
    write_json(project_root / ENVELOPE_JSON_REL, envelopes)

    openfoam_mapping = build_openfoam_mapping(contract, case_index)
    calculix_mapping = build_calculix_mapping(contract, case_index)
    write_json(project_root / OPENFOAM_MAP_REL, openfoam_mapping)
    write_json(project_root / CALCULIX_MAP_REL, calculix_mapping)
    (project_root / SVG_REL).parent.mkdir(parents=True, exist_ok=True)
    (project_root / SVG_REL).write_text(build_svg(envelopes), encoding="utf-8")
    pillow_version = render_png(envelopes, project_root / PNG_REL)

    report = {
        "schema_version": "1.0.0",
        "phase": "F47",
        "classification": contract["classification"],
        "input_manifest": {
            key: value for key, value in contract["upstream"].items()
        },
        "source_case_count": len(case_index),
        "source_case_index": case_index,
        "transfer": {
            "grid": contract["transfer_grid"],
            "equations": contract["load_equations"],
            "envelope_policy": contract["envelope_policy"],
            "envelope_csv_paths": envelope_csv_paths,
            "envelope_json_path": ENVELOPE_JSON_REL.as_posix(),
        },
        "metrics": metrics,
        "solver_handoff": {
            "openfoam_mapping_path": OPENFOAM_MAP_REL.as_posix(),
            "calculix_mapping_path": CALCULIX_MAP_REL.as_posix(),
            "solver_execution_claimed": False,
        },
        "figure": {
            "svg_path": SVG_REL.as_posix(),
            "png_path": PNG_REL.as_posix(),
            "png_dimensions_px": [1920, 1080],
            "png_renderer": f"Pillow {pillow_version}",
        },
        "quality": {
            "all_source_hashes_verified": True,
            "all_36_traces_loaded": True,
            "exact_samples_without_interpolation": True,
            "wall_flux_closure_limit": limit,
            "wall_flux_closure_worst_relative_error": rounded(worst_closure, 12),
            "wall_flux_closure_pass": worst_closure <= limit,
            "pointwise_envelopes_are_joint_trajectories": False,
            "physical_correlation_completed": False,
        },
        "geometry": contract["geometry_policy"],
        "release_gates": contract["release_gates"],
        "conclusion": {
            "load_transfer_completed": True,
            "future_solver_inputs_ready_without_geometry": False,
            "CFD_or_CHT_or_FEA_executed": False,
            "manufacturing_or_start_authorized": False,
        },
    }
    write_json(project_root / REPORT_REL, report)
    summary = {
        "schema_version": "1.0.0",
        "phase": "F47",
        "classification": contract["classification"],
        "source_case_count": len(case_index),
        "envelope_rows_total": sum(
            envelopes["architectures"][arch]["rows_count"] for arch in ARCHITECTURES
        ),
        "metrics": metrics,
        "mapping_status": {
            "OpenFOAM_AATE_engineFoam": "planned_names_only_blocked_without_sealed_fluid_domains",
            "CalculiX": "planned_loads_only_blocked_without_verified_solid_mesh_and_sets",
        },
        "quality": report["quality"],
        "release_gates": contract["release_gates"],
    }
    write_json(project_root / SUMMARY_REL, summary)

    artifacts = [
        REPORT_REL,
        SUMMARY_REL,
        ENVELOPE_JSON_REL,
        OPENFOAM_MAP_REL,
        CALCULIX_MAP_REL,
        SVG_REL,
        PNG_REL,
    ] + [Path(path) for path in envelope_csv_paths.values()]
    manifest = {
        "schema_version": "1.0.0",
        "phase": "F47",
        "contract": artifact_record(project_root, CONTRACT_REL),
        "generator": artifact_record(project_root, SOURCE_REL),
        "artifacts": [artifact_record(project_root, rel) for rel in sorted(artifacts)],
    }
    write_json(project_root / MANIFEST_REL, manifest)


def validate_csv(path: Path) -> None:
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        require(reader.fieldnames == envelope_csv_fields(), f"colonnes CSV F47 invalides: {path}")
        rows = list(reader)
    require(len(rows) == 720, f"CSV F47 incomplet: {path}")
    for expected_angle, row in enumerate(rows):
        require(int(row["crank_angle_deg"]) == expected_angle, f"angle CSV invalide: {path}")
        for field in envelope_csv_fields()[2:]:
            finite_float(row[field], f"{path}:{field}")
        for variable in VARIABLES:
            for prefix in ("cantera", "wiebe", "cross_model"):
                low = float(row[f"{prefix}_{variable}_min"])
                high = float(row[f"{prefix}_{variable}_max"])
                require(low <= high, f"bornes inversees: {path}:{field}")
        require(float(row["cross_model_h_gas_w_m2_k_min"]) > 0.0, "h gaz non positif")


def check(project_root: Path) -> None:
    contract = load_json(project_root / CONTRACT_REL)
    validate_contract(contract)
    f46_contract, f46_report, artifact_map = verify_upstream(project_root, contract)
    _, case_index, worst_closure = load_all_cases(
        project_root, contract, f46_contract, f46_report, artifact_map
    )
    require(len(case_index) == 36, "F47 ne reference pas 36 traces")
    require(
        worst_closure <= contract["quality_limits"]["relative_wall_flux_closure_limit"],
        "fermeture h/T/q F47 invalide",
    )

    manifest_path = project_root / MANIFEST_REL
    require(manifest_path.is_file() and not manifest_path.is_symlink(), "manifeste F47 absent")
    manifest = load_json(manifest_path)
    require(manifest.get("phase") == "F47", "manifeste hors F47")
    contract_record = manifest.get("contract", {})
    require(contract_record.get("path") == CONTRACT_REL.as_posix(), "contrat manifeste invalide")
    require(contract_record.get("sha256") == sha256_file(project_root / CONTRACT_REL), "SHA contrat F47 divergent")
    generator_record = manifest.get("generator", {})
    require(generator_record.get("path") == SOURCE_REL.as_posix(), "generateur manifeste invalide")
    require(generator_record.get("sha256") == sha256_file(project_root / SOURCE_REL), "SHA generateur F47 divergent")
    expected_paths = {
        REPORT_REL.as_posix(), SUMMARY_REL.as_posix(), ENVELOPE_JSON_REL.as_posix(),
        OPENFOAM_MAP_REL.as_posix(), CALCULIX_MAP_REL.as_posix(), SVG_REL.as_posix(), PNG_REL.as_posix(),
    }
    expected_paths.update(
        (EVIDENCE_REL / f"envelopes/f47-{arch}-load-envelope.csv").as_posix()
        for arch in ARCHITECTURES
    )
    artifacts = manifest.get("artifacts", [])
    require({item.get("path") for item in artifacts} == expected_paths, "inventaire F47 divergent")
    for item in artifacts:
        path = project_root / item["path"]
        require(path.is_file() and not path.is_symlink(), f"artefact F47 absent: {item['path']}")
        require(path.stat().st_size == item.get("bytes"), f"taille F47 divergente: {item['path']}")
        require(sha256_file(path) == item.get("sha256"), f"SHA F47 divergent: {item['path']}")

    report = load_json(project_root / REPORT_REL)
    summary = load_json(project_root / SUMMARY_REL)
    envelopes = load_json(project_root / ENVELOPE_JSON_REL)
    require(report.get("source_case_count") == summary.get("source_case_count") == 36, "cas F47 incomplets")
    require(summary.get("envelope_rows_total") == 1440, "enveloppes F47 incompletes")
    require(report["quality"].get("physical_correlation_completed") is False, "fausse correlation")
    require(report["conclusion"].get("CFD_or_CHT_or_FEA_executed") is False, "fausse simulation")
    require(all(value is False for value in report["release_gates"].values()), "gate rapport ouverte")
    require(all(value is False for value in summary["release_gates"].values()), "gate resume ouverte")
    require(envelopes["envelope_policy"].get("joint_trajectory_claimed") is False, "fausse trajectoire")
    for arch in ARCHITECTURES:
        rows = envelopes["architectures"][arch]["rows"]
        require(len(rows) == 720, f"JSON enveloppe incomplet: {arch}")
        validate_csv(project_root / (EVIDENCE_REL / f"envelopes/f47-{arch}-load-envelope.csv"))
    for mapping_rel in (OPENFOAM_MAP_REL, CALCULIX_MAP_REL):
        mapping = load_json(project_root / mapping_rel)
        require(mapping.get("execution_claimed") is False, f"execution indue: {mapping_rel}")
        require(mapping.get("geometry_loaded") is False, f"geometrie indue: {mapping_rel}")
        require(all(value is False for value in mapping["release_gates"].values()), f"gate mapping ouverte: {mapping_rel}")
    svg = (project_root / SVG_REL).read_text(encoding="utf-8")
    require("aucune CFD/CHT/FEA" in svg and "Bornes non corrélées" in svg, "limites absentes du SVG")
    require(png_dimensions(project_root / PNG_REL) == (1920, 1080), "dimensions PNG F47 invalides")
    print("F47 CAE load-transfer evidence: OK")


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--check", action="store_true")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    project_root = args.project_root.resolve()
    try:
        if args.check:
            check(project_root)
        else:
            build(project_root)
            check(project_root)
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        print(f"F47 ERROR: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
