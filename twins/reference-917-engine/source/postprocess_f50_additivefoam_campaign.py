#!/usr/bin/env python3
"""Sanitize and evaluate the private F50 AdditiveFOAM coupon campaign."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


CAP_K = 3300.0
LIQUIDUS_K = 870.0


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def numeric_suffix(path: Path) -> int:
    match = re.search(r"_(\d+)\.vtk$", path.name)
    return int(match.group(1)) if match else -1


def tetra_volumes(points: np.ndarray) -> np.ndarray:
    return np.abs(np.einsum("ij,ij->i", np.cross(points[:, 1] - points[:, 0], points[:, 2] - points[:, 0]), points[:, 3] - points[:, 0])) / 6.0


def block_volumes(points: np.ndarray, cell_type: str, cells: np.ndarray) -> np.ndarray:
    xyz = points[cells]
    if cell_type == "tetra":
        return tetra_volumes(xyz)
    if cell_type == "hexahedron":
        splits = ((0, 1, 3, 4), (1, 2, 3, 6), (1, 3, 4, 6), (1, 4, 5, 6), (3, 4, 6, 7))
        return sum((tetra_volumes(xyz[:, indices, :]) for indices in splits), start=np.zeros(len(cells)))
    if cell_type == "wedge":
        splits = ((0, 1, 2, 3), (1, 2, 3, 4), (2, 3, 4, 5))
        return sum((tetra_volumes(xyz[:, indices, :]) for indices in splits), start=np.zeros(len(cells)))
    if cell_type == "pyramid":
        return tetra_volumes(xyz[:, (0, 1, 2, 4), :]) + tetra_volumes(xyz[:, (0, 2, 3, 4), :])
    raise RuntimeError(f"unsupported_volume_cell_type:{cell_type}")


def read_state(path: Path) -> dict[str, float | bool]:
    import meshio

    mesh = meshio.read(path)
    temperatures = mesh.cell_data.get("T")
    if temperatures is None:
        raise RuntimeError(f"cell_temperature_missing:{path.name}")
    if len(temperatures) != len(mesh.cells):
        raise RuntimeError(f"temperature_block_mismatch:{path.name}")
    temperature_blocks = []
    volume_blocks = []
    for block, values in zip(mesh.cells, temperatures, strict=True):
        if block.type not in {"tetra", "hexahedron", "wedge", "pyramid"}:
            continue
        values = np.asarray(values, dtype=float).reshape(-1)
        if len(values) != len(block.data):
            raise RuntimeError(f"temperature_cell_count_mismatch:{path.name}:{block.type}")
        temperature_blocks.append(values)
        volume_blocks.append(block_volumes(np.asarray(mesh.points, dtype=float), block.type, np.asarray(block.data, dtype=np.int64)))
    if not temperature_blocks:
        raise RuntimeError(f"vtk_without_volume_cells:{path.name}")
    temperature = np.concatenate(temperature_blocks)
    volume = np.concatenate(volume_blocks)
    molten = temperature >= LIQUIDUS_K
    return {
        "temperature_max_k": float(np.max(temperature)),
        "temperature_p99_k": float(np.quantile(temperature, 0.99)),
        "molten_volume_mm3": float(np.sum(volume[molten]) * 1.0e9),
        "finite": bool(np.isfinite(temperature).all() and np.isfinite(volume).all()),
    }


def melt_pool_dimensions(case: Path) -> dict[str, float]:
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
        raise RuntimeError(f"melt_pool_dimensions_missing:{case.name}")
    return {
        "melt_pool_length_mm": max(row["length"] for row in rows),
        "melt_pool_width_mm": max(row["width"] for row in rows),
        "melt_pool_depth_mm": max(row["depth"] for row in rows),
    }


def evaluate_case(entry: dict) -> dict:
    configured = entry["configured"]
    result = entry["result"]
    case = Path(configured["case_path"])
    build_evidence = []
    for log_path in [case / "f50-additivefoam-run.log", *sorted(case.glob("layer*/log.additiveFoam"))]:
        build_evidence.extend(re.findall(r"^Build\s+:\s+(\S+)", log_path.read_text(encoding="utf-8", errors="replace"), re.MULTILINE))
    builds = sorted(set(build_evidence))
    if len(builds) != 1:
        raise RuntimeError(f"openfoam_build_ambiguous:{case.name}:{builds}")
    paths = sorted((case / "layer1/VTK").glob("layer1_*.vtk"), key=numeric_suffix)
    if not paths:
        raise RuntimeError(f"vtk_missing:{case.name}")
    states = [read_state(path) for path in paths]
    hottest = max(states, key=lambda item: (item["temperature_max_k"], item["temperature_p99_k"]))
    maximum_co = max(
        float(layer["maximum_courant_number"])
        for layer in result["layer_log_checks"]
        if layer["maximum_courant_number"] is not None
    )
    cap_hit = hottest["temperature_max_k"] >= CAP_K - 1.0
    return {
        "completed": bool(result["completed"]),
        "finite": bool(hottest["finite"]),
        **{key: configured["process"][key] for key in ("laser_power_w", "scan_speed_mm_s", "hatch_spacing_mm")},
        "layer_thickness_mm": 0.05,
        "volumetric_energy_density_j_mm3": configured["process"]["laser_power_w"]
        / (configured["process"]["scan_speed_mm_s"] * configured["process"]["hatch_spacing_mm"] * 0.05),
        "resolution": configured["resolution"],
        **hottest,
        **melt_pool_dimensions(case),
        "maximum_courant_number": maximum_co,
        "temperature_cap_hit": cap_hit,
        "numerical_case_pass": bool(
            result["completed"]
            and hottest["finite"]
            and maximum_co <= 0.5
            and not cap_hit
        ),
        "configuration_sha256": configured["configuration_sha256"],
        "run_log_sha256": result["run_log_sha256"],
        "layer_log_sha256": [item["sha256"] for item in result["layer_log_checks"]],
        "vtk_state_count": len(paths),
        "openfoam_runtime_build": builds[0],
    }


def rel_diff(a: float, b: float) -> float:
    scale = max(abs(a), abs(b))
    return 0.0 if scale == 0.0 else abs(a - b) / scale


def compare(a: dict, b: dict) -> dict:
    differences = {
        key: rel_diff(float(a[key]), float(b[key]))
        for key in (
            "temperature_p99_k",
            "molten_volume_mm3",
            "melt_pool_length_mm",
            "melt_pool_width_mm",
            "melt_pool_depth_mm",
        )
    }
    return differences


def render(path: Path, cases: dict[str, dict], report: dict) -> None:
    ordered = sorted(cases)
    labels = [key.replace("published_witness", "witness").replace("low_ved_screen", "lowVED") for key in ordered]
    temperatures = [cases[key]["temperature_p99_k"] for key in ordered]
    lengths = [cases[key]["melt_pool_length_mm"] for key in ordered]
    widths = [cases[key]["melt_pool_width_mm"] for key in ordered]
    depths = [cases[key]["melt_pool_depth_mm"] for key in ordered]
    figure, axes = plt.subplots(2, 2, figsize=(15, 9), facecolor="#07131b")
    figure.suptitle("F50 — ADDITIVEFOAM MULTILAYERPBF — COUPONS DE REFERENCE", color="white", fontsize=18, weight="bold")
    plots = [
        (axes[0, 0], temperatures, "Temperature P99", "K", "#ff7849"),
        (axes[0, 1], lengths, "Longueur maximale du bain", "mm", "#4cc9f0"),
        (axes[1, 0], widths, "Largeur maximale du bain", "mm", "#90be6d"),
        (axes[1, 1], depths, "Profondeur maximale du bain", "mm", "#f9c74f"),
    ]
    x = np.arange(len(labels))
    for axis, values, title, unit, color in plots:
        axis.set_facecolor("#10212d")
        axis.bar(x, values, color=color)
        axis.set_title(title, color="white", weight="bold")
        axis.set_ylabel(unit, color="#d7e4ec")
        axis.set_xticks(x, labels, rotation=30, ha="right", fontsize=7)
        axis.tick_params(colors="#d7e4ec")
        axis.grid(axis="y", alpha=0.18)
    figure.text(
        0.5,
        0.015,
        "Modele AlSi10Mg F42 non calibre CP1 — coupons locaux, jamais une distorsion pleine culasse — impression et demarrage interdits.",
        color="#ffb4a2",
        ha="center",
        fontsize=10,
    )
    figure.tight_layout(rect=(0.02, 0.06, 0.98, 0.94))
    figure.savefig(path, dpi=170, facecolor=figure.get_facecolor())
    plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-run-manifest", type=Path, required=True)
    parser.add_argument("--geometry-report-2v", type=Path, required=True)
    parser.add_argument("--geometry-report-4v", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    private = json.loads(args.private_run_manifest.read_text(encoding="utf-8"))
    geometry = {
        "2v": json.loads(args.geometry_report_2v.read_text(encoding="utf-8")),
        "4v": json.loads(args.geometry_report_4v.read_text(encoding="utf-8")),
    }
    if private["master_hashes"] != {variant: geometry[variant]["master"]["sha256"] for variant in ("2v", "4v")}:
        raise SystemExit("geometry_and_campaign_master_hash_mismatch")
    cases = {key: evaluate_case(entry) for key, entry in sorted(private["cases"].items())}
    nominal = cases["shared:published_witness:nominal"]
    fine = cases["shared:published_witness:fine"]
    delta = compare(nominal, fine)
    convergence = {
        "nominal_to_fine_relative_difference": delta,
        "passes": bool(
            nominal["numerical_case_pass"]
            and fine["numerical_case_pass"]
            and delta["temperature_p99_k"] <= 0.03
            and delta["molten_volume_mm3"] <= 0.05
            and all(delta[key] <= 0.05 for key in ("melt_pool_length_mm", "melt_pool_width_mm", "melt_pool_depth_mm"))
        ),
    }
    all_numerical = all(item["numerical_case_pass"] for item in cases.values())
    all_solver_runs = all(item["completed"] and item["finite"] for item in cases.values())
    all_converged = convergence["passes"]
    report = {
        "schema_version": "1.0.0",
        "phase": "F50",
        "classification": "sanitized_hash-linked_AdditiveFOAM_coupon_campaign_not_full-head_distortion",
        "master_hashes": private["master_hashes"],
        "software": {
            **private["software"],
            "observed_openfoam_runtime_builds": sorted({item["openfoam_runtime_build"] for item in cases.values()}),
        },
        "method": {
            "solver": "ORNL AdditiveFOAM multiLayerPBF",
            "governing_equation": "rho*cp*dT/dt = div(k*grad(T)) + Q_laser - Q_losses + Q_latent",
            "layers_per_case": 2,
            "temperature_limit_k": CAP_K,
            "temperature_cap_policy": "right-censored and fail-closed at >=3299 K",
            "reference": "https://github.com/ORNL/AdditiveFOAM",
        },
        "material_model": private["material_model"],
        "representativity": {
            "2v_thickness_p01_mm": geometry["2v"]["thickness_screen"]["p01_mm"],
            "4v_thickness_p01_mm": geometry["4v"]["thickness_screen"]["p01_mm"],
            "published_witness_role": "local melt-pool control for thin-feature process risk; no cylinder-head sector geometry",
            "low_ved_screen_role": "local lower-energy sensitivity; no bulk-head or support geometry",
            "full_head_distortion_simulated": False,
            "reason": "No complete CP1 hot constitutive and process-calibration card exists; inventing it is prohibited.",
        },
        "cases": cases,
        "resolution_convergence": convergence,
        "two_variant_process_binding": {
            "2v_master_sha256": private["master_hashes"]["2v"],
            "4v_master_sha256": private["master_hashes"]["4v"],
            "shared_local_witness": True,
            "interpretation": "The process witness is architecture-independent and is not duplicated. The full-piece geometric method, not this coupon, compares 2V and 4V.",
        },
        "gates": {
            "four_hash_linked_solver_runs_completed": len(cases) == 4 and all_solver_runs,
            "all_numerical_case_gates_passed": all_numerical,
            "temperature_cap_free": all(not item["temperature_cap_hit"] for item in cases.values()),
            "witness_nominal_to_fine_converged": all_converged,
            "target_CP1_material_card_used": False,
            "full_head_thermomechanical_distortion_simulated": False,
            "supplier_process_calibrated": False,
            "physical_coupon_qualified": False,
            "metal_print_authorized": False,
            "engine_start_authorized": False,
        },
        "verdict": "reference_coupon_numerics_evaluated_but_target_process_and_full_build_not_qualified",
    }
    args.output.mkdir(parents=True, exist_ok=True)
    csv_path = args.output / "917-head-f50-additivefoam-cases.csv"
    public_columns = [
        "case_id", "completed", "finite", "numerical_case_pass", "laser_power_w", "scan_speed_mm_s",
        "hatch_spacing_mm", "layer_thickness_mm", "volumetric_energy_density_j_mm3", "resolution",
        "temperature_max_k", "temperature_p99_k", "temperature_cap_hit", "molten_volume_mm3",
        "melt_pool_length_mm", "melt_pool_width_mm", "melt_pool_depth_mm", "maximum_courant_number",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=public_columns, lineterminator="\n")
        writer.writeheader()
        for key, item in cases.items():
            writer.writerow({"case_id": key, **{name: item[name] for name in public_columns if name != "case_id"}})
    report_path = args.output / "917-head-f50-additivefoam-report.json"
    report["publication"] = {"cases_csv": csv_path.name, "cases_csv_sha256": sha256(csv_path), "contains_private_paths_or_geometry": False}
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    image_path = args.output / "917-head-f50-additivefoam-coupons.png"
    render(image_path, cases, report)
    manifest = {
        "report": {"path": report_path.name, "sha256": sha256(report_path)},
        "cases": {"path": csv_path.name, "sha256": sha256(csv_path)},
        "image": {"path": image_path.name, "sha256": sha256(image_path)},
    }
    (args.output / "917-head-f50-additivefoam-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"cases": len(cases), "gates": report["gates"]}, sort_keys=True))
    return 0 if all_numerical and all_converged else 2


if __name__ == "__main__":
    raise SystemExit(main())
