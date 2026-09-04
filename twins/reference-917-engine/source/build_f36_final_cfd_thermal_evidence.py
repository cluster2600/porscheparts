#!/usr/bin/env python3
"""Consolide les écrans CFD/thermiques F36 et génère une planche d'évidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
from pathlib import Path

AIR_DENSITY_KG_M3 = 1.06
AIR_CP_J_KG_K = 1007.0
AIR_GAS_CONSTANT_J_KG_K = 287.05
AIR_DYNAMIC_VISCOSITY_PA_S = 1.90e-5
INLET_TEMPERATURE_K = 308.15
OUTLET_PRESSURE_PA = 100000.0
INLET_AREA_M2 = 0.03
TARGET_MASS_FLOW_KG_S = 0.85
WALL_TEMPERATURE_K = 533.15
SERVICE_SCREEN_C = 260.0


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def evidence_record(path: Path, root: Path) -> dict:
    """Describe one exact published input without embedding its contents."""
    return {
        "path": path.relative_to(root).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def copy_openfoam_evidence(source: Path, destination: Path) -> None:
    """Publish only the compact files that are actually consumed by the parser."""
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)
    fixed = (
        Path("case-metadata.json"),
        Path("log.fluid-recovered"),
        Path("log.checkMesh-recovered-default"),
        Path("log.checkMesh-recovered-strict"),
        Path("constant/polyMesh/boundary"),
        Path("constant/momentumTransport"),
        Path("system/fvSolution"),
        Path("system/fvSchemes"),
        Path("system/controlDict"),
    )
    for relative in fixed:
        candidate = source / relative
        if candidate.is_file():
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(candidate, target)
    for pattern in ("log.fluid*", "driver*.log"):
        for candidate in sorted(source.glob(pattern)):
            if candidate.is_file():
                shutil.copy2(candidate, destination / candidate.name)
    functions = {
        "outletMassFlow": "surfaceFieldValue.dat",
        "weightedOutletTemperature": "surfaceFieldValue.dat",
        "inletPressure": "surfaceFieldValue.dat",
        "outletTotalEnergyTerms": "surfaceFieldValue.dat",
        "headHeatFlux": "wallHeatFlux.dat",
    }
    for function_name, filename in functions.items():
        for candidate in sorted((source / "postProcessing" / function_name).glob(f"*/{filename}")):
            relative = candidate.relative_to(source)
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(candidate, target)


def relative_difference(a: float, b: float) -> float:
    return abs(a - b) / max(abs(b), 1.0e-12)


def last_rows(path: Path) -> tuple[list[str] | None, list[str] | None]:
    if not path.is_file():
        return None, None
    rows = [
        line.split()
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not rows:
        return None, None
    return rows[-1], rows[-2] if len(rows) > 1 else None


def function_selection(root: Path, function_name: str, filename: str) -> dict:
    """Select restart rows deterministically and retain exact row provenance."""
    records = []
    paths = sorted((root / function_name).glob(f"*/{filename}"), key=lambda path: path.as_posix())
    for path in paths:
        try:
            restart_time = float(path.parent.name)
        except ValueError:
            restart_time = -math.inf
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(),
            start=1,
        ):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            row = line.split()
            records.append(
                {
                    "time": float(row[0]),
                    "restart_time": restart_time,
                    "path": path,
                    "line_number": line_number,
                    "row": row,
                }
            )
    by_time = {}
    for record in records:
        time = record["time"]
        previous = by_time.get(time)
        if previous is None or (
            record["restart_time"], record["path"].as_posix(), record["line_number"]
        ) > (
            previous["restart_time"], previous["path"].as_posix(), previous["line_number"]
        ):
            by_time[time] = record
    deduplicated = [by_time[time] for time in sorted(by_time)]
    return {
        "latest": deduplicated[-1] if deduplicated else None,
        "previous": deduplicated[-2] if len(deduplicated) > 1 else None,
        "candidate_files": paths,
        "duplicate_time_rows_removed": len(records) - len(deduplicated),
    }


def function_rows(root: Path, function_name: str, filename: str) -> tuple[list[str] | None, list[str] | None]:
    """Compatibility wrapper returning the two deterministic selected rows."""
    selection = function_selection(root, function_name, filename)
    latest = selection["latest"]
    previous = selection["previous"]
    return (
        latest["row"] if latest else None,
        previous["row"] if previous else None,
    )


def parse_openfoam(case: Path, manifest_root: Path | None = None) -> dict:
    manifest_root = manifest_root or case
    metadata_path = case / "case-metadata.json"
    metadata = load(metadata_path) if metadata_path.is_file() else {}
    inlet_area_m2 = float(metadata.get("inlet_cross_section_m2", INLET_AREA_M2))
    target_mass_flow = float(metadata.get("target_mass_flow_kg_s", TARGET_MASS_FLOW_KG_S))
    fluid_log = case / "log.fluid-recovered"
    check_log = case / "log.checkMesh-recovered-default"
    strict_log = case / "log.checkMesh-recovered-strict"
    boundary = case / "constant/polyMesh/boundary"
    solution = case / "system/fvSolution"
    fluid_text = fluid_log.read_text(encoding="utf-8", errors="replace") if fluid_log.is_file() else ""
    check_text = check_log.read_text(encoding="utf-8", errors="replace") if check_log.is_file() else ""
    strict_text = strict_log.read_text(encoding="utf-8", errors="replace") if strict_log.is_file() else ""
    boundary_text = boundary.read_text(encoding="utf-8", errors="replace") if boundary.is_file() else ""
    solution_text = solution.read_text(encoding="utf-8", errors="replace") if solution.is_file() else ""
    relaxation_text = solution_text.partition("relaxationFactors")[2]
    head_match = re.search(r"\bhead\s*\{.*?nFaces\s+(\d+);", boundary_text, re.DOTALL)
    cells_match = re.search(r"^\s*cells:\s+(\d+)", check_text, re.MULTILINE)
    strict_failed = re.search(r"Failed\s+(\d+)\s+mesh checks", strict_text)
    duplicate_faces = re.search(r"Number of duplicate \(not baffle\) faces found:\s*(\d+)", strict_text)
    nonconsecutive_faces = re.search(r"Number of faces with non-consecutive shared points:\s*(\d+)", strict_text)
    small_determinant_cells = re.search(r"Cells with small determinant \(< 0\.001\) found, number of cells:\s*(\d+)", strict_text)
    concave_cells = re.search(r"Concave cells \(using face planes\) found, number of cells:\s*(\d+)", strict_text)

    root = case / "postProcessing"
    function_files = {
        "outlet_mass_flow": ("outletMassFlow", "surfaceFieldValue.dat"),
        "weighted_outlet_temperature": ("weightedOutletTemperature", "surfaceFieldValue.dat"),
        "inlet_pressure": ("inletPressure", "surfaceFieldValue.dat"),
        "outlet_total_energy_terms": ("outletTotalEnergyTerms", "surfaceFieldValue.dat"),
        "head_heat_flux": ("headHeatFlux", "wallHeatFlux.dat"),
    }
    selections = {
        key: function_selection(root, function_name, filename)
        for key, (function_name, filename) in function_files.items()
    }
    rows = {
        key: (
            selection["latest"]["row"] if selection["latest"] else None,
            selection["previous"]["row"] if selection["previous"] else None,
        )
        for key, selection in selections.items()
    }
    mass, _ = rows["outlet_mass_flow"]
    temperature, _ = rows["weighted_outlet_temperature"]
    pressure, _ = rows["inlet_pressure"]
    energy, _ = rows["outlet_total_energy_terms"]
    heat, heat_previous = rows["head_heat_flux"]
    fixed_evidence = {
        key: evidence_record(path, manifest_root)
        for key, path in {
            "case_metadata": metadata_path,
            "fluid_log": fluid_log,
            "mesh_check_standard": check_log,
            "mesh_check_strict": strict_log,
            "boundary": boundary,
            "fv_solution": solution,
            "fv_schemes": case / "system/fvSchemes",
            "control_dict": case / "system/controlDict",
            "momentum_transport": case / "constant/momentumTransport",
        }.items()
        if path.is_file()
    }
    numerical_evidence = {}
    for key, selection in selections.items():
        latest = selection["latest"]
        previous = selection["previous"]
        numerical_evidence[key] = {
            "selected": (
                {
                    "row": latest["row"],
                    "line_number": latest["line_number"],
                    "source": evidence_record(latest["path"], manifest_root),
                }
                if latest
                else None
            ),
            "previous": (
                {
                    "row": previous["row"],
                    "line_number": previous["line_number"],
                    "source": evidence_record(previous["path"], manifest_root),
                }
                if previous
                else None
            ),
            "files": [
                evidence_record(path, manifest_root)
                for path in selection["candidate_files"]
            ],
            "duplicate_time_rows_removed": selection["duplicate_time_rows_removed"],
        }
    evidence_complete = all(row is not None for row in (mass, temperature, pressure, energy, heat))
    base = {
        "case_id": case.name,
        "classification": (
            "steady_laminar_lower_bound_fixed_wall_temperature_external_air_not_CHT"
            if metadata.get("turbulence_model") == "laminar"
            else "steady_RANS_fixed_wall_temperature_external_air_not_CHT"
        ),
        "geometry_variant": metadata.get("classification", "unshrouded_external_domain"),
        "shroud_gap_mm": metadata.get("shroud_gap_mm"),
        "base_cell_mm": metadata.get("base_cell_mm"),
        "turbulence_model": metadata.get("turbulence_model", "kOmegaSST"),
        "domain_m": metadata.get("domain_m"),
        "head_patch_faces": int(head_match.group(1)) if head_match else 0,
        "cells": int(cells_match.group(1)) if cells_match else None,
        "solver_completed": "\nEnd\n" in f"\n{fluid_text}\n",
        "standard_mesh_check_passed": "Mesh OK." in check_text,
        "strict_mesh_check_passed": bool(strict_text)
        and strict_failed is None
        and "Mesh OK." in strict_text,
        "strict_failed_mesh_checks": int(strict_failed.group(1)) if strict_failed else 0,
        "strict_mesh_diagnostics": {
            "duplicate_faces": int(duplicate_faces.group(1)) if duplicate_faces else 0,
            "nonconsecutive_shared_point_faces": int(nonconsecutive_faces.group(1)) if nonconsecutive_faces else 0,
            "small_determinant_cells": int(small_determinant_cells.group(1)) if small_determinant_cells else 0,
            "concave_cells": int(concave_cells.group(1)) if concave_cells else 0,
        },
        "head_heat_flux_rows_present": heat is not None,
        "input_evidence": {
            "fixed_files": fixed_evidence,
            "numerical_selections": numerical_evidence,
            "auxiliary_solver_logs": [
                evidence_record(path, manifest_root)
                for pattern in ("log.fluid*", "driver*.log")
                for path in sorted(case.glob(pattern))
                if path.is_file() and path != fluid_log
            ],
        },
        "solver_configuration": {
            key: float(matches[-1])
            for key, pattern in {
                "p_relaxation": r"\bp\s+([0-9.eE+-]+);",
                "rho_relaxation": r"\brho\s+([0-9.eE+-]+);",
                "U_relaxation": r"\bU\s+([0-9.eE+-]+);",
                "h_relaxation": r"\bh\s+([0-9.eE+-]+);",
                "turbulence_relaxation": r'"\(k\|(?:omega|epsilon)\)"\s+([0-9.eE+-]+);',
            }.items()
            if (matches := re.findall(pattern, relaxation_text))
        },
    }
    if not evidence_complete:
        return {**base, "status": "incomplete_or_rejected"}

    mass_flow = abs(float(mass[1]))
    outlet_temperature = float(temperature[1])
    inlet_pressure = float(pressure[1])
    outlet_velocity_squared = float(energy[2])
    heat_rejection = float(heat[4])
    mean_heat_flux = float(heat[5])
    rho_inlet = inlet_pressure / (AIR_GAS_CONSTANT_J_KG_K * INLET_TEMPERATURE_K)
    inlet_velocity = mass_flow / (rho_inlet * inlet_area_m2)
    domain_m = metadata.get("domain_m") or []
    hydraulic_diameter = (
        2.0 * float(domain_m[1]) * float(domain_m[2]) / (float(domain_m[1]) + float(domain_m[2]))
        if len(domain_m) == 3
        else None
    )
    outlet_energy_gain = mass_flow * (
        AIR_CP_J_KG_K * (outlet_temperature - INLET_TEMPERATURE_K)
        + 0.5 * (outlet_velocity_squared - inlet_velocity * inlet_velocity)
    )
    energy_error = relative_difference(outlet_energy_gain, heat_rejection)
    heat_change = (
        relative_difference(heat_rejection, float(heat_previous[4]))
        if heat_previous is not None
        else None
    )
    checks = {
        "geometry_patch_present": base["head_patch_faces"] > 0,
        "solver_completed": base["solver_completed"],
        "standard_mesh_check_passed": base["standard_mesh_check_passed"],
        "mass_flow_within_1_percent": relative_difference(mass_flow, target_mass_flow) <= 0.01,
        "energy_balance_within_5_percent": energy_error <= 0.05,
        "last_heat_change_within_2_percent": heat_change is not None and heat_change <= 0.02,
        "outlet_temperature_bounded": INLET_TEMPERATURE_K <= outlet_temperature <= WALL_TEMPERATURE_K,
    }
    return {
        **base,
        "status": "completed_geometry_resolved_screen" if all(checks.values()) else "completed_with_failed_checks",
        "results": {
            "mass_flow_kg_s": mass_flow,
            "outlet_temperature_k": outlet_temperature,
            "wall_heat_rejection_w": heat_rejection,
            "mean_wall_heat_flux_w_m2": mean_heat_flux,
            "head_patch_area_from_integrated_flux_m2": heat_rejection / mean_heat_flux,
            "effective_h_w_m2k": mean_heat_flux / (WALL_TEMPERATURE_K - INLET_TEMPERATURE_K),
            "pressure_drop_pa": inlet_pressure - OUTLET_PRESSURE_PA,
            "inlet_cross_section_m2": inlet_area_m2,
            "inlet_bulk_velocity_m_s": inlet_velocity,
            "hydraulic_diameter_full_rectangle_m": hydraulic_diameter,
            "bulk_reynolds_full_rectangle": (
                rho_inlet * inlet_velocity * hydraulic_diameter / AIR_DYNAMIC_VISCOSITY_PA_S
                if hydraulic_diameter is not None
                else None
            ),
            "ideal_air_power_w": (inlet_pressure - OUTLET_PRESSURE_PA) * mass_flow / rho_inlet,
            "outlet_total_energy_gain_w": outlet_energy_gain,
            "relative_energy_balance_error": energy_error,
            "last_heat_relative_change": heat_change,
        },
        "checks": checks,
    }


def fluidx_case(path: Path) -> dict:
    payload = load(path)
    return {
        "case_id": path.stem,
        "source_sha256": sha256(path),
        "grid": payload["grid"],
        "cell_size_mm": payload["cell_size_mm"],
        "mass_flow_kg_s": payload["mass_flow_kg_s"],
        "heat_rejection_w": payload["heat_rejection_w"],
        "effective_h_w_m2k": payload["effective_h_w_m2k"],
        "pressure_drop_from_drag_pa": payload["pressure_drop_from_drag_pa"],
        "velocity_m_s": payload["velocity_m_s"],
        "temporal_convergence_relative": payload["convergence_relative_two_half_means"],
        "converged": payload["converged"],
        "numerically_stable": payload["numerically_stable"],
        "classification": payload["classification"],
    }


def thermal_case(path: Path) -> dict:
    payload = load(path)
    return {
        "case_id": path.parent.name,
        "source_sha256": sha256(path),
        "pitch_mm": payload["mesh"]["pitch_mm_if_obj_unit_is_mm"],
        "hexahedra": payload["mesh"]["hexahedra"],
        "chamber_flux_w_mm2": payload["boundary_conditions"]["chamber_flux_w_mm2"],
        "external_h_w_m2k": payload["boundary_conditions"]["external_air"]["h_w_mm2k"] * 1.0e6,
        "conductivity_scale": payload["material"].get("conductivity_scale", 1.0),
        "maximum_temperature_c": payload["results"]["maximum_temperature_c"],
        "p95_temperature_c": payload["results"]["p95_temperature_c"],
        "screen_below_260_c": payload["engineering_gates"]["maximum_below_260_c_service_screen"],
        "material_card_qualified": payload["engineering_gates"]["thermal_material_card_qualified"],
        "classification": payload["classification"],
    }


def render(report: dict, output: Path) -> None:
    # Le parseur et les contrôles de preuve restent utilisables sans la
    # dépendance graphique ; le rendu l'importe seulement lorsqu'il est demandé.
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.style.use("dark_background")
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.subplots_adjust(left=0.06, right=0.98, top=0.91, bottom=0.10, hspace=0.28, wspace=0.20)
    fig.patch.set_facecolor("#08131c")
    fig.suptitle(
        "Porsche 917 — culasse F36 · recoupement CFD / thermique final",
        fontsize=18,
        fontweight="bold",
        y=0.975,
    )

    ax = axes[0, 0]
    grid = report["fluidx3d"]["grid_series"]
    x = [item["cell_size_mm"] for item in grid]
    heat = [item["heat_rejection_w"] / 1000.0 for item in grid]
    pressure = [item["pressure_drop_from_drag_pa"] / 1000.0 for item in grid]
    ax.plot(x, heat, "o-", color="#ffb000", linewidth=2.5, label="Chaleur rejetée [kW]")
    ax.set_xlabel("Pas LBM [mm] (fin → gauche)")
    ax.set_ylabel("Chaleur [kW]", color="#ffb000")
    ax.invert_xaxis()
    ax.grid(alpha=0.2)
    ax2 = ax.twinx()
    ax2.plot(x, pressure, "s--", color="#45caff", linewidth=2, label="Δp [kPa]")
    ax2.set_ylabel("Δp [kPa]", color="#45caff")
    ax.set_title("FluidX3D : convergence spatiale non acquise")
    for item in grid:
        ax.annotate(f"{item['effective_h_w_m2k']:.0f} W/m²K", (item["cell_size_mm"], item["heat_rejection_w"] / 1000.0), xytext=(0, 8), textcoords="offset points", ha="center", fontsize=8)

    ax = axes[0, 1]
    shrouds = report["fluidx3d"]["shroud_sweep"]
    for item in shrouds:
        feasible = item["pressure_drop_from_drag_pa"] <= 10000.0 and item["effective_h_w_m2k"] >= 800.0
        color = "#4ade80" if feasible else "#fb7185"
        ax.scatter(item["pressure_drop_from_drag_pa"] / 1000.0, item["effective_h_w_m2k"], s=75, color=color)
        gap = re.search(r"gap(\d+)", item["case_id"])
        ax.annotate(f"{gap.group(1) if gap else '?'} mm", (item["pressure_drop_from_drag_pa"] / 1000.0, item["effective_h_w_m2k"]), xytext=(5, 5), textcoords="offset points", fontsize=8)
    ax.axvline(10.0, color="#fb7185", linestyle="--", linewidth=1)
    ax.axhline(800.0, color="#facc15", linestyle="--", linewidth=1)
    ax.set_xlim(-1.0, 52.0)
    ax.set_xlabel("Δp estimée par traînée [kPa]")
    ax.set_ylabel("h effectif écran [W/m²K]")
    ax.set_title("Balayage LBM : candidat 20 mm non validé")
    ax.grid(alpha=0.2)

    ax = axes[1, 0]
    h_sweep = report["solid_conduction"]["h_sweep"]
    hx = [item["external_h_w_m2k"] for item in h_sweep]
    max_t = [item["maximum_temperature_c"] for item in h_sweep]
    p95_t = [item["p95_temperature_c"] for item in h_sweep]
    ax.plot(hx, max_t, "o-", color="#ff7a59", linewidth=2.5, label="T max")
    ax.plot(hx, p95_t, "s--", color="#c084fc", linewidth=2, label="T p95")
    ax.axhline(SERVICE_SCREEN_C, color="#facc15", linestyle="--", label="écran 260 °C")
    linked = report["solid_conduction"]["fluidx_linked_case"]
    ax.scatter([linked["external_h_w_m2k"]], [linked["maximum_temperature_c"]], s=150, facecolors="none", edgecolors="#4ade80", linewidths=2.5, label="LBM gap 20 mm")
    ax.set_xlabel("h imposé [W/m²K]")
    ax.set_ylabel("Température [°C]")
    ax.set_title("CalculiX conduction : flux moyen 0,45 W/mm²")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.2)

    ax = axes[1, 1]
    ax.axis("off")
    checks = report["decision"]["proof_matrix"]
    lines = ["MATRICE DE PREUVE"]
    displayed_checks = (
        "LBM temporal convergence",
        "LBM spatial convergence",
        "OpenFOAM geometry-resolved completion",
        "OpenFOAM accepted-case run checks",
        "OpenFOAM strict mesh check",
        "OpenFOAM RANS shroud two-grid agreement",
        "OpenFOAM shroud reaches h 800",
        "OpenFOAM-shroud-linked thermal screen",
        "thermal mesh change below 5 percent",
        "minus-20-percent conductivity screen",
        "qualified hot material card",
        "full conjugate heat transfer",
        "physical thermal correlation",
    )
    for label in displayed_checks:
        value = checks[label]
        glyph = "PASS" if value else "BLOQUÉ"
        lines.append(f"{glyph:7s}  {label}")
    lines.extend(
        [
            "",
            f"LBM fin→ultra : ΔQ={report['fluidx3d']['grid_comparison']['fine_to_ultra_heat_relative']*100:.1f}% ; Δp={report['fluidx3d']['grid_comparison']['fine_to_ultra_pressure_relative']*100:.1f}%",
            f"Gap 20 mm : h={linked['external_h_w_m2k']:.0f} W/m²K ; T max={linked['maximum_temperature_c']:.1f} °C",
            f"k à 80 % : T max={report['solid_conduction']['conductivity_sensitivity']['k0p8_maximum_temperature_c']:.1f} °C → échec",
        ]
    )
    comparison = report.get("cross_solver_comparison")
    if comparison:
        lines.extend(
            [
                f"OpenFOAM : Q={comparison['openfoam_heat_rejection_w']/1000:.2f} kW ; h={comparison['openfoam_effective_h_w_m2k']:.1f} W/m²K",
                f"Écart LBM/OpenFOAM : Q={comparison['heat_relative_difference']*100:.1f}% ; Δp={comparison['pressure_relative_difference']*100:.1f}%",
            ]
        )
    openfoam_linked = report["solid_conduction"].get("openfoam_linked_case")
    if openfoam_linked:
        lines.append(
            f"Solide lié OpenFOAM : T max={openfoam_linked['maximum_temperature_c']:.1f} °C → "
            f"{'PASS' if openfoam_linked['screen_below_260_c'] else 'ÉCHEC'}"
        )
    closure = report["decision"].get("cooling_closure")
    if closure:
        best = closure["best_rans_rejected_observation"]
        lines.extend(
            [
                f"OF carénage 20 mm, RANS rejeté : h={best['effective_h_w_m2k']:.1f} ; Δp={best['pressure_drop_pa']/1000:.2f} kPa",
                f"Bilan énergie OF : erreur={best['energy_error_relative']*100:.1f}% → REJET",
                f"Solide lié au meilleur OF : T max={best['linked_maximum_temperature_c']:.1f} °C → ÉCHEC",
                f"Mailles RANS : Δh={closure['rans_two_grid_effective_h_relative']*100:.1f}% → non convergé",
            ]
        )
    blocked_shroud = next(
        (
            item
            for item in report["openfoam"].get("attempt_log", [])
            if item.get("case_id", "").startswith("shroud-") and item.get("status") != "completed"
        ),
        None,
    )
    if blocked_shroud:
        lines.append("OF carénage 10 mm : solveur BLOQUÉ à t=6 s (omegaWallFunction).")
    lines.append("Conclusion : refroidissement NON fermé; pas CHT ni autorisation d'impression.")
    ax.text(0.02, 0.96, "\n".join(lines), va="top", ha="left", family="monospace", fontsize=8.4, linespacing=1.15)
    ax.set_title("Décision d'ingénierie", loc="left")

    fig.text(
        0.5,
        0.02,
        "OpenFOAM et FluidX3D : paroi isotherme, air externe. CalculiX : conduction stationnaire avec flux/films hypothétiques. Échelle du scan, carte matériau à chaud et corrélation physique non acquises.",
        ha="center",
        fontsize=9,
        color="#b8c7d1",
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180, facecolor=fig.get_facecolor())
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--openfoam-case", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    fluidx_root = args.raw / "fluidx3d"
    grid_names = ["coarse-96x54x40.json", "medium-192x107x80.json", "fine-288x160x120.json", "ultra-384x213x160.json"]
    grid = [fluidx_case(fluidx_root / name) for name in grid_names]
    shroud_paths = sorted(
        path
        for path in fluidx_root.glob("shroud-gap*-384.json")
        if "alpha" not in path.name and "flow" not in path.name
    )
    shrouds = [fluidx_case(path) for path in shroud_paths]
    shrouds.sort(key=lambda item: int(re.search(r"gap(\d+)", item["case_id"]).group(1)))
    gap20 = next(item for item in shrouds if item["case_id"] == "shroud-gap20-384")
    closure_sensitivity = [
        fluidx_case(fluidx_root / "shroud-gap20-alpha0p006-384.json"),
        fluidx_case(fluidx_root / "shroud-gap20-alpha0p020-384.json"),
    ]
    flow_sweep = [
        gap20,
        fluidx_case(fluidx_root / "shroud-gap20-flow1p20-384.json"),
        fluidx_case(fluidx_root / "shroud-gap20-flow1p40-384.json"),
    ]

    h_names = [
        "selected-q0p45-h800-p2p5",
        "selected-q0p45-h900-p2p5",
        "selected-q0p45-h1000-p2p5",
        "selected-q0p45-h1108-p2p5",
        "selected-q0p45-h1181-p2p5",
    ]
    h_sweep = [thermal_case(args.raw / "thermal" / name / "report.json") for name in h_names]
    linked = next(item for item in h_sweep if math.isclose(item["external_h_w_m2k"], gap20["effective_h_w_m2k"], rel_tol=1.0e-5))
    openfoam_linked_path = args.raw / "thermal/openfoam-coarse-h81p55-p2p5/report.json"
    openfoam_linked = thermal_case(openfoam_linked_path) if openfoam_linked_path.is_file() else None
    openfoam_shroud_linked = [
        thermal_case(path)
        for path in sorted((args.raw / "thermal").glob("openfoam-shroud-*/report.json"))
    ]
    k0p8 = thermal_case(args.raw / "thermal/selected-k0p8/report.json")
    k1p2 = thermal_case(args.raw / "thermal/selected-k1p2/report.json")
    mesh_p3 = thermal_case(args.raw / "thermal/selected-p3/report.json")
    mesh_p2p5 = thermal_case(args.raw / "thermal/selected-p2p5/report.json")
    attempt_path = args.raw / "openfoam/campaign-attempts.json"
    attempt_log = load(attempt_path).get("attempts", []) if attempt_path.is_file() else []
    published_case_root = args.output / "openfoam-runs"
    published_cases = []
    for source_case in args.openfoam_case:
        published_case = published_case_root / source_case.name
        copy_openfoam_evidence(source_case, published_case)
        published_cases.append(published_case)
    openfoam = [parse_openfoam(case, args.output) for case in published_cases]
    completed_openfoam = [
        item
        for item in openfoam
        if item.get("status") in {"completed_geometry_resolved_screen", "completed_with_failed_checks"}
        and item.get("head_patch_faces", 0) > 0
        and item.get("solver_completed")
        and item.get("head_heat_flux_rows_present")
    ]
    completed_openfoam.sort(key=lambda item: item.get("cells") or 0)
    baseline_openfoam = [item for item in completed_openfoam if item.get("shroud_gap_mm") is None]
    shroud_openfoam = [item for item in completed_openfoam if item.get("shroud_gap_mm") is not None]

    fine, ultra = grid[-2:]
    grid_comparison = {
        "fine_to_ultra_heat_relative": relative_difference(ultra["heat_rejection_w"], fine["heat_rejection_w"]),
        "fine_to_ultra_pressure_relative": relative_difference(ultra["pressure_drop_from_drag_pa"], fine["pressure_drop_from_drag_pa"]),
        "fine_to_ultra_mass_flow_relative": relative_difference(ultra["mass_flow_kg_s"], fine["mass_flow_kg_s"]),
        "grid_independence_5_percent": False,
    }
    thermal_mesh = {
        "p3_to_p2p5_maximum_temperature_relative": relative_difference(mesh_p2p5["maximum_temperature_c"], mesh_p3["maximum_temperature_c"]),
        "p3_to_p2p5_p95_temperature_relative": relative_difference(mesh_p2p5["p95_temperature_c"], mesh_p3["p95_temperature_c"]),
    }
    cross_solver = None
    openfoam_grid = None
    shroud_grid_comparisons = []
    if len(baseline_openfoam) >= 2:
        previous, current = baseline_openfoam[-2:]
        openfoam_grid = {
            "last_two_heat_relative": relative_difference(
                current["results"]["wall_heat_rejection_w"],
                previous["results"]["wall_heat_rejection_w"],
            ),
            "last_two_pressure_relative": relative_difference(
                current["results"]["pressure_drop_pa"],
                previous["results"]["pressure_drop_pa"],
            ),
        }
    if baseline_openfoam:
        of_case = baseline_openfoam[-1]
        cross_solver = {
            "openfoam_case_id": of_case["case_id"],
            "fluidx_case_id": "ultra-flow-tuned-384x213x160",
            "classification": "nominal_boundary_cross_check_with_different_turbulence_and_pressure_estimators",
            "heat_relative_difference": relative_difference(
                load(fluidx_root / "ultra-flow-tuned-384x213x160.json")["heat_rejection_w"],
                of_case["results"]["wall_heat_rejection_w"],
            ),
            "pressure_relative_difference": relative_difference(
                load(fluidx_root / "ultra-flow-tuned-384x213x160.json")["pressure_drop_from_drag_pa"],
                of_case["results"]["pressure_drop_pa"],
            ),
            "openfoam_heat_rejection_w": of_case["results"]["wall_heat_rejection_w"],
            "openfoam_effective_h_w_m2k": of_case["results"]["effective_h_w_m2k"],
            "agreement_is_validation": False,
        }

    shroud_groups: dict[tuple, list[dict]] = {}
    for item in shroud_openfoam:
        key = (
            item.get("shroud_gap_mm"),
            item.get("turbulence_model"),
            tuple(item.get("domain_m") or []),
        )
        shroud_groups.setdefault(key, []).append(item)
    for (gap_mm, turbulence_model, domain_m), group in shroud_groups.items():
        if len(group) < 2:
            continue
        previous, current = sorted(group, key=lambda item: item.get("cells") or 0)[-2:]
        comparison = {
            "shroud_gap_mm": gap_mm,
            "turbulence_model": turbulence_model,
            "domain_m": list(domain_m),
            "coarse_case_id": previous["case_id"],
            "fine_case_id": current["case_id"],
            "heat_relative": relative_difference(
                current["results"]["wall_heat_rejection_w"],
                previous["results"]["wall_heat_rejection_w"],
            ),
            "effective_h_relative": relative_difference(
                current["results"]["effective_h_w_m2k"],
                previous["results"]["effective_h_w_m2k"],
            ),
            "pressure_relative": relative_difference(
                current["results"]["pressure_drop_pa"],
                previous["results"]["pressure_drop_pa"],
            ),
            "mass_flow_relative": relative_difference(
                current["results"]["mass_flow_kg_s"],
                previous["results"]["mass_flow_kg_s"],
            ),
        }
        comparison["agreement_within_5_percent"] = max(
            comparison["heat_relative"],
            comparison["pressure_relative"],
            comparison["mass_flow_relative"],
        ) <= 0.05
        comparison["both_cases_pass_run_checks"] = all(
            item["status"] == "completed_geometry_resolved_screen" for item in (previous, current)
        )
        comparison["physically_applicable_turbulence_model"] = turbulence_model != "laminar"
        shroud_grid_comparisons.append(comparison)

    openfoam_grid_established = (
        len(baseline_openfoam) >= 3
        and openfoam_grid is not None
        and max(openfoam_grid.values()) <= 0.05
    )
    rans_shroud = [item for item in shroud_openfoam if item.get("turbulence_model") != "laminar"]
    rans_grid = next(
        (
            item
            for item in shroud_grid_comparisons
            if item["physically_applicable_turbulence_model"]
        ),
        None,
    )
    cooling_closure = None
    if rans_shroud and openfoam_shroud_linked:
        best_rans = max(rans_shroud, key=lambda item: item["results"]["effective_h_w_m2k"])
        best_linked = min(
            openfoam_shroud_linked,
            key=lambda item: abs(
                item["external_h_w_m2k"] - best_rans["results"]["effective_h_w_m2k"]
            ),
        )
        cooling_closure = {
            "required_h_w_m2k": 800.0,
            "service_screen_c": SERVICE_SCREEN_C,
            "best_rans_rejected_observation": {
                "case_id": best_rans["case_id"],
                "status": best_rans["status"],
                "effective_h_w_m2k": best_rans["results"]["effective_h_w_m2k"],
                "pressure_drop_pa": best_rans["results"]["pressure_drop_pa"],
                "ideal_air_power_w": best_rans["results"]["ideal_air_power_w"],
                "bulk_reynolds_full_rectangle": best_rans["results"]["bulk_reynolds_full_rectangle"],
                "energy_error_relative": best_rans["results"]["relative_energy_balance_error"],
                "linked_case_id": best_linked["case_id"],
                "linked_maximum_temperature_c": best_linked["maximum_temperature_c"],
            },
            "indicative_h_shortfall_relative": 1.0 - best_rans["results"]["effective_h_w_m2k"] / 800.0,
            "rans_two_grid_effective_h_relative": (
                rans_grid["effective_h_relative"] if rans_grid is not None else None
            ),
            "rans_two_grid_agreement": bool(rans_grid and rans_grid["agreement_within_5_percent"]),
            "airflow_model_physically_acceptable": False,
            "linked_solid_screen_passed": best_linked["screen_below_260_c"],
            "cooling_closed": False,
            "reason": "RANS shroud runs fail energy conservation and grid agreement; linked conduction remains above 260 C.",
        }

    report = {
        "schema_version": "1.0.0",
        "phase": "F36",
        "status": "cross_solver_virtual_screen_complete_release_blocked",
        "classification": "external_air_CFD_and_solid_conduction_cross_screen_not_CHT_not_physical_validation",
        "boundary_alignment": {
            "nominal_mass_flow_kg_s": TARGET_MASS_FLOW_KG_S,
            "inlet_temperature_k": INLET_TEMPERATURE_K,
            "wall_temperature_k": WALL_TEMPERATURE_K,
            "note": "FluidX3D ultra-flow-tuned atteint 0.8555 kg/s; OpenFOAM impose 0.85 kg/s.",
        },
        "fluidx3d": {
            "classification": "D3Q19_TRT_FP32_fixed_wall_temperature_with_constant_effective_diffusivity",
            "grid_series": grid,
            "grid_comparison": grid_comparison,
            "shroud_sweep": shrouds,
            "selected_shroud": {
                **gap20,
                "estimated_air_power_w": gap20["pressure_drop_from_drag_pa"] * gap20["mass_flow_kg_s"] / AIR_DENSITY_KG_M3,
                "classification": "LBM_screening_candidate_not_selected_for_release",
                "selection_basis": "LBM-only candidate: highest effective h among sampled cases satisfying h>=800 W/m2K and drag-derived pressure drop<=10 kPa",
                "same_shroud_cross_solver_validation": False,
            },
            "constant_effective_diffusivity_sensitivity": {
                "cases": closure_sensitivity,
                "effective_h_span_relative_to_selected": (
                    max(item["effective_h_w_m2k"] for item in closure_sensitivity)
                    - min(item["effective_h_w_m2k"] for item in closure_sensitivity)
                )
                / gap20["effective_h_w_m2k"],
            },
            "gap20_flow_sweep": flow_sweep,
            "closure_is_calibrated": False,
        },
        "openfoam": {
            "classification": "steady_compressible_RANS_plus_nonphysical_laminar_diagnostics_external_air_fixed_wall_temperature",
            "attempt_log": attempt_log,
            "cases": openfoam,
            "geometry_resolved_completed_case_count": len(completed_openfoam),
            "baseline_completed_case_count": len(baseline_openfoam),
            "shroud_completed_case_count": len(shroud_openfoam),
            "shroud_improvement_cases": shroud_openfoam,
            "shroud_grid_comparisons": shroud_grid_comparisons,
            "grid_comparison": openfoam_grid,
            "grid_independence_established": openfoam_grid_established,
            "rejected_empty_box_run_is_evidence": False,
        },
        "cross_solver_comparison": cross_solver,
        "solid_conduction": {
            "classification": "CalculiX_steady_conduction_with_mean_chamber_flux_and_film_hypotheses",
            "h_sweep": h_sweep,
            "minimum_sampled_passing_h_w_m2k": min(item["external_h_w_m2k"] for item in h_sweep if item["screen_below_260_c"]),
            "fluidx_linked_case": linked,
            "openfoam_linked_case": openfoam_linked,
            "openfoam_shroud_linked_cases": openfoam_shroud_linked,
            "linked_temperature_margin_to_260_c": SERVICE_SCREEN_C - linked["maximum_temperature_c"],
            "mesh_comparison": thermal_mesh,
            "conductivity_sensitivity": {
                "k0p8_maximum_temperature_c": k0p8["maximum_temperature_c"],
                "k0p8_screen_passed": k0p8["screen_below_260_c"],
                "k1p2_maximum_temperature_c": k1p2["maximum_temperature_c"],
                "k1p2_screen_passed": k1p2["screen_below_260_c"],
                "note": "sensibilité calculée sur le maillage 4 mm, pas une carte coupon qualifiée",
            },
            "temperature_field_from_CHT": False,
        },
        "decision": {
            "selected_virtual_cooling_layout": None,
            "candidate_virtual_cooling_layout": "shroud_gap_20_mm_LBM_screen_only",
            "selection_blocker": "20 mm OpenFOAM RANS shroud runs fail energy conservation and two-grid agreement; the LBM grid study is also not spatially converged",
            "cooling_closure": cooling_closure,
            "proof_matrix": {
                "LBM temporal convergence": all(item["converged"] and item["numerically_stable"] for item in grid),
                "LBM spatial convergence": grid_comparison["grid_independence_5_percent"],
                "OpenFOAM geometry-resolved completion": bool(baseline_openfoam),
                "OpenFOAM accepted-case run checks": bool(completed_openfoam)
                and all(item["status"] == "completed_geometry_resolved_screen" for item in completed_openfoam),
                "OpenFOAM attempted cases completed": bool(openfoam)
                and all(item["status"] == "completed_geometry_resolved_screen" for item in openfoam),
                "OpenFOAM strict mesh check": bool(completed_openfoam)
                and all(item["strict_mesh_check_passed"] for item in completed_openfoam),
                "OpenFOAM three-grid convergence": openfoam_grid_established,
                "OpenFOAM shroud reaches h 800": bool(shroud_openfoam)
                and max(item["results"]["effective_h_w_m2k"] for item in shroud_openfoam) >= 800.0,
                "OpenFOAM RANS shroud two-grid agreement": any(
                    item["physically_applicable_turbulence_model"]
                    and item["agreement_within_5_percent"]
                    and item["both_cases_pass_run_checks"]
                    for item in shroud_grid_comparisons
                ),
                "OpenFOAM laminar-bound two-grid agreement": any(
                    not item["physically_applicable_turbulence_model"]
                    and item["agreement_within_5_percent"]
                    and item["both_cases_pass_run_checks"]
                    for item in shroud_grid_comparisons
                ),
                "LBM-linked nominal thermal screen": linked["screen_below_260_c"],
                "OpenFOAM-linked thermal screen": bool(openfoam_linked)
                and openfoam_linked["screen_below_260_c"],
                "OpenFOAM-shroud-linked thermal screen": bool(openfoam_shroud_linked)
                and all(item["screen_below_260_c"] for item in openfoam_shroud_linked),
                "thermal mesh change below 5 percent": max(thermal_mesh.values()) <= 0.05,
                "minus-20-percent conductivity screen": k0p8["screen_below_260_c"],
                "qualified hot material card": False,
                "full conjugate heat transfer": False,
                "physical thermal correlation": False,
            },
            "metal_print_authorized": False,
            "engine_start_authorized": False,
            "manufacturing_release_reason": "blocked by unconfirmed scan scale, unqualified hot material card, missing CHT/thermomechanical fatigue, CT/NDT and physical correlation",
        },
    }
    report_path = args.output / "cross-solver-report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    run_manifest_path = args.output / "openfoam-run-manifest.json"
    run_manifest = {
        "schema_version": "1.0.0",
        "classification": "compact_published_evidence_for_all_requested_openfoam_runs",
        "runs": [
            {
                "case_id": item["case_id"],
                "status": item["status"],
                "classification": item["classification"],
                "input_evidence": item["input_evidence"],
            }
            for item in openfoam
        ],
    }
    run_manifest_path.write_text(
        json.dumps(run_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    figure_path = args.output / "917-head-f36-final-cfd-thermal.png"
    render(report, figure_path)
    bundle_manifest_path = args.output / "bundle-manifest.json"
    compact_run_files = sorted(
        path for path in published_case_root.rglob("*") if path.is_file()
    )
    bundle_manifest = {
        "schema_version": "1.0.0",
        "classification": "published_bundle_integrity_manifest",
        "artifacts": [
            evidence_record(path, args.output)
            for path in (report_path, run_manifest_path, figure_path, *compact_run_files)
        ],
    }
    bundle_manifest["artifact_count"] = len(bundle_manifest["artifacts"])
    bundle_manifest_path.write_text(
        json.dumps(bundle_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": report["status"], "report": str(report_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
