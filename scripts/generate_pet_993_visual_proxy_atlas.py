#!/usr/bin/env python3
"""Generate a complete, fail-closed OpenUSD visual proxy atlas for PET 993.

Every PET part master gets one renderable archetype symbol and one deterministic
catalogue-atlas position.  Symbols and positions are deliberately non-dimensional:
they are navigation aids for the documentary twin, not reconstructed part geometry,
vehicle transforms, collision shapes, material assignments, or CAE input.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from generate_pet_993_openusd_federation import (
    ContractError,
    READINESS_INDEX,
    ROOT,
    SHARD_IDS,
    SKELETON,
    merged_records,
    relative,
    sha256_bytes,
    sha256_file,
    usd_bool,
    usd_name,
    usd_string,
    usd_string_array,
)


DOCUMENTARY_MANIFEST = ROOT / "twins" / "pet-993" / "openusd-federation-f0.json"
FUNCTIONAL_FLOW_CONTRACT = (
    ROOT / "twins" / "vehicle-993" / "functional-flow-openusd-f0.json"
)
FUNCTIONAL_FLOW_STAGE = ROOT / "twins" / "vehicle-993" / "usd" / "993-functional-flow-f0.usda"
PROGRAM_DEFINITION = ROOT / "twins" / "vehicle-993" / "program-definition.json"
OUTPUT_ROOT = ROOT / "work" / "pet-993" / "visual-proxy-atlas"
ROOT_STAGE = OUTPUT_ROOT / "pet-993-visual-proxy-atlas-f0.usda"
PROTOTYPE_STAGE = OUTPUT_ROOT / "pet-993-visual-proxy-prototypes-f0.usda"
SHARD_ROOT = OUTPUT_ROOT / "shards"
COMPOSED_STAGE = (
    ROOT / "work" / "vehicle-993" / "openusd" / "993-pet-catalogue-digital-twin-f0.usda"
)
MANIFEST = ROOT / "twins" / "pet-993" / "visual-proxy-atlas-f0.json"

GRID_COLUMNS = 64
GRID_SPACING_M = 0.14
SYSTEM_SPACING_X_M = 10.5
SYSTEM_SPACING_Y_M = 6.0


# These are display glyphs, not nominal dimensions.  The primitive choice only
# makes archetypes distinguishable in a catalogue browser.
ARCHETYPE_VISUALS: dict[str, dict[str, Any]] = {
    "bearing_or_bushing": {"primitive": "Cylinder", "radius": 0.035, "height": 0.012},
    "body_panel_or_external_structure": {"primitive": "Cube", "scale": [0.100, 0.060, 0.012]},
    "brake_hydraulic_friction_component": {"primitive": "Cylinder", "radius": 0.043, "height": 0.014},
    "cover_cap_or_trim": {"primitive": "Cube", "scale": [0.055, 0.040, 0.008]},
    "elastomer_mount_buffer_or_grommet": {"primitive": "Cylinder", "radius": 0.032, "height": 0.022},
    "fastener_or_retainer": {"primitive": "Cylinder", "radius": 0.012, "height": 0.060},
    "filter_screen_or_flow_conditioner": {"primitive": "Cylinder", "radius": 0.040, "height": 0.020},
    "fluid_hose_pipe_or_duct": {"primitive": "Capsule", "radius": 0.010, "height": 0.080},
    "fuel_exhaust_or_emissions_component": {"primitive": "Cylinder", "radius": 0.026, "height": 0.100},
    "generic_rigid_interface_piece": {"primitive": "Cube", "scale": [0.040, 0.030, 0.020]},
    "generic_system_0xx_service_or_documentation": {"primitive": "Cube", "scale": [0.030, 0.030, 0.006]},
    "generic_system_1xx_engine_component": {"primitive": "Sphere", "radius": 0.036},
    "generic_system_2xx_fuel_exhaust_component": {"primitive": "Capsule", "radius": 0.022, "height": 0.070},
    "generic_system_3xx_transmission_component": {"primitive": "Cylinder", "radius": 0.036, "height": 0.032},
    "generic_system_4xx_front_axle_steering_component": {"primitive": "Capsule", "radius": 0.024, "height": 0.060},
    "generic_system_5xx_rear_axle_driveline_component": {"primitive": "Cylinder", "radius": 0.040, "height": 0.026},
    "generic_system_6xx_brake_hydraulic_component": {"primitive": "Cylinder", "radius": 0.034, "height": 0.018},
    "generic_system_7xx_controls_pedals_clutch_component": {"primitive": "Cube", "scale": [0.052, 0.018, 0.030]},
    "generic_system_8xx_body_cabin_electrical_component": {"primitive": "Cube", "scale": [0.050, 0.038, 0.022]},
    "generic_system_9xx_option_accessory_component": {"primitive": "Sphere", "radius": 0.030},
    "glazing_mirror_or_optical_component": {"primitive": "Cube", "scale": [0.060, 0.045, 0.005]},
    "guide_rail_slide_or_hinge": {"primitive": "Cube", "scale": [0.075, 0.012, 0.012]},
    "heat_exchanger_or_cooler": {"primitive": "Cube", "scale": [0.070, 0.050, 0.015]},
    "housing_case_or_manifold": {"primitive": "Cube", "scale": [0.060, 0.045, 0.040]},
    "hvac_or_cabin_thermal_component": {"primitive": "Cube", "scale": [0.060, 0.040, 0.030]},
    "instrument_gauge_or_display_component": {"primitive": "Cylinder", "radius": 0.038, "height": 0.010},
    "insulation_absorber_or_heat_shield": {"primitive": "Cube", "scale": [0.075, 0.050, 0.006]},
    "joint_coupling_or_flange": {"primitive": "Cylinder", "radius": 0.040, "height": 0.014},
    "label_decal_film_or_trim_item": {"primitive": "Cube", "scale": [0.045, 0.030, 0.003]},
    "linkage_lever_cable_or_control": {"primitive": "Capsule", "radius": 0.012, "height": 0.075},
    "load_bearing_bracket_carrier_or_mount": {"primitive": "Cube", "scale": [0.060, 0.022, 0.040]},
    "pump_valve_or_injector": {"primitive": "Cylinder", "radius": 0.032, "height": 0.055},
    "rotating_powertrain_component": {"primitive": "Cylinder", "radius": 0.036, "height": 0.072},
    "seal_gasket_or_boot": {"primitive": "Cylinder", "radius": 0.034, "height": 0.006},
    "seat_restraint_or_occupant_structure": {"primitive": "Cube", "scale": [0.060, 0.050, 0.080]},
    "sensor_actuator_or_electrical_component": {"primitive": "Sphere", "radius": 0.030},
    "service_material_chemical_or_kit": {"primitive": "Sphere", "radius": 0.022},
    "shim_spacer_or_alignment_component": {"primitive": "Cylinder", "radius": 0.032, "height": 0.004},
    "spring_belt_or_compliant_mechanism": {"primitive": "Capsule", "radius": 0.018, "height": 0.072},
    "structural_reinforcement_member_or_plate": {"primitive": "Cube", "scale": [0.080, 0.025, 0.012]},
    "turbocharger_rotating_hot_flow_assembly": {"primitive": "Sphere", "radius": 0.052},
    "wheel_suspension_or_steering_component": {"primitive": "Cylinder", "radius": 0.050, "height": 0.025},
}


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot_load:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"expected_object:{path}")
    return value


def render_json(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def stable_color(archetype: str) -> tuple[float, float, float]:
    digest = hashlib.sha256(archetype.encode("utf-8")).digest()
    return tuple(0.25 + (channel / 255.0) * 0.60 for channel in digest[:3])


def primary_system_id(master: dict[str, Any]) -> str:
    system_ids = sorted(
        str(value)
        for value in master.get("documentary_graph", {}).get("system_ids", [])
    )
    if not system_ids:
        raise ContractError(f"master_without_system:{master.get('twin_id')}")
    unknown = set(system_ids) - {f"{value}xx" for value in range(10)}
    if unknown:
        raise ContractError(f"unknown_system:{master.get('twin_id')}:{sorted(unknown)}")
    return system_ids[0]


def layout_records(
    merged: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]],
) -> tuple[
    dict[str, list[tuple[dict[str, Any], dict[str, Any], str, int]]],
    Counter[str],
    Counter[str],
]:
    all_records = sorted(
        [
            (master, task, shard_id)
            for shard_id in SHARD_IDS
            for master, task in merged[shard_id]
        ],
        key=lambda item: str(item[0]["twin_id"]),
    )
    local_indexes: Counter[str] = Counter()
    by_primary_system: Counter[str] = Counter()
    by_archetype: Counter[str] = Counter()
    laid_out: dict[str, list[tuple[dict[str, Any], dict[str, Any], str, int]]] = {
        shard_id: [] for shard_id in SHARD_IDS
    }
    for master, task, shard_id in all_records:
        system_id = primary_system_id(master)
        archetype = str(task.get("engineering_route", {}).get("engineering_archetype", ""))
        if archetype not in ARCHETYPE_VISUALS:
            raise ContractError(f"missing_archetype_visual:{archetype}")
        local_index = local_indexes[system_id]
        local_indexes[system_id] += 1
        by_primary_system[system_id] += 1
        by_archetype[archetype] += 1
        laid_out[shard_id].append((master, task, system_id, local_index))
    for values in laid_out.values():
        values.sort(key=lambda item: (item[2], item[3], str(item[0]["twin_id"])))
    return laid_out, by_primary_system, by_archetype


def render_primitive(archetype: str, visual: dict[str, Any]) -> list[str]:
    primitive = str(visual["primitive"])
    red, green, blue = stable_color(archetype)
    lines = [
        f'    def Xform "{usd_name("Archetype_" + archetype)}"',
        "    {",
        f"        custom string engineeringArchetype = {usd_string(archetype)}",
        '        custom string representation = "archetype_display_symbol_not_part_geometry"',
        "        custom bool dimensionallyAccurate = false",
        "        custom bool usableForCae = false",
        "        custom bool usableForManufacturing = false",
        f'        def {primitive} "DisplaySymbol"',
        "        {",
    ]
    if primitive == "Cube":
        scale = visual["scale"]
        lines.extend(
            [
                "            double size = 1",
                f"            double3 xformOp:scale = ({scale[0]:.6f}, {scale[1]:.6f}, {scale[2]:.6f})",
                '            uniform token[] xformOpOrder = ["xformOp:scale"]',
            ]
        )
    elif primitive in {"Cylinder", "Capsule"}:
        lines.extend(
            [
                f"            double radius = {float(visual['radius']):.6f}",
                f"            double height = {float(visual['height']):.6f}",
                '            uniform token axis = "Z"',
            ]
        )
    elif primitive == "Sphere":
        lines.append(f"            double radius = {float(visual['radius']):.6f}")
    else:
        raise ContractError(f"unsupported_primitive:{primitive}")
    lines.extend(
        [
            f"            color3f[] primvars:displayColor = [({red:.4f}, {green:.4f}, {blue:.4f})]",
            '            uniform token primvars:displayColor:interpolation = "constant"',
            "        }",
            "    }",
        ]
    )
    return lines


def render_prototype_stage(archetypes: list[str]) -> str:
    lines = [
        "#usda 1.0",
        "(",
        '    defaultPrim = "PET993ProxyLibrary"',
        "    metersPerUnit = 1",
        '    upAxis = "Z"',
        ")",
        "",
        'def Scope "PET993ProxyLibrary"',
        "{",
    ]
    for archetype in archetypes:
        lines.extend(render_primitive(archetype, ARCHETYPE_VISUALS[archetype]))
    lines.extend(["}", ""])
    return "\n".join(lines)


def system_origin(system_index: int) -> tuple[float, float, float]:
    return (
        float(system_index % 5) * SYSTEM_SPACING_X_M,
        float(system_index // 5) * SYSTEM_SPACING_Y_M,
        0.0,
    )


def render_root_stage(
    skeleton: dict[str, Any],
    by_primary_system: Counter[str],
    part_count: int,
    archetypes: list[str],
) -> str:
    sublayers = ",\n".join(f"        @shards/{value}.usda@" for value in SHARD_IDS)
    lines = [
        "#usda 1.0",
        "(",
        '    defaultPrim = "PET993VisualAtlas"',
        "    metersPerUnit = 1",
        '    upAxis = "Z"',
        "    subLayers = [",
        sublayers,
        "    ]",
        ")",
        "",
        'def Xform "PET993VisualAtlas" (',
        "    customData = {",
        '        string fidelity = "F0_visual_archetype_proxy"',
        '        string purpose = "catalogue_navigation_not_vehicle_geometry"',
        f"        int partMasterProxyCount = {part_count}",
        f"        int archetypePrototypeCount = {len(archetypes)}",
        "        int engineeringGeometryCount = 0",
        "        int positionedVehiclePartCount = 0",
        "        int qualifiedMaterialCount = 0",
        "        int referenceSolverPassCount = 0",
        "        int physicsNeMoPassCount = 0",
        "        int simreadyValidatedCount = 0",
        "        bool functioningVehicle = false",
        "    }",
        ")",
        "{",
        '    def Scope "Systems"',
        "    {",
    ]
    systems = skeleton.get("systems", [])
    if len(systems) != 10:
        raise ContractError("skeleton_system_count")
    for index, system in enumerate(systems):
        system_id = str(system["system_id"])
        origin = system_origin(index)
        lines.extend(
            [
                f'        def Xform "{usd_name("System_" + system_id)}"',
                "        {",
                f"            custom string systemId = {usd_string(system_id)}",
                f"            custom string systemName = {usd_string(system.get('name', ''))}",
                f"            custom int primaryPartMasterCount = {by_primary_system[system_id]}",
                '            custom string positionSemantics = "catalogue_atlas_group_origin_not_vehicle_coordinates"',
                "            custom bool vehicleTransformKnown = false",
                f"            double3 xformOp:translate = ({origin[0]:.6f}, {origin[1]:.6f}, {origin[2]:.6f})",
                '            uniform token[] xformOpOrder = ["xformOp:translate"]',
                "        }",
            ]
        )
    lines.extend(
        [
            "    }",
            '    def Scope "PrototypeLegend"',
            "    {",
        ]
    )
    for archetype in archetypes:
        lines.extend(
            [
                f'        def Scope "{usd_name("Archetype_" + archetype)}"',
                "        {",
                f"            custom string engineeringArchetype = {usd_string(archetype)}",
                "            custom asset prototypeAsset = @pet-993-visual-proxy-prototypes-f0.usda@",
                '            custom string representation = "display_symbol_only"',
                "        }",
            ]
        )
    lines.extend(["    }", "}", ""])
    return "\n".join(lines)


def render_proxy_instance(
    master: dict[str, Any], task: dict[str, Any], system_id: str, local_index: int
) -> list[str]:
    twin_id = str(master["twin_id"])
    route = task.get("engineering_route", {})
    gates = task.get("engineering_gates", {})
    configuration = task.get("configuration_evidence", {})
    risk = task.get("risk_and_priority", {})
    archetype = str(route["engineering_archetype"])
    system_ids = sorted(
        str(value)
        for value in master.get("documentary_graph", {}).get("system_ids", [])
    )
    column = local_index % GRID_COLUMNS
    row = local_index // GRID_COLUMNS
    x = float(column) * GRID_SPACING_M
    y = float(row) * GRID_SPACING_M
    prototype_path = usd_name("Archetype_" + archetype)
    return [
        f'            def Xform "{usd_name(twin_id)}" (',
        f"                prepend references = @../pet-993-visual-proxy-prototypes-f0.usda@</PET993ProxyLibrary/{prototype_path}>",
        "                instanceable = true",
        "            )",
        "            {",
        f"                custom string partMasterTwinId = {usd_string(twin_id)}",
        f"                custom string engineeringTaskId = {usd_string(task.get('engineering_task_id', ''))}",
        f"                custom string engineeringArchetype = {usd_string(archetype)}",
        f"                custom string primarySystemId = {usd_string(system_id)}",
        f"                custom string[] systemMembership = {usd_string_array(system_ids)}",
        f"                custom string sourceFidelity = {usd_string(gates.get('current_fidelity', 'F0_reference'))}",
        f"                custom string configurationStatus = {usd_string(configuration.get('status', ''))}",
        f"                custom string criticalityTier = {usd_string(risk.get('criticality_tier', ''))}",
        f"                custom bool professionalEngineeringReviewRequired = {usd_bool(risk.get('professional_engineering_review_required'))}",
        '                custom string representation = "F0_visual_archetype_proxy"',
        '                custom string positionSemantics = "catalogue_grid_index_not_vehicle_transform"',
        "                custom bool displayGeometryOnly = true",
        "                custom bool dimensionallyAccurate = false",
        "                custom bool vehicleTransformKnown = false",
        "                custom bool materialSelected = false",
        "                custom bool referenceSimulationPassed = false",
        "                custom bool physicsNeMoValidated = false",
        "                custom bool simreadyValidated = false",
        "                custom bool manufacturingReleased = false",
        f"                custom int catalogueAtlasIndex = {local_index}",
        f"                double3 xformOp:translate = ({x:.6f}, {y:.6f}, 0.000000)",
        '                uniform token[] xformOpOrder = ["xformOp:translate"]',
        "            }",
    ]


def render_shard(
    records: list[tuple[dict[str, Any], dict[str, Any], str, int]],
) -> str:
    by_system: dict[str, list[tuple[dict[str, Any], dict[str, Any], str, int]]] = defaultdict(list)
    for record in records:
        by_system[record[2]].append(record)
    lines = ["#usda 1.0", "", 'over "PET993VisualAtlas"', "{", '    over "Systems"', "    {"]
    for system_id in sorted(by_system):
        lines.extend(
            [
                f'        over "{usd_name("System_" + system_id)}"',
                "        {",
            ]
        )
        for master, task, primary_system, local_index in by_system[system_id]:
            lines.extend(render_proxy_instance(master, task, primary_system, local_index))
        lines.append("        }")
    lines.extend(["    }", "}", ""])
    return "\n".join(lines)


def render_composed_stage(documentary_root: Path) -> str:
    documentary_asset = os.path.relpath(documentary_root, COMPOSED_STAGE.parent)
    visual_asset = os.path.relpath(ROOT_STAGE, COMPOSED_STAGE.parent)
    flow_asset = os.path.relpath(FUNCTIONAL_FLOW_STAGE, COMPOSED_STAGE.parent)
    return "\n".join(
        [
            "#usda 1.0",
            "(",
            '    defaultPrim = "Porsche993CatalogueDigitalTwin"',
            "    metersPerUnit = 1",
            '    upAxis = "Z"',
            ")",
            "",
            'def Xform "Porsche993CatalogueDigitalTwin"',
            "{",
            '    custom string fidelity = "F0_documentary_and_visual_proxy_composition"',
            '    custom string scope = "complete_pet_catalogue_not_configured_vehicle_bom"',
            "    custom int partMasterTwinCount = 6013",
            "    custom int visualProxyInstanceCount = 6013",
            "    custom int engineeringGeometryCount = 0",
            "    custom int positionedVehiclePartCount = 0",
            "    custom bool physicsAssigned = false",
            "    custom bool simreadyValidated = false",
            "    custom bool functioningVehicle = false",
            "",
            '    def Xform "DocumentaryCatalogue" (',
            f"        prepend references = @{documentary_asset}@</PET993Catalogue>",
            "    )",
            "    {",
            "    }",
            '    def Xform "VisualProxyAtlas" (',
            f"        prepend references = @{visual_asset}@</PET993VisualAtlas>",
            "    )",
            "    {",
            "    }",
            '    def Xform "FunctionalFlowTopology" (',
            f"        prepend references = @{flow_asset}@</FunctionalFlow993>",
            "    )",
            "    {",
            "    }",
            "}",
            "",
        ]
    )


def build() -> tuple[str, str, dict[str, str], str, dict[str, Any]]:
    merged, _pet_index, readiness, skeleton = merged_records()
    laid_out, by_primary_system, by_archetype = layout_records(merged)
    expected_archetypes = readiness.get("coverage", {}).get("tasks_by_engineering_archetype", {})
    if dict(sorted(by_archetype.items())) != expected_archetypes:
        raise ContractError("archetype_coverage_mismatch")
    used_archetypes = sorted(by_archetype)
    unsupported = set(used_archetypes) - set(ARCHETYPE_VISUALS)
    if unsupported:
        raise ContractError(f"missing_archetype_visuals:{sorted(unsupported)}")
    part_count = sum(by_primary_system.values())
    root_stage = render_root_stage(
        skeleton, by_primary_system, part_count, used_archetypes
    )
    prototype_stage = render_prototype_stage(used_archetypes)
    shard_texts = {
        shard_id: render_shard(laid_out[shard_id]) for shard_id in SHARD_IDS
    }

    documentary = load_json(DOCUMENTARY_MANIFEST)
    documentary_root = ROOT / str(documentary.get("output", {}).get("root_stage", ""))
    if not documentary_root.is_file():
        raise ContractError(f"missing_documentary_root_stage:{documentary_root}")
    if sha256_file(documentary_root) != documentary.get("output", {}).get("root_stage_sha256"):
        raise ContractError("documentary_root_stage_digest")
    if not FUNCTIONAL_FLOW_STAGE.is_file():
        raise ContractError(f"missing_functional_flow_stage:{FUNCTIONAL_FLOW_STAGE}")
    composed_stage = render_composed_stage(documentary_root)
    program_definition = load_json(PROGRAM_DEFINITION)
    physicsnemo = program_definition.get("physicsnemo_policy", {})
    manifest = {
        "$comment": (
            "Atlas OpenUSD F0 couvrant chaque maitre PET par un symbole d'archetype. "
            "Les formes et positions sont visuelles, non dimensionnelles et inutilisables "
            "pour CAE, montage ou fabrication."
        ),
        "schema_version": "1.0.0",
        "generated_by": relative(Path(__file__).resolve()),
        "source_boundary": {
            "engineering_readiness_index": relative(READINESS_INDEX),
            "engineering_readiness_index_sha256": sha256_file(READINESS_INDEX),
            "documentary_openusd_manifest": relative(DOCUMENTARY_MANIFEST),
            "documentary_openusd_manifest_sha256": sha256_file(DOCUMENTARY_MANIFEST),
            "documentary_root_stage": relative(documentary_root),
            "documentary_root_stage_sha256": sha256_file(documentary_root),
            "functional_flow_contract": relative(FUNCTIONAL_FLOW_CONTRACT),
            "functional_flow_contract_sha256": sha256_file(FUNCTIONAL_FLOW_CONTRACT),
            "functional_flow_stage": relative(FUNCTIONAL_FLOW_STAGE),
            "functional_flow_stage_sha256": sha256_file(FUNCTIONAL_FLOW_STAGE),
            "assembly_skeleton": relative(SKELETON),
            "assembly_skeleton_sha256": sha256_file(SKELETON),
            "program_definition": relative(PROGRAM_DEFINITION),
            "program_definition_sha256": sha256_file(PROGRAM_DEFINITION),
        },
        "atlas": {
            "fidelity": "F0_visual_archetype_proxy",
            "part_master_proxy_instances": part_count,
            "catalogue_master_coverage_ratio": 1.0,
            "archetype_prototypes": len(used_archetypes),
            "system_groups": len(by_primary_system),
            "shard_layers": len(SHARD_IDS),
            "engineering_geometry_count": 0,
            "positioned_vehicle_part_count": 0,
            "by_primary_system": dict(sorted(by_primary_system.items())),
            "by_engineering_archetype": dict(sorted(by_archetype.items())),
            "layout": {
                "kind": "deterministic_catalogue_grid",
                "columns": GRID_COLUMNS,
                "part_spacing_m_display_only": GRID_SPACING_M,
                "system_spacing_x_m_display_only": SYSTEM_SPACING_X_M,
                "system_spacing_y_m_display_only": SYSTEM_SPACING_Y_M,
                "position_semantics": "catalogue_navigation_not_vehicle_coordinates",
            },
            "shape_semantics": "archetype_symbol_not_reconstructed_part_geometry",
        },
        "output": {
            "tracked": False,
            "root_stage": relative(ROOT_STAGE),
            "root_stage_sha256": sha256_bytes(root_stage.encode("utf-8")),
            "prototype_stage": relative(PROTOTYPE_STAGE),
            "prototype_stage_sha256": sha256_bytes(prototype_stage.encode("utf-8")),
            "composed_catalogue_digital_twin_stage": relative(COMPOSED_STAGE),
            "composed_catalogue_digital_twin_stage_sha256": sha256_bytes(
                composed_stage.encode("utf-8")
            ),
            "shards": [
                {
                    "shard_id": shard_id,
                    "path": relative(SHARD_ROOT / f"{shard_id}.usda"),
                    "proxy_instance_count": len(laid_out[shard_id]),
                    "sha256": sha256_bytes(shard_texts[shard_id].encode("utf-8")),
                }
                for shard_id in SHARD_IDS
            ],
        },
        "physicsnemo_dataset_boundary": {
            "canonical_repository": physicsnemo.get("canonical_repository"),
            "discovered_commit": physicsnemo.get("discovered_commit"),
            "candidate_model_families": [
                "GeoTransolver",
                "Transolver",
                "MeshGraphNet",
                "DoMINO",
            ],
            "candidate_data_interfaces": [
                "MeshReader",
                "DomainMeshReader",
                "VTKReader",
                "TransolverDataPipe",
                "DoMINODataPipe",
            ],
            "atlas_is_training_or_validation_data": False,
            "execution_enabled": False,
            "required_before_training": [
                "F3_engineering_geometry_or_qualified_CFD_domain",
                "mesh_convergence_evidence",
                "qualified_material_and_boundary_conditions",
                "converged_reference_solver_samples",
                "geometry_and_load_family_grouped_splits",
                "held_out_validation_and_out_of_domain_rejection",
            ],
        },
        "validation": {
            "source_shard_digests": "passed",
            "one_proxy_instance_per_part_master": "passed",
            "archetype_partition_matches_engineering_readiness": "passed",
            "primary_system_partition_closes": "passed",
            "deterministic_ascii_contract": "passed",
            "openusd_python_api": "blocked_by_recorded_preflight",
            "asset_validator": "blocked_by_recorded_preflight",
            "simready_validated": False,
        },
        "rights_boundary": {
            "detailed_identity_text_location": "work_only_untracked",
            "tracked_manifest_contains_oem_references_or_descriptions": False,
            "raw_pet_pdf_or_illustrations_copied": False,
            "do_not_commit_generated_usd_layers": True,
        },
        "claim_boundary": {
            "visual_symbol_is_dimensionally_accurate_geometry": False,
            "catalogue_grid_position_is_vehicle_transform": False,
            "part_master_is_configured_vehicle_instance": False,
            "archetype_is_human_reviewed_classification": False,
            "proxy_is_valid_cae_mesh": False,
            "proxy_has_qualified_material": False,
            "proxy_is_physicsnemo_dataset": False,
            "stage_is_simready": False,
            "stage_proves_functioning_vehicle": False,
            "stage_authorizes_manufacturing_or_road_use": False,
        },
        "next_gate": (
            "replace_each_visual_symbol_with_configuration_specific_editable_geometry_"
            "measured_or_source_bounded_interfaces_material_loads_and_reference_solver_evidence"
        ),
    }
    validate(root_stage, prototype_stage, shard_texts, composed_stage, manifest)
    return root_stage, prototype_stage, shard_texts, composed_stage, manifest


def validate(
    root_stage: str,
    prototype_stage: str,
    shard_texts: dict[str, str],
    composed_stage: str,
    manifest: dict[str, Any],
) -> None:
    atlas = manifest.get("atlas", {})
    if atlas.get("part_master_proxy_instances") != 6013:
        raise ContractError("proxy_instance_count")
    if atlas.get("catalogue_master_coverage_ratio") != 1.0:
        raise ContractError("catalogue_coverage_ratio")
    if atlas.get("archetype_prototypes") != len(
        atlas.get("by_engineering_archetype", {})
    ):
        raise ContractError("archetype_prototype_count")
    if atlas.get("system_groups") != 10 or atlas.get("shard_layers") != 16:
        raise ContractError("atlas_partition")
    if sum(atlas.get("by_primary_system", {}).values()) != 6013:
        raise ContractError("primary_system_partition")
    if sum(atlas.get("by_engineering_archetype", {}).values()) != 6013:
        raise ContractError("archetype_partition")
    if sum(text.count('def Xform "TWIN_') for text in shard_texts.values()) != 6013:
        raise ContractError("rendered_proxy_instance_count")
    reference_token = "prepend references = @../pet-993-visual-proxy-prototypes-f0.usda@"
    if sum(text.count(reference_token) for text in shard_texts.values()) != 6013:
        raise ContractError("rendered_prototype_reference_count")
    if sum(
        prototype_stage.count(f'def {name} "DisplaySymbol"')
        for name in ("Cube", "Cylinder", "Capsule", "Sphere")
    ) != atlas.get("archetype_prototypes"):
        raise ContractError("rendered_prototype_count")
    if root_stage.count('def Xform "System_') != 10:
        raise ContractError("rendered_system_count")
    if len(shard_texts) != 16 or set(shard_texts) != set(SHARD_IDS):
        raise ContractError("rendered_shard_count")
    for prim in ("DocumentaryCatalogue", "VisualProxyAtlas", "FunctionalFlowTopology"):
        if f'def Xform "{prim}"' not in composed_stage:
            raise ContractError(f"composed_stage_missing:{prim}")
    combined = root_stage + prototype_stage + composed_stage + "".join(shard_texts.values())
    for prohibited in (
        "UsdPhysics",
        "RigidBodyAPI",
        "CollisionAPI",
        "MassAPI",
        "MaterialBindingAPI",
    ):
        if prohibited in combined:
            raise ContractError(f"prohibited_physics_claim:{prohibited}")
    for field in ("engineering_geometry_count", "positioned_vehicle_part_count"):
        if atlas.get(field) != 0:
            raise ContractError(f"overclaim:{field}")
    if manifest.get("output", {}).get("tracked") is not False:
        raise ContractError("output_tracking_boundary")
    if manifest.get("physicsnemo_dataset_boundary", {}).get("execution_enabled") is not False:
        raise ContractError("physicsnemo_execution_overclaim")
    if manifest.get("physicsnemo_dataset_boundary", {}).get("atlas_is_training_or_validation_data") is not False:
        raise ContractError("physicsnemo_dataset_overclaim")
    if manifest.get("validation", {}).get("simready_validated") is not False:
        raise ContractError("simready_overclaim")
    if any(value is not False for value in manifest.get("claim_boundary", {}).values()):
        raise ContractError("claim_boundary")
    rights = manifest.get("rights_boundary", {})
    if rights.get("tracked_manifest_contains_oem_references_or_descriptions") is not False:
        raise ContractError("rights_boundary")


def validate_tracked_manifest() -> None:
    manifest = load_json(MANIFEST)
    sources = manifest.get("source_boundary", {})
    tracked_sources = (
        (READINESS_INDEX, "engineering_readiness_index_sha256"),
        (DOCUMENTARY_MANIFEST, "documentary_openusd_manifest_sha256"),
        (FUNCTIONAL_FLOW_CONTRACT, "functional_flow_contract_sha256"),
        (FUNCTIONAL_FLOW_STAGE, "functional_flow_stage_sha256"),
        (SKELETON, "assembly_skeleton_sha256"),
        (PROGRAM_DEFINITION, "program_definition_sha256"),
    )
    for path, digest_key in tracked_sources:
        if not path.is_file() or sources.get(digest_key) != sha256_file(path):
            raise ContractError(f"tracked_source_digest:{relative(path)}")
    atlas = manifest.get("atlas", {})
    if atlas.get("part_master_proxy_instances") != 6013:
        raise ContractError("tracked_proxy_instance_count")
    readiness = load_json(READINESS_INDEX)
    expected_archetypes = readiness.get("coverage", {}).get("tasks_by_engineering_archetype", {})
    if atlas.get("by_engineering_archetype") != expected_archetypes:
        raise ContractError("tracked_archetype_partition")
    if sum(atlas.get("by_primary_system", {}).values()) != 6013:
        raise ContractError("tracked_primary_system_partition")
    output = manifest.get("output", {})
    if len(output.get("shards", [])) != 16:
        raise ContractError("tracked_shard_count")
    if sum(item.get("proxy_instance_count", 0) for item in output["shards"]) != 6013:
        raise ContractError("tracked_shard_instance_count")
    if output.get("tracked") is not False:
        raise ContractError("tracked_output_boundary")
    if any(value is not False for value in manifest.get("claim_boundary", {}).values()):
        raise ContractError("tracked_claim_boundary")


def write_outputs(
    root_stage: str,
    prototype_stage: str,
    shards: dict[str, str],
    composed_stage: str,
    manifest: dict[str, Any],
) -> None:
    SHARD_ROOT.mkdir(parents=True, exist_ok=True)
    COMPOSED_STAGE.parent.mkdir(parents=True, exist_ok=True)
    ROOT_STAGE.write_text(root_stage, encoding="utf-8")
    PROTOTYPE_STAGE.write_text(prototype_stage, encoding="utf-8")
    for shard_id in SHARD_IDS:
        (SHARD_ROOT / f"{shard_id}.usda").write_text(shards[shard_id], encoding="utf-8")
    COMPOSED_STAGE.write_text(composed_stage, encoding="utf-8")
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(render_json(manifest), encoding="utf-8")


def check_outputs(
    root_stage: str,
    prototype_stage: str,
    shards: dict[str, str],
    composed_stage: str,
    manifest: dict[str, Any],
) -> None:
    expected: dict[Path, str] = {
        ROOT_STAGE: root_stage,
        PROTOTYPE_STAGE: prototype_stage,
        COMPOSED_STAGE: composed_stage,
        MANIFEST: render_json(manifest),
    }
    expected.update({SHARD_ROOT / f"{key}.usda": value for key, value in shards.items()})
    for path, content in expected.items():
        if not path.is_file():
            raise ContractError(f"missing_output:{path}")
        if path.read_text(encoding="utf-8") != content:
            raise ContractError(f"stale_output:{path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--check-index", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.check_index:
            validate_tracked_manifest()
            print(f"valid {relative(MANIFEST)}: complete 6013-master visual-proxy index")
            return 0
        root_stage, prototype_stage, shards, composed_stage, manifest = build()
        if args.write:
            write_outputs(root_stage, prototype_stage, shards, composed_stage, manifest)
            print(f"wrote {relative(ROOT_STAGE)} with {manifest['atlas']['part_master_proxy_instances']} proxies")
            print(f"wrote {relative(COMPOSED_STAGE)}")
            print(f"wrote {relative(MANIFEST)}")
            return 0
        check_outputs(root_stage, prototype_stage, shards, composed_stage, manifest)
        print(f"current {relative(ROOT_STAGE)}: 6013 visual proxy instances")
        print(f"current {relative(COMPOSED_STAGE)}")
        print(f"current {relative(MANIFEST)}")
        return 0
    except (ContractError, KeyError, TypeError, ValueError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
