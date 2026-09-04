#!/usr/bin/env python3
"""Simulation thermique macroscopique par activation de voxels de la F41.

Le modele resout explicitement la diffusion 3D, la convection et le rayonnement
sur une grille cartésienne remplie par le STL. Il couvre la piece complete mais
homogeneise le laser et les couches; il ne remplace pas AdditiveFOAM local.
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
import numpy as np
import trimesh


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def shifted(values: np.ndarray, axis: int, offset: int, fill) -> np.ndarray:
    result = np.full_like(values, fill)
    source = [slice(None)] * 3
    destination = [slice(None)] * 3
    if offset > 0:
        source[axis] = slice(0, -offset)
        destination[axis] = slice(offset, None)
    else:
        source[axis] = slice(-offset, None)
        destination[axis] = slice(0, offset)
    result[tuple(destination)] = values[tuple(source)]
    return result


def transform_y_down(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    transformed = mesh.copy()
    matrix = np.asarray(
        [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, -1.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )
    transformed.apply_transform(matrix)
    transformed.apply_translation(-transformed.bounds[0])
    return transformed


def material_fields(temperature: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Carte AlSi10Mg d'AdditiveFOAM 9c05c5e, avec chaleur latente lissée."""
    conductivity = 78.0 + 0.108 * temperature
    heat_capacity = 780.0 + 0.40 * temperature
    phase = (temperature >= 850.0) & (temperature <= 870.0)
    heat_capacity = heat_capacity + phase * (3.9e5 / 20.0)
    return conductivity, heat_capacity


def render(occupancy: np.ndarray, dose: np.ndarray, final: np.ndarray, history: dict, destination: Path) -> None:
    figure, axes = plt.subplots(2, 2, figsize=(14, 9), facecolor="#07131b")
    figure.suptitle("F41 — IMPRESSION LPBF VIRTUELLE, MODELE MACRO 3D", color="white", fontsize=18, fontweight="bold")
    slices = [occupancy.shape[0] // 2, occupancy.shape[1] // 2]
    fields = [
        (np.where(occupancy[slices[0]], final[slices[0]], np.nan), "Temperature finale — coupe X", "inferno", "K"),
        (np.where(occupancy[:, slices[1], :], final[:, slices[1], :], np.nan), "Temperature finale — coupe Y", "inferno", "K"),
        (np.where(occupancy[slices[0]], dose[slices[0]], np.nan), "Dose thermique au-dessus du plateau — coupe X", "magma", "K.s"),
    ]
    for axis, (field, title, colormap, unit) in zip(axes.flat[:3], fields, strict=True):
        axis.set_facecolor("#0d202b")
        image = axis.imshow(field.T, origin="lower", cmap=colormap, interpolation="nearest", aspect="auto")
        axis.set_title(title, color="white", fontweight="bold")
        axis.set_xlabel("voxel", color="#c9d5dc")
        axis.set_ylabel("couche", color="#c9d5dc")
        axis.tick_params(colors="#c9d5dc")
        bar = figure.colorbar(image, ax=axis, fraction=0.046, pad=0.03)
        bar.set_label(unit, color="white")
        bar.ax.tick_params(colors="white")

    chart = axes.flat[3]
    chart.set_facecolor("#0d202b")
    chart.plot(history["macro_layer"], history["mean_temperature_k"], color="#ff6f4f", label="T moyenne")
    chart.plot(history["macro_layer"], history["p95_temperature_k"], color="#68c8e8", label="T p95")
    chart.set_title("Activation séquentielle de toute la pièce", color="white", fontweight="bold")
    chart.set_xlabel("macro-couche voxel", color="#c9d5dc")
    chart.set_ylabel("K", color="#c9d5dc")
    chart.tick_params(colors="#c9d5dc")
    chart.grid(alpha=0.18)
    chart.legend(facecolor="#0d202b", labelcolor="white")
    for axis in axes.flat:
        for spine in axis.spines.values():
            spine.set_color("#35505e")
    figure.text(
        0.5,
        0.025,
        "Diffusion 3D + convection + rayonnement; laser et 50 µm homogénéisés en macro-couches. Paramètres non calibrés fournisseur.",
        color="#efc36a",
        ha="center",
        fontsize=10,
    )
    figure.tight_layout(rect=(0.02, 0.05, 0.98, 0.94))
    figure.savefig(destination, dpi=170, facecolor=figure.get_facecolor())
    plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--head", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pitch-mm", type=float, default=2.0)
    parser.add_argument("--steps-per-layer", type=int, default=12)
    args = parser.parse_args()
    if not 1.5 <= args.pitch_mm <= 3.0:
        raise ValueError("pitch_hors_domaine")
    args.output.mkdir(parents=True, exist_ok=True)

    mesh = trimesh.load_mesh(args.head, process=True)
    if not isinstance(mesh, trimesh.Trimesh) or not mesh.is_watertight:
        raise RuntimeError("maillage_non_etanche")
    oriented = transform_y_down(mesh)
    voxels = oriented.voxelized(args.pitch_mm).fill()
    occupancy = np.asarray(voxels.matrix, dtype=bool)

    rho = 2670.0
    dx = args.pitch_mm / 1000.0
    sampled_temperature = np.linspace(300.0, activation_temperature := 1100.0, 801)
    sampled_k, sampled_cp = material_fields(sampled_temperature)
    maximum_diffusivity = float(np.max(sampled_k / (rho * sampled_cp)))
    dt_limit = dx * dx / (6.0 * maximum_diffusivity)
    dt = 0.65 * dt_limit
    ambient = 300.0
    plate = 473.0
    convection = 12.0
    emissivity = 0.4
    sigma = 5.670374419e-8

    active = np.zeros_like(occupancy)
    temperature = np.full(occupancy.shape, ambient, dtype=np.float32)
    peak = temperature.copy()
    dose = np.zeros_like(temperature)
    history = {"macro_layer": [], "mean_temperature_k": [], "p95_temperature_k": []}
    for layer in range(occupancy.shape[2]):
        newly_active = occupancy[:, :, layer]
        active[:, :, layer] = newly_active
        temperature[:, :, layer][newly_active] = activation_temperature
        for _ in range(args.steps_per_layer):
            neighbour_sum = np.zeros_like(temperature)
            neighbour_count = np.zeros_like(temperature, dtype=np.uint8)
            for axis in range(3):
                for offset in (-1, 1):
                    neighbour_active = shifted(active, axis, offset, False)
                    neighbour_sum += shifted(temperature, axis, offset, ambient) * neighbour_active
                    neighbour_count += neighbour_active
            laplacian = neighbour_sum - neighbour_count * temperature
            local_k, local_cp = material_fields(temperature)
            local_diffusivity = local_k / (rho * local_cp)
            next_temperature = temperature + (local_diffusivity * dt / (dx * dx)) * laplacian
            exposed_faces = 6 - neighbour_count
            surface_temperature = np.maximum(temperature, ambient)
            h_radiation = emissivity * sigma * (surface_temperature + ambient) * (
                surface_temperature * surface_temperature + ambient * ambient
            )
            loss = (convection + h_radiation) * exposed_faces * dt / (rho * local_cp * dx)
            next_temperature -= loss * (temperature - ambient)
            temperature[active] = np.maximum(next_temperature[active], ambient)
            base = active[:, :, 0]
            temperature[:, :, 0][base] = plate
            peak[active] = np.maximum(peak[active], temperature[active])
            dose[active] += np.maximum(temperature[active] - plate, 0.0) * dt
        values = temperature[active]
        history["macro_layer"].append(layer)
        history["mean_temperature_k"].append(float(np.mean(values)))
        history["p95_temperature_k"].append(float(np.quantile(values, 0.95)))

    for _ in range(300):
        neighbour_sum = np.zeros_like(temperature)
        neighbour_count = np.zeros_like(temperature, dtype=np.uint8)
        for axis in range(3):
            for offset in (-1, 1):
                neighbour_sum += shifted(temperature, axis, offset, ambient) * shifted(active, axis, offset, False)
                neighbour_count += shifted(active, axis, offset, False)
        laplacian = neighbour_sum - neighbour_count * temperature
        local_k, local_cp = material_fields(temperature)
        local_diffusivity = local_k / (rho * local_cp)
        next_temperature = temperature + (local_diffusivity * dt / (dx * dx)) * laplacian
        exposed_faces = 6 - neighbour_count
        surface_temperature = np.maximum(temperature, ambient)
        h_radiation = emissivity * sigma * (surface_temperature + ambient) * (
            surface_temperature * surface_temperature + ambient * ambient
        )
        loss = (convection + h_radiation) * exposed_faces * dt / (rho * local_cp * dx)
        next_temperature -= loss * (temperature - ambient)
        temperature[active] = np.maximum(next_temperature[active], ambient)
        temperature[:, :, 0][active[:, :, 0]] = plate
        dose[active] += np.maximum(temperature[active] - plate, 0.0) * dt

    active_peak = peak[occupancy]
    active_final = temperature[occupancy]
    gradient = np.gradient(temperature.astype(np.float64), dx)
    gradient_magnitude = np.sqrt(sum(component * component for component in gradient))
    strain = 21.5e-6 * np.maximum(active_peak - plate, 0.0)
    field_path = args.output / "917-head-lpbf-macro-f41-fields.npz"
    np.savez_compressed(
        field_path,
        occupancy=occupancy,
        peak_temperature_k=peak,
        final_temperature_k=temperature,
        thermal_dose_above_plate_k_s=dose,
    )
    image_path = args.output / "917-head-lpbf-macro-f41.png"
    render(occupancy, dose, temperature, history, image_path)
    report = {
        "schema_version": "1.0.0",
        "phase": "F41",
        "method": "A_macro_voxel_layer_activation_explicit_heat_diffusion_convection_radiation",
        "classification": "whole_part_virtual_process_screen_not_calibrated_machine_simulation",
        "input": {"path": args.head.name, "sha256": sha256(args.head)},
        "grid": {
            "pitch_mm": args.pitch_mm,
            "shape": list(occupancy.shape),
            "solid_voxels": int(np.count_nonzero(occupancy)),
            "macro_layer_count": int(occupancy.shape[2]),
            "represented_physical_50_um_layers": int(math.ceil(oriented.extents[2] / 0.05)),
        },
        "material_assumptions": {
            "alloy": "AlSi10Mg",
            "density_kg_m3": rho,
            "solid_heat_capacity_polynomial_j_kg_k": [780.0, 0.40, 0.0],
            "solid_conductivity_polynomial_w_m_k": [78.0, 0.108, 0.0],
            "latent_heat_j_kg": 3.9e5,
            "phase_path_k": [[850.0, 1.0], [870.0, 0.0]],
            "source": "ORNL_AdditiveFOAM_9c05c5e_etc_materials_AlSi10Mg.cfg",
            "thermal_expansion_1_k": 21.5e-6,
            "temperature_dependence_included": True,
        },
        "boundary_and_source_assumptions": {
            "ambient_temperature_k": ambient,
            "plate_temperature_k": plate,
            "activation_temperature_k": activation_temperature,
            "convection_w_m2_k": convection,
            "emissivity": emissivity,
            "laser_scan_path_resolved": False,
        },
        "numerics": {
            "time_step_s": dt,
            "explicit_stability_limit_s": dt_limit,
            "steps_per_macro_layer": args.steps_per_layer,
            "post_build_cooling_steps": 300,
        },
        "results": {
            "maximum_temperature_k": float(np.max(active_peak)),
            "p99_peak_temperature_k": float(np.quantile(active_peak, 0.99)),
            "final_maximum_temperature_k": float(np.max(active_final)),
            "maximum_temperature_gradient_k_m": float(np.max(gradient_magnitude[occupancy])),
            "p99_temperature_gradient_k_m": float(np.quantile(gradient_magnitude[occupancy], 0.99)),
            "maximum_free_thermal_strain_proxy": float(np.max(strain)),
            "maximum_thermal_dose_above_plate_k_s": float(np.max(dose[occupancy])),
            "p95_thermal_dose_above_plate_k_s": float(np.quantile(dose[occupancy], 0.95)),
        },
        "files": {
            "fields": {"path": field_path.name, "sha256": sha256(field_path), "bytes": field_path.stat().st_size},
            "image": {"path": image_path.name, "sha256": sha256(image_path), "bytes": image_path.stat().st_size},
        },
        "gates": {
            "whole_part_activated": True,
            "explicit_scheme_stable_by_fourier_limit": dt < dt_limit,
            "mesh_convergence_complete": False,
            "temperature_dependent_coupon_card_used": False,
            "machine_scan_strategy_calibrated": False,
            "lpbf_process_released": False,
        },
    }
    report_path = args.output / "917-head-lpbf-macro-f41-report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(report_path), "results": report["results"], "gates": report["gates"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
