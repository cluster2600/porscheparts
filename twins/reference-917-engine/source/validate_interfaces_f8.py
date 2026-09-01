#!/usr/bin/env python3
"""Validate the fail-closed 917 F8 connection, seal and duct contracts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
VALID_VARIANTS = {"all", "type_912_4_5_na", "917_30_only"}
VALID_SCOPES = {"engine_family", "bench_component", "support_component", "external_interface"}
FORBIDDEN_F9_KEYS = {"power", "power_kw", "horsepower", "target_power", "boost_target", "combustion_model"}


def is_missing(value: object) -> bool:
    return value is None or value == "" or value == [] or value == {}


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: JSON root must be an object")
    return value


def collect_keys(value: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            keys.add(key)
            keys.update(collect_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(collect_keys(child))
    return keys


def source_registry(project_root: Path) -> set[str]:
    result = set()
    for path in (project_root / "catalog" / "sources").glob("*.json"):
        try:
            source_id = load_json(path).get("source_id")
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(source_id, str):
            result.add(source_id)
    return result


def endpoint_registry(project_root: Path) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    twin_root = project_root / "twins" / "reference-917-engine"
    engine = load_json(twin_root / "complete-engine-f1.json")
    detail = load_json(twin_root / "detail-expansion-f3.json")
    bench = load_json(twin_root / "test-bench-f4.json")
    support = load_json(twin_root / "start-support-f5.json")
    systems = load_json(twin_root / "systems-f4.json")
    endpoints = {
        "engine_family": {item["id"] for item in engine["component_families"]}
        | {item["id"] for item in detail["families"]},
        "bench_component": {item["id"] for item in bench["bench_components"]},
        "support_component": {item["id"] for item in support["support_components"]},
    }
    route_refs = {
        "F3": {item["id"] for item in detail["families"]},
        "F4": {item["id"] for item in systems["fluid_routes"]},
        "F5": {item["id"] for item in support["support_components"]},
    }
    return endpoints, route_refs


def validate_endpoint(endpoint: object, label: str, registry: dict[str, set[str]], errors: list[str]) -> None:
    if not isinstance(endpoint, dict):
        errors.append(f"{label}: endpoint must be an object")
        return
    scope = endpoint.get("scope")
    endpoint_id = endpoint.get("id")
    if scope not in VALID_SCOPES:
        errors.append(f"{label}: invalid endpoint scope {scope!r}")
        return
    if not isinstance(endpoint_id, str) or not endpoint_id:
        errors.append(f"{label}: endpoint id is required")
        return
    if scope != "external_interface" and endpoint_id not in registry[scope]:
        errors.append(f"{label}: unknown {scope} id {endpoint_id!r}")


def validate_profiled_entries(
    config: dict,
    collection_key: str,
    endpoint_keys: tuple[str, str],
    measurement_key: str,
    readiness_key: str,
    registry: dict[str, set[str]],
    errors: list[str],
) -> tuple[int, int, int]:
    profiles = config.get("input_profiles")
    entries = config.get(collection_key)
    if not isinstance(profiles, dict) or not profiles:
        errors.append(f"{collection_key}: input_profiles must be a non-empty object")
        return 0, 0, 0
    if not isinstance(entries, list) or not entries:
        errors.append(f"{collection_key}: collection must be a non-empty list")
        return 0, 0, 0

    for profile_id, fields in profiles.items():
        if not isinstance(fields, list) or not fields or not all(isinstance(field, str) and field for field in fields):
            errors.append(f"{collection_key}: profile {profile_id!r} must contain named inputs")
        elif len(fields) != len(set(fields)):
            errors.append(f"{collection_key}: profile {profile_id!r} contains duplicate inputs")

    ids: set[str] = set()
    instance_count = 0
    ready_count = 0
    for index, item in enumerate(entries):
        label = f"{collection_key}[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label}: entry must be an object")
            continue
        item_id = item.get("id")
        if not isinstance(item_id, str) or not item_id:
            errors.append(f"{label}: id is required")
        elif item_id in ids:
            errors.append(f"{label}: duplicate id {item_id!r}")
        else:
            ids.add(item_id)
            label = f"{collection_key}.{item_id}"

        count = item.get("count")
        if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
            errors.append(f"{label}: count must be a positive integer")
        else:
            instance_count += count
        if item.get("variant") not in VALID_VARIANTS:
            errors.append(f"{label}: invalid variant {item.get('variant')!r}")

        profile_id = item.get("input_profile")
        if profile_id not in profiles:
            errors.append(f"{label}: unknown input profile {profile_id!r}")
            required = []
        else:
            required = profiles[profile_id]
        measurements = item.get(measurement_key)
        if not isinstance(measurements, dict):
            errors.append(f"{label}: {measurement_key} must be an object")
            measurements = {}
        unknown = sorted(set(measurements) - set(required))
        if unknown:
            errors.append(f"{label}: measurements outside profile: {', '.join(unknown)}")
        complete = bool(required) and all(not is_missing(measurements.get(field)) for field in required)
        ready = item.get(readiness_key)
        if not isinstance(ready, bool):
            errors.append(f"{label}: {readiness_key} must be boolean")
        elif ready:
            ready_count += count if isinstance(count, int) and count > 0 else 0
            if not complete:
                errors.append(f"{label}: {readiness_key} cannot be true with missing measured inputs")

        for endpoint_key in endpoint_keys:
            validate_endpoint(item.get(endpoint_key), f"{label}.{endpoint_key}", registry, errors)

    return len(ids), instance_count, ready_count


def validate_contracts(project_root: Path, mechanical_path: Path, seals_path: Path, ducts_path: Path) -> dict:
    errors: list[str] = []
    try:
        mechanical = load_json(mechanical_path)
        seals = load_json(seals_path)
        ducts = load_json(ducts_path)
        registry, route_refs = endpoint_registry(project_root)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        return {"schema_version": "1.0.0", "status": "failed", "errors": [str(exc)]}

    sources = source_registry(project_root)
    for name, config in (("mechanical", mechanical), ("seals", seals), ("ducts", ducts)):
        if config.get("schema_version") != "1.0.0":
            errors.append(f"{name}: schema_version must be 1.0.0")
        if not str(config.get("status", "")).startswith("F8_"):
            errors.append(f"{name}: status must be an F8 status")
        for source_id in config.get("source_ids", []):
            if source_id not in sources:
                errors.append(f"{name}: unknown source_id {source_id!r}")
        forbidden = sorted(collect_keys(config) & FORBIDDEN_F9_KEYS)
        if forbidden:
            errors.append(f"{name}: F9 power keys are forbidden in F8: {', '.join(forbidden)}")
        if not config.get("prohibited_use"):
            errors.append(f"{name}: prohibited_use must be non-empty")

    mech_groups, mech_instances, physics_instances = validate_profiled_entries(
        mechanical,
        "mechanical_connections",
        ("body_a", "body_b"),
        "measurements",
        "physics_enabled",
        registry,
        errors,
    )
    seal_groups, seal_instances, released_seals = validate_profiled_entries(
        seals,
        "sealing_interfaces",
        ("interface_a", "interface_b"),
        "seal_specification",
        "seal_released",
        registry,
        errors,
    )
    duct_groups, duct_instances, released_ducts = validate_profiled_entries(
        ducts,
        "ducts",
        ("source", "target"),
        "measurements",
        "geometry_released",
        registry,
        errors,
    )

    flow_ready = 0
    for item in ducts.get("ducts", []):
        if not isinstance(item.get("flow_simulation_ready"), bool):
            errors.append(f"ducts.{item.get('id', '?')}: flow_simulation_ready must be boolean")
        elif item["flow_simulation_ready"]:
            flow_ready += item.get("count", 0)
            if not item.get("geometry_released"):
                errors.append(f"ducts.{item.get('id', '?')}: flow readiness requires released geometry")
        route_ref = item.get("upstream_route_ref")
        if route_ref is not None:
            if not isinstance(route_ref, str) or ":" not in route_ref:
                errors.append(f"ducts.{item.get('id', '?')}: invalid upstream_route_ref")
            else:
                stage, ref_id = route_ref.split(":", 1)
                if stage not in route_refs or ref_id not in route_refs[stage]:
                    errors.append(f"ducts.{item.get('id', '?')}: unknown upstream route {route_ref!r}")

    expected = (
        (mechanical, "connection_group_count", mech_groups),
        (mechanical, "connection_instance_count", mech_instances),
        (mechanical, "physics_joint_count", physics_instances),
        (seals, "seal_group_count", seal_groups),
        (seals, "seal_instance_count", seal_instances),
        (seals, "released_seal_count", released_seals),
        (ducts, "duct_group_count", duct_groups),
        (ducts, "duct_instance_count", duct_instances),
        (ducts, "released_geometry_count", released_ducts),
        (ducts, "flow_ready_count", flow_ready),
    )
    for config, key, actual in expected:
        if config.get("acceptance", {}).get(key) != actual:
            errors.append(f"acceptance.{key}: expected {actual}, got {config.get('acceptance', {}).get(key)!r}")

    if mechanical.get("acceptance", {}).get("physics_ready") is not False:
        errors.append("mechanical: physics_ready must remain false")
    if seals.get("acceptance", {}).get("pressure_boundary_ready") is not False:
        errors.append("seals: pressure_boundary_ready must remain false")
    if ducts.get("acceptance", {}).get("fluid_simulation_ready") is not False:
        errors.append("ducts: fluid_simulation_ready must remain false")

    return {
        "schema_version": "1.0.0",
        "status": "passed" if not errors else "failed",
        "counts": {
            "mechanical_connection_groups": mech_groups,
            "mechanical_connection_instances": mech_instances,
            "sealing_interface_groups": seal_groups,
            "sealing_interface_instances": seal_instances,
            "duct_groups": duct_groups,
            "duct_instances": duct_instances,
        },
        "readiness": {
            "physics_joint_instances": physics_instances,
            "released_seal_instances": released_seals,
            "released_duct_instances": released_ducts,
            "flow_ready_instances": flow_ready,
        },
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--mechanical", type=Path)
    parser.add_argument("--seals", type=Path)
    parser.add_argument("--ducts", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    project_root = args.project_root.resolve()
    twin_root = project_root / "twins" / "reference-917-engine"
    report = validate_contracts(
        project_root,
        (args.mechanical or twin_root / "mechanical-connections-f8.json").resolve(),
        (args.seals or twin_root / "sealing-interfaces-f8.json").resolve(),
        (args.ducts or twin_root / "ducts-f8.json").resolve(),
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
