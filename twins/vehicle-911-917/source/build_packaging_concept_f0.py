#!/usr/bin/env python3
"""Construit le premier dessin d'encombrement de la 911-917.

Le script exploite la forme du scan local sans publier ses coordonnees. Son
echelle 1:1 reste une hypothese de screening. La CAO produite contient des
volumes de garde, pas des pieces de vehicule fabricables.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
TWIN_ROOT = ROOT / "twins" / "vehicle-911-917"
CONFIG_PATH = TWIN_ROOT / "packaging-concept-f0.json"
WORK_ROOT = ROOT / "work" / "911-917-packaging-f0"
REPORT_PATH = WORK_ROOT / "packaging-report-f0.json"
PNG_PATH = WORK_ROOT / "911-917-packaging-f0.png"
SVG_PATH = WORK_ROOT / "911-917-packaging-f0.svg"
STEP_PATH = WORK_ROOT / "911-917-packaging-preferred-f0.step"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: objet JSON attendu")
    return value


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rounded(values: Any, digits: int = 3) -> Any:
    if hasattr(values, "tolist"):
        return rounded(values.tolist(), digits)
    if isinstance(values, (list, tuple)):
        return [rounded(value, digits) for value in values]
    try:
        return round(float(values), digits)
    except (TypeError, ValueError):
        return values


def scan_geometry(config: dict[str, Any], *, keep_sample: bool) -> dict[str, Any]:
    import numpy as np

    scan_path = ROOT / config["inputs"]["engine_scan"]
    interface_path = ROOT / config["inputs"]["engine_scan_interface_report"]
    interface_report = load_json(interface_path)
    registry = interface_report["interface_registry"]
    centres = np.asarray([item["center_scan_coordinates_obj_units"] for item in registry], dtype=float)

    # Axe longitudinal : direction principale des douze ouvertures detectees.
    longitudinal = np.linalg.svd(centres - centres.mean(axis=0), full_matrices=False)[2][0]
    ordered = sorted(registry, key=lambda item: item["center_longitudinal_vertical_obj_units"][0])
    ordered_vector = (
        np.asarray(ordered[-1]["center_scan_coordinates_obj_units"], dtype=float)
        - np.asarray(ordered[0]["center_scan_coordinates_obj_units"], dtype=float)
    )
    if float(np.dot(ordered_vector, longitudinal)) < 0.0:
        longitudinal = -longitudinal
    longitudinal /= np.linalg.norm(longitudinal)

    positive = np.mean(
        [item["center_scan_coordinates_obj_units"] for item in registry if item["bank"] == "positive"],
        axis=0,
    )
    negative = np.mean(
        [item["center_scan_coordinates_obj_units"] for item in registry if item["bank"] == "negative"],
        axis=0,
    )
    lateral = positive - negative
    lateral -= longitudinal * float(np.dot(lateral, longitudinal))
    lateral /= np.linalg.norm(lateral)
    vertical = np.cross(longitudinal, lateral)
    vertical /= np.linalg.norm(vertical)
    basis = np.column_stack((longitudinal, lateral, vertical))
    origin = centres.mean(axis=0)

    raw_min = np.full(3, np.inf)
    raw_max = np.full(3, -np.inf)
    oriented_min = np.full(3, np.inf)
    oriented_max = np.full(3, -np.inf)
    sample: list[Any] = []
    vertex_count = 0
    sample_point_count = 0
    sample_stride = 71

    with scan_path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            if not line.startswith("v "):
                continue
            fields = line.split()
            if len(fields) < 4:
                continue
            point = np.asarray((float(fields[1]), float(fields[2]), float(fields[3])), dtype=float)
            raw_min = np.minimum(raw_min, point)
            raw_max = np.maximum(raw_max, point)
            local = (point - origin) @ basis
            oriented_min = np.minimum(oriented_min, local)
            oriented_max = np.maximum(oriented_max, local)
            if vertex_count % sample_stride == 0:
                sample_point_count += 1
                if keep_sample:
                    sample.append(local)
            vertex_count += 1

    if vertex_count == 0:
        raise ValueError(f"{scan_path}: aucun sommet OBJ")

    sample_array = np.asarray(sample, dtype=float) if keep_sample else np.empty((0, 3), dtype=float)
    if keep_sample:
        sample_array -= oriented_min

    scale = float(config["engine_screening"]["obj_unit_to_mm"])
    f21 = load_json(ROOT / config["inputs"]["engine_scan_sha256_contract"])
    expected_hash = f21["asset"]["source_scan_sha256"]
    actual_hash = hash_file(scan_path)
    return {
        "vertex_count": vertex_count,
        "sample_point_count": sample_point_count,
        "raw_bounds_obj_units": {
            "minimum": rounded(raw_min),
            "maximum": rounded(raw_max),
            "size": rounded(raw_max - raw_min),
        },
        "screening_frame": {
            "basis_columns_in_scan_coordinates": rounded(basis.T, 9),
            "oriented_bounds_obj_units": {
                "minimum": rounded(oriented_min),
                "maximum": rounded(oriented_max),
                "size": rounded(oriented_max - oriented_min),
            },
            "screening_size_mm": rounded((oriented_max - oriented_min) * scale),
            "scale_mm_per_obj_unit": scale,
            "scale_verified": False,
            "orientation_verified": False,
        },
        "source_scan_sha256": actual_hash,
        "source_scan_sha256_matches_f21": actual_hash == expected_hash,
        "sample": sample_array * scale,
    }


def power_torque_screen(config: dict[str, Any]) -> dict[str, Any]:
    power_hp = float(config["power_screening"]["target_power_hp"])
    torque_by_speed: dict[str, float] = {}
    for speed in config["power_screening"]["speed_range_rpm"]:
        speed = float(speed)
        torque_nm = power_hp * 745.6998715822702 / (2.0 * math.pi * speed / 60.0)
        torque_by_speed[str(int(speed))] = round(torque_nm, 1)

    candidate_ratings = {
        "dma_1071_w_2wd_five_speed": 1200.0,
        "dma_1071_w_2wd_six_speed": 900.0,
        "dma_s1098_endurance": 900.0,
        "dma_s1098_sprint_hillclimb": 1300.0,
        "hewland_lws_200": 935.0,
    }
    minimum_required = max(torque_by_speed.values())
    comparisons = {
        candidate: {
            "published_rating_nm": rating,
            "margin_to_1600_hp_at_8000_rpm_nm": round(rating - minimum_required, 1),
            "passes_zero_factor_8000_rpm_screen": rating >= minimum_required,
            "accepted_for_vehicle": False,
        }
        for candidate, rating in candidate_ratings.items()
    }
    return {
        "target_power_hp": power_hp,
        "mathematical_input_torque_nm": torque_by_speed,
        "basis": "P=T*omega; this is not a measured 917/30 torque curve",
        "candidate_comparisons": comparisons,
        "gearbox_selected": None,
        "reason": "No public candidate combines accepted duty-cycle margin, installation GA, bellhousing interface and overall dimensions.",
    }


def compute_layouts(
    config: dict[str, Any],
    vehicle: dict[str, Any],
    scan_size_mm: list[float],
) -> dict[str, Any]:
    parameters = vehicle["parameters"]
    length = float(parameters["length_mm"]["value_mm"])
    width = float(parameters["width_mm"]["value_mm"])
    height = float(parameters["height_mm"]["value_mm"])
    wheelbase = float(parameters["wheelbase_mm"]["value_mm"])
    centred_overhang = (length - wheelbase) / 2.0
    body_front = -centred_overhang
    stock_body_rear = wheelbase + centred_overhang

    occupant = config["occupant_and_body_screening_mm"]
    occupant_rear = float(occupant["front_occupant_rear_limit_x"])
    engine_service = config["engine_screening"]["full_engine_service_envelope_mm"]
    service_length = float(engine_service["length"])
    service_width = float(engine_service["width"])
    service_height = float(engine_service["height"])
    gearbox = config["gearbox_research"]["screening_reservation_mm"]
    gearbox_front_extent = float(gearbox["front_extent_from_differential_plane"])
    gearbox_rear_extent = float(gearbox["rear_extent_from_differential_plane_to_engine_mating_plane"])

    def front_gearbox_layout(layout_id: str, tail_extension: float) -> dict[str, Any]:
        differential_x = wheelbase
        engine_mating_x = differential_x + gearbox_rear_extent
        gearbox_front_x = differential_x - gearbox_front_extent
        engine_scan_rear_x = engine_mating_x + float(scan_size_mm[0])
        engine_service_rear_x = engine_mating_x + service_length
        body_rear = stock_body_rear + tail_extension
        rear_margin = body_rear - engine_service_rear_x
        occupant_margin = gearbox_front_x - occupant_rear
        lateral_margin = (width - service_width) / 2.0
        return {
            "layout_id": layout_id,
            "architecture": "911_rear_engine_transaxle_ahead_of_engine",
            "body_front_x_mm": body_front,
            "body_rear_x_mm": body_rear,
            "rear_tail_extension_mm": tail_extension,
            "rear_axle_x_mm": wheelbase,
            "differential_plane_x_mm": differential_x,
            "gearbox_bounds_x_mm": [gearbox_front_x, engine_mating_x],
            "engine_mating_plane_x_mm": engine_mating_x,
            "engine_scan_bounds_x_mm": [engine_mating_x, engine_scan_rear_x],
            "engine_service_bounds_x_mm": [engine_mating_x, engine_service_rear_x],
            "front_occupant_clearance_to_gearbox_mm": round(occupant_margin, 1),
            "engine_service_lateral_margin_per_side_mm": round(lateral_margin, 1),
            "engine_service_rear_body_margin_mm": round(rear_margin, 1),
            "rear_seats_deleted": True,
            "screening_pass": occupant_margin >= 100.0 and rear_margin >= 75.0 and lateral_margin >= 100.0,
        }

    def rear_gearbox_layout(layout_id: str) -> dict[str, Any]:
        differential_x = wheelbase
        engine_mating_x = differential_x - gearbox_rear_extent
        engine_scan_front_x = engine_mating_x - float(scan_size_mm[0])
        engine_service_front_x = engine_mating_x - service_length
        gearbox_rear_x = differential_x + gearbox_front_extent
        intrusion = occupant_rear - engine_service_front_x
        return {
            "layout_id": layout_id,
            "architecture": "917_mid_engine_transaxle_behind_engine",
            "body_front_x_mm": body_front,
            "body_rear_x_mm": stock_body_rear,
            "rear_tail_extension_mm": 0.0,
            "rear_axle_x_mm": wheelbase,
            "differential_plane_x_mm": differential_x,
            "gearbox_bounds_x_mm": [engine_mating_x, gearbox_rear_x],
            "engine_mating_plane_x_mm": engine_mating_x,
            "engine_scan_bounds_x_mm": [engine_scan_front_x, engine_mating_x],
            "engine_service_bounds_x_mm": [engine_service_front_x, engine_mating_x],
            "front_occupant_intrusion_mm": round(max(0.0, intrusion), 1),
            "engine_service_lateral_margin_per_side_mm": round((width - service_width) / 2.0, 1),
            "gearbox_rear_body_margin_mm": round(stock_body_rear - gearbox_rear_x, 1),
            "rear_seats_deleted": True,
            "screening_pass": intrusion <= 0.0,
        }

    trials = [
        front_gearbox_layout("911_FRONT_GEARBOX_STOCK_BODY", 0.0),
        front_gearbox_layout(
            "911_FRONT_GEARBOX_LONG_TAIL_450",
            float(occupant["preferred_rear_tail_extension"]),
        ),
        rear_gearbox_layout("917_MID_ENGINE_REAR_GEARBOX_STOCK_BODY"),
    ]
    return {
        "vehicle_reference_mm": {
            "overall_length": length,
            "overall_width": width,
            "overall_height": height,
            "wheelbase": wheelbase,
            "front_track": float(parameters["front_track_mm"]["value_mm"]),
            "rear_track": float(parameters["rear_track_mm"]["value_mm"]),
            "centred_overhang_each_end_for_visualisation": centred_overhang,
            "overhang_status": "visualisation_assumption_not_measured_axle_to_body_surface",
        },
        "engine_service_envelope_mm": {
            "length": service_length,
            "width": service_width,
            "height": service_height,
            "status": engine_service["status"],
        },
        "gearbox_reservation_mm": {
            "length": gearbox_front_extent + gearbox_rear_extent,
            "width": float(gearbox["width"]),
            "height": float(gearbox["height"]),
            "differential_to_engine_mating_plane": gearbox_rear_extent,
            "status": gearbox["status"],
        },
        "trials": trials,
        "preferred_layout_id": "911_FRONT_GEARBOX_LONG_TAIL_450",
        "preference_basis": "Only this trial preserves the existing front-occupant screening zone and leaves at least 75 mm behind the provisional full-engine service envelope.",
    }


def build_report(config: dict[str, Any], *, keep_sample: bool) -> tuple[dict[str, Any], Any]:
    scan = scan_geometry(config, keep_sample=keep_sample)
    vehicle = load_json(ROOT / config["inputs"]["vehicle_reference"])
    layouts = compute_layouts(config, vehicle, scan["screening_frame"]["screening_size_mm"])
    sample = scan.pop("sample")
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
        "gearbox_power_screening": power_torque_screen(config),
        "decision": {
            "preferred_layout_id": layouts["preferred_layout_id"],
            "gearbox_selected": None,
            "request_manufacturer_GA_before_freezing_package": True,
            "rear_seats_deleted": True,
            "stock_wheelbase_retained_in_preferred_trial": True,
            "rear_tail_extension_screening_mm": 450.0,
        },
        "outputs": {
            "designer_drawing_png": str(PNG_PATH.relative_to(ROOT)),
            "designer_drawing_svg": str(SVG_PATH.relative_to(ROOT)),
            "preferred_packaging_step": str(STEP_PATH.relative_to(ROOT)),
        },
        "claim_limits": [
            "The scan shape is real local evidence, but its 1:1 metric scale and orientation are not physically verified.",
            "The scan omits complete heads, intake, exhaust, turbochargers, cooling and service clearances.",
            "The gearbox volume is a reservation because no public manufacturer GA dimensions were found.",
            "The body silhouette and centred overhangs are presentation geometry, not measured Porsche surfaces.",
            "No fitment, structural, thermal, driveline, manufacturing, road or track claim is released.",
        ],
        "release_gates": config["release_gates"],
    }
    return report, sample


def body_side_polygon(body_front: float, body_rear: float, height: float) -> list[tuple[float, float]]:
    return [
        (body_front, 190.0),
        (body_front + 90.0, 480.0),
        (body_front + 520.0, 720.0),
        (-80.0, 890.0),
        (520.0, height * 0.94),
        (1080.0, height),
        (1580.0, height * 0.96),
        (1980.0, 1080.0),
        (2320.0, 900.0),
        (body_rear - 420.0, 760.0),
        (body_rear, 500.0),
        (body_rear, 180.0),
    ]


def draw_side_vehicle(axis: Any, layout: dict[str, Any], vehicle: dict[str, Any], *, extended: bool) -> None:
    from matplotlib.patches import Circle, Polygon, Rectangle

    front = float(layout["body_front_x_mm"])
    rear = float(layout["body_rear_x_mm"])
    height = float(vehicle["overall_height"])
    body = Polygon(
        body_side_polygon(front, rear, height),
        closed=True,
        facecolor="#d8dde1" if extended else "#e7e9eb",
        edgecolor="#1b2228",
        linewidth=1.4,
        alpha=0.58,
        zorder=1,
    )
    axis.add_patch(body)
    for axle in (0.0, float(vehicle["wheelbase"])):
        axis.add_patch(Circle((axle, 330.0), 320.0, facecolor="#13181c", edgecolor="#59636b", linewidth=1.2, zorder=4))
        axis.add_patch(Circle((axle, 330.0), 185.0, facecolor="#d0d5d8", edgecolor="#59636b", linewidth=1.0, zorder=5))
    axis.axvspan(1365.0, 1840.0, color="#7f8790", alpha=0.18, zorder=0)
    axis.axvline(1510.0, color="#d43f52", linewidth=1.4, linestyle="--", zorder=6)
    gearbox_start, gearbox_end = layout["gearbox_bounds_x_mm"]
    axis.add_patch(Rectangle((gearbox_start, 260.0), gearbox_end - gearbox_start, 460.0, facecolor="#37a7c5", edgecolor="#12627a", linewidth=1.2, alpha=0.65, zorder=2))
    service_start, service_end = layout["engine_service_bounds_x_mm"]
    axis.add_patch(Rectangle((service_start, 180.0), service_end - service_start, 800.0, facecolor="#f39a3c", edgecolor="#b35413", linewidth=1.5, alpha=0.17, zorder=2))
    axis.axvline(float(layout["differential_plane_x_mm"]), color="#37a7c5", linewidth=2.0, zorder=6)


def render_drawing(config: dict[str, Any], report: dict[str, Any], sample: Any) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.patches import Polygon, Rectangle

    vehicle = report["layout_screening"]["vehicle_reference_mm"]
    trials = {item["layout_id"]: item for item in report["layout_screening"]["trials"]}
    preferred = trials[report["layout_screening"]["preferred_layout_id"]]
    scan_size = np.asarray(report["scan_screening"]["screening_frame"]["screening_size_mm"], dtype=float)

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "figure.facecolor": "#f4f2ed",
            "axes.facecolor": "#f4f2ed",
            "savefig.facecolor": "#f4f2ed",
        }
    )
    figure = plt.figure(figsize=(18, 11), dpi=180)
    grid = figure.add_gridspec(2, 2, height_ratios=(1.2, 1.0), width_ratios=(1.55, 1.0), hspace=0.22, wspace=0.12)
    side = figure.add_subplot(grid[0, :])
    plan = figure.add_subplot(grid[1, 0])
    comparison = figure.add_subplot(grid[1, 1])

    draw_side_vehicle(side, preferred, vehicle, extended=True)
    mate = float(preferred["engine_mating_plane_x_mm"])
    side.scatter(mate + sample[:, 0], 300.0 + sample[:, 2], s=0.24, color="#cb5a1b", alpha=0.24, rasterized=True, zorder=3)
    side.annotate("", (mate, 1050.0), (mate + scan_size[0], 1050.0), arrowprops={"arrowstyle": "<->", "color": "#8f3d12", "linewidth": 1.2})
    side.text(mate + scan_size[0] / 2.0, 1080.0, f"scan carter/cylindres : {scan_size[0]:.0f} unités ≈ mm", ha="center", color="#8f3d12", fontsize=9)
    side.annotate("", (preferred["body_rear_x_mm"] - 450.0, 118.0), (preferred["body_rear_x_mm"], 118.0), arrowprops={"arrowstyle": "<->", "color": "#1b2228"})
    side.text(preferred["body_rear_x_mm"] - 225.0, 70.0, "+450 mm de poupe — hypothèse", ha="center", fontsize=9, color="#1b2228")
    side.text(1378.0, 1210.0, "places arrière supprimées", fontsize=9, color="#555d64")
    side.text(1530.0, 1030.0, "cloison feu\nà mesurer", fontsize=8, color="#b12639")
    side.text(1870.0, 520.0, "boîte devant", fontsize=10, color="#07526a", fontweight="bold")
    side.text(2730.0, 760.0, "flat-12", fontsize=12, color="#9b3f0b", fontweight="bold")
    side.set_title("ESSAI RETENU F0 — ARCHITECTURE 911 : BOÎTE DEVANT, FLAT-12 DERRIÈRE", fontsize=14, fontweight="bold", color="#161c20")
    side.set_xlim(float(preferred["body_front_x_mm"]) - 180.0, float(preferred["body_rear_x_mm"]) + 180.0)
    side.set_ylim(0.0, 1510.0)
    side.set_aspect("equal", adjustable="box")
    side.set_xlabel("X depuis l’axe avant [mm]")
    side.set_ylabel("Z de visualisation [mm]")
    side.grid(color="#8d9499", linewidth=0.35, alpha=0.28)

    front = float(preferred["body_front_x_mm"])
    rear = float(preferred["body_rear_x_mm"])
    half_width = float(vehicle["overall_width"]) / 2.0
    top_points = [
        (front, -460.0),
        (-520.0, -760.0),
        (0.0, -half_width),
        (1100.0, -790.0),
        (2272.0, -half_width),
        (rear - 520.0, -720.0),
        (rear, -430.0),
        (rear, 430.0),
        (rear - 520.0, 720.0),
        (2272.0, half_width),
        (1100.0, 790.0),
        (0.0, half_width),
        (-520.0, 760.0),
        (front, 460.0),
    ]
    plan.add_patch(Polygon(top_points, closed=True, facecolor="#d8dde1", edgecolor="#1b2228", linewidth=1.3, alpha=0.58))
    plan.add_patch(Rectangle((1365.0, -620.0), 475.0, 1240.0, facecolor="#7f8790", edgecolor="none", alpha=0.16))
    gearbox_start, gearbox_end = preferred["gearbox_bounds_x_mm"]
    gearbox_width = float(report["layout_screening"]["gearbox_reservation_mm"]["width"])
    plan.add_patch(Rectangle((gearbox_start, -gearbox_width / 2.0), gearbox_end - gearbox_start, gearbox_width, facecolor="#37a7c5", edgecolor="#12627a", linewidth=1.2, alpha=0.65))
    service_start, service_end = preferred["engine_service_bounds_x_mm"]
    service_width = float(report["layout_screening"]["engine_service_envelope_mm"]["width"])
    plan.add_patch(Rectangle((service_start, -service_width / 2.0), service_end - service_start, service_width, facecolor="#f39a3c", edgecolor="#b35413", linewidth=1.4, alpha=0.16))
    plan.scatter(mate + sample[:, 0], sample[:, 1] - scan_size[1] / 2.0, s=0.24, color="#cb5a1b", alpha=0.24, rasterized=True)
    plan.axvline(float(preferred["rear_axle_x_mm"]), color="#1b2228", linewidth=1.0, linestyle=":")
    plan.text(2390.0, 700.0, f"réserve moteur complet : {service_width:.0f} mm", color="#9b3f0b", fontsize=9)
    plan.text(1740.0, 330.0, f"réserve boîte : {gearbox_width:.0f} mm", color="#07526a", fontsize=9)
    plan.set_title("VUE DE DESSUS — LE SCAN RESTE DANS LA LARGEUR, LES PÉRIPHÉRIQUES SONT RÉSERVÉS", fontsize=11, fontweight="bold")
    plan.set_xlim(front - 120.0, rear + 120.0)
    plan.set_ylim(-1000.0, 1000.0)
    plan.set_aspect("equal", adjustable="box")
    plan.set_xlabel("X [mm]")
    plan.set_ylabel("Y [mm]")
    plan.grid(color="#8d9499", linewidth=0.35, alpha=0.28)

    comparison.set_title("TROIS IMPLANTATIONS TESTÉES", fontsize=12, fontweight="bold")
    row_y = [2.5, 1.5, 0.5]
    colors = ["#c73f4e", "#2a9b73", "#c73f4e"]
    labels = [
        "911 / boîte devant / carrosserie stock",
        "911 / boîte devant / poupe +450",
        "917 / moteur central / boîte derrière",
    ]
    ordered_trials = [
        trials["911_FRONT_GEARBOX_STOCK_BODY"],
        trials["911_FRONT_GEARBOX_LONG_TAIL_450"],
        trials["917_MID_ENGINE_REAR_GEARBOX_STOCK_BODY"],
    ]
    for y, color, label, trial in zip(row_y, colors, labels, ordered_trials):
        body_start = float(trial["body_front_x_mm"])
        body_end = float(trial["body_rear_x_mm"])
        comparison.plot((body_start, body_end), (y, y), color="#7f878d", linewidth=10.0, alpha=0.32, solid_capstyle="round")
        engine_start, engine_end = trial["engine_service_bounds_x_mm"]
        box_start, box_end = trial["gearbox_bounds_x_mm"]
        comparison.plot((box_start, box_end), (y, y), color="#2392b1", linewidth=8.0, solid_capstyle="butt")
        comparison.plot((engine_start, engine_end), (y, y), color="#e47725", linewidth=8.0, solid_capstyle="butt")
        comparison.text(body_start, y + 0.25, label, fontsize=8.5, color="#22282d", fontweight="bold")
        if trial["layout_id"] == "911_FRONT_GEARBOX_STOCK_BODY":
            note = f"dépassement arrière {abs(trial['engine_service_rear_body_margin_mm']):.0f} mm"
        elif trial["layout_id"] == "911_FRONT_GEARBOX_LONG_TAIL_450":
            note = f"marge arrière {trial['engine_service_rear_body_margin_mm']:.0f} mm — retenu F0"
        else:
            note = f"intrusion zone occupants {trial['front_occupant_intrusion_mm']:.0f} mm"
        comparison.text(body_start, y - 0.29, note, fontsize=8.5, color=color)
    comparison.set_xlim(-1120.0, 3890.0)
    comparison.set_ylim(0.0, 3.05)
    comparison.set_yticks([])
    comparison.set_xlabel("X depuis l’axe avant [mm]")
    comparison.grid(axis="x", color="#8d9499", linewidth=0.35, alpha=0.28)
    for spine in ("left", "right", "top"):
        comparison.spines[spine].set_visible(False)

    figure.suptitle("PORSCHE 911–917/30 — ÉTUDE D’ENCOMBREMENT DESIGN F0", fontsize=20, fontweight="bold", color="#11171b", y=0.975)
    figure.text(
        0.5,
        0.018,
        "Orange plein : projection du scan réel · orange transparent : réserve moteur complet · bleu : réserve de boîte\n"
        "ÉCHELLE DU SCAN, SURFACES DE CAISSE ET DIMENSIONS DE BOÎTE NON VÉRIFIÉES — AUCUNE LIBÉRATION FABRICATION / ROUTE / CIRCUIT",
        ha="center",
        fontsize=9,
        color="#4f585f",
    )
    WORK_ROOT.mkdir(parents=True, exist_ok=True)
    figure.savefig(PNG_PATH, bbox_inches="tight", pad_inches=0.18, metadata={"Software": "matplotlib; 911-917 packaging F0"})
    figure.savefig(SVG_PATH, bbox_inches="tight", pad_inches=0.18, metadata={"Date": None})
    plt.close(figure)


def build_cad(report: dict[str, Any]) -> None:
    from build123d import Align, Box, Compound, Pos, export_step

    layouts = {item["layout_id"]: item for item in report["layout_screening"]["trials"]}
    layout = layouts[report["layout_screening"]["preferred_layout_id"]]
    vehicle = report["layout_screening"]["vehicle_reference_mm"]
    scan_size = report["scan_screening"]["screening_frame"]["screening_size_mm"]
    gearbox = report["layout_screening"]["gearbox_reservation_mm"]
    service = report["layout_screening"]["engine_service_envelope_mm"]
    front = float(layout["body_front_x_mm"])
    rear = float(layout["body_rear_x_mm"])
    width = float(vehicle["overall_width"])
    height = float(vehicle["overall_height"])
    gearbox_start, gearbox_end = (float(value) for value in layout["gearbox_bounds_x_mm"])
    scan_start, scan_end = (float(value) for value in layout["engine_scan_bounds_x_mm"])
    service_start, service_end = (float(value) for value in layout["engine_service_bounds_x_mm"])

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
    add("POWERTRAIN_FIREWALL_SCREENING", Pos(1510.0, 0.0, 650.0) * Box(24.0, 1300.0, 940.0, align=Align.CENTER))
    add("REAR_SEAT_DELETE_VOLUME", Pos((1365.0 + 1840.0) / 2.0, 0.0, 520.0) * Box(475.0, 1240.0, 680.0, align=Align.CENTER))
    add(
        "GEARBOX_RESERVED_VOLUME_NOT_VENDOR_GA",
        Pos((gearbox_start + gearbox_end) / 2.0, 0.0, 180.0 + float(gearbox["height"]) / 2.0)
        * Box(gearbox_end - gearbox_start, float(gearbox["width"]), float(gearbox["height"]), align=Align.CENTER),
    )
    add(
        "ENGINE_SCAN_ORIENTED_BOUNDING_BOX_SCALE_UNVERIFIED",
        Pos((scan_start + scan_end) / 2.0, 0.0, 300.0 + float(scan_size[2]) / 2.0)
        * Box(scan_end - scan_start, float(scan_size[1]), float(scan_size[2]), align=Align.CENTER),
    )
    add(
        "COMPLETE_ENGINE_SERVICE_RESERVED_VOLUME_NOT_MEASURED",
        Pos((service_start + service_end) / 2.0, 0.0, 180.0 + float(service["height"]) / 2.0)
        * Box(service_end - service_start, float(service["width"]), float(service["height"]), align=Align.CENTER),
    )
    for name, x_value in (("FRONT_AXLE", 0.0), ("REAR_AXLE", float(vehicle["wheelbase"]))):
        add(name, Pos(x_value, 0.0, 330.0) * Box(18.0, width, 18.0, align=Align.CENTER))
    add("DIFFERENTIAL_PLANE", Pos(float(layout["differential_plane_x_mm"]), 0.0, 420.0) * Box(12.0, 900.0, 500.0, align=Align.CENTER))

    compound = Compound(children=shapes, label="911 917 PACKAGING F0 - SCREENING ONLY")
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
        raise SystemExit("packaging-report-f0.json n'est pas reproductible; relancer --mode render")
    if not expected["source_integrity"]["source_scan_sha256_matches_f21"]:
        raise SystemExit("le scan local ne correspond pas au SHA-256 F21")
    preferred = next(
        item
        for item in expected["layout_screening"]["trials"]
        if item["layout_id"] == expected["decision"]["preferred_layout_id"]
    )
    if not preferred["screening_pass"]:
        raise SystemExit("l'implantation retenue ne passe pas le screening d'encombrement")
    if expected["gearbox_power_screening"]["gearbox_selected"] is not None:
        raise SystemExit("une boîte a été sélectionnée sans dossier constructeur complet")
    if any(expected["release_gates"].values()):
        raise SystemExit("un gate de libération interdit est ouvert")
    for path, minimum_size in ((PNG_PATH, 50_000), (SVG_PATH, 50_000), (STEP_PATH, 20_000)):
        if not path.exists() or path.stat().st_size < minimum_size:
            raise SystemExit(f"sortie absente ou trop petite: {path.relative_to(ROOT)}")
    print("911-917 packaging F0: PASS (screening only, all release gates closed)")


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
        build_cad(report)
        print(STEP_PATH.relative_to(ROOT))
    if args.mode == "check":
        check_outputs(config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
