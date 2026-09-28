#!/usr/bin/env python3
"""Rend la cellule automobile et les packages distincts C2/C4."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.gridspec import GridSpec
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


ROOT = Path(__file__).resolve().parents[3]
TWIN_ROOT = ROOT / "twins" / "993-carbon-safety-cell"
DERIVED = TWIN_ROOT / "derived"
OUTPUT = DERIVED / "964-993-carbon-monocoque-packaging-overview.png"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def cuboid_faces(center, dimensions):
    cx, cy, cz = center
    dx, dy, dz = (value / 2.0 for value in dimensions)
    vertices = [
        (cx - dx, cy - dy, cz - dz), (cx + dx, cy - dy, cz - dz),
        (cx + dx, cy + dy, cz - dz), (cx - dx, cy + dy, cz - dz),
        (cx - dx, cy - dy, cz + dz), (cx + dx, cy - dy, cz + dz),
        (cx + dx, cy + dy, cz + dz), (cx - dx, cy + dy, cz + dz),
    ]
    return [[vertices[index] for index in face] for face in ((0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))]


def add_box(axis, center, dimensions, color="#1d2329", alpha=0.80, edge="#6c747b", linewidth=0.45):
    axis.add_collection3d(Poly3DCollection(cuboid_faces(center, dimensions), facecolors=color, edgecolors=edge, linewidths=linewidth, alpha=alpha))


def add_beam(axis, start, end, color="#252c32", linewidth=7.0, alpha=1.0):
    axis.plot((start[0], end[0]), (start[1], end[1]), (start[2], end[2]), color=color, linewidth=linewidth, alpha=alpha, solid_capstyle="round")


def add_tube(axis, start, end, color, linewidth, alpha=1.0):
    axis.plot((start[0], end[0]), (start[1], end[1]), (start[2], end[2]), color=color, linewidth=linewidth, alpha=alpha, solid_capstyle="round")


def style_axis(axis, *, azim=-58.0, elev=24.0, compact=False):
    axis.set_xlim(-310.0, 2390.0)
    axis.set_ylim(-850.0, 850.0)
    axis.set_zlim(80.0, 1360.0 if not compact else 740.0)
    axis.set_box_aspect((2.7, 1.7, 1.28 if not compact else 0.68))
    axis.view_init(elev=elev, azim=azim)
    axis.set_axis_off()


def draw_cell(axis, config, *, alpha=0.82, include_roof=True, cutaway=False):
    geometry = config["screening_geometry_mm"]
    common = config["vehicle_packaging_mm"]["common_cell"]
    floor_z = float(geometry["floor_z"])
    half_width = float(geometry["cell_half_width"])
    belt_z = float(geometry["belt_z"])
    roof_z = float(geometry["roof_z"])
    tub_start = float(common["tub_start_x"])
    tub_end = float(common["tub_end_x"])
    sill_start = float(common["sill_start_x"])
    sill_end = float(common["sill_end_x"])
    sill_width = float(common["sill_width"])
    sill_height = float(common["sill_height"])
    tunnel_start = float(common["tunnel_start_x"])
    tunnel_end = float(common["tunnel_end_x"])
    tunnel_width = float(common["tunnel_outer_width"])
    tunnel_height = float(common["tunnel_outer_height"])
    carbon = "#20262b"
    carbon_light = "#343b41"
    edge = "#838b91"
    local_alpha = min(alpha, 0.25) if cutaway else alpha

    add_box(axis, ((tub_start + tub_end) / 2.0, 0.0, floor_z), (tub_end - tub_start, 2 * half_width, 34.0), carbon_light, local_alpha, edge)
    for sign in (-1.0, 1.0):
        y = sign * (half_width - sill_width / 2.0)
        add_box(axis, ((sill_start + sill_end) / 2.0, y, floor_z + sill_height / 2.0), (sill_end - sill_start, sill_width, sill_height), carbon, alpha, edge)
        add_box(axis, (570.0, sign * 365.0, floor_z + 62.0), (330.0, 430.0, 92.0), carbon_light, local_alpha, edge)
        add_box(axis, (1580.0, sign * 350.0, float(common["rear_shelf_z"]) - 30.0), (430.0, 420.0, 46.0), carbon_light, local_alpha, edge)
        add_box(axis, (1830.0, sign * 535.0, floor_z + 300.0), (360.0, 190.0, 430.0), carbon, alpha, edge)
        if include_roof:
            add_beam(axis, (560.0, sign * 590.0, belt_z), (1660.0, sign * 590.0, belt_z + 20.0), carbon_light, 8.0)
            add_beam(axis, (510.0, sign * 590.0, belt_z), (735.0, sign * 505.0, roof_z), carbon_light, 8.0)
            add_beam(axis, (1660.0, sign * 590.0, belt_z + 20.0), (1540.0, sign * 505.0, roof_z), carbon_light, 8.0)
            add_beam(axis, (735.0, sign * 505.0, roof_z), (1540.0, sign * 505.0, roof_z), carbon_light, 8.0)

    # Tunnel en U : le couvercle reste translucide en vue principale et disparaît en coupe.
    tunnel_center = (tunnel_start + tunnel_end) / 2.0
    for sign in (-1.0, 1.0):
        add_box(axis, (tunnel_center, sign * (tunnel_width - 26.0) / 2.0, floor_z + tunnel_height / 2.0), (tunnel_end - tunnel_start, 26.0, tunnel_height), "#2a3035", alpha, edge)
    if not cutaway:
        add_box(axis, (tunnel_center, 0.0, floor_z + tunnel_height), (tunnel_end - tunnel_start, tunnel_width, float(common["service_cover_thickness"])), "#485159", 0.60, "#9ba4aa")

    # Cloisons avant/arrière avec passage central visible.
    width = 2.0 * half_width
    side_width = (width - tunnel_width - 120.0) / 2.0
    by = (tunnel_width + 60.0 + side_width) / 2.0
    for sign in (-1.0, 1.0):
        add_box(axis, (float(common["front_bulkhead_x"]), sign * by, floor_z + 310.0), (38.0, side_width, 570.0), carbon, alpha, edge)
        add_box(axis, (float(common["rear_bulkhead_x"]), sign * by, floor_z + 350.0), (44.0, side_width, 650.0), carbon, alpha, edge)
    add_box(axis, (float(common["front_bulkhead_x"]), 0.0, belt_z + 120.0), (42.0, width - 170.0, 210.0), carbon, alpha, edge)
    add_box(axis, (float(common["rear_bulkhead_x"]), 0.0, belt_z + 135.0), (46.0, width - 140.0, 240.0), carbon, alpha, edge)
    add_box(axis, (1660.0, 0.0, float(common["rear_shelf_z"])), (360.0, width - 260.0, 42.0), carbon_light, local_alpha, edge)

    for sign in (-1.0, 1.0):
        for x_mm in (880.0, 1320.0):
            add_box(axis, (x_mm, sign * 365.0, floor_z + 62.0), (110.0, 410.0, 70.0), "#3a4248", local_alpha, "#7e878d")

    if include_roof:
        add_beam(axis, (735.0, -505.0, roof_z), (735.0, 505.0, roof_z), carbon_light, 8.0)
        add_beam(axis, (1540.0, -505.0, roof_z), (1540.0, 505.0, roof_z), carbon_light, 8.0)
        add_beam(axis, (1130.0, -505.0, roof_z + 10.0), (1130.0, 505.0, roof_z + 10.0), carbon_light, 6.0)


def draw_services(axis, config):
    floor_z = float(config["screening_geometry_mm"]["floor_z"])
    services = config["vehicle_packaging_mm"]["protected_service_channels"]
    for key, color in (("brake_fuel_left_center_y", "#efb340"), ("wiring_right_center_y", "#d861cc"), ("parking_brake_left_center_y", "#83c96b"), ("parking_brake_right_center_y", "#83c96b")):
        y = float(services[key])
        add_tube(axis, (540.0, y, floor_z + 72.0), (1860.0, y, floor_z + 72.0), color, 2.5, 0.95)


def draw_c2(axis, config):
    data = config["vehicle_packaging_mm"]["c2_package"]
    start = float(data["external_shift_rod_start_x"])
    end = float(data["external_shift_rod_end_x"])
    y = float(data["external_shift_rod_center_y"])
    z = float(data["external_shift_rod_center_z"])
    add_tube(axis, (start, y, z), (end, y, z), "#ff9b36", 6.0)
    add_box(axis, tuple(float(v) for v in data["shifter_tower_center_xyz"]), tuple(float(v) for v in data["shifter_tower_envelope_xyz"]), "#ff9b36", 0.72, "#ffd0a0")
    axis.text(1040.0, -40.0, 570.0, "tour de levier", color="#ffbd78", fontsize=7)
    axis.text(1610.0, -45.0, z + 60.0, "tringlerie C2", color="#ffbd78", fontsize=7)


def draw_c4(axis, config):
    data = config["vehicle_packaging_mm"]["c4_package"]
    start = float(data["central_tube_start_x"])
    end = float(data["central_tube_end_x"])
    z = float(data["central_tube_center_z"])
    add_tube(axis, (start, 0.0, z), (end, 0.0, z), "#246e86", 16.0, 0.68)
    add_tube(axis, (start, 0.0, z), (end, 0.0, z), "#62d9ff", 7.0, 1.0)
    guide_y = float(data["shift_guide_center_y"])
    add_tube(axis, (100.0, guide_y, z + 82.0), (1850.0, guide_y, z + 82.0), "#ff9b36", 3.5, 1.0)
    diff_center = tuple(float(v) for v in data["front_final_drive_center_xyz"])
    diff_dims = tuple(float(v) for v in data["front_final_drive_envelope_xyz"])
    add_box(axis, diff_center, diff_dims, "#2d9dc2", 0.74, "#91e4ff")
    span = float(data["front_halfshaft_total_span"]) / 2.0
    add_tube(axis, (0.0, -span, z), (0.0, span, z), "#62d9ff", 6.0)
    axis.text(340.0, 45.0, z + 95.0, "tube central + arbre C4", color="#91e4ff", fontsize=7)
    axis.text(-270.0, 260.0, z + 150.0, "pont avant", color="#91e4ff", fontsize=7)


def main() -> int:
    config = load_json(TWIN_ROOT / "design-space.json")
    plt.rcParams.update({"font.family": "DejaVu Sans", "figure.facecolor": "#f3f2ef", "axes.facecolor": "#f3f2ef", "savefig.facecolor": "#f3f2ef"})
    figure = plt.figure(figsize=(18, 10), dpi=190)
    grid = GridSpec(2, 2, figure=figure, width_ratios=(1.65, 1.0), height_ratios=(1.0, 1.0), wspace=0.02, hspace=0.02)

    main_axis = figure.add_subplot(grid[:, 0], projection="3d")
    draw_cell(main_axis, config, alpha=0.88, include_roof=True)
    style_axis(main_axis, azim=-56.0, elev=25.0)
    main_axis.set_title("CELLULE COMMUNE CFRP — BAIGNOIRE ET OUVRANTS", color="#111820", fontsize=13, fontweight="bold", pad=2)
    main_axis.text(1100.0, -700.0, 780.0, "ouverture de porte", color="#6d7378", fontsize=8)
    main_axis.text(1210.0, 15.0, 520.0, "tunnel creux + couvercle", color="#4c555c", fontsize=8)
    main_axis.text(1700.0, 520.0, 520.0, "passage de roue AR", color="#4c555c", fontsize=8)
    main_axis.text(1540.0, 20.0, 655.0, "plage / cloison arrière", color="#4c555c", fontsize=8)

    c2_axis = figure.add_subplot(grid[0, 1], projection="3d")
    draw_cell(c2_axis, config, alpha=0.18, include_roof=False, cutaway=True)
    draw_services(c2_axis, config)
    draw_c2(c2_axis, config)
    style_axis(c2_axis, azim=-64.0, elev=27.0, compact=True)
    c2_axis.set_title("964 / 993 C2 — COMMANDE DE BOÎTE", color="#111820", fontsize=11, fontweight="bold", pad=0)

    c4_axis = figure.add_subplot(grid[1, 1], projection="3d")
    draw_cell(c4_axis, config, alpha=0.18, include_roof=False, cutaway=True)
    draw_services(c4_axis, config)
    draw_c4(c4_axis, config)
    style_axis(c4_axis, azim=-64.0, elev=27.0, compact=True)
    c4_axis.set_title("964 / 993 C4 — TRANSMISSION AVANT", color="#111820", fontsize=11, fontweight="bold", pad=0)

    figure.suptitle("MONOCOQUE 964 / 993 — ARCHITECTURE VÉHICULE CORRIGÉE", color="#111820", fontsize=19, fontweight="bold", y=0.965)
    figure.text(0.5, 0.025, "Noir : structure CFRP · orange : commande de boîte · bleu : tube/arbre/pont C4 · lignes fines : services protégés\nENVELOPPES CONCEPTUELLES NON MESURÉES — PAS DE FABRICATION, ROUTE, CIRCUIT OU HOMOLOGATION", ha="center", color="#515960", fontsize=9)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(OUTPUT, bbox_inches="tight", pad_inches=0.18, metadata={"Software": "matplotlib; clean-sheet functional packaging"})
    plt.close(figure)
    print(OUTPUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
