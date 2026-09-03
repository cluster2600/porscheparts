#!/usr/bin/env python3
"""Construit le porte-axes F38 arrondi et son assemblage 4 soupapes.

F38 reste une définition analytique conditionnelle dérivée des interfaces F36/F37.
Les composants STEP ne constituent ni une définition fournisseur ni une autorisation
de fabrication.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
from typing import Any

from build_f37_manufacturing_definition import (
    centred_box,
    export_shape,
    load,
    sha256,
    valve_axis_cylinder,
    vertical_cylinder,
    x_cylinder,
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def verify(path: Path, expected: str, label: str) -> None:
    require(path.is_file(), f"missing_{label}:{path}")
    require(sha256(path) == expected, f"{label}_sha256_mismatch")


def rounded_box(x: float, y: float, z: float, cx: float, cy: float, cz: float, radius: float) -> Any:
    from build123d import fillet

    solid = centred_box(x, y, z, cx, cy, cz)
    return fillet(solid.edges(), radius)


def build_carrier(spec: dict[str, Any], geometry: dict[str, Any]) -> Any:
    from build123d import fillet

    carrier = spec["carrier"]
    rail_x, rail_y, rail_z = map(float, carrier["rail_size_xyz_mm"])
    rail_centre_z = float(carrier["rail_centre_z_mm"])
    rail_bottom = rail_centre_z - rail_z / 2.0
    rail_top = rail_centre_z + rail_z / 2.0
    body = None
    for axis_y in (carrier["intake_axis_yz_mm"][0], carrier["exhaust_axis_yz_mm"][0]):
        rail = centred_box(rail_x, rail_y, rail_z, 0.0, float(axis_y), rail_centre_z)
        body = rail if body is None else body + rail

    studs = [tuple(map(float, item)) for item in geometry["geometry"]["packaging_checks"]["stud_centres_local_mm"]]
    x_columns = [sum(x for x, _ in studs if math.copysign(1.0, x) == sign) / 2.0 for sign in (-1.0, 1.0)]
    bridge_y = max(y for _, y in studs) - min(y for _, y in studs) + float(carrier["mount_transition_outer_diameter_mm"])
    bridge_height = float(carrier["mount_bridge_height_z_mm"])
    for x in x_columns:
        bridge = centred_box(
            float(carrier["mount_bridge_width_x_mm"]),
            bridge_y,
            bridge_height,
            x,
            0.0,
            rail_bottom + bridge_height / 2.0,
        )
        body = body + bridge
    require(body.is_valid and body.is_manifold, "invalid_f38_carrier_after_bridges")

    interface_z = float(carrier["mount_interface_z_mm"])
    foot_height = rail_bottom - interface_z
    foot_radius = float(carrier["mount_boss_outer_diameter_mm"]) / 2.0
    for x, y in studs:
        # Le bossage pénètre le pont sur 8 mm. La surface cylindrique fournit
        # un raccord continu sans l'arête rentrante du pied F37.
        foot = vertical_cylinder(foot_radius, foot_height + 8.0, x, y, interface_z)
        body = body + foot
    require(body.is_valid and body.is_manifold, "invalid_f38_carrier_after_bosses")

    axis_z = float(carrier["intake_axis_yz_mm"][1])
    window_bottom = axis_z - 11.5
    window_top = rail_top + 1.0
    window_x, window_y = map(float, carrier["rocker_window_size_xy_mm"])
    for axis_y in (carrier["intake_axis_yz_mm"][0], carrier["exhaust_axis_yz_mm"][0]):
        for x in (-18.0, 18.0):
            cutter = centred_box(
                window_x,
                window_y,
                window_top - window_bottom,
                x,
                float(axis_y),
                (window_bottom + window_top) / 2.0,
            )
            body = body - cutter
    require(body.is_valid and body.is_manifold, "invalid_f38_carrier_after_windows")

    for axis_y in (carrier["intake_axis_yz_mm"][0], carrier["exhaust_axis_yz_mm"][0]):
        body = body - x_cylinder(float(carrier["shaft_as_printed_bore_diameter_mm"]) / 2.0, 114.0, -57.0, float(axis_y), axis_z)
    require(body.is_valid and body.is_manifold, "invalid_f38_carrier_after_shafts")
    for x, y in studs:
        body = body - vertical_cylinder(
            float(carrier["mount_as_printed_pilot_mm"]) / 2.0,
            rail_top - interface_z + 4.0,
            x,
            y,
            interface_z - 2.0,
        )
    require(body.is_valid and body.is_manifold, "invalid_f38_carrier")
    return body


def build_rockers(spec: dict[str, Any]) -> Any:
    from build123d import Compound, fillet

    carrier = spec["carrier"]
    axis_z = float(carrier["intake_axis_yz_mm"][1])
    arm_x, arm_z = map(float, carrier["rocker_arm_section_xz_mm"])
    shapes = []
    for axis_y in (carrier["intake_axis_yz_mm"][0], carrier["exhaust_axis_yz_mm"][0]):
        for x in (-18.0, 18.0):
            contact_y = math.copysign(48.0, float(axis_y))
            arm = centred_box(
                arm_x,
                abs(contact_y - float(axis_y)) + 8.0,
                arm_z,
                x,
                0.5 * (float(axis_y) + contact_y),
                axis_z,
            )
            boss = x_cylinder(10.5, arm_x, x - arm_x / 2.0, float(axis_y), axis_z)
            arm = arm + boss
            arm = arm - x_cylinder(
                float(carrier["shaft_final_diameter_mm"]) / 2.0 + 0.05,
                arm_x + 2.0,
                x - arm_x / 2.0 - 1.0,
                float(axis_y),
                axis_z,
            )
            arm = arm - vertical_cylinder(3.5, 22.0, x, contact_y, axis_z - 12.0)
            shapes.append(arm)
    return Compound(shapes)


def build_shafts(spec: dict[str, Any]) -> Any:
    from build123d import Compound

    carrier = spec["carrier"]
    return Compound([
        x_cylinder(float(carrier["shaft_final_diameter_mm"]) / 2.0, 110.0, -55.0, float(axis_y), float(carrier["intake_axis_yz_mm"][1]))
        for axis_y in (carrier["intake_axis_yz_mm"][0], carrier["exhaust_axis_yz_mm"][0])
    ])


def build_valves(spec: dict[str, Any], family: str) -> Any:
    from build123d import Compound

    data = spec["valvetrain"][family]
    shapes = []
    for x, y, z in data["centres_mm"]:
        head = valve_axis_cylinder(float(data["head_diameter_mm"]) / 2.0, 3.0, x, y, z, float(data["tilt_y_deg"]))
        stem = valve_axis_cylinder(float(data["stem_diameter_mm"]) / 2.0, float(data["valve_length_mm"]), x, y, z + 2.0, float(data["tilt_y_deg"]))
        shapes.append(head + stem)
    return Compound(shapes)


def build_guides(spec: dict[str, Any]) -> Any:
    from build123d import Compound

    guide = spec["valvetrain"]["guide"]
    shapes = []
    for family in ("intake", "exhaust"):
        data = spec["valvetrain"][family]
        for x, y, z in data["centres_mm"]:
            outer = valve_axis_cylinder(float(guide["outer_diameter_mm"]) / 2.0, float(guide["length_mm"]), x, y, z + 20.0, float(data["tilt_y_deg"]))
            inner = valve_axis_cylinder(float(guide["inner_diameter_mm"]) / 2.0, float(guide["length_mm"]) + 2.0, x, y, z + 19.0, float(data["tilt_y_deg"]))
            shapes.append(outer - inner)
    return Compound(shapes)


def build_seats(spec: dict[str, Any]) -> Any:
    from build123d import Compound

    shapes = []
    for family in ("intake", "exhaust"):
        data = spec["valvetrain"][family]
        for x, y, z in data["centres_mm"]:
            outer = valve_axis_cylinder(float(data["seat_outer_diameter_mm"]) / 2.0, 5.0, x, y, z - 1.0, float(data["tilt_y_deg"]))
            inner = valve_axis_cylinder(float(data["seat_inner_diameter_mm"]) / 2.0, 7.0, x, y, z - 2.0, float(data["tilt_y_deg"]))
            shapes.append(outer - inner)
    return Compound(shapes)


def helical_spring(mean_diameter: float, wire: float, turns: float, height: float, x: float, y: float, z: float, tilt: float) -> Any:
    from build123d import Circle, Helix, Plane, Pos, Rot, sweep

    path = Helix(pitch=height / turns, height=height, radius=mean_diameter / 2.0)
    profile = Plane(origin=path @ 0.0, z_dir=path % 0.0) * Circle(wire / 2.0)
    coil = sweep(profile, path=path, is_frenet=True)
    return Pos(x, y, z) * Rot(-tilt, 0.0, 0.0) * coil


def build_springs(spec: dict[str, Any]) -> Any:
    from build123d import Compound

    spring = spec["valvetrain"]["spring"]
    shapes = []
    for family in ("intake", "exhaust"):
        data = spec["valvetrain"][family]
        for x, y, z in data["centres_mm"]:
            base_z = z + 50.0
            shapes.append(helical_spring(float(spring["outer_mean_diameter_mm"]), float(spring["outer_wire_diameter_mm"]), float(spring["outer_active_turns"]), float(spring["installed_length_mm"]), x, y, base_z, float(data["tilt_y_deg"])))
            shapes.append(helical_spring(float(spring["inner_mean_diameter_mm"]), float(spring["inner_wire_diameter_mm"]), float(spring["inner_active_turns"]), float(spring["installed_length_mm"]), x, y, base_z, float(data["tilt_y_deg"])))
    return Compound(shapes)


def build_retainers(spec: dict[str, Any], upper: bool) -> Any:
    from build123d import Compound

    retainer = spec["valvetrain"]["retainer"]
    spring = spec["valvetrain"]["spring"]
    outer = float(retainer["upper_outer_diameter_mm"] if upper else retainer["lower_outer_diameter_mm"])
    thickness = float(retainer["thickness_mm"])
    shapes = []
    for family in ("intake", "exhaust"):
        data = spec["valvetrain"][family]
        for x, y, z in data["centres_mm"]:
            position_z = z + 50.0 + (float(spring["installed_length_mm"]) if upper else 0.0)
            ring = valve_axis_cylinder(outer / 2.0, thickness, x, y, position_z, float(data["tilt_y_deg"]))
            hole = valve_axis_cylinder(float(retainer["central_clearance_mm"]) / 2.0, thickness + 2.0, x, y, position_z - 1.0, float(data["tilt_y_deg"]))
            shapes.append(ring - hole)
    return Compound(shapes)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--f37-contract", type=Path, required=True)
    parser.add_argument("--geometry-report", type=Path, required=True)
    parser.add_argument("--f37-cad-report", type=Path, required=True)
    parser.add_argument("--f37-carrier-step", type=Path, required=True)
    parser.add_argument("--f37-calculix-report", type=Path, required=True)
    parser.add_argument("--f37-kinematic-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bounded-finalize", action="store_true")
    args = parser.parse_args()

    spec = load(args.spec)
    require(spec["phase"] == "F38", "spec_phase_must_be_f38")
    sources = {
        "f37_contract": args.f37_contract,
        "f36_geometry_report": args.geometry_report,
        "f37_cad_report": args.f37_cad_report,
        "f37_carrier_step": args.f37_carrier_step,
        "f37_calculix_report": args.f37_calculix_report,
        "f37_kinematic_report": args.f37_kinematic_report,
    }
    for key, path in sources.items():
        verify(path, spec["parent_evidence"][key]["sha256"], key)
    geometry = load(args.geometry_report)
    require(geometry["phase"] == "F36", "geometry_phase_must_be_f36")
    args.output.mkdir(parents=True, exist_ok=True)

    carrier = build_carrier(spec, geometry)
    rockers = build_rockers(spec)
    shafts = build_shafts(spec)
    intake_valves = build_valves(spec, "intake")
    exhaust_valves = build_valves(spec, "exhaust")
    guides = build_guides(spec)
    seats = build_seats(spec)
    springs = build_springs(spec)
    lower_retainers = build_retainers(spec, upper=False)
    upper_retainers = build_retainers(spec, upper=True)
    from build123d import Compound
    assembly = Compound([
        carrier, rockers, shafts, intake_valves, exhaust_valves, guides,
        seats, springs, lower_retainers, upper_retainers,
    ])

    definitions = [
        ("rocker-carrier-f38-rounded-reinforced", carrier, 1),
        ("four-rockers-f38", rockers, 4),
        ("two-rocker-shafts-f38", shafts, 2),
        ("two-intake-valves-f38", intake_valves, 2),
        ("two-exhaust-valves-f38", exhaust_valves, 2),
        ("four-valve-guides-f38", guides, 4),
        ("four-valve-seats-f38", seats, 4),
        ("four-lower-spring-cups-f38", lower_retainers, 4),
        ("four-upper-spring-retainers-f38", upper_retainers, 4),
    ]
    artifacts = [export_shape(name, shape, args.output, expected_solids=count) for name, shape, count in definitions]
    if args.bounded_finalize:
        # Les ressorts hélicoïdaux ont un STL très dense. Leur STEP et leur STL
        # déjà exportés sont liés, mais le round-trip OCCT est laissé ouvert.
        spring_step = args.output / "eight-valve-springs-f38.step"
        spring_stl = args.output / "eight-valve-springs-f38.stl"
        require(spring_step.is_file() and spring_stl.is_file(), "bounded_spring_artifacts_missing")
        spring_metrics = {
            "valid": bool(springs.is_valid),
            "manifold": bool(springs.is_manifold),
            "solid_count": len(springs.solids()),
            "all_solids_closed": all(solid.is_valid and solid.is_manifold for solid in springs.solids()),
            "volume_mm3": round(sum(solid.volume for solid in springs.solids()), 6),
        }
        artifacts.append({
            "id": "eight-valve-springs-f38",
            "created": spring_metrics,
            "reopened_step": None,
            "step_roundtrip_relative_volume_drift": None,
            "step": {"path": spring_step.name, "bytes": spring_step.stat().st_size, "sha256": sha256(spring_step)},
            "stl": {"path": spring_stl.name, "bytes": spring_stl.stat().st_size, "sha256": sha256(spring_stl)},
            "verification_limit": "step_roundtrip_interrupted_by_bounded_runtime",
        })
        from build123d import export_step
        assembly_step = args.output / "f38-four-valve-rocker-assembly.step"
        export_step(assembly, assembly_step)
        from build_f37_manufacturing_definition import canonicalize_step_header
        canonicalize_step_header(assembly_step)
        assembly_metrics = {
            "valid": bool(assembly.is_valid),
            "manifold": bool(assembly.is_manifold),
            "solid_count": len(assembly.solids()),
            "all_solids_closed": all(solid.is_valid and solid.is_manifold for solid in assembly.solids()),
            "volume_mm3": round(sum(solid.volume for solid in assembly.solids()), 6),
        }
        artifacts.append({
            "id": "f38-four-valve-rocker-assembly",
            "created": assembly_metrics,
            "reopened_step": None,
            "step_roundtrip_relative_volume_drift": None,
            "step": {"path": assembly_step.name, "bytes": assembly_step.stat().st_size, "sha256": sha256(assembly_step)},
            "stl": None,
            "verification_limit": "compound_step_exported_without_roundtrip_or_assembly_stl_in_bounded_runtime",
        })
    else:
        artifacts.extend([
            export_shape("eight-valve-springs-f38", springs, args.output, expected_solids=8),
            export_shape("f38-four-valve-rocker-assembly", assembly, args.output, expected_solids=35),
        ])
    by_id = {item["id"]: item for item in artifacts}
    parent_report = load(args.f37_calculix_report)
    report = {
        "schema_version": "1.0.0",
        "phase": "F38",
        "status": "rounded_reinforced_carrier_and_four_valve_step_assembly_bounded_export_release_blocked" if args.bounded_finalize else "rounded_reinforced_carrier_and_four_valve_step_assembly_complete_release_blocked",
        "classification": spec["classification"],
        "inputs": {key + "_sha256": sha256(path) for key, path in sources.items()} | {"spec_sha256": sha256(args.spec)},
        "toolchain": {"python": platform.python_version(), "geometry_kernel": "build123d_OCCT"},
        "design_delta_from_f37": {
            "parent_finest_raw_maximum_mpa": parent_report["cases"][-1]["von_mises_mpa"]["maximum"],
            "rail_size_xyz_mm_f37": [110.0, 34.0, 40.0],
            "rail_size_xyz_mm_f38": spec["carrier"]["rail_size_xyz_mm"],
            "mount_boss_outer_diameter_mm_f37": 20.0,
            "mount_boss_outer_diameter_mm_f38": spec["carrier"]["mount_boss_outer_diameter_mm"],
            "mount_bridge_width_x_mm_f37": 18.0,
            "mount_bridge_width_x_mm_f38": spec["carrier"]["mount_bridge_width_x_mm"],
            "explicit_rounded_transitions": True,
        },
        "artifacts": artifacts,
        "checks": {
            "all_shapes_valid_closed": all(item["created"]["valid"] and item["created"]["all_solids_closed"] for item in artifacts),
            "all_step_roundtrips_valid_closed": all(isinstance(item["reopened_step"], dict) and item["reopened_step"]["valid"] and item["reopened_step"]["all_solids_closed"] for item in artifacts),
            "carrier_single_solid": by_id["rocker-carrier-f38-rounded-reinforced"]["created"]["solid_count"] == 1,
            "four_rockers": by_id["four-rockers-f38"]["created"]["solid_count"] == 4,
            "four_valves": by_id["two-intake-valves-f38"]["created"]["solid_count"] + by_id["two-exhaust-valves-f38"]["created"]["solid_count"] == 4,
            "four_guides": by_id["four-valve-guides-f38"]["created"]["solid_count"] == 4,
            "four_seats": by_id["four-valve-seats-f38"]["created"]["solid_count"] == 4,
            "eight_springs": by_id["eight-valve-springs-f38"]["created"]["solid_count"] == 8,
            "four_lower_cups": by_id["four-lower-spring-cups-f38"]["created"]["solid_count"] == 4,
            "four_upper_retainers": by_id["four-upper-spring-retainers-f38"]["created"]["solid_count"] == 4,
            "assembly_step_delivered": by_id["f38-four-valve-rocker-assembly"]["step"] is not None,
            "assembly_step_roundtrip_verified": by_id["f38-four-valve-rocker-assembly"]["reopened_step"] is not None,
            "spring_step_roundtrip_verified": by_id["eight-valve-springs-f38"]["reopened_step"] is not None,
            "assembly_is_multi_body_not_whole_head": True,
        },
        "release_gates": spec["release_gates"],
    }
    (args.output / "f38-rocker-carrier-cad-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "artifacts": len(artifacts)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
