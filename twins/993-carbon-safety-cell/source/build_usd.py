#!/usr/bin/env python3
"""Construit les couches OpenUSD diagnostiques de la monocoque carbone 964/993."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
TWIN_ROOT = ROOT / "twins" / "993-carbon-safety-cell"
DEFAULT_CONFIG = TWIN_ROOT / "design-space.json"
DEFAULT_TOPOLOGY = TWIN_ROOT / "derived" / "selected-topology.json"
DEFAULT_SCREENING = TWIN_ROOT / "derived" / "structural-screening.json"
DEFAULT_OUTPUT = TWIN_ROOT / "derived"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: objet JSON attendu")
    return value


def number(value: float) -> str:
    rendered = f"{value:.9f}".rstrip("0").rstrip(".")
    return rendered if rendered not in {"", "-0"} else "0"


def point(value: tuple[float, float, float] | list[float]) -> str:
    return "(" + ", ".join(number(float(item)) for item in value) + ")"


def material(name: str, color: tuple[float, float, float], metallic: float, roughness: float, opacity: float = 1.0) -> str:
    return f'''        def Material "{name}"
        {{
            token outputs:surface.connect = </World/Looks/{name}/PreviewSurface.outputs:surface>

            def Shader "PreviewSurface"
            {{
                uniform token info:id = "UsdPreviewSurface"
                color3f inputs:diffuseColor = {point(color)}
                float inputs:metallic = {number(metallic)}
                float inputs:opacity = {number(opacity)}
                float inputs:roughness = {number(roughness)}
                token outputs:surface
            }}
        }}
'''


def cube(name: str, center: tuple[float, float, float], dimensions: tuple[float, float, float], material_path: str, purpose: str = "proxy") -> str:
    scale = tuple(value / 2.0 for value in dimensions)
    return f'''            def Cube "{name}" (
                prepend apiSchemas = ["MaterialBindingAPI"]
            )
            {{
                double size = 2
                uniform token purpose = "{purpose}"
                rel material:binding = <{material_path}>
                double3 xformOp:scale = {point(scale)}
                double3 xformOp:translate = {point(center)}
                uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
            }}
'''


def curves(name: str, segments: list[tuple[tuple[float, float, float], tuple[float, float, float], float]], material_path: str) -> str:
    points = [coordinate for start, end, _ in segments for coordinate in (start, end)]
    counts = ", ".join("2" for _ in segments)
    widths = ", ".join(number(width) for _, _, width in segments for _ in range(2))
    coordinates = ",\n                    ".join(point(value) for value in points)
    return f'''            def BasisCurves "{name}" (
                prepend apiSchemas = ["MaterialBindingAPI"]
            )
            {{
                int[] curveVertexCounts = [{counts}]
                point3f[] points = [
                    {coordinates}
                ]
                uniform token purpose = "guide"
                rel material:binding = <{material_path}>
                uniform token type = "linear"
                float[] widths = [{widths}]
                uniform token wrap = "nonperiodic"
            }}
'''


def build_cell_usd(config: dict[str, Any], topology: dict[str, Any], screening: dict[str, Any]) -> str:
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
    width = 2.0 * half_width
    node_map = {item["node_id"]: tuple(float(value) for value in item["xyz_mm"]) for item in topology["nodes"]}
    selected = next(item for item in screening["architectures"] if item["architecture_id"] == screening["selection"]["architecture_id"])

    carbon_segments = []
    for member in topology["members"]:
        if member["material"] != config["material_policy"]["primary_structure_material"]:
            raise ValueError(f"chemin primaire non CFRP interdit: {member['member_id']}")
        carbon_segments.append((node_map[member["node_a"]], node_map[member["node_b"]], 9.0))

    deformation_scale = 35.0
    displaced = {
        node_id: tuple(node_map[node_id][axis] + deformation_scale * float(values[axis]) for axis in range(3))
        for node_id, values in selected["displacements_mm"].items()
    }
    deformed_segments = [
        (displaced[member["node_a"]], displaced[member["node_b"]], 5.0)
        for member in topology["members"]
    ]

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
    panels = [cube("FloorSandwich", ((tub_start + tub_end) / 2.0, 0.0, floor_z), (tub_end - tub_start, width, 34.0), "/World/Looks/Carbon")]
    for side, sign in (("L", 1.0), ("R", -1.0)):
        panels.extend([
            cube(f"{side}_DeepSill", ((sill_start + sill_end) / 2.0, sign * (half_width - sill_width / 2.0), floor_z + sill_height / 2.0), (sill_end - sill_start, sill_width, sill_height), "/World/Looks/Carbon"),
            cube(f"{side}_Footwell", (570.0, sign * 365.0, floor_z + 62.0), (330.0, 430.0, 92.0), "/World/Looks/Carbon"),
            cube(f"{side}_RearSeatWell", (1580.0, sign * 350.0, float(common["rear_shelf_z"]) - 30.0), (430.0, 420.0, 46.0), "/World/Looks/Carbon"),
            cube(f"{side}_RearWheelhouseProxy", (1830.0, sign * 535.0, floor_z + 300.0), (360.0, 190.0, 430.0), "/World/Looks/Carbon"),
        ])
    tunnel_center = (tunnel_start + tunnel_end) / 2.0
    for side, sign in (("L", 1.0), ("R", -1.0)):
        panels.append(cube(f"TunnelWall{side}", (tunnel_center, sign * (tunnel_width - 26.0) / 2.0, floor_z + tunnel_height / 2.0), (tunnel_end - tunnel_start, 26.0, tunnel_height), "/World/Looks/Carbon"))
    panels.append(cube("TunnelRemovableServiceCover", (tunnel_center, 0.0, floor_z + tunnel_height), (tunnel_end - tunnel_start, tunnel_width, float(common["service_cover_thickness"])), "/World/Looks/Carbon"))
    bulkhead_side_width = (width - tunnel_width - 120.0) / 2.0
    bulkhead_y = (tunnel_width + 60.0 + bulkhead_side_width) / 2.0
    for side, sign in (("L", 1.0), ("R", -1.0)):
        panels.append(cube(f"FrontBulkhead{side}", (x_dash, sign * bulkhead_y, floor_z + 310.0), (38.0, bulkhead_side_width, 570.0), "/World/Looks/Carbon"))
        panels.append(cube(f"RearBulkhead{side}", (x_bulkhead, sign * bulkhead_y, floor_z + 350.0), (44.0, bulkhead_side_width, 650.0), "/World/Looks/Carbon"))
    panels.extend([
        cube("FrontBulkheadHeader", (x_dash, 0.0, belt_z + 120.0), (42.0, width - 170.0, 210.0), "/World/Looks/Carbon"),
        cube("RearBulkheadHeader", (x_bulkhead, 0.0, belt_z + 135.0), (46.0, width - 140.0, 240.0), "/World/Looks/Carbon"),
        cube("RearShelf", (1660.0, 0.0, float(common["rear_shelf_z"])), (360.0, width - 260.0, 42.0), "/World/Looks/Carbon"),
    ])
    automotive_frame = []
    for sign in (-1.0, 1.0):
        automotive_frame.extend([
            ((560.0, sign * 590.0, belt_z), (1660.0, sign * 590.0, belt_z + 20.0), 34.0),
            ((510.0, sign * 590.0, belt_z), (735.0, sign * 505.0, roof_z), 34.0),
            ((1660.0, sign * 590.0, belt_z + 20.0), (1540.0, sign * 505.0, roof_z), 38.0),
            ((735.0, sign * 505.0, roof_z), (1540.0, sign * 505.0, roof_z), 36.0),
        ])
    automotive_frame.extend([
        ((735.0, -505.0, roof_z), (735.0, 505.0, roof_z), 36.0),
        ((1540.0, -505.0, roof_z), (1540.0, 505.0, roof_z), 38.0),
        ((1130.0, -505.0, roof_z + 10.0), (1130.0, 505.0, roof_z + 10.0), 29.0),
    ])

    services = package["protected_service_channels"]
    service_segments = [
        ((540.0, float(services[key]), floor_z + 72.0), (1860.0, float(services[key]), floor_z + 72.0), 14.0)
        for key in ("brake_fuel_left_center_y", "wiring_right_center_y", "parking_brake_left_center_y", "parking_brake_right_center_y")
    ]
    c2 = package["c2_package"]
    c2_segments = [((float(c2["external_shift_rod_start_x"]), float(c2["external_shift_rod_center_y"]), float(c2["external_shift_rod_center_z"])), (float(c2["external_shift_rod_end_x"]), float(c2["external_shift_rod_center_y"]), float(c2["external_shift_rod_center_z"])), float(c2["external_shift_rod_diameter"]))]
    c2_shapes = [cube("ShifterTowerClearance", tuple(float(v) for v in c2["shifter_tower_center_xyz"]), tuple(float(v) for v in c2["shifter_tower_envelope_xyz"]), "/World/Looks/Shift", "guide")]
    c4 = package["c4_package"]
    c4_start = float(c4["central_tube_start_x"])
    c4_end = float(c4["central_tube_end_x"])
    c4_z = float(c4["central_tube_center_z"])
    c4_segments = [
        ((c4_start, 0.0, c4_z), (c4_end, 0.0, c4_z), float(c4["central_tube_outer_diameter"])),
        ((c4_start, 0.0, c4_z), (c4_end, 0.0, c4_z), float(c4["propeller_shaft_clearance_diameter"])),
        ((100.0, float(c4["shift_guide_center_y"]), c4_z + 82.0), (1850.0, float(c4["shift_guide_center_y"]), c4_z + 82.0), float(c4["shift_guide_diameter"])),
        ((0.0, -float(c4["front_halfshaft_total_span"]) / 2.0, c4_z), (0.0, float(c4["front_halfshaft_total_span"]) / 2.0, c4_z), float(c4["front_halfshaft_clearance_diameter"])),
    ]
    c4_shapes = [cube("FrontFinalDriveClearance", tuple(float(v) for v in c4["front_final_drive_center_xyz"]), tuple(float(v) for v in c4["front_final_drive_envelope_xyz"]), "/World/Looks/C4", "guide")]
    adapter_half_width = half_width - 50.0
    for station, x_mm in (("Front", x_front), ("Rear", x_rear)):
        for side, sign in (("L", 1.0), ("R", -1.0)):
            panels.append(cube(f"{station}CommonAdapter{side}", (x_mm, sign * adapter_half_width, floor_z), (120.0, 100.0, 80.0), "/World/Looks/Interface"))

    platform_panels = []
    platform_materials = {
        "964_Carrera_2_Coupe": "/World/Looks/Platform964",
        "993_Carrera_narrow_reference": "/World/Looks/Platform993",
    }
    for platform_id, dimensions in config["platform_reference_dimensions_mm"].items():
        for station, x_mm, track_key in (
            ("Front", x_front, "front_track"),
            ("Rear", x_rear, "rear_track"),
        ):
            envelope_half_track = float(dimensions[track_key]) / 2.0
            span = envelope_half_track - adapter_half_width
            for side, sign in (("L", 1.0), ("R", -1.0)):
                center_y = sign * (adapter_half_width + span / 2.0)
                platform_panels.append(
                    cube(
                        f"P_{platform_id}_{station}Pod{side}",
                        (x_mm, center_y, floor_z),
                        (100.0, abs(span), 64.0),
                        platform_materials[platform_id],
                    )
                )
                platform_panels.append(
                    cube(
                        f"P_{platform_id}_{station}Envelope{side}",
                        (x_mm, sign * envelope_half_track, floor_z),
                        (110.0, 90.0, 74.0),
                        platform_materials[platform_id],
                        "guide",
                    )
                )

    load_segments = [
        ((x_front, float(geometry["front_half_track"]), floor_z + 220.0), (x_front, float(geometry["front_half_track"]), floor_z), 18.0),
        ((x_front, -float(geometry["front_half_track"]), floor_z - 220.0), (x_front, -float(geometry["front_half_track"]), floor_z), 18.0),
    ]
    support_boxes = [
        cube("RearSupportL", (x_rear, float(geometry["rear_half_track"]), floor_z - 85.0), (180.0, 180.0, 120.0), "/World/Looks/Support", "guide"),
        cube("RearSupportR", (x_rear, -float(geometry["rear_half_track"]), floor_z - 85.0), (180.0, 180.0, 120.0), "/World/Looks/Support", "guide"),
    ]
    return f'''#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 0.001
    upAxis = "Z"
)

def Xform "World" (
    kind = "assembly"
)
{{
    custom string analysisStatus = "F1_screening_complete_not_validated"
    custom string architectureId = "{screening['selection']['architecture_id']}"
    custom string designOrigin = "clean_sheet_original_topology"
    custom bool allCarbonPrimaryStructure = true
    custom bool dimensionalFit964Validated = false
    custom bool dimensionalFit993Validated = false
    custom bool C2C4DynamicClearanceValidated = false
    custom bool roadOrTrackReleased = false
    custom double targetVehicleMassKg = {number(float(config['mass_and_load_basis']['target_vehicle_mass_kg']))}
    custom double screeningTorsionalStiffnessNmPerDeg = {number(float(selected['torsion']['stiffness_Nm_per_deg']))}
    custom string screeningWarning = "Treillis lineaire non correle; aucune aptitude crash route circuit ou fabrication"
    custom string packagingStatus = "functional topology present; dimensions are hypotheses pending four-vehicle metrology"

    def Scope "Looks"
    {{
{material('Carbon', (0.025, 0.035, 0.045), 0.15, 0.28)}
{material('Interface', (0.95, 0.56, 0.08), 0.35, 0.32)}
{material('Platform964', (0.12, 0.52, 0.86), 0.25, 0.32)}
{material('Platform993', (0.18, 0.76, 0.38), 0.25, 0.32)}
{material('Load', (0.90, 0.03, 0.02), 0.05, 0.42)}
{material('Support', (0.03, 0.18, 0.85), 0.35, 0.30)}
{material('Deformed', (0.95, 0.14, 0.02), 0.05, 0.35)}
{material('Shift', (0.96, 0.43, 0.05), 0.22, 0.34)}
{material('C4', (0.04, 0.58, 0.82), 0.32, 0.28)}
{material('Service', (0.55, 0.75, 0.18), 0.10, 0.42)}
    }}

    def Xform "Cell"
    {{
        def Xform "ConceptPanels"
        {{
{''.join(panels)}        }}

        def Xform "AutomotiveRoofAndDoorFrames"
        {{
{curves('CFRPFramePaths', automotive_frame, '/World/Looks/Carbon')}
        }}

        def Xform "EquivalentLoadPaths"
        {{
{curves('CarbonPaths', carbon_segments, '/World/Looks/Carbon')}
        }}

        def Xform "PlatformEnvelopeModules"
        {{
{''.join(platform_panels)}        }}

        def Xform "ProtectedServiceChannels"
        {{
{curves('BrakeFuelWiringParkingBrakeGuides', service_segments, '/World/Looks/Service')}
        }}

        def Xform "DrivelinePackages"
        {{
            def Xform "C2"
            {{
                custom string status = "hypothesis_envelope_not_measured"
                custom bool longPropellerShaftPresent = false
{curves('ExternalShiftRodClearance', c2_segments, '/World/Looks/Shift')}
{''.join(c2_shapes)}            }}

            def Xform "C4"
            {{
                custom string status = "hypothesis_envelope_not_measured"
                custom bool longPropellerShaftPresent = true
{curves('CentralTubePropShaftShiftGuideFrontHalfshafts', c4_segments, '/World/Looks/C4')}
{''.join(c4_shapes)}            }}
        }}
    }}

    def Xform "BoundaryConditions"
    {{
{curves('OpposedTorsionLoads', load_segments, '/World/Looks/Load')}
{''.join(support_boxes)}    }}

    def Xform "DeformedShape_x35"
    {{
{curves('TorsionResult', deformed_segments, '/World/Looks/Deformed')}
    }}
}}
'''


def build_tooling_usd(config: dict[str, Any]) -> str:
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
    tools = [
        cube("M01_FloorLower", ((x_front + x_rear) / 2.0, 0.0, floor_z - backing / 2.0), (length + 2 * flange, width + 2 * flange, backing), "/World/Looks/Tool"),
        cube("M02_LeftSide", ((x_front + x_rear) / 2.0, half_width + backing / 2.0, (floor_z + belt_z) / 2.0), (length + 2 * flange, backing, belt_z - floor_z + 2 * flange), "/World/Looks/Tool"),
        cube("M03_RightSide", ((x_front + x_rear) / 2.0, -half_width - backing / 2.0, (floor_z + belt_z) / 2.0), (length + 2 * flange, backing, belt_z - floor_z + 2 * flange), "/World/Looks/Tool"),
        cube("M04_FrontBulkhead", (x_dash - backing / 2.0, 0.0, (floor_z + belt_z) / 2.0), (backing, width + 2 * flange, belt_z - floor_z + 2 * flange), "/World/Looks/Tool"),
        cube("M05_RearBulkhead", (x_bulkhead + backing / 2.0, 0.0, (floor_z + belt_z) / 2.0), (backing, width + 2 * flange, belt_z - floor_z + 2 * flange), "/World/Looks/Tool"),
        cube("M06_RoofLeftJig", ((x_dash + x_bulkhead) / 2.0, half_width * 0.78, roof_z + 70.0), (x_bulkhead - x_dash + 2 * flange, 120.0, 140.0), "/World/Looks/Tool"),
        cube("M07_RoofRightJig", ((x_dash + x_bulkhead) / 2.0, -half_width * 0.78, roof_z + 70.0), (x_bulkhead - x_dash + 2 * flange, 120.0, 140.0), "/World/Looks/Tool"),
        cube("M08_TunnelMandrel", ((float(common["tunnel_start_x"]) + float(common["tunnel_end_x"])) / 2.0, 0.0, floor_z + float(common["tunnel_outer_height"]) / 2.0), (float(common["tunnel_end_x"]) - float(common["tunnel_start_x"]), float(common["tunnel_outer_width"]) - 52.0, float(common["tunnel_outer_height"]) - 32.0), "/World/Looks/Tool"),
        cube("M09_RearShelfUpper", (1660.0, 0.0, float(common["rear_shelf_z"]) + backing / 2.0), (650.0, width - 80.0, backing), "/World/Looks/Tool"),
        cube("M10_RoofHeadersJig", (1135.0, 0.0, roof_z + 70.0), (1050.0, width, 140.0), "/World/Looks/Tool"),
    ]
    return f'''#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 0.001
    upAxis = "Z"
)

def Xform "World" (
    kind = "assembly"
)
{{
    custom string manufacturingStatus = "tooling_partition_concept_only"
    custom bool partingDraftValidated = false
    custom bool autoclaveThermalPressureValidated = false
    custom bool fabricationReleased = false

    def Scope "Looks"
    {{
{material('Tool', (0.12, 0.42, 0.62), 0.55, 0.24, 0.58)}
    }}

    def Xform "ToolingSectors"
    {{
{''.join(tools)}    }}
}}
'''


def root_layer() -> str:
    return '''#usda 1.0
(
    defaultPrim = "DigitalTwin"
    metersPerUnit = 0.001
    upAxis = "Z"
)

def Xform "DigitalTwin" (
    kind = "assembly"
)
{
    custom string claimScope = "964 993 all-carbon concept, structural screening and tooling layout only"
    custom bool simReadyValidated = false
    custom bool roadOrTrackReleased = false

    def Xform "Cell" (
        prepend references = @./993-carbon-safety-cell-structural.usda@</World>
    )
    {
    }

    def Xform "Tooling" (
        prepend references = @./993-carbon-safety-cell-tooling.usda@</World>
    )
    {
        token visibility = "invisible"
    }
}
'''


def build_outputs(config: dict[str, Any], topology: dict[str, Any], screening: dict[str, Any]) -> dict[Path, str]:
    return {
        DEFAULT_OUTPUT / "993-carbon-safety-cell-structural.usda": build_cell_usd(config, topology, screening),
        DEFAULT_OUTPUT / "993-carbon-safety-cell-tooling.usda": build_tooling_usd(config),
        DEFAULT_OUTPUT / "993-carbon-safety-cell-digital-twin.usda": root_layer(),
    }


def run(write: bool) -> int:
    outputs = build_outputs(load_json(DEFAULT_CONFIG), load_json(DEFAULT_TOPOLOGY), load_json(DEFAULT_SCREENING))
    stale = []
    for path, content in outputs.items():
        if write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        elif not path.is_file() or path.read_text(encoding="utf-8") != content:
            stale.append(path)
    if stale:
        for path in stale:
            print(f"stale: {path.relative_to(ROOT)}")
        return 1
    print(f"carbon safety cell USD: {len(outputs)} layers {'written' if write else 'current'}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    return run(write=args.write)


if __name__ == "__main__":
    raise SystemExit(main())
