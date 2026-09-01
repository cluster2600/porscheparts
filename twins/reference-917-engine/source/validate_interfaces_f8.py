#!/usr/bin/env python3
"""Validate the fail-closed 917 F8 connection, seal, duct and boundary contracts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
VALID_VARIANTS = {"all", "type_912_4_5_na", "917_30_only"}
VALID_SCOPES = {"engine_family", "bench_component", "support_component", "external_interface"}
FORBIDDEN_F9_KEYS = {"power", "power_kw", "horsepower", "target_power", "boost_target", "combustion_model"}
EXPECTED_STATUSES = {
    "mechanical": "F8_mechanical_connection_contract_measurements_pending",
    "seals": "F8_sealing_interface_contract_measurements_pending",
    "ducts": "F8_duct_contract_geometry_and_boundary_conditions_pending",
    "external": "F8_1_external_interface_registry_measurements_pending",
}
ROOT_KEYS = {
    "mechanical": {
        "schema_version", "status", "units", "base_stage_requirement", "source_ids", "upstream_contracts",
        "input_profiles", "mechanical_connections", "acceptance", "prohibited_use",
    },
    "seals": {
        "schema_version", "status", "units", "base_stage_requirement", "source_ids", "input_profiles",
        "sealing_interfaces", "acceptance", "prohibited_use",
    },
    "ducts": {
        "schema_version", "status", "units", "base_stage_requirement", "source_ids", "input_profiles",
        "ducts", "acceptance", "prohibited_use",
    },
    "external": {
        "schema_version", "status", "units", "base_stage_requirement", "source_ids", "input_profiles",
        "external_interfaces", "acceptance", "prohibited_use",
    },
}
ENTRY_KEYS = {
    "mechanical_connections": {
        "id", "count", "variant", "body_a", "body_b", "planned_constraint", "input_profile", "confidence",
        "measurements", "physics_enabled",
    },
    "sealing_interfaces": {
        "id", "count", "variant", "interface_a", "interface_b", "input_profile", "confidence",
        "seal_specification", "seal_released",
    },
    "ducts": {
        "id", "domain", "count", "variant", "source", "target", "input_profile", "upstream_route_ref",
        "coverage_status", "measurements", "geometry_released", "flow_simulation_ready",
    },
    "external_interfaces": {
        "id", "domain", "count", "variant", "input_profile", "traceability", "measurements",
        "geometry_released", "boundary_conditions_released",
    },
}
ACCEPTANCE_KEYS = {
    "mechanical": {"connection_group_count", "connection_instance_count", "physics_joint_count", "inventory_complete", "physics_ready"},
    "seals": {"seal_group_count", "seal_instance_count", "released_seal_count", "inventory_complete", "pressure_boundary_ready"},
    "ducts": {"duct_group_count", "duct_instance_count", "released_geometry_count", "flow_ready_count", "inventory_complete", "fluid_simulation_ready"},
    "external": {"external_interface_group_count", "external_interface_instance_count", "released_geometry_count", "released_boundary_condition_count", "inventory_complete", "geometry_ready", "boundary_conditions_ready"},
}
REQUIRED_TOPOLOGY = {
    "mechanical_connections": {
        "intake_valve_to_head_guide": {
            "count": 12,
            "variant": "all",
            "body_a": {"scope": "engine_family", "id": "intake_valve"},
            "body_b": {"scope": "engine_family", "id": "individual_head"},
            "planned_constraint": "prismatic",
            "input_profile": "prismatic_guided",
        },
        "exhaust_valve_to_head_guide": {
            "count": 12,
            "variant": "all",
            "body_a": {"scope": "engine_family", "id": "exhaust_valve"},
            "body_b": {"scope": "engine_family", "id": "individual_head"},
            "planned_constraint": "prismatic",
            "input_profile": "prismatic_guided",
        },
    },
    "sealing_interfaces": {
        "ambient_intake_to_turbo_compressor_inlet_connection": {
            "count": 2,
            "variant": "917_30_only",
            "interface_a": {"scope": "external_interface", "id": "bench_intake_ambient"},
            "interface_b": {"scope": "engine_family", "id": "turbocharger"},
            "input_profile": "hose_or_tube_fitting",
        },
        "na_exhaust_collector_to_bench_extraction_connection": {
            "count": 2,
            "variant": "type_912_4_5_na",
            "interface_a": {"scope": "engine_family", "id": "exhaust_collector"},
            "interface_b": {"scope": "bench_component", "id": "exhaust_extraction"},
            "input_profile": "hose_or_tube_fitting",
        },
        "turbo_turbine_outlet_to_bench_extraction_connection": {
            "count": 2,
            "variant": "917_30_only",
            "interface_a": {"scope": "engine_family", "id": "turbocharger"},
            "interface_b": {"scope": "bench_component", "id": "exhaust_extraction"},
            "input_profile": "hose_or_tube_fitting",
        },
        "bench_fuel_supply_to_injection_pump_fitting": {
            "count": 1,
            "variant": "all",
            "interface_a": {"scope": "bench_component", "id": "fuel_supply"},
            "interface_b": {"scope": "engine_family", "id": "twelve_plunger_injection_pump"},
            "input_profile": "hose_or_tube_fitting",
        },
        "injection_pump_to_injection_line_fittings": {
            "count": 12,
            "variant": "all",
            "interface_a": {"scope": "engine_family", "id": "twelve_plunger_injection_pump"},
            "interface_b": {"scope": "engine_family", "id": "injection_line"},
            "input_profile": "hose_or_tube_fitting",
        },
        "injection_line_to_injector_fittings": {
            "count": 12,
            "variant": "all",
            "interface_a": {"scope": "engine_family", "id": "injection_line"},
            "interface_b": {"scope": "engine_family", "id": "injector"},
            "input_profile": "hose_or_tube_fitting",
        },
    },
    "ducts": {
        "ambient_to_intake_trumpets": {
            "count": 12,
            "variant": "type_912_4_5_na",
            "source": {"scope": "external_interface", "id": "bench_intake_ambient"},
            "target": {"scope": "engine_family", "id": "intake_trumpet"},
            "domain": "intake_air",
            "input_profile": "compressible_intake",
        },
        "ambient_to_turbo_compressor_inlet": {
            "count": 2,
            "variant": "917_30_only",
            "source": {"scope": "external_interface", "id": "bench_intake_ambient"},
            "target": {"scope": "engine_family", "id": "turbocharger"},
            "domain": "intake_air",
            "input_profile": "compressible_intake",
        },
        "na_exhaust_collector_to_bench_extraction": {
            "count": 2,
            "variant": "type_912_4_5_na",
            "source": {"scope": "engine_family", "id": "exhaust_collector"},
            "target": {"scope": "bench_component", "id": "exhaust_extraction"},
            "domain": "exhaust_gas",
            "input_profile": "compressible_exhaust",
        },
        "turbo_turbine_outlet_to_bench_extraction": {
            "count": 2,
            "variant": "917_30_only",
            "source": {"scope": "engine_family", "id": "turbocharger"},
            "target": {"scope": "bench_component", "id": "exhaust_extraction"},
            "domain": "exhaust_gas",
            "input_profile": "compressible_exhaust",
        },
    },
}
FORBIDDEN_LEGACY_TOPOLOGY_IDS = {"valve_to_head_guide", "engine_exhaust_to_bench_extraction"}


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


def endpoint_registry(
    project_root: Path,
    external_interface_ids: set[str],
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
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
        "external_interface": external_interface_ids,
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
    unknown = sorted(set(endpoint) - {"scope", "id"})
    if unknown:
        errors.append(f"{label}: unknown endpoint fields: {', '.join(unknown)}")
    scope = endpoint.get("scope")
    endpoint_id = endpoint.get("id")
    if scope not in VALID_SCOPES:
        errors.append(f"{label}: invalid endpoint scope {scope!r}")
        return
    if not isinstance(endpoint_id, str) or not endpoint_id:
        errors.append(f"{label}: endpoint id is required")
        return
    if endpoint_id not in registry[scope]:
        errors.append(f"{label}: unknown {scope} id {endpoint_id!r}")


def validate_required_topology(config: dict, collection_key: str, errors: list[str]) -> None:
    entries = config.get(collection_key)
    if not isinstance(entries, list):
        return
    by_id = {
        item["id"]: item
        for item in entries
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    for legacy_id in sorted(FORBIDDEN_LEGACY_TOPOLOGY_IDS & set(by_id)):
        errors.append(f"{collection_key}: ambiguous legacy topology id is forbidden: {legacy_id!r}")
    for item_id, expected_fields in REQUIRED_TOPOLOGY[collection_key].items():
        item = by_id.get(item_id)
        if item is None:
            errors.append(f"{collection_key}: required F8.1 topology entry missing: {item_id!r}")
            continue
        for field, expected in expected_fields.items():
            if item.get(field) != expected:
                errors.append(
                    f"{collection_key}.{item_id}: {field} must remain {expected!r}, got {item.get(field)!r}"
                )


def validate_profiled_entries(
    config: dict,
    collection_key: str,
    endpoint_keys: tuple[str, str],
    measurement_key: str,
    readiness_key: str,
    allowed_entry_keys: set[str],
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
        missing_fields = sorted(allowed_entry_keys - set(item))
        unknown_fields = sorted(set(item) - allowed_entry_keys)
        if missing_fields:
            errors.append(f"{label}: missing fields: {', '.join(missing_fields)}")
        if unknown_fields:
            errors.append(f"{label}: unknown fields: {', '.join(unknown_fields)}")
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
        if not isinstance(profile_id, str) or profile_id not in profiles:
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


def validate_contracts(
    project_root: Path,
    mechanical_path: Path,
    seals_path: Path,
    ducts_path: Path,
    external_interfaces_path: Path,
) -> dict:
    errors: list[str] = []
    try:
        mechanical = load_json(mechanical_path)
        seals = load_json(seals_path)
        ducts = load_json(ducts_path)
        external = load_json(external_interfaces_path)
        external_entries = external.get("external_interfaces")
        external_ids = {
            item["id"]
            for item in external_entries
            if isinstance(item, dict) and isinstance(item.get("id"), str) and item["id"]
        } if isinstance(external_entries, list) else set()
        registry, route_refs = endpoint_registry(project_root, external_ids)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        return {"schema_version": "1.0.0", "status": "failed", "errors": [str(exc)]}

    sources = source_registry(project_root)
    for name, config in (("mechanical", mechanical), ("seals", seals), ("ducts", ducts), ("external", external)):
        missing_root = sorted(ROOT_KEYS[name] - set(config))
        unknown_root = sorted(set(config) - ROOT_KEYS[name])
        if missing_root:
            errors.append(f"{name}: missing root fields: {', '.join(missing_root)}")
        if unknown_root:
            errors.append(f"{name}: unknown root fields: {', '.join(unknown_root)}")
        if config.get("schema_version") != "1.0.0":
            errors.append(f"{name}: schema_version must be 1.0.0")
        if config.get("status") != EXPECTED_STATUSES[name]:
            errors.append(f"{name}: status must remain {EXPECTED_STATUSES[name]!r}")
        source_ids = config.get("source_ids")
        if not isinstance(source_ids, list) or not source_ids or not all(isinstance(source_id, str) and source_id for source_id in source_ids):
            errors.append(f"{name}: source_ids must be a non-empty string array")
        else:
            for source_id in source_ids:
                if source_id not in sources:
                    errors.append(f"{name}: unknown source_id {source_id!r}")
        forbidden = sorted(collect_keys(config) & FORBIDDEN_F9_KEYS)
        if forbidden:
            errors.append(f"{name}: F9 power keys are forbidden in F8: {', '.join(forbidden)}")
        prohibited_use = config.get("prohibited_use")
        if not isinstance(prohibited_use, list) or not prohibited_use or not all(isinstance(value, str) and value for value in prohibited_use):
            errors.append(f"{name}: prohibited_use must be a non-empty string array")
        acceptance = config.get("acceptance")
        if not isinstance(acceptance, dict):
            errors.append(f"{name}: acceptance must be an object")
        else:
            missing_acceptance = sorted(ACCEPTANCE_KEYS[name] - set(acceptance))
            unknown_acceptance = sorted(set(acceptance) - ACCEPTANCE_KEYS[name])
            if missing_acceptance:
                errors.append(f"{name}: missing acceptance fields: {', '.join(missing_acceptance)}")
            if unknown_acceptance:
                errors.append(f"{name}: unknown acceptance fields: {', '.join(unknown_acceptance)}")

    external_groups, external_instances, released_external_geometry = validate_profiled_entries(
        external,
        "external_interfaces",
        (),
        "measurements",
        "geometry_released",
        ENTRY_KEYS["external_interfaces"],
        registry,
        errors,
    )
    released_external_boundaries = 0
    for item in external_entries if isinstance(external_entries, list) else []:
        if not isinstance(item, dict):
            continue
        label = f"external_interfaces.{item.get('id', '?')}"
        if not isinstance(item.get("domain"), str) or not item["domain"]:
            errors.append(f"{label}: domain must be a non-empty string")
        if not isinstance(item.get("traceability"), str) or not item["traceability"]:
            errors.append(f"{label}: traceability must be a non-empty string")
        boundary_released = item.get("boundary_conditions_released")
        if not isinstance(boundary_released, bool):
            errors.append(f"{label}: boundary_conditions_released must be boolean")
        elif boundary_released:
            released_external_boundaries += item.get("count", 0)

    mech_groups, mech_instances, physics_instances = validate_profiled_entries(
        mechanical,
        "mechanical_connections",
        ("body_a", "body_b"),
        "measurements",
        "physics_enabled",
        ENTRY_KEYS["mechanical_connections"],
        registry,
        errors,
    )
    seal_groups, seal_instances, released_seals = validate_profiled_entries(
        seals,
        "sealing_interfaces",
        ("interface_a", "interface_b"),
        "seal_specification",
        "seal_released",
        ENTRY_KEYS["sealing_interfaces"],
        registry,
        errors,
    )
    duct_groups, duct_instances, released_ducts = validate_profiled_entries(
        ducts,
        "ducts",
        ("source", "target"),
        "measurements",
        "geometry_released",
        ENTRY_KEYS["ducts"],
        registry,
        errors,
    )
    validate_required_topology(mechanical, "mechanical_connections", errors)
    validate_required_topology(seals, "sealing_interfaces", errors)
    validate_required_topology(ducts, "ducts", errors)

    flow_ready = 0
    duct_entries = ducts.get("ducts") if isinstance(ducts.get("ducts"), list) else []
    for item in duct_entries:
        if not isinstance(item, dict):
            continue
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
        (external, "external_interface_group_count", external_groups),
        (external, "external_interface_instance_count", external_instances),
        (external, "released_geometry_count", released_external_geometry),
        (external, "released_boundary_condition_count", released_external_boundaries),
    )
    for config, key, actual in expected:
        acceptance = config.get("acceptance") if isinstance(config.get("acceptance"), dict) else {}
        if acceptance.get(key) != actual:
            errors.append(f"acceptance.{key}: expected {actual}, got {acceptance.get(key)!r}")

    if physics_instances:
        errors.append("mechanical: physics_enabled must remain false for every F8 connection")
    if released_seals:
        errors.append("seals: seal_released must remain false for every F8 interface")
    if released_ducts:
        errors.append("ducts: geometry_released must remain false for every F8 duct")
    if flow_ready:
        errors.append("ducts: flow_simulation_ready must remain false for every F8 duct")
    if released_external_geometry:
        errors.append("external: geometry_released must remain false for every F8.1 boundary")
    if released_external_boundaries:
        errors.append("external: boundary_conditions_released must remain false for every F8.1 boundary")

    mechanical_acceptance = mechanical.get("acceptance") if isinstance(mechanical.get("acceptance"), dict) else {}
    seal_acceptance = seals.get("acceptance") if isinstance(seals.get("acceptance"), dict) else {}
    duct_acceptance = ducts.get("acceptance") if isinstance(ducts.get("acceptance"), dict) else {}
    external_acceptance = external.get("acceptance") if isinstance(external.get("acceptance"), dict) else {}
    if mechanical_acceptance.get("inventory_complete") is not False:
        errors.append("mechanical: inventory_complete must remain false")
    if seal_acceptance.get("inventory_complete") is not False:
        errors.append("seals: inventory_complete must remain false")
    if duct_acceptance.get("inventory_complete") is not False:
        errors.append("ducts: inventory_complete must remain false")
    if external_acceptance.get("inventory_complete") is not False:
        errors.append("external: inventory_complete must remain false")
    if mechanical_acceptance.get("physics_ready") is not False:
        errors.append("mechanical: physics_ready must remain false")
    if seal_acceptance.get("pressure_boundary_ready") is not False:
        errors.append("seals: pressure_boundary_ready must remain false")
    if duct_acceptance.get("fluid_simulation_ready") is not False:
        errors.append("ducts: fluid_simulation_ready must remain false")
    if external_acceptance.get("geometry_ready") is not False:
        errors.append("external: geometry_ready must remain false")
    if external_acceptance.get("boundary_conditions_ready") is not False:
        errors.append("external: boundary_conditions_ready must remain false")

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
            "external_interface_groups": external_groups,
            "external_interface_instances": external_instances,
        },
        "readiness": {
            "physics_joint_instances": physics_instances,
            "released_seal_instances": released_seals,
            "released_duct_instances": released_ducts,
            "flow_ready_instances": flow_ready,
            "released_external_geometry_instances": released_external_geometry,
            "released_external_boundary_instances": released_external_boundaries,
        },
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--mechanical", type=Path)
    parser.add_argument("--seals", type=Path)
    parser.add_argument("--ducts", type=Path)
    parser.add_argument("--external-interfaces", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    project_root = args.project_root.resolve()
    twin_root = project_root / "twins" / "reference-917-engine"
    report = validate_contracts(
        project_root,
        (args.mechanical or twin_root / "mechanical-connections-f8.json").resolve(),
        (args.seals or twin_root / "sealing-interfaces-f8.json").resolve(),
        (args.ducts or twin_root / "ducts-f8.json").resolve(),
        (args.external_interfaces or twin_root / "external-interfaces-f8.json").resolve(),
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
