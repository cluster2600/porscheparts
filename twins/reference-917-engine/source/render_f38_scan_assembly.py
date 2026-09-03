#!/usr/bin/env python3
"""Rend le sous-ensemble F38 dans la peau scan-conforming transparente."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def binary_stl(path: Path) -> np.ndarray:
    with path.open("rb") as stream:
        stream.seek(80)
        count = struct.unpack("<I", stream.read(4))[0]
    expected = 84 + 50 * count
    if path.stat().st_size != expected:
        raise RuntimeError(f"binary_stl_required:{path}")
    dtype = np.dtype([
        ("normal", "<f4", (3,)),
        ("vertices", "<f4", (3, 3)),
        ("attribute", "<u2"),
    ])
    return np.memmap(path, dtype=dtype, mode="r", offset=84, shape=(count,))["vertices"]


def sampled_triangles(path: Path, limit: int, cut_x_positive: bool = False) -> np.ndarray:
    triangles = binary_stl(path)
    if cut_x_positive:
        triangles = triangles[np.mean(triangles[:, :, 0], axis=1) <= 0.0]
    stride = max(1, int(np.ceil(len(triangles) / limit)))
    return np.asarray(triangles[::stride], dtype=float)


def add_mesh(ax, path: Path, colour: str, alpha: float, limit: int, cut: bool = False, edge: str = "none") -> dict:
    triangles = sampled_triangles(path, limit, cut_x_positive=cut)
    collection = Poly3DCollection(triangles, facecolor=colour, alpha=alpha, edgecolor=edge, linewidth=0.08)
    ax.add_collection3d(collection)
    return {"path": str(path), "sha256": sha256(path), "triangles_rendered": len(triangles)}


def add_scan_shell(ax, path: Path, cut: bool) -> dict:
    triangles = sampled_triangles(path, 42000, cut_x_positive=cut)
    points = triangles.reshape((-1, 3))
    ax.scatter(points[:, 0], points[:, 1], points[:, 2], s=0.18, c="#b9c7cd", alpha=0.20 if not cut else 0.32, depthshade=False)
    return {"path": str(path), "sha256": sha256(path), "scan_points_rendered": len(points), "half_section_x_le_zero": cut}


def configure(ax, title: str) -> None:
    ax.set_xlim(-72, 72)
    ax.set_ylim(-98, 122)
    ax.set_zlim(-12, 126)
    ax.set_box_aspect((144, 220, 138))
    ax.view_init(elev=24, azim=-56)
    ax.set_xlabel("X [mm]", color="#aec2cc")
    ax.set_ylabel("Y [mm]", color="#aec2cc")
    ax.set_zlabel("Z [mm]", color="#aec2cc")
    ax.tick_params(colors="#6f8792", labelsize=7)
    ax.set_facecolor("#081721")
    ax.set_title(title, color="white", fontsize=13, fontweight="bold", pad=12)
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.pane.set_facecolor((0.04, 0.10, 0.14, 1.0))
        axis.pane.set_edgecolor((0.2, 0.32, 0.38, 0.5))


def render(head: Path, cad: Path, output: Path, cut: bool) -> dict:
    fig = plt.figure(figsize=(12, 9), dpi=145, facecolor="#061019")
    ax = fig.add_subplot(111, projection="3d")
    configure(ax, "F38 — COUPE SUR PEAU SCAN-CONFORMING" if cut else "F38 — ASSEMBLAGE DANS LA PEAU SCAN-CONFORMING")
    items = [add_scan_shell(ax, head, cut=cut)]
    components = [
        ("rocker-carrier-f38-rounded-reinforced.stl", "#e2a43c", 1.0, 8000),
        ("four-rockers-f38.stl", "#eb5b4c", 1.0, 5000),
        ("two-rocker-shafts-f38.stl", "#77d8ff", 1.0, 2500),
        ("two-intake-valves-f38.stl", "#42cfff", 1.0, 2500),
        ("two-exhaust-valves-f38.stl", "#ff7657", 1.0, 2500),
        ("four-valve-guides-f38.stl", "#d8dde0", 1.0, 2500),
        ("four-valve-seats-f38.stl", "#b8c1c6", 1.0, 2500),
        ("eight-valve-springs-f38.stl", "#a9f06a", 1.0, 6000),
        ("four-lower-spring-cups-f38.stl", "#f3d27e", 1.0, 2500),
        ("four-upper-spring-retainers-f38.stl", "#f5e2a8", 1.0, 2500),
    ]
    missing = []
    for name, colour, alpha, limit in components:
        path = cad / name
        if not path.is_file():
            missing.append(name)
            continue
        items.append(add_mesh(ax, path, colour, alpha, limit))
    fig.text(0.5, 0.03, "PEAU HYBRIDE F37/F38 TRANSPARENTE • COMPOSANTS ANALYTIQUES CONDITIONNELS • PAS UNE AUTORISATION DE FABRICATION", ha="center", color="#ffcf78", fontsize=9, fontweight="bold")
    fig.tight_layout(rect=(0.02, 0.06, 0.98, 0.98))
    fig.savefig(output, facecolor=fig.get_facecolor())
    plt.close(fig)
    return {"path": output.name, "sha256": sha256(output), "bytes": output.stat().st_size, "sources": items, "missing_components": missing}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--head", type=Path, required=True)
    parser.add_argument("--cad", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    exterior = render(args.head, args.cad, args.output / "f38-scan-conforming-assembly-exterior.png", cut=False)
    section = render(args.head, args.cad, args.output / "f38-scan-conforming-assembly-section.png", cut=True)
    report = {
        "schema_version": "1.0.0",
        "phase": "F38",
        "status": "scan_conforming_transparent_assembly_views_complete_release_blocked",
        "classification": "visual_alignment_evidence_not_dimensional_fit_or_dynamic_validation",
        "head": {"path": str(args.head), "sha256": sha256(args.head)},
        "views": [exterior, section],
        "gates": {"dimensionally_fitted": False, "dynamic_valvetrain_correlated": False, "metal_print_authorized": False, "engine_start_authorized": False},
    }
    (args.output / "f38-scan-assembly-render-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "views": len(report["views"]), "missing": sorted(set(exterior["missing_components"] + section["missing_components"]))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
