#!/usr/bin/env python3
"""Convertit, contrôle et exécute les écrans OpenFOAM F49 préparés.

Ce runner doit être appelé dans l'image F47. Un échec de checkMesh est conservé
dans la preuve; le solveur peut encore être lancé pour documenter son comportement,
mais aucun gate de solution ne peut passer avec un gate maillage rouge.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import time
from pathlib import Path


PATCHES = ("intake", "exhaust", "valve", "chamber", "deck", "bore", "walls")
CP_AIR_J_KG_K = 1005.0
OPENFOAM_TSTD_K = 298.15


def assert_openfoam_environment() -> dict:
    project_dir = os.environ.get("WM_PROJECT_DIR")
    foam_etc_file = shutil.which("foamEtcFile")
    if not project_dir or not Path(project_dir).is_dir() or foam_etc_file is None:
        raise RuntimeError("openfoam_environment_not_sourced")
    completed = subprocess.run(
        [foam_etc_file, "configDict"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    config_path = completed.stdout.strip()
    if completed.returncode != 0 or not config_path or not Path(config_path).is_file():
        raise RuntimeError("openfoam_configDict_not_resolved")
    return {
        "WM_PROJECT_DIR": project_dir,
        "foamEtcFile": foam_etc_file,
        "configDict": config_path,
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(command: list[str], log_path: Path, cwd: Path) -> dict:
    started = time.monotonic()
    with log_path.open("w", encoding="utf-8") as log:
        completed = subprocess.run(command, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, text=True, check=False)
    return {
        "command": command,
        "return_code": completed.returncode,
        "elapsed_s": round(time.monotonic() - started, 6),
        "log": log_path.name,
        "log_sha256": sha256(log_path),
    }


def replace_patch_types(boundary_path: Path, wall_patches: list[str]) -> None:
    lines = boundary_path.read_text(encoding="utf-8").splitlines()
    current = None
    depth = 0
    seen = set()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if current is None and stripped in PATCHES:
            current = stripped
            depth = 0
            continue
        if current is not None:
            depth += line.count("{") - line.count("}")
            if current in wall_patches and stripped.startswith("type"):
                lines[index] = re.sub(r"\bpatch\s*;", "wall;", line)
                seen.add(current)
            if depth == 0 and stripped == "}":
                current = None
    missing = set(wall_patches) - seen
    if missing:
        raise RuntimeError(f"wall_patch_type_not_rewritten:{sorted(missing)}")
    boundary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_named_patch_types(path: Path) -> dict[str, str | None]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    result: dict[str, str | None] = {}
    current = None
    depth = 0
    for line in lines:
        stripped = line.strip()
        if current is None and stripped in PATCHES:
            current = stripped
            depth = 0
            result[current] = None
            continue
        if current is None:
            continue
        depth += line.count("{") - line.count("}")
        match = re.match(r"type\s+([^;]+);", stripped)
        if match:
            result[current] = match.group(1)
        if depth == 0 and stripped == "}":
            current = None
    return result


def audit_patch_types(case: Path, source: str, sink: str, wall_patches: list[str]) -> dict:
    mesh_types = parse_named_patch_types(case / "constant" / "polyMesh" / "boundary")
    velocity_types = parse_named_patch_types(case / "0" / "U")
    omega_types = parse_named_patch_types(case / "0" / "omega")
    wall_set = set(wall_patches)
    flow_set = {source, sink}
    checks = {
        "all_named_patches_present": set(mesh_types) == set(PATCHES),
        "source_and_sink_are_not_mesh_walls": all(mesh_types.get(patch) == "patch" for patch in flow_set),
        "all_non_flow_patches_are_mesh_walls": all(mesh_types.get(patch) == "wall" for patch in wall_set),
        "omega_wall_function_only_on_no_slip": all(
            (omega_types.get(patch) == "omegaWallFunction") == (velocity_types.get(patch) == "noSlip")
            for patch in PATCHES
        ),
        "omega_wall_function_exactly_on_wall_set": {
            patch for patch, patch_type in omega_types.items() if patch_type == "omegaWallFunction"
        } == wall_set,
        "flow_patches_have_no_omega_wall_function": all(omega_types.get(patch) != "omegaWallFunction" for patch in flow_set),
    }
    return {
        "mesh_patch_types": mesh_types,
        "velocity_patch_types": velocity_types,
        "omega_patch_types": omega_types,
        "checks": checks,
        "pass": all(checks.values()),
    }


def last_data_row(path: Path) -> list[float] | None:
    if not path.is_file():
        return None
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        try:
            rows.append([float(token) for token in stripped.replace("(", " ").replace(")", " ").split()])
        except ValueError:
            continue
    return rows[-1] if rows else None


def latest_post(case: Path, function_name: str, filename: str) -> Path | None:
    candidates = sorted((case / "postProcessing" / function_name).glob(f"*/{filename}"), key=lambda p: float(p.parent.name))
    return candidates[-1] if candidates else None


def scalar_result(case: Path, function_name: str, filename: str = "surfaceFieldValue.dat") -> float | None:
    path = latest_post(case, function_name, filename)
    row = last_data_row(path) if path else None
    return row[-1] if row and len(row) >= 2 else None


def scalar_tail(case: Path, function_name: str, count: int = 5) -> list[float]:
    path = latest_post(case, function_name, "surfaceFieldValue.dat")
    if not path:
        return []
    values = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        try:
            values.append(float(line.split()[-1]))
        except ValueError:
            continue
    return values[-count:]


def scalar_series(case: Path, function_name: str, filename: str) -> list[tuple[float, float]]:
    path = latest_post(case, function_name, filename)
    if not path:
        return []
    values = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        tokens = line.replace("(", " ").replace(")", " ").split()
        try:
            values.append((float(tokens[0]), float(tokens[-1])))
        except (ValueError, IndexError):
            continue
    return values


def last_storage_rate(case: Path) -> dict:
    enthalpy = scalar_series(case, "fluidEnthalpyIntegral", "volFieldValue.dat")
    kinetic_twice = scalar_series(case, "fluidKineticIntegral", "volFieldValue.dat")
    pairs = []
    kinetic_by_time = {time_value: value for time_value, value in kinetic_twice}
    for time_value, enthalpy_value in enthalpy:
        if time_value in kinetic_by_time:
            pairs.append((time_value, enthalpy_value + 0.5 * kinetic_by_time[time_value]))
    rate = None
    if len(pairs) >= 2 and pairs[-1][0] > pairs[-2][0]:
        rate = (pairs[-1][1] - pairs[-2][1]) / (pairs[-1][0] - pairs[-2][0])
    return {
        "last_two_total_energy_j": pairs[-2:],
        "finite_difference_storage_rate_w": rate,
    }


def courant_summary(log_path: Path) -> dict:
    text = log_path.read_text(encoding="utf-8", errors="replace")
    maxima = [float(value) for value in re.findall(r"Courant Number mean:\s*[^\s]+\s+max:\s*([+\-0-9.eE]+)", text)]
    return {
        "sample_count": len(maxima),
        "maximum_reported": max(maxima) if maxima else None,
        "last_reported": maxima[-1] if maxima else None,
    }


def heat_flux_integral(case: Path) -> float | None:
    path = latest_post(case, "headHeatFlux", "wallHeatFlux.dat")
    if not path:
        return None
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        tokens = line.split()
        if len(tokens) != 6 or tokens[0].startswith("#"):
            continue
        try:
            rows.append((float(tokens[0]), float(tokens[4])))
        except ValueError:
            continue
    if not rows:
        return None
    latest_time = max(time_value for time_value, _ in rows)
    return sum(q for time_value, q in rows if time_value == latest_time)


def vector_result(case: Path, function_name: str) -> list[float] | None:
    path = latest_post(case, function_name, "surfaceFieldValue.dat")
    row = last_data_row(path) if path else None
    return row[1:] if row and len(row) >= 3 else None


def parse_check_mesh(log_path: Path, expected_volume_m3: float) -> dict:
    text = log_path.read_text(encoding="utf-8", errors="replace")
    volume_match = re.search(r"Mesh stats.*?\bcells:\s+(\d+).*?\b(?:Overall domain|Total) volume\s*=\s*([+\-0-9.eE]+)", text, re.S)
    if not volume_match:
        volume_match = re.search(r"\bcells:\s+(\d+).*?\b(?:Overall domain|Total) volume\s*=\s*([+\-0-9.eE]+)", text, re.S)
    cells = int(volume_match.group(1)) if volume_match else None
    volume = float(volume_match.group(2).rstrip(".")) if volume_match else None
    relative = abs(volume - expected_volume_m3) / expected_volume_m3 if volume is not None else None
    patch_names = sorted(set(re.findall(r"^\s*(intake|exhaust|valve|chamber|deck|bore|walls)\s+\d+\s+\d+\s+", text, re.M)))
    return {
        "cells": cells,
        "volume_m3": volume,
        "F48_reference_volume_kind": "exact_OCC_getMass_before_linear_tetrahedral_conversion",
        "volume_relative_difference_from_F48": relative,
        "volume_difference_interpretation": "linear_tetrahedral_discretization_and_MSH4_to_MSH2_conversion_error; source_geometry_not_modified",
        "failed_mesh_checks": int((re.search(r"Failed\s+(\d+)\s+mesh checks", text) or [None, 0])[1]),
        "mesh_ok_marker": "Mesh OK." in text,
        "negative_volume_marker": "negative volume" in text.lower(),
        "patch_names_seen_in_log": patch_names,
    }


def parse_residuals(case: Path) -> dict:
    path = latest_post(case, "residuals", "residuals.dat")
    if not path:
        return {"path": None, "fields": None}
    rows = [line.split() for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip() and not line.startswith("#")]
    fields = None
    if rows:
        names = ("time", "p", "Ux", "Uy", "Uz", "T", "k", "omega", "h")
        fields = {name: (None if value == "N/A" else float(value)) for name, value in zip(names, rows[-1])}
    return {"path": str(path.relative_to(case)), "fields": fields}


def convergence_screen(case: Path, residuals: dict, contract: dict) -> dict:
    fields = residuals.get("fields") or {}
    targets = contract["openfoam"]["residual_targets"]
    checks = {
        "p": fields.get("p") is not None and fields["p"] <= targets["p"],
        "U": all(fields.get(name) is not None and fields[name] <= targets["U"] for name in ("Ux", "Uy", "Uz")),
        "k": fields.get("k") is not None and fields["k"] <= targets["k"],
        "omega": fields.get("omega") is not None and fields["omega"] <= targets["omega"],
        "h": fields.get("h") is not None and fields["h"] <= targets["h"],
    }
    tail = scalar_tail(case, "sinkMassFlow")
    plateau = None
    if len(tail) >= 5 and max(abs(value) for value in tail) > 0:
        plateau = (max(tail) - min(tail)) / max(abs(value) for value in tail) * 100.0
    return {
        "residual_checks": checks,
        "sink_mass_flow_last_five_kg_s": tail,
        "sink_mass_flow_last_five_spread_percent": plateau,
        "sink_mass_flow_plateau_at_most_1_percent": plateau is not None and plateau <= 1.0,
        "pass": all(checks.values()) and plateau is not None and plateau <= 1.0,
    }


def execute_case(case: Path, contract: dict) -> dict:
    metadata = json.loads((case / "case.json").read_text(encoding="utf-8"))
    screen = contract["openfoam"]["screens"][metadata["screen"]]
    expected_volume_m3 = metadata["F48_native_volume_scan_units_cubed"] * 1.0e-9
    source = case / metadata["source_mesh"]
    require_hash = metadata["source_mesh_sha256"]
    if sha256(source) != require_hash:
        raise RuntimeError(f"source_mesh_hash_mismatch:{metadata['case_id']}")
    for path in (case / "constant" / "polyMesh", case / "postProcessing"):
        if path.exists():
            shutil.rmtree(path)
    for path in case.iterdir():
        if path.is_dir() and re.fullmatch(r"[1-9][0-9]*(?:\.[0-9]+)?", path.name):
            shutil.rmtree(path)
    msh2 = case / "source" / "domain-msh2.msh"
    steps = []
    steps.append(run(["gmsh", str(source), "-format", "msh2", "-save", "-o", str(msh2)], case / "log.gmsh-msh2", case))
    if steps[-1]["return_code"] != 0:
        return {**metadata, "steps": steps, "solver_executed": False, "status": "MESH_CONVERSION_FAILED"}
    steps.append(run(["gmshToFoam", "-case", str(case), str(msh2)], case / "log.gmshToFoam", case))
    if steps[-1]["return_code"] != 0:
        return {**metadata, "steps": steps, "solver_executed": False, "status": "MESH_CONVERSION_FAILED"}
    steps.append(run(["transformPoints", "-case", str(case), "scale=(0.001 0.001 0.001)"], case / "log.transformPoints", case))
    if steps[-1]["return_code"] != 0:
        return {**metadata, "steps": steps, "solver_executed": False, "status": "MESH_SCALE_FAILED"}
    replace_patch_types(case / "constant" / "polyMesh" / "boundary", metadata["wall_patches"])
    patch_audit = audit_patch_types(case, screen["source_patch"], screen["sink_patch"], metadata["wall_patches"])
    if not patch_audit["pass"]:
        raise RuntimeError(f"patch_type_audit_failed:{metadata['case_id']}")
    steps.append(run(["checkMesh", "-case", str(case)], case / "log.checkMesh", case))
    mesh = parse_check_mesh(case / "log.checkMesh", expected_volume_m3)
    mesh_gate = (
        steps[-1]["return_code"] == 0
        and mesh["mesh_ok_marker"]
        and mesh["volume_relative_difference_from_F48"] is not None
        and mesh["volume_relative_difference_from_F48"] <= contract["mesh_matrix"]["openfoam_mesh_gate"]["cell_volume_relative_difference_from_F48_at_most"]
    )
    steps.append(run(["foamRun", "-solver", "fluid", "-case", str(case)], case / "log.foamRun-fluid", case))
    values = {
        "source_mass_flow_kg_s": scalar_result(case, "sourceMassFlow"),
        "sink_mass_flow_kg_s": scalar_result(case, "sinkMassFlow"),
        "source_pressure_area_average_pa": scalar_result(case, "sourcePressure"),
        "sink_pressure_area_average_pa": scalar_result(case, "sinkPressure"),
        "sink_temperature_mass_weighted_k": scalar_result(case, "sinkTemperature"),
        "wall_heat_flux_integral_w": heat_flux_integral(case),
        "source_total_energy_terms": vector_result(case, "sourceTotalEnergyTerms"),
        "sink_total_energy_terms": vector_result(case, "sinkTotalEnergyTerms"),
    }
    m_in = values["source_mass_flow_kg_s"]
    m_out = values["sink_mass_flow_kg_s"]
    values["mass_imbalance_percent"] = (
        abs(m_in + m_out) / max(abs(m_in), abs(m_out)) * 100.0
        if m_in not in (None, 0.0) and m_out is not None
        else None
    )
    tout = values["sink_temperature_mass_weighted_k"]
    qwall = values["wall_heat_flux_integral_w"]
    source_terms = values["source_total_energy_terms"]
    sink_terms = values["sink_total_energy_terms"]
    dh = abs(m_out) * 1005.0 * (tout - screen["source_temperature_k"]) if m_out is not None and tout is not None else None
    values["fluid_sensible_enthalpy_change_w"] = dh
    net_advective_out = None
    if m_in is not None and m_out is not None and source_terms and sink_terms and len(source_terms) >= 2 and len(sink_terms) >= 2:
        source_total_enthalpy = 1005.0 * source_terms[0] + 0.5 * source_terms[1]
        sink_total_enthalpy = 1005.0 * sink_terms[0] + 0.5 * sink_terms[1]
        net_advective_out = m_in * source_total_enthalpy + m_out * sink_total_enthalpy
        values["source_specific_total_enthalpy_j_kg"] = source_total_enthalpy
        values["sink_specific_total_enthalpy_j_kg"] = sink_total_enthalpy
    values["net_advective_total_enthalpy_out_w"] = net_advective_out
    storage = last_storage_rate(case)
    values["unsteady_total_energy_storage"] = storage
    sensible_storage_rate = storage["finite_difference_storage_rate_w"]
    mass_storage_rate = -(m_in + m_out) if None not in (m_in, m_out) else None
    enthalpy_reference_storage_rate = (
        CP_AIR_J_KG_K * OPENFOAM_TSTD_K * mass_storage_rate if mass_storage_rate is not None else None
    )
    absolute_storage_rate = (
        sensible_storage_rate + enthalpy_reference_storage_rate
        if None not in (sensible_storage_rate, enthalpy_reference_storage_rate)
        else None
    )
    storage["mass_storage_rate_from_boundary_flux_kg_s"] = mass_storage_rate
    storage["OpenFOAM_hConst_default_Tref_k"] = OPENFOAM_TSTD_K
    storage["enthalpy_reference_storage_rate_w"] = enthalpy_reference_storage_rate
    storage["absolute_total_energy_storage_rate_w"] = absolute_storage_rate
    energy_residual = absolute_storage_rate + net_advective_out - qwall if None not in (absolute_storage_rate, net_advective_out, qwall) else None
    values["energy_balance_sign_convention"] = "storage + outward_advective_total_enthalpy - wallHeatFlux_reported"
    values["energy_balance_residual_w"] = energy_residual
    values["approximate_energy_imbalance_percent"] = (
        abs(energy_residual) / max(abs(absolute_storage_rate), abs(net_advective_out), abs(qwall), 1.0) * 100.0
        if energy_residual is not None
        else None
    )
    mass_gate = values["mass_imbalance_percent"] is not None and values["mass_imbalance_percent"] <= contract["comparison_gates"]["mass_imbalance_percent_at_most"]
    solver_ok = steps[-1]["return_code"] == 0
    energy_gate = (
        solver_ok
        and values["approximate_energy_imbalance_percent"] is not None
        and values["approximate_energy_imbalance_percent"] <= contract["comparison_gates"]["approximate_energy_imbalance_percent_at_most"]
    )
    residuals = parse_residuals(case)
    convergence = convergence_screen(case, residuals, contract)
    return {
        **metadata,
        "steps": steps,
        "mesh": mesh,
        "patch_type_audit": patch_audit,
        "mesh_gate_pass": mesh_gate,
        "solver_executed": True,
        "solver_return_code_zero": solver_ok,
        "residuals": residuals,
        "Courant_number": courant_summary(case / "log.foamRun-fluid"),
        "convergence_screen": convergence,
        "values": values,
        "mass_balance_gate_pass": mass_gate,
        "approximate_energy_balance_gate_pass": energy_gate,
        "temperature_constraint_activation_quantified": False,
        "converged_claim": False,
        "status": "EXECUTED_FAIL_CLOSED" if solver_ok else "SOLVER_FAILED",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--levels", nargs="+", choices=("coarse", "medium", "fine"), default=("coarse", "medium"))
    parser.add_argument("--variants", nargs="+", choices=("2V", "4V"), default=("2V", "4V"))
    parser.add_argument("--screens", nargs="+", choices=("intake", "exhaust"), default=("intake", "exhaust"))
    parser.add_argument("--report-name", default="execution-report.json")
    parser.add_argument("--correction", type=Path)
    args = parser.parse_args()
    environment = assert_openfoam_environment()
    contract_path = args.project_root / "twins/reference-917-engine/f49-cfd-cht-contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    correction_sha256 = None
    if args.correction is not None:
        correction_path = args.correction if args.correction.is_absolute() else args.project_root / args.correction
        correction = json.loads(correction_path.read_text(encoding="utf-8"))
        if correction["base_contract"]["sha256"] != sha256(contract_path):
            raise RuntimeError("correction_base_hash_mismatch")
        correction_sha256 = sha256(correction_path)
    results = []
    for variant in args.variants:
        for level in args.levels:
            for screen in args.screens:
                case = args.work_root / "cases" / f"{variant.lower()}-{level}-{screen}"
                metadata = json.loads((case / "case.json").read_text(encoding="utf-8"))
                if metadata.get("numerical_correction_sha256") != correction_sha256:
                    raise RuntimeError(f"case_correction_hash_mismatch:{metadata['case_id']}")
                results.append(execute_case(case, contract))
                print(json.dumps({"case": results[-1]["case_id"], "status": results[-1]["status"]}), flush=True)
    report = {
        "schema_version": "porsche-917-f49-openfoam-execution/v1",
        "contract_sha256": sha256(contract_path),
        "numerical_correction_sha256": correction_sha256,
        "image_expected": "3dprinting993-cfd-cae-f47:kali-local",
        "image_id_expected": "sha256:a233511bef9b4fbf0653ca94258061d61b3fccbd6b4e3ef6d71c669d70de1c17",
        "openfoam_environment": environment,
        "cases": results,
        "AATE_dynamic_engine_case_executed": False,
        "conjugate_CHT_executed": False,
        "validation_claim": False,
    }
    report_path = args.work_root / args.report_name
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(report_path), "sha256": sha256(report_path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
