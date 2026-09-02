#!/usr/bin/env python3
"""Publie les preuves et figures de la campagne virtuelle integree F33."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REPORT = ROOT / "work/917-integrated-virtual-f33/report.json"
DEFAULT_OUTPUT = ROOT / "twins/reference-917-engine/evidence/f33"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sanitize_text(value: str, roots: list[str]) -> str:
    sanitized = value
    for root in sorted({item for item in roots if item}, key=len, reverse=True):
        replacement = (
            "${PHYSICAL_AI_SKILL_HOME}"
            if "omniverse-cad-to-simready" in root
            else "${PROJECT_ROOT}"
        )
        sanitized = sanitized.replace(root, replacement)
    return sanitized


def sanitize_value(value: Any, roots: list[str]) -> Any:
    if isinstance(value, str):
        return sanitize_text(value, roots)
    if isinstance(value, list):
        return [sanitize_value(item, roots) for item in value]
    if isinstance(value, dict):
        return {key: sanitize_value(item, roots) for key, item in value.items()}
    return value


def validate_report(report: dict[str, Any]) -> None:
    expected = "integrated_virtual_campaign_complete_not_physical_validation"
    if report.get("status") != expected:
        raise ValueError(f"F33 source report status is not publishable: {report.get('status')}")
    if not all(report.get("checks", {}).values()):
        raise ValueError("F33 source report did not pass its virtual acceptance checks")
    if any(report.get("release_gates", {}).values()):
        raise ValueError("F33 publication refuses an open physical release gate")
    if report["claims"]["manufacturing_or_engine_start_authorized"]:
        raise ValueError("F33 publication cannot authorize manufacture or engine start")


def render_integrated_comparison(report: dict[str, Any], path: Path) -> None:
    colors = {"2v": "#8c564b", "4v": "#1f77b4"}
    figure, axes = plt.subplots(2, 2, figsize=(13.2, 9.0), constrained_layout=True)

    for architecture, data in report["virtual_flowbench"]["architectures"].items():
        points = data["points"]
        axes[0, 0].plot(
            [item["lift_mm"] for item in points],
            [item["volume_flow_cfm"] for item in points],
            marker="o",
            color=colors[architecture],
            label=architecture.upper(),
        )
    axes[0, 0].set(title="Banc de flux virtuel a 6,95 kPa", xlabel="Levee [mm]", ylabel="Debit [cfm]")
    axes[0, 0].legend(frameon=False)

    target = report["zero_dimensional_engine_dyno"]["target_power_mechanical_hp"]
    for architecture, curve in report["zero_dimensional_engine_dyno"]["curves"].items():
        axes[0, 1].plot(
            [item["rpm"] for item in curve],
            [item["brake_power_mechanical_hp"] for item in curve],
            marker="o",
            color=colors[architecture],
            label=architecture.upper(),
        )
    axes[0, 1].axhline(target, color="#d62728", linestyle="--", label="Cible 1 600 ch")
    axes[0, 1].set(title="Cycle moteur 0D non correle", xlabel="Regime [tr/min]", ylabel="Puissance [ch mecaniques]")
    axes[0, 1].legend(frameon=False)

    architectures = ["2v", "4v"]
    wall_temperatures = [
        report["cht_reduced_order"][item]["combustion_side_wall_temperature_c"]
        for item in architectures
    ]
    axes[1, 0].bar(
        [item.upper() for item in architectures],
        wall_temperatures,
        color=[colors[item] for item in architectures],
    )
    axes[1, 0].set(title="Reseau thermique CHT reduit", ylabel="Temperature paroi chambre [degC]")
    for index, value in enumerate(wall_temperatures):
        axes[1, 0].text(index, value + 2.5, f"{value:.1f}", ha="center")

    damages = [
        report["fatigue_tmf_screen"]["architectures"][item]["miner_total_damage"]
        for item in architectures
    ]
    axes[1, 1].bar(
        [item.upper() for item in architectures],
        damages,
        color=[colors[item] for item in architectures],
    )
    axes[1, 1].axhline(1.0, color="#d62728", linestyle="--", label="Limite Miner D=1")
    axes[1, 1].set_yscale("log")
    axes[1, 1].set(title="Sensibilite fatigue/TMF", ylabel="Dommage Miner suppose [-]")
    axes[1, 1].legend(frameon=False)

    for axis in axes.flat:
        axis.grid(alpha=0.25)
    figure.suptitle(
        "Porsche 917 F33 — comparaison virtuelle 2V/4V\n"
        "Geometrie solveur feuille blanche; aucune correlation physique ni autorisation d'impression",
        fontsize=13,
    )
    figure.savefig(path, dpi=180, metadata={"Software": "3dprinting993 F33"})
    plt.close(figure)


def render_virtual_ndt(report: dict[str, Any], path: Path) -> None:
    cases = report["virtual_ct_ndt"]["ct_cases"]
    voxel = [item["voxel_size_mm"] * 1000.0 for item in cases]
    pod = [100.0 * item["mean_detection_probability_critical_defects"] for item in cases]
    colors = ["#2ca02c" if item["critical_pod_screen_passed"] else "#d62728" for item in cases]
    figure, axis = plt.subplots(figsize=(9.4, 5.5), constrained_layout=True)
    axis.bar([str(int(item)) for item in voxel], pod, color=colors, edgecolor="#222222")
    axis.axhline(90.0, color="#111111", linestyle="--", label="Cible POD virtuelle 90 %")
    axis.set(
        title="F33 — probabilite de detection synthetique des defauts critiques",
        xlabel="Voxel CT [micrometres]",
        ylabel="POD moyenne virtuelle [%]",
        ylim=(0, 108),
    )
    axis.grid(axis="y", alpha=0.25)
    axis.legend(frameon=False)
    for index, value in enumerate(pod):
        axis.text(index, value + 2.0, f"{value:.1f} %", ha="center")
    axis.text(
        0.01,
        0.02,
        "20 000 defauts Monte-Carlo; ce graphique n'est ni une CT reelle ni une qualification CND.",
        transform=axis.transAxes,
        fontsize=9,
    )
    figure.savefig(path, dpi=180, metadata={"Software": "3dprinting993 F33"})
    plt.close(figure)


def load_ascii_stl(path: Path) -> np.ndarray:
    vertices: list[list[float]] = []
    for line in path.read_text(encoding="ascii").splitlines():
        tokens = line.split()
        if len(tokens) == 4 and tokens[0] == "vertex":
            vertices.append([float(value) for value in tokens[1:]])
    if not vertices or len(vertices) % 3:
        raise ValueError(f"invalid ASCII STL triangles: {path}")
    return np.asarray(vertices, dtype=float).reshape((-1, 3, 3))


def render_product(stl_path: Path, geometry_report_path: Path, path: Path) -> None:
    geometry = load_json(geometry_report_path)
    variant = next(item for item in geometry["variants"] if item["architecture"] == "4v")
    if sha256(stl_path) != variant["stl"]["sha256"]:
        raise ValueError("4V product render STL digest does not match the geometry report")
    triangles = load_ascii_stl(stl_path)
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    lengths = np.linalg.norm(normals, axis=1)
    normals = normals / np.maximum(lengths[:, None], 1e-12)
    light = np.asarray([0.35, -0.45, 0.82])
    light = light / np.linalg.norm(light)
    shade = 0.48 + 0.52 * np.clip(normals @ light, 0.0, 1.0)
    base = np.asarray([0.76, 0.67, 0.49])
    colors = np.column_stack((shade[:, None] * base[None, :], np.ones(len(shade))))
    bounds_min = triangles.min(axis=(0, 1))
    bounds_max = triangles.max(axis=(0, 1))
    center = 0.5 * (bounds_min + bounds_max)
    span = np.maximum(bounds_max - bounds_min, 1.0)

    figure = plt.figure(figsize=(13.2, 6.8), constrained_layout=True)
    axis = figure.add_subplot(1, 2, 1, projection="3d")
    axis.add_collection3d(Poly3DCollection(triangles, facecolors=colors, linewidths=0.05))
    for setter, value, width in zip(
        (axis.set_xlim, axis.set_ylim, axis.set_zlim), center, span
    ):
        setter(value - 0.54 * width, value + 0.54 * width)
    axis.set_box_aspect(span)
    axis.view_init(elev=24, azim=-52)
    axis.set_axis_off()
    axis.set_title("Vue supérieure / conduits", fontsize=12)

    underside = triangles[:, :, 2].mean(axis=1) <= 14.0
    axis = figure.add_subplot(1, 2, 2)
    axis.add_collection(
        PolyCollection(
            triangles[underside, :, :2],
            facecolors=colors[underside],
            edgecolors=(0.2, 0.18, 0.13, 0.18),
            linewidths=0.08,
        )
    )
    axis.set_xlim(bounds_min[0] - 4.0, bounds_max[0] + 4.0)
    axis.set_ylim(bounds_min[1] - 4.0, bounds_max[1] + 4.0)
    axis.set_aspect("equal")
    axis.set_axis_off()
    axis.set_title("Vue orthographique chambre / sièges", fontsize=12)
    figure.suptitle(
        "Porsche 917 F33 — concept de culasse 4 soupapes\n"
        "Rendu du STL solveur vérifié — NON FABRICABLE / NOT FOR MANUFACTURE",
        fontsize=15,
        color="#8b1a1a",
    )
    figure.text(
        0.5,
        0.025,
        "Chambre, 4 soupapes, sièges/guides, bougie, fixations, jacket annulaire et galerie d'huile. "
        "Tolérances, filetages, contacts, porte-arbres et manifolds complets exclus.",
        ha="center",
        fontsize=9,
    )
    figure.savefig(path, dpi=190, metadata={"Software": "3dprinting993 F33"}, facecolor="#f7f5ef")
    plt.close(figure)


def publish(
    report_path: Path,
    output_root: Path,
    geometry_report_path: Path,
    product_stl_path: Path,
    container_image_path: Path,
    x86_cross_check_path: Path,
    preflight_json: Path,
    preflight_markdown: Path,
) -> dict[str, Any]:
    report = load_json(report_path)
    validate_report(report)
    preflight = load_json(preflight_json)
    if preflight.get("status") != "blocked":
        raise ValueError("F33 expects the observed blocked Omniverse preflight")

    output_root.mkdir(parents=True, exist_ok=True)
    figures = output_root / "figures"
    omniverse = output_root / "omniverse"
    functional_cad = output_root / "functional-cad"
    toolchain = output_root / "toolchain"
    for directory in (figures, omniverse, functional_cad, toolchain):
        directory.mkdir(parents=True, exist_ok=True)

    (output_root / "report.json").write_bytes(report_path.read_bytes())
    (functional_cad / "geometry-report.json").write_bytes(geometry_report_path.read_bytes())
    (toolchain / "container-image.json").write_bytes(container_image_path.read_bytes())
    (toolchain / "x86-cross-check.json").write_bytes(x86_cross_check_path.read_bytes())
    roots = [str(ROOT), str(ROOT.resolve()), str(preflight.get("paths", {}).get("home", ""))]
    (omniverse / "preflight.json").write_text(
        json.dumps(sanitize_value(preflight, roots), ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    (omniverse / "preflight.md").write_text(
        sanitize_text(preflight_markdown.read_text(encoding="utf-8"), roots),
        encoding="utf-8",
    )

    comparison = figures / "integrated-2v-4v.png"
    ndt = figures / "virtual-ndt-pod.png"
    product = figures / "product-4v-functional-cad.png"
    render_integrated_comparison(report, comparison)
    render_virtual_ndt(report, ndt)
    render_product(product_stl_path, geometry_report_path, product)

    relative_paths = (
        "report.json",
        "functional-cad/geometry-report.json",
        "toolchain/container-image.json",
        "toolchain/x86-cross-check.json",
        "omniverse/preflight.json",
        "omniverse/preflight.md",
        "figures/integrated-2v-4v.png",
        "figures/virtual-ndt-pod.png",
        "figures/product-4v-functional-cad.png",
    )
    publication = {
        "schema_version": "1.0.0",
        "phase": "F33",
        "status": "published_integrated_virtual_evidence_not_physical_validation",
        "files": {item: sha256(output_root / item) for item in relative_paths},
        "release_gates": report["release_gates"],
    }
    (output_root / "publication.json").write_text(
        json.dumps(publication, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return publication


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--geometry-report", type=Path, required=True)
    parser.add_argument("--product-stl", type=Path, required=True)
    parser.add_argument("--container-image", type=Path, required=True)
    parser.add_argument("--x86-cross-check", type=Path, required=True)
    parser.add_argument("--preflight-json", type=Path, required=True)
    parser.add_argument("--preflight-markdown", type=Path, required=True)
    args = parser.parse_args()
    result = publish(
        args.report.resolve(),
        args.output.resolve(),
        args.geometry_report.resolve(),
        args.product_stl.resolve(),
        args.container_image.resolve(),
        args.x86_cross_check.resolve(),
        args.preflight_json.resolve(),
        args.preflight_markdown.resolve(),
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
