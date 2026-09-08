#!/usr/bin/env python3
"""Génère la CAO conceptuelle de la cellule CFRP 964/993 et de son packaging.

Le modèle matérialise une baignoire automobile, ses ouvertures et les volumes
fonctionnels C2/C4 révélés par les catalogues PET Porsche. Toutes les dimensions
autres que les enveloppes publiques restent des hypothèses de packaging : aucun
point de caisse, perçage ou stratifié n'est fabricable depuis ces sorties.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
TWIN_ROOT = HERE.parent
ROOT = TWIN_ROOT.parents[1]
DEFAULT_CONFIG = TWIN_ROOT / "design-space.json"
DEFAULT_TOPOLOGY = TWIN_ROOT / "derived" / "selected-topology.json"
DEFAULT_OUTPUT = TWIN_ROOT / "derived"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: objet JSON attendu")
    return value


def beam_between(start: tuple[float, float, float], end: tuple[float, float, float], size_mm: float):
    from build123d import Align, Axis, Box, Vector

    dx, dy, dz = (end[index] - start[index] for index in range(3))
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    if length <= 0.0:
        raise ValueError("poutre de longueur nulle")
    yaw = math.degrees(math.atan2(dy, dx))
    pitch = math.degrees(math.atan2(dz, math.hypot(dx, dy)))
    beam = Box(length, size_mm, size_mm, align=(Align.MIN, Align.CENTER, Align.CENTER))
    beam = beam.rotate(Axis.Y, -pitch).rotate(Axis.Z, yaw)
    return beam.translate(Vector(*start))


def cylinder_x(center: tuple[float, float, float], length: float, diameter: float):
    from build123d import Align, Axis, Cylinder, Pos

    shape = Cylinder(diameter / 2.0, length, align=(Align.CENTER, Align.CENTER, Align.CENTER)).rotate(Axis.Y, 90.0)
    return Pos(*center) * shape


def cylinder_y(center: tuple[float, float, float], length: float, diameter: float):
    from build123d import Align, Axis, Cylinder, Pos

    shape = Cylinder(diameter / 2.0, length, align=(Align.CENTER, Align.CENTER, Align.CENTER)).rotate(Axis.X, 90.0)
    return Pos(*center) * shape


def build_cell(config: dict[str, Any], topology: dict[str, Any]):
    """Construit la baignoire commune et réserve les passages fonctionnels."""

    from build123d import Align, Box, Compound, Pos

    geometry = config["screening_geometry_mm"]
    package = config["vehicle_packaging_mm"]
    common = package["common_cell"]
    x_front = float(geometry["front_axle_x"])
    x_rear = float(geometry["rear_axle_x"])
    x_dash = float(common["front_bulkhead_x"])
    x_bulkhead = float(common["rear_bulkhead_x"])
    half_width = float(geometry["cell_half_width"])
    floor_z = float(geometry["floor_z"])
    belt_z = float(geometry["belt_z"])
    roof_z = float(geometry["roof_z"])
    tub_start = float(common["tub_start_x"])
    tub_end = float(common["tub_end_x"])
    tub_length = tub_end - tub_start
    width = 2.0 * half_width
    sill_start = float(common["sill_start_x"])
    sill_end = float(common["sill_end_x"])
    sill_length = sill_end - sill_start
    sill_width = float(common["sill_width"])
    sill_height = float(common["sill_height"])
    tunnel_start = float(common["tunnel_start_x"])
    tunnel_end = float(common["tunnel_end_x"])
    tunnel_length = tunnel_end - tunnel_start
    tunnel_width = float(common["tunnel_outer_width"])
    tunnel_height = float(common["tunnel_outer_height"])
    tunnel_wall = 26.0

    solids: list[Any] = []
    groups: dict[str, int] = {}

    def add(group: str, shape: Any) -> None:
        solids.append(shape)
        groups[group] = groups.get(group, 0) + 1

    # Plancher structurel, avec zones occupants séparées par le tunnel.
    add("floor", Pos((tub_start + tub_end) / 2.0, 0.0, floor_z) * Box(tub_length, width, 34.0, align=Align.CENTER))
    for sign in (-1.0, 1.0):
        add("occupant_floor", Pos(1100.0, sign * 365.0, floor_z + 28.0) * Box(1260.0, 430.0, 28.0, align=Align.CENTER))
        add("footwell", Pos(570.0, sign * 365.0, floor_z + 62.0) * Box(330.0, 430.0, 92.0, align=Align.CENTER))
        add("rear_seat_well", Pos(1580.0, sign * 350.0, float(common["rear_shelf_z"]) - 30.0) * Box(430.0, 420.0, 46.0, align=Align.CENTER))

    # Tunnel structurel creux : deux voiles, une peau supérieure démontable et
    # un nez avant. Le volume intérieur reste disponible aux packages C2/C4.
    tunnel_center_x = (tunnel_start + tunnel_end) / 2.0
    for sign in (-1.0, 1.0):
        add("central_tunnel", Pos(tunnel_center_x, sign * (tunnel_width - tunnel_wall) / 2.0, floor_z + tunnel_height / 2.0) * Box(tunnel_length, tunnel_wall, tunnel_height, align=Align.CENTER))
    add("central_tunnel", Pos(tunnel_center_x, 0.0, floor_z + tunnel_height) * Box(tunnel_length, tunnel_width, float(common["service_cover_thickness"]), align=Align.CENTER))
    add("central_tunnel", Pos(tunnel_start, 0.0, floor_z + tunnel_height / 2.0) * Box(38.0, tunnel_width, tunnel_height, align=Align.CENTER))

    # Caissons latéraux profonds et véritables ouvertures de portes.
    for sign in (-1.0, 1.0):
        sill_y = sign * (half_width - sill_width / 2.0)
        add("sill", Pos((sill_start + sill_end) / 2.0, sill_y, floor_z + sill_height / 2.0) * Box(sill_length, sill_width, sill_height, align=Align.CENTER))
        add("door_upper_rail", beam_between((560.0, sign * 590.0, belt_z), (1660.0, sign * 590.0, belt_z + 20.0), 72.0))
        add("a_pillar", beam_between((510.0, sign * 590.0, belt_z), (735.0, sign * 505.0, roof_z), 70.0))
        add("rear_pillar", beam_between((1660.0, sign * 590.0, belt_z + 20.0), (1540.0, sign * 505.0, roof_z), 76.0))
        add("roof_rail", beam_between((735.0, sign * 505.0, roof_z), (1540.0, sign * 505.0, roof_z), 72.0))
        add("rear_wheelhouse", Pos(1830.0, sign * 535.0, floor_z + 300.0) * Box(360.0, 190.0, 430.0, align=Align.CENTER))

    add("roof_header", beam_between((735.0, -505.0, roof_z), (735.0, 505.0, roof_z), 72.0))
    add("roof_header", beam_between((1540.0, -505.0, roof_z), (1540.0, 505.0, roof_z), 76.0))
    add("roof_bow", beam_between((1130.0, -505.0, roof_z + 10.0), (1130.0, 505.0, roof_z + 10.0), 58.0))

    # Cloisons interrompues au centre pour le tube C4 et le nez de boîte.
    bulkhead_side_width = (width - tunnel_width - 120.0) / 2.0
    bulkhead_y = (tunnel_width + 60.0 + bulkhead_side_width) / 2.0
    for sign in (-1.0, 1.0):
        add("front_bulkhead", Pos(x_dash, sign * bulkhead_y, floor_z + 310.0) * Box(38.0, bulkhead_side_width, 570.0, align=Align.CENTER))
        add("rear_bulkhead", Pos(x_bulkhead, sign * bulkhead_y, floor_z + 350.0) * Box(44.0, bulkhead_side_width, 650.0, align=Align.CENTER))
    add("front_bulkhead", Pos(x_dash, 0.0, belt_z + 120.0) * Box(42.0, width - 170.0, 210.0, align=Align.CENTER))
    add("rear_bulkhead", Pos(x_bulkhead, 0.0, belt_z + 135.0) * Box(46.0, width - 140.0, 240.0, align=Align.CENTER))
    add("rear_shelf", Pos(1660.0, 0.0, float(common["rear_shelf_z"])) * Box(360.0, width - 260.0, 42.0, align=Align.CENTER))

    # Zones sièges, pédalier, levage et conduits qui manquaient au concept initial.
    for sign in (-1.0, 1.0):
        for x_mm in (880.0, 1320.0):
            add("seat_support", Pos(x_mm, sign * 365.0, floor_z + 62.0) * Box(110.0, 410.0, 70.0, align=Align.CENTER))
        add("pedal_box", Pos(485.0, sign * 365.0, floor_z + 300.0) * Box(100.0, 300.0, 340.0, align=Align.CENTER))
        add("jacking_point", Pos(1080.0, sign * 620.0, floor_z - 18.0) * Box(150.0, 100.0, 86.0, align=Align.CENTER))

    services = package["protected_service_channels"]
    for key in ("brake_fuel_left_center_y", "wiring_right_center_y", "parking_brake_left_center_y", "parking_brake_right_center_y"):
        add("service_duct", cylinder_x((1200.0, float(services[key]), floor_z + 72.0), 1320.0, float(services["service_tube_diameter"])))

    # Bossages de frontière seulement; ce ne sont pas des points de suspension.
    adapter_half_width = half_width - 50.0
    for x_mm in (x_front, x_rear):
        for sign in (-1.0, 1.0):
            add("interface_boss", Pos(x_mm, sign * adapter_half_width, floor_z) * Box(120.0, 100.0, 80.0, align=Align.CENTER))

    return Compound(children=solids, label="964 993 CFRP VEHICLE CELL F1 PACKAGING CONCEPT"), {
        "solid_count": len(solids),
        "functional_groups": groups,
        "door_apertures_modelled": True,
        "central_tunnel_is_hollow": True,
        "seat_and_pedal_zones_modelled": True,
        "wheelhouse_proxies_modelled": True,
        "protected_service_ducts_modelled": True,
        "interface_boss_count": groups["interface_boss"],
        "common_adapter_half_width_mm": adapter_half_width,
        "nominal_envelope_mm": [x_rear - x_front, width, roof_z - floor_z],
        "primary_structure_material": "CFRP",
        "local_metallic_hardware_modelled": False,
        "geometry_status": package["status"],
    }


def build_driveline_package(config: dict[str, Any], platform: str, drive: str):
    """Construit des volumes de garde, pas des pièces Porsche réutilisables."""

    from build123d import Align, Box, Compound, Pos

    package = config["vehicle_packaging_mm"]
    solids: list[Any] = []
    feature_ids: list[str] = []

    if drive == "C2":
        data = package["c2_package"]
        start = float(data["external_shift_rod_start_x"])
        end = float(data["external_shift_rod_end_x"])
        solids.append(cylinder_x(((start + end) / 2.0, float(data["external_shift_rod_center_y"]), float(data["external_shift_rod_center_z"])), end - start, float(data["external_shift_rod_diameter"])))
        solids.append(Pos(*[float(v) for v in data["shifter_tower_center_xyz"]]) * Box(*[float(v) for v in data["shifter_tower_envelope_xyz"]], align=Align.CENTER))
        feature_ids.extend(["external_shift_rod_clearance", "shifter_tower_clearance"])
    elif drive == "C4":
        data = package["c4_package"]
        start = float(data["central_tube_start_x"])
        end = float(data["central_tube_end_x"])
        center_x = (start + end) / 2.0
        center_z = float(data["central_tube_center_z"])
        solids.append(cylinder_x((center_x, 0.0, center_z), end - start, float(data["central_tube_outer_diameter"])))
        solids.append(cylinder_x((center_x, 0.0, center_z), end - start, float(data["propeller_shaft_clearance_diameter"])))
        solids.append(cylinder_x((center_x, float(data["shift_guide_center_y"]), center_z + 82.0), end - start - 260.0, float(data["shift_guide_diameter"])))
        solids.append(Pos(*[float(v) for v in data["front_final_drive_center_xyz"]]) * Box(*[float(v) for v in data["front_final_drive_envelope_xyz"]], align=Align.CENTER))
        solids.append(cylinder_y((0.0, 0.0, center_z), float(data["front_halfshaft_total_span"]), float(data["front_halfshaft_clearance_diameter"])))
        feature_ids.extend(["central_tube_clearance", "propeller_shaft_clearance", "C4_shift_guide_clearance", "front_final_drive_clearance", "front_halfshaft_clearance"])
    else:
        raise ValueError(f"transmission inconnue: {drive}")

    return Compound(children=solids, label=f"{platform} {drive} DRIVELINE CLEARANCE ENVELOPES"), {
        "platform": platform,
        "drive": drive,
        "solid_count": len(solids),
        "feature_ids": feature_ids,
        "geometry_status": "hypothesis_envelope_not_measured",
        "rotating_parts_are_clearance_only": True,
        "porsche_part_geometry_used": False,
    }


def build_platform_modules(config: dict[str, Any], platform_id: str, dimensions: dict[str, Any]):
    """Crée des pods CFRP d'enveloppe, sans prétendre placer les articulations."""

    from build123d import Align, Box, Compound, Pos

    geometry = config["screening_geometry_mm"]
    floor_z = float(geometry["floor_z"])
    adapter_half_width = float(geometry["cell_half_width"]) - 50.0
    stations = (("FRONT", float(geometry["front_axle_x"]), float(dimensions["front_track"]) / 2.0), ("REAR", float(geometry["rear_axle_x"]), float(dimensions["rear_track"]) / 2.0))
    solids = []
    pod_ids = []
    for station, x_mm, envelope_half_track in stations:
        for side, sign in (("L", 1.0), ("R", -1.0)):
            inner = (x_mm, sign * adapter_half_width, floor_z)
            outer = (x_mm, sign * envelope_half_track, floor_z)
            solids.append(beam_between(inner, outer, 64.0))
            solids.append(Pos(*outer) * Box(110.0, 90.0, 74.0, align=Align.CENTER))
            brace_start = (x_mm + (75.0 if station == "FRONT" else -75.0), sign * adapter_half_width, floor_z + 95.0)
            solids.append(beam_between(brace_start, outer, 42.0))
            pod_ids.append(f"{platform_id}_{station}_{side}")
    return Compound(children=solids, label=f"{platform_id} CFRP ENVELOPE PODS - NO PICKUP HOLES"), {
        "platform_id": platform_id,
        "solid_count": len(solids),
        "pod_ids": pod_ids,
        "front_track_envelope_mm": float(dimensions["front_track"]),
        "rear_track_envelope_mm": float(dimensions["rear_track"]),
        "wheelbase_envelope_mm": float(dimensions["wheelbase"]),
        "suspension_pickup_coordinates_modelled": False,
        "fastener_holes_or_inserts_modelled": False,
        "material_intent": "CFRP primary structure; local metallic hardware TBD",
    }


def build_tooling(config: dict[str, Any], cell):
    from build123d import Align, Box, Compound, Pos

    geometry = config["screening_geometry_mm"]
    common = config["vehicle_packaging_mm"]["common_cell"]
    x_front = float(common["tub_start_x"])
    x_rear = float(common["tub_end_x"])
    x_dash = float(common["front_bulkhead_x"])
    x_bulkhead = float(common["rear_bulkhead_x"])
    half_width = float(geometry["cell_half_width"])
    floor_z = float(geometry["floor_z"])
    belt_z = float(geometry["belt_z"])
    roof_z = float(geometry["roof_z"])
    length = x_rear - x_front
    width = 2.0 * half_width
    flange = 180.0
    backing = 90.0
    tunnel_width = float(common["tunnel_outer_width"])
    tunnel_height = float(common["tunnel_outer_height"])

    blanks = [
        ("M01_FLOOR_LOWER", Pos((x_front + x_rear) / 2.0, 0.0, floor_z - backing / 2.0) * Box(length + 2 * flange, width + 2 * flange, backing, align=Align.CENTER)),
        ("M02_LEFT_SILL_SIDE", Pos((x_front + x_rear) / 2.0, half_width + backing / 2.0, (floor_z + belt_z) / 2.0) * Box(length + 2 * flange, backing, belt_z - floor_z + 2 * flange, align=Align.CENTER)),
        ("M03_RIGHT_SILL_SIDE", Pos((x_front + x_rear) / 2.0, -half_width - backing / 2.0, (floor_z + belt_z) / 2.0) * Box(length + 2 * flange, backing, belt_z - floor_z + 2 * flange, align=Align.CENTER)),
        ("M04_FRONT_BULKHEAD", Pos(x_dash - backing / 2.0, 0.0, (floor_z + belt_z) / 2.0) * Box(backing, width + 2 * flange, belt_z - floor_z + 2 * flange, align=Align.CENTER)),
        ("M05_REAR_BULKHEAD", Pos(x_bulkhead + backing / 2.0, 0.0, (floor_z + belt_z) / 2.0) * Box(backing, width + 2 * flange, belt_z - floor_z + 2 * flange, align=Align.CENTER)),
        ("M06_LEFT_ROOF_FRAME_JIG", Pos((x_dash + x_bulkhead) / 2.0, half_width * 0.78, roof_z + 70.0) * Box(x_bulkhead - x_dash + 2 * flange, 120.0, 140.0, align=Align.CENTER)),
        ("M07_RIGHT_ROOF_FRAME_JIG", Pos((x_dash + x_bulkhead) / 2.0, -half_width * 0.78, roof_z + 70.0) * Box(x_bulkhead - x_dash + 2 * flange, 120.0, 140.0, align=Align.CENTER)),
        ("M08_TUNNEL_MANDREL", Pos((float(common["tunnel_start_x"]) + float(common["tunnel_end_x"])) / 2.0, 0.0, floor_z + tunnel_height / 2.0) * Box(float(common["tunnel_end_x"]) - float(common["tunnel_start_x"]), tunnel_width - 52.0, tunnel_height - 32.0, align=Align.CENTER)),
        ("M09_REAR_SHELF_UPPER", Pos(1660.0, 0.0, float(common["rear_shelf_z"]) + backing / 2.0) * Box(650.0, width - 80.0, backing, align=Align.CENTER)),
        ("M10_ROOF_HEADERS_JIG", Pos(1135.0, 0.0, roof_z + 70.0) * Box(1050.0, width, 140.0, align=Align.CENTER)),
    ]
    tools = []
    subtraction_failures = []
    for label, blank in blanks:
        try:
            tool = blank - cell if label != "M08_TUNNEL_MANDREL" else blank
        except Exception as exc:
            tool = blank
            subtraction_failures.append({"tool_id": label, "reason": str(exc)})
        tool.label = label
        tools.append(tool)
    return Compound(children=tools, label="964 993 CFRP COMMON CELL F1 MULTIPART TOOLING"), {
        "tool_count": len(tools),
        "tool_ids": [label for label, _ in blanks],
        "cavity_subtraction_failures": subtraction_failures,
        "tunnel_mandrel_modelled": True,
        "manufacturing_status": "tooling_partition_concept_only",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--topology", type=Path, default=DEFAULT_TOPOLOGY)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    config = load_json(args.config.resolve())
    topology = load_json(args.topology.resolve())
    selected = topology["architecture"]["architecture_id"]
    if selected != "all_carbon_multicell_x10":
        raise SystemExit(f"architecture CAO inattendue: {selected}")

    from build123d import export_step

    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    cell, cell_stats = build_cell(config, topology)
    tooling, tooling_stats = build_tooling(config, cell)
    platform_shapes = {platform_id: build_platform_modules(config, platform_id, dimensions) for platform_id, dimensions in config["platform_reference_dimensions_mm"].items()}
    package_shapes = {f"{platform}_{drive}": build_driveline_package(config, platform, drive) for platform in ("964", "993") for drive in ("C2", "C4")}

    cell_path = output / "993-carbon-safety-cell-concept.step"
    tooling_path = output / "993-carbon-safety-cell-tooling-concept.step"
    platform_paths = {
        "964_Carrera_2_Coupe": output / "964-carbon-interface-modules-concept.step",
        "993_Carrera_narrow_reference": output / "993-carbon-interface-modules-concept.step",
    }
    package_paths = {key: output / f"{key.lower().replace('_', '-')}-packaging-envelope.step" for key in package_shapes}
    export_step(cell, cell_path)
    export_step(tooling, tooling_path)
    for platform_id, (shape, _) in platform_shapes.items():
        export_step(shape, platform_paths[platform_id])
    for key, (shape, _) in package_shapes.items():
        export_step(shape, package_paths[key])

    report = {
        "schema_version": "1.1.0",
        "status": "concept_cad_generated_packaging_not_measured",
        "design_id": config["design_id"],
        "architecture_id": selected,
        "kernel": "build123d_OCCT",
        "units": "mm",
        "outputs": {
            "cell_step": str(cell_path.relative_to(ROOT)),
            "tooling_step": str(tooling_path.relative_to(ROOT)),
            "platform_module_steps": {platform_id: str(path.relative_to(ROOT)) for platform_id, path in platform_paths.items()},
            "driveline_packaging_steps": {key: str(path.relative_to(ROOT)) for key, path in package_paths.items()},
        },
        "cell": cell_stats,
        "tooling": tooling_stats,
        "platform_modules": {platform_id: stats for platform_id, (_, stats) in platform_shapes.items()},
        "driveline_packages": {key: stats for key, (_, stats) in package_shapes.items()},
        "mass_basis": config["mass_and_load_basis"],
        "material_policy": config["material_policy"],
        "source_boundary": {
            "clean_sheet": True,
            "zesad_or_ruf_surfaces_used": False,
            "porsche_pet_used_for_topology_only": True,
            "porsche_pet_dimensions_used": False,
            "vehicle_scan_used": False,
        },
        "release_gates": {
            "dimensionally_compatible_with_964": False,
            "dimensionally_compatible_with_993": False,
            "C2_C4_dynamic_clearance_verified": False,
            "vehicle_mass_target_verified": False,
            "laminate_defined": False,
            "tool_parting_and_draft_validated": False,
            "tool_thermal_vacuum_pressure_validated": False,
            "fabrication_released": False,
            "road_or_track_released": False,
        },
    }
    report_path = output / "cad-generation-report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
