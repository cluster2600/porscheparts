#!/usr/bin/env python3
"""Extrait les metriques, l'image et la video du coupon AdditiveFOAM F41."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy


LIQUIDUS_K = 870.0
SOLIDUS_K = 850.0
SOLVER_TMAX_K = 3300.0


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_state(path: Path) -> dict:
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
        converter.PassPointDataOn()
        converter.Update()
        grid = converter.GetOutput()

    temperature_array = grid.GetCellData().GetArray("T")
    if temperature_array is None:
        raise RuntimeError(f"champ_T_absent:{path}")
    temperature = vtk_to_numpy(temperature_array).astype(float)

    centres_filter = vtk.vtkCellCenters()
    centres_filter.SetInputData(grid)
    centres_filter.Update()
    centres = vtk_to_numpy(centres_filter.GetOutput().GetPoints().GetData()).astype(float)

    size_filter = vtk.vtkCellSizeFilter()
    size_filter.SetInputData(grid)
    size_filter.SetComputeArea(False)
    size_filter.SetComputeLength(False)
    size_filter.SetComputeVertexCount(False)
    size_filter.SetComputeVolume(True)
    size_filter.Update()
    volumes_array = size_filter.GetOutput().GetCellData().GetArray("Volume")
    volumes = vtk_to_numpy(volumes_array).astype(float) if volumes_array is not None else np.ones_like(temperature)

    velocity_array = grid.GetCellData().GetArray("U")
    if velocity_array is None and grid.GetPointData().GetArray("U") is not None:
        velocity_array = grid.GetPointData().GetArray("U")
    velocity = vtk_to_numpy(velocity_array).astype(float) if velocity_array is not None else np.zeros((len(temperature), 3))
    if len(velocity) != len(temperature):
        velocity_max = float(np.linalg.norm(velocity, axis=1).max(initial=0.0))
    else:
        velocity_max = float(np.linalg.norm(velocity, axis=1).max(initial=0.0))

    molten = temperature >= LIQUIDUS_K
    mushy = (temperature >= SOLIDUS_K) & (temperature < LIQUIDUS_K)
    if molten.any():
        mins = centres[molten].min(axis=0)
        maxs = centres[molten].max(axis=0)
        dimensions = (maxs - mins) * 1000.0
    else:
        dimensions = np.zeros(3)

    return {
        "path": str(path),
        "centres": centres,
        "temperature": temperature,
        "volumes": volumes,
        "temperature_min_k": float(np.min(temperature)),
        "temperature_max_k": float(np.max(temperature)),
        "temperature_p99_k": float(np.quantile(temperature, 0.99)),
        "molten_cell_count": int(np.count_nonzero(molten)),
        "mushy_cell_count": int(np.count_nonzero(mushy)),
        "molten_volume_mm3": float(np.sum(volumes[molten]) * 1.0e9),
        "melt_pool_length_x_mm": float(dimensions[0]),
        "melt_pool_width_y_mm": float(dimensions[1]),
        "melt_pool_depth_z_mm": float(dimensions[2]),
        "velocity_max_m_s": velocity_max,
        "finite": bool(np.isfinite(temperature).all()),
        "solver_temperature_cap_hit": bool(np.max(temperature) >= SOLVER_TMAX_K - 1.0),
    }


def public_metrics(state: dict) -> dict:
    return {key: value for key, value in state.items() if key not in {"centres", "temperature", "volumes"}}


def read_solver_melt_pool(case: Path, threshold_k: int = 870) -> dict:
    rows = []
    files = sorted(case.glob(f"layer*/postProcessing/meltPoolDimensions/{threshold_k}.csv"))
    for path in files:
        with path.open(encoding="utf-8") as stream:
            for row in csv.DictReader(stream):
                rows.append(
                    {
                        "time_s": float(row["time(s)"]),
                        "length_mm": float(row["length(m)"]) * 1000.0,
                        "width_mm": float(row["width(m)"]) * 1000.0,
                        "depth_mm": float(row["depth(m)"]) * 1000.0,
                    }
                )
    if not rows:
        raise RuntimeError(f"melt_pool_csv_absent:{case}:{threshold_k}")
    return {
        "threshold_k": threshold_k,
        "source": "AdditiveFOAM_meltPoolDimensions_function_object",
        "sample_count": len(rows),
        "maximum_length_mm": max(row["length_mm"] for row in rows),
        "maximum_width_mm": max(row["width_mm"] for row in rows),
        "maximum_depth_mm": max(row["depth_mm"] for row in rows),
    }


def plot_slice(axis, state: dict, title: str) -> None:
    centres = state["centres"]
    temperature = state["temperature"]
    y_values = np.unique(np.round(centres[:, 1], decimals=12))
    hottest_y = centres[int(np.argmax(temperature)), 1]
    y_slice = y_values[np.argmin(np.abs(y_values - hottest_y))]
    tolerance = max(1.0e-12, np.min(np.diff(y_values)) * 0.45) if len(y_values) > 1 else 1.0
    mask = np.abs(centres[:, 1] - y_slice) <= tolerance
    points = centres[mask] * 1000.0
    values = temperature[mask]
    image = axis.scatter(
        points[:, 0],
        points[:, 2],
        c=values,
        s=10,
        cmap="inferno",
        vmin=303.15,
        vmax=SOLVER_TMAX_K,
    )
    axis.set_title(title)
    axis.set_xlabel("x (mm)")
    axis.set_ylabel("z (mm)")
    axis.set_aspect("equal", adjustable="box")
    return image


def make_summary_image(output: Path, states: dict[int, dict], melt_pools: dict[int, dict], report: dict) -> Path:
    nominal = states[500]
    powers = sorted(states)
    peak_temperatures = [states[power]["temperature_max_k"] for power in powers]
    p99_temperatures = [states[power]["temperature_p99_k"] for power in powers]
    lengths = [melt_pools[power]["maximum_length_mm"] for power in powers]
    widths = [melt_pools[power]["maximum_width_mm"] for power in powers]
    depths = [melt_pools[power]["maximum_depth_mm"] for power in powers]

    plt.style.use("dark_background")
    figure, axes = plt.subplots(1, 3, figsize=(18, 7.2), constrained_layout=False)
    figure.patch.set_facecolor("#06131c")
    figure.subplots_adjust(left=0.055, right=0.985, bottom=0.16, top=0.76, wspace=0.30)
    for axis in axes:
        axis.set_facecolor("#0c202c")

    image = plot_slice(axes[0], nominal, "500 W — coupe locale au pic thermique")
    colorbar = figure.colorbar(image, ax=axes[0], fraction=0.046, pad=0.04)
    colorbar.set_label("T (K)")
    axes[0].axhline(0, color="#55c8e8", linewidth=1, alpha=0.7)

    axes[1].plot(powers, peak_temperatures, "o-", color="#ff5964", linewidth=2, label="maximum borne")
    axes[1].plot(powers, p99_temperatures, "o-", color="#ffbf55", linewidth=2, label="P99 du champ")
    axes[1].axhline(LIQUIDUS_K, color="#55c8e8", linestyle="--", label="liquidus 870 K")
    axes[1].axhline(SOLVER_TMAX_K, color="#ff5964", linestyle=":", label="plafond solveur")
    axes[1].set_title("Sensibilite de puissance")
    axes[1].set_xlabel("puissance laser (W)")
    axes[1].set_ylabel("temperature maximale (K)")
    axes[1].legend()
    axes[1].grid(alpha=0.2)

    axes[2].plot(powers, lengths, "o-", label="longueur x")
    axes[2].plot(powers, widths, "o-", label="largeur y")
    axes[2].plot(powers, depths, "o-", label="profondeur z")
    axes[2].set_title("Dimensions du bain fondu")
    axes[2].set_xlabel("puissance laser (W)")
    axes[2].set_ylabel("dimension aux centres de cellules (mm)")
    axes[2].legend()
    axes[2].grid(alpha=0.2)

    figure.suptitle(
        "F41 — ORNL AdditiveFOAM / ZRapid iSLM420DN / AlSi10Mg\n"
        "coupon local 2 couches de 40 um; 1300 mm/s; hatch 0,10 mm; spot publie 80 um",
        fontsize=17,
        fontweight="bold",
        y=0.96,
    )
    figure.text(
        0.5,
        0.035,
        "Ecran numerique non calibre fournisseur — ne constitue pas une autorisation d'impression de la culasse.",
        ha="center",
        color="#ffbf55",
        fontsize=11,
    )
    image_path = output / "917-head-lpbf-additivefoam-f41.png"
    figure.savefig(image_path, dpi=170, facecolor=figure.get_facecolor())
    plt.close(figure)
    return image_path


def make_video(output: Path, nominal_states: list[dict]) -> Path | None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None or len(nominal_states) < 2:
        return None
    frames = output / "video-frames"
    if frames.exists():
        shutil.rmtree(frames)
    frames.mkdir()
    plt.style.use("dark_background")
    for index, state in enumerate(nominal_states):
        figure, axis = plt.subplots(figsize=(9, 5.5), constrained_layout=True)
        figure.patch.set_facecolor("#06131c")
        axis.set_facecolor("#0c202c")
        image = plot_slice(axis, state, f"F41 — AdditiveFOAM 500 W — etape {index + 1}/{len(nominal_states)}")
        colorbar = figure.colorbar(image, ax=axis)
        colorbar.set_label("T (K)")
        figure.text(0.5, 0.01, "Coupon local AlSi10Mg; simulation non qualifiee fournisseur", ha="center", color="#ffbf55")
        figure.savefig(frames / f"frame-{index:04d}.png", dpi=140, facecolor=figure.get_facecolor())
        plt.close(figure)

    video = output / "917-head-lpbf-additivefoam-f41.mp4"
    result = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-framerate",
            "2",
            "-i",
            str(frames / "frame-%04d.png"),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(video),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    shutil.rmtree(frames)
    return video if result.returncode == 0 else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads(args.run_report.read_text(encoding="utf-8"))
    args.output.mkdir(parents=True, exist_ok=True)
    states: dict[int, dict] = {}
    melt_pools: dict[int, dict] = {}
    time_series: dict[int, list[dict]] = {}
    for power_text, run in report["sensitivities"].items():
        power = int(power_text)
        case = Path(run["run_log"]).parent
        files = sorted(
            (case / "layer1/VTK").glob("*.vtk"),
            key=lambda path: int(re.search(r"_(\d+)\.vtk$", path.name).group(1))
            if re.search(r"_(\d+)\.vtk$", path.name)
            else -1,
        )
        if not files:
            raise RuntimeError(f"vtk_absent:{case}")
        series = [read_state(path) for path in files]
        time_series[power] = series
        states[power] = max(
            series,
            key=lambda item: (item["temperature_max_k"], item["temperature_p99_k"]),
        )
        melt_pools[power] = read_solver_melt_pool(case)

    if 500 not in states:
        raise RuntimeError("cas_nominal_500W_absent")
    finite = all(state["finite"] for state in states.values())
    molten = all(state["molten_cell_count"] > 0 for state in states.values())
    cap_free = all(not state["solver_temperature_cap_hit"] for state in states.values())
    monotonic = all(
        states[a]["temperature_max_k"] <= states[b]["temperature_max_k"]
        for a, b in zip(sorted(states)[:-1], sorted(states)[1:], strict=True)
    )
    p99_monotonic = all(
        states[a]["temperature_p99_k"] < states[b]["temperature_p99_k"]
        for a, b in zip(sorted(states)[:-1], sorted(states)[1:], strict=True)
    )

    report["results"] = {
        str(power): {
            **public_metrics(states[power]),
            "solver_melt_pool_dimensions": melt_pools[power],
        }
        for power in sorted(states)
    }
    report["gates"].update(
        {
            "all_fields_finite": finite,
            "all_cases_melt_AlSi10Mg": molten,
            "temperature_cap_not_hit": cap_free,
            "peak_temperature_monotonic_with_power": monotonic,
            "temperature_p99_strictly_increases_with_power": p99_monotonic,
            "local_process_screen_passes": finite and molten and cap_free and p99_monotonic,
            "supplier_parameter_card_qualified": False,
            "physical_coupon_qualified": False,
            "metal_print_authorized": False,
        }
    )

    image = make_summary_image(args.output, states, melt_pools, report)
    video = make_video(args.output, time_series[500])
    report["artifacts"] = {
        image.name: {"sha256": sha256(image), "bytes": image.stat().st_size},
    }
    if video is not None:
        report["artifacts"][video.name] = {"sha256": sha256(video), "bytes": video.stat().st_size}

    final_report = args.output / "917-head-lpbf-additivefoam-f41-report.json"
    report["artifacts"][final_report.name] = {"self_hash_excluded": True}
    final_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(final_report), "gates": report["gates"]}, sort_keys=True))
    return 0 if report["gates"]["local_process_screen_passes"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
