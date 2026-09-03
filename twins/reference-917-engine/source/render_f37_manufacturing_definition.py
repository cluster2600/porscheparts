#!/usr/bin/env python3
"""Rend la définition de fabrication F37 sur la peau locale F36-013."""

from __future__ import annotations

import argparse
import json
import math
import struct
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import to_rgb
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


def load_stl(path: Path) -> np.ndarray:
    payload = path.read_bytes()
    count = struct.unpack_from("<I", payload, 80)[0]
    if len(payload) != 84 + count * 50:
        raise RuntimeError(f"binary_stl_required:{path}")
    fields = np.frombuffer(payload, dtype=np.uint8, offset=84).reshape(count, 50)
    return fields[:, 12:48].copy().view("<f4").reshape(count, 3, 3).astype(float)


def add_mesh(ax, triangles: np.ndarray, color: str, alpha: float = 1.0, limit: int = 90_000) -> None:
    stride = max(1, math.ceil(len(triangles) / limit))
    selected = triangles[::stride]
    normal = np.cross(selected[:, 1] - selected[:, 0], selected[:, 2] - selected[:, 0])
    normal /= np.maximum(np.linalg.norm(normal, axis=1, keepdims=True), 1.0e-12)
    light = np.asarray((0.25, -0.45, 0.86))
    light /= np.linalg.norm(light)
    intensity = np.clip(0.32 + 0.68 * np.maximum(normal @ light, 0.0), 0.25, 1.0)
    base = np.asarray(to_rgb(color))
    facecolors = np.column_stack((intensity[:, None] * base[None, :], np.full(len(selected), alpha)))
    collection = Poly3DCollection(selected, linewidths=0.0, facecolors=facecolors)
    collection.set_edgecolor("none")
    ax.add_collection3d(collection)


def frame(ax, all_triangles: list[np.ndarray], elev: float, azim: float, title: str) -> None:
    points = np.concatenate([item.reshape(-1, 3) for item in all_triangles], axis=0)
    lower, upper = points.min(axis=0), points.max(axis=0)
    centre = (lower + upper) / 2.0
    span = upper - lower
    margin = span * 0.035
    ax.set_xlim(lower[0] - margin[0], upper[0] + margin[0])
    ax.set_ylim(lower[1] - margin[1], upper[1] + margin[1])
    ax.set_zlim(lower[2] - margin[2], upper[2] + margin[2])
    ax.set_box_aspect(span, zoom=1.16)
    ax.set_proj_type("ortho")
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    ax.set_title(title, color="white", weight="bold", pad=8)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--head", type=Path, required=True)
    parser.add_argument("--cad-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads((args.cad_dir / "f37-cad-report.json").read_text(encoding="utf-8"))
    head = load_stl(args.head)
    carrier = load_stl(args.cad_dir / "rocker-carrier-as-printed.stl")
    rockers = load_stl(args.cad_dir / "four-rocker-envelopes.stl")
    shafts = load_stl(args.cad_dir / "two-rocker-shafts.stl")
    oil = load_stl(args.cad_dir / "oil-gallery-core.stl")
    allowances = load_stl(args.cad_dir / "machining-allowance-volumes.stl")
    cutters = load_stl(args.cad_dir / "finish-machining-cutters.stl")

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})
    fig = plt.figure(figsize=(16, 10), facecolor="#e9edf0")
    grid = fig.add_gridspec(2, 2, hspace=0.10, wspace=0.04)
    axes = [fig.add_subplot(grid[i, j], projection="3d", facecolor="#0c1a22") for i in range(2) for j in range(2)]

    add_mesh(axes[0], head, "#c7974f", limit=1_000_000)
    add_mesh(axes[0], carrier, "#3f5664")
    add_mesh(axes[0], rockers, "#d9dde0")
    add_mesh(axes[0], shafts, "#292f32")
    frame(axes[0], [head, carrier, rockers, shafts], 23, -54, "Ensemble F37 — peau du scan + porte-culbuteurs 4V")

    add_mesh(axes[1], head, "#c7974f", alpha=0.12, limit=140_000)
    add_mesh(axes[1], carrier, "#405c6c", alpha=0.72)
    add_mesh(axes[1], rockers, "#eef1f2")
    add_mesh(axes[1], shafts, "#252b2e")
    add_mesh(axes[1], oil, "#1b8fd2")
    frame(axes[1], [head, carrier, rockers, oil], 20, 34, "Transparence — galeries d’huile et cinématique")

    add_mesh(axes[2], head, "#c7974f", alpha=0.09, limit=120_000)
    add_mesh(axes[2], oil, "#18a2e0")
    add_mesh(axes[2], cutters, "#df5d50", alpha=0.75)
    frame(axes[2], [head, oil, cutters], 5, -72, "Noyau d’huile connexe + volumes de finition")

    add_mesh(axes[3], head, "#c7974f", alpha=0.14, limit=120_000)
    add_mesh(axes[3], allowances, "#e64f9a", alpha=0.82)
    add_mesh(axes[3], carrier, "#405c6c", alpha=0.34)
    frame(axes[3], [head, allowances, carrier], 72, -88, "Carte 3D des surépaisseurs d’usinage")

    checks = report["checks"]
    fig.suptitle(
        "Culasse Porsche 917 F37 — définition fonctionnelle avant impression",
        fontsize=18,
        weight="bold",
        color="#17242b",
        y=0.975,
    )
    fig.text(
        0.5,
        0.935,
        "6 familles B-Rep OCCT · STEP réimportés sans dérive · porte-axes repris sur 4 goujons · 4 culbuteurs · 2 axes",
        ha="center",
        color="#334650",
        weight="bold",
    )
    fig.text(
        0.02,
        0.018,
        "Contrôles CAO : "
        + ("formes fermées, " if checks["all_created_shapes_valid_and_closed"] else "")
        + ("round-trip STEP, " if checks["all_step_roundtrips_valid_and_closed"] else "")
        + ("noyau d’huile connexe; débouchés : voir audit maillage séparé" if checks["oil_core_is_one_connected_solid"] else "noyau d’huile non connexe"),
        color="#245f50",
        weight="bold",
    )
    fig.text(
        0.98,
        0.018,
        "ROUGE : pas encore une CAO monobloc de production — impression et démarrage interdits",
        ha="right",
        color="#a3322c",
        weight="bold",
    )
    fig.subplots_adjust(left=0.025, right=0.975, bottom=0.065, top=0.89)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=150)
    plt.close(fig)
    print(json.dumps({"status": "rendered", "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
