#!/usr/bin/env python3
"""Extract F42 DOE measurements from completed AdditiveFOAM case folders."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import csv
import json
import math
from pathlib import Path
import re


LIQUIDUS_K = 870.0


def numeric_suffix(path: Path) -> int:
    match = re.search(r"_(\d+)\.vtk$", path.name)
    return int(match.group(1)) if match else -1


def volume_state_paths(case: Path) -> list[Path]:
    """Return only the volume datasets emitted by foamToVTK.

    Patch subdirectories contain POLYDATA surfaces and must not be read as
    unstructured volume grids.  The top-level ``layer1_*.vtk`` files contain
    the cell temperatures and volumes used by the DOE metrics.
    """
    return sorted((case / "layer1/VTK").glob("layer1_*.vtk"), key=numeric_suffix)


def read_state(path: Path) -> dict:
    try:
        import numpy as np
        import vtk
        from vtk.util.numpy_support import vtk_to_numpy
    except ImportError as exc:
        raise RuntimeError("vtk_et_numpy_requis_pour_extraire_les_champs") from exc

    reader = vtk.vtkUnstructuredGridReader()
    reader.SetFileName(str(path))
    reader.ReadAllScalarsOn()
    reader.ReadAllVectorsOn()
    reader.Update()
    grid = reader.GetOutput()
    if grid.GetNumberOfCells() == 0:
        raise RuntimeError(f"vtk_sans_cellules:{path}")
    if grid.GetCellData().GetArray("T") is None and grid.GetPointData().GetArray("T") is not None:
        converter = vtk.vtkPointDataToCellData()
        converter.SetInputData(grid)
        converter.Update()
        grid = converter.GetOutput()
    array = grid.GetCellData().GetArray("T")
    if array is None:
        raise RuntimeError(f"champ_T_absent:{path}")
    temperature = vtk_to_numpy(array).astype(float)
    size_filter = vtk.vtkCellSizeFilter()
    size_filter.SetInputData(grid)
    size_filter.SetComputeArea(False)
    size_filter.SetComputeLength(False)
    size_filter.SetComputeVertexCount(False)
    size_filter.SetComputeVolume(True)
    size_filter.Update()
    volume_array = size_filter.GetOutput().GetCellData().GetArray("Volume")
    if volume_array is None:
        raise RuntimeError(f"volume_cellule_absent:{path}")
    volumes = vtk_to_numpy(volume_array).astype(float)
    molten = temperature >= LIQUIDUS_K
    return {
        "temperature_max_k": float(temperature.max()),
        "temperature_p99_k": float(np.quantile(temperature, 0.99)),
        "molten_volume_mm3": float(volumes[molten].sum() * 1.0e9),
        "finite": bool(np.isfinite(temperature).all() and np.isfinite(volumes).all()),
    }


def read_melt_pool_dimensions(case: Path) -> dict:
    rows = []
    for path in sorted(case.glob("layer*/postProcessing/meltPoolDimensions/870.csv")):
        with path.open(encoding="utf-8") as stream:
            for row in csv.DictReader(stream):
                rows.append(
                    {
                        "length": float(row["length(m)"]) * 1000.0,
                        "width": float(row["width(m)"]) * 1000.0,
                        "depth": float(row["depth(m)"]) * 1000.0,
                    }
                )
    if not rows:
        raise RuntimeError(f"melt_pool_870K_absent:{case}")
    return {
        "melt_pool_length_mm": max(row["length"] for row in rows),
        "melt_pool_width_mm": max(row["width"] for row in rows),
        "melt_pool_depth_mm": max(row["depth"] for row in rows),
    }


def parse_max_courant(paths: list[Path]) -> float:
    maxima = []
    pattern = re.compile(r"Courant Number mean:\s*[0-9.eE+-]+\s+max:\s*([0-9.eE+-]+)")
    for path in paths:
        content = path.read_text(encoding="utf-8", errors="replace")
        maxima.extend(float(value) for value in pattern.findall(content))
    if not maxima or not all(math.isfinite(value) for value in maxima):
        raise RuntimeError("nombre_Courant_absent_ou_non_fini")
    return max(maxima)


def extract_case(configured: dict, solver_result: dict) -> dict:
    case = Path(configured["case_path"])
    vtk_files = volume_state_paths(case)
    if not vtk_files:
        raise RuntimeError(f"vtk_absent:{case}")
    states = [read_state(path) for path in vtk_files]
    hottest = max(states, key=lambda state: (state["temperature_max_k"], state["temperature_p99_k"]))
    layer_logs = sorted(case.glob("layer*/log.additiveFoam"))
    return {
        "case_id": configured["case_id"],
        "resolution": configured["resolution"],
        "completed": bool(solver_result.get("completed")),
        "fatal_error": bool(solver_result.get("fatal_error")),
        **hottest,
        **read_melt_pool_dimensions(case),
        "maximum_courant_number": parse_max_courant(layer_logs),
        "vtk_state_count": len(states),
    }


def extract_case_pair(pair: tuple[dict, dict]) -> dict:
    return extract_case(*pair)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=1)
    args = parser.parse_args()

    manifest = json.loads(args.run_manifest.read_text(encoding="utf-8"))
    configured = {
        f"{case['case_id']}:{case['resolution']}": case for case in manifest["configured_cases"]
    }
    solver_results = manifest.get("solver_results", {})
    if set(solver_results) != set(configured):
        missing = sorted(set(configured) - set(solver_results))
        extra = sorted(set(solver_results) - set(configured))
        raise SystemExit(f"resultats_incomplets_ou_inconnus:missing={missing}:extra={extra}")
    if args.jobs < 1:
        raise SystemExit("jobs_doit_etre_positif")
    work = [(configured[key], solver_results[key]) for key in sorted(configured)]
    if args.jobs == 1:
        measurements = [extract_case_pair(pair) for pair in work]
    else:
        with ProcessPoolExecutor(max_workers=args.jobs) as executor:
            measurements = list(executor.map(extract_case_pair, work))
    payload = {
        "schema_version": "1.0.0",
        "phase": "F42",
        "run_manifest": str(args.run_manifest),
        "measurements": measurements,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "measurements": len(measurements)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
