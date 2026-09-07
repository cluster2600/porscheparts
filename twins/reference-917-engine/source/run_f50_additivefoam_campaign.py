#!/usr/bin/env python3
"""Prepare and execute the F50 local AdditiveFOAM reference campaign.

The multiLayerPBF cases are process coupons. They are hash-linked to the two
private F50 masters but never contain or approximate the cylinder-head skin.
The AlSi10Mg model is the published F42 control model, not a fabricated CP1
material card and not a full-head distortion simulation.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess


ADDITIVEFOAM_REVISION = "9c05c5eb54db03faa342b14b0806efe740de8c44"
OPENFOAM_PACKAGE = "14-20260724"
TEMPERATURE_LIMIT_K = 3300.0
MASTER_HASHES = {
    "2v": "1574eb58b7af09bcadab6c9cfcdd9a56940d479a5aa1b1eb807d31d41d4f7c36",
    "4v": "10ff1a2af8f2dbca78cf6ac2f72a9e1f2842e171f1e1e76080f07eacd4162131",
}
RESOLUTIONS = {
    "coarse": {"base_mesh_cells": [32, 20, 24], "cells_per_layer": 4},
    "nominal": {"base_mesh_cells": [40, 25, 30], "cells_per_layer": 5},
    "fine": {"base_mesh_cells": [48, 30, 36], "cells_per_layer": 6},
}
MPI_RANKS = 8
PROCESS_POINTS = {
    "published_witness": {
        "laser_power_w": 380,
        "scan_speed_mm_s": 1300,
        "hatch_spacing_mm": 0.15,
        "resolutions": ["coarse", "nominal", "fine"],
    },
    "low_ved_screen": {
        "laser_power_w": 360,
        "scan_speed_mm_s": 1500,
        "hatch_spacing_mm": 0.16,
        "resolutions": ["nominal"],
    },
}


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
        raise RuntimeError(f"replace_failed:{path.name}:{pattern}:{count}")
    path.write_text(updated, encoding="utf-8")


def repository_head(repository: Path) -> str:
    """Read a detached or referenced Git HEAD without requiring git in the image."""

    head = (repository / ".git/HEAD").read_text(encoding="utf-8").strip()
    if not head.startswith("ref: "):
        return head
    return (repository / ".git" / head.removeprefix("ref: ")).read_text(encoding="utf-8").strip()


def configure_case(template: Path, case: Path, point: dict, resolution: str) -> dict:
    if case.exists():
        shutil.rmtree(case)
    shutil.copytree(template, case)
    scan = case / "constant/createScanPathDict"
    replace_once(scan, r"^power\s+[^;]+;", f"power       {point['laser_power_w']};")
    replace_once(scan, r"^speed\s+[^;]+;", f"speed       {point['scan_speed_mm_s'] / 1000.0:.12g};")
    replace_once(scan, r"^hatch\s+[^;]+;", f"hatch       {point['hatch_spacing_mm'] / 1000.0:.12g};")
    # Short-track process witness: same 0.4 mm laser track for every case.
    # It preserves the F42 local melt-pool method while avoiding any claim of
    # simulating the full head or a supplier coupon geometry.
    replace_once(scan, r"^minPoint\s+[^;]+;", "minPoint    (0.000 -1e-4);")
    replace_once(scan, r"^maxPoint\s+[^;]+;", "maxPoint    (0.0004 1e-4);")
    material = case / "constant/transportProperties"
    replace_once(
        material,
        r'^#include\s+"\$ADDITIVEFOAM_ETC/materials/IN625\.cfg"',
        '#include "$ADDITIVEFOAM_ETC/materials/AlSi10Mg.cfg"',
    )
    replace_once(case / "0/T", r"\buniform\s+[0-9.eE+-]+", "uniform 293.15")
    allrun = case / "Allrun"
    replace_once(allrun, r"(-nLayers\s+)\d+", r"\g<1>2")
    replace_once(allrun, r"(-nCellsPerLayer\s+)\d+", rf"\g<1>{RESOLUTIONS[resolution]['cells_per_layer']}")
    replace_once(allrun, r"(-layerThickness\s+)[0-9.eE+-]+", r"\g<1>50e-6")
    cells = RESOLUTIONS[resolution]["base_mesh_cells"]
    replace_once(
        case / "system/blockMeshDict",
        r"(hex\s*\([^\n]+\)\s*)\(\s*\d+\s+\d+\s+\d+\s*\)",
        rf"\g<1>({cells[0]} {cells[1]} {cells[2]})",
    )
    replace_once(case / "system/blockMeshDict", r"^xmin\s+[^;]+;", "xmin -0.0002;")
    replace_once(case / "system/blockMeshDict", r"^xmax\s+[^;]+;", "xmax 0.0006;")
    control = case / "system/controlDict"
    control_text = control.read_text(encoding="utf-8")
    marker = "type            meltPoolDimensions;\n        enabled         false;"
    if marker not in control_text:
        raise RuntimeError("melt_pool_function_object_missing")
    control.write_text(control_text.replace(marker, marker.replace("false", "true")), encoding="utf-8")
    replace_once(control, r"^endTime\s+[^;]+;", "endTime         0.0005;")
    replace_once(control, r"^writeInterval\s+[^;]+;", "writeInterval   0.0001;")
    replace_once(case / "system/decomposeParDict", r"^numberOfSubdomains\s+[^;]+;", f"numberOfSubdomains {MPI_RANKS};")
    fv_solution = case / "system/fvSolution"
    match = re.search(r"^\s*Tmax\s+([0-9.eE+-]+);", fv_solution.read_text(encoding="utf-8"), re.MULTILINE)
    if match is None or not math.isclose(float(match.group(1)), TEMPERATURE_LIMIT_K):
        raise RuntimeError("temperature_limit_changed")
    files = [scan, material, case / "0/T", allrun, case / "system/blockMeshDict", control, case / "system/decomposeParDict", fv_solution]
    return {
        "process": point,
        "resolution": resolution,
        "case_path": str(case),
        "base_mesh_cells": cells,
        "cells_per_layer": RESOLUTIONS[resolution]["cells_per_layer"],
        "short_track_length_mm": 0.4,
        "simulation_end_time_s": 0.0005,
        "post_scan_cooling_time_s": 0.0005 - 0.0004 / (point["scan_speed_mm_s"] / 1000.0),
        "coupon_domain_mm": [0.8, 0.5, 0.3],
        "mpi_ranks": MPI_RANKS,
        "configuration_sha256": {str(path.relative_to(case)): sha256(path) for path in files},
    }


def execute_case(openfoam: Path, additivefoam: Path, case: Path) -> dict:
    command = (
        "set -o pipefail; export OMPI_ALLOW_RUN_AS_ROOT=1; export OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1; "
        f"source {openfoam}/etc/bashrc; source {additivefoam}/etc/bashrc; "
        f"cd {case}; ./Allrun; foamToVTK -case layer1 -ascii -fields '(T alpha.solid alpha.powder U)'"
    )
    log = case / "f50-additivefoam-run.log"
    with log.open("w", encoding="utf-8") as stream:
        completed = subprocess.run(["bash", "-lc", command], stdout=stream, stderr=subprocess.STDOUT, text=True, check=False)
    layer_logs = sorted(case.glob("layer*/log.additiveFoam"))
    checks = []
    for path in layer_logs:
        text = path.read_text(encoding="utf-8", errors="replace")
        times = re.findall(r"^Time = ([0-9.eE+-]+)\s*$", text, flags=re.MULTILINE)
        courant = [float(value) for value in re.findall(r"Courant Number mean:\s*[0-9.eE+-]+\s+max:\s*([0-9.eE+-]+)", text)]
        checks.append(
            {
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
                "end_marker": bool(re.search(r"^(?:End|Finalising parallel run)\s*$", text, re.MULTILINE)),
                "fatal_error": "FOAM FATAL" in text or "mpirun has detected" in text,
                "final_simulation_time_s": float(times[-1]) if times else None,
                "maximum_courant_number": max(courant) if courant else None,
            }
        )
    vtk = sorted((case / "layer1/VTK").glob("layer1_*.vtk"))
    success = (
        completed.returncode == 0
        and len(checks) == 2
        and all(item["end_marker"] and not item["fatal_error"] for item in checks)
        and bool(vtk)
    )
    return {
        "return_code": completed.returncode,
        "run_log_sha256": sha256(log),
        "run_log_bytes": log.stat().st_size,
        "layer_log_checks": checks,
        "vtk_state_count": len(vtk),
        "completed": success,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--openfoam", type=Path, required=True)
    parser.add_argument("--additivefoam", type=Path, required=True)
    parser.add_argument("--master-hash-lock", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-parallel", type=int, default=1)
    args = parser.parse_args()
    lock = json.loads(args.master_hash_lock.read_text(encoding="utf-8"))
    if lock.get("master_hashes") != MASTER_HASHES:
        raise SystemExit("private_master_hash_lock_mismatch")
    if lock.get("contains_private_geometry") is not False:
        raise SystemExit("private_master_hash_lock_privacy_missing")
    if args.max_parallel < 1 or args.max_parallel > 4:
        raise SystemExit("max_parallel_out_of_range")
    if repository_head(args.additivefoam) != ADDITIVEFOAM_REVISION:
        raise SystemExit("wrong_additivefoam_revision")
    template = args.additivefoam / "tutorials/multiLayerPBF"
    if not template.is_dir():
        raise SystemExit("multiLayerPBF_template_missing")
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "1.0.0",
        "phase": "F50",
        "classification": "private_runtime_manifest_local_process_coupon_not_full_head_simulation",
        "master_hashes": MASTER_HASHES,
        "master_hash_lock_sha256": sha256(args.master_hash_lock),
        "software": {
            "openfoam": OPENFOAM_PACKAGE,
            "additivefoam_revision": ADDITIVEFOAM_REVISION,
            "additivefoam_binary_sha256": sha256(Path(subprocess.check_output(["bash", "-lc", f"source {args.openfoam}/etc/bashrc; source {args.additivefoam}/etc/bashrc; command -v additiveFoam"], text=True).strip())),
        },
        "material_model": {
            "name": "AlSi10Mg",
            "role": "F42 published control model only",
            "target_CP1_card_used": False,
            "reason": "No complete supplier CP1 temperature-dependent AdditiveFOAM card is available.",
        },
        "witness_geometry": {
            "role": "short-track local process witness, no head architecture",
            "track_length_mm": 0.4,
            "domain_mm": [0.8, 0.5, 0.3],
            "full_head_or_supplier_coupon_geometry": False,
        },
        "cases": {},
    }
    configured_cases = {}
    for point_name, point in PROCESS_POINTS.items():
        for resolution in point["resolutions"]:
            key = f"shared:{point_name}:{resolution}"
            case = args.output / f"case-shared-{point_name}-{resolution}"
            configured = configure_case(template, case, point, resolution)
            configured["architecture_binding"] = {
                "2v_master_sha256": MASTER_HASHES["2v"],
                "4v_master_sha256": MASTER_HASHES["4v"],
                "interpretation": "one architecture-independent local process witness linked to both private masters",
            }
            configured_cases[key] = (case, configured)
    with ThreadPoolExecutor(max_workers=args.max_parallel) as executor:
        pending = {
            executor.submit(execute_case, args.openfoam, args.additivefoam, case): (key, configured)
            for key, (case, configured) in configured_cases.items()
        }
        for future in as_completed(pending):
            key, configured = pending[future]
            manifest["cases"][key] = {"configured": configured, "result": future.result()}
    manifest["cases"] = dict(sorted(manifest["cases"].items()))
    manifest["all_cases_completed"] = bool(manifest["cases"]) and all(item["result"]["completed"] for item in manifest["cases"].values())
    path = args.output / "f50-additivefoam-private-run-manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(path), "cases": len(manifest["cases"]), "all_completed": manifest["all_cases_completed"]}, sort_keys=True))
    return 0 if manifest["all_cases_completed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
