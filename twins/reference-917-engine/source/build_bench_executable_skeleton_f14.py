#!/usr/bin/env python3
"""Build fail-closed F14 Omniverse bench overlays without authoring engine physics."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[3]
VARIANT_NA = "type_912_4_5_na"
VARIANT_TURBO = "917_30_turbo_5374"
VARIANT_TAGS = {
    VARIANT_NA: {"all", "type_912_4_5_na"},
    VARIANT_TURBO: {"all", "917_30_only"},
}
ENDPOINT_KEYS = {
    "mechanical_connections": ("body_a", "body_b"),
    "ducts": ("source", "target"),
}
NEW_PHYSICS_TOKENS = (
    "PhysicsJoint",
    "PhysicsRevoluteJoint",
    "PhysicsPrismaticJoint",
    "PhysicsFixedJoint",
    "PhysicsArticulationRootAPI",
    "PhysicsRigidBodyAPI",
    "PhysicsCollisionAPI",
    "PhysicsMassAPI",
    "PhysicsScene",
)
ASCII_JOINT_TOKENS = (
    "PhysicsJoint",
    "PhysicsRevoluteJoint",
    "PhysicsPrismaticJoint",
    "PhysicsFixedJoint",
)


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: JSON root must be an object")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def identifier(value: str) -> str:
    result = re.sub(r"[^A-Za-z0-9_]", "_", value)
    if not result or result[0].isdigit():
        result = f"id_{result}"
    return result


def string_literal(value: str) -> str:
    return json.dumps(value, ensure_ascii=True)


def relative_asset(layer: Path, asset: Path) -> str:
    return os.path.relpath(asset.resolve(), layer.parent.resolve()).replace(os.sep, "/")


def applies(item: dict, variant_id: str) -> bool:
    return item["variant"] in VARIANT_TAGS[variant_id]


def instances(items: Iterable[dict], variant_id: str | None = None) -> int:
    selected = items if variant_id is None else (item for item in items if applies(item, variant_id))
    return sum(item["count"] for item in selected)


def endpoint_path(scope: str, endpoint_id: str) -> str:
    return f"/World/BenchExecutableF14/Ports/{identifier(scope)}/{identifier(endpoint_id)}"


def endpoint_target(scope: str, endpoint_id: str) -> str:
    if scope == "engine_family":
        return f"/World/Components/{identifier(endpoint_id)}"
    if scope == "bench_component":
        return f"/World/BenchExecutableF14/Equipment/{identifier(endpoint_id)}"
    if scope == "support_component":
        return f"semantic-support-component:{endpoint_id}"
    if scope == "external_interface":
        return f"semantic-external-interface:{endpoint_id}"
    raise ValueError(f"unsupported endpoint scope: {scope}")


def source_paths(project_root: Path, config: dict) -> dict[str, Path]:
    return {
        key: (project_root / value).resolve()
        for key, value in config["source_contracts"].items()
    }


def endpoint_registry(project_root: Path, config: dict, sources: dict[str, Path]) -> dict[str, set[str]]:
    base = load_json(sources["base_engine_families"])
    detail = load_json(sources["detail_engine_families"])
    support = load_json(sources["support_components"])
    external = load_json(sources["external_interfaces"])
    return {
        "engine_family": {item["id"] for item in base["component_families"]}
        | {item["id"] for item in detail["families"]},
        "bench_component": {item["id"] for item in config["bench_equipment"]},
        "support_component": {item["id"] for item in support["support_components"]},
        "external_interface": {item["id"] for item in external["external_interfaces"]},
    }


def validate_endpoint(endpoint: object, registry: dict[str, set[str]], label: str, errors: list[str]) -> None:
    if not isinstance(endpoint, dict):
        errors.append(f"{label}: endpoint must be an object")
        return
    scope = endpoint.get("scope")
    endpoint_id = endpoint.get("id")
    if scope not in registry:
        errors.append(f"{label}: unknown scope {scope!r}")
    elif endpoint_id not in registry[scope]:
        errors.append(f"{label}: unknown {scope} endpoint {endpoint_id!r}")


def validate_contract(
    config: dict,
    f10_variants: dict,
    f4_bench: dict,
    mechanical: dict,
    ducts: dict,
    registry: dict[str, set[str]],
) -> tuple[list[str], dict]:
    errors: list[str] = []
    equipment = config["bench_equipment"]
    sensors = config["instrumentation"]
    mechanical_items = mechanical["mechanical_connections"]
    duct_items = ducts["ducts"]

    derived = {
        "bench_equipment_groups": len(equipment),
        "bench_equipment_instances": instances(equipment),
        "f4_missing_equipment_instances": sum(
            item["count"] for item in equipment if item["f4_authoring_status"] == "missing"
        ),
        "sensor_families": len(sensors),
        "sensor_endpoints": instances(sensors),
        "mechanical_groups": len(mechanical_items),
        "mechanical_union_instances": instances(mechanical_items),
        "mechanical_na_instances": instances(mechanical_items, VARIANT_NA),
        "mechanical_turbo_instances": instances(mechanical_items, VARIANT_TURBO),
        "duct_groups": len(duct_items),
        "duct_union_instances": instances(duct_items),
        "duct_common_instances": sum(item["count"] for item in duct_items if item["variant"] == "all"),
        "duct_na_only_instances": sum(
            item["count"] for item in duct_items if item["variant"] == "type_912_4_5_na"
        ),
        "duct_turbo_only_instances": sum(
            item["count"] for item in duct_items if item["variant"] == "917_30_only"
        ),
        "duct_na_instances": instances(duct_items, VARIANT_NA),
        "duct_turbo_instances": instances(duct_items, VARIANT_TURBO),
    }

    acceptance = config["acceptance"]
    expected = {
        "bench_equipment_groups": acceptance["bench_equipment_group_count"],
        "bench_equipment_instances": acceptance["bench_equipment_instance_count"],
        "f4_missing_equipment_instances": acceptance["f4_missing_equipment_instance_count_materialized"],
        "sensor_families": acceptance["sensor_family_count"],
        "sensor_endpoints": acceptance["sensor_endpoint_count"],
        "mechanical_groups": config["semantic_graph"]["mechanical_connections"]["group_count"],
        "mechanical_union_instances": config["semantic_graph"]["mechanical_connections"]["union_instance_count"],
        "mechanical_na_instances": config["semantic_graph"]["mechanical_connections"]["na_instance_count"],
        "mechanical_turbo_instances": config["semantic_graph"]["mechanical_connections"]["turbo_instance_count"],
        "duct_groups": config["semantic_graph"]["ducts"]["group_count"],
        "duct_union_instances": config["semantic_graph"]["ducts"]["union_instance_count"],
        "duct_common_instances": config["semantic_graph"]["ducts"]["common_instance_count"],
        "duct_na_only_instances": config["semantic_graph"]["ducts"]["na_only_instance_count"],
        "duct_turbo_only_instances": config["semantic_graph"]["ducts"]["turbo_only_instance_count"],
        "duct_na_instances": config["semantic_graph"]["ducts"]["na_instance_count"],
        "duct_turbo_instances": config["semantic_graph"]["ducts"]["turbo_instance_count"],
    }
    for key, expected_value in expected.items():
        if derived[key] != expected_value:
            errors.append(f"count mismatch for {key}: derived {derived[key]}, expected {expected_value}")

    f4_equipment = {item["id"]: item["count"] for item in f4_bench["bench_components"]}
    f14_equipment = {item["id"]: item["count"] for item in equipment}
    if f14_equipment != f4_equipment:
        errors.append("F14 bench equipment ids/counts do not reproduce the F4 declared inventory")
    f4_sensors = {
        item["id"]: (item["count"], item["required_for"])
        for item in f4_bench["instrumentation"]
    }
    f14_sensors = {
        item["id"]: (item["count"], item["required_for"])
        for item in sensors
    }
    if f14_sensors != f4_sensors:
        errors.append("F14 sensor endpoints do not reproduce the F4 instrumentation contract")

    if derived["mechanical_groups"] != mechanical["acceptance"]["connection_group_count"]:
        errors.append("F8 mechanical group acceptance count is internally inconsistent")
    if derived["mechanical_union_instances"] != mechanical["acceptance"]["connection_instance_count"]:
        errors.append("F8 mechanical instance acceptance count is internally inconsistent")
    if derived["duct_groups"] != ducts["acceptance"]["duct_group_count"]:
        errors.append("F8 duct group acceptance count is internally inconsistent")
    if derived["duct_union_instances"] != ducts["acceptance"]["duct_instance_count"]:
        errors.append("F8 duct instance acceptance count is internally inconsistent")

    variants = {item["variant_id"]: item for item in config["variants"]}
    upstream_variants = {item["variant_id"]: item for item in f10_variants["variants"]}
    for variant_id in (VARIANT_NA, VARIANT_TURBO):
        if variant_id not in variants:
            errors.append(f"missing F14 variant {variant_id}")
            continue
        if variant_id not in upstream_variants:
            errors.append(f"missing upstream F10 variant {variant_id}")
            continue
        expected_input = f"work/917-variant-geometry-f10/{upstream_variants[variant_id]['outputs']['detail_stage']}"
        if variants[variant_id]["input_stage"] != expected_input:
            errors.append(
                f"{variant_id}: input_stage must point to its explicit F10 detail stage {expected_input}"
            )
        expected_mechanical = derived[f"mechanical_{'na' if variant_id == VARIANT_NA else 'turbo'}_instances"]
        expected_ducts = derived[f"duct_{'na' if variant_id == VARIANT_NA else 'turbo'}_instances"]
        if variants[variant_id]["expected_mechanical_connection_instances"] != expected_mechanical:
            errors.append(f"{variant_id}: mechanical count does not match source F8")
        if variants[variant_id]["expected_duct_instances"] != expected_ducts:
            errors.append(f"{variant_id}: duct count does not match source F8")

    for collection_name, collection in (
        ("mechanical_connections", mechanical_items),
        ("ducts", duct_items),
    ):
        first_key, second_key = ENDPOINT_KEYS[collection_name]
        for item in collection:
            validate_endpoint(item.get(first_key), registry, f"{collection_name}.{item['id']}.{first_key}", errors)
            validate_endpoint(item.get(second_key), registry, f"{collection_name}.{item['id']}.{second_key}", errors)

    return errors, derived


def used_endpoints(mechanical_items: list[dict], duct_items: list[dict], variant_id: str) -> set[tuple[str, str]]:
    result: set[tuple[str, str]] = set()
    for collection_name, collection in (
        ("mechanical_connections", mechanical_items),
        ("ducts", duct_items),
    ):
        first_key, second_key = ENDPOINT_KEYS[collection_name]
        for item in collection:
            if not applies(item, variant_id):
                continue
            for key in (first_key, second_key):
                endpoint = item[key]
                result.add((endpoint["scope"], endpoint["id"]))
    return result


def authored_equipment(lines: list[str], equipment: list[dict]) -> None:
    lines.extend(['        def Scope "Equipment"', "        {"])
    global_index = 0
    for item in equipment:
        item_id = identifier(item["id"])
        lines.extend([f'            def Scope "{item_id}"', "            {"])
        for index in range(1, item["count"] + 1):
            column = global_index % 8
            row = global_index // 8
            x = -630 + column * 180
            y = -760 - row * 90
            z = -430
            global_index += 1
            lines.extend(
                [
                    f'                def Xform "{item_id}_{index:02d}" (',
                    "                    customData = {",
                    '                        dictionary "3dprinting993" = {',
                    f"                            string equipmentId = {string_literal(item['id'])}",
                    f"                            int equipmentInstanceIndex = {index}",
                    f"                            string f4AuthoringStatus = {string_literal(item['f4_authoring_status'])}",
                    f"                            string status = {string_literal(item['f14_status'])}",
                    "                            bool physicalInterfaceMeasured = 0",
                    "                            bool simulationReady = 0",
                    "                        }",
                    "                    }",
                    "                )",
                    "                {",
                    f"                    double3 xformOp:translate = ({x}, {y}, {z})",
                    '                    uniform token[] xformOpOrder = ["xformOp:translate"]',
                    '                    def Sphere "EndpointMarker"',
                    "                    {",
                    "                        double radius = 18",
                    "                        color3f[] primvars:displayColor = [(0.82, 0.47, 0.04)]",
                    "                    }",
                    "                }",
                ]
            )
        lines.extend(["            }", ""])
    lines.extend(["        }", ""])


def authored_sensors(lines: list[str], sensors: list[dict]) -> None:
    lines.extend(['        def Scope "Sensors"', "        {"])
    global_index = 0
    for item in sensors:
        item_id = identifier(item["id"])
        lines.extend([f'            def Scope "{item_id}"', "            {"])
        for index in range(1, item["count"] + 1):
            column = global_index % 14
            row = global_index // 14
            x = -650 + column * 100
            y = 760 + row * 45
            z = -430
            global_index += 1
            lines.extend(
                [
                    f'                def Xform "{item_id}_{index:02d}" (',
                    "                    customData = {",
                    '                        dictionary "3dprinting993" = {',
                    f"                            string sensorFamily = {string_literal(item['id'])}",
                    f"                            int sensorInstanceIndex = {index}",
                    f"                            string requiredForJson = {string_literal(json.dumps(item['required_for']))}",
                    '                            string status = "semantic_endpoint_range_position_and_calibration_unmeasured"',
                    "                            bool calibrated = 0",
                    "                            bool simulationReady = 0",
                    "                        }",
                    "                    }",
                    "                )",
                    "                {",
                    f"                    double3 xformOp:translate = ({x}, {y}, {z})",
                    '                    uniform token[] xformOpOrder = ["xformOp:translate"]',
                    '                    def Sphere "EndpointMarker"',
                    "                    {",
                    "                        double radius = 5",
                    "                        color3f[] primvars:displayColor = [(0.08, 0.68, 0.88)]",
                    "                    }",
                    "                }",
                ]
            )
        lines.extend(["            }", ""])
    lines.extend(["        }", ""])


def authored_ports(lines: list[str], endpoints: set[tuple[str, str]]) -> None:
    lines.extend(['        def Scope "Ports"', "        {"])
    grouped: dict[str, list[str]] = {}
    for scope, endpoint_id in endpoints:
        grouped.setdefault(scope, []).append(endpoint_id)
    for scope in sorted(grouped):
        lines.extend([f'            def Scope "{identifier(scope)}"', "            {"])
        for endpoint_id in sorted(grouped[scope]):
            lines.extend(
                [
                    f'                def Xform "{identifier(endpoint_id)}" (',
                    "                    customData = {",
                    '                        dictionary "3dprinting993" = {',
                    f"                            string endpointScope = {string_literal(scope)}",
                    f"                            string endpointId = {string_literal(endpoint_id)}",
                    f"                            string semanticTarget = {string_literal(endpoint_target(scope, endpoint_id))}",
                    '                            string status = "semantic_family_port_frame_and_geometry_unmeasured"',
                    "                            bool physicalFrameMeasured = 0",
                    "                        }",
                    "                    }",
                    "                )",
                    "                {",
                    "                }",
                ]
            )
        lines.extend(["            }", ""])
    lines.extend(["        }", ""])


def authored_graph(
    lines: list[str],
    scope_name: str,
    items: list[dict],
    variant_id: str,
    endpoint_keys: tuple[str, str],
) -> int:
    first_key, second_key = endpoint_keys
    count = 0
    lines.extend([f'        def Scope "{scope_name}"', "        {"])
    for item in items:
        if not applies(item, variant_id):
            continue
        for index in range(1, item["count"] + 1):
            first = item[first_key]
            second = item[second_key]
            count += 1
            lines.extend(
                [
                    f'            def Scope "{identifier(item["id"])}_{index:03d}" (',
                    "                customData = {",
                    '                    dictionary "3dprinting993" = {',
                    f"                        string groupId = {string_literal(item['id'])}",
                    f"                        int groupInstanceIndex = {index}",
                    f"                        string variantId = {string_literal(variant_id)}",
                    '                        string status = "semantic_connectivity_only_exact_instance_pairing_unresolved"',
                    "                        bool physicsEnabled = 0",
                    "                        bool geometryReleased = 0",
                    "                    }",
                    "                }",
                    "            )",
                    "            {",
                    f"                custom rel {first_key} = <{endpoint_path(first['scope'], first['id'])}>",
                    f"                custom rel {second_key} = <{endpoint_path(second['scope'], second['id'])}>",
                    "            }",
                ]
            )
    lines.extend(["        }", ""])
    return count


def build_overlay(
    output: Path,
    input_stage: Path,
    variant: dict,
    config: dict,
    mechanical_items: list[dict],
    duct_items: list[dict],
) -> dict:
    endpoints = used_endpoints(mechanical_items, duct_items, variant["variant_id"])
    lines = [
        "#usda 1.0",
        "(",
        '    defaultPrim = "World"',
        "    endTimeCode = 240",
        "    framesPerSecond = 24",
        "    metersPerUnit = 0.001",
        "    startTimeCode = 0",
        "    subLayers = [",
        f"        @{relative_asset(output, input_stage)}@",
        "    ]",
        "    timeCodesPerSecond = 24",
        '    upAxis = "Z"',
        ")",
        "",
        'over "World" (',
        "    customData = {",
        '        dictionary "3dprinting993" = {',
        '            string benchExecutableSkeletonPhase = "F14"',
        f"            string benchExecutableVariantId = {string_literal(variant['variant_id'])}",
        '            string status = "software_skeleton_only_engine_physics_blocked"',
        "            bool softwareRuntimeDoesNotProveEnginePhysics = 1",
        "            bool enginePhysicsValidated = 0",
        "            bool fluidSimulationReady = 0",
        "            bool firedRunAuthorized = 0",
        "        }",
        "    }",
        ")",
        "{",
        '    def Xform "BenchExecutableF14" (',
        "        customData = {",
        '            dictionary "3dprinting993" = {',
        '                string releaseStatus = "research_only"',
        '                string connectivityStatus = "semantic_only"',
        "                int newJointSchemaCount = 0",
        "                int newCfdVolumeCount = 0",
        "            }",
        "        }",
        '        kind = "assembly"',
        "    )",
        "    {",
    ]
    authored_equipment(lines, config["bench_equipment"])
    authored_sensors(lines, config["instrumentation"])
    authored_ports(lines, endpoints)
    mechanical_count = authored_graph(
        lines,
        "MechanicalConnectionGraph",
        mechanical_items,
        variant["variant_id"],
        ENDPOINT_KEYS["mechanical_connections"],
    )
    duct_count = authored_graph(
        lines,
        "DuctConnectivityGraph",
        duct_items,
        variant["variant_id"],
        ENDPOINT_KEYS["ducts"],
    )
    lines.extend(["    }", "}", ""])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    text = output.read_text(encoding="utf-8")
    forbidden = [token for token in NEW_PHYSICS_TOKENS if token in text]
    return {
        "variant_id": variant["variant_id"],
        "input_stage": str(input_stage.resolve()),
        "input_stage_sha256": sha256(input_stage),
        "output_stage": str(output.resolve()),
        "output_stage_sha256": sha256(output),
        "bench_equipment_instances": instances(config["bench_equipment"]),
        "sensor_endpoints": instances(config["instrumentation"]),
        "semantic_port_count": len(endpoints),
        "orphan_semantic_endpoint_count": 0,
        "mechanical_connection_instances": mechanical_count,
        "duct_instances": duct_count,
        "new_physics_schema_tokens": forbidden,
        "new_physics_joint_count": 0,
        "new_cfd_volume_count": 0,
    }


def scan_ascii_joint_tokens(root_stage: Path) -> dict:
    pending = [root_stage.resolve()]
    visited: set[Path] = set()
    findings: list[dict[str, str]] = []
    skipped_binary: list[str] = []
    while pending:
        path = pending.pop()
        if path in visited or not path.is_file():
            continue
        visited.add(path)
        if path.suffix.lower() in {".usdc", ".usdz"}:
            skipped_binary.append(str(path))
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            skipped_binary.append(str(path))
            continue
        for token in ASCII_JOINT_TOKENS:
            if token in text:
                findings.append({"path": str(path), "token": token})
        for asset_ref in re.findall(r"@([^@]+)@", text):
            referenced = (path.parent / asset_ref).resolve()
            if referenced.suffix.lower() in {".usd", ".usda", ".usdc", ".usdz"}:
                pending.append(referenced)
    return {
        "ascii_layer_count": len(visited) - len(skipped_binary),
        "ascii_joint_token_findings": findings,
        "binary_assets_not_joint_inspected": sorted(skipped_binary),
    }


def run_usdchecker(checker: str | None, stage: Path) -> dict:
    if not checker:
        return {
            "status": "not_available",
            "passed": False,
            "tool": None,
            "note": "USDA was authored and statically checked, but no USD runtime checker was available.",
        }
    try:
        result = subprocess.run(
            [checker, str(stage.resolve())],
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "failed", "passed": False, "tool": checker, "error": str(exc)}
    combined = (result.stdout + "\n" + result.stderr).strip().splitlines()
    return {
        "status": "passed" if result.returncode == 0 else "failed",
        "passed": result.returncode == 0,
        "tool": checker,
        "returncode": result.returncode,
        "output_tail": combined[-12:],
        "scope": "USD syntax_composition_and_dependency_check_only_not_engine_physics",
    }


def blocked_report(output_root: Path, errors: list[str], derived: dict | None = None) -> dict:
    report = {
        "schema_version": "1.0.0",
        "phase": "F14",
        "status": "blocked_before_authoring",
        "software_runtime_passed": False,
        "engine_physics_validated": False,
        "fluid_simulation_ready": False,
        "fired_run_executed": False,
        "errors": errors,
        "derived_counts": derived or {},
    }
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "state-machine-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--na-input-stage", type=Path)
    parser.add_argument("--turbo-input-stage", type=Path)
    parser.add_argument("--usdchecker")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    config_path = (args.config or project_root / "twins/reference-917-engine/bench-executable-skeleton-f14.json").resolve()
    output_root = args.output.resolve()
    try:
        config = load_json(config_path)
        sources = source_paths(project_root, config)
        missing_sources = [str(path) for path in sources.values() if not path.is_file()]
        if missing_sources:
            report = blocked_report(output_root, [f"missing source contract: {path}" for path in missing_sources])
            print(json.dumps(report, indent=2))
            return 2
        f10_variants = load_json(sources["variants"])
        f4_bench = load_json(sources["bench"])
        mechanical = load_json(sources["mechanical_connections"])
        ducts = load_json(sources["ducts"])
        registry = endpoint_registry(project_root, config, sources)
        errors, derived = validate_contract(
            config,
            f10_variants,
            f4_bench,
            mechanical,
            ducts,
            registry,
        )
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        report = blocked_report(output_root, [str(exc)])
        print(json.dumps(report, indent=2))
        return 2

    if errors:
        report = blocked_report(output_root, errors, derived)
        print(json.dumps(report, indent=2))
        return 1

    variant_by_id = {item["variant_id"]: item for item in config["variants"]}
    input_overrides = {
        VARIANT_NA: args.na_input_stage,
        VARIANT_TURBO: args.turbo_input_stage,
    }
    input_stages: dict[str, Path] = {}
    stage_errors: list[str] = []
    for variant_id, variant in variant_by_id.items():
        candidate = input_overrides.get(variant_id) or project_root / variant["input_stage"]
        candidate = candidate.resolve()
        input_stages[variant_id] = candidate
        if not candidate.is_file():
            stage_errors.append(f"{variant_id}: missing explicit F10 input stage {candidate}")
            continue
        try:
            header = candidate.read_bytes()[:16]
        except OSError as exc:
            stage_errors.append(f"{variant_id}: cannot read input stage: {exc}")
            continue
        if not header.startswith(b"#usda"):
            stage_errors.append(f"{variant_id}: F14 requires an ASCII USDA F10 input stage")
    if stage_errors:
        report = blocked_report(output_root, stage_errors, derived)
        print(json.dumps(report, indent=2))
        return 2

    output_root.mkdir(parents=True, exist_ok=True)
    stage_reports = []
    for variant_id in (VARIANT_NA, VARIANT_TURBO):
        variant = variant_by_id[variant_id]
        output_stage = output_root / variant["output_slug"] / "917-engine-bench-executable-skeleton-f14.usda"
        stage_report = build_overlay(
            output_stage,
            input_stages[variant_id],
            variant,
            config,
            mechanical["mechanical_connections"],
            ducts["ducts"],
        )
        stage_report["ascii_dependency_joint_scan"] = scan_ascii_joint_tokens(output_stage)
        stage_reports.append(stage_report)

    checker = args.usdchecker if args.usdchecker is not None else shutil.which("usdchecker")
    runtime_results = [run_usdchecker(checker, Path(item["output_stage"])) for item in stage_reports]
    for stage_report, runtime in zip(stage_reports, runtime_results):
        stage_report["usd_runtime_check"] = runtime

    new_schema_free = all(not item["new_physics_schema_tokens"] for item in stage_reports)
    no_ascii_joints = all(
        not item["ascii_dependency_joint_scan"]["ascii_joint_token_findings"]
        for item in stage_reports
    )
    runtime_passed = all(item["passed"] for item in runtime_results)
    counts_passed = all(
        item["mechanical_connection_instances"]
        == variant_by_id[item["variant_id"]]["expected_mechanical_connection_instances"]
        and item["duct_instances"] == variant_by_id[item["variant_id"]]["expected_duct_instances"]
        for item in stage_reports
    )
    semantic_endpoints_passed = all(item["orphan_semantic_endpoint_count"] == 0 for item in stage_reports)
    software_runtime_passed = (
        runtime_passed and counts_passed and semantic_endpoints_passed and new_schema_free and no_ascii_joints
    )

    gates = [
        {
            "id": "source_stage_integrity",
            "status": "passed",
            "evidence": [item["input_stage_sha256"] for item in stage_reports],
        },
        {
            "id": "contract_count_consistency",
            "status": "passed" if counts_passed else "failed",
            "evidence": derived,
        },
        {
            "id": "semantic_endpoint_resolution",
            "status": "passed" if semantic_endpoints_passed else "failed",
            "orphan_endpoint_count": sum(item["orphan_semantic_endpoint_count"] for item in stage_reports),
        },
        {
            "id": "usd_overlay_validation",
            "status": "passed" if runtime_passed else "blocked_or_failed",
            "scope": "software_USD_runtime_only",
        },
        {
            "id": "measured_interface_frames",
            "status": "blocked",
            "reason": "F8 mechanical interface frames, clearances, masses and inertias remain unmeasured",
        },
        {
            "id": "closed_internal_fluid_volumes",
            "status": "blocked",
            "reason": "F8 ducts are semantic family-level edges; no watertight internal flow volume was authored",
        },
        {
            "id": "reference_solver_and_test_correlation",
            "status": "blocked",
            "reason": "No correlated multibody, CFD, thermal, structural or combustion result is attached to F14",
        },
        {
            "id": "instrumented_start_authorization",
            "status": "blocked",
            "reason": "The 49 endpoints have no calibrated ranges, positions, sampling rates or trip thresholds",
        },
    ]
    report = {
        "schema_version": "1.0.0",
        "phase": "F14",
        "status": (
            "software_runtime_passed_engine_physics_blocked"
            if software_runtime_passed
            else "software_skeleton_authored_runtime_not_verified_engine_physics_blocked"
        ),
        "contract": str(config_path),
        "contract_sha256": sha256(config_path),
        "derived_counts": derived,
        "variant_stages": stage_reports,
        "state_machine": gates,
        "software_runtime_passed": software_runtime_passed,
        "software_runtime_scope": "USD syntax, composition, dependency and semantic graph checks only; not engine physics validation",
        "engine_physics_validated": False,
        "engine_physics_joint_count": 0,
        "engine_articulation_root_count": 0,
        "cfd_volume_count": 0,
        "fluid_simulation_ready": False,
        "physicsnemo_training_ready": False,
        "fired_run_executed": False,
        "fired_run_authorized": False,
        "unresolved_physical_work": [
            "measure every mechanical interface frame and exact instance pairing",
            "measure masses, inertias, clearances, friction, stiffness, damping and limits",
            "reconstruct watertight internal intake, exhaust, oil, fuel and cooling domains",
            "define and validate seals and external boundary conditions",
            "correlate classical solvers against calibrated physical tests before PhysicsNeMo",
        ],
        "prohibited_use": config["prohibited_use"],
    }
    (output_root / "state-machine-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    return 0 if counts_passed and semantic_endpoints_passed and new_schema_free and no_ascii_joints else 1


if __name__ == "__main__":
    raise SystemExit(main())
