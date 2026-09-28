#!/usr/bin/env python3
"""Construit le dessin F1 de la 911-917 à moteur central arrière.

Le flat-12 est placé devant l'essieu arrière et une réserve de transaxle est
placée derrière. Le scan local est réellement projeté dans le dessin, sans
publier ses coordonnées. Toutes les réserves restent non fabricables.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
TWIN_ROOT = ROOT / "twins" / "vehicle-911-917"
CONFIG_PATH = TWIN_ROOT / "packaging-concept-f1.json"
BASE_CONFIG_PATH = TWIN_ROOT / "packaging-concept-f0.json"
F0_SCRIPT_PATH = TWIN_ROOT / "source" / "build_packaging_concept_f0.py"
WORK_ROOT = ROOT / "work" / "911-917-packaging-f1"
REPORT_PATH = WORK_ROOT / "packaging-report-f1.json"
PNG_PATH = WORK_ROOT / "911-917-mid-engine-layout-f1.png"
SVG_PATH = WORK_ROOT / "911-917-mid-engine-layout-f1.svg"
STEP_PATH = WORK_ROOT / "911-917-mid-engine-packaging-f1.step"
DESIGNER_PNG_PATH = WORK_ROOT / "911-917-mid-engine-designer-f1.png"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: objet JSON attendu")
    return value


def load_f0_module() -> Any:
    spec = importlib.util.spec_from_file_location("packaging_f0", F0_SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"module impossible à charger: {F0_SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def compute_trials(
    config: dict[str, Any],
    vehicle: dict[str, Any],
    scan_size_mm: list[float],
) -> dict[str, Any]:
    parameters = vehicle["parameters"]
    stock_length = float(parameters["length_mm"]["value_mm"])
    body_width = float(parameters["width_mm"]["value_mm"])
    body_height = float(parameters["height_mm"]["value_mm"])
    stock_wheelbase = float(parameters["wheelbase_mm"]["value_mm"])
    centred_overhang = (stock_length - stock_wheelbase) / 2.0
    body_front = -centred_overhang

    body = config["body_and_occupant_screening_mm"]
    transaxle = config["rear_transaxle_screening"]
    engine = config["engine_screening"]["full_engine_service_envelope_mm"]
    handling = config["handling_screening"]
    occupant_rear = float(body["front_occupant_rear_limit_x"])
    firewall_x = float(body["powertrain_firewall_x"])
    service_length = float(engine["length"])
    service_width = float(engine["width"])
    engine_mate_ahead = float(transaxle["engine_mating_plane_ahead_of_differential_mm"])
    gearbox_rear_extent = float(transaxle["rear_extent_from_differential_plane_mm"])
    target_engine_cg_ahead = [float(value) for value in handling["engine_geometric_centre_target_ahead_of_rear_axle_mm"]]

    trials: list[dict[str, Any]] = []
    for extension_value in body["wheelbase_extension_trials"]:
        extension = float(extension_value)
        rear_axle_x = stock_wheelbase + extension
        body_rear = rear_axle_x + centred_overhang
        engine_mating_x = rear_axle_x - engine_mate_ahead
        scan_front_x = engine_mating_x - float(scan_size_mm[0])
        service_front_x = engine_mating_x - service_length
        gearbox_rear_x = rear_axle_x + gearbox_rear_extent
        scan_centre_x = (scan_front_x + engine_mating_x) / 2.0
        scan_centre_ahead = rear_axle_x - scan_centre_x
        occupant_clearance = service_front_x - occupant_rear
        firewall_clearance = service_front_x - firewall_x
        lateral_margin = (body_width - service_width) / 2.0
        gearbox_rear_margin = body_rear - gearbox_rear_x
        packaging_pass = (
            occupant_clearance >= float(body["minimum_occupant_to_engine_service_clearance"])
            and firewall_clearance >= float(body["minimum_firewall_to_engine_service_clearance"])
            and lateral_margin >= 100.0
            and gearbox_rear_margin >= 75.0
        )
        handling_target_pass = target_engine_cg_ahead[0] <= scan_centre_ahead <= target_engine_cg_ahead[1]
        trials.append(
            {
                "layout_id": f"MID_ENGINE_WHEELBASE_PLUS_{int(extension)}",
                "architecture": "flat_12_ahead_of_rear_axle_transaxle_behind",
                "wheelbase_extension_mm": extension,
                "wheelbase_mm": rear_axle_x,
                "body_front_x_mm": body_front,
                "body_rear_x_mm": body_rear,
                "overall_length_visualisation_mm": body_rear - body_front,
                "stock_rear_axle_reference_x_mm": stock_wheelbase,
                "rear_axle_x_mm": rear_axle_x,
                "differential_plane_x_mm": rear_axle_x,
                "engine_mating_plane_x_mm": engine_mating_x,
                "engine_scan_bounds_x_mm": [round(scan_front_x, 3), round(engine_mating_x, 3)],
                "engine_scan_geometric_centre_x_mm": round(scan_centre_x, 3),
                "engine_scan_geometric_centre_ahead_of_rear_axle_mm": round(scan_centre_ahead, 3),
                "engine_service_bounds_x_mm": [round(service_front_x, 3), round(engine_mating_x, 3)],
                "gearbox_bounds_x_mm": [round(engine_mating_x, 3), round(gearbox_rear_x, 3)],
                "front_occupant_to_engine_service_clearance_mm": round(occupant_clearance, 1),
                "firewall_to_engine_service_clearance_mm": round(firewall_clearance, 1),
                "engine_service_lateral_margin_per_side_mm": round(lateral_margin, 1),
                "gearbox_rear_body_margin_mm": round(gearbox_rear_margin, 1),
                "rear_seats_deleted": True,
                "packaging_screening_pass": packaging_pass,
                "engine_position_target_pass": handling_target_pass,
                "screening_pass": packaging_pass and handling_target_pass,
            }
        )

    selected_extension = float(body["selected_wheelbase_extension"])
    selected = next(item for item in trials if item["wheelbase_extension_mm"] == selected_extension)
    passing_extensions = [item["wheelbase_extension_mm"] for item in trials if item["screening_pass"]]
    if not passing_extensions:
        raise ValueError("aucun essai F1 ne passe le screening")

    return {
        "vehicle_reference_mm": {
            "stock_overall_length": stock_length,
            "overall_width": body_width,
            "overall_height": body_height,
            "stock_wheelbase": stock_wheelbase,
            "front_track": float(parameters["front_track_mm"]["value_mm"]),
            "rear_track": float(parameters["rear_track_mm"]["value_mm"]),
            "centred_overhang_each_end_for_visualisation": centred_overhang,
            "overhang_status": "visualisation_assumption_not_measured_axle_to_body_surface",
        },
        "engine_service_envelope_mm": {
            "length": service_length,
            "width": service_width,
            "height": float(engine["height"]),
            "status": engine["status"],
        },
        "gearbox_reservation_mm": {
            "length": engine_mate_ahead + gearbox_rear_extent,
            "width": float(transaxle["width"]),
            "height": float(transaxle["height"]),
            "engine_mating_plane_ahead_of_differential": engine_mate_ahead,
            "status": transaxle["status"],
        },
        "trials": trials,
        "selected_layout_id": selected["layout_id"],
        "minimum_passing_wheelbase_extension_mm": min(passing_extensions),
        "selection_basis": (
            "Shortest tested wheelbase that keeps the compact complete-engine reservation at least "
            "100 mm behind the occupant limit and 50 mm behind the provisional firewall, while the "
            "scan geometric centre remains ahead of the rear axle."
        ),
    }


def build_report(config: dict[str, Any], *, keep_sample: bool) -> tuple[dict[str, Any], Any]:
    f0 = load_f0_module()
    base_config = load_json(BASE_CONFIG_PATH)
    scan_config = dict(base_config)
    scan_config["inputs"] = config["inputs"]
    scan_config["engine_screening"] = {
        **base_config["engine_screening"],
        "obj_unit_to_mm": config["engine_screening"]["obj_unit_to_mm"],
    }
    scan = f0.scan_geometry(scan_config, keep_sample=keep_sample)
    sample = scan.pop("sample")
    vehicle = load_json(ROOT / config["inputs"]["vehicle_reference"])
    layouts = compute_trials(config, vehicle, scan["screening_frame"]["screening_size_mm"])
    selected = next(item for item in layouts["trials"] if item["layout_id"] == layouts["selected_layout_id"])
    rear_fraction = [float(value) for value in config["handling_screening"]["vehicle_static_rear_mass_fraction_target"]]
    target_vehicle_cg = [round(selected["wheelbase_mm"] * value, 1) for value in rear_fraction]

    report = {
        "schema_version": "1.0.0",
        "concept_id": config["concept_id"],
        "status": config["status"],
        "source_integrity": {
            "source_scan_sha256": scan["source_scan_sha256"],
            "source_scan_sha256_matches_f21": scan["source_scan_sha256_matches_f21"],
            "raw_scan_coordinates_published": False,
        },
        "scan_screening": scan,
        "layout_screening": layouts,
        "handling_screening": {
            "engine_position_proxy": "geometric centre of the oriented partial scan, not measured mass CG",
            "engine_scan_geometric_centre_ahead_of_rear_axle_mm": selected[
                "engine_scan_geometric_centre_ahead_of_rear_axle_mm"
            ],
            "target_static_rear_mass_fraction": rear_fraction,
            "corresponding_target_vehicle_cg_x_mm": target_vehicle_cg,
            "weight_distribution_computed": False,
            "reason": "Complete component masses and centres of gravity are not available.",
        },
        "gearbox_power_screening": f0.power_torque_screen(base_config),
        "decision": {
            "selected_layout_id": layouts["selected_layout_id"],
            "architecture": "rear_mid_engine_flat_12_ahead_of_rear_axle_transaxle_behind",
            "rear_seats_deleted": True,
            "wheelbase_extension_mm": selected["wheelbase_extension_mm"],
            "wheelbase_mm": selected["wheelbase_mm"],
            "stock_wheelbase_retained": False,
            "rear_tail_extension_beyond_constant_overhang_mm": 0.0,
            "gearbox_selected": None,
            "request_manufacturer_GA_before_freezing_package": True,
        },
        "outputs": {
            "technical_drawing_png": str(PNG_PATH.relative_to(ROOT)),
            "technical_drawing_svg": str(SVG_PATH.relative_to(ROOT)),
            "packaging_step": str(STEP_PATH.relative_to(ROOT)),
            "designer_concept_png_optional_non_dimensional": str(DESIGNER_PNG_PATH.relative_to(ROOT)),
        },
        "claim_limits": [
            "The engine is no longer placed behind the rear axle; its partial-scan geometric centre is ahead of it in the selected layout.",
            "The scan metric scale and orientation are not physically verified, and its geometric centre is not a mass centre of gravity.",
            "The compact complete-engine envelope is an aggressive design reservation and does not prove that heads, fan, exhaust, turbos or service access fit.",
            "The gearbox volume is a reservation because no public manufacturer general-arrangement dimensions were found.",
            "The stretched body silhouette, firewall, occupant volume and axle relocation are design hypotheses, not measured Porsche surfaces or suspension geometry.",
            "The static mass-distribution corridor is a target only; no vehicle weight distribution has been calculated.",
            "The separate designer rendering is non-dimensional concept art; the technical PNG, report and STEP govern the screening layout.",
            "No fitment, structural, thermal, driveline, manufacturing, road or track claim is released.",
        ],
        "release_gates": config["release_gates"],
    }
    return report, sample


def body_side_polygon(body_front: float, body_rear: float, height: float, rear_axle: float) -> list[tuple[float, float]]:
    return [
        (body_front, 190.0),
        (body_front + 90.0, 480.0),
        (body_front + 520.0, 720.0),
        (-80.0, 890.0),
        (520.0, height * 0.94),
        (1080.0, height),
        (1530.0, height * 0.96),
        (1900.0, 1110.0),
        (rear_axle - 420.0, 860.0),
        (body_rear - 420.0, 730.0),
        (body_rear, 500.0),
        (body_rear, 180.0),
    ]


def render_drawing(config: dict[str, Any], report: dict[str, Any], sample: Any) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.patches import Circle, Polygon, Rectangle

    vehicle = report["layout_screening"]["vehicle_reference_mm"]
    trials = report["layout_screening"]["trials"]
    selected = next(item for item in trials if item["layout_id"] == report["decision"]["selected_layout_id"])
    scan_size = np.asarray(report["scan_screening"]["screening_frame"]["screening_size_mm"], dtype=float)
    body = config["body_and_occupant_screening_mm"]
    service = report["layout_screening"]["engine_service_envelope_mm"]
    gearbox = report["layout_screening"]["gearbox_reservation_mm"]
    front = float(selected["body_front_x_mm"])
    rear = float(selected["body_rear_x_mm"])
    rear_axle = float(selected["rear_axle_x_mm"])
    stock_rear_axle = float(selected["stock_rear_axle_reference_x_mm"])
    scan_front, scan_rear = (float(value) for value in selected["engine_scan_bounds_x_mm"])
    service_front, service_rear = (float(value) for value in selected["engine_service_bounds_x_mm"])
    gearbox_front, gearbox_rear = (float(value) for value in selected["gearbox_bounds_x_mm"])

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "figure.facecolor": "#f2f0eb",
            "axes.facecolor": "#f2f0eb",
            "savefig.facecolor": "#f2f0eb",
        }
    )
    figure = plt.figure(figsize=(19, 12), dpi=180)
    grid = figure.add_gridspec(2, 2, height_ratios=(1.25, 1.0), width_ratios=(1.62, 1.0), hspace=0.24, wspace=0.14)
    side = figure.add_subplot(grid[0, :])
    plan = figure.add_subplot(grid[1, 0])
    comparison = figure.add_subplot(grid[1, 1])

    side.add_patch(
        Polygon(
            body_side_polygon(front, rear, float(vehicle["overall_height"]), rear_axle),
            closed=True,
            facecolor="#d7dbde",
            edgecolor="#182026",
            linewidth=1.5,
            alpha=0.58,
            zorder=1,
        )
    )
    for axle in (0.0, rear_axle):
        side.add_patch(Circle((axle, 330.0), 320.0, facecolor="#11171b", edgecolor="#59636b", linewidth=1.2, zorder=5))
        side.add_patch(Circle((axle, 330.0), 185.0, facecolor="#d0d5d8", edgecolor="#59636b", linewidth=1.0, zorder=6))
    side.axvline(stock_rear_axle, color="#899198", linewidth=1.1, linestyle=":", zorder=2)
    side.axvspan(float(body["rear_seat_delete_start_x"]), float(body["rear_seat_delete_end_x"]), color="#7f8790", alpha=0.13, zorder=0)
    side.axvline(float(body["powertrain_firewall_x"]), color="#cf3c50", linewidth=1.6, linestyle="--", zorder=7)
    side.add_patch(
        Rectangle(
            (service_front, float(body["powertrain_floor_z"])),
            service_rear - service_front,
            float(service["height"]),
            facecolor="#f39a3c",
            edgecolor="#ad4c10",
            linewidth=1.5,
            alpha=0.16,
            zorder=2,
        )
    )
    side.add_patch(
        Rectangle(
            (gearbox_front, 260.0),
            gearbox_rear - gearbox_front,
            float(gearbox["height"]),
            facecolor="#39a7c4",
            edgecolor="#0c6179",
            linewidth=1.4,
            alpha=0.68,
            zorder=3,
        )
    )
    side.scatter(scan_front + sample[:, 0], 300.0 + sample[:, 2], s=0.22, color="#c95719", alpha=0.25, rasterized=True, zorder=4)
    side.axvline(rear_axle, color="#117791", linewidth=2.2, zorder=7)

    side.annotate("", (0.0, 85.0), (rear_axle, 85.0), arrowprops={"arrowstyle": "<->", "color": "#182026", "linewidth": 1.2})
    side.text(rear_axle / 2.0, 36.0, f"empattement F1 : {rear_axle:.0f} mm", ha="center", fontsize=9.5, color="#182026")
    side.annotate("", (stock_rear_axle, 148.0), (rear_axle, 148.0), arrowprops={"arrowstyle": "<->", "color": "#8b3f75", "linewidth": 1.3})
    side.text((stock_rear_axle + rear_axle) / 2.0, 168.0, "+450 mm", ha="center", fontsize=9.5, color="#8b3f75", fontweight="bold")
    engine_centre = float(selected["engine_scan_geometric_centre_x_mm"])
    side.annotate("", (engine_centre, 1060.0), (rear_axle, 1060.0), arrowprops={"arrowstyle": "<->", "color": "#9b3f0b", "linewidth": 1.3})
    side.text(
        (engine_centre + rear_axle) / 2.0,
        1090.0,
        f"centre géométrique du scan : {selected['engine_scan_geometric_centre_ahead_of_rear_axle_mm']:.0f} mm devant l’axe",
        ha="center",
        fontsize=9,
        color="#8f3d12",
    )
    side.text(920.0, 1040.0, "2 places", fontsize=10, color="#353c42", fontweight="bold")
    side.text(1390.0, 1200.0, "banquette supprimée", fontsize=9, color="#555d64")
    side.text(float(body["powertrain_firewall_x"]) + 20.0, 1010.0, "cloison feu\nhypothèse", fontsize=8, color="#b12639")
    side.text((service_front + service_rear) / 2.0, 780.0, "FLAT-12 DEVANT L’ESSIEU", ha="center", fontsize=11, color="#913b09", fontweight="bold")
    side.text((gearbox_front + gearbox_rear) / 2.0, 510.0, "TRANSAXLE\nDERRIÈRE", ha="center", fontsize=9, color="#07526a", fontweight="bold")
    side.set_title("F1 RETENU — MOTEUR CENTRAL ARRIÈRE, EMPATTEMENT +450 mm", fontsize=15, fontweight="bold", color="#141b20")
    side.set_xlim(front - 170.0, rear + 170.0)
    side.set_ylim(0.0, 1510.0)
    side.set_aspect("equal", adjustable="box")
    side.set_xlabel("X depuis l’axe avant [mm]")
    side.set_ylabel("Z de visualisation [mm]")
    side.grid(color="#8d9499", linewidth=0.35, alpha=0.28)

    half_width = float(vehicle["overall_width"]) / 2.0
    top_points = [
        (front, -460.0),
        (-520.0, -760.0),
        (0.0, -half_width),
        (1100.0, -790.0),
        (rear_axle, -half_width),
        (rear - 520.0, -720.0),
        (rear, -430.0),
        (rear, 430.0),
        (rear - 520.0, 720.0),
        (rear_axle, half_width),
        (1100.0, 790.0),
        (0.0, half_width),
        (-520.0, 760.0),
        (front, 460.0),
    ]
    plan.add_patch(Polygon(top_points, closed=True, facecolor="#d7dbde", edgecolor="#182026", linewidth=1.4, alpha=0.58))
    plan.add_patch(
        Rectangle(
            (float(body["rear_seat_delete_start_x"]), -620.0),
            float(body["rear_seat_delete_end_x"]) - float(body["rear_seat_delete_start_x"]),
            1240.0,
            facecolor="#7f8790",
            edgecolor="none",
            alpha=0.13,
        )
    )
    plan.add_patch(Rectangle((service_front, -float(service["width"]) / 2.0), service_rear - service_front, float(service["width"]), facecolor="#f39a3c", edgecolor="#ad4c10", linewidth=1.4, alpha=0.16))
    plan.add_patch(Rectangle((gearbox_front, -float(gearbox["width"]) / 2.0), gearbox_rear - gearbox_front, float(gearbox["width"]), facecolor="#39a7c4", edgecolor="#0c6179", linewidth=1.3, alpha=0.68))
    plan.scatter(scan_front + sample[:, 0], sample[:, 1] - scan_size[1] / 2.0, s=0.22, color="#c95719", alpha=0.25, rasterized=True)
    plan.axvline(rear_axle, color="#117791", linewidth=2.0)
    plan.axvline(float(body["powertrain_firewall_x"]), color="#cf3c50", linewidth=1.3, linestyle="--")
    plan.text((service_front + service_rear) / 2.0, 665.0, f"réserve moteur complet {service['length']:.0f} × {service['width']:.0f} mm", ha="center", color="#913b09", fontsize=9)
    plan.text((gearbox_front + gearbox_rear) / 2.0, 335.0, f"réserve boîte {gearbox['length']:.0f} × {gearbox['width']:.0f} mm", ha="center", color="#07526a", fontsize=8.5)
    plan.set_title("VUE DE DESSUS — LE FLAT-12 OCCUPE L’ANCIENNE ZONE ARRIÈRE DE L’HABITACLE", fontsize=11, fontweight="bold")
    plan.set_xlim(front - 120.0, rear + 120.0)
    plan.set_ylim(-1000.0, 1000.0)
    plan.set_aspect("equal", adjustable="box")
    plan.set_xlabel("X [mm]")
    plan.set_ylabel("Y [mm]")
    plan.grid(color="#8d9499", linewidth=0.35, alpha=0.28)

    comparison.set_title("EMPATTEMENT ET COULOIR DE MASSE", fontsize=12, fontweight="bold")
    row_y = [3.1, 2.2, 1.3]
    for y, trial in zip(row_y, trials):
        body_start = float(trial["body_front_x_mm"])
        body_end = float(trial["body_rear_x_mm"])
        comparison.plot((body_start, body_end), (y, y), color="#7f878d", linewidth=9.0, alpha=0.3, solid_capstyle="round")
        engine_start, engine_end = trial["engine_service_bounds_x_mm"]
        box_start, box_end = trial["gearbox_bounds_x_mm"]
        comparison.plot((engine_start, engine_end), (y, y), color="#e47725", linewidth=7.0, solid_capstyle="butt")
        comparison.plot((box_start, box_end), (y, y), color="#2392b1", linewidth=7.0, solid_capstyle="butt")
        comparison.scatter([trial["rear_axle_x_mm"]], [y], marker="|", s=200, color="#117791", linewidth=2.0)
        result_color = "#25815f" if trial["screening_pass"] else "#bd3446"
        result = "PASSE" if trial["screening_pass"] else "NE PASSE PAS"
        comparison.text(body_start, y + 0.24, f"+{trial['wheelbase_extension_mm']:.0f} mm — {result}", fontsize=8.7, color=result_color, fontweight="bold")
        comparison.text(
            body_start,
            y - 0.28,
            f"dégagement occupant {trial['front_occupant_to_engine_service_clearance_mm']:.0f} mm · cloison {trial['firewall_to_engine_service_clearance_mm']:.0f} mm",
            fontsize=8.1,
            color="#343b40",
        )

    target_start, target_end = report["handling_screening"]["corresponding_target_vehicle_cg_x_mm"]
    comparison.plot((0.0, rear_axle), (0.45, 0.45), color="#737c83", linewidth=4.0, alpha=0.35)
    comparison.plot((target_start, target_end), (0.45, 0.45), color="#8b3f75", linewidth=11.0, solid_capstyle="butt")
    comparison.scatter([float(selected["engine_scan_geometric_centre_x_mm"])], [0.45], s=80, color="#d1621c", zorder=5)
    comparison.text(0.0, 0.72, "cible véhicule 55–60 % arrière (pas un calcul)", fontsize=8.5, color="#8b3f75", fontweight="bold")
    comparison.text(0.0, 0.08, "● centre géométrique du scan ≠ centre de masse moteur", fontsize=8.2, color="#913b09")
    comparison.set_xlim(front - 120.0, max(float(item["body_rear_x_mm"]) for item in trials) + 120.0)
    comparison.set_ylim(-0.1, 3.55)
    comparison.set_yticks([])
    comparison.set_xlabel("X depuis l’axe avant [mm]")
    comparison.grid(axis="x", color="#8d9499", linewidth=0.35, alpha=0.28)
    for spine in ("left", "right", "top"):
        comparison.spines[spine].set_visible(False)

    figure.suptitle("911–917/30 — PLAN D’ARCHITECTURE CENTRALE ARRIÈRE F1", fontsize=21, fontweight="bold", color="#10161a", y=0.975)
    figure.text(
        0.5,
        0.015,
        "Orange plein : scan réel réorienté · orange transparent : réserve moteur complet · bleu : réserve de transaxle\n"
        "ÉCHELLE DU SCAN, CAISSE, CLOISON, SUSPENSION ET DIMENSIONS DE BOÎTE NON VÉRIFIÉES — SCREENING UNIQUEMENT",
        ha="center",
        fontsize=9,
        color="#4f585f",
    )
    WORK_ROOT.mkdir(parents=True, exist_ok=True)
    figure.savefig(PNG_PATH, bbox_inches="tight", pad_inches=0.18, metadata={"Software": "matplotlib; 911-917 packaging F1"})
    figure.savefig(SVG_PATH, bbox_inches="tight", pad_inches=0.18, metadata={"Date": None})
    plt.close(figure)


def build_cad(report: dict[str, Any], config: dict[str, Any]) -> None:
    from build123d import Align, Box, Compound, Pos, export_step

    selected = next(
        item
        for item in report["layout_screening"]["trials"]
        if item["layout_id"] == report["decision"]["selected_layout_id"]
    )
    vehicle = report["layout_screening"]["vehicle_reference_mm"]
    scan_size = report["scan_screening"]["screening_frame"]["screening_size_mm"]
    service = report["layout_screening"]["engine_service_envelope_mm"]
    gearbox = report["layout_screening"]["gearbox_reservation_mm"]
    body = config["body_and_occupant_screening_mm"]
    front = float(selected["body_front_x_mm"])
    rear = float(selected["body_rear_x_mm"])
    width = float(vehicle["overall_width"])
    height = float(vehicle["overall_height"])
    gearbox_start, gearbox_end = (float(value) for value in selected["gearbox_bounds_x_mm"])
    scan_start, scan_end = (float(value) for value in selected["engine_scan_bounds_x_mm"])
    service_start, service_end = (float(value) for value in selected["engine_service_bounds_x_mm"])
    shapes = []

    def add(label: str, shape: Any) -> None:
        shape.label = label
        shapes.append(shape)

    add("BODY_FLOOR_PRESENTATION_ONLY", Pos((front + rear) / 2.0, 0.0, 170.0) * Box(rear - front, width, 20.0, align=Align.CENTER))
    for sign in (-1.0, 1.0):
        add(
            f"BODY_SIDE_REFERENCE_{'L' if sign > 0 else 'R'}",
            Pos((front + rear) / 2.0, sign * width / 2.0, height / 2.0) * Box(rear - front, 18.0, height, align=Align.CENTER),
        )
    add("POWERTRAIN_FIREWALL_SCREENING", Pos(float(body["powertrain_firewall_x"]), 0.0, 650.0) * Box(24.0, 1300.0, 940.0, align=Align.CENTER))
    add(
        "REAR_SEAT_DELETE_VOLUME",
        Pos((float(body["rear_seat_delete_start_x"]) + float(body["rear_seat_delete_end_x"])) / 2.0, 0.0, 520.0)
        * Box(float(body["rear_seat_delete_end_x"]) - float(body["rear_seat_delete_start_x"]), 1240.0, 680.0, align=Align.CENTER),
    )
    add(
        "COMPLETE_ENGINE_SERVICE_RESERVED_VOLUME_NOT_MEASURED",
        Pos((service_start + service_end) / 2.0, 0.0, float(body["powertrain_floor_z"]) + float(service["height"]) / 2.0)
        * Box(service_end - service_start, float(service["width"]), float(service["height"]), align=Align.CENTER),
    )
    add(
        "ENGINE_SCAN_ORIENTED_BOUNDING_BOX_SCALE_UNVERIFIED",
        Pos((scan_start + scan_end) / 2.0, 0.0, 300.0 + float(scan_size[2]) / 2.0)
        * Box(scan_end - scan_start, float(scan_size[1]), float(scan_size[2]), align=Align.CENTER),
    )
    add(
        "REAR_TRANSAXLE_RESERVED_VOLUME_NOT_VENDOR_GA",
        Pos((gearbox_start + gearbox_end) / 2.0, 0.0, 260.0 + float(gearbox["height"]) / 2.0)
        * Box(gearbox_end - gearbox_start, float(gearbox["width"]), float(gearbox["height"]), align=Align.CENTER),
    )
    for name, x_value in (
        ("FRONT_AXLE", 0.0),
        ("STOCK_REAR_AXLE_REFERENCE", float(vehicle["stock_wheelbase"])),
        ("F1_REAR_AXLE_AND_DIFFERENTIAL", float(selected["rear_axle_x_mm"])),
    ):
        add(name, Pos(x_value, 0.0, 330.0) * Box(18.0, width, 18.0, align=Align.CENTER))
    target_start, target_end = report["handling_screening"]["corresponding_target_vehicle_cg_x_mm"]
    add(
        "TARGET_VEHICLE_CG_CORRIDOR_55_TO_60_PERCENT_REAR_NOT_PREDICTED",
        Pos((target_start + target_end) / 2.0, 0.0, 1150.0) * Box(target_end - target_start, 120.0, 120.0, align=Align.CENTER),
    )

    compound = Compound(children=shapes, label="911 917 MID ENGINE PACKAGING F1 - SCREENING ONLY")
    WORK_ROOT.mkdir(parents=True, exist_ok=True)
    export_step(compound, STEP_PATH)


def write_report(report: dict[str, Any]) -> None:
    WORK_ROOT.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def check_outputs(config: dict[str, Any]) -> None:
    expected, _ = build_report(config, keep_sample=False)
    if not REPORT_PATH.exists():
        raise SystemExit(f"sortie absente: {REPORT_PATH.relative_to(ROOT)}")
    current = load_json(REPORT_PATH)
    if current != expected:
        raise SystemExit("packaging-report-f1.json n'est pas reproductible; relancer --mode render")
    if not expected["source_integrity"]["source_scan_sha256_matches_f21"]:
        raise SystemExit("le scan local ne correspond pas au SHA-256 F21")
    selected = next(
        item
        for item in expected["layout_screening"]["trials"]
        if item["layout_id"] == expected["decision"]["selected_layout_id"]
    )
    if not selected["screening_pass"]:
        raise SystemExit("l'implantation F1 retenue ne passe pas le screening")
    if selected["wheelbase_extension_mm"] != expected["layout_screening"]["minimum_passing_wheelbase_extension_mm"]:
        raise SystemExit("l'implantation F1 n'est pas le plus court essai passant")
    if selected["engine_scan_geometric_centre_x_mm"] >= selected["rear_axle_x_mm"]:
        raise SystemExit("le centre géométrique du scan moteur reste derrière l'essieu arrière")
    if expected["gearbox_power_screening"]["gearbox_selected"] is not None:
        raise SystemExit("une boîte a été sélectionnée sans dossier constructeur complet")
    if expected["handling_screening"]["weight_distribution_computed"]:
        raise SystemExit("une répartition des masses a été déclarée sans données de masse et de CG")
    if any(expected["release_gates"].values()):
        raise SystemExit("un gate de libération interdit est ouvert")
    for path, minimum_size in ((PNG_PATH, 50_000), (SVG_PATH, 50_000), (STEP_PATH, 20_000)):
        if not path.exists() or path.stat().st_size < minimum_size:
            raise SystemExit(f"sortie absente ou trop petite: {path.relative_to(ROOT)}")
    print("911-917 mid-engine packaging F1: PASS (screening only, all release gates closed)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("render", "cad", "check", "all"), default="render")
    args = parser.parse_args()
    config = load_json(CONFIG_PATH)

    if args.mode in ("render", "all"):
        report, sample = build_report(config, keep_sample=True)
        write_report(report)
        render_drawing(config, report, sample)
        print(PNG_PATH.relative_to(ROOT))
        print(SVG_PATH.relative_to(ROOT))
    if args.mode in ("cad", "all"):
        report, _ = build_report(config, keep_sample=False)
        build_cad(report, config)
        print(STEP_PATH.relative_to(ROOT))
    if args.mode == "check":
        check_outputs(config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
