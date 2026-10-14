#!/usr/bin/env python3
"""Étude cinématique analytique; prépare les entrées du contrôle natif PicoGK."""
import json
import math
from pathlib import Path

from annotate_picogk_visualization_f11 import sha256

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "work/911-917-picogk-f14"


def travel_case(track, flange, travel):
    if not all(math.isfinite(v) for v in (track, flange, travel)) or flange <= 0 or track <= 2 * flange or travel < 0:
        raise ValueError("invalid driveline dimensions")
    span = track / 2 - flange
    return {"travel_each_direction_mm": travel, "nominal_joint_distance_mm": span,
            "maximum_joint_distance_mm": math.hypot(span, travel),
            "required_length_change_mm": math.hypot(span, travel) - span,
            "required_joint_angle_deg": math.degrees(math.atan2(travel, span))}


def validate_config(config):
    positive = ("sample_step_mm", "required_clearance_mm", "voxel_guard_cells", "candidate_rear_track_mm",
                "candidate_rail_y_mm", "candidate_rail_z_mm", "candidate_floor_width_mm", "candidate_floor_z_mm")
    if any(not math.isfinite(config[k]) or config[k] <= 0 for k in positive):
        raise ValueError("positive finite dimensions required")
    cases = config["wheel_vertical_travel_cases_mm"]
    if not cases or any(not math.isfinite(v) or v <= 0 for v in cases) or config["sample_step_mm"] > min(cases):
        raise ValueError("invalid travel sampling")
    bounds = config["inspection_bounds_mm"]
    if (len(bounds) != 2 or any(len(row) != 3 for row in bounds)
            or any(not math.isfinite(v) for row in bounds for v in row)
            or any(a >= b for a, b in zip(*bounds))):
        raise ValueError("ordered finite inspection bounds required")
    if not config["candidate_crossmember_x_mm"] or any(not math.isfinite(v) for v in config["candidate_crossmember_x_mm"]):
        raise ValueError("finite crossmember positions required")
    if any(value is not None for value in config["unknowns"].values()):
        raise ValueError("measured interfaces require a new evidence-backed study")


def build():
    paths = [ROOT / "twins/vehicle-911-917" / name for name in (
        "rear-driveline-study-f14.json", "picogk-full-vehicle-f12.json", "picogk-mechanical-f13.json")]
    packaging_path = ROOT / "twins/vehicle-911-917/packaging-concept-f1.json"
    config, f12, f13 = [json.loads(p.read_text()) for p in paths]
    validate_config(config)
    packaging = json.loads(packaging_path.read_text())
    vehicle_path = ROOT / packaging["inputs"]["vehicle_reference"]
    vehicle = json.loads(vehicle_path.read_text())["parameters"]
    engine = packaging["engine_screening"]["full_engine_service_envelope_mm"]
    gearbox = packaging["rear_transaxle_screening"]
    axle_x = vehicle["wheelbase_mm"]["value_mm"] + packaging["body_and_occupant_screening_mm"]["selected_wheelbase_extension"]
    mating_x = axle_x - gearbox["engine_mating_plane_ahead_of_differential_mm"]
    tracks = {"baseline": vehicle["rear_track_mm"]["value_mm"], "candidate": config["candidate_rear_track_mm"]}
    flange = f13["transaxle"]["output_flange_half_span_mm"]
    config["rear_axle_x_mm"] = axle_x
    config["axle_z_mm"] = f12["wheel_reservation"]["centre_z_mm"]
    config["baseline_rear_track_mm"] = tracks["baseline"]
    config["flange_half_span_mm"] = flange
    config["shaft_radius_mm"] = f13["halfshafts"]["shaft_radius_mm"]
    config["joint_radius_mm"] = f13["halfshafts"]["cv_joint_radius_mm"]
    config["wheel_width_mm"] = f12["wheel_reservation"]["width_mm"]
    config["wheel_radius_mm"] = f12["wheel_reservation"]["outer_diameter_mm"] / 2
    config["gearbox_bounds_x_mm"] = [mating_x, axle_x + gearbox["rear_extent_from_differential_plane_mm"]]
    config["engine_service_bounds_x_mm"] = [mating_x - engine["length"], mating_x]
    config["kinematics"] = {name: [travel_case(track, flange, dz) for dz in config["wheel_vertical_travel_cases_mm"]]
                            for name, track in tracks.items()}
    config["tyre_outer_width_mm"] = {name: track + config["wheel_width_mm"] for name, track in tracks.items()}
    half_rail_width = f12["rear_structure_corridors"]["rail_size_mm"][1] / 2
    config["candidate_lateral_gaps_mm"] = {
        "engine_envelope_to_rail": config["candidate_rail_y_mm"] - half_rail_width - engine["width"] / 2,
        "rail_to_tyre_inner_face": tracks["candidate"] / 2 - config["wheel_width_mm"] / 2 - config["candidate_rail_y_mm"] - half_rail_width}
    travel = max(config["wheel_vertical_travel_cases_mm"])
    joint = config["joint_radius_mm"]
    frame = f12["rear_structure_corridors"]
    config["candidate_analytic_clearance_lower_bounds_mm"] = {
        "swept_shafts_to_floor": config["axle_z_mm"] - travel - joint - (config["candidate_floor_z_mm"] + 10),
        "swept_shafts_to_rails": config["candidate_rail_z_mm"] - frame["rail_size_mm"][2] / 2 - (config["axle_z_mm"] + travel + joint),
        "swept_shafts_to_rear_crossmember": min(config["candidate_crossmember_x_mm"]) - frame["crossmember_size_mm"][0] / 2 - config["rear_axle_x_mm"] - joint}
    # Two power conventions bracket the unconfirmed meaning of the user's 1600 ch.
    config["torque_sensitivity"] = [{"power_unit": unit, "power_w": 1600 * conversion, "rpm": rpm,
        "equivalent_input_torque_nm": 1600 * conversion / (2 * math.pi * rpm / 60)}
        for unit, conversion in (("metric_ch", 735.49875), ("mechanical_hp", 745.6998715822702))
        for rpm in (7000, 8000, 9000)]
    sources = [Path(__file__), ROOT / "twins/vehicle-911-917/picogk/Program.cs",
               ROOT / "twins/vehicle-911-917/picogk/RearDrivelineStudy.cs"]
    config["inputs"] = [{"path": str(p.relative_to(ROOT)), "sha256": sha256(p)} for p in paths + [packaging_path, vehicle_path] + sources]
    config["release_gates"] = {key: False for key in ("physical_fit_verified", "suspension_kinematics_verified",
        "joint_capacity_verified", "structural_strength_verified", "transaxle_selected", "manufacturing_authorized")}
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "study-inputs-f14.json").write_text(json.dumps(config, indent=2) + "\n")
    print(json.dumps({k: config[k] for k in ("kinematics", "tyre_outer_width_mm", "candidate_lateral_gaps_mm")}, indent=2))


if __name__ == "__main__":
    build()
