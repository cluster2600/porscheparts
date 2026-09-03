#!/usr/bin/env python3
"""Rend une planche F36 lisible sans inventer de contour de simulation."""

from __future__ import annotations

import argparse
import json
import math
import struct
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


def load_stl_triangles(path: Path) -> np.ndarray:
    payload = path.read_bytes()
    if len(payload) >= 84:
        count = struct.unpack_from("<I", payload, 80)[0]
        if len(payload) == 84 + count * 50:
            values = np.frombuffer(payload, dtype=np.uint8, offset=84).reshape(count, 50)
            return values[:, 12:48].copy().view("<f4").reshape(count, 3, 3).astype(float)
    vertices = []
    for line in payload.decode("ascii", errors="ignore").splitlines():
        fields = line.strip().split()
        if len(fields) == 4 and fields[0] == "vertex":
            vertices.append([float(value) for value in fields[1:]])
    if not vertices or len(vertices) % 3:
        raise SystemExit("STL binaire ou ASCII invalide")
    return np.asarray(vertices, dtype=float).reshape(-1, 3, 3)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stl", type=Path, required=True)
    parser.add_argument("--product-image", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    mesh_triangles = load_stl_triangles(args.stl)

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})
    fig = plt.figure(figsize=(16, 9), facecolor="#eef1f3")
    grid = fig.add_gridspec(2, 3, width_ratios=(1.45, 1.0, 1.0), hspace=0.28, wspace=0.23)

    if args.product_image is not None:
        ax_mesh = fig.add_subplot(grid[:, 0], facecolor="#10202a")
        product = plt.imread(args.product_image)
        height, width = product.shape[:2]
        crop = product[int(0.17 * height) : int(0.48 * height), int(0.12 * width) : int(0.40 * width)]
        ax_mesh.imshow(crop)
        ax_mesh.set_axis_off()
        ax_mesh.set_title("Peau extérieure F36 issue du scan\n(ailettes et bossages conservés)", color="#18242b", pad=14, weight="bold")
        ax_mesh.text(
            0.04,
            0.035,
            "Air forcé : +Y → −Y dans le repère du scan\nÉchelle OBJ plausible en mm, non confirmée",
            transform=ax_mesh.transAxes,
            color="#dbe5eb",
        )
    else:
        ax_mesh = fig.add_subplot(grid[:, 0], projection="3d", facecolor="#10202a")
        stride = max(1, math.ceil(len(mesh_triangles) / 18_000))
        triangles = mesh_triangles[::stride]
        collection = Poly3DCollection(triangles, linewidths=0.0, alpha=1.0)
        collection.set_facecolor("#b98b45")
        ax_mesh.add_collection3d(collection)
        bounds = np.asarray([mesh_triangles.min(axis=(0, 1)), mesh_triangles.max(axis=(0, 1))])
        centre = bounds.mean(axis=0)
        extent = float(np.max(bounds[1] - bounds[0])) * 0.55
        ax_mesh.set_xlim(centre[0] - extent, centre[0] + extent)
        ax_mesh.set_ylim(centre[1] - extent, centre[1] + extent)
        ax_mesh.set_zlim(centre[2] - extent, centre[2] + extent)
        ax_mesh.view_init(elev=22, azim=-52)
        ax_mesh.set_axis_off()
        ax_mesh.set_title("Peau extérieure F36 issue du scan\n(ailettes et bossages conservés)", color="white", pad=14, weight="bold")
        ax_mesh.text2D(
            0.04,
            0.04,
            "Air forcé : +Y → −Y dans le repère du scan\nÉchelle OBJ plausible en mm, non confirmée",
            transform=ax_mesh.transAxes,
            color="#dbe5eb",
        )

    ax_cfd = fig.add_subplot(grid[0, 1])
    openfoam = [case for case in report["openfoam_external_air"]["cases"] if "results" in case]
    labels = [case["mesh_id"] for case in openfoam]
    heat_kw = [case["results"]["wall_heat_rejection_w"] / 1000.0 for case in openfoam]
    ax_cfd.bar(labels, heat_kw, color="#2474a6", label="OpenFOAM RANS")
    fluidx = [case for case in report["fluidx3d_external_air"]["cases"] if case.get("numerically_stable")]
    if fluidx:
        ax_cfd.axhline(fluidx[-1]["heat_rejection_w"] / 1000.0, color="#c9503e", linewidth=2.0, label="FluidX3D LBM")
    ax_cfd.set_ylabel("Chaleur extraite [kW]")
    ax_cfd.set_title("Refroidissement externe à 0,85 kg/s\nTair 308 K · paroi imposée 533 K", weight="bold")
    ax_cfd.grid(axis="y", alpha=0.25)
    ax_cfd.legend(frameon=False, fontsize=8)

    ax_dp = fig.add_subplot(grid[0, 2])
    pressure = [case["results"]["pressure_drop_pa"] for case in openfoam]
    ax_dp.bar(labels, pressure, color="#398b74")
    ax_dp.set_ylabel("Perte de charge [Pa]")
    ax_dp.set_title("Coût aérodynamique du refroidissement", weight="bold")
    ax_dp.grid(axis="y", alpha=0.25)

    ax_fea = fig.add_subplot(grid[1, 1])
    cases = report["calculix_thermomechanical"]["cases"]
    pitch = [case["mesh"]["pitch_mm_if_obj_unit_is_mm"] for case in cases]
    p95 = [case["results"]["von_mises_p95_mpa"] for case in cases]
    maximum = [case["results"]["von_mises_max_mpa"] for case in cases]
    hot_yield = cases[-1]["material"]["hot_yield_mpa_at_250c"]
    ax_fea.plot(pitch, p95, "o-", color="#2474a6", label="Von Mises p95")
    ax_fea.plot(pitch, maximum, "s--", color="#c9503e", label="Maximum local")
    ax_fea.axhline(hot_yield, color="#222", linestyle=":", label=f"Rp0,2 chaud {hot_yield:.0f} MPa")
    ax_fea.invert_xaxis()
    ax_fea.set_xlabel("Pas voxel [unités OBJ, mm si échelle confirmée]")
    ax_fea.set_ylabel("Contrainte [MPa]")
    ax_fea.set_title("Écran thermo-mécanique CalculiX", weight="bold")
    ax_fea.grid(alpha=0.25)
    ax_fea.legend(frameon=False, fontsize=8)

    ax_gate = fig.add_subplot(grid[1, 2])
    ax_gate.axis("off")
    gates = report["release_gates"]
    rows = [
        ("Maillage structure p95", gates["calculix_p95_and_displacement_grid_independence"]),
        ("Pic < limite chaude", gates["calculix_peak_stress_below_hot_yield"]),
        ("CHT air/métal 3D", gates["full_3d_conjugate_heat_transfer"]),
        ("CFD interne 2V/4V fermé", gates["closed_internal_flow_domains_2v_and_4v"]),
        ("Banc de flux corrélé", gates["physical_flowbench_correlation"]),
        ("CT/CND", gates["ct_ndt"]),
        ("Impression métal autorisée", gates["metal_print_authorized"]),
    ]
    ax_gate.set_title("Portes de validation", weight="bold", loc="left")
    for index, (name, passed) in enumerate(rows):
        y = 0.88 - index * 0.115
        color = "#27855f" if passed else "#b64035"
        ax_gate.text(0.0, y, "●", color=color, fontsize=14, va="center")
        ax_gate.text(0.07, y, name, color="#1d252a", va="center")
    ax_gate.text(0.0, 0.02, "ROUGE = bloquant. Aucun feu vert impression/démarrage.", color="#8f2e28", weight="bold")

    fig.suptitle(
        "Culasse F36 quatre soupapes — recalcul multi-solveur sur la morphologie du scan",
        fontsize=17,
        weight="bold",
        color="#18242b",
        y=0.975,
    )
    fig.text(
        0.5,
        0.012,
        "ÉCRAN NUMÉRIQUE DE CONCEPTION — pas une validation physique ni une autorisation de fabrication",
        ha="center",
        color="#9b332d",
        weight="bold",
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(json.dumps({"status": "rendered", "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
