#!/usr/bin/env python3
"""Prepare and optionally execute the fail-closed AdditiveFOAM F42 DOE.

Preparation is the default. Solver execution requires ``--execute`` and exact
OpenFOAM/AdditiveFOAM revisions. The script never changes the 3300 K limiter.
"""

from __future__ import annotations

import argparse
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import shlex
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SPEC = ROOT / "twins/reference-917-engine/f42-lpbf-doe.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def replace_once(path: Path, pattern: str, replacement: str) -> None:
    text = path.read_text(encoding="utf-8")
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise RuntimeError(f"remplacement_inattendu:{path}:{pattern}:{count}")
    path.write_text(updated, encoding="utf-8")


def case_id(power_w: int, speed_mm_s: int, hatch_mm: float) -> str:
    return f"P{power_w}-V{speed_mm_s}-H{round(hatch_mm * 1000):03d}"


def energy_density(power_w: int, speed_mm_s: int, hatch_mm: float, layer_mm: float) -> float:
    return power_w / (speed_mm_s * hatch_mm * layer_mm)


def build_matrix(spec: dict) -> list[dict]:
    window = spec["published_process_window"]
    layer_mm = float(window["layer_thickness_mm"])
    rows = []
    for power_w, speed_mm_s, hatch_mm in itertools.product(
        window["laser_power_w"],
        window["scan_speed_mm_s"],
        window["hatch_spacing_mm"],
    ):
        rows.append(
            {
                "case_id": case_id(int(power_w), int(speed_mm_s), float(hatch_mm)),
                "laser_power_w": int(power_w),
                "scan_speed_mm_s": int(speed_mm_s),
                "hatch_spacing_mm": float(hatch_mm),
                "layer_thickness_mm": layer_mm,
                "volumetric_energy_density_j_mm3": energy_density(
                    int(power_w), int(speed_mm_s), float(hatch_mm), layer_mm
                ),
            }
        )
    return rows


def validate_spec(spec: dict, spec_path: Path) -> list[dict]:
    if spec.get("phase") != "F42":
        raise ValueError("phase_F42_requise")
    for evidence in spec["geometry_provenance"].values():
        if not isinstance(evidence, dict) or "path" not in evidence:
            continue
        path = ROOT / evidence["path"]
        if not path.is_file() or sha256(path) != evidence["sha256"]:
            raise ValueError(f"preuve_geometrie_alteree:{path}")

    window = spec["published_process_window"]
    if window["laser_power_w"] != [360, 380, 400]:
        raise ValueError("axes_puissance_F42_invalides")
    if window["scan_speed_mm_s"] != [1200, 1300, 1500]:
        raise ValueError("axes_vitesse_F42_invalides")
    if window["hatch_spacing_mm"] != [0.13, 0.15, 0.16]:
        raise ValueError("axes_hatch_F42_invalides")
    if not math.isclose(window["layer_thickness_mm"], 0.05, abs_tol=1e-12):
        raise ValueError("couche_F42_doit_etre_50_um")

    matrix = build_matrix(spec)
    if len(matrix) != spec["doe"]["expected_screening_case_count"]:
        raise ValueError("taille_matrice_Doe_invalide")
    if len({row["case_id"] for row in matrix}) != len(matrix):
        raise ValueError("identifiants_Doe_non_uniques")
    observed_range = [
        min(row["volumetric_energy_density_j_mm3"] for row in matrix),
        max(row["volumetric_energy_density_j_mm3"] for row in matrix),
    ]
    expected_range = spec["doe"]["expected_ved_range_j_mm3"]
    if any(not math.isclose(a, b, rel_tol=1e-12) for a, b in zip(observed_range, expected_range)):
        raise ValueError("plage_VED_incoherente")

    machine = spec["machine_reference"]["build_volume_mm"]
    envelope = spec["orientation_and_support"]["oriented_envelope_mm_if_scale_is_mm"]
    if any(part >= build for part, build in zip(envelope, machine)):
        raise ValueError("enveloppe_conditionnelle_hors_machine")
    layer_count = math.ceil(envelope[2] / window["layer_thickness_mm"])
    if layer_count != spec["slicing_contract"]["expected_layer_count_from_oriented_height"]:
        raise ValueError("nombre_couches_incoherent")
    if spec["additivefoam"]["temperature_limit_k"] != 3300.0:
        raise ValueError("plafond_solveur_modifie_interdit")
    if any(spec["release_gates"].values()):
        raise ValueError("autorisation_F42_ne_doit_pas_etre_ouverte")
    if not spec_path.is_file():
        raise ValueError("specification_F42_absente")
    return matrix


def configure_case(template: Path, case: Path, row: dict, spec: dict, resolution: str) -> dict:
    if case.exists():
        shutil.rmtree(case)
    shutil.copytree(template, case)

    scan = case / "constant/createScanPathDict"
    replace_once(scan, r"^power\s+[^;]+;", f"power       {row['laser_power_w']};")
    replace_once(scan, r"^speed\s+[^;]+;", f"speed       {row['scan_speed_mm_s'] / 1000.0:.12g};")
    replace_once(scan, r"^hatch\s+[^;]+;", f"hatch       {row['hatch_spacing_mm'] / 1000.0:.12g};")

    material = case / "constant/transportProperties"
    replace_once(
        material,
        r'^#include\s+"\$ADDITIVEFOAM_ETC/materials/IN625\.cfg"',
        '#include "$ADDITIVEFOAM_ETC/materials/AlSi10Mg.cfg"',
    )

    initial_temperature = spec["model_hypotheses"]["initial_temperature_k"]
    temperature = case / "0/T"
    replace_once(temperature, r"\buniform\s+[0-9.eE+-]+", f"uniform {initial_temperature}")

    allrun = case / "Allrun"
    level = spec["resolution_study"]["levels"][resolution]
    replace_once(allrun, r"(-nLayers\s+)\d+", rf"\g<1>{spec['additivefoam']['simulated_layers']}")
    replace_once(allrun, r"(-nCellsPerLayer\s+)\d+", rf"\g<1>{level['cells_per_layer']}")
    replace_once(allrun, r"(-layerThickness\s+)[0-9.eE+-]+", r"\g<1>50e-6")

    block_mesh = case / "system/blockMeshDict"
    cells = level["base_mesh_cells"]
    replace_once(
        block_mesh,
        r"(hex\s*\([^\n]+\)\s*)\(\s*\d+\s+\d+\s+\d+\s*\)",
        rf"\g<1>({cells[0]} {cells[1]} {cells[2]})",
    )

    control = case / "system/controlDict"
    text = control.read_text(encoding="utf-8")
    marker = "type            meltPoolDimensions;\n        enabled         false;"
    if marker in text:
        control.write_text(text.replace(marker, marker.replace("false", "true")), encoding="utf-8")
    elif "meltPoolDimensions" not in text:
        raise RuntimeError("melt_pool_function_object_introuvable")

    decomposition = case / "system/decomposeParDict"
    replace_once(
        decomposition,
        r"^numberOfSubdomains\s+[^;]+;",
        f"numberOfSubdomains {spec['additivefoam']['mpi_ranks_per_case']};",
    )

    fv_solution = case / "system/fvSolution"
    fv_text = fv_solution.read_text(encoding="utf-8")
    match = re.search(r"^\s*Tmax\s+([0-9.eE+-]+);", fv_text, flags=re.MULTILINE)
    if match is None or not math.isclose(float(match.group(1)), 3300.0, abs_tol=1e-12):
        raise RuntimeError("Tmax_3300_absent_ou_modifie")

    configured = {
        **row,
        "resolution": resolution,
        "case_path": str(case),
        "cells_per_layer": level["cells_per_layer"],
        "base_mesh_cells": cells,
        "configuration_sha256": {
            str(path.relative_to(case)): sha256(path)
            for path in (scan, material, temperature, allrun, block_mesh, control, decomposition, fv_solution)
        },
        "temperature_limit_k_verified": 3300.0,
    }
    (case / "f42-case.json").write_text(
        json.dumps(configured, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return configured


def git_revision(repository: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def execute_case(openfoam: Path, additivefoam: Path, case: Path) -> dict:
    command = (
        "set -o pipefail; "
        "export OMPI_ALLOW_RUN_AS_ROOT=1; "
        "export OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1; "
        f"source {shlex.quote(str(openfoam / 'etc/bashrc'))}; "
        f"source {shlex.quote(str(additivefoam / 'etc/bashrc'))}; "
        f"cd {shlex.quote(str(case))}; ./Allrun; "
        "foamToVTK -case layer1 -fields '(T alpha.solid alpha.powder U)'"
    )
    log = case / "f42-additivefoam-run.log"
    with log.open("w", encoding="utf-8") as stream:
        result = subprocess.run(
            ["bash", "-lc", command],
            stdout=stream,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    content = log.read_text(encoding="utf-8", errors="replace")
    layer_logs = sorted(case.glob("layer*/log.additiveFoam"))
    layer_log_checks = []
    for layer_log in layer_logs:
        layer_content = layer_log.read_text(encoding="utf-8", errors="replace")
        times = re.findall(r"^Time = ([0-9.eE+-]+)\s*$", layer_content, flags=re.MULTILINE)
        layer_log_checks.append(
            {
                "path": str(layer_log),
                "sha256": sha256(layer_log),
                "final_simulation_time_s": float(times[-1]) if times else None,
                "solver_end_marker": bool(
                    re.search(
                        r"^(?:End|Finalising parallel run)\s*$",
                        layer_content,
                        flags=re.MULTILINE,
                    )
                ),
                "fatal_error": "FOAM FATAL" in layer_content
                or "mpirun has detected" in layer_content,
            }
        )
    vtk_files = sorted((case / "layer1/VTK").rglob("*.vtk")) if (case / "layer1/VTK").is_dir() else []
    completed = (
        result.returncode == 0
        and len(layer_log_checks) == spec_layer_count(case)
        and all(check["solver_end_marker"] for check in layer_log_checks)
        and not any(check["fatal_error"] for check in layer_log_checks)
        and bool(vtk_files)
    )
    return {
        "return_code": result.returncode,
        "run_log": str(log),
        "run_log_sha256": sha256(log),
        "layer_log_count": len(layer_logs),
        "layer_log_checks": layer_log_checks,
        "vtk_file_count": len(vtk_files),
        "fatal_error": "FOAM FATAL" in content or "mpirun has detected" in content,
        "completed": completed,
    }


def spec_layer_count(case: Path) -> int:
    text = (case / "Allrun").read_text(encoding="utf-8")
    match = re.search(r"-nLayers\s+(\d+)", text)
    if match is None:
        raise RuntimeError(f"nLayers_absent:{case}")
    return int(match.group(1))


def select_jobs(matrix: list[dict], spec: dict, mode: str) -> list[tuple[dict, str]]:
    jobs: list[tuple[dict, str]] = []
    if mode in {"screening", "all"}:
        jobs.extend((row, "nominal") for row in matrix)
    if mode in {"convergence", "all"}:
        selected = set(spec["resolution_study"]["case_ids"])
        by_id = {row["case_id"]: row for row in matrix}
        if not selected.issubset(by_id):
            raise ValueError("cas_convergence_absent_de_la_matrice")
        for selected_id in sorted(selected):
            for resolution in ("coarse", "nominal", "fine"):
                if mode == "all" and resolution == "nominal":
                    continue
                jobs.append((by_id[selected_id], resolution))
    return jobs


def write_matrix(output: Path, matrix: list[dict]) -> Path:
    path = output / "917-head-lpbf-doe-f42.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(matrix[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(matrix)
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--additivefoam", type=Path)
    parser.add_argument("--openfoam", type=Path)
    parser.add_argument("--mode", choices=("screening", "convergence", "all"), default="all")
    parser.add_argument("--matrix-only", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--jobs", type=int, default=1)
    args = parser.parse_args()

    spec = load_json(args.spec)
    matrix = validate_spec(spec, args.spec)
    args.output.mkdir(parents=True, exist_ok=True)
    matrix_path = write_matrix(args.output, matrix)
    manifest = {
        "schema_version": "1.0.0",
        "phase": "F42",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "classification": spec["classification"],
        "specification": {"path": str(args.spec), "sha256": sha256(args.spec)},
        "design": spec["doe"],
        "matrix": matrix,
        "matrix_artifact": {"path": str(matrix_path), "sha256": sha256(matrix_path)},
        "orientation_and_support": spec["orientation_and_support"],
        "slicing_contract": spec["slicing_contract"],
        "configured_cases": [],
        "solver_results": {},
        "gates": deepcopy(spec["release_gates"]),
    }

    if not args.matrix_only:
        if args.additivefoam is None:
            raise SystemExit("--additivefoam_requis_sauf_avec_--matrix-only")
        template = args.additivefoam / spec["additivefoam"]["template"]
        if not template.is_dir():
            raise SystemExit(f"template_absent:{template}")
        revision = git_revision(args.additivefoam)
        if revision != spec["additivefoam"]["required_revision"]:
            raise SystemExit(f"revision_AdditiveFOAM_incorrecte:{revision}")
        for row, resolution in select_jobs(matrix, spec, args.mode):
            suffix = "" if resolution == "nominal" else f"-{resolution}"
            case = args.output / f"case-{row['case_id']}{suffix}"
            manifest["configured_cases"].append(
                configure_case(template, case, row, spec, resolution)
            )

    if args.execute:
        if args.matrix_only or args.openfoam is None or args.additivefoam is None:
            raise SystemExit("--execute_exige_--openfoam_--additivefoam_et_des_cas_configures")
        openfoam_revision = git_revision(args.openfoam)
        if openfoam_revision != spec["additivefoam"]["openfoam_required_revision"]:
            raise SystemExit(f"revision_OpenFOAM_incorrecte:{openfoam_revision}")
        if args.jobs < 1:
            raise SystemExit("--jobs_doit_etre_positif")
        with ThreadPoolExecutor(max_workers=args.jobs) as executor:
            futures = {
                executor.submit(execute_case, args.openfoam, args.additivefoam, Path(case["case_path"])): case
                for case in manifest["configured_cases"]
            }
            for future in as_completed(futures):
                case = futures[future]
                manifest["solver_results"][f"{case['case_id']}:{case['resolution']}"] = future.result()
        completed = [result["completed"] for result in manifest["solver_results"].values()]
        manifest["gates"]["doe_solver_executed"] = bool(completed) and all(completed)

    report_path = args.output / "917-head-lpbf-doe-f42-manifest.json"
    manifest["artifacts"] = {
        matrix_path.name: {"sha256": sha256(matrix_path), "bytes": matrix_path.stat().st_size},
        report_path.name: {"self_hash_excluded": True},
    }
    report_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(report_path), "cases": len(matrix), "gates": manifest["gates"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
