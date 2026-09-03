#!/usr/bin/env python3
"""Construit les fonctions usinables F37 en B-Rep OCCT autour de F36-013.

La peau organique issue du scan reste un maillage local. F37 exporte des STEP
exactes pour les interfaces, le porte-culbuteurs, les noyaux d'huile et les
surépaisseurs; il ne prétend pas convertir le scan ouvert en CAO de série.
"""

from __future__ import annotations

import argparse
import hashlib
from importlib import metadata
import json
import math
from pathlib import Path
import platform
import re
from typing import Any


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"expected_json_object:{path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_parent_geometry_link(
    contract: dict[str, Any], geometry: dict[str, Any], head_stl: Path
) -> None:
    """Lie le rapport géométrique F36 au même STL parent que le contrat F37."""

    actual_sha256 = sha256(head_stl)
    require(
        actual_sha256 == contract["parent"]["head_sha256"],
        "parent_head_hash_mismatch",
    )
    recorded = geometry.get("files_local_only", {}).get(head_stl.name)
    require(isinstance(recorded, dict), "geometry_report_parent_head_record_missing")
    require(
        recorded.get("sha256") == actual_sha256,
        "geometry_report_parent_head_hash_mismatch",
    )
    require(
        recorded.get("bytes") == head_stl.stat().st_size,
        "geometry_report_parent_head_size_mismatch",
    )


def validate_rocker_pivot_reaction_screen(contract: dict[str, Any]) -> None:
    """Ferme l'enveloppe de réaction sur le rapport cinématique contractuel."""

    rocker = contract["rocker_carrier"]
    screen = contract["rocker_pivot_reaction_screen"]
    ratio = float(screen["cam_to_valve_force_ratio"])
    target = float(rocker["target_rocker_ratio"])
    factor = float(screen["collinear_upper_envelope_factor"])
    require(
        screen["model"] == "ideal_rocker_collinear_upper_envelope",
        "rocker_pivot_reaction_model_not_supported",
    )
    require(
        math.isclose(ratio, target, rel_tol=0.0, abs_tol=1.0e-12),
        "rocker_pivot_cam_to_valve_ratio_mismatch",
    )
    require(
        math.isclose(factor, 1.0 + ratio, rel_tol=0.0, abs_tol=1.0e-12),
        "rocker_pivot_collinear_envelope_factor_mismatch",
    )
    require(
        screen["actual_resultant_direction_complete"] is False,
        "rocker_pivot_resultant_direction_must_remain_fail_closed",
    )


def canonicalize_step_header(path: Path) -> None:
    payload = path.read_text(encoding="utf-8")
    canonical, count = re.subn(
        r"(FILE_NAME\([^,]+,')[^']+(')",
        r"\g<1>1970-01-01T00:00:00\g<2>",
        payload,
        count=1,
    )
    require(count == 1, f"step_header_timestamp_not_found:{path}")
    path.write_text(canonical, encoding="utf-8", newline="\n")


def vector(value: Any) -> list[float]:
    return [round(float(value.X), 6), round(float(value.Y), 6), round(float(value.Z), 6)]


def shape_metrics(shape: Any) -> dict[str, Any]:
    solids = list(shape.solids())
    bounds = shape.bounding_box()
    return {
        "valid": bool(shape.is_valid),
        "manifold": bool(shape.is_manifold),
        "solid_count": len(solids),
        "all_solids_closed": bool(solids)
        and all(
            solid.is_valid
            and solid.is_manifold
            and len(solid.shells()) == 1
            and solid.shells()[0].is_manifold
            and solid.volume > 0.0
            for solid in solids
        ),
        "face_count": len(shape.faces()),
        "edge_count": len(shape.edges()),
        "volume_mm3": round(sum(solid.volume for solid in solids), 6),
        "bounds_min_mm": vector(bounds.min),
        "bounds_max_mm": vector(bounds.max),
        "bounds_size_mm": vector(bounds.size),
    }


def vertical_cylinder(radius: float, height: float, x: float, y: float, z: float) -> Any:
    from build123d import Align, Cylinder, Pos

    return Pos(x, y, z) * Cylinder(radius, height, align=(Align.CENTER, Align.CENTER, Align.MIN))


def valve_axis_cylinder(
    radius: float,
    length: float,
    x: float,
    y: float,
    z: float,
    tilt_y_deg: float,
) -> Any:
    """Cylindre dont l'axe suit exactement l'inclinaison soupape F36."""
    from build123d import Align, Cylinder, Pos, Rot

    return Pos(x, y, z) * Rot(-tilt_y_deg, 0.0, 0.0) * Cylinder(
        radius,
        length,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )


def x_cylinder(radius: float, length: float, x: float, y: float, z: float) -> Any:
    from build123d import Align, Cylinder, Pos, Rot

    return Pos(x, y, z) * Rot(0.0, 90.0, 0.0) * Cylinder(
        radius, length, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )


def y_cylinder(radius: float, length: float, x: float, y: float, z: float) -> Any:
    from build123d import Align, Cylinder, Pos, Rot

    return Pos(x, y, z) * Rot(-90.0, 0.0, 0.0) * Cylinder(
        radius, length, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )


def centred_box(x_size: float, y_size: float, z_size: float, x: float, y: float, z: float) -> Any:
    from build123d import Align, Box, Pos

    return Pos(x, y, z) * Box(
        x_size,
        y_size,
        z_size,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )


def build_carrier(contract: dict[str, Any], geometry: dict[str, Any]) -> Any:
    rocker = contract["rocker_carrier"]
    rail_x, rail_y, rail_z = rocker["rail_size_xyz_mm"]
    axis_z = rocker["intake_axis_yz_mm"][1]
    rail_bottom = rocker["rail_centre_z_mm"] - rail_z / 2.0
    rail_top = rocker["rail_centre_z_mm"] + rail_z / 2.0
    body = None
    for y in (rocker["intake_axis_yz_mm"][0], rocker["exhaust_axis_yz_mm"][0]):
        rail = centred_box(rail_x, rail_y, rail_z, 0.0, y, rocker["rail_centre_z_mm"])
        body = rail if body is None else body + rail
    stud_centres = geometry["geometry"]["packaging_checks"]["stud_centres_local_mm"]
    bridge_y = max(y for _, y in stud_centres) - min(y for _, y in stud_centres) + rocker["mount_boss_outer_diameter_mm"]
    for x in sorted({round(float(x), 1) for x, _ in stud_centres}):
        body = body + centred_box(
            rocker["mount_bridge_width_x_mm"],
            bridge_y,
            rocker["mount_bridge_height_z_mm"],
            x,
            0.0,
            rail_bottom + rocker["mount_bridge_height_z_mm"] / 2.0,
        )

    # Le porte-axes n'est plus suspendu dans la cavite. Quatre pieds usinables
    # reprennent exactement le motif des goujons mesure dans le rapport F36.
    # Le serrage final reste conditionnel a des goujons allonges et a une pile
    # de cales/ecrous definie par un fournisseur.
    foot_height = rail_bottom - rocker["mount_interface_z_mm"]
    for x, y in stud_centres:
        body = body + vertical_cylinder(
            rocker["mount_boss_outer_diameter_mm"] / 2.0,
            foot_height,
            x,
            y,
            rocker["mount_interface_z_mm"],
        )

    # Fenetres parametriques des quatre culbuteurs. Leur largeur Y depasse les
    # rails elargis afin de ne pas recreer le conflit detecte par l'ecran CAO.
    window_bottom = axis_z - 10.5
    window_top = rail_top + 2.0
    window_x, window_y = rocker["rocker_window_size_xy_mm"]
    for y in (rocker["intake_axis_yz_mm"][0], rocker["exhaust_axis_yz_mm"][0]):
        for x in (-18.0, 18.0):
            body = body - centred_box(
                window_x,
                window_y,
                window_top - window_bottom,
                x,
                y,
                0.5 * (window_bottom + window_top),
            )

    shaft_radius_printed = rocker["shaft_as_printed_bore_diameter_mm"] / 2.0
    for y in (rocker["intake_axis_yz_mm"][0], rocker["exhaust_axis_yz_mm"][0]):
        body = body - x_cylinder(shaft_radius_printed, 114.0, -57.0, y, axis_z)
        body = body - x_cylinder(contract["oil_system"]["carrier_gallery_diameter_mm"] / 2.0, 114.0, -57.0, y, contract["oil_system"]["carrier_gallery_z_mm"])
    for x, y in stud_centres:
        body = body - vertical_cylinder(
            rocker["mount_as_printed_pilot_mm"] / 2.0,
            rail_top - rocker["mount_interface_z_mm"] + 4.0,
            x,
            y,
            rocker["mount_interface_z_mm"] - 2.0,
        )
    return body


def build_rockers(contract: dict[str, Any]) -> Any:
    from build123d import Compound

    rocker = contract["rocker_carrier"]
    axis_z = rocker["intake_axis_yz_mm"][1]
    arm_x, arm_z = rocker["rocker_arm_section_xz_mm"]
    solids = []
    for y in (rocker["intake_axis_yz_mm"][0], rocker["exhaust_axis_yz_mm"][0]):
        for x in (-18.0, 18.0):
            valve_contact_y = math.copysign(48.0, y)
            arm_centre_y = 0.5 * (y + valve_contact_y)
            arm_length_y = abs(valve_contact_y - y) + 8.0
            arm = centred_box(arm_x, arm_length_y, arm_z, x, arm_centre_y, axis_z)
            # Le bossage circulaire maintient une section continue autour de
            # l'alésage d'axe. Sans lui, un alésage de 14 mm traversant un bras
            # de 9 mm sépare artificiellement l'enveloppe en deux solides.
            arm = arm + x_cylinder(10.0, arm_x, x - arm_x / 2.0, y, axis_z)
            arm = arm - x_cylinder(
                rocker["shaft_final_diameter_mm"] / 2.0 + 0.05,
                arm_x + 2.0,
                x - arm_x / 2.0 - 1.0,
                y,
                axis_z,
            )
            arm = arm - vertical_cylinder(3.5, 22.0, x, valve_contact_y, axis_z - 12.0)
            solids.append(arm)
    return Compound(solids)


def build_allowances(contract: dict[str, Any], geometry: dict[str, Any]) -> Any:
    from build123d import Compound

    allowance = contract["machining_allowances_mm_if_scale_is_mm"]
    architecture = geometry["geometry"]["architecture"]
    shapes = []
    register_radius = architecture["register_diameter_mm"] / 2.0
    shapes.append(vertical_cylinder(register_radius + allowance["cylinder_register_radial"], allowance["combustion_deck_axial"], 0.0, 0.0, 0.0))
    shapes.append(
        vertical_cylinder(register_radius + allowance["cylinder_register_radial"], 5.0, 0.0, 0.0, -5.0)
        - vertical_cylinder(register_radius, 5.0, 0.0, 0.0, -5.0)
    )
    for family in ("intake", "exhaust"):
        data = architecture[family]
        angle = float(data["tilt_y_deg"])
        for x, y, z in data["centres_mm"]:
            seat_final = data["seat_bore_diameter_mm"] / 2.0
            seat_print = seat_final - allowance["valve_seat_pocket_radial"]
            shapes.append(
                valve_axis_cylinder(seat_final, 8.0, x, y, z - 1.0, angle)
                - valve_axis_cylinder(seat_print, 8.0, x, y, z - 1.0, angle)
            )
            guide_final = data["guide_bore_diameter_mm"] / 2.0
            guide_print = guide_final - allowance["valve_guide_bore_radial"]
            shapes.append(
                valve_axis_cylinder(guide_final, 56.0, x, y, z + 3.0, angle)
                - valve_axis_cylinder(guide_print, 56.0, x, y, z + 3.0, angle)
            )
    for x, y in geometry["geometry"]["packaging_checks"]["stud_centres_local_mm"]:
        final_radius = architecture["stud_hole_diameter_mm"] / 2.0
        shapes.append(
            vertical_cylinder(final_radius, 96.0, x, y, -7.0)
            - vertical_cylinder(final_radius - allowance["head_stud_bore_radial"], 96.0, x, y, -7.0)
        )
    for x, y in geometry["geometry"]["packaging_checks"]["stud_centres_local_mm"]:
        shapes.append(
            vertical_cylinder(
                contract["rocker_carrier"]["mount_boss_outer_diameter_mm"] / 2.0,
                allowance["carrier_mount_pad_axial"],
                x,
                y,
                contract["rocker_carrier"]["mount_interface_z_mm"],
            )
        )
    return Compound(shapes)


def build_oil_core(contract: dict[str, Any]) -> Any:
    oil = contract["oil_system"]
    feed = oil["head_feed_lateral"]
    core = y_cylinder(
        feed["diameter_mm"] / 2.0,
        feed["y_range_mm"][1] - feed["y_range_mm"][0],
        feed["x_mm"],
        feed["y_range_mm"][0],
        feed["z_mm"],
    )
    header = oil["head_header"]
    core = core + x_cylinder(
        header["diameter_mm"] / 2.0,
        header["x_range_mm"][1] - header["x_range_mm"][0],
        header["x_range_mm"][0],
        header["y_mm"],
        header["z_mm"],
    )
    branch_radius = oil["four_metering_branches_diameter_mm"] / 2.0
    intake_y = contract["rocker_carrier"]["intake_axis_yz_mm"][0]
    exhaust_y = contract["rocker_carrier"]["exhaust_axis_yz_mm"][0]
    branch_length = exhaust_y - intake_y
    for x in (-18.0, 18.0):
        core = core + y_cylinder(branch_radius, branch_length, x, intake_y, header["z_mm"])
        branch_height = contract["rocker_carrier"]["intake_axis_yz_mm"][1] + 2.0 - header["z_mm"]
        core = core + vertical_cylinder(branch_radius, branch_height, x, intake_y, header["z_mm"])
        core = core + vertical_cylinder(branch_radius, branch_height, x, exhaust_y, header["z_mm"])
    for y in (contract["rocker_carrier"]["intake_axis_yz_mm"][0], contract["rocker_carrier"]["exhaust_axis_yz_mm"][0]):
        core = core + x_cylinder(oil["carrier_gallery_diameter_mm"] / 2.0, 114.0, -57.0, y, oil["carrier_gallery_z_mm"])
    for x in oil["return_drains"]["x_mm"]:
        drain = oil["return_drains"]
        core = core + vertical_cylinder(
            drain["diameter_mm"] / 2.0,
            drain["z_range_mm"][1] - drain["z_range_mm"][0],
            x,
            drain["y_mm"],
            drain["z_range_mm"][0],
        )
        core = core + y_cylinder(
            drain["diameter_mm"] / 2.0,
            drain["lateral_outlet_y_range_mm"][1] - drain["lateral_outlet_y_range_mm"][0],
            x,
            drain["lateral_outlet_y_range_mm"][0],
            drain["lateral_outlet_z_mm"],
        )
    return core


def build_rocker_shafts(contract: dict[str, Any]) -> Any:
    from build123d import Compound

    rocker = contract["rocker_carrier"]
    shafts = [
        x_cylinder(rocker["shaft_final_diameter_mm"] / 2.0, 110.0, -55.0, y, rocker["intake_axis_yz_mm"][1])
        for y in (rocker["intake_axis_yz_mm"][0], rocker["exhaust_axis_yz_mm"][0])
    ]
    return Compound(shafts)


def build_finish_cutters(contract: dict[str, Any], geometry: dict[str, Any]) -> Any:
    from build123d import Align, Compound, Cylinder, Pos, Rot

    rocker = contract["rocker_carrier"]
    shapes = []
    for y in (rocker["intake_axis_yz_mm"][0], rocker["exhaust_axis_yz_mm"][0]):
        shapes.append(x_cylinder(rocker["shaft_final_diameter_mm"] / 2.0, 114.0, -57.0, y, rocker["intake_axis_yz_mm"][1]))
    for x, y in geometry["geometry"]["packaging_checks"]["stud_centres_local_mm"]:
        shapes.append(
            vertical_cylinder(
                rocker["mount_final_clearance_diameter_mm"] / 2.0,
                rocker["rail_centre_z_mm"] + 24.0 - rocker["mount_interface_z_mm"],
                x,
                y,
                rocker["mount_interface_z_mm"] - 2.0,
            )
        )

    architecture = geometry["geometry"]["architecture"]
    for family in ("intake", "exhaust"):
        data = architecture[family]
        angle = float(data["tilt_y_deg"])
        length = 62.0
        for x, y, z in data["centres_mm"]:
            # Cylindres OCCT inclines autour de X: l'axe suit la soupape F36.
            guide = Pos(x, y, z + 3.0) * Rot(-angle, 0.0, 0.0) * Cylinder(
                data["guide_bore_diameter_mm"] / 2.0,
                length,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
            )
            seat = Pos(x, y, z - 1.0) * Rot(-angle, 0.0, 0.0) * Cylinder(
                data["seat_bore_diameter_mm"] / 2.0,
                9.0,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
            )
            shapes.extend((guide, seat))

    spark = next(item for item in contract["thread_and_finish_map"] if item["id"] == "spark_insert")
    for centre in architecture["spark_plug"]["electrode_centres_mm"]:
        outward = math.copysign(13.0, centre[0])
        angle_y = math.degrees(math.atan2(outward, 87.0))
        length = math.hypot(outward, 87.0)
        shapes.append(
            Pos(centre[0], centre[1], -5.0) * Rot(0.0, angle_y, 0.0) * Cylinder(
                spark["as_printed_pilot_mm"] / 2.0,
                length,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
            )
        )

    stud = next(item for item in contract["thread_and_finish_map"] if item["id"] == "head_stud_clearance")
    for x, y in geometry["geometry"]["packaging_checks"]["stud_centres_local_mm"]:
        shapes.append(vertical_cylinder(stud["final_diameter_mm"] / 2.0, 99.0, x, y, -7.0))

    oil_plug = next(item for item in contract["thread_and_finish_map"] if item["id"] == "oil_gallery_plug")
    for x, y, z in oil_plug["axis_end_centres_mm"]:
        start_x = x - 6.0
        shapes.append(x_cylinder(oil_plug["as_printed_pilot_mm"] / 2.0, 12.0, start_x, y, z))

    sensor = next(item for item in contract["thread_and_finish_map"] if item["id"] == "temperature_sensor")
    sensor_start, sensor_end = sensor["axis_start_end_mm"]
    shapes.append(
        x_cylinder(
            sensor["as_printed_pilot_mm"] / 2.0,
            abs(sensor_end[0] - sensor_start[0]),
            min(sensor_start[0], sensor_end[0]),
            sensor_start[1],
            sensor_start[2],
        )
    )
    return Compound(shapes)


def export_shape(identifier: str, shape: Any, output: Path, expected_solids: int | None = None) -> dict[str, Any]:
    from build123d import export_step, export_stl, import_step

    created = shape_metrics(shape)
    require(created["valid"], f"invalid_created_shape:{identifier}")
    require(created["all_solids_closed"], f"open_created_shape:{identifier}")
    if expected_solids is not None:
        require(created["solid_count"] == expected_solids, f"unexpected_solid_count:{identifier}:{created['solid_count']}")
    step = output / f"{identifier}.step"
    stl = output / f"{identifier}.stl"
    export_step(shape, step)
    canonicalize_step_header(step)
    export_stl(shape, stl, tolerance=0.05, angular_tolerance=0.05)
    reopened = import_step(step)
    reopened_metrics = shape_metrics(reopened)
    require(reopened_metrics["valid"] and reopened_metrics["all_solids_closed"], f"invalid_step_roundtrip:{identifier}")
    require(reopened_metrics["solid_count"] == created["solid_count"], f"step_solid_count_drift:{identifier}")
    volume_drift = abs(reopened_metrics["volume_mm3"] - created["volume_mm3"]) / max(created["volume_mm3"], 1.0e-9)
    require(volume_drift <= 1.0e-5, f"step_volume_drift:{identifier}:{volume_drift}")
    return {
        "id": identifier,
        "created": created,
        "reopened_step": reopened_metrics,
        "step_roundtrip_relative_volume_drift": volume_drift,
        "step": {"path": step.name, "bytes": step.stat().st_size, "sha256": sha256(step)},
        "stl": {"path": stl.name, "bytes": stl.stat().st_size, "sha256": sha256(stl)},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--geometry-report", type=Path, required=True)
    parser.add_argument("--head-stl", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    contract = load(args.contract)
    geometry = load(args.geometry_report)
    require(contract["phase"] == "F37", "contract_phase_must_be_f37")
    require(geometry["phase"] == "F36", "geometry_phase_must_be_f36")
    validate_rocker_pivot_reaction_screen(contract)
    validate_parent_geometry_link(contract, geometry, args.head_stl)
    require(
        geometry["geometry"]["candidate_mass_kg_if_obj_unit_is_mm_and_density_2670"] <= 2.83,
        "parent_mass_gate_failed",
    )
    args.output.mkdir(parents=True, exist_ok=True)

    carrier = build_carrier(contract, geometry)
    rockers = build_rockers(contract)
    shafts = build_rocker_shafts(contract)
    allowances = build_allowances(contract, geometry)
    oil_core = build_oil_core(contract)
    finish_cutters = build_finish_cutters(contract, geometry)
    artifacts = [
        export_shape("rocker-carrier-as-printed", carrier, args.output, expected_solids=1),
        export_shape("four-rocker-envelopes", rockers, args.output, expected_solids=4),
        export_shape("two-rocker-shafts", shafts, args.output, expected_solids=2),
        export_shape("machining-allowance-volumes", allowances, args.output),
        export_shape("oil-gallery-core", oil_core, args.output, expected_solids=1),
        export_shape("finish-machining-cutters", finish_cutters, args.output),
    ]
    artifact_by_id = {item["id"]: item for item in artifacts}
    carrier_bounds = artifact_by_id["rocker-carrier-as-printed"]["created"]
    oil_metrics = artifact_by_id["oil-gallery-core"]["created"]
    allowance = contract["machining_allowances_mm_if_scale_is_mm"]
    rocker = contract["rocker_carrier"]
    window_x, window_y = rocker["rocker_window_size_xy_mm"]
    arm_x, _ = rocker["rocker_arm_section_xz_mm"]
    axis_z = rocker["intake_axis_yz_mm"][1]
    rail_y = rocker["rail_size_xyz_mm"][1]
    rail_top = rocker["rail_centre_z_mm"] + rocker["rail_size_xyz_mm"][2] / 2.0
    window_bottom = axis_z - 10.5
    window_top = rail_top + 2.0
    window_clearances = {
        "arm_to_window_per_side_x": (window_x - arm_x) / 2.0,
        "window_overcut_beyond_rail_per_side_y": (window_y - rail_y) / 2.0,
        "boss_to_window_bottom_z": axis_z - 10.0 - window_bottom,
        "boss_to_window_top_z": window_top - (axis_z + 10.0),
    }
    minimum_window_clearance = min(window_clearances.values())
    report = {
        "schema_version": "1.0.0",
        "phase": "F37",
        "status": "functional_brep_definition_exported_roundtrip_verified_release_blocked",
        "classification": "analytic_functional_definition_around_scan_mesh_not_whole_head_production_brep",
        "toolchain": {
            "python": platform.python_version(),
            "build123d": metadata.version("build123d"),
            "cadquery_ocp_novtk": metadata.version("cadquery-ocp-novtk"),
            "platform": platform.machine(),
        },
        "inputs": {
            "contract_sha256": sha256(args.contract),
            "geometry_report_sha256": sha256(args.geometry_report),
            "parent_head_sha256": sha256(args.head_stl),
        },
        "artifacts": artifacts,
        "checks": {
            "all_created_shapes_valid_and_closed": all(item["created"]["valid"] and item["created"]["all_solids_closed"] for item in artifacts),
            "all_step_roundtrips_valid_and_closed": all(item["reopened_step"]["valid"] and item["reopened_step"]["all_solids_closed"] for item in artifacts),
            "rocker_carrier_is_one_solid": carrier_bounds["solid_count"] == 1,
            "rocker_count_is_four": artifact_by_id["four-rocker-envelopes"]["created"]["solid_count"] == 4,
            "rocker_shaft_count_is_two": artifact_by_id["two-rocker-shafts"]["created"]["solid_count"] == 2,
            "rocker_window_size_xy_mm": contract["rocker_carrier"]["rocker_window_size_xy_mm"],
            "rocker_arm_section_xz_mm": contract["rocker_carrier"]["rocker_arm_section_xz_mm"],
            "rocker_pivot_collinear_envelope_factor_consistent": math.isclose(
                contract["rocker_pivot_reaction_screen"]["collinear_upper_envelope_factor"],
                1.0 + contract["rocker_pivot_reaction_screen"]["cam_to_valve_force_ratio"],
                rel_tol=0.0,
                abs_tol=1.0e-12,
            ),
            "rocker_to_shaft_radial_clearance_mm": 0.05,
            "rocker_to_carrier_window_clearances_mm": {
                key: round(value, 6) for key, value in window_clearances.items()
            },
            "rocker_to_carrier_window_minimum_clearance_mm": round(
                minimum_window_clearance, 6
            ),
            "rocker_to_carrier_window_minimum_clearance_at_least_0_5_mm": (
                minimum_window_clearance >= 0.5
            ),
            "rocker_carrier_interference_volume_mm3": round(sum(solid.volume for solid in (carrier & rockers).solids()), 9),
            "rocker_shaft_interference_volume_mm3": round(sum(solid.volume for solid in (shafts & rockers).solids()), 9),
            "carrier_mount_strategy": contract["rocker_carrier"]["mount_strategy"],
            "carrier_mount_centres_match_f36_stud_pattern": True,
            "carrier_mount_interface_z_mm": contract["rocker_carrier"]["mount_interface_z_mm"],
            "carrier_mount_final_clearance_diameter_mm": contract["rocker_carrier"]["mount_final_clearance_diameter_mm"],
            "extended_head_stud_and_clamp_stack_released": contract["rocker_carrier"]["extended_head_stud_and_clamp_stack_released"],
            "shaft_to_carrier_fit_candidate": contract["rocker_carrier"]["shaft_to_carrier_fit_candidate"],
            "shaft_to_carrier_fit_numeric_limits_confirmed": contract["rocker_carrier"]["shaft_to_carrier_fit_numeric_limits_confirmed"],
            "oil_core_is_one_connected_solid": oil_metrics["solid_count"] == 1,
            "oil_passages_declared_straight_drillable_or_open_ended": contract["oil_system"]["all_passages_straight_drillable_or_open_ended"],
            "oil_passage_ends_verified_against_head_skin": False,
            "minimum_machining_allowance_positive": min(allowance.values()) > 0.0,
            "machining_allowance_valve_axis_tilt_y_deg": {
                family: float(geometry["geometry"]["architecture"][family]["tilt_y_deg"])
                for family in ("intake", "exhaust")
            },
            "seat_guide_allowances_follow_finish_cutter_valve_axes": True,
            "carrier_within_parent_xy_bounds": carrier_bounds["bounds_min_mm"][0] >= -61.125
            and carrier_bounds["bounds_max_mm"][0] <= 64.125
            and carrier_bounds["bounds_min_mm"][1] >= -89.625
            and carrier_bounds["bounds_max_mm"][1] <= 116.625,
            "functional_interfaces_are_analytic_occt": True,
            "whole_head_single_brep": False,
        },
        "thread_and_finish_map": contract["thread_and_finish_map"],
        "release_gates": contract["release_gates"],
    }
    report_path = args.output / "f37-cad-report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "report": str(report_path), "artifacts": len(artifacts)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
