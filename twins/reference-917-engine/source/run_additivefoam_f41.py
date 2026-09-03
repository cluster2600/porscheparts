#!/usr/bin/env python3
"""Execute le coupon LPBF F41 avec OpenFOAM 14 et ORNL AdditiveFOAM.

Le coupon local reproduit deux couches du jeu de parametres ZRapid
iSLM420DN/AlSi10Mg publie. La simulation de bain de fusion complete l'ecran
thermique macroscopique de la culasse; elle ne remplace ni un tranchage
fournisseur, ni des coupons fabriques sur la machine retenue.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def replace_once(path: Path, pattern: str, replacement: str) -> None:
    text = path.read_text(encoding="utf-8")
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise RuntimeError(f"remplacement_inattendu:{path}:{pattern}:{count}")
    path.write_text(updated, encoding="utf-8")


def git_revision(repository: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def configure_case(template: Path, case: Path, power_w: int) -> None:
    shutil.copytree(template, case)

    scan = case / "constant/createScanPathDict"
    replace_once(scan, r"^power\s+[^;]+;", f"power       {power_w};")
    replace_once(scan, r"^speed\s+[^;]+;", "speed       1.3;")
    replace_once(scan, r"^hatch\s+[^;]+;", "hatch       1e-4;")

    material = case / "constant/transportProperties"
    replace_once(
        material,
        r'^#include\s+"\$ADDITIVEFOAM_ETC/materials/IN625\.cfg"',
        '#include "$ADDITIVEFOAM_ETC/materials/AlSi10Mg.cfg"',
    )

    temperature = case / "0/T"
    temperature.write_text(
        temperature.read_text(encoding="utf-8").replace("uniform 300", "uniform 303.15"),
        encoding="utf-8",
    )

    control = case / "system/controlDict"
    text = control.read_text(encoding="utf-8")
    text, count = re.subn(
        r"^writeInterval\s+[^;]+;",
        "writeInterval   0.001;",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise RuntimeError("write_interval_introuvable")
    marker = "type            meltPoolDimensions;\n        enabled         false;"
    if text.count(marker) != 1:
        raise RuntimeError("melt_pool_function_object_introuvable")
    control.write_text(text.replace(marker, marker.replace("false", "true")), encoding="utf-8")

    decomposition = case / "system/decomposeParDict"
    replace_once(
        decomposition,
        r"^numberOfSubdomains\s+[^;]+;",
        "numberOfSubdomains 16;",
    )


def run_case(openfoam: Path, additivefoam: Path, case: Path, execute: bool = True) -> dict:
    command = (
        "set -o pipefail; "
        "export OMPI_ALLOW_RUN_AS_ROOT=1; "
        "export OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1; "
        f"source {openfoam}/etc/bashrc; "
        f"source {additivefoam}/etc/bashrc; "
        f"cd {case}; ./Allrun; "
        "foamToVTK -case layer1 "
        "-fields '(T alpha.solid alpha.powder U)'"
    )
    log = case / "f41-additivefoam-run.log"
    if execute:
        with log.open("w", encoding="utf-8") as stream:
            result = subprocess.run(
                ["bash", "-lc", command],
                stdout=stream,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )
        return_code = result.returncode
    else:
        if not log.is_file():
            raise RuntimeError(f"journal_execution_absent:{case}")
        return_code = 0

    layer_logs = sorted(case.glob("layer*/log.additiveFoam"))
    layer_log_checks = []
    for layer_log in layer_logs:
        content = layer_log.read_text(encoding="utf-8", errors="replace")
        times = re.findall(r"^Time = ([0-9.eE+-]+)\s*$", content, flags=re.MULTILINE)
        execution_times = re.findall(
            r"^ExecutionTime = ([0-9.eE+-]+) s", content, flags=re.MULTILINE
        )
        layer_log_checks.append(
            {
                "path": str(layer_log),
                "bytes": layer_log.stat().st_size,
                "sha256": sha256(layer_log),
                "solver_end_marker": bool(
                    re.search(r"^(?:End|Finalising parallel run)\s*$", content, flags=re.MULTILINE)
                ),
                "fatal_error": "FOAM FATAL" in content or "mpirun has detected" in content,
                "final_simulation_time_s": float(times[-1]) if times else None,
                "execution_time_s": float(execution_times[-1]) if execution_times else None,
            }
        )
    vtk_files = sorted((case / "layer1/VTK").rglob("*.vtk")) if (case / "layer1/VTK").is_dir() else []
    melt_pool_files = sorted(case.glob("layer*/postProcessing/meltPoolDimensions/*.csv"))
    solver_completed = (
        len(layer_log_checks) == 2
        and all(check["solver_end_marker"] for check in layer_log_checks)
        and not any(check["fatal_error"] for check in layer_log_checks)
    )
    return {
        "return_code": return_code,
        "reused_existing_results": not execute,
        "run_log": str(log),
        "run_log_evidence": {
            "bytes": log.stat().st_size,
            "sha256": sha256(log),
        },
        "layer_logs": [str(path) for path in layer_logs],
        "layer_log_checks": layer_log_checks,
        "vtk_files": [str(path) for path in vtk_files],
        "melt_pool_files": [str(path) for path in melt_pool_files],
        "completed": return_code == 0 and solver_completed and bool(vtk_files),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--openfoam", type=Path, required=True)
    parser.add_argument("--additivefoam", type=Path, required=True)
    parser.add_argument("--geometry", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--powers", type=int, nargs="+", default=[400, 450, 500])
    parser.add_argument("--reuse-existing", action="store_true")
    args = parser.parse_args()

    template = args.additivefoam / "tutorials/multiLayerPBF"
    if not template.is_dir():
        raise SystemExit(f"template_absent:{template}")
    if not args.geometry.is_file():
        raise SystemExit(f"geometrie_absente:{args.geometry}")
    if any(power <= 0 or power > 500 for power in args.powers):
        raise SystemExit("puissance_hors_limite_machine_1_500_W")

    args.output.mkdir(parents=True, exist_ok=True)
    process = {
        "machine": "ZRapid iSLM420DN",
        "material": "AlSi10Mg",
        "laser_power_nominal_w": 500,
        "scan_speed_mm_s": 1300,
        "hatch_spacing_mm": 0.10,
        "layer_thickness_mm": 0.040,
        "published_beam_spot_diameter_mm": 0.080,
        "additivefoam_radius_parameter_mm": 0.040,
        "substrate_temperature_c": 30.0,
        "volumetric_energy_density_j_mm3": 500.0 / (1300.0 * 0.10 * 0.040),
        "number_of_simulated_layers": 2,
        "cells_per_layer": 4,
        "mpi_ranks_per_case": 16,
    }
    report = {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "classification": "local_melt_pool_virtual_process_screen_not_supplier_qualification",
        "geometry": {
            "path": str(args.geometry),
            "sha256": sha256(args.geometry),
        },
        "software": {
            "openfoam_revision": git_revision(args.openfoam),
            "additivefoam_revision": git_revision(args.additivefoam),
        },
        "machine_reference": {
            "manufacturer_country": "China",
            "build_volume_mm": [420, 420, 450],
            "laser_configuration": "2 x 500 W fibre",
            "fit_screen_for_f41": True,
            "source": "https://www.zero-tek.com/cn/slm420dn.html",
        },
        "published_process_reference": {
            **process,
            "doi": "10.1016/j.mtcomm.2026.115712",
            "source": "https://www.sciencedirect.com/science/article/pii/S2352492826011013",
        },
        "sensitivities": {},
        "limitations": [
            "La recette publiee n'est pas une carte fournisseur signee pour le lot de poudre futur.",
            "Le modele AdditiveFOAM est local au bain de fusion et ne maille pas la culasse complete a 20 micrometres.",
            "Le coupon emploie un seul faisceau; les recouvrements et calibrations entre les deux lasers ne sont pas modelises.",
            "Absorption, convection de gaz et etat de surface ne sont pas calibres sur la machine cible.",
            "Le diametre de spot publie est mappe sur un rayon AdditiveFOAM de 40 micrometres sans mesure de profil de faisceau.",
            "La densite mesuree sur coupons dans la publication ne vaut pas qualification de la culasse.",
        ],
        "gates": {
            "openfoam_solver_executed": False,
            "additivefoam_solver_executed": False,
            "nominal_case_completed": False,
            "supplier_parameter_card_qualified": False,
            "physical_coupon_qualified": False,
            "metal_print_authorized": False,
        },
    }

    configured_cases: dict[int, Path] = {}
    for power in args.powers:
        case = args.output / f"case-P{power}W"
        if args.reuse_existing:
            if not case.is_dir():
                raise SystemExit(f"cas_existant_absent:{case}")
        else:
            if case.exists():
                shutil.rmtree(case)
            configure_case(template, case, power)
        configured_cases[power] = case

    with ThreadPoolExecutor(max_workers=min(3, len(configured_cases))) as executor:
        futures = {
            executor.submit(run_case, args.openfoam, args.additivefoam, case, not args.reuse_existing): power
            for power, case in configured_cases.items()
        }
        for future in as_completed(futures):
            power = futures[future]
            result = future.result()
            result["power_w"] = power
            result["energy_density_j_mm3"] = power / (1300.0 * 0.10 * 0.040)
            report["sensitivities"][str(power)] = result

    report["sensitivities"] = dict(sorted(report["sensitivities"].items(), key=lambda item: int(item[0])))

    completed = [item["completed"] for item in report["sensitivities"].values()]
    nominal = report["sensitivities"].get("500", {})
    report["gates"]["openfoam_solver_executed"] = any(completed)
    report["gates"]["additivefoam_solver_executed"] = any(completed)
    report["gates"]["nominal_case_completed"] = bool(nominal.get("completed"))

    report_path = args.output / "917-head-lpbf-additivefoam-f41-run-report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(report_path), "gates": report["gates"]}, sort_keys=True))
    return 0 if report["gates"]["nominal_case_completed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
